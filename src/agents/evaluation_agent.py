# agents/evaluation_agent.py
"""
评估智能体 - 评估提取质量，提供改进反馈
"""

from typing import List, Dict
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_agent import BaseAgent
from src.core.result_types import Node, Relation, EvaluationResult
from src.utils.json_parser import JSONParser


class EvaluationAgent(BaseAgent):
    """评估智能体"""

    def initialize(self):
        """初始化评估智能体"""
        from src.config.prompts import CHECKER_NODE_SYSTEM_PROMPT
        self.set_system_prompt(CHECKER_NODE_SYSTEM_PROMPT)

    def execute(self, nodes: List[Node] = None, relations: List[Relation] = None) -> EvaluationResult:
        """
        执行评估任务

        Args:
            nodes: 节点列表
            relations: 关系列表

        Returns:
            评估结果
        """
        # 评估节点
        node_result = self.evaluate_nodes(nodes) if nodes else None

        # 评估关系
        relation_result = self.evaluate_relations(relations) if relations else None

        # 合并结果
        if node_result and relation_result:
            return EvaluationResult(
                qualified_nodes=node_result.qualified_nodes,
                unqualified_nodes=node_result.unqualified_nodes,
                qualified_relations=relation_result.qualified_relations,
                unqualified_relations=relation_result.unqualified_relations,
                feedback={
                    "node_feedback": node_result.feedback,
                    "rel_feedback": relation_result.feedback
                },
                stats={
                    **node_result.stats,
                    **relation_result.stats
                }
            )
        elif node_result:
            return node_result
        elif relation_result:
            return relation_result
        else:
            return EvaluationResult()

    def evaluate_nodes(self, nodes: List[Node]) -> EvaluationResult:
        """
        评估节点质量

        Args:
            nodes: 节点列表

        Returns:
            评估结果
        """
        self.logger.info(f"开始评估 {len(nodes)} 个节点...")

        # 导入提示词
        from src.config.prompts import CHECKER_NODE_USER_TEMPLATE

        if not nodes:
            return EvaluationResult(
                qualified_nodes=[],
                unqualified_nodes=[],
                stats={"total_nodes": 0}
            )

        # 构造评估消息
        nodes_str = JSONParser.to_json_string([n.to_dict() for n in nodes[:100]])

        user_message = CHECKER_NODE_USER_TEMPLATE.format(
            node_count=len(nodes),
            nodes=nodes_str
        )

        self.conversation_manager.add_user_message(user_message)

        # 调用API（启用JSON模式）
        response = self._call_api(json_mode=True)
        self.conversation_manager.add_assistant_message(response)

        # 解析评估结果
        result = self._parse_evaluation_response(response)
        parse_error = result.get("_parse_error", False)

        if parse_error:
            self.logger.warning("节点评估解析失败，回退为保留全部生成节点")
            feedback = {
                "node_feedback": result,
                "stats": {
                    "total_nodes": len(nodes),
                    "qualified_nodes": len(nodes),
                    "unqualified_nodes": 0
                }
            }
            return EvaluationResult(
                qualified_nodes=nodes,
                unqualified_nodes=[],
                feedback=feedback,
                stats=feedback["stats"]
            )

        # 分离合格和不合格节点
        qualified_nodes, unqualified_nodes = self._separate_nodes(nodes, result)

        # 构建反馈
        feedback = {
            "node_feedback": result,
            "stats": {
                "total_nodes": len(nodes),
                "qualified_nodes": len(qualified_nodes),
                "unqualified_nodes": len(unqualified_nodes)
            }
        }

        self.logger.info(f"节点评估完成: {len(qualified_nodes)} 合格, {len(unqualified_nodes)} 不合格")
        if unqualified_nodes:
            self.logger.debug(f"不合格节点: {[n.name for n in unqualified_nodes]}")

        return EvaluationResult(
            qualified_nodes=qualified_nodes,
            unqualified_nodes=unqualified_nodes,
            feedback=feedback,
            stats=feedback["stats"]
        )

    def evaluate_relations(self, relations: List[Relation]) -> EvaluationResult:
        """
        评估关系质量

        Args:
            relations: 关系列表

        Returns:
            评估结果
        """
        self.logger.info(f"开始评估 {len(relations)} 条关系...")

        # 导入提示词
        from src.config.prompts import CHECKER_RELATION_SYSTEM_PROMPT, CHECKER_RELATION_USER_TEMPLATE

        # 切换到关系评估的系统提示
        self.update_system_prompt(CHECKER_RELATION_SYSTEM_PROMPT)

        if not relations:
            return EvaluationResult(
                qualified_relations=[],
                unqualified_relations=[],
                stats={"total_relations": 0}
            )

        # 构造评估消息
        relations_str = JSONParser.to_json_string([r.to_dict() for r in relations[:100]])

        user_message = CHECKER_RELATION_USER_TEMPLATE.format(
            relation_count=len(relations),
            relations=relations_str,
            node_count=0,
            nodes="（节点信息未提供）"
        )

        self.conversation_manager.add_user_message(user_message)

        # 调用API（启用JSON模式）
        response = self._call_api(json_mode=True)
        self.conversation_manager.add_assistant_message(response)

        # 解析评估结果
        result = self._parse_evaluation_response(response)
        parse_error = result.get("_parse_error", False)

        if parse_error:
            self.logger.warning("关系评估解析失败，回退为保留全部生成关系")
            feedback = {
                "rel_feedback": result,
                "stats": {
                    "total_relations": len(relations),
                    "qualified_relations": len(relations),
                    "unqualified_relations": 0
                }
            }
            return EvaluationResult(
                qualified_relations=relations,
                unqualified_relations=[],
                feedback=feedback,
                stats=feedback["stats"]
            )

        # 分离合格和不合格关系
        qualified_relations, unqualified_relations = self._separate_relations(relations, result)

        # 构建反馈
        feedback = {
            "rel_feedback": result,
            "stats": {
                "total_relations": len(relations),
                "qualified_relations": len(qualified_relations),
                "unqualified_relations": len(unqualified_relations)
            }
        }

        self.logger.info(f"关系评估完成: {len(qualified_relations)} 合格, {len(unqualified_relations)} 不合格")
        if unqualified_relations:
            self.logger.debug(
                f"不合格关系: {[(r.object_a, r.object_b) for r in unqualified_relations]}"
            )

        return EvaluationResult(
            qualified_relations=qualified_relations,
            unqualified_relations=unqualified_relations,
            feedback=feedback,
            stats=feedback["stats"]
        )

    def _parse_evaluation_response(self, response: str) -> Dict:
        """解析评估响应"""
        try:
            result = JSONParser.parse(response, repair=True)

            if "evaluation_results" not in result:
                result["evaluation_results"] = []
            result["_parse_error"] = False

            return result

        except Exception as e:
            self.logger.error(f"解析评估结果失败: {e}")
            return {"evaluation_results": [], "_parse_error": True}

    def _separate_nodes(self, nodes: List[Node], result: Dict) -> tuple:
        """分离合格和不合格节点"""
        evaluation_results = result.get("evaluation_results", [])

        # 构建评估映射
        eval_map = {}
        for eval_result in evaluation_results:
            item_name = eval_result.get("item", "")
            eval_map[item_name] = eval_result

        # 分离节点
        qualified_nodes = []
        unqualified_nodes = []

        for node in nodes:
            eval_result = eval_map.get(node.name, {})
            issues = eval_result.get("issues", [])

            if len(issues) == 0:
                qualified_nodes.append(node)
            else:
                unqualified_nodes.append(node)

        return qualified_nodes, unqualified_nodes

    def _separate_relations(self, relations: List[Relation], result: Dict) -> tuple:
        """分离合格和不合格关系"""
        evaluation_results = result.get("evaluation_results", [])

        # 构建评估映射
        eval_map = {}
        for eval_result in evaluation_results:
            item_str = eval_result.get("item", "")
            if " -> " in item_str:
                parts = item_str.split(" -> ")
                if len(parts) == 2:
                    obj_a = parts[0].strip()
                    obj_b = parts[1].split("(")[0].strip()
                    key = (obj_a, obj_b)
                    eval_map[key] = eval_result

        # 分离关系
        qualified_relations = []
        unqualified_relations = []

        for relation in relations:
            key = (relation.object_a, relation.object_b)
            eval_result = eval_map.get(key, {})

            # 检查逻辑检查
            logic_check = eval_result.get("logic_check", {})
            mathematically_valid = logic_check.get("mathematically_valid", True)
            direction_correct = logic_check.get("direction_correct", True)
            relation_type_appropriate = logic_check.get("relation_type_appropriate", True)

            # 检查问题
            issues = eval_result.get("issues", [])

            # 判断是否通过
            logic_check_passed = mathematically_valid and direction_correct and relation_type_appropriate
            is_passed = logic_check_passed and len(issues) == 0

            if is_passed:
                qualified_relations.append(relation)
            else:
                unqualified_relations.append(relation)

        return qualified_relations, unqualified_relations
