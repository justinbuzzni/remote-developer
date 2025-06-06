#!/usr/bin/env python3
"""
Run the Remote Developer API server with Docker backend
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api_server_docker import app

if __name__ == '__main__':
    print("Starting Remote Developer API Server (Docker Backend)...")
    print("Web interface available at: http://localhost:15001")
    print("API endpoints:")
    print("  - POST /api/create-task")
    print("  - GET  /api/task-status/<task_id>")
    print("  - GET  /api/tasks")
    print("  - GET  /api/dashboard")
    print()
    print("Note: This version uses Docker containers instead of DevPod")
    print("Make sure Docker is running on your system")
    
    app.run(host='0.0.0.0', port=15001, debug=True)