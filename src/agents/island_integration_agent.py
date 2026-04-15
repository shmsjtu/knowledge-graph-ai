"""
孤岛整合智能体 - 将不连通子图两两送入LLM建立跨孤岛关系
"""

from typing import Dict, List, Set, Tuple
import json
import random
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_agent import BaseAgent
from .evaluation_agent import EvaluationAgent
from src.core.result_types import Node, Relation
from src.utils.json_parser import JSONParser
from src.infrastructure import Logger


class IslandIntegrationAgent(BaseAgent):
    """孤岛整合智能体"""

    def initialize(self):
        from src.config.prompts import ISLAND_BRIDGE_SYSTEM_PROMPT
        self.set_system_prompt(ISLAND_BRIDGE_SYSTEM_PROMPT)

    def execute(
        self,
        nodes: List[Node],
        relations: List[Relation],
        max_workers: int = 4,
        random_pair_limit: int = 80,
        random_seed: int = 42
    ) -> List[Relation]:
        """
        对每个孤岛对建立跨孤岛关系
        """
        if not nodes:
            return []

        components = self._find_components(nodes, relations)
        if len(components) <= 1:
            self.logger.info("图谱已连通，无需孤岛整合")
            return []

        self.logger.info(f"检测到 {len(components)} 个孤岛，开始两两建立联系...")
        component_pairs = self._build_component_pairs(components)
        selected_pairs = self._sample_pairs(component_pairs, random_pair_limit, random_seed)
        self.logger.info(
            f"共 {len(component_pairs)} 个孤岛对，随机选择 {len(selected_pairs)} 个进行建桥"
        )

        pair_bridge_results: List[Tuple[int, List[Relation]]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for idx, (comp_a, comp_b) in enumerate(selected_pairs):
                pair_agent = self._create_pair_agent()
                future = executor.submit(
                    self._bridge_one_pair,
                    pair_agent,
                    comp_a,
                    comp_b,
                    idx + 1
                )
                futures[future] = idx + 1

            for future in as_completed(futures):
                pair_idx = futures[future]
                try:
                    pair_relations = future.result()
                    pair_bridge_results.append((pair_idx, pair_relations))
                    self.logger.info(f"孤岛对 {pair_idx} 生成 {len(pair_relations)} 条关系")
                except Exception as e:
                    self.logger.error(f"孤岛对 {pair_idx} 处理失败: {e}")

        # 每个孤岛对的关系都先交给 evaluation LLM 检查
        all_new_relations: List[Relation] = []
        evaluator = EvaluationAgent(self.api_client, logger=Logger("IslandEvalAgent"))
        for pair_idx, pair_relations in sorted(pair_bridge_results, key=lambda x: x[0]):
            if not pair_relations:
                continue
            evaluator.initialize()
            eval_result = evaluator.evaluate_relations(pair_relations)
            accepted = eval_result.qualified_relations
            all_new_relations.extend(accepted)
            self.logger.info(
                f"孤岛对 {pair_idx} 评估通过 {len(accepted)}/{len(pair_relations)} 条关系"
            )

        filtered = self._filter_new_relations(all_new_relations, relations)
        self.logger.info(f"孤岛整合完成，新增 {len(filtered)} 条跨孤岛关系")
        return filtered

    def _create_pair_agent(self):
        return IslandIntegrationAgent(
            api_client=self.api_client,
            logger=Logger("IslandPairAgent")
        )

    def _find_components(
        self,
        nodes: List[Node],
        relations: List[Relation]
    ) -> List[Set[str]]:
        node_names = {n.name for n in nodes}
        adjacency: Dict[str, Set[str]] = {name: set() for name in node_names}

        for rel in relations:
            a = rel.object_a
            b = rel.object_b
            if a in node_names and b in node_names and a != b:
                adjacency[a].add(b)
                adjacency[b].add(a)

        components: List[Set[str]] = []
        visited: Set[str] = set()
        for start in node_names:
            if start in visited:
                continue
            stack = [start]
            comp = set()
            visited.add(start)
            while stack:
                current = stack.pop()
                comp.add(current)
                for nxt in adjacency[current]:
                    if nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
            components.append(comp)

        # 从大到小排序，提升建桥稳定性
        components.sort(key=lambda c: len(c), reverse=True)
        return components

    def _build_component_pairs(self, components: List[Set[str]]) -> List[Tuple[Set[str], Set[str]]]:
        pairs = []
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                pairs.append((components[i], components[j]))
        return pairs

    def _sample_pairs(
        self,
        pairs: List[Tuple[Set[str], Set[str]]],
        limit: int,
        seed: int
    ) -> List[Tuple[Set[str], Set[str]]]:
        """随机抽取孤岛对。"""
        if not pairs:
            return []
        if limit <= 0 or len(pairs) <= limit:
            return pairs
        rnd = random.Random(seed)
        return rnd.sample(pairs, limit)

    def _bridge_one_pair(
        self,
        pair_agent,
        component_a: Set[str],
        component_b: Set[str],
        pair_idx: int
    ) -> List[Relation]:
        from src.config.prompts import ISLAND_BRIDGE_SYSTEM_PROMPT, ISLAND_BRIDGE_USER_TEMPLATE

        nodes_a = sorted(component_a)
        nodes_b = sorted(component_b)

        pair_agent.initialize()
        pair_agent.update_system_prompt(ISLAND_BRIDGE_SYSTEM_PROMPT)
        user_message = ISLAND_BRIDGE_USER_TEMPLATE.format(
            island_a_nodes=json.dumps(nodes_a, ensure_ascii=False),
            island_b_nodes=json.dumps(nodes_b, ensure_ascii=False)
        )
        pair_agent.conversation_manager.add_user_message(user_message)
        response = pair_agent._call_api(json_mode=True)
        pair_agent.conversation_manager.add_assistant_message(response)

        return self._parse_bridge_relations(response, component_a, component_b)

    def _parse_bridge_relations(
        self,
        response: str,
        component_a: Set[str],
        component_b: Set[str]
    ) -> List[Relation]:
        try:
            data = JSONParser.parse(response, repair=True)
        except Exception as e:
            self.logger.error(f"解析孤岛关系失败: {e}")
            return []

        if isinstance(data, dict):
            items = data.get("bridge_relations", data.get("relations", []))
        else:
            items = data

        if not isinstance(items, list):
            return []

        allowed = component_a | component_b
        parsed: List[Relation] = []
        for item in items:
            relation = self._to_relation(item)
            if not relation:
                continue
            if relation.object_a not in allowed or relation.object_b not in allowed:
                continue
            if relation.object_a == relation.object_b:
                continue

            # 必须是跨孤岛关系
            cross = (
                (relation.object_a in component_a and relation.object_b in component_b) or
                (relation.object_a in component_b and relation.object_b in component_a)
            )
            if cross:
                parsed.append(relation)

        return parsed

    def _to_relation(self, item) -> Relation:
        try:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                return Relation.from_tuple(item)
            if isinstance(item, dict):
                object_a = item.get("object_a") or item.get("a") or ""
                object_b = item.get("object_b") or item.get("b") or ""
                rel_type = item.get("rel") or item.get("relation_type") or item.get("relation") or "关联"
                explanation = item.get("定理") or item.get("explanation") or ""
                color = item.get("color") or "#888888"
                if not object_a or not object_b:
                    return None
                return Relation(
                    object_a=object_a,
                    object_b=object_b,
                    relation_type=rel_type,
                    explanation=explanation,
                    color=color
                )
        except Exception:
            return None
        return None

    def _filter_new_relations(
        self,
        new_relations: List[Relation],
        existing_relations: List[Relation]
    ) -> List[Relation]:
        existing_keys = {(r.object_a, r.object_b) for r in existing_relations}
        unique = []
        seen = set()
        for rel in new_relations:
            key = (rel.object_a, rel.object_b)
            if key in existing_keys or key in seen:
                continue
            seen.add(key)
            unique.append(rel)
        return unique
