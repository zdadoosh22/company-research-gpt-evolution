"""Transparent calculation primitives. No network, automatic forecasts or market anchoring."""
from datetime import date
from math import isfinite, exp, expm1, log1p, nextafter


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{name}: finite numeric input required; missing is not zero')
    return float(value)


def ttm(full_year, current_ytd, prior_ytd, *, compatible=True):
    if not compatible:
        raise ValueError('Incompatible cumulative periods/scope/currency')
    return number(full_year, 'full year') + number(current_ytd, 'current YTD') - number(prior_ytd, 'prior YTD')


def dated_years(start, end):
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    if days <= 0:
        raise ValueError('End date must follow start date')
    return days / 365.0


def discounted_cashflows(flows, dates, as_of, rate):
    rate = number(rate, 'discount rate')
    if rate <= -1 or len(flows) != len(dates):
        raise ValueError('Invalid discount rate or cash-flow/date lengths')
    origin = date.fromisoformat(as_of)
    total = 0.0
    for cash, when in zip(flows, dates):
        year = (date.fromisoformat(when) - origin).days / 365.0
        if year < 0:
            raise ValueError('Cash-flow date precedes valuation date')
        total += number(cash, 'cash flow') / (1 + rate) ** year
    return total


def xirr(flows, dates):
    if len(flows) != len(dates) or len(flows) < 2:
        raise ValueError('XIRR needs matching cash flows and dates')
    flows = [number(x, 'cash flow') for x in flows]
    if flows[0] >= 0 or any(x < 0 for x in flows[1:]) or not any(x > 0 for x in flows[1:]):
        raise ValueError('Supported shareholder XIRR needs one initial outflow followed by nonnegative receipts')
    if dates != sorted(dates) or dates[-1] == dates[0]:
        raise ValueError('Cash-flow dates must be ordered and span time')
    origin=date.fromisoformat(dates[0])
    years=[(date.fromisoformat(d)-origin).days/365 for d in dates]
    def npv_log(z):
        try:
            return sum(c*exp(-z*y) for c,y in zip(flows,years) if c)
        except OverflowError:
            return float('inf')  # Only future nonnegative receipts can overflow.
    # Solve in log(1+r), including deep losses close to -100%. Both endpoints
    # must actually bracket a root; a hardcoded lower rate is not a result.
    lo,hi=log1p(nextafter(-1.0,0.0)),log1p(1.0)
    while npv_log(hi)>0 and hi<709:
        hi=min(709,hi*2)
    if npv_log(lo)<0 or npv_log(hi)>0:
        raise ValueError('Cannot bracket shareholder return at supported numeric precision')
    for _ in range(180):
        mid = (lo + hi) / 2
        if npv_log(mid) > 0:
            lo = mid
        else:
            hi = mid
    result=expm1((lo+hi)/2)
    if not isfinite(result) or result<=-1:
        raise ValueError('Shareholder return exceeds supported numeric precision')
    residual=discounted_cashflows(flows,dates,dates[0],result)
    if abs(residual)>max(1,abs(flows[0]))*1e-8:
        raise ValueError('Shareholder return cannot meet the cash-flow residual tolerance')
    return result


def shareholder_path(model, scenario):
    """Equity dividend/retention model, FCFE after debt service; no second debt deduction.

    Terminal continuing value excludes accumulated excess cash; add that cash once.
    Existing awards belong in opening ownership. Forecast EBIT expenses future SBC;
    future gross dilution must represent separate justified claims, not the same awards.
    """
    dates = model['forecast_dates']
    if not dates or dates != sorted(set(dates)):
        raise ValueError('Forecast dates must be unique and ordered')
    n = len(dates)
    k = number(scenario['cost_of_equity'], 'cost of equity')
    g = number(scenario['terminal_growth'], 'terminal growth')
    if k <= g or k <= 0 or g < 0:
        raise ValueError('Fixed-debt perpetuity requires nonnegative growth below positive equity cost')
    revenue = number(model['base_revenue'], 'base revenue')
    if revenue <= 0:
        raise ValueError('This operating pattern requires positive opening revenue')
    shares = number(model['diluted_shares'], 'ownership shares')
    cash = number(model['excess_cash'], 'opening excess cash')
    if shares <= 0 or cash < 0:
        raise ValueError('Shares positive; excess cash nonnegative')
    arrays = ['growth', 'operating_margin', 'tax_rate', 'da_ratio', 'capex_ratio', 'working_capital_ratio', 'interest', 'net_borrowing', 'dividend_payout', 'buybacks', 'gross_dilution', 'repurchase_price', 'cash_yield']
    for key in arrays:
        if len(scenario[key]) != n:
            raise ValueError(f'{key}: one input per forecast period required')
    previous = model['as_of']
    rows = []
    divs = []
    for i, end in enumerate(dates):
        dt = dated_years(previous, end)
        growth = number(scenario['growth'][i], 'growth')
        if growth <= -1:
            raise ValueError('Revenue growth must exceed -100%')
        prior_revenue = revenue
        revenue *= (1 + growth) ** dt
        margin = number(scenario['operating_margin'][i], 'margin')
        tax = number(scenario['tax_rate'][i], 'tax')
        payout = number(scenario['dividend_payout'][i], 'payout')
        if not 0 <= tax <= 1 or not 0 <= payout <= 1:
            raise ValueError('Tax and payout between 0 and 1')
        ebit = revenue * margin * dt
        da = revenue * number(scenario['da_ratio'][i], 'DA ratio') * dt
        capex = revenue * number(scenario['capex_ratio'][i], 'capex ratio') * dt
        wc = (revenue - prior_revenue) * number(scenario['working_capital_ratio'][i], 'working capital ratio')
        interest = number(scenario['interest'][i], 'annual interest') * dt
        net_borrowing = number(scenario['net_borrowing'][i], 'net borrowing') * dt
        if any(scenario[key][i] < 0 for key in ['da_ratio', 'capex_ratio', 'working_capital_ratio', 'interest']):
            raise ValueError('DA, capex, working capital and interest inputs must be nonnegative')
        if net_borrowing != 0:
            raise ValueError('Nonzero net borrowing requires a separately validated debt, service and claims schedule')
        fcfe = (ebit - interest) * (1 - tax) + da - capex - wc + net_borrowing
        dividend = max(fcfe, 0) * payout
        buyback = number(scenario['buybacks'][i], 'buyback')
        dilution = number(scenario['gross_dilution'][i], 'gross dilution')
        repurchase = number(scenario['repurchase_price'][i], 'repurchase price')
        cash_yield = number(scenario['cash_yield'][i], 'cash yield')
        if buyback < 0 or dilution < 0 or repurchase <= 0 or cash_yield <= -1:
            raise ValueError('Invalid buyback, dilution, repurchase price or cash yield')
        # Dividends precede end-period issuance/buyback. Treasury interest is retained.
        dps = dividend / shares
        cash = cash * (1 + cash_yield) ** dt + fcfe - dividend - buyback
        shares = shares * (1 + dilution) ** dt - buyback / repurchase
        if cash < -1e-8 or shares <= 0:
            raise ValueError('Unfunded liquidity/repurchase path: financing assumptions required')
        years = dated_years(model['as_of'], end)
        rows.append(dict(date=end, fraction=dt, years=years, revenue=revenue, ebit=ebit, tax_rate=tax, da=da, capex=capex, working_capital=wc, interest=interest, net_borrowing=net_borrowing, fcfe=fcfe, dividends=dividend, dividend_per_share=dps, buybacks=buyback, shares=shares, excess_cash=cash))
        divs.append(dps)
        previous = end
    last = rows[-1]
    # Rebuild the annual terminal period: terminal growth changes reinvestment.
    # Perpetual borrowing is not an operating source of value.
    terminal_revenue = revenue * (1 + g)
    terminal_pre_interest_fcfe = terminal_revenue * margin * (1 - tax)
    terminal_pre_interest_fcfe += terminal_revenue * (number(scenario['da_ratio'][-1], 'terminal DA') - number(scenario['capex_ratio'][-1], 'terminal capex'))
    terminal_pre_interest_fcfe -= (terminal_revenue - revenue) * number(scenario['working_capital_ratio'][-1], 'terminal working capital')
    terminal_after_tax_interest = number(scenario['interest'][-1], 'terminal annual interest') * (1 - tax)
    terminal_fcfe = terminal_pre_interest_fcfe - terminal_after_tax_interest
    if terminal_fcfe <= 0:
        raise ValueError('Perpetuity requires positive sustainable FCFE; use conditional/finite-life model')
    # Operating cash grows at g; fixed-principal refinancing keeps annual interest
    # constant. Do not silently make the interest claim grow with operating cash.
    terminal_interest_value = terminal_after_tax_interest / k
    operating_equity = terminal_pre_interest_fcfe / (k - g) - terminal_interest_value
    horizon_value = (operating_equity + cash + number(model.get('other_equity_assets', 0), 'other assets')) / shares
    receipts = divs[:]
    receipts[-1] += horizon_value
    current_value = discounted_cashflows(receipts, dates, model['as_of'], k)
    price = model.get('price')
    price_date = model.get('price_date') or model['as_of']
    if price_date > model['as_of']:
        raise ValueError('Price observation cannot follow the research cutoff')
    if price is not None and number(price, 'dated price') <= 0:
        raise ValueError('Dated security price must be positive')
    returns = None if price is None else xirr([-price] + receipts, [price_date] + dates)
    entry_prices = {str(h): discounted_cashflows(receipts, dates, model['as_of'], h) for h in [0.08, 0.10, 0.12, 0.15]}
    return dict(rows=rows, current_value=current_value, horizon_value=horizon_value, terminal_fcfe=terminal_fcfe, terminal_pre_interest_fcfe=terminal_pre_interest_fcfe, terminal_after_tax_interest=terminal_after_tax_interest, terminal_interest_value=terminal_interest_value, terminal_operating_equity=operating_equity, annualised_return=returns, entry_prices=entry_prices, receipts=receipts, horizon_date=dates[-1], holding_years=last['years'], method='Equity dividend/retention model; fixed-principal refinancing, growing operating cash and constant interest')


def bank_excess_return(book_per_share, roe, cost_of_equity, growth):
    tbv = number(book_per_share, 'tangible book per share')
    roe=number(roe,'prospective return on tangible equity')
    cost_of_equity=number(cost_of_equity,'bank equity cost')
    growth=number(growth,'bank sustainable growth')
    if tbv <= 0 or not 0 <= growth < min(roe, cost_of_equity):
        raise ValueError('Positive book, sustainable ROE and equity cost above growth required')
    return tbv * (roe - growth) / (cost_of_equity - growth)


def financing_runway(cash, burn_per_year, commitments=0):
    cash = number(cash, 'unrestricted cash') - number(commitments, 'commitments')
    burn = number(burn_per_year, 'forward annual burn')
    if cash < 0 or burn <= 0:
        raise ValueError('Funding need or invalid forward burn; runway is not a negative/zero success')
    return cash / burn * 12
