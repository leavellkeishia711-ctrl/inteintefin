# Stage 2: Data Connectors Status

Source of truth for Stage 2. ROADMAP.md and task.md summarize this file and must not contradict it.

**Status Scale:**
- **Done**: Available in production via API/scheduler, covered by CI.
- **Implemented, not wired**: Code and tests exist, but not available in prod (explain why).
- **Mock-verified**: Local implementation is done and tested via mocks, live-validation pending.
- **Partial**: Partially implemented.
- **Stub, blocked**: Only a stub exists, blocked in prod.
- **Open**: Not implemented.

Stage 2 foundational slice: **MERGED AND VERIFIED**
Full Stage 2 roadmap: **PARTIAL / IN PROGRESS**

### CI/CD Baseline
- Current main SHA: `d56e80e8a3f548b9b5e8d20b25b0010e31c2a766` (last code change on main)
- PR #32 squash merge
- Backend CI: 37280619697, Frontend CI: 37280619642, Production Gate: 37280619568

## Verified Implementation (Post-Merge)

| Requirement | Status | Evidence |
|---|---|---|
| Connector base interface (`Connector` ABC) | Done | `04-backend/app/connectors/base.py` |
| `NormalizedRecord` / `NormalizedAdAccount` | Done | `04-backend/app/connectors/base.py` |
| Connector configuration (CRUD API) | Done | `04-backend/app/api/v1/connectors.py` |
| Encrypted credentials (Fernet) | Done | `04-backend/app/connectors/credentials.py` |
| Sync scheduling | Done | `04-backend/app/connectors/scheduler.py` |
| Shared retry/backoff (`with_retry`) | Done | `04-backend/app/connectors/base.py` |
| Keitaro integration | **Stub, blocked** | `app/api/v1/connectors.py:53` (HTTP 422 on create); `app/connectors/scheduler.py:44` (paused if in NON_PRODUCTION_CONNECTORS) |
| Binom integration | **Implemented, not wired** | `04-backend/app/connectors/binom.py` exists but missing from `CONNECTOR_NAMES` |
| Voluum integration | **Implemented, not wired** | `04-backend/app/connectors/voluum.py` exists but missing from `CONNECTOR_NAMES` |
| Affise integration | **Implemented, not wired** | `04-backend/app/connectors/affise.py` exists but missing from `CONNECTOR_NAMES` |
| Meta Ads integration (hardened) | **Mock-verified** | `04-backend/app/connectors/meta_ads.py:24` (settings config missing for base_url and lookback_days, live-validation pending) |
| TikTok Ads integration | **Mock-verified** | `04-backend/app/connectors/tiktok_ads.py` (live credential validation pending) |
| Google Ads integration | **Done** | `04-backend/app/connectors/google_ads.py` (live auth and schema validated on prod data) |
| Ad accounts mapping (Meta, Google, TikTok) | Done | `fetch_ad_accounts()`/`normalize_ad_accounts()` in connectors; mapped in `test_*_fetch_ad_accounts`; persistence via `upsert_ad_accounts()` covered by `test_ad_accounts_upsert_idempotency.py` |
| Persistence tests | Done | `pytest tests/test_connectors_persistence.py` |
| Tenant isolation tests | Done | `test_meta_tenant_isolation`, `test_binom_tenant_isolation` |
| Idempotency tests | Done | `test_meta_upsert_idempotency`, `test_binom_upsert_idempotency` |
| Production smoke | Done | `.github/workflows/prod-gate.yml` |
| `CampaignRunStat` soft delete (`deleted_at`) | Done | `SoftDeleteMixin`, API read query filters |
| `CampaignRunStat` uniqueness | Done | Partial unique indexes `uq_campaign_run_stats_not_null_ext` and `uq_campaign_run_stats_null_ext`, checking `deleted_at IS NULL` (`app/db/models/campaigns.py`) |
| Atomic upsert (ON CONFLICT) | Done | `campaigns.py:upsert_campaign_run_stat_atomic` |
| Cross-source conflict resolution / reconciliation | **Implemented, not wired** | `CampaignRunReconciliation` model and `reconcile_company_data_task` exist (`app/workers/tasks.py:75`), but no trigger: not in beat, no API caller |
| Stale-source Data Quality (DQ) alerts | Done | Runs daily via beat (`app/workers/tasks.py:60`), calls `monitor_stalled_data`, tested in `test_stale_source_dq.py`; alert latency up to 24h |

## Source Data Storage Design

Data from different sources (e.g., Meta spend + Binom tracker revenue) for the same campaign and date are stored as **separate rows** keyed by `(company_id, campaign_run_id, stat_date, source, external_id)`. This is a deliberate side-by-side design for media buying analytics. Cross-source reconciliation / conflict resolution is **implemented** via the `CampaignRunReconciliation` table and `reconcile_company_data_task`.

- **Idempotency**: All CampaignRunStat records upserted using ON CONFLICT DO UPDATE.
- **Soft Delete**: Uses deleted_at instead of physical deletion.
- **Mapping**: ExternalCampaignMapping table links (company_id, platform, external_id) to campaign_run_id (1-to-many: one CampaignRun can have many external_id).

## Open Scope (Pending Next PRs)

The following requirements remain OPEN and must be implemented before full Stage 2 completion:

- Credential rotation (safe update, re-encryption endpoint) - **Partial** (`PATCH` endpoint exists with validation and audit, but re-encryption of existing keys is missing in `app/connectors/credentials.py`)
- ECB FX rate auto-fetch - **Implemented, not wired to Prod** (Celery beat automated, triangulation via EUR implemented, policy without overwrites. Awaiting live prod check).
- Expanded observability (structured logging, metrics) - **Open** (currently uses standard Python logging)
- Production validation with real external API credentials:
  - **Google**: **Done** (auth and schema validated on prod data).
  - **TikTok**: pending.
  - **Meta**: pending.
  - **Binom**: pending.
  - **Live validation harness now fully supports Google, TikTok, Meta, and Binom.**
  - **Google Details:** Added `cloud_managed` mode (without developer token) and precise error mappings.
  - **Meta Details:** scheduled sync always requests daily stats for an explicit date range (default lookback 7 days, configurable via settings.lookback_days, 1..90); aggregated rows (date_start != date_stop) are dropped.
  - **Binom Details:** Upgraded to API v2 endpoints and normalized `base_url` handling.
- Keitaro: full implementation (`test_connection`, `fetch_campaigns`, `fetch_metrics`) - **Stub, blocked**
- Ad accounts mapping for Binom, Voluum, Affise: N/A for current ad_accounts model. (These are tracker/workspace or affiliate-network entities, not advertising source accounts; such unification requires a separate product scope).

### Known gaps after PR-A
- `settings` column is missing in `ConnectorConfig`, so Binom/Google settings (`base_url`, `customer_id`) and Meta `lookback_days` are not accessible to the scheduler.
- **SECURITY / SSRF Risk:** Currently, users cannot set a custom `base_url` because `settings` is missing from `ConnectorConfig` and the API schema. However, `MetaAdsConnector` code already calls `settings.get("base_url")`. Once `settings` is exposed via the API, allowing arbitrary `base_url` without an allowlist/strict validation will introduce an SSRF and token leak vulnerability (sending the Bearer token to a malicious host). Note: configuring `lookback_days` via `settings` does not pose an SSRF risk.
- Unmapped rows (without `ExternalCampaignMapping`) are silently skipped in upsert.

## Performance Metrics Updates (PR #25)
- **clicks, impressions, conversions added** to `NormalizedRecord` and `CampaignRunStat`.
- **conversions** stored as `NUMERIC(20,4)` (Decimal), never float. Protected from negative values via Pydantic `ge=Decimal("0")`.
- **Default values**: If a source (e.g. Trackers) does not provide `conversions`, it defaults to `0` / `Decimal("0")`.
- Stage 3 Analytics (ROI, CPM, forecasting) is **NOT** implemented yet (explicitly out of scope).

## Reconciliation Status (PR #26)
- **Implemented, not wired**: `CampaignRunReconciliation` tracks `status` (reconciled, partial, conflict, no_data).
- **Thresholds**: 1% relative difference threshold (`abs(a-b)/max(abs(a),abs(b)) > 0.01`) strictly using `Decimal` for spend, revenue, conversions, clicks, and impressions.
- **Duplicates**: Multiple stats for the same source are deterministically reduced (`priority` -> `external_id asc` -> `stat id asc`).
- **Currency**: Different currencies instantly flag a conflict.
- **Trigger**: No API caller or beat schedule invokes `reconcile_company_data_task`.
