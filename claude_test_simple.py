#!/usr/bin/env python3
"""Simple Claude test script"""

import subprocess
import sys

POD_NAME = "devpod-auto-worke-b056e"
TASK = "streamlit으로 문자열을 입력 받으면 그 결과를 화면에 출력해주는 demo web"

def exec_cmd(cmd):
    """Execute command in pod"""
    full_cmd = f"kubectl exec -n devpod {POD_NAME} -- bash -c '{cmd}'"
    print(f"\n🔧 Running: {cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result

print("🚀 Claude Direct Test")
print("=" * 60)

# Check Claude
print("\n1. Checking Claude installation...")
result = exec_cmd("which claude")
claude_path = result.stdout.strip()

if not claude_path:
    print("❌ Claude not found. Installing...")
    exec_cmd("npm install -g @anthropic-ai/claude-code")
    result = exec_cmd("which claude")
    claude_path = result.stdout.strip()

print(f"✅ Claude path: {claude_path}")

# Check authentication
print("\n2. Checking Claude authentication...")
result = exec_cmd("claude --version 2>&1")

if "Invalid API key" in result.stdout or "Please run /login" in result.stdout:
    print("\n" + "="*60)
    print("⚠️  CLAUDE AUTHENTICATION REQUIRED!")
    print("="*60)
    print(f"\n1. Run: kubectl exec -it -n devpod {POD_NAME} -- bash")
    print("2. Run: claude")
    print("3. Complete authentication")
    print("4. Exit the container")
    print("="*60)
    input("\nPress Enter after authentication...")
    
    # Re-check
    result = exec_cmd("claude --version 2>&1")
    if "Invalid API key" in result.stdout:
        print("❌ Still not authenticated")
        sys.exit(1)

print("✅ Claude is ready!")

# Execute task
print(f"\n3. Executing task: {TASK}")
print("\n🤖 Running Claude...")

# First, go to the repo directory
exec_cmd("cd ~/auto-worker-demo && pwd")

# Run Claude with the task
cmd = f'cd ~/auto-worker-demo && claude -p "{TASK}"'
result = exec_cmd(cmd)

if result.returncode == 0:
    print("\n✅ Success! Checking generated files...")
    exec_cmd("cd ~/auto-worker-demo && ls -la")
    
    # Check specific files
    for file in ['app.py', 'streamlit_app.py', 'requirements.txt']:
        print(f"\n📄 Checking {file}...")
        result = exec_cmd(f"cd ~/auto-worker-demo && [ -f {file} ] && head -10 {file}")
else:
    print(f"\n❌ Claude execution failed: {result.stderr}")

print("\n✅ Test complete!")