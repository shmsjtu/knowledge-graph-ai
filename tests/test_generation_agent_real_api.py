import unittest

from scripts.config import get_api_endpoint, get_api_key, get_material_path
from src.agents.generation_agent import GenerationAgent
from src.core.result_types import Node
from src.infrastructure.api_client import APIClient


def _load_theorem_snippet() -> str:
    with open(get_material_path(), "r", encoding="utf-8") as f:
        text = f.read()

    start = text.find("## 集合及其运算")
    end = text.find("## 映射")
    if start == -1:
        return text[:4000]
    if end == -1 or end <= start:
        return text[start:start + 4000]
    return text[start:end]


class TestGenerationAgentWithRealAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api_key = get_api_key()
        api_endpoint = get_api_endpoint()
        assert api_key, "缺少 DEEPSEEK_API_KEY，无法执行真实 API 测试"

        cls.material_snippet = _load_theorem_snippet()
        cls.agent = GenerationAgent(
            api_client=APIClient(api_key=api_key, api_endpoint=api_endpoint)
        )
        cls.agent.initialize()
        cls.generated_nodes = cls.agent.extract_nodes(
            {"task_id": "gen_nodes_once", "task_type": "extract_nodes", "target_sections": ["all"]},
            cls.material_snippet
        )

    def test_extract_nodes_real_api(self):
        nodes = self.generated_nodes
        self.assertIsInstance(nodes, list)
        for node in nodes[:5]:
            self.assertTrue(hasattr(node, "name"))
            self.assertIsInstance(node.name, str)

    def test_extract_relations_real_api(self):
        nodes = self.generated_nodes
        if not nodes:
            nodes = [
                Node(name="可列集", desc="可与自然数建立一一对应", level=1),
                Node(name="不可列集", desc="不能与自然数建立一一对应", level=1),
                Node(name="实数集", desc="实数的集合", level=1),
            ]

        task = {
            "task_id": "gen_relations_once",
            "task_type": "extract_relations",
            "target_sections": ["all"],
        }
        relations = self.agent.extract_relations(task, nodes, self.material_snippet)
        self.assertIsInstance(relations, list)
        for relation in relations[:5]:
            self.assertTrue(hasattr(relation, "object_a"))
            self.assertTrue(hasattr(relation, "object_b"))
            self.assertIsInstance(relation.object_a, str)
            self.assertIsInstance(relation.object_b, str)


if __name__ == "__main__":
    unittest.main()
