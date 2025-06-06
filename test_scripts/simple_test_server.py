#!/usr/bin/env python
"""간단한 테스트 서버 - 블로킹 없이 작업 실행"""
import json
import time
import threading
import subprocess
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 메모리에 작업 저장
tasks = {}

def execute_task_simple(task_id, devpod_name, github_repo, github_token, task_description):
    """간단한 작업 실행 - 블로킹 없이"""
    print(f"[{task_id}] 작업 시작: {task_description}")
    
    # 작업 상태 업데이트
    tasks[task_id] = {
        'status': 'running',
        'progress': 0,
        'created_at': datetime.now().isoformat(),
        'devpod_name': devpod_name,
        'github_repo': github_repo,
        'task_description': task_description,
        'logs': []
    }
    
    # DevPod 확인 (타임아웃 포함)
    try:
        cmd = f"timeout 2 kubectl get pods -n devpod | grep {devpod_name[:10]}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            pod_line = result.stdout.strip().split('\n')[0]
            pod_name = pod_line.split()[0] if pod_line else None
            tasks[task_id]['logs'].append(f"Found pod: {pod_name}")
            print(f"[{task_id}] Found pod: {pod_name}")
        else:
            tasks[task_id]['logs'].append("Pod not found, but continuing...")
            print(f"[{task_id}] Pod not found")
    except Exception as e:
        tasks[task_id]['logs'].append(f"Error checking pod: {e}")
        print(f"[{task_id}] Error: {e}")
    
    # 작업 진행 시뮬레이션
    for i in range(5):
        time.sleep(2)  # 2초마다
        tasks[task_id]['progress'] = (i + 1) * 20
        tasks[task_id]['logs'].append(f"Progress: {tasks[task_id]['progress']}%")
        print(f"[{task_id}] Progress: {tasks[task_id]['progress']}%")
    
    # 완료
    tasks[task_id]['status'] = 'completed'
    tasks[task_id]['logs'].append("Task completed successfully!")
    print(f"[{task_id}] 작업 완료!")

@app.route('/api/dashboard')
def dashboard():
    """대시보드 - 빠른 응답"""
    return jsonify({
        'total_tasks': len(tasks),
        'completed_tasks': sum(1 for t in tasks.values() if t.get('status') == 'completed'),
        'failed_tasks': sum(1 for t in tasks.values() if t.get('status') == 'failed'),
        'running_tasks': sum(1 for t in tasks.values() if t.get('status') == 'running'),
        'recent_tasks': list(tasks.values())[-10:]
    })

@app.route('/api/create-task', methods=['POST'])
def create_task():
    """작업 생성"""
    data = request.json
    task_id = f"task-{int(time.time())}"
    
    # 백그라운드에서 실행
    thread = threading.Thread(
        target=execute_task_simple,
        args=(task_id, data['devpod_name'], data['github_repo'], 
              data['github_token'], data['task_description'])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/task-status/<task_id>')
def task_status(task_id):
    """작업 상태 확인"""
    if task_id in tasks:
        return jsonify(tasks[task_id])
    return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    print("간단한 테스트 서버 시작 - http://localhost:15002")
    app.run(host='0.0.0.0', port=15002, debug=False)