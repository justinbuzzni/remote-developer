import os
import threading
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import git
from typing import Dict, Any, Optional
import subprocess
import json
import logging

from .docker_manager import DockerManager
from .config import Config

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active tasks and their status
tasks_status = {}
tasks_lock = threading.Lock()

# Docker manager instance
docker_mgr = DockerManager()

def execute_remote_task(task_id: str, container_name: str, github_repo: str, 
                       github_token: str, task_description: str):
    """Execute task in background thread"""
    try:
        with tasks_lock:
            tasks_status[task_id] = {
                'status': 'initializing',
                'progress': 0,
                'logs': [],
                'created_at': datetime.now().isoformat(),
                'container_name': container_name,
                'github_repo': github_repo,
                'task_description': task_description
            }
        
        # Step 1: Create or get container
        with tasks_lock:
            tasks_status[task_id]['status'] = 'creating_container'
            tasks_status[task_id]['progress'] = 10
            tasks_status[task_id]['logs'].append('Creating/checking Docker container...')
        
        container_id = docker_mgr.create_or_get_container(container_name)
        if not container_id:
            raise Exception("Failed to create or get container")
        
        with tasks_lock:
            tasks_status[task_id]['logs'].append(f'Container ready: {container_id[:12]}')
        
        # Step 2: Configure git
        with tasks_lock:
            tasks_status[task_id]['status'] = 'configuring_git'
            tasks_status[task_id]['progress'] = 20
            tasks_status[task_id]['logs'].append('Configuring git...')
        
        git_config_cmds = [
            'git config --global user.name "Auto Worker"',
            'git config --global user.email "auto-worker@example.com"',
            'git config --global credential.helper store',
            f'echo "https://{github_token}@github.com" > ~/.git-credentials'
        ]
        
        for cmd in git_config_cmds:
            result = docker_mgr.exec_command(container_name, cmd)
            if result['exit_code'] != 0:
                logger.warning(f"Git config warning: {result['stderr']}")
        
        # Step 3: Clone or update repository
        with tasks_lock:
            tasks_status[task_id]['status'] = 'cloning_repository'
            tasks_status[task_id]['progress'] = 30
            tasks_status[task_id]['logs'].append('Cloning/updating repository...')
        
        repo_name = github_repo.split('/')[-1]
        clone_cmd = f'cd ~ && (git clone https://{github_token}@github.com/{github_repo}.git {repo_name} || (cd {repo_name} && git pull origin main))'
        result = docker_mgr.exec_command(container_name, clone_cmd)
        
        if result['exit_code'] != 0:
            # Try to create main branch if it doesn't exist
            create_main_cmd = f'cd ~/{repo_name} && (git checkout -b main || git checkout main)'
            docker_mgr.exec_command(container_name, create_main_cmd)
        
        with tasks_lock:
            tasks_status[task_id]['logs'].append('Repository ready')
        
        # Step 4: Install Claude Code
        with tasks_lock:
            tasks_status[task_id]['status'] = 'installing_claude_code'
            tasks_status[task_id]['progress'] = 40
            tasks_status[task_id]['logs'].append('Installing Claude Code...')
        
        # Check if claude-code is already installed
        check_cmd = 'which claude-code || echo "not found"'
        result = docker_mgr.exec_command(container_name, check_cmd)
        
        if "not found" in result['stdout']:
            install_cmd = 'curl -fsSL https://cdn.anthropic.com/install/claude-code.sh | sh'
            result = docker_mgr.exec_command(container_name, install_cmd)
            with tasks_lock:
                tasks_status[task_id]['logs'].append('Claude Code installed')
        else:
            with tasks_lock:
                tasks_status[task_id]['logs'].append('Claude Code already installed')
        
        # Step 5: Create new branch
        with tasks_lock:
            tasks_status[task_id]['status'] = 'creating_branch'
            tasks_status[task_id]['progress'] = 50
            tasks_status[task_id]['logs'].append('Creating new branch...')
        
        branch_name = f"auto-pr-{int(time.time())}"
        branch_cmd = f'cd ~/{repo_name} && git checkout -b {branch_name}'
        result = docker_mgr.exec_command(container_name, branch_cmd)
        
        with tasks_lock:
            tasks_status[task_id]['logs'].append(f'Branch created: {branch_name}')
        
        # Step 6: Execute Claude Code task
        with tasks_lock:
            tasks_status[task_id]['status'] = 'executing_task'
            tasks_status[task_id]['progress'] = 60
            tasks_status[task_id]['logs'].append('Executing Claude Code task...')
        
        task_cmd = f'cd ~/{repo_name} && claude-code execute --task "{task_description}"'
        result = docker_mgr.exec_command(container_name, task_cmd)
        
        with tasks_lock:
            tasks_status[task_id]['logs'].append(f"Task execution completed")
            if result['stdout']:
                tasks_status[task_id]['logs'].append(f"Output: {result['stdout'][:200]}...")
        
        # Step 7: Commit changes
        with tasks_lock:
            tasks_status[task_id]['status'] = 'committing_changes'
            tasks_status[task_id]['progress'] = 70
            tasks_status[task_id]['logs'].append('Committing changes...')
        
        commit_cmds = [
            f'cd ~/{repo_name} && git add -A',
            f'cd ~/{repo_name} && git commit -m "Auto PR: {task_description}" || echo "No changes to commit"'
        ]
        
        for cmd in commit_cmds:
            result = docker_mgr.exec_command(container_name, cmd)
        
        # Step 8: Push branch
        with tasks_lock:
            tasks_status[task_id]['status'] = 'pushing_branch'
            tasks_status[task_id]['progress'] = 80
            tasks_status[task_id]['logs'].append('Pushing branch...')
        
        push_cmd = f'cd ~/{repo_name} && git push origin {branch_name}'
        result = docker_mgr.exec_command(container_name, push_cmd)
        
        if result['exit_code'] != 0:
            # Try to set upstream
            push_cmd = f'cd ~/{repo_name} && git push -u origin {branch_name}'
            result = docker_mgr.exec_command(container_name, push_cmd)
            if result['exit_code'] != 0:
                raise Exception(f"Failed to push branch: {result['stderr']}")
        
        with tasks_lock:
            tasks_status[task_id]['logs'].append('Branch pushed successfully')
        
        # Step 9: Create PR using GitHub CLI
        with tasks_lock:
            tasks_status[task_id]['status'] = 'creating_pr'
            tasks_status[task_id]['progress'] = 90
            tasks_status[task_id]['logs'].append('Creating pull request...')
        
        # Install gh CLI if needed
        gh_check = 'which gh || echo "not found"'
        result = docker_mgr.exec_command(container_name, gh_check)
        
        if "not found" in result['stdout']:
            gh_install = '''
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
            apt update && apt install gh -y
            '''
            docker_mgr.exec_command(container_name, gh_install)
        
        # Authenticate gh with token
        auth_cmd = f'echo {github_token} | gh auth login --with-token'
        docker_mgr.exec_command(container_name, auth_cmd)
        
        # Create PR
        pr_cmd = f'''cd ~/{repo_name} && gh pr create --title "Auto PR: {task_description}" --body "This PR was automatically generated by Claude Code.

Task: {task_description}

Generated with Remote Developer" --base main --head {branch_name}'''
        
        result = docker_mgr.exec_command(container_name, pr_cmd)
        
        if result['exit_code'] == 0:
            pr_url = result['stdout'].strip()
            with tasks_lock:
                tasks_status[task_id]['pr_url'] = pr_url
                tasks_status[task_id]['logs'].append(f'PR created: {pr_url}')
        else:
            with tasks_lock:
                tasks_status[task_id]['logs'].append(f'PR creation failed: {result["stderr"]}')
        
        # Step 10: Set up port forwarding if server was created
        with tasks_lock:
            tasks_status[task_id]['status'] = 'setting_up_access'
            tasks_status[task_id]['progress'] = 95
            tasks_status[task_id]['logs'].append('Checking for servers...')
        
        # Check for common server files
        server_checks = [
            (f'cd ~/{repo_name} && find . -name "*.py" -exec grep -l "streamlit\\|flask\\|fastapi" {{}} \\; | head -1', 8501),
            (f'cd ~/{repo_name} && find . -name "package.json" | head -1', 3000),
        ]
        
        for check_cmd, default_port in server_checks:
            result = docker_mgr.exec_command(container_name, check_cmd)
            if result['stdout'].strip():
                with tasks_lock:
                    tasks_status[task_id]['logs'].append(f'Server file found: {result["stdout"].strip()}')
                    tasks_status[task_id]['logs'].append(f'To access: docker exec -it {container_name} bash')
                break
        
        # Complete
        with tasks_lock:
            tasks_status[task_id]['status'] = 'completed'
            tasks_status[task_id]['progress'] = 100
            tasks_status[task_id]['logs'].append('Task completed successfully!')
            
    except Exception as e:
        with tasks_lock:
            tasks_status[task_id]['status'] = 'failed'
            tasks_status[task_id]['error'] = str(e)
            tasks_status[task_id]['logs'].append(f'Error: {str(e)}')
        logger.error(f"Task {task_id} failed: {e}")

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
    
    # Use devpod_name as container_name
    container_name = data['devpod_name']
    task_id = f"task-{int(time.time())}"
    
    # Start task in background thread
    thread = threading.Thread(
        target=execute_remote_task,
        args=(task_id, container_name, data['github_repo'], 
              data['github_token'], data['task_description'])
    )
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/task-status/<task_id>')
def get_task_status(task_id):
    """Get status of a specific task"""
    with tasks_lock:
        if task_id in tasks_status:
            return jsonify(tasks_status[task_id])
        else:
            return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks')
def list_tasks():
    """List all tasks"""
    with tasks_lock:
        return jsonify(list(tasks_status.values()))

@app.route('/api/dashboard')
def dashboard():
    """Get dashboard data"""
    with tasks_lock:
        total_tasks = len(tasks_status)
        completed_tasks = sum(1 for t in tasks_status.values() if t['status'] == 'completed')
        failed_tasks = sum(1 for t in tasks_status.values() if t['status'] == 'failed')
        running_tasks = sum(1 for t in tasks_status.values() if t['status'] not in ['completed', 'failed'])
        
        return jsonify({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'recent_tasks': list(tasks_status.values())[-10:]  # Last 10 tasks
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=15001, debug=True)