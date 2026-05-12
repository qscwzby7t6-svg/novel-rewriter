"""
Pydantic 数据模型定义

定义小说仿写系统中使用的所有核心数据结构。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.models.enums import (
    ChapterStatus,
    CopyrightRisk,
    DetailLevel,
    ForeshadowStatus,
    Genre,
    OutputFormat,
    QualityLevel,
    TaskStatus,
)


# ============================================================
# 角色相关模型
# ============================================================

class CharacterRelation(BaseModel):
    """角色关系"""
    target_name: str = Field(..., description="关系目标角色名")
    relation_type: str = Field(default="朋友", description="关系类型：朋友/敌人/师徒/恋人/亲人等")
    description: str = Field(default="", description="关系描述")


class Character(BaseModel):
    """角色信息"""
    name: str = Field(..., description="角色姓名")
    aliases: list[str] = Field(default_factory=list, description="角色别名/绰号")
    role_type: str = Field(default="主角", description="角色类型：主角/配角/反派/路人")
    description: str = Field(default="", description="角色外貌描述")
    personality: str = Field(default="", description="性格特征")
    background: str = Field(default="", description="背景故事")
    abilities: list[str] = Field(default_factory=list, description="能力/技能列表")
    speech_style: str = Field(default="", description="语言风格描述")
    goals: str = Field(default="", description="角色目标/动机")
    relations: list[CharacterRelation] = Field(default_factory=list, description="角色关系")
    first_appearance_chapter: int = Field(default=0, description="首次出场章节")
    notes: str = Field(default="", description="备注")


# ============================================================
# 世界观相关模型
# ============================================================

class Geography(BaseModel):
    """地理设定"""
    world_name: str = Field(default="", description="世界名称")
    map_description: str = Field(default="", description="地图描述")
    regions: list[dict[str, Any]] = Field(default_factory=list, description="区域列表")
    important_locations: list[dict[str, Any]] = Field(default_factory=list, description="重要地点")


class History(BaseModel):
    """历史设定"""
    timeline: list[dict[str, Any]] = Field(default_factory=list, description="历史时间线")
    major_events: list[dict[str, Any]] = Field(default_factory=list, description="重大事件")
    legends: list[str] = Field(default_factory=list, description="传说/神话")


class Society(BaseModel):
    """社会设定"""
    factions: list[dict[str, Any]] = Field(default_factory=list, description="势力/组织")
    social_structure: str = Field(default="", description="社会结构描述")
    economy: str = Field(default="", description="经济体系描述")
    politics: str = Field(default="", description="政治体系描述")


class Culture(BaseModel):
    """文化设定"""
    customs: list[str] = Field(default_factory=list, description="风俗习惯")
    religions: list[str] = Field(default_factory=list, description="宗教信仰")
    arts: list[str] = Field(default_factory=list, description="艺术形式")
    taboos: list[str] = Field(default_factory=list, description="禁忌")


class WorldSetting(BaseModel):
    """世界观设定"""
    genre: Genre = Field(default=Genre.FANTASY, description="小说类型")
    geography: Geography = Field(default_factory=Geography, description="地理设定")
    history: History = Field(default_factory=History, description="历史设定")
    society: Society = Field(default_factory=Society, description="社会设定")
    culture: Culture = Field(default_factory=Culture, description="文化设定")
    rules: list[str] = Field(default_factory=list, description="世界规则/法则")
    technology_level: str = Field(default="", description="科技水平描述")
    magic_system: str = Field(default="", description="魔法/修炼体系概述")


# ============================================================
# 力量体系模型
# ============================================================

class PowerLevel(BaseModel):
    """力量等级"""
    level_name: str = Field(..., description="等级名称")
    level_number: int = Field(default=0, description="等级序号")
    description: str = Field(default="", description="等级描述")
    abilities: list[str] = Field(default_factory=list, description="该等级可拥有的能力")
    requirements: str = Field(default="", description="突破条件")


class PowerSystem(BaseModel):
    """力量体系"""
    name: str = Field(default="", description="体系名称（如：修仙体系、斗气体系）")
    description: str = Field(default="", description="体系概述")
    levels: list[PowerLevel] = Field(default_factory=list, description="等级列表")
    skills: list[dict[str, Any]] = Field(default_factory=list, description="技能列表")
    equipment_types: list[str] = Field(default_factory=list, description="装备类型")
    cultivation_methods: list[dict[str, Any]] = Field(default_factory=list, description="修炼功法")


# ============================================================
# 伏笔模型
# ============================================================

class Foreshadow(BaseModel):
    """伏笔"""
    id: str = Field(default="", description="伏笔ID")
    description: str = Field(default="", description="伏笔描述")
    plant_chapter: int = Field(default=0, description="设置章节")
    resolve_chapter: Optional[int] = Field(default=None, description="回收章节")
    status: ForeshadowStatus = Field(default=ForeshadowStatus.PLANTED, description="状态")
    importance: str = Field(default="normal", description="重要程度：critical/normal/minor")
    related_characters: list[str] = Field(default_factory=list, description="相关角色")
    notes: str = Field(default="", description="备注")


# ============================================================
# 写作风格模型
# ============================================================

class WritingStyle(BaseModel):
    """写作风格"""
    tone: str = Field(default="", description="基调：轻松/沉重/幽默/严肃")
    perspective: str = Field(default="第三人称", description="叙事视角")
    sentence_style: str = Field(default="", description="句子风格：短句为主/长句为主/混合")
    description_density: str = Field(default="适中", description="描写密度：稀疏/适中/密集")
    dialogue_ratio: float = Field(default=0.3, description="对话占比（0-1）")
    vocabulary_level: str = Field(default="通俗", description="用词水平：通俗/文学/古风")
    special_elements: list[str] = Field(default_factory=list, description="特殊元素：诗词/方言/专业术语等")
    reference_style: str = Field(default="", description="参考风格描述（如：模仿某作者风格）")
    forbidden_patterns: list[str] = Field(default_factory=list, description="禁止使用的模式/词汇")


# ============================================================
# 章节模型
# ============================================================

class ChapterOutline(BaseModel):
    """章节大纲"""
    chapter_number: int = Field(..., description="章节序号")
    title: str = Field(default="", description="章节标题")
    summary: str = Field(default="", description="章节摘要")
    key_events: list[str] = Field(default_factory=list, description="关键事件")
    characters_involved: list[str] = Field(default_factory=list, description="出场角色")
    foreshadows_to_plant: list[str] = Field(default_factory=list, description="本章节设置的伏笔")
    foreshadows_to_resolve: list[str] = Field(default_factory=list, description="本章节回收的伏笔")
    emotional_arc: str = Field(default="", description="情感弧线")
    word_count_target: int = Field(default=3000, description="目标字数")


class Chapter(BaseModel):
    """章节信息"""
    chapter_number: int = Field(..., description="章节序号")
    title: str = Field(default="", description="章节标题")
    content: str = Field(default="", description="章节内容")
    word_count: int = Field(default=0, description="实际字数")
    status: ChapterStatus = Field(default=ChapterStatus.PENDING, description="章节状态")
    outline: Optional[ChapterOutline] = Field(default=None, description="章节大纲")
    quality_score: float = Field(default=0.0, description="质量评分（0-1）")
    copyright_risk: CopyrightRisk = Field(default=CopyrightRisk.SAFE, description="版权风险")
    cost: float = Field(default=0.0, description="生成成本（元）")
    retry_count: int = Field(default=0, description="重试次数")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    notes: str = Field(default="", description="备注")


# ============================================================
# 小说信息模型
# ============================================================

class NovelInfo(BaseModel):
    """小说基本信息"""
    name: str = Field(default="", description="小说名称")
    genre: Genre = Field(default=Genre.FANTASY, description="小说类型")
    description: str = Field(default="", description="小说简介")
    total_chapters: int = Field(default=300, description="总章数")
    chapter_words_target: int = Field(default=3000, description="每章目标字数")
    total_words_target: int = Field(default=900000, description="总目标字数")
    world_setting: Optional[WorldSetting] = Field(default=None, description="世界观设定")
    power_system: Optional[PowerSystem] = Field(default=None, description="力量体系")
    characters: list[Character] = Field(default_factory=list, description="角色列表")
    foreshadows: list[Foreshadow] = Field(default_factory=list, description="伏笔列表")
    writing_style: Optional[WritingStyle] = Field(default=None, description="写作风格")
    chapters: list[Chapter] = Field(default_factory=list, description="章节列表")
    source_novel_path: str = Field(default="", description="源小说路径（仿写参考）")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


# ============================================================
# 任务配置模型
# ============================================================

class TaskConfig(BaseModel):
    """任务配置"""
    task_id: str = Field(default="", description="任务ID")
    novel_info: NovelInfo = Field(default_factory=NovelInfo, description="小说信息")
    start_chapter: int = Field(default=1, description="起始章节")
    end_chapter: int = Field(default=300, description="结束章节")
    auto_save: bool = Field(default=True, description="自动保存")
    save_interval: int = Field(default=5, description="每N章自动保存")
    max_concurrent: int = Field(default=1, description="最大并发数")
    enable_deai: bool = Field(default=True, description="启用去AI化")
    enable_copyright_check: bool = Field(default=True, description="启用版权检测")
    enable_quality_check: bool = Field(default=True, description="启用质量检查")
    quality_threshold: float = Field(default=0.7, description="质量阈值")
    chapter_budget: float = Field(default=0.5, description="每章预算上限（元）")
    total_budget: float = Field(default=100.0, description="总预算上限（元）")


# ============================================================
# 质量报告模型
# ============================================================

class QualityIssue(BaseModel):
    """质量问题"""
    type: str = Field(default="", description="问题类型")
    description: str = Field(default="", description="问题描述")
    location: str = Field(default="", description="问题位置")
    severity: str = Field(default="warning", description="严重程度：info/warning/error")
    suggestion: str = Field(default="", description="修改建议")


class QualityReport(BaseModel):
    """质量报告"""
    chapter_number: int = Field(default=0, description="章节序号")
    overall_score: float = Field(default=0.0, description="总体评分（0-1）")
    quality_level: QualityLevel = Field(default=QualityLevel.ACCEPTABLE, description="质量等级")
    coherence_score: float = Field(default=0.0, description="连贯性评分")
    character_consistency: float = Field(default=0.0, description="角色一致性评分")
    plot_logic: float = Field(default=0.0, description="情节逻辑评分")
    language_quality: float = Field(default=0.0, description="语言质量评分")
    ai_trace_score: float = Field(default=0.0, description="AI痕迹评分（越低越好）")
    copyright_similarity: float = Field(default=0.0, description="版权相似度（越低越好）")
    issues: list[QualityIssue] = Field(default_factory=list, description="问题列表")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


# ============================================================
# LLM调用记录模型
# ============================================================

class LLMCallRecord(BaseModel):
    """LLM调用记录"""
    call_id: str = Field(default="", description="调用ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间")
    provider: str = Field(default="", description="提供商")
    model: str = Field(default="", description="模型")
    prompt_tokens: int = Field(default=0, description="提示词token数")
    completion_tokens: int = Field(default=0, description="生成token数")
    total_tokens: int = Field(default=0, description="总token数")
    cost: float = Field(default=0.0, description="调用成本（元）")
    latency_ms: float = Field(default=0.0, description="延迟（毫秒）")
    success: bool = Field(default=True, description="是否成功")
    error_message: str = Field(default="", description="错误信息")
    chapter_number: int = Field(default=0, description="关联章节")
    is_fallback: bool = Field(default=False, description="是否使用了备用模型")


# ============================================================
# 任务状态模型
# ============================================================

class TaskState(BaseModel):
    """任务运行时状态"""
    task_id: str = Field(default="", description="任务ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    progress: float = Field(default=0.0, description="进度百分比（0-100）")
    current_chapter: int = Field(default=0, description="当前章节")
    total_chapters: int = Field(default=0, description="总章数")
    estimated_cost: float = Field(default=0.0, description="预估总成本")
    actual_cost: float = Field(default=0.0, description="实际成本")
    total_words: int = Field(default=0, description="已生成总字数")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    error_message: str = Field(default="", description="错误信息")
    call_records: list[LLMCallRecord] = Field(default_factory=list, description="调用记录")
