"""
主程序：基于新架构的知识图谱提取
功能：
1. 使用新的模块化架构
2. 支持断点续传
3. 统一的配置管理
4. 完整的错误处理
"""

import os
import sys
import io
import json
from datetime import datetime

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from src.pipeline import PipelineOrchestrator
from src.infrastructure import Logger


class CheckpointManager:
    """检查点管理器：负责保存和恢复进度"""

    def __init__(self, checkpoint_dir: str, material_name: str):
        """
        初始化检查点管理器

        Args:
            checkpoint_dir: 检查点目录
            material_name: 教材名称
        """
        self.checkpoint_dir = checkpoint_dir
        self.material_name = material_name
        self.logger = Logger("CheckpointManager")

        os.makedirs(checkpoint_dir, exist_ok=True)

        # 检查点文件路径
        self.checkpoint_file = os.path.join(
            checkpoint_dir,
            f"{material_name}_checkpoint.json"
        )
        self.log_file = os.path.join(
            checkpoint_dir,
            f"{material_name}_log.txt"
        )

    def save(self, nodes: list, relations: list):
        """
        保存检查点

        Args:
            nodes: 节点列表
            relations: 关系列表
        """
        from src.core import Node, Relation

        state = {
            "timestamp": datetime.now().isoformat(),
            "material_name": self.material_name,
            "nodes_count": len(nodes),
            "relations_count": len(relations),
            "nodes": [node.to_tuple() if isinstance(node, Node) else node for node in nodes],
            "relations": [rel.to_tuple() if isinstance(rel, Relation) else rel for rel in relations]
        }

        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        self.log(f"检查点已保存: {len(nodes)} 节点, {len(relations)} 关系")

    def load(self):
        """
        加载检查点

        Returns:
            (nodes, relations) 或 (None, None)
        """
        if not os.path.exists(self.checkpoint_file):
            return None, None

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.log(f"检查点已加载: {state.get('timestamp', 'unknown')}")
            self.log(f"  节点: {state.get('nodes_count', 0)}, 关系: {state.get('relations_count', 0)}")

            # 转换为Node和Relation对象
            from src.core import Node, Relation

            nodes = []
            for node_data in state.get("nodes", []):
                if isinstance(node_data, (list, tuple)) and len(node_data) == 2:
                    nodes.append(Node.from_tuple(node_data))

            relations = []
            for rel_data in state.get("relations", []):
                if isinstance(rel_data, (list, tuple)) and len(rel_data) == 3:
                    relations.append(Relation.from_tuple(rel_data))

            return nodes, relations

        except Exception as e:
            self.log(f"加载检查点失败: {e}")
            return None, None

    def exists(self) -> bool:
        """检查是否存在检查点"""
        return os.path.exists(self.checkpoint_file)

    def clear(self):
        """清除检查点"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            self.log("检查点已清除")

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"

        # 打印到控制台
        print(log_line)

        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")


def main():
    """主函数"""
    # 导入配置
    from scripts.config import (
        get_api_key,
        get_api_endpoint,
        MATERIAL_NAME,
        MATERIAL_TOC,
        MAX_ITERATIONS,
        MAX_WORKERS,
        FORCE_RESTART,
        get_material_path,
        get_nodes_output_path,
        get_relations_output_path,
        ensure_directories,
        validate_config,
        print_config
    )

    # 打印配置
    print_config()

    # 验证配置
    if not validate_config():
        print("\n配置验证失败，请检查配置文件")
        return

    # 获取 API 配置
    api_key = get_api_key()
    api_endpoint = get_api_endpoint()

    # 确保目录存在
    ensure_directories()

    # 读取教材文本
    material_path = get_material_path()
    print(f"\n加载教材: {material_path}")

    # 根据文件扩展名确定文件类型
    import os
    _, ext = os.path.splitext(material_path)
    file_type = ext.lstrip('.').lower()

    with open(material_path, 'r', encoding='utf-8') as f:
        material_text = f.read()
    print(f"教材加载完成: {len(material_text)} 字符")
    print(f"文件类型: {file_type}")

    # 计算章节长度信息（支持任意层级）
    print("\n计算章节长度信息...")
    from src.utils.section_length_calculator import SectionLengthCalculator
    from src.utils.unified_section_extractor import UnifiedSectionExtractor

    # 获取所有章节标题（带缩进，表示层级）
    all_section_titles = UnifiedSectionExtractor.get_section_summary(material_text, file_type)
    print(f"找到 {len(all_section_titles)} 个章节")

    # 提取所有层级的标题并计算长度
    section_lengths = {}
    for title_with_indent in all_section_titles:
        title = title_with_indent.strip()
        if title:  # 忽略空标题
            # 计算该标题对应的内容长度
            lengths = SectionLengthCalculator.calculate_section_lengths(
                material_text,
                [title],
                file_type
            )
            if title in lengths:
                section_lengths[title] = lengths[title]

    print(f"章节长度计算完成: {len(section_lengths)} 个章节")

    # 创建检查点管理器
    checkpoint_manager = CheckpointManager(
        checkpoint_dir="checkpoints",
        material_name=MATERIAL_NAME
    )

    # 检查是否有检查点
    if not FORCE_RESTART and checkpoint_manager.exists():
        print("\n发现检查点，尝试恢复...")
        nodes, relations = checkpoint_manager.load()

        if nodes is not None and relations is not None:
            print("\n从检查点恢复成功！")
            print(f"  节点: {len(nodes)}")
            print(f"  关系: {len(relations)}")

            # 询问用户是否继续
            response = input("\n是否继续从检查点恢复？(y/n): ").strip().lower()
            if response == 'y':
                # 保存结果
                save_results(nodes, relations, get_nodes_output_path(), get_relations_output_path())
                return
            else:
                print("将重新开始提取...")

    # 创建管线编排器
    orchestrator = PipelineOrchestrator(
        api_key,
        api_endpoint,
        material_text=material_text
    )

    # 运行管线
    try:
        nodes, relations = orchestrator.run(
            MATERIAL_TOC,
            section_lengths=section_lengths,
            max_iterations=MAX_ITERATIONS,
            max_workers=MAX_WORKERS
        )

        # 显示结果
        print("\n" + "=" * 80)
        print("提取完成")
        print("=" * 80)
        print(f"\n最终结果：")
        print(f"  - 节点：{len(nodes)}")
        print(f"  - 关系：{len(relations)}")

        # 显示节点示例
        if nodes:
            print("\n节点示例（前10个）：")
            for i, node in enumerate(nodes[:10], 1):
                print(f"  {i}. {node.name} (Level {node.level})")
                print(f"     描述: {node.desc[:60]}...")

        # 显示关系示例
        if relations:
            print("\n关系示例（前10条）：")
            for i, rel in enumerate(relations[:10], 1):
                print(f"  {i}. {rel.object_a} -> {rel.object_b} ({rel.relation_type})")
                if rel.explanation:
                    print(f"     说明: {rel.explanation[:50]}...")

        # 保存结果
        save_results(nodes, relations, get_nodes_output_path(), get_relations_output_path())

        # 清除检查点
        checkpoint_manager.clear()

        print("\n✓ 知识图谱提取完成！")

    except KeyboardInterrupt:
        print("\n\n用户中断，正在保存进度...")
        # 保存检查点
        if 'nodes' in locals() and 'relations' in locals():
            checkpoint_manager.save(nodes, relations)
            print("进度已保存到检查点，重新运行程序将从检查点继续")
        raise

    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()

        # 保存当前进度
        if 'nodes' in locals() and 'relations' in locals():
            checkpoint_manager.save(nodes, relations)
            print("\n进度已保存到检查点，重新运行程序将尝试恢复")


def save_results(nodes, relations, nodes_path, relations_path):
    """保存结果到JSON文件"""
    from src.core import Node, Relation
    from src.utils import JSONParser

    # 保存节点
    nodes_data = [node.to_tuple() if isinstance(node, Node) else node for node in nodes]
    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes_data, f, ensure_ascii=False, indent=2)
    print(f"\n节点已保存: {nodes_path}")

    # 保存关系
    relations_data = [rel.to_tuple() if isinstance(rel, Relation) else rel for rel in relations]
    with open(relations_path, 'w', encoding='utf-8') as f:
        json.dump(relations_data, f, ensure_ascii=False, indent=2)
    print(f"关系已保存: {relations_path}")


if __name__ == "__main__":
    main()
