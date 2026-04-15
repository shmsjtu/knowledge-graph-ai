#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from pathlib import Path

from pyvis.network import Network


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DEFAULT_TOPICS = ["复分析", "数学分析II"]

RELATION_COLORS = {
    "层级包含": "#F5B721",
    "数学包含": "#D4A017",
    "具有性质": "#8CC78A",
    "具有实例": "#0000FF",
    "充分递推": "#00A5B1",
    "必要递推": "#00A5B1",
    "充要递推": "#FF8983",
    "部分递推": "#00A5B1",
    "对偶": "#53B5FF",
    "推广": "#FFA500",
    "关联": "#7A7A7A",
}

LEVEL_SIZE_MAP = {
    0: 50,
    1: 25,
    2: 17,
    3: 11,
    4: 5,
}

LEVEL_LABELS = {
    0: "核心知识点",
    1: "主要知识点",
    2: "定义",
    3: "性质/定理",
    4: "实例",
}

SIGNATURE_INFO = {
    "复分析": {
        "制作者": "孙浩民",
        "设计者": "孙浩民",
        "参考文献": "《复变函数》余家荣",
        "合作者": "杜健豪、林子绚、吴铭迪、唐博宇",
        "制作时间": "2026年4月",
        "版本号": "V1.0",
    },
    "数学分析II": {
        "制作者": "孙浩民",
        "设计者": "孙浩民",
        "参考文献": "上海交通大学张永甲老师的授课讲义",
        "合作者": "杜健豪、林子绚、吴铭迪、唐博宇",
        "制作时间": "2026年4月",
        "版本号": "V1.0",
    },
}

DIRECTED_RELATIONS = {
    "层级包含",
    "数学包含",
    "具有性质",
    "具有实例",
    "充分递推",
    "必要递推",
    "部分递推",
    "推广",
}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_topic_graph(topic: str):
    material_dir = ROOT / "material" / topic
    nodes_path = material_dir / f"{topic}_nodes.json"
    relations_path = material_dir / f"{topic}_relations.json"

    raw_nodes = read_json(nodes_path)
    raw_relations = read_json(relations_path)

    nodes = []
    for item in raw_nodes:
        if isinstance(item, list) and len(item) == 2 and isinstance(item[1], dict):
            name, data = item
            nodes.append(
                {
                    "id": name,
                    "label": name,
                    "desc": data.get("desc", ""),
                    "level": int(data.get("level", 2)),
                    "color": data.get("color", "#FFFF00"),
                }
            )

    node_ids = {node["id"] for node in nodes}
    relations = []
    for item in raw_relations:
        if not (isinstance(item, list) and len(item) == 3 and isinstance(item[2], dict)):
            continue
        source, target, data = item
        if source not in node_ids or target not in node_ids or source == target:
            continue
        rel = data.get("rel", "关联")
        relations.append(
            {
                "from": source,
                "to": target,
                "rel": rel,
                "定理": data.get("定理", ""),
                "color": data.get("color") or RELATION_COLORS.get(rel, "#888888"),
            }
        )

    return nodes, relations


def build_network(nodes, relations):
    net = Network(
        notebook=False,
        directed=True,
        height="900px",
        width="100%",
        bgcolor="#e6f3ff",
        font_color="#333333",
    )

    for node in nodes:
        net.add_node(
            node["id"],
            label=node["label"],
            title=f'{node["label"]}\n{node["desc"]}',
            color=node["color"],
            size=LEVEL_SIZE_MAP.get(node["level"], 17),
            desc=node["desc"],
            level=node["level"],
        )

    for edge in relations:
        arrows = "to" if edge["rel"] in DIRECTED_RELATIONS else "to,from"
        theorem = edge["定理"] or "未提供说明"
        net.add_edge(
            edge["from"],
            edge["to"],
            title=f'关系: {edge["rel"]}\n说明: {theorem}',
            color=edge["color"],
            rel=edge["rel"],
            定理=edge["定理"],
            arrows=arrows,
        )

    net.set_options(
        """
var options = {
  "nodes": {
    "shape": "dot",
    "font": {"size": 24},
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
    "tooltipDelay": 200,
    "navigationButtons": true,
    "keyboard": true
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -220000,
      "springLength": 155,
      "springConstant": 0.035,
      "damping": 0.11
    },
    "stabilization": {
      "iterations": 1200,
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
"""
    )
    return net


def build_custom_script(topic: str, nodes, relations):
    relation_colors = {}
    for edge in relations:
        relation_colors.setdefault(edge["rel"], edge["color"])
    signature_info = SIGNATURE_INFO.get(
        topic,
        {
            "制作者": "孙浩民",
            "设计者": "孙浩民",
            "参考文献": "待补充",
            "合作者": "杜健豪、林子绚、吴铭迪、唐博宇",
            "制作时间": "2026年4月",
            "版本号": "V1.0",
        },
    )

    return f"""
<script type="text/javascript">
document.addEventListener("DOMContentLoaded", function() {{
    var container = document.getElementById("mynetwork");
    if (!container || typeof network === "undefined" || typeof nodes === "undefined" || typeof edges === "undefined") {{
        return;
    }}

    document.title = {json.dumps(topic + " 知识图谱", ensure_ascii=False)};
    document.body.style.margin = "0";
    document.body.style.fontFamily = "Arial, sans-serif";
    container.style.position = "absolute";
    container.style.left = "0";
    container.style.top = "0";
    container.style.width = "72%";
    container.style.height = "100vh";

    var infoPanel = document.createElement("div");
    infoPanel.id = "infoPanel";
    infoPanel.style.position = "absolute";
    infoPanel.style.right = "0";
    infoPanel.style.top = "0";
    infoPanel.style.width = "28%";
    infoPanel.style.height = "100vh";
    infoPanel.style.backgroundColor = "#f9f9f9";
    infoPanel.style.padding = "18px";
    infoPanel.style.boxSizing = "border-box";
    infoPanel.style.boxShadow = "-2px 0 8px rgba(0,0,0,0.12)";
    infoPanel.style.overflowY = "auto";
    infoPanel.innerHTML = "<h2 style='margin-top:0;'>{topic}</h2><p>点击节点可查看定义与相邻关系。</p>";
    document.body.appendChild(infoPanel);

    var legend = document.createElement("div");
    legend.id = "legend";
    legend.style.position = "fixed";
    legend.style.left = "12px";
    legend.style.bottom = "12px";
    legend.style.width = "285px";
    legend.style.maxHeight = "72vh";
    legend.style.overflowY = "auto";
    legend.style.backgroundColor = "rgba(249,249,249,0.96)";
    legend.style.padding = "12px";
    legend.style.borderRadius = "8px";
    legend.style.boxShadow = "0 2px 8px rgba(0,0,0,0.16)";
    legend.style.zIndex = "1000";
    legend.style.fontSize = "12px";
    legend.style.lineHeight = "1.45";
    document.body.appendChild(legend);

    var titleTag = document.createElement("div");
    titleTag.style.position = "fixed";
    titleTag.style.left = "12px";
    titleTag.style.top = "12px";
    titleTag.style.backgroundColor = "rgba(255,255,255,0.92)";
    titleTag.style.padding = "8px 12px";
    titleTag.style.borderRadius = "8px";
    titleTag.style.boxShadow = "0 2px 8px rgba(0,0,0,0.12)";
    titleTag.style.zIndex = "1000";
    titleTag.style.fontWeight = "bold";
    titleTag.textContent = {json.dumps(topic + " 知识图谱", ensure_ascii=False)};
    document.body.appendChild(titleTag);

    var signatureDiv = document.createElement("div");
    signatureDiv.id = "signature";
    signatureDiv.style.position = "fixed";
    signatureDiv.style.bottom = "0";
    signatureDiv.style.right = "0";
    signatureDiv.style.backgroundColor = "rgba(0,0,0,0.32)";
    signatureDiv.style.color = "white";
    signatureDiv.style.padding = "6px 8px";
    signatureDiv.style.fontSize = "10px";
    signatureDiv.style.borderTopLeftRadius = "6px";
    signatureDiv.style.zIndex = "1000";
    signatureDiv.style.fontFamily = "sans-serif";
    signatureDiv.style.lineHeight = "1.35";
    signatureDiv.innerHTML = `
        制作者：{signature_info["制作者"]}<br>
        设计者：{signature_info["设计者"]}<br>
        参考文献：{signature_info["参考文献"]}<br>
        合作者：{signature_info["合作者"]}<br>
        制作时间：{signature_info["制作时间"]}<br>
        版本号：{signature_info["版本号"]}
    `;
    document.body.appendChild(signatureDiv);

    var relationColors = {json.dumps(relation_colors, ensure_ascii=False)};
    var levelLabels = {json.dumps(LEVEL_LABELS, ensure_ascii=False)};
    var nodeRecords = {json.dumps(nodes, ensure_ascii=False)};

    function visibleNodeIds() {{
        return new Set(nodes.get().filter(function(node) {{ return !node.hidden; }}).map(function(node) {{ return node.id; }}));
    }}

    function countRelationsByType() {{
        var counts = {{}};
        edges.get().forEach(function(edge) {{
            counts[edge.rel] = (counts[edge.rel] || 0) + 1;
        }});
        return counts;
    }}

    function countNodesByLevel() {{
        var counts = {{}};
        nodeRecords.forEach(function(node) {{
            counts[node.level] = (counts[node.level] || 0) + 1;
        }});
        return counts;
    }}

    function refreshLegend() {{
        var levelCounts = countNodesByLevel();
        var relationCounts = countRelationsByType();
        var levelItems = Object.keys(levelLabels).map(function(level) {{
            var checked = true;
            return "<label style='display:block;margin:2px 0;'><input type='checkbox' name='level-filter' value='" + level + "' " + (checked ? "checked" : "") + "> " + levelLabels[level] + " (节点数: " + (levelCounts[level] || 0) + ")</label>";
        }}).join("");

        var relationItems = Object.keys(relationColors).sort().map(function(rel) {{
            return "<div style='margin:2px 0;'><span style='color:" + relationColors[rel] + ";'>■</span> " + rel + " (" + (relationCounts[rel] || 0) + ")</div>";
        }}).join("");

        legend.innerHTML =
            "<div style='font-weight:bold;margin-bottom:6px;'>{topic}</div>" +
            "<div style='margin-bottom:8px;'>总节点数: " + nodeRecords.length + "<br>总关系数: " + edges.length + "</div>" +
            "<div style='margin-bottom:8px;'><div style='font-weight:bold;'>层级筛选</div>" + levelItems + "<button id='apply-level-filter' style='margin-top:6px;'>更新显示</button></div>" +
            "<div><div style='font-weight:bold;margin-bottom:4px;'>关系图例</div>" + relationItems + "</div>";
    }}

    function applyLevelFilter() {{
        var selectedLevels = Array.from(document.querySelectorAll("input[name='level-filter']:checked")).map(function(item) {{
            return parseInt(item.value, 10);
        }});
        var selectedSet = new Set(selectedLevels);
        nodes.get().forEach(function(node) {{
            nodes.update({{ id: node.id, hidden: !selectedSet.has(node.level) }});
        }});
        network.stabilize(120);
        network.fit();
    }}

    refreshLegend();
    document.getElementById("apply-level-filter").addEventListener("click", applyLevelFilter);

    network.on("click", function(params) {{
        if (!params.nodes.length) {{
            infoPanel.innerHTML = "<h2 style='margin-top:0;'>{topic}</h2><p>点击节点可查看定义与相邻关系。</p>";
            return;
        }}

        var nodeId = params.nodes[0];
        var nodeData = nodes.get(nodeId);
        var connectedEdgeIds = network.getConnectedEdges(nodeId);
        var relationItems = connectedEdgeIds.map(function(edgeId) {{
            var edge = edges.get(edgeId);
            var relatedNodeId = edge.from === nodeId ? edge.to : edge.from;
            var relatedNode = nodes.get(relatedNodeId);
            if (!relatedNode) {{
                return "";
            }}
            var explain = edge["定理"] ? "，说明：" + edge["定理"] : "";
            return "<li><strong>" + relatedNode.label + "</strong>，关系：" + edge.rel + explain + "</li>";
        }}).filter(Boolean).join("");

        infoPanel.innerHTML =
            "<h2 style='margin-top:0;'>" + nodeData.label + "</h2>" +
            "<p><strong>层级：</strong>" + (levelLabels[nodeData.level] || nodeData.level) + "</p>" +
            "<p><strong>定义：</strong>" + (nodeData.desc || "无描述") + "</p>" +
            "<p><strong>相关节点：</strong></p>" +
            "<ul style='padding-left:18px;'>" + (relationItems || "<li>暂无相邻关系</li>") + "</ul>";
    }});
}});
</script>
"""


def inject_script(html: str, script: str):
    if "</body>" in html:
        return html.replace("</body>", script + "\n</body>")
    return html + script


def generate_topic_html(topic: str):
    nodes, relations = load_topic_graph(topic)
    if not nodes:
        raise ValueError(f"{topic} 没有可用节点数据")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    network = build_network(nodes, relations)
    html = network.generate_html()
    html = inject_script(html, build_custom_script(topic, nodes, relations))

    output_path = OUTPUT_DIR / f"{topic}.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"已生成: {output_path}")


def main():
    for topic in DEFAULT_TOPICS:
        generate_topic_html(topic)


if __name__ == "__main__":
    main()
