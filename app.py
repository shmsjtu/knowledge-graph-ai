"""
知识图谱 AI 助手 —— 统一 Streamlit 应用

功能页：
  A. 知识图谱生成：文本清洗 → 节点提取 → 关系提取 → 图谱微调
  B. 图谱查看与编辑：交互式可视化 + 节点/关系增删改 + AI 智能补全
"""

import streamlit as st
import json
import os
import sys
import random
import threading
import networkx as nx
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 确保 new_Lib 可被 import（app.py 与 new_Lib/ 同级）
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import new_Lib.new_prompt as prompt
import new_Lib as utils

# ─────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
ENDPOINT = os.getenv("DEEPSEEK_API_ENDPOINT", "https://api.deepseek.com")

PIPELINE_DEFAULTS = {
    "threshold": 0.7,
    "batch_num": 3,
    "max_dynamic_rounds": 5,
    "weak_degree_threshold": 1,
    "candidate_theme_limit": 3,
    "candidate_pool_size": 12,
    "candidate_top_k": 4,
    "max_targets_per_round": 5,
    "context_char_limit": 2000,
}

AI_SYSTEM_PROMPT = """
你是一个精通数学的知识图谱构建助手。你的任务是判断两个数学概念（节点A -> 节点B）之间的逻辑关系。

请严格基于以下定义的11种关系类别进行分类（严禁创造新类别）：
1. 层级包含：目录结构上的包含，或B是A的子类。
2. 数学包含：集合论意义上的包含，A ⊇ B 或 B ∈ A。
3. 具有性质：B是A的性质，或B是描述A的公式/定理。
4. 具有实例：B是A的具体例子。
5. 充分递推：A是B的充分条件。
6. 必要递推：A是B的必要条件/基础/前提。
7. 充要递推：A ↔ B，等价或一一对应。
8. 部分递推：A是B的工具/方法，或A决定B的性质/存在性。
9. 对偶：A与B结构对称互补。
10. 推广：B是A的高维/一般化/抽象化形式。
11. 关联：结构相似或有交叉，但不符合上述任一强逻辑关系。

输出要求：仅输出标准 JSON 格式，不含markdown标记：
{"rel_name": "上述11个类别中的一个", "explan": "选择该关系类别的理由"}
"""

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def get_material_dir(title: str) -> str:
    return os.path.join(_ROOT, "material", title)


def list_topics() -> list:
    """扫描 material/ 目录，返回所有已有主题列表"""
    mat_dir = os.path.join(_ROOT, "material")
    if not os.path.isdir(mat_dir):
        return []
    return [d for d in os.listdir(mat_dir) if os.path.isdir(os.path.join(mat_dir, d))]


def load_graph_data(nodes_path: str, relations_path: str):
    raw_nodes = utils.load_from_json(nodes_path) or []
    raw_rels = utils.load_from_json(relations_path) or []

    # 节点去重：避免 agraph 因重复 id 报错
    node_map = {}

    # Handle both old dict format and new tuple format
    for n in raw_nodes:
        # Check if it's new tuple format: (name, data_dict)
        if isinstance(n, (list, tuple)) and len(n) == 2:
            name = n[0]
            node_data = n[1]
        # Old dict format
        elif isinstance(n, dict):
            name = n.get("name")
            node_data = n
        else:
            continue

        if not name:
            continue
        # 保留第一次出现，避免同名节点覆盖
        if name not in node_map:
            node_map[name] = node_data

    nodes = [{"name": name, **data} for name, data in node_map.items()]
    valid_node_names = set(node_map.keys())

    # 兼容两种关系格式：
    # - 新格式: tuple/list [node_a, node_b, {"rel": ..., "定理": ...}]
    # - 旧格式: dict with object_a/object_b/relation/explanation
    rels = []
    for r in raw_rels:
        # Check if it's new tuple format
        if isinstance(r, (list, tuple)) and len(r) == 3:
            obj_a = r[0]
            obj_b = r[1]
            rel_data = r[2]
            rel_name = rel_data.get("rel", "")
            explan = rel_data.get("定理", "")
        # Old dict format
        elif isinstance(r, dict):
            obj_a = r.get("obj_a", r.get("object_a", ""))
            obj_b = r.get("obj_b", r.get("object_b", ""))
            rel_name = r.get("rel_name", r.get("relation", ""))
            explan = r.get("explan", r.get("explanation", ""))
        else:
            continue

        # 过滤无效关系，避免图渲染阶段异常
        if not obj_a or not obj_b:
            continue
        if obj_a not in valid_node_names or obj_b not in valid_node_names:
            continue
        rels.append({
            "obj_a": obj_a,
            "obj_b": obj_b,
            "rel_name": rel_name,
            "explan": explan,
        })
    return nodes, rels


def save_graph_data(nodes, rels, nodes_path: str, relations_path: str):
    # Save nodes in new tuple format
    nodes_new_format = []
    for n in nodes:
        if isinstance(n, dict):
            name = n.get("name", "未命名")
            desc = n.get("desc", "")
            classification = n.get("classification", "定义")

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

            nodes_new_format.append([name, {
                "desc": desc,
                "level": level,
                "color": color
            }])

    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes_new_format, f, indent=2, ensure_ascii=False)

    # Save relations in new tuple format
    rels_new_format = []
    for r in rels:
        obj_a = r.get("object_a", r.get("obj_a", ""))
        obj_b = r.get("object_b", r.get("obj_b", ""))
        rel_name = r.get("relation", r.get("rel_name", ""))
        explan = r.get("explanation", r.get("explan", ""))

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
            "等价": "#ff8983"
        }
        color = rel_colors.get(rel_name, "#888888")

        rels_new_format.append([obj_a, obj_b, {
            "rel": rel_name,
            "定理": explan,
            "color": color
        }])

    with open(relations_path, 'w', encoding='utf-8') as f:
        json.dump(rels_new_format, f, indent=2, ensure_ascii=False)


def get_relation_prediction(client: OpenAI, node_a: str, desc_a: str,
                            node_b: str, desc_b: str) -> dict:
    user_content = f"对象 A: {node_a}\n描述 A: {desc_a}\n\n对象 B: {node_b}\n描述 B: {desc_b}"
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={'type': 'json_object'},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"rel_name": "API Error", "explan": str(e)}


# ─────────────────────────────────────────────
# Pipeline 步骤函数（用于页面 A）
# ─────────────────────────────────────────────

def run_step1_clean(title: str, status_container) -> bool:
    """步骤1：从原始 Markdown 清洗提炼各章节内容"""
    current_dir = _ROOT
    main_file = os.path.join(current_dir, "material", title, title + ".md")

    if not os.path.exists(main_file):
        status_container.error(f"找不到文件：{main_file}")
        return False

    status_container.write(f"正在读取：{main_file}")
    full_content = utils.markdown_to_string_path(main_file)

    sections = utils.split_by_section_marker(full_content)
    material_dir = os.path.join(current_dir, "material", title)
    status_container.write(f"按 `## §` 拆分为 {len(sections)} 个章节，开始 LLM 清洗…")

    for idx, section_content in enumerate(sections):
        raw_path = os.path.join(material_dir, f"raw_{idx}.md")
        utils.string_to_markdown_path(section_content, raw_path, overwrite=True)

        subsections = utils.split_by_subsection(section_content)
        processed_parts = []
        MIN_LEN, MAX_RETRY = 100, 5

        for sub_idx, (sub_title, sub_content) in enumerate(subsections):
            status_container.write(
                f"  章节 {idx + 1}/{len(sections)} · 小节 {sub_idx + 1}/{len(subsections)}"
            )
            processed = None
            for _ in range(MAX_RETRY):
                msgs = prompt.build_prompt_clear(text=sub_content)
                resp = utils.ask_deepseek(msgs, API_KEY, ENDPOINT, modell="reasoner", max_tokens=16384)
                if resp and len(resp.strip()) >= MIN_LEN:
                    processed = resp.replace("```", "").replace("markdown", "")
                    break
            if not processed:
                processed = sub_content
            processed_parts.append((sub_title + "\n" + processed) if sub_title else processed)

        final = "\n\n".join(processed_parts)
        sub_path = os.path.join(material_dir, f"{title}_subsection{idx}.md")
        utils.string_to_markdown_path(final, sub_path, overwrite=True)
        status_container.write(f"  ✓ 已保存：{title}_subsection{idx}.md")

    status_container.success(f"步骤1完成，共处理 {len(sections)} 个章节。")
    return True


def run_step2_nodes(title: str, num_subsections: int, status_container) -> bool:
    """步骤2：从 subsection 文件提取知识节点"""
    current_dir = _ROOT
    textt = []
    for i in range(num_subsections):
        fpath = os.path.join(current_dir, "material", title, f"{title}_subsection{i}.md")
        try:
            textt.append(utils.markdown_to_string_path(fpath))
        except Exception as e:
            status_container.warning(f"读取 subsection{i} 失败：{e}")

    if not textt:
        status_container.error("无法读取任何 subsection 文件。")
        return False

    _, examples, _, _, _ = utils.classify_text(textt)
    save_path = os.path.join(current_dir, "material", title, f"{title}_nodes.json")
    status_container.write(f"分类完成，例子类共 {len(examples)} 项，开始逐项提取节点…")

    results_ex = []
    for i, (text, sub_title, related_theme) in enumerate(examples):
        status_container.write(f"  提取例子节点 {i + 1}/{len(examples)}…")
        texts = f"**{sub_title}:** {text}\n\n"
        msgs = prompt.build_prompt_ex(related_theme=related_theme, text=texts)
        raw = utils.ask_deepseek(msgs, API_KEY, ENDPOINT, modell="chat")
        try:
            results_ex = utils.parse_answers_2(raw, related_theme, texts=texts)
        except Exception as e:
            status_container.warning(f"解析失败：{e}")
        utils.save_to_json(results_ex, save_path, indent=4)

    nodes = utils.load_from_json(save_path) or []
    status_container.success(f"步骤2完成，共提取 {len(nodes)} 个节点，已保存至：{save_path}")
    return True


def run_step3_relations(title: str, num_subsections: int,
                        cfg: dict, status_container) -> bool:
    """步骤3：两阶段（骨架+动态修复）关系提取"""
    current_dir = _ROOT
    mat_dir = os.path.join(current_dir, "material", title)

    # 读取 subsection
    textt = []
    for i in range(num_subsections):
        try:
            textt.append(utils.markdown_to_string_path(
                os.path.join(mat_dir, f"{title}_subsection{i}.md")))
        except Exception:
            textt.append("")

    _, _, _, _, Theme = utils.classify_text(textt)
    if not Theme:
        status_container.error("未检测到章节主题，终止。")
        return False
    status_container.write(f"检测到章节主题：{Theme}")

    nodes_path = os.path.join(mat_dir, f"{title}_nodes.json")
    relation_path = os.path.join(mat_dir, f"{title}_relations.json")
    entities = utils.load_from_json(nodes_path)
    if not entities:
        status_container.error(f"节点文件为空或不存在：{nodes_path}")
        return False

    # 加载已有关系
    existing_relations = []
    if os.path.exists(relation_path):
        raw_rels = utils.load_from_json(relation_path) or []
        for item in raw_rels:
            existing_relations.append((
                item.get('object_a', ''), item.get('object_b', ''),
                {"rel": item.get('relation', ''), "定理": item.get('explanation', '')}
            ))

    # 构建图
    G = nx.DiGraph()
    node_lookup = {}
    for node in entities:
        name = node.get("name")
        if not name:
            continue
        node_lookup[name] = node
        G.add_node(name, **node)
    for u, v, data in existing_relations:
        if u in node_lookup and v in node_lookup:
            G.add_edge(u, v, relation=data['rel'])

    raw_text_cache = {}

    def get_raw_text(theme_val: str) -> str:
        idx = utils.get_index_from_theme(theme_val)
        if idx not in raw_text_cache:
            rp = os.path.join(mat_dir, f"raw_{idx}.md")
            try:
                raw_text_cache[idx] = utils.markdown_to_string_path(rp)
            except Exception:
                raw_text_cache[idx] = ""
        return raw_text_cache[idx]

    theme_to_entities = {t: [] for t in Theme}
    for node in entities:
        node_theme = node.get("theme", "")
        matched = False
        for t in Theme:
            if t and t in node_theme:
                theme_to_entities.setdefault(t, []).append(node)
                matched = True
                break
        if not matched:
            theme_to_entities.setdefault("UNMATCHED", []).append(node)

    def register_relations(new_rels):
        if not new_rels:
            return
        existing_relations.extend(new_rels)
        for obj_a, obj_b, meta in new_rels:
            if obj_a in node_lookup and obj_b in node_lookup:
                G.add_edge(obj_a, obj_b, relation=meta.get("rel", ""))
        utils.list_save_to_json(existing_relations, relation_path)

    def run_extraction(label, e1, e2, t1, t2, batches=cfg["batch_num"]):
        if not e1 or not t1:
            return
        local_new = []
        utils.batch_extract_relations(
            entities_1_list=e1, entities_2_list=e2 or [],
            text_1=t1, text_2=t2,
            relation_name=label,
            api_key=API_KEY, api_endpoint=ENDPOINT,
            batch_num=batches,
            existing_relations=existing_relations,
            all_new_relations=local_new
        )
        register_relations(local_new)

    # ── Phase 1：评估章节关联矩阵 ──
    status_container.write("Phase 1：评估章节关联矩阵…")
    msgs = prompt.build_prompt_evaluate(chapter_list='\n'.join(Theme))
    raw = utils.ask_deepseek(msgs, API_KEY, ENDPOINT, modell="chat")
    try:
        A = utils.convert_string_to_matrix(raw)
    except ValueError as e:
        status_container.error(f"关联矩阵解析失败：{e}")
        return False

    # 自关联提取
    for t in Theme:
        ents = [str(n) for n in theme_to_entities.get(t, [])]
        txt = get_raw_text(t)
        if ents and txt:
            status_container.write(f"  提取 {t} × {t} 关系…")
            run_extraction(f"{t} × {t}", ents, ents, txt, txt)

    # 跨章节提取（阈值过滤）
    for j in range(len(Theme)):
        for k in range(j + 1, len(Theme)):
            if A[j, k] < cfg["threshold"]:
                continue
            tj, tk = Theme[j], Theme[k]
            ej = [str(n) for n in theme_to_entities.get(tj, [])]
            ek = [str(n) for n in theme_to_entities.get(tk, [])]
            tj_txt, tk_txt = get_raw_text(tj), get_raw_text(tk)
            if ej and ek and tj_txt and tk_txt:
                status_container.write(f"  提取 {tj} × {tk} 关系…")
                run_extraction(f"{tj} × {tk}", ej, ek, tj_txt, tk_txt)

    # ── Phase 2：动态修复孤立/弱连接节点 ──
    status_container.write("Phase 2：动态修复孤立节点…")
    for round_idx in range(1, cfg["max_dynamic_rounds"] + 1):
        isolates = [n for n in G.nodes if G.degree(n) == 0]
        weak = [n for n in G.nodes if 0 < G.degree(n) <= cfg["weak_degree_threshold"]]
        comps = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
        disconnected = []
        if len(comps) > 1:
            for comp in comps[1:]:
                disconnected.extend(list(comp))

        status_container.write(
            f"  第 {round_idx}/{cfg['max_dynamic_rounds']} 轮："
            f"孤立节点={len(isolates)}, 弱连接={len(weak)}, 分支数={len(comps)}"
        )

        if not isolates and not weak and len(comps) == 1:
            status_container.write("  图谱诊断正常，结束动态修复。")
            break

        targets = list(dict.fromkeys(isolates + weak + disconnected))
        new_this_round = 0

        for node_name in targets[:cfg["max_targets_per_round"]]:
            if node_name not in G:
                continue
            node_data = G.nodes[node_name]
            theme_idx = next(
                (i for i, t in enumerate(Theme) if t and t in node_data.get("theme", "")),
                None
            )
            if theme_idx is None:
                continue

            target_text = get_raw_text(Theme[theme_idx])[:cfg["context_char_limit"]]
            scores = [(max(float(A[theme_idx, i]), float(A[i, theme_idx])), i)
                      for i in range(len(Theme))]
            scores.sort(reverse=True)
            sel_indices = [i for _, i in scores[:cfg["candidate_theme_limit"]]]
            if theme_idx not in sel_indices:
                sel_indices.insert(0, theme_idx)
            sel_indices = sel_indices[:cfg["candidate_theme_limit"]]

            pool = []
            for idx in sel_indices:
                pool.extend(theme_to_entities.get(Theme[idx], []))

            neighbours = set(G.predecessors(node_name)) | set(G.successors(node_name))
            seen = set()
            filtered = []
            for cand in pool:
                cn = cand.get("name")
                if not cn or cn == node_name or cn in neighbours or cn in seen:
                    continue
                seen.add(cn)
                filtered.append(cand)

            if not filtered:
                continue
            if len(filtered) > cfg["candidate_pool_size"]:
                filtered = random.sample(filtered, cfg["candidate_pool_size"])

            try:
                msgs = prompt.build_prompt_candidate_recall(
                    target_node=node_data, candidate_nodes=filtered,
                    top_k=cfg["candidate_top_k"],
                    target_text=target_text,
                    max_context_chars=cfg["context_char_limit"]
                )
                raw_sel = utils.ask_deepseek(msgs, API_KEY, ENDPOINT, modell="chat")
                candidate_selection = utils.parse_candidate_selection(raw_sel)
            except Exception:
                continue

            confirmed = [node_lookup[c["candidate_name"]]
                         for c in candidate_selection
                         if c.get("candidate_name") in node_lookup][:cfg["candidate_top_k"]]
            if not confirmed:
                continue

            cand_texts = []
            for cand in confirmed:
                ci = next((i for i, t in enumerate(Theme)
                           if t and t in cand.get("theme", "")), None)
                cand_texts.append(get_raw_text(Theme[ci]) if ci is not None else "")
            combined_text = "\n\n".join(t for t in cand_texts if t)[:cfg["context_char_limit"]]

            verif = []
            utils.batch_extract_relations(
                entities_1_list=[str(node_lookup[node_name])],
                entities_2_list=[str(c) for c in confirmed],
                text_1=target_text, text_2=combined_text,
                relation_name=f"{node_name} × candidates",
                api_key=API_KEY, api_endpoint=ENDPOINT,
                batch_num=1,
                existing_relations=existing_relations,
                all_new_relations=verif
            )
            if verif:
                register_relations(verif)
                new_this_round += len(verif)

        if new_this_round == 0:
            status_container.write("  本轮无新增关系，动态修复结束。")
            break

    utils.list_save_to_json(existing_relations, relation_path)
    status_container.success(
        f"步骤3完成！关系总数：{len(existing_relations)}，已保存至：{relation_path}"
    )
    return True


# ─────────────────────────────────────────────
# 页面 A：知识图谱生成
# ─────────────────────────────────────────────

def page_generate():
    st.header("知识图谱生成")
    st.caption("依次执行四个步骤，将 Markdown 教材自动转换为知识图谱 JSON 文件。")

    if not API_KEY:
        st.error("未配置 DEEPSEEK_API_KEY，请在项目根目录创建 `.env` 文件并填入 API Key。")
        return

    # ── 全局配置 ──
    with st.expander("高级参数配置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            threshold = st.number_input("关联阈值 threshold", 0.0, 1.0,
                                        PIPELINE_DEFAULTS["threshold"], 0.05)
            batch_num = st.number_input("批次数 batch_num", 1, 20,
                                        PIPELINE_DEFAULTS["batch_num"])
            max_rounds = st.number_input("动态修复最大轮数", 1, 20,
                                         PIPELINE_DEFAULTS["max_dynamic_rounds"])
        with col2:
            candidate_pool = st.number_input("候选池大小", 1, 50,
                                             PIPELINE_DEFAULTS["candidate_pool_size"])
            candidate_topk = st.number_input("候选 Top-K", 1, 20,
                                             PIPELINE_DEFAULTS["candidate_top_k"])
            max_targets = st.number_input("每轮最大目标节点数", 1, 20,
                                          PIPELINE_DEFAULTS["max_targets_per_round"])
        cfg = {**PIPELINE_DEFAULTS, "threshold": threshold, "batch_num": batch_num,
               "max_dynamic_rounds": max_rounds, "candidate_pool_size": candidate_pool,
               "candidate_top_k": candidate_topk, "max_targets_per_round": max_targets}

    st.divider()

    # ─── Step 1 ───────────────────────────────
    with st.container(border=True):
        st.subheader("步骤 1 · 文本清洗提炼")
        st.caption("读取 `material/<主题>/<主题>.md`，拆分章节后调用 LLM 清洗，"
                   "输出 `raw_i.md` 和 `<主题>_subsection_i.md`。")
        title1 = st.text_input("教材主题名称", key="s1_title",
                               placeholder="例：微分学")
        if st.button("▶ 执行步骤 1", key="btn_s1"):
            if not title1.strip():
                st.warning("请输入主题名称。")
            else:
                with st.status("步骤 1 运行中…", expanded=True) as s:
                    ok = run_step1_clean(title1.strip(), s)
                    s.update(state="complete" if ok else "error")

    # ─── Step 2 ───────────────────────────────
    with st.container(border=True):
        st.subheader("步骤 2 · 节点提取")
        st.caption("对清洗后的 subsection 文件分类，调用 LLM 提取知识节点，"
                   "输出 `<主题>_nodes.json`。")
        title2 = st.text_input("教材主题名称", key="s2_title",
                               placeholder="例：微分学")
        num2 = st.number_input("subsection 文件数量", 1, 30, 7, key="s2_num")
        if st.button("▶ 执行步骤 2", key="btn_s2"):
            if not title2.strip():
                st.warning("请输入主题名称。")
            else:
                with st.status("步骤 2 运行中…", expanded=True) as s:
                    ok = run_step2_nodes(title2.strip(), int(num2), s)
                    s.update(state="complete" if ok else "error")

    # ─── Step 3 ───────────────────────────────
    with st.container(border=True):
        st.subheader("步骤 3 · 关系提取（两阶段 + 多线程）")
        st.caption("基于章节关联矩阵提取骨架关系，再动态修复孤立节点，"
                   "输出 `<主题>_relations.json`。")
        title3 = st.text_input("教材主题名称", key="s3_title",
                               placeholder="例：微分学")
        num3 = st.number_input("subsection 文件数量", 1, 30, 7, key="s3_num")
        if st.button("▶ 执行步骤 3", key="btn_s3"):
            if not title3.strip():
                st.warning("请输入主题名称。")
            else:
                with st.status("步骤 3 运行中…", expanded=True) as s:
                    ok = run_step3_relations(title3.strip(), int(num3), cfg, s)
                    s.update(state="complete" if ok else "error")

    # ─── Step 4 ───────────────────────────────
    with st.container(border=True):
        st.subheader("步骤 4 · 图谱微调")
        st.caption("手动删除节点、清理重复关系，或调用 LLM 批量评估并删除冗余关系。")
        topics = list_topics()
        if not topics:
            st.info("暂无可用主题，请先完成步骤 1-3。")
        else:
            title4 = st.selectbox("选择主题", topics, key="s4_title")
            mat_dir4 = get_material_dir(title4)
            nodes_path4 = os.path.join(mat_dir4, f"{title4}_nodes.json")
            rels_path4 = os.path.join(mat_dir4, f"{title4}_relations.json")
            nodes4 = utils.load_from_json(nodes_path4) or []
            rels4 = utils.load_from_json(rels_path4) or []
            st.caption(f"当前：**{len(nodes4)}** 个节点 / **{len(rels4)}** 条关系")

            tab_del, tab_dup, tab_llm = st.tabs(["删除节点", "清理重复关系", "LLM 智能清洗"])

            with tab_del:
                node_name_del = st.text_input("节点名称（级联删除所有相关关系）",
                                              key="s4_del_name")
                if st.button("确认删除", key="btn_s4_del", type="primary"):
                    if node_name_del.strip():
                        ok = utils.delete_node_from_graph(
                            node_name_del.strip(), nodes_path4, rels_path4)
                        if ok:
                            st.success(f"已删除节点：{node_name_del}")
                            st.rerun()
                        else:
                            st.error("删除失败，请检查节点名称是否正确。")
                    else:
                        st.warning("节点名称不能为空。")

            with tab_dup:
                st.caption("删除 object_a 和 object_b 完全相同的重复关系。")
                if st.button("清理重复关系", key="btn_s4_dup"):
                    ok = utils.remove_duplicate_relations(rels_path4)
                    if ok:
                        st.success("重复关系已清理。")
                        st.rerun()
                    else:
                        st.error("清理失败。")

            with tab_llm:
                st.caption("调用 LLM 批量评估关系，对建议删除的关系进行人工确认。")
                if "llm_eval_results" not in st.session_state:
                    st.session_state.llm_eval_results = None
                    st.session_state.llm_eval_title = None

                if st.button("启动 LLM 关系评估", key="btn_s4_llm"):
                    all_rels = utils.load_from_json(rels_path4) or []
                    all_nodes = utils.load_from_json(nodes_path4) or []
                    node_lookup = {n['name']: n for n in all_nodes if 'name' in n}
                    BATCH = 5
                    results = []
                    progress = st.progress(0)
                    total = len(all_rels)
                    for i in range(0, total, BATCH):
                        batch = all_rels[i:i + BATCH]
                        msgs = prompt.build_prompt_evaluate_relations_batch(
                            batch, node_lookup)
                        response = utils.ask_deepseek(
                            msgs, API_KEY, ENDPOINT, modell="chat")
                        eval_res = utils.parse_evaluation_batch_response(response)
                        eval_map = {item.get('id'): item for item in eval_res
                                    if item.get('id') is not None}
                        for j, rel in enumerate(batch):
                            res = eval_map.get(j, {})
                            results.append({
                                "rel": rel,
                                "suggest_removal": res.get("suggest_removal", False),
                                "reason": res.get("reason", ""),
                                "score": res.get("score", 10),
                                "keep": True
                            })
                        progress.progress(min((i + BATCH) / total, 1.0))
                    st.session_state.llm_eval_results = results
                    st.session_state.llm_eval_title = title4
                    st.rerun()

                if st.session_state.llm_eval_results is not None:
                    flagged = [r for r in st.session_state.llm_eval_results
                               if r["suggest_removal"]]
                    st.info(f"LLM 共建议删除 **{len(flagged)}** 条关系，请逐条确认：")
                    changed = False
                    for i, item in enumerate(st.session_state.llm_eval_results):
                        if not item["suggest_removal"]:
                            continue
                        rel = item["rel"]
                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.markdown(
                                f"**{rel.get('object_a')} → {rel.get('object_b')}**  \n"
                                f"类型：`{rel.get('relation')}`  \n"
                                f"LLM 评分：{item['score']}/10  原因：{item['reason']}"
                            )
                        with col_b:
                            keep = st.checkbox("保留", value=item["keep"], key=f"llm_keep_{i}")
                            if keep != item["keep"]:
                                st.session_state.llm_eval_results[i]["keep"] = keep
                                changed = True

                    if st.button("提交清洗结果", key="btn_llm_commit"):
                        final_rels = [
                            r["rel"] for r in st.session_state.llm_eval_results
                            if not r["suggest_removal"] or r["keep"]
                        ]
                        with open(rels_path4, 'w', encoding='utf-8') as f:
                            json.dump(final_rels, f, indent=4, ensure_ascii=False)
                        st.success(f"已保存，剩余 {len(final_rels)} 条关系。")
                        st.session_state.llm_eval_results = None
                        st.rerun()

    # ─── 可视化预览 ────────────────────────────
    st.divider()
    st.subheader("图谱预览")
    topics_vis = list_topics()
    if topics_vis:
        sel_vis = st.multiselect("选择要预览的主题（可多选合并）", topics_vis)
        if sel_vis and st.button("生成并预览"):
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "show_module", os.path.join(_ROOT, "show.py"))
            show_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(show_mod)
            html_path = os.path.join(_ROOT, "output", "_preview.html")
            os.makedirs(os.path.join(_ROOT, "output"), exist_ok=True)
            try:
                show_mod.create_knowledge_graph(
                    sel_vis,
                    output_file="_preview.html",
                    output_dir="output"
                )
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_str = f.read()
                st.components.v1.html(html_str, height=700, scrolling=True)
            except Exception as e:
                st.error(f"预览失败：{e}")
    else:
        st.info("暂无可用主题，请先完成图谱生成流程。")


# ─────────────────────────────────────────────
# 页面 B：图谱查看与编辑
# ─────────────────────────────────────────────

def page_editor():
    st.header("图谱查看与编辑")
    st.caption("交互式查看知识图谱，支持节点/关系的增删改，以及 AI 智能补全空白关系。")

    if not API_KEY:
        st.warning("未配置 DEEPSEEK_API_KEY，AI 补全功能将不可用。")

    try:
        from streamlit_agraph import agraph, Node, Edge, Config
    except ImportError:
        st.error("缺少依赖 `streamlit-agraph`，请运行：pip install streamlit-agraph")
        return

    # ── 主题选择 ──
    topics = list_topics()
    if not topics:
        st.info("暂无可用主题数据，请先在「知识图谱生成」页完成步骤 1-3。")
        return

    sel_topic = st.selectbox("选择主题", topics)
    mat_dir = get_material_dir(sel_topic)
    nodes_path = os.path.join(mat_dir, f"{sel_topic}_nodes.json")
    rels_path = os.path.join(mat_dir, f"{sel_topic}_relations.json")

    # 初始化/刷新 session state
    state_key_n = f"nodes_{sel_topic}"
    state_key_r = f"rels_{sel_topic}"
    if state_key_n not in st.session_state:
        st.session_state[state_key_n], st.session_state[state_key_r] = \
            load_graph_data(nodes_path, rels_path)

    nodes_data = st.session_state[state_key_n]
    rels_data = st.session_state[state_key_r]

    def persist():
        save_graph_data(nodes_data, rels_data, nodes_path, rels_path)

    def get_node_idx(name):
        for i, n in enumerate(nodes_data):
            if n['name'] == name:
                return i
        return -1

    # ── 渲染参数 ──
    with st.expander("渲染设置", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            graph_height = st.slider("画布高度", 600, 1200, 850, 50)
            max_label_len = st.slider("节点标签最大长度", 4, 20, 8, 1)
        with c2:
            show_edge_labels = st.checkbox("显示关系标签", value=False)
            node_base_size = st.slider("节点基准大小", 10, 30, 16, 1)

    def shorten(text: str, max_len: int) -> str:
        if not text:
            return ""
        return text if len(text) <= max_len else (text[:max_len] + "…")

    # ── 布局 ──
    col_graph, col_ctrl = st.columns([3, 1])

    with col_graph:
        vis_nodes = [
            Node(
                id=n['name'],
                label=shorten(n['name'], max_label_len),
                title=f"{n.get('name', '')}\n{n.get('desc', '')}",
                size=max(8, node_base_size + (4 - int(n.get('level', 4))) * 2),
                color=n.get('color', '#97C2FC')
            )
            for n in nodes_data
        ]
        vis_edges = [
            Edge(
                source=r['obj_a'],
                target=r['obj_b'],
                label=(r.get('rel_name', '') if show_edge_labels else ""),
                title=f"{r.get('obj_a', '')} -> {r.get('obj_b', '')}\n"
                      f"{r.get('rel_name', '')}\n{r.get('explan', '')}"
            )
            for r in rels_data
        ]
        config = Config(
            width="100%",
            height=graph_height,
            directed=True,
            physics=True,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=False
        )
        selected_node = agraph(nodes=vis_nodes, edges=vis_edges, config=config)

    node_names = [n['name'] for n in nodes_data]

    with col_ctrl:
        st.caption(f"节点：{len(nodes_data)} · 关系：{len(rels_data)}")
        tab_create, tab_link, tab_edit, tab_rel, tab_ai = st.tabs(
            ["新建节点", "新建关系", "编辑节点", "编辑关系", "AI 补全"]
        )

        # ── Tab 1：新建节点 ──
        with tab_create:
            with st.form("create_node_form"):
                nn_name = st.text_input("节点名称（唯一）",
                                        placeholder="例：连续函数")
                nn_desc = st.text_input("描述", placeholder="例：在某点连续的函数")
                nn_level = st.number_input("等级 (0-4)", min_value=0,
                                           max_value=4, value=4)
                nn_color = st.color_picker("颜色", "#97C2FC")
                if st.form_submit_button("创建节点", type="primary"):
                    if not nn_name:
                        st.error("名称不能为空")
                    elif get_node_idx(nn_name) != -1:
                        st.error("该节点已存在")
                    else:
                        nodes_data.append({
                            "name": nn_name, "desc": nn_desc,
                            "level": nn_level, "color": nn_color
                        })
                        persist()
                        st.success(f"已创建节点：{nn_name}")
                        st.rerun()

        # ── Tab 2：新建关系 ──
        with tab_link:
            src = st.selectbox("起点 A", node_names, key="lnk_src")
            tgt = st.selectbox("终点 B", node_names, key="lnk_tgt")
            if st.button("建立连接", type="primary", key="btn_link"):
                if src and tgt and src != tgt:
                    rels_data.append({
                        "obj_a": src, "obj_b": tgt,
                        "rel_name": "", "explan": ""
                    })
                    persist()
                    st.rerun()
                else:
                    st.warning("起点与终点不能相同。")

        # ── Tab 3：编辑节点 ──
        with tab_edit:
            target = selected_node or st.selectbox(
                "选择节点", node_names, key="edit_sel")
            if not target:
                st.info("请点击左侧图谱中的节点，或从下拉菜单选择。")
            else:
                idx = get_node_idx(target)
                if idx != -1:
                    curr = nodes_data[idx]
                    with st.form("edit_node_form"):
                        e_name = st.text_input("名称", value=curr['name'])
                        e_desc = st.text_input("描述",
                                               value=curr.get('desc', ''))
                        e_level = st.number_input(
                            "等级", min_value=0, max_value=4,
                            value=int(curr.get('level', 4)))
                        e_color = st.color_picker(
                            "颜色", value=curr.get('color', '#97C2FC'))
                        c1, c2 = st.columns(2)
                        save_btn = c1.form_submit_button("保存", type="primary")
                        del_btn = c2.form_submit_button("删除")

                    if save_btn:
                        old_name = curr['name']
                        if e_name != old_name and get_node_idx(e_name) != -1:
                            st.error(f"节点名称 '{e_name}' 已存在。")
                        else:
                            nodes_data[idx].update({
                                'name': e_name, 'desc': e_desc,
                                'level': e_level, 'color': e_color
                            })
                            if e_name != old_name:
                                for r in rels_data:
                                    if r['obj_a'] == old_name:
                                        r['obj_a'] = e_name
                                    if r['obj_b'] == old_name:
                                        r['obj_b'] = e_name
                            persist()
                            st.success("保存成功")
                            st.rerun()

                    if del_btn:
                        st.session_state[state_key_n] = [
                            n for n in nodes_data if n['name'] != target]
                        st.session_state[state_key_r] = [
                            r for r in rels_data
                            if r['obj_a'] != target and r['obj_b'] != target
                        ]
                        persist()
                        st.rerun()

        # ── Tab 4：编辑关系 ──
        with tab_rel:
            filter_node = selected_node or st.selectbox(
                "按节点筛选", ["（全部）"] + node_names, key="rel_filter")
            if filter_node and filter_node != "（全部）":
                related = [(i, r) for i, r in enumerate(rels_data)
                           if r['obj_a'] == filter_node or r['obj_b'] == filter_node]
            else:
                related = list(enumerate(rels_data))

            if not related:
                st.info("该节点暂无关系。")
            else:
                opts = [f"{r['obj_a']} → {r['obj_b']}" for _, r in related]
                sel_i = st.selectbox("选择关系", range(len(related)),
                                     format_func=lambda x: opts[x],
                                     key="rel_sel")
                real_idx, rel_obj = related[sel_i]
                with st.form("rel_edit_form"):
                    n_rel = st.text_input("关系名称",
                                          value=rel_obj.get('rel_name', ''))
                    n_exp = st.text_area("说明",
                                         value=rel_obj.get('explan', ''))
                    c1, c2 = st.columns(2)
                    save_r = c1.form_submit_button("保存", type="primary")
                    del_r = c2.form_submit_button("删除关系")

                if save_r:
                    rels_data[real_idx]['rel_name'] = n_rel
                    rels_data[real_idx]['explan'] = n_exp
                    persist()
                    st.rerun()
                if del_r:
                    rels_data.pop(real_idx)
                    persist()
                    st.rerun()

        # ── Tab 5：AI 智能补全 ──
        with tab_ai:
            st.markdown("#### AI 智能补全")
            incomplete = [r for r in rels_data
                          if not r.get('rel_name') or not r.get('explan')]
            st.info(f"共 **{len(rels_data)}** 条关系，其中 **{len(incomplete)}** 条待补全。")

            if incomplete:
                st.warning("⚠ 将调用 API，耗时较长。")
                if st.button(f"启动 AI 补全（{len(incomplete)} 条）",
                             type="primary", key="btn_ai_fill"):
                    if not API_KEY:
                        st.error("未配置 API Key。")
                    else:
                        client = OpenAI(api_key=API_KEY, base_url=ENDPOINT)
                        node_lookup = {n['name']: n.get('desc', '')
                                       for n in nodes_data}
                        prog = st.progress(0)
                        status_txt = st.empty()
                        done = 0

                        # 使用多线程并发补全
                        lock = threading.Lock()

                        def fill_one(r):
                            da = node_lookup.get(r['obj_a'], '')
                            db = node_lookup.get(r['obj_b'], '')
                            result = get_relation_prediction(
                                client, r['obj_a'], da, r['obj_b'], db)
                            return r, result

                        with ThreadPoolExecutor(max_workers=4) as executor:
                            futures = {executor.submit(fill_one, r): r
                                       for r in rels_data
                                       if not r.get('rel_name') or not r.get('explan')}
                            for future in as_completed(futures):
                                rel, res = future.result()
                                rel['rel_name'] = res.get('rel_name', 'Error')
                                rel['explan'] = res.get('explan', '')
                                with lock:
                                    done += 1
                                    prog.progress(done / len(incomplete))
                                    status_txt.text(
                                        f"已处理 {done}/{len(incomplete)}：{rel['obj_a']} → {rel['obj_b']}")

                        persist()
                        status_txt.success("所有关系已补全并保存！")
                        st.rerun()
            else:
                st.success("所有关系均已完整，无需 AI 补全。")


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="知识图谱 AI 助手",
        page_icon="🧠",
        layout="wide"
    )

    st.sidebar.title("知识图谱 AI 助手")
    st.sidebar.caption("AI 赋能知识图谱构建与管理平台")

    # API Key 状态指示
    if API_KEY:
        st.sidebar.success("API Key 已配置")
    else:
        st.sidebar.error("未检测到 API Key\n请配置 `.env` 文件")

    st.sidebar.divider()

    page = st.sidebar.radio(
        "功能导航",
        options=["知识图谱生成", "图谱查看与编辑"],
        format_func=lambda x: f"📐 {x}" if "生成" in x else f"✏️ {x}"
    )

    if page == "知识图谱生成":
        page_generate()
    else:
        page_editor()


if __name__ == "__main__":
    main()
