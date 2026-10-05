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

## Stage 2 - Data Connectors
**Status:** IN PROGRESS (Foundational Slice + Tracker/Meta Connectors Merged)

**Goal:** Automated ingestion of costs, revenues, and campaigns.
**Note:** See STAGE2_STATUS.md for the detailed source of truth for Stage 2.

**Completed:**
- [x] `connectors/base.py` abstract class.
- [x] Encrypted credentials storage.
- [x] Sync scheduling (Celery beat).
- [x] Connector API endpoints & DB models.
- [x] Tenant isolation and persistence testing.
- [x] Production Smoke Test.
- [x] Shared rate-limit/retry/backoff policy (`with_retry`).
- [x] `ad_accounts` mapping (Meta/Google/TikTok).
- [x] `CampaignRunStat` soft delete.
- [x] Stale-source DQ alert.

**Implemented, pending wiring/validation:**
- [ ] Binom integration (Implemented, not wired).
- [ ] Voluum integration (Implemented, not wired).
- [ ] Affise integration (Implemented, not wired).
- [ ] Meta Ads integration (Mock-verified).
- [ ] Google Ads integration (Mock-verified).
- [ ] TikTok Ads integration (Mock-verified).
- [ ] Cross-source conflict resolution / reconciliation (Implemented, not wired).

**Open (Pending Implementation):**
- [ ] Credential rotation endpoint (partial).
- [ ] ECB FX rate auto-fetch (stub only).
- [ ] Expanded observability (structured logging, metrics).
- [ ] Production validation with real API credentials.
- [ ] Keitaro implementation (blocked/stub).

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
