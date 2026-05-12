"""
世界观与架构复制引擎 - 小说仿写系统

基于原小说的解析结果，通过"变形复制"策略构建仿写用的世界观：
- 保留结构逻辑（地理结构、社会阶层、力量等级划分等）
- 替换具体皮囊（地名、组织名、技能名、角色名等）
- 确保内部一致性
"""

from __future__ import annotations

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


class WorldBuilder:
    """
    世界观与架构复制引擎。

    核心理念是"变形复制"：
    - 保留原小说的深层结构（叙事节奏、力量等级逻辑、角色功能定位等）
    - 替换表层元素（名称、描述、具体事件等）
    - 确保仿写世界观的内部一致性
    """

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    async def build_world(
        self,
        original: NovelInfo,
        protagonist_name: str = "主角",
        genre: Optional[Genre] = None,
        world_similarity: float = 0.7,
        plot_similarity: float = 0.6,
        character_similarity: float = 0.5,
        custom_requirements: Optional[list[str]] = None,
    ) -> NovelInfo:
        custom_reqs = custom_requirements or []
        target_genre = genre or original.genre

        logger.info(
            "开始构建仿写世界观，主角名: %s，目标类型: %s，世界观相似度: %.1f",
            protagonist_name, target_genre.value, world_similarity,
        )

        # 1. 世界观变形复制
        logger.info("[1/5] 世界观变形复制...")
        new_world = await self.transform_world_setting(original.world_setting)
        logger.info(
            "世界观复制完成: 区域 %d, 势力 %d, 地点 %d",
            len(new_world.geography.regions),
            len(new_world.society.factions),
            len(new_world.geography.important_locations),
        )

        # 2. 力量体系变形复制
        logger.info("[2/5] 力量体系变形复制...")
        new_power = await self.transform_power_system(original.power_system)
        logger.info(
            "力量体系复制完成: %d 个等级, %d 个技能",
            len(new_power.levels), len(new_power.skills),
        )

        # 3. 设计仿写角色
        logger.info("[3/5] 设计仿写角色...")
        new_characters = await self.design_characters(original.characters, protagonist_name)
        logger.info("角色设计完成: %d 个角色", len(new_characters))

        # 4. 设计仿写情节架构
        logger.info("[4/5] 设计仿写情节架构...")
        original_plot = self._extract_plot_from_chapters(original)
        new_plot = await self.design_plot_architecture(original_plot, original)
        logger.info("情节架构设计完成: %d 个结构节点", len(new_plot))

        # 5. 验证内部一致性
        logger.info("[5/5] 验证内部一致性...")
        temp_novel = NovelInfo(
            name="", genre=target_genre,
            characters=new_characters, world_setting=new_world,
            power_system=new_power, foreshadows=[], writing_style=original.writing_style,
        )
        issues = self.verify_consistency(temp_novel)
        if issues:
            logger.warning("发现 %d 个一致性问题: %s", len(issues), issues)
            new_world, new_power = self._auto_fix_issues(issues, new_world, new_power)

        # 6. 组装仿写 NovelInfo
        new_foreshadows = self._transform_foreshadows(original.foreshadows, new_characters)
        new_style = self._transform_writing_style(original.writing_style)

        new_novel = NovelInfo(
            name=f"{protagonist_name}传",
            genre=target_genre,
            description=await self._generate_synopsis(original, new_world, new_characters, protagonist_name),
            total_chapters=original.total_chapters,
            chapter_words_target=original.chapter_words_target,
            total_words_target=original.total_words_target,
            world_setting=new_world,
            power_system=new_power,
            characters=new_characters,
            foreshadows=new_foreshadows,
            writing_style=new_style,
        )

        logger.info("仿写世界观构建完成: 《%s》", new_novel.name)
        return new_novel

    async def transform_world_setting(self, original: WorldSetting) -> WorldSetting:
        """世界观变形复制：保留结构逻辑，替换名称和描述"""
        original_json = original.model_dump_json(indent=2, exclude_defaults=True)

        system_prompt = (
            "你是一位专业的奇幻世界观设计师。对给定的世界观设定进行\"变形复制\"。\n\n"
            "核心原则：\n"
            "1. 保留深层结构逻辑，替换表层名称和描述\n"
            "2. 新的世界观必须与原版有本质区别\n"
            "3. 所有名称必须全新，不能与原版重合\n"
            "4. 结构逻辑（区域数量、势力数量等）保持一致\n\n"
            "保留：地理结构逻辑、社会阶层逻辑、文化冲突模式、历史脉络节奏\n"
            "替换：所有地名、组织名、节日名、重要地点名\n\n"
            "请返回与原版相同 JSON 结构的变形结果。\n\n"
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"请对以下世界观设定进行变形复制：\n\n{original_json}"

        try:
            raw_text = await self._llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8,
            )
            result = self._parse_json_fallback(raw_text)

            geography = Geography(
                world_name=result.get("world_name", original.geography.world_name),
                map_description=result.get("map_description", original.geography.map_description),
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
                genre=result.get("genre", original.genre),
                geography=geography, history=history, society=society, culture=culture,
                rules=result.get("rules", []),
                technology_level=result.get("technology_level", ""),
                magic_system=result.get("magic_system", ""),
            )
        except Exception as e:
            logger.error("世界观变形复制失败: %s", e)
            return WorldSetting()

    async def transform_power_system(self, original: PowerSystem) -> PowerSystem:
        """力量体系变形复制：保留等级逻辑，替换名称"""
        original_json = original.model_dump_json(indent=2, exclude_defaults=True)

        system_prompt = (
            "你是一位专业的力量体系设计师。对给定的力量体系进行\"变形复制\"。\n\n"
            "核心原则：\n"
            "1. 保留力量体系的结构逻辑\n"
            "2. 新体系必须与原版有本质区别\n"
            "3. 等级数量必须与原版一致\n"
            "4. 技能数量应与原版大致相同\n\n"
            "保留：等级数量和层次关系、突破条件类型、技能分类方式\n"
            "替换：体系名称、等级名称、技能名称、资源名称\n\n"
            "请返回与原版相同 JSON 结构的变形结果。\n\n"
            "【重要】请严格按照 JSON 格式输出结果。"
        )
        user_prompt = f"请对以下力量体系进行变形复制：\n\n{original_json}"

        try:
            raw_text = await self._llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8,
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
            logger.error("力量体系变形复制失败: %s", e)
            return PowerSystem()

    async def design_characters(self, original_chars: list[Character], protagonist_name: str) -> list[Character]:
        """设计仿写角色：保留功能定位和关系拓扑，替换姓名和描述"""
        if not original_chars:
            return []

        chars_summary = []
        for ch in original_chars:
            chars_summary.append({
                "name": ch.name,
                "aliases": ch.aliases,
                "role_type": ch.role_type,
                "description": ch.description[:100] if ch.description else "",
                "personality": ch.personality[:80] if ch.personality else "",
                "abilities": ch.abilities[:5],
                "relations": [{"target_name": r.target_name, "relation_type": r.relation_type} for r in ch.relations],
                "first_appearance_chapter": ch.first_appearance_chapter,
                "importance": ch.notes,
            })
        chars_json = json.dumps(chars_summary, ensure_ascii=False, indent=2)

        system_prompt = (
            "你是一位专业的角色设计师。对给定的角色列表进行\"变形复制\"设计。\n\n"
            f"主角名必须使用：{protagonist_name}\n\n"
            "保留：角色功能定位、成长弧线类型、关系网络拓扑、重要度排序\n"
            "替换：所有角色姓名、外貌描述、背景故事、语言风格、能力名称\n\n"
            "请返回 JSON 数组格式：\n"
            '[{"name": "新角色名", "aliases": ["别名"], "role_type": "类型", '
            '"description": "外貌", "personality": "性格", "background": "背景", '
            '"abilities": ["能力"], "speech_style": "语言风格", "goals": "目标", '
            '"relations": [{"target_name": "角色名", "relation_type": "关系", "description": "描述"}], '
            '"first_appearance_chapter": 章节号, "importance": "critical/normal/minor"}]\n\n'
            "【重要】请严格按照 JSON 数组格式输出结果。"
        )
        user_prompt = f"请对以下角色列表进行变形复制设计：\n\n{chars_json}"

        try:
            raw_text = await self._llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8,
            )
            raw_list = self._parse_json_list_fallback(raw_text)
        except Exception as e:
            logger.error("角色设计 LLM 调用失败: %s", e)
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

        # 确保主角名正确
        for char in characters:
            if char.role_type == "主角":
                char.name = protagonist_name
                break
        return characters

    async def design_plot_architecture(self, original_plot: list[dict], original_novel: NovelInfo) -> list[dict]:
        """设计仿写情节架构：保留节奏和节点位置，替换具体事件"""
        if not original_plot:
            return []

        avg_word_count = original_novel.chapter_words_target or 3000
        plot_json = json.dumps(original_plot, ensure_ascii=False, indent=2)

        system_prompt = (
            "你是一位专业的叙事架构设计师。对给定的情节架构进行\"变形复制\"设计。\n\n"
            "核心原则：\n"
            "1. 保留叙事节奏和结构节点位置\n"
            "2. 结构节点数量和类型必须与原版一致\n"
            "3. 章节范围保持不变\n"
            "4. 具体情节内容必须全新\n\n"
            f"原版平均每章约 {avg_word_count} 字。\n\n"
            "请返回 JSON 数组格式：\n"
            '[{"chapter_range": "章节范围", "type": "结构类型", '
            '"description": "新的情节描述", "significance": "重要性"}]\n\n'
            "【重要】请严格按照 JSON 数组格式输出结果。"
        )
        user_prompt = f"请对以下情节架构进行变形复制设计：\n\n{plot_json}"

        try:
            raw_text = await self._llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.8,
            )
            return self._parse_json_list_fallback(raw_text)
        except Exception as e:
            logger.error("情节架构设计失败: %s", e)
            return []

    def verify_consistency(self, world: NovelInfo) -> list[str]:
        """验证世界观内部一致性，返回问题列表"""
        issues: list[str] = []

        # 1. 角色关系一致性
        character_names = {c.name for c in world.characters}
        character_names.update(alias for c in world.characters for alias in c.aliases)
        for char in world.characters:
            for rel in char.relations:
                if rel.target_name and rel.target_name not in character_names:
                    issues.append(f"角色 '{char.name}' 的关系对象 '{rel.target_name}' 未在角色列表中找到")

        # 2. 力量体系内部一致性
        issues.extend(self._check_power_system_consistency(world.power_system))

        # 3. 世界观与力量体系兼容性
        issues.extend(self._check_world_power_compatibility(world.world_setting, world.power_system))

        # 4. 地理描述一致性
        issues.extend(self._check_geography_consistency(world.world_setting))

        return issues

    def _check_power_system_consistency(self, power: PowerSystem) -> list[str]:
        issues = []
        if not power.levels:
            return issues
        ranks = sorted([lvl.level_number for lvl in power.levels if lvl.level_number > 0])
        for i in range(len(ranks) - 1):
            if ranks[i + 1] != ranks[i] + 1:
                issues.append(f"力量等级编号不连续: rank {ranks[i]} 后缺少 rank {ranks[i] + 1}")
        level_names = {lvl.level_name for lvl in power.levels}
        for skill in power.skills:
            level_req = skill.get("level_req", "")
            if level_req and level_names and level_req not in level_names:
                issues.append(f"技能 '{skill.get('name', '')}' 引用了不存在的等级 '{level_req}'")
        seen = set()
        for lvl in power.levels:
            if lvl.level_name in seen:
                issues.append(f"力量等级名称重复: '{lvl.level_name}'")
            seen.add(lvl.level_name)
        return issues

    def _check_world_power_compatibility(self, world: WorldSetting, power: PowerSystem) -> list[str]:
        issues = []
        if not world.magic_system and power.name:
            issues.append("世界观的 magic_system 为空，但存在独立的力量体系定义，建议补充概述")
        if world.technology_level and power.levels:
            high_tech_keywords = ["高度发达", "星际", "赛博", "量子", "人工智能"]
            if any(kw in world.technology_level for kw in high_tech_keywords) and len(power.levels) > 5:
                issues.append("世界观科技水平很高但力量体系等级过多，可能存在设定冲突")
        return issues

    def _check_geography_consistency(self, world: WorldSetting) -> list[str]:
        issues = []
        geo_names = [r.get("name", "") for r in world.geography.regions]
        location_names = [l.get("name", "") for l in world.geography.important_locations]
        all_names = [n for n in geo_names + location_names if n]
        seen = set()
        for name in all_names:
            if name in seen:
                issues.append(f"地名重复: '{name}'")
            seen.add(name)
        return issues

    def _auto_fix_issues(self, issues: list[str], world: WorldSetting, power: PowerSystem) -> tuple[WorldSetting, PowerSystem]:
        if not issues:
            return world, power
        logger.info("尝试自动修复 %d 个一致性问题...", len(issues))
        if power.levels:
            valid_level_names = {lvl.level_name for lvl in power.levels}
            valid_skills = []
            for skill in power.skills:
                level_req = skill.get("level_req", "")
                if not level_req or level_req in valid_level_names:
                    valid_skills.append(skill)
                else:
                    logger.info("移除引用不存在等级的技能: %s (等级: %s)", skill.get("name", ""), level_req)
            power.skills = valid_skills
            seen_names: set[str] = set()
            for lvl in power.levels:
                if lvl.level_name in seen_names:
                    old_name = lvl.level_name
                    lvl.level_name = f"{old_name}_变体"
                    logger.info("修复重复等级名称: %s -> %s", old_name, lvl.level_name)
                seen_names.add(lvl.level_name)
        return world, power

    def _extract_plot_from_chapters(self, novel: NovelInfo) -> list[dict]:
        """从原小说信息中提取情节架构"""
        total = novel.total_chapters
        if total <= 0:
            return []
        return [
            {"chapter_range": f"第1-{max(1, total // 10)}章", "type": "opening", "description": "开篇引入", "significance": "high"},
            {"chapter_range": f"第{total // 10 + 1}-{total // 2}章", "type": "rising_action", "description": "情节上升", "significance": "medium"},
            {"chapter_range": f"第{total // 2 + 1}-{total * 3 // 4}章", "type": "turning_point", "description": "转折点", "significance": "high"},
            {"chapter_range": f"第{total * 3 // 4 + 1}-{total * 9 // 10}章", "type": "climax", "description": "高潮", "significance": "high"},
            {"chapter_range": f"第{total * 9 // 10 + 1}-{total}章", "type": "resolution", "description": "结局", "significance": "high"},
        ]

    async def _generate_synopsis(self, original: NovelInfo, new_world: WorldSetting, new_characters: list[Character], protagonist_name: str) -> str:
        protagonist = next((c for c in new_characters if c.role_type == "主角"), None)
        system_prompt = (
            "你是一位专业的小说编辑。请根据以下信息生成一段小说简介（200-400字）。\n\n"
            "要求：突出主角特色、暗示核心冲突、展现世界观特色、吸引读者、不剧透。"
        )
        world_desc = (
            f"世界名称：{new_world.geography.world_name}\n"
            f"地理概述：{new_world.geography.map_description}\n"
            f"世界规则：{'；'.join(new_world.rules[:3]) if new_world.rules else '未知'}\n"
            f"力量体系：{new_world.magic_system}"
        )
        protagonist_desc = ""
        if protagonist:
            protagonist_desc = f"主角：{protagonist.name}\n性格：{protagonist.personality}\n目标：{protagonist.goals}"
        user_prompt = f"原小说简介（参考风格）：{original.description}\n\n新世界观：\n{world_desc}\n\n{protagonist_desc}\n\n请生成新的小说简介。"
        try:
            return await self._llm.call_with_retry(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.7, max_tokens=800,
            )
        except Exception as e:
            logger.error("生成简介失败: %s", e)
            return f"{protagonist_name}的故事，在一个全新的世界中展开。"

    def _transform_foreshadows(self, original_foreshadows: list[Foreshadow], new_characters: list[Character]) -> list[Foreshadow]:
        if not original_foreshadows:
            return []
        all_orig_names: list[str] = []
        for fs in original_foreshadows:
            for name in fs.related_characters:
                if name not in all_orig_names:
                    all_orig_names.append(name)
        name_map: dict[str, str] = {}
        new_sorted = sorted(new_characters, key=lambda c: c.notes, reverse=True)
        for i, orig_name in enumerate(all_orig_names):
            if i < len(new_sorted):
                name_map[orig_name] = new_sorted[i].name
        transformed = []
        for fs in original_foreshadows:
            new_related = [name_map.get(n, n) for n in fs.related_characters]
            transformed.append(Foreshadow(
                id=fs.id, description=fs.description,
                plant_chapter=fs.plant_chapter, resolve_chapter=fs.resolve_chapter,
                status=fs.status, importance=fs.importance,
                related_characters=new_related,
            ))
        return transformed

    @staticmethod
    def _transform_writing_style(original: WritingStyle) -> WritingStyle:
        return WritingStyle(
            tone=original.tone, perspective=original.perspective,
            sentence_style=original.sentence_style,
            description_density=original.description_density,
            dialogue_ratio=original.dialogue_ratio,
            vocabulary_level=original.vocabulary_level,
            special_elements=[],
            reference_style=original.reference_style,
            forbidden_patterns=original.forbidden_patterns,
        )

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
        for match in re.findall(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL):
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
        for match in re.findall(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL):
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
