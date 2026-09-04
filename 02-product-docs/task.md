# Project Tasks

## Completed (Stage 1 & Stage 2 Foundational)

- [x] Mono-repo setup (backend, frontend, devops).
- [x] DB Models (SQLAlchemy 2.0) matching DB_SCHEMA.md.
- [x] Multi-tenancy Layer 1: PostgreSQL Row-Level Security (RLS) on `company_id`.
- [x] Multi-tenancy Layer 2: FastAPI Dependency (`tenant_session(company_id)`).
- [x] Auth: Argon2, JWT (access 15m, refresh httpOnly).
- [x] Endpoints: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/invite`.
- [x] Backend Decimal validation rule (prohibit float).
- [x] Transactions CRUD + CSV Import Wizard.
- [x] PCI Masking logic (last 4 digits).
- [x] Media Buying Domain: `ad_accounts`, `consumables`, `campaign_runs`.
- [x] `account_cost(ad_account_id)` calculation.
- [x] P&L & Cashflow calculation.
- [x] Audit Log JSONB-diff.
- [x] Celery + beat isolated tenant tasks.
- [x] Alerts: cash_runway, ROI.
- [x] Telegram-bot (outgoing only).
- [x] AI Financial Analyst (Anthropic) with strict RLS and SQL tool.
- [x] Data Connectors: `connectors/base.py` abstract class.
- [x] Data Connectors: encrypted credentials storage.
- [x] Data Connectors: Celery beat sync scheduler.
- [x] Data Connectors: Keitaro implementation.
- [x] Data Connectors: API endpoints (CRUD & sync).
- [x] Data Connectors: DB models & Alembic migration.
- [x] Data Connectors: Tenant isolation and persistence tests.
- [x] Data Connectors: Production Smoke Test.

## Open (Full Stage 2)

- [ ] `ad_accounts` mapping and synchronization.
- [ ] Shared rate-limit/retry/backoff policy for connectors.
- [ ] Credential rotation (safe update, re-encryption).
- [ ] Stale-source DQ alert.
- [ ] Binom integration.
- [ ] Voluum integration.
- [ ] Affise integration.
- [ ] Meta Ads integration.
- [ ] Google Ads integration.
- [ ] TikTok Ads integration.

## Open (Other)

- [ ] Data Quality Monitoring: test cases.
- [ ] Backend i18n implementation & tests.
- [ ] Frontend: Data Layer refactoring (TanStack Query, API client).
- [ ] Frontend: i18n label migration.

## Next Implementation Order

1. `connectors/base.py` standardization.
2. `ad_accounts` syncing.
3. Shared rate-limit/retry/backoff.
4. Credential rotation.
5. Stale-source DQ alert.
6. Binom integration.
7. Voluum integration.
8. Affise integration.
9. Meta Ads integration.
10. Google Ads integration.
11. TikTok Ads integration.
