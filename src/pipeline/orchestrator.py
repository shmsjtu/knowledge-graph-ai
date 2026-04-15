# pipeline/orchestrator.py
"""
管线编排器 - 协调三大智能体，管理整体流程
"""

from typing import List, Tuple
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents import TwoStepPlanningAgent, GenerationAgent, EvaluationAgent, IslandIntegrationAgent
from src.infrastructure import APIClient, Logger
from src.core.result_types import Node, Relation, TaskResult
from .task_executor import TaskExecutor
from .dependency_resolver import DependencyResolver


class PipelineOrchestrator:
    """管线编排器 - 使用两步规划"""

    def __init__(
        self,
        api_key: str,
        api_endpoint: str,
        material_text: str = None
    ):
        """
        初始化管线编排器

        Args:
            api_key: API密钥
            api_endpoint: API端点
            material_text: 教材文本
        """
        # 初始化基础设施
        self.api_client = APIClient(api_key, api_endpoint)
        self.logger = Logger("PipelineOrchestrator")

        # 初始化智能体（使用新的两步规划智能体）
        self.planning_agent = TwoStepPlanningAgent(self.api_client)
        self.generation_agent = GenerationAgent(self.api_client)
        self.evaluation_agent = EvaluationAgent(self.api_client)
        self.island_integration_agent = IslandIntegrationAgent(self.api_client)

        # 初始化辅助组件
        self.task_executor = TaskExecutor(
            self.generation_agent,
            self.evaluation_agent,
            material_text
        )
        self.dependency_resolver = DependencyResolver()

        # 教材文本
        self.material_text = material_text

    def run(
        self,
        material_toc: str,
        section_lengths: dict = None,
        max_iterations: int = 3,
        max_workers: int = 4
    ) -> Tuple[List[Node], List[Relation]]:
        """
        运行完整管线

        Args:
            material_toc: 教材目录
            section_lengths: 章节长度信息（可选）
            max_iterations: 最大迭代次数
            max_workers: 最大并发数

        Returns:
            (节点列表, 关系列表)
        """
        self.logger.info("=" * 80)
        self.logger.info("开始知识图谱提取")
        self.logger.info("=" * 80)

        try:
            # 1. Planning阶段（使用两步规划）
            self.logger.info("\n[Planning] 分析教材目录...")
            plan = self._run_planning(material_toc, section_lengths, max_workers)

            # 2. Generation & Evaluation阶段
            self.logger.info("\n[Generation & Evaluation] 执行任务...")
            nodes, relations = self._run_tasks(plan, max_iterations, max_workers)

            # 3. 孤岛整合阶段
            self.logger.info("\n[Island Integration] 整合孤岛...")
            nodes, relations = self._run_island_integration(nodes, relations, max_workers)

            # 完成
            self.logger.info("\n" + "=" * 80)
            self.logger.info("知识图谱提取完成")
            self.logger.info(f"最终结果: {len(nodes)} 个节点, {len(relations)} 条关系")
            self.logger.info("=" * 80)

            return nodes, relations

        except KeyboardInterrupt:
            self.logger.warning("\n用户中断")
            raise

        except Exception as e:
            self.logger.error(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _run_planning(self, material_toc: str, section_lengths: dict = None, max_workers: int = 4) -> dict:
        """运行规划阶段（使用两步规划）"""
        self.planning_agent.initialize()
        plan = self.planning_agent.two_step_planning(material_toc, section_lengths, max_workers)

        subtasks = plan.get("subtasks", [])
        self.logger.info(f"[Planning] 完成，生成 {len(subtasks)} 个任务")

        # 显示任务信息
        section_groups = plan.get("section_groups", [])
        if section_groups:
            self.logger.info(f"\n章节分组（共 {len(section_groups)} 组）:")
            for group in section_groups[:10]:  # 只显示前10个
                group_id = group.get("group_id", "?")
                sections = group.get("sections", [])
                reasoning = group.get("reasoning", "")
                self.logger.info(f"  {group_id}: {', '.join(sections)}")
                if reasoning:
                    self.logger.info(f"    原因: {reasoning}")

            if len(section_groups) > 10:
                self.logger.info(f"  ... 还有 {len(section_groups) - 10} 个章节组")

        # 显示任务依赖关系
        cross_relations = plan.get("cross_section_relations", [])
        if cross_relations:
            self.logger.info(f"\n跨章节关系任务（共 {len(cross_relations)} 个）")

        return plan

    def _run_tasks(
        self,
        plan: dict,
        max_iterations: int,
        max_workers: int
    ) -> Tuple[List[Node], List[Relation]]:
        """运行任务执行阶段"""
        subtasks = plan.get("subtasks", [])

        # 解析依赖关系
        execution_batches = self.dependency_resolver.resolve(subtasks)

        # 执行任务
        all_nodes = []
        all_relations = []
        completed_tasks = {}

        for batch_idx, task_batch in enumerate(execution_batches, 1):
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"执行批次 {batch_idx}/{len(execution_batches)}")
            self.logger.info(f"{'='*80}")

            # 执行一批任务
            results = self.task_executor.execute_batch(
                task_batch,
                completed_tasks,
                max_iterations,
                max_workers
            )

            # 收集结果
            for task_id, result in results.items():
                completed_tasks[task_id] = result
                all_nodes.extend(result.nodes)
                all_relations.extend(result.relations)

                # 显示结果
                self.logger.info(
                    f"  任务 {task_id}: {len(result.nodes)} 节点, {len(result.relations)} 关系"
                )

        # 去重
        all_nodes = self._deduplicate_nodes(all_nodes)
        all_relations = self._deduplicate_relations(all_relations)

        self.logger.info(f"\n去重后: {len(all_nodes)} 个节点, {len(all_relations)} 条关系")

        return all_nodes, all_relations

    def _run_island_integration(
        self,
        nodes: List[Node],
        relations: List[Relation],
        max_workers: int
    ) -> Tuple[List[Node], List[Relation]]:
        """运行孤岛整合阶段"""
        self.island_integration_agent.initialize()
        bridge_relations = self.island_integration_agent.execute(
            nodes=nodes,
            relations=relations,
            max_workers=max_workers
        )
        if not bridge_relations:
            self.logger.info("[Island Integration] 无新增跨孤岛关系")
            return nodes, relations

        merged_relations = relations + bridge_relations
        merged_relations = self._deduplicate_relations(merged_relations)
        self.logger.info(
            f"[Island Integration] 新增 {len(bridge_relations)} 条关系，整合后共 {len(merged_relations)} 条关系"
        )
        return nodes, merged_relations

    def _deduplicate_nodes(self, nodes: List[Node]) -> List[Node]:
        """节点去重"""
        seen_names = set()
        unique_nodes = []
        duplicate_count = 0

        for node in nodes:
            if node.name in seen_names:
                duplicate_count += 1
                continue

            seen_names.add(node.name)
            unique_nodes.append(node)

        if duplicate_count > 0:
            self.logger.info(f"节点去重: 删除了 {duplicate_count} 个重复节点")

        return unique_nodes

    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """关系去重"""
        seen_keys = set()
        unique_relations = []
        duplicate_count = 0

        for relation in relations:
            key = (relation.object_a, relation.object_b)

            if key in seen_keys:
                duplicate_count += 1
                continue

            seen_keys.add(key)
            unique_relations.append(relation)

        if duplicate_count > 0:
            self.logger.info(f"关系去重: 删除了 {duplicate_count} 条重复关系")

        return unique_relations
