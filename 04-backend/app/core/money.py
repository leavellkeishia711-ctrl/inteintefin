from decimal import Decimal, ROUND_HALF_UP, getcontext

getcontext().prec = 28
CENTS = Decimal("0.0001")

def q(value: Decimal | int | str) -> Decimal:
    """Единая политика квантования денег: 4 знака, банковское округление вверх."""
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception:
            raise TypeError(f"Money must be Decimal-convertible, got {type(value)}")
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)

def to_base(amount: Decimal, fx_rate: Decimal | None) -> Decimal:
    if fx_rate is None:
        # If no FX rate is passed, it implies amount is already in base currency.
        return q(amount)
    return q(amount * fx_rate)
