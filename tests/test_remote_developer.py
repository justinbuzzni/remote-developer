"""
Tests for Remote Developer main class
"""

import pytest
from unittest.mock import Mock, patch
from src.remote_developer import RemoteDeveloper
from src.config import Config


class TestRemoteDeveloper:
    """Test cases for RemoteDeveloper class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "claude_code_version": "latest",
            "claude_auto_confirm": True,
            "claude_verbose": False,
            "deploy_script": "./deploy.sh"
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_devpod_manager(self):
        """Create mock devpod manager"""
        with patch('src.remote_developer.DevpodManager') as mock:
            manager = Mock()
            manager.ensure_running.return_value = True
            manager.execute_command.return_value = {
                "exit_code": 0,
                "output": "Success",
                "error": ""
            }
            manager.is_running.return_value = True
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_claude_installer(self):
        """Create mock Claude Code installer"""
        with patch('src.remote_developer.ClaudeCodeInstaller') as mock:
            installer = Mock()
            installer.install.return_value = True
            mock.return_value = installer
            yield installer
    
    def test_initialization(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test RemoteDeveloper initialization"""
        rd = RemoteDeveloper("test-pod", mock_config)
        assert rd.devpod_name == "test-pod"
        assert rd.config == mock_config
    
    def test_setup_claude_code_success(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test successful Claude Code setup"""
        rd = RemoteDeveloper("test-pod", mock_config)
        result = rd.setup_claude_code()
        
        assert result is True
        assert rd.devpod_manager.ensure_running.called
        assert rd.claude_installer.install.called
    
    def test_setup_claude_code_devpod_failure(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test Claude Code setup when devpod fails to start"""
        rd = RemoteDeveloper("test-pod", mock_config)
        rd.devpod_manager.ensure_running.return_value = False
        
        result = rd.setup_claude_code()
        assert result is False
    
    def test_execute_task(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test task execution"""
        rd = RemoteDeveloper("test-pod", mock_config)
        result = rd.execute_task("Test task")
        
        assert result["success"] is True
        assert result["output"] == "Success"
        rd.devpod_manager.execute_command.assert_called()
    
    def test_commit_changes(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test committing changes"""
        rd = RemoteDeveloper("test-pod", mock_config)
        result = rd.commit_changes("Test commit")
        
        assert result is True
        # Should have called git add, commit, and push
        assert rd.devpod_manager.execute_command.call_count == 3
    
    def test_get_status(self, mock_config, mock_devpod_manager, mock_claude_installer):
        """Test getting status"""
        rd = RemoteDeveloper("test-pod", mock_config)
        status = rd.get_status()
        
        assert status["devpod"] == "test-pod"
        assert status["devpod_running"] is True