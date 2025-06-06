#!/usr/bin/env python
"""Streaming API server with non-blocking command execution"""
import os
import threading
import time
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from datetime import datetime
import subprocess
import json
import logging
import queue
from pathlib import Path
import select

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# DevPod 경로
DEVPOD_PATH = '/Users/namsangboy/.local/bin/devpod'

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

# Load existing tasks on startup
load_all_tasks()

def add_log(task_id: str, message: str):
    """Add log message and notify streams"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    
    with tasks_lock:
        if task_id in tasks_status:
            tasks_status[task_id]['logs'].append(log_message)
            tasks_status[task_id]['last_updated'] = datetime.now().isoformat()
            # 로그가 100개를 넘으면 오래된 것 제거
            if len(tasks_status[task_id]['logs']) > 100:
                tasks_status[task_id]['logs'] = tasks_status[task_id]['logs'][-100:]
    
    # Save task status to file (less frequently)
    if "completed" in message.lower() or "failed" in message.lower() or "error" in message.lower():
        save_task_status(task_id)
    
    # Notify all streams watching this task
    with log_streams_lock:
        if task_id in log_streams:
            for stream_queue in log_streams[task_id]:
                try:
                    stream_queue.put(log_message)
                except:
                    pass

def run_command_streaming(cmd: str, task_id: str, timeout: int = 300) -> tuple[int, str, str]:
    """Run command with streaming output"""
    logger.info(f"[{task_id}] Running streaming command: {cmd}")
    
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        stdout_lines = []
        stderr_lines = []
        start_time = time.time()
        
        # Read output in real-time
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                process.kill()
                logger.error(f"[{task_id}] Command timed out after {timeout}s")
                return -1, "", f"Command timed out after {timeout} seconds"
            
            # Check if process has finished
            if process.poll() is not None:
                # Read any remaining output
                remaining_stdout = process.stdout.read()
                remaining_stderr = process.stderr.read()
                if remaining_stdout:
                    stdout_lines.append(remaining_stdout)
                if remaining_stderr:
                    stderr_lines.append(remaining_stderr)
                break
            
            # Read available output (non-blocking)
            readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
            
            for stream in readable:
                if stream == process.stdout:
                    line = stream.readline()
                    if line:
                        stdout_lines.append(line)
                        # Log git clone progress
                        if "Cloning into" in line or "Receiving objects" in line:
                            add_log(task_id, f"Git: {line.strip()}")
                elif stream == process.stderr:
                    line = stream.readline()
                    if line:
                        stderr_lines.append(line)
                        # Git often outputs to stderr
                        if "Cloning into" in line or "Receiving objects" in line:
                            add_log(task_id, f"Git: {line.strip()}")
            
            # Small sleep to avoid busy waiting
            time.sleep(0.01)
        
        stdout = ''.join(stdout_lines)
        stderr = ''.join(stderr_lines)
        
        elapsed = time.time() - start_time
        logger.info(f"[{task_id}] Command completed in {elapsed:.2f}s: returncode={process.returncode}")
        
        return process.returncode, stdout, stderr
        
    except Exception as e:
        logger.error(f"[{task_id}] Command error: {e}")
        return -1, "", str(e)

def run_command(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run command with timeout (simple version for quick commands)"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return -1, "", str(e)

def get_pod_name(devpod_name: str) -> str:
    """Get pod name for devpod"""
    cmd = f"kubectl get pods -n devpod | grep 'devpod-{devpod_name[:10]}' | awk '{{print $1}}' | head -1"
    returncode, stdout, stderr = run_command(cmd, timeout=5)
    
    if returncode == 0 and stdout.strip():
        return stdout.strip()
    else:
        raise Exception(f"Pod not found for devpod {devpod_name}")

def execute_streaming_task(task_id: str, devpod_name: str, github_repo: str, 
                          github_token: str, task_description: str):
    """Execute task with streaming output"""
    repo_name = github_repo.split('/')[-1]
    
    try:
        # Initialize task status
        with tasks_lock:
            tasks_status[task_id] = {
                'status': 'initializing',
                'progress': 0,
                'logs': [],
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'devpod_name': devpod_name,
                'github_repo': github_repo,
                'task_description': task_description
            }
        
        add_log(task_id, f"🚀 Starting task: {task_description}")
        
        # Step 1: Start DevPod
        with tasks_lock:
            tasks_status[task_id]['status'] = 'starting_devpod'
            tasks_status[task_id]['progress'] = 10
        
        add_log(task_id, "Starting DevPod...")
        returncode, stdout, stderr = run_command(f"{DEVPOD_PATH} up {devpod_name}", timeout=60)
        
        if returncode != 0:
            raise Exception(f"Failed to start DevPod: {stderr}")
        
        add_log(task_id, "✅ DevPod started")
        
        # Step 2: Get pod name
        try:
            pod_name = get_pod_name(devpod_name)
            add_log(task_id, f"Found pod: {pod_name}")
        except Exception as e:
            add_log(task_id, f"❌ Failed to find pod: {e}")
            raise Exception(f"Failed to find pod: {e}")
        
        # Step 3: Setup Git
        with tasks_lock:
            tasks_status[task_id]['status'] = 'setting_up_git'
            tasks_status[task_id]['progress'] = 20
        
        add_log(task_id, "Setting up Git...")
        
        git_commands = [
            f"kubectl exec -n devpod {pod_name} -- bash -c \"git config --global user.name 'Auto Worker'\"",
            f"kubectl exec -n devpod {pod_name} -- bash -c \"git config --global user.email 'auto-worker@example.com'\"",
            f"kubectl exec -n devpod {pod_name} -- bash -c \"echo 'https://{github_token}@github.com' > ~/.git-credentials\"",
            f"kubectl exec -n devpod {pod_name} -- bash -c \"git config --global credential.helper store\""
        ]
        
        for cmd in git_commands:
            run_command(cmd)
        
        # Step 4: Clone or update repository
        with tasks_lock:
            tasks_status[task_id]['status'] = 'cloning_repository'
            tasks_status[task_id]['progress'] = 30
        
        add_log(task_id, "Cloning/updating repository...")
        
        # Check if repo exists
        check_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && pwd'"
        returncode, stdout, stderr = run_command(check_cmd, timeout=10)
        
        if returncode == 0:
            # Update existing repo
            add_log(task_id, "Repository exists, updating...")
            update_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && git fetch && git reset --hard origin/main || git reset --hard origin/master'"
            returncode, stdout, stderr = run_command_streaming(update_cmd, task_id, timeout=60)
            if returncode != 0:
                add_log(task_id, f"⚠️ Update warning: {stderr}")
        else:
            # Clone new repo - use streaming for progress
            add_log(task_id, f"Cloning new repository from {github_repo}...")
            clone_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~ && git clone https://{github_token}@github.com/{github_repo}.git'"
            returncode, stdout, stderr = run_command_streaming(clone_cmd, task_id, timeout=300)
            
            if returncode != 0:
                add_log(task_id, f"❌ Clone failed: {stderr}")
                raise Exception(f"Failed to clone repository: {stderr}")
        
        add_log(task_id, "✅ Repository ready")
        
        # Step 5: Install Claude if needed
        with tasks_lock:
            tasks_status[task_id]['status'] = 'setting_up_claude'
            tasks_status[task_id]['progress'] = 40
        
        add_log(task_id, "Setting up Claude...")
        
        # Check if Claude is installed
        check_claude = f"kubectl exec -n devpod {pod_name} -- bash -c 'which claude'"
        returncode, stdout, stderr = run_command(check_claude)
        
        if returncode != 0 or not stdout.strip():
            add_log(task_id, "Installing Claude...")
            install_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'npm install -g @anthropic-ai/claude-code'"
            returncode, stdout, stderr = run_command_streaming(install_cmd, task_id, timeout=180)
        
        # Create Claude settings
        settings_cmd = f'''kubectl exec -n devpod {pod_name} -- bash -c 'mkdir -p ~/.claude && cat > ~/.claude/settings.json << EOF
{
  "permissions": {
    "allow": ["Write(*)", "Read(*)", "Edit(*)", "Bash(*)", "Grep(*)", "Glob(*)", "MultiEdit(*)"],
    "deny": []
  },
  "enableAllProjectMcpServers": false
}
EOF' '''
        run_command(settings_cmd)
        
        add_log(task_id, "✅ Claude ready")
        
        # Step 6: Create branch
        branch_name = f"auto-pr-{int(time.time())}"
        branch_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && git checkout -b {branch_name}'"
        run_command(branch_cmd)
        
        # Step 7: Execute Claude
        with tasks_lock:
            tasks_status[task_id]['status'] = 'executing_claude'
            tasks_status[task_id]['progress'] = 60
        
        add_log(task_id, "🤖 Executing Claude...")
        
        # Create simple Claude execution script
        claude_script = f'''cd ~/{repo_name}
echo "Task: {task_description}"
if command -v claude &> /dev/null; then
    timeout 300 claude --print "{task_description}" 2>&1
else
    echo "Claude not found!"
    exit 1
fi'''
        
        # Execute Claude with streaming
        claude_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c '{claude_script}'"
        returncode, stdout, stderr = run_command_streaming(claude_cmd, task_id, timeout=360)
        
        if returncode != 0:
            if "timeout" in stderr.lower():
                add_log(task_id, "⚠️ Claude execution timed out")
            else:
                raise Exception(f"Claude execution failed: {stderr}")
        else:
            add_log(task_id, "✅ Claude execution completed")
        
        # Step 8: Commit changes
        with tasks_lock:
            tasks_status[task_id]['status'] = 'committing'
            tasks_status[task_id]['progress'] = 80
        
        commit_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && git add -A && git commit -m \"Task: {task_description}\"'"
        run_command(commit_cmd)
        
        # Step 9: Check for Streamlit app
        with tasks_lock:
            tasks_status[task_id]['status'] = 'checking_app'
            tasks_status[task_id]['progress'] = 90
        
        add_log(task_id, "Checking for application...")
        
        # Check if app.py exists
        check_app = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && [ -f app.py ] && echo EXISTS'"
        returncode, stdout, stderr = run_command(check_app)
        
        if "EXISTS" in stdout:
            add_log(task_id, "Found app.py, starting Streamlit...")
            
            # Install requirements if exists
            req_check = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && [ -f requirements.txt ] && echo EXISTS'"
            returncode, stdout, stderr = run_command(req_check)
            
            if "EXISTS" in stdout:
                add_log(task_id, "Installing requirements...")
                install_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && pip3 install --break-system-packages -r requirements.txt'"
                run_command_streaming(install_cmd, task_id, timeout=300)
            
            # Kill existing Streamlit
            kill_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'pkill -f streamlit || true'"
            run_command(kill_cmd)
            
            # Start Streamlit
            start_cmd = f"kubectl exec -n devpod {pod_name} -- bash -c 'cd ~/{repo_name} && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &'"
            run_command(start_cmd)
            
            time.sleep(3)  # Wait for server to start
            
            # Setup port forwarding
            add_log(task_id, "Setting up port forwarding...")
            
            # Kill existing port forwards
            kill_forward = "pkill -f 'kubectl port-forward.*8501' || true"
            subprocess.run(kill_forward, shell=True)
            
            # Start new port forward
            forward_cmd = f"kubectl port-forward -n devpod {pod_name} 8501:8501"
            subprocess.Popen(forward_cmd, shell=True)
            
            app_url = "http://localhost:8501"
            add_log(task_id, f"✅ Streamlit app running at {app_url}")
            
            with tasks_lock:
                tasks_status[task_id]['app_url'] = app_url
                tasks_status[task_id]['server_running'] = True
        
        # Complete
        with tasks_lock:
            tasks_status[task_id]['status'] = 'completed'
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['branch_name'] = branch_name
        
        add_log(task_id, f"✅ Task completed! Branch: {branch_name}")
        save_task_status(task_id)
        
    except Exception as e:
        with tasks_lock:
            tasks_status[task_id]['status'] = 'failed'
            tasks_status[task_id]['error'] = str(e)
        add_log(task_id, f"❌ Error: {str(e)}")
        save_task_status(task_id)

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/create-task', methods=['POST'])
def create_task():
    """Create a new automated task"""
    data = request.json
    
    required_fields = ['devpod_name', 'github_repo', 'github_token', 'task_description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    task_id = f"task-{int(time.time())}"
    
    # Start task in background thread
    thread = threading.Thread(
        target=execute_streaming_task,
        args=(task_id, data['devpod_name'], data['github_repo'], 
              data['github_token'], data['task_description'])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/task-status/<task_id>')
def get_task_status(task_id):
    """Get status of a specific task"""
    with tasks_lock:
        if task_id in tasks_status:
            task_data = dict(tasks_status[task_id])
            task_data['task_id'] = task_id
            return jsonify(task_data)
        else:
            return jsonify({'error': 'Task not found'}), 404

@app.route('/api/dashboard')
def dashboard():
    """Get dashboard data - fast, non-blocking"""
    try:
        with tasks_lock:
            total_tasks = len(tasks_status)
            completed_tasks = sum(1 for t in tasks_status.values() if t.get('status') == 'completed')
            failed_tasks = sum(1 for t in tasks_status.values() if t.get('status') == 'failed')
            running_tasks = sum(1 for t in tasks_status.values() if t.get('status') not in ['completed', 'failed'])
            
            # Get recent tasks
            recent_tasks = []
            for task_id, task_data in sorted(tasks_status.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:10]:
                safe_task = {
                    'task_id': task_id,
                    'status': task_data.get('status', 'unknown'),
                    'progress': task_data.get('progress', 0),
                    'created_at': task_data.get('created_at', ''),
                    'last_updated': task_data.get('last_updated', ''),
                    'devpod_name': task_data.get('devpod_name', ''),
                    'task_description': task_data.get('task_description', ''),
                    'github_repo': task_data.get('github_repo', ''),
                    'app_url': task_data.get('app_url', ''),
                    'server_running': task_data.get('server_running', False),
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

@app.route('/api/task-logs/<task_id>/stream')
def stream_task_logs(task_id):
    """Stream task logs using Server-Sent Events"""
    def generate():
        client_queue = queue.Queue()
        
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
                    log = client_queue.get(timeout=30)
                    yield f"data: {json.dumps({'log': log})}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                    
                with tasks_lock:
                    if task_id in tasks_status:
                        status = tasks_status[task_id]['status']
                        if status in ['completed', 'failed']:
                            yield f"data: {json.dumps({'status': status, 'complete': True})}\n\n"
                            break
                            
        finally:
            with log_streams_lock:
                if task_id in log_streams and client_queue in log_streams[task_id]:
                    log_streams[task_id].remove(client_queue)
                    if not log_streams[task_id]:
                        del log_streams[task_id]
    
    return Response(generate(), mimetype="text/event-stream")

if __name__ == '__main__':
    print("Starting Streaming API Server on http://localhost:15001")
    app.run(host='0.0.0.0', port=15001, debug=False, threaded=True)