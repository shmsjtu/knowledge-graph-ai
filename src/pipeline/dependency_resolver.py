# pipeline/dependency_resolver.py
"""
依赖解析器 - 解析任务依赖关系，确定执行顺序
"""

from typing import List, Dict
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.exceptions import DependencyError
from src.infrastructure import Logger


class DependencyResolver:
    """依赖解析器"""

    def __init__(self):
        self.logger = Logger("DependencyResolver")

    def resolve(self, tasks: List[Dict]) -> List[List[Dict]]:
        """
        解析任务依赖关系，返回执行批次

        Args:
            tasks: 任务列表

        Returns:
            执行批次列表，每个批次可以并行执行

        Raises:
            DependencyError: 如果检测到循环依赖
        """
        if not tasks:
            return []

        # 构建任务映射
        task_map = {task["task_id"]: task for task in tasks}

        # 计算每个任务的依赖深度
        depth_map = {}
        for task in tasks:
            self._calculate_depth(task["task_id"], task_map, depth_map, set())

        # 按深度分组
        max_depth = max(depth_map.values()) if depth_map else 0
        batches = [[] for _ in range(max_depth + 1)]

        for task_id, depth in depth_map.items():
            batches[depth].append(task_map[task_id])

        # 过滤空批次
        batches = [batch for batch in batches if batch]

        # 记录日志
        self.logger.info(f"任务依赖解析完成，共 {len(batches)} 个批次")
        for i, batch in enumerate(batches):
            task_ids = [t["task_id"] for t in batch]
            self.logger.info(f"  批次 {i+1}: {', '.join(task_ids)}")

        return batches

    def _calculate_depth(
        self,
        task_id: str,
        task_map: Dict,
        depth_map: Dict,
        visiting: set
    ) -> int:
        """
        计算任务的依赖深度

        Args:
            task_id: 任务ID
            task_map: 任务映射
            depth_map: 深度映射（缓存）
            visiting: 正在访问的任务集合（用于检测循环依赖）

        Returns:
            依赖深度
        """
        # 检查缓存
        if task_id in depth_map:
            return depth_map[task_id]

        # 检测循环依赖
        if task_id in visiting:
            raise DependencyError(task_id, list(visiting))

        visiting.add(task_id)

        task = task_map.get(task_id)
        if not task:
            visiting.remove(task_id)
            return 0

        dependencies = task.get("dependencies", [])

        if not dependencies:
            depth = 0
        else:
            # 深度 = 最大依赖深度 + 1
            max_dep_depth = max(
                self._calculate_depth(dep_id, task_map, depth_map, visiting)
                for dep_id in dependencies
            )
            depth = max_dep_depth + 1

        depth_map[task_id] = depth
        visiting.remove(task_id)

        return depth

    def validate_dependencies(self, tasks: List[Dict]) -> bool:
        """
        验证依赖关系是否有效

        Args:
            tasks: 任务列表

        Returns:
            是否有效
        """
        try:
            self.resolve(tasks)
            return True
        except DependencyError as e:
            self.logger.error(f"依赖验证失败: {e}")
            return False

    def get_execution_order(self, tasks: List[Dict]) -> List[str]:
        """
        获取任务的执行顺序（扁平化）

        Args:
            tasks: 任务列表

        Returns:
            任务ID列表（按执行顺序）
        """
        batches = self.resolve(tasks)
        return [task["task_id"] for batch in batches for task in batch]
