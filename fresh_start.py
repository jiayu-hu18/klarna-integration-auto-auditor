#!/usr/bin/env python3
"""
Create a fresh git history without any secrets
"""
import subprocess
import os
import sys

PROJECT_DIR = "/Users/jiayu.hu/Documents/Cursor/klarna-integration-auto-auditor"
USERNAME = "jiayu-hu18"
REPO_NAME = "klarna-integration-auto-auditor"

os.chdir(PROJECT_DIR)

print("="*60)
print("Creating Fresh Git History (No Secrets)")
print("="*60)

print("\nStep 1: Removing old git history...")
# Remove .git directory to start fresh
import shutil
if os.path.exists(".git"):
    shutil.rmtree(".git")
    print("✓ Old git history removed")

print("\nStep 2: Initializing new git repository...")
subprocess.run(["git", "init"], check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("✓ New git repository initialized")

print("\nStep 3: Adding files (excluding sensitive ones)...")
# Add all files except the ones in .gitignore
subprocess.run(["git", "add", "."], check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("✓ Files added")

print("\nStep 4: Creating initial commit...")
subprocess.run(["git", "commit", "-m", "Initial commit: Klarna Integration Auto Auditor"], 
              check=True, cwd=PROJECT_DIR, 
              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("✓ Initial commit created")

print("\nStep 5: Setting up remote...")
remote_url = f"https://github.com/{USERNAME}/{REPO_NAME}.git"
subprocess.run(["git", "remote", "add", "origin", remote_url], 
               check=True, cwd=PROJECT_DIR, 
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("✓ Remote configured")

print("\nStep 6: Pushing to GitHub...")
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
    print("\nNote: If you see authentication prompts, use your GitHub")
    print("Personal Access Token as the password.")
    print("="*60)
else:
    print("\n" + "="*60)
    print("Push output:")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("Error:")
        print(result.stderr)
    print("\nYou may need to authenticate.")
    print("Run manually: git push -u origin main --force")
    print("When prompted for password, use your GitHub token")
    print("="*60)
