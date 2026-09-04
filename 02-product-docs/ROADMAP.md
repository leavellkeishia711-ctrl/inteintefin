# FinanceIntel Roadmap

This document outlines the phased delivery plan for FinanceIntel.

---

## Stage 1 - Foundation & Core (MVP)
**Status:** COMPLETED

- [x] Multi-tenancy & Security (RLS, JWT, Argon2).
- [x] Database Schema & DB Migrations.
- [x] Transactions CRUD & CSV Import.
- [x] P&L and Cashflow Calculation.
- [x] Tenant-isolated Background Tasks (Celery).
- [x] Base AI Financial Analyst (SQL tool).
- [x] Telegram Alerts.
- [x] Foundational Frontend (Next.js, Tailwind).

---

## 📍 МЫ ЗДЕСЬ: Stage 2 - Data Connectors
**Status:** IN PROGRESS (Foundational Slice Merged)

**Goal:** Automated ingestion of costs, revenues, and campaigns.

**Completed (Foundational Slice):**
- [x] `connectors/base.py` abstract class.
- [x] Encrypted credentials storage.
- [x] Keitaro implementation.
- [x] Sync scheduling (Celery beat).
- [x] Connector API endpoints & DB models.
- [x] Tenant isolation and persistence testing.
- [x] Production Smoke Test.

**Open (Pending Implementation):**
- [ ] `ad_accounts` mapping and synchronization.
- [ ] Shared rate-limit/retry/backoff policy.
- [ ] Credential rotation.
- [ ] Stale-source DQ alert.
- [ ] Binom integration.
- [ ] Voluum integration.
- [ ] Affise integration.
- [ ] Meta Ads integration.
- [ ] Google Ads integration.
- [ ] TikTok Ads integration.

---

## Stage 3 - Cashflow & Budget Planning
**Status:** PLANNED

- [ ] Budget Requests & Approvals workflow.
- [ ] Automated Payroll run generation.
- [ ] Invoice generation & PDF export.
- [ ] Partner / Affiliate Payout lifecycle (Hold, Scrubbed, Paid).
- [ ] Advanced Rule Engine for cost allocation.

---

## Stage 4a - Market Intelligence (Human-in-the-loop)
**Status:** PLANNED (Out of current scope)

- [ ] Telegram / News scraping.
- [ ] Admin / Moderator Frontend for Human Review.
- [ ] Signal Extraction & Pattern Detection.

---

## Stage 4b - Market Intelligence (Automated)
**Status:** PLANNED (Out of current scope)

- [ ] Telethon/MTProto direct connections.
- [ ] Auto-publishing to intelligence feeds.
- [ ] Impact Briefs.

---

## Stage 5 - Decision & Scale
**Status:** PLANNED (Out of current scope)

- [ ] Decision Recommendation Engine (ROI optimization).
- [ ] Scenario Modeling (What-If).
- [ ] Enterprise SSO/SAML & Compliance Logs.
