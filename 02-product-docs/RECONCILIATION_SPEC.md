# Reconciliation Specification (Stage 2)

## 1. Unit of Reconciliation
- Grouping key: `(company_id, campaign_run_id, stat_date)`
- `external_id` is NOT part of the reconciliation group because different platforms (e.g., Meta and Voluum) have different external IDs for the same logical campaign run.

## 2. Sources
- Identified by the `source` field in `CampaignRunStat` (e.g., "meta", "voluum", "binom", "google_ads").
- Soft-deleted rows (`deleted_at IS NOT NULL`) are ignored.
- Rows belonging to other `company_id` are strictly isolated and ignored.

## 3. Reconciled Fields
The following fields are compared and canonicalized:
- `spend` (Decimal)
- `revenue` (Decimal)
- `clicks` (Integer)
- `impressions` (Integer)
- `conversions` (Decimal)
- `currency` (String) - canonical currency matches the chosen source.

## 4. Canonical Result Model
The canonical result (`CampaignRunReconciliation`) stores:
- `status`: `reconciled`, `partial`, `conflict`, `no_data`
- `chosen_source`: The source selected based on deterministic priority.
- Canonical metrics: `canonical_spend`, `canonical_revenue`, `canonical_clicks`, `canonical_impressions`, `canonical_conversions`, `canonical_currency`.
- `conflict_fields`: JSONB object listing fields that diverged above thresholds.
- `source_snapshot`: JSONB object containing safe identifiers and metric values of all observed sources.
- `decision_reason`: Explicit text describing why the decision was made.

## 5. Conflict Determination
- **Missing Source**: Not a conflict in itself.
- **Exact Match / Within Threshold**: If multiple sources exist and their metrics are equal or within predefined tolerance thresholds, they are considered in agreement.
- **Conflict**: Two or more valid sources diverge beyond the threshold on any reconciled field.
- **Thresholds (Technical Defaults)**:
  - Threshold formula: `abs(a - b) / max(abs(a), abs(b)) > 0.01` (1% relative difference).
  - Spend/Revenue/Conversions: use the 1% relative difference formula. `0` vs `non-zero` is a conflict. `0` vs `0` is not a conflict. Uses `Decimal` type exclusively (no floats).
  - Clicks/Impressions: uses the exact same 1% relative difference policy. No float conversion is allowed.

## 6. Source Selection Policy
The selection of the canonical source is deterministic. We do not automatically average or sum conflicting values.

**Priority List (Technical Default)**:
1. `voluum` (Tracker)
2. `binom` (Tracker)
3. `keitaro` (Tracker)
4. `affise` (Network)
5. `meta` (Ad Network)
6. `google_ads` (Ad Network)
7. `tiktok_ads` (Ad Network)

**Rules**:
1. If no valid stats exist -> `no_data`.
2. If exactly one source exists -> `partial` (single source). Canonical values take this source.
3. If multiple sources exist and agree (within thresholds) -> `reconciled`. Canonical values take the highest priority source.
4. If multiple sources exist and conflict -> `conflict`. Canonical values STILL take the highest priority source, but `conflict_fields` explicitly records the divergence.
5. Missing sources fall back to the next available valid source in the priority list.
6. **Duplicate sources**: If multiple stats exist for the *same* source (e.g. two `meta` rows with different `external_id`), one deterministic representative is chosen (`priority` -> `external_id asc` -> `stat id asc`). All original rows are preserved as a list in `source_snapshot` under that source key.
7. **Currencies**: Different currencies are an immediate conflict. Raw numeric values must never be compared directly across different currencies without a verified exchange rate.
8. **Observed source count**: Tracks the count of *unique* valid sources observed, not the raw row count.
9. **Automatic Trigger**: Reconciliation is executed exclusively via an internal/manual Celery task (`reconcile_company_data_task`). No automatic trigger exists on data sync.
