"""
去AI化服务

负责检测和消除生成文本中的AI痕迹，使文本更加自然、人性化。
"""

import logging
import re
from typing import Optional

from backend.models.schemas import Chapter
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class DeAIService:
    """去AI化处理器"""

    # 常见AI痕迹模式
    AI_PATTERNS = [
        r"总之[，,]",
        r"综上所述[，,]",
        r"值得注意的是[，,]",
        r"需要指出的是[，,]",
        r"不言而喻[，,]",
        r"毫无疑问[，,]",
        r"众所周知[，,]",
        r"在这个[^\n]{2,10}的时代",
        r"让我们一起",
        r"相信.*?一定",
        r"仿佛.*?一般",
        r"不禁.*?起来",
    ]

    # AI常用词汇替换表
    AI_VOCABULARY_REPLACEMENTS = {
        "总之": "",
        "综上所述": "",
        "值得注意的是": "",
        "需要指出的是": "",
        "不言而喻": "",
        "毫无疑问": "",
        "众所周知": "",
        "与此同时": "同时",
        "另外": "",
        "此外": "",
        "不仅如此": "",
        "换句话说": "",
        "换言之": "",
        "由此可见": "",
        "毋庸置疑": "",
        "显而易见": "",
        "事实上": "",
        "实际上": "",
        "本质上": "",
        "从根本上说": "",
        "从某种意义上说": "",
        "在这个瞬息万变的时代": "",
        "让我们一起": "",
    }

    # 抽象到具体的转换规则
    ABSTRACT_TO_CONCRETE_RULES = {
        "美丽的": ["如花般娇艳的", "清秀动人的", "明艳照人的"],
        "可怕的": ["令人毛骨悚然的", "阴森恐怖的", "触目惊心的"],
        "高兴的": ["喜上眉梢的", "眉开眼笑的", "心花怒放的"],
        "伤心的": ["黯然神伤的", "泪眼婆娑的", "心如刀割的"],
        "强大的": ["深不可测的", "力拔山兮的", "威震四方的"],
        "快速的": ["疾如闪电的", "迅雷不及掩耳的", "风驰电掣的"],
        "安静的": ["万籁俱寂的", "悄无声息的", "鸦雀无声的"],
        "黑暗的": ["伸手不见五指的", "漆黑如墨的", "暗无天日的"],
        "明亮的": ["灯火通明的", "光芒四射的", "金碧辉煌的"],
        "古老的": ["历经沧桑的", "源远流长的", "古色古香的"],
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化去AI化处理器。

        Args:
            llm_client: LLM客户端（用于LLM辅助去AI化）
        """
        self._llm = llm_client
        self._compiled_patterns = [
            re.compile(pattern) for pattern in self.AI_PATTERNS
        ]

    def detect_ai_traces(self, text: str) -> list[dict]:
        """
        检测文本中的AI痕迹。

        Args:
            text: 待检测文本

        Returns:
            list[dict]: AI痕迹列表，每项包含位置、类型和内容
        """
        traces = []
        for pattern in self._compiled_patterns:
            for match in pattern.finditer(text):
                traces.append({
                    "start": match.start(),
                    "end": match.end(),
                    "type": "pattern_match",
                    "content": match.group(),
                })

        # TODO: 添加更多AI痕迹检测方法
        # - 句式结构分析
        # - 词汇多样性分析
        # - 情感波动分析

        return traces

    def calculate_ai_score(self, text: str) -> float:
        """
        计算文本的AI痕迹评分。

        Args:
            text: 待评估文本

        Returns:
            float: AI痕迹评分（0-1，越低越好）
        """
        traces = self.detect_ai_traces(text)
        if not text:
            return 0.0

        # 基于匹配数量的简单评分
        char_count = len(text)
        if char_count == 0:
            return 0.0

        base_score = min(len(traces) * 0.05, 0.5)

        # TODO: 添加更多评分维度
        # - 句式多样性
        # - 词汇丰富度
        # - 情感自然度

        return min(base_score, 1.0)

    def remove_ai_traces(self, text: str) -> str:
        """
        基于规则去除AI痕迹。

        Args:
            text: 待处理文本

        Returns:
            str: 处理后的文本
        """
        result = text
        for pattern in self._compiled_patterns:
            result = pattern.sub("", result)

        # 清理多余空格
        result = re.sub(r"  +", " ", result)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    def replace_ai_vocabulary(self, text: str) -> str:
        """
        替换AI常用词汇为更自然的表达。

        基于规则方法，遍历预定义的AI词汇替换表进行替换。

        Args:
            text: 待处理的文本

        Returns:
            str: 替换后的文本
        """
        result = text
        for ai_word, replacement in self.AI_VOCABULARY_REPLACEMENTS.items():
            result = result.replace(ai_word, replacement)

        # 清理替换后可能出现的多余标点
        result = re.sub(r"[，,]{2,}", "，", result)
        result = re.sub(r"  +", " ", result)

        return result.strip()

    def abstract_to_concrete(self, text: str) -> str:
        """
        将抽象形容词转换为更具体的描写。

        基于规则方法，使用预定义的抽象-具体转换规则表。
        对每个抽象形容词，随机选择一个具体表达进行替换。

        Args:
            text: 待处理的文本

        Returns:
            str: 转换后的文本
        """
        import random

        result = text
        for abstract, concrete_options in self.ABSTRACT_TO_CONCRETE_RULES.items():
            if abstract in result:
                replacement = random.choice(concrete_options)
                result = result.replace(abstract, replacement, 1)  # 每次只替换第一个

        return result

    async def deai_chapter(self, chapter: Chapter) -> Chapter:
        """
        对整章进行去AI化处理。

        Args:
            chapter: 待处理的章节

        Returns:
            Chapter: 处理后的章节
        """
        logger.info(f"对第{chapter.chapter_number}章进行去AI化处理...")

        # 1. 基于规则的处理
        processed_content = self.remove_ai_traces(chapter.content)

        # 2. 计算AI痕迹评分
        ai_score = self.calculate_ai_score(processed_content)

        # 3. 如果评分仍然较高且LLM可用，使用LLM辅助优化
        if ai_score > 0.3 and self._llm is not None:
            processed_content = await self._llm_assisted_deai(
                processed_content, chapter.chapter_number
            )

        chapter.content = processed_content
        logger.info(
            f"第{chapter.chapter_number}章去AI化完成, "
            f"AI痕迹评分: {ai_score:.2f}"
        )

        return chapter

    async def _llm_assisted_deai(
        self,
        text: str,
        chapter_number: int = 0,
    ) -> str:
        """
        使用LLM辅助去AI化。

        Args:
            text: 待处理文本
            chapter_number: 章节号

        Returns:
            str: 优化后的文本
        """
        if self._llm is None:
            return text

        # TODO: 构建去AI化提示词并调用LLM
        return text
