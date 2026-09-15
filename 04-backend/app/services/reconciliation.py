from dataclasses import dataclass
from typing import Sequence, Dict, Any, List
from decimal import Decimal
import uuid
from datetime import date

# Use standard project model for input/output typing if possible,
# or define a clean struct for pure logic.
from app.db.models.campaigns import CampaignRunStat

def is_conflict(a: Decimal | int, b: Decimal | int, relative_threshold: Decimal = Decimal("0.01")) -> bool:
    """
    Evaluates if two values conflict based on a relative threshold.
    - If both are 0, no conflict.
    - If one is 0 and the other is not, conflict.
    - Otherwise, abs(a-b)/max(abs(a), abs(b)) > threshold.
    """
    da = Decimal(str(a))
    db = Decimal(str(b))
    if da == Decimal("0") and db == Decimal("0"):
        return False
    if da == Decimal("0") or db == Decimal("0"):
        return True
    
    relative_difference = abs(da - db) / max(abs(da), abs(db))
    return relative_difference > relative_threshold


@dataclass
class ReconciliationThresholds:
    relative_threshold: Decimal = Decimal("0.01")


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

    # Build snapshot with lists to preserve duplicates
    source_snapshot = {}
    for s in active_stats:
        source_snapshot.setdefault(s.source, []).append({
            "stat_id": str(s.id),
            "external_id": s.external_id,
            "spend": str(s.spend),
            "revenue": str(s.revenue),
            "currency": s.currency,
            "clicks": s.clicks,
            "impressions": s.impressions,
            "conversions": str(s.conversions),
            "fx_rate_to_base": str(s.fx_rate_to_base)
        })

    # Sort stats deterministically: priority index, source name, external_id, stat_id
    def sort_key(stat):
        try:
            p_idx = source_priority.index(stat.source)
        except ValueError:
            p_idx = len(source_priority)
        return (p_idx, stat.source, stat.external_id or "", str(stat.id))
            
    sorted_stats = sorted(active_stats, key=sort_key)
    
    # Choose representative per unique source (first one wins due to sort_key)
    unique_sources = {}
    has_duplicates = False
    for stat in sorted_stats:
        if stat.source not in unique_sources:
            unique_sources[stat.source] = stat
        else:
            has_duplicates = True
            
    representatives = list(unique_sources.values())
    chosen = representatives[0]
    observed_source_count = len(unique_sources)

    if observed_source_count == 1:
        reason = "Single source available."
        if has_duplicates:
            reason = "Single source available. Chose deterministic representative among duplicate rows."
        
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
            observed_source_count=observed_source_count,
            conflict_fields={},
            source_snapshot=source_snapshot,
            decision_reason=reason
        )

    # Check for conflicts against the chosen source among the representatives
    conflict_fields = {}
    for s in representatives[1:]:
        # Explicit currency conflict handling
        if chosen.currency != s.currency:
            conflict_fields.setdefault("currency", []).append(s.source)
            # If currencies differ, we can't meaningfully compare raw numeric spend/revenue 
            # without ECB FX in this PR, so we explicitly skip numeric comparison for them 
            # and just flag currency as conflicting.
        else:
            if is_conflict(chosen.spend, s.spend, thresholds.relative_threshold):
                conflict_fields.setdefault("spend", []).append(s.source)
            if is_conflict(chosen.revenue, s.revenue, thresholds.relative_threshold):
                conflict_fields.setdefault("revenue", []).append(s.source)
                
        if is_conflict(chosen.clicks, s.clicks, thresholds.relative_threshold):
            conflict_fields.setdefault("clicks", []).append(s.source)
        if is_conflict(chosen.impressions, s.impressions, thresholds.relative_threshold):
            conflict_fields.setdefault("impressions", []).append(s.source)
        if is_conflict(chosen.conversions, s.conversions, thresholds.relative_threshold):
            conflict_fields.setdefault("conversions", []).append(s.source)

    if conflict_fields:
        status = "conflict"
        reason = f"Conflict detected in fields: {', '.join(conflict_fields.keys())}. Selected canonical based on priority."
    else:
        status = "reconciled"
        reason = "Multiple sources agree within thresholds."
        
    if has_duplicates:
        reason += " Chose deterministic representative among duplicate rows."

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
        observed_source_count=observed_source_count,
        conflict_fields=conflict_fields,
        source_snapshot=source_snapshot,
        decision_reason=reason
    )
