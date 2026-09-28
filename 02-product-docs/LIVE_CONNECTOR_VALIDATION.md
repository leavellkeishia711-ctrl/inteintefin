# Live Connector Validation Runbook

## Security Warning
- **DO NOT** commit `.env` or `.env.local` to version control.
- **DO NOT** paste real access tokens in Gemini chat or GitHub PRs.
- **DO NOT** save raw JSON API payloads containing personal or financial tokens.
- **NEVER** pass secrets through `sys.argv`.

## How to Run

1. Create `04-backend/.env.local` (this is ignored by Git, double-check your `.gitignore`)
2. Fill it with your real credentials:
```env
GOOGLE_ADS_DEVELOPER_TOKEN=your-token
GOOGLE_ADS_CLIENT_ID=your-id
GOOGLE_ADS_CLIENT_SECRET=your-secret
GOOGLE_ADS_REFRESH_TOKEN=your-refresh
GOOGLE_ADS_CUSTOMER_ID=your-customer
GOOGLE_ADS_LOGIN_CUSTOMER_ID=optional-mcc-id

TIKTOK_ACCESS_TOKEN=your-token
TIKTOK_ADVERTISER_ID=your-adv-id

META_ACCESS_TOKEN=your-token
META_AD_ACCOUNT_ID=your-adv-id
META_API_VERSION=v26.0

BINOM_BASE_URL=https://your-tracker.com
BINOM_API_KEY=your-api-key
BINOM_CURRENCY=USD

LIVE_CONNECTOR_VALIDATION=1
```
*(Google Ads API version is automatically read from `settings.GOOGLE_ADS_API_VERSION`, but you can override via `--api-version` if testing.)*

3. Run the validation harness:
```bash
python scripts/validate_live_connectors.py --platform google_ads
python scripts/validate_live_connectors.py --platform tiktok_ads
python scripts/validate_live_connectors.py --platform meta_ads
python scripts/validate_live_connectors.py --platform binom
```

## Production Harness Value
This harness imports and exercises the **production connector classes** (`GoogleAdsConnector` and `TikTokAdsConnector`). It simulates the exact code path used in production, injecting credentials via JSON as expected by the Fernet decryption layer.

## Error Taxonomy & Exit Codes
The script returns exit code `0` ONLY on pass or `empty_result`. Any failure returns `1`.
- `invalid_credentials` -> Authentication failed (401/403)
- `insufficient_permission` -> Auth OK, but lack read permissions (e.g., Google CUSTOMER_NOT_ENABLED)
- `developer_token_not_approved` -> Google Developer Token not approved
- `rate_limited` -> 429 after retries
- `malformed_response` -> Missing required fields
- `schema_mismatch` -> Data type errors (e.g. unexpected floats, missing currency)
- `unsupported_api_version` -> Google Ads v16 sunset or version error
- `network_failure` -> Connection drop
- `empty_result` -> Auth OK, but no metrics for the requested date

## Token Rotation
- **Google Ads**: Revoke refresh token via Google Cloud Console or regenerate developer token.
- **TikTok Ads**: Revoke App authorization or regenerate access token via TikTok Dev Portal.

*Note: A green CI run does NOT mean production validation passed. Real validation requires a manual run by the product owner with their credentials.*
## Validation Log
| Date | Platform | Account Type | Access Mode | Status | Stages Passed | Schema Validated | Notes |
|---|---|---|---|---|---|---|---|
| 2026-09-28 | Google Ads | Test Manager -> Test Client | cloud_managed | empty_result | token_refresh, list_accessible_customers, customer_query, campaigns | false | Live auth path validated on test account, no metrics/spend available. |

## Google Ads: Path to Full Validation
To complete validation for Google Ads on production data, perform the following steps:
1. **Apply for Explorer Access**: Navigate to Google Cloud Console → Google Ads API page → apply for Explorer access.
2. **Production Account**: Obtain access to a production Google Ads account with non-zero spend on the target date.
3. **Refresh Token**: Generate an OAuth refresh token from a Google account (Gmail) that has access to this production ad account.
4. **Final Run**: Rerun the live validation harness WITHOUT the `--allow-empty` flag. The expected outcome is `status=pass` and `schema_validated=true`.

### Test Account Features (Google Ads)
The harness is equipped with specialized behavior for Google Ads Test Accounts:
- **GAQL Test Account Check:** A read-only query is executed during validation (`SELECT customer.id, customer.test_account, customer.currency_code FROM customer LIMIT 1`) to determine if the customer ID points to a test account. The `is_test_account` flag is injected into the JSON output.
- **Empty Metrics Bypass:** If `is_test_account` is `true` and the account returns no metrics (because test accounts cannot accrue real ad spend), the harness gracefully handles this by returning `empty_result` with `auth_path_validated=true` and an exit code of `0` even without `--allow-empty`.
- **Production Safety:** For non-test accounts (production), returning no metrics correctly causes the harness to exit with code `2` unless `--allow-empty` is specified.
- **Hints for Missing Approvals:** If the Google Ads API rejects the query due to lack of Explorer Access (`CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` or `ACTION_NOT_PERMITTED`), the script outputs a clear hint to apply for Explorer Access or use a Test Account.
- **Developer Token Masking:** If a `GOOGLE_ADS_DEVELOPER_TOKEN` is supplied, its presence is logged as a warning, and its value is strictly masked. Init errors will also mask exception text and tracebacks to prevent token leakage.
