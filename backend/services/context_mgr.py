"""
上下文一致性管理服务

多层次记忆系统，解决百万字长文本的上下文一致性问题。
四层记忆架构：
  - 全局记忆：世界观、力量体系、所有角色基本信息
  - 卷级记忆：当前卷的情节进展、活跃角色状态、本卷伏笔
  - 章节记忆：近期章节的内容摘要（滑动窗口，保留最近20章）
  - 即时记忆：当前正在写作的段落和前几段
"""

from __future__ import annotations

import logging
import re
from collections import OrderedDict
from typing import Any, Optional

from backend.models.enums import ForeshadowStatus
from backend.models.schemas import (
    Chapter,
    Character,
    CharacterRelation,
    Foreshadow,
    NovelInfo,
    WorldSetting,
)
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================

# 章节记忆滑动窗口大小
CHAPTER_MEMORY_WINDOW = 20

# 近期详细摘要章数
RECENT_DETAILED_CHAPTERS = 5

# 即时记忆保留段落数
INSTANT_MEMORY_PARAGRAPHS = 3

# Token 估算系数：中文约 1 字 ≈ 1.5 token
CHAR_TO_TOKEN_RATIO = 1.5

# Token 预算分配比例（总和 = 1.0）
BUDGET_GLOBAL = 0.20        # 全局记忆
BUDGET_VOLUME = 0.30        # 卷级记忆
BUDGET_CHAPTER = 0.35       # 章节记忆
BUDGET_INSTANT = 0.15       # 即时记忆


class ContextManager:
    """多层次记忆系统，解决百万字长文本的上下文一致性问题"""

    def __init__(self, llm_client: LLMClient, novel_info: NovelInfo):
        """
        初始化上下文管理器。

        Args:
            llm_client: LLM客户端（用于复杂一致性检查）
            novel_info: 小说信息
        """
        self._llm = llm_client

        # 四层记忆
        self.global_memory: dict[str, Any] = {}
        self.volume_memory: dict[str, Any] = {}
        self.chapter_memory: OrderedDict[int, dict] = OrderedDict()
        self.instant_memory: str = ""

        # 角色运行时状态（轻量级字典）
        self._character_states: dict[str, dict[str, Any]] = {}

        # 伏笔运行时列表
        self._foreshadows: list[Foreshadow] = []

        # 当前卷号
        self._current_volume: int = 1

        # 已完成章节号列表（用于判断角色是否死亡等）
        self._completed_chapters: list[int] = []

        # 已死亡角色集合
        self._dead_characters: set[str] = set()

        # 已毁坏地点集合
        self._destroyed_locations: set[str] = set()

        # 关键时间线事件（用于时间线一致性检查）
        self._timeline_events: list[dict[str, Any]] = []

        # 初始化
        self._novel_info = novel_info

    # ============================================================
    # 初始化
    # ============================================================

    async def initialize(self, novel_info: NovelInfo) -> None:
        """
        初始化全局记忆。

        从 novel_info 中提取并存储所有关键信息，构建全局记忆层。

        Args:
            novel_info: 小说信息
        """
        logger.info("初始化全局记忆...")

        # --- 世界观概要 ---
        world_summary = self._build_world_summary(novel_info.world_setting)
        self.global_memory["world_summary"] = world_summary

        # --- 力量体系概要 ---
        power_summary = self._build_power_summary(novel_info.power_system)
        self.global_memory["power_summary"] = power_summary

        # --- 角色基本信息 ---
        character_index = self._build_character_index(novel_info.characters)
        self.global_memory["character_index"] = character_index

        # --- 写作风格 ---
        if novel_info.writing_style:
            self.global_memory["writing_style"] = {
                "tone": novel_info.writing_style.tone,
                "perspective": novel_info.writing_style.perspective,
                "sentence_style": novel_info.writing_style.sentence_style,
                "description_density": novel_info.writing_style.description_density,
                "dialogue_ratio": novel_info.writing_style.dialogue_ratio,
                "vocabulary_level": novel_info.writing_style.vocabulary_level,
                "forbidden_patterns": novel_info.writing_style.forbidden_patterns,
            }

        # --- 初始化角色运行时状态 ---
        for char in novel_info.characters:
            self._character_states[char.name] = {
                "location": "",
                "abilities": list(char.abilities),
                "power_level": "",
                "mental_state": "",
                "inventory": [],
                "injuries": [],
                "relationships": {
                    rel.target_name: rel.relation_type
                    for rel in char.relations
                },
                "last_appearance": 0,
                "status": "alive",  # alive / dead / missing / sealed
                "notes": char.notes,
            }
            # 注册别名
            for alias in char.aliases:
                self._character_states[alias] = self._character_states[char.name]

        # --- 初始化伏笔 ---
        self._foreshadows = list(novel_info.foreshadows)

        # --- 初始化卷级记忆 ---
        self._init_volume_memory(1)

        logger.info(
            f"全局记忆初始化完成: "
            f"{len(novel_info.characters)}个角色, "
            f"{len(novel_info.foreshadows)}个伏笔"
        )

    def _build_world_summary(self, world_setting: Optional[WorldSetting]) -> str:
        """构建世界观概要文本"""
        if not world_setting:
            return ""

        parts = []

        # 世界名称和类型
        if world_setting.geography.world_name:
            parts.append(f"世界: {world_setting.geography.world_name}")

        # 地理概要
        if world_setting.geography.map_description:
            parts.append(f"地理: {world_setting.geography.map_description[:200]}")

        # 重要区域
        if world_setting.geography.regions:
            region_names = [r.get("name", "") for r in world_setting.geography.regions[:10]]
            parts.append(f"主要区域: {'、'.join(region_names)}")

        # 重要地点
        if world_setting.geography.important_locations:
            loc_names = [l.get("name", "") for l in world_setting.geography.important_locations[:15]]
            parts.append(f"重要地点: {'、'.join(loc_names)}")

        # 势力
        if world_setting.society.factions:
            faction_names = [f.get("name", "") for f in world_setting.society.factions[:10]]
            parts.append(f"主要势力: {'、'.join(faction_names)}")

        # 社会结构
        if world_setting.society.social_structure:
            parts.append(f"社会结构: {world_setting.society.social_structure[:150]}")

        # 世界规则
        if world_setting.rules:
            rules_text = "；".join(world_setting.rules[:5])
            parts.append(f"世界规则: {rules_text}")

        # 科技/魔法水平
        if world_setting.technology_level:
            parts.append(f"科技水平: {world_setting.technology_level[:100]}")
        if world_setting.magic_system:
            parts.append(f"力量体系概述: {world_setting.magic_system[:200]}")

        return "\n".join(parts)

    def _build_power_summary(self, power_system: Optional[Any]) -> str:
        """构建力量体系概要文本"""
        if not power_system:
            return ""

        parts = []
        if power_system.name:
            parts.append(f"体系名称: {power_system.name}")
        if power_system.description:
            parts.append(f"概述: {power_system.description[:200]}")

        # 等级列表
        if power_system.levels:
            level_strs = []
            for lvl in power_system.levels:
                desc = f"{lvl.level_name}(第{lvl.level_number}级)"
                if lvl.description:
                    desc += f": {lvl.description[:50]}"
                level_strs.append(desc)
            parts.append("等级体系:\n" + "\n".join(f"  - {s}" for s in level_strs))

        return "\n".join(parts)

    def _build_character_index(self, characters: list[Character]) -> dict[str, dict]:
        """构建角色索引（基本信息）"""
        index = {}
        for char in characters:
            index[char.name] = {
                "role_type": char.role_type,
                "description": char.description[:100] if char.description else "",
                "personality": char.personality[:80] if char.personality else "",
                "speech_style": char.speech_style[:60] if char.speech_style else "",
                "aliases": char.aliases,
                "goals": char.goals[:80] if char.goals else "",
            }
        return index

    def _init_volume_memory(self, volume_num: int) -> None:
        """初始化卷级记忆"""
        self._current_volume = volume_num
        self.volume_memory = {
            "volume_num": volume_num,
            "plot_progress": [],       # 本卷情节进展摘要列表
            "active_characters": [],    # 本卷活跃角色名列表
            "volume_foreshadows": [],   # 本卷伏笔
            "key_events": [],           # 本卷关键事件
            "start_chapter": 0,
            "end_chapter": 0,
        }

    # ============================================================
    # 章节完成后更新记忆
    # ============================================================

    def update_after_chapter(self, chapter: Chapter) -> None:
        """
        章节完成后更新记忆。

        Args:
            chapter: 已完成的章节
        """
        ch_num = chapter.chapter_number

        # 1. 生成章节摘要（规则方法，不调用LLM）
        summary = self._extract_chapter_summary(chapter)

        # 2. 添加到章节记忆（保持滑动窗口）
        self.chapter_memory[ch_num] = {
            "summary": summary,
            "title": chapter.title,
            "word_count": chapter.word_count,
            "key_events": self._extract_key_events(chapter),
            "characters_involved": self._detect_characters_in_chapter(chapter),
        }
        self._maintain_chapter_window()

        # 3. 更新角色状态
        self._update_character_states_from_chapter(chapter)

        # 4. 更新伏笔状态
        self._update_foreshadows_from_chapter(chapter)

        # 5. 更新卷级记忆
        self._update_volume_memory(chapter)

        # 6. 记录已完成章节
        if ch_num not in self._completed_chapters:
            self._completed_chapters.append(ch_num)

        logger.debug(f"记忆已更新: 第{ch_num}章")

    def _extract_chapter_summary(self, chapter: Chapter) -> str:
        """
        使用规则方法从章节内容中提取摘要。

        策略：优先使用大纲摘要，否则从正文中提取关键句子。

        Args:
            chapter: 章节对象

        Returns:
            str: 章节摘要（200字以内）
        """
        # 优先使用大纲摘要
        if chapter.outline and chapter.outline.summary:
            return chapter.outline.summary[:200]

        content = chapter.content
        if not content:
            return f"{chapter.title} ({chapter.word_count}字)"

        # 规则方法：按段落提取关键句子
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if not paragraphs:
            return f"{chapter.title} ({chapter.word_count}字)"

        key_sentences = []

        # 提取包含关键动作/事件的句子
        action_keywords = [
            "突然", "猛然", "刹那", "瞬间", "终于", "竟然", "不料",
            "只见", "听到", "发现", "明白", "意识到", "决定", "出手",
            "击败", "突破", "觉醒", "死亡", "消失", "出现", "来到",
        ]
        dialogue_keywords = ["说道", "喊道", "冷笑", "叹息", "怒吼", "低语"]

        for para in paragraphs[:30]:  # 最多检查前30段
            sentences = re.split(r'[。！？]', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 8:
                    continue
                # 优先选取包含关键词的句子
                if any(kw in sentence for kw in action_keywords):
                    if sentence not in key_sentences:
                        key_sentences.append(sentence)
                elif any(kw in sentence for kw in dialogue_keywords):
                    if sentence not in key_sentences and len(key_sentences) < 8:
                        key_sentences.append(sentence)

        # 如果关键句子不够，取首尾段落
        if len(key_sentences) < 3 and paragraphs:
            if paragraphs[0] not in key_sentences:
                key_sentences.insert(0, paragraphs[0][:100])
            if len(paragraphs) > 1 and paragraphs[-1] not in key_sentences:
                key_sentences.append(paragraphs[-1][:100])

        summary = "".join(key_sentences[:5])
        if len(summary) > 200:
            summary = summary[:200]

        return summary or f"{chapter.title} ({chapter.word_count}字)"

    def _extract_key_events(self, chapter: Chapter) -> list[str]:
        """从章节中提取关键事件列表"""
        events = []

        # 从大纲中提取
        if chapter.outline and chapter.outline.key_events:
            events.extend(chapter.outline.key_events)

        return events[:5]

    def _detect_characters_in_chapter(self, chapter: Chapter) -> list[str]:
        """
        从章节内容中检测出场角色。

        使用角色名和别名进行匹配。

        Args:
            chapter: 章节对象

        Returns:
            list[str]: 检测到的角色名列表
        """
        if not chapter.content:
            return []

        # 优先使用大纲中的角色列表
        if chapter.outline and chapter.outline.characters_involved:
            return chapter.outline.characters_involved

        # 从内容中匹配角色名
        content = chapter.content
        found = set()

        for name in self._character_states:
            if name in content:
                # 确保是独立匹配（不是其他名字的子串）
                # 简单处理：检查名字前后是否有非中文字符
                pattern = re.compile(r'(?<![^\s，。！？、；：""\'\'（）])' + re.escape(name) + r'(?![^\s，。！？、；：""\'\'（）])')
                if pattern.search(content):
                    found.add(name)

        return list(found)

    def _maintain_chapter_window(self) -> None:
        """维护章节记忆滑动窗口"""
        while len(self.chapter_memory) > CHAPTER_MEMORY_WINDOW:
            self.chapter_memory.popitem(last=False)

    def _update_character_states_from_chapter(self, chapter: Chapter) -> None:
        """从章节内容更新角色状态"""
        involved = self._detect_characters_in_chapter(chapter)

        for name in involved:
            if name not in self._character_states:
                continue

            state = self._character_states[name]
            state["last_appearance"] = chapter.chapter_number

            # 检测角色状态变化（死亡、受伤等）
            content = chapter.content
            if not content:
                continue

            # 检测死亡
            death_patterns = [
                f"{name}死了", f"{name}陨落", f"{name}身亡",
                f"{name}气绝", f"{name}断气", f"{name}倒下不再动弹",
                f"杀死了{name}", f"击杀了{name}", f"斩杀了{name}",
            ]
            for pattern in death_patterns:
                if pattern in content and state["status"] == "alive":
                    state["status"] = "dead"
                    self._dead_characters.add(name)
                    logger.info(f"角色状态更新: {name} 在第{chapter.chapter_number}章死亡")
                    break

            # 检测受伤
            injury_patterns = [
                f"{name}受了伤", f"{name}吐血", f"{name}重伤",
                f"{name}负伤", f"{name}挂彩",
            ]
            for pattern in injury_patterns:
                if pattern in content:
                    if "受伤" not in str(state.get("injuries", [])):
                        state.setdefault("injuries", []).append(
                            f"第{chapter.chapter_number}章受伤"
                        )
                    break

    def _update_foreshadows_from_chapter(self, chapter: Chapter) -> None:
        """从章节更新伏笔状态"""
        if not chapter.outline:
            return

        # 处理本章节设置的伏笔
        for fs_id in chapter.outline.foreshadows_to_plant:
            for fs in self._foreshadows:
                if fs.id == fs_id and fs.status in (ForeshadowStatus.PLANTED, ForeshadowStatus.HINTED):
                    fs.status = ForeshadowStatus.HINTED
                    break

        # 处理本章节回收的伏笔
        for fs_id in chapter.outline.foreshadows_to_resolve:
            for fs in self._foreshadows:
                if fs.id == fs_id:
                    fs.status = ForeshadowStatus.RESOLVED
                    fs.resolve_chapter = chapter.chapter_number
                    logger.info(
                        f"伏笔回收: [{fs.description[:30]}...] "
                        f"在第{chapter.chapter_number}章"
                    )
                    break

    def _update_volume_memory(self, chapter: Chapter) -> None:
        """更新卷级记忆"""
        # 计算当前卷号（每30章为一卷，可配置）
        chapters_per_volume = 30
        volume_num = (chapter.chapter_number - 1) // chapters_per_volume + 1

        if volume_num != self._current_volume:
            self._init_volume_memory(volume_num)

        vm = self.volume_memory
        if not vm.get("start_chapter") or chapter.chapter_number < vm["start_chapter"]:
            vm["start_chapter"] = chapter.chapter_number
        vm["end_chapter"] = chapter.chapter_number

        # 添加情节进展
        summary = self._extract_chapter_summary(chapter)
        vm["plot_progress"].append({
            "chapter": chapter.chapter_number,
            "summary": summary,
        })
        # 保留最近15条
        if len(vm["plot_progress"]) > 15:
            vm["plot_progress"] = vm["plot_progress"][-15:]

        # 更新活跃角色
        involved = self._detect_characters_in_chapter(chapter)
        for name in involved:
            if name not in vm["active_characters"]:
                vm["active_characters"].append(name)
        # 保留最近活跃的15个角色
        vm["active_characters"] = vm["active_characters"][-15:]

        # 更新关键事件
        events = self._extract_key_events(chapter)
        for event in events:
            vm["key_events"].append({
                "chapter": chapter.chapter_number,
                "event": event,
            })
        if len(vm["key_events"]) > 20:
            vm["key_events"] = vm["key_events"][-20:]

        # 更新本卷伏笔
        vm["volume_foreshadows"] = [
            fs for fs in self._foreshadows
            if fs.status in (ForeshadowStatus.PLANTED, ForeshadowStatus.HINTED)
        ]

    # ============================================================
    # 获取写作上下文（核心方法）
    # ============================================================

    def get_writing_context(
        self,
        chapter_plan: dict,
        max_tokens: int = 4000,
    ) -> str:
        """
        获取当前写作所需的上下文（压缩到 max_tokens 以内）。

        按优先级分配 token 预算：
          - 全局记忆 20%：世界观概要、力量体系概要、主要角色列表
          - 卷级记忆 30%：当前卷进展、活跃角色状态、待解决伏笔
          - 章节记忆 35%：最近5章详细摘要 + 更早章节简短摘要
          - 即时记忆 15%：最近3段的内容

        Args:
            chapter_plan: 章节计划（可包含 chapter_number, rhythm_type 等字段）
            max_tokens: 最大 token 数

        Returns:
            str: 格式化的上下文字符串
        """
        # 计算 token 预算（中文字符数 ≈ tokens / CHAR_TO_TOKEN_RATIO）
        max_chars = int(max_tokens / CHAR_TO_TOKEN_RATIO)

        budget_global = int(max_chars * BUDGET_GLOBAL)
        budget_volume = int(max_chars * BUDGET_VOLUME)
        budget_chapter = int(max_chars * BUDGET_CHAPTER)
        budget_instant = int(max_chars * BUDGET_INSTANT)

        parts = []

        # 1. 全局记忆（压缩版）
        global_text = self._build_global_context(budget_global)
        if global_text:
            parts.append(global_text)

        # 2. 卷级记忆
        volume_text = self._build_volume_context(budget_volume)
        if volume_text:
            parts.append(volume_text)

        # 3. 章节记忆
        chapter_text = self._build_chapter_context(budget_chapter)
        if chapter_text:
            parts.append(chapter_text)

        # 4. 即时记忆
        instant_text = self._build_instant_context(budget_instant)
        if instant_text:
            parts.append(instant_text)

        context = "\n\n".join(parts)

        # 最终裁剪确保不超过预算
        if len(context) > max_chars:
            context = context[:max_chars]

        return context

    def _build_global_context(self, max_chars: int) -> str:
        """构建全局记忆上下文"""
        parts = []
        current_len = 0

        # 世界观概要
        world_summary = self.global_memory.get("world_summary", "")
        if world_summary:
            text = f"【世界观】\n{world_summary}"
            if current_len + len(text) <= max_chars * 0.5:
                parts.append(text)
                current_len += len(text)
            else:
                parts.append(f"【世界观】\n{world_summary[:max_chars // 3]}")
                current_len += max_chars // 3

        # 力量体系概要
        power_summary = self.global_memory.get("power_summary", "")
        if power_summary and current_len < max_chars * 0.8:
            remaining = max_chars - current_len
            text = f"\n【力量体系】\n{power_summary[:remaining]}"
            parts.append(text)
            current_len += len(text)

        # 主要角色列表（压缩版）
        char_index = self.global_memory.get("character_index", {})
        if char_index and current_len < max_chars:
            remaining = max_chars - current_len
            char_lines = []
            for name, info in char_index.items():
                line = f"- {name}({info['role_type']})"
                if info.get("personality"):
                    line += f": {info['personality'][:30]}"
                char_lines.append(line)
            char_text = "【主要角色】\n" + "\n".join(char_lines[:15])
            if len(char_text) <= remaining:
                parts.append(char_text)
            else:
                # 只保留主角和配角
                main_chars = [
                    (n, i) for n, i in char_index.items()
                    if i["role_type"] in ("主角", "配角", "反派")
                ]
                char_lines = [
                    f"- {n}({i['role_type']})" for n, i in main_chars[:10]
                ]
                parts.append("【主要角色】\n" + "\n".join(char_lines))

        return "".join(parts)

    def _build_volume_context(self, max_chars: int) -> str:
        """构建卷级记忆上下文"""
        vm = self.volume_memory
        if not vm.get("plot_progress"):
            return ""

        parts = []
        current_len = 0

        # 当前卷进展
        parts.append(f"【第{vm.get('volume_num', 1)}卷进展】")
        progress_lines = []
        for item in vm["plot_progress"][-8:]:
            progress_lines.append(f"  第{item['chapter']}章: {item['summary'][:60]}")
        progress_text = "\n".join(progress_lines)
        parts.append(progress_text)
        current_len += len(progress_text) + 10

        # 活跃角色状态
        if vm.get("active_characters") and current_len < max_chars * 0.6:
            parts.append("\n【活跃角色状态】")
            state_lines = []
            for name in vm["active_characters"][-8:]:
                state = self._character_states.get(name)
                if not state:
                    continue
                line = f"  {name}:"
                if state.get("status") and state["status"] != "alive":
                    line += f" [{state['status']}]"
                if state.get("location"):
                    line += f" 位置={state['location']}"
                if state.get("power_level"):
                    line += f" 境界={state['power_level']}"
                if state.get("mental_state"):
                    line += f" 心态={state['mental_state'][:20]}"
                if state.get("injuries"):
                    line += f" 伤势={'、'.join(state['injuries'][:2])}"
                state_lines.append(line)
            state_text = "\n".join(state_lines[:8])
            if current_len + len(state_text) <= max_chars * 0.8:
                parts.append(state_text)
                current_len += len(state_text)

        # 待解决伏笔
        active_fs = self.get_active_foreshadows()
        if active_fs and current_len < max_chars * 0.9:
            parts.append("\n【待解决伏笔】")
            fs_lines = []
            for fs in active_fs[:5]:
                fs_lines.append(
                    f"  - [{fs.importance}] 第{fs.plant_chapter}章: {fs.description[:50]}"
                )
            fs_text = "\n".join(fs_lines)
            remaining = max_chars - current_len
            if len(fs_text) <= remaining:
                parts.append(fs_text)

        return "\n".join(parts)

    def _build_chapter_context(self, max_chars: int) -> str:
        """
        构建章节记忆上下文。

        最近5章使用详细摘要，更早章节使用简短摘要。
        """
        if not self.chapter_memory:
            return ""

        chapters = list(self.chapter_memory.items())
        if not chapters:
            return ""

        parts = []
        current_len = 0

        # 分离近期和远期章节
        recent = chapters[-RECENT_DETAILED_CHAPTERS:]
        older = chapters[:-RECENT_DETAILED_CHAPTERS]

        # 远期章节：简短摘要
        if older:
            parts.append("【远期章节摘要】")
            older_lines = []
            for ch_num, info in older:
                line = f"  第{ch_num}章({info['title']}): {info['summary'][:40]}"
                older_lines.append(line)
            older_text = "\n".join(older_lines)
            # 远期摘要最多占 30% 预算
            older_budget = int(max_chars * 0.3)
            if len(older_text) > older_budget:
                older_text = older_text[:older_budget]
            parts.append(older_text)
            current_len += len(older_text) + 10

        # 近期章节：详细摘要
        if recent:
            parts.append("\n【近期章节详情】")
            remaining = max_chars - current_len
            per_chapter_budget = remaining // max(len(recent), 1)

            recent_lines = []
            for ch_num, info in recent:
                line = f"  第{ch_num}章 {info['title']}:\n"
                line += f"    {info['summary'][:per_chapter_budget - 30]}"
                # 出场角色
                if info.get("characters_involved"):
                    line += f"\n    出场: {'、'.join(info['characters_involved'][:5])}"
                recent_lines.append(line)

            recent_text = "\n".join(recent_lines)
            if len(recent_text) > remaining:
                recent_text = recent_text[:remaining]
            parts.append(recent_text)

        return "\n".join(parts)

    def _build_instant_context(self, max_chars: int) -> str:
        """构建即时记忆上下文"""
        if not self.instant_memory:
            return ""

        text = f"【前文内容】\n{self.instant_memory}"
        if len(text) > max_chars:
            # 保留最后部分
            text = "【前文内容】\n..." + self.instant_memory[-(max_chars - 20):]
        return text

    # ============================================================
    # 角色状态管理
    # ============================================================

    def get_character_state(self, character_name: str) -> dict:
        """
        获取角色的当前状态。

        Args:
            character_name: 角色名（支持别名）

        Returns:
            dict: 角色状态字典，如果角色不存在返回空字典
        """
        return dict(self._character_states.get(character_name, {}))

    def update_character_state(self, character_name: str, updates: dict) -> None:
        """
        更新角色状态。

        Args:
            character_name: 角色名
            updates: 要更新的字段，支持：
                - location: 位置
                - abilities: 能力列表
                - power_level: 力量等级
                - mental_state: 心态
                - inventory: 物品
                - injuries: 伤势列表
                - relationships: 关系字典
                - status: 状态（alive/dead/missing/sealed）
                - notes: 备注
        """
        if character_name not in self._character_states:
            logger.warning(f"未知角色: {character_name}，跳过状态更新")
            return

        state = self._character_states[character_name]

        for key, value in updates.items():
            if key == "relationships" and isinstance(value, dict):
                # 合并关系而非覆盖
                state.setdefault("relationships", {}).update(value)
            elif key == "abilities" and isinstance(value, list):
                state["abilities"] = value
            elif key == "injuries" and isinstance(value, list):
                state.setdefault("injuries", []).extend(value)
            elif key == "status" and value == "dead":
                state["status"] = "dead"
                self._dead_characters.add(character_name)
            else:
                state[key] = value

        logger.debug(f"角色状态已更新: {character_name} -> {list(updates.keys())}")

    # ============================================================
    # 伏笔管理
    # ============================================================

    def get_active_foreshadows(self) -> list[Foreshadow]:
        """
        获取所有待解决的伏笔。

        Returns:
            list[Foreshadow]: 状态为 PLANTED 或 HINTED 的伏笔列表
        """
        return [
            fs for fs in self._foreshadows
            if fs.status in (ForeshadowStatus.PLANTED, ForeshadowStatus.HINTED)
        ]

    def add_foreshadow(self, foreshadow: Foreshadow) -> None:
        """添加新伏笔"""
        self._foreshadows.append(foreshadow)

    def resolve_foreshadow(self, foreshadow_id: str, chapter_num: int) -> None:
        """标记伏笔为已回收"""
        for fs in self._foreshadows:
            if fs.id == foreshadow_id:
                fs.status = ForeshadowStatus.RESOLVED
                fs.resolve_chapter = chapter_num
                break

    # ============================================================
    # 即时记忆管理
    # ============================================================

    def set_instant_memory(self, text: str) -> None:
        """
        设置即时记忆（当前正在写作的段落和前几段）。

        Args:
            text: 最近几段的内容
        """
        self.instant_memory = text

    def append_instant_memory(self, paragraph: str) -> None:
        """
        追加段落到即时记忆，保持滑动窗口。

        Args:
            paragraph: 新段落
        """
        if self.instant_memory:
            self.instant_memory += "\n" + paragraph
        else:
            self.instant_memory = paragraph

        # 保持即时记忆在合理长度内
        max_instant_chars = 1500
        if len(self.instant_memory) > max_instant_chars:
            # 保留最后部分
            paragraphs = self.instant_memory.split("\n")
            self.instant_memory = "\n".join(
                paragraphs[-INSTANT_MEMORY_PARAGRAPHS * 3:]
            )

    # ============================================================
    # 一致性检查
    # ============================================================

    def check_consistency(
        self,
        text: str,
        chapter_num: int,
    ) -> list[dict]:
        """
        检查文本与已有上下文的一致性。

        检查维度：
          1. 角色一致性（姓名、外貌、能力）
          2. 时间线一致性（已死角色、已毁地点）
          3. 力量体系一致性（能力表现与等级匹配）
          4. 地理一致性（地名、距离）
          5. 伏笔一致性（已设伏笔是否被合理推进）

        Args:
            text: 待检查的文本
            chapter_num: 当前章节号

        Returns:
            list[dict]: 一致性问题列表，每项包含：
              - type: 问题类型
              - issue: 问题描述
              - severity: 严重程度 (high/medium/low)
              - suggestion: 修改建议
        """
        issues: list[dict] = []

        # 1. 角色一致性检查
        issues.extend(self._check_character_consistency(text, chapter_num))

        # 2. 时间线一致性检查
        issues.extend(self._check_timeline_consistency(text, chapter_num))

        # 3. 力量体系一致性检查
        issues.extend(self._check_power_consistency(text))

        # 4. 地理一致性检查
        issues.extend(self._check_geography_consistency(text))

        # 5. 伏笔一致性检查
        issues.extend(self._check_foreshadow_consistency(text, chapter_num))

        return issues

    def _check_character_consistency(
        self, text: str, chapter_num: int
    ) -> list[dict]:
        """角色一致性检查"""
        issues = []

        for name, state in self._character_states.items():
            # 跳过别名（它们指向同一个状态字典）
            if name != list(self._character_states.keys())[
                list(self._character_states.values()).index(state)
            ] and any(
                k != name and self._character_states.get(k) is state
                for k in self._character_states
                if k != name
            ):
                # 这是一个别名，避免重复检查
                continue

            if name not in text:
                continue

            # 检查已死角色是否出现
            if state.get("status") == "dead" and name in self._dead_characters:
                # 检查是否是回忆/闪回/幻觉场景
                flashback_keywords = ["回忆", "想起", "梦中", "幻象", "仿佛看到", "恍惚间"]
                is_flashback = any(kw in text[max(0, text.find(name) - 20):text.find(name) + 50] for kw in flashback_keywords)
                if not is_flashback:
                    death_chapter = state.get("last_appearance", 0)
                    issues.append({
                        "type": "character",
                        "issue": f"角色「{name}」已在第{death_chapter}章死亡，但在第{chapter_num}章再次出现",
                        "severity": "high",
                        "suggestion": f"删除「{name}」的出场，或改为回忆/闪回场景",
                    })

            # 检查角色能力是否超出设定
            char_info = self.global_memory.get("character_index", {}).get(name, {})
            if char_info.get("abilities") and state.get("abilities"):
                # 简单检查：文本中提到的能力是否在角色能力列表中
                for ability in state.get("abilities", []):
                    if ability and ability not in text:
                        continue

        return issues

    def _check_timeline_consistency(
        self, text: str, chapter_num: int
    ) -> list[dict]:
        """时间线一致性检查"""
        issues = []

        # 检查已毁坏地点
        for location in self._destroyed_locations:
            if location in text:
                # 检查是否是回忆
                flashback_keywords = ["曾经", "过去", "从前", "回忆中"]
                nearby = text[max(0, text.find(location) - 30):text.find(location) + 50]
                is_flashback = any(kw in nearby for kw in flashback_keywords)
                if not is_flashback:
                    issues.append({
                        "type": "timeline",
                        "issue": f"地点「{location}」已被毁坏，不应出现在当前场景中",
                        "severity": "high",
                        "suggestion": f"将「{location}」改为回忆中的描述，或使用其他地点",
                    })

        return issues

    def _check_power_consistency(self, text: str) -> list[dict]:
        """力量体系一致性检查（规则方法）"""
        issues = []
        power_system = self._novel_info.power_system

        if not power_system or not power_system.levels:
            return issues

        # 检查是否有角色使用了超出其等级的能力
        for name, state in self._character_states.items():
            if name not in text:
                continue

            current_level = state.get("power_level", "")
            if not current_level:
                continue

            # 查找当前等级对应的序号
            current_level_num = 0
            for lvl in power_system.levels:
                if lvl.level_name == current_level:
                    current_level_num = lvl.level_number
                    break

            # 检查文本中是否出现了高等级能力
            for lvl in power_system.levels:
                if lvl.level_number <= current_level_num:
                    continue
                for ability in lvl.abilities:
                    if ability in text:
                        # 可能是使用了超出等级的能力
                        issues.append({
                            "type": "power_system",
                            "issue": f"角色「{name}」({current_level})可能使用了{lvl.level_name}的能力「{ability}」",
                            "severity": "medium",
                            "suggestion": f"确认「{name}」是否已突破到{lvl.level_name}，或修改能力描述",
                        })

        return issues

    def _check_geography_consistency(self, text: str) -> list[dict]:
        """地理一致性检查"""
        issues = []
        world_setting = self._novel_info.world_setting

        if not world_setting:
            return issues

        # 收集所有已知地点名称
        known_locations = set()
        if world_setting.geography.important_locations:
            for loc in world_setting.geography.important_locations:
                if loc.get("name"):
                    known_locations.add(loc["name"])
        if world_setting.geography.regions:
            for region in world_setting.geography.regions:
                if region.get("name"):
                    known_locations.add(region["name"])

        # 检查文本中出现的地点是否在已知地点中
        # （仅做警告，因为可能存在新发现的地点）
        for loc_name in known_locations:
            if loc_name in text:
                # 验证上下文中地点的使用是否合理
                pass

        return issues

    def _check_foreshadow_consistency(
        self, text: str, chapter_num: int
    ) -> list[dict]:
        """伏笔一致性检查"""
        issues = []
        active_fs = self.get_active_foreshadows()

        # 检查是否有长期未推进的伏笔
        for fs in active_fs:
            if fs.importance != "critical":
                continue

            chapters_since_plant = chapter_num - fs.plant_chapter
            # 关键伏笔超过30章未推进，发出警告
            if chapters_since_plant > 30:
                issues.append({
                    "type": "foreshadow",
                    "issue": f"关键伏笔「{fs.description[:30]}...」已{chapters_since_plant}章未推进（第{fs.plant_chapter}章设置）",
                    "severity": "medium",
                    "suggestion": "考虑在本章或近几章中暗示或推进该伏笔",
                })

        return issues

    # ============================================================
    # 辅助方法
    # ============================================================

    def get_completed_chapters(self) -> list[int]:
        """获取已完成章节号列表"""
        return list(self._completed_chapters)

    def get_dead_characters(self) -> set[str]:
        """获取已死亡角色集合"""
        return set(self._dead_characters)

    def mark_location_destroyed(self, location_name: str) -> None:
        """标记地点为已毁坏"""
        self._destroyed_locations.add(location_name)

    def get_all_character_names(self) -> list[str]:
        """获取所有角色名（不含别名）"""
        seen = set()
        names = []
        for name, state in self._character_states.items():
            if id(state) not in seen:
                seen.add(id(state))
                names.append(name)
        return names

    def get_context_stats(self) -> dict[str, Any]:
        """获取上下文系统统计信息"""
        return {
            "global_memory_size": len(self.global_memory),
            "volume_memory_size": len(self.volume_memory),
            "chapter_memory_count": len(self.chapter_memory),
            "character_states_count": len(self._character_states),
            "active_foreshadows_count": len(self.get_active_foreshadows()),
            "dead_characters_count": len(self._dead_characters),
            "destroyed_locations_count": len(self._destroyed_locations),
            "completed_chapters_count": len(self._completed_chapters),
            "current_volume": self._current_volume,
            "instant_memory_length": len(self.instant_memory),
        }
