# utils/json_parser.py
"""
JSON解析器 - 统一JSON解析逻辑，支持自动修复
"""

import json
import re
from typing import Any
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exceptions import JSONParseError


class JSONParser:
    """JSON解析器 - 统一JSON解析逻辑"""

    @staticmethod
    def parse(content: str, repair: bool = True) -> Any:
        """
        解析JSON字符串

        Args:
            content: JSON字符串
            repair: 是否尝试修复损坏的JSON

        Returns:
            解析后的数据

        Raises:
            JSONParseError: JSON解析失败
        """
        content = content.strip()

        # 尝试从Markdown代码块中提取
        json_str = JSONParser._extract_from_markdown(content)

        # 如果需要修复
        if repair:
            json_str = JSONParser._repair_json(json_str)

        # 解析JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JSONParseError(f"JSON解析失败: {e}", raw_content=content)

    @staticmethod
    def _extract_from_markdown(content: str) -> str:
        """从Markdown代码块中提取JSON"""
        if "```json" in content:
            try:
                return content.split("```json")[1].split("```")[0].strip()
            except:
                pass

        if "```" in content:
            try:
                parts = content.split("```")
                if len(parts) >= 2:
                    return parts[1].strip()
            except:
                pass

        return content

    @staticmethod
    def _repair_json(json_str: str) -> str:
        """尝试修复损坏的JSON"""
        # 检查是否不完整
        if json_str.startswith("{") and not json_str.endswith("}"):
            # 尝试找到最后一个完整的对象
            last_complete = json_str.rfind("},")
            if last_complete > 0:
                json_str = json_str[:last_complete+1] + "]}"
            else:
                # 简单地补充缺失的括号
                open_braces = json_str.count("{") - json_str.count("}")
                open_brackets = json_str.count("[") - json_str.count("]")
                json_str = json_str + "]" * open_brackets + "}" * open_braces

        elif json_str.startswith("[") and not json_str.endswith("]"):
            # 尝试找到最后一个完整的元素
            last_complete = json_str.rfind("},")
            if last_complete > 0:
                json_str = json_str[:last_complete+1] + "]"
            else:
                # 简单地补充缺失的括号
                open_brackets = json_str.count("[") - json_str.count("]")
                json_str = json_str + "]" * open_brackets

        return json_str

    @staticmethod
    def to_json_string(data: Any, indent: int = 2) -> str:
        """
        将数据转换为JSON字符串

        Args:
            data: 数据对象
            indent: 缩进

        Returns:
            JSON字符串
        """
        return json.dumps(data, ensure_ascii=False, indent=indent)
