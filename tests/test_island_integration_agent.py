import unittest

from src.agents.island_integration_agent import IslandIntegrationAgent
from src.core.result_types import Node, Relation


class FakeAPIClient:
    def call(self, messages, model=None, max_tokens=None, temperature=None, json_mode=False, **kwargs):
        user_content = messages[-1].get("content", "") if messages else ""
        if "请在以下两个孤岛之间建立联系" in user_content:
            # 建桥调用：固定输出一条跨孤岛关系
            return '[["A", "C", {"rel": "关联", "定理": "A与C在概念上相关", "color": "#888888"}]]'

        # 评估调用：返回空评估结果（默认视为通过）
        return '{"evaluation_results": []}'


class TestIslandIntegrationAgent(unittest.TestCase):
    def setUp(self):
        self.agent = IslandIntegrationAgent(api_client=FakeAPIClient())
        self.agent.initialize()

    def test_find_components_and_bridge(self):
        nodes = [
            Node(name="A", desc=""),
            Node(name="B", desc=""),
            Node(name="C", desc=""),
            Node(name="D", desc=""),
        ]
        # A-B 与 C-D 是两个孤岛
        relations = [
            Relation(object_a="A", object_b="B", relation_type="关联", explanation=""),
            Relation(object_a="C", object_b="D", relation_type="关联", explanation=""),
        ]

        new_relations = self.agent.execute(nodes, relations, max_workers=1)
        self.assertEqual(len(new_relations), 1)
        self.assertEqual(new_relations[0].object_a, "A")
        self.assertEqual(new_relations[0].object_b, "C")

    def test_no_island_no_bridge(self):
        nodes = [Node(name="A", desc=""), Node(name="B", desc="")]
        relations = [Relation(object_a="A", object_b="B", relation_type="关联", explanation="")]
        new_relations = self.agent.execute(nodes, relations, max_workers=1)
        self.assertEqual(len(new_relations), 0)


if __name__ == "__main__":
    unittest.main()
