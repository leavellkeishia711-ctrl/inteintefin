import urllib.request, json
url = 'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs?branch=docs/google-ads-live-validation-result&per_page=10'
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        runs = data.get('workflow_runs', [])
        for r in runs[:5]:
            print(f"{r['name']} (ID: {r['id']}): {r['status']} / {r['conclusion']} (Commit: {r.get('head_sha')})")
except Exception as e:
    print(e)
