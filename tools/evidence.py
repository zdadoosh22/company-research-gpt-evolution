"""Evidence arithmetic with explicit comparability; no speculative reconciliations."""
from finance import number

def normalize_amount(raw, scale, *, currency, sign=1):
    if not currency or scale not in {1,1000,1000000,1000000000} or sign not in {-1,1}:
        raise ValueError('Explicit currency, conventional scale and sign required')
    return number(raw,'raw source amount')*scale*sign

def compare_observations(left,right, *, tolerance=0):
    keys=('metric','period','scope','currency','unit')
    differences=[k for k in keys if not left.get(k) or left.get(k)!=right.get(k)]
    if differences:return dict(status='incomparable',different_fields=differences,selected_value=None)
    a,b=number(left.get('value'),'left source value'),number(right.get('value'),'right source value')
    if abs(a-b)>number(tolerance,'tolerance'):
        return dict(status='conflict',left=a,right=b,selected_value=None,required='Read underlying sources and document a verified reconciliation or withhold the affected conclusion.')
    return dict(status='agreement',selected_value=a)

def available_filings(records,as_of):
    # Discover amendments without silently deciding which facts changed.
    result=[r for r in records if r.get('filed') and r['filed']<=as_of]
    return sorted(result,key=lambda r:(r['filed'],r.get('accession','')))
