"""
Task Manager for long-running tasks with persistence and recovery
"""

import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TaskManager:
    """Manages long-running tasks with persistence"""
    
    def __init__(self, tasks_dir=None):
        self.tasks_dir = tasks_dir or (Path.home() / '.remote_developer' / 'tasks')
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.active_tasks = {}
        self.recovery_file = self.tasks_dir / 'active_tasks.json'
        
    def save_active_tasks(self):
        """Save list of active tasks for recovery after restart"""
        active_list = []
        for task_id, thread_info in self.active_tasks.items():
            active_list.append({
                'task_id': task_id,
                'thread_name': thread_info.get('thread_name'),
                'started_at': thread_info.get('started_at'),
                'is_alive': thread_info.get('thread', threading.Thread()).is_alive()
            })
        
        with open(self.recovery_file, 'w') as f:
            json.dump(active_list, f, indent=2)
    
    def load_active_tasks(self):
        """Load list of previously active tasks"""
        if self.recovery_file.exists():
            try:
                with open(self.recovery_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def register_task(self, task_id: str, thread: threading.Thread):
        """Register a new task thread"""
        self.active_tasks[task_id] = {
            'thread': thread,
            'thread_name': thread.name,
            'started_at': datetime.now().isoformat()
        }
        self.save_active_tasks()
    
    def unregister_task(self, task_id: str):
        """Unregister a completed task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            self.save_active_tasks()
    
    def check_orphaned_tasks(self):
        """Check for tasks that were running before restart"""
        previous_tasks = self.load_active_tasks()
        orphaned = []
        
        for task_info in previous_tasks:
            task_id = task_info['task_id']
            # Check if task file exists and is not completed
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                    if task_data.get('status') not in ['completed', 'failed']:
                        orphaned.append({
                            'task_id': task_id,
                            'status': task_data.get('status'),
                            'last_updated': task_data.get('last_updated')
                        })
        
        return orphaned
    
    def monitor_tasks(self):
        """Monitor running tasks and clean up completed ones"""
        while True:
            time.sleep(30)  # Check every 30 seconds
            
            completed = []
            for task_id, info in self.active_tasks.items():
                thread = info.get('thread')
                if thread and not thread.is_alive():
                    completed.append(task_id)
                    logger.info(f"Task {task_id} thread completed")
            
            for task_id in completed:
                self.unregister_task(task_id)

# Global task manager instance
task_manager = TaskManager()