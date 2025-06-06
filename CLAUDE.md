# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Remote Developer is a Python automation tool that enables remote development workflows by managing devpod containers and integrating Claude Code for automated development tasks.

## Key Architecture

The system follows a modular architecture with clear separation of concerns:

- **RemoteDeveloper** (src/remote_developer.py): Main orchestrator that coordinates all operations including Claude Code setup, task execution, git operations, and deployments
- **DevpodManager** (src/devpod_manager.py): Handles all devpod container interactions - status checking, starting/stopping, command execution, and file transfers
- **ClaudeCodeInstaller** (src/claude_code_installer.py): Manages Claude Code installation within devpod environments
- **Config** (src/config.py): Centralized configuration management using YAML files with support for nested keys and default values

## Common Commands

```bash
# Create virtual environment with Python 3.10
uv venv -p python3.10

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
uv pip install -r requirements.txt

# Install package in development mode
uv pip install -e .

# Run tests
pytest tests/

# Run a specific test
pytest tests/test_remote_developer.py::TestRemoteDeveloper::test_execute_task_success -v

# Deploy (requires configuration)
./deploy.sh [environment]
```

## Development Workflow

1. Configuration is loaded from `config.yaml` - modify this file to change behavior
2. The main entry point is through the RemoteDeveloper class which requires a devpod_name
3. All devpod operations go through DevpodManager which handles container lifecycle
4. Task execution flows: RemoteDeveloper → DevpodManager → execute command in devpod
5. Git operations are automated through GitPython with configurable commit prefixes

## Testing Strategy

- All modules have corresponding test files using pytest
- Heavy use of mocking for external dependencies (devpod, Claude Code)
- Tests focus on success/failure scenarios and edge cases
- Run tests before committing to ensure nothing is broken

## Important Notes

- The ClaudeCodeInstaller currently contains a mock implementation placeholder
- Devpod must be running before executing tasks
- Git operations respect the auto_push configuration setting
- All operations have configurable timeouts and retry mechanisms
- Logging is configurable via config.yaml (console and file outputs)