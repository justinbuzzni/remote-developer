# Long-Running Tasks Guide

## Overview

Remote Developer supports long-running tasks that can execute for hours, with proper handling for disconnections and server restarts.

## Features

### 1. Extended Timeouts
- **Claude Execution**: 2 hours (7200 seconds) timeout
- **Other Operations**: 2 minutes (120 seconds) timeout
- Configurable via `config/long_running_tasks.yaml`

### 2. Background Execution
- Tasks run in non-daemon threads
- Continue running even if main process restarts
- Thread information tracked in `TaskManager`

### 3. Persistent State
- Task status saved to disk periodically (every 10 logs)
- Logs preserved across reconnections
- Task files stored in `~/.remote_developer/tasks/`

### 4. Reconnection Support
- Disconnect and reconnect anytime
- Real-time log streaming resumes automatically
- Previous logs available immediately

### 5. Server Restart Handling
- Orphaned tasks detected on startup
- Tasks marked as 'interrupted' if server restarted
- Active tasks list maintained in `active_tasks.json`

## API Endpoints

### Check Task Status
```bash
GET /api/task/{task_id}/check-alive
```
Returns:
- `is_alive`: Whether the task thread is still running
- `thread_info`: Thread details (name, start time)
- `task_status`: Current task status

### List All Tasks
```bash
GET /api/tasks
```
Enhanced response includes:
- `is_running`: Real-time thread status
- All task details with running state

## Usage Scenarios

### 1. Start Long Task and Disconnect
```bash
# Start task
curl -X POST http://localhost:15001/api/create-task \
  -H "Content-Type: application/json" \
  -d '{...}'

# Get task_id from response
# Close browser/terminal - task continues running
```

### 2. Reconnect Later
```bash
# Check if task is still running
curl http://localhost:15001/api/task/{task_id}/check-alive

# Resume watching logs
curl http://localhost:15001/api/task-logs/{task_id}/stream
```

### 3. Server Restart Recovery
```bash
# Stop server (Ctrl+C)
# Restart server
python run_server.py

# Server will detect orphaned tasks and mark them appropriately
# Check task status to see 'interrupted' tasks
```

## Configuration

Edit `config/long_running_tasks.yaml`:

```yaml
task_execution:
  claude_timeout: 7200  # 2 hours
  status_save_interval: 10  # Save every 10 logs
  use_daemon_threads: false  # Keep running after exit

recovery:
  check_orphaned_tasks: true
  orphaned_task_action: 'interrupted'
```

## Implementation Details

### TaskManager
- Tracks all running task threads
- Persists active task list
- Monitors thread health
- Handles cleanup

### Status Persistence
- Periodic saves during execution
- Critical transition points always saved
- File-based storage for reliability

### Thread Management
- Non-daemon threads for persistence
- Thread registry with metadata
- Automatic cleanup on completion

## Best Practices

1. **Monitor Long Tasks**
   - Use `/api/task/{task_id}/check-alive` periodically
   - Check logs for progress updates

2. **Handle Interruptions**
   - Tasks marked 'interrupted' on server restart
   - Check last_updated timestamp
   - Consider implementing task resumption

3. **Resource Management**
   - Long tasks consume server resources
   - Monitor memory usage for large logs
   - Consider log rotation for very long tasks

## Troubleshooting

### Task Stuck in 'executing_task'
- Check if thread is alive: `/api/task/{task_id}/check-alive`
- Review last logs for errors
- Check kubectl/devpod connectivity

### Server Restart Issues
- Check `~/.remote_developer/tasks/active_tasks.json`
- Look for 'interrupted' status in task files
- Review server startup logs

### Memory Issues
- Logs accumulate in memory
- Restart server periodically for very long tasks
- Consider implementing log pagination