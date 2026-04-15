# infrastructure/api_client.py
"""
API客户端 - 封装API调用，统一错误处理
"""

from openai import OpenAI
from typing import List, Dict, Any, Callable
import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exceptions import APIError
from src.core.constants import APIConstants


class APIClient:
    """API客户端 - 封装API调用"""

    def __init__(self, api_key: str, api_endpoint: str):
        """
        初始化API客户端

        Args:
            api_key: API密钥
            api_endpoint: API端点
        """
        self.client = OpenAI(api_key=api_key, base_url=api_endpoint)
        self.api_key = api_key
        self.api_endpoint = api_endpoint

    def call(
        self,
        messages: List[Dict],
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        """
        调用API

        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            json_mode: 是否启用JSON模式（强制输出JSON格式）
            **kwargs: 其他参数

        Returns:
            API响应内容

        Raises:
            APIError: API调用失败
        """
        model = model or APIConstants.DEFAULT_MODEL
        max_tokens = max_tokens or APIConstants.DEFAULT_MAX_TOKENS
        temperature = temperature or APIConstants.DEFAULT_TEMPERATURE

        # 重试机制
        for retry in range(APIConstants.MAX_RETRIES):
            try:
                start_time = time.time()

                # 构建请求参数
                request_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                    **kwargs
                }

                # 如果启用JSON模式，添加response_format参数
                if json_mode:
                    request_params["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**request_params)

                elapsed_time = time.time() - start_time
                print(f"[API调用耗时: {elapsed_time:.2f}秒]")
                return response.choices[0].message.content

            except Exception as e:
                if retry < APIConstants.MAX_RETRIES - 1:
                    time.sleep(APIConstants.RETRY_DELAY)
                    continue
                else:
                    raise APIError(
                        f"API调用失败（重试{retry}次）: {e}",
                        retry_count=retry
                    )

    def call_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        tool_executor: Callable,
        model: str = None,
        max_iterations: int = 5,
        **kwargs
    ) -> str:
        """
        调用API（支持工具调用）

        Args:
            messages: 消息列表
            tools: 工具列表
            tool_executor: 工具执行函数
            model: 模型名称
            max_iterations: 最大迭代次数
            **kwargs: 其他参数

        Returns:
            最终响应内容
        """
        iteration = 0

        while iteration < max_iterations:
            # 调用API
            response = self.client.chat.completions.create(
                model=model or APIConstants.DEFAULT_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=APIConstants.DEFAULT_TEMPERATURE,
                max_tokens=APIConstants.DEFAULT_MAX_TOKENS,
                stream=False,
                **kwargs
            )

            choice = response.choices[0]

            # 如果返回内容（没有工具调用），完成
            if choice.message.content and not choice.message.tool_calls:
                return choice.message.content

            # 如果返回工具调用，执行工具
            if choice.message.tool_calls:
                # 添加助手消息
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in choice.message.tool_calls
                    ]
                })

                # 执行工具
                for tool_call in choice.message.tool_calls:
                    import json
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    try:
                        result = tool_executor(tool_name, **tool_args)
                    except Exception as e:
                        result = f"Error executing tool: {str(e)}"

                    # 添加工具结果
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            iteration += 1

        return "Error: Max iterations reached"
