# FinanceIntel MVP Readiness Status (Stage 1)

This document tracks the readiness of the Stage 1 MVP against the requirements defined in `MVP.md`.

## Stage 1: COMPLETED

**Post-Merge Verification (Historical Reference):**
- **Target SHA:** `d07c8174f8fd18f545d7f08298f4da99a020e803`
- **CI Runs:**
  - Backend CI: Passed (Run ID: `31249721497`)
  - Frontend CI: Passed (Run ID: `31249721778`)
  - Production Gate: Passed (Run ID: `31249721501`)

## Phase 2 (Frontend Debt): COMPLETED

**Post-Merge Verification (Historical Reference):**
- **Target SHA:** `976b4795a94dd1288f5a01b10f46ac328b7cc4dc`
- **CI Runs:**
  - Backend CI: Passed (Run ID: `33736109606`)
  - Frontend CI: Passed (Run ID: `33736109521`)
  - Production Gate: Passed (Run ID: `33736109479`)

## Stage 2 Foundational Slice (Data Connectors): MERGED

**Post-Merge Verification:**
- **Main SHA:** `8505645fb49a4e8b3a239f91de3ee01c8abda587`
- **PR #3:** Merged
- **CI Runs (on main `8505645fb49a4e8b3a239f91de3ee01c8abda587`):**
  - Backend CI: Passed (Run ID: `33855813988`)
  - Frontend CI: Passed (Run ID: `33855813989`)
  - Production Gate: Passed (Run ID: `33855813997`)

---

## Core Infrastructure (Stage 1)
| Requirement | Status | Evidence / Notes |
| :--- | :--- | :--- |
| PostgreSQL 16 (Multi-tenant schema) | Done | `init-db.sql` schemas, migrations |
| Redis 7 (Caching, Celery broker, rate limits) | Done | `docker-compose.yml`, rate limits configured |
| Python 3.11 + FastAPI + SQLAlchemy 2.0 | Done | `requirements.txt`, endpoints |
| Celery workers & beat | Done | `docker-compose.yml`, `celery_app.py` |
| Next.js 16 + React 19 + Tailwind v4 | Done | `package.json`, production builds configured |
| Docker Compose (Local & Production Gate) | Done | `docker-compose.yml`, `docker-compose.ci.yml` |

## Security & Architecture Invariants (Stage 1)
| Requirement | Status | Evidence / Notes |
| :--- | :--- | :--- |
| Decimal `NUMERIC(20,4)` for all currency | Done | Custom `condecimal`, `check_floats.py` |
| RLS (Row-Level Security) on `company_id` | Passed | `init-db.sql`, `tenant_session` |
| JWT Authentication & Refresh Tokens | Passed | `deps.py`, `auth.py` |
| Roles & Invites (Media Buyer ready) | Passed | `invites.py`, `require_roles` |
| Idempotency on Imports | Done | `UNIQUE(company_id, source, external_id)` |
| UTC Timestamps | Done | `TIMESTAMPTZ` on all models |
| Soft Delete | Done | `deleted_at` on models |
| PCI Masking | Done | Last 4 digits logic implemented |
| Secret rotation and hygiene | Done | Untracked `.env`, `check_secrets.py` |

## Features (Stage 1)
| Requirement | Status | Evidence / Notes |
| :--- | :--- | :--- |
| User Auth (Register, Login, JWT) | Done | `auth.py` endpoints |
| Transactions CRUD & Categorization | Done | `transactions.py` |
| P&L & Cashflow calculation | Done | `pnl.py`, `cashflow.py` |
| Telegram Bot Integration (`/status`, `/link`) | Done | `telegram_bot.py`, `webhooks.py` |
| AI Analyst Tool Use (Anthropic) | Done | `ai/client.py`, SQL tool use only |
| Background Payroll & Alerts | Done | Celery `tasks.py` |
