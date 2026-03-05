# new_prompt.py
from typing import List, Dict, Any

def build_prompt_clear(text: str) -> List[Dict[str, str]]:
    """
    构建用于清理 Markdown 文本的多轮对话提示词。
    """
    system_message = """你是一位资深的数学教材编辑，非常了解数学教材中的结构。
这是一本数学分析教材中的部分内容，已经用 markdown 文件格式给出。请给我剔除文件中不重要的内容，提取出该文件中的知识点，最终要求同样以 markdown 代码的形式呈现。markdown 代码中，所有正文的前面都需要以"**定义:**"，"**定理:**"，"**引理:**"，"**推论:**"，"**命题:**"，"**例子:**" 或 "**证明:**" 开头。
但是注意对于 "定义"，"定理"，"引理"，"命题"，"推论" 这些内容，如果原文中有标号(例如"定理1:")，则开头则为对应的标号(即以"**定理1:**"开头)。注意如果出现了标号，则标号必须要与原文保持一致，但是冒号必须用英文标点，中间不允许空格！

另外注意：需要完全一致地保留文件中的标题，总共只有四级标题（即"#"，"##"，"###"，"####"）。
"#" 为章节标题，后接含类似"第（）章"的标题，例如 "# 第九章 连续映射（一般理论）"
"##" 为节标题，后接特殊符号"§"，例如 "## §1. 度量空间"
"###" 为小节标题，后接数字与小节名，例如 "### 1. 定义和实例"
"###" 为次标题，后接小写字母名，例如 "#### a. 定义"
注：不同级别的标题不能混用！严禁出现类似"# §1. 度量空间" 或 "## 1. 定义和实例" 这样的标题。
所有标题前后都需要空一行。

注意这里的"定义"，"命题"，"定理"，"引理"，"命题"，"推论"，"证明"是数学教材中常用的内容分类，请严格按照这个分类来提取内容。
请提取全面，很多知识点并不会直接以"定义"，"命题"，"例子"，"证明"等开头，而是需要你理解内容后进行归类。
特别注意：一些形如 "称之为..." 或 "称...为..." 的句子很有可能是"定义"，需要特别注意提取出来。

对于行间公式，即如果正文中如果出现了类似 "(1)" 的内容，这些都是之前出现的行间公式，请你根据前面出现过的行间公式中的内容合理填补正文中缺失的内容。请你确保每一段文字单独看都可以被理解，不出现类似 "(4)" 这样的符号。

最后请直接输出 markdown 代码，不要输出任何多余的文字。
"""
    
    user_message = f"""下面是我给你的文本，请你完成以上任务：{text}，特别注意请你确保每一段文字单独看都可以被理解，不会因为出现了符号引用而无法理解的情况，特别地不出现类似 "(4)" 这样的符号!"""
    
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

def build_prompt_def(related_theme: str, text: str) -> List[Dict[str, str]]:
    """
    构建用于从定义中提取数学对象的多轮对话提示词。
    """
    system_message = f"""你是一位专业的大学数学教学者，非常了解教材中的核心知识点以及其层级关系与重要性。你现在有一些从数学教材中截取的数学定义，你需要从这些定义中截取和{related_theme}有关的数学知识。

请先仔细思考和分析文本内容，理解这段文字中主要是在定义什么数学对象/概念，再将其中核心的数学对象/概念提炼出来，然后以 JSON 格式输出结果。

输出要求：
1. 请先进行思考分析，说明你识别到了哪些数学对象以及为什么。
2. 最后必须用 JSON 格式输出结果，格式如下：
```json
[
  {{"name": "对象名称", "desc": "对象的具体描述", "importance": "重要性评分"}},
  {{"name": "对象名称", "desc": "对象的具体描述", "importance": "重要性评分"}}
]
```

注意事项：
1. 对于一个需满足若干条件的数学定义，如果某个条件非常重要，以至于数学界对此有专门的名称，那你需要讲该条件单独列为一个数学对象，原来的数学对象中的描述可以利用该条件来定义。
2. 请你务必仔细思考这段文字主要在定义什么，如果某个数学概念仅仅是在定义过程中被用到，请不要输出它。
3. 如果一个数学对象在定义中没有明确的名称，你需要为它起一个合适的名称，名称要简洁且能反映对象的本质。
4. 务必检查是否所有的数学对象都被提取出来了，不能遗漏。
5. 思考过程可以写在 JSON 之前，但最终结果必须严格使用 JSON 格式。
6. 重要性评分范围为1-5，1表示不重要，5表示非常重要。
7. 对象的描述需要较为详细，不能过于简略。
8. 注意：请不要提取出类似 "函数$f$" , "定理2.1" 等没有实际含义的指代性对象，确保你提取出的对象具有实际的数学含义以及充足的教学价值。
"""

    example_user_input = """related_theme = "群"
输入：**定义：** 设 G 为非空集合，其上有二元运算 \(*\)（记为 \((G, *)\)），且需同时满足以下四条公理：1、对任意 \(a, b \in G\)， \(a*b\) 仍属于 G；2、对任意 \(a, b, c \in G\)， \((a*b)*c = a*(b*c)\)；3、存在唯一元素 \(e \in G\)，使得对任意 \(a \in G\)，都有 \(e*a = a*e = a\)；4、对任意 \(a \in G\)，存在唯一元素 \(a^{{-1}} \in G\)，使得 \(a*a^{{-1}} = a^{{-1}}*a = e\)。"""

    example_assistant_output = """让我分析这个群的定义。定义中提到了四条公理，每条公理都定义了一个数学对象或性质。此外，整个结构"群"本身也是一个数学对象。

最后，我需要给每个对象一个重要性评分：群作为最重要的数学对象，评分应为5，其他对象的评分应根据其重要性程度给出，例如封闭性、结合律、存在单位元、存在逆元等，评分应为4。
```json
[
  {{"name": "封闭性", "desc": "对任意 \\(a, b \\in G\\)，\\(a*b\\) 仍属于 G", "importance": 4}},
  {{"name": "结合律", "desc": "对任意 \\(a, b, c \\in G\\)，\\((a*b)*c = a*(b*c)\\)", "importance": 4}},
  {{"name": "存在单位元", "desc": "存在唯一元素 \\(e \\in G\\)，使得对任意 \\(a \\in G\\)，都有 \\(e*a = a*e = a\\)", "importance": 4}},
  {{"name": "存在逆元", "desc": "对任意 \\(a \\in G\\)，存在唯一元素 \\(a^{{-1}} \\in G\\)，使得 \\(a*a^{{-1}} = a^{{-1}}*a = e\\)", "importance": 4}},
  {{"name": "群", "desc": "非空集合G以及二元关系 \\(*\\)，满足封闭性、结合律、存在单位元、存在逆元", "importance": 5}},
  {{"name": "群的单位元", "desc": "对任意 \\(a \\in G\\)，都有 \\(e*a = a*e = a\\)", "importance": 4}},
  {{"name": "a的逆元", "desc": "\\(a*a^{{-1}} = a^{{-1}}*a = e\\)", "importance": 4}}
]
```"""

    final_user_input = f"下面是我给你的文本，请你完成以上任务。\n\n{text}"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": example_user_input},
        {"role": "assistant", "content": example_assistant_output},
        {"role": "user", "content": final_user_input}
    ]

def build_prompt_ex(related_theme: str, text: str) -> List[Dict[str, str]]:
    """
    构建用于从示例中提取数学对象的多轮对话提示词。
    """
    system_message = f"""你是一位专业的大学数学教学者，非常了解教材中的核心知识点以及其层级关系与重要性。你现在有一些从数学教材中截取的例子，你需要从这些例子中截取和{related_theme}有关的数学知识。

请先仔细思考和分析文本内容，理解这个例子主要讲的是什么，再将最核心的结论提炼出来，然后以 JSON 格式输出结果。

输出要求：
1. 请先进行思考分析，理解例子主要讲的内容，再从内容中提取结论。最后，你还需要根据这个结论在学生学习以及老师教学过程中的重要性，给出一个重要性评分。
2. 最后必须用 JSON 格式输出结果，格式如下：
```json
[
  {{"name": "结论名称", "desc": "结论的具体描述", "importance": "重要性评分"}},
  {{"name": "结论名称", "desc": "结论的具体描述", "importance": "重要性评分"}}
]
```

注意事项：
1. 例子中的数学对象不能是和{related_theme}直接相关的的数学概念与定义。
2. 你需要给你提炼出来的结论起一个合适的名称，名称要简洁且能反映对象的本质；但是对该结论的描述需要较为详细，不能过于简略。
3. 务必检查是否所有的结论都被提取出来了，不能遗漏。
4. 思考过程可以写在 JSON 之前，但最终结果必须严格使用 JSON 格式。
5. 重要性评分范围为1-5，1表示不重要，5表示非常重要。
7. 注意：请不要提取出类似 "函数$f$" , "定理2.1" 等没有实际含义的指代性对象，确保你提取出的对象具有实际的数学含义以及充足的教学价值。
"""

    example_user_input = """related_theme = "群"
输入：**例子7:** 集合\(S_3\) 构成群，其由 3 个元素（通常记为 1,2,3）的所有置换组成，其二元运算 \(*\)为置换的复合，即先做第一个置换，再对结果做第二个置换。"""

    example_assistant_output = """让我分析这个例子。例子中提到了集合S_3，这是一个具体的数学对象，它是3个元素的所有置换组成的集合，并且配有二元运算。

```json
[
  {{"name": "S_3", "desc": "由3个元素（通常记为1,2,3）的所有置换组成的集合，配有二元运算\\(*\\)为置换的复合", "classification": "例子7", "importance": 2}}
]
```"""

    final_user_input = f"下面是我给你的文本，请你完成以上任务。\n\n{text}"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": example_user_input},
        {"role": "assistant", "content": example_assistant_output},
        {"role": "user", "content": final_user_input}
    ]

def build_prompt_prop(related_theme: str, text: str) -> List[Dict[str, str]]:
    """
    构建用于从命题中提取数学对象的多轮对话提示词。
    """
    system_message = f"""你是一位专业的大学数学教学者，非常了解教材中的核心知识点以及其层级关系与重要性。你现在有一些从数学教材中截取的命题，你需要从这些命题中截取所有和{related_theme}有关的数学知识。这些知识主要是数学命题的结论，但也包括命题中涵盖的一些数学对象。

请先仔细思考和分析文本内容，识别所有相关的数学知识，然后以 JSON 格式输出结果。

输出要求：
1. 请先进行思考分析，理解命题主要讲的内容，分析其条件与结论，根据经验判断哪些知识应当被抽取出来。最后，你还需要根据这些知识在学生学习以及老师教学过程中的重要性，给出一个重要性评分。
2. 最后必须用 JSON 格式输出结果，格式如下：
```json
[
  {{"name": "结论名称", "desc": "结论的具体描述", "importance": "重要性评分"}},
  {{"name": "结论名称", "desc": "结论的具体描述", "importance": "重要性评分"}},
  {{"name": "对象名称", "desc": "对象的具体描述", "importance": "重要性评分"}}
]
```

注意事项：
1. 有些命题可能是很多子命题的集合，你需要将每个子命题单独列为一个数学对象，并为它们起合适的名称。
2. 如果该命题再文本中没有明确的名称，你需要为它起一个合适的名称，名称要简洁同时能正确反映其内容。
3. 有时可以直接将其命题的内容作为其名称，此时其 "desc" 与 "name" 相同。
4. 务必检查是否所有有价值的数学知识都被提取出来了，不能遗漏。
5. 思考过程可以写在 JSON 之前，但最终结果必须严格使用 JSON 格式。
6. 重要性评分范围为1-5，1表示不重要，5表示非常重要。
7. 对象的描述需要较为详细，不能过于简略。
8. 注意：请不要提取出类似 "函数$f$" , "定理2.1" 等没有实际含义的指代性对象，确保你提取出的对象具有实际的数学含义以及充足的教学价值。
"""

    example_user_input = """related_theme = "连续算子空间"
输入：**命题12:** 对于从赋范空间 \( X_1, \dots, X_n \) 的直积到赋范空间 \( Y \) 的多重线性算子 \( A: X_1 \\times \dots \times X_n \\to Y \)，以下条件是等价的：
a) \( A \) 具有有限的范数，
b) \( A \) 是有界算子，
c) \( A \) 是连续算子，
d) \( A \) 是在点 \( (0, \dots, 0) \in X_1 \\times \dots \\times X_n \) 连续的算子。"""

    example_assistant_output = """让我分析这个命题。命题中提到了多个等价条件，每个条件都定义了一个数学对象或性质。此外，整个等价关系本身也是一个数学对象。最后，我要给每个对象一个重要性评分：多重线性算子连续性的等价条件作为最重要的数学对象，评分应为5，其他对象的评分应根据其重要性程度给出，例如具有有限范数的算子、有界算子、连续算子、在 0 点连续的算子等，评分应为3。

```json
[
  {{"name": "具有有限范数的算子", "desc": "算子 \\( A \\) 具有有限的范数", "classification": "命题12", "importance": 3}},
  {{"name": "有界算子", "desc": "算子 \\( A \\) 是有界算子", "classification": "命题12", "importance": 3}},
  {{"name": "连续算子", "desc": "算子 \\( A \\) 是连续算子", "classification": "命题12", "importance": 3}},
  {{"name": "在 0 点连续的算子", "desc": "算子 \\( A \\) 是在点 \\( (0, \\dots, 0) \\in X_1 \\times \\dots \\times X_n \\) 连续的算子", "classification": "命题12", "importance": 3}},
  {{"name": "多重线性算子连续性的等价条件", "desc": "对于从赋范空间 \\( X_1, \\dots, X_n \\) 的直积到赋范空间 \\( Y \\) 的多重线性算子 \\( A: X_1 \\times \\dots \\times X_n \\to Y \\)，则 A 是具有有限范数的算子等价于 A 是有界算子等价于 A 是连续算子等价于 A 是在 0 点连续的算子", "classification": "命题12", "importance": 5}}
]
```"""
    
    final_user_input = f"下面是我给你的文本，请你完成以上任务，请务必检查提取出的内容是否具有充足的教学价值。\n\n{text}"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": example_user_input},
        {"role": "assistant", "content": example_assistant_output},
        {"role": "user", "content": final_user_input}
    ]

# ... (为 prompt_template_proof, evaluate, relation 等添加类似的构建函数) ...

def build_prompt_proof(proof: str, material: str) -> List[Dict[str, str]]:
    """
    构建用于分析证明思路的多轮对话提示词。
    """
    system_message = """你是一位数学教学者，你现在有一段从数学教材中截取的定理证明 "proof" 以及一些其他定理/定义的内容 "material"。"material"中的元素 ("name":"对象名称", "desc":"对象的具体描述") 的形式给出。你需要通过列举出这段证明用到的所有方法以及其是怎么使用的来理清这段定理证明的思路，并进行格式化的输出。
输出格式为：
"strategy":"使用的定理/引理/定义/方法", "desc":"论证细节以及结果"
"strayegy":"使用的定理/引理/定义/方法", "desc":"论证细节以及结果"
...
注意事项：1、证明过程中使用的定理、引理、定义、方法可能是没有直接说明的，请你将这些都提取出来
2、某些证明可能会用到构造性的方法，这时 "strategy" 就是所构造的对象
3、某些证明可能会用到反证法，这时 "strategy" 就是"反证法"
4、"desc":" 后的论证细节需要你自己总结，尽量精炼，不要直接照搬原文
5、使用到的定理/引理/定义 可能会在"material"中给出来，这时候的strategy就是"material"中对应条目的 "name" 属性
6、务必检查是否所有使用的方法以及其论证细节都被提取出来了，不能遗漏
7、直接输出结果，不要输出任何多余的文字。"""

    example_user_input = """proof: "假设角A和角B都是直角。根据直角的定义，角A = 90度，角B = 90度。因此，角A = 角B。"
material: [
("name": "直角定义", "desc": "一个角是直角当且仅当它的度数是90度。"),
("name": "等角定义", "desc": "两个角相等当且仅当它们的度数相等。")
]"""
    
    example_assistant_output = """"strategy":"直角定义","desc":"应用直角定义于角A，推导出角A=90度"
"strategy":"直角定义","desc":"应用直角定义于角B，推导出角B=90度"
"strategy":"等角定义","desc":"从角A和角B度数相等，根据等角定义得出角A=角B"
"""

    final_user_input = f'下面是我给你的证明以及材料："proof"={proof}，"material"={material}。请你完成以上任务。'

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": example_user_input},
        {"role": "assistant", "content": example_assistant_output},
        {"role": "user", "content": final_user_input}
    ]

def build_prompt_evaluate(chapter_list: str) -> List[Dict[str, str]]:
    """
    构建用于评估章节关系强度的多轮对话提示词。
    """
    system_message = """你是一位数学教育专家,擅长分析数学知识体系中不同主题之间的关联性。给定一个数学教材章节标题列表,请你评判每对章节之间的关系强度评分并生成一个上三角矩阵，评分标准为(0-1分):
1.0: 强相关 - 知识点直接依赖或高度重叠
0.7-0.9: 较强相关 - 有明显的概念联系或方法共通
0.4-0.6: 中等相关 - 有一定联系但相对独立
0.1-0.3: 弱相关 - 仅有间接或浅层联系
0.0: 无关 - 几乎没有知识关联

评估两个章节的关系时,请综合考虑以下方面:
概念依赖性: 章节 j 是否需要章节 i 的前置知识
知识重叠度: 两章节涉及的数学对象、定理或方法的重叠程度
方法论共通性: 是否使用相似的数学思维或解题技巧
应用场景关联: 两章节的知识是否经常在同一类问题中联合应用
逻辑递进关系: 是否存在从基础到高级的自然过渡

请先进行思考分析，然后以 JSON 格式输出结果。

输出要求：
1. 请先进行思考分析，说明你如何评估每对章节的关系。
2. 最后必须用 JSON 格式输出矩阵，格式如下：
```json
{{"matrix": [[1.0, score_12, score_13, ..., score_1n],[0.0, 1.0, score_23, ..., score_2n],[0.0, 0.0, 1.0, ..., score_3n],...[0.0, 0.0, 0.0, ..., 1.0]]}}
```

如果无法使用 JSON，也可以直接输出矩阵字符串格式：
[[1.0, score_12, score_13, ..., score_1n],[0.0, 1.0, score_23, ..., score_2n],[0.0, 0.0, 1.0, ..., score_3n],...[0.0, 0.0, 0.0, ..., 1.0]]
"""
    
    example_user_input = """示例 1
输入章节列表:
集合与逻辑
函数的概念
函数的性质
"""
    example_assistant_output = "[[1.0, 0.6, 0.5],[0.0, 1.0, 0.9],[0.0, 0.0, 1.0]]"

    example_user_input_2 = """示例 2
输入章节列表:
导数的定义
导数的计算
定积分
微分方程
"""
    example_assistant_output_2 = "[[1.0, 0.9, 0.7, 0.8],[0.0, 1.0, 0.6, 0.9],[0.0, 0.0, 1.0, 0.7],[0.0, 0.0, 0.0, 1.0]]"

    final_user_input = f"请为以下章节列表生成关系矩阵:\n{chapter_list}\n请先思考分析，然后输出矩阵。"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": example_user_input},
        {"role": "assistant", "content": example_assistant_output},
        {"role": "user", "content": example_user_input_2},
        {"role": "assistant", "content": example_assistant_output_2},
        {"role": "user", "content": final_user_input}
    ]


def build_prompt_candidate_recall(
    target_node: Dict[str, Any],
    candidate_nodes: List[Dict[str, Any]],
    top_k: int,
    target_text: str = "",
    max_context_chars: int = 2000
) -> List[Dict[str, str]]:
    """
    构建用于筛选候选节点的提示词，让模型只返回最有可能与目标节点存在关系的 Top-K 节点。
    """

    def format_node(node: Dict[str, Any]) -> str:
        return (
            f"- 名称: {node.get('name', '未知')}\n"
            f"  分类: {node.get('classification', '')}\n"
            f"  主题: {node.get('theme', '')}\n"
            f"  描述: {node.get('desc', '')}"
        )

    truncated_context = target_text.strip()
    if max_context_chars > 0 and len(truncated_context) > max_context_chars:
        truncated_context = truncated_context[:max_context_chars] + "\n...（上下文已截断）"

    candidate_summary = "\n".join(format_node(node) for node in candidate_nodes)

    system_message = f"""你是一位数学知识图谱构建专家，需要帮助我为一个“孤立节点”寻找最有可能与之建立关系的 Top-{top_k} 个候选节点。

请先仔细分析目标节点与候选节点的定义、主题与描述，判断哪些候选节点与目标节点最有可能存在数学关系（无论是包含、必要条件、充分条件、实例、性质等）。

### 输出要求
1. 先进行简短的推理，说明你是怎样筛选候选节点的。
2. 最后必须输出 JSON 数组，数组长度不超过 {top_k}。每个元素的格式为：
```json
{{
  "candidate_name": "节点名称",
  "reason": "为何认为这两个节点可能存在关系",
  "confidence": 0.0-1.0 之间的分数
}}
```
3. 只返回你最确信的 Top-{top_k} 个候选节点；如果候选节点都不合适，可以返回空数组。
"""

    user_message = f"""下面是需要分析的内容：

目标节点:
名称: {target_node.get('name', '')}
分类: {target_node.get('classification', '')}
主题: {target_node.get('theme', '')}
描述: {target_node.get('desc', '')}

目标节点所属章节的上下文（摘要）:
{truncated_context}

候选节点列表（最多 {len(candidate_nodes)} 个）:
{candidate_summary}
"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]


def build_prompt_relation(entities_1: str, entities_2: str, text_1: str, text_2: str) -> List[Dict[str, str]]:
    """
    构建用于分析两组数学对象关系的多轮对话提示词。
    现在包含了两组对象对应的原始 markdown 文本。
    """
    def get_extraction_prompt(entities_1, entities_2, text_1, text_2):
        system_message = """你是一位精通数学逻辑的知识图谱构建专家。你需要分析两组数学对象列表（entities_1, entities_2）以及它们各自对应的原始 markdown 文本（text_1, text_2）。
你需要结合实体列表和原始文本上下文，找出第一组中每个对象与第二组中每个对象之间的数学关系。

请先仔细思考和分析，识别对象之间的关系，然后以 JSON 格式输出结果。

### 输入数据说明
你将收到两组对象列表，每个对象包含 name, desc, classification, theme。
同时会收到两段原始文本作为上下文依据。

### 关系类型定义 (严格遵守以下12种)
你只能从以下列表中选择一种最合适的关系。如果关系不明显，请不要输出。

1. **instance (实例)**
   - 定义：A是B的一个具体实例（通常A是具体的，B是抽象的）。
   - 示例：实轴 instance 完备度量空间

2. **use_concept (使用概念)**
   - 定义：概念A在定义时运用到了概念B，即A是B的下级概念或依赖B定义。
   - 示例：域 use_concept 环 (域的定义基于环)

3. **is_special_case_of (特例)**
   - 定义：A是B的特例。A拥有B的所有特征，且有自己特殊的性质（通常A和B都是抽象概念，只是A的约束更强）。
   - 示例：方阵 is_special_case_of 矩阵

4. **sufficiently_imply (充分递推)**
   - 定义：若A成立则B一定成立 (A=>B)。A是B的充分条件。
   - 示例：矩阵不满秩 sufficiently_imply 行列式为0

5. **necessarily_imply (必要递推)**
   - 定义：有B必须有A，没有A则没有B。A是构建B的前提、基础或必要条件。
   - 注意方向：逻辑上是 B=>A，但关系标记为 A necessarily_imply B (意为 A是B的必要条件)。
   - 示例：连续 necessarily_imply 可导 (因为可导必连续，所以连续是可导的必要基础)

6. **equivalent (等价)**
   - 定义：A和B是同一数学对象的不同描述方式但是在语言上不一样。
   - 示例：线性算子在0点连续 equivalent 线性算子连续

7. **partially_imply (部分递推)**
   - 定义：A成立可以推出B部分成立，或者A能保证B中某个性质成立，但既不充分也不必要。
   - 示例：凸函数 partially_imply 二阶导数非负

8. **generalize (推广)**
   - 定义：A与B具有几乎一样的结构，仅仅存在讨论的范围或语境不同（通常B是A在更广泛情形下的版本，或者A推广到了B）。
   - 示例：函数极限的Cauchy准则 generalize 数列极限的Cauchy准则

9. **dual_to (对偶)**
   - 定义：A和B在结构、性质上呈对称互补关系。
   - 示例：线性空间 dual_to 对偶空间

10. **exclusive (互斥)**
    - 定义：A成立则B不成立，有A则没有B。
    - 示例：奇数 exclusive 偶数

11. **has_property (性质)**
    - 定义：A（通常是具体的数学对象）满足某些性质B。注意B必须只能是与A有关的性质描述，不能是其他独立数学对象。
    - 示例：度量 has_property 对称性

12. **relate_to (关联)**
    - 定义：A和B有相似结构或性质，交互但不能归类为以上关系，或关系未明确定义。
    - 示例：(作为兜底选项)

### 关系判断指南 (思维链)
在判断关系时，请遵循以下逻辑：

1. **区分"实例"与"特例"**：
   - 如果A是一个具体的、特定的对象（如"实数集R"），B是一个类（如"群"），选 `instance`。
   - 如果A和B都是类，但A的条件比B多（如"阿贝尔群"和"群"），选 `is_special_case_of`。

2. **区分"属性"与"使用概念"**：
   - 如果B仅仅是一个形容词或性质（如"紧致性"），选 `has_property`。
   - 如果B是一个独立定义的数学结构，且A的定义建立在B之上（如"向量空间"定义中用到了"域"），选 `use_concept`。

3. **区分逻辑推导**：
   - A => B：选 `sufficiently_imply` (A充分推出B)。
   - B => A (即A是B的基础)：选 `necessarily_imply` (A是B的必要条件)。
   - A <=> B：选 `equivalent`。

4. **结构性关系**：
   - 如果两者互为镜像或翻转：选 `dual_to`。
   - 如果两者公式极其相似，只是变量类型变了（如离散变连续）：选 `generalize`。

### 输出格式
请先进行思考分析，说明你识别到了哪些关系以及为什么。

然后必须用 JSON 格式输出结果，格式如下：
```json
[
  {{"object_a": "对象A名称", "object_b": "对象B名称", "relation": "关系英文名称", "explanation": "简短解释"}},
  {{"object_a": "对象A名称", "object_b": "对象B名称", "relation": "关系英文名称", "explanation": "简短解释"}}
]
```

### 注意事项
1. 不要建立对象与自身的联系（即不要输出类似 object_a equivalent object_a 这样的关系）。
2. 关系必须有文本或数学常识作为依据。
3. relation 字段必须严格使用上述 12 个英文关键词。
4. 解释要简明扼要。
5. 思考过程可以写在 JSON 之前，但最终结果必须严格使用 JSON 格式。

现在，让我们逐个分析两组数学对象中的关系：
"""

        final_user_input = f"""现在，请根据提供的两组数学对象和它们对应的原始文本，按照上述要求进行关系分析。

--- 文本1 (对应 entities_1) ---
{text_1}
--- 结束 文本1 ---

--- 文本2 (对应 entities_2) ---
{text_2}
--- 结束 文本2 ---

--- 实体1 (来自 文本1) ---
{entities_1}
--- 结束 实体1 ---

--- 实体2 (来自 文本2) ---
{entities_2}
--- 结束 实体2 ---

请开始分析并输出 JSON 行：
"""

        return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": final_user_input}
        ]
    
    return get_extraction_prompt(entities_1, entities_2, text_1, text_2)


def build_prompt_add(entities_1: str, entities_2: str, text_1: str, text_2: str) -> List[Dict[str, str]]:
    """
    构建用于分析两组数学对象关系的多轮对话提示词。
    现在包含了两组对象对应的原始 markdown 文本。
    """
    def get_extraction_prompt(entities_1, entities_2, text_1, text_2):
        system_message = """你是一位精通数学逻辑的知识图谱构建专家。你需要分析两组数学对象列表（entities_1, entities_2）以及它们各自对应的原始 markdown 文本（text_1, text_2）。
你需要结合实体列表和原始文本上下文，找出第一组中每个对象与第二组中每个对象之间的数学关系。

请先仔细思考和分析，识别对象之间的关系，然后以 JSON 格式输出结果。

### 输入数据说明
你将收到两组对象列表，每个对象包含 name, desc, classification, theme。
同时会收到两段原始文本作为上下文依据。

### 关系类型定义 (严格遵守以下12种)
你只能从以下列表中选择一种最合适的关系。如果关系不明显，请不要输出。

1. **instance (实例)**
   - 定义：A是B的一个具体实例（通常A是具体的，B是抽象的）。
   - 示例：实轴 instance 完备度量空间

2. **use_concept (使用概念)**
   - 定义：概念A在定义时运用到了概念B，即A是B的下级概念或依赖B定义。
   - 示例：域 use_concept 环 (域的定义基于环)

3. **is_special_case_of (特例)**
   - 定义：A是B的特例。A拥有B的所有特征，且有自己特殊的性质（通常A和B都是抽象概念，只是A的约束更强）。
   - 示例：方阵 is_special_case_of 矩阵

4. **sufficiently_imply (充分递推)**
   - 定义：若A成立则B一定成立 (A=>B)。A是B的充分条件。
   - 示例：矩阵不满秩 sufficiently_imply 行列式为0

5. **necessarily_imply (必要递推)**
   - 定义：有B必须有A，没有A则没有B。A是构建B的前提、基础或必要条件。
   - 注意方向：逻辑上是 B=>A，但关系标记为 A necessarily_imply B (意为 A是B的必要条件)。
   - 示例：连续 necessarily_imply 可导 (因为可导必连续，所以连续是可导的必要基础)

6. **equivalent (等价)**
   - 定义：A和B是同一数学对象的不同描述方式但是在语言上不一样。
   - 示例：线性算子在0点连续 equivalent 线性算子连续

7. **partially_imply (部分递推)**
   - 定义：A成立可以推出B部分成立，或者A能保证B中某个性质成立，但既不充分也不必要。
   - 示例：凸函数 partially_imply 二阶导数非负

8. **generalize (推广)**
   - 定义：A与B具有几乎一样的结构，仅仅存在讨论的范围或语境不同（通常B是A在更广泛情形下的版本，或者A推广到了B）。
   - 示例：函数极限的Cauchy准则 generalize 数列极限的Cauchy准则

9. **dual_to (对偶)**
   - 定义：A和B在结构、性质上呈对称互补关系。
   - 示例：线性空间 dual_to 对偶空间

10. **exclusive (互斥)**
    - 定义：A成立则B不成立，有A则没有B。
    - 示例：奇数 exclusive 偶数

11. **has_property (性质)**
    - 定义：A（通常是具体的数学对象）满足某些性质B。注意B必须只能是与A有关的性质描述，不能是其他独立数学对象。
    - 示例：度量 has_property 对称性

12. **relate_to (关联)**
    - 定义：A和B有相似结构或性质，交互但不能归类为以上关系，或关系未明确定义。
    - 示例：(作为兜底选项)

### 关系判断指南 (思维链)
在判断关系时，请遵循以下逻辑：

1. **区分"实例"与"特例"**：
   - 如果A是一个具体的、特定的对象（如"实数集R"），B是一个类（如"群"），选 `instance`。
   - 如果A和B都是类，但A的条件比B多（如"阿贝尔群"和"群"），选 `is_special_case_of`。

2. **区分"属性"与"使用概念"**：
   - 如果B仅仅是一个形容词或性质（如"紧致性"），选 `has_property`。
   - 如果B是一个独立定义的数学结构，且A的定义建立在B之上（如"向量空间"定义中用到了"域"），选 `use_concept`。

3. **区分逻辑推导**：
   - A => B：选 `sufficiently_imply` (A充分推出B)。
   - B => A (即A是B的基础)：选 `necessarily_imply` (A是B的必要条件)。
   - A <=> B：选 `equivalent`。

4. **结构性关系**：
   - 如果两者互为镜像或翻转：选 `dual_to`。
   - 如果两者公式极其相似，只是变量类型变了（如离散变连续）：选 `generalize`。

### 输出格式
请先进行思考分析，说明你识别到了哪些关系以及为什么。

然后必须用 JSON 格式输出结果，格式如下：
```json
[
  {{"object_a": "对象A名称", "object_b": "对象B名称", "relation": "关系英文名称", "explanation": "简短解释"}},
  {{"object_a": "对象A名称", "object_b": "对象B名称", "relation": "关系英文名称", "explanation": "简短解释"}}
]
```

### 注意事项
1. 不要建立对象与自身的联系（即不要输出类似 object_a equivalent object_a 这样的关系）。
2. 关系必须有文本或数学常识作为依据。
3. relation 字段必须严格使用上述 12 个英文关键词。
4. 解释要较为详细，但不用太长或大量引用原文。
5. 思考过程可以写在 JSON 之前，但最终结果必须严格使用 JSON 格式。

现在，让我们逐个分析两组数学对象中的关系：
"""

        final_user_input = f"""现在，请根据提供的两组数学对象和它们对应的原始文本，按照上述要求进行关系分析。

--- 文本1 (对应 entities_1) ---
{text_1}
--- 结束 文本1 ---

--- 文本2 (对应 entities_2) ---
{text_2}
--- 结束 文本2 ---

--- 实体1 (来自 文本1) ---
{entities_1}
--- 结束 实体1 ---

--- 实体2 (来自 文本2) ---
{entities_2}
--- 结束 实体2 ---

请开始分析并输出 JSON 行：
"""

        return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": final_user_input}
        ]
    
    return get_extraction_prompt(entities_1, entities_2, text_1, text_2)



def build_prompt_evaluate_relation(relations_batch, node_lookup):
    """
    构建用于评估单个关系质量的提示词
    """
    system_prompt = """你是一位严谨的数学学科教育专家和知识图谱架构师。你的任务是审核知识图谱中的一条“实体关系”，判断其保留价值。

你需要基于以下三个维度进行严格打分（0-10分）和评估：
1. **准确性**：该关系在学科逻辑上是否严格成立？
2. **核心性**：这对关系是该学科的“骨架”知识吗？还是仅仅是过度联想？
3. **教学价值**：向学生展示这条关系，有助于他们构建知识体系吗？（如果关系显而易见或是废话；或者不能向学生展示数学对象之间的深层关系，则价值低）

请特别注意识别并标记“冗余关系”：
- 如果关系仅仅是“文本相邻”而非“逻辑关联”，应去除。
- 模糊的“相关”关系如果缺乏具体定理支持，应去除。

请输出一个标准的 JSON 对象，不要包含 markdown 格式标记，格式如下：
{
    "suggest_removal": true/false,  // 是否建议去除。分数低于6分或有逻辑错误通常建议去除
    "relation_strength_score": int, // 0-10 整数。0为完全错误，10为核心公理
    "reason": "简短的中文评估理由，解释为什么保留或删除"
}
"""

    relations_text = ""
    for idx, rel in enumerate(relations_batch):
        # 获取节点上下文，如果没有描述则显示暂无
        node_a_desc = node_lookup.get(rel['object_a'], {}).get('desc', '暂无详细描述')
        node_b_desc = node_lookup.get(rel['object_b'], {}).get('desc', '暂无详细描述')
        

        relations_text += f"""
---
【ID: {idx}】
关系: {rel['object_a']} --[{rel.get('relation', '未知')}]--> {rel['object_b']}
说明: {rel.get('explanation', '无')}
实体A背景: {node_a_desc}
实体B背景: {node_b_desc}
"""

    user_prompt = f"""请评估以下 {len(relations_batch)} 条关系：
{relations_text}

请直接返回 JSON 数据列表。
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]