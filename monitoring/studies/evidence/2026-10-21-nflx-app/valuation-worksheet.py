"""Scratch valuation arithmetic for 2026-10-21 NFLX/APP dossiers (uses repo tools; not a repo deliverable)."""
import sys, json
from datetime import date
sys.path.insert(0, r'C:\Users\aidan\Documents\Company research 2\tools')
import finance, decision_economics as de

GBP_PER_USD = '0.74638'   # 1 / 1.3398 (Yahoo GBPUSD=X 2026-10-21 18:44Z)
FX = 0.0015               # Trading 212 FX fee each way (additive on GBP gross)
TERMS = dict(currency='USD', unit='major', gbp_per_major_unit=GBP_PER_USD,
             fx_direction='GBP_per_major_unit', fee_rate=str(FX), tax_rate='0', fixed_fees_gbp='0')

def implied_growth(ev, fcf0, disc, years=10, term_g=0.03, fade=True):
    """Solve constant 10y FCF growth g so PV(FCF path)+PV(terminal) == EV. Dates yearly from 2026-10-21."""
    def pv(g):
        flows, dates = [], []
        f = fcf0
        for y in range(1, years + 1):
            f *= (1 + g)
            flows.append(f); dates.append(f'{2026 + y}-10-21')
        tv = f * (1 + term_g) / (disc - term_g)
        flows[-1] += tv
        return finance.discounted_cashflows(flows, dates, '2026-10-21', disc)
    lo, hi = -0.2, 0.6
    for _ in range(80):
        mid = (lo + hi) / 2
        if pv(mid) < ev: lo = mid
        else: hi = mid
    return (lo + hi) / 2

out = {}
# ---------------- NFLX ----------------
px, sh = 65.80, 4165.0           # $/share; FD shares (m) est. period-end (Q3 wtd 4,195 less ~half of 63.9m Q3 buyback)
cap = px * sh / 1000             # $bn
netdebt = 7.114                  # company-defined, 30 Sep 2026
leases = 2.330                   # operating lease liability 30 Jun 2026 (cost already inside CFO/FCF)
ev = cap + netdebt
fcf_guide, windfall_at, radford = 12.0, 2.2, 0.5
fcf_norm = fcf_guide - windfall_at + radford
out['NFLX'] = dict(px=px, shares_m=sh, mktcap_bn=round(cap, 1), net_debt_bn=netdebt, ev_bn=round(ev, 1),
                   ev_incl_leases_bn=round(ev + leases, 1), fcf_norm_bn=round(fcf_norm, 2),
                   fcf_yield_pct=round(fcf_norm / cap * 100, 2),
                   implied_10y_growth_at_9pct=round(implied_growth(ev, fcf_norm, 0.09) * 100, 1),
                   implied_10y_growth_at_8pct=round(implied_growth(ev, fcf_norm, 0.08) * 100, 1))
# FY27 EPS scenarios
def eps(rev26, g, m, interest_net, tax, shares):
    oi = rev26 * (1 + g) * m
    ni = (oi - interest_net) * (1 - tax)
    return ni / shares, ni
for name, g, m, sh27 in (('bear', .09, .30, 4100), ('base', .115, .325, 4046), ('bull', .13, .34, 3990)):
    e, ni = eps(51.1, g, m, 0.66, 0.17, sh27 / 1000)
    out['NFLX'][f'FY27_EPS_{name}'] = round(e, 2); out['NFLX'][f'FY27_NI_{name}_bn'] = round(ni, 2)
out['NFLX']['PE_at_price_on_base_FY27'] = round(px / out['NFLX']['FY27_EPS_base'], 1)

# ---------------- APP ----------------
apx, ash = 267.90, 337.0
acap = apx * ash / 1000
adebt, acash = 3.55, 3.053       # note principal; 30 Jun 2026 cash
aev = acap + adebt - acash
ebitda_q3 = 1.725; da = .033; sbc = .090; intr = .051; intinc = .030; tax = .16
pbt = ebitda_q3 - da - sbc - intr + intinc
ni_q = pbt * (1 - tax)
owner_q = ni_q + da - 0.006      # SBC treated as cash-equivalent cost (no add-back); capex+fin-lease principal
owner_ann_prewc = owner_q * 4
owner_ann = owner_ann_prewc - 0.4   # ~$0.1bn/qtr receivables build drag
h1_fcf_after_sbc = (2.160433 - 0.012) - 0.169252
out['APP'] = dict(px=apx, shares_m=ash, mktcap_bn=round(acap, 1), net_debt_bn=round(adebt - acash, 2), ev_bn=round(aev, 1),
                  q3_NI_run_bn=round(ni_q, 3), q3_EPS_implied=round(ni_q * 1000 / ash, 2),
                  owner_fcfe_runrate_bn=round(owner_ann, 2), owner_fcfe_H1_annualised_bn=round(h1_fcf_after_sbc * 2, 2),
                  fcfe_yield_runrate_pct=round(owner_ann / acap * 100, 2), fcfe_yield_H1_pct=round(h1_fcf_after_sbc * 2 / acap * 100, 2),
                  implied_10y_growth_runrate_at_11pct=round(implied_growth(aev, owner_ann, 0.11) * 100, 1),
                  implied_10y_growth_H1_at_11pct=round(implied_growth(aev, h1_fcf_after_sbc * 2, 0.11) * 100, 1),
                  FY26E_EPS=round(3.56 + 3.76 + 3.94 + 4.2, 2))
out['APP']['PE_on_FY26E'] = round(apx / out['APP']['FY26E_EPS'], 1)

# ---------------- hurdle tests via decision_economics ----------------
def test(name, entry, bear, base, bull, stop, probs, budget):
    slip = entry * 1.004                       # manual-delay/spread allowance on entry
    sizing = de.derive_entry(str(budget), f'{slip:.2f}', '0.0001', **TERMS)
    q = sizing['quantity']
    sc = lambda n, x: dict(name=n, entry_native_price=f'{slip:.2f}', exit_native_price=f'{x:.2f}',
                           entry_terms=TERMS, exit_terms=TERMS)
    res = de.scenario_analysis(q, [sc('bear', bear), sc('base', base), sc('bull', bull), sc('stop', stop)])
    g = {r['name']: float(r['gain_loss_gbp']) for r in res['scenarios']}
    debit = float(res['scenarios'][0]['entry_debit_gbp'])
    pct = {k: v / debit * 100 for k, v in g.items()}
    pb, pm, pu = probs
    ev_pct = pb * pct['bear'] + pm * pct['base'] + pu * pct['bull']
    up = pm * pct['base'] + pu * pct['bull']; dn = -pb * pct['bear']
    be = de.round_trip_break_even(q, f'{slip:.2f}', '0.01', TERMS, TERMS)
    return dict(name=name, qty=q, entry_with_delay=round(slip, 2), debit_gbp=round(debit, 2),
                net_pct={k: round(v, 2) for k, v in pct.items()}, gbp={k: round(v, 2) for k, v in g.items()},
                prob_weighted_net_pct=round(ev_pct, 2), up_to_down_ratio=round(up / dn, 2),
                breakeven_exit=be['exit_native_price'], base_passes_8pct=pct['base'] > 8, ratio_passes_2=(up / dn) > 2)

def ceiling(entry_grid, bear, base, bull, probs):
    pb, pm, pu = probs; best = None
    for e in entry_grid:
        slip = e * 1.004
        b = lambda x: (x * (1 - FX)) / (slip * (1 + FX)) - 1
        up = pm * b(base) + pu * b(bull); dn = -pb * b(bear)
        if b(base) > 0.08 and up / dn > 2: best = e
    return best

out['NFLX_test'] = test('NFLX', 65.80, 48.70, 71.40, 90.90, 60.00, (.35, .45, .20), 100)
out['NFLX_ceiling'] = ceiling([x / 10 for x in range(500, 700)], 48.70, 71.40, 90.90, (.35, .45, .20))
out['APP_test100'] = test('APP', 267.90, 205.00, 285.00, 360.00, 236.00, (.30, .45, .25), 100)
out['APP_test75'] = test('APP75', 267.90, 205.00, 285.00, 360.00, 236.00, (.30, .45, .25), 75)
out['APP_ceiling'] = ceiling([x / 10 for x in range(2000, 3000)], 205.00, 285.00, 360.00, (.30, .45, .25))
print(json.dumps(out, indent=1))
