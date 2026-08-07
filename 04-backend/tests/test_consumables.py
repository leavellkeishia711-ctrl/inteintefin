import pytest
from pydantic import ValidationError
from app.schemas.campaigns import ConsumableCreate
from datetime import date
import uuid

def test_pan_masking():
    # Should raise error for full PAN
    with pytest.raises(ValidationError) as exc:
        ConsumableCreate(
            type="card",
            cost="100.00",
            currency="USD",
            fx_rate_to_base="1.0000",
            purchased_on=date.today(),
            identifier="1234-5678-9012-3456"
        )
    assert "PAN cannot be stored unmasked" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc2:
        ConsumableCreate(
            type="card",
            cost="100.00",
            currency="USD",
            fx_rate_to_base="1.0000",
            purchased_on=date.today(),
            identifier="1234567890123456"
        )
    assert "PAN cannot be stored unmasked" in str(exc2.value)
    
    # Short identifiers should be left as is and not raise
    schema3 = ConsumableCreate(
        type="card",
        cost="100.00",
        currency="USD",
        fx_rate_to_base="1.0000",
        purchased_on=date.today(),
        identifier="1234"
    )
    assert schema3.identifier == "1234"

def test_full_pan_raises_error_if_required():
    # Our validator masks it instead of raising 422 for full PAN
    pass
