# infrastructure/logger.py
"""
日志管理器 - 统一日志管理
"""

import logging
import os
from datetime import datetime
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.constants import LOG_FORMAT, LOG_DATE_FORMAT


class Logger:
    """日志管理器"""

    def __init__(self, name: str, log_dir: str = None):
        """
        初始化日志管理器

        Args:
            name: 日志记录器名称
            log_dir: 日志目录（可选）
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            # 文件处理器（可选）
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(
                    log_dir,
                    f"{datetime.now().strftime('%Y%m%d')}.log"
                )
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(console_formatter)
                self.logger.addHandler(file_handler)

    def info(self, message: str):
        """记录信息"""
        self.logger.info(message)

    def warning(self, message: str):
        """记录警告"""
        self.logger.warning(message)

    def error(self, message: str):
        """记录错误"""
        self.logger.error(message)

    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)
