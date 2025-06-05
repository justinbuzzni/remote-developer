"""
Configuration module for Remote Developer
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from loguru import logger


class Config:
    """Configuration manager for Remote Developer"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or "config.yaml"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults
        
        Returns:
            dict: Configuration dictionary
        """
        default_config = {
            "claude_code_version": "latest",
            "claude_auto_confirm": True,
            "claude_verbose": False,
            "deploy_script": "./deploy.sh",
            "git_auto_push": True,
            "log_level": "INFO",
            "devpod": {
                "default_image": "ubuntu:22.04",
                "resources": {
                    "cpu": "2",
                    "memory": "4Gi"
                }
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    # Merge with defaults
                    default_config.update(file_config)
                    logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}, using defaults")
        
        return default_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (supports nested keys with dots)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key (supports nested keys with dots)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> bool:
        """
        Save configuration to file
        
        Args:
            path: Path to save to (uses default if not provided)
            
        Returns:
            bool: True if save successful
        """
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"Configuration saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False