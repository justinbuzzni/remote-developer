#!/usr/bin/env python3
"""Demo script to show log streaming in action"""
import requests
import json
import time

# API server URL
API_BASE_URL = "http://localhost:15001"

def main():
    print("🚀 Log Streaming Demo")
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
    print("\n📌 Open your browser to http://localhost:15001 to see real-time logs!")
    
    # Create a real task
    test_data = {
        "devpod_name": "auto-worker-demo",
        "github_repo": "justinbuzzni/auto-worker-demo",
        "github_token": input("\nEnter your GitHub token: ").strip(),
        "task_description": "Create a simple Python script that prints 'Hello' 10 times with 1 second delay between each print"
    }
    
    print("\n📝 Creating task...")
    response = requests.post(
        f"{API_BASE_URL}/api/create-task",
        json=test_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create task: {response.text}")
        return
        
    task_id = response.json()['task_id']
    print(f"✅ Task created: {task_id}")
    print(f"\n🌐 Watch the logs at: http://localhost:15001")
    print("\n👀 The web interface will show:")
    print("   - Real-time log streaming")
    print("   - Claude execution progress")
    print("   - Task status updates")
    print("   - Progress bar animation")
    
    # Monitor task status
    print("\n📊 Task Progress:")
    last_status = None
    while True:
        time.sleep(2)
        
        try:
            response = requests.get(f"{API_BASE_URL}/api/task-status/{task_id}")
            if response.status_code == 200:
                task = response.json()
                status = task.get('status', 'unknown')
                progress = task.get('progress', 0)
                claude_status = task.get('claude_status', '')
                
                if status != last_status:
                    print(f"\n  Status changed: {last_status} → {status}")
                    last_status = status
                
                if status in ['completed', 'failed']:
                    print(f"\n{'✅' if status == 'completed' else '❌'} Task {status}!")
                    
                    if task.get('app_url'):
                        print(f"🌐 App running at: {task['app_url']}")
                    
                    break
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break
    
    print("\n" + "=" * 50)
    print("Demo completed! Check the web interface for the full log history.")

if __name__ == "__main__":
    main()