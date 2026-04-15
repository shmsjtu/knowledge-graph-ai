import unittest

from src.agents.two_step_planning_agent import TwoStepPlanningAgent
from src.infrastructure.api_client import APIClient
from scripts.config import extract_toc_from_file, get_material_path


class TestSectionGroupingAndMerging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        material_path = get_material_path()
        cls.full_toc = extract_toc_from_file(material_path)
        cls.agent = TwoStepPlanningAgent(
            api_client=APIClient(api_key="dummy-key", api_endpoint="https://api.deepseek.com")
        )

    def test_full_toc_split_to_leaf_sections(self):
        leaves = self.agent._split_to_leaf_sections(self.full_toc)
        self.assertGreater(len(leaves), 0, "全量章节应拆分出叶子章节")
        leaf_titles = [item["title"] for item in leaves]
        self.assertTrue(
            any("基本定义" in title for title in leaf_titles),
            "应包含教材中的真实叶子章节标题"
        )

    def test_full_toc_auto_split_generates_valid_subtasks(self):
        leaves = self.agent._split_to_leaf_sections(self.full_toc)
        section_lengths = {
            leaf["title"]: 300 + (idx % 5) * 100
            for idx, leaf in enumerate(leaves)
        }

        result = self.agent._auto_split_sections(
            toc_content=self.full_toc,
            section_lengths=section_lengths,
            max_chars=2000
        )
        section_groups = result.get("section_groups", [])
        subtasks = result.get("subtasks", [])

        self.assertEqual(len(section_groups), len(subtasks))
        self.assertGreater(len(section_groups), 0, "全量章节应生成分组与任务")
        self.assertTrue(all(group.get("total_length", 0) <= 2000 for group in section_groups))
        self.assertTrue(all("target_sections" in task for task in subtasks))
        self.assertTrue(all("section_paths" in task for task in subtasks))

    def test_merge_with_real_chapter_titles(self):
        mini_toc = "\n".join(
            [
                "  集合及其运算",
                "    1. 集合的定义.",
                "    2. 集合的运算.",
                "  映射",
                "    1. 基本定义",
                "    2. 逆映射与复合映射",
            ]
        )
        section_lengths = {
            "1. 集合的定义.": 500,
            "2. 集合的运算.": 500,
            "1. 基本定义": 500,
            "2. 逆映射与复合映射": 500,
        }

        result = self.agent._auto_split_sections(
            toc_content=mini_toc,
            section_lengths=section_lengths,
            max_chars=1200
        )
        subtasks = result["subtasks"]
        self.assertEqual(len(subtasks), 2, "应按预算将 4 个叶子章节合并为 2 组")
        self.assertEqual(len(subtasks[0]["target_sections"]), 2)
        self.assertEqual(len(subtasks[1]["target_sections"]), 2)

    def test_step2_batches_use_sliding_windows(self):
        groups = [{"group_id": i + 1, "sections": [f"S{i+1}"], "total_length": 100} for i in range(20)]
        windows = self.agent._create_section_group_batches(groups)

        self.assertGreaterEqual(len(windows), 5)
        self.assertTrue(all(len(w) > 0 for w in windows))
        # 滑动窗口应存在重叠
        overlap_found = False
        for i in range(len(windows) - 1):
            current_ids = {g["group_id"] for g in windows[i]}
            next_ids = {g["group_id"] for g in windows[i + 1]}
            if current_ids & next_ids:
                overlap_found = True
                break
        self.assertTrue(overlap_found, "窗口之间应存在重叠")


if __name__ == "__main__":
    unittest.main()
