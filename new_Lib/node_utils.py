# node_utils.py
"""
节点文件操作工具函数
专门用于处理知识图谱节点文件的各种操作
"""
from typing import List, Dict, Any
from .json_utils import load_from_json, save_to_json


def remove_duplicate_nodes(nodes_path: str, encoding: str = 'utf-8') -> bool:
    """
    剔除节点文件中的重复节点（按照 "name" 字段），只保留第一次出现的节点。
    
    参数:
        nodes_path: 节点文件路径（JSON 格式）
        encoding: 文件编码（默认 'utf-8'）
        
    返回:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 加载节点数据
        nodes = load_from_json(nodes_path, encoding=encoding)
        
        if not isinstance(nodes, list):
            print(f"✗ 错误: 节点文件格式不正确，应为列表格式")
            return False
        
        if not nodes:
            print(f"✓ 节点文件为空，无需去重")
            return True
        
        original_count = len(nodes)
        seen_names = set()
        unique_nodes = []
        removed_count = 0
        
        for node in nodes:
            if not isinstance(node, dict):
                print(f"⚠ 警告: 跳过非字典格式的节点: {node}")
                continue
            
            node_name = node.get("name")
            
            # 如果节点没有 name 字段，保留它（但给出警告）
            if not node_name:
                print(f"⚠ 警告: 发现没有 'name' 字段的节点，将保留: {node}")
                unique_nodes.append(node)
                continue
            
            # 如果 name 已经出现过，跳过（不添加）
            if node_name in seen_names:
                removed_count += 1
                print(f"  移除重复节点: {node_name}")
                continue
            
            # 第一次出现的节点，添加到结果中
            seen_names.add(node_name)
            unique_nodes.append(node)
        
        # 保存去重后的节点
        if removed_count > 0:
            # 使用 save_to_json，设置 merge=False 来覆盖原文件
            success = save_to_json(unique_nodes, nodes_path, encoding=encoding, merge=False)
            if success:
                print(f"✓ 去重完成: 原有 {original_count} 个节点，移除 {removed_count} 个重复节点，保留 {len(unique_nodes)} 个唯一节点")
            else:
                print(f"✗ 保存去重后的节点失败")
                return False
        else:
            print(f"✓ 未发现重复节点，所有 {original_count} 个节点都是唯一的")
        
        return True
        
    except FileNotFoundError:
        print(f"✗ 错误: 文件未找到 - {nodes_path}")
        return False
    except Exception as e:
        print(f"✗ 去重失败: {e}")
        return False

