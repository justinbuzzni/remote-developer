#!/usr/bin/env python3
"""
Run the Remote Developer API server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api_server import app

if __name__ == '__main__':
    print("Starting Remote Developer API Server...")
    print("Web interface available at: http://localhost:15001")
    print("API endpoints:")
    print("  - POST /api/create-task")
    print("  - GET  /api/task-status/<task_id>")
    print("  - GET  /api/tasks")
    print("  - GET  /api/dashboard")
    
    app.run(host='0.0.0.0', port=15001, debug=True)