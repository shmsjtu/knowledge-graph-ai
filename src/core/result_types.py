# core/result_types.py
"""
统一的结果数据类型定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(Enum):
    """任务类型枚举"""
    EXTRACT_NODES = "extract_nodes"
    EXTRACT_RELATIONS = "extract_relations"
    EXTRACT_BOTH = "extract_nodes_and_internal_relations"
    EXTRACT_CROSS_SECTION = "extract_cross_section_relations"


@dataclass
class Node:
    """节点数据结构"""
    name: str
    desc: str = ""
    level: int = 2  # 0-4
    color: str = "#FFFF00"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_tuple(self) -> tuple:
        """转换为元组格式（兼容旧系统）"""
        attrs = {
            "desc": self.desc,
            "level": self.level,
            "color": self.color
        }
        if self.metadata:
            attrs["metadata"] = self.metadata
        return (self.name, attrs)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        data = {
            "name": self.name,
            "desc": self.desc,
            "level": self.level,
            "color": self.color
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_tuple(cls, data: tuple) -> 'Node':
        """从元组格式创建"""
        if not isinstance(data, (list, tuple)) or len(data) < 2:
            raise ValueError(f"Invalid tuple format for Node: {data}")

        name, attrs = data[0], data[1]
        if not isinstance(attrs, dict):
            raise ValueError(f"Invalid attributes format for Node: {attrs}")

        return cls(
            name=name,
            desc=attrs.get("desc", ""),
            level=attrs.get("level", 2),
            color=attrs.get("color", "#FFFF00"),
            metadata=attrs.get("metadata", {})
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'Node':
        """从字典格式创建"""
        return cls(
            name=data.get("name", "未命名"),
            desc=data.get("desc", ""),
            level=data.get("level", 2),
            color=data.get("color", "#FFFF00"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Relation:
    """关系数据结构"""
    object_a: str
    object_b: str
    relation_type: str = "relate_to"
    explanation: str = ""
    color: str = "#888888"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_tuple(self) -> tuple:
        """转换为元组格式（兼容旧系统）"""
        attrs = {
            "rel": self.relation_type,
            "定理": self.explanation,
            "color": self.color
        }
        if self.metadata:
            attrs["metadata"] = self.metadata
        return (self.object_a, self.object_b, attrs)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        data = {
            "object_a": self.object_a,
            "object_b": self.object_b,
            "relation_type": self.relation_type,
            "explanation": self.explanation,
            "color": self.color
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_tuple(cls, data: tuple) -> 'Relation':
        """从元组格式创建"""
        if not isinstance(data, (list, tuple)) or len(data) < 3:
            raise ValueError(f"Invalid tuple format for Relation: {data}")

        obj_a, obj_b, attrs = data[0], data[1], data[2]
        if not isinstance(attrs, dict):
            raise ValueError(f"Invalid attributes format for Relation: {attrs}")

        return cls(
            object_a=obj_a,
            object_b=obj_b,
            relation_type=attrs.get("rel", "relate_to"),
            explanation=attrs.get("定理", ""),
            color=attrs.get("color", "#888888"),
            metadata=attrs.get("metadata", {})
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'Relation':
        """从字典格式创建"""
        return cls(
            object_a=data.get("object_a", ""),
            object_b=data.get("object_b", ""),
            relation_type=data.get("relation", data.get("relation_type", "relate_to")),
            explanation=data.get("explanation", ""),
            color=data.get("color", "#888888"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExtractionResult:
    """提取结果"""
    nodes: List[Node] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    """评估结果"""
    qualified_nodes: List[Node] = field(default_factory=list)
    unqualified_nodes: List[Node] = field(default_factory=list)
    qualified_relations: List[Relation] = field(default_factory=list)
    unqualified_relations: List[Relation] = field(default_factory=list)
    feedback: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    nodes: List[Node] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    iterations: int = 0
    evaluation_result: Optional[EvaluationResult] = None
    error: Optional[str] = None
