#!/usr/bin/env python3
"""
ci_setup.py - Automated CI/CD Setup for Quran Downloader

This script automates:
1. Creating GitHub Actions workflow directory
2. Generating workflow YAML file
3. Creating requirements.txt
4. Initializing Git repository (if needed)
5. Committing and pushing changes
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
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
    
    - name: Cache pip packages
      uses: actions/cache@v2
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest-cov
    
    - name: Run tests
      run: |
        python -m pytest --cov=./ --cov-report=xml -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
    
    - name: Run security check
      run: |
        pip install safety
        safety check
"""

REQUIREMENTS = """requests==2.31.0
tqdm==4.66.1
python-dotenv==1.0.0
pytest==7.4.0
pytest-cov==4.1.0
"""

def create_ci_files():
    """Create CI/CD configuration files"""
    try:
        # Create .github/workflows directory
        workflow_dir = Path(".github/workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {workflow_dir}")

        # Create workflow file
        workflow_file = workflow_dir / "python-tests.yml"
        with open(workflow_file, "w") as f:
            f.write(WORKFLOW_CONTENT)
        print(f"✅ Created workflow file: {workflow_file}")

        # Create requirements.txt
        with open("requirements.txt", "w") as f:
            f.write(REQUIREMENTS)
        print("✅ Created requirements.txt")

        return True
    except Exception as e:
        print(f"❌ Error creating CI files: {e}")
        return False

def setup_git():
    """Initialize Git repository and commit changes"""
    try:
        # Check if Git is installed
        subprocess.run(["git", "--version"], check=True, capture_output=True)

        # Initialize repository if needed
        if not Path(".git").exists():
            subprocess.run(["git", "init"], check=True)
            print("✅ Initialized Git repository")

        # Add and commit files
        subprocess.run(["git", "add", ".github/workflows/python-tests.yml", "requirements.txt"], check=True)
        subprocess.run(["git", "commit", "-m", "Add CI/CD automation"], check=True)
        print("✅ Committed CI/CD files")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e.stderr.decode().strip()}")
        return False
    except Exception as e:
        print(f"❌ Error setting up Git: {e}")
        return False

def main():
    print("\n🚀 Starting CI/CD Automation Setup for Quran Downloader\n")
    
    # Step 1: Create CI files
    if not create_ci_files():
        print("\n❌ Failed to create CI files. Exiting.")
        sys.exit(1)
    
    # Step 2: Set up Git
    print("\n🔧 Setting up Git repository...")
    if not setup_git():
        print("\n⚠️ Git setup completed with warnings. CI files were created but not committed.")
    
    # Final instructions
    print("\n🎉 CI/CD Setup Complete! Next steps:")
    print("1. Create a GitHub repository if you haven't already")
    print("2. Add your remote origin: git remote add origin <your-repo-url>")
    print("3. Push your changes: git push -u origin main")
    print("4. Check the Actions tab in GitHub to see your workflow run\n")

if __name__ == "__main__":
    main()