# infrastructure/__init__.py
"""
基础设施层 - 提供API客户端、对话管理器、日志管理器等基础服务
"""

from .api_client import APIClient
from .conversation_manager import ConversationManager
from .logger import Logger

__all__ = [
    'APIClient',
    'ConversationManager',
    'Logger',
]
