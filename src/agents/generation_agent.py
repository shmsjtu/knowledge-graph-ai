# agents/generation_agent.py
"""
生成智能体 - 根据任务提取节点和关系
"""

from typing import List, Dict, Optional
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_agent import BaseAgent
from src.core.result_types import Node, Relation
from src.utils.json_parser import JSONParser


class GenerationAgent(BaseAgent):
    """生成智能体"""

    def initialize(self):
        """初始化生成智能体"""
        from src.config.prompts import GENERATOR_NODE_SYSTEM_PROMPT
        self.set_system_prompt(GENERATOR_NODE_SYSTEM_PROMPT)

    def execute(self, task: Dict, material_text: str = None, existing_nodes: List[Node] = None):
        """
        执行生成任务

        Args:
            task: 任务定义
            material_text: 教材文本
            existing_nodes: 已有节点（用于关系提取）

        Returns:
            提取结果
        """
        task_type = task.get("task_type")

        if task_type in ["extract_nodes", "extract_nodes_and_internal_relations"]:
            nodes = self.extract_nodes(task, material_text)
            if task_type == "extract_nodes":
                return nodes, []
            else:
                relations = self.extract_relations(task, nodes, material_text)
                return nodes, relations
        elif task_type == "extract_relations":
            relations = self.extract_relations(task, existing_nodes, material_text)
            return [], relations
        elif task_type == "extract_cross_section_relations":
            relations = self.extract_relations(task, existing_nodes, material_text)
            return [], relations
        else:
            return [], []

    def extract_nodes(self, task: Dict, material_text: str = None) -> List[Node]:
        """
        提取节点

        Args:
            task: 任务定义
            material_text: 教材文本

        Returns:
            节点列表
        """
        self.logger.info(f"开始提取节点: {task.get('task_id')}")

        # 导入提示词
        from src.config.prompts import GENERATOR_NODE_USER_TEMPLATE
        from src.utils.unified_section_extractor import UnifiedSectionExtractor

        # 根据目标章节提取内容
        target_sections = task.get("target_sections", [])
        if material_text and target_sections and target_sections != ["all"]:
            self.logger.info(f"提取章节内容: {target_sections}")
            # 使用统一提取器，自动识别文件类型
            content = UnifiedSectionExtractor.extract_sections(material_text, target_sections)
            self.logger.info(f"提取的章节内容长度: {len(content)} 字符")
        else:
            content = material_text or task.get("material_text", "")

        # 按类型分别提取（每次提取都重置对话上下文）
        all_nodes = []
        node_types = ["定义", "定理", "实例"]

        for node_type in node_types:
            # 重置对话上下文，只保留 system prompt
            self.reset()

            # 提取该类型的节点
            nodes = self._extract_nodes_by_type(task, content, node_type)
            all_nodes.extend(nodes)

        self.logger.info(f"提取完成，共 {len(all_nodes)} 个节点")
        return all_nodes

    def extract_relations(
        self,
        task: Dict,
        existing_nodes: List[Node],
        material_text: str = None
    ) -> List[Relation]:
        """
        提取关系

        Args:
            task: 任务定义
            existing_nodes: 已有节点列表
            material_text: 教材文本

        Returns:
            关系列表
        """
        self.logger.info(f"开始提取关系: {task.get('task_id')}")

        # 导入提示词
        from src.config.prompts import GENERATOR_RELATION_SYSTEM_PROMPT, GENERATOR_RELATION_USER_TEMPLATE
        from src.utils.unified_section_extractor import UnifiedSectionExtractor

        # 切换到关系提取的系统提示
        self.update_system_prompt(GENERATOR_RELATION_SYSTEM_PROMPT)

        # 根据目标章节提取内容
        target_sections = task.get("target_sections", [])
        if material_text and target_sections and target_sections != ["all"]:
            self.logger.info(f"提取章节内容: {target_sections}")
            # 使用统一提取器，自动识别文件类型
            content = UnifiedSectionExtractor.extract_sections(material_text, target_sections)
            self.logger.info(f"提取的章节内容长度: {len(content)} 字符")
        else:
            content = material_text or task.get("material_text", "")

        # 构造用户消息
        extraction_focus = ["逻辑关系", "依赖关系"]

        # 格式化节点列表
        nodes_str = ""
        if existing_nodes:
            nodes_str = JSONParser.to_json_string([n.to_dict() for n in existing_nodes[:100]])

        user_message = GENERATOR_RELATION_USER_TEMPLATE.format(
            target_sections=', '.join(target_sections) if isinstance(target_sections, list) else target_sections,
            extraction_focus=', '.join(extraction_focus),
            node_count=len(existing_nodes) if existing_nodes else 0,
            nodes=nodes_str if nodes_str else "（无已有节点）",
            content=content if content else "（请使用工具获取教材内容）"
        )

        self.conversation_manager.add_user_message(user_message)

        # 调用API（启用JSON模式）
        response = self._call_api(json_mode=True)
        self.conversation_manager.add_assistant_message(response)

        # 解析关系
        relations = self._parse_relations(response)

        # 验证节点存在性
        if existing_nodes:
            relations = self._validate_relation_nodes(relations, existing_nodes)

        self.logger.info(f"提取完成，共 {len(relations)} 条有效关系")
        return relations

    def improve_nodes(self, feedback: Dict) -> List[Node]:
        """
        根据反馈改进节点

        Args:
            feedback: 评估反馈

        Returns:
            改进后的节点列表
        """
        self.logger.info("开始改进节点...")

        improvement_prompt = self._build_node_improvement_prompt(feedback)
        self.conversation_manager.add_user_message(improvement_prompt)

        response = self._call_api()
        self.conversation_manager.add_assistant_message(response)

        nodes = self._parse_nodes(response)

        self.logger.info(f"改进完成，共 {len(nodes)} 个节点")
        return nodes

    def improve_relations(self, feedback: Dict, existing_nodes: List[Node]) -> List[Relation]:
        """
        根据反馈改进关系

        Args:
            feedback: 评估反馈
            existing_nodes: 已有节点列表

        Returns:
            改进后的关系列表
        """
        self.logger.info("开始改进关系...")

        improvement_prompt = self._build_relation_improvement_prompt(feedback, existing_nodes)
        self.conversation_manager.add_user_message(improvement_prompt)

        response = self._call_api()
        self.conversation_manager.add_assistant_message(response)

        relations = self._parse_relations(response)

        self.logger.info(f"改进完成，共 {len(relations)} 条关系")
        return relations

    def _extract_nodes_by_type(self, task: Dict, content: str, node_type: str) -> List[Node]:
        """按类型提取节点"""
        from src.config.prompts import GENERATOR_NODE_USER_TEMPLATE

        target_sections = task.get("target_sections", [])

        user_message = GENERATOR_NODE_USER_TEMPLATE.format(
            target_sections=', '.join(target_sections) if isinstance(target_sections, list) else target_sections,
            extraction_focus=node_type,
            content=content
        )

        user_message += f"\n\n**重要：仅提取【{node_type}】类型的节点，不要提取其他类型。**"

        self.conversation_manager.add_user_message(user_message)

        # 调用API（启用JSON模式）
        response = self._call_api(json_mode=True)
        self.conversation_manager.add_assistant_message(response)

        return self._parse_nodes(response)

    def _parse_nodes(self, response: str) -> List[Node]:
        """解析节点响应"""
        try:
            nodes_data = JSONParser.parse(response, repair=True)

            nodes = []
            for item in nodes_data:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    nodes.append(Node.from_tuple(item))
                elif isinstance(item, dict):
                    nodes.append(Node.from_dict(item))

            return nodes

        except Exception as e:
            self.logger.error(f"解析节点失败: {e}")
            return []

    def _parse_relations(self, response: str) -> List[Relation]:
        """解析关系响应"""
        try:
            relations_data = JSONParser.parse(response, repair=True)

            relations = []
            for item in relations_data:
                if isinstance(item, (list, tuple)) and len(item) == 3:
                    relations.append(Relation.from_tuple(item))
                elif isinstance(item, dict):
                    relations.append(Relation.from_dict(item))

            return relations

        except Exception as e:
            self.logger.error(f"解析关系失败: {e}")
            return []

    def _validate_relation_nodes(
        self,
        relations: List[Relation],
        existing_nodes: List[Node]
    ) -> List[Relation]:
        """
        验证关系中的节点是否在已有节点列表中

        Args:
            relations: 提取的关系列表
            existing_nodes: 已有节点列表

        Returns:
            过滤后的关系列表（只包含节点存在的关系）
        """
        if not existing_nodes:
            self.logger.warning("没有提供已有节点列表，跳过节点验证")
            return relations

        # 创建节点名称集合（用于快速查找）
        node_names = {n.name for n in existing_nodes}

        valid_relations = []
        invalid_count = 0

        for relation in relations:
            if relation.object_a in node_names and relation.object_b in node_names:
                valid_relations.append(relation)
            else:
                invalid_count += 1
                missing_nodes = []
                if relation.object_a not in node_names:
                    missing_nodes.append(relation.object_a)
                if relation.object_b not in node_names:
                    missing_nodes.append(relation.object_b)

                self.logger.warning(
                    f"关系 [{relation.object_a} -> {relation.object_b}] "
                    f"包含不存在的节点: {missing_nodes}，已过滤"
                )

        if invalid_count > 0:
            self.logger.warning(
                f"过滤了 {invalid_count} 条关系（节点不存在于列表中）"
            )

        return valid_relations

    def _build_node_improvement_prompt(self, feedback: Dict) -> str:
        """构建节点改进提示"""
        node_feedback = feedback.get("node_feedback", {})
        evaluation_results = node_feedback.get("evaluation_results", [])

        # 提取不合格节点
        issues_list = []
        for result in evaluation_results:
            if len(result.get("issues", [])) > 0:
                issues_list.append(result)

        if not issues_list:
            return "所有节点都合格，无需改进。"

        # 构建改进提示
        prompt = f"""根据评估反馈，请**仅改进不合格的节点**。

## 不合格的节点（共 {len(issues_list)} 个）
"""
        for issue in issues_list:
            prompt += f"\n### {issue.get('item')}"
            prompt += f"\n问题: {', '.join(issue.get('issues', []))}"
            if issue.get('suggestions'):
                prompt += f"\n建议: {', '.join(issue.get('suggestions', []))}"
            if issue.get('example_fix'):
                fix = issue['example_fix']
                if fix.get('after'):
                    prompt += f"\n\n修改示例:"
                    prompt += f"\n修改前: {fix.get('before')}"
                    prompt += f"\n修改后: {fix.get('after')}"

        prompt += """

## 重要要求
1. **只输出改进后的节点**，不要输出已经合格的节点
2. 参考修改示例进行改进
3. 如果建议删除，则不要输出该节点
4. 保持 JSON 格式输出
5. 输出格式：[["节点名称", {"desc": "描述", "level": 0, "color": "#FF0000"}]]

请仅输出改进后的节点："""

        return prompt

    def _build_relation_improvement_prompt(self, feedback: Dict, existing_nodes: List[Node]) -> str:
        """构建关系改进提示"""
        rel_feedback = feedback.get("rel_feedback", {})
        evaluation_results = rel_feedback.get("evaluation_results", [])

        # 提取不合格关系
        issues_list = []
        for result in evaluation_results:
            if len(result.get("issues", [])) > 0 or not result.get("logic_check", {}).get("mathematically_valid", True):
                issues_list.append(result)

        if not issues_list:
            return "所有关系都合格，无需改进。"

        # 构建改进提示
        prompt = f"""根据评估反馈，请**仅改进不合格的关系**。

## 不合格的关系（共 {len(issues_list)} 条）
"""
        for issue in issues_list:
            prompt += f"\n### {issue.get('item')}"
            prompt += f"\n问题: {', '.join(issue.get('issues', []))}"
            if issue.get('suggestions'):
                prompt += f"\n建议: {', '.join(issue.get('suggestions', []))}"
            if issue.get('example_fix'):
                fix = issue['example_fix']
                if fix.get('after'):
                    prompt += f"\n\n修改示例:"
                    prompt += f"\n修改前: {fix.get('before')}"
                    prompt += f"\n修改后: {fix.get('after')}"

        if existing_nodes:
            nodes_str = "\n".join([f"  - {n.name}" for n in existing_nodes[:50]])
            prompt += f"\n\n## 已有节点（共 {len(existing_nodes)} 个，显示前50个）\n{nodes_str}"

        prompt += """

## 重要要求
1. **只输出改进后的关系**，不要输出已经合格的关系
2. 参考修改示例进行改进
3. 如果建议删除，则不要输出该关系
4. 保持 JSON 格式输出
5. 输出格式：[["节点A", "节点B", {"rel": "关系类型", "定理": "说明", "color": "#F5B721"}]]

请仅输出改进后的关系："""

        return prompt
