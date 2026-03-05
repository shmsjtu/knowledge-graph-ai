import os
import json
from pyvis.network import Network

def load_json_file(file_path):
    """加载JSON文件并返回字典"""
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
    """合并多个主题的节点数据"""
    all_nodes = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for title in titles:
        nodes_path = os.path.join(current_dir, "material", title, f"{title}_nodes.json")
        nodes_data = load_json_file(nodes_path)
        
        if isinstance(nodes_data, list):
            all_nodes.extend(nodes_data)
        else:
            print(f"警告: {title}_nodes.json 不是列表格式")
    
    return all_nodes

def merge_relations(titles):
    """合并多个主题的关系数据"""
    all_relations = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for title in titles:
        relations_path = os.path.join(current_dir, "material", title, f"{title}_relations.json")
        relations_data = load_json_file(relations_path)
        
        if isinstance(relations_data, list):
            all_relations.extend(relations_data)
        else:
            print(f"警告: {title}_relations.json 不是列表格式")
    
    return all_relations

def get_node_color(classification):
    """根据节点分类返回颜色"""
    color_map = {
        "核心知识点": "#FF0000",
        "主要知识点": "#FFA500",
        "基本定义": "#FFFF00",
        "性质定理": "#008000",
        "具体实例": "#0000FF"
    }
    return color_map.get(classification, "#808080")

def get_edge_color(relation):
    """根据关系类型返回颜色"""
    color_map = {
        "包含": "#F5B721",
        "性质": "#8cc78a",
        "属性": "#8cc78a",
        "递推": "#00a5b1",
        "充分递推": "#00a5b1",
        "必要递推": "#00a5b1",
        "充要递推": "#00a5b1",
        "部分递推": "#00a5b1",
        "对应": "#53B5FF",
        "互斥": "#007665",
        "等价": "#ff8983"
    }
    return color_map.get(relation, "#808080")

def assign_levels(nodes, relations, max_level=4):
    """根据节点连接的关系数分配层级"""
    node_map = {node["name"]: idx for idx, node in enumerate(nodes)}
    degrees = [0] * len(nodes)
    
    for relation in relations:
        obj_a = relation.get("object_a")
        obj_b = relation.get("object_b")
        
        if obj_a in node_map:
            degrees[node_map[obj_a]] += 1
        if obj_b in node_map:
            degrees[node_map[obj_b]] += 1
    
    if not degrees:
        return []
    
    max_degree = max(degrees)
    if max_degree == 0:
        return [0] * len(nodes)
    
    # 将连接数映射到有限层级，层级越高表示连接越多
    return [
        int(round((degree / max_degree) * max_level))
        for degree in degrees
    ]

def create_knowledge_graph(titles, output_file="knowledge_graph.html", output_dir="output"):
    """创建知识图谱"""
    print(f"正在处理主题: {', '.join(titles)}")
    
    # 确保输出目录存在
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建完整的输出路径
    output_path = os.path.join(current_dir,output_dir,output_file)
    
    # 加载并合并数据
    nodes = merge_nodes(titles)
    relations = merge_relations(titles)
    
    print(f"总节点数: {len(nodes)}")
    print(f"总关系数: {len(relations)}")
    
    if not nodes:
        print("错误: 没有找到任何节点数据")
        return
    
    # 分配层级
    levels = assign_levels(nodes, relations)
    
    # 创建网络图
    net = Network(notebook=True,height="100vh", width="100%", directed=True, bgcolor="#ffffff")
    
    # 创建节点名称集合，用于验证关系
    node_names = set()
    
    # 添加节点
    for idx, node in enumerate(nodes):
        name = node.get("name", "未命名")
        desc = node.get("desc", "无描述")
        classification = node.get("classification", "其他")
        theme = node.get("theme", "")
        level = levels[idx] if levels else 0
        size = 18 + level * 6
        
        # 将节点名称添加到集合中
        node_names.add(name)
        
        color = get_node_color(classification)
        
        # 创建节点标题（悬停时显示）
        title = f"<b>{name}</b><br>分类: {classification}<br>主题: {theme}<br>描述: {desc}"
        
        net.add_node(
            name,
            label=name,
            title=title,
            color=color,
            level=level,
            desc=desc,
            classification=classification,
            theme=theme,
            size=size
        )
    
    # 添加边（增加鲁棒性检查）
    skipped_relations = 0
    added_relations = 0
    
    for relation in relations:
        obj_a = relation.get("object_a")
        obj_b = relation.get("object_b")
        rel_type = relation.get("relation", "未知关系")
        explanation = relation.get("explanation", "")
        
        # 检查节点是否存在
        if not obj_a or not obj_b:
            skipped_relations += 1
            continue
        
        if obj_a not in node_names:
            print(f"警告: 关系中的节点 '{obj_a}' 不存在，跳过该关系")
            skipped_relations += 1
            continue
        
        if obj_b not in node_names:
            print(f"警告: 关系中的节点 '{obj_b}' 不存在，跳过该关系")
            skipped_relations += 1
            continue

        if obj_a == obj_b:
            print(f"警告: 关系中的节点 '{obj_a}' 和 '{obj_b}' 相同，跳过该关系")
            skipped_relations += 1
            continue
        
        # 两个节点都存在，添加边
        color = get_edge_color(rel_type)
        title = f"{rel_type}: {explanation}" if explanation else rel_type
        
        net.add_edge(
            obj_a,
            obj_b,
            title=title,
            color=color,
            rel=rel_type,
            定理=explanation
        )
        added_relations += 1
    
    # 输出统计信息
    print(f"成功添加关系: {added_relations}")
    if skipped_relations > 0:
        print(f"跳过的关系: {skipped_relations} (节点不存在)")
    
    # 配置2D可视化选项
    net.set_options('''
    var options = {
        "nodes": {
            "shape": "dot",
            "size": 16,
            "font": {"size": 16},
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
                "gravitationalConstant": -9000,
                "springLength": 220,
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
    
    """
    # 生成HTML
    html_content = net.generate_html()
    
    # 添加自定义JavaScript
    custom_js = generate_custom_js(net)
    html_content = html_content.replace('</body>', f'{custom_js}</body>')
    
    # 保存文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"知识图谱已生成: {output_path}")
    """
    net.show(output_path) 

def generate_custom_js(net):
    """生成自定义JavaScript代码"""
    return f'''
<script type="text/javascript">
document.addEventListener("DOMContentLoaded", function() {{
    // 调整主容器样式
    var container = document.getElementById('mynetwork');
    container.style.width = '70%';
    container.style.height = '100%';
    container.style.position = 'absolute';
    container.style.left = '0';
    container.style.top = '0';
    
    // 创建右侧信息面板
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
    
    // 创建图例容器
    var legend = document.createElement('div');
    legend.id = 'legend';
    legend.style.position = 'absolute';
    legend.style.left = '10px';
    legend.style.bottom = '20px';
    legend.style.width = '250px';
    legend.style.backgroundColor = '#f9f9f9';
    legend.style.padding = '10px';
    legend.style.boxShadow = '2px 2px 5px rgba(0,0,0,0.1)';
    legend.style.borderRadius = '5px';
    legend.style.zIndex = '1000';
    legend.style.fontSize = '12px';
    legend.style.lineHeight = '1.4';
    document.body.appendChild(legend);
    
    // 图例内容
    var legendHTML = `
        <div style="margin-bottom: 10px;">
            <strong>节点颜色</strong><br>
            <span style="color:#FF0000">■</span> 核心知识点<br>
            <span style="color:#FFA500">■</span> 主要知识点<br>
            <span style="color:#FFFF00">■</span> 基本定义<br>
            <span style="color:#008000">■</span> 性质定理<br>
            <span style="color:#0000FF">■</span> 具体实例
        </div>
        <div>
            <strong>关系颜色</strong><br>
            <span style="color:#F5B721">■</span> 包含<br>
            <span style="color:#8cc78a">■</span> 性质/属性<br>
            <span style="color:#00a5b1">■</span> 递推<br>
            <span style="color:#53B5FF">■</span> 对应<br>
            <span style="color:#007665">■</span> 互斥<br>
            <span style="color:#ff8983">■</span> 等价
        </div>
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
            <button onclick="resetView()" style="width: 100%; padding: 5px; cursor: pointer;">
                重置视图
            </button>
        </div>
    `;
    legend.innerHTML = legendHTML;
    
    // 获取网络对象（pyvis创建的）
    var network = window.network;
    
    // 点击节点显示详细信息
    network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
            var nodeId = params.nodes[0];
            var nodeData = network.body.data.nodes.get(nodeId);
            
            // 获取连接的边和节点
            var connectedEdges = network.getConnectedEdges(nodeId);
            var connectedNodes = network.getConnectedNodes(nodeId);
            
            var relatedInfo = [];
            connectedEdges.forEach(function(edgeId) {{
                var edge = network.body.data.edges.get(edgeId);
                var otherNodeId = edge.from === nodeId ? edge.to : edge.from;
                var otherNode = network.body.data.nodes.get(otherNodeId);
                
                relatedInfo.push({{
                    node: otherNode.label,
                    relation: edge.rel || '未知',
                    explanation: edge.定理 || ''
                }});
            }});
            
            var infoHTML = `
                <h2 style="margin-top: 0;">${{nodeData.label}}</h2>
                <p><strong>分类:</strong> ${{nodeData.classification || '未分类'}}</p>
                <p><strong>主题:</strong> ${{nodeData.theme || '无'}}</p>
                <p><strong>描述:</strong> ${{nodeData.desc || '无描述'}}</p>
                <hr>
                <h3>相关节点 (${{relatedInfo.length}})</h3>
                <ul style="padding-left: 20px;">
                    ${{relatedInfo.map(function(info) {{
                        return '<li><strong>' + info.node + '</strong><br>' +
                               '关系: ' + info.relation + 
                               (info.explanation ? '<br>说明: ' + info.explanation : '') +
                               '</li>';
                    }}).join('')}}
                </ul>
            `;
            
            infoPanel.innerHTML = infoHTML;
            infoPanel.style.display = 'block';
        }} else {{
            infoPanel.style.display = 'none';
        }}
    }});
    
    // 重置视图函数
    window.resetView = function() {{
        network.fit();
        infoPanel.style.display = 'none';
    }};
}});
</script>
'''


def test_simple_graph():
    """创建一个简单的测试图谱"""
    net = Network(notebook=True,height="100vh", width="100%", directed=True, bgcolor="#ffffff")
    
    # 添加测试节点
    net.add_node("节点1", label="节点1", color="#FF0000", size=25)
    net.add_node("节点2", label="节点2", color="#00FF00", size=25)
    net.add_node("节点3", label="节点3", color="#0000FF", size=25)
    
    # 添加测试边
    net.add_edge("节点1", "节点2")
    net.add_edge("节点2", "节点3")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建完整的输出路径
    output_path = os.path.join(current_dir,"test_graph.html")
    net.show(output_path)
    print("测试图谱已生成: test_graph.html")

if __name__ == "__main__":
    # 示例使用
    print("=== 知识图谱生成器 ===")
    print("请输入要加载的主题（用逗号分隔，例如: 线性代数,微积分）")
    
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
        # 示例：如果没有输入，可以使用默认主题
        titles = ["线性代数"]  # 修改为你的默认主题
        create_knowledge_graph(titles)