"""
知识图谱 AI 助手 - Streamlit 应用
功能：
1. 管线流程控制：运行知识图谱提取管线
2. 图谱可视化：使用 pyvis 交互式可视化
3. 图谱编辑：实时查看和修改图谱
4. AI 助手：通过自然语言添加节点/关系
"""

import streamlit as st
import os
import sys
import json
import networkx as nx
from pyvis.network import Network
from datetime import datetime
from typing import List, Tuple
import tempfile

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# 延迟导入，避免循环导入问题
def import_modules():
    """延迟导入项目模块"""
    global Node, Relation, PipelineOrchestrator, Logger, prompts, OpenAI
    from src.core import Node, Relation
    from src.pipeline import PipelineOrchestrator
    from src.infrastructure import Logger
    from src.config import prompts
    from openai import OpenAI

# 在需要时调用
import_modules()

# ============================================================================
# 配置
# ============================================================================

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_ENDPOINT = os.getenv("DEEPSEEK_API_ENDPOINT", "https://api.deepseek.com")

# 关系颜色映射
REL_COLORS = {
    "层级包含": "#F5B721",
    "数学包含": "#F5B721",
    "具有性质": "#8cc78a",
    "具有实例": "#0000FF",
    "充分递推": "#00a5b1",
    "必要递推": "#00a5b1",
    "充要递推": "#00a5b1",
    "部分递推": "#00a5b1",
    "对偶": "#53B5FF",
    "推广": "#FFA500",
    "关联": "#888888",
}

# 节点层级大小映射
SIZE_MAP = {
    0: 50,  # 核心知识点
    1: 25,  # 主要知识点
    2: 17,  # 基本定义
    3: 11,  # 性质定理
    4: 5,   # 具体实例
}

# ============================================================================
# 工具函数
# ============================================================================

def load_graph_data(nodes_path: str, relations_path: str) -> Tuple[List[dict], List[dict]]:
    """加载图谱数据"""
    if not os.path.exists(nodes_path) or not os.path.exists(relations_path):
        return [], []

    with open(nodes_path, 'r', encoding='utf-8') as f:
        nodes_data = json.load(f)

    with open(relations_path, 'r', encoding='utf-8') as f:
        relations_data = json.load(f)

    # 转换为统一格式
    nodes = []
    for n in nodes_data:
        if isinstance(n, (list, tuple)) and len(n) == 2:
            name, data = n
            nodes.append({"name": name, **data})
        elif isinstance(n, dict):
            nodes.append(n)

    relations = []
    for r in relations_data:
        if isinstance(r, (list, tuple)) and len(r) == 3:
            obj_a, obj_b, data = r
            relations.append({
                "object_a": obj_a,
                "object_b": obj_b,
                "relation_type": data.get("rel", ""),
                "explanation": data.get("定理", ""),
                "color": data.get("color", "#888888")
            })
        elif isinstance(r, dict):
            relations.append(r)

    return nodes, relations


def save_graph_data(nodes: List[dict], relations: List[dict], nodes_path: str, relations_path: str):
    """保存图谱数据"""
    # 保存节点（tuple 格式）
    nodes_data = []
    for n in nodes:
        name = n.get("name", "未命名")
        nodes_data.append([name, {
            "desc": n.get("desc", ""),
            "level": n.get("level", 4),
            "color": n.get("color", "#FFFF00")
        }])

    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes_data, f, ensure_ascii=False, indent=2)

    # 保存关系（tuple 格式）
    relations_data = []
    for r in relations:
        obj_a = r.get("object_a", r.get("obj_a", ""))
        obj_b = r.get("object_b", r.get("obj_b", ""))
        rel_type = r.get("relation_type", r.get("rel_name", ""))
        explanation = r.get("explanation", r.get("explan", ""))
        color = r.get("color", REL_COLORS.get(rel_type, "#888888"))

        relations_data.append([obj_a, obj_b, {
            "rel": rel_type,
            "定理": explanation,
            "color": color
        }])

    with open(relations_path, 'w', encoding='utf-8') as f:
        json.dump(relations_data, f, ensure_ascii=False, indent=2)


def create_visualization(nodes: List[dict], relations: List[dict], height: str = "750px") -> str:
    """创建 pyvis 可视化"""
    # 创建有向图
    G = nx.DiGraph()

    # 添加节点
    for node in nodes:
        name = node.get("name", "未命名")
        G.add_node(
            name,
            desc=node.get("desc", ""),
            level=node.get("level", 4),
            color=node.get("color", "#FFFF00")
        )

    # 添加边
    for rel in relations:
        obj_a = rel.get("object_a", rel.get("obj_a", ""))
        obj_b = rel.get("object_b", rel.get("obj_b", ""))
        rel_type = rel.get("relation_type", rel.get("rel_name", ""))
        explanation = rel.get("explanation", rel.get("explan", ""))
        color = rel.get("color", REL_COLORS.get(rel_type, "#888888"))

        if obj_a and obj_b:
            G.add_edge(obj_a, obj_b, rel=rel_type, 定理=explanation, color=color)

    # 创建 pyvis 网络
    net = Network(notebook=True, directed=True, height=height, width="100%",
                  bgcolor="#e6f3ff", font_color="#333333")

    # 添加节点到 pyvis
    for node, data in G.nodes(data=True):
        title = f"{node}\n{data.get('desc', '')}"
        net.add_node(
            node,
            label=node,
            title=title,
            color=data.get("color", "#FFFF00"),
            size=SIZE_MAP.get(data.get("level", 4), 5),
            desc=data.get("desc", ""),
            level=data.get("level", 4)
        )

    # 添加边到 pyvis
    for u, v, data in G.edges(data=True):
        rel = data.get("rel", "未定义")
        theorem = data.get("定理", "未定义")

        # 根据关系类型设置箭头样式
        if rel in ["层级包含", "数学包含", "充分递推", "必要递推", "部分递推", "具有性质"]:
            arrows = "to"
        else:
            arrows = "to,from"

        net.add_edge(
            u, v,
            title=f"关系: {rel}\n定理: {theorem}",
            color=data.get("color", "#888888"),
            rel=rel,
            定理=theorem,
            arrows=arrows
        )

    # 配置可视化选项
    net.set_options('''
    var options = {
        "nodes": {
            "shape": "dot",
            "size": 16,
            "font": {"size": 28},
            "title": {
                "wrap": true,
                "maxWidth": 500
            },
            "borderWidth": 1,
            "shadow": true
        },
        "edges": {
            "arrows": {"to": {"enabled": true}},
            "smooth": {"type": "continuous"},
            "color": "#808080"
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200
        },
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -270000,
                "springLength": 150,
                "springConstant": 0.04,
                "damping": 0.09
            },
            "stabilization": {
                "iterations": 1000,
                "fit": true
            }
        },
        "layout": {
            "improvedLayout": true,
            "hierarchical": {
                "enabled": false
            }
        }
    }
    ''')

    # 生成 HTML
    html = net.generate_html()

    # 添加自定义 JavaScript（图例、信息面板等）
    custom_js = f'''
    <script type="text/javascript">
    var relColors = {json.dumps(REL_COLORS)};

    document.addEventListener("DOMContentLoaded", function() {{
        // 信息面板
        var infoPanel = document.createElement('div');
        infoPanel.id = 'infoPanel';
        infoPanel.style.position = 'absolute';
        infoPanel.style.right = '0';
        infoPanel.style.top = '0';
        infoPanel.style.width = '30%';
        infoPanel.style.height = '100%';
        infoPanel.style.backgroundColor = '#f9f9f9';
        infoPanel.style.padding = '20px';
        infoPanel.style.boxShadow = '-2px 0 5px rgba(0,0,0,0.1)';
        infoPanel.style.overflowY = 'auto';
        infoPanel.style.display = 'none';
        document.body.appendChild(infoPanel);

        // 图例
        var legend = document.createElement('div');
        legend.id = 'legend';
        legend.style.position = 'absolute';
        legend.style.left = '0px';
        legend.style.bottom = '20px';
        legend.style.width = '250px';
        legend.style.backgroundColor = '#f9f9f9';
        legend.style.padding = '10px';
        legend.style.boxShadow = '-2px 0 5px rgba(0,0,0,0.1)';
        legend.style.borderRadius = '5px';
        legend.style.zIndex = '1000';
        legend.style.fontSize = '12px';
        legend.style.lineHeight = '1.2';
        document.body.appendChild(legend);

        // 统计信息
        var nodeCount = {len(nodes)};
        var edgeCount = {len(relations)};

        var legendContent = `
            <p style="margin: 5px 0; font-weight: bold;">节点层级</p>
            <p style="margin: 3px 0;"><span style="color:#FF0000">■</span> 核心知识点 (Level 0)</p>
            <p style="margin: 3px 0;"><span style="color:#FFA500">■</span> 主要知识点 (Level 1)</p>
            <p style="margin: 3px 0;"><span style="color:#FFFF00">■</span> 基本定义 (Level 2)</p>
            <p style="margin: 3px 0;"><span style="color:#008000">■</span> 性质定理 (Level 3)</p>
            <p style="margin: 3px 0;"><span style="color:#0000FF">■</span> 具体实例 (Level 4)</p>

            <p style="margin: 10px 0 5px 0; font-weight: bold;">关系类型</p>
            <p style="margin: 3px 0;"><span style="color:#F5B721">■</span> 层级包含/数学包含</p>
            <p style="margin: 3px 0;"><span style="color:#8cc78a">■</span> 具有性质</p>
            <p style="margin: 3px 0;"><span style="color:#00a5b1">■</span> 递推关系</p>
            <p style="margin: 3px 0;"><span style="color:#53B5FF">■</span> 对偶</p>
            <p style="margin: 3px 0;"><span style="color:#FFA500">■</span> 推广</p>

            <p style="margin: 10px 0 5px 0; font-weight: bold;">统计</p>
            <p style="margin: 3px 0;">总节点数: ${{nodeCount}}</p>
            <p style="margin: 3px 0;">总关系数: ${{edgeCount}}</p>
        `;
        legend.innerHTML = legendContent;
    }});
    </script>
    '''

    # 将自定义脚本添加到 HTML
    html = html.replace('</body>', custom_js + '</body>')

    return html


def get_ai_relation_prediction(client: OpenAI, node_a: str, desc_a: str,
                                node_b: str, desc_b: str) -> dict:
    """使用 AI 预测两个节点之间的关系"""
    system_prompt = """你是一位数学知识图谱专家。请判断两个数学概念之间的关系。

请严格基于以下11种关系类别进行分类：
1. 层级包含：目录结构上的包含，或B是A的子类
2. 数学包含：集合论意义上的包含，A ⊇ B 或 B ∈ A
3. 具有性质：B是A的性质，或B是描述A的公式/定理
4. 具有实例：B是A的具体例子
5. 充分递推：A是B的充分条件
6. 必要递推：A是B的必要条件/基础/前提
7. 充要递推：A ↔ B，等价或一一对应
8. 部分递推：A是B的工具/方法，或A决定B的性质/存在性
9. 对偶：A与B结构对称互补
10. 推广：B是A的高维/一般化/抽象化形式
11. 关联：结构相似或有交叉，但不符合上述任一强逻辑关系

输出要求：仅输出标准 JSON 格式，不含markdown标记：
{"relation_type": "上述11个类别中的一个", "explanation": "选择该关系类别的理由"}
"""

    user_content = f"对象 A: {node_a}\n描述 A: {desc_a}\n\n对象 B: {node_b}\n描述 B: {desc_b}"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={'type': 'json_object'},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"relation_type": "API Error", "explanation": str(e)}


# ============================================================================
# 页面函数
# ============================================================================

def page_pipeline():
    """管线流程页面"""
    st.header("🔄 知识图谱提取管线")

    if not API_KEY:
        st.error("未配置 DEEPSEEK_API_KEY，请在项目根目录创建 `.env` 文件并填入 API Key。")
        return

    # 配置参数
    with st.expander("⚙️ 管线参数配置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            material_name = st.text_input("教材名称", value="微分学", key="pipeline_material_name")
            max_iterations = st.number_input("最大迭代次数", 1, 10, 3)
        with col2:
            max_workers = st.number_input("最大并发数", 1, 10, 4)
            force_restart = st.checkbox("强制重新开始", value=False)

    # 教材文件选择
    material_dir = os.path.join(project_root, "material")
    if os.path.exists(material_dir):
        material_folders = [d for d in os.listdir(material_dir)
                           if os.path.isdir(os.path.join(material_dir, d))]
        selected_folder = st.selectbox("选择教材", material_folders, key="pipeline_folder")

        if selected_folder:
            material_path = os.path.join(material_dir, selected_folder, f"{selected_folder}.md")

            if os.path.exists(material_path):
                st.success(f"教材文件: {material_path}")

                # 显示教材预览
                with st.expander("📖 教材预览", expanded=False):
                    with open(material_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.text_area("教材内容", content[:2000], height=300, disabled=True)
                    st.caption(f"总字符数: {len(content)}")

                # 运行管线按钮
                if st.button("🚀 运行管线", type="primary", key="run_pipeline_btn"):
                    run_pipeline_process(
                        material_name=selected_folder,
                        material_path=material_path,
                        max_iterations=max_iterations,
                        max_workers=max_workers,
                        force_restart=force_restart
                    )
            else:
                st.warning(f"未找到教材文件: {material_path}")
    else:
        st.warning("未找到 material 目录")


def run_pipeline_process(material_name: str, material_path: str,
                         max_iterations: int, max_workers: int, force_restart: bool):
    """运行管线流程"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.container()

    def update_progress(progress: float, message: str):
        progress_bar.progress(progress)
        status_text.text(message)

    try:
        # 读取教材
        update_progress(0.1, "正在读取教材...")
        with open(material_path, 'r', encoding='utf-8') as f:
            material_text = f.read()

        # 计算章节长度
        update_progress(0.2, "正在分析章节结构...")
        from src.utils.section_length_calculator import SectionLengthCalculator
        from src.utils.unified_section_extractor import UnifiedSectionExtractor

        _, ext = os.path.splitext(material_path)
        file_type = ext.lstrip('.').lower()

        all_section_titles = UnifiedSectionExtractor.get_section_summary(material_text, file_type)

        # 提取章节标题
        if file_type == 'tex':
            sections = [title.strip() for title in all_section_titles
                       if title.startswith("  ") and not title.startswith("    ")]
        else:
            sections = [title.strip() for title in all_section_titles
                       if title.startswith("  ") and not title.startswith("    ")]

        section_lengths = SectionLengthCalculator.calculate_section_lengths(
            material_text, sections, file_type
        )

        update_progress(0.3, f"找到 {len(sections)} 个章节")

        # 创建管线编排器
        update_progress(0.4, "正在初始化管线...")
        orchestrator = PipelineOrchestrator(
            API_KEY,
            API_ENDPOINT,
            material_text=material_text
        )

        # 运行管线
        update_progress(0.5, "正在运行管线...")
        material_toc = "\n".join(sections)

        nodes, relations = orchestrator.run(
            material_toc,
            section_lengths=section_lengths,
            max_iterations=max_iterations,
            max_workers=max_workers
        )

        # 保存结果
        update_progress(0.9, "正在保存结果...")
        output_dir = os.path.join(project_root, "material", material_name)
        os.makedirs(output_dir, exist_ok=True)

        nodes_path = os.path.join(output_dir, f"{material_name}_nodes.json")
        relations_path = os.path.join(output_dir, f"{material_name}_relations.json")

        save_graph_data(
            [{"name": n.name, "desc": n.desc, "level": n.level, "color": n.color} for n in nodes],
            [{"object_a": r.object_a, "object_b": r.object_b,
              "relation_type": r.relation_type, "explanation": r.explanation,
              "color": r.color} for r in relations],
            nodes_path,
            relations_path
        )

        update_progress(1.0, "完成！")

        # 显示结果
        st.success(f"✅ 知识图谱提取完成！\n- 节点数: {len(nodes)}\n- 关系数: {len(relations)}")

        with log_container:
            st.subheader("提取结果示例")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**节点示例（前10个）:**")
                for i, node in enumerate(nodes[:10], 1):
                    st.text(f"{i}. {node.name} (Level {node.level})")

            with col2:
                st.markdown("**关系示例（前10条）:**")
                for i, rel in enumerate(relations[:10], 1):
                    st.text(f"{i}. {rel.object_a} → {rel.object_b}")

    except Exception as e:
        st.error(f"❌ 管线运行失败: {e}")
        import traceback
        st.code(traceback.format_exc())


def page_workspace():
    """图谱工作台 - 整合可视化、编辑和AI助手"""
    st.header("🎯 知识图谱工作台")
    st.caption("在同一界面中查看图谱、编辑节点关系、调用AI助手")

    # 选择教材
    material_dir = os.path.join(project_root, "material")
    if not os.path.exists(material_dir):
        st.warning("未找到 material 目录")
        return

    material_folders = [d for d in os.listdir(material_dir)
                       if os.path.isdir(os.path.join(material_dir, d))]

    if not material_folders:
        st.warning("未找到任何教材数据")
        return

    # 选择教材和数据加载
    col_select, col_save = st.columns([4, 1])
    with col_select:
        selected_folder = st.selectbox("选择教材", material_folders, key="workspace_folder")

    if selected_folder:
        nodes_path = os.path.join(material_dir, selected_folder, f"{selected_folder}_nodes.json")
        relations_path = os.path.join(material_dir, selected_folder, f"{selected_folder}_relations.json")

        if not os.path.exists(nodes_path) or not os.path.exists(relations_path):
            st.warning("未找到图谱数据文件，请先运行管线提取")
            return

        # 加载图谱数据
        nodes, relations = load_graph_data(nodes_path, relations_path)

        if not nodes:
            st.warning("图谱数据为空")
            return

        # 显示统计信息和保存按钮
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            st.metric("节点数", len(nodes))
        with col2:
            st.metric("关系数", len(relations))
        with col3:
            st.metric("教材", selected_folder)
        with col4:
            if st.button("💾 保存修改", type="primary", key="save_all"):
                save_graph_data(nodes, relations, nodes_path, relations_path)
                st.success("✅ 已保存")
                st.rerun()

        st.divider()

        # 主布局：左侧可视化，右侧编辑和AI助手
        col_left, col_right = st.columns([2, 1])

        # ========== 左侧：图谱可视化 ==========
        with col_left:
            st.subheader("📊 图谱可视化")

            # 可视化参数
            with st.expander("⚙️ 可视化参数", expanded=False):
                viz_height = st.slider("画布高度", 400, 1200, 750, 50, key="viz_height")

            # 生成可视化
            if st.button("🎨 生成/刷新可视化", type="primary", key="gen_viz"):
                with st.spinner("正在生成可视化..."):
                    html = create_visualization(nodes, relations, f"{viz_height}px")

                    # 保存到临时文件
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
                    temp_file.write(html)
                    temp_file.close()

                    # 读取并显示
                    with open(temp_file.name, 'r', encoding='utf-8') as f:
                        html_content = f.read()

                    st.components.v1.html(html_content, height=viz_height, scrolling=True)

                    # 清理临时文件
                    os.unlink(temp_file.name)

        # ========== 右侧：编辑和AI助手 ==========
        with col_right:
            # 创建标签页切换编辑和AI助手
            right_tab1, right_tab2 = st.tabs(["✏️ 图谱编辑", "🤖 AI 助手"])

            # ---------- 标签页1：图谱编辑 ----------
            with right_tab1:
                # 节点操作
                st.markdown("### 节点操作")

                # 添加节点
                with st.expander("➕ 添加节点", expanded=False):
                    with st.form("add_node_form"):
                        node_name = st.text_input("名称 *", key="add_node_name")
                        node_desc = st.text_area("描述 *", key="add_node_desc")
                        node_level = st.selectbox("层级", [0, 1, 2, 3, 4], key="add_node_level")

                        level_colors = {
                            0: "#FF0000", 1: "#FFA500", 2: "#FFFF00",
                            3: "#008000", 4: "#0000FF",
                        }
                        node_color = st.color_picker("颜色", value=level_colors[node_level], key="add_node_color")

                        if st.form_submit_button("添加", type="primary"):
                            if node_name and node_desc:
                                if any(n.get("name") == node_name for n in nodes):
                                    st.error(f"节点 '{node_name}' 已存在！")
                                else:
                                    nodes.append({
                                        "name": node_name,
                                        "desc": node_desc,
                                        "level": node_level,
                                        "color": node_color
                                    })
                                    save_graph_data(nodes, relations, nodes_path, relations_path)
                                    st.success(f"✅ 已添加")
                                    st.rerun()
                            else:
                                st.error("请填写必填项")

                # 编辑/删除节点
                if nodes:
                    with st.expander("✏️ 编辑节点", expanded=False):
                        node_names = [n.get("name") for n in nodes]
                        selected_node = st.selectbox("选择节点", node_names, key="edit_node_select")

                        if selected_node:
                            node_idx = next((i for i, n in enumerate(nodes) if n.get("name") == selected_node), None)
                            if node_idx is not None:
                                node = nodes[node_idx]

                                with st.form("edit_node_form"):
                                    e_name = st.text_input("名称", value=node.get("name"), key="edit_node_name")
                                    e_desc = st.text_area("描述", value=node.get("desc", ""), key="edit_node_desc")
                                    e_level = st.selectbox("层级", [0, 1, 2, 3, 4],
                                                          index=node.get("level", 4), key="edit_node_level")
                                    e_color = st.color_picker("颜色", value=node.get("color", "#FFFF00"), key="edit_node_color")

                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.form_submit_button("保存", type="primary"):
                                            if e_name != selected_node and any(n.get("name") == e_name for n in nodes):
                                                st.error(f"名称 '{e_name}' 已存在！")
                                            else:
                                                nodes[node_idx] = {
                                                    "name": e_name, "desc": e_desc,
                                                    "level": e_level, "color": e_color
                                                }
                                                if e_name != selected_node:
                                                    for rel in relations:
                                                        if rel.get("object_a") == selected_node:
                                                            rel["object_a"] = e_name
                                                        if rel.get("object_b") == selected_node:
                                                            rel["object_b"] = e_name
                                                save_graph_data(nodes, relations, nodes_path, relations_path)
                                                st.success("✅ 已更新")
                                                st.rerun()

                                    with c2:
                                        if st.form_submit_button("删除"):
                                            nodes.pop(node_idx)
                                            relations = [r for r in relations
                                                       if r.get("object_a") != selected_node
                                                       and r.get("object_b") != selected_node]
                                            save_graph_data(nodes, relations, nodes_path, relations_path)
                                            st.success(f"✅ 已删除")
                                            st.rerun()

                st.divider()

                # 关系操作
                st.markdown("### 关系操作")

                # 添加关系
                with st.expander("➕ 添加关系", expanded=False):
                    if len(nodes) < 2:
                        st.warning("需要至少 2 个节点")
                    else:
                        node_names = [n.get("name") for n in nodes]

                        with st.form("add_relation_form"):
                            c1, c2 = st.columns(2)
                            with c1:
                                obj_a = st.selectbox("起点", node_names, key="add_rel_a")
                            with c2:
                                obj_b = st.selectbox("终点", node_names, key="add_rel_b")

                            rel_type = st.selectbox("类型", list(REL_COLORS.keys()), key="add_rel_type")
                            explanation = st.text_area("说明", key="add_rel_exp")

                            if st.form_submit_button("添加", type="primary"):
                                if obj_a == obj_b:
                                    st.error("起点和终点不能相同")
                                else:
                                    exists = any(r.get("object_a") == obj_a and r.get("object_b") == obj_b for r in relations)
                                    if exists:
                                        st.error(f"关系已存在！")
                                    else:
                                        relations.append({
                                            "object_a": obj_a, "object_b": obj_b,
                                            "relation_type": rel_type,
                                            "explanation": explanation,
                                            "color": REL_COLORS[rel_type]
                                        })
                                        save_graph_data(nodes, relations, nodes_path, relations_path)
                                        st.success(f"✅ 已添加")
                                        st.rerun()

                # 编辑/删除关系
                if relations:
                    with st.expander("✏️ 编辑关系", expanded=False):
                        rel_opts = [f"{r.get('object_a')} → {r.get('object_b')} ({r.get('relation_type', '')})"
                                   for r in relations]
                        selected_rel_idx = st.selectbox("选择关系", range(len(rel_opts)),
                                                       format_func=lambda x: rel_opts[x],
                                                       key="edit_rel_select")

                        if selected_rel_idx is not None:
                            rel = relations[selected_rel_idx]
                            node_names = [n.get("name") for n in nodes]

                            with st.form("edit_relation_form"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    e_obj_a = st.selectbox("起点", node_names,
                                                          index=node_names.index(rel.get("object_a")) if rel.get("object_a") in node_names else 0,
                                                          key="edit_rel_a")
                                with c2:
                                    e_obj_b = st.selectbox("终点", node_names,
                                                          index=node_names.index(rel.get("object_b")) if rel.get("object_b") in node_names else 0,
                                                          key="edit_rel_b")

                                e_rel_type = st.selectbox("类型", list(REL_COLORS.keys()),
                                                         index=list(REL_COLORS.keys()).index(rel.get("relation_type")) if rel.get("relation_type") in REL_COLORS else 0,
                                                         key="edit_rel_type")
                                e_explanation = st.text_area("说明", value=rel.get("explanation", ""), key="edit_rel_exp")

                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.form_submit_button("保存", type="primary"):
                                        relations[selected_rel_idx] = {
                                            "object_a": e_obj_a, "object_b": e_obj_b,
                                            "relation_type": e_rel_type,
                                            "explanation": e_explanation,
                                            "color": REL_COLORS[e_rel_type]
                                        }
                                        save_graph_data(nodes, relations, nodes_path, relations_path)
                                        st.success("✅ 已更新")
                                        st.rerun()

                                with c2:
                                    if st.form_submit_button("删除"):
                                        relations.pop(selected_rel_idx)
                                        save_graph_data(nodes, relations, nodes_path, relations_path)
                                        st.success("✅ 已删除")
                                        st.rerun()

                st.divider()

                # 批量操作
                st.markdown("### 批量操作")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ 删除孤立节点", key="del_isolated"):
                        connected = set()
                        for rel in relations:
                            connected.add(rel.get("object_a"))
                            connected.add(rel.get("object_b"))
                        original = len(nodes)
                        nodes = [n for n in nodes if n.get("name") in connected]
                        if len(nodes) < original:
                            save_graph_data(nodes, relations, nodes_path, relations_path)
                            st.success(f"✅ 删除 {original - len(nodes)} 个")
                            st.rerun()
                        else:
                            st.info("无孤立节点")

                with c2:
                    if st.button("🗑️ 删除重复关系", key="del_dup"):
                        seen = set()
                        unique = []
                        dup = 0
                        for rel in relations:
                            key = (rel.get("object_a"), rel.get("object_b"))
                            if key not in seen:
                                seen.add(key)
                                unique.append(rel)
                            else:
                                dup += 1
                        if dup > 0:
                            relations = unique
                            save_graph_data(nodes, relations, nodes_path, relations_path)
                            st.success(f"✅ 删除 {dup} 条")
                            st.rerun()
                        else:
                            st.info("无重复关系")

            # ---------- 标签页2：AI 助手 ----------
            with right_tab2:
                if not API_KEY:
                    st.error("未配置 API Key")
                else:
                    st.markdown("### AI 助手")

                    # AI 功能选择
                    ai_func = st.radio("选择功能", ["智能添加节点", "智能添加关系", "智能补全关系"], key="ai_func")

                    if ai_func == "智能添加节点":
                        st.markdown("**通过自然语言添加节点**")

                        user_input = st.text_area(
                            "描述节点",
                            placeholder="例：添加一个名为'连续函数'的节点，描述函数在某点连续的性质",
                            height=80, key="ai_node_input"
                        )

                        if st.button("🤖 生成", type="primary", key="ai_gen_node"):
                            if user_input:
                                with st.spinner("AI 生成中..."):
                                    client = OpenAI(api_key=API_KEY, base_url=API_ENDPOINT)

                                    system_prompt = """你是数学知识图谱专家。根据用户描述生成节点信息。

输出 JSON 格式：
{"name": "名称", "desc": "描述(15-50字)", "level": 0-4}

层级：0=核心知识点, 1=主要知识点, 2=基本定义, 3=性质定理, 4=具体实例"""

                                    try:
                                        response = client.chat.completions.create(
                                            model="deepseek-chat",
                                            messages=[
                                                {"role": "system", "content": system_prompt},
                                                {"role": "user", "content": user_input}
                                            ],
                                            response_format={'type': 'json_object'},
                                            temperature=0.3
                                        )

                                        result = json.loads(response.choices[0].message.content)
                                        st.json(result)

                                        if st.button("✅ 确认添加", key="confirm_ai_node"):
                                            level_colors = {0: "#FF0000", 1: "#FFA500", 2: "#FFFF00",
                                                          3: "#008000", 4: "#0000FF"}
                                            nodes.append({
                                                "name": result["name"],
                                                "desc": result["desc"],
                                                "level": result["level"],
                                                "color": level_colors[result["level"]]
                                            })
                                            save_graph_data(nodes, relations, nodes_path, relations_path)
                                            st.success(f"✅ 已添加 '{result['name']}'")
                                            st.rerun()

                                    except Exception as e:
                                        st.error(f"失败: {e}")
                            else:
                                st.warning("请输入描述")

                    elif ai_func == "智能添加关系":
                        st.markdown("**AI 判断节点关系**")

                        if len(nodes) < 2:
                            st.warning("需要至少 2 个节点")
                        else:
                            node_names = [n.get("name") for n in nodes]
                            node_descs = {n.get("name"): n.get("desc", "") for n in nodes}

                            c1, c2 = st.columns(2)
                            with c1:
                                node_a = st.selectbox("起点", node_names, key="ai_rel_a")
                            with c2:
                                node_b = st.selectbox("终点", node_names, key="ai_rel_b")

                            if st.button("🤖 判断", type="primary", key="ai_judge_rel"):
                                if node_a == node_b:
                                    st.error("起点和终点不能相同")
                                else:
                                    with st.spinner("AI 判断中..."):
                                        client = OpenAI(api_key=API_KEY, base_url=API_ENDPOINT)

                                        result = get_ai_relation_prediction(
                                            client, node_a, node_descs.get(node_a, ""),
                                            node_b, node_descs.get(node_b, "")
                                        )

                                        st.json(result)

                                        if st.button("✅ 确认添加", key="confirm_ai_rel"):
                                            relations.append({
                                                "object_a": node_a,
                                                "object_b": node_b,
                                                "relation_type": result["relation_type"],
                                                "explanation": result["explanation"],
                                                "color": REL_COLORS.get(result["relation_type"], "#888888")
                                            })
                                            save_graph_data(nodes, relations, nodes_path, relations_path)
                                            st.success(f"✅ 已添加关系")
                                            st.rerun()

                    elif ai_func == "智能补全关系":
                        st.markdown("**批量补全空白关系**")

                        incomplete = [(i, r) for i, r in enumerate(relations)
                                     if not r.get("relation_type") or not r.get("explanation")]

                        if not incomplete:
                            st.success("✅ 所有关系已完整")
                        else:
                            st.warning(f"发现 {len(incomplete)} 条待补全")

                            if st.button("🤖 批量补全", type="primary", key="ai_batch_fill"):
                                client = OpenAI(api_key=API_KEY, base_url=API_ENDPOINT)
                                node_descs = {n.get("name"): n.get("desc", "") for n in nodes}

                                progress = st.progress(0)
                                status = st.empty()

                                for idx, (rel_idx, rel) in enumerate(incomplete):
                                    status.text(f"{idx + 1}/{len(incomplete)}: {rel.get('object_a')} → {rel.get('object_b')}")

                                    result = get_ai_relation_prediction(
                                        client, rel.get("object_a"), node_descs.get(rel.get("object_a"), ""),
                                        rel.get("object_b"), node_descs.get(rel.get("object_b"), "")
                                    )

                                    relations[rel_idx]["relation_type"] = result["relation_type"]
                                    relations[rel_idx]["explanation"] = result["explanation"]
                                    relations[rel_idx]["color"] = REL_COLORS.get(result["relation_type"], "#888888")

                                    progress.progress((idx + 1) / len(incomplete))

                                save_graph_data(nodes, relations, nodes_path, relations_path)
                                st.success(f"✅ 已补全 {len(incomplete)} 条")
                                st.rerun()



# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    st.set_page_config(
        page_title="知识图谱 AI 助手",
        page_icon="🧠",
        layout="wide"
    )

    # 侧边栏
    st.sidebar.title("🧠 知识图谱 AI 助手")
    st.sidebar.caption("AI 赋能知识图谱构建与管理平台")

    if API_KEY:
        st.sidebar.success("✅ API Key 已配置")
    else:
        st.sidebar.error("❌ 未检测到 API Key")

    st.sidebar.divider()

    # 页面选择
    page = st.sidebar.radio(
        "功能导航",
        options=["管线流程", "图谱工作台"],
        format_func=lambda x: {
            "管线流程": "🔄 管线流程",
            "图谱工作台": "🎯 图谱工作台"
        }.get(x, x)
    )

    # 路由到对应页面
    if page == "管线流程":
        page_pipeline()
    elif page == "图谱工作台":
        page_workspace()


if __name__ == "__main__":
    main()
