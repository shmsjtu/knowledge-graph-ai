# core/constants.py
"""
常量定义
"""


# API相关常量
class APIConstants:
    DEFAULT_MODEL = "deepseek-chat"
    REASONER_MODEL = "deepseek-reasoner"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # 秒


# 迭代相关常量
class IterationConstants:
    DEFAULT_MAX_ITERATIONS = 3
    MAX_ITERATIONS_HARD_LIMIT = 10


# 节点级别映射
NODE_LEVEL_MAPPING = {
    "核心知识点": 0,
    "主要知识点": 1,
    "定义": 2,
    "定理": 3,
    "实例": 4,
}

# 节点颜色映射
NODE_COLOR_MAPPING = {
    0: "#FF0000",  # 红色 - 核心知识点
    1: "#FFA500",  # 橙色 - 主要知识点
    2: "#FFFF00",  # 黄色 - 定义
    3: "#008000",  # 绿色 - 定理
    4: "#0000FF",  # 蓝色 - 实例
}

# 关系类型颜色映射
RELATION_COLOR_MAPPING = {
    "包含": "#F5B721",
    "属性": "#8cc78a",
    "充分递推": "#00a5b1",
    "必要递推": "#00a5b1",
    "充要递推": "#00a5b1",
    "等价": "#ff8983",
    "relate_to": "#888888",
}

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 文件编码
DEFAULT_ENCODING = "utf-8"
