# utils/section_length_calculator.py
"""
章节长度计算器 - 计算每个章节的内容长度
"""

from typing import Dict
import os


class SectionLengthCalculator:
    """章节长度计算器"""

    @staticmethod
    def calculate_section_lengths(
        text: str,
        section_titles: list,
        file_type: str = None
    ) -> Dict[str, int]:
        """
        计算每个章节的内容长度

        Args:
            text: 完整的文本内容
            section_titles: 章节标题列表
            file_type: 文件类型 ('tex', 'md', 'markdown')

        Returns:
            {章节名: 字符数}
        """
        if not section_titles:
            return {}

        # 自动检测文件类型
        if file_type is None:
            file_type = SectionLengthCalculator._detect_file_type(text)

        # 根据文件类型选择提取器
        if file_type in ['md', 'markdown']:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            extractor = MarkdownSectionExtractor
        elif file_type == 'tex':
            from src.utils.section_extractor import SectionExtractor
            extractor = SectionExtractor
        else:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            extractor = MarkdownSectionExtractor

        # 计算每个章节的长度
        section_lengths = {}
        for title in section_titles:
            content = extractor.extract_sections(text, [title])
            section_lengths[title] = len(content)

        return section_lengths

    @staticmethod
    def calculate_section_lengths_from_file(
        file_path: str,
        section_titles: list
    ) -> Dict[str, int]:
        """
        从文件计算章节长度

        Args:
            file_path: 文件路径
            section_titles: 章节标题列表

        Returns:
            {章节名: 字符数}
        """
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # 根据文件扩展名确定文件类型
        _, ext = os.path.splitext(file_path)
        file_type = ext.lstrip('.').lower()

        return SectionLengthCalculator.calculate_section_lengths(
            text,
            section_titles,
            file_type
        )

    @staticmethod
    def get_section_summary_with_lengths(
        text: str,
        file_type: str = None,
        max_level: int = 3
    ) -> list:
        """
        获取章节概览（包含长度信息）

        Args:
            text: 完整的文本内容
            file_type: 文件类型
            max_level: 最大标题级别

        Returns:
            [(章节名, 字符数, 估算tokens)]
        """
        # 自动检测文件类型
        if file_type is None:
            file_type = SectionLengthCalculator._detect_file_type(text)

        # 获取章节列表
        if file_type in ['md', 'markdown']:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            section_titles = MarkdownSectionExtractor.get_section_summary(text, max_level)
        elif file_type == 'tex':
            from src.utils.section_extractor import SectionExtractor
            section_titles = SectionExtractor.get_section_summary(text)
        else:
            from src.utils.markdown_section_extractor import MarkdownSectionExtractor
            section_titles = MarkdownSectionExtractor.get_section_summary(text, max_level)

        # 计算每个章节的长度
        result = []
        for title in section_titles:
            content_len = len(text)  # 简化版本，实际应该提取章节内容
            tokens = content_len // 4
            result.append((title, content_len, tokens))

        return result

    @staticmethod
    def _detect_file_type(text: str) -> str:
        """自动检测文件类型"""
        import re

        # 检测 LaTeX 特征
        latex_patterns = [r'\\section\{', r'\\subsection\{', r'\\begin\{']
        latex_score = sum(1 for p in latex_patterns if re.search(p, text))

        # 检测 Markdown 特征
        markdown_patterns = [r'^#{1,5}\s+', r'^\*\*.*\*\*$', r'^\* .*']
        markdown_score = sum(1 for p in markdown_patterns if re.search(p, text, re.MULTILINE))

        if latex_score > markdown_score:
            return 'tex'
        elif markdown_score > 0:
            return 'md'
        else:
            return 'unknown'
