# Walkthrough: Stage 1 Financial Core (Part 3)

*Note: The conversation history leading up to this point has been mostly truncated. The following outlines the immediate changes that were implemented in the latest session.*

## 1. Monorepo Migration
- Killed `05-frontend` submodule.
- Pulled the repo natively into the tree.
- Archived all `chat_history_*.md` files to `archive/ai-logs/`.
- Updated `README.md` to reflect the current structure.

## 2. Infrastructure Setup
- Configured `08-devops/docker-compose.yml` for Postgres 16 and Redis 7.
- Added `init-db.sql` which enforces `app_user` for RLS.
- Defined `.env.example` with standard defaults.

## 3. Row-Level Security (RLS)
- Re-wrote `app/db/session.py` and `deps.py` to enforce `SET LOCAL app.company_id` before yielding sessions to routes.
- Wrote `alembic/versions/0002_rls.py` explicitly forcing `tenant_isolation` policy on all core tables.
- Implemented `test_tenant_isolation.py` which guarantees 403/404 when querying across tenants for every single `v1` endpoint.

## 4. Backend Services
- **Money & Parsing**: Created `money.py` (strictly decimal precision 28, 4 decimal places) and `parsing.py` for dealing with different currency input formats (like "(500)").
- **Transactions & Imports**: Created `app/services/transactions.py`, `app/services/imports.py`, and `app/api/v1/transactions.py` to deal with direct inserts and batch CSV parsing with `on_conflict_do_nothing`.
- **FX Rates**: Implemented `resolve_fx_rate` in `fx.py` capable of looking backward 7 days and inferring inverse rates.
- **Audit Logging**: Basic generic audit tracking in `audit.py`.

## 5. Frontend (`05-frontend`)
- Implemented `TransactionsScreen.tsx` mock/TanStack layout with navigation layout in `Sidebar.tsx`.
- Ensured locale translations exist in `en.json` and `ru.json`.
- Implemented `src/lib/api/client.ts`.

## 6. Product Docs
- Resolved the addendums note directly inside `OPEN_QUESTIONS.md` as explicitly requested.
- Documented `processor` role piece-rate rule inside `MVP.md`.
- Wrote `AGENTS.md` in root to govern absolute rules across all AI subagents.

## 7. Financial Calculation Engine (Latest Changes)
- **Supavisor Transaction Bug Fixed**: Replaced `JSONB` with `JSON` in SQLAlchemy models (`AuditLog.diff` etc.) to force `psycopg3` to use the standard text-based binding. This completely eliminated the `server closed the connection unexpectedly` error caused by binary protocol mismatch over Supavisor's transactional pool.
- **Reporting Services (`app/services/finance.py`)**:
  - `get_pnl_report`: Implemented full accrual P&L logic. Accurately calculates `booked_revenue`, `scrubbed_amount`, `confirmed_payout`, `direct_ad_spend`, `allocated_consumables`, `contribution_profit` (with margin), and `net_profit` (after payroll and overheads).
  - `get_cash_flow_report`: Implemented cash basis tracking to calculate total `inflows` and `outflows` based on actual transactions.
  - `get_liquidity`: Calculates the currently available cash position.
- **Test Coverage (`tests/test_finance_core.py`)**: 
  - Wrote a complex control dataset fixture (simulating actual operations: booked revenue, scrubs, ad spend, proxies, payroll, and overheads).
  - Ensured all mathematical assertions pass at 100%. Teardown bugs were completely resolved.
- **Reports API (`app/api/v1/reports.py`)**:
  - Exposed `GET /reports/pnl`, `GET /reports/cash-flow`, and `GET /reports/liquidity` routes with Pydantic schemas. Integrated into the main router.
