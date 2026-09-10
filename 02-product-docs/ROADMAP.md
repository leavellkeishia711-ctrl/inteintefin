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
**Status:** IN PROGRESS (Foundational Slice + Tracker/Meta Connectors Merged)

**Goal:** Automated ingestion of costs, revenues, and campaigns.

**Completed (Merged & Post-Merge Verified):**
- [x] `connectors/base.py` abstract class.
- [x] Encrypted credentials storage.
- [x] Keitaro implementation (stub-grade; `test_connection`/`fetch_campaigns`/`fetch_metrics` not production-ready).
- [x] Sync scheduling (Celery beat).
- [x] Connector API endpoints & DB models.
- [x] Tenant isolation and persistence testing.
- [x] Production Smoke Test.
- [x] Shared rate-limit/retry/backoff policy (`with_retry`).
- [x] Binom integration.
- [x] Voluum integration.
- [x] Affise integration.
- [x] Meta Ads integration (hardened: pagination, secret stripping, ad accounts).
- [x] `ad_accounts` mapping (Meta only — Binom/Voluum/Affise pending).

**Open (Pending Implementation):**
- [ ] Cross-source conflict resolution / reconciliation.
- [ ] Credential rotation endpoint.
- [ ] Stale-source DQ alert.
- [ ] `CampaignRunStat` soft delete.
- [ ] ECB FX rate auto-fetch.
- [ ] Expanded observability (structured logging, metrics).
- [ ] Google Ads integration.
- [ ] TikTok Ads integration.
- [ ] Production validation with real API credentials.

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
