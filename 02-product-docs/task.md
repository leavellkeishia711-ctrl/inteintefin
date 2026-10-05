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
- [x] Data Connectors: API endpoints (CRUD & sync).
- [x] Data Connectors: DB models & Alembic migration.
- [x] Data Connectors: Tenant isolation and persistence tests.
- [x] Data Connectors: Production Smoke Test.

## Open (Full Stage 2)

- [x] `ad_accounts` mapping and synchronization (Meta/Google/TikTok done; Binom/Voluum/Affise N/A for current ad_accounts model. They are tracker/workspace or affiliate-network entities, not advertising source accounts; such unification requires a separate product scope).
- [x] Shared rate-limit/retry/backoff policy for connectors.
- [x] Stale-source DQ alert.
- [ ] Binom integration (Implemented, not wired).
- [ ] Voluum integration (Implemented, not wired).
- [ ] Affise integration (Implemented, not wired).
- [ ] Meta Ads integration (Mock-verified).
- [ ] Google Ads integration (Mock-verified).
- [ ] TikTok Ads integration (Mock-verified).
- [ ] Credential rotation (partial).
- [ ] Keitaro integration (stub/blocked).
- [ ] Cross-source conflict resolution / reconciliation (Implemented, not wired).

## Open (Other)

- [ ] Data Quality Monitoring: test cases.
- [ ] Backend i18n implementation & tests.
- [ ] Frontend: Data Layer refactoring (TanStack Query, API client).
- [ ] Frontend: i18n label migration.

## Next Implementation Order (Proposed, Requires Owner Confirmation)

1. PR-B: ConnectorConfig.settings (JSONB, per-connector Pydantic allowlist, API create/patch, PATCH validate, tests).
2. PR-C: Registration of binom/voluum/affise + `base_url` validation (https-only, block private/loopback IP).
3. ECB FX auto-fetch.
4. Reconciliation trigger (beat or post-sync).
5. Observability (structured logging, metrics).
6. Live validation with real credentials (Google schema, TikTok, Meta, Binom).
7. Keitaro full implementation.
