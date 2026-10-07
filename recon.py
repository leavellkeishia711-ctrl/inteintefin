import subprocess
import time
from datetime import datetime

def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"cmd": cmd, "stdout": res.stdout, "stderr": res.stderr, "rc": res.returncode}

print(f"Time: {datetime.now().astimezone().isoformat()}")

print("\n--- ls-remote 1 ---")
print(run_cmd("git ls-remote origin refs/heads/main refs/heads/feat/docs-refine-meta-ssrf-risk"))
time.sleep(10)
print("\n--- ls-remote 2 ---")
print(run_cmd("git ls-remote origin refs/heads/main refs/heads/feat/docs-refine-meta-ssrf-risk"))
time.sleep(10)
print("\n--- ls-remote 3 ---")
print(run_cmd("git ls-remote origin refs/heads/main refs/heads/feat/docs-refine-meta-ssrf-risk"))

print("\n--- Fetch ---")
print(run_cmd("git fetch origin main feat/docs-refine-meta-ssrf-risk"))

print("\n--- rev-parse ---")
print("main:", run_cmd("git rev-parse origin/main")['stdout'].strip())
print("docs:", run_cmd("git rev-parse origin/feat/docs-refine-meta-ssrf-risk")['stdout'].strip())

print("\n--- log ---")
print(run_cmd("git log --oneline --decorate -10 origin/main")['stdout'])

print("\n--- status ---")
print(run_cmd("git status --short --branch")['stdout'])
