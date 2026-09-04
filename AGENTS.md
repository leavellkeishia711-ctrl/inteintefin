# FinanceIntel — Rules for AI Agents

SaaS financial management for media buying. Virtual CFO over trackers.
Stage: Stage 2 "Data Connectors" (Foundational slice and core merged, full stage partial/in-progress).
Everything not in 02-product-docs/CURRENT_STATUS.md and current STAGE2_STATUS.md is OUT OF SCOPE.

## Structure
- 02-product-docs/ PRD, MVP, ROADMAP, DB_SCHEMA, OPEN_QUESTIONS (source of truth)
- 03-database/ init scripts
- 04-backend/ FastAPI + SQLAlchemy 2.0 + Alembic + Celery
- 05-frontend/ Next.js 16.2.10 + React 19 + Tailwind v4 + next-intl
- 08-devops/ docker-compose, deploy

## Invariants (Violation = Blocking Bug)
1. MONEY. Only Decimal / NUMERIC(20,4). `float` is STRICTLY FORBIDDEN. Rounding ROUND_HALF_UP to 4 places. Currency stored with amount.
2. TENANTS. `company_id` comes ONLY from JWT session. Never from request body, query params, or LLM tool args. Plus RLS in Postgres. Must use strict tenant isolation.
3. CR-1. AI Analyst responds only via tool use with real SQL to DB. No hallucinations.
4. PCI. Full card numbers and proxy passwords are not stored. Only masked identifiers (last 4 chars).
5. SECRETS. Never logged. Plaintext secrets are explicitly banned. Credentials rotated safely in transactions.
6. SOFT DELETE. `deleted_at` instead of DELETE on all financial tables.
7. TIME. TIMESTAMPTZ in UTC. created_at/updated_at everywhere.
8. IDEMPOTENCY. UNIQUE (company_id, source, external_id) on imports.
9. MIGRATIONS. `alembic upgrade/downgrade` must be flawless.

## Stage 2 Connector Constraints
- `BaseConnector` enforces contracts (`test_connection`, `fetch_ad_accounts`, `normalize`, `upsert`).
- `ad_accounts` must isolate by tenant via RLS and unique keys.
- `retry/backoff` must handle 429 and 50x safely with exponential backoff.
- `stale-source DQ` monitors ingestion using intervals.

## Backend
- Logic in `services/`, routers are thin. SQL only in `repositories/services`.
- Pydantic v2, `condecimal(max_digits=20, decimal_places=4)` for amounts.
- Every new route covered by tenant isolation test.
- Migrations only via `alembic revision --autogenerate`, manual diff check.

## Frontend
- Screens in `src/components/screens/`, pages only import them.
- Navigation via `Link/usePathname` from `@/i18n/routing`, NOT from `next/link`.
- Texts in `messages/en.json` and `messages/ru.json`. No hardcoded strings in JSX.
- Colors from Tailwind `@theme`. Palette `ai-*` only for AI blocks.
- Data via TanStack Query + `src/lib/api`. Direct import from mockData forbidden.
- Next.js 16 is newer than your training data: read `node_modules/next/dist/docs/`.

## Out of Scope Right Now
Stage 3+, Market Intelligence, Telegram parsing, 06-admin-frontend, Forecasting, Scenario Modeling, custom inference. Do not offer, do not write.
