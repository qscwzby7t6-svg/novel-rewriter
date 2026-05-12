"""
文本解析器测试
"""

import pytest
from backend.services.parser import TextParser


class TestTextParser:
    """TextParser测试类"""

    @pytest.fixture
    def parser(self):
        return TextParser()

    def test_split_chapters_basic(self, parser):
        """测试基本章节分割"""
        text = (
            "第一章 初入江湖\n"
            "少年踏上了旅途。\n"
            "他背着一把旧剑。\n"
            "\n"
            "第二章 奇遇\n"
            "在山洞中发现了一本秘籍。\n"
            "他开始修炼。\n"
        )

        chapters = parser._split_chapters(text)
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第一章 初入江湖"
        assert chapters[1]["title"] == "第二章 奇遇"

    def test_split_chapters_no_chapter_title(self, parser):
        """测试没有章节标题的文本"""
        text = "这是一段没有章节标题的文本。\n" "只是普通的段落。"

        chapters = parser._split_chapters(text)
        assert len(chapters) == 0

    def test_split_chapters_arabic_numerals(self, parser):
        """测试阿拉伯数字章节标题"""
        text = "第1章 开始\n内容\n\n第2章 发展\n更多内容"

        chapters = parser._split_chapters(text)
        assert len(chapters) == 2
        assert chapters[0]["title"] == "第1章 开始"
        assert chapters[1]["title"] == "第2章 发展"

    def test_count_words_chinese(self, parser):
        """测试中文字数统计"""
        text = "这是一个测试文本。包含中文和English混合。"
        count = parser.count_words(text)
        assert count == 14  # 14个中文字符

    def test_count_words_empty(self, parser):
        """测试空文本字数统计"""
        assert parser.count_words("") == 0

    def test_extract_dialogues(self, parser):
        """测试对话提取"""
        text = '他说："你好啊。"\n她回答："你好。"'
        dialogues = parser.extract_dialogues(text)
        assert len(dialogues) == 2
        assert "你好啊。" in dialogues
        assert "你好。" in dialogues

    def test_extract_dialogues_japanese_quotes(self, parser):
        """测试日式引号对话提取"""
        text = "「这是日式引号」\n『这也是日式引号』"
        dialogues = parser.extract_dialogues(text)
        assert len(dialogues) == 2

    @pytest.mark.asyncio
    async def test_parse_novel_text(self, parser):
        """测试小说文本解析"""
        text = "第一章 测试\n这是测试内容。\n\n第二章 继续\n更多内容。"
        novel_info = await parser.parse_novel_text(text, "测试小说")

        assert novel_info.name == "测试小说"
        assert novel_info.total_chapters == 2

    def test_is_chapter_title_pattern(self, parser):
        """测试章节标题识别"""
        assert parser._chapter_pattern.match("第一章 开始") is not None
        assert parser._chapter_pattern.match("第100章 大结局") is not None
        assert parser._chapter_pattern.match("第十二章 转折") is not None
        assert parser._chapter_pattern.match("这是普通文本") is None
        assert parser._chapter_pattern.match("") is None
