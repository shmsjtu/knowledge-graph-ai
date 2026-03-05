# api_utils.py
from openai import OpenAI
from typing import List, Dict
import time


def ask_deepseek(messages: List[Dict[str, str]], api_key: str, api_base: str, modell="chat", max_tokens: int = 4096) -> str:
    """
    使用多轮对话消息列表向 DeepSeek API 发送请求。
    
    参数:
        messages (List[Dict[str, str]]): 符合 API 格式的消息列表
        api_key (str): API 密钥
        api_base (str): API 端点
        modell (str): 模型名称，默认为 "chat"
        max_tokens (int): 最大输出 token 数，默认 4096
        
    返回:
        str: 模型的回复内容
    """
    client = OpenAI(
        api_key=api_key,
        base_url=api_base
    )

    # 记录开始时间
    start_time = time.time()
    
    response = client.chat.completions.create(
        model="deepseek-" + modell,
        messages=messages,  # 直接传递消息列表
        temperature=0.7,
        max_tokens=max_tokens,
        stream=False
    )
    
    # 计算运行时间
    elapsed_time = time.time() - start_time
    
    response_content = response.choices[0].message.content
    
    # 打印运行时间和响应内容
    print(f"[模型运行时间: {elapsed_time:.2f}秒]")
    print(response_content)
    print("-" * 80)
    
    return response_content

