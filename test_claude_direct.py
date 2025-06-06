#!/usr/bin/env python3
"""
Direct Claude execution test script
Tests Claude code generation in DevPod without web interface
"""

import subprocess
import json
import time
import sys

# Configuration
DEVPOD_NAME = "auto-worker-demo"
GITHUB_REPO = "justinbuzzni/auto-worker-demo"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
TASK_DESCRIPTION = "streamlit으로 문자열을 입력 받으면 그 결과를 화면에 출력해주는 demo web"

DEVPOD_PATH = '/Users/namsangboy/.local/bin/devpod'

def run_command(command, capture=True):
    """Run a shell command and return the result"""
    print(f"\n🔧 Running: {command}")
    if capture:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"⚠️  Error: {result.stderr[:200]}...")
        return result
    else:
        return subprocess.run(command, shell=True)

def get_pod_name(devpod_name):
    """Get the kubernetes pod name for the devpod"""
    print(f"\n🔍 Getting pod name for {devpod_name}...")
    
    # Try different methods to find the pod
    commands = [
        f"kubectl get pods -n devpod -l devpod.sh/workspace={devpod_name} -o jsonpath='{{.items[0].metadata.name}}'",
        f"kubectl get pods -n devpod | grep -E 'devpod-{devpod_name[:10]}' | awk '{{print $1}}' | head -1",
        f"kubectl get pods -n devpod | grep -i '{devpod_name.replace('-', '')[:10]}' | awk '{{print $1}}' | head -1"
    ]
    
    for cmd in commands:
        result = run_command(cmd)
        if result.stdout.strip():
            pod_name = result.stdout.strip()
            print(f"✅ Found pod: {pod_name}")
            return pod_name
    
    # List all pods if not found
    print("\n❌ Pod not found. Available pods:")
    run_command("kubectl get pods -n devpod")
    raise Exception(f"Pod not found for devpod {devpod_name}")

def exec_in_devpod(devpod_name, command, pod_name=None):
    """Execute command in devpod"""
    if not pod_name:
        pod_name = get_pod_name(devpod_name)
    
    escaped_cmd = command.replace("'", "'\"'\"'")
    kubectl_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c '{escaped_cmd}'"
    return run_command(kubectl_cmd)

def main():
    print("🚀 Starting Claude Direct Execution Test")
    print("=" * 60)
    
    # Step 1: Ensure DevPod exists and is running
    print("\n📦 Step 1: Checking DevPod...")
    result = run_command(f"{DEVPOD_PATH} list")
    
    if DEVPOD_NAME not in result.stdout:
        print(f"Creating new DevPod: {DEVPOD_NAME}")
        run_command(f"{DEVPOD_PATH} up --provider kubernetes {DEVPOD_NAME}")
    else:
        print(f"DevPod {DEVPOD_NAME} already exists")
    
    # Get pod name
    pod_name = get_pod_name(DEVPOD_NAME)
    
    # Step 2: Clone or update repository
    print(f"\n📚 Step 2: Setting up repository...")
    repo_name = GITHUB_REPO.split('/')[-1]
    
    # Configure git
    exec_in_devpod(DEVPOD_NAME, 'git config --global user.name "Auto Worker"', pod_name)
    exec_in_devpod(DEVPOD_NAME, 'git config --global user.email "auto-worker@example.com"', pod_name)
    
    # Check if repo exists
    check_result = exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && pwd', pod_name)
    
    if check_result.returncode != 0:
        print("Cloning repository...")
        exec_in_devpod(DEVPOD_NAME, f'cd ~ && git clone https://github.com/{GITHUB_REPO}.git', pod_name)
    else:
        print("Repository exists, pulling latest...")
        exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && git pull', pod_name)
    
    # Step 3: Install Node.js and Claude
    print("\n🔧 Step 3: Installing dependencies...")
    
    # Check Node.js
    node_check = exec_in_devpod(DEVPOD_NAME, 'which node', pod_name)
    if not node_check.stdout.strip():
        print("Installing Node.js...")
        exec_in_devpod(DEVPOD_NAME, 'apt-get update && apt-get install -y nodejs npm', pod_name)
    
    # Install Claude
    print("\n📦 Installing Claude Code...")
    exec_in_devpod(DEVPOD_NAME, 'npm install -g @anthropic-ai/claude-code', pod_name)
    
    # Check Claude installation
    claude_check = exec_in_devpod(DEVPOD_NAME, 'which claude', pod_name)
    claude_path = claude_check.stdout.strip()
    print(f"Claude installed at: {claude_path}")
    
    # Step 4: Check Claude authentication
    print("\n🔐 Step 4: Checking Claude authentication...")
    auth_check = exec_in_devpod(DEVPOD_NAME, 'claude --version 2>&1', pod_name)
    
    if "Invalid API key" in auth_check.stdout or "Please run /login" in auth_check.stdout:
        print("\n" + "="*60)
        print("⚠️  CLAUDE AUTHENTICATION REQUIRED!")
        print("="*60)
        print("\nClaude is installed but requires authentication.")
        print("Please follow these steps:\n")
        print(f"1. Open a new terminal")
        print(f"2. Run: kubectl exec -it -n devpod {pod_name} -- bash")
        print(f"3. Inside the container, run: claude")
        print(f"4. Follow the authentication prompts")
        print(f"5. After authentication, type 'exit' to leave the container")
        print(f"6. Press Enter here to continue...")
        print("="*60)
        
        input("\nPress Enter after completing authentication...")
        
        # Verify authentication
        auth_check = exec_in_devpod(DEVPOD_NAME, 'claude --version 2>&1', pod_name)
        if "Invalid API key" in auth_check.stdout or "Please run /login" in auth_check.stdout:
            print("❌ Authentication still required. Please complete the authentication process.")
            return
    
    print("✅ Claude is authenticated!")
    
    # Step 5: Execute Claude task
    print(f"\n🤖 Step 5: Executing Claude task...")
    print(f"Task: {TASK_DESCRIPTION}")
    
    # Create a new branch
    branch_name = f"claude-test-{int(time.time())}"
    exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && git checkout -b {branch_name}', pod_name)
    
    # Execute Claude
    claude_command = f'''cd ~/{repo_name} && claude -p "{TASK_DESCRIPTION}"'''
    
    print("\n🚀 Running Claude...")
    result = exec_in_devpod(DEVPOD_NAME, claude_command, pod_name)
    
    if result.returncode == 0:
        print("\n✅ Claude execution completed successfully!")
        
        # Show created files
        print("\n📄 Files in repository:")
        exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && ls -la', pod_name)
        
        # Show specific files if they exist
        files_to_check = ['app.py', 'main.py', 'streamlit_app.py', 'requirements.txt']
        for file in files_to_check:
            file_check = exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && [ -f {file} ] && echo "EXISTS"', pod_name)
            if "EXISTS" in file_check.stdout:
                print(f"\n📄 Content of {file}:")
                exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && head -20 {file}', pod_name)
        
        # Commit changes
        print("\n💾 Committing changes...")
        exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && git add -A', pod_name)
        exec_in_devpod(DEVPOD_NAME, f'cd ~/{repo_name} && git commit -m "Claude: {TASK_DESCRIPTION}"', pod_name)
        
        print("\n✅ Task completed successfully!")
        print(f"Branch: {branch_name}")
        print("\nYou can now push this branch and create a PR if desired.")
        
    else:
        print("\n❌ Claude execution failed")
        print(f"Error: {result.stderr}")

if __name__ == "__main__":
    main()