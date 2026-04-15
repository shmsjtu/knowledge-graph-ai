# core/__init__.py
"""
核心抽象层 - 提供统一的数据类型、异常和常量定义
"""

from .result_types import (
    Node,
    Relation,
    TaskStatus,
    TaskType,
    ExtractionResult,
    EvaluationResult,
    TaskResult
)

from .exceptions import (
    KnowledgeGraphError,
    APIError,
    JSONParseError,
    ValidationError,
    TaskExecutionError,
    IterationLimitExceeded,
    DependencyError
)

from .constants import (
    APIConstants,
    IterationConstants,
    NODE_LEVEL_MAPPING,
    NODE_COLOR_MAPPING,
    RELATION_COLOR_MAPPING,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    DEFAULT_ENCODING
)

__all__ = [
    # Result types
    'Node',
    'Relation',
    'TaskStatus',
    'TaskType',
    'ExtractionResult',
    'EvaluationResult',
    'TaskResult',

    # Exceptions
    'KnowledgeGraphError',
    'APIError',
    'JSONParseError',
    'ValidationError',
    'TaskExecutionError',
    'IterationLimitExceeded',
    'DependencyError',

    # Constants
    'APIConstants',
    'IterationConstants',
    'NODE_LEVEL_MAPPING',
    'NODE_COLOR_MAPPING',
    'RELATION_COLOR_MAPPING',
    'LOG_FORMAT',
    'LOG_DATE_FORMAT',
    'DEFAULT_ENCODING',
]
