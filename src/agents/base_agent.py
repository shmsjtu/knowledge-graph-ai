# agents/base_agent.py
"""
智能体基类 - 定义智能体通用接口和行为
"""

from abc import ABC, abstractmethod
from typing import Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.infrastructure.api_client import APIClient
from src.infrastructure.conversation_manager import ConversationManager
from src.infrastructure.logger import Logger


class BaseAgent(ABC):
    """智能体基类"""

    def __init__(
        self,
        api_client: APIClient,
        conversation_manager: Optional[ConversationManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        初始化智能体

        Args:
            api_client: API客户端实例
            conversation_manager: 对话管理器实例（可选）
            logger: 日志记录器实例（可选）
        """
        self.api_client = api_client
        self.conversation_manager = conversation_manager or ConversationManager()
        self.logger = logger or Logger(self.__class__.__name__)

    def set_system_prompt(self, system_prompt: str):
        """
        设置系统提示词

        Args:
            system_prompt: 系统提示词
        """
        self.conversation_manager.set_system_prompt(system_prompt)

    def initialize(self):
        """
        初始化智能体（子类可重写）
        默认行为：清空对话历史，准备新的对话
        """
        self.reset()

    def update_system_prompt(self, new_system_prompt: str):
        """
        更新系统提示词

        Args:
            new_system_prompt: 新的系统提示词
        """
        self.conversation_manager.update_system_prompt(new_system_prompt)

    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        执行智能体任务（子类实现）

        Returns:
            执行结果
        """
        pass

    def reset(self):
        """重置智能体状态"""
        self.conversation_manager.clear_history(keep_system=True)

    def get_conversation_history(self) -> list:
        """获取对话历史"""
        return self.conversation_manager.get_history()

    def _call_api(self, model: str = None, json_mode: bool = False, **kwargs) -> str:
        """
        调用API的统一方法

        Args:
            model: 模型名称
            json_mode: 是否启用JSON模式
            **kwargs: 其他API参数

        Returns:
            API响应内容
        """
        try:
            response = self.api_client.call(
                messages=self.conversation_manager.get_history(),
                model=model,
                json_mode=json_mode,
                **kwargs
            )
            return response
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            raise
