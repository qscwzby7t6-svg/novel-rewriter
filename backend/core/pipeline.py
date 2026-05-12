"""
主流水线

实现小说仿写的完整流水线，串联所有服务模块。
支持进度回调、断点续传、暂停/恢复。
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from backend.config import get_config
from backend.core.quality_checker import QualityChecker
from backend.core.task_scheduler import TaskScheduler
from backend.models.enums import ChapterStatus, TaskStatus
from backend.models.schemas import (
    Chapter,
    NovelInfo,
    TaskConfig,
    TaskState,
    QualityReport,
)
from backend.services.chapter_ctrl import ChapterController
from backend.services.context_mgr import ContextManager
from backend.services.copyright import CopyrightDetector
from backend.services.deai import DeAIService
from backend.services.llm_client import LLMClient
from backend.services.parser import TextParser
from backend.services.writer import Writer
from backend.services.world_builder import WorldBuilder

logger = logging.getLogger(__name__)


# 进度回调类型: callback(stage: str, progress: float, message: str)
ProgressCallback = Callable[[str, float, str], Any]


class NovelPipeline:
    """
    小说仿写主流水线

    串联解析、世界观构建、章节生成、质量检查、去AI化、版权检测等环节。
    支持进度回调和断点续传。
    """

    def __init__(
        self,
        task_id: Optional[str] = None,
        config: Optional[TaskConfig] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        """
        初始化流水线。

        Args:
            task_id: 任务ID，为None时自动生成
            config: 任务配置
            progress_callback: 进度回调函数，签名: (stage, progress, message)
        """
        self._app_config = get_config()
        self._task_id = task_id or str(uuid.uuid4())[:8]
        self._task_config = config or TaskConfig(task_id=self._task_id)
        self._progress_callback = progress_callback

        # 初始化各服务
        self._llm_client = LLMClient(self._app_config)
        self._parser = TextParser(self._llm_client)
        self._world_builder = WorldBuilder(self._llm_client)
        self._writer = Writer(self._llm_client)
        self._context_mgr = None  # 延迟初始化，需要 novel_info
        self._chapter_ctrl = None  # 延迟初始化，需要 context_mgr
        self._quality_checker = QualityChecker(
            threshold=self._app_config.writing.quality_threshold
        )
        self._deai_service = DeAIService(self._llm_client)
        self._copyright_detector = CopyrightDetector()
        self._scheduler = TaskScheduler()

        # 运行时状态
        self._state: Optional[TaskState] = None
        self._novel_info: Optional[NovelInfo] = None
        self._source_text: str = ""

        # 断点续传相关
        self._checkpoint_dir = Path(self._app_config.output.path) / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def state(self) -> Optional[TaskState]:
        return self._state

    @property
    def novel_info(self) -> Optional[NovelInfo]:
        return self._novel_info

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """设置进度回调函数"""
        self._progress_callback = callback

    def _emit_progress(self, stage: str, progress: float, message: str) -> None:
        """触发进度回调"""
        if self._progress_callback:
            try:
                self._progress_callback(stage, progress, message)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")

    def _init_state(self) -> TaskState:
        """初始化任务状态"""
        self._state = TaskState(
            task_id=self._task_id,
            status=TaskStatus.PENDING,
            total_chapters=self._task_config.end_chapter
            - self._task_config.start_chapter + 1,
            start_time=datetime.now(),
        )
        return self._state

    # ================================================================
    # 断点续传
    # ================================================================

    def _get_checkpoint_path(self) -> Path:
        """获取检查点文件路径"""
        return self._checkpoint_dir / f"checkpoint_{self._task_id}.json"

    def _save_checkpoint(self) -> None:
        """保存检查点（断点续传用）"""
        if self._novel_info is None or self._state is None:
            return

        checkpoint = {
            "task_id": self._task_id,
            "novel_info": json.loads(self._novel_info.model_dump_json()),
            "state": json.loads(self._state.model_dump_json()),
            "source_text_length": len(self._source_text),
            "saved_at": datetime.now().isoformat(),
        }

        checkpoint_path = self._get_checkpoint_path()
        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            logger.debug(f"检查点已保存: {checkpoint_path}")
        except Exception as e:
            logger.warning(f"保存检查点失败: {e}")

    def _load_checkpoint(self) -> bool:
        """
        尝试加载检查点。

        Returns:
            bool: 是否成功加载检查点
        """
        checkpoint_path = self._get_checkpoint_path()
        if not checkpoint_path.exists():
            return False

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            # 恢复小说信息
            self._novel_info = NovelInfo.model_validate(checkpoint["novel_info"])

            # 恢复任务状态
            self._state = TaskState.model_validate(checkpoint["state"])

            logger.info(
                f"已加载检查点: 任务={self._task_id}, "
                f"已完成 {len(self._novel_info.chapters)} 章, "
                f"保存时间={checkpoint.get('saved_at', '未知')}"
            )
            return True

        except Exception as e:
            logger.warning(f"加载检查点失败: {e}")
            return False

    def _clear_checkpoint(self) -> None:
        """清除检查点文件"""
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
                logger.debug(f"检查点已清除: {checkpoint_path}")
            except Exception as e:
                logger.warning(f"清除检查点失败: {e}")

    def has_checkpoint(self) -> bool:
        """检查是否存在检查点"""
        return self._get_checkpoint_path().exists()

    def get_resume_info(self) -> Optional[dict]:
        """
        获取断点续传信息。

        Returns:
            dict 或 None: 续传信息
        """
        checkpoint_path = self._get_checkpoint_path()
        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            state = checkpoint.get("state", {})
            novel = checkpoint.get("novel_info", {})
            completed_chapters = len(novel.get("chapters", []))

            return {
                "task_id": self._task_id,
                "status": state.get("status", "unknown"),
                "completed_chapters": completed_chapters,
                "total_chapters": state.get("total_chapters", 0),
                "progress": state.get("progress", 0.0),
                "saved_at": checkpoint.get("saved_at", "未知"),
                "novel_name": novel.get("name", ""),
            }
        except Exception:
            return None

    # ================================================================
    # 主流水线
    # ================================================================

    async def run(self, resume: bool = False) -> NovelInfo:
        """
        执行完整的仿写流水线。

        Args:
            resume: 是否从断点续传

        Returns:
            NovelInfo: 生成的小说信息
        """
        logger.info(f"========== 开始仿写流水线 (任务: {self._task_id}) ==========")

        try:
            # 初始化状态
            if resume and self._load_checkpoint():
                logger.info("从断点恢复执行...")
                self._emit_progress("resume", 0.0, "从断点恢复执行")
            else:
                self._init_state()
                self._clear_checkpoint()

            # 1. 解析源小说
            await self.parse_novel()

            # 2. 构建世界观（仅在非续传或世界观数据缺失时执行）
            if not resume or not self._novel_info or not self._novel_info.world_setting:
                await self.build_world()

            # 3. 生成章节
            await self.generate_chapters()

            # 4. 完成
            if self._state:
                self._state.status = TaskStatus.COMPLETED
                self._state.end_time = datetime.now()

            # 清除检查点
            self._clear_checkpoint()

            # 最终保存
            await self._save_progress()

            self._emit_progress("completed", 100.0, "仿写流水线完成")

            logger.info(f"========== 仿写流水线完成 (任务: {self._task_id}) ==========")

        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            if self._state:
                self._state.status = TaskStatus.FAILED
                self._state.error_message = str(e)
            # 保存检查点以便续传
            self._save_checkpoint()
            self._emit_progress("failed", 0.0, f"流水线执行失败: {e}")
            raise

        return self._novel_info or NovelInfo()

    async def pause(self) -> None:
        """暂停当前任务"""
        if self._state:
            self._state.status = TaskStatus.PAUSED
            self._save_checkpoint()
            self._scheduler.cancel(self._task_id)
            logger.info(f"任务已暂停: {self._task_id}")
            self._emit_progress("paused", 0.0, "任务已暂停")

    async def resume(self) -> NovelInfo:
        """恢复暂停的任务"""
        if self._state:
            self._state.status = TaskStatus.PENDING
        return await self.run(resume=True)

    # ================================================================
    # 阶段1: 解析源小说
    # ================================================================

    async def parse_novel(self) -> None:
        """
        阶段1: 解析源小说。

        如果有源小说路径，解析并提取信息；
        否则使用配置中的默认设置创建新的小说框架。
        """
        if self._state:
            self._state.status = TaskStatus.PARSING

        self._emit_progress("parse_novel", 0.0, "开始解析源小说...")
        logger.info("[阶段1] 解析源小说...")

        novel_info = self._task_config.novel_info

        if novel_info.source_novel_path:
            # 解析源小说文件
            from backend.utils.file_utils import read_text_file
            source_text = read_text_file(novel_info.source_novel_path)
            self._novel_info = await self._parser.parse_novel(source_text)
            # 保存源文本用于后续版权检测
            self._source_text = source_text
        else:
            # 创建新的小说框架
            self._novel_info = NovelInfo(
                name=novel_info.name or f"仿写小说_{self._task_id}",
                genre=novel_info.genre,
                description=novel_info.description,
                total_chapters=self._task_config.end_chapter,
                chapter_words_target=self._app_config.novel.default_chapter_words,
            )

        self._emit_progress(
            "parse_novel", 1.0,
            f"解析完成: 《{self._novel_info.name}》, 共{self._novel_info.total_chapters}章"
        )
        logger.info(
            f"[阶段1] 完成: 小说《{self._novel_info.name}》, "
            f"共{self._novel_info.total_chapters}章"
        )

    # ================================================================
    # 阶段2: 构建世界观
    # ================================================================

    async def build_world(self) -> None:
        """
        阶段2: 构建世界观。

        使用LLM生成世界观设定和力量体系。
        """
        if self._state:
            self._state.status = TaskStatus.BUILDING_WORLD

        self._emit_progress("build_world", 0.0, "开始构建世界观...")
        logger.info("[阶段2] 构建世界观...")

        if self._novel_info is None:
            raise RuntimeError("小说信息未初始化")

        # 构建世界观（使用 WorldBuilder 的变形复制方法）
        self._emit_progress("build_world", 0.3, "生成世界观设定...")
        new_novel = await self._world_builder.build_world(
            original=self._novel_info,
        )
        self._novel_info.world_setting = new_novel.world_setting
        self._novel_info.power_system = new_novel.power_system
        self._novel_info.characters = new_novel.characters
        self._novel_info.foreshadows = new_novel.foreshadows
        self._novel_info.writing_style = new_novel.writing_style
        self._novel_info.description = new_novel.description

        # 初始化上下文管理器和章节控制器
        self._context_mgr = ContextManager(
            llm_client=self._llm_client,
            novel_info=self._novel_info,
        )
        self._chapter_ctrl = ChapterController(
            llm_client=self._llm_client,
            writer=self._writer,
            context_manager=self._context_mgr,
        )

        # 保存检查点
        self._save_checkpoint()

        self._emit_progress("build_world", 1.0, "世界观构建完成")
        logger.info("[阶段2] 世界观构建完成")

    # ================================================================
    # 阶段3: 逐章生成
    # ================================================================

    async def generate_chapters(self) -> None:
        """
        阶段3: 逐章生成小说内容。

        对每一章执行：生成大纲 -> 生成正文 -> 质量检查 -> 版权检测 -> 去AI化
        支持断点续传，跳过已完成的章节。
        """
        if self._state:
            self._state.status = TaskStatus.GENERATING

        if self._novel_info is None:
            raise RuntimeError("小说信息未初始化")

        # 确保上下文管理器和章节控制器已初始化
        if self._context_mgr is None:
            self._context_mgr = ContextManager(
                llm_client=self._llm_client,
                novel_info=self._novel_info,
            )
        if self._chapter_ctrl is None:
            self._chapter_ctrl = ChapterController(
                llm_client=self._llm_client,
                writer=self._writer,
                context_manager=self._context_mgr,
            )

        start_ch = self._task_config.start_chapter
        end_ch = self._task_config.end_chapter

        # 断点续传：确定已完成的章节
        completed_chapter_nums = {ch.chapter_number for ch in self._novel_info.chapters}
        actual_start = start_ch
        if completed_chapter_nums:
            max_completed = max(completed_chapter_nums)
            if max_completed >= start_ch:
                actual_start = max_completed + 1
                logger.info(f"断点续传: 跳过已完成的 {len(completed_chapter_nums)} 章，从第 {actual_start} 章开始")

        if actual_start > end_ch:
            logger.info("所有章节已完成，无需生成")
            return

        total_to_generate = end_ch - actual_start + 1
        logger.info(f"[阶段3] 开始生成章节: {actual_start} -> {end_ch} (共 {total_to_generate} 章)")

        generated_count = 0

        for ch_num in range(actual_start, end_ch + 1):
            # 检查暂停/取消
            if self._state and self._scheduler.is_cancelled(self._task_id):
                logger.info("任务已取消，停止生成")
                self._save_checkpoint()
                break

            chapter_progress = generated_count / total_to_generate
            self._emit_progress(
                "generate_chapters", chapter_progress,
                f"正在生成第 {ch_num}/{end_ch} 章..."
            )

            # 生成章节
            chapter = await self._chapter_ctrl.generate_chapter(
                chapter_number=ch_num,
                novel_info=self._novel_info,
            )

            # 质量检查（含版权检测）
            if self._task_config.enable_quality_check:
                chapter = await self.check_quality(chapter)

            # 去AI化
            if self._task_config.enable_deai:
                chapter = await self.optimize(chapter)

            # 版权检测
            if self._task_config.enable_copyright_check and self._source_text:
                risk, similarity = await self._copyright_detector.check_chapter(
                    chapter, self._source_text
                )
                chapter.copyright_risk = risk

            # 添加到小说
            self._novel_info.chapters.append(chapter)

            generated_count += 1

            # 更新状态
            if self._state:
                self._state.current_chapter = ch_num
                self._state.progress = (
                    (ch_num - start_ch + 1) / (end_ch - start_ch + 1) * 100
                )
                self._state.total_words += chapter.word_count
                self._state.actual_cost = self._llm_client.cost_tracker.total_cost

            # 自动保存（定期保存检查点）
            if (
                self._task_config.auto_save
                and generated_count % self._task_config.save_interval == 0
            ):
                self._save_checkpoint()
                await self._save_progress()

            logger.info(
                f"[阶段3] 第{ch_num}/{end_ch}章完成, "
                f"字数={chapter.word_count}, "
                f"质量={chapter.quality_score:.2f}, "
                f"版权风险={chapter.copyright_risk.value}, "
                f"累计成本={self._state.actual_cost if self._state else 0:.4f}元"
            )

        # 生成完成后保存检查点
        self._save_checkpoint()

        self._emit_progress(
            "generate_chapters", 1.0,
            f"章节生成完成: 共 {generated_count} 章"
        )

    # ================================================================
    # 阶段4: 质量检查
    # ================================================================

    async def check_quality(self, chapter: Chapter) -> Chapter:
        """
        阶段4: 质量检查（含版权检测）。

        Args:
            chapter: 待检查的章节

        Returns:
            Chapter: 检查后的章节
        """
        if self._state:
            self._state.status = TaskStatus.CHECKING_QUALITY

        self._emit_progress(
            "check_quality", 0.0,
            f"质量检查: 第 {chapter.chapter_number} 章"
        )

        # 基础质量检查
        report = self._quality_checker.check_chapter(chapter)
        chapter.quality_score = report.overall_score

        # 如果有源文本，执行版权检测
        if self._source_text and self._task_config.enable_copyright_check:
            copyright_report = self._copyright_detector.full_copyright_check(
                chapter.content, self._source_text
            )
            report.copyright_similarity = copyright_report.copyright_similarity
            # 合并版权问题到质量报告
            report.issues.extend(copyright_report.issues)
            report.suggestions.extend(copyright_report.suggestions)

            # 更新版权风险
            if copyright_report.copyright_similarity >= 0.30:
                chapter.copyright_risk = CopyrightRisk.HIGH
            elif copyright_report.copyright_similarity >= 0.20:
                chapter.copyright_risk = CopyrightRisk.MEDIUM
            elif copyright_report.copyright_similarity >= 0.10:
                chapter.copyright_risk = CopyrightRisk.LOW
            else:
                chapter.copyright_risk = CopyrightRisk.SAFE

        if not self._quality_checker.is_acceptable(report):
            logger.warning(
                f"第{chapter.chapter_number}章质量不达标: "
                f"评分={report.overall_score:.2f}, "
                f"问题数={len(report.issues)}"
            )
            # TODO: 自动修改不达标的章节
            # chapter = await self._chapter_ctrl.regenerate_chapter(
            #     chapter, self._novel_info, str(report.issues)
            # )

        self._emit_progress(
            "check_quality", 1.0,
            f"质量检查完成: 第 {chapter.chapter_number} 章, 评分={report.overall_score:.2f}"
        )

        return chapter

    # ================================================================
    # 阶段5: 去AI化优化
    # ================================================================

    async def optimize(self, chapter: Chapter) -> Chapter:
        """
        阶段5: 优化（去AI化处理）。

        Args:
            chapter: 待优化的章节

        Returns:
            Chapter: 优化后的章节
        """
        if self._state:
            self._state.status = TaskStatus.OPTIMIZING

        self._emit_progress(
            "optimize", 0.0,
            f"去AI化优化: 第 {chapter.chapter_number} 章"
        )

        chapter = await self._deai_service.deai_chapter(chapter)

        self._emit_progress(
            "optimize", 1.0,
            f"去AI化完成: 第 {chapter.chapter_number} 章"
        )

        return chapter

    # ================================================================
    # 保存与报告
    # ================================================================

    async def _save_progress(self) -> None:
        """保存当前进度"""
        if self._novel_info is None:
            return

        output_path = Path(self._app_config.output.path)
        output_path.mkdir(parents=True, exist_ok=True)

        progress_file = output_path / f"progress_{self._task_id}.json"
        data = self._novel_info.model_dump_json(indent=2)

        with open(progress_file, "w", encoding="utf-8") as f:
            f.write(data)

        logger.info(f"进度已保存: {progress_file}")

    def get_cost_report(self) -> dict:
        """获取成本报告"""
        return self._llm_client.get_cost_summary()

    def get_status(self) -> dict:
        """
        获取当前任务状态的摘要信息。

        Returns:
            dict: 任务状态摘要
        """
        if self._state is None:
            return {
                "task_id": self._task_id,
                "status": "not_started",
                "progress": 0.0,
                "current_chapter": 0,
                "total_chapters": 0,
                "total_words": 0,
                "actual_cost": 0.0,
                "estimated_cost": 0.0,
                "error_message": "",
            }

        return {
            "task_id": self._state.task_id,
            "status": self._state.status.value,
            "progress": round(self._state.progress, 1),
            "current_chapter": self._state.current_chapter,
            "total_chapters": self._state.total_chapters,
            "total_words": self._state.total_words,
            "actual_cost": round(self._state.actual_cost, 4),
            "estimated_cost": round(self._state.estimated_cost, 4),
            "error_message": self._state.error_message,
            "start_time": self._state.start_time.isoformat() if self._state.start_time else None,
            "end_time": self._state.end_time.isoformat() if self._state.end_time else None,
            "novel_name": self._novel_info.name if self._novel_info else "",
            "completed_chapters": len(self._novel_info.chapters) if self._novel_info else 0,
        }
