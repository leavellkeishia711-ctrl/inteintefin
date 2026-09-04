# FinanceIntel — Rules for AI Agents

SaaS financial management for media buying. Virtual CFO over trackers.
Stage: Stage 2 "Data Connectors" (Foundational slice merged, full stage partial).
Everything not in 02-product-docs/MVP.md and current STAGE2_STATUS.md is OUT OF SCOPE.

## Structure
- 02-product-docs/ PRD, MVP, ROADMAP, DB_SCHEMA, OPEN_QUESTIONS (source of truth)
- 03-database/ init scripts
- 04-backend/ FastAPI + SQLAlchemy 2.0 + Alembic + Celery
- 05-frontend/ Next.js 16.2.10 + React 19 + Tailwind v4 + next-intl
- 08-devops/ docker-compose, deploy

## Invariants (Violation = Blocking Bug)
1. MONEY. Only Decimal / NUMERIC(20,4). `float` is STRICTLY FORBIDDEN. Rounding ROUND_HALF_UP to 4 places. Currency stored with amount.
2. TENANTS. `company_id` comes ONLY from JWT session. Never from request body, query params, or LLM tool args. Plus RLS in Postgres.
3. CR-1. AI Analyst responds only via tool use with real SQL to DB. No hallucinations.
4. PCI. Full card numbers and proxy passwords are not stored. Only masked identifiers (last 4 chars).
5. SECRETS. Never logged. Never in LLM context.
6. SOFT DELETE. `deleted_at` instead of DELETE on all financial tables.
7. TIME. TIMESTAMPTZ in UTC. created_at/updated_at everywhere.
8. IDEMPOTENCY. UNIQUE (company_id, source, external_id) on imports.

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

## Data Connectors (Stage 2)
- All integrations MUST implement the base interface `Connector` from `connectors/base.py`.
- `company_id` only from JWT.
- RLS enforced on all connector tables.
- Secrets encrypted at rest (Fernet).
- Secrets NEVER logged.
- API responses MUST NOT contain plaintext or encrypted secrets.
- Decimal for money.
- Idempotent upsert is STRICTLY REQUIRED.
- Timeout, retry, and exponential backoff for external APIs.
- Tenant isolation tests and migration tests required.

## Out of Scope Right Now
Market Intelligence, Telegram parsing, 06-admin-frontend, Forecasting, Scenario Modeling, custom inference. Do not offer, do not write.
