"""
段落级提示词

定义用于段落级生成的提示词，支持将章节拆分为多个段落分别生成。
"""

PARAGRAPH_GENERATE_PROMPT = """请根据以下信息撰写一个小说段落。

【段落定位】
章节：第{chapter_number}章 {chapter_title}
段落序号：{paragraph_index}/{total_paragraphs}

【段落要求】
内容方向：{content_direction}
情感基调：{emotion}
场景：{scene}
出场角色：{characters}

【前一段结尾】
{previous_paragraph_end}

【写作风格】
{style_requirements}

请撰写约{target_words}字的段落内容。直接输出段落文本，不要添加标注。"""

PARAGRAPH_TRANSITION_PROMPT = """请为以下两个段落之间写一个过渡段落。

【前一段结尾】
{previous_end}

【后一段开头方向】
{next_direction}

【要求】
- 过渡自然流畅
- 长度约50-150字
- 保持叙事连贯性

请直接输出过渡段落。"""

PARAGRAPH_EXPAND_PROMPT = """请扩写以下段落，使其更加丰富生动。

【原段落】
{original_paragraph}

【扩写要求】
- 增加细节描写
- 丰富感官描写（视觉、听觉、触觉等）
- 增加角色心理活动
- 目标字数：{target_words}字
- 保持原意不变

请直接输出扩写后的段落。"""

PARAGRAPH_POLISH_PROMPT = """请润色以下段落，提升文笔质量。

【原段落】
{original_paragraph}

【润色要求】
- 修正不通顺的句子
- 优化用词
- 增强表现力
- 消除AI化表达
- 保持原意不变

请直接输出润色后的段落。"""


def get_paragraph_prompt(prompt_type: str, **kwargs) -> str:
    """
    获取段落级提示词。

    Args:
        prompt_type: 提示词类型 (generate/transition/expand/polish)
        **kwargs: 模板变量

    Returns:
        str: 格式化的提示词
    """
    prompts = {
        "generate": PARAGRAPH_GENERATE_PROMPT,
        "transition": PARAGRAPH_TRANSITION_PROMPT,
        "expand": PARAGRAPH_EXPAND_PROMPT,
        "polish": PARAGRAPH_POLISH_PROMPT,
    }

    template = prompts.get(prompt_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
