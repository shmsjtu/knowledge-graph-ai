import unittest

from scripts.config import get_api_endpoint, get_api_key
from src.agents.evaluation_agent import EvaluationAgent
from src.core.result_types import Node, Relation
from src.infrastructure.api_client import APIClient


class TestEvaluationAgentWithRealAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api_key = get_api_key()
        api_endpoint = get_api_endpoint()
        assert api_key, "缺少 DEEPSEEK_API_KEY，无法执行真实 API 测试"

        cls.agent = EvaluationAgent(
            api_client=APIClient(api_key=api_key, api_endpoint=api_endpoint)
        )
        cls.agent.initialize()

        cls.sample_nodes = [
            Node(name="可列集", desc="可与自然数建立一一对应", level=1),
            Node(name="有理数集Q", desc="有理数构成的集合", level=1),
            Node(name="实数集R", desc="实数构成的集合", level=1),
        ]
        cls.sample_relations = [
            Relation(
                object_a="有理数集Q",
                object_b="可列集",
                relation_type="属于",
                explanation="定理指出 Q 是可列集",
            ),
            Relation(
                object_a="实数集R",
                object_b="不可列集",
                relation_type="属于",
                explanation="定理指出 R 不可列",
            ),
        ]

    def test_evaluate_nodes_real_api(self):
        result = self.agent.evaluate_nodes(self.sample_nodes)
        self.assertEqual(result.stats.get("total_nodes"), len(self.sample_nodes))
        total = len(result.qualified_nodes) + len(result.unqualified_nodes)
        self.assertEqual(total, len(self.sample_nodes))

    def test_evaluate_relations_real_api(self):
        result = self.agent.evaluate_relations(self.sample_relations)
        self.assertEqual(result.stats.get("total_relations"), len(self.sample_relations))
        total = len(result.qualified_relations) + len(result.unqualified_relations)
        self.assertEqual(total, len(self.sample_relations))


if __name__ == "__main__":
    unittest.main()
