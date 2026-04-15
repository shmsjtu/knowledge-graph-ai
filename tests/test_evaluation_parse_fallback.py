import unittest

from src.agents.evaluation_agent import EvaluationAgent
from src.core.result_types import Node, Relation


class BrokenAPIClient:
    def call(self, *args, **kwargs):
        # 故意返回不可解析内容，触发评估解析失败分支
        return "this is not json"


class TestEvaluationParseFallback(unittest.TestCase):
    def setUp(self):
        self.agent = EvaluationAgent(api_client=BrokenAPIClient())
        self.agent.initialize()

    def test_nodes_fallback_keeps_all_generated_content(self):
        nodes = [
            Node(name="A", desc="desc A", level=1),
            Node(name="B", desc="desc B", level=1),
        ]
        result = self.agent.evaluate_nodes(nodes)

        self.assertEqual(len(result.qualified_nodes), len(nodes))
        self.assertEqual(len(result.unqualified_nodes), 0)
        self.assertTrue(result.feedback.get("node_feedback", {}).get("_parse_error", False))

    def test_relations_fallback_keeps_all_generated_content(self):
        relations = [
            Relation(object_a="A", object_b="B", relation_type="推导"),
            Relation(object_a="B", object_b="C", relation_type="依赖"),
        ]
        result = self.agent.evaluate_relations(relations)

        self.assertEqual(len(result.qualified_relations), len(relations))
        self.assertEqual(len(result.unqualified_relations), 0)
        self.assertTrue(result.feedback.get("rel_feedback", {}).get("_parse_error", False))


if __name__ == "__main__":
    unittest.main()
