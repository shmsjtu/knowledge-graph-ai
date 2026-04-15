# core/exceptions.py
"""
自定义异常体系
"""


class KnowledgeGraphError(Exception):
    """知识图谱基础异常"""
    pass


class APIError(KnowledgeGraphError):
    """API调用异常"""
    def __init__(self, message: str, status_code: int = None, retry_count: int = 0):
        self.status_code = status_code
        self.retry_count = retry_count
        super().__init__(message)


class JSONParseError(KnowledgeGraphError):
    """JSON解析异常"""
    def __init__(self, message: str, raw_content: str = None):
        self.raw_content = raw_content
        super().__init__(message)


class ValidationError(KnowledgeGraphError):
    """数据验证异常"""
    def __init__(self, message: str, errors: list = None):
        self.errors = errors or []
        super().__init__(message)


class TaskExecutionError(KnowledgeGraphError):
    """任务执行异常"""
    def __init__(self, task_id: str, message: str, cause: Exception = None):
        self.task_id = task_id
        self.cause = cause
        super().__init__(f"Task {task_id} failed: {message}")


class IterationLimitExceeded(KnowledgeGraphError):
    """迭代次数超限异常"""
    def __init__(self, max_iterations: int, task_id: str = None):
        self.max_iterations = max_iterations
        self.task_id = task_id
        super().__init__(f"Exceeded maximum iterations: {max_iterations}")


class DependencyError(KnowledgeGraphError):
    """依赖关系异常"""
    def __init__(self, task_id: str, missing_dependencies: list):
        self.task_id = task_id
        self.missing_dependencies = missing_dependencies
        super().__init__(f"Task {task_id} has missing dependencies: {missing_dependencies}")
