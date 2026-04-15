# pipeline/task_executor.py
"""
任务执行器 - 执行单个任务，管理迭代改进流程
"""

from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents import GenerationAgent, EvaluationAgent
from src.core.result_types import Node, Relation, TaskResult, TaskType
from src.infrastructure import Logger
from .iteration_manager import IterationManager


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        generation_agent: GenerationAgent,
        evaluation_agent: EvaluationAgent,
        material_text: str = None
    ):
        """
        初始化任务执行器

        Args:
            generation_agent: 生成智能体（模板，不会被直接使用）
            evaluation_agent: 评估智能体（模板，不会被直接使用）
            material_text: 教材文本
        """
        self.generation_agent_template = generation_agent
        self.evaluation_agent_template = evaluation_agent
        self.material_text = material_text
        self.iteration_manager = IterationManager()
        self.logger = Logger("TaskExecutor")

    def _create_generation_agent(self) -> GenerationAgent:
        """创建新的生成智能体实例"""
        return GenerationAgent(
            api_client=self.generation_agent_template.api_client,
            logger=Logger("GenerationAgent")
        )

    def _create_evaluation_agent(self) -> EvaluationAgent:
        """创建新的评估智能体实例"""
        return EvaluationAgent(
            api_client=self.evaluation_agent_template.api_client,
            logger=Logger("EvaluationAgent")
        )

    def execute(
        self,
        task: Dict,
        existing_nodes: List[Node] = None,
        max_iterations: int = 3
    ) -> TaskResult:
        """
        执行单个任务

        Args:
            task: 任务定义
            existing_nodes: 已有节点（用于关系提取）
            max_iterations: 最大迭代次数

        Returns:
            任务执行结果
        """
        task_id = task.get("task_id")
        task_type_str = task.get("task_type")

        # 转换任务类型
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.EXTRACT_BOTH

        self.logger.info(f"开始执行任务: {task_id} ({task_type_str})")

        try:
            # 根据任务类型执行不同的提取逻辑
            if task_type == TaskType.EXTRACT_NODES:
                nodes, relations = self._execute_extract_nodes(task, max_iterations)
            elif task_type == TaskType.EXTRACT_RELATIONS:
                nodes, relations = self._execute_extract_relations(task, existing_nodes, max_iterations)
            elif task_type == TaskType.EXTRACT_BOTH:
                nodes, relations = self._execute_extract_both(task, max_iterations)
            elif task_type == TaskType.EXTRACT_CROSS_SECTION:
                nodes, relations = self._execute_extract_cross_section(task, existing_nodes, max_iterations)
            else:
                nodes, relations = [], []

            self.logger.info(f"任务完成: {task_id}, 节点: {len(nodes)}, 关系: {len(relations)}")

            return TaskResult(
                task_id=task_id,
                task_type=task_type,
                status="completed",
                nodes=nodes,
                relations=relations,
                iterations=max_iterations
            )

        except Exception as e:
            self.logger.error(f"任务执行失败: {task_id}, 错误: {e}")
            import traceback
            traceback.print_exc()

            return TaskResult(
                task_id=task_id,
                task_type=task_type,
                status="failed",
                nodes=[],
                relations=[],
                iterations=0,
                error=str(e)
            )

    def execute_batch(
        self,
        tasks: List[Dict],
        completed_tasks: Dict[str, TaskResult],
        max_iterations: int,
        max_workers: int = 4
    ) -> Dict[str, TaskResult]:
        """
        批量执行任务（支持并发）

        Args:
            tasks: 任务列表
            completed_tasks: 已完成任务
            max_iterations: 最大迭代次数
            max_workers: 最大并发数

        Returns:
            {task_id: TaskResult}
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for task in tasks:
                task_id = task.get("task_id")

                # 收集依赖任务的节点
                existing_nodes = []
                for dep_id in task.get("dependencies", []):
                    if dep_id in completed_tasks:
                        existing_nodes.extend(completed_tasks[dep_id].nodes)

                # 提交任务
                future = executor.submit(
                    self.execute,
                    task,
                    existing_nodes if existing_nodes else None,
                    max_iterations
                )
                futures[future] = task_id

            # 收集结果
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    result = future.result()
                    results[task_id] = result
                except Exception as e:
                    self.logger.error(f"任务 {task_id} 执行失败: {e}")
                    # 任务失败，记录错误
                    results[task_id] = TaskResult(
                        task_id=task_id,
                        task_type=TaskType.EXTRACT_BOTH,
                        status="failed",
                        nodes=[],
                        relations=[],
                        iterations=0,
                        error=str(e)
                    )

        return results

    def _execute_extract_nodes(
        self,
        task: Dict,
        max_iterations: int
    ) -> Tuple[List[Node], List[Relation]]:
        """执行节点提取任务"""
        # 为此任务创建新的 agent 实例
        generation_agent = self._create_generation_agent()
        evaluation_agent = self._create_evaluation_agent()

        # 初始化生成智能体
        generation_agent.initialize()

        # 提取节点
        nodes = generation_agent.extract_nodes(task, self.material_text)

        # 迭代改进
        nodes = self.iteration_manager.improve_nodes(
            nodes,
            generation_agent,
            evaluation_agent,
            max_iterations
        )

        return nodes, []

    def _execute_extract_relations(
        self,
        task: Dict,
        existing_nodes: List[Node],
        max_iterations: int
    ) -> Tuple[List[Node], List[Relation]]:
        """执行关系提取任务"""
        # 为此任务创建新的 agent 实例
        generation_agent = self._create_generation_agent()
        evaluation_agent = self._create_evaluation_agent()

        # 初始化生成智能体
        generation_agent.initialize()

        # 提取关系
        relations = generation_agent.extract_relations(task, existing_nodes, self.material_text)

        # 迭代改进
        relations = self.iteration_manager.improve_relations(
            relations,
            existing_nodes,
            generation_agent,
            evaluation_agent,
            max_iterations
        )

        return [], relations

    def _execute_extract_both(
        self,
        task: Dict,
        max_iterations: int
    ) -> Tuple[List[Node], List[Relation]]:
        """执行节点和关系提取任务"""
        # 为节点提取创建新的 agent 实例
        generation_agent_nodes = self._create_generation_agent()
        evaluation_agent_nodes = self._create_evaluation_agent()

        # 初始化生成智能体
        generation_agent_nodes.initialize()

        # 提取节点
        nodes = generation_agent_nodes.extract_nodes(task, self.material_text)

        # 迭代改进节点
        nodes = self.iteration_manager.improve_nodes(
            nodes,
            generation_agent_nodes,
            evaluation_agent_nodes,
            max_iterations
        )

        # 为关系提取创建新的 agent 实例（独立的对话上下文）
        generation_agent_relations = self._create_generation_agent()
        evaluation_agent_relations = self._create_evaluation_agent()

        # 提取关系
        relations = generation_agent_relations.extract_relations(task, nodes, self.material_text)

        # 迭代改进关系
        relations = self.iteration_manager.improve_relations(
            relations,
            nodes,
            generation_agent_relations,
            evaluation_agent_relations,
            max_iterations
        )

        return nodes, relations

    def _execute_extract_cross_section(
        self,
        task: Dict,
        existing_nodes: List[Node],
        max_iterations: int
    ) -> Tuple[List[Node], List[Relation]]:
        """执行跨章节关系提取任务"""
        # 为此任务创建新的 agent 实例
        generation_agent = self._create_generation_agent()
        evaluation_agent = self._create_evaluation_agent()

        # 初始化生成智能体
        generation_agent.initialize()

        # 提取关系
        relations = generation_agent.extract_relations(task, existing_nodes, self.material_text)

        # 迭代改进
        relations = self.iteration_manager.improve_relations(
            relations,
            existing_nodes,
            generation_agent,
            evaluation_agent,
            max_iterations
        )

        return [], relations
