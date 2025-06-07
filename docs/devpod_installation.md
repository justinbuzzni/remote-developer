# DevPod Installation Guide

This guide covers how to install DevPod on different operating systems for use with Remote Developer.

## What is DevPod?

DevPod is an open-source development environment manager that creates reproducible development environments. It's used by Remote Developer to create isolated containers for executing tasks.

## Installation

### Linux (Ubuntu/Debian)

#### Method 1: Direct Download (Recommended)
```bash
# Download latest DevPod CLI
curl -L -o devpod "https://github.com/loft-sh/devpod/releases/latest/download/devpod-linux-amd64"

# Make executable
chmod +x devpod

# Install to system (requires sudo)
sudo mv devpod /usr/local/bin

# OR install to user directory (no sudo required)
mkdir -p ~/bin
mv devpod ~/bin/
echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

#### Method 2: Using Package Manager
```bash
# Add DevPod repository
curl -fsSL https://download.devpod.sh/linux/latest/devpod.gpg | sudo apt-key add -
echo "deb https://download.devpod.sh/linux/latest /" | sudo tee /etc/apt/sources.list.d/devpod.list

# Install DevPod
sudo apt update
sudo apt install devpod
```

### macOS

#### Method 1: Homebrew (Recommended)
```bash
brew install loft-sh/tap/devpod
```

#### Method 2: Direct Download
```bash
# Intel Macs
curl -L -o devpod "https://github.com/loft-sh/devpod/releases/latest/download/devpod-darwin-amd64"

# Apple Silicon Macs
curl -L -o devpod "https://github.com/loft-sh/devpod/releases/latest/download/devpod-darwin-arm64"

chmod +x devpod
sudo mv devpod /usr/local/bin
```

### Windows

#### Method 1: Chocolatey
```powershell
choco install devpod
```

#### Method 2: Direct Download
1. Download the latest Windows binary from [DevPod Releases](https://github.com/loft-sh/devpod/releases/latest)
2. Extract `devpod-windows-amd64.exe` to a directory in your PATH
3. Rename to `devpod.exe`

## Verification

After installation, verify DevPod is working:

```bash
devpod version
```

You should see output similar to:
```
v0.6.15
```

## Prerequisites

DevPod requires one of the following container runtimes:

### Docker (Recommended)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io
sudo usermod -aG docker $USER
newgrp docker

# macOS
brew install docker
# Or download Docker Desktop

# Windows
# Download and install Docker Desktop from docker.com
```

### Podman (Alternative)
```bash
# Ubuntu/Debian
sudo apt install podman

# macOS
brew install podman

# Windows
# Use WSL2 with Linux installation
```

## Configuration for Remote Developer

### Initialize DevPod
```bash
# Set up DevPod with Docker provider
devpod provider add docker
devpod provider use docker
```

### Test DevPod Installation
```bash
# Create a test workspace
devpod up https://github.com/loft-sh/devpod-example-python --ide none

# List workspaces
devpod list

# Delete test workspace
devpod delete devpod-example-python
```

## Kubernetes Integration (Optional)

If you're using Remote Developer with Kubernetes:

### Install kubectl
```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin

# macOS
brew install kubectl

# Windows
choco install kubernetes-cli
```

### Configure DevPod for Kubernetes
```bash
# Add Kubernetes provider
devpod provider add kubernetes
devpod provider use kubernetes

# Configure with your kubeconfig
devpod provider set-options kubernetes KUBE_CONFIG_PATH=~/.kube/config
```

## Troubleshooting

### Common Issues

1. **DevPod command not found**
   - Ensure DevPod is in your PATH
   - Restart your terminal or run `source ~/.bashrc`

2. **Permission denied errors**
   - Make sure devpod binary is executable: `chmod +x devpod`
   - Check if user is in docker group: `groups $USER`

3. **Docker connection errors**
   - Ensure Docker is running: `docker ps`
   - Check Docker permissions: `docker run hello-world`

4. **Kubernetes connection issues**
   - Verify kubectl works: `kubectl get nodes`
   - Check kubeconfig: `kubectl config current-context`

### Logs and Debugging

```bash
# Enable debug logging
export DEVPOD_DEBUG=true

# View DevPod logs
devpod logs

# Check provider status
devpod provider list
```

## Next Steps

After installing DevPod:

1. Configure your development environment providers
2. Test workspace creation and deletion
3. Integrate with Remote Developer configuration
4. Set up your preferred IDE (VS Code, JetBrains, etc.)

## Useful Commands

```bash
# List all workspaces
devpod list

# Create workspace from Git repository
devpod up https://github.com/user/repo

# SSH into workspace
devpod ssh workspace-name

# Stop workspace
devpod stop workspace-name

# Delete workspace
devpod delete workspace-name

# Update DevPod
devpod upgrade
```

## Resources

- [DevPod Official Documentation](https://devpod.sh/docs)
- [DevPod GitHub Repository](https://github.com/loft-sh/devpod)
- [Remote Developer Documentation](../README.md)

## Version Information

This guide was tested with:
- DevPod v0.6.15
- Docker 20.10+
- Kubernetes 1.25+
- Ubuntu 20.04 LTS

---

**Note**: DevPod is actively developed. Check the [official releases page](https://github.com/loft-sh/devpod/releases) for the latest version and features.