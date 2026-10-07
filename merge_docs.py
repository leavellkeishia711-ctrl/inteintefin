import subprocess
import sys

def run(cmd):
    print(f"> {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"Command failed with code {res.returncode}")
        sys.exit(res.returncode)

run("git checkout main")
run("git pull --ff-only")
run("git merge --squash feat/docs-fix-stage2-facts")
run('git commit -m "docs: correct Stage 2 status facts against code"')
run("git push origin main")
