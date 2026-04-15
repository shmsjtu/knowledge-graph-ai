"""
配置文件：统一管理所有超参数和路径
"""

import os
import re

# ============================================================================
# API 配置
# ============================================================================
API_KEY_ENV = "DEEPSEEK_API_KEY"
API_ENDPOINT_ENV = "DEEPSEEK_API_ENDPOINT"
API_ENDPOINT_DEFAULT = "https://api.deepseek.com"

# ============================================================================
# 教材配置
# ============================================================================
# 教材名称（用于区分不同教材的检查点和输出）
MATERIAL_NAME = "复分析II"

# 教材文件路径（相对于项目根目录）
MATERIAL_FILE = "复分析.md"

# ============================================================================
# 路径配置
# ============================================================================
# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 输出目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# 检查点目录
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "checkpoints")

# 日志目录
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# ============================================================================
# 自动提取教材目录
# ============================================================================
def get_material_path():
    """获取教材文件完整路径"""
    return os.path.join(PROJECT_ROOT, MATERIAL_FILE)

def extract_toc_from_file(file_path: str) -> str:
    """
    从 tex 或 md 文件中自动提取章节，生成目录结构

    Args:
        file_path: 文件路径

    Returns:
        目录字符串
    """
    import os

    # 获取文件扩展名
    _, ext = os.path.splitext(file_path)
    file_type = ext.lstrip('.').lower()

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if file_type == 'tex':
        # LaTeX 格式：提取 section, subsection, subsubsection 等
        # 匹配 \section, \subsection, \subsubsection 等
        pattern = r'\\(sub)*section\{([^}]+)\}'
        matches = re.findall(pattern, content)

        toc_lines = []
        for subs, title in matches:
            # subs 是 ('sub', 'sub', ...) 元组，表示层级
            level = len(subs) + 1 if subs else 1
            # section 是顶级标题（level=1），不缩进
            # subsection 是 level=2，缩进 2 个空格
            # subsubsection 是 level=3，缩进 4 个空格
            indent = '  ' * (level - 1)
            toc_lines.append(f"{indent}{title}")

        return '\n'.join(toc_lines)

    elif file_type in ['md', 'markdown']:
        # Markdown 格式：提取所有层级的标题
        lines = content.split('\n')
        toc_lines = []

        for line in lines:
            # 匹配任意级别的 Markdown 标题（##, ###, ####, 等）
            match = re.match(r'^(#{2,})\s+(.+)$', line)
            if match:
                level = len(match.group(1))  # # 的数量
                title = match.group(2).strip()
                # 二级标题（##）是 level=2，缩进 2 个空格
                # 三级标题（###）是 level=3，缩进 4 个空格
                # 以此类推，每多一级多缩进 2 个空格
                indent = '  ' * (level - 1)
                toc_lines.append(f"{indent}{title}")

        return '\n'.join(toc_lines)

    else:
        print(f"警告: 不支持的文件类型 {file_type}")
        return ""


def get_material_toc():
    """
    获取教材目录（自动从文件提取）

    Returns:
        目录字符串
    """
    material_path = get_material_path()

    if not os.path.exists(material_path):
        print(f"警告: 教材文件不存在 {material_path}")
        return ""

    try:
        toc = extract_toc_from_file(material_path)
        print(f"已从 {MATERIAL_FILE} 提取目录结构")
        return toc
    except Exception as e:
        print(f"警告: 提取目录失败 {e}")
        return ""


# 教材目录（自动从 tex 文件提取）
MATERIAL_TOC = get_material_toc()

# ============================================================================
# 管线配置
# ============================================================================
# 最大迭代次数（每个任务）
MAX_ITERATIONS = 3

# 最大并发数
MAX_WORKERS = 4

# ============================================================================
# 路径配置
# ============================================================================
# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 输出目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# 检查点目录
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, "checkpoints")

# 日志目录
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# ============================================================================
# 输出配置
# ============================================================================
# 节点输出文件名
NODES_OUTPUT_FILE = "{material_name}_nodes.json"

# 关系输出文件名
RELATIONS_OUTPUT_FILE = "{material_name}_relations.json"

# 显示的节点/关系示例数量
DISPLAY_EXAMPLES_COUNT = 10

# ============================================================================
# 运行配置
# ============================================================================
# 是否强制重新开始（忽略检查点）
FORCE_RESTART = False

# 是否显示详细日志
VERBOSE = True

# ============================================================================
# 辅助函数
# ============================================================================
def get_api_key():
    """获取 API Key"""
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv(API_KEY_ENV, "")

def get_api_endpoint():
    """获取 API Endpoint"""
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv(API_ENDPOINT_ENV, API_ENDPOINT_DEFAULT)

def get_nodes_output_path(material_name=None):
    """获取节点输出文件完整路径"""
    name = material_name or MATERIAL_NAME
    filename = NODES_OUTPUT_FILE.format(material_name=name)
    return os.path.join(OUTPUT_DIR, filename)

def get_relations_output_path(material_name=None):
    """获取关系输出文件完整路径"""
    name = material_name or MATERIAL_NAME
    filename = RELATIONS_OUTPUT_FILE.format(material_name=name)
    return os.path.join(OUTPUT_DIR, filename)

def ensure_directories():
    """确保所有必要的目录都存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

def print_config():
    """打印当前配置"""
    print("=" * 80)
    print("当前配置")
    print("=" * 80)
    print(f"教材名称: {MATERIAL_NAME}")
    print(f"教材文件: {MATERIAL_FILE}")
    print(f"最大迭代次数: {MAX_ITERATIONS}")
    print(f"最大并发数: {MAX_WORKERS}")
    print(f"强制重新开始: {FORCE_RESTART}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"检查点目录: {CHECKPOINT_DIR}")
    print("=" * 80)


# ============================================================================
# 配置验证
# ============================================================================
def validate_config():
    """验证配置是否有效"""
    errors = []

    # 检查 API Key
    if not get_api_key():
        errors.append(f"未设置 {API_KEY_ENV} 环境变量")

    # 检查教材文件
    material_path = get_material_path()
    if not os.path.exists(material_path):
        errors.append(f"教材文件不存在: {material_path}")

    # 检查教材目录
    if not MATERIAL_TOC or not MATERIAL_TOC.strip():
        errors.append("教材目录为空")

    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True


if __name__ == "__main__":
    # 测试配置
    print_config()
    print()
    if validate_config():
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败")
