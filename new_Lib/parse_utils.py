# parse_utils.py
import re
import json
import ast
import numpy as np
from typing import List, Dict, Optional


def fix_json_escapes(json_str: str) -> str:
    """
    修复 JSON 字符串中的转义问题，特别是 LaTeX 公式中的反斜杠。
    
    参数:
        json_str: 可能包含未转义反斜杠的 JSON 字符串
        
    返回:
        str: 修复后的 JSON 字符串
    """
    # 使用正则表达式来修复字符串值中的反斜杠
    # 匹配 JSON 字符串值：": "..." 或 ": "..."
    def fix_string_value(match):
        prefix = match.group(1)  # "key": "
        content = match.group(2)  # 字符串内容
        suffix = match.group(3)  # "
        
        # 修复内容中的反斜杠（除了已经是有效转义的）
        fixed_content = re.sub(
            r'\\(?!["\\/bfnrtu])',  # 匹配不是有效 JSON 转义的反斜杠
            r'\\\\',  # 转义为 \\
            content
        )
        
        return prefix + fixed_content + suffix
    
    # 匹配 JSON 字符串值
    pattern = r'("(?:[^"\\]|\\.)*"\s*:\s*")((?:[^"\\]|\\.)*)(")'
    
    # 需要多次应用，因为嵌套的引号可能影响匹配
    fixed = json_str
    prev_fixed = None
    max_iterations = 10
    
    while prev_fixed != fixed and max_iterations > 0:
        prev_fixed = fixed
        fixed = re.sub(pattern, fix_string_value, fixed)
        max_iterations -= 1
    
    return fixed


def extract_json_from_response(raw_response: str) -> Optional[str]:
    """
    从响应中提取 JSON 部分。
    
    参数:
        raw_response: 原始响应字符串
        
    返回:
        Optional[str]: 提取的 JSON 字符串，如果未找到则返回 None
    """
    # 首先尝试提取 JSON 代码块
    json_match = re.search(r'```json\s*(\[.*?\])\s*```', raw_response, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    
    # 如果没有代码块，尝试直接查找 JSON 数组（从 [ 开始到匹配的 ] 结束）
    bracket_count = 0
    start_idx = raw_response.find('[')
    if start_idx != -1:
        for i in range(start_idx, len(raw_response)):
            if raw_response[i] == '[':
                bracket_count += 1
            elif raw_response[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    return raw_response[start_idx:i+1]
    
    return None


def extract_string_value(text: str, start_pos: int) -> tuple:
    """
    从指定位置开始提取 JSON 字符串值，能够处理未转义的反斜杠。
    使用简单的状态机：遇到未转义的引号就结束。
    
    参数:
        text: 文本
        start_pos: 开始位置（应该在引号位置）
        
    返回:
        tuple: (值, 结束位置)，如果失败返回 (None, start_pos)
    """
    if start_pos >= len(text) or text[start_pos] != '"':
        return None, start_pos
    
    value = []
    i = start_pos + 1  # 跳过开始引号
    
    while i < len(text):
        char = text[i]
        
        if char == '"':
            # 检查前面的字符是否是反斜杠
            # 需要检查是否是转义的引号 \" 或双反斜杠加引号 \\"
            if i > start_pos:
                # 计算连续反斜杠的数量
                backslash_count = 0
                j = i - 1
                while j >= start_pos + 1 and text[j] == '\\':
                    backslash_count += 1
                    j -= 1
                
                # 如果反斜杠数量是偶数（包括0），这是字符串结束
                # 如果反斜杠数量是奇数，这是转义的引号
                if backslash_count % 2 == 0:
                    # 字符串结束
                    return ''.join(value), i + 1
                else:
                    # 转义的引号，添加到值中
                    value.append(char)
            else:
                # 字符串结束
                return ''.join(value), i + 1
        else:
            value.append(char)
        
        i += 1
    
    # 如果没找到结束引号，返回已提取的内容
    return ''.join(value), i


def extract_json_objects_with_regex(json_str: str) -> List[Dict]:
    """
    使用更智能的方法从 JSON 字符串中提取对象，能够处理未转义的反斜杠。
    
    参数:
        json_str: JSON 字符串
        
    返回:
        List[Dict]: 提取的对象列表
    """
    objects = []
    
    # 查找所有对象：从 { 开始到 } 结束
    i = 0
    while i < len(json_str):
        # 查找对象开始
        obj_start = json_str.find('{', i)
        if obj_start == -1:
            break
        
        # 查找对应的对象结束
        brace_count = 0
        obj_end = -1
        for j in range(obj_start, len(json_str)):
            if json_str[j] == '{':
                brace_count += 1
            elif json_str[j] == '}':
                brace_count -= 1
                if brace_count == 0:
                    obj_end = j + 1
                    break
        
        if obj_end == -1:
            break
        
        # 提取对象内容
        obj_str = json_str[obj_start:obj_end]
        
        # 尝试提取字段
        obj = {}
        
        # 提取 name
        name_match = re.search(r'"name"\s*:\s*"', obj_str)
        if name_match:
            name, name_end = extract_string_value(obj_str, name_match.end() - 1)
            if name is not None:
                obj["name"] = name.replace('\\"', '"').replace('\\\\', '\\')
        
        # 提取 desc
        desc_match = re.search(r'"desc"\s*:\s*"', obj_str)
        if desc_match:
            desc, desc_end = extract_string_value(obj_str, desc_match.end() - 1)
            if desc is not None:
                obj["desc"] = desc.replace('\\"', '"').replace('\\\\', '\\')
        
        # 提取 classification（可选）
        class_match = re.search(r'"classification"\s*:\s*"', obj_str)
        if class_match:
            classification, class_end = extract_string_value(obj_str, class_match.end() - 1)
            if classification is not None:
                obj["classification"] = classification.replace('\\"', '"').replace('\\\\', '\\')
        
        if "name" in obj and "desc" in obj:
            objects.append(obj)
        
        i = obj_end
    
    return objects


def parse_json_with_fallback(json_str: str) -> Optional[List]:
    """
    尝试解析 JSON，如果失败则尝试修复转义问题后再次解析，最后使用正则表达式提取。
    
    参数:
        json_str: JSON 字符串
        
    返回:
        Optional[List]: 解析后的列表，如果失败则返回 None
    """
    # 第一次尝试：直接解析
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    
    # 第二次尝试：修复转义后解析
    try:
        fixed_json = fix_json_escapes(json_str)
        data = json.loads(fixed_json)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    
    # 第三次尝试：使用正则表达式提取对象
    objects = extract_json_objects_with_regex(json_str)
    if objects:
        return objects
    
    return None


def parse_answers_1(raw_response: str, theme: str, texts: str = "") -> List[dict]:
    """
    解析第一类答案格式（定义类），从 JSON 格式中提取 name、desc 和 importance。
    支持修复包含未转义反斜杠的 JSON。
    
    参数:
        raw_response: 原始响应字符串（可能包含思考过程和 JSON）
        theme: 主题字符串
        texts: 原始文本内容，将被添加到每个对象的 texts 字段中
        
    返回:
        List[dict]: 解析后的对象列表
    """
    result = []
    
    # 提取 JSON 部分
    json_str = extract_json_from_response(raw_response)
    
    if json_str:
        # 尝试解析 JSON
        data = parse_json_with_fallback(json_str)
        
        if data and isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "desc" in item:
                    # 提取 importance，默认为 3
                    importance = item.get("importance", 3)
                    try:
                        importance = int(importance)
                        # 确保在 1-5 范围内
                        importance = max(1, min(5, importance))
                    except (ValueError, TypeError):
                        importance = 3
                    
                    obj = {
                        "name": str(item["name"]),
                        "desc": str(item["desc"]),
                        "classification": "定义",
                        "theme": theme,
                        "importance": importance,
                        "texts": texts
                    }
                    result.append(obj)
            return result
    
    # 如果 JSON 解析失败，尝试逐行解析（兼容旧格式）
    lines = raw_response.strip().split('\n')
    pattern = r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"desc"\s*:\s*"((?:[^"\\]|\\.)*)"(?:\s*,\s*"importance"\s*:\s*(\d+))?'
    for line in lines:
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            match = re.search(pattern, line)
            if match:
                name = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
                desc = match.group(2).replace('\\"', '"').replace('\\\\', '\\')
                importance_str = match.group(3)
                if importance_str:
                    try:
                        importance = max(1, min(5, int(importance_str)))
                    except (ValueError, TypeError):
                        importance = 3
                else:
                    importance = 3
                obj = {
                    "name": name,
                    "desc": desc,
                    "classification": "定义",
                    "theme": theme,
                    "importance": importance,
                    "texts": texts
                }
                result.append(obj)
        except Exception:
            continue
    
    return result


def parse_answers_2(raw_response: str, theme: str, texts: str = "") -> List[dict]:
    """
    解析第二类答案格式（例子、命题类），从 JSON 格式中提取 name、desc、classification 和 importance。
    支持修复包含未转义反斜杠的 JSON。
    
    参数:
        raw_response: 原始响应字符串（可能包含思考过程和 JSON）
        theme: 主题字符串
        texts: 原始文本内容，将被添加到每个对象的 texts 字段中
        
    返回:
        List[dict]: 解析后的对象列表
    """
    result = []
    
    # 提取 JSON 部分
    json_str = extract_json_from_response(raw_response)
    
    if json_str:
        # 尝试解析 JSON
        data = parse_json_with_fallback(json_str)
        
        if data and isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "desc" in item:
                    # 提取 importance，默认为 3
                    importance = item.get("importance", 3)
                    try:
                        importance = int(importance)
                        # 确保在 1-5 范围内
                        importance = max(1, min(5, importance))
                    except (ValueError, TypeError):
                        importance = 3
                    
                    obj = {
                        "name": str(item["name"]),
                        "desc": str(item["desc"]),
                        "classification": str(item.get("classification", "")),
                        "theme": theme,
                        "importance": importance,
                        "texts": texts
                    }
                    result.append(obj)
            return result
    
    # 如果 JSON 解析失败，尝试逐行解析（兼容旧格式）
    lines = raw_response.strip().split('\n')
    pattern = r'"name"\s*:\s*"([^"]*(?:\\.[^"]*)*)"\s*,\s*"desc"\s*:\s*"([^"]*(?:\\.[^"]*)*)"\s*,\s*"classification"\s*:\s*"([^"]*(?:\\.[^"]*)*)"(?:\s*,\s*"importance"\s*:\s*(\d+))?'
    for line in lines:
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            match = re.search(pattern, line)
            if match:
                name = match.group(1).replace('\\"', '"').replace('\\\\', '\\')
                desc = match.group(2).replace('\\"', '"').replace('\\\\', '\\')
                classification = match.group(3).replace('\\"', '"').replace('\\\\', '\\')
                importance_str = match.group(4)
                if importance_str:
                    try:
                        importance = max(1, min(5, int(importance_str)))
                    except (ValueError, TypeError):
                        importance = 3
                else:
                    importance = 3
                obj = {
                    "name": name,
                    "desc": desc,
                    "classification": classification,
                    "theme": theme,
                    "importance": importance,
                    "texts": texts
                }
                result.append(obj)
        except Exception:
            continue
    
    return result


def convert_string_to_matrix(data_str: str) -> np.ndarray:
    """
    将字符串格式的矩阵转换为 numpy 数组。
    支持从包含思考过程的响应中提取矩阵（JSON 格式或直接数组格式）。
    
    参数:
        data_str: 字符串格式的矩阵数据（可能包含思考过程和 JSON 代码块）
        
    返回:
        np.ndarray: 转换后的矩阵
        
    异常:
        ValueError: 解析失败或格式不正确时抛出
    """
    matrix_data = None
    
    # 方法1: 尝试从 JSON 代码块中提取 matrix 字段
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', data_str, re.DOTALL)
    if json_match:
        try:
            json_obj = json.loads(json_match.group(1))
            if isinstance(json_obj, dict) and "matrix" in json_obj:
                matrix_data = json_obj["matrix"]
        except json.JSONDecodeError:
            pass
    
    # 方法2: 如果没有找到 JSON 代码块，尝试直接查找 JSON 对象
    if matrix_data is None:
        json_match = re.search(r'\{"matrix"\s*:\s*(\[.*?\])\}', data_str, re.DOTALL)
        if json_match:
            try:
                matrix_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
    
    # 方法3: 尝试直接查找矩阵数组格式 [[...], [...], ...]
    if matrix_data is None:
        # 查找最外层的数组结构
        bracket_count = 0
        start_idx = data_str.find('[')
        if start_idx != -1:
            for i in range(start_idx, len(data_str)):
                if data_str[i] == '[':
                    bracket_count += 1
                elif data_str[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        # 找到了完整的数组
                        array_str = data_str[start_idx:i+1]
                        try:
                            matrix_data = json.loads(array_str)
                        except json.JSONDecodeError:
                            # 如果 JSON 解析失败，尝试使用 ast.literal_eval
                            try:
                                cleaned_str = re.sub(r'\s+', '', array_str)
                                matrix_data = ast.literal_eval(cleaned_str)
                            except (ValueError, SyntaxError):
                                pass
                        break
    
    # 方法4: 如果以上都失败，尝试直接解析整个字符串（兼容旧格式）
    if matrix_data is None:
        try:
            cleaned_str = re.sub(r'\s+', '', data_str)
            matrix_data = ast.literal_eval(cleaned_str)
        except (ValueError, SyntaxError):
            raise ValueError(f"无法从响应中提取矩阵数据。响应内容: {data_str[:200]}...")
    
    # 验证和转换
    if not isinstance(matrix_data, list) or not all(isinstance(row, list) for row in matrix_data):
        raise ValueError("解析后的数据不是列表的列表格式")
    
    n = len(matrix_data)
    if n == 0:
        raise ValueError("输入数据不能为空")
    
    for i, row in enumerate(matrix_data):
        expected_length = n
        if len(row) != expected_length:
            raise ValueError(f"第 {i} 行的长度应为 {expected_length}，但实际为 {len(row)}")
    
    matrix = np.array(matrix_data, dtype=float)
    return matrix


def convert_string_to_list(input_string):
    """
    将字符串格式的关系列表转换为 Python 列表。
    支持从 JSON 数组或每行一个 JSON 对象的格式中提取。
    支持修复包含未转义反斜杠的 JSON。
    
    参数:
        input_string: 可能包含思考过程和 JSON 的字符串
        
    返回:
        List[Tuple]: 转换后的元组列表
    """
    result = []
    
    # 尝试从响应中提取 JSON 部分
    json_str = extract_json_from_response(input_string)
    
    if json_str:
        # 尝试解析 JSON 数组
        data = parse_json_with_fallback(json_str)
        
        if data and isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "object_a" in item and "object_b" in item:
                    tuple_item = (
                        str(item["object_a"]),
                        str(item["object_b"]),
                        {
                            "rel": str(item.get("relation", "")),
                            "定理": str(item.get("explanation", ""))
                        }
                    )
                    result.append(tuple_item)
            return result
    
    # 如果 JSON 解析失败，尝试逐行解析（每行一个 JSON 对象）
    lines = input_string.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        try:
            # 尝试解析单行 JSON
            data = parse_json_with_fallback(line)
            if data and isinstance(data, dict) and "object_a" in data and "object_b" in data:
                tuple_item = (
                    str(data["object_a"]),
                    str(data["object_b"]),
                    {
                        "rel": str(data.get("relation", "")),
                        "定理": str(data.get("explanation", ""))
                    }
                )
                result.append(tuple_item)
        except Exception:
            continue
    
    return result


def parse_candidate_selection(raw_response: str) -> List[Dict[str, str]]:
    """
    解析候选节点筛选结果，返回包含候选名称、置信度和理由的列表。
    """
    results = []
    
    json_str = extract_json_from_response(raw_response)
    if not json_str:
        return results
    
    data = parse_json_with_fallback(json_str)
    if not data or not isinstance(data, list):
        return results
    
    for item in data:
        if not isinstance(item, dict):
            continue
        candidate_name = item.get("candidate_name") or item.get("name")
        if not candidate_name:
            continue
        confidence = item.get("confidence", 0)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0
        results.append({
            "candidate_name": str(candidate_name),
            "reason": str(item.get("reason", "")),
            "confidence": max(0.0, min(1.0, confidence_value))
        })
    
    return results
