import urllib.request, json
url = 'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs/37290899254/artifacts'
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for a in data.get('artifacts', []):
            print(f"Artifact: {a['name']} (ID: {a['id']})")
except Exception as e:
    print(e)
