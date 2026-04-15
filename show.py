import os
import json
from pyvis.network import Network

def load_json_file(file_path):
    """加载JSON文件并返回数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: 文件未找到 - {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"警告: JSON解析错误 - {file_path}")
        return []

def merge_nodes(titles):
    """合并多个主题的节点数据，返回新格式（元组列表）"""
    all_nodes = []
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for title in titles:
        nodes_path = os.path.join(current_dir, "material", title, f"{title}_nodes.json")
        nodes_data = load_json_file(nodes_path)

        if not isinstance(nodes_data, list):
            print(f"警告: {title}_nodes.json 不是列表格式")
            continue

        # Convert JSON arrays to tuples if in new format
        for item in nodes_data:
            if isinstance(item, list) and len(item) == 2:
                # New format: [name, data_dict]
                all_nodes.append((item[0], item[1]))
            elif isinstance(item, dict):
                # Old format: convert to new
                name = item.get("name", "未命名")
                desc = item.get("desc", "")
                classification = item.get("classification", "定义")

                # Map classification to level and color
                level_map = {
                    "核心知识点": 0,
                    "主要知识点": 1,
                    "定义": 2,
                    "性质定理": 3,
                    "具体实例": 4,
                    "定理": 3,
                    "命题": 3,
                    "例子": 4
                }
                color_map = {
                    "核心知识点": "#FF0000",
                    "主要知识点": "#FFA500",
                    "定义": "#FFFF00",
                    "性质定理": "#008000",
                    "具体实例": "#0000FF",
                    "定理": "#008000",
                    "命题": "#008000",
                    "例子": "#0000FF"
                }

                level = level_map.get(classification, 2)
                color = color_map.get(classification, "#FFFF00")

                all_nodes.append((name, {
                    "desc": desc,
                    "level": level,
                    "color": color
                }))

    return all_nodes

def merge_relations(titles):
    """合并多个主题的关系数据，返回新格式（元组列表）"""
    all_relations = []
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for title in titles:
        relations_path = os.path.join(current_dir, "material", title, f"{title}_relations.json")
        relations_data = load_json_file(relations_path)

        if not isinstance(relations_data, list):
            print(f"警告: {title}_relations.json 不是列表格式")
            continue

        # Convert JSON arrays to tuples if in new format
        for item in relations_data:
            if isinstance(item, list) and len(item) == 3:
                # New format: [node_a, node_b, data_dict]
                all_relations.append((item[0], item[1], item[2]))
            elif isinstance(item, dict):
                # Old format: convert to new
                obj_a = item.get("object_a", "")
                obj_b = item.get("object_b", "")
                relation = item.get("relation", "relate_to")
                explanation = item.get("explanation", "")

                # Map relation to color
                rel_colors = {
                    "包含": "#F5B721",
                    "属性": "#8cc78a",
                    "充分递推": "#00a5b1",
                    "必要递推": "#00a5b1",
                    "充要递推": "#00a5b1",
                    "部分递推": "#00a5b1",
                    "对应": "#53B5FF",
                    "互斥": "#007665",
                    "等价": "#ff8983",
                    "instance": "#0000FF",
                    "use_concept": "#8cc78a",
                    "is_special_case_of": "#F5B721",
                    "sufficiently_imply": "#00a5b1",
                    "necessarily_imply": "#00a5b1",
                    "equivalent": "#ff8983",
                    "partially_imply": "#00a5b1",
                    "generalize": "#53B5FF",
                    "dual_to": "#53B5FF",
                    "exclusive": "#007665",
                    "has_property": "#8cc78a",
                    "relate_to": "#888888"
                }

                color = rel_colors.get(relation, "#888888")

                all_relations.append((obj_a, obj_b, {
                    "rel": relation,
                    "定理": explanation,
                    "color": color
                }))

    return all_relations

def create_knowledge_graph(titles, output_file="knowledge_graph.html", output_dir="output"):
    """创建知识图谱"""
    print(f"正在处理主题: {', '.join(titles)}")

    # 确保输出目录存在
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, output_dir, output_file)

    # 加载并合并数据
    nodes = merge_nodes(titles)
    relations = merge_relations(titles)

    print(f"总节点数: {len(nodes)}")
    print(f"总关系数: {len(relations)}")

    if not nodes:
        print("错误: 没有找到任何节点数据")
        return

    # 创建节点名称集合，用于验证关系
    node_names = {name for name, _ in nodes}

    # Size mapping based on level
    size_map = {
        0: 50,  # 层级 0 的节点最大
        1: 25,
        2: 17,
        3: 11,
        4: 5   # 层级 4 的节点最小
    }

    # 创建网络图 - 完全按照目标文件的方式
    net = Network(notebook=True, directed=True, height="750px", width="100%",
                  bgcolor="#e6f3ff", font_color="#333333")

    # 添加节点
    for node_name, node_data in nodes:
        desc = node_data.get("desc", "无描述")
        level = node_data.get("level", 2)
        color = node_data.get("color", "#FFFF00")

        title = f"{node_name}\n{desc}"

        net.add_node(
            node_name,
            label=node_name,
            title=title,
            color=color,
            size=size_map.get(level, 17),
            desc=desc,
            level=level
        )

    # 添加边
    skipped_relations = 0
    added_relations = 0

    for node_a, node_b, edge_data in relations:
        # 检查节点是否存在
        if not node_a or not node_b:
            skipped_relations += 1
            continue

        if node_a not in node_names:
            print(f"警告: 关系中的节点 '{node_a}' 不存在，跳过该关系")
            skipped_relations += 1
            continue

        if node_b not in node_names:
            print(f"警告: 关系中的节点 '{node_b}' 不存在，跳过该关系")
            skipped_relations += 1
            continue

        if node_a == node_b:
            print(f"警告: 关系中的节点 '{node_a}' 和 '{node_b}' 相同，跳过该关系")
            skipped_relations += 1
            continue

        rel = edge_data.get("rel", "未定义")
        theorem = edge_data.get("定理", "未定义")
        color = edge_data.get("color", "#888888")

        # 根据关系类型设置箭头样式
        if rel in ["包含", "充分递推", "必要递推", "部分递推", "属性", "use_concept", "instance", "is_special_case_of", "sufficiently_imply", "necessarily_imply", "partially_imply", "has_property"]:
            arrows = "to"  # 单箭头
        else:
            arrows = "to,from"  # 双箭头

        net.add_edge(
            node_a, node_b,
            title=f"关系: {rel}\n定理: {theorem}",
            color=color,
            rel=rel,
            定理=theorem,
            arrows=arrows
        )
        added_relations += 1

    # 输出统计信息
    print(f"成功添加关系: {added_relations}")
    if skipped_relations > 0:
        print(f"跳过的关系: {skipped_relations} (节点不存在)")

    # 配置 2D 可视化选项 - 完全按照目标文件
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

    # 保存为 HTML 文件 - 完全按照目标文件的方式
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(net.generate_html())

    # 添加自定义 JavaScript 代码以支持交互 - 完全按照目标文件的方式
    import json as json_module

    # 准备节点和边的数据
    nodes_json = []
    for node_name, node_data in nodes:
        nodes_json.append({
            "id": node_name,
            "label": node_name,
            "desc": node_data.get("desc", ""),
            "level": node_data.get("level", 2),
            "color": node_data.get("color", "#FFFF00")
        })

    edges_json = []
    for node_a, node_b, edge_data in relations:
        edges_json.append({
            "from": node_a,
            "to": node_b,
            "rel": edge_data.get("rel", ""),
            "定理": edge_data.get("定理", "")
        })

    html_script = f'''
var container = document.getElementById('mynetwork');
container.style.width = '70%';
container.style.height = '100%';
container.style.position = 'absolute';
container.style.left = '0';
container.style.top = '0';
<script type="text/javascript">
document.addEventListener("DOMContentLoaded", function() {{
    // 创建右侧信息面板（初始隐藏）
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
    infoPanel.style.display = 'none';  // 初始隐藏
    document.body.appendChild(infoPanel);

    // 创建图例容器（放在左下角）
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

    // 初始化网络
    var container = document.getElementById('mynetwork');
    var data = {{
        nodes: new vis.DataSet({json_module.dumps(nodes_json, ensure_ascii=False)}),
        edges: new vis.DataSet({json_module.dumps(edges_json, ensure_ascii=False)})
    }};
    var options = {json_module.dumps(net.options, ensure_ascii=False)};
    var network = new vis.Network(container, data, options);

    // 原始节点布局缓存
    var originalPositions = {{}};
    data.nodes.forEach(function(node) {{
        originalPositions[node.id] = {{x: node.x, y: node.y}};
    }});

    // 统计每个层级的节点数和关系数
    function countLevelNodesAndEdges() {{
        var levelCounts = {{}};
        data.nodes.forEach(function(node) {{
            var level = node.level;
            if (!levelCounts[level]) {{
                levelCounts[level] = {{nodes: 0, edges: 0}};
            }}
            levelCounts[level].nodes++;
        }});
        data.edges.forEach(function(edge) {{
            var fromNode = data.nodes.get(edge.from);
            var toNode = data.nodes.get(edge.to);
            var levels = [fromNode.level, toNode.level];
            levels.forEach(function(level) {{
                if (!levelCounts[level]) {{
                    levelCounts[level] = {{nodes: 0, edges: 0}};
                }}
                levelCounts[level].edges++;
            }});
        }});
        return levelCounts;
    }}

    // 更新图例内容
    function updateLegend() {{
        var levelCounts = countLevelNodesAndEdges();
        // 计算节点和关系的总数
        var totalNodes = 0;
        var totalEdges = 0;
        for (var level in levelCounts) {{
            totalNodes += levelCounts[level].nodes;
            totalEdges += levelCounts[level].edges;
        }}
        var nodeColorLegend = `
            <p style="margin: 5px 0;">节点颜色含义</p>
            <p style="margin: 3px 0;"><span style="color:#FF0000">■</span> 核心知识点</p>
            <p style="margin: 3px 0;"><span style="color:#FFA500">■</span> 主要知识点</p>
            <p style="margin: 3px 0;"><span style="color:#FFFF00">■</span> 基本定义</p>
            <p style="margin: 3px 0;"><span style="color:#00FF00">■</span> 性质定理</p>
            <p style="margin: 3px 0;"><span style="color:#0000FF">■</span> 具体实例</p>
        `;
        var edgeColorLegend = `
            <p style="margin: 5px 0;">关系种类及颜色</p>
            <p style="margin: 3px 0;"><span style="color:#F5B721">■</span> 包含</p>
            <p style="margin: 3px 0;"><span style="color:#8cc78a">■</span> 性质（属性）</p>
            <p style="margin: 3px 0;"><span style="color:#00a5b1">■</span> 递推（包含充分递推，必要递推，充要递推，部分递推）</p>
            <p style="margin: 3px 0;"><span style="color:#53B5FF">■</span> 对应</p>
            <p style="margin: 3px 0;"><span style="color:#007665">■</span> 互斥</p>
            <p style="margin: 3px 0;"><span style="color:#ff8983">■</span> 等价</p>
        `;
        var levelSelection = `
            <p style="margin: 5px 0;">层级选择</p>
            <p style="margin: 3px 0;">选择显示的节点层级：</p>
            <label style="margin: 3px 0;"><input type="checkbox" name="level" value="0" checked> 层级 0 (节点数: ${{levelCounts[0]?.nodes || 0}}, 关系数: ${{levelCounts[0]?.edges || 0}})</label><br>
            <label style="margin: 3px 0;"><input type="checkbox" name="level" value="1" checked> 层级 1 (节点数: ${{levelCounts[1]?.nodes || 0}}, 关系数: ${{levelCounts[1]?.edges || 0}})</label><br>
            <label style="margin: 3px 0;"><input type="checkbox" name="level" value="2" checked> 层级 2 (节点数: ${{levelCounts[2]?.nodes || 0}}, 关系数: ${{levelCounts[2]?.edges || 0}})</label><br>
            <label style="margin: 3px 0;"><input type="checkbox" name="level" value="3" checked> 层级 3 (节点数: ${{levelCounts[3]?.nodes || 0}}, 关系数: ${{levelCounts[3]?.edges || 0}})</label><br>
            <label style="margin: 3px 0;"><input type="checkbox" name="level" value="4" checked> 层级 4 (节点数: ${{levelCounts[4]?.nodes || 0}}, 关系数: ${{levelCounts[4]?.edges || 0}})</label><br>
            <button style="margin: 5px 0;" onclick="updateNodeVisibility()">更新</button>
        `;
        var totalStats = `
            <p style="margin: 5px 0;">总量统计</p>
            <p style="margin: 3px 0;">总节点数: ${{totalNodes}}</p>
            <p style="margin: 3px 0;">总关系数: ${{totalEdges}}</p>
        `;
        legend.innerHTML = levelSelection + nodeColorLegend + edgeColorLegend + totalStats;
    }}

    // 初始化图例
    updateLegend();

    // 点击事件处理
    network.on("click", function(params) {{
        if (params.nodes.length) {{
            var nodeId = params.nodes[0];
            var connectedNodes = network.getConnectedNodes(nodeId);
            var visibleNodes = [nodeId].concat(connectedNodes);
            // 更新节点可见性并保持原始位置
            data.nodes.forEach(function(node) {{
                if (!visibleNodes.includes(node.id)) {{
                    data.nodes.update({{id: node.id, hidden: true}});
                }} else {{
                    data.nodes.update({{
                        id: node.id,
                        hidden: false,
                        x: originalPositions[node.id]?.x || Math.random()*500,
                        y: originalPositions[node.id]?.y || Math.random()*500
                    }});
                }}
            }});
            // 重新稳定布局
            network.stabilize(100);
            network.fit();
            // 更新右侧信息面板并显示
            var nodeData = data.nodes.get(nodeId);
            var edges = network.getConnectedEdges(nodeId);
            var relatedNodes = [];
            edges.forEach(function(edgeId) {{
                var edgeData = data.edges.get(edgeId);
                var relatedNodeId = edgeData.from === nodeId ? edgeData.to : edgeData.from;
                var relatedNodeData = data.nodes.get(relatedNodeId);
                relatedNodes.push({{
                    node: relatedNodeData.label,
                    rel: edgeData.rel,
                    定理: edgeData.定理
                }});
            }});
            var infoHtml = `
                <h2>${{nodeData.label}}</h2>
                <p><strong>定义:</strong> ${{nodeData.desc}}</p>
                <p><strong>相关节点:</strong></p>
                <ul>
                    ${{relatedNodes.map(function(relatedNode) {{
                        return `<li>${{relatedNode.node}}: 关系: ${{relatedNode.rel}} ${{relatedNode.定理 ? '定理: ' + relatedNode.定理 : ''}}</li>`;
                    }}).join('')}}
                </ul>
            `;
            infoPanel.innerHTML = infoHtml;
            infoPanel.style.display = 'block';  // 显示信息面板
        }} else {{

            // 隐藏右侧信息面板
            infoPanel.style.display = 'none';
        }}
    }});

    // 层级选择更新函数
    window.updateNodeVisibility = function() {{
        var selectedLevels = Array.from(document.querySelectorAll('input[name="level"]:checked')).map(function(checkbox) {{
            return parseInt(checkbox.value);
        }});
        data.nodes.forEach(function(node) {{
            var nodeData = data.nodes.get(node.id);
            if (selectedLevels.includes(nodeData.level)) {{
                data.nodes.update({{id: node.id, hidden: false}});
            }} else {{
                data.nodes.update({{id: node.id, hidden: true}});
            }}
        }});
        network.stabilize(100);
        network.fit();
    }};
}});
</script>
'''

    # 追加 JavaScript 到 HTML 文件 - 完全按照目标文件的方式
    with open(output_path, 'a', encoding='utf-8') as f:
        f.write(html_script)

    print(f"知识图谱已生成: {output_path}")

if __name__ == "__main__":
    # 示例使用
    print("=== 知识图谱生成器 ===")
    print("请输入要加载的主题（用逗号分隔，例如: 微分学,傅里叶）")

    user_input = input("主题: ").strip()

    if user_input:
        titles = [title.strip() for title in user_input.split(',')]
        output_file = input("输出文件名 (默认: knowledge_graph.html): ").strip()
        output_dir = input("输出目录 (默认: output): ").strip()

        if not output_file:
            output_file = "knowledge_graph.html"

        if not output_dir:
            output_dir = "output"

        create_knowledge_graph(titles, output_file, output_dir)
    else:
        print("未输入任何主题，使用示例数据...")
        titles = ["微分学"]
        create_knowledge_graph(titles)
