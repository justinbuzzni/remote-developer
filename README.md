# Remote Developer

A Flask-based API server that automates development workflows using Claude Code in DevPod containers. Execute AI-powered development tasks, manage git repositories, and deploy applications automatically.

## 🚀 Features

- **Web Interface**: User-friendly dashboard for managing development tasks
- **Claude Code Integration**: Execute AI-powered development tasks in isolated DevPod containers
- **Automated Git Workflow**: Clone repos, create branches, commit changes automatically
- **Real-time Monitoring**: Stream logs and track task progress in real-time
- **Application Detection**: Automatically detect and deploy Streamlit/FastAPI applications
- **Port Forwarding**: Access deployed applications through automatic port forwarding
- **Task Persistence**: Resume tasks after server restarts

## 📁 Project Structure

```
remote-developer/
├── src/                      # Source code
│   ├── api_server.py         # Main API server implementation
│   ├── remote_developer.py   # Core remote developer logic
│   ├── devpod_manager.py     # DevPod container management
│   ├── claude_code_installer.py  # Claude Code installation
│   ├── config.py             # Configuration management
│   └── docker_manager.py     # Docker integration (experimental)
├── templates/                # Web interface templates
│   └── index.html            # Main dashboard
├── tests/                    # Unit tests
│   └── test_remote_developer.py
├── test_scripts/             # Test and validation scripts
│   ├── test_api.py           # API endpoint tests
│   ├── test_claude_direct.py # Direct Claude execution test
│   ├── test_real_task.py     # Real task execution test
│   └── ...
├── debug/                    # Debugging scripts
│   ├── manual_debug.sh       # Manual debugging script
│   ├── manual_debug.success.sh  # Working debug script
│   └── debug_clone.sh        # Repository cloning debug
├── examples/                 # Example implementations
│   ├── api_server_original.py  # Original API server
│   ├── simple_api_server.py    # Simplified version
│   └── ...
├── run_server.py             # Main server runner
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── CLAUDE.md                 # Claude Code instructions
└── .env.example              # Environment variables example
```

## 🛠 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/justinbuzzni/remote-developer.git
   cd remote-developer
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GitHub token
   ```

5. **Configure DevPod** (if not already installed):
   ```bash
   # Install DevPod from https://devpod.sh/
   # Configure Kubernetes provider
   devpod provider use kubernetes
   ```

## 🚀 Quick Start

1. **Start the API server**:
   ```bash
   ./run_server.py
   ```
   The server will start at http://localhost:15001

2. **Open the web interface**:
   Navigate to http://localhost:15001 in your browser

3. **Create a task**:
   - Enter DevPod name (e.g., "auto-worker-demo")
   - Enter GitHub repository (e.g., "username/repo")
   - Enter your GitHub token
   - Describe the task (e.g., "Create a Streamlit app that displays user input")
   - Click "Create Task"

4. **Monitor progress**:
   - Watch real-time logs in the dashboard
   - Access deployed applications via provided URLs

## 📡 API Endpoints

### Create Task
```bash
POST /api/create-task
Content-Type: application/json

{
  "devpod_name": "auto-worker-demo",
  "github_repo": "username/repo",
  "github_token": "YOUR_GITHUB_TOKEN",
  "task_description": "Create a simple web app"
}
```

### Get Task Status
```bash
GET /api/task-status/<task_id>
```

### List All Tasks
```bash
GET /api/tasks
```

### Dashboard Data
```bash
GET /api/dashboard
```

### Stream Task Logs
```bash
GET /api/task-logs/<task_id>/stream
```

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
devpod:
  provider: kubernetes
  namespace: devpod

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

git:
  auto_commit: true
  auto_push: false
  commit_prefix: "Auto: "
```

## 🧪 Testing

Run unit tests:
```bash
pytest tests/
```

Run integration tests:
```bash
python test_scripts/test_api.py
```

Debug Claude execution:
```bash
./debug/manual_debug.success.sh
```

## 🐛 Troubleshooting

### DevPod Connection Issues
- Ensure DevPod is running: `devpod list`
- Check pod status: `kubectl get pods -n devpod`
- Verify Kubernetes connection: `kubectl cluster-info`

### Claude Code Not Found
- Claude Code requires authentication on first use
- Check installation in DevPod: `devpod ssh <name> -- which claude`
- Manual authentication: `kubectl exec -it -n devpod <pod-name> -- claude`

### Port Forwarding Issues
- Check if port is already in use
- Verify pod is running: `kubectl get pods -n devpod`
- Manual port forward: `kubectl port-forward -n devpod <pod> 8501:8501`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Claude Code](https://claude.ai/code) integration
- Powered by [DevPod](https://devpod.sh/) for container management
- Uses Flask for the web framework