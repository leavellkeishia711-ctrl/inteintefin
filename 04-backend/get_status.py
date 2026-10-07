import urllib.request, json
url = 'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs?branch=feat/csv-import-e2e&event=push'
req = urllib.request.Request(url)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    runs = data.get('workflow_runs', [])
    for r in runs[:3]:
        print(r['name'], r['status'], r['conclusion'], r['head_sha'])
except Exception as e:
    print('Error:', e)
