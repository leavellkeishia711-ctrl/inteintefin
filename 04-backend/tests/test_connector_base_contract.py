import pytest
from app.connectors.base import Connector

def test_connector_base_contract():
    assert hasattr(Connector, "test_connection")
    assert hasattr(Connector, "fetch_ad_accounts")
    assert hasattr(Connector, "normalize_ad_accounts")
    assert hasattr(Connector, "upsert_ad_accounts")
    assert hasattr(Connector, "fetch_campaigns")
    assert hasattr(Connector, "fetch_metrics")
    assert hasattr(Connector, "normalize")
    assert hasattr(Connector, "upsert")
