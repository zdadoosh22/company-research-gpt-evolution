"""Pure mechanical economics for supplied experimental inputs.

These functions derive affordability and cost break-even, not optimal allocation,
research approval, price forecasts or trading signals. Rates are explicitly
supplied additive charges on GBP gross value. If FX already includes a fee,
do not also enter that fee as a separate rate. No broker-specific rate, tax,
spread, tick, quantity step, FX movement or probability is assumed.
"""
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN
from fractions import Fraction


def _number(value, positive=False):
    if isinstance(value, (float, bool)):
        raise ValueError('Use exact decimal strings; floats and booleans rejected')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('Invalid decimal') from None
    if not result.is_finite() or result < 0 or positive and result == 0:
        raise ValueError('Finite nonnegative input required (positive where specified)')
    if result.adjusted() >= 18 or result.as_tuple().exponent < -18:
        raise ValueError('Input representation supports 18 integer and 18 fractional digits')
    return result


def _terms(*, currency, unit, gbp_per_major_unit, fx_direction,
           fee_rate, tax_rate, fixed_fees_gbp):
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
        raise ValueError('Explicit uppercase three-letter quote currency required')
    if fx_direction != 'GBP_per_major_unit':
        raise ValueError('FX must be explicitly GBP per major currency unit')
    fx = _number(gbp_per_major_unit, True)
    if currency == 'GBX':
        if unit != 'pence' or fx != 1:
            raise ValueError('GBX pence uses GBP-per-GBP factor one and division by 100')
        unit_factor = Fraction(1, 100)
    else:
        if unit != 'major' or currency == 'GBP' and fx != 1:
            raise ValueError('Major unit required; GBP must have conversion factor one')
        unit_factor = Fraction(1)
    return {'factor': Fraction(fx) * unit_factor,
            'fee': Fraction(_number(fee_rate)),
            'tax': Fraction(_number(tax_rate)),
            'fixed': Fraction(_number(fixed_fees_gbp)),
            'currency': currency, 'unit': unit,
            'gbp_per_major_unit': str(fx)}


def _decimal(value):
    # Fixed local precision makes results independent of caller's Decimal context.
    # Discrete floor/ceiling comparisons are performed as exact rationals first.
    with localcontext() as context:
        context.prec = 200
        context.rounding = ROUND_HALF_EVEN
        context.Emax = 999999
        context.Emin = -999999
        return Decimal(value.numerator) / Decimal(value.denominator)


def _s(value):
    return str(_decimal(value))


def _round_step(value, step, up=False):
    ratio = value / step
    steps = -(-ratio.numerator // ratio.denominator) if up else ratio.numerator // ratio.denominator
    return steps * step


def _cost(quantity, price, terms, side):
    gross = quantity * price * terms['factor']
    fees, taxes = gross * terms['fee'], gross * terms['tax']
    charged = fees + taxes + terms['fixed']
    total = gross + charged if side == 'buy' else gross - charged
    return {'side': side, 'quantity': _s(quantity), 'native_price': _s(price),
            'currency': terms['currency'], 'unit': terms['unit'],
            'gbp_per_major_unit': terms['gbp_per_major_unit'],
            'gross_gbp': _s(gross), 'proportional_fees_gbp': _s(fees),
            'taxes_gbp': _s(taxes), 'fixed_fees_gbp': _s(terms['fixed']),
            'total_costs_gbp': _s(charged),
            'total_gbp': _s(total), 'actionable': False,
            'basis': 'Mechanical supplied costs/FX; no broker computation or optimal allocation claim'}


def buy_total(quantity, native_price, **terms):
    return _cost(Fraction(_number(quantity, True)), Fraction(_number(native_price, True)), _terms(**terms), 'buy')


def sell_proceeds(quantity, native_price, **terms):
    """Net GBP proceeds can be negative if supplied charges exceed gross sale."""
    return _cost(Fraction(_number(quantity, True)), Fraction(_number(native_price, True)), _terms(**terms), 'sell')


def derive_entry(budget_gbp, native_limit, quantity_step, **buy_terms):
    """Largest supplied quantity-step multiple within all-in GBP budget."""
    budget = Fraction(_number(budget_gbp))
    price, step = Fraction(_number(native_limit, True)), Fraction(_number(quantity_step, True))
    terms = _terms(**buy_terms)
    remaining = budget - terms['fixed']
    quantity = Fraction(0) if remaining <= 0 else _round_step(
        remaining / (price * terms['factor'] * (1 + terms['fee'] + terms['tax'])), step)
    # Supported broker-style input precision must also represent the output.
    _number(_decimal(quantity))
    spent = quantity * price * terms['factor'] * (1 + terms['fee'] + terms['tax']) + terms['fixed'] if quantity else Fraction(0)
    if spent > budget:
        raise ArithmeticError('Exact affordability invariant violated')
    return {'quantity': _s(quantity), 'quantity_step': _s(step), 'native_limit': _s(price),
            'budget_gbp': _s(budget), 'total_gbp': _s(spent), 'unspent_gbp': _s(budget - spent),
            'feasible': bool(quantity), 'actionable': False,
            'basis': 'Maximum mechanical affordable quantity; not a recommended allocation'}


def price_ceiling(budget_gbp, quantity, price_step, **buy_terms):
    """Highest supplied native price-tick multiple within all-in GBP budget."""
    budget, qty, tick = Fraction(_number(budget_gbp)), Fraction(_number(quantity, True)), Fraction(_number(price_step, True))
    terms = _terms(**buy_terms)
    remaining = budget - terms['fixed']
    ceiling = Fraction(0) if remaining <= 0 else _round_step(remaining / (qty * terms['factor'] * (1 + terms['fee'] + terms['tax'])), tick)
    _number(_decimal(ceiling))
    spent = qty * ceiling * terms['factor'] * (1 + terms['fee'] + terms['tax']) + terms['fixed'] if ceiling else Fraction(0)
    return {'quantity': _s(qty), 'native_price_ceiling': _s(ceiling), 'price_step': _s(tick),
            'total_gbp': _s(spent), 'budget_gbp': _s(budget), 'feasible': bool(ceiling),
            'actionable': False, 'basis': 'Affordability ceiling only; not an intrinsic-value or research entry threshold'}


def round_trip_break_even(quantity, entry_native_price, exit_price_step, entry_terms, exit_terms):
    """Minimum native sell tick recovering the supplied entry debit and exit costs."""
    qty, entry, tick = Fraction(_number(quantity, True)), Fraction(_number(entry_native_price, True)), Fraction(_number(exit_price_step, True))
    buy, sell = _terms(**entry_terms), _terms(**exit_terms)
    if buy['currency'] != sell['currency'] or buy['unit'] != sell['unit']:
        raise ValueError('Round trip must use the same native price currency/unit')
    debit = qty * entry * buy['factor'] * (1 + buy['fee'] + buy['tax']) + buy['fixed']
    multiplier = 1 - sell['fee'] - sell['tax']
    if multiplier <= 0:
        return {'feasible': False, 'entry_debit_gbp': _s(debit), 'exit_native_price': None,
                'reason': 'Supplied proportional exit charges leave no positive proceeds multiplier', 'actionable': False}
    exact = (debit + sell['fixed']) / (qty * sell['factor'] * multiplier)
    price = _round_step(exact, tick, True)
    _number(_decimal(price), True)
    proceeds = qty * price * sell['factor'] * multiplier - sell['fixed']
    return {'feasible': True, 'quantity': _s(qty), 'entry_debit_gbp': _s(debit),
            'exit_native_price': _s(price), 'exit_price_step': _s(tick),
            'exit_net_gbp': _s(proceeds), 'surplus_gbp': _s(proceeds - debit),
            'actionable': False, 'basis': 'Mechanical round-trip cost recovery; not a price forecast or sell rule'}


def scenario_analysis(quantity, scenarios):
    """Independent supplied price/FX/cost cases; no probabilities or aggregation."""
    qty = Fraction(_number(quantity, True))
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('Supply at least one explicit scenario')
    names, results = set(), []
    for scenario in scenarios:
        name = scenario['name']
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('Scenario names must be nonempty and unique')
        names.add(name)
        entry, exit = Fraction(_number(scenario['entry_native_price'], True)), Fraction(_number(scenario['exit_native_price'], True))
        buy, sell = _terms(**scenario['entry_terms']), _terms(**scenario['exit_terms'])
        if buy['currency'] != sell['currency'] or buy['unit'] != sell['unit']:
            raise ValueError('Round trip must use the same native price currency/unit')
        debit = qty * entry * buy['factor'] * (1 + buy['fee'] + buy['tax']) + buy['fixed']
        credit = qty * exit * sell['factor'] * (1 - sell['fee'] - sell['tax']) - sell['fixed']
        results.append({'name': name, 'entry_debit_gbp': _s(debit), 'exit_net_gbp': _s(credit),
                        'gain_loss_gbp': _s(credit - debit), 'actionable': False,
                        'inputs': scenario, 'basis': 'Supplied hypothetical price/FX/cost case; not an execution guarantee'})
    return {'quantity': _s(qty), 'scenarios': results, 'probabilities': None,
            'actionable': False, 'basis': 'Unweighted experimental cases; no optimal allocation or expected-return claim'}
