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

LIVE_CONNECTOR_VALIDATION=1
```
*(Google Ads API version is automatically read from `settings.GOOGLE_ADS_API_VERSION`, but you can override via `--api-version` if testing.)*

3. Run the validation harness:
```bash
python scripts/validate_live_connectors.py --platform google_ads
python scripts/validate_live_connectors.py --platform tiktok_ads
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