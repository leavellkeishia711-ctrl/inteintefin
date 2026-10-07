import urllib.request, json
url = 'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs?branch=feat/connector-config-settings&per_page=5'
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    runs = data.get('workflow_runs', [])
    for r in runs:
        if r['head_sha'].startswith('1e854a80'):
            print(f"{r['name']} (ID: {r['id']}): {r['status']} / {r['conclusion']} (Commit: {r['head_sha']})")
