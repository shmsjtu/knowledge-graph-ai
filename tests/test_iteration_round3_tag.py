import unittest

from src.core.result_types import EvaluationResult, Node, Relation
from src.pipeline.iteration_manager import IterationManager


class AlwaysUnqualifiedEvaluationAgent:
    def initialize(self):
        return None

    def evaluate_nodes(self, nodes):
        results = []
        for node in nodes:
            results.append(
                {
                    "item": node.name,
                    "issues": ["desc too short"],
                    "example_fix": {"after": [node.name, {"desc": node.desc, "level": node.level, "color": node.color}]},
                }
            )
        return EvaluationResult(
            qualified_nodes=[],
            unqualified_nodes=nodes,
            feedback={"node_feedback": {"evaluation_results": results}},
            stats={"total_nodes": len(nodes), "qualified_nodes": 0, "unqualified_nodes": len(nodes)},
        )

    def evaluate_relations(self, relations):
        results = []
        for rel in relations:
            results.append(
                {
                    "item": f"{rel.object_a} -> {rel.object_b} ({rel.relation_type})",
                    "issues": ["logic invalid"],
                    "example_fix": {
                        "after": [rel.object_a, rel.object_b, {"rel": rel.relation_type, "定理": rel.explanation, "color": rel.color}]
                    },
                }
            )
        return EvaluationResult(
            qualified_relations=[],
            unqualified_relations=relations,
            feedback={"rel_feedback": {"evaluation_results": results}},
            stats={"total_relations": len(relations), "qualified_relations": 0, "unqualified_relations": len(relations)},
        )


class TestIterationRound3Tag(unittest.TestCase):
    def test_unqualified_nodes_tagged_after_max_rounds(self):
        manager = IterationManager()
        evaluator = AlwaysUnqualifiedEvaluationAgent()
        nodes = [Node(name="A", desc="x", level=1)]

        output = manager.improve_nodes(nodes, generation_agent=None, evaluation_agent=evaluator, max_iterations=3)

        self.assertEqual(len(output), 1)
        marker = output[0].metadata.get(manager.UNQUALIFIED_ROUND3_MARKER)
        self.assertIsNotNone(marker)
        self.assertTrue(marker["enabled"])
        self.assertEqual(marker["rounds"], 3)

    def test_unqualified_relations_tagged_after_max_rounds(self):
        manager = IterationManager()
        evaluator = AlwaysUnqualifiedEvaluationAgent()
        nodes = [Node(name="A", desc="x", level=1), Node(name="B", desc="y", level=1)]
        relations = [Relation(object_a="A", object_b="B", relation_type="依赖", explanation="bad")]

        output = manager.improve_relations(
            relations,
            existing_nodes=nodes,
            generation_agent=None,
            evaluation_agent=evaluator,
            max_iterations=3,
        )

        self.assertEqual(len(output), 1)
        marker = output[0].metadata.get(manager.UNQUALIFIED_ROUND3_MARKER)
        self.assertIsNotNone(marker)
        self.assertTrue(marker["enabled"])
        self.assertEqual(marker["rounds"], 3)


if __name__ == "__main__":
    unittest.main()
