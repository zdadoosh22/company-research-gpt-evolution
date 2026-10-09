"""Synthetic exit/cost illustrations, not forecasts or a broker matching engine.

No production ledger writes, source retrieval, model calls or real orders.
Every path, stop and delay below is a deliberately constructed test fixture.
"""
from decimal import Decimal, localcontext
import json
from pathlib import Path


def number(value, *, positive=False):
    if isinstance(value,(bool,float)): raise ValueError('Use exact decimal strings')
    value=Decimal(str(value))
    if not value.is_finite() or value<0 or (positive and value==0): raise ValueError('Invalid nonnegative number')
    return value


def illustrate(prices, *, policy, initial='300', entry_cost_rate='0.0015',
               exit_cost_rate='0.0015', stop='95', stop_limit='90',
               deterioration_at=None, response_delay=1):
    """Prices are hypothetical executable GBP-equivalent quotes per share.

    A stop-market assumes execution at the first observed quote below its trigger;
    a real fill could be worse. A stop-limit assumes enough liquidity at an observed
    bid meeting its limit. Neither assumption establishes real execution quality.
    A thesis exit uses only the supplied, contemporaneously declared deterioration
    event, then waits response_delay observations. Missing future quote stays open.
    """
    if policy not in ('stop-market','stop-limit','thesis','time'): raise ValueError('Unknown policy')
    if type(response_delay) is not int or response_delay<0: raise ValueError('Invalid response delay')
    if deterioration_at is not None and (type(deterioration_at) is not int or deterioration_at<1 or deterioration_at>=len(prices)):
        raise ValueError('Invalid event index')
    with localcontext() as context:
        context.prec=50
        prices=[number(x,positive=True) for x in prices]
        if len(prices)<2: raise ValueError('Need entry and later observations')
        budget=number(initial,positive=True)
        entry_rate=number(entry_cost_rate); exit_rate=number(exit_cost_rate)
        if entry_rate>=1 or exit_rate>=1: raise ValueError('Cost rate must be below one')
        trigger=number(stop,positive=True); limit=number(stop_limit,positive=True)
        if policy=='stop-limit' and limit>trigger: raise ValueError('Sell limit cannot exceed this fixture stop')
        shares=budget/(prices[0]*(1+entry_rate))
        triggered=None; exit_index=None
        if policy in ('stop-market','stop-limit'):
            for index,price in enumerate(prices[1:],1):
                if triggered is None and price<=trigger: triggered=index
                if triggered is not None and (policy=='stop-market' or price>=limit):
                    exit_index=index; break
        elif policy=='thesis' and deterioration_at is not None:
            requested=deterioration_at+response_delay
            if requested<len(prices): exit_index=requested
        elif policy=='time': exit_index=len(prices)-1
        mark=prices[exit_index] if exit_index is not None else prices[-1]
        gross=shares*mark
        fees=gross*exit_rate if exit_index is not None else Decimal(0)
        value=gross-fees
        return {'policy':policy,'status':'closed' if exit_index is not None else 'open',
          'triggered_at':triggered,'exit_observation':exit_index,'shares':str(shares),
          'entry_cost_gbp':str(budget-shares*prices[0]),'exit_cost_gbp':str(fees),
          'cash_gbp':str(value if exit_index is not None else Decimal(0)),
          'open_marked_value_gbp':str(value if exit_index is None else Decimal(0)),
          'marked_total_gbp':str(value),'gain_loss_gbp':str(value-budget),
          'future_liquidation_cost_excluded':exit_index is None,'actionable':False}


def report():
    fixtures=[
      ('temporary dip then recovery',['100','91','107','112'],None),
      ('deterioration with delayed manual response',['100','98','90','80','85'],2),
      ('gap below both stop and limit',['100','70','65','75'],1),
      ('gradual appreciation',['100','105','113','115'],None)]
    scenarios=[]
    for name,prices,event in fixtures:
        scenarios.append({'name':name,'fictional_quotes':prices,'declared_deterioration_at':event,
          'outcomes':[illustrate(prices,policy=p,deterioration_at=event) for p in ('stop-market','stop-limit','thesis','time')]})
    with localcontext() as context:
        context.prec=50
        fee=Decimal('0.0015')
        flat_factor=(1-fee)/(1+fee)
        cost_examples={str(n):str(Decimal(300)*(flat_factor**n)) for n in (1,5,20)}
    return {'kind':'synthetic workflow and order-risk illustration; not backtest or expected returns',
      'generated_paths':True,'stops':'95 trigger / 90 sell limit are test values, not adopted policy',
      'response_delay':'one observation interval; interval deliberately unspecified',
      'fee_assumption':'0.15% each side; only FX-style illustrative cost, no taxes/spread beyond supplied quotes',
      'important_limits':['No fill guarantee, liquidity queue, partial fill or exact broker trigger simulation',
         'No dividends, FX path or corporate actions; prices are fictional GBP equivalents',
         'Open marks exclude future liquidation costs; closed/open outcomes must be distinguished',
         'These contrasting paths cannot rank strategies or prove profitability'],
      'scenarios':scenarios,'flat_price_cash_after_repeated_round_trips_gbp':cost_examples}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path)
    args=parser.parse_args(); result=report()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    else: print(json.dumps(result,indent=2))
