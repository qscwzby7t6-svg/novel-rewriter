"""
任务级提示词

定义用于世界观构建、角色提取、风格分析等任务的提示词。
"""

WORLD_BUILDING_PROMPT = """请根据以下信息构建一个完整的{genre}类型小说世界观设定：

小说简介：{description}
详细程度：{detail_level}

请按以下结构输出（使用JSON格式）：
{{
    "geography": {{
        "world_name": "世界名称",
        "map_description": "地图/地理概述",
        "regions": ["区域1", "区域2"],
        "important_locations": ["重要地点1", "重要地点2"]
    }},
    "history": {{
        "timeline": ["历史事件1", "历史事件2"],
        "major_events": ["重大事件"],
        "legends": ["传说/神话"]
    }},
    "society": {{
        "factions": ["势力/组织"],
        "social_structure": "社会结构描述",
        "economy": "经济体系",
        "politics": "政治体系"
    }},
    "culture": {{
        "customs": ["风俗习惯"],
        "religions": ["宗教信仰"],
        "arts": ["艺术形式"],
        "taboos": ["禁忌"]
    }},
    "rules": ["世界规则/法则"],
    "technology_level": "科技水平描述",
    "magic_system": "力量/魔法体系概述"
}}"""

POWER_SYSTEM_PROMPT = """请为{genre}类型小说设计一个力量体系：

世界设定：{world_description}

请按以下结构输出（使用JSON格式）：
{{
    "name": "体系名称",
    "description": "体系概述",
    "levels": [
        {{
            "level_name": "等级名称",
            "level_number": 1,
            "description": "等级描述",
            "abilities": ["该等级能力"],
            "requirements": "突破条件"
        }}
    ],
    "skills": ["技能列表"],
    "equipment_types": ["装备类型"],
    "cultivation_methods": ["修炼功法"]
}}"""

CHARACTER_EXTRACTION_PROMPT = """请从以下小说文本中提取角色信息：

{text_sample}

请按以下结构输出（使用JSON格式）：
{{
    "characters": [
        {{
            "name": "角色姓名",
            "aliases": ["别名"],
            "role_type": "主角/配角/反派/路人",
            "description": "外貌描述",
            "personality": "性格特征",
            "background": "背景故事",
            "abilities": ["能力/技能"],
            "speech_style": "语言风格",
            "goals": "目标/动机",
            "relations": [
                {{
                    "target_name": "关系对象",
                    "relation_type": "关系类型",
                    "description": "关系描述"
                }}
            ]
        }}
    ]
}}"""

WRITING_STYLE_ANALYSIS_PROMPT = """请分析以下小说文本的写作风格：

{text_sample}

请按以下结构输出（使用JSON格式）：
{{
    "tone": "基调（轻松/沉重/幽默/严肃）",
    "perspective": "叙事视角",
    "sentence_style": "句子风格",
    "description_density": "描写密度（稀疏/适中/密集）",
    "dialogue_ratio": 0.3,
    "vocabulary_level": "用词水平（通俗/文学/古风）",
    "special_elements": ["特殊元素"],
    "reference_style": "参考风格描述"
}}"""


def get_task_prompt(task_type: str, **kwargs) -> str:
    """
    获取任务提示词。

    Args:
        task_type: 任务类型 (world_building/power_system/character_extraction/writing_style)
        **kwargs: 模板变量

    Returns:
        str: 格式化的任务提示词
    """
    prompts = {
        "world_building": WORLD_BUILDING_PROMPT,
        "power_system": POWER_SYSTEM_PROMPT,
        "character_extraction": CHARACTER_EXTRACTION_PROMPT,
        "writing_style": WRITING_STYLE_ANALYSIS_PROMPT,
    }

    template = prompts.get(task_type, "")
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return template
