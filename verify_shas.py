import subprocess
import time
import urllib.request
import json
from datetime import datetime, timezone

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "stdout": res.stdout,
        "stderr": res.stderr,
        "rc": res.returncode
    }

def get_api(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        t = datetime.now().astimezone().isoformat()
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {"url": url, "data": data, "time": t, "status": response.getcode()}
    except urllib.error.URLError as e:
        t = datetime.now().astimezone().isoformat()
        return {"url": url, "error": str(e), "time": t}

print(f"Current local time: {datetime.now().astimezone().isoformat()}")

print("\n--- 1. Git ls-remote Run 1 ---")
print(run_cmd("git ls-remote origin refs/heads/main"))
time.sleep(10)
print("\n--- 2. Git ls-remote Run 2 ---")
print(run_cmd("git ls-remote origin refs/heads/main"))
time.sleep(10)
print("\n--- 3. Git ls-remote Run 3 ---")
print(run_cmd("git ls-remote origin refs/heads/main"))

print("\n--- 4. Git Fetch ---")
print(run_cmd("git fetch origin main"))

print("\n--- 5. Git Rev-Parse ---")
print(run_cmd("git rev-parse origin/main"))

print("\n--- 6. Git Log ---")
print(run_cmd("git log --oneline --decorate -10 origin/main"))

print("\n--- 7. Git Status ---")
print(run_cmd("git status --short --branch"))

print("\n--- 8. GitHub API refs/heads/main ---")
api_ref_main = get_api("https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/git/refs/heads/main")
print(api_ref_main.get("data", {}).get("object", {}).get("sha", api_ref_main.get("error")))

print("\n--- 9. GitHub API commits/main ---")
api_commits_main = get_api("https://api.github.com/repos/leavellkeishia711-ctrl/inteintefin/commits/main")
print(api_commits_main.get("data", {}).get("sha", api_commits_main.get("error")))

print("\n--- 10. Ancestry ---")
ancestry = run_cmd("git merge-base --is-ancestor e4c273ba82661f40e3a1f380cea93ab0fc0affd6 origin/main")
print("Is ancestor:", ancestry['rc'] == 0)
print("Difference:")
print(run_cmd("git log --oneline e4c273ba82661f40e3a1f380cea93ab0fc0affd6..origin/main")['stdout'])
