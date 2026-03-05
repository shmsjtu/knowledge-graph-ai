# json_utils.py
import json
import os
from pathlib import Path
from typing import List, Dict, Any


def save_to_json(data: List[dict], file_path: str, encoding: str = 'utf-8', indent: int = 4, merge: bool = True) -> bool:
    """
    将数据保存到 JSON 文件，支持合并现有数据。
    
    参数:
        data: 要保存的数据列表
        file_path: 文件路径
        encoding: 文件编码（默认 'utf-8'）
        indent: JSON 缩进（默认 4）
        merge: 是否合并现有数据（默认 True）
        
    返回:
        bool: 成功返回 True，失败返回 False
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_data = []
        if merge and path.exists():
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        print(f"警告: 现有文件内容不是列表格式，将覆盖原内容")
                        existing_data = []
                    else:
                        print(f"✓ 读取到现有数据 {len(existing_data)} 条")
            except json.JSONDecodeError:
                print(f"警告: 现有文件不是有效的JSON格式，将覆盖原内容")
                existing_data = []
            except Exception as e:
                print(f"警告: 读取现有文件失败 ({e})，将覆盖原内容")
                existing_data = []
        merged_data = existing_data + data
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=indent)
        if merge and existing_data:
            print(f"✓ 成功合并并保存: 原有 {len(existing_data)} 条 + 新增 {len(data)} 条 = 共 {len(merged_data)} 条数据到: {file_path}")
        else:
            print(f"✓ 成功保存 {len(data)} 条数据到: {file_path}")
        return True
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return False


def load_from_json(file_path: str, encoding: str = 'utf-8'):
    """
    从 JSON 文件加载数据。
    
    参数:
        file_path: 文件路径
        encoding: 文件编码（默认 'utf-8'）
        
    返回:
        List[dict] 或 None: 成功返回数据列表，失败返回 None
    """
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"✗ 文件不存在: {file_path}")
            return None
        if path.suffix.lower() != '.json':
            print(f"警告: 文件扩展名不是 .json: {file_path}")
        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"✗ JSON文件内容不是列表格式，而是 {type(data).__name__}")
            return None
        non_dict_count = sum(1 for item in data if not isinstance(item, dict))
        if non_dict_count > 0:
            print(f"警告: 列表中有 {non_dict_count} 个元素不是字典格式")
        print(f"✓ 成功读取 {len(data)} 条数据从: {file_path}")
        return data
    except json.JSONDecodeError as e:
        print(f"✗ JSON格式错误: {e}")
        return None
    except Exception as e:
        print(f"✗ 读取失败: {e}")
        return None


def list_to_json_format(tuple_list):
    """
    将元组列表转换为 JSON 格式的字典列表。
    
    参数:
        tuple_list: 元组列表，格式为 (object_a, object_b, {"rel": relation, "定理": explanation})
        
    返回:
        List[dict]: JSON 格式的字典列表
    """
    json_list = []
    for item in tuple_list:
        json_item = {
            "object_a": item[0],
            "object_b": item[1],
            "relation": item[2]["rel"],
            "explanation": item[2]["定理"]
        }
        json_list.append(json_item)
    return json_list


def list_save_to_json(tuple_list, file_path, merge=True):
    """
    将元组列表保存到 JSON 文件，支持合并现有数据。
    
    参数:
        tuple_list: 元组列表
        file_path: 文件路径
        merge: 是否合并现有数据（默认 True）
    """
    new_data = list_to_json_format(tuple_list)
    if merge and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            if not isinstance(existing_data, list):
                existing_data = []
            existing_keys = {
                (item['object_a'], item['object_b'], item['relation'])
                for item in existing_data
            }
            for item in new_data:
                key = (item['object_a'], item['object_b'], item['relation'])
                if key not in existing_keys:
                    existing_data.append(item)
                    existing_keys.add(key)
            final_data = existing_data
            print(f"合并完成：原有 {len(existing_data) - len(new_data)} 条，新增 {len(new_data)} 条")
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"无法读取现有文件，将创建新文件")
            final_data = new_data
    else:
        final_data = new_data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"成功保存到: {file_path}")
    print(f"总共 {len(final_data)} 条记录")


def delete_node_from_graph(node_name: str, nodes_path: str, relations_path: str) -> bool:
    """
    从知识图谱中删除节点及其所有相关关系。
    
    参数:
        node_name: 要删除的节点名称
        nodes_path: nodes.json 文件路径
        relations_path: relations.json 文件路径
        
    返回:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 加载节点
        nodes = load_from_json(nodes_path)
        if nodes is None:
            print(f"✗ 无法加载节点文件: {nodes_path}")
            return False
        
        # 检查节点是否存在
        node_exists = any(node.get('name') == node_name for node in nodes)
        if not node_exists:
            print(f"✗ 节点 '{node_name}' 不存在于节点列表中")
            return False
        
        # 删除节点
        original_count = len(nodes)
        nodes = [node for node in nodes if node.get('name') != node_name]
        deleted_nodes_count = original_count - len(nodes)
        
        # 保存更新后的节点
        with open(nodes_path, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=2)
        print(f"✓ 已删除节点 '{node_name}'，节点总数从 {original_count} 减少到 {len(nodes)}")
        
        # 加载关系
        relations = load_from_json(relations_path)
        if relations is None:
            print(f"✗ 无法加载关系文件: {relations_path}")
            return False
        
        # 删除包含该节点的所有关系
        original_relations_count = len(relations)
        relations = [
            rel for rel in relations 
            if rel.get('object_a') != node_name and rel.get('object_b') != node_name
        ]
        deleted_relations_count = original_relations_count - len(relations)
        
        # 保存更新后的关系
        with open(relations_path, 'w', encoding='utf-8') as f:
            json.dump(relations, f, ensure_ascii=False, indent=2)
        print(f"✓ 已删除 {deleted_relations_count} 个包含节点 '{node_name}' 的关系，关系总数从 {original_relations_count} 减少到 {len(relations)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 删除节点时出错: {e}")
        return False


def remove_duplicate_relations(relations_path: str) -> bool:
    """
    清理 relations.json 中重复的关系（object_a 和 object_b 都相等）。
    
    参数:
        relations_path: relations.json 文件路径
        
    返回:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 加载关系
        relations = load_from_json(relations_path)
        if relations is None:
            print(f"✗ 无法加载关系文件: {relations_path}")
            return False
        
        original_count = len(relations)
        
        # 使用集合来跟踪已见过的关系（基于 object_a 和 object_b）
        seen_relations = set()
        unique_relations = []
        duplicate_count = 0
        
        for rel in relations:
            object_a = rel.get('object_a', '')
            object_b = rel.get('object_b', '')
            relation_key = (object_a, object_b)
            
            if relation_key in seen_relations:
                duplicate_count += 1
                continue
            
            seen_relations.add(relation_key)
            unique_relations.append(rel)
        
        # 保存去重后的关系
        with open(relations_path, 'w', encoding='utf-8') as f:
            json.dump(unique_relations, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 清理完成：删除了 {duplicate_count} 个重复关系，关系总数从 {original_count} 减少到 {len(unique_relations)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 清理重复关系时出错: {e}")
        return False

def parse_evaluation_batch_response(response_str):
    """
    解析批量评估的 JSON 响应
    """
    try:
        # 清洗 Markdown 标记
        content = response_str.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # 尝试解析 JSON
        data = json.loads(content)
        
        # 确保是列表格式
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 兼容 LLM 可能只返回一个对象的情况
            return [data]
        else:
            return []
            
    except json.JSONDecodeError:
        print(f"警告: 批量评估 JSON 解析失败")
        return []
    except Exception as e:
        print(f"警告: 解析过程发生未知错误: {e}")
        return []