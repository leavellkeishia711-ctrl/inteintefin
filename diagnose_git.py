import subprocess
import time
import urllib.request
import json
from datetime import datetime, timezone

def run_cmd(cmd):
    start = datetime.now().isoformat()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = datetime.now().isoformat()
    return {
        "start": start,
        "end": end,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "rc": res.returncode
    }

def get_api(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        start = datetime.now().isoformat()
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            end = datetime.now().isoformat()
            return {"url": url, "data": data, "start": start, "end": end, "status": response.getcode()}
    except urllib.error.URLError as e:
        end = datetime.now().isoformat()
        return {"url": url, "error": str(e), "start": start, "end": end}

print(f"Current local time script start: {datetime.now().astimezone().isoformat()}")

print("--- 1. Git ls-remote Run 1 ---")
ls_remote_1 = run_cmd("git ls-remote origin refs/heads/main refs/heads/feat/docs-refine-meta-ssrf-risk")
print(json.dumps(ls_remote_1, indent=2))

print("Sleeping 10s...")
time.sleep(10)

print("--- 2. Git ls-remote Run 2 ---")
ls_remote_2 = run_cmd("git ls-remote origin refs/heads/main refs/heads/feat/docs-refine-meta-ssrf-risk")
print(json.dumps(ls_remote_2, indent=2))

print("--- 3. GitHub API refs/heads/main ---")
api_ref_main = get_api("https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/git/refs/heads/main")
print(json.dumps(api_ref_main, indent=2))

print("--- 4. GitHub API refs/heads/feat/docs-refine-meta-ssrf-risk ---")
api_ref_docs = get_api("https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/git/refs/heads/feat/docs-refine-meta-ssrf-risk")
print(json.dumps(api_ref_docs, indent=2))

print("--- 5. GitHub API commits/main ---")
api_commits_main = get_api("https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/commits/main")
print(json.dumps({k: v for k, v in api_commits_main.items() if k != 'data'} | {'data_sha': api_commits_main.get('data', {}).get('sha')}, indent=2))

print("--- 6. Ancestry & Diff ---")
ancestry = run_cmd('git log -1 --format="%P" 0f936cead27d40de6f11e260fe466de1070356a5')
print("Ancestry:", ancestry['stdout'].strip())
diff_stat = run_cmd("git diff --stat e4c273ba82661f40e3a1f380cea93ab0fc0affd6..0f936cead27d40de6f11e260fe466de1070356a5")
print("Diff stat:\n", diff_stat['stdout'])

print("--- 7. CI Runs ---")
for run_id in [37283708528, 37283708530, 37283708531]:
    run_info = get_api(f"https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/actions/runs/{run_id}")
    data = run_info.get("data", {})
    print(f"Run {run_id}: status={data.get('status')}, conclusion={data.get('conclusion')}, head_sha={data.get('head_sha')}, name={data.get('name')}, html_url={data.get('html_url')}")
