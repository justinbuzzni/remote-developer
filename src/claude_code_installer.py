"""
Claude Code Installer - Handles Claude Code installation in devpod
"""

import os
from typing import Optional
from loguru import logger
from .devpod_manager import DevpodManager


class ClaudeCodeInstaller:
    """Installer for Claude Code in devpod environments"""
    
    def __init__(self):
        """Initialize Claude Code Installer"""
        self.install_script = """#!/bin/bash
# Claude Code installation script

set -e

echo "Installing Claude Code..."

# Update package manager
sudo apt-get update || true

# Install required dependencies
sudo apt-get install -y curl wget git python3 python3-pip || true

# Download and install Claude Code
# Note: This is a placeholder - actual installation method may vary
# when Claude Code becomes available

echo "Downloading Claude Code..."
# curl -L https://example.com/claude-code/install.sh | bash

# For now, create a mock installation
sudo mkdir -p /usr/local/bin
sudo tee /usr/local/bin/claude-code > /dev/null << 'EOF'
#!/bin/bash
echo "Claude Code v0.1.0 (mock)"
if [[ "$1" == "--version" ]]; then
    echo "0.1.0"
elif [[ "$1" == "execute" ]]; then
    echo "Executing task: $3"
    echo "Task execution simulated successfully"
else
    echo "Usage: claude-code [--version|execute --task <task>]"
fi
EOF

sudo chmod +x /usr/local/bin/claude-code

echo "Claude Code installation completed!"
"""
    
    def install(self, devpod_manager: DevpodManager, version: str = "latest") -> bool:
        """
        Install Claude Code in devpod
        
        Args:
            devpod_manager: DevpodManager instance
            version: Version to install (default: latest)
            
        Returns:
            bool: True if installation successful
        """
        logger.info(f"Installing Claude Code version: {version}")
        
        # Create temporary install script
        temp_script = "/tmp/install_claude_code.sh"
        
        # Write script to devpod
        result = devpod_manager.execute_command(
            f"cat > {temp_script} << 'EOFSCRIPT'\n{self.install_script}\nEOFSCRIPT"
        )
        
        if result["exit_code"] != 0:
            logger.error("Failed to create installation script")
            return False
        
        # Make script executable
        devpod_manager.execute_command(f"chmod +x {temp_script}")
        
        # Execute installation script
        result = devpod_manager.execute_command(f"bash {temp_script}")
        
        if result["exit_code"] == 0:
            logger.success("Claude Code installed successfully")
            # Cleanup
            devpod_manager.execute_command(f"rm -f {temp_script}")
            return True
        else:
            logger.error(f"Installation failed: {result['error']}")
            return False
    
    def verify_installation(self, devpod_manager: DevpodManager) -> bool:
        """
        Verify Claude Code installation
        
        Args:
            devpod_manager: DevpodManager instance
            
        Returns:
            bool: True if Claude Code is properly installed
        """
        result = devpod_manager.execute_command("which claude-code")
        return result["exit_code"] == 0