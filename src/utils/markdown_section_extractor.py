# utils/markdown_section_extractor.py
"""
Markdown 章节内容提取器 - 根据标题提取对应的 Markdown 内容
支持 # 到 ##### 级别的标题
"""

import re
from typing import List, Dict


class MarkdownSectionExtractor:
    """Markdown 章节内容提取器"""

    # Markdown 标题级别映射
    HEADER_LEVELS = {
        '#': 1,
        '##': 2,
        '###': 3,
        '####': 4,
        '#####': 5,
    }

    @staticmethod
    def extract_sections(markdown_text: str, target_sections: List[str]) -> str:
        """
        从 Markdown 文本中提取指定章节的内容

        Args:
            markdown_text: 完整的 Markdown 文本
            target_sections: 目标章节列表，如 ["第一章 集合论", "1.1 集合的基本概念"]

        Returns:
            提取的章节内容
        """
        if not target_sections or target_sections == ["all"]:
            # 如果没有指定章节或指定为 all，返回全部内容
            return markdown_text

        # 提取所有章节的位置
        section_positions = MarkdownSectionExtractor._find_all_sections(markdown_text)

        # 提取目标章节的内容
        extracted_content = []
        for target in target_sections:
            content = MarkdownSectionExtractor._extract_single_section(
                markdown_text,
                target,
                section_positions
            )
            if content:
                extracted_content.append(content)

        return "\n\n".join(extracted_content)

    @staticmethod
    def _find_all_sections(markdown_text: str) -> List[Dict]:
        """
        找到所有章节的位置

        Args:
            markdown_text: Markdown 文本

        Returns:
            章节位置列表，每个元素包含 {level, title, start, end}
        """
        # 匹配 Markdown 标题：# 到 #####
        pattern = r'^(#{1,5})\s+(.+?)$'

        sections = []
        lines = markdown_text.split('\n')

        current_pos = 0
        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                level = len(match.group(1))  # # 的数量表示级别
                title = match.group(2).strip()
                start = current_pos

                # 章节结束位置是下一个同级或更高级标题的开始位置
                # 或者是文档末尾
                end = len(markdown_text)

                # 查找下一个同级或更高级标题
                for j in range(i + 1, len(lines)):
                    next_match = re.match(pattern, lines[j])
                    if next_match:
                        next_level = len(next_match.group(1))
                        if next_level <= level:
                            # 找到下一个同级或更高级标题
                            # 计算其位置
                            end = sum(len(lines[k]) + 1 for k in range(j))
                            break

                sections.append({
                    'level': level,
                    'title': title,
                    'start': start,
                    'end': end
                })

            current_pos += len(line) + 1  # +1 for newline

        return sections

    @staticmethod
    def _extract_single_section(
        markdown_text: str,
        target_section: str,
        section_positions: List[Dict]
    ) -> str:
        """
        提取单个章节的内容

        Args:
            markdown_text: Markdown 文本
            target_section: 目标章节名称
            section_positions: 章节位置列表

        Returns:
            章节内容
        """
        # 清理目标章节名称
        target_clean = target_section.strip()
        target_normalized = MarkdownSectionExtractor._normalize_title(target_clean)

        # 尝试多种匹配方式
        for section in section_positions:
            title = section['title']

            # 匹配方式1: 完全匹配
            if target_clean == title:
                return markdown_text[section['start']:section['end']].strip()

            # 匹配方式2: 规范化后的精确匹配（去编号、空白、常见标点差异）
            title_normalized = MarkdownSectionExtractor._normalize_title(title)
            if target_normalized and title_normalized and target_normalized == title_normalized:
                return markdown_text[section['start']:section['end']].strip()

        # 如果找不到匹配的章节，返回空字符串（禁用包含式模糊匹配）
        return ""

    @staticmethod
    def _normalize_title(title: str) -> str:
        """规范化标题，仅用于精确等价匹配。"""
        if not title:
            return ""

        normalized = title.strip()
        # 去掉前导编号，例如 "1.2. "、"2．"、"3 "
        normalized = re.sub(r'^\d+(?:[.．]\d+)*[.．]?\s*', '', normalized)
        # 去掉末尾常见标点，避免 "." 与 "。" 差异
        normalized = re.sub(r'[.。．：:;；,，、\s]+$', '', normalized)
        # 合并所有空白
        normalized = re.sub(r'\s+', '', normalized)
        return normalized

    @staticmethod
    def _similarity(str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度（简单的字符重叠率）

        Args:
            str1: 字符串1
            str2: 字符串2

        Returns:
            相似度 [0, 1]
        """
        if not str1 or not str2:
            return 0.0

        # 去掉空格和特殊字符
        s1 = set(re.sub(r'[\s\d.#\-\[\]]', '', str1))
        s2 = set(re.sub(r'[\s\d.#\-\[\]]', '', str2))

        if not s1 or not s2:
            return 0.0

        intersection = s1 & s2
        union = s1 | s2

        return len(intersection) / len(union)

    @staticmethod
    def get_section_summary(markdown_text: str, max_level: int = 5) -> List[str]:
        """
        获取 Markdown 文档的章节概览

        Args:
            markdown_text: Markdown 文本
            max_level: 最大标题级别（1-5），默认为 5（显示所有级别）

        Returns:
            章节标题列表，带缩进表示层级
        """
        section_positions = MarkdownSectionExtractor._find_all_sections(markdown_text)

        summaries = []
        for section in section_positions:
            level = section['level']
            title = section['title']

            if level <= max_level:
                # 根据级别添加缩进
                indent = "  " * (level - 1)
                summaries.append(f"{indent}{title}")

        return summaries

    @staticmethod
    def get_toc(markdown_text: str, max_level: int = 3) -> str:
        """
        生成 Markdown 文档的目录（Table of Contents）

        Args:
            markdown_text: Markdown 文本
            max_level: 最大标题级别（1-5），默认为 3

        Returns:
            目录字符串
        """
        section_positions = MarkdownSectionExtractor._find_all_sections(markdown_text)

        toc_lines = []
        for section in section_positions:
            level = section['level']
            title = section['title']

            if level <= max_level:
                # 生成目录项
                indent = "  " * (level - 1)
                # 生成锚点链接（GitHub 风格）
                anchor = re.sub(r'[^\w\u4e00-\u9fff]+', '-', title.lower())
                anchor = anchor.strip('-')
                toc_lines.append(f"{indent}- [{title}](#{anchor})")

        return "\n".join(toc_lines)

    @staticmethod
    def extract_by_level(
        markdown_text: str,
        level: int,
        include_subsections: bool = True
    ) -> List[Dict]:
        """
        提取指定级别的所有章节

        Args:
            markdown_text: Markdown 文本
            level: 标题级别（1-5）
            include_subsections: 是否包含子章节

        Returns:
            章节列表，每个元素包含 {title, content, level}
        """
        if level < 1 or level > 5:
            raise ValueError("Level must be between 1 and 5")

        section_positions = MarkdownSectionExtractor._find_all_sections(markdown_text)

        results = []
        for i, section in enumerate(section_positions):
            if section['level'] == level:
                content = markdown_text[section['start']:section['end']]

                if not include_subsections:
                    # 不包含子章节，只提取到下一个同级标题之前
                    for j in range(i + 1, len(section_positions)):
                        if section_positions[j]['level'] <= level:
                            content = markdown_text[section['start']:section_positions[j]['start']]
                            break

                results.append({
                    'title': section['title'],
                    'content': content.strip(),
                    'level': section['level']
                })

        return results

    @staticmethod
    def extract_first_n_sections(markdown_text: str, n: int) -> str:
        """
        提取前 N 个章节的内容

        Args:
            markdown_text: Markdown 文本
            n: 章节数量

        Returns:
            提取的内容
        """
        section_positions = MarkdownSectionExtractor._find_all_sections(markdown_text)

        if not section_positions or n <= 0:
            return ""

        # 取前 N 个章节
        n = min(n, len(section_positions))
        end_pos = section_positions[n - 1]['end']

        return markdown_text[:end_pos].strip()
