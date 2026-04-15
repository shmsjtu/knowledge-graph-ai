# 知识图谱 AI 助手

基于 LLM（DeepSeek）的知识图谱自动构建与可视化平台，采用 **Plan-Generate-Evaluate 三阶段管线架构**，从数学教材中自动提取知识节点与概念关系，生成可交互的知识图谱。

---

## 核心架构：Plan-Generate-Evaluate 管线

本项目采用三阶段串行管线架构，每个阶段由专门的 LLM 模块负责：

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Planning   │ ──→  │ Generation  │ ──→  │ Evaluation  │
│     LLM     │      │     LLM     │      │     LLM     │
└─────────────┘      └─────────────┘      └─────────────┘
     规划阶段              生成阶段              评估阶段
   分析教材目录          提取节点与关系         质量检查过滤
   制定构建计划          执行提取任务           反馈优化建议
```

### 1. Planning LLM（规划阶段）
- **输入**：教材目录结构（TOC）
- **任务**：
  - 分析章节之间的逻辑关系
  - 制定图谱构建计划（任务分解）
  - 确定节点提取优先级和关系提取策略
- **输出**：JSON 格式的任务列表，包含：
  - 任务类型（extract_nodes / extract_relations / extract_both）
  - 目标章节
  - 提取重点（定义、定理、实例等）
  - 任务优先级和依赖关系

### 2. Generation LLM（生成阶段）
- **输入**：Planning 阶段的任务计划
- **任务**：
  - 根据任务类型提取知识节点（定义、定理、实例等）
  - 提取节点间的逻辑关系（包含、递推、对偶等）
  - 支持工具调用（Tool Calling）获取教材内容
- **输出**：
  - 节点列表：`[节点名称, {desc, level, color}]`
  - 关系列表：`[起点, 终点, {rel, 定理, color}]`

### 3. Evaluation LLM（评估阶段）
- **输入**：Generation 阶段生成的节点和关系
- **任务**：
  - 评估节点质量（完整性、准确性、层级合理性）
  - 评估关系质量（逻辑正确性、冗余检测）
  - 过滤低质量内容，生成反馈建议
- **输出**：
  - 合格的节点和关系
  - 评估反馈（可用于迭代优化）

---

## 功能概览

| 功能模块 | 说明 |
|---------|------|
| **Pipeline 管线** | Plan-Generate-Evaluate 三阶段串行处理，自动化程度高 |
| **Streamlit 应用** | 全新的 Streamlit 交互界面，集成管线、可视化、编辑和 AI 助手 |
| **文本清洗** | 将原始 Markdown/TeX 教材按章节拆分，调用 LLM 提炼主干内容 |
| **节点提取** | 基于规划任务，智能提取定义、定理、实例等知识节点 |
| **关系提取** | 两阶段策略：骨架关系（章节关联矩阵）+ 动态修复（孤立节点） |
| **质量评估** | LLM 自动评估节点和关系的质量，过滤低质量内容 |
| **工具调用** | 支持 Tool Calling，动态查询已有知识和教材内容 |
| **可视化编辑** | pyvis 交互式图谱可视化，支持节点/关系的增删改 |
| **AI 助手** | 通过自然语言智能添加节点/关系，自动补全关系信息 |

---

## 目录结构

```
知识图谱 AI 助手/
├── streamlit_app.py        # Streamlit 应用入口（主程序，推荐）
├── app.py                  # 旧版 Streamlit 应用（已废弃）
├── show.py                 # 知识图谱 HTML 可视化渲染器
├── start_app.bat           # Windows 启动脚本
├── start_app.sh            # macOS/Linux 启动脚本
├── requirements.txt        # Python 依赖清单
├── .env                    # API 密钥配置（不提交到版本控制）
├── .env.example            # 密钥配置模板
│
├── scripts/                # 脚本目录
│   ├── run_pipeline.py     # 管线流程脚本
│   └── config.py           # 配置管理
│
├── src/                    # 源代码目录
│   ├── agents/             # 智能体模块
│   │   ├── planning_agent.py       # 规划智能体
│   │   ├── generation_agent.py     # 生成智能体
│   │   └── evaluation_agent.py     # 评估智能体
│   ├── pipeline/           # 管线模块
│   │   ├── orchestrator.py         # 管线编排器
│   │   ├── task_executor.py        # 任务执行器
│   │   └── dependency_resolver.py  # 依赖解析器
│   ├── core/               # 核心数据结构
│   │   ├── result_types.py         # 结果类型定义
│   │   ├── constants.py            # 常量定义
│   │   └── exceptions.py           # 异常定义
│   ├── infrastructure/     # 基础设施
│   │   ├── api_client.py           # API 客户端
│   │   ├── logger.py               # 日志工具
│   │   └── conversation_manager.py # 对话管理
│   ├── utils/              # 工具模块
│   │   ├── json_parser.py          # JSON 解析器
│   │   ├── section_extractor.py    # 章节提取器
│   │   └── markdown_section_extractor.py # Markdown 章节提取
│   └── config/             # 配置模块
│       ├── prompts.py              # 提示词模板
│       └── two_step_planning_prompts.py # 两步规划提示词
│
├── material/               # 教材原文与中间产物（按主题分文件夹）
│   └── <主题>/
│       ├── <主题>.md             # 原始教材文本（输入）
│       ├── raw_i.md              # 按章节拆分的原始内容
│       ├── <主题>_subsection_i.md # LLM 清洗后的章节内容
│       ├── <主题>_nodes.json     # 提取的知识节点（新格式）
│       └── <主题>_relations.json # 提取的知识关系（新格式）
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
DEEPSEEK_API_ENDPOINT=
```

> 前往 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取 API Key。

### 3. 启动应用

#### 方式一：使用 Streamlit 应用（推荐）

**Windows:**
```bash
# 双击运行
start_app.bat

# 或命令行运行
streamlit run streamlit_app.py
```

**macOS / Linux:**
```bash
# 添加执行权限
chmod +x start_app.sh

# 运行
./start_app.sh

# 或直接运行
streamlit run streamlit_app.py
```

浏览器将自动打开 `http://localhost:8501`。

#### 方式二：使用管线脚本

```bash
python scripts/run_pipeline.py
```

---

## 使用流程

### 方式一：使用 Streamlit 应用（推荐）

启动后，在侧边栏选择功能页：

#### 📊 页面 B · 图谱可视化与编辑

注意：可视化要求的文件在 `material` 中，正确示例如下：

```
material ---- 复分析 ---- 复分析_nodes.json
                      |--- 复分析_relations.json
```

交互式查看知识图谱：

1. **选择教材**：选择已生成图谱的教材
2. **配置参数**：调整画布高度等可视化参数
3. **生成可视化**：点击「生成可视化」，使用 pyvis 生成交互式图谱
4. **交互操作**：
   - 鼠标拖拽移动节点
   - 滚轮缩放图谱
   - 点击节点查看详细信息
   - 悬停查看关系说明

实时编辑知识图谱：

**节点管理**
- ➕ 添加新节点：填写名称、描述、层级、颜色
- ✏️ 编辑节点：修改节点属性
- 🗑️ 删除节点：级联删除相关关系

**关系管理**
- ➕ 添加新关系：选择起点、终点，填写关系类型和说明
- ✏️ 编辑关系：修改关系属性
- 🗑️ 删除关系：移除不需要的关系

**批量操作**
- 删除孤立节点（无任何关系的节点）
- 删除重复关系

---

### 方式二：使用 Pipeline 管线脚本

使用 Python 命令行执行管线脚本：

- 首先修改 `scripts/config.py` 中的 `MATERIAL_NAME` 与 `MATERIAL_FILE` 

---

## 数据格式说明

### 节点格式（新格式）
```json
[
  ["集合", {"desc": "由确定的、互不相同的对象组成的整体", "level": 0, "color": "#FF0000"}],
  ["映射", {"desc": "两个集合之间的对应关系", "level": 1, "color": "#FFA500"}]
]
```

### 关系格式（新格式）
```json
[
  ["集合", "映射", {"rel": "必要递推", "定理": "映射建立在集合基础上", "color": "#00a5b1"}]
]
```

---

## 常见问题

**Q: 步骤 1 清洗结果中出现大量 `(4)` 等标号怎么办？**
A: 这是数学教材中公式引用编号的已知问题。建议在预处理阶段手动或用脚本将编号替换为完整公式描述。

**Q: 关系提取后仍有大量孤立节点？**
A: 可增大「动态修复最大轮数」（默认 5）或降低「关联阈值」（默认 0.7）再次执行步骤 3。

**Q: API 调用超时或报错？**
A: DeepSeek API 在高峰期可能响应较慢，程序已内置重试机制。如频繁超时，可在高级参数中减小 `batch_num` 以降低单次请求复杂度。

**Q: 如何使用 Pipeline 管线？**
A: 参考「使用流程 - 方式一」章节，使用 `PipelineOrchestrator` 类运行完整管线。

**Q: 新旧数据格式如何转换？**
A: 使用 `new_Lib/format_utils.py` 中的转换函数，支持单文件迁移和批量转换。

---

## 技术栈

参考环境 `kg_app`

- **前端**：Streamlit（交互界面）、pyvis（图谱可视化）
- **后端**：Python 3.8+
- **LLM**：DeepSeek API（deepseek-chat / deepseek-reasoner）
- **图处理**：NetworkX
- **并发**：ThreadPoolExecutor

---

## 许可证

MIT License
