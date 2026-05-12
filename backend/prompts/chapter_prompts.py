"""
章节级提示词

定义用于章节大纲生成、正文生成、续写、修改等场景的提示词。
"""

CHAPTER_OUTLINE_PROMPT = """请为小说《{novel_name}》生成第{chapter_number}章的大纲。

【小说信息】
类型：{genre}
简介：{description}
总章数：{total_chapters}

【世界观设定】
{world_context}

【前情提要】
{previous_summary}

【上一章大纲】
{previous_outline}

【写作要求】
- 目标字数：{target_words}字
- 本章需要推进的主要情节：{main_plot}
- 本章出场角色：{characters}

请按以下结构输出（使用JSON格式）：
{{
    "title": "章节标题",
    "summary": "章节摘要（100字以内）",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "characters_involved": ["角色1", "角色2"],
    "foreshadows_to_plant": ["本章设置的伏笔"],
    "foreshadows_to_resolve": ["本章回收的伏笔"],
    "emotional_arc": "情感弧线描述",
    "word_count_target": {target_words}
}}"""

CHAPTER_WRITING_PROMPT = """请根据以下信息撰写小说章节正文。

【小说信息】
小说名：{novel_name}
类型：{genre}

【世界观设定】
{world_context}

【本章大纲】
标题：{chapter_title}
摘要：{chapter_summary}
关键事件：{key_events}
出场角色：{characters_involved}
情感弧线：{emotional_arc}

【前文上下文】
{context}

【写作风格要求】
{style_requirements}

【写作规则】
1. 严格按照大纲推进情节，不要偏离主线
2. 保持角色性格和语言风格的一致性
3. 对话要自然，符合角色身份和性格
4. 描写要生动具体，避免空洞的概括
5. 注意节奏控制，张弛有度
6. 不要使用"总之"、"综上所述"等AI化表达
7. 目标字数：{target_words}字左右

请直接输出章节正文，不要添加任何解释或标注。"""

CHAPTER_CONTINUE_PROMPT = """请续写以下章节内容。

【已写内容】（{current_words}字）
{existing_content}

【剩余大纲要点】
{remaining_points}

【续写要求】
- 目标总字数：{target_words}字
- 需要再写约：{remaining_words}字
- 保持与前文风格一致
- 自然衔接已有内容
- 完成剩余的大纲要点

请直接输出续写内容，不要重复已有内容。"""

CHAPTER_REVISE_PROMPT = """请根据以下反馈修改章节内容。

【原章节内容】
{chapter_content}

【修改反馈】
{feedback}

【修改要求】
1. 针对反馈中的每个问题进行修改
2. 保持章节的整体结构和情节不变
3. 修改后的文本要自然流畅
4. 保持前后文风格一致

请直接输出修改后的完整章节内容。"""


def get_chapter_prompt(prompt_type: str, **kwargs) -> str:
    """
    获取章节级提示词。

    Args:
        prompt_type: 提示词类型 (outline/writing/continue/revise)
        **kwargs: 模板变量

    Returns:
        str: 格式化的提示词
    """
    prompts = {
        "outline": CHAPTER_OUTLINE_PROMPT,
        "writing": CHAPTER_WRITING_PROMPT,
        "continue": CHAPTER_CONTINUE_PROMPT,
        "revise": CHAPTER_REVISE_PROMPT,
    }

    template = prompts.get(prompt_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
