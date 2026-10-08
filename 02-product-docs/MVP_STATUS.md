# FinanceIntel MVP Readiness Status (Stage 1)

This document tracks the readiness of the Stage 1 MVP against the requirements defined in `MVP.md`.

## Stage 1: COMPLETED

**Post-Merge Verification:**
- **Current Main SHA:** `924d48482e1db8b6a590e906c3d0f41c77630359`
- **CI Runs (on current main):** НЕ ПРОВЕРЕНО

## Phase 2 (Frontend Debt): COMPLETED

## Stage 2 Foundational Slice (Data Connectors): MERGED

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
| Alerts | Done | Celery `tasks.py` (Payroll task is missing, Implemented but not wired) |
