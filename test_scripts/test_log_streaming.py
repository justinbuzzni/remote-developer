#!/usr/bin/env python3
"""Test script to verify real-time log streaming functionality"""
import requests
import json
import time
import threading
import sseclient

# API server URL
API_BASE_URL = "http://localhost:15001"

# Test data
test_data = {
    "devpod_name": "log-test-pod",
    "github_repo": "test-user/test-repo",
    "github_token": "test-token-12345",
    "task_description": "Test task to verify log streaming. Print progress messages every second for 10 seconds."
}

def stream_logs(task_id):
    """Stream logs from the server using SSE"""
    print(f"\n📡 Starting log stream for task {task_id}...")
    
    try:
        # Create SSE client
        response = requests.get(f"{API_BASE_URL}/api/task-logs/{task_id}/stream", stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.data:
                try:
                    data = json.loads(event.data)
                    
                    if 'log' in data:
                        # Display log with formatting
                        log_line = data['log']
                        if 'CLAUDE_STATUS:' in log_line:
                            print(f"🤖 {log_line}")
                        elif 'CLAUDE_PROGRESS:' in log_line:
                            print(f"📊 {log_line}")
                        elif '✅' in log_line or 'completed' in log_line.lower():
                            print(f"✅ {log_line}")
                        elif '❌' in log_line or 'error' in log_line.lower():
                            print(f"❌ {log_line}")
                        else:
                            print(f"   {log_line}")
                    
                    if data.get('complete'):
                        print(f"\n✅ Stream completed for task {task_id}")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing event data: {e}")
                    
    except Exception as e:
        print(f"❌ Error streaming logs: {e}")

def main():
    print("🧪 Testing Real-Time Log Streaming")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/api/dashboard")
        if response.status_code != 200:
            print("❌ API server is not responding. Please start it with: ./run_server.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Please start it with: ./run_server.py")
        return
    
    print("✅ API server is running")
    
    # Create a test task
    print("\n📝 Creating test task...")
    response = requests.post(
        f"{API_BASE_URL}/api/create-task",
        json=test_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create task: {response.text}")
        return
        
    task_id = response.json()['task_id']
    print(f"✅ Task created: {task_id}")
    
    # Start streaming logs in a separate thread
    stream_thread = threading.Thread(target=stream_logs, args=(task_id,))
    stream_thread.start()
    
    # Also poll task status periodically
    print("\n📊 Monitoring task status...")
    while True:
        time.sleep(2)
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/task-status/{task_id}")
            if response.status_code == 200:
                task = response.json()
                status = task.get('status', 'unknown')
                progress = task.get('progress', 0)
                claude_status = task.get('claude_status', '')
                
                status_line = f"Status: {status} | Progress: {progress}%"
                if claude_status:
                    status_line += f" | Claude: {claude_status}"
                print(f"\r{status_line}", end='', flush=True)
                
                if status in ['completed', 'failed']:
                    print(f"\n\n{'✅' if status == 'completed' else '❌'} Task {status}")
                    break
                    
        except Exception as e:
            print(f"\n❌ Error checking status: {e}")
            break
    
    # Wait for stream thread to complete
    stream_thread.join(timeout=5)
    
    print("\n" + "=" * 50)
    print("🧪 Test completed!")

if __name__ == "__main__":
    main()