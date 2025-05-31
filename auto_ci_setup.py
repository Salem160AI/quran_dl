#!/usr/bin/env python3
"""
auto_ci_setup.py - Complete CI/CD Automation for Quran Downloader

This script automates:
1. Checking/installing Git
2. Creating GitHub repository
3. Setting up CI/CD workflow
4. Configuring local Git repository
5. Pushing to GitHub
"""

import os
import sys
import subprocess
import webbrowser
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# Configuration
GITHUB_API = "https://api.github.com"
WORKFLOW_CONTENT = """name: Quran Downloader Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10']
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: |
        python -m pytest --cov=./ --cov-report=xml -v
    - name: Upload coverage
      uses: codecov/codecov-action@v1
"""

REQUIREMENTS = """requests==2.31.0
tqdm==4.66.1
python-dotenv==1.0.0
pytest==7.4.0
pytest-cov==4.1.0
"""

def run_command(cmd, check=True):
    """Run shell command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e.stderr.strip()}")
        return None

def install_git():
    """Guide through Git installation"""
    print("\n🔧 Git is required but not found. Let's install it:")
    git_url = "https://git-scm.com/download/win"
    print(f"1. Download Git from: {git_url}")
    print("2. Run the installer with these options:")
    print("   - Select 'Use Git from the Windows Command Prompt'")
    print("   - Check 'Add Git to PATH'")
    
    webbrowser.open(git_url)
    input("\nPress Enter after Git installation completes...")
    
    # Verify installation
    if run_command("git --version"):
        print("✅ Git successfully installed")
        return True
    print("❌ Git installation failed")
    return False

def create_github_repo(token, repo_name):
    """Create GitHub repository using API"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": "Quran Audio Downloader with CI/CD",
        "private": False,
        "auto_init": False
    }
    
    try:
        req = Request(f"{GITHUB_API}/user/repos", 
                     data=json.dumps(data).encode(),
                     headers=headers, method="POST")
        with urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result["clone_url"]
    except URLError as e:
        print(f"❌ Failed to create repository: {e}")
        return None

def setup_ci_files():
    """Create CI/CD configuration files"""
    try:
        # Create workflow directory
        workflow_dir = Path(".github") / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Create workflow file
        with open(workflow_dir / "python-tests.yml", "w") as f:
            f.write(WORKFLOW_CONTENT)
        
        # Create requirements.txt
        with open("requirements.txt", "w") as f:
            f.write(REQUIREMENTS)
        
        print("✅ Created CI/CD configuration files")
        return True
    except Exception as e:
        print(f"❌ Error creating files: {e}")
        return False

def main():
    print("\n🚀 Quran Downloader CI/CD Auto-Setup\n")
    
    # 1. Check Git installation
    if not run_command("git --version", check=False):
        if not install_git():
            sys.exit(1)
    
    # 2. Get GitHub credentials
    print("\n🔑 GitHub Setup:")
    print("1. Create a Personal Access Token (PAT) with 'repo' scope")
    print("   at: https://github.com/settings/tokens")
    print("2. We'll use this to create your repository")
    
    token = input("\nEnter GitHub PAT: ").strip()
    repo_name = input("Repository name (e.g., Quran_dl): ").strip() or "Quran_dl"
    
    # 3. Create GitHub repository
    print("\n🛠 Creating GitHub repository...")
    repo_url = create_github_repo(token, repo_name)
    if not repo_url:
        sys.exit(1)
    print(f"✅ Created repository: {repo_url}")
    
    # 4. Set up local files
    if not setup_ci_files():
        sys.exit(1)
    
    # 5. Initialize and push to GitHub
    print("\n💾 Configuring local repository...")
    commands = [
        "git init",
        "git add .",
        'git commit -m "Initial commit with CI/CD"',
        f"git remote add origin {repo_url}",
        "git push -u origin main"
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            print(f"❌ Failed to run: {cmd}")
            sys.exit(1)
    
    print("\n🎉 Successfully set up CI/CD pipeline!")
    print(f"Visit your repository: {repo_url.replace('.git', '')}/actions")
    print("Your tests will run automatically on push")

if __name__ == "__main__":
    main()