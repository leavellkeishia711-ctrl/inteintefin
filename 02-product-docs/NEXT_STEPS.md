# Next Steps

**Current Task:**
Review documentation reconciliation PR.

**Upcoming PR:**
`feat/stage2-binom-connector`

**Connector Order:**
1. Binom
2. Voluum
3. Affise
4. Meta Ads
5. Google Ads
6. TikTok Ads

**Acceptance Criteria for Connectors:**
- Idempotent upserts.
- Decimal metric conversions.
- Tenant isolation verified.
- Generic backoff/retry correctly integrated.

**Testing Strategy:**
- Integration tests simulating HTTP 429 and 500 scenarios for each provider.
- DB persistence testing checking duplicate sync deduplication.

**Security Rules:**
- DO NOT expose credentials in logs.
- Rotate functionality must be supported.
- Credentials read from protected runtime only.

**CI Requirements:**
- Must pass `check_floats.py` unconditionally.
- Standard backend tests, frontend tests, prod-gate deployment tests.

**PROHIBITED ACTIONS NOW:**
Do not start Binom, Voluum, Affise, Meta Ads, Google Ads or TikTok Ads implementation in this documentation task.
