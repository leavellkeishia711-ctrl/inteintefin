import pytest
from decimal import Decimal
from app.connectors.base import NormalizedRecord
from pydantic import ValidationError
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.meta_ads import MetaAdsConnector
from app.connectors.tiktok_ads import TikTokAdsConnector
from datetime import date

def test_normalized_record_defaults_new_metrics():
    record = NormalizedRecord(
        source="test",
        external_id="123",
        stat_date=date(2026, 1, 1),
        spend=Decimal("10.0"),
        revenue=Decimal("20.0"),
        currency="USD"
    )
    assert record.clicks == 0
    assert record.impressions == 0
    assert record.conversions == Decimal("0")

def test_normalized_record_rejects_negative_clicks():
    # As Pydantic v2 is configured with ge=0
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        NormalizedRecord(
            source="test",
            external_id="123",
            stat_date=date(2026, 1, 1),
            spend=Decimal("10.0"),
            revenue=Decimal("20.0"),
            currency="USD",
            clicks=-5
        )

def test_normalized_record_rejects_negative_conversions():
    with pytest.raises(ValidationError):
        NormalizedRecord(
            source="test",
            external_id="123",
            stat_date=date.today(),
            spend=Decimal("10"),
            revenue=Decimal("20"),
            currency="USD",
            conversions=Decimal("-1.5")
        )

def test_normalized_record_conversions_are_decimal():
    record = NormalizedRecord(
        source="test",
        external_id="123",
        stat_date=date(2026, 1, 1),
        spend=Decimal("10.0"),
        revenue=Decimal("20.0"),
        currency="USD",
        conversions="15.5"  # Pydantic should convert string to Decimal
    )
    assert isinstance(record.conversions, Decimal)
    assert record.conversions == Decimal("15.5")

class DummyConfig:
    company_id = "test-co"
    connector_name = "test"
    settings = {"currency": "USD"}

def test_google_ads_normalize_metrics():
    connector = GoogleAdsConnector(DummyConfig(), '{"developer_token":"a","client_id":"b","client_secret":"c","refresh_token":"d","login_customer_id":"e","customer_id":"f"}')
    raw = [{
        "campaign": {"id": "123"},
        "segments": {"date": "2026-01-01"},
        "customer": {"currencyCode": "USD"},
        "metrics": {
            "costMicros": "1000000",
            "conversionsValue": "5.5",
            "clicks": "100",
            "impressions": "5000",
            "conversions": "3"
        }
    }]
    res = connector.normalize(raw)
    assert len(res) == 1
    assert res[0].clicks == 100
    assert res[0].impressions == 5000
    assert res[0].conversions == Decimal("3")
    assert res[0].spend == Decimal("1")
    assert res[0].revenue == Decimal("5.5")

def test_meta_normalize_metrics():
    connector = MetaAdsConnector(DummyConfig(), '{"access_token":"a","account_id":"b"}')
    raw = [{
        "campaign_id": "123",
        "date_start": "2026-01-01",
        "spend": "10.5",
        "clicks": "50",
        "impressions": "1000",
        "actions": [
            {"action_type": "purchase", "value": "2"},
            {"action_type": "omni_purchase", "value": "1.5"}
        ],
        "action_values": []
    }]
    res = connector.normalize(raw)
    assert len(res) == 1
    assert res[0].clicks == 50
    assert res[0].impressions == 1000
    assert res[0].conversions == Decimal("3.5")
    assert res[0].spend == Decimal("10.5")

def test_tiktok_normalize_metrics():
    connector = TikTokAdsConnector(DummyConfig(), '{"access_token":"a","advertiser_id":"b"}')
    raw = [{
        "dimensions": {"campaign_id": "123", "stat_time_day": "2026-01-01"},
        "metrics": {
            "spend": "10.5",
            "total_purchase_value": "20",
            "clicks": "200",
            "impressions": "3000",
            "conversion": "5"
        },
        "_currency": "USD"
    }]
    res = connector.normalize(raw)
    assert len(res) == 1
    assert res[0].clicks == 200
    assert res[0].impressions == 3000
    assert res[0].conversions == Decimal("5")

def test_missing_metrics_default_to_zero():
    connector = GoogleAdsConnector(DummyConfig(), '{"developer_token":"a","client_id":"b","client_secret":"c","refresh_token":"d","login_customer_id":"e","customer_id":"f"}')
    raw = [{
        "campaign": {"id": "123"},
        "segments": {"date": "2026-01-01"},
        "customer": {"currencyCode": "USD"},
        "metrics": {
            "costMicros": "1000000"
        }
    }]
    res = connector.normalize(raw)
    assert len(res) == 0

def test_all_connectors_return_metrics():
    from app.connectors.google_ads import GoogleAdsConnector
    from app.connectors.meta_ads import MetaAdsConnector
    from app.connectors.tiktok_ads import TikTokAdsConnector
    from app.connectors.binom import BinomConnector
    from app.connectors.voluum import VoluumConnector
    from app.connectors.affise import AffiseConnector
    from app.connectors.keitaro import KeitaroConnector

    class DummyConfig:
        company_id = "test-co"
        connector_name = "test"
        settings = {"currency": "USD"}

    connectors = [
        (GoogleAdsConnector(DummyConfig(), '{"developer_token":"a","client_id":"b","client_secret":"c","refresh_token":"d","login_customer_id":"e","customer_id":"f"}'), [{"campaign": {"id": "1"}, "segments": {"date": "2026-01-01"}, "customer": {"currencyCode": "USD"}, "metrics": {"clicks": "10", "conversions": "2", "costMicros": "0", "conversionsValue": "0", "impressions": "0"}}]),
        (MetaAdsConnector(DummyConfig(), '{"access_token":"a","account_id":"b"}'), [{"campaign_id": "1", "date_start": "2026-01-01", "spend": "0", "impressions": "0", "clicks": "10", "actions": [{"action_type": "purchase", "value": "2"}]}]),
        (TikTokAdsConnector(DummyConfig(), '{"access_token":"a","advertiser_id":"b"}'), [{"dimensions": {"campaign_id": "1", "stat_time_day": "2026-01-01"}, "_currency": "USD", "metrics": {"clicks": "10", "conversion": "2", "spend": "0", "total_purchase_value": "0", "impressions": "0"}}]),
        (BinomConnector(DummyConfig(), '{"url":"http://a","api_key":"b"}'), [{"camp_id": "1", "date": "2026-01-01", "clicks": "10", "leads": "2"}]),
        (VoluumConnector(DummyConfig(), '{"access_key":"a","access_token":"b"}'), [{"campaignId": "1", "date": "2026-01-01", "clicks": "10", "conversions": "2"}]),
        (AffiseConnector(DummyConfig(), '{"url":"http://a","api_key":"b"}'), [{"offer_id": "1", "date": "2026-01-01", "clicks": "10", "conversions": "2"}]),
        (KeitaroConnector(DummyConfig(), '{"url":"http://a","api_key":"b"}'), [{"campaign_id": "1", "date": "2026-01-01", "clicks": "10", "conversions": "2"}])
    ]

    for conn, payload in connectors:
        res = conn.normalize(payload)
        assert len(res) == 1, f"{conn.__class__.__name__} failed to normalize"
        assert res[0].clicks == 10, f"{conn.__class__.__name__} failed to extract clicks"
        assert res[0].conversions == Decimal("2"), f"{conn.__class__.__name__} failed to extract conversions"
        rec = res[0]
        assert isinstance(rec, NormalizedRecord)
        assert isinstance(rec.clicks, int)
        assert isinstance(rec.impressions, int)
        assert isinstance(rec.conversions, Decimal)
        assert rec.external_id == "1"
        assert rec.stat_date == date(2026, 1, 1)
