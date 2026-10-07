import urllib.request
import json
for run_id in ['37280619697', '37280619642', '37280619568']:
    try:
        url = f'https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs/{run_id}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            print(f"{run_id} | {data['name']} | {data['conclusion']}")
    except Exception as e:
        print(f"{run_id} Error: {e}")
