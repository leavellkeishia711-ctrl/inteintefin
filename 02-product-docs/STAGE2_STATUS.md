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
- Current main SHA: `d56e80e8a3f548b9b5e8d20b25b0010e31c2a766`
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
| Keitaro integration | **Stub, blocked** | Blocked in `registry.NON_PRODUCTION_CONNECTORS`; `test_connection` returns True; `fetch_campaigns` and `fetch_metrics` return empty lists |
| Binom integration | **Implemented, not wired** | `04-backend/app/connectors/binom.py` exists but missing from `CONNECTOR_NAMES` |
| Voluum integration | **Implemented, not wired** | `04-backend/app/connectors/voluum.py` exists but missing from `CONNECTOR_NAMES` |
| Affise integration | **Implemented, not wired** | `04-backend/app/connectors/affise.py` exists but missing from `CONNECTOR_NAMES` |
| Meta Ads integration (hardened) | **Done** | `04-backend/app/connectors/meta_ads.py` |
| TikTok Ads integration | **Mock-verified** | `04-backend/app/connectors/tiktok_ads.py` (live credential validation pending) |
| Google Ads integration | **Mock-verified** | `04-backend/app/connectors/google_ads.py` (live auth validated on test account, schema validation on prod data pending) |
| Ad accounts mapping (Meta, Google, TikTok) | Done | `fetch_ad_accounts()`/`normalize_ad_accounts()` in connectors; mapped in `test_*_fetch_ad_accounts`; persistence via `upsert_ad_accounts()` covered by `test_ad_accounts_upsert_idempotency.py` |
| Persistence tests | Done | `pytest tests/test_connectors_persistence.py` |
| Tenant isolation tests | Done | `test_meta_tenant_isolation`, `test_binom_tenant_isolation` |
| Idempotency tests | Done | `test_meta_upsert_idempotency`, `test_binom_upsert_idempotency` |
| Production smoke | Done | `.github/workflows/prod-gate.yml` |
| `CampaignRunStat` soft delete (`deleted_at`) | Done | `SoftDeleteMixin`, API read query filters |
| `CampaignRunStat` uniqueness | Done | Partial unique index `uix_company_connector`, checking `deleted_at IS NULL` |
| Atomic upsert (ON CONFLICT) | Done | `campaigns.py:upsert_campaign_run_stat_atomic` |
| Cross-source conflict resolution / reconciliation | Done | `CampaignRunReconciliation` model and `reconcile_company_data_task` |

## Source Data Storage Design

Data from different sources (e.g., Meta spend + Binom tracker revenue) for the same campaign and date are stored as **separate rows** keyed by `(company_id, campaign_run_id, stat_date, source, external_id)`. This is a deliberate side-by-side design for media buying analytics. Cross-source reconciliation / conflict resolution is **implemented** via the `CampaignRunReconciliation` table and `reconcile_company_data_task`.

- **Idempotency**: All CampaignRunStat records upserted using ON CONFLICT DO UPDATE.
- **Soft Delete**: Uses deleted_at instead of physical deletion.
- **Mapping**: ExternalCampaignMapping table links (company_id, platform, external_id) to campaign_run_id (1-to-many: one CampaignRun can have many external_id).

## Open Scope (Pending Next PRs)

The following requirements remain OPEN and must be implemented before full Stage 2 completion:

- Credential rotation (safe update, re-encryption endpoint) - **Partial** (`PATCH` endpoint exists with validation and audit, but re-encryption of existing keys is missing)
- Stale-source Data Quality (DQ) alerts - **Implemented, not wired** (logic in `app/services/data_quality.py` but no Celery beat task)
- ECB FX rate auto-fetch - **Implemented, not wired** (logic in `app/services/fx.py:fetch_ecb_rates` but no Celery beat task)
- Expanded observability (structured logging, metrics) - **Open** (currently uses standard Python logging)
- Production validation with real external API credentials:
  - **Google**: auth validated / schema pending.
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
- **SECURITY:** Meta reads `settings["lookback_days"]` (and others like Binom read `settings["base_url"]`), so `settings` via API cannot be open without an allowlist (risk of SSRF / token leak).
- Unmapped rows (without `ExternalCampaignMapping`) are silently skipped in upsert.
- ECB FX rate auto-fetch is not wired (multi-currency sync without cached rate raises error).

## Performance Metrics Updates (PR #25)
- **clicks, impressions, conversions added** to `NormalizedRecord` and `CampaignRunStat`.
- **conversions** stored as `NUMERIC(20,4)` (Decimal), never float. Protected from negative values via Pydantic `ge=Decimal("0")`.
- **Default values**: If a source (e.g. Trackers) does not provide `conversions`, it defaults to `0` / `Decimal("0")`.
- Stage 3 Analytics (ROI, CPM, forecasting) is **NOT** implemented yet (explicitly out of scope).

## Reconciliation Status (PR #26)
- **Implemented**: `CampaignRunReconciliation` tracks `status` (reconciled, partial, conflict, no_data).
- **Thresholds**: 1% relative difference threshold (`abs(a-b)/max(abs(a),abs(b)) > 0.01`) strictly using `Decimal` for spend, revenue, conversions, clicks, and impressions.
- **Duplicates**: Multiple stats for the same source are deterministically reduced (`priority` -> `external_id asc` -> `stat id asc`).
- **Currency**: Different currencies instantly flag a conflict.
- **Trigger**: No automatic DB trigger; manually executed via `reconcile_company_data_task` background task.
