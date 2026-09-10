# Stage 2: Data Connectors Status

Stage 2 foundational slice: **MERGED AND VERIFIED**
Full Stage 2 roadmap: **PARTIAL / IN PROGRESS**

**Current main SHA:** `9a1b62aaf87149a046bd60a44eb5acbde42ca586`

## Verified Implementation (Post-Merge)

| Requirement | Status | Evidence |
|---|---|---|
| Connector base interface (`Connector` ABC) | Done | `04-backend/app/connectors/base.py` |
| `NormalizedRecord` / `NormalizedAdAccount` | Done | `04-backend/app/connectors/base.py` |
| Connector configuration (CRUD API) | Done | `04-backend/app/api/v1/connectors.py` |
| Encrypted credentials (Fernet) | Done | `04-backend/app/connectors/credentials.py` |
| Sync scheduling | Done | `04-backend/app/connectors/scheduler.py` |
| Shared retry/backoff (`with_retry`) | Done | `04-backend/app/connectors/base.py` |
| Keitaro integration | **Stub / Not Production-Ready** | `test_connection`/`fetch_campaigns`/`fetch_metrics` return stubs |
| Binom integration | **Merged & Post-Merge Verified** | `04-backend/app/connectors/binom.py` |
| Voluum integration | **Merged & Post-Merge Verified** | `04-backend/app/connectors/voluum.py` |
| Affise integration | **Merged & Post-Merge Verified** | `04-backend/app/connectors/affise.py` |
| Meta Ads integration (hardened) | **Merged & Post-Merge Verified** | `04-backend/app/connectors/meta_ads.py` |
| Ad accounts mapping (Meta only) | Done | `MetaAdsConnector.fetch_ad_accounts()` / `normalize_ad_accounts()` |
| Persistence tests | Done | `pytest tests/test_connectors_persistence.py` |
| Tenant isolation tests | Done | `test_meta_tenant_isolation`, `test_binom_tenant_isolation` |
| Idempotency tests | Done | `test_meta_upsert_idempotency`, `test_binom_upsert_idempotency` |
| Production smoke | Done | `.github/workflows/prod-gate.yml` |
| Post-merge CI (main) | Done | Backend: 34341326240, Frontend: 34341326184, Prod Gate: 34341326236 (on main `9a1b62aa`) |

## Source Data Storage Design

Data from different sources (e.g., Meta spend + Binom tracker revenue) for the same campaign and date are stored as **separate rows** keyed by `(company_id, campaign_run_id, stat_date, source, external_id)`. This is a deliberate side-by-side design for media buying analytics. **Cross-source reconciliation / conflict resolution is NOT yet implemented** and remains an OPEN GAP.

## Open Scope (Pending Next PRs)

The following requirements remain OPEN and must be implemented before full Stage 2 completion:

- Google Ads integration
- TikTok Ads integration
- Cross-source conflict resolution / reconciliation layer
- Credential rotation (safe update, re-encryption endpoint)
- Stale-source Data Quality (DQ) alerts
- `CampaignRunStat` soft delete (`deleted_at`)
- ECB FX rate auto-fetch
- Expanded observability (structured logging, metrics)
- Production validation with real external API credentials
- Keitaro: full implementation (`test_connection`, `fetch_campaigns`, `fetch_metrics`)
- Ad accounts mapping for Binom, Voluum, Affise (currently only Meta)
