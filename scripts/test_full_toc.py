"""
测试 Planning LLM 处理完整教材目录
"""

import os
import sys
import io
import json

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from new_Lib.planning_llm import PlanningLLM
from scripts.config import MATERIAL_TOC, get_api_key, get_api_endpoint

def test_full_toc():
    """测试完整教材目录"""
    print("\n" + "="*80)
    print("测试 Planning LLM 处理完整教材目录")
    print("="*80)

    api_key = get_api_key()
    api_endpoint = get_api_endpoint()

    print(f"\n教材目录长度: {len(MATERIAL_TOC)} 字符")
    print(f"教材目录行数: {len(MATERIAL_TOC.splitlines())} 行")

    print("\n前50行目录:")
    for i, line in enumerate(MATERIAL_TOC.splitlines()[:50], 1):
        print(f"  {i:2d}. {line}")

    planner = PlanningLLM(api_key, api_endpoint)
    planner.initialize_conversation()

    print("\n调用 Planning LLM...")
    plan = planner.analyze_toc(MATERIAL_TOC)

    print(f"\n解析结果:")
    print(f"  - 任务数量: {len(plan.get('subtasks', []))}")
    print(f"  - 章节分组数量: {len(plan.get('section_groups', []))}")
    print(f"  - 跨章节关系数量: {len(plan.get('cross_section_relations', []))}")

    if len(plan.get('subtasks', [])) > 1:
        print(f"\n✅ 成功：生成了 {len(plan.get('subtasks', []))} 个任务")

        print("\n任务列表:")
        for i, task in enumerate(plan.get('subtasks', [])[:10], 1):
            task_id = task.get('task_id', '?')
            task_type = task.get('task_type', '?')
            sections = task.get('target_sections', [])
            print(f"  {i:2d}. {task_id} ({task_type})")
            if sections:
                print(f"      章节: {', '.join(sections[:3])}")

        if len(plan.get('subtasks', [])) > 10:
            print(f"  ... 还有 {len(plan.get('subtasks', [])) - 10} 个任务")

        return True
    else:
        print("\n❌ 失败：只生成了一个任务")
        print("\n默认任务:")
        for task in plan.get('subtasks', []):
            print(f"  - {task}")

        return False


if __name__ == "__main__":
    success = test_full_toc()

    if success:
        print("\n" + "="*80)
        print("🎉 测试通过！Planning LLM 能够处理完整教材目录")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠️ 测试失败！需要进一步调试")
        print("="*80)
