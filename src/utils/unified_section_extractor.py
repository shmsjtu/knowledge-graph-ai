# utils/unified_section_extractor.py
"""
统一章节内容提取器 - 自动识别文件类型并提取章节内容
支持 LaTeX (.tex) 和 Markdown (.md) 文件
"""

import os
from typing import List


class UnifiedSectionExtractor:
    """统一章节内容提取器"""

    @staticmethod
    def extract_sections(text: str, target_sections: List[str], file_type: str = None) -> str:
        """
        根据文件类型提取指定章节的内容

        Args:
            text: 完整的文本内容
            target_sections: 目标章节列表
            file_type: 文件类型 ('tex', 'md', 'markdown')，如果为 None 则自动检测

        Returns:
            提取的章节内容
        """
        if not target_sections or target_sections == ["all"]:
            return text

        # 自动检测文件类型
        if file_type is None:
            file_type = UnifiedSectionExtractor._detect_file_type(text)

        # 根据文件类型选择提取器
        if file_type in ['md', 'markdown']:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            return MarkdownSectionExtractor.extract_sections(text, target_sections)
        elif file_type == 'tex':
            from src.utils.section_extractor import SectionExtractor
            return SectionExtractor.extract_sections(text, target_sections)
        else:
            # 默认使用 Markdown 提取器
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            return MarkdownSectionExtractor.extract_sections(text, target_sections)

    @staticmethod
    def get_section_summary(text: str, file_type: str = None) -> List[str]:
        """
        获取文档的章节概览

        Args:
            text: 完整的文本内容
            file_type: 文件类型，如果为 None 则自动检测

        Returns:
            章节标题列表
        """
        # 自动检测文件类型
        if file_type is None:
            file_type = UnifiedSectionExtractor._detect_file_type(text)

        # 根据文件类型选择提取器
        if file_type in ['md', 'markdown']:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            return MarkdownSectionExtractor.get_section_summary(text)
        elif file_type == 'tex':
            from src.utils.section_extractor import SectionExtractor
            return SectionExtractor.get_section_summary(text)
        else:
            # 默认使用 Markdown 提取器
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            return MarkdownSectionExtractor.get_section_summary(text)

    @staticmethod
    def _detect_file_type(text: str) -> str:
        """
        自动检测文件类型

        Args:
            text: 文本内容

        Returns:
            文件类型 ('tex', 'md', 'unknown')
        """
        # 检测 LaTeX 特征
        latex_patterns = [
            r'\\section\{',
            r'\\subsection\{',
            r'\\begin\{',
            r'\\end\{',
            r'\\documentclass',
        ]

        # 检测 Markdown 特征
        markdown_patterns = [
            r'^#{1,5}\s+',  # Markdown 标题
            r'^\*\*.*\*\*$',  # 粗体
            r'^\* .*',  # 无序列表
            r'^\d+\.\s+',  # 有序列表
        ]

        import re

        # 计算 LaTeX 特征数量
        latex_score = 0
        for pattern in latex_patterns:
            if re.search(pattern, text, re.MULTILINE):
                latex_score += 1

        # 计算 Markdown 特征数量
        markdown_score = 0
        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                markdown_score += 1

        # 根据分数判断
        if latex_score > markdown_score:
            return 'tex'
        elif markdown_score > 0:
            return 'md'
        else:
            return 'unknown'

    @staticmethod
    def extract_from_file(file_path: str, target_sections: List[str]) -> str:
        """
        从文件中提取指定章节的内容

        Args:
            file_path: 文件路径
            target_sections: 目标章节列表

        Returns:
            提取的章节内容
        """
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # 根据文件扩展名确定文件类型
        _, ext = os.path.splitext(file_path)
        file_type = ext.lstrip('.').lower()

        # 提取章节
        return UnifiedSectionExtractor.extract_sections(text, target_sections, file_type)
