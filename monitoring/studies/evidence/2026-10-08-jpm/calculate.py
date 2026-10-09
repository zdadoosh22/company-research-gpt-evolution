from decimal import Decimal as D
from pathlib import Path
import json

p=D('329.58'); tbv=D('113.35'); shares=D('2.6942'); tax=D('0.25')
h1=D('46.957'); guide=D('96.5'); q2=D('23.677'); card=D('243.5')
calc={
 'units':'USD billions unless per-share, ratio or stated otherwise; shares in billions',
 'h2_nii_ex_markets_required':str(guide-h1),
 'h2_half_on_half_growth_pct':str(((guide-h1)/h1-1)*100),
 'h2_quarterly_average_required':str((guide-h1)/2),
 'h2_quarterly_average_vs_q2_pct':str((((guide-h1)/2)/q2-1)*100),
 'incremental_eps_per_1bn_pretax':str((1-tax)/shares),
 'nii_1_5bn_eps':str(D('1.5')*(1-tax)/shares),
 'nii_1_5bn_equal_quarter_allocation_eps':str(D('1.5')*(1-tax)/shares/4),
 'card_3_47_vs_3_20_annual_nco_increment':str(card*D('0.0027')),
 'card_increment_annual_eps_drag':str(card*D('0.0027')*(1-tax)/shares),
 'combined_nii_reversal_and_card_annual_eps_drag':str((D('1.5')+card*D('0.0027'))*(1-tax)/shares),
 'price_to_dated_tbv':str(p/tbv),
 'q2_adjusted_eps_annualized_not_forecast':str(D('6.14')*4),
 'price_to_q2_adjusted_annualized_not_forward_PE':str(p/(D('6.14')*4)),
 'transient_1_5bn_aftertax_per_end_period_share':str(D('1.5')*(1-tax)/D('2.658186195')),
 'conditional_constant_multiple_nii_increment':str((D('1.5')*(1-tax)/shares)*p/(D('6.14')*4)),
 'conditional_constant_multiple_combined_decrement':str(((D('1.5')+card*D('0.0027'))*(1-tax)/shares)*p/(D('6.14')*4)),
 'capital_headroom_advanced_total':str(D('346.248')-D('0.15')*D('2123.862')),
 'capital_headroom_standardized_CET1':str(D('302.619')-D('0.115')*D('2132.428')),
 'advanced_RWA_h1_increase':str(D('2123.862')-D('2045.249')),
 'advanced_requirement_if_h1_RWA_increment_repeats':str((D('2123.862')-D('2045.249'))*D('0.15')),
 'uninsured_deposit_ratio_pct':str(D('1743.9')/D('2713.7')*100),
 'repricing_multiple_r_open_as_function':'r_open = g + '+str(p/tbv)+' * (k - g); algebra only, June TBV and October price',
}
assert guide-h1==D('49.543')
assert D('346.248')-D('0.15')*D('2123.862')==D('27.66870')
assert D('1.5')*(1-tax)==D('1.125')
Path(__file__).with_name('calculations.json').write_text(json.dumps(calc,indent=2),encoding='utf-8')
print(json.dumps(calc,indent=2))
