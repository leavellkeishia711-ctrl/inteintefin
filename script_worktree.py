import os
import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    return result.returncode

os.chdir("c:\\Users\\fylht\\Desktop\\Стартапы\\SaaS финансовый менеджмент для медиабаинговых компаний")

# Ensure worktree is there
run("git worktree remove ../pr-a-main --force")
run("git worktree add ../pr-a-main 2d01c4c5")

# Copy test file
import shutil
shutil.copy2("04-backend/tests/test_pr_a_data_integrity.py", "../pr-a-main/04-backend/tests/test_pr_a_data_integrity.py")

# Mock env
shutil.copy2("08-devops/.env.example", "../pr-a-main/04-backend/.env")

# Run tests 1, 3, 6
os.chdir("../pr-a-main/04-backend")
run("python -m pytest tests/test_pr_a_data_integrity.py::test_tiktok_upsert_fx_signature -v")
run("python -m pytest tests/test_pr_a_data_integrity.py::test_sync_rollback_on_fx_error -v")
run("python -m pytest tests/test_pr_a_data_integrity.py::test_meta_fetch_uses_explicit_daily_range -v")

# cleanup
os.chdir("c:\\Users\\fylht\\Desktop\\Стартапы\\SaaS финансовый менеджмент для медиабаинговых компаний")
run("git worktree remove ../pr-a-main --force")
