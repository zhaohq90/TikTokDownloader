"""
Web UI 模块
提供图形化界面进行账号作品批量下载和单个作品下载
"""

from .server import WebUIServer
from .manager import WebUIManager

__all__ = ["WebUIServer", "WebUIManager"]