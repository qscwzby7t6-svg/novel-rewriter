"""
章节精确控制服务

负责章节生成流程的精确控制，包括：
- 章节数匹配与节奏控制
- 字数精确控制（目标字数 +/- 10%）
- 节奏曲线设计（每10章一个小高潮）
- 高潮类型轮换
- 批量章节生成
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from typing import Any, Optional

from backend.models.enums import ChapterStatus
from backend.models.schemas import (
    Chapter,
    ChapterOutline,
    NovelInfo,
)
from backend.services.context_mgr import ContextManager
from backend.services.llm_client import LLMClient
from backend.services.writer import Writer

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================

# 每卷章节数（用于节奏曲线分组）
CHAPTERS_PER_VOLUME = 30

# 字数容差
WORD_COUNT_TOLERANCE = 0.10

# 字数调整最大重试次数
WORD_COUNT_ADJUST_RETRIES = 3

# 高潮类型池
CLIMAX_TYPES = [
    "战斗高潮",
    "情感高潮",
    "真相揭示",
    "逆转",
    "能力突破",
    "团队胜利",
]

# 节奏类型定义
RHYTHM_TYPES = {
    "setup": {
        "label": "铺垫",
        "description": "世界观/角色介绍、氛围营造、日常互动",
        "tension": 1,
        "word_count_factor": 1.0,
    },
    "development": {
        "label": "发展",
        "description": "情节推进、角色成长、矛盾初现",
        "tension": 3,
        "word_count_factor": 1.0,
    },
    "rising": {
        "label": "上升",
        "description": "矛盾加剧、紧张感提升、冲突升级",
        "tension": 6,
        "word_count_factor": 1.05,
    },
    "climax": {
        "label": "高潮",
        "description": "冲突爆发、关键对决、真相大白",
        "tension": 9,
        "word_count_factor": 1.10,
    },
    "falling": {
        "label": "回落",
        "description": "高潮余波、战后整理、情感沉淀",
        "tension": 4,
        "word_count_factor": 0.95,
    },
    "resolution": {
        "label": "收束",
        "description": "阶段性总结、新伏笔设置、过渡",
        "tension": 2,
        "word_count_factor": 0.95,
    },
}


class ChapterController:
    """章节精确控制：确保章节数匹配、字数 +/- 10%、节奏控制"""

    def __init__(
        self,
        llm_client: LLMClient,
        writer: Writer,
        context_manager: ContextManager,
    ):
        """
        初始化章节控制器。

        Args:
            llm_client: LLM客户端
            writer: 写作引擎
            context_manager: 上下文管理器
        """
        self._llm = llm_client
        self._writer = writer
        self._context = context_manager

        # 高潮类型使用记录（用于避免重复）
        self._used_climax_types: list[str] = []

        # 已生成章节缓存
        self._generated_chapters: list[Chapter] = []

    # ============================================================
    # 批量章节生成
    # ============================================================

    async def generate_all_chapters(self, blueprint: NovelInfo) -> list[Chapter]:
        """
        生成所有章节。

        按卷分组，每卷内按节奏曲线生成。

        Args:
            blueprint: 小说蓝图（包含完整设定信息）

        Returns:
            list[Chapter]: 所有生成的章节列表
        """
        total_chapters = blueprint.total_chapters
        logger.info(f"=== 开始生成全部 {total_chapters} 章 ===")

        # 初始化上下文管理器
        await self._context.initialize(blueprint)

        all_chapters: list[Chapter] = []
        num_volumes = math.ceil(total_chapters / CHAPTERS_PER_VOLUME)

        for vol in range(1, num_volumes + 1):
            start_ch = (vol - 1) * CHAPTERS_PER_VOLUME + 1
            end_ch = min(vol * CHAPTERS_PER_VOLUME, total_chapters)

            volume_plan = {
                "volume_num": vol,
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "num_chapters": end_ch - start_ch + 1,
            }

            logger.info(
                f"--- 开始生成第{vol}卷 "
                f"(第{start_ch}章 ~ 第{end_ch}章) ---"
            )

            volume_chapters = await self.generate_volume(volume_plan, self._context)
            all_chapters.extend(volume_chapters)

            logger.info(
                f"--- 第{vol}卷生成完成, "
                f"共{len(volume_chapters)}章, "
                f"总字数{sum(c.word_count for c in volume_chapters)} ---"
            )

        self._generated_chapters = all_chapters
        logger.info(
            f"=== 全部 {len(all_chapters)} 章生成完成, "
            f"总字数{sum(c.word_count for c in all_chapters)} ==="
        )

        return all_chapters

    async def generate_volume(
        self,
        volume_plan: dict,
        context: ContextManager,
    ) -> list[Chapter]:
        """
        生成一卷的章节。

        设计节奏曲线，按节奏曲线逐章生成。

        Args:
            volume_plan: 卷计划，包含：
                - volume_num: 卷号
                - start_chapter: 起始章节号
                - end_chapter: 结束章节号
                - num_chapters: 章节数
            context: 上下文管理器

        Returns:
            list[Chapter]: 本卷生成的章节列表
        """
        num_chapters = volume_plan["num_chapters"]
        start_ch = volume_plan["start_chapter"]

        # 设计本卷的节奏曲线
        rhythm_curve = self.design_rhythm_curve(num_chapters)
        logger.info(
            f"第{volume_plan['volume_num']}卷节奏曲线: "
            f"{[RHYTHM_TYPES[r]['label'] for r in rhythm_curve]}"
        )

        chapters: list[Chapter] = []

        for i in range(num_chapters):
            chapter_num = start_ch + i
            rhythm_type = rhythm_curve[i]
            rhythm_info = RHYTHM_TYPES[rhythm_type]

            logger.info(
                f"生成第{chapter_num}章 "
                f"(节奏: {rhythm_info['label']}, "
                f"张力: {rhythm_info['tension']})"
            )

            # 重置章节成本
            self._llm.reset_chapter_cost()

            # 获取写作上下文
            chapter_plan = {
                "chapter_number": chapter_num,
                "rhythm_type": rhythm_type,
                "tension": rhythm_info["tension"],
                "volume_num": volume_plan["volume_num"],
            }
            writing_context = context.get_writing_context(chapter_plan)

            # 获取目标字数（根据节奏类型微调）
            target_words = self.get_target_word_count(
                chapter_num,
                [c.word_count for c in chapters] if chapters else [],
            )
            # 根据节奏类型调整目标字数
            base_target = target_words[0]
            adjusted_target = int(base_target * rhythm_info["word_count_factor"])
            target_min = int(adjusted_target * (1 - WORD_COUNT_TOLERANCE))
            target_max = int(adjusted_target * (1 + WORD_COUNT_TOLERANCE))

            # 获取上一章大纲
            previous_outline = None
            if chapters:
                previous_outline = chapters[-1].outline

            # 1. 生成大纲
            outline = await self._writer.generate_chapter_outline(
                chapter_number=chapter_num,
                novel_info=self._build_novel_info_for_chapter(
                    chapter_num, volume_plan, rhythm_type
                ),
                previous_outline=previous_outline,
            )

            # 在大纲中标注节奏信息
            outline.word_count_target = adjusted_target

            # 2. 生成正文
            chapter = await self._writer.generate_chapter_content(
                outline=outline,
                novel_info=self._build_novel_info_for_chapter(
                    chapter_num, volume_plan, rhythm_type
                ),
                context=writing_context,
            )

            # 3. 检查并调整字数
            chapter = await self._ensure_word_count(
                chapter, adjusted_target, chapter_num
            )

            # 4. 一致性检查
            consistency_issues = context.check_consistency(
                chapter.content, chapter_num
            )
            if consistency_issues:
                high_severity = [
                    issue for issue in consistency_issues
                    if issue["severity"] == "high"
                ]
                if high_severity:
                    logger.warning(
                        f"第{chapter_num}章发现{len(high_severity)}个高严重度一致性问题: "
                        f"{[issue['issue'][:50] for issue in high_severity]}"
                    )
                    # 尝试修复高严重度问题
                    chapter = await self._fix_consistency_issues(
                        chapter, high_severity
                    )

            # 5. 更新上下文
            context.update_after_chapter(chapter)

            # 6. 更新章节状态
            chapter.status = ChapterStatus.COMPLETED
            chapter.updated_at = datetime.now()

            chapters.append(chapter)

            logger.info(
                f"第{chapter_num}章完成: "
                f"{chapter.word_count}字 "
                f"(目标{adjusted_target}, "
                f"范围{target_min}-{target_max})"
            )

        return chapters

    # ============================================================
    # 节奏曲线设计
    # ============================================================

    def design_rhythm_curve(self, num_chapters: int) -> list[str]:
        """
        设计节奏曲线，确保每10章有小高潮。

        基本模式（每10章一个周期）：
          铺垫(1-2) -> 发展(3-4) -> 上升(5-6) -> 高潮(7-8) -> 回落(9) -> 收束(10)

        对于不满10章的情况，按比例裁剪。

        Args:
            num_chapters: 章节数

        Returns:
            list[str]: 每章的节奏类型列表
        """
        # 基础10章节奏模式
        base_pattern = [
            "setup",        # 第1章: 铺垫
            "setup",        # 第2章: 铺垫
            "development",  # 第3章: 发展
            "development",  # 第4章: 发展
            "rising",       # 第5章: 上升
            "rising",       # 第6章: 上升
            "climax",       # 第7章: 高潮
            "climax",       # 第8章: 高潮
            "falling",      # 第9章: 回落
            "resolution",   # 第10章: 收束
        ]

        if num_chapters <= 0:
            return []

        if num_chapters <= 10:
            # 按比例裁剪
            return self._scale_pattern(base_pattern, num_chapters)

        # 多个完整周期 + 余数
        full_cycles = num_chapters // 10
        remainder = num_chapters % 10

        curve = []
        for cycle in range(full_cycles):
            # 每个周期的高潮类型轮换
            cycle_pattern = list(base_pattern)
            curve.extend(cycle_pattern)

        # 处理余数
        if remainder > 0:
            remainder_pattern = self._scale_pattern(base_pattern, remainder)
            curve.extend(remainder_pattern)

        return curve[:num_chapters]

    def _scale_pattern(self, base_pattern: list[str], target_length: int) -> list[str]:
        """
        将基础模式缩放到目标长度。

        使用等间距采样确保节奏分布均匀。

        Args:
            base_pattern: 基础节奏模式
            target_length: 目标长度

        Returns:
            list[str]: 缩放后的节奏类型列表
        """
        if target_length <= 0:
            return []
        if target_length >= len(base_pattern):
            return base_pattern[:target_length]

        result = []
        for i in range(target_length):
            # 等间距采样
            index = int(i * len(base_pattern) / target_length)
            result.append(base_pattern[index])

        return result

    # ============================================================
    # 字数控制
    # ============================================================

    def get_target_word_count(
        self,
        chapter_num: int,
        original_chapters: list,
    ) -> tuple[int, int]:
        """
        获取目标字数范围（基准 +/- 10%）。

        Args:
            chapter_num: 章节序号
            original_chapters: 已生成章节的字数列表（用于动态调整基准）

        Returns:
            tuple[int, int]: (目标字数, 允许偏差)
        """
        # 基准字数从上下文管理器的 novel_info 获取
        base_target = self._context._novel_info.chapter_words_target or 3000

        # 如果有已生成章节的字数数据，使用滑动平均微调
        if original_chapters:
            recent = original_chapters[-5:]
            avg_words = sum(recent) / len(recent)
            # 轻微向平均值靠拢（30%权重），保持稳定性
            base_target = int(base_target * 0.7 + avg_words * 0.3)

        tolerance = int(base_target * WORD_COUNT_TOLERANCE)
        return (base_target, tolerance)

    def check_word_count(
        self,
        text: str,
        target: int,
        tolerance: float = WORD_COUNT_TOLERANCE,
    ) -> dict:
        """
        检查字数是否在目标范围内。

        Args:
            text: 待检查的文本
            target: 目标字数
            tolerance: 容差比例（默认0.1，即 +/- 10%）

        Returns:
            dict: 字数检查结果，包含：
              - current: 当前字数
              - target: 目标字数
              - min: 最小允许字数
              - max: 最大允许字数
              - pass: 是否通过
              - diff: 与目标的差值（正数表示超出）
              - diff_percent: 差值百分比
        """
        current = self._count_words(text)
        min_words = int(target * (1 - tolerance))
        max_words = int(target * (1 + tolerance))
        diff = current - target
        diff_percent = (diff / target * 100) if target > 0 else 0

        return {
            "current": current,
            "target": target,
            "min": min_words,
            "max": max_words,
            "pass": min_words <= current <= max_words,
            "diff": diff,
            "diff_percent": round(diff_percent, 1),
        }

    def _count_words(self, text: str) -> int:
        """
        统计中文字数。

        策略：统计所有非空白字符（中文字符、标点、数字、英文字母均计为1字）。

        Args:
            text: 文本

        Returns:
            int: 字数
        """
        if not text:
            return 0
        # 去除空白字符后统计
        return len(text.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", ""))

    async def adjust_word_count(self, text: str, target: int) -> str:
        """
        调整字数到目标范围。

        字数不足：增加环境描写、心理描写、细节描写
        字数超出：精简冗余描写、合并相似段落

        Args:
            text: 原始文本
            target: 目标字数

        Returns:
            str: 调整后的文本
        """
        current = self._count_words(text)
        diff = current - target
        diff_ratio = abs(diff) / target if target > 0 else 0

        # 如果已经在容差范围内，直接返回
        if abs(diff) <= target * WORD_COUNT_TOLERANCE:
            return text

        if diff < 0:
            # 字数不足，需要扩充
            return await self._expand_text(text, target, -diff)
        else:
            # 字数超出，需要精简
            return self._compress_text(text, target, diff)

    async def _expand_text(self, text: str, target: int, deficit: int) -> str:
        """
        扩充文本以满足字数要求。

        策略：
          1. 在段落间插入环境描写
          2. 在对话后增加心理描写
          3. 在动作场景中增加细节描写

        Args:
            text: 原始文本
            target: 目标字数
            deficit: 缺少的字数

        Returns:
            str: 扩充后的文本
        """
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return text

        # 需要增加的字数（目标 deficit 的 1.2 倍，留有余量）
        needed_chars = int(deficit * 1.2)

        # 扩充提示词
        expand_prompt = (
            f"请为以下小说文本增加约{needed_chars}字的描写内容。"
            f"要求：\n"
            f"1. 在适当位置增加环境描写（天气、光线、气味、声音等感官细节）\n"
            f"2. 在角色对话后增加心理活动描写\n"
            f"3. 在动作场景中增加细节描写（动作分解、表情变化等）\n"
            f"4. 保持原文风格和语气不变\n"
            f"5. 不要改变原有情节走向\n"
            f"6. 直接输出扩充后的完整文本，不要添加任何解释\n\n"
            f"原文：\n{text}"
        )

        try:
            messages = [
                {"role": "system", "content": "你是一位专业的小说编辑，擅长在不改变情节的前提下丰富文本细节。"},
                {"role": "user", "content": expand_prompt},
            ]

            expanded = await self._llm.call_with_retry(
                messages=messages,
                chapter_number=0,
                temperature=0.7,
            )

            if expanded and self._count_words(expanded) >= target * 0.9:
                return expanded

        except Exception as e:
            logger.warning(f"LLM扩充文本失败: {e}")

        # LLM 失败时使用规则方法扩充
        return self._rule_based_expand(text, deficit)

    def _rule_based_expand(self, text: str, deficit: int) -> str:
        """
        基于规则的文本扩充（LLM失败时的后备方案）。

        Args:
            text: 原始文本
            deficit: 缺少的字数

        Returns:
            str: 扩充后的文本
        """
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return text

        # 环境描写模板
        env_templates = [
            "四周的空气似乎凝固了，一丝微风拂过，带起地上的落叶。",
            "远处传来几声鸟鸣，在这寂静的氛围中显得格外清晰。",
            "阳光透过云层洒下斑驳的光影，为这片大地披上了一层金色的外衣。",
            "空气中弥漫着淡淡的草木清香，让人精神为之一振。",
            "天边的云霞渐渐染上了橘红色，预示着黄昏即将来临。",
        ]

        # 心理描写模板
        mind_templates = [
            "他的心中涌起一股难以言喻的感觉，似乎有什么东西正在悄然改变。",
            "这一刻，她的内心翻涌着复杂的情绪，久久不能平静。",
            "他深吸一口气，努力让自己冷静下来，脑中快速思索着对策。",
            "一种莫名的预感涌上心头，让他不由得提高了警惕。",
            "她的目光微微闪烁，似乎在权衡着什么，最终下定了决心。",
        ]

        import random
        expanded_paragraphs = list(paragraphs)
        chars_added = 0
        insert_positions = list(range(1, len(paragraphs)))
        random.shuffle(insert_positions)

        for pos in insert_positions:
            if chars_added >= deficit:
                break

            # 在段落间插入描写
            if chars_added < deficit * 0.5:
                template = random.choice(env_templates + mind_templates)
            else:
                template = random.choice(env_templates)

            expanded_paragraphs.insert(pos, template)
            chars_added += len(template)

        return "\n".join(expanded_paragraphs)

    def _compress_text(self, text: str, target: int, excess: int) -> str:
        """
        精简文本以满足字数要求。

        策略：
          1. 识别并删除过度冗余的形容词堆叠
          2. 合并语义相似的相邻段落
          3. 精简过长的环境描写段落
          4. 删除重复的情感表达

        Args:
            text: 原始文本
            target: 目标字数
            excess: 超出的字数

        Returns:
            str: 精简后的文本
        """
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return text

        # 需要删除的字数
        needed_cut = int(excess * 1.1)

        # 策略1: 精简过长的段落（超过200字的段落）
        compressed = []
        cut_total = 0

        for para in paragraphs:
            if cut_total >= needed_cut:
                compressed.append(para)
                continue

            para_len = self._count_words(para)

            if para_len > 200 and cut_total < needed_cut:
                # 尝试精简：删除冗余形容词和重复表达
                trimmed = self._trim_paragraph(para, needed_cut - cut_total)
                trimmed_len = self._count_words(trimmed)
                cut_total += para_len - trimmed_len
                compressed.append(trimmed)
            else:
                compressed.append(para)

        # 策略2: 如果还不够，合并短段落
        if cut_total < needed_cut and len(compressed) > 3:
            compressed = self._merge_short_paragraphs(
                compressed, needed_cut - cut_total
            )

        return "\n".join(compressed)

    def _trim_paragraph(self, paragraph: str, max_cut: int) -> str:
        """
        精简单个段落。

        Args:
            paragraph: 段落文本
            max_cut: 最多可删除的字数

        Returns:
            str: 精简后的段落
        """
        # 删除重复的形容词（如：非常非常 -> 非常）
        text = re.sub(r'(非常|十分|极其|特别|格外){2,}', r'\1', paragraph)

        # 精简冗余的描写短语
        redundancy_patterns = [
            (r'不由自主地', ''),
            (r'下意识地', ''),
            (r'情不自禁地', ''),
            (r'似乎好像是', '好像是'),
            (r'慢慢地、缓缓地', '缓缓地'),
            (r'一步一步地', '一步步地'),
        ]
        for pattern, replacement in redundancy_patterns:
            text = re.sub(pattern, replacement, text)

        # 如果精简后仍超出预算，截断过长的句子
        current_cut = self._count_words(paragraph) - self._count_words(text)
        if current_cut < max_cut:
            # 按句子分割，删除最不重要的句子
            sentences = re.split(r'([。！？])', text)
            if len(sentences) > 4:
                # 保留首尾，删除中间较短的句子
                kept = [sentences[0], sentences[1]]  # 首句
                middle = sentences[2:-2]
                kept.append(sentences[-2])  # 尾句标点
                kept.append(sentences[-1])  # 尾句

                # 从中间句子中删除较短的
                remaining_cut = max_cut - current_cut
                for i in range(0, len(middle) - 1, 2):
                    sentence = middle[i] + (middle[i + 1] if i + 1 < len(middle) else "")
                    if self._count_words(sentence) < 30 and remaining_cut > 0:
                        remaining_cut -= self._count_words(sentence)
                    else:
                        kept.append(middle[i])
                        if i + 1 < len(middle):
                            kept.append(middle[i + 1])

                text = "".join(kept)

        return text

    def _merge_short_paragraphs(
        self, paragraphs: list[str], max_cut: int
    ) -> list[str]:
        """
        合并短段落以减少总字数。

        Args:
            paragraphs: 段落列表
            max_cut: 需要减少的字数

        Returns:
            list[str]: 合并后的段落列表
        """
        if len(paragraphs) <= 2:
            return paragraphs

        merged = []
        cut_total = 0
        i = 0

        while i < len(paragraphs):
            if cut_total >= max_cut:
                merged.append(paragraphs[i])
                i += 1
                continue

            current = paragraphs[i]
            current_len = self._count_words(current)

            # 如果当前段落很短（< 50字），尝试与下一段合并
            if current_len < 50 and i + 1 < len(paragraphs):
                next_para = paragraphs[i + 1]
                # 合并时删除过渡句
                combined = current + next_para
                # 删除合并处的过渡词
                combined = re.sub(r'与此同时，?', '', combined)
                combined = re.sub(r'另外，?', '', combined)
                merged.append(combined)
                cut_total += self._count_words(current) + self._count_words(next_para) - self._count_words(combined)
                i += 2
            else:
                merged.append(current)
                i += 1

        return merged

    # ============================================================
    # 高潮类型选择
    # ============================================================

    def select_climax_type(
        self,
        chapter_num: int,
        used_types: Optional[list[str]] = None,
    ) -> str:
        """
        选择高潮类型，避免重复。

        类型池：战斗高潮、情感高潮、真相揭示、逆转、能力突破、团队胜利

        Args:
            chapter_num: 章节序号
            used_types: 已使用的高潮类型列表

        Returns:
            str: 选中的高潮类型
        """
        if used_types is None:
            used_types = self._used_climax_types

        # 找出未使用的类型
        available = [t for t in CLIMAX_TYPES if t not in used_types]

        if not available:
            # 所有类型都已使用，重置
            self._used_climax_types = []
            available = list(CLIMAX_TYPES)

        # 根据章节序号选择（增加多样性）
        index = (chapter_num - 1) % len(available)
        selected = available[index]

        self._used_climax_types.append(selected)
        return selected

    # ============================================================
    # 内部辅助方法
    # ============================================================

    async def _ensure_word_count(
        self,
        chapter: Chapter,
        target: int,
        chapter_num: int,
    ) -> Chapter:
        """
        确保章节字数在目标范围内。

        Args:
            chapter: 章节对象
            target: 目标字数
            chapter_num: 章节序号

        Returns:
            Chapter: 字数调整后的章节
        """
        for attempt in range(WORD_COUNT_ADJUST_RETRIES):
            result = self.check_word_count(chapter.content, target)

            if result["pass"]:
                break

            logger.info(
                f"第{chapter_num}章字数调整 (尝试{attempt + 1}): "
                f"当前{result['current']}字, "
                f"目标{result['target']}字 "
                f"(范围{result['min']}-{result['max']}), "
                f"差值{result['diff']:+d}字 ({result['diff_percent']:+.1f}%)"
            )

            # 调整字数
            adjusted_content = await self.adjust_word_count(
                chapter.content, target
            )
            chapter.content = adjusted_content
            chapter.word_count = self._count_words(adjusted_content)

        # 最终检查
        final_result = self.check_word_count(chapter.content, target)
        if not final_result["pass"]:
            logger.warning(
                f"第{chapter_num}章字数调整后仍未达标: "
                f"{final_result['current']}字 "
                f"(目标{final_result['target']}, "
                f"范围{final_result['min']}-{final_result['max']})"
            )

        return chapter

    async def _fix_consistency_issues(
        self,
        chapter: Chapter,
        issues: list[dict],
    ) -> Chapter:
        """
        尝试修复一致性问题的章节。

        Args:
            chapter: 章节对象
            issues: 一致性问题列表

        Returns:
            Chapter: 修复后的章节
        """
        # 构建修复提示
        fix_instructions = []
        for issue in issues[:3]:  # 最多修复3个问题
            fix_instructions.append(
                f"- 问题: {issue['issue']}\n  修改建议: {issue['suggestion']}"
            )

        fix_prompt = (
            f"请修复以下小说文本中的一致性问题：\n\n"
            f"问题列表：\n"
            + "\n".join(fix_instructions)
            + f"\n\n要求：\n"
            f"1. 严格按照修改建议进行修复\n"
            f"2. 保持文本整体风格和流畅性\n"
            f"3. 只修改涉及问题的部分，不要大范围重写\n"
            f"4. 直接输出修复后的完整文本\n\n"
            f"原文：\n{chapter.content}"
        )

        try:
            messages = [
                {"role": "system", "content": "你是一位专业的小说编辑，负责修复文本中的逻辑一致性问题。"},
                {"role": "user", "content": fix_prompt},
            ]

            fixed_content = await self._llm.call_with_retry(
                messages=messages,
                chapter_number=chapter.chapter_number,
                temperature=0.3,  # 低温度以保持修改精确
            )

            if fixed_content:
                chapter.content = fixed_content
                chapter.word_count = self._count_words(fixed_content)
                logger.info(
                    f"第{chapter.chapter_number}章一致性修复完成"
                )

        except Exception as e:
            logger.warning(
                f"第{chapter.chapter_number}章一致性修复失败: {e}"
            )

        return chapter

    def _build_novel_info_for_chapter(
        self,
        chapter_num: int,
        volume_plan: dict,
        rhythm_type: str,
    ) -> NovelInfo:
        """
        为单章生成构建精简的 NovelInfo。

        避免传递完整的大对象，只保留写作所需的信息。

        Args:
            chapter_num: 章节序号
            volume_plan: 卷计划
            rhythm_type: 节奏类型

        Returns:
            NovelInfo: 精简的小说信息
        """
        novel_info = self._context._novel_info

        # 返回原始对象（Writer 内部会按需取用）
        # 这里可以后续优化为构建精简版本
        return novel_info

    async def generate_chapter(
        self,
        chapter_number: int,
        novel_info: NovelInfo,
        max_retries: int = 3,
    ) -> Chapter:
        """
        生成单个章节（完整流程）。

        保留与旧接口的兼容性。

        Args:
            chapter_number: 章节序号
            novel_info: 小说信息
            max_retries: 最大重试次数

        Returns:
            Chapter: 生成的章节
        """
        logger.info(f"=== 开始生成第{chapter_number}章 ===")

        # 重置章节成本
        self._llm.reset_chapter_cost()

        # 获取写作上下文
        chapter_plan = {
            "chapter_number": chapter_number,
            "rhythm_type": "development",
            "tension": 3,
            "volume_num": 1,
        }
        context = self._context.get_writing_context(chapter_plan)

        # 获取上一章大纲
        previous_outline = None
        if self._generated_chapters:
            for ch in reversed(self._generated_chapters):
                if ch.outline:
                    previous_outline = ch.outline
                    break

        # 1. 生成大纲
        outline = await self._writer.generate_chapter_outline(
            chapter_number=chapter_number,
            novel_info=novel_info,
            previous_outline=previous_outline,
        )

        # 2. 生成正文
        chapter = await self._writer.generate_chapter_content(
            outline=outline,
            novel_info=novel_info,
            context=context,
        )

        # 3. 检查字数，不足则续写
        target_words = novel_info.chapter_words_target
        chapter = await self._ensure_word_count(chapter, target_words, chapter_number)

        # 4. 更新上下文
        self._context.update_after_chapter(chapter)

        # 5. 更新状态
        chapter.status = ChapterStatus.COMPLETED
        chapter.updated_at = datetime.now()

        self._generated_chapters.append(chapter)

        logger.info(
            f"=== 第{chapter_number}章生成完成: "
            f"{chapter.word_count}字 ==="
        )

        return chapter

    async def regenerate_chapter(
        self,
        chapter: Chapter,
        novel_info: NovelInfo,
        feedback: str = "",
    ) -> Chapter:
        """
        重新生成章节。

        Args:
            chapter: 原章节
            novel_info: 小说信息
            feedback: 修改反馈

        Returns:
            Chapter: 重新生成的章节
        """
        logger.info(f"重新生成第{chapter.chapter_number}章...")

        revised = await self._writer.revise_chapter(chapter, feedback)
        revised.word_count = self._count_words(revised.content)
        return revised

    def get_generation_stats(self) -> dict[str, Any]:
        """
        获取生成统计信息。

        Returns:
            dict: 包含生成统计的字典
        """
        if not self._generated_chapters:
            return {
                "total_chapters": 0,
                "total_words": 0,
                "avg_words_per_chapter": 0,
                "word_count_pass_rate": 0.0,
            }

        word_counts = [c.word_count for c in self._generated_chapters]
        target = self._context._novel_info.chapter_words_target or 3000

        pass_count = sum(
            1 for wc in word_counts
            if int(target * (1 - WORD_COUNT_TOLERANCE))
            <= wc
            <= int(target * (1 + WORD_COUNT_TOLERANCE))
        )

        return {
            "total_chapters": len(self._generated_chapters),
            "total_words": sum(word_counts),
            "avg_words_per_chapter": sum(word_counts) / len(word_counts),
            "min_words": min(word_counts),
            "max_words": max(word_counts),
            "word_count_pass_rate": pass_count / len(word_counts),
            "used_climax_types": list(self._used_climax_types),
        }
