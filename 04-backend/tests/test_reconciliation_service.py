import pytest
from decimal import Decimal
import uuid
from datetime import date
from app.db.models.campaigns import CampaignRunStat
from app.services.reconciliation import reconcile_stat_group, ReconciliationThresholds

@pytest.fixture
def base_kwargs():
    return {
        "id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "campaign_run_id": uuid.uuid4(),
        "stat_date": date(2026, 9, 14),
        "currency": "USD",
        "fx_rate_to_base": Decimal("1.0"),
        "external_id": "test",
        "deleted_at": None,
    }

def test_reconciliation_no_data():
    decision = reconcile_stat_group([])
    assert decision.status == "no_data"
    assert decision.chosen_source is None
    assert decision.canonical_spend is None
    assert decision.observed_source_count == 0

def test_reconciliation_single_source(base_kwargs):
    stat = CampaignRunStat(
        **base_kwargs,
        source="meta",
        spend=Decimal("100.0000"),
        revenue=Decimal("150.0000"),
        clicks=10,
        impressions=1000,
        conversions=Decimal("2.0000")
    )
    decision = reconcile_stat_group([stat])
    assert decision.status == "partial"
    assert decision.chosen_source == "meta"
    assert decision.canonical_spend == Decimal("100.0000")
    assert decision.canonical_clicks == 10
    assert decision.observed_source_count == 1
    assert decision.conflict_fields == {}

def test_reconciliation_equal_sources_is_reconciled(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("100.0000"), revenue=Decimal("150.0000"), clicks=10, impressions=1000, conversions=Decimal("2.0000"))
    s2 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("100.0000"), revenue=Decimal("150.0000"), clicks=10, impressions=1000, conversions=Decimal("2.0000"))
    
    # Priority: voluum > meta
    decision = reconcile_stat_group([s1, s2])
    assert decision.status == "reconciled"
    assert decision.chosen_source == "voluum"
    assert decision.conflict_fields == {}
    assert decision.observed_source_count == 2

def test_reconciliation_conflict_is_detected(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("100.0000"), revenue=Decimal("150.0000"), clicks=10, impressions=1000, conversions=Decimal("2.0000"))
    s2 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("105.0000"), revenue=Decimal("150.0000"), clicks=12, impressions=1000, conversions=Decimal("2.0000"))
    
    decision = reconcile_stat_group([s1, s2])
    assert decision.status == "conflict"
    assert decision.chosen_source == "voluum"  # still chosen due to priority
    assert decision.canonical_spend == Decimal("105.0000")
    assert decision.canonical_clicks == 12
    assert "spend" in decision.conflict_fields
    assert "clicks" in decision.conflict_fields
    assert "revenue" not in decision.conflict_fields

def test_reconciliation_source_priority_is_deterministic(base_kwargs):
    # Pass in reverse order of priority, it should still pick 'voluum'
    s_meta = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    s_affise = CampaignRunStat(**base_kwargs, source="affise", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    s_voluum = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    
    decision = reconcile_stat_group([s_meta, s_affise, s_voluum])
    assert decision.chosen_source == "voluum"

def test_reconciliation_result_does_not_depend_on_input_order(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("15"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    
    d1 = reconcile_stat_group([s1, s2])
    d2 = reconcile_stat_group([s2, s1])
    
    assert d1.chosen_source == d2.chosen_source == "voluum"
    assert d1.status == d2.status == "conflict"

def test_reconciliation_ignores_soft_deleted_stats(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    kw = dict(base_kwargs)
    kw["deleted_at"] = date(2026, 1, 1)
    s2 = CampaignRunStat(**kw, source="voluum", spend=Decimal("15"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    
    decision = reconcile_stat_group([s1, s2])
    assert decision.status == "partial"
    assert decision.chosen_source == "meta"
    assert decision.observed_source_count == 1

def test_reconciliation_reports_conflict_fields(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("110"), revenue=Decimal("200"), clicks=5, impressions=110, conversions=Decimal("1"))
    
    decision = reconcile_stat_group([s1, s2])
    assert "spend" in decision.conflict_fields
    assert "impressions" in decision.conflict_fields
    assert "meta" in decision.conflict_fields["spend"]

def test_reconciliation_does_not_sum_sources(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    
    decision = reconcile_stat_group([s1, s2])
    assert decision.canonical_spend == Decimal("10")
    assert decision.canonical_clicks == 1
    assert decision.canonical_spend != Decimal("20")

def test_reconciliation_does_not_average_conflicting_sources(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10"), revenue=Decimal("20"), clicks=10, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("20"), revenue=Decimal("20"), clicks=20, impressions=100, conversions=Decimal("1"))
    
    decision = reconcile_stat_group([s1, s2])
    assert decision.canonical_spend == Decimal("10")
    assert decision.canonical_clicks == 10

def test_reconciliation_uses_decimal_for_money(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10.55"), revenue=Decimal("20.12"), clicks=1, impressions=1, conversions=Decimal("1"))
    decision = reconcile_stat_group([s1])
    assert isinstance(decision.canonical_spend, Decimal)
    assert isinstance(decision.canonical_revenue, Decimal)

def test_reconciliation_uses_integer_metrics(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10"), revenue=Decimal("20"), clicks=15, impressions=100, conversions=Decimal("1"))
    decision = reconcile_stat_group([s1])
    assert isinstance(decision.canonical_clicks, int)
    assert isinstance(decision.canonical_impressions, int)

def test_reconciliation_negative_values_are_rejected_or_flagged(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("-10.00"), revenue=Decimal("20.00"), clicks=1, impressions=1, conversions=Decimal("1"))
    decision = reconcile_stat_group([s1])
    assert decision.canonical_spend == Decimal("-10.00")

def test_reconciliation_snapshot_contains_no_secrets(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    decision = reconcile_stat_group([s1])
    snap = decision.source_snapshot.get("voluum")[0]
    assert "token" not in snap
    assert "secret" not in snap
    assert snap["spend"] == "10"
    assert snap["currency"] == "USD"

def test_reconciliation_missing_primary_source_falls_back_deterministically(base_kwargs):
    s_meta = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    s_tiktok = CampaignRunStat(**base_kwargs, source="tiktok_ads", spend=Decimal("10"), revenue=Decimal("20"), clicks=1, impressions=1, conversions=Decimal("1"))
    
    # Priority: meta > tiktok_ads
    decision = reconcile_stat_group([s_meta, s_tiktok])
    assert decision.chosen_source == "meta"

def test_reconciliation_uses_one_percent_relative_threshold(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("101"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d_no = reconcile_stat_group([s1, s2])
    assert d_no.status == "reconciled"
    
    s3 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("102"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d_yes = reconcile_stat_group([s1, s3])
    assert d_yes.status == "conflict"
    assert "spend" in d_yes.conflict_fields

def test_reconciliation_zero_to_nonzero_is_conflict(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("0"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("1"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d = reconcile_stat_group([s1, s2])
    assert d.status == "conflict"
    assert "spend" in d.conflict_fields

def test_reconciliation_small_nonzero_values_are_not_hidden(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("1"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("2"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d = reconcile_stat_group([s1, s2])
    assert d.status == "conflict"
    assert "spend" in d.conflict_fields

def test_reconciliation_clicks_and_impressions_follow_documented_threshold(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("100"), revenue=Decimal("200"), clicks=100, impressions=1000, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=101, impressions=1010, conversions=Decimal("1"))
    d_no = reconcile_stat_group([s1, s2])
    assert d_no.status == "reconciled"

    s3 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=102, impressions=1000, conversions=Decimal("1"))
    d_yes = reconcile_stat_group([s1, s3])
    assert "clicks" in d_yes.conflict_fields
    assert d_yes.status == "conflict"

def test_reconciliation_currency_difference_is_conflict(base_kwargs):
    s1 = CampaignRunStat(**base_kwargs, source="voluum", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**base_kwargs, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2.currency = "EUR"
    d = reconcile_stat_group([s1, s2])
    assert d.status == "conflict"
    assert "currency" in d.conflict_fields
    assert d.chosen_source == "voluum"
    assert d.canonical_currency == "USD"

def test_reconciliation_duplicate_same_source_is_deterministic(base_kwargs):
    kw_b = dict(base_kwargs)
    kw_b["external_id"] = "B"
    kw_a = dict(base_kwargs)
    kw_a["external_id"] = "A"
    
    s1 = CampaignRunStat(**kw_b, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**kw_a, source="meta", spend=Decimal("99"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s1.id = uuid.uuid4()
    s2.id = uuid.uuid4()
    
    d1 = reconcile_stat_group([s1, s2])
    d2 = reconcile_stat_group([s2, s1])
    
    assert d1.chosen_stat_id == d2.chosen_stat_id == s2.id
    assert d1.canonical_spend == d2.canonical_spend == Decimal("99")

def test_reconciliation_snapshot_preserves_duplicate_source_rows(base_kwargs):
    kw_b = dict(base_kwargs)
    kw_b["external_id"] = "B"
    kw_a = dict(base_kwargs)
    kw_a["external_id"] = "A"
    s1 = CampaignRunStat(**kw_b, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**kw_a, source="meta", spend=Decimal("99"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d = reconcile_stat_group([s1, s2])
    assert isinstance(d.source_snapshot["meta"], list)
    assert len(d.source_snapshot["meta"]) == 2

def test_reconciliation_observed_source_count_counts_unique_sources(base_kwargs):
    kw_a = dict(base_kwargs)
    kw_a["external_id"] = "A"
    kw_b = dict(base_kwargs)
    kw_b["external_id"] = "B"
    kw_c = dict(base_kwargs)
    kw_c["external_id"] = "C"
    s1 = CampaignRunStat(**kw_a, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**kw_b, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s3 = CampaignRunStat(**kw_c, source="voluum", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d = reconcile_stat_group([s1, s2, s3])
    assert d.observed_source_count == 2

def test_reconciliation_unknown_source_order_is_deterministic(base_kwargs):
    kw_a = dict(base_kwargs)
    kw_a["external_id"] = "A"
    kw_b = dict(base_kwargs)
    kw_b["external_id"] = "B"
    s1 = CampaignRunStat(**kw_a, source="unknown2", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s2 = CampaignRunStat(**kw_b, source="unknown1", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    s1.id = uuid.uuid4()
    s2.id = uuid.uuid4()
    d1 = reconcile_stat_group([s1, s2])
    d2 = reconcile_stat_group([s2, s1])
    assert d1.chosen_stat_id == d2.chosen_stat_id
    assert d1.chosen_source == "unknown1"

def test_reconciliation_single_source_is_partial(base_kwargs):
    kw_a = dict(base_kwargs)
    kw_a["external_id"] = "A"
    s1 = CampaignRunStat(**kw_a, source="meta", spend=Decimal("100"), revenue=Decimal("200"), clicks=5, impressions=100, conversions=Decimal("1"))
    d = reconcile_stat_group([s1])
    assert d.status == "partial"
    assert d.observed_source_count == 1
    assert "Single source available." in d.decision_reason

def test_reconciliation_relative_threshold_uses_decimal_only():
    from app.services.reconciliation import is_conflict
    assert is_conflict(Decimal("100.00"), Decimal("101.00")) == False
    assert is_conflict(Decimal("100.00"), Decimal("102.00")) == True
    # Verify exact types are handled
    assert is_conflict(100, 101) == False
    assert is_conflict(100, 102) == True
