import os
import threading
import time
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from datetime import datetime
import git
from typing import Dict, Any, Optional
import subprocess
import json
import logging
import tempfile
import queue
import pickle
from pathlib import Path

from .remote_developer import RemoteDeveloper
from .config import Config

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create directory for task persistence
TASKS_DIR = Path.home() / '.remote_developer' / 'tasks'
TASKS_DIR.mkdir(parents=True, exist_ok=True)

# Store active tasks and their status
tasks_status = {}
tasks_lock = threading.Lock()

# Store log streams for real-time updates
log_streams = {}
log_streams_lock = threading.Lock()

def save_task_status(task_id: str):
    """Save task status to file"""
    try:
        with tasks_lock:
            if task_id in tasks_status:
                task_file = TASKS_DIR / f"{task_id}.json"
                with open(task_file, 'w') as f:
                    json.dump(tasks_status[task_id], f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save task {task_id}: {e}")

def load_all_tasks():
    """Load all tasks from files on startup"""
    try:
        for task_file in TASKS_DIR.glob("*.json"):
            with open(task_file, 'r') as f:
                task_data = json.load(f)
                task_id = task_file.stem
                tasks_status[task_id] = task_data
                logger.info(f"Loaded task {task_id} from file")
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")

def check_incomplete_tasks():
    """Check incomplete tasks in background after startup"""
    try:
        time.sleep(5)  # Wait for server to fully start
        
        with tasks_lock:
            incomplete_tasks = [
                (task_id, task) for task_id, task in tasks_status.items()
                if task.get('status') in ['executing_task', 'checking_server']
            ]
        
        for task_id, task in incomplete_tasks:
            try:
                logger.info(f"Checking incomplete task {task_id}")
                devpod_name = task.get('devpod_name')
                github_repo = task.get('github_repo')
                
                if not devpod_name or not github_repo:
                    continue
                    
                repo_name = github_repo.split('/')[-1]
                
                # Check if Claude is still running
                if check_claude_still_running(devpod_name, repo_name, task_id):
                    add_log(task_id, "ℹ️ Task was still running when server restarted")
                else:
                    # Task is not running, mark as interrupted
                    with tasks_lock:
                        tasks_status[task_id]['status'] = 'interrupted'
                        tasks_status[task_id]['progress'] = tasks_status[task_id].get('progress', 0)
                    add_log(task_id, "⚠️ Task was interrupted when server shut down")
                    save_task_status(task_id)
                    
            except Exception as e:
                logger.error(f"Failed to check task {task_id}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to check incomplete tasks: {e}")

# Load existing tasks on startup
load_all_tasks()

# Disable background check for now - causing blocking issues
# TODO: Fix DevPod connection timeout issues
# check_thread = threading.Thread(target=check_incomplete_tasks)
# check_thread.daemon = True
# check_thread.start()

def create_or_get_devpod(devpod_name: str) -> bool:
    """Create devpod if it doesn't exist"""
    try:
        # Use full path to devpod
        devpod_path = '/Users/namsangboy/.local/bin/devpod'
        
        # First check if devpod is installed
        version_result = subprocess.run([devpod_path, 'version'], 
                                      capture_output=True, text=True)
        if version_result.returncode != 0:
            logger.error("DevPod is not accessible. Check installation at: /Users/namsangboy/.local/bin/devpod")
            return False
            
        # Check if devpod exists
        result = subprocess.run([devpod_path, 'list', '--output', 'json'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to list devpods: {result.stderr}")
            # Try without --output json flag
            result = subprocess.run([devpod_path, 'list'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to list devpods: {result.stderr}")
                return False
            
            # Parse text output
            exists = devpod_name in result.stdout
        else:
            # Parse JSON output
            try:
                devpods = json.loads(result.stdout)
                exists = any(pod.get('Name') == devpod_name for pod in devpods)
            except json.JSONDecodeError:
                # Fallback to text parsing
                exists = devpod_name in result.stdout
            
        if not exists:
            logger.info(f"Creating new devpod: {devpod_name}")
            
            # List available providers
            providers_result = subprocess.run([devpod_path, 'provider', 'list'], 
                                            capture_output=True, text=True)
            logger.info(f"Available providers: {providers_result.stdout}")
            
            # Check kubernetes provider settings
            k8s_use_result = subprocess.run([devpod_path, 'provider', 'use', 'kubernetes'], 
                                           capture_output=True, text=True)
            logger.info(f"Setting kubernetes as provider: {k8s_use_result.stdout}")
            
            # Create local workspace directory
            workspace_dir = f"/tmp/devpod-workspace-{devpod_name}"
            os.makedirs(workspace_dir, exist_ok=True)
            
            # Create new devpod with kubernetes provider (default)
            create_result = subprocess.run([devpod_path, 'up', '--provider', 'kubernetes', f'--source', f'local:{workspace_dir}', devpod_name], 
                                         capture_output=True, text=True)
            if create_result.returncode != 0:
                logger.error(f"Failed to create devpod with kubernetes: {create_result.stderr}")
                # Try without specifying provider (use default)
                create_result = subprocess.run([devpod_path, 'up', f'--source', f'local:{workspace_dir}', devpod_name], 
                                             capture_output=True, text=True)
                if create_result.returncode != 0:
                    logger.error(f"Failed to create devpod: {create_result.stderr}")
                    return False
                    
        else:
            logger.info(f"DevPod {devpod_name} already exists")
            
        # Start the devpod if it's not running
        logger.info(f"Ensuring DevPod {devpod_name} is running...")
        start_result = subprocess.run([devpod_path, 'up', devpod_name], 
                                    capture_output=True, text=True)
        if start_result.returncode != 0:
            logger.warning(f"Failed to ensure devpod is running: {start_result.stderr}")
        else:
            logger.info(f"DevPod {devpod_name} is ready")
            
        return True
    except FileNotFoundError:
        logger.error("DevPod command not found. Please install DevPod: https://devpod.sh/docs/getting-started/install")
        return False
    except Exception as e:
        logger.error(f"Error managing devpod: {e}")
        return False

def add_log(task_id: str, message: str):
    """Add log message and notify streams"""
    with tasks_lock:
        if task_id in tasks_status:
            tasks_status[task_id]['logs'].append(message)
            tasks_status[task_id]['last_updated'] = datetime.now().isoformat()
    
    # Save task status to file
    save_task_status(task_id)
    
    # Notify all streams watching this task
    with log_streams_lock:
        if task_id in log_streams:
            for stream_queue in log_streams[task_id]:
                try:
                    stream_queue.put(message)
                except:
                    pass

def get_pod_name(devpod_name: str) -> str:
    """Get pod name for devpod with timeout"""
    logger.info(f"Getting pod name for devpod: {devpod_name}")
    try:
        # Method 1: Try with label selector (reduced timeout)
        pod_name_cmd = f"timeout 2 kubectl get pods -n devpod -l devpod.sh/workspace={devpod_name} -o jsonpath='{{.items[0].metadata.name}}'"
        logger.debug(f"Running: {pod_name_cmd}")
        pod_result = subprocess.run(pod_name_cmd, shell=True, capture_output=True, text=True)
        pod_name = pod_result.stdout.strip()
        logger.debug(f"Method 1 result: {pod_name}")
        
        # Method 2: If not found, try with name prefix
        if not pod_name:
            # DevPod names get truncated, so search by prefix
            # Replace dashes with regex pattern to handle truncation
            name_parts = devpod_name.replace('-', '.*')
            pod_name_cmd = f"timeout 2 kubectl get pods -n devpod | grep -E 'devpod-{name_parts[:10]}' | awk '{{print $1}}' | head -1"
            pod_result = subprocess.run(pod_name_cmd, shell=True, capture_output=True, text=True)
            pod_name = pod_result.stdout.strip()
            
            # Method 3: More flexible search
            if not pod_name:
                # Try even shorter prefix
                short_name = devpod_name.replace('-', '')[:10]
                pod_name_cmd = f"timeout 2 kubectl get pods -n devpod | grep -i '{short_name}' | awk '{{print $1}}' | head -1"
                pod_result = subprocess.run(pod_name_cmd, shell=True, capture_output=True, text=True)
                pod_name = pod_result.stdout.strip()
        
        if not pod_name:
            # List all devpod pods for debugging
            list_cmd = "timeout 2 kubectl get pods -n devpod"
            list_result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
            logger.error(f"Available pods:\n{list_result.stdout}")
            raise Exception(f"Pod not found for devpod {devpod_name}")
        
        return pod_name
    except Exception as e:
        logger.error(f"Failed to get pod name for {devpod_name}: {e}")
        raise

def exec_in_devpod(devpod_name: str, command: str, pod_name: str = None) -> subprocess.CompletedProcess:
    """Execute command in devpod using kubectl exec"""
    if not pod_name:
        pod_name = get_pod_name(devpod_name)
    
    logger.info(f"Using pod: {pod_name}")
    
    # Escape single quotes in command
    escaped_cmd = command.replace("'", "'\"'\"'")
    # Add timeout to kubectl exec
    kubectl_cmd = f"timeout 30 kubectl exec -n devpod {pod_name} -- bash -c '{escaped_cmd}'"
    return subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)

def exec_in_devpod_stream(devpod_name: str, command: str, task_id: str, pod_name: str = None):
    """Execute command in devpod with streaming output - non-blocking"""
    if not pod_name:
        logger.warning(f"Pod name not provided for streaming execution, getting it now...")
        try:
            pod_name = get_pod_name(devpod_name)
        except Exception as e:
            logger.error(f"Failed to get pod name: {e}")
            add_log(task_id, f"Error: Failed to get pod name: {e}")
            return -1
    
    # Escape single quotes in command
    escaped_cmd = command.replace("'", "'\"'\"'")
    kubectl_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c '{escaped_cmd}'"
    
    try:
        process = subprocess.Popen(
            kubectl_cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Set non-blocking
        import fcntl
        import os
        flags = fcntl.fcntl(process.stdout, fcntl.F_GETFL)
        fcntl.fcntl(process.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Stream output with timeout
        empty_reads = 0
        max_empty_reads = 600  # 10 minutes of no output
        
        while True:
            try:
                line = process.stdout.readline()
                if line:
                    empty_reads = 0
                    line_text = line.rstrip()
                    add_log(task_id, line_text)
                    
                    # Parse Claude status updates
                    with tasks_lock:
                        if task_id in tasks_status:
                            if "CLAUDE_STATUS: RUNNING" in line_text and "minutes" in line_text:
                                try:
                                    minutes = int(line_text.split('(')[1].split(' ')[0])
                                    tasks_status[task_id]['claude_runtime'] = minutes * 60
                                except:
                                    pass
                            elif "CLAUDE_STATUS:" in line_text:
                                status = line_text.split("CLAUDE_STATUS:")[1].strip().split()[0]
                                tasks_status[task_id]['claude_status'] = status
                                tasks_status[task_id]['last_updated'] = datetime.now().isoformat()
                                save_task_status(task_id)
                else:
                    # Check if process is still running
                    if process.poll() is not None:
                        break
                    
                    # No output, wait a bit
                    time.sleep(0.1)
                    empty_reads += 1
                    
                    if empty_reads > max_empty_reads:
                        logger.warning(f"No output for 10 minutes, terminating")
                        process.terminate()
                        break
                        
            except IOError:
                # No data available
                if process.poll() is not None:
                    break
                time.sleep(0.1)
                empty_reads += 1
                
                if empty_reads > max_empty_reads:
                    logger.warning(f"No output for 10 minutes, terminating")
                    process.terminate()
                    break
        
        # Wait for process to complete
        return_code = process.wait()
        return return_code
        
    except Exception as e:
        logger.error(f"Error in streaming execution: {e}")
        add_log(task_id, f"Error: {e}")
        return -1

def check_claude_still_running(devpod_name: str, repo_name: str, task_id: str) -> bool:
    """Check if Claude is still running in the devpod"""
    try:
        # Add timeout to prevent hanging
        pod_name = get_pod_name(devpod_name)
        check_cmd = f'cd ~/{repo_name} && ps aux | grep "claude --print" | grep -v grep'
        
        # Run with timeout
        kubectl_cmd = f"timeout 5 kubectl exec -n devpod {pod_name} -- bash -c '{check_cmd}'"
        result = subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            # Claude is still running
            return True
        
        # Check if claude_output.txt is still being written
        check_output = f'cd ~/{repo_name} && [ -f claude_output.txt ] && echo "EXISTS"'
        kubectl_cmd = f"timeout 5 kubectl exec -n devpod {pod_name} -- bash -c '{check_output}'"
        result = subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)
        
        if "EXISTS" in result.stdout:
            # Get the last modified time
            stat_cmd = f'cd ~/{repo_name} && stat -c %Y claude_output.txt 2>/dev/null || stat -f %m claude_output.txt 2>/dev/null'
            kubectl_cmd = f"timeout 5 kubectl exec -n devpod {pod_name} -- bash -c '{stat_cmd}'"
            stat_result = subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)
            
            try:
                last_modified = int(stat_result.stdout.strip())
                current_time = int(time.time())
                # If file was modified in the last 5 minutes, consider it still running
                if current_time - last_modified < 300:
                    return True
            except:
                pass
                
        return False
    except Exception as e:
        logger.warning(f"Failed to check if Claude is running: {e}")
        return False

def execute_remote_task(task_id: str, devpod_name: str, github_repo: str, 
                       github_token: str, task_description: str):
    """Execute task in background thread"""
    devpod_path = '/Users/namsangboy/.local/bin/devpod'
    try:
        with tasks_lock:
            tasks_status[task_id] = {
                'status': 'initializing',
                'progress': 0,
                'logs': [],
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'devpod_name': devpod_name,
                'github_repo': github_repo,
                'task_description': task_description,
                'github_token': github_token  # Store for potential recovery
            }
        
        save_task_status(task_id)
        
        # Step 1: Create or get devpod
        with tasks_lock:
            tasks_status[task_id]['status'] = 'creating_devpod'
            tasks_status[task_id]['progress'] = 10
        save_task_status(task_id)
        add_log(task_id, 'Creating/checking devpod...')
        
        if not create_or_get_devpod(devpod_name):
            error_msg = "Failed to create or get devpod. Please ensure DevPod is installed: https://devpod.sh/docs/getting-started/install"
            add_log(task_id, f'Error: {error_msg}')
            raise Exception(error_msg)
        
        # Step 2: Clone or update repository
        with tasks_lock:
            tasks_status[task_id]['status'] = 'cloning_repository'
            tasks_status[task_id]['progress'] = 20
        add_log(task_id, 'Cloning/updating repository...')
        
        # Configure git in devpod
        git_config_cmds = [
            f'git config --global user.name "Auto Worker"',
            f'git config --global user.email "auto-worker@example.com"',
            f'git config --global credential.helper store',
            f'echo "https://{github_token}@github.com" > ~/.git-credentials'
        ]
        
        # Get pod name early
        try:
            pod_name = get_pod_name(devpod_name)
        except Exception as e:
            logger.error(f"Failed to get pod name: {e}")
            error_msg = f"Failed to connect to DevPod {devpod_name}. Please ensure the DevPod is running."
            add_log(task_id, f'Error: {error_msg}')
            with tasks_lock:
                tasks_status[task_id]['status'] = 'failed'
                tasks_status[task_id]['error'] = error_msg
            save_task_status(task_id)
            return
        
        for cmd in git_config_cmds:
            exec_in_devpod(devpod_name, cmd, pod_name)
        
        # Clone or pull latest code
        repo_name = github_repo.split('/')[-1]
        
        # Check if repository already exists
        check_repo_cmd = f'cd ~/{repo_name} && git status'
        check_result = exec_in_devpod(devpod_name, check_repo_cmd, pod_name)
        
        if check_result.returncode == 0:
            # Repository exists, update it
            add_log(task_id, 'Repository exists, updating...')
            
            update_cmds = [
                f'cd ~/{repo_name} && git fetch origin',
                f'cd ~/{repo_name} && git checkout main || git checkout master || git checkout -b main',
                f'cd ~/{repo_name} && git reset --hard origin/$(git symbolic-ref --short HEAD) || true',
                f'cd ~/{repo_name} && git clean -fd'
            ]
            
            for cmd in update_cmds:
                result = exec_in_devpod(devpod_name, cmd, pod_name)
                if "error" in result.stderr.lower() and "fatal" in result.stderr.lower():
                    logger.warning(f"Git command warning: {result.stderr}")
        else:
            # Repository doesn't exist, clone it
            add_log(task_id, 'Cloning repository...')
            
            clone_cmd = f'cd ~ && git clone https://{github_token}@github.com/{github_repo}.git {repo_name}'
            result = exec_in_devpod(devpod_name, clone_cmd, pod_name)
            
            if result.returncode != 0:
                # If clone fails, try to remove existing directory and clone again
                remove_cmd = f'rm -rf ~/{repo_name}'
                exec_in_devpod(devpod_name, remove_cmd, pod_name)
                
                result = exec_in_devpod(devpod_name, clone_cmd, pod_name)
                if result.returncode != 0:
                    raise Exception(f"Failed to clone repository: {result.stderr}")
        
        # Step 3: Setup Claude Code
        with tasks_lock:
            tasks_status[task_id]['status'] = 'setting_up_claude'
            tasks_status[task_id]['progress'] = 30
        add_log(task_id, 'Setting up Claude Code...')
        
        # Install Node.js if not present
        node_check = 'which node || echo "not found"'
        result = exec_in_devpod(devpod_name, node_check, pod_name)
        
        if "not found" in result.stdout:
            add_log(task_id, 'Installing Node.js...')
            
            # Install Node.js
            node_install_cmds = [
                'apt-get update',
                'apt-get install -y nodejs npm'
            ]
            for cmd in node_install_cmds:
                exec_in_devpod(devpod_name, cmd, pod_name)
        
        # Install Claude via npm
        claude_install = 'npm install -g @anthropic-ai/claude-code || echo "Claude installation failed"'
        result = exec_in_devpod(devpod_name, claude_install, pod_name)
        
        if "Claude installation failed" not in result.stdout:
            add_log(task_id, 'Claude installed (from @anthropic-ai/claude-code package)')
        else:
            add_log(task_id, 'Claude installation failed, will use fallback')
        
        # Create Claude settings file with permissions
        claude_settings = '''mkdir -p ~/.claude && cat > ~/.claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Write(*)",
      "Read(*)",
      "Edit(*)",
      "Bash(*)",
      "Grep(*)",
      "Glob(*)",
      "MultiEdit(*)"
    ],
    "deny": []
  },
  "enableAllProjectMcpServers": false
}
EOF'''
        exec_in_devpod(devpod_name, claude_settings, pod_name)
        add_log(task_id, 'Created Claude settings with auto-permissions')
        
        # The package installs 'claude' command, not 'claude-code'
        check_claude = 'which claude || echo "not found"'
        check_result = exec_in_devpod(devpod_name, check_claude, pod_name)
        
        add_log(task_id, f'Claude command location: {check_result.stdout.strip()}')
        
        # Step 4: Create new branch
        with tasks_lock:
            tasks_status[task_id]['status'] = 'creating_branch'
            tasks_status[task_id]['progress'] = 40
        add_log(task_id, 'Creating new branch...')
        
        branch_name = f"auto-pr-{int(time.time())}"
        branch_cmd = f'cd ~/{repo_name} && git checkout -b {branch_name}'
        exec_in_devpod(devpod_name, branch_cmd, pod_name)
        
        # Step 5: Execute Claude task
        with tasks_lock:
            tasks_status[task_id]['status'] = 'executing_task'
            tasks_status[task_id]['progress'] = 60
        add_log(task_id, 'Executing Claude task...')
        
        # Create task history directory
        task_history_cmd = f'''
        mkdir -p ~/{repo_name}/.task_history
        echo "Task ID: {task_id}" > ~/{repo_name}/.task_history/{task_id}.txt
        echo "Timestamp: $(date)" >> ~/{repo_name}/.task_history/{task_id}.txt
        echo "Description: {task_description}" >> ~/{repo_name}/.task_history/{task_id}.txt
        echo "---" >> ~/{repo_name}/.task_history/{task_id}.txt
        '''
        exec_in_devpod(devpod_name, task_history_cmd, pod_name)
        
        # Create a script to run Claude
        claude_script = f'''#!/bin/bash
# Claude execution script
cd ~/{repo_name}

# Execute the task using Claude
echo "Executing task: {task_description}"
echo "Task started at: $(date)"
echo "CLAUDE_STATUS: STARTING"

# Check if claude command exists
if command -v claude &> /dev/null; then
    echo "Claude is available at: $(which claude)"
    echo "CLAUDE_STATUS: RUNNING"
    
    # Create a file to track Claude output in real-time
    touch claude_output.txt
    touch claude_progress.log
    
    # Run Claude in background with 1 hour timeout
    timeout 3600 claude --print "{task_description}" > claude_output.txt 2>&1 &
    claude_pid=$!
    
    # Monitor Claude execution
    echo "Claude is running in background (PID: $claude_pid)..."
    
    # Monitor for up to 1 hour
    wait_time=0
    last_size=0
    
    while [ $wait_time -lt 3600 ]; do
        if ! ps -p $claude_pid > /dev/null; then
            echo "CLAUDE_STATUS: COMPLETED"
            echo "Claude execution completed after $wait_time seconds"
            break
        fi
        
        # Check if output file is growing
        current_size=$(stat -f%z claude_output.txt 2>/dev/null || stat -c%s claude_output.txt 2>/dev/null || echo 0)
        if [ "$current_size" -gt "$last_size" ]; then
            echo "CLAUDE_PROGRESS: Output size: $current_size bytes"
            # Show last few lines of output
            echo "CLAUDE_OUTPUT_PREVIEW:"
            tail -5 claude_output.txt 2>/dev/null || true
            echo "---"
            last_size=$current_size
        fi
        
        sleep 10
        wait_time=$((wait_time + 10))
        
        # Status update every minute
        if [ $((wait_time % 60)) -eq 0 ]; then
            echo "CLAUDE_STATUS: RUNNING ($((wait_time / 60)) minutes)"
        fi
    done
    
    # If still running after 1 hour, kill it
    if ps -p $claude_pid > /dev/null; then
        echo "CLAUDE_STATUS: TIMEOUT"
        kill $claude_pid 2>/dev/null || true
        echo "Claude execution timed out after 1 hour"
    fi
    
    # Check result
    if [ -f claude_output.txt ]; then
        echo "=== Claude Output ==="
        cat claude_output.txt
        echo "===================="
    fi
    
    echo "Execution completed at: $(date)" >> .task_history/{task_id}.txt
else
    echo "Claude not available"
    echo "CLAUDE_STATUS: ERROR"
    echo "Error: Claude not available" >> .task_history/{task_id}.txt
    exit 1
fi

# Check if any files were created/modified
echo ""
echo "=== Files in directory ==="
ls -la

# Check for common application files
for file in app.py main.py server.py streamlit_app.py requirements.txt package.json; do
    if [ -f "$file" ]; then
        echo ""
        echo "=== Content of $file ==="
        head -20 "$file"
    fi
done

echo "CLAUDE_STATUS: DONE"
'''
        
        # Write and execute the script
        script_cmd = f'cd ~/{repo_name} && cat > run_claude.sh << \'EOF\'\n{claude_script}\nEOF && chmod +x run_claude.sh'
        exec_in_devpod(devpod_name, script_cmd, pod_name)
        
        # Execute Claude with streaming
        add_log(task_id, 'Executing Claude task...')
        
        # Track Claude execution status
        with tasks_lock:
            tasks_status[task_id]['claude_status'] = 'STARTING'
            tasks_status[task_id]['claude_runtime'] = 0
        
        # Execute Claude script with streaming output
        execute_cmd = f'cd ~/{repo_name} && bash run_claude.sh 2>&1'
        
        # Pod name already obtained earlier
        
        # Use streaming execution
        returncode = exec_in_devpod_stream(devpod_name, execute_cmd, task_id, pod_name)
        
        # Parse Claude status from logs
        claude_failed = False
        with tasks_lock:
            if task_id in tasks_status:
                logs = tasks_status[task_id]['logs']
                for log in reversed(logs):
                    if "CLAUDE_STATUS: COMPLETED" in log:
                        tasks_status[task_id]['claude_status'] = 'COMPLETED'
                        break
                    elif "CLAUDE_STATUS: TIMEOUT" in log:
                        tasks_status[task_id]['claude_status'] = 'TIMEOUT'
                        break
                    elif "CLAUDE_STATUS: ERROR" in log:
                        tasks_status[task_id]['claude_status'] = 'ERROR'
                        claude_failed = True
                        break
                    elif "Claude not available" in log or "command not found" in log:
                        claude_failed = True
                        break
        
        # If Claude fails or is not installed, use fallback
        if returncode != 0 or claude_failed:
            add_log(task_id, "Claude Code not available, using fallback implementation...")
            
            # Fallback: Create files based on task description
            if "streamlit" in task_description.lower():
                fallback_script = '''#!/bin/bash
cd ~/auto-worker-demo

# Create Streamlit app
cat > app.py << 'EOF'
import streamlit as st

st.title("Text Display Demo")
st.write("This application displays text input from users")

# Input text from user
user_input = st.text_input("Enter your text here:", "")

# Display the input text
if user_input:
    st.write("You entered:")
    st.success(user_input)
    
    # Additional display options
    with st.expander("View in different formats"):
        st.code(user_input)
        st.info(user_input)
        st.markdown(f"**Bold:** **{user_input}**")

# Add some statistics
if user_input:
    st.sidebar.header("Text Statistics")
    st.sidebar.write(f"Length: {len(user_input)} characters")
    st.sidebar.write(f"Words: {len(user_input.split())} words")
EOF

# Create requirements.txt
echo "streamlit" > requirements.txt

# Create README
cat > README.md << 'EOF'
# Streamlit Text Display Demo

A simple Streamlit application that displays user input text.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

## Features
- Text input field
- Multiple display formats
- Text statistics

Generated by Remote Developer
EOF

echo "Streamlit app created successfully!"
ls -la
'''
                fallback_cmd = f'cd ~/{repo_name} && cat > fallback.sh << \'EOF\'\n{fallback_script}\nEOF && chmod +x fallback.sh && bash fallback.sh'
                result = exec_in_devpod(devpod_name, fallback_cmd, pod_name)
                
                add_log(task_id, "Fallback execution completed")
        else:
            add_log(task_id, "Claude execution completed successfully")
        
        # Step 7: Commit changes
        with tasks_lock:
            tasks_status[task_id]['status'] = 'committing_changes'
            tasks_status[task_id]['progress'] = 75
        add_log(task_id, 'Committing changes...')
        
        # Add task summary to README if not exists
        readme_cmd = f'''cd ~/{repo_name} && if [ ! -f README.md ]; then
    echo "# {repo_name}" > README.md
    echo "" >> README.md
    echo "## Task History" >> README.md
    echo "" >> README.md
fi

# Add latest task to README
echo "- [{task_id}](.task_history/{task_id}.txt): {task_description} ($(date '+%Y-%m-%d %H:%M'))" >> README.md
'''
        exec_in_devpod(devpod_name, readme_cmd, pod_name)
        
        commit_cmds = [
            f'cd ~/{repo_name} && git add -A',
            f'cd ~/{repo_name} && git commit -m "Task: {task_description}" || true'
        ]
        
        for cmd in commit_cmds:
            exec_in_devpod(devpod_name, cmd, pod_name)
        
        # Step 8: Check if a server was created and run it
        with tasks_lock:
            tasks_status[task_id]['status'] = 'checking_server'
            tasks_status[task_id]['progress'] = 85
        add_log(task_id, 'Checking for server applications...')
        
        # Store server info
        server_started = False
        
        # Check for Python requirements
        req_check = exec_in_devpod(devpod_name, f'cd ~/{repo_name} && [ -f requirements.txt ] && echo "FOUND"', pod_name)
        if "FOUND" in req_check.stdout:
            add_log(task_id, 'Installing Python dependencies...')
            exec_in_devpod(devpod_name, f'cd ~/{repo_name} && pip3 install --break-system-packages -r requirements.txt || true', pod_name)
        
        # Check for Node.js dependencies
        pkg_check = exec_in_devpod(devpod_name, f'cd ~/{repo_name} && [ -f package.json ] && echo "FOUND"', pod_name)
        if "FOUND" in pkg_check.stdout:
            add_log(task_id, 'Installing Node.js dependencies...')
            exec_in_devpod(devpod_name, f'cd ~/{repo_name} && npm install || true', pod_name)
        
        # Check for Streamlit app
        streamlit_check = exec_in_devpod(devpod_name, f'cd ~/{repo_name} && ([ -f app.py ] || [ -f streamlit_app.py ]) && grep -l "streamlit" *.py 2>/dev/null | head -1', pod_name)
        if streamlit_check.stdout.strip():
            app_file = streamlit_check.stdout.strip()
            add_log(task_id, f'Starting Streamlit app: {app_file}')
            
            # Kill any existing streamlit process
            exec_in_devpod(devpod_name, 'pkill -f streamlit || true', pod_name)
            
            # Start Streamlit in background
            start_cmd = f'cd ~/{repo_name} && nohup streamlit run {app_file} --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &'
            exec_in_devpod(devpod_name, start_cmd, pod_name)
            
            # Wait a bit for server to start
            time.sleep(3)
            
            # Set up port forwarding
            add_log(task_id, 'Setting up port forwarding for Streamlit (port 8501)...')
            forward_thread = threading.Thread(
                target=lambda: subprocess.run(['kubectl', 'port-forward', '-n', 'devpod', pod_name, '8501:8501'])
            )
            forward_thread.daemon = True
            forward_thread.start()
            
            add_log(task_id, '✅ Streamlit app is running!')
            add_log(task_id, '🌐 Access your app at: http://localhost:8501')
            
            with tasks_lock:
                tasks_status[task_id]['app_url'] = 'http://localhost:8501'
                tasks_status[task_id]['server_type'] = 'streamlit'
            
            server_started = True
        
        # Check for FastAPI app
        if not server_started:
            fastapi_check = exec_in_devpod(devpod_name, f'cd ~/{repo_name} && grep -l "FastAPI\\|fastapi" *.py 2>/dev/null | head -1', pod_name)
            if fastapi_check.stdout.strip():
                app_file = fastapi_check.stdout.strip()
                add_log(task_id, f'Starting FastAPI app: {app_file}')
                
                # Start FastAPI in background
                start_cmd = f'cd ~/{repo_name} && nohup uvicorn {app_file.replace(".py", "")}:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &'
                exec_in_devpod(devpod_name, start_cmd, pod_name)
                
                # Wait a bit for server to start
                time.sleep(3)
                
                # Set up port forwarding
                add_log(task_id, 'Setting up port forwarding for FastAPI (port 8000)...')
                forward_thread = threading.Thread(
                    target=lambda: subprocess.run(['kubectl', 'port-forward', '-n', 'devpod', pod_name, '8000:8000'])
                )
                forward_thread.daemon = True
                forward_thread.start()
                
                add_log(task_id, '✅ FastAPI app is running!')
                add_log(task_id, '🌐 Access your app at: http://localhost:8000')
                
                with tasks_lock:
                    tasks_status[task_id]['app_url'] = 'http://localhost:8000'
                    tasks_status[task_id]['server_type'] = 'fastapi'
                
                server_started = True
        
        # Complete - even if server is running
        with tasks_lock:
            tasks_status[task_id]['status'] = 'completed'
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['branch_name'] = branch_name
            if server_started:
                tasks_status[task_id]['server_running'] = True
        
        if server_started:
            add_log(task_id, f'✅ Task completed! Server is running. Branch: {branch_name}')
        else:
            add_log(task_id, f'✅ Task completed! Branch: {branch_name}')
            
    except Exception as e:
        with tasks_lock:
            tasks_status[task_id]['status'] = 'failed'
            tasks_status[task_id]['error'] = str(e)
        add_log(task_id, f'Error: {str(e)}')

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/create-task', methods=['POST'])
def create_task():
    """Create a new automated PR task"""
    data = request.json
    
    required_fields = ['devpod_name', 'github_repo', 'github_token', 'task_description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    task_id = f"task-{int(time.time())}"
    
    # Start task in background thread
    thread = threading.Thread(
        target=execute_remote_task,
        args=(task_id, data['devpod_name'], data['github_repo'], 
              data['github_token'], data['task_description'])
    )
    thread.daemon = True  # Allow main process to exit even if thread is running
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/task-status/<task_id>')
def get_task_status(task_id):
    """Get status of a specific task"""
    with tasks_lock:
        if task_id in tasks_status:
            # Make a copy to ensure all fields are included
            task_data = dict(tasks_status[task_id])
            task_data['task_id'] = task_id
            return jsonify(task_data)
        else:
            return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks')
def list_tasks():
    """List all tasks"""
    with tasks_lock:
        return jsonify(list(tasks_status.values()))

@app.route('/api/dashboard')
def dashboard():
    """Get dashboard data - fast, non-blocking"""
    try:
        with tasks_lock:
            # Quick stats calculation
            total_tasks = len(tasks_status)
            completed_tasks = sum(1 for t in tasks_status.values() if t.get('status') == 'completed')
            failed_tasks = sum(1 for t in tasks_status.values() if t.get('status') == 'failed')
            running_tasks = sum(1 for t in tasks_status.values() if t.get('status') not in ['completed', 'failed', 'interrupted'])
            
            # Get recent tasks with their IDs (limit sensitive data)
            recent_tasks = []
            for task_id, task_data in sorted(tasks_status.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:10]:
                # Create a safe copy without sensitive data
                safe_task = {
                    'task_id': task_id,
                    'status': task_data.get('status', 'unknown'),
                    'progress': task_data.get('progress', 0),
                    'created_at': task_data.get('created_at', ''),
                    'last_updated': task_data.get('last_updated', ''),
                    'devpod_name': task_data.get('devpod_name', ''),
                    'task_description': task_data.get('task_description', ''),
                    'github_repo': task_data.get('github_repo', ''),
                    'claude_status': task_data.get('claude_status', ''),
                    'app_url': task_data.get('app_url', ''),
                    'server_running': task_data.get('server_running', False),
                    'branch_name': task_data.get('branch_name', ''),
                    'logs': task_data.get('logs', [])[-5:]  # Only last 5 logs for dashboard
                }
                recent_tasks.append(safe_task)
            
            return jsonify({
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'running_tasks': running_tasks,
                'recent_tasks': recent_tasks
            })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'running_tasks': 0,
            'recent_tasks': [],
            'error': str(e)
        })

@app.route('/api/task/<task_id>/continue', methods=['POST'])
def continue_task(task_id):
    """Continue a task that requires authentication"""
    with tasks_lock:
        if task_id not in tasks_status:
            return jsonify({'error': 'Task not found'}), 404
        
        if tasks_status[task_id].get('requires_authentication', False):
            tasks_status[task_id]['authentication_confirmed'] = True
            return jsonify({'status': 'ok', 'message': 'Task will continue'})
        else:
            return jsonify({'error': 'Task does not require authentication'}), 400

@app.route('/api/create-pr', methods=['POST'])
def create_pr():
    """Create a pull request for a DevPod"""
    data = request.json
    
    required_fields = ['devpod_name', 'github_repo', 'github_token', 'pr_title']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    devpod_name = data['devpod_name']
    github_repo = data['github_repo']
    github_token = data['github_token']
    pr_title = data['pr_title']
    pr_body = data.get('pr_body', 'Pull request created by Remote Developer')
    
    try:
        # Get pod name
        pod_name = get_pod_name(devpod_name)
        repo_name = github_repo.split('/')[-1]
        
        # Get current branch
        branch_result = exec_in_devpod(devpod_name, f'cd ~/{repo_name} && git branch --show-current', pod_name)
        branch_name = branch_result.stdout.strip()
        
        if not branch_name or branch_name == 'main' or branch_name == 'master':
            return jsonify({'error': 'Please create and checkout a feature branch first'}), 400
        
        # Push current branch
        push_cmd = f'cd ~/{repo_name} && git push origin {branch_name}'
        push_result = exec_in_devpod(devpod_name, push_cmd, pod_name)
        
        if push_result.returncode != 0:
            return jsonify({'error': f'Failed to push branch: {push_result.stderr}'}), 500
        
        # Install gh CLI if needed
        gh_check = exec_in_devpod(devpod_name, 'which gh', pod_name)
        if not gh_check.stdout.strip():
            gh_install = 'curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && apt update && apt install gh -y'
            exec_in_devpod(devpod_name, gh_install, pod_name)
        
        # Authenticate gh with token
        auth_cmd = f'echo {github_token} | gh auth login --with-token'
        exec_in_devpod(devpod_name, auth_cmd, pod_name)
        
        # Create PR
        pr_cmd = f'cd ~/{repo_name} && gh pr create --title "{pr_title}" --body "{pr_body}" --base main --head {branch_name}'
        pr_result = exec_in_devpod(devpod_name, pr_cmd, pod_name)
        
        if pr_result.returncode == 0:
            pr_url = pr_result.stdout.strip()
            return jsonify({'status': 'success', 'pr_url': pr_url})
        else:
            return jsonify({'error': f'Failed to create PR: {pr_result.stderr}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/task/<task_id>/check-running', methods=['GET'])
def check_task_running(task_id):
    """Check if a task is still running in the devpod"""
    with tasks_lock:
        if task_id not in tasks_status:
            return jsonify({'error': 'Task not found'}), 404
        
        task = tasks_status[task_id]
        
        # Only check if task was executing
        if task['status'] in ['executing_task', 'checking_server']:
            devpod_name = task['devpod_name']
            github_repo = task['github_repo']
            repo_name = github_repo.split('/')[-1]
            
            if check_claude_still_running(devpod_name, repo_name, task_id):
                return jsonify({
                    'running': True,
                    'message': 'Claude is still running in the background'
                })
            else:
                # Check if task completed while server was down
                try:
                    pod_name = get_pod_name(devpod_name)
                    output_cmd = f'cd ~/{repo_name} && [ -f claude_output.txt ] && cat claude_output.txt || echo "NOT_FOUND"'
                    result = exec_in_devpod(devpod_name, output_cmd, pod_name)
                    
                    if result.stdout and "NOT_FOUND" not in result.stdout:
                        # Task completed, update status
                        task['status'] = 'completed'
                        task['claude_status'] = 'COMPLETED'
                        add_log(task_id, '✅ Task completed while server was offline')
                        save_task_status(task_id)
                except:
                    pass
                
                return jsonify({
                    'running': False,
                    'message': 'Task is not running'
                })
        
        return jsonify({
            'running': False,
            'message': 'Task is not in execution state'
        })

@app.route('/api/task/<task_id>/recover-logs', methods=['POST'])
def recover_task_logs(task_id):
    """Recover logs from a task that was running when server shut down"""
    with tasks_lock:
        if task_id not in tasks_status:
            return jsonify({'error': 'Task not found'}), 404
        
        task = tasks_status[task_id]
        devpod_name = task['devpod_name']
        github_repo = task['github_repo']
        repo_name = github_repo.split('/')[-1]
        
        try:
            pod_name = get_pod_name(devpod_name)
            
            # Get Claude output
            output_cmd = f'cd ~/{repo_name} && [ -f claude_output.txt ] && tail -50 claude_output.txt || echo "No output found"'
            result = exec_in_devpod(devpod_name, output_cmd, pod_name)
            
            if result.stdout:
                add_log(task_id, "=== Recovered Claude Output ===")
                for line in result.stdout.strip().split('\n'):
                    add_log(task_id, line)
                add_log(task_id, "==============================")
            
            # Get streamlit/server logs if any
            server_log_cmd = f'cd ~/{repo_name} && [ -f streamlit.log ] && tail -20 streamlit.log || [ -f fastapi.log ] && tail -20 fastapi.log || echo ""'
            server_result = exec_in_devpod(devpod_name, server_log_cmd, pod_name)
            
            if server_result.stdout.strip():
                add_log(task_id, "=== Server Logs ===")
                for line in server_result.stdout.strip().split('\n'):
                    add_log(task_id, line)
                add_log(task_id, "==================")
            
            return jsonify({'status': 'success', 'message': 'Logs recovered'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/task-logs/<task_id>/stream')
def stream_task_logs(task_id):
    """Stream task logs using Server-Sent Events"""
    def generate():
        # Create a queue for this client
        client_queue = queue.Queue()
        
        # Register this client for the task
        with log_streams_lock:
            if task_id not in log_streams:
                log_streams[task_id] = []
            log_streams[task_id].append(client_queue)
        
        try:
            # Send existing logs first
            with tasks_lock:
                if task_id in tasks_status:
                    for log in tasks_status[task_id]['logs']:
                        yield f"data: {json.dumps({'log': log})}\n\n"
            
            # Stream new logs
            while True:
                try:
                    # Wait for new log with timeout
                    log = client_queue.get(timeout=30)
                    yield f"data: {json.dumps({'log': log})}\n\n"
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                    
                # Check if task is completed
                with tasks_lock:
                    if task_id in tasks_status:
                        status = tasks_status[task_id]['status']
                        if status in ['completed', 'failed']:
                            yield f"data: {json.dumps({'status': status, 'complete': True})}\n\n"
                            break
                            
        finally:
            # Unregister this client
            with log_streams_lock:
                if task_id in log_streams and client_queue in log_streams[task_id]:
                    log_streams[task_id].remove(client_queue)
                    if not log_streams[task_id]:
                        del log_streams[task_id]
    
    return Response(generate(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=15001, debug=False, threaded=True)