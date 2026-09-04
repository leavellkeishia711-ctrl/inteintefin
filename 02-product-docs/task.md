# Checklist for Massive Refactoring

## Part 1: DB_SCHEMA.md Updates
- [x] Remove spend, revenue, currency, stat_date, external_id from `campaigns`.
- [x] Remove spend, revenue from `campaign_runs`.
- [x] Add `campaign_run_stats` table (id, company_id, campaign_run_id, stat_date, spend, revenue, currency, fx_rate_to_base, source, external_id, created_at, updated_at). Add UNIQUE and INDEX.
- [x] Define source of truth rules (P&L = transactions; Ad stats = campaign_run_stats).
- [x] Transactions: split `payout` into `payout_incoming` and `payout_outgoing`. No auto creation from stats, or use `source='derived'`.
- [x] `companies.cash_balance`: remove column, define as calculated from transactions.
- [x] Add `available_balance` formula.
- [x] Add `expected_amount`, `scrubbed_amount`, `actual_amount` to `partner_payouts`.
- [x] Add `fx_rate_to_base` (NOT NULL) to: `campaign_run_stats`, `consumables`, `partner_payouts`, `payroll_runs`, `payroll_line_items`, `compensation_plans`.
- [x] Add `fx_rates` table.
- [x] Fix division by zero logic for ROI, ROAS, Margin.
- [x] Define Cash Runway window (30 days).
- [x] Document Finance Health Score formula.
- [x] P&L Mapping definitions.
- [x] Add `company_id` to `decision_recommendations`, `payroll_line_items`.
- [x] Document RLS and filtering. Prevent cross-company FKs.
- [x] Update `users` email UNIQUE to include company_id.
- [x] Add CHECK/enum constraints for types/status/roles/categories.
- [x] Add missing fields: `ad_accounts.updated_at`, `ad_accounts.deleted_at`, `payroll_runs.deleted_at`, `payroll_line_items.updated_at`.
- [x] Add `telegram_link_tokens` table.
- [x] Add `invites` table.
- [x] Add `import_batches` table and `transactions.import_batch_id`.
- [x] Add EXCLUDE USING gist constraint for `compensation_plans` (no overlapping dates).
- [x] Add `dedup_key`, `cooldown_until` to `alerts`.
- [x] Document Argon2id hash logic.
- [x] Data storage & masking policies.
- [x] Sync `telegram_chat_id`.
- [x] Translate English comments to Russian in schema.

## Part 2: Product Docs Refactor
- [x] Create `archive/` dir. Move legacy docs (addendums, docx, PROMPT, old PRD).
- [x] PRD.md: bump to v2.6, update §9 stack, update §8 MI, update §6 roles, fix §5.3.1/§5.4/§5.14, fix links.
- [x] MVP.md: sync roles, finance health score, payroll, consumables, close Keitaro question, add 12-step plan items, add i18n to scope.
- [x] ROADMAP.md: sync Stage 1 with MVP, sync Stage 4a, mark Stage 5.
- [x] OPEN_QUESTIONS.md: renumber, close Q8/Q11/Q13/Q14, remove R18.
- [x] Create `DECISIONS.md`.
- [x] Root `README.md`.
- [x] Add `.gitignore` for root.
- [x] Fix/Remove `.gitmodules`.
- [x] Add `09-reference/README.md`.
- [x] Remove empty `03-database/README.md` / `04-backend/README.md`.

## Part 3: Frontends
- [x] `05-frontend`: package.json, lock file, tsconfig, next config, .env.example, gitignore.
- [x] `05-frontend`: restructure into app/components/features/lib/providers/hooks/types/tests/public.
- [ ] `05-frontend`: Data Layer refactoring (TanStack Query, API client, types from OpenAPI).
- [ ] `05-frontend`: Remove hardcoded English labels (use i18n).
- [ ] `05-frontend`: Remove fake `/api/user/preferences` call from Header.
- [x] `06-admin-frontend`: boilerplate, separate package.json, next.config, structure, etc.

## Part 4: Backend Skeleton & Core (Week 1 & 2)
- [x] Mono-repo setup (unsubmodule frontend, update README).
- [x] `08-devops` with `docker-compose.yml` and `.env.example`.
- [x] `AGENTS.md` in root with invariants (Decimal, company_id, CR-1).
- [x] Move chat history and prompts to `archive/`.
- [x] Setup `04-backend` skeleton (folders, pyproject.toml).
- [x] DB Models (SQLAlchemy 2.0) matching DB_SCHEMA.md. `app/db/models/` (base.py, campaigns.py, companies.py, finance.py, system.py, users.py) + `test_types.py`, `test_rls_completeness.py`.
- [x] Multi-tenancy Layer 1: PostgreSQL Row-Level Security (RLS) on all domain tables. `alembic/versions/0002_rls.py`, `e8acf4873fc7_enforce_rls_on_remaining_tables.py`.
- [x] Multi-tenancy Layer 2: FastAPI Dependency (`set_config('app.company_id', ...)`). `app/db/session.py` L104-107, `app/core/deps.py` `tenant_session(company_id)`.
- [x] Auth: Argon2, JWT (access 15m, refresh httpOnly). `app/api/v1/auth.py`, `app/core/security.py` + `test_auth.py`.
- [x] Endpoints: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/invite`. `app/api/v1/auth.py`, `app/api/v1/invites.py` + `test_auth.py`, `test_invites.py`.
- [x] `test_tenant_isolation.py` (Must be GREEN). `tests/test_tenant_isolation.py`.
- [x] Alembic migrations setup and generated. 8 migration versions in `alembic/versions/`.
- [x] Backend Decimal validation rule (prohibit float). `scripts/check_floats.py` + `tests/test_no_float.py`.
- [x] Transactions CRUD + CSV Import Wizard (2 steps: parse/preview -> confirm). `app/api/v1/transactions.py`, `app/api/v1/imports.py`, `app/services/imports.py` + `test_transactions.py`.
- [x] `consumables.identifier` PAN validator (PCI rule). `app/schemas/campaigns.py` validator + `test_consumables.py` (test_pan_masking).

## Part 5: Domain & Calculations (Week 3 & 4)
- [x] Media Buying Domain: `ad_accounts` -> `consumables` -> `campaign_runs`. `app/api/v1/ad_accounts.py`, `app/api/v1/campaign_runs.py`, `app/api/v1/campaign_run_stats.py`, `app/api/v1/consumables.py` + `test_campaigns.py`, `test_media_buying.py`.
- [x] `account_cost(ad_account_id)` calculation. `app/services/campaigns.py:get_ad_account_cost` + `test_campaigns.py:test_get_ad_account_cost`.
- [x] `services/pnl.py`, `services/cashflow.py`, `services/metrics.py` (Gross, EBITDA, EBIT, Net, Runway, Health Score). + `test_computation.py`.
- [~] Partner payouts lifecycle (booked -> in_hold -> scrubbed -> paid). `app/services/partners.py`, `app/schemas/partners.py`, `app/api/v1/partners.py` exist. **No dedicated test file.**

## Track A: Backend Finalization (Block 7)
- [x] 7.1 Audit Log: JSONB-diff of transactions, budgets, payroll. System actor for celery tasks. Explicit blacklist for secrets. `app/services/audit.py` (generate_diff, record_user_audit, record_system_audit) + `test_audit.py`.
- [x] 7.2 Celery + beat: `app/workers/celery_app.py`, tasks in `tasks.py`. Tenant isolation context manager `tenant_task_session(company_id)`. Broker config via `.env`. + `test_celery_tenant_isolation.py`.
- [x] 7.3 Alerts: cash_runway < N days, ROI < threshold. Dedup via dedup_key and cooldown_until. Email + Telegram delivery. `app/services/alerts.py`, `app/api/v1/alerts.py` + `test_alerts.py`.
- [x] 7.4 Telegram-bot (outgoing only): POST `/telegram/link`, handle `/start <token>`, return personal stats isolated by RLS. `app/services/telegram_bot.py`, `app/api/v1/webhooks.py` + `test_telegram.py`, `test_telegram_link.py`.
- [~] 7.5 Data Quality Monitoring: Check stalled data (no transactions, stalled trackers). `app/services/data_quality.py` exists. **No dedicated test file.**
- [~] 7.6 Backend i18n: Language from company/user profile (EN, RU). `app/core/i18n.py` exists. **No dedicated test file.**
- [x] 7.7 AI Financial Analyst: Fixed tool set, strict RLS, no text-to-SQL. Handle tool failure gracefully with 5 retries. `app/ai/analyst.py`, `app/ai/tools.py`, `app/ai/client.py` + `test_ai_analyst.py`.

## Track B: Frontend Data Layer & i18n
- [ ] B.1 Backend decimal serialization to string configured globally.
- [ ] B.1 OpenAPI TS generation script.
- [ ] B.1 Unified API client with fetch, 401 handling, include credentials.
- [ ] B.1 TanStack Query client setup.
- [ ] B.1 Decimal formatter (`Intl.NumberFormat`) treating values as strings without `parseFloat`. Explicit `null` handling.
- [ ] B.2 i18n migration (next-intl).
- [ ] B.3 Header fetching from `/auth/me`.

## Долг по тестам

Пункты, где код существует, но выделенные тесты отсутствуют (помечены `[~]`):

1. **Partner payouts lifecycle** — `app/services/partners.py`, `app/schemas/partners.py`, `app/api/v1/partners.py` существуют. Нет `test_partners.py`. Нужны тесты: создание, смена статуса (booked→in_hold→scrubbed→paid), запрет перехода в невалидный статус, тенант-изоляция.
2. **Data Quality Monitoring** — `app/services/data_quality.py` существует. Нет `test_data_quality.py`. Нужны тесты: обнаружение stalled данных, отсутствие транзакций за период, stalled трекеры.
3. **Backend i18n** — `app/core/i18n.py` существует. Нет `test_i18n.py`. Нужны тесты: определение языка из профиля пользователя/компании, fallback на EN.

## Phase 3 � Stage 2: Data Connectors
- [x] 3.1 Branch feat/stage2-connectors from main
- [x] 3.2 connectors/base.py abstract class
- [x] 3.3 connectors/credentials.py encrypted storage
- [x] 3.4 connectors/scheduler.py Celery beat
- [x] 3.5 connectors/keitaro.py Keitaro implementation
- [x] 3.6 api/v1/connectors.py CRUD & sync endpoints
- [x] 3.7 DB model & Alembic migration
- [x] 3.8 Add metrics to data_quality.py
- [x] 3.9 Write test_connectors.py
