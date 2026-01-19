#!/usr/bin/env python3
"""
Clean git history and push to GitHub
This script removes sensitive files from git history
"""
import subprocess
import os
import sys

PROJECT_DIR = "/Users/jiayu.hu/Documents/Cursor/klarna-integration-auto-auditor"
USERNAME = "jiayu-hu18"
REPO_NAME = "klarna-integration-auto-auditor"

os.chdir(PROJECT_DIR)

print("="*60)
print("Cleaning Git History and Pushing to GitHub")
print("="*60)

# Files that contain secrets and should be removed from history
secret_files = [
    "fix_repo.py",
    "push_alternative.py",
    "fix_deploy.py",
    "push_fix.py",
    "run_deploy.py",
    "execute_deploy.py",
    "deploy.sh",
    "DEPLOY_INSTRUCTIONS.md",
    "setup_github.py",
    "setup_github_simple.sh",
    "deploy_to_github.py"
]

print("\nStep 1: Removing sensitive files from git history...")
print("This will rewrite git history to remove secrets.")

# Check if files exist in git history
for file in secret_files:
    result = subprocess.run(
        ["git", "log", "--all", "--full-history", "--", file],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(f"  Found {file} in git history, removing...")
        # Remove file from all commits
        subprocess.run(
            ["git", "filter-branch", "--force", "--index-filter", 
             f"git rm --cached --ignore-unmatch {file}",
             "--prune-empty", "--tag-name-filter", "cat", "--", "--all"],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

print("\nStep 2: Cleaning up...")
# Clean up refs
subprocess.run(["git", "for-each-ref", "--format", "delete %(refname)", "refs/original"],
              cwd=PROJECT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"],
              cwd=PROJECT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["git", "gc", "--prune=now", "--aggressive"],
              cwd=PROJECT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("✓ Git history cleaned")

print("\nStep 3: Ensuring all current files are committed...")
subprocess.run(["git", "add", "."], check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

result = subprocess.run(["git", "diff", "--cached", "--quiet"], 
                       check=False, cwd=PROJECT_DIR)
if result.returncode != 0:
    subprocess.run(["git", "commit", "-m", "Remove sensitive files and clean git history"], 
                  check=True, cwd=PROJECT_DIR, 
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✓ Changes committed")

print("\nStep 4: Setting up remote...")
# Remove and re-add remote (without token in URL)
remote_url = f"https://github.com/{USERNAME}/{REPO_NAME}.git"
subprocess.run(["git", "remote", "remove", "origin"], 
               check=False, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(["git", "remote", "add", "origin", remote_url], 
               check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("✓ Remote configured (without token)")

print("\nStep 5: Pushing to GitHub...")
print("You will need to authenticate when pushing.")
print("Use your GitHub token when prompted for password.")

subprocess.run(["git", "branch", "-M", "main"], 
               check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

result = subprocess.run(["git", "push", "-u", "origin", "main", "--force"], 
                       check=False, cwd=PROJECT_DIR, 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("\n" + "="*60)
    print("✓ SUCCESS! Code pushed to GitHub!")
    print("="*60)
    print(f"Repository: https://github.com/{USERNAME}/{REPO_NAME}")
    print("="*60)
else:
    print("\n" + "="*60)
    print("Push output:")
    print(result.stdout)
    if result.stderr:
        print("Error:")
        print(result.stderr)
    print("\nIf authentication is needed, use your GitHub token as password")
    print("Or run: git push -u origin main --force")
    print("="*60)
