"""
Remote Developer - Main class for orchestrating Claude Code operations
"""

import os
import json
from typing import Optional, Dict, Any
from loguru import logger
from .devpod_manager import DevpodManager
from .claude_code_installer import ClaudeCodeInstaller
from .config import Config


class RemoteDeveloper:
    """Main class for managing remote development with Claude Code"""
    
    def __init__(self, devpod_name: str, config: Optional[Config] = None):
        """
        Initialize Remote Developer
        
        Args:
            devpod_name: Name of the devpod to work with
            config: Configuration object (optional)
        """
        self.devpod_name = devpod_name
        self.config = config or Config()
        self.devpod_manager = DevpodManager(devpod_name)
        self.claude_installer = ClaudeCodeInstaller()
        
    def setup_claude_code(self) -> bool:
        """
        Setup Claude Code in the devpod
        
        Returns:
            bool: True if setup successful
        """
        logger.info(f"Starting Claude Code setup in {self.devpod_name}")
        
        # Ensure devpod is running
        if not self.devpod_manager.ensure_running():
            logger.error("Failed to start devpod")
            return False
        
        # Install Claude Code
        success = self.claude_installer.install(
            self.devpod_manager,
            self.config.get("claude_code_version", "latest")
        )
        
        if success:
            logger.success("Claude Code installation completed")
        else:
            logger.error("Claude Code installation failed")
            
        return success
    
    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a development task using Claude Code
        
        Args:
            task_description: Description of the task to execute
            
        Returns:
            dict: Result of the task execution
        """
        logger.info(f"Executing task: {task_description}")
        
        # Prepare task command
        command = self._prepare_claude_command(task_description)
        
        # Execute via devpod
        result = self.devpod_manager.execute_command(command)
        
        return {
            "success": result.get("exit_code", 1) == 0,
            "output": result.get("output", ""),
            "error": result.get("error", "")
        }
    
    def commit_changes(self, commit_message: str) -> bool:
        """
        Commit changes made by Claude Code
        
        Args:
            commit_message: Commit message
            
        Returns:
            bool: True if commit successful
        """
        logger.info("Committing changes...")
        
        commands = [
            "git add -A",
            f'git commit -m "{commit_message}"',
            "git push"
        ]
        
        for cmd in commands:
            result = self.devpod_manager.execute_command(cmd)
            if result.get("exit_code", 1) != 0:
                logger.error(f"Failed to execute: {cmd}")
                return False
                
        logger.success("Changes committed successfully")
        return True
    
    def deploy(self) -> bool:
        """
        Deploy the application
        
        Returns:
            bool: True if deployment successful
        """
        logger.info("Starting deployment...")
        
        deploy_script = self.config.get("deploy_script", "./deploy.sh")
        result = self.devpod_manager.execute_command(f"bash {deploy_script}")
        
        success = result.get("exit_code", 1) == 0
        if success:
            logger.success("Deployment completed successfully")
        else:
            logger.error("Deployment failed")
            
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get Claude Code status in the devpod
        
        Returns:
            dict: Status information
        """
        status = {
            "devpod": self.devpod_name,
            "devpod_running": self.devpod_manager.is_running(),
            "claude_code_installed": False,
            "claude_code_version": "unknown"
        }
        
        if status["devpod_running"]:
            # Check Claude Code installation
            result = self.devpod_manager.execute_command("claude-code --version")
            if result.get("exit_code", 1) == 0:
                status["claude_code_installed"] = True
                status["claude_code_version"] = result.get("output", "").strip()
                
        return status
    
    def _prepare_claude_command(self, task: str) -> str:
        """
        Prepare Claude Code command for task execution
        
        Args:
            task: Task description
            
        Returns:
            str: Formatted command
        """
        # Escape quotes in task description
        task_escaped = task.replace('"', '\\"')
        
        # Build Claude Code command
        command = f'claude-code execute --task "{task_escaped}"'
        
        # Add additional flags from config
        if self.config.get("claude_auto_confirm", True):
            command += " --auto-confirm"
            
        if self.config.get("claude_verbose", False):
            command += " --verbose"
            
        return command