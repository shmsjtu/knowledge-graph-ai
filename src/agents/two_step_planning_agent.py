# agents/two_step_planning_agent.py
"""
两步规划智能体 - 将规划过程拆分为两步：
第一步：章节分组（输入目录和内容长度）
第二步：跨章节关系提取（输入分组信息，可并行执行）
"""

from typing import Dict, List, Optional
import sys
import os
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_agent import BaseAgent
from src.utils.json_parser import JSONParser
from src.infrastructure import Logger


class TwoStepPlanningAgent(BaseAgent):
    """两步规划智能体"""
    _STEP2_SINGLE_CALL_THRESHOLD = 3
    _STEP2_WINDOW_COUNT = 5

    def initialize(self):
        """初始化规划智能体"""
        # 第一步的 system prompt
        from src.config.two_step_planning_prompts import PLANNING_STEP1_SYSTEM_PROMPT
        self.set_system_prompt(PLANNING_STEP1_SYSTEM_PROMPT)

    def execute(self, toc_content: str, section_lengths: Dict[str, int] = None) -> Dict:
        """
        执行两步规划任务

        Args:
            toc_content: 教材目录内容
            section_lengths: 章节内容长度字典 {章节名: 字符数}

        Returns:
            任务计划字典
        """
        return self.two_step_planning(toc_content, section_lengths)

    def two_step_planning(
        self,
        toc_content: str,
        section_lengths: Dict[str, int] = None,
        max_workers: int = 3
    ) -> Dict:
        """
        两步规划流程

        Args:
            toc_content: 教材目录内容
            section_lengths: 章节内容长度字典
            max_workers: 第一步和第二步并行执行的最大线程数

        Returns:
            完整的任务计划
        """
        self.logger.info("开始两步规划...")

        # 第一步：章节分组（可并行）
        self.logger.info("\n[第一步] 章节分组...")
        step1_result = self._step1_group_sections(toc_content, section_lengths, max_workers)

        # 第二步：跨章节关系提取（可并行）
        self.logger.info("\n[第二步] 跨章节关系提取...")
        step2_result = self._step2_extract_cross_relations(
            step1_result,
            max_workers
        )

        # 合并结果
        final_plan = self._merge_results(step1_result, step2_result)

        self.logger.info(f"\n规划完成，生成 {len(final_plan.get('subtasks', []))} 个节点提取任务，"
                        f"{len(final_plan.get('cross_section_relations', []))} 个跨章节关系任务")

        return final_plan

    def _step1_group_sections(
        self,
        toc_content: str,
        section_lengths: Dict[str, int] = None,
        max_workers: int = 3
    ) -> Dict:
        """
        第一步：章节分组（自动分割）

        Args:
            toc_content: 教材目录内容
            section_lengths: 章节内容长度字典
            max_workers: 最大并行数（保留参数，但不再使用LLM并行）

        Returns:
            包含 section_groups 和 subtasks 的字典
        """
        self.logger.info("使用自动分割策略...")

        # 使用新的自动分割逻辑
        return self._auto_split_sections(toc_content, section_lengths or {}, max_chars=2000)

    def _process_level2_section(
        self,
        batch_agent,
        level2_section: Dict,
        section_lengths: Dict[str, int],
        section_idx: int
    ) -> Dict:
        """
        处理单个二级标题下的分组

        Args:
            batch_agent: 批次 agent 实例
            level2_section: 二级标题信息 {title, subsections}
            section_lengths: 章节内容长度字典
            section_idx: 章节索引

        Returns:
            该二级标题下的分组结果
        """
        from src.config.two_step_planning_prompts import (
            PLANNING_STEP1_SYSTEM_PROMPT,
            PLANNING_STEP1_USER_TEMPLATE
        )
        from src.core.constants import APIConstants

        # 初始化
        batch_agent.initialize()
        batch_agent.update_system_prompt(PLANNING_STEP1_SYSTEM_PROMPT)

        # 构造该二级标题的目录内容
        title = level2_section.get("title", "")
        subsections = level2_section.get("subsections", [])

        toc_lines = [title]
        for subsection in subsections:
            toc_lines.append(f"  {subsection}")

        toc_content = "\n".join(toc_lines)

        # 筛选该二级标题下的章节长度信息
        if section_lengths:
            filtered_lengths = {
                k: v for k, v in section_lengths.items()
                if k in subsections or k == title
            }
        else:
            filtered_lengths = {}

        # 格式化章节长度信息
        section_lengths_str = self._format_section_lengths(filtered_lengths)

        # 构造用户消息
        user_message = PLANNING_STEP1_USER_TEMPLATE.format(
            toc_content=toc_content,
            section_lengths=section_lengths_str
        )

        batch_agent.conversation_manager.add_user_message(user_message)

        # 调用 API
        response = batch_agent._call_api(model=APIConstants.DEFAULT_MODEL, json_mode=True)

        batch_agent.conversation_manager.add_assistant_message(response)

        # 解析响应
        result = self._parse_step1_response(response)

        return result

    def _parse_toc_by_level2(self, toc_content: str) -> List[Dict]:
        """
        按二级标题解析目录

        Args:
            toc_content: 目录内容

        Returns:
            二级标题列表，每个元素包含 {title, subsections}
        """
        lines = toc_content.strip().split("\n")
        level2_sections = []
        current_level2 = None
        current_subsections = []

        for line in lines:
            line = line.rstrip()
            if not line:
                continue

            # Markdown 格式：
            # 二级标题：有2个空格缩进（如 "  多元函数微分学"）
            # 三级标题：有4个空格缩进（如 "    1. 定义与基本性质"）

            # 计算前导空格数
            stripped = line.lstrip()
            spaces = len(line) - len(stripped)

            # 检测二级标题（2个空格缩进）
            if spaces == 2:
                # 这是二级标题
                # 保存之前的二级标题
                if current_level2:
                    level2_sections.append({
                        "title": current_level2,
                        "subsections": current_subsections
                    })

                # 开始新的二级标题
                current_level2 = stripped
                current_subsections = []

            elif spaces == 4:
                # 这是三级标题（4个空格缩进）
                if current_level2:
                    current_subsections.append(stripped)

        # 保存最后一个二级标题
        if current_level2:
            level2_sections.append({
                "title": current_level2,
                "subsections": current_subsections
            })

        return level2_sections

    def _auto_split_sections(
        self,
        toc_content: str,
        section_lengths: Dict[str, int],
        max_chars: int = 4000
    ) -> Dict:
        """
        自动分割章节（基于字符数）- 分拆再合并策略

        Args:
            toc_content: 目录内容
            section_lengths: 章节长度字典
            max_chars: 每组最大字符数

        Returns:
            包含 section_groups 和 subtasks 的字典
        """
        self.logger.info(f"开始自动分割，最大字符数: {max_chars}")

        # Step 1: Split to finest granularity
        leaf_sections = self._split_to_leaf_sections(toc_content)
        self.logger.info(f"拆分到最小粒度，共 {len(leaf_sections)} 个叶子章节")

        # Step 2: Calculate character count for each leaf section
        leaf_with_lengths = self._calculate_leaf_lengths(leaf_sections, section_lengths or {})

        # Step 3: Merge adjacent sections if combined length < max_chars
        merged_groups = self._merge_sections(leaf_with_lengths, max_chars)
        self.logger.info(f"合并后共 {len(merged_groups)} 个章节组")

        # Step 4: Generate subtasks
        return self._create_subtasks_from_groups(merged_groups)

    def _split_to_leaf_sections(self, toc_content: str) -> List[Dict]:
        """
        将目录拆分到最小粒度（level-4 或直到没有子章节）

        Args:
            toc_content: 目录内容

        Returns:
            叶子章节列表，每个元素包含 {path: [章节路径], title: "章节标题"}
        """
        lines = toc_content.strip().split("\n")
        leaf_sections = []

        # 栈结构用于追踪当前路径
        path_stack = []  # [(level, title)]

        for line in lines:
            line = line.rstrip()
            if not line:
                continue

            # 计算前导空格数
            stripped = line.lstrip()
            spaces = len(line) - len(stripped)

            # 确定层级（每2个空格一个层级）
            level = spaces // 2

            # 更新路径栈
            while path_stack and path_stack[-1][0] >= level:
                path_stack.pop()

            path_stack.append((level, stripped))

            # 检查是否为叶子节点（下一行层级更深或没有下一行）
            # 简化处理：所有节点都作为潜在叶子节点
            path = [title for _, title in path_stack]
            leaf_sections.append({
                "path": path,
                "title": stripped,
                "level": level
            })

        # 过滤：只保留真正的叶子节点（没有子节点的节点）
        true_leaves = []
        for i, section in enumerate(leaf_sections):
            is_leaf = True
            # 检查下一个节点是否是子节点
            if i + 1 < len(leaf_sections):
                next_section = leaf_sections[i + 1]
                if next_section["level"] > section["level"]:
                    is_leaf = False

            if is_leaf:
                true_leaves.append(section)

        return true_leaves

    def _calculate_leaf_lengths(
        self,
        leaf_sections: List[Dict],
        section_lengths: Dict[str, int]
    ) -> List[Dict]:
        """
        计算每个叶子章节的字符数

        Args:
            leaf_sections: 叶子章节列表
            section_lengths: 章节长度字典

        Returns:
            包含字符数的叶子章节列表
        """
        result = []

        section_lengths = section_lengths or {}

        # 调试：输出 section_lengths 的键
        self.logger.debug(f"section_lengths 键列表: {list(section_lengths.keys())[:10]}")

        for section in leaf_sections:
            title = section["title"]
            path = section["path"]

            # 尝试标题直接匹配（最常见的情况）
            char_count = section_lengths.get(title, 0)

            # 如果匹配不到，尝试去掉编号前缀匹配
            if char_count == 0:
                # 去掉类似 "1. ", "2. " 这样的编号前缀
                import re
                title_no_number = re.sub(r'^\d+\.\s*', '', title)
                char_count = section_lengths.get(title_no_number, 0)

            # 调试日志
            if char_count == 0:
                self.logger.debug(f"未匹配到章节: {title}")

            result.append({
                **section,
                "char_count": char_count
            })

        # 统计匹配情况
        matched_count = sum(1 for s in result if s["char_count"] > 0)
        self.logger.info(f"章节长度匹配: {matched_count}/{len(result)} 个叶子章节")

        return result

    def _merge_sections(
        self,
        leaf_with_lengths: List[Dict],
        max_chars: int
    ) -> List[Dict]:
        """
        合并相邻的小章节

        Args:
            leaf_with_lengths: 包含字符数的叶子章节列表
            max_chars: 每组最大字符数

        Returns:
            合并后的章节组列表
        """
        if not leaf_with_lengths:
            return []

        groups = []
        current_group = []
        current_length = 0

        for section in leaf_with_lengths:
            section_length = section.get("char_count", 0)

            # 如果当前组为空，直接添加
            if not current_group:
                current_group.append(section)
                current_length = section_length
            # 如果添加后不超过限制，则合并
            elif current_length + section_length <= max_chars:
                current_group.append(section)
                current_length += section_length
            # 否则，保存当前组，开始新组
            else:
                if current_group:
                    groups.append(self._create_group(current_group))
                current_group = [section]
                current_length = section_length

        # 保存最后一组
        if current_group:
            groups.append(self._create_group(current_group))

        return groups

    def _create_group(self, sections: List[Dict]) -> Dict:
        """
        创建章节组

        Args:
            sections: 章节列表

        Returns:
            章节组字典
        """
        paths = [s["path"] for s in sections]
        titles = [s["title"] for s in sections]
        total_length = sum(s.get("char_count", 0) for s in sections)

        return {
            "section_paths": paths,
            "section_titles": titles,
            "total_length": total_length,
            "_sections": sections  # 保存原始章节信息用于日志输出
        }

    def _create_subtasks_from_groups(self, groups: List[Dict]) -> Dict:
        """
        从章节组生成子任务

        Args:
            groups: 章节组列表

        Returns:
            包含 section_groups 和 subtasks 的字典
        """
        section_groups = []
        subtasks = []

        # 输出分组结果
        self.logger.info("=" * 80)
        self.logger.info("自动分组结果：")
        self.logger.info("=" * 80)

        for i, group in enumerate(groups):
            # 创建 section_group
            section_group = {
                "group_id": i + 1,
                "sections": group["section_titles"],
                "total_length": group["total_length"]
            }
            section_groups.append(section_group)

            # 输出每个分组的信息
            self.logger.info(f"\n分组 {i + 1} (总字符数: {group['total_length']})：")
            for j, title in enumerate(group["section_titles"], 1):
                # 找到对应章节的字符数
                char_count = 0
                for section in group.get("_sections", []):
                    if section["title"] == title:
                        char_count = section.get("char_count", 0)
                        break
                self.logger.info(f"  {j}. {title} ({char_count} 字符)")

            # 创建 subtask
            subtask = {
                "task_id": f"node_extraction_{i + 1}",
                "task_type": "node_extraction",
                "target_sections": group["section_titles"],
                "section_paths": group["section_paths"],
                "estimated_length": group["total_length"]
            }
            subtasks.append(subtask)

        self.logger.info(f"\n生成 {len(section_groups)} 个章节组，{len(subtasks)} 个子任务")
        self.logger.info("=" * 80)

        return {
            "section_groups": section_groups,
            "subtasks": subtasks
        }

    def _step2_extract_cross_relations(
        self,
        step1_result: Dict,
        max_workers: int = 3
    ) -> List[Dict]:
        """
        第二步：跨章节关系提取（可并行执行）

        Args:
            step1_result: 第一步的结果
            max_workers: 最大并行数

        Returns:
            跨章节关系任务列表
        """
        section_groups = step1_result.get("section_groups", [])
        existing_subtasks = step1_result.get("subtasks", [])

        # 如果章节组数量较少，直接单次调用
        if len(section_groups) <= self._STEP2_SINGLE_CALL_THRESHOLD:
            self.logger.info("章节组数量较少，使用单次调用...")
            return self._step2_single_call(section_groups, existing_subtasks)

        # 如果章节组数量较多，并行执行
        self.logger.info(f"章节组数量较多（{len(section_groups)}），使用并行调用...")
        return self._step2_parallel_calls(
            section_groups,
            existing_subtasks,
            max_workers
        )

    def _step2_single_call(
        self,
        section_groups: List[Dict],
        existing_subtasks: List[Dict]
    ) -> List[Dict]:
        """
        第二步：单次调用（适用于章节组较少的情况）

        Args:
            section_groups: 章节分组列表
            existing_subtasks: 已有的节点提取任务

        Returns:
            跨章节关系任务列表
        """
        from src.config.two_step_planning_prompts import PLANNING_STEP2_SYSTEM_PROMPT

        # 重置对话上下文，设置第二步的 system prompt
        self.reset()
        self.update_system_prompt(PLANNING_STEP2_SYSTEM_PROMPT)
        cross_relations = self._run_step2_call(section_groups, existing_subtasks, agent=self)

        self.logger.info(f"第二步完成，生成 {len(cross_relations)} 个跨章节关系任务")

        return cross_relations

    def _step2_parallel_calls(
        self,
        section_groups: List[Dict],
        existing_subtasks: List[Dict],
        max_workers: int
    ) -> List[Dict]:
        """
        第二步：并行调用（适用于章节组较多的情况）

        将章节组分成多个批次，每个批次独立调用 LLM，
        最后汇总所有跨章节关系任务。

        Args:
            section_groups: 章节分组列表
            existing_subtasks: 已有的节点提取任务
            max_workers: 最大并行数

        Returns:
            汇总的跨章节关系任务列表
        """
        # 将章节组按滑动窗口分批
        batches = self._create_section_group_batches(section_groups)

        self.logger.info(
            f"将 {len(section_groups)} 个章节组按滑动窗口分成 {len(batches)} 个批次"
        )

        all_cross_relations = []

        # 并行执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for batch_idx, batch_groups in enumerate(batches):
                # 为每个批次创建新的 agent 实例
                batch_agent = self._create_batch_agent()

                # 提交任务
                future = executor.submit(
                    self._process_batch,
                    batch_agent,
                    batch_groups,
                    existing_subtasks,
                    batch_idx
                )
                futures[future] = batch_idx

            # 收集结果
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    cross_relations = future.result()
                    all_cross_relations.extend(cross_relations)
                    self.logger.info(f"批次 {batch_idx} 完成，生成 {len(cross_relations)} 个跨章节关系任务")
                except Exception as e:
                    self.logger.error(f"批次 {batch_idx} 执行失败: {e}")

        # 去重和验证
        all_cross_relations = self._deduplicate_cross_relations(all_cross_relations)

        self.logger.info(f"第二步完成，汇总后共 {len(all_cross_relations)} 个跨章节关系任务")

        return all_cross_relations

    def _create_batch_agent(self):
        """创建用于批处理的 agent 实例"""
        return TwoStepPlanningAgent(
            api_client=self.api_client,
            logger=Logger("BatchAgent")
        )

    def _build_step2_user_message(
        self,
        section_groups: List[Dict],
        existing_subtasks: List[Dict]
    ) -> str:
        """构造第二步用户消息"""
        from src.config.two_step_planning_prompts import PLANNING_STEP2_USER_TEMPLATE

        section_groups_str = JSONParser.to_json_string(section_groups)
        existing_subtasks_str = JSONParser.to_json_string(existing_subtasks)
        return PLANNING_STEP2_USER_TEMPLATE.format(
            section_groups=section_groups_str,
            existing_subtasks=existing_subtasks_str
        )

    def _run_step2_call(
        self,
        section_groups: List[Dict],
        existing_subtasks: List[Dict],
        agent: Optional["TwoStepPlanningAgent"] = None
    ) -> List[Dict]:
        """执行第二步单次 API 调用并返回跨章节任务"""
        from src.core.constants import APIConstants

        caller = agent or self
        user_message = self._build_step2_user_message(section_groups, existing_subtasks)
        caller.conversation_manager.add_user_message(user_message)

        response = caller._call_api(model=APIConstants.DEFAULT_MODEL, json_mode=True)
        caller.conversation_manager.add_assistant_message(response)
        self.logger.info(f"第二步 API 响应长度: {len(response)} 字符")

        result = self._parse_step2_response(response)
        return result.get("cross_section_relations", [])

    def _process_batch(
        self,
        batch_agent,
        batch_groups: List[Dict],
        existing_subtasks: List[Dict],
        batch_idx: int
    ) -> List[Dict]:
        """
        处理单个批次

        Args:
            batch_agent: 批次 agent 实例
            batch_groups: 该批次的章节组
            existing_subtasks: 已有的节点提取任务
            batch_idx: 批次索引

        Returns:
            该批次的跨章节关系任务列表
        """
        from src.config.two_step_planning_prompts import PLANNING_STEP2_SYSTEM_PROMPT

        # 初始化
        batch_agent.initialize()
        batch_agent.update_system_prompt(PLANNING_STEP2_SYSTEM_PROMPT)
        return self._run_step2_call(batch_groups, existing_subtasks, agent=batch_agent)

    def _create_section_group_batches(
        self,
        section_groups: List[Dict],
        window_count: int = _STEP2_WINDOW_COUNT
    ) -> List[List[Dict]]:
        """
        将章节组分成滑动窗口批次

        Args:
            section_groups: 章节分组列表
            window_count: 窗口数量（默认 5）

        Returns:
            批次列表
        """
        total = len(section_groups)
        if total == 0:
            return []

        if total <= window_count:
            return [[group] for group in section_groups]

        # 默认分为 5 个窗口；为了形成滑动窗口，引入重叠窗口（stride < window_size）
        window_size = math.ceil(total / window_count)
        max_start = total - window_size
        stride = math.ceil(max_start / (window_count - 1)) if window_count > 1 else window_size
        if stride >= window_size and window_size > 1:
            stride = window_size - 1

        starts = []
        for i in range(window_count):
            start = min(i * stride, max_start)
            if not starts or start != starts[-1]:
                starts.append(start)

        if starts[-1] != max_start:
            starts.append(max_start)

        return [section_groups[start:start + window_size] for start in starts]

    def _deduplicate_cross_relations(self, cross_relations: List[Dict]) -> List[Dict]:
        """
        去重跨章节关系任务

        Args:
            cross_relations: 跨章节关系任务列表

        Returns:
            去重后的列表
        """
        seen_keys = set()
        unique_relations = []

        for relation in cross_relations:
            # 使用 target_groups 作为去重键
            target_groups = tuple(sorted(relation.get("target_groups", [])))
            if target_groups not in seen_keys:
                seen_keys.add(target_groups)
                unique_relations.append(relation)

        return unique_relations

    def _format_section_lengths(self, section_lengths: Dict[str, int]) -> str:
        """
        格式化章节长度信息

        Args:
            section_lengths: {章节名: 字符数}

        Returns:
            格式化的字符串
        """
        if not section_lengths:
            return "（未提供章节长度信息）"

        lines = []
        for section, length in section_lengths.items():
            tokens = length // 4  # 估算 tokens
            lines.append(f"- {section}: {length} 字符 (约 {tokens} tokens)")

        return "\n".join(lines)

    def _parse_step1_response(self, response: str) -> Dict:
        """解析第一步的响应"""
        try:
            result = JSONParser.parse(response, repair=True)
            result = self._validate_step1_result(result)
            return result
        except Exception as e:
            self.logger.error(f"解析第一步响应失败: {e}")
            return self._get_default_step1_result()

    def _parse_step2_response(self, response: str) -> Dict:
        """解析第二步的响应"""
        try:
            result = JSONParser.parse(response, repair=True)
            result = self._validate_step2_result(result)
            return result
        except Exception as e:
            self.logger.error(f"解析第二步响应失败: {e}")
            return {"cross_section_relations": []}

    def _validate_step1_result(self, result: Dict) -> Dict:
        """验证并补全第一步结果"""
        if "section_groups" not in result:
            result["section_groups"] = []

        # 自动生成 subtasks（如果 LLM 没有输出）
        if "subtasks" not in result or not result["subtasks"]:
            result["subtasks"] = self._auto_generate_subtasks(result["section_groups"])

        if "analysis" not in result:
            result["analysis"] = {}

        return result

    def _auto_generate_subtasks(self, section_groups: List[Dict]) -> List[Dict]:
        """
        自动为每个章节组生成节点提取任务

        Args:
            section_groups: 章节分组列表

        Returns:
            自动生成的任务列表
        """
        subtasks = []
        for idx, group in enumerate(section_groups, 1):
            task = {
                "task_id": f"task_{idx}",
                "task_type": "extract_nodes_and_internal_relations",
                "target_sections": group.get("sections", []),
                "section_group": group.get("group_id", f"group_{idx}"),
                "dependencies": []
            }
            subtasks.append(task)

        return subtasks

    def _validate_step2_result(self, result: Dict) -> Dict:
        """验证并补全第二步结果"""
        if "cross_section_relations" not in result:
            result["cross_section_relations"] = []

        # 为跨章节关系任务自动添加 task_type（如果 LLM 没有输出）
        for task in result["cross_section_relations"]:
            if "task_type" not in task:
                task["task_type"] = "extract_cross_section_relations"

        return result

    def _merge_results(self, step1_result: Dict, cross_relations: List[Dict]) -> Dict:
        """
        合并第一步和第二步的结果

        Args:
            step1_result: 第一步结果
            cross_relations: 第二步的跨章节关系任务列表

        Returns:
            完整的计划
        """
        final_plan = {
            "analysis": step1_result.get("analysis", {}),
            "section_groups": step1_result.get("section_groups", []),
            "subtasks": step1_result.get("subtasks", []),
            "cross_section_relations": cross_relations
        }

        return final_plan

    def _get_default_step1_result(self) -> Dict:
        """返回默认的第一步结果"""
        return {
            "analysis": {},
            "section_groups": [],
            "subtasks": []
        }
