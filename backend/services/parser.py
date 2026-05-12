"""
深度文本解析与知识提取引擎 - 小说仿写系统

负责对原始小说文本进行全面解析，提取结构化知识：
- 文本预处理（清洗、分章）
- 角色信息提取与合并
- 世界观设定提取
- 力量体系提取
- 伏笔提取
- 写作风格分析
- 叙事结构分析
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Optional

from backend.models.enums import ForeshadowStatus, Genre
from backend.models.schemas import (
    Character,
    CharacterRelation,
    Foreshadow,
    Geography,
    History,
    NovelInfo,
    PowerLevel,
    PowerSystem,
    Society,
    Culture,
    WorldSetting,
    WritingStyle,
)
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------

CHAPTERS_PER_BATCH = 25

ADVERTISEMENT_PATTERNS = [
    r"(?:求|投|催)更(?:票|更|定|藏)*[!！]*",
    r"PS[：:].*?(?:\n|$)",
    r"作者.*?说[：:].*?(?:\n|$)",
    r"本章.*?完(?:毕)?[!！。]*",
    r"(?:手机|电脑|微信|QQ|公众号).*?(?:\n|$)",
    r"(?:www\.|http|https).{0,100}",
    r"(?:广告|推广|赞助).*?(?:\n|$)",
    r"（?:本章完）",
    r"无弹窗.*?(?:\n|$)",
    r"最新章节.*?(?:\n|$)",
]

CHAPTER_TITLE_PATTERNS = [
    r"^(?:第[零一二三四五六七八九十百千万\d]+[章节回卷集部篇]\s*.+)$",
    r"^(?:[Cc]hapter\s+\d+.*)$",
    r"^(?:卷[零一二三四五六七八九十百千万\d]+\s*.+)$",
    r"^(?:\d{1,4}\s*[.、．]\s*.+)$",
    r"^(?:序[章言]\s*.+|引子|楔子|尾声|番外.+)$",
    r"^【第[零一二三四五六七八九十百千万\d]+[章节回]】\s*.+$",
    r"^(\d{1,4})$",
]


class TextParser:
    """
    深度文本解析与知识提取引擎。

    对原始小说文本进行多维度解析，提取角色、世界观、力量体系、
    伏笔、写作风格和叙事结构等结构化信息。
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self._ad_pattern = re.compile(
            "|".join(ADVERTISEMENT_PATTERNS),
            re.MULTILINE | re.IGNORECASE,
        )
        self._chapter_pattern = re.compile(
            "|".join(CHAPTER_TITLE_PATTERNS),
            re.MULTILINE,
        )

    async def parse_novel(self, text: str) -> NovelInfo:
        logger.info("开始解析小说，原始文本长度: %d 字符", len(text))

        logger.info("[1/9] 文本预处理...")
        chapters = await self.preprocess_text(text)
        logger.info("预处理完成，共识别 %d 章", len(chapters))

        if not chapters:
            logger.warning("未能识别到任何章节，将整段文本作为单一章节处理")
            chapters = [{
                "chapter": 1, "title": "全文",
                "content": text, "word_count": self._count_words(text),
            }]

        logger.info("[2/9] 提取基本信息...")
        basic_info = await self._extract_basic_info(chapters)

        logger.info("[3/9] 提取角色信息...")
        characters = await self.extract_characters(chapters)
        logger.info("提取到 %d 个角色", len(characters))

        logger.info("[4/9] 提取世界观设定...")
        world_setting = await self.extract_world_setting(chapters)

        logger.info("[5/9] 提取力量体系...")
        power_system = await self.extract_power_system(chapters)

        logger.info("[6/9] 提取伏笔...")
        foreshadows = await self.extract_foreshadows(chapters)
        logger.info("提取到 %d 条伏笔", len(foreshadows))

        logger.info("[7/9] 提取写作风格...")
        writing_style = await self.extract_writing_style(chapters)

        logger.info("[8/9] 分析叙事结构...")
        plot_structure = await self.analyze_plot_structure(chapters)
        logger.info("识别到 %d 个叙事结构节点", len(plot_structure))

        logger.info("[9/9] 统计字数...")
        total_word_count = sum(ch.get("word_count", 0) for ch in chapters)

        novel_info = NovelInfo(
            name=basic_info.get("title", "未知"),
            genre=basic_info.get("genre", Genre.FANTASY),
            description=basic_info.get("synopsis", ""),
            total_chapters=len(chapters),
            total_words_target=total_word_count,
            world_setting=world_setting,
            power_system=power_system,
            characters=characters,
            foreshadows=foreshadows,
            writing_style=writing_style,
        )

        logger.info(
            "小说解析完成: 《%s》 共 %d 章, 约 %d 字",
            novel_info.name, novel_info.total_chapters, novel_info.total_words_target,
        )
        return novel_info

    async def preprocess_text(self, text: str) -> list[dict]:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = self._remove_advertisements(text)
        text = self._normalize_punctuation(text)
        chapters = self._split_into_chapters(text)
        for ch in chapters:
            ch["content"] = ch["content"].strip()
            ch["word_count"] = self._count_words(ch["content"])
        chapters = [ch for ch in chapters if ch["word_count"] > 10]
        return chapters

    def _remove_advertisements(self, text: str) -> str:
        text = self._ad_pattern.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize_punctuation(self, text: str) -> str:
        replacements = {"\uff0e": "\u3002"}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _split_into_chapters(self, text: str) -> list[dict]:
        lines = text.split("\n")
        chapters: list[dict] = []
        current_chapter: Optional[dict] = None
        current_lines: list[str] = []
        chapter_num = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append("")
                continue
            if self._is_chapter_title(stripped):
                if current_chapter is not None:
                    current_chapter["content"] = "\n".join(current_lines)
                    chapters.append(current_chapter)
                chapter_num += 1
                current_chapter = {
                    "chapter": chapter_num, "title": stripped,
                    "content": "", "word_count": 0,
                }
                current_lines = []
            else:
                current_lines.append(stripped)

        if current_chapter is not None:
            current_chapter["content"] = "\n".join(current_lines)
            chapters.append(current_chapter)
        elif current_lines:
            chapters.append({
                "chapter": 1, "title": "正文",
                "content": "\n".join(current_lines), "word_count": 0,
            })
        return chapters

    def _is_chapter_title(self, line: str) -> bool:
        if len(line) > 50:
            return False
        return bool(self._chapter_pattern.match(line))

    @staticmethod
    def _count_words(text: str) -> int:
        if not text:
            return 0
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        numbers = len(re.findall(r"\d+", text))
        return chinese_chars + english_words + numbers

    async def _extract_basic_info(self, chapters: list[dict]) -> dict[str, Any]:
        sample = self._get_sample_chapters(chapters, head=3, tail=2)
        system_prompt = (
            "你是一位专业的文学分析师。请分析以下小说文本片段，提取基本信息。\n\n"
            "请返回如下 JSON 格式：\n"
            '{"title": "小说标题", "genre": "小说类型'
            '（玄幻/仙侠/都市/科幻/历史/游戏/悬疑/言情）", '
            '"synopsis": "小说简介（100-300字）"}'
        )
        user_prompt = f"请分析以下小说片段并提取基本信息：\n\n{sample}"
        try:
            result = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            return self._parse_json_fallback(result)
        except Exception as e:
            logger.error("提取基本信息失败: %s", e)
            return {"title": "未知", "genre": Genre.FANTASY, "synopsis": ""}

    async def extract_characters(self, chapters: list[dict]) -> list[Character]:
        all_characters: list[Character] = []
        total_chapters = len(chapters)

        if total_chapters <= CHAPTERS_PER_BATCH:
            characters = await self._extract_characters_from_batch(chapters, 1, 1)
            all_characters.extend(characters)
        else:
            total_batches = (total_chapters + CHAPTERS_PER_BATCH - 1) // CHAPTERS_PER_BATCH
            logger.info("小说共 %d 章，将分 %d 批提取角色（每批 %d 章）", total_chapters, total_batches, CHAPTERS_PER_BATCH)
            for batch_idx in range(total_batches):
                start = batch_idx * CHAPTERS_PER_BATCH
                end = min(start + CHAPTERS_PER_BATCH, total_chapters)
                batch_chapters = chapters[start:end]
                logger.info("处理角色提取批次 %d/%d（第 %d-%d 章）", batch_idx + 1, total_batches, start + 1, end)
                try:
                    characters = await self._extract_characters_from_batch(batch_chapters, batch_idx + 1, total_batches)
                    all_characters.extend(characters)
                except Exception as e:
                    logger.error("角色提取批次 %d 失败: %s", batch_idx + 1, e)

        merged = self._merge_characters(all_characters)
        logger.info("角色合并完成: %d -> %d 个角色", len(all_characters), len(merged))
        return merged

    async def _extract_characters_from_batch(self, chapters: list[dict], batch_num: int, total_batches: int) -> list[Character]:
        content = self._concat_chapters_content(chapters)
        content = self._truncate_text(content, max_chars=15000)

        system_prompt = (
            "你是一位专业的文学角色分析师。请从以下小说文本中提取所有重要角色信息。\n\n"
            "角色类型（role_type）可选值：主角/配角/反派/路人\n\n"
            "请返回 JSON 数组格式：\n"
            '[{"name": "角色名称", "aliases": ["别名1"], "role_type": "角色类型", '
            '"description": "外貌描述", "personality": "性格", "background": "背景", '
            '"abilities": ["能力1"], "speech_style": "语言风格", "goals": "目标", '
            '"relations": [{"target_name": "角色名", "relation_type": "关系", "description": "描述"}], '
            '"first_appearance_chapter": 章节号, "importance": "critical/normal/minor"}]\n\n'
            f"这是第 {batch_num}/{total_batches} 批，请注意与前面批次的角色保持一致\n\n"
            "【重要】请严格按照 JSON 数组格式输出结果。"
        )
        user_prompt = f"请从以下小说文本中提取角色信息：\n\n{content}"

        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            raw_list = self._parse_json_list_fallback(raw_text)
        except Exception as e:
            logger.error("角色提取 LLM 调用失败: %s", e)
            return []

        characters = []
        for item in raw_list:
            try:
                relations = []
                for rel in item.get("relations", []):
                    relations.append(CharacterRelation(
                        target_name=rel.get("target_name", ""),
                        relation_type=rel.get("relation_type", "朋友"),
                        description=rel.get("description", ""),
                    ))
                char = Character(
                    name=item.get("name", "未命名"),
                    aliases=item.get("aliases", []),
                    role_type=item.get("role_type", "配角"),
                    description=item.get("description", ""),
                    personality=item.get("personality", ""),
                    background=item.get("background", ""),
                    abilities=item.get("abilities", []),
                    speech_style=item.get("speech_style", ""),
                    goals=item.get("goals", ""),
                    relations=relations,
                    first_appearance_chapter=item.get("first_appearance_chapter", 0),
                    notes=item.get("importance", "normal"),
                )
                characters.append(char)
            except Exception as e:
                logger.warning("解析角色数据失败: %s, 数据: %s", e, item)
        return characters

    def _merge_characters(self, characters: list[Character]) -> list[Character]:
        if not characters:
            return []
        characters.sort(key=lambda c: len(c.description) + len(c.background), reverse=True)
        merged: list[Character] = []
        for char in characters:
            normalized_name = char.name.strip()
            normalized_aliases = {a.strip() for a in char.aliases}
            is_duplicate = False
            for existing in merged:
                existing_name = existing.name.strip()
                existing_aliases = {a.strip() for a in existing.aliases}
                if normalized_name == existing_name:
                    is_duplicate = True; break
                if normalized_name in existing_aliases:
                    is_duplicate = True; break
                if existing_name in normalized_aliases:
                    is_duplicate = True; break
                if normalized_aliases & existing_aliases:
                    is_duplicate = True; break
            if not is_duplicate:
                merged.append(char)
        return merged

    async def extract_world_setting(self, chapters: list[dict]) -> WorldSetting:
        sample = self._get_distributed_sample(chapters, sample_ratio=0.15)
        content = self._concat_chapters_content(sample)
        content = self._truncate_text(content, max_chars=20000)

        system_prompt = (
            "你是一位专业的奇幻/科幻世界观分析师。请从以下小说文本中提取世界观设定信息。\n\n"
            "请返回如下 JSON 格式：\n"
            '{"genre": "类型", "world_name": "世界名称", "map_description": "地理概述", '
            '"regions": [{"name": "区域名", "description": "描述", "features": ["特征"]}], '
            '"important_locations": [{"name": "地点名", "description": "描述", "significance": "重要性"}], '
            '"timeline": [{"era": "时代", "events": ["事件"]}], '
            '"major_events": [{"name": "事件名", "description": "描述", "impact": "影响"}], '
            '"legends": ["传说"], '
            '"factions": [{"name": "势力名", "description": "描述", "territory": "领地"}], '
            '"social_structure": "社会结构", "economy": "经济", "politics": "政治", '
            '"customs": ["风俗"], "religions": ["宗教"], "arts": ["艺术"], "taboos": ["禁忌"], '
            '"rules": ["世界规则"], "technology_level": "科技水平", "magic_system": "力量体系概述"}\n\n'
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"请从以下小说文本中提取世界观设定：\n\n{content}"

        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            result = self._parse_json_fallback(raw_text)
            genre_str = result.get("genre", "玄幻")
            try:
                genre = Genre(genre_str)
            except ValueError:
                genre = Genre.FANTASY
            geography = Geography(
                world_name=result.get("world_name", ""),
                map_description=result.get("map_description", ""),
                regions=result.get("regions", []),
                important_locations=result.get("important_locations", []),
            )
            history = History(
                timeline=result.get("timeline", []),
                major_events=result.get("major_events", []),
                legends=result.get("legends", []),
            )
            society = Society(
                factions=result.get("factions", []),
                social_structure=result.get("social_structure", ""),
                economy=result.get("economy", ""),
                politics=result.get("politics", ""),
            )
            culture = Culture(
                customs=result.get("customs", []),
                religions=result.get("religions", []),
                arts=result.get("arts", []),
                taboos=result.get("taboos", []),
            )
            return WorldSetting(
                genre=genre, geography=geography, history=history,
                society=society, culture=culture,
                rules=result.get("rules", []),
                technology_level=result.get("technology_level", ""),
                magic_system=result.get("magic_system", ""),
            )
        except Exception as e:
            logger.error("提取世界观设定失败: %s", e)
            return WorldSetting()

    async def extract_power_system(self, chapters: list[dict]) -> PowerSystem:
        battle_keywords = ["战", "斗", "修炼", "突破", "境界", "功法", "灵力", "斗气", "真气", "法力", "武", "剑", "术", "阵"]
        battle_chapters = self._find_chapters_by_keywords(chapters, battle_keywords)
        if len(battle_chapters) < 5:
            battle_chapters = self._get_distributed_sample(chapters, sample_ratio=0.15)
        content = self._concat_chapters_content(battle_chapters)
        content = self._truncate_text(content, max_chars=18000)

        system_prompt = (
            "你是一位专业的力量体系分析师。请从以下小说文本中提取力量/修炼体系信息。\n\n"
            "请返回如下 JSON 格式：\n"
            '{"name": "体系名称", "description": "概述", '
            '"levels": [{"level_name": "等级名", "level_number": 序号, "description": "描述", '
            '"abilities": ["能力"], "requirements": "突破条件"}], '
            '"skills": [{"name": "技能名", "type": "类型", "description": "描述", '
            '"level_req": "所需等级", "effects": ["效果"]}], '
            '"equipment_types": ["装备类型"], '
            '"cultivation_methods": [{"name": "功法名", "description": "描述", "level_req": "所需等级"}]}\n\n'
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"请从以下小说文本中提取力量体系信息：\n\n{content}"

        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            result = self._parse_json_fallback(raw_text)
            levels = []
            for lvl in result.get("levels", []):
                levels.append(PowerLevel(
                    level_name=lvl.get("level_name", ""),
                    level_number=lvl.get("level_number", 0),
                    description=lvl.get("description", ""),
                    abilities=lvl.get("abilities", []),
                    requirements=lvl.get("requirements", ""),
                ))
            return PowerSystem(
                name=result.get("name", ""),
                description=result.get("description", ""),
                levels=levels,
                skills=result.get("skills", []),
                equipment_types=result.get("equipment_types", []),
                cultivation_methods=result.get("cultivation_methods", []),
            )
        except Exception as e:
            logger.error("提取力量体系失败: %s", e)
            return PowerSystem()

    async def extract_foreshadows(self, chapters: list[dict]) -> list[Foreshadow]:
        total = len(chapters)
        mid = total // 2
        if total < 10:
            return await self._extract_foreshadows_from_range(chapters, 1, total)

        first_half = chapters[:mid]
        second_half = chapters[mid:]
        logger.info("从前半部分（第1-%d章）提取伏笔...", mid)
        planted = await self._extract_foreshadows_from_range(first_half, 1, mid)
        if not planted:
            return []

        logger.info("从后半部分（第%d-%d章）查找伏笔揭示...", mid + 1, total)
        revealed_map = await self._find_foreshadow_reveals(second_half, planted, start_chapter=mid + 1)

        for fs in planted:
            if fs.id in revealed_map:
                fs.resolve_chapter = revealed_map[fs.id]
                fs.status = ForeshadowStatus.RESOLVED
            else:
                partial = await self._check_partial_reveal(second_half, fs, start_chapter=mid + 1)
                if partial:
                    fs.status = ForeshadowStatus.HINTED
        return planted

    async def _extract_foreshadows_from_range(self, chapters: list[dict], start_chapter: int, end_chapter: int) -> list[Foreshadow]:
        content = self._concat_chapters_content(chapters)
        content = self._truncate_text(content, max_chars=15000)
        system_prompt = (
            "你是一位专业的文学伏笔分析师。请从以下小说文本中识别所有伏笔。\n\n"
            "请返回 JSON 数组格式：\n"
            '[{"id": "foreshadow_001", "description": "伏笔描述", '
            '"plant_chapter": 章节号, "related_characters": ["角色名"], '
            '"importance": "critical/normal/minor"}]\n\n'
            "【重要】请严格按照 JSON 数组格式输出结果。"
        )
        user_prompt = f"请从以下小说文本（第{start_chapter}-{end_chapter}章）中识别伏笔：\n\n{content}"

        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            raw_list = self._parse_json_list_fallback(raw_text)
        except Exception as e:
            logger.error("提取伏笔失败: %s", e)
            return []

        foreshadows = []
        for item in raw_list:
            try:
                fs_id = item.get("id", "")
                if not fs_id:
                    desc = item.get("description", "")
                    fs_id = f"fs_{hashlib.md5(desc.encode()).hexdigest()[:8]}"
                fs = Foreshadow(
                    id=fs_id,
                    description=item.get("description", ""),
                    plant_chapter=item.get("plant_chapter", start_chapter),
                    status=ForeshadowStatus.PLANTED,
                    importance=item.get("importance", "normal"),
                    related_characters=item.get("related_characters", []),
                )
                foreshadows.append(fs)
            except Exception as e:
                logger.warning("解析伏笔数据失败: %s", e)
        return foreshadows

    async def _find_foreshadow_reveals(self, chapters: list[dict], foreshadows: list[Foreshadow], start_chapter: int) -> dict[str, int]:
        if not foreshadows:
            return {}
        content = self._concat_chapters_content(chapters)
        content = self._truncate_text(content, max_chars=15000)
        fs_summary = "\n".join(f"- {fs.id}: {fs.description}（第{fs.plant_chapter}章埋下）" for fs in foreshadows)
        system_prompt = (
            "你是一位文学分析师。已知以下伏笔信息，请判断它们在后续文本中是否被揭示。\n\n"
            '请返回 JSON 格式：{"伏笔ID": 揭示章节号（整数）}\n'
            "只返回被揭示的伏笔。\n\n"
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"已知伏笔：\n{fs_summary}\n\n后续文本（第{start_chapter}章起）：\n{content}"
        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.2,
            )
            result = self._parse_json_fallback(raw_text)
            return {k: int(v) for k, v in result.items() if isinstance(v, (int, float)) and int(v) > 0}
        except Exception as e:
            logger.error("查找伏笔揭示失败: %s", e)
            return {}

    async def _check_partial_reveal(self, chapters: list[dict], foreshadow: Foreshadow, start_chapter: int) -> bool:
        if foreshadow.importance != "critical":
            return False
        content = self._concat_chapters_content(chapters)
        content = self._truncate_text(content, max_chars=8000)
        system_prompt = "请判断以下伏笔在文本中是否有部分揭示。请只回答 true 或 false。"
        user_prompt = f"伏笔：{foreshadow.description}（第{foreshadow.plant_chapter}章埋下）\n\n后续文本：\n{content}"
        try:
            response = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=10,
            )
            return "true" in response.strip().lower()
        except Exception:
            return False

    async def extract_writing_style(self, chapters: list[dict]) -> WritingStyle:
        sample = self._get_distributed_sample(chapters, sample_ratio=0.1, min_chapters=5)
        content = self._concat_chapters_content(sample)
        content = self._truncate_text(content, max_chars=15000)
        system_prompt = (
            "你是一位专业的文学风格分析师。请分析以下小说文本的写作风格。\n\n"
            "请返回如下 JSON 格式：\n"
            '{"tone": "基调", "perspective": "叙事视角", "sentence_style": "句子风格", '
            '"description_density": "描写密度", "dialogue_ratio": 0.5, '
            '"vocabulary_level": "用词水平", "special_elements": ["特殊元素"], '
            '"reference_style": "参考风格", "forbidden_patterns": ["不良用语"]}\n\n'
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"请分析以下小说文本的写作风格：\n\n{content}"
        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            result = self._parse_json_fallback(raw_text)
            return WritingStyle(**result)
        except Exception as e:
            logger.error("提取写作风格失败: %s", e)
            return WritingStyle()

    async def analyze_plot_structure(self, chapters: list[dict]) -> list[dict]:
        total = len(chapters)
        if total <= CHAPTERS_PER_BATCH:
            return await self._analyze_plot_structure_batch(chapters, 1, total)
        all_structure: list[dict] = []
        total_batches = (total + CHAPTERS_PER_BATCH - 1) // CHAPTERS_PER_BATCH
        for batch_idx in range(total_batches):
            start = batch_idx * CHAPTERS_PER_BATCH
            end = min(start + CHAPTERS_PER_BATCH, total)
            batch = chapters[start:end]
            logger.info("分析叙事结构批次 %d/%d（第 %d-%d 章）", batch_idx + 1, total_batches, start + 1, end)
            try:
                structure = await self._analyze_plot_structure_batch(batch, start + 1, end)
                all_structure.extend(structure)
            except Exception as e:
                logger.error("叙事结构分析批次 %d 失败: %s", batch_idx + 1, e)
        return all_structure

    async def _analyze_plot_structure_batch(self, chapters: list[dict], start_chapter: int, end_chapter: int) -> list[dict]:
        content = self._concat_chapters_content(chapters)
        content = self._truncate_text(content, max_chars=15000)
        system_prompt = (
            "你是一位专业的叙事结构分析师。请分析以下小说文本的叙事结构。\n\n"
            "结构类型：opening/introduction/rising_action/turning_point/climax/falling_action/subplot/resolution/filler\n\n"
            "请返回 JSON 数组格式：\n"
            '[{"chapter_range": "第X-Y章", "type": "结构类型", "description": "情节描述", "significance": "high/medium/low"}]\n\n'
            "【重要】请严格按照 JSON 数组格式输出结果。"
        )
        user_prompt = f"请分析以下小说文本（第{start_chapter}-{end_chapter}章）的叙事结构：\n\n{content}"
        try:
            raw_text = await self.llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.3,
            )
            return self._parse_json_list_fallback(raw_text)
        except Exception as e:
            logger.error("分析叙事结构失败: %s", e)
            return []

    @staticmethod
    def _parse_json_fallback(text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
            return {"data": result}
        except (json.JSONDecodeError, ValueError):
            pass
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        for match in re.findall(code_block_pattern, text, re.DOTALL):
            try:
                result = json.loads(match.strip())
                if isinstance(result, dict):
                    return result
                return {"data": result}
            except (json.JSONDecodeError, ValueError):
                continue
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
        logger.error("无法从 LLM 响应中解析 JSON: %s", text[:500])
        raise ValueError(f"LLM 响应无法解析为 JSON: {text[:200]}")

    @staticmethod
    def _parse_json_list_fallback(text: str) -> list[dict[str, Any]]:
        text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        except (json.JSONDecodeError, ValueError):
            pass
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        for match in re.findall(code_block_pattern, text, re.DOTALL):
            try:
                result = json.loads(match.strip())
                if isinstance(result, list):
                    return result
                if isinstance(result, dict):
                    return [result]
            except (json.JSONDecodeError, ValueError):
                continue
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
        logger.error("无法从 LLM 响应中解析 JSON 数组: %s", text[:500])
        raise ValueError(f"LLM 响应无法解析为 JSON 数组: {text[:200]}")

    def _concat_chapters_content(self, chapters: list[dict], max_per_chapter: int = 3000) -> str:
        parts = []
        for ch in chapters:
            content = ch.get("content", "")
            if len(content) > max_per_chapter:
                content = content[:max_per_chapter] + "\n...(截断)"
            parts.append(f"【{ch.get('title', '')}】\n{content}")
        return "\n\n".join(parts)

    def _get_sample_chapters(self, chapters: list[dict], head: int = 3, tail: int = 2) -> list[dict]:
        if len(chapters) <= head + tail:
            return chapters
        return chapters[:head] + chapters[-tail:]

    def _get_distributed_sample(self, chapters: list[dict], sample_ratio: float = 0.1, min_chapters: int = 5) -> list[dict]:
        total = len(chapters)
        sample_size = max(min_chapters, int(total * sample_ratio))
        sample_size = min(sample_size, total)
        if total <= sample_size:
            return chapters
        step = total / sample_size
        indices = [min(int(i * step), total - 1) for i in range(sample_size)]
        return [chapters[i] for i in indices]

    def _find_chapters_by_keywords(self, chapters: list[dict], keywords: list[str], max_results: int = 30) -> list[dict]:
        scored = []
        for ch in chapters:
            text = ch.get("title", "") + " " + ch.get("content", "")
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ch for _, ch in scored[:max_results]]

    @staticmethod
    def _truncate_text(text: str, max_chars: int = 15000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...(文本过长，已截断)"
