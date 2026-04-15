# pipeline/iteration_manager.py
"""
迭代管理器 - 统一管理迭代改进逻辑

修改说明：
- EvaluationAgent既评估又修改（提示词已包含example_fix）
- GenerationAgent不再需要improve方法
- 迭代流程简化：提取 -> 评估+修改 -> 合并结果
"""

from typing import List
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.result_types import Node, Relation, EvaluationResult
from src.agents import GenerationAgent, EvaluationAgent
from src.infrastructure import Logger


class IterationManager:
    """迭代管理器 - 统一管理迭代改进逻辑"""

    UNQUALIFIED_ROUND3_MARKER = "__unqualified_after_3_rounds__"

    def __init__(self):
        self.logger = Logger("IterationManager")

    def improve_nodes(
        self,
        nodes: List[Node],
        generation_agent: GenerationAgent,
        evaluation_agent: EvaluationAgent,
        max_iterations: int
    ) -> List[Node]:
        """
        迭代改进节点

        新流程：
        1. EvaluationAgent评估节点并生成修改建议（包含example_fix）
        2. 从evaluation_result中提取修改后的节点
        3. 合并合格节点和修改后的节点
        4. 重复直到没有不合格节点或达到最大迭代次数

        Args:
            nodes: 初始节点列表
            generation_agent: 生成智能体（用于重新提取，如果需要）
            evaluation_agent: 评估智能体（评估+修改）
            max_iterations: 最大迭代次数

        Returns:
            改进后的合格节点列表
        """
        if not nodes:
            return []

        # 初始化评估智能体
        evaluation_agent.initialize()

        # 评估节点（评估+修改建议）
        eval_result = evaluation_agent.evaluate_nodes(nodes)

        qualified_nodes = eval_result.qualified_nodes
        unqualified_nodes = eval_result.unqualified_nodes

        self.logger.info(f"初始评估: {len(qualified_nodes)} 合格, {len(unqualified_nodes)} 不合格")

        # 迭代改进
        iteration = 1
        while iteration <= max_iterations and unqualified_nodes:
            self.logger.info(f"迭代 {iteration}/{max_iterations}: 改进 {len(unqualified_nodes)} 个节点...")

            # 从评估结果中提取修改后的节点
            improved_nodes = self._extract_improved_nodes_from_evaluation(
                eval_result.feedback.get("node_feedback", {})
            )

            if not improved_nodes:
                self.logger.warning("评估结果中没有修改建议，停止迭代")
                break

            # 去重：排除已经在合格列表中的节点
            qualified_names = {n.name for n in qualified_nodes}
            unique_improved_nodes = [n for n in improved_nodes if n.name not in qualified_names]

            # 重新评估修改后的节点
            eval_result = evaluation_agent.evaluate_nodes(unique_improved_nodes)

            # 合并
            qualified_nodes.extend(eval_result.qualified_nodes)
            unqualified_nodes = eval_result.unqualified_nodes

            self.logger.info(f"新增 {len(eval_result.qualified_nodes)} 个合格节点")

            iteration += 1

        if iteration > max_iterations and unqualified_nodes:
            self.logger.warning(
                f"达到最大迭代次数，仍有 {len(unqualified_nodes)} 个不合格节点: "
                f"{[n.name for n in unqualified_nodes]} - 这些节点将打标后保留"
            )
            tagged_nodes = self._tag_unqualified_nodes(unqualified_nodes, max_iterations)
            qualified_nodes.extend(tagged_nodes)
            unqualified_nodes = []

        # 添加最终统计日志
        self.logger.info(f"节点迭代完成，共 {len(qualified_nodes)} 个合格节点")
        if unqualified_nodes:
            self.logger.info(f"已过滤 {len(unqualified_nodes)} 个不合格节点")

        return qualified_nodes

    def improve_relations(
        self,
        relations: List[Relation],
        existing_nodes: List[Node],
        generation_agent: GenerationAgent,
        evaluation_agent: EvaluationAgent,
        max_iterations: int
    ) -> List[Relation]:
        """
        迭代改进关系

        新流程：
        1. EvaluationAgent评估关系并生成修改建议（包含example_fix）
        2. 从evaluation_result中提取修改后的关系
        3. 合并合格关系和修改后的关系
        4. 重复直到没有不合格关系或达到最大迭代次数

        Args:
            relations: 初始关系列表
            existing_nodes: 已有节点列表
            generation_agent: 生成智能体（用于重新提取，如果需要）
            evaluation_agent: 评估智能体（评估+修改）
            max_iterations: 最大迭代次数

        Returns:
            改进后的合格关系列表
        """
        if not relations:
            return []

        # 初始化评估智能体
        evaluation_agent.initialize()

        # 评估关系（评估+修改建议）
        eval_result = evaluation_agent.evaluate_relations(relations)

        qualified_relations = eval_result.qualified_relations
        unqualified_relations = eval_result.unqualified_relations

        self.logger.info(f"初始评估: {len(qualified_relations)} 合格, {len(unqualified_relations)} 不合格")

        # 迭代改进
        iteration = 1
        while iteration <= max_iterations and unqualified_relations:
            self.logger.info(f"迭代 {iteration}/{max_iterations}: 改进 {len(unqualified_relations)} 条关系...")

            # 从评估结果中提取修改后的关系
            improved_relations = self._extract_improved_relations_from_evaluation(
                eval_result.feedback.get("rel_feedback", {})
            )

            # 验证节点存在性
            if existing_nodes and improved_relations:
                improved_relations = self._validate_relation_nodes(
                    improved_relations, existing_nodes
                )

            if not improved_relations:
                self.logger.warning("评估结果中没有修改建议，停止迭代")
                break

            # 去重
            def get_relation_key(r):
                return (r.object_a, r.object_b)

            qualified_keys = {get_relation_key(r) for r in qualified_relations}
            unique_improved_relations = [r for r in improved_relations if get_relation_key(r) not in qualified_keys]

            # 重新评估修改后的关系
            eval_result = evaluation_agent.evaluate_relations(unique_improved_relations)

            # 合并
            qualified_relations.extend(eval_result.qualified_relations)
            unqualified_relations = eval_result.unqualified_relations

            self.logger.info(f"新增 {len(eval_result.qualified_relations)} 条合格关系")

            iteration += 1

        if iteration > max_iterations and unqualified_relations:
            self.logger.warning(
                f"达到最大迭代次数，仍有 {len(unqualified_relations)} 条不合格关系: "
                f"{[(r.object_a, r.object_b) for r in unqualified_relations]} - 这些关系将打标后保留"
            )
            tagged_relations = self._tag_unqualified_relations(unqualified_relations, max_iterations)
            qualified_relations.extend(tagged_relations)
            unqualified_relations = []

        # 添加最终统计日志
        self.logger.info(f"关系迭代完成，共 {len(qualified_relations)} 条合格关系")
        if unqualified_relations:
            self.logger.info(f"已过滤 {len(unqualified_relations)} 条不合格关系")

        return qualified_relations

    def _extract_improved_nodes_from_evaluation(self, node_feedback: dict) -> List[Node]:
        """
        从评估反馈中提取修改后的节点

        Args:
            node_feedback: 节点评估反馈

        Returns:
            修改后的节点列表
        """
        improved_nodes = []
        evaluation_results = node_feedback.get("evaluation_results", [])

        for result in evaluation_results:
            # 检查是否有修改建议
            example_fix = result.get("example_fix")
            if example_fix and example_fix.get("after"):
                # 提取修改后的节点
                after = example_fix["after"]
                if isinstance(after, (list, tuple)) and len(after) == 2:
                    try:
                        node = Node.from_tuple(after)
                        improved_nodes.append(node)
                    except Exception as e:
                        self.logger.warning(f"解析修改后的节点失败: {e}")

        self.logger.info(f"从评估结果中提取了 {len(improved_nodes)} 个修改后的节点")
        return improved_nodes

    def _extract_improved_relations_from_evaluation(self, rel_feedback: dict) -> List[Relation]:
        """
        从评估反馈中提取修改后的关系

        Args:
            rel_feedback: 关系评估反馈

        Returns:
            修改后的关系列表
        """
        improved_relations = []
        evaluation_results = rel_feedback.get("evaluation_results", [])

        for result in evaluation_results:
            # 检查是否有修改建议
            example_fix = result.get("example_fix")
            if example_fix and example_fix.get("after"):
                # 提取修改后的关系
                after = example_fix["after"]
                if isinstance(after, (list, tuple)) and len(after) == 3:
                    try:
                        relation = Relation.from_tuple(after)
                        improved_relations.append(relation)
                    except Exception as e:
                        self.logger.warning(f"解析修改后的关系失败: {e}")

        self.logger.info(f"从评估结果中提取了 {len(improved_relations)} 条修改后的关系")
        return improved_relations

    def _validate_relation_nodes(
        self,
        relations: List[Relation],
        existing_nodes: List[Node]
    ) -> List[Relation]:
        """
        验证关系节点存在性

        Args:
            relations: 关系列表
            existing_nodes: 已有节点列表

        Returns:
            过滤后的关系列表（只包含节点存在的关系）
        """
        node_names = {n.name for n in existing_nodes}
        valid_relations = [
            r for r in relations
            if r.object_a in node_names and r.object_b in node_names
        ]

        filtered_count = len(relations) - len(valid_relations)
        if filtered_count > 0:
            self.logger.warning(
                f"过滤了 {filtered_count} 条关系（节点不存在于列表中）"
            )

        return valid_relations

    def _tag_unqualified_nodes(self, nodes: List[Node], rounds: int) -> List[Node]:
        """为达到迭代上限仍不合格的节点添加独特标记。"""
        tagged = []
        for node in nodes:
            metadata = dict(node.metadata or {})
            metadata[self.UNQUALIFIED_ROUND3_MARKER] = {
                "enabled": True,
                "rounds": rounds
            }
            tagged.append(
                Node(
                    name=node.name,
                    desc=node.desc,
                    level=node.level,
                    color=node.color,
                    metadata=metadata
                )
            )
        return tagged

    def _tag_unqualified_relations(self, relations: List[Relation], rounds: int) -> List[Relation]:
        """为达到迭代上限仍不合格的关系添加独特标记。"""
        tagged = []
        for relation in relations:
            metadata = dict(relation.metadata or {})
            metadata[self.UNQUALIFIED_ROUND3_MARKER] = {
                "enabled": True,
                "rounds": rounds
            }
            tagged.append(
                Relation(
                    object_a=relation.object_a,
                    object_b=relation.object_b,
                    relation_type=relation.relation_type,
                    explanation=relation.explanation,
                    color=relation.color,
                    metadata=metadata
                )
            )
        return tagged
