# Live Connector Validation Runbook

This document describes how to manually validate that Google Ads and TikTok Ads data connectors are fully functional in the production environment (i.e. they authenticate successfully with real API credentials, fetch metrics without errors, and parse responses according to the expected schema).

> [!WARNING]
> This is a manual opt-in validation, NOT a CI/CD process. NEVER run these validation tests within GitHub Actions with real credentials, and NEVER commit your secrets.

## 1. Prerequisites

### Google Ads
To run a live validation, you must manually obtain the following from your Google Ads developer account:
- `GOOGLE_ADS_DEVELOPER_TOKEN` (approved token)
- `GOOGLE_ADS_CLIENT_ID` (OAuth2 client ID)
- `GOOGLE_ADS_CLIENT_SECRET` (OAuth2 client secret)
- `GOOGLE_ADS_REFRESH_TOKEN` (acquired via OAuth flow)
- `GOOGLE_ADS_CUSTOMER_ID` (target client account ID, without dashes)
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (optional, the manager account ID if authenticating via an MCC)

### TikTok Ads
To run a live validation, you must manually obtain the following from your TikTok Developer app:
- `TIKTOK_ACCESS_TOKEN` (long-lived access token, authorized for reading ads)
- `TIKTOK_ADVERTISER_ID` (the specific ad account ID to query)
- Approved App scopes for Ads reading (`ad.account.read`, `ad.campaign.read`, `ad.report.read`)

## 2. Setting Up Environment Variables Safely

Do not put these in the tracked `.env` file and **do not commit them**. You can export them directly in your shell or use a `.env.local` file that is in `.gitignore`.

**Example (Linux/macOS):**
```bash
export LIVE_CONNECTOR_VALIDATION=1
export GOOGLE_ADS_DEVELOPER_TOKEN="your_token_here"
export GOOGLE_ADS_CLIENT_ID="your_client_id"
export GOOGLE_ADS_CLIENT_SECRET="your_client_secret"
export GOOGLE_ADS_REFRESH_TOKEN="your_refresh_token"
export GOOGLE_ADS_CUSTOMER_ID="1234567890"

export TIKTOK_ACCESS_TOKEN="your_tiktok_token"
export TIKTOK_ADVERTISER_ID="your_advertiser_id"
```

## 3. Running the Validation

Once variables are set, run the validation script from the `04-backend` directory:

```bash
# Validate Google Ads
python scripts/validate_live_connectors.py --platform google_ads

# Validate TikTok Ads
python scripts/validate_live_connectors.py --platform tiktok_ads
```

## 4. Reading the Output

If the integration is fully functional, the script will exit with code `0` and output a sanitized JSON payload:
```json
{"platform": "google_ads", "customer_id": "123***90", "currency": "USD", "date_range": "2026-09-15", "rows_fetched": 3, "status": "pass"}
```

If the validation fails, it will output the error and exit with code `1`:
```json
{"platform": "google_ads", "status": "fail", "error": "UnauthorizedError", "message": "OAuth Failed"}
```

## 5. Troubleshooting Common Errors

- **401/403 (UnauthorizedError):**
  - Google: Your refresh token might be expired, the OAuth client might not have the correct scopes, or the developer token is not approved. Check `login_customer_id` if using an MCC.
  - TikTok: Ensure the advertiser ID has been authorized by the app, and that the token hasn't expired.
- **Empty Report / rows_fetched = 0:**
  - The API connection is valid (pass), but no spend occurred on the specified date (`yesterday` UTC).
- **Rate Limits (429):**
  - The script employs exponential backoff. If it ultimately fails, wait 15 minutes before running the check again.
- **ValueError / Type mismatches:**
  - If a metric (e.g., spend, conversions) comes back in a new format or contains unexpected characters/negatives. 

## 6. Security & Credential Revocation

1. **DO NOT** send your secrets or API tokens to Gemini or any other AI assistant.
2. **DO NOT** paste error traces into GitHub issues or pull requests without thoroughly checking for embedded tokens.
3. **DO NOT** commit your `.env` or any debug files.
4. **DO NOT** publish the raw API responses.

Once your validation is successfully completed in production, you should rotate/revoke the tokens you used for manual testing or securely save them to the production Vault/Secrets Manager.