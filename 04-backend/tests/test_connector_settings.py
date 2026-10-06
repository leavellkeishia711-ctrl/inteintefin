import pytest
from app.api.v1.connectors import validate_connector_settings
from fastapi import HTTPException

def test_meta_settings_valid():
    settings = validate_connector_settings("meta", {"lookback_days": 14})
    assert settings == {"lookback_days": 14}

def test_meta_settings_invalid_type():
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("meta", {"lookback_days": "14"}) # String instead of int
    assert exc.value.status_code == 422
    
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("meta", {"lookback_days": True}) # Boolean instead of strict int
    assert exc.value.status_code == 422

def test_meta_settings_invalid_range():
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("meta", {"lookback_days": 100}) # > 90
    assert exc.value.status_code == 422

def test_meta_settings_base_url_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("meta", {"base_url": "https://evil.com"})
    assert exc.value.status_code == 422

def test_google_ads_settings_valid():
    settings = validate_connector_settings("google_ads", {"access_mode": "legacy"})
    assert settings == {"access_mode": "legacy"}

def test_google_ads_settings_invalid():
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("google_ads", {"access_mode": "unauthorized"})
    assert exc.value.status_code == 422

def test_tiktok_ads_settings():
    assert validate_connector_settings("tiktok_ads", {}) == {}
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("tiktok_ads", {"any_key": "val"})
    assert exc.value.status_code == 422

def test_unsupported_connector():
    with pytest.raises(HTTPException) as exc:
        validate_connector_settings("unknown", {"k": "v"})
    assert exc.value.status_code == 422
