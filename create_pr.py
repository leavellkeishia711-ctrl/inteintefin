import os
import urllib.request
import json

token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("GITHUB_TOKEN is missing")
    exit(1)

url = "https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/pulls"

req = urllib.request.Request(url, method="POST")
req.add_header("Authorization", f"token {token}")
req.add_header("Accept", "application/vnd.github.v3+json")
req.add_header("Content-Type", "application/json")

data = {
    "title": "feat(connectors): PR-B add validated connector settings",
    "head": "feat/connector-config-settings",
    "base": "main",
    "body": "## What changed\n- Added JSONB settings column to ConnectorConfig.\n- Strict Pydantic models for per-connector validation.\n- Meta: lookback_days only (no arbitrary base_url to prevent SSRF).\n- Google Ads: access_mode.\n- TikTok: empty settings.\n- Excluded settings from ConnectorResponse.\n- Audit log captures keys changed, not raw values."
}

try:
    with urllib.request.urlopen(req, data=json.dumps(data).encode("utf-8")) as response:
        result = json.loads(response.read().decode())
        print(f"PR Created: {result.get('html_url')}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, "read"):
        print(e.read().decode())
