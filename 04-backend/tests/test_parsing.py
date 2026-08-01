import pytest
from decimal import Decimal
from app.services.parsing import parse_amount

def test_parse_amount():
    cases = [
        ("1234.56", Decimal("1234.56")),
        ("1 234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("$1,234.56", Decimal("1234.56")),
        ("(500)", Decimal("-500")),
        ("−500", Decimal("-500")),
        ("-500", Decimal("-500")),
        ("1 234,56 ₽", Decimal("1234.56")),
        ("0.01", Decimal("0.01")),
        ("1000", Decimal("1000")),
        ("1.000.000,00", Decimal("1000000.00")),
        ("1,000,000.00", Decimal("1000000.00")),
        ("€ 50,25", Decimal("50.25")),
    ]
    
    for raw, expected in cases:
        assert parse_amount(raw) == expected

def test_parse_amount_errors():
    with pytest.raises(ValueError):
        parse_amount("")
    with pytest.raises(ValueError):
        parse_amount(None)
    with pytest.raises(ValueError):
        parse_amount("abc")
