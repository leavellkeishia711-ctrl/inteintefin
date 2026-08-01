import re
from decimal import Decimal, InvalidOperation

_CURRENCY = re.compile(r"[$€₽£\s\u00a0']")

def parse_amount(raw: str) -> Decimal:
    """
    Держит: '1234.56'  '1 234,56'  '1,234.56'  '$1,234.56'
            '(500)' → -500   '−500' (юникод-минус)   '1 234,56 ₽'
    """
    if raw is None or str(raw).strip() == "":
        raise ValueError("пустая сумма")
    s = str(raw).strip().replace("\u2212", "-").replace("\u00a0", "")
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = _CURRENCY.sub("", s)

    # разделитель: последний из . и , считаем десятичным
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot > last_comma:
        s = s.replace(",", "")
    elif last_comma > last_dot:
        s = s.replace(".", "").replace(",", ".")
    # если ни одного — целое число, ничего не делаем

    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"не число: {raw!r}")
    return -value if negative else value
