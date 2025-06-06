# Remote Developer - Auto PR Generator

This system automates the creation of pull requests using DevPod containers and Claude Code.

## Features

- **Automated DevPod Management**: Creates or uses existing DevPod containers
- **GitHub Integration**: Clones repositories, creates branches, and submits PRs
- **Claude Code Integration**: Executes development tasks using AI
- **Web Interface**: User-friendly form for task submission
- **Real-time Dashboard**: Monitor task progress and status
- **Port Forwarding**: Automatic local access to services created in DevPod

## Quick Start

1. Install dependencies:
```bash
uv venv -p python3.10
source .venv/bin/activate
uv pip install -r requirements.txt
```

2. Start the server:
```bash
python run_server.py
```

3. Open http://localhost:5000 in your browser

4. Fill in the form:
   - DevPod Name: Name for your development container
   - GitHub Repository: username/repo format
   - GitHub Token: Your personal access token
   - Task Description: What you want Claude Code to build

## Test Example

To test with the provided example:
- DevPod Name: `auto-worker-demo`
- GitHub Repository: `justinbuzzni/auto-worker-demo`
- GitHub Token: [Your token]
- Task Description: `streamlit app that displays input text on screen`

## Architecture

The system consists of:
- **API Server** (Flask): Handles task creation and management
- **DevPod Manager**: Controls container lifecycle
- **Claude Code Integration**: Executes development tasks
- **GitHub Integration**: Creates branches and pull requests
- **Web Dashboard**: Real-time task monitoring

## API Endpoints

- `POST /api/create-task`: Create a new automated task
- `GET /api/task-status/<task_id>`: Get status of a specific task
- `GET /api/tasks`: List all tasks
- `GET /api/dashboard`: Get dashboard statistics