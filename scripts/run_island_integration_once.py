import datetime
import json
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.config import get_api_endpoint, get_api_key
from src.agents.island_integration_agent import IslandIntegrationAgent
from src.core.result_types import Node, Relation
from src.infrastructure.api_client import APIClient


def main():
    base = "material/数学分析I"
    nodes_path = f"{base}/数学分析I_nodes.json"
    relations_path = f"{base}/数学分析I_relations.json"

    nodes_raw = json.load(open(nodes_path, "r", encoding="utf-8"))
    relations_raw = json.load(open(relations_path, "r", encoding="utf-8"))

    nodes = [
        Node.from_tuple(item)
        for item in nodes_raw
        if isinstance(item, (list, tuple)) and len(item) == 2
    ]
    relations = [
        Relation.from_tuple(item)
        for item in relations_raw
        if isinstance(item, (list, tuple)) and len(item) == 3
    ]

    api_key = get_api_key()
    api_endpoint = get_api_endpoint()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置")

    agent = IslandIntegrationAgent(APIClient(api_key, api_endpoint))
    agent.initialize()

    components = agent._find_components(nodes, relations)
    print("COMPONENTS_BEFORE", len(components))

    if len(components) <= 1:
        print("图谱已连通，无需处理")
        return

    components.sort(key=lambda c: len(c), reverse=True)
    component_pairs = agent._build_component_pairs(components)
    selected_pairs = agent._sample_pairs(component_pairs, limit=80, seed=42)
    print("PAIR_TOTAL", len(component_pairs))
    print("PAIR_SELECTED", len(selected_pairs))

    # 关系建立 + evaluation 检查（复用已有 prompt）
    filtered = agent.execute(
        nodes=nodes,
        relations=relations,
        max_workers=4,
        random_pair_limit=80,
        random_seed=42
    )
    merged = relations + filtered
    merged = agent._filter_new_relations(merged, [])

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{base}/数学分析I_relations.backup_{ts}.json"
    json.dump(relations_raw, open(backup_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    merged_out = [r.to_tuple() for r in merged]
    json.dump(merged_out, open(relations_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    components_after = agent._find_components(nodes, merged)
    print("ADDED_RELATIONS", len(filtered))
    print("TOTAL_RELATIONS_AFTER", len(merged))
    print("COMPONENTS_AFTER", len(components_after))
    print("BACKUP", backup_path)


if __name__ == "__main__":
    main()
