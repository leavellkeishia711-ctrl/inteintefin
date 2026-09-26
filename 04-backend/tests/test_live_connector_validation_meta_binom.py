import pytest
import httpx
from app.connectors.meta_ads import MetaAdsConnector
from app.connectors.binom import BinomConnector
from scripts.validate_live_connectors import HarnessError, map_meta_error, map_binom_error

class DummyConfig:
    connector_name = "dummy"
    company_id = 1
    settings = {}







def test_meta_live_validation_rejects_negative_metrics():

    conf = DummyConfig()

    conf.settings = {"currency": "USD"}

    conn = MetaAdsConnector(conf, "tok")

    # -1 spend

    res = conn.normalize([{"campaign_id": "1", "date_start": "2026-09-01", "spend": "-1.0", "_currency": "USD"}])

    assert len(res) == 0



def test_meta_connector_no_usd_fallback():

    conf = DummyConfig()

    conf.settings = {}

    conn = MetaAdsConnector(conf, "tok")

    # missing _currency

    res = conn.normalize([{"campaign_id": "1", "date_start": "2026-09-01", "spend": "1"}])

    assert len(res) == 0



def test_meta_connector_missing_required_metric_is_error():

    conf = DummyConfig()

    conn = MetaAdsConnector(conf, "tok")

    # missing spend

    res = conn.normalize([{"campaign_id": "1", "date_start": "2026-09-01", "_currency": "USD", "clicks": "1", "impressions": "1"}])

    assert len(res) == 0

    # missing clicks

    res = conn.normalize([{"campaign_id": "1", "date_start": "2026-09-01", "_currency": "USD", "spend": "1", "impressions": "1"}])

    assert len(res) == 0



def test_meta_error_code_mapping():

    req = httpx.Request("POST", "http://test")

    def get_err(code):

        resp = httpx.Response(400, json={"error": {"code": code}}, request=req)

        return httpx.HTTPStatusError("err", request=req, response=resp)

        

    assert map_meta_error(get_err(190)).category == "invalid_credentials"

    assert map_meta_error(get_err(200)).category == "insufficient_permission"

    assert map_meta_error(get_err(4)).category == "rate_limit"

    assert map_meta_error(get_err(100)).category == "malformed_request"

    assert map_meta_error(get_err(2635)).category == "unsupported_api_version"



def test_binom_base_url_normalization_strips_index():

    conf = DummyConfig()

    conf.settings = {"base_url": "http://b.com/index.php", "currency": "USD"}

    conn = BinomConnector(conf, "key")

    assert conn.base_url == "http://b.com"





def test_binom_no_mock_url_fallback():

    conf = DummyConfig()

    conf.settings = {"currency": "USD"}

    with pytest.raises(ValueError, match="must be provided"):

        BinomConnector(conf, "key")



def test_binom_no_usd_fallback():

    conf = DummyConfig()

    conf.settings = {"base_url": "http://b.com"}

    with pytest.raises(ValueError, match="BINOM_CURRENCY is missing"):

        BinomConnector(conf, "key")







