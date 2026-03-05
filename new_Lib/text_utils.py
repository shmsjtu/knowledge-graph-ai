# text_utils.py
import re
from typing import List, Tuple


def get_index_from_theme(theme_str: str) -> int:
    """
    从 "第九章...--§7. 压缩映射原理" 这样的 theme 字符串中提取索引 6 (7-1)。
    
    参数:
        theme_str: 主题字符串
        
    返回:
        int: 提取的索引（如果失败返回 0）
    """
    # 查找 "--§" 之后的部分
    parts = theme_str.split('--')
    if len(parts) < 2:
        print(f"警告: theme 格式不正确，无法提取索引: {theme_str}")
        return 0  # 返回一个默认值

    # "§7. 压缩映射原理"
    section_part = parts[-1]
    
    # 使用正则表达式查找第一个数字
    # \s* 匹配 "§" 和数字之间的任意空格
    # (\d+) 捕获一个或多个数字
    match = re.search(r'§\s*(\d+)', section_part)
    
    if match:
        try:
            # 提取捕获的数字 (group 1)
            number = int(match.group(1))
            # 用户的要求是减一
            return number - 1
        except ValueError:
            print(f"警告: 从 theme 提取的数字无效: {match.group(1)}")
            return 0
    
    print(f"警告: 未能在 theme 中找到 '§' + 数字: {theme_str}")
    return 0  # 返回默认值


def merge_strings(strings):
    """
    合并字符串列表，根据 "## §" 标记进行分割和合并。
    
    参数:
        strings: 字符串列表
        
    返回:
        List[str]: 合并后的字符串列表
    """
    if not strings:
        return []
    pattern = r'^## §.*$'
    merged_strings = []
    current_string = ""
    has_marker = False
    for s in strings:
        lines = s.split('\n')
        marker_indices = []
        for idx, line in enumerate(lines):
            if re.match(pattern, line):
                marker_indices.append(idx)
        if not marker_indices:
            if current_string:
                current_string += '\n' + s
            else:
                current_string = s
        else:
            for j, marker_idx in enumerate(marker_indices):
                if j == 0:
                    before_marker = '\n'.join(lines[:marker_idx])
                else:
                    before_marker = '\n'.join(lines[marker_indices[j-1]+1:marker_idx])
                if before_marker:
                    if current_string:
                        current_string += '\n' + before_marker
                    else:
                        current_string = before_marker
                if has_marker:
                    merged_strings.append(current_string)
                    current_string = ""
                    has_marker = False
                if j < len(marker_indices) - 1:
                    segment = '\n'.join(lines[marker_idx:marker_indices[j+1]])
                else:
                    segment = '\n'.join(lines[marker_idx:])
                if current_string:
                    current_string += '\n' + segment
                else:
                    current_string = segment
                has_marker = True
    if current_string:
        merged_strings.append(current_string)
    return merged_strings


def split_by_section_marker(content: str) -> List[str]:
    """
    按照 "## §" 标记将内容拆分成多个部分。
    
    参数:
        content: 完整的 markdown 内容字符串
        
    返回:
        List[str]: 拆分后的字符串列表，每个元素是一个部分
    """
    if not content:
        return []
    
    lines = content.split('\n')
    pattern = r'^## §.*$'
    sections = []
    current_section = []
    
    for line in lines:
        if re.match(pattern, line):
            # 如果遇到新的 "## §" 标记，保存当前部分并开始新部分
            if current_section:
                sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            # 继续添加到当前部分
            current_section.append(line)
    
    # 添加最后一个部分
    if current_section:
        sections.append('\n'.join(current_section))
    
    # 如果存在至少两个部分，则将第一个（通常为 "#" 开头的章节标题）
    # 与第二个（第一个 "## §" 小节）合并，保持结构完整
    if len(sections) >= 2:
        combined_first = sections[0].strip()
        second_section = sections[1].strip()
        merged = (combined_first + "\n\n" + second_section).strip()
        sections = [merged] + sections[2:]

    return sections


def split_by_subsection(content: str) -> List[Tuple[str, str]]:
    """
    按照 "###" 次标题将内容拆分成多个小部分。
    
    参数:
        content: markdown 内容字符串
        
    返回:
        List[Tuple[str, str]]: 列表，每个元素是 (标题, 内容) 的元组
            - 如果没有 "###" 标题，标题为空字符串
            - 如果有多个 "###" 标题，每个标题及其后续内容作为一个部分
    """
    if not content:
        return []
    
    lines = content.split('\n')
    pattern = r'^###\s+.*$'  # 匹配以 "### " 开头的行
    subsections = []
    current_title = []
    current_content = []
    flag = 0
    for line in lines:
        if re.match(pattern, line):
            # 如果遇到新的 "###" 标题，保存当前部分并开始新部分
            if current_title or current_content:
                # 保存之前的部分（标题和内容）
                if flag == 0:
                    current_content = []
                    flag = 1
                    current_title.append(line)
                    continue
                else:
                    content_str = '\n'.join(current_content).strip()
                    subsections.append(('\n'.join(current_title), content_str))
                    current_title = []
                current_title.append(line)  # 保存标题行
        else:
            # 检查 line 是否为空或长度不足，避免索引越界
            if len(line) >= 2 and line[0] == '#' and len(line) >= 2 and line[1] != '#':
                current_title.append(line)
            elif len(line) >= 3 and line[0:2] == '##' and line[2] != '#':
                current_title.append(line)
            else:
                current_content.append(line)
    
    # 添加最后一个部分
    if current_title or current_content:
        content_str = '\n'.join(current_content).strip()
        subsections.append(('\n'.join(current_title), content_str))
    
    # 如果没有找到任何 "###" 标题，将整个内容作为一个部分
    if not subsections:
        subsections.append(("", content.strip()))
    
    return subsections


def print_results(merged_strings):
    """
    打印合并后的字符串列表。
    
    参数:
        merged_strings: 合并后的字符串列表
    """
    print(f"合并后共有 {len(merged_strings)} 个字符串:\n")
    for i, s in enumerate(merged_strings, 1):
        print(f"=== 字符串 {i} ===")
        print(s)
        print()


def classify_text(textt: List[str]) -> List[Tuple[str, str, str]]:
    """
    对文本进行分类，提取定义、例子、证明和其他内容。
    
    参数:
        textt: 文本列表
        
    返回:
        Tuple: (definitions, examples, proofs, others, Theme)
            - definitions: 定义列表
            - examples: 例子列表
            - proofs: 证明列表
            - others: 其他内容列表
            - Theme: 主题列表
    """
    result = []
    chapters = {1: "", 2: "", 3: "", 4: ""}
    content_pattern = r'^\*\*(定义|定理|命题|引理|推论|例子|证明)([^:：]*):\*\*\s*(.*)'
    Theme = []
    for j in range(len(textt)):
        lines = textt[j].split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('####'):
                chapters[4] = line[4:].strip()
                i += 1
                continue
            elif line.startswith('###'):
                chapters[3] = line[3:].strip()
                chapters[4] = ""
                i += 1
                continue
            elif line.startswith('##'):
                chapters[2] = line[2:].strip()
                chapters[3] = ""
                chapters[4] = ""
                i += 1
                li = []
                for k in range(1, 3):
                    li.append(chapters[k])
                temp = '--'.join(li) if li else ""
                if temp not in Theme:
                    Theme.append(temp)
                continue
            elif line.startswith('#'):
                chapters[1] = line[1:].strip()
                chapters[2] = ""
                chapters[3] = ""
                chapters[4] = ""
                i += 1
                continue
            match = re.match(content_pattern, line)
            if match:
                classification_type = match.group(1)
                number = match.group(2)
                if number:
                    classification = f"{classification_type} {number}"
                else:
                    classification = classification_type
                # 从当前匹配的行开始收集内容（包括 content_pattern 本身）
                content_lines = [lines[i]]  # 使用原始行（包括标记），不 strip
                i += 1
                # 继续收集直到遇到下一个 content_pattern 或文件结束
                while i < len(lines):
                    next_line = lines[i]
                    # 检查是否是下一个 content_pattern
                    if re.match(content_pattern, next_line.strip()):
                        # 遇到下一个 content_pattern，停止收集，不移动 i（让外层循环处理）
                        break
                    content_lines.append(next_line)
                    i += 1
                # 合并内容，保留换行符
                content = '\n'.join(content_lines).strip()
                theme_parts = []
                for level in range(1, 5):
                    if chapters[level]:
                        theme_parts.append(chapters[level])
                theme = '--'.join(theme_parts) if theme_parts else ""
                result.append((content, classification, theme))
                # 注意：如果遇到下一个 content_pattern，i 已经指向它，外层循环会继续处理
                # 如果没有遇到（文件结束），循环会自动结束
            else:
                i += 1
    definitions = []
    examples = []
    proofs = []
    others = []
    for item in result:
        content, classification, theme = item
        if classification.startswith("定义"):
            definitions.append(item)
        elif classification.startswith("例子"):
            examples.append(item)
        elif classification.startswith("证明"):
            proofs.append(item)
        else:
            others.append(item)
    return definitions, examples, proofs, others, Theme

