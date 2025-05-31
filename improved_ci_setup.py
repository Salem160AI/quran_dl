#!/usr/bin/env python3
"""
improved_ci_setup.py - More Robust CI/CD Setup
"""

import os
import sys
import subprocess
import webbrowser
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# Configuration [keep existing config...]

def check_git_installed():
    """Check if Git is properly installed and in PATH"""
    try:
        result = subprocess.run(["git", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_git():
    """Guided Git installation with better feedback"""
    print("\n🔧 Git installation required:")
    git_url = "https://git-scm.com/download/win"
    print(f"1. Download from: {git_url}")
    print("2. Run installer with THESE options:")
    print("   - Select 'Use Git from Windows Command Prompt'")
    print("   - Check 'Add Git to PATH'")
    print("3. RESTART your Command Prompt after installation")
    
    webbrowser.open(git_url)
    input("\nPress Enter AFTER installation completes...")
    
    if not check_git_installed():
        print("\n❌ Git still not detected. Please:")
        print("- Restart Command Prompt")
        print("- Or add Git to PATH manually")
        return False
    return True

def setup_local_repo():
    """More robust Git repository setup"""
    commands = [
        ["git", "init"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Initial commit with CI/CD"]
    ]
    
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ {cmd[0]} completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run: {' '.join(cmd)}")
            print(f"Error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False
    return True

def main():
    print("\n🚀 Improved CI/CD Setup for Quran Downloader\n")
    
    # 1. Verify Git
    if not check_git_installed():
        if not install_git():
            sys.exit(1)
    
    # [Rest of your existing main() function...]
    # Replace the git commands section with:
    print("\n💾 Configuring local repository...")
    if not setup_local_repo():
        print("\n⚠️ Manual steps required:")
        print("1. Initialize Git manually:")
        print("   git init")
        print("2. Add files:")
        print("   git add .")
        print("3. Commit:")
        print('   git commit -m "Initial commit"')
        print("4. Push:")
        print(f"   git remote add origin {repo_url}")
        print("   git push -u origin main")
        sys.exit(1)
    
    # Continue with push commands...

if __name__ == "__main__":
    main()