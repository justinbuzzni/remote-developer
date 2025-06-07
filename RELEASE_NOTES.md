# Remote Developer Release Notes

## v1.5.0 - MongoDB Integration & Repository Grouping (2025-06-07)

### 🎉 Major Features

#### MongoDB Integration
- **Persistent Storage**: Migrated from local file storage to MongoDB for better scalability
- **Automatic Migration**: Existing tasks automatically migrate to MongoDB on first run
- **Environment Configuration**: MongoDB connection configured via environment variables
- **Fallback Support**: Gracefully falls back to local storage if MongoDB is unavailable
- **Connection Pooling**: Optimized database connections with configurable pool sizes

#### Repository-based Task Grouping
- **By Repository View**: New UI view to see tasks grouped by GitHub repository
- **Repository Statistics**: View total tasks, success rates, and activity for each repo
- **Quick Navigation**: Jump from repository view to specific task details
- **Aggregated Metrics**: See completion rates and task counts per repository

### 🔧 Technical Improvements

#### New API Endpoints
- **GET /api/tasks/by-repo**: Get all tasks grouped by repository with statistics
- **GET /api/tasks/repo/{github_repo}**: Get tasks for a specific repository
- **GET /api/repository-stats**: Get aggregated statistics for all repositories
- **GET /api/task/{task_id}/logs**: Retrieve all logs for a task from MongoDB

#### Database Schema
- **Tasks Collection**: Stores task metadata with indexes on task_id, github_repo, and status
- **Task Logs Collection**: Stores all task logs with efficient querying by task_id
- **Automatic Indexes**: Performance-optimized indexes created on startup
- **Timestamp Tracking**: Automatic created_at and last_updated timestamps

#### Frontend Enhancements
- **View Mode Toggle**: Switch between "Recent Tasks" and "By Repository" views
- **Repository Cards**: Visual cards showing repository statistics and task lists
- **Task Status Indicators**: Color-coded status bars for quick task status overview
- **Smooth Navigation**: Click to navigate from repository view to task details

### 🐛 Bug Fixes

#### UI Fixes
- **Toast Notifications**: Fixed undefined showToast function references
- **Update Dashboard**: Fixed fetchTasks() calls to use updateDashboard()
- **Task ID Anchors**: Added proper IDs for smooth scrolling to specific tasks

#### Connection Handling
- **Graceful Fallback**: Handles MongoDB connection failures without crashing
- **Authentication Support**: Works with both authenticated and non-authenticated MongoDB
- **Timeout Configuration**: Configurable connection timeouts to prevent hanging
- **Replica Set Support**: Fixed MongoDB connection issues with directConnection=true parameter
- **Connection Initialization**: Fixed NoneType errors by properly initializing MongoDB connection on API server startup

### 📝 Configuration

#### Environment Variables
```bash
# MongoDB Configuration
MONGODB_HOST=idc.buzzni.com:32720      # MongoDB host and port
MONGODB_USER=your_mongodb_user          # MongoDB username
MONGODB_PASSWORD=your_mongodb_password  # MongoDB password
MONGODB_DATABASE=remote_developer       # Database name (default: remote_developer)

# Optional: Use full connection URL instead
MONGODB_URL=mongodb://user:pass@host:port/

# Connection Pool Settings
MONGODB_MAX_POOL_SIZE=50               # Maximum connection pool size
MONGODB_MIN_POOL_SIZE=10               # Minimum connection pool size
MONGODB_TIMEOUT_MS=5000                # Connection timeout in milliseconds
```

### 🔍 Implementation Details

#### Data Migration
- Automatic migration of existing local tasks to MongoDB
- Preserves all task data including logs and status
- One-time migration on server startup
- No data loss during migration process

#### Repository Grouping
```javascript
// Frontend view modes
- Recent Tasks: Traditional chronological task list
- By Repository: Tasks grouped by GitHub repository with stats
```

#### MongoDB Collections
```
tasks:
  - task_id (unique index)
  - github_repo (index)
  - status (index)
  - created_at (index)
  - devpod_name, task_description, etc.

task_logs:
  - task_id (index)
  - timestamp (index)
  - message
```

### 📋 Breaking Changes
- None - backward compatible with local storage fallback

### 🎯 Benefits

#### Performance
- Faster task queries with MongoDB indexes
- Efficient aggregation for repository statistics
- Reduced file I/O operations

#### Scalability
- Handle thousands of tasks efficiently
- Better concurrent access support
- Optimized for large-scale deployments

#### Analytics
- Repository-level insights and metrics
- Task success rate tracking
- Activity timeline visualization

### 🚀 Migration Guide

For existing users:
1. Install MongoDB locally or use a remote instance
2. Update .env with MongoDB connection details
3. Start the server - tasks will auto-migrate
4. Use new "By Repository" view for grouped tasks

#### Local MongoDB Setup
```bash
# For macOS with Homebrew
brew install mongodb-community
brew services start mongodb-community

# Default connection (no auth)
MONGODB_URL=mongodb://localhost:27017/
```

---

**Contributors**: Claude Code Assistant
**Key Feature**: MongoDB integration with repository-based task grouping

## v1.4.0 - Manual Commit/PR Workflow & Long-Running Tasks (2025-06-07)

### 🎉 Major Features

#### Manual Commit and PR Workflow
- **No Automatic Commits**: Tasks now work on the main branch without auto-committing
- **Explicit Commit Button**: Users must manually commit changes when ready
- **Separate PR Creation**: Pull requests are created only when explicitly requested
- **Review Before Commit**: See all modified files before committing
- **Flexible Workflow**: Work remains on main branch until user decides to create PR

#### Long-Running Task Support
- **Extended Timeouts**: Claude execution timeout increased from 5 minutes to 2 hours
- **Task Persistence**: Tasks survive server restarts and disconnections
- **Background Execution**: Non-daemon threads continue running after main process exit
- **Reconnection Support**: Resume watching logs after browser reconnection
- **Task Health Monitoring**: Check if tasks are still alive with new API endpoint

### 🔧 Technical Improvements

#### New API Endpoints
- **POST /api/task/{task_id}/commit**: Manually commit task changes
- **POST /api/task/{task_id}/create-pr**: Create PR from committed changes
- **GET /api/task/{task_id}/check-alive**: Check if task thread is still running

#### Task Management
- **TaskManager Class**: Centralized management of long-running tasks
- **Orphaned Task Detection**: Detects tasks interrupted by server restart
- **Active Task Registry**: Maintains list of running tasks in active_tasks.json
- **Periodic Status Saving**: Saves task status every 10 log entries

#### UI Enhancements
- **Commit Changes Button**: Yellow button appears when changes are detected
- **Create PR Button**: Green button appears after changes are committed
- **Modified Files Display**: Shows list of changed files before commit
- **Branch Display**: Shows current working branch (usually main)
- **Status Updates**: New statuses for 'preparing_workspace' and 'reviewing_changes'

### 🐛 Bug Fixes

#### Workflow Improvements
- **Branch Management**: Removed automatic branch creation
- **Commit Control**: Users have full control over when to commit
- **PR Timing**: PRs only created when explicitly requested

#### Stability Enhancements
- **Thread Management**: Fixed daemon thread issues for long-running tasks
- **Status Persistence**: Improved saving of task status during execution
- **Timeout Handling**: Better handling of long Claude executions

### 📝 Configuration

#### New Configuration File
- **config/long_running_tasks.yaml**: Configure timeouts and persistence settings
- Claude timeout: 7200 seconds (2 hours)
- Status save interval: Every 10 logs
- Task monitoring interval: 30 seconds

### 🔍 Implementation Details

#### Workflow Changes
```
Old: Auto-create branch → Execute → Auto-commit → Manual PR
New: Stay on main → Execute → Manual commit → Manual PR
```

#### Task Lifecycle
1. Task executes on main branch
2. Changes are made but not committed
3. User reviews modified files
4. User clicks "Commit Changes" when ready
5. User clicks "Create PR" to open pull request

#### Long-Running Support
- Tasks tracked in `~/.remote_developer/tasks/`
- Active tasks saved to `active_tasks.json`
- Orphaned tasks marked as 'interrupted'
- Logs preserved across reconnections

### 📋 Breaking Changes
- Tasks no longer auto-commit changes
- Default branch is now main (not auto-generated branches)
- PR creation requires explicit user action

### 🎯 Use Cases

#### Quick Experimentation
- Run tasks on main branch
- Test changes without commits
- Discard unwanted changes easily

#### Controlled Deployment
- Review all changes before committing
- Write custom commit messages
- Create PRs only when ready

#### Long Claude Tasks
- Run complex tasks taking 30+ minutes
- Disconnect and reconnect anytime
- Monitor progress across sessions

### 🚀 Migration Guide

For existing users:
1. Tasks will now stay on main branch
2. Look for "Commit Changes" button after task completion
3. Use "Create PR" button when ready to submit
4. Check modified files list before committing

---

**Contributors**: Claude Code Assistant
**Key Feature**: Manual control over commits and PR creation with support for long-running tasks

## v1.3.0 - Real-time Streaming and Task Completion Fixes (2025-06-07)

### 🎉 Major Features

#### Real-time Claude Output Streaming
- **Unbuffered Output Streaming**: Implemented character-by-character and line-by-line streaming for real-time Claude execution output
- **Multiple Streaming Methods**: Added support for stdbuf, script command, and basic streaming with fallback options
- **Non-blocking I/O**: Implemented advanced streaming using fcntl and select for better real-time performance
- **Progress Tracking**: Enhanced Claude output parsing for progress bars, file operations, and completion status

### 🔧 Technical Improvements

#### Streaming Enhancements
- **Unbuffered Subprocess Execution**: Set `PYTHONUNBUFFERED=1` and optimized buffer settings
- **Improved Claude Script**: Simplified execution script with proper exit codes and status messages
- **Streaming Function Options**: Created both `exec_in_devpod_stream_realtime` and `exec_in_devpod_stream_simple` for flexibility

#### Task Completion Fixes
- **Status Update Reliability**: Fixed issue where tasks would hang at "executing_task" status
- **Proper State Transitions**: Added explicit status updates at each major phase transition
- **Enhanced Logging**: Added detailed debug logs for tracking execution flow
- **Timeout Adjustments**: Increased kubectl exec timeout from 30s to 120s for long-running operations

#### Performance Optimizations
- **Reduced File I/O**: Commented out excessive `save_task_status()` calls in hot paths
- **Selective Status Saving**: Only save task status at critical transition points
- **Efficient Log Processing**: Optimized log parsing and status detection

### 🐛 Bug Fixes

#### Critical Fixes
- **Task Completion Detection**: Fixed tasks not transitioning to "completed" status despite successful execution
- **Streaming Termination**: Resolved early termination of streaming output
- **Lock Contention**: Fixed deadlock issues with `add_log` calls inside `tasks_lock` blocks
- **Script Exit Handling**: Added explicit exit codes to ensure proper script completion

#### Error Handling
- **Exception Logging**: Enhanced error logging with stack traces
- **Finally Block**: Added finally block to ensure task status is always saved
- **Graceful Degradation**: Multiple fallback methods for output streaming

### 📝 Code Quality Improvements

#### Documentation
- **Streaming Guide**: Added comprehensive documentation at `docs/streaming_output.md`
- **Test Scripts**: Created test utilities for verifying streaming functionality
- **Debug Tools**: Added debugging scripts for testing execution flow

#### Code Organization
- **Parse Function**: Created dedicated `parse_claude_output()` for better code organization
- **Status Constants**: Better separation of Claude status vs task status
- **Import Organization**: Added necessary imports for select and fcntl modules

### 🔍 Technical Details

#### Streaming Implementation
```python
# Three streaming approaches implemented:
1. Real-time with non-blocking I/O (select + fcntl)
2. Simple line-buffered streaming (default)
3. Character-by-character reading (fallback)
```

#### Status Update Flow
```
initializing -> creating_devpod -> cloning_repository -> 
setting_up_claude -> creating_branch -> executing_task -> 
committing_changes -> checking_server -> completed
```

#### Key Configuration Changes
- Subprocess buffer size: Set to 1 (line buffered) for reliability
- Kubectl timeout: Increased to 120 seconds
- Added 1-second delay after streaming for output capture
- Environment variable: PYTHONUNBUFFERED=1

### 🎯 Testing

#### Test Coverage
- Created `test_streaming_claude.py` for streaming verification
- Added `test_flow.py` for execution flow testing
- Comprehensive logging at each execution phase

### 📋 Breaking Changes
- None - all changes are backward compatible

### 🚀 Performance Impact
- Improved real-time visibility into Claude execution
- Slightly increased memory usage during streaming
- Better user experience with immediate feedback

---

**Contributors**: Claude Code Assistant
**Key Fix**: Tasks now properly complete and show real-time output during Claude execution

## v1.2.0 - Web Interface Major Update (2025-06-06)

### 🎉 Major Features

#### Web Interface Complete Rewrite
- **React Frontend Implementation**: Completely rewritten web interface using React for better state management and real-time updates
- **Real-time Log Streaming**: Implemented Server-Sent Events (SSE) for live task log streaming
- **Enhanced Task Dashboard**: Interactive task management with real-time status updates

#### User Experience Improvements
- **Toast Notifications**: Custom toast notification system for better user feedback
- **Form Data Persistence**: DevPod name, GitHub repo, and token are automatically saved in localStorage
- **Auto-log Display**: Task logs are shown by default for running tasks
- **Responsive Design**: Improved mobile and desktop layout with Tailwind CSS

### 🔧 Technical Improvements

#### Code Organization
- **Project Restructuring**: Organized debugging and test files into proper directories
  - `debug/` - Debug scripts (manual_debug.sh, debug_clone.sh)
  - `test_scripts/` - Test files (test_api.py, test_claude_direct.py, etc.)
  - `examples/` - Alternative API server implementations
- **Main Server Runner**: Consolidated to `run_server.py` as the primary entry point

#### Bug Fixes
- **Fixed Claude Execution Hanging**: Resolved heredoc syntax issues causing "EOF: command not found" errors by implementing base64 encoding
- **Resolved Template Conflicts**: Fixed Jinja2 template processing conflicting with React JSX syntax
- **SSE Connection Issues**: Fixed EventSource infinite loop and dependency array problems in React useEffect
- **Log Auto-scroll**: Disabled automatic scrolling for better user experience during log viewing

#### API Enhancements
- **CORS Support**: Added proper CORS headers for cross-origin requests
- **Static File Serving**: Changed from Jinja2 template rendering to static file serving for React compatibility
- **Enhanced Error Handling**: Improved error messages and status reporting

### 🛠️ Infrastructure Changes

#### Development Workflow
- **Improved Testing**: Enhanced test structure with proper file organization
- **Debug Tools**: Added comprehensive debugging scripts and manual testing capabilities
- **Documentation Updates**: Updated README with new project structure and usage instructions

#### Performance Optimizations
- **Efficient State Management**: Optimized React component re-rendering cycles
- **Memory Management**: Proper EventSource cleanup to prevent memory leaks
- **Reduced Network Overhead**: Fixed infinite SSE request loops

### 🔍 Technical Details

#### React Implementation
- Custom toast notification component (replaced ReactToastify dependency)
- useEffect hooks for task lifecycle management
- EventSource API for real-time log streaming
- localStorage integration for form data persistence

#### Server-Side Events (SSE)
- `/api/task-logs/{taskId}/stream` endpoint for real-time log streaming
- JSON-formatted event data with completion status
- Proper connection lifecycle management

#### Code Quality
- Enhanced error handling and logging
- Proper component cleanup and memory management
- Consistent code organization and naming conventions

### 📋 Breaking Changes
- Web interface now requires JavaScript enabled
- Changed from Jinja2 templates to React frontend
- Some API response formats may have changed for better React integration

### 🎯 Next Steps
- Consider adding user authentication
- Implement task filtering and search functionality
- Add export capabilities for task logs
- Enhanced error recovery mechanisms

---

**Contributors**: Claude Code Assistant
**Deployment**: Use `./run_server.py` to start the updated web interface