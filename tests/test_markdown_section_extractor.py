import unittest

from scripts.config import get_material_path
from src.utils.markdown_section_extractor import MarkdownSectionExtractor


class TestMarkdownSectionExtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(get_material_path(), "r", encoding="utf-8") as f:
            cls.text = f.read()

    def test_precise_match_not_fallback_to_parent_heading(self):
        target = "1. 定积分的定义."
        content = MarkdownSectionExtractor.extract_sections(self.text, [target])
        self.assertIn("### 1. 定积分的定义.", content)
        self.assertNotIn("### 2. 定积分的存在条件.", content)
        self.assertLess(len(content), 10000, "不应误匹配到整章“定积分”")

    def test_precise_match_for_nested_heading(self):
        target = "1.2. 广义积分的基本性质."
        content = MarkdownSectionExtractor.extract_sections(self.text, [target])
        self.assertIn("#### 1.2. 广义积分的基本性质.", content)
        self.assertNotIn("#### 1.3. 广义积分的计算.", content)


if __name__ == "__main__":
    unittest.main()
