import urllib.request, json, sys, time
url = "https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs?head_sha=f6ed67bd10c97700c105776fbf81f0660ccbd379"
req = urllib.request.Request(url)
req.add_header("Accept", "application/vnd.github.v3+json")

def check():
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        runs = data.get("workflow_runs", [])
        if not runs:
            print("No runs found yet...")
            return False
        
        all_done = True
        for run in runs:
            print(f"ID: {run['id']}, Name: {run['name']}, Status: {run['status']}, Conclusion: {run['conclusion']}, HTML: {run['html_url']}")
            if run['status'] != 'completed':
                all_done = False
        return all_done

print("Initial check:")
if not check():
    print("Waiting for runs to complete...")
