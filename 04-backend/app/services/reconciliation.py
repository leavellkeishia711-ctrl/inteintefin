from dataclasses import dataclass
from typing import Sequence, Dict, Any, List
from decimal import Decimal
import uuid
from datetime import date

# Use standard project model for input/output typing if possible,
# or define a clean struct for pure logic.
from app.db.models.campaigns import CampaignRunStat

@dataclass
class ReconciliationThresholds:
    spend_revenue_diff: Decimal = Decimal("0.0001")
    clicks_diff: int = 0
    impressions_diff: int = 0
    conversions_diff: Decimal = Decimal("0.0001")

@dataclass
class ReconciliationDecision:
    status: str
    chosen_source: str | None
    chosen_stat_id: uuid.UUID | None
    canonical_spend: Decimal | None
    canonical_revenue: Decimal | None
    canonical_clicks: int | None
    canonical_impressions: int | None
    canonical_conversions: Decimal | None
    canonical_currency: str | None
    observed_source_count: int
    conflict_fields: dict
    source_snapshot: dict
    decision_reason: str


DEFAULT_SOURCE_PRIORITY = [
    "voluum",
    "binom",
    "keitaro",
    "affise",
    "meta",
    "google_ads",
    "tiktok_ads"
]


def reconcile_stat_group(
    stats: Sequence[CampaignRunStat],
    source_priority: Sequence[str] = DEFAULT_SOURCE_PRIORITY,
    thresholds: ReconciliationThresholds | None = None
) -> ReconciliationDecision:
    """
    Pure function to determine the canonical state for a given group of stats.
    Preconditions:
      - All stats must belong to the same (company_id, campaign_run_id, stat_date).
      - All stats must be active (deleted_at IS NULL).
    """
    if thresholds is None:
        thresholds = ReconciliationThresholds()

    if not stats:
        return ReconciliationDecision(
            status="no_data",
            chosen_source=None,
            chosen_stat_id=None,
            canonical_spend=None,
            canonical_revenue=None,
            canonical_clicks=None,
            canonical_impressions=None,
            canonical_conversions=None,
            canonical_currency=None,
            observed_source_count=0,
            conflict_fields={},
            source_snapshot={},
            decision_reason="No valid sources available."
        )

    # Validate isolation manually just in case
    company_id = stats[0].company_id
    campaign_run_id = stats[0].campaign_run_id
    stat_date = stats[0].stat_date
    for s in stats:
        if s.company_id != company_id or s.campaign_run_id != campaign_run_id or s.stat_date != stat_date:
            raise ValueError("All stats must belong to the same reconciliation group (company_id, campaign_run_id, stat_date)")

    # Filter out anything deleted or unexpected (defense in depth)
    active_stats = [s for s in stats if s.deleted_at is None]
    if not active_stats:
        return ReconciliationDecision(
            status="no_data",
            chosen_source=None,
            chosen_stat_id=None,
            canonical_spend=None,
            canonical_revenue=None,
            canonical_clicks=None,
            canonical_impressions=None,
            canonical_conversions=None,
            canonical_currency=None,
            observed_source_count=0,
            conflict_fields={},
            source_snapshot={},
            decision_reason="No active sources available."
        )

    source_snapshot = {}
    for s in active_stats:
        # Save snapshot without sensitive tokens
        source_snapshot[s.source] = {
            "stat_id": str(s.id),
            "external_id": s.external_id,
            "spend": str(s.spend),
            "revenue": str(s.revenue),
            "currency": s.currency,
            "clicks": s.clicks,
            "impressions": s.impressions,
            "conversions": str(s.conversions),
            "fx_rate_to_base": str(s.fx_rate_to_base)
        }

    # Deterministic selection based on priority
    # Sort active_stats by their index in source_priority, fallback to end of list for unknown sources
    def sort_key(stat):
        try:
            return source_priority.index(stat.source)
        except ValueError:
            return len(source_priority)
            
    sorted_stats = sorted(active_stats, key=sort_key)
    chosen = sorted_stats[0]

    if len(active_stats) == 1:
        return ReconciliationDecision(
            status="partial",
            chosen_source=chosen.source,
            chosen_stat_id=chosen.id,
            canonical_spend=chosen.spend,
            canonical_revenue=chosen.revenue,
            canonical_clicks=chosen.clicks,
            canonical_impressions=chosen.impressions,
            canonical_conversions=chosen.conversions,
            canonical_currency=chosen.currency,
            observed_source_count=1,
            conflict_fields={},
            source_snapshot=source_snapshot,
            decision_reason="Single source available."
        )

    # Check for conflicts against the chosen source
    conflict_fields = {}
    for s in sorted_stats[1:]:
        if abs(chosen.spend - s.spend) > thresholds.spend_revenue_diff:
            conflict_fields.setdefault("spend", []).append(s.source)
        if abs(chosen.revenue - s.revenue) > thresholds.spend_revenue_diff:
            conflict_fields.setdefault("revenue", []).append(s.source)
        if abs(chosen.clicks - s.clicks) > thresholds.clicks_diff:
            conflict_fields.setdefault("clicks", []).append(s.source)
        if abs(chosen.impressions - s.impressions) > thresholds.impressions_diff:
            conflict_fields.setdefault("impressions", []).append(s.source)
        if abs(chosen.conversions - s.conversions) > thresholds.conversions_diff:
            conflict_fields.setdefault("conversions", []).append(s.source)
        if chosen.currency != s.currency:
            conflict_fields.setdefault("currency", []).append(s.source)

    if conflict_fields:
        status = "conflict"
        decision_reason = f"Conflict detected in fields: {', '.join(conflict_fields.keys())}. Selected canonical based on priority."
    else:
        status = "reconciled"
        decision_reason = "Multiple sources agree within thresholds."

    return ReconciliationDecision(
        status=status,
        chosen_source=chosen.source,
        chosen_stat_id=chosen.id,
        canonical_spend=chosen.spend,
        canonical_revenue=chosen.revenue,
        canonical_clicks=chosen.clicks,
        canonical_impressions=chosen.impressions,
        canonical_conversions=chosen.conversions,
        canonical_currency=chosen.currency,
        observed_source_count=len(active_stats),
        conflict_fields=conflict_fields,
        source_snapshot=source_snapshot,
        decision_reason=decision_reason
    )
