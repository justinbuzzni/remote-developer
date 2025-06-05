"""Remote Developer package"""

__version__ = "0.1.0"
__author__ = "Remote Developer Team"

from .remote_developer import RemoteDeveloper
from .config import Config
from .devpod_manager import DevpodManager
from .claude_code_installer import ClaudeCodeInstaller

__all__ = [
    "RemoteDeveloper",
    "Config",
    "DevpodManager",
    "ClaudeCodeInstaller",
]