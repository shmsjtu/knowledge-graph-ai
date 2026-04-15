# infrastructure/conversation_manager.py
"""
对话管理器 - 管理多轮对话状态
"""

from typing import List, Dict, Any
import json


class ConversationManager:
    """管理多轮对话状态"""

    def __init__(self, system_prompt: str = None):
        """
        初始化对话管理器

        Args:
            system_prompt: 可选的系统提示词
        """
        self.conversation_history: List[Dict[str, Any]] = []
        if system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": system_prompt
            })

    def set_system_prompt(self, system_prompt: str):
        """
        设置系统提示词

        Args:
            system_prompt: 系统提示词
        """
        # 移除现有的系统提示词
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = system_prompt
        else:
            # 在开头插入系统提示词
            self.conversation_history.insert(0, {
                "role": "system",
                "content": system_prompt
            })

    def update_system_prompt(self, new_system_prompt: str):
        """
        更新系统提示词（别名）

        Args:
            new_system_prompt: 新的系统提示词
        """
        self.set_system_prompt(new_system_prompt)

    def add_user_message(self, content: str):
        """
        添加用户消息

        Args:
            content: 消息内容
        """
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """
        添加助手消息

        Args:
            content: 消息内容
        """
        self.conversation_history.append({"role": "assistant", "content": content})

    def add_tool_call(self, tool_name: str, tool_args: Dict, tool_call_id: str = None):
        """
        添加工具调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            tool_call_id: 工具调用ID
        """
        if tool_call_id is None:
            tool_call_id = f"call_{len(self.conversation_history)}"

        self.conversation_history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args, ensure_ascii=False)
                }
            }]
        })

    def add_tool_result(self, tool_call_id: str, result: str):
        """
        添加工具执行结果

        Args:
            tool_call_id: 工具调用ID
            result: 执行结果
        """
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result
        })

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Returns:
            对话历史列表
        """
        return self.conversation_history.copy()

    def clear_history(self, keep_system: bool = True):
        """
        清空对话历史

        Args:
            keep_system: 是否保留系统提示词
        """
        if keep_system and self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history = [self.conversation_history[0]]
        else:
            self.conversation_history = []

    def get_last_user_message(self) -> str:
        """
        获取最后一条用户消息

        Returns:
            最后一条用户消息内容
        """
        for msg in reversed(self.conversation_history):
            if msg["role"] == "user":
                return msg["content"]
        return ""

    def get_last_assistant_message(self) -> str:
        """
        获取最后一条助手消息

        Returns:
            最后一条助手消息内容
        """
        for msg in reversed(self.conversation_history):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]
        return ""

    def __len__(self):
        """返回消息数量"""
        return len(self.conversation_history)

    def __repr__(self):
        """字符串表示"""
        return f"ConversationManager(messages={len(self.conversation_history)})"
