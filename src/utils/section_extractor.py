# utils/section_extractor.py
"""
章节内容提取器 - 根据章节名称提取对应的教材内容
"""

import re
from typing import List, Dict


class SectionExtractor:
    """章节内容提取器"""

    @staticmethod
    def extract_sections(material_text: str, target_sections: List[str]) -> str:
        """
        从教材文本中提取指定章节的内容

        Args:
            material_text: 完整的教材文本
            target_sections: 目标章节列表，如 ["§1 集合的基本概念", "§2 集合的运算"]

        Returns:
            提取的章节内容
        """
        if not target_sections or target_sections == ["all"]:
            # 如果没有指定章节或指定为 all，返回全部内容
            return material_text

        # 提取所有章节的位置
        section_positions = SectionExtractor._find_all_sections(material_text)

        # 提取目标章节的内容
        extracted_content = []
        for target in target_sections:
            content = SectionExtractor._extract_single_section(
                material_text,
                target,
                section_positions
            )
            if content:
                extracted_content.append(content)

        return "\n\n".join(extracted_content)

    @staticmethod
    def _find_all_sections(material_text: str) -> List[Dict]:
        """
        找到所有章节的位置

        Args:
            material_text: 教材文本

        Returns:
            章节位置列表，每个元素包含 {title, start, end}
        """
        # 匹配 \section{...} 和 \subsection{...}
        pattern = r'\\(section|subsection)\{([^}]+)\}'
        matches = list(re.finditer(pattern, material_text))

        sections = []
        for i, match in enumerate(matches):
            level = match.group(1)  # section 或 subsection
            title = match.group(2)
            start = match.start()

            # 章节结束位置是下一个章节的开始位置，或者是文档末尾
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(material_text)

            sections.append({
                'level': level,
                'title': title,
                'start': start,
                'end': end
            })

        return sections

    @staticmethod
    def _extract_single_section(
        material_text: str,
        target_section: str,
        section_positions: List[Dict]
    ) -> str:
        """
        提取单个章节的内容

        Args:
            material_text: 教材文本
            target_section: 目标章节名称
            section_positions: 章节位置列表

        Returns:
            章节内容
        """
        # 清理目标章节名称
        target_clean = target_section.strip()

        # 尝试多种匹配方式
        for section in section_positions:
            title = section['title']

            # 匹配方式1: 完全匹配
            if target_clean == title:
                return material_text[section['start']:section['end']].strip()

            # 匹配方式2: 去掉 § 符号后匹配
            target_no_section = re.sub(r'^§\d+\s*', '', target_clean)
            if target_no_section == title:
                return material_text[section['start']:section['end']].strip()

            # 匹配方式3: 目标章节包含在标题中
            if target_clean in title or title in target_clean:
                return material_text[section['start']:section['end']].strip()

        # 如果找不到匹配的章节，尝试模糊匹配
        for section in section_positions:
            title = section['title']
            # 计算相似度（简单的字符重叠）
            if SectionExtractor._similarity(target_clean, title) > 0.5:
                return material_text[section['start']:section['end']].strip()

        # 找不到章节，返回空字符串
        return ""

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
        s1 = set(re.sub(r'[\s§\d]', '', str1))
        s2 = set(re.sub(r'[\s§\d]', '', str2))

        if not s1 or not s2:
            return 0.0

        intersection = s1 & s2
        union = s1 | s2

        return len(intersection) / len(union)

    @staticmethod
    def get_section_summary(material_text: str) -> List[str]:
        """
        获取教材的章节概览

        Args:
            material_text: 教材文本

        Returns:
            章节标题列表
        """
        section_positions = SectionExtractor._find_all_sections(material_text)

        summaries = []
        for section in section_positions:
            level = section['level']
            title = section['title']
            prefix = "" if level == "section" else "  "
            summaries.append(f"{prefix}{title}")

        return summaries
