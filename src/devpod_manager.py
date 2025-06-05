"""
Devpod Manager - Handles devpod operations
"""

import subprocess
import json
from typing import Dict, Any, Optional
from loguru import logger


class DevpodManager:
    """Manager for devpod operations"""
    
    def __init__(self, devpod_name: str):
        """
        Initialize Devpod Manager
        
        Args:
            devpod_name: Name of the devpod
        """
        self.devpod_name = devpod_name
        
    def is_running(self) -> bool:
        """
        Check if devpod is running
        
        Returns:
            bool: True if devpod is running
        """
        try:
            result = subprocess.run(
                ["devpod", "list", "--output", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            devpods = json.loads(result.stdout)
            for pod in devpods:
                if pod.get("name") == self.devpod_name:
                    return pod.get("status") == "Running"
                    
            return False
        except Exception as e:
            logger.error(f"Failed to check devpod status: {e}")
            return False
    
    def ensure_running(self) -> bool:
        """
        Ensure devpod is running, start if needed
        
        Returns:
            bool: True if devpod is running
        """
        if self.is_running():
            logger.info(f"Devpod {self.devpod_name} is already running")
            return True
            
        logger.info(f"Starting devpod {self.devpod_name}...")
        try:
            subprocess.run(
                ["devpod", "up", self.devpod_name],
                check=True
            )
            logger.success(f"Devpod {self.devpod_name} started successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start devpod: {e}")
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a command in the devpod
        
        Args:
            command: Command to execute
            
        Returns:
            dict: Execution result with exit_code, output, and error
        """
        logger.debug(f"Executing in devpod: {command}")
        
        try:
            result = subprocess.run(
                ["devpod", "ssh", self.devpod_name, "--", command],
                capture_output=True,
                text=True
            )
            
            return {
                "exit_code": result.returncode,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "exit_code": -1,
                "output": "",
                "error": str(e)
            }
    
    def copy_to_devpod(self, local_path: str, remote_path: str) -> bool:
        """
        Copy file to devpod
        
        Args:
            local_path: Local file path
            remote_path: Remote path in devpod
            
        Returns:
            bool: True if copy successful
        """
        try:
            subprocess.run(
                ["devpod", "cp", local_path, f"{self.devpod_name}:{remote_path}"],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    def copy_from_devpod(self, remote_path: str, local_path: str) -> bool:
        """
        Copy file from devpod
        
        Args:
            remote_path: Remote path in devpod
            local_path: Local file path
            
        Returns:
            bool: True if copy successful
        """
        try:
            subprocess.run(
                ["devpod", "cp", f"{self.devpod_name}:{remote_path}", local_path],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to copy file: {e}")
            return False