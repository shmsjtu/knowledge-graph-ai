# 知识图谱 AI 助手

基于 LLM（DeepSeek）的知识图谱自动构建与可视化平台。输入 Markdown 格式的教材文本，自动提取知识节点与概念关系，生成可交互的知识图谱，并提供图形化编辑界面。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| **文本清洗** | 将原始 Markdown 教材按章节拆分，调用 LLM（deepseek-reasoner）提炼主干内容 |
| **节点提取** | 对清洗后的文本分类（定义/例子/命题/证明），批量提取知识节点并输出 JSON |
| **关系提取** | 两阶段策略：先建立基础骨架（基于章节关联矩阵），再动态修复孤立节点；支持多线程并发 |
| **图谱微调** | 删除节点、清理重复关系、调用 LLM 批量评估并清洗冗余关系 |
| **可视化编辑** | Streamlit 交互界面，支持节点/关系的增删改，以及 AI 智能补全空白关系 |

---

## 目录结构

```
知识图谱 AI 助手/
├── app.py                  # Streamlit 应用入口（主程序）
├── show.py                 # 知识图谱 HTML 可视化渲染器
├── requirements.txt        # Python 依赖清单
├── .env                    # API 密钥配置（不提交到版本控制）
├── .env.example            # 密钥配置模板
│
├── new_Lib/                # 核心工具库
│   ├── __init__.py         # 统一导出
│   ├── new_prompt.py       # 所有 LLM Prompt 构建函数
│   ├── api_utils.py        # DeepSeek API 调用封装
│   ├── text_utils.py       # 文本分割与分类工具
│   ├── parse_utils.py      # LLM 响应 JSON 解析工具
│   ├── json_utils.py       # JSON 文件读写与处理工具
│   ├── file_utils.py       # Markdown 文件读写工具
│   ├── relation_utils.py   # 批量关系提取（支持多线程）
│   └── node_utils.py       # 节点去重工具
│
├── material/               # 教材原文与中间产物（按主题分文件夹）
│   └── <主题>/
│       ├── <主题>.md             # 原始教材文本（输入）
│       ├── raw_i.md              # 按章节拆分的原始内容
│       ├── <主题>_subsection_i.md # LLM 清洗后的章节内容
│       ├── <主题>_nodes.json     # 提取的知识节点
│       └── <主题>_relations.json # 提取的知识关系
│
└── output/                 # 可视化输出（HTML 文件）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制模板文件并填入你的 DeepSeek API Key：

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

编辑 `.env` 文件：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_ENDPOINT=https://api.deepseek.com
```

> 前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取 API Key。

### 3. 启动应用

```bash
streamlit run app.py
```

浏览器将自动打开 `http://localhost:8501`。

---

## 使用流程

### Streamlit 图形界面

启动后在侧边栏选择功能页：

#### 页面 A · 知识图谱生成

按顺序执行以下四个步骤：

**步骤 1 · 文本清洗提炼**

1. 将教材文本保存为 `material/<主题>/<主题>.md`（使用 `## §` 作为章节分隔符）
2. 在输入框中填写主题名称（如：`微分学`）
3. 点击「执行步骤 1」，等待 LLM 逐章节清洗完成
4. 输出：`raw_i.md` 和 `<主题>_subsection_i.md`

**步骤 2 · 节点提取**

1. 填写主题名称和 subsection 文件数量
2. 点击「执行步骤 2」，LLM 自动提取知识节点
3. 输出：`material/<主题>/<主题>_nodes.json`

**步骤 3 · 关系提取**

1. 填写主题名称和 subsection 文件数量
2. 点击「执行步骤 3」，执行两阶段关系提取：
   - Phase 1：基于章节关联矩阵建立骨架关系（多线程并发）
   - Phase 2：动态修复孤立节点（循环最多 N 轮）
3. 输出：`material/<主题>/<主题>_relations.json`

**步骤 4 · 图谱微调**

- **删除节点**：输入节点名称，级联删除所有相关关系
- **清理重复关系**：自动去除完全重复的关系条目
- **LLM 智能清洗**：批量评估关系质量，对建议删除的关系逐条人工确认

**图谱预览**：选择主题后点击「生成并预览」，在页面内嵌查看交互式知识图谱。

---

#### 页面 B · 图谱查看与编辑

选择已生成图谱的主题，进入交互式编辑界面：

| Tab | 功能 |
|-----|------|
| 新建节点 | 填写名称、描述、等级、颜色后创建节点 |
| 新建关系 | 选择起点和终点，建立有向关系 |
| 编辑节点 | 点击图中节点，修改名称/描述（级联更新关系）或删除节点 |
| 编辑关系 | 按节点筛选关联关系，修改关系名称/说明或删除关系 |
| AI 补全 | 一键调用 LLM 批量填充空白的关系类型与说明（多线程并发） |

图谱生成完成后，可使用「生成并预览」内嵌查看；若需单独输出 HTML 文件，可运行 `show.py` 并按提示输入主题名称（逗号分隔可合并多个主题），输出至 `output/` 目录。

---

## 技术说明

### 关系提取策略

采用「**基础骨架 + 动态图修复**」两阶段策略，有效解决单次提取孤立节点多、多次提取关系冗余的问题：

1. **Phase 1 基础骨架**：计算章节间语义关联矩阵（LLM 评分 0-1），对达到阈值（默认 0.7）的章节对并发提取关系，建立骨架图
2. **Phase 2 动态修复**：用 NetworkX 检测孤立节点和弱连接节点，为每个目标节点召回最相关的候选节点池，再提取补充关系；循环至图谱连通或达到最大轮数

### 多线程优化

- **关系提取**（`relation_utils.py`）：同一关系对的多个批次并发执行，使用 `ThreadPoolExecutor` + `threading.Lock` 保证结果安全合并
- **AI 补全**（`app.py` 页面 B）：多条空白关系同时并发调用 LLM，默认 4 个并发线程

### 支持的关系类型（12 种）

`instance` / `use_concept` / `is_special_case_of` / `sufficiently_imply` / `necessarily_imply` / `equivalent` / `partially_imply` / `generalize` / `dual_to` / `exclusive` / `has_property` / `relate_to`

---

## 常见问题

**Q: 步骤 1 清洗结果中出现大量 `(4)` 等标号怎么办？**  
A: 这是数学教材中公式引用编号的已知问题。建议在预处理阶段手动或用脚本将编号替换为完整公式描述。

**Q: 关系提取后仍有大量孤立节点？**  
A: 可增大「动态修复最大轮数」（默认 5）或降低「关联阈值」（默认 0.7）再次执行步骤 3。

**Q: API 调用超时或报错？**  
A: DeepSeek API 在高峰期可能响应较慢，程序已内置重试机制。如频繁超时，可在高级参数中减小 `batch_num` 以降低单次请求复杂度。
