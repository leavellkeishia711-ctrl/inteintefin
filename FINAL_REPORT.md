## FINAL REPORT

### 1. Read-only Audit & TikTok API Contract Verification
- **API Base:** `https://business-api.tiktok.com/open_api/v1.3`
- **Authentication:** Requires an `Access-Token` header.
- **Initialization:** Most endpoints require `advertiser_id`.
- **Advertiser Account Endpoint:** `GET /advertiser/info/` with `advertiser_ids=["<id>"]`. It returns `currency`, `name`, and `advertiser_id`.
- **Campaign Endpoint:** `GET /campaign/get/` providing `campaign_id` and `campaign_name`.
- **Reporting Endpoint:** `GET /report/integrated/get/` at `AUCTION_CAMPAIGN` level. Metrics available include `spend` and `total_purchase_value` (mapped to revenue).
- **Pagination:** Uses `page` and `page_size` query parameters, and responds with `page_info: {total_page}`.

### 2. Implementation details
- **File scope:** Added `app/connectors/tiktok_ads.py` and `tests/test_tiktok_ads_connector.py`. Updated `app/connectors/scheduler.py` to register the connector and `STAGE2_STATUS.md` to reflect completion.
- **Credentials:** The TikTok Connector uses the existing `ConnectorConfig.encrypted_secret`. The decrypted secret is expected to be a JSON string formatted as `{"access_token": "...", "advertiser_id": "..."}`.
- **Normalization:** `total_purchase_value` is mapped to `revenue`. `spend` is parsed to `Decimal`. The `stat_date` is parsed from `stat_time_day`. Both use `campaign_id` as `external_id`.
- **Tests:** All 13 requested test cases were successfully implemented in `test_tiktok_ads_connector.py`, covering validation, HTTP failure handling, network-free parsing, atomic upsert, and tenant isolation tests. The tests run completely offline.

### 3. Explicit Confirmation
- Yes, I have rigorously verified that zero float values are passed into any money fields (`spend`, `revenue`). 
- Yes, the persistence completely matches the existing `upsert_campaign_run_stat_atomic` approach used by Meta Ads and Binom.

The code has been committed to `feat/stage2-tiktok-ads-connector` and pushed to remote!
