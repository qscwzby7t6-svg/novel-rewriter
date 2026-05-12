"""
写作引擎服务

负责调用LLM生成小说内容，包括章节大纲生成和正文生成。
"""

import logging
from typing import Optional

from backend.models.schemas import (
    Chapter,
    ChapterOutline,
    NovelInfo,
    WritingStyle,
    WorldSetting,
)
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class Writer:
    """写作引擎"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化写作引擎。

        Args:
            llm_client: LLM客户端
        """
        self._llm = llm_client

    async def generate_chapter_outline(
        self,
        chapter_number: int,
        novel_info: NovelInfo,
        previous_outline: Optional[ChapterOutline] = None,
    ) -> ChapterOutline:
        """
        生成章节大纲。

        Args:
            chapter_number: 章节序号
            novel_info: 小说信息
            previous_outline: 上一章大纲

        Returns:
            ChapterOutline: 章节大纲
        """
        logger.info(f"生成第{chapter_number}章大纲...")

        # TODO: 构建提示词并调用LLM生成大纲
        outline = ChapterOutline(
            chapter_number=chapter_number,
            title=f"第{chapter_number}章",
            word_count_target=novel_info.chapter_words_target,
        )

        logger.info(f"第{chapter_number}章大纲生成完成")
        return outline

    async def generate_chapter_content(
        self,
        outline: ChapterOutline,
        novel_info: NovelInfo,
        context: str = "",
    ) -> Chapter:
        """
        生成章节正文。

        Args:
            outline: 章节大纲
            novel_info: 小说信息
            context: 上下文信息

        Returns:
            Chapter: 生成的章节
        """
        logger.info(f"生成第{outline.chapter_number}章正文...")

        # TODO: 构建提示词并调用LLM生成正文
        chapter = Chapter(
            chapter_number=outline.chapter_number,
            title=outline.title,
            content="",
            word_count=0,
        )

        logger.info(f"第{outline.chapter_number}章正文生成完成")
        return chapter

    async def continue_writing(
        self,
        partial_chapter: Chapter,
        target_words: int,
        novel_info: NovelInfo,
    ) -> Chapter:
        """
        续写章节内容（字数不足时）。

        Args:
            partial_chapter: 部分完成的章节
            target_words: 目标字数
            novel_info: 小说信息

        Returns:
            Chapter: 续写后的章节
        """
        logger.info(
            f"续写第{partial_chapter.chapter_number}章, "
            f"当前{partial_chapter.word_count}字, 目标{target_words}字..."
        )

        # TODO: 实现续写逻辑
        return partial_chapter

    async def revise_chapter(
        self,
        chapter: Chapter,
        feedback: str = "",
    ) -> Chapter:
        """
        根据反馈修改章节。

        Args:
            chapter: 待修改的章节
            feedback: 修改反馈

        Returns:
            Chapter: 修改后的章节
        """
        logger.info(f"修改第{chapter.chapter_number}章...")

        # TODO: 构建修改提示词并调用LLM
        return chapter


# 兼容别名
WritingEngine = Writer
