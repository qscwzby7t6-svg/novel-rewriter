"""
集成测试 - novel-rewriter 核心功能测试

测试范围：
1. 文本预处理功能（parser.py 的 preprocess_text 方法）
2. 去AI化功能（deai.py 的 replace_ai_vocabulary 和 abstract_to_concrete 方法）
3. 版权检测功能（copyright.py 的 check_ngram_similarity 方法）
4. 字数控制功能（chapter_ctrl.py 的 check_word_count 方法）
5. 节奏曲线设计（chapter_ctrl.py 的 design_rhythm_curve 方法）
6. 文本工具函数（text_utils.py 的所有函数）

所有测试均使用 mock，不需要真实的 API key。
"""

import asyncio
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 测试1: 文本预处理功能
# ============================================================

class TestTextParserPreprocess(unittest.TestCase):
    """测试 TextParser.preprocess_text 方法（纯规则，不需要LLM）"""

    def setUp(self):
        from backend.services.parser import TextParser
        from backend.services.llm_client import LLMClient
        # 使用 mock LLMClient
        mock_llm = MagicMock(spec=LLMClient)
        self.parser = TextParser(mock_llm)

    def test_preprocess_removes_advertisements(self):
        """测试广告过滤"""
        text = (
            "第一章 开始\n"
            "这是正文内容。\n"
            "求更票！\n"
            "PS：加群讨论\n"
            "更多内容请访问www.example.com\n"
            "正文继续。\n"
        )
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        # 广告应被移除
        combined = "\n".join(ch["content"] for ch in result)
        self.assertNotIn("PS", combined)
        self.assertNotIn("www.example.com", combined)

    def test_preprocess_splits_chapters(self):
        """测试章节分割"""
        text = (
            "第一章 初入江湖\n"
            "少年行走在山间小路上，微风拂过他的脸颊。\n\n"
            "第二章 奇遇\n"
            "他在山洞中发现了一本古书，上面记载着失传的功法。\n\n"
            "第三章 突破\n"
            "修炼之后他突破了第一层境界，浑身充满了力量。\n"
        )
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["title"], "第一章 初入江湖")
        self.assertEqual(result[1]["title"], "第二章 奇遇")
        self.assertEqual(result[2]["title"], "第三章 突破")

    def test_preprocess_counts_words(self):
        """测试字数统计"""
        text = (
            "第一章 测试\n"
            "这是一个测试章节，包含一些中文内容。\n"
        )
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        self.assertTrue(len(result) > 0)
        self.assertTrue(result[0]["word_count"] > 0)

    def test_preprocess_normalizes_punctuation(self):
        """测试标点标准化"""
        text = "第一章 测试\uff0e正文内容。"
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        combined = "\n".join(ch["content"] for ch in result)
        # 全角句点应被替换为中文句号
        self.assertNotIn("\uff0e", combined)

    def test_preprocess_empty_text(self):
        """测试空文本处理"""
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text("")
        )
        self.assertEqual(len(result), 0)

    def test_preprocess_no_chapter_titles(self):
        """测试无章节标题的文本"""
        text = "这是一段没有章节标题的正文。\n\n" * 20
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        # 没有章节标题时，整段文本作为单一章节处理
        self.assertTrue(len(result) >= 1)

    def test_preprocess_filters_short_chapters(self):
        """测试过滤过短章节"""
        text = (
            "第一章 正常章节\n"
            "这是一段足够长的正常章节内容，字数超过十个字。\n\n"
            "第二章 短章节\n"
            "短\n\n"
        )
        result = asyncio.get_event_loop().run_until_complete(
            self.parser.preprocess_text(text)
        )
        # 短章节应被过滤（word_count <= 10）
        for ch in result:
            self.assertTrue(ch["word_count"] > 10)


# ============================================================
# 测试2: 去AI化功能
# ============================================================

class TestDeAIService(unittest.TestCase):
    """测试 DeAIService 的规则方法"""

    def setUp(self):
        from backend.services.deai import DeAIService
        self.deai = DeAIService(llm_client=None)

    def test_detect_ai_traces(self):
        """测试AI痕迹检测"""
        text = "总之，这是一个非常重要的决定。综上所述，我们应该采取行动。"
        traces = self.deai.detect_ai_traces(text)
        self.assertTrue(len(traces) > 0)
        # 检查检测到的痕迹包含位置信息
        for trace in traces:
            self.assertIn("start", trace)
            self.assertIn("end", trace)
            self.assertIn("content", trace)

    def test_detect_ai_traces_clean_text(self):
        """测试干净文本的AI痕迹检测"""
        text = "他抬起头，目光如炬，手中的长剑泛着寒光。"
        traces = self.deai.detect_ai_traces(text)
        self.assertEqual(len(traces), 0)

    def test_calculate_ai_score(self):
        """测试AI痕迹评分"""
        text_with_traces = "总之，综上所述，值得注意的是，毫无疑问，众所周知，"
        score = self.deai.calculate_ai_score(text_with_traces)
        self.assertTrue(0.0 < score <= 1.0)

    def test_calculate_ai_score_clean(self):
        """测试干净文本的AI评分"""
        text = "他抬起头，目光如炬，手中的长剑泛着寒光。"
        score = self.deai.calculate_ai_score(text)
        self.assertEqual(score, 0.0)

    def test_calculate_ai_score_empty(self):
        """测试空文本的AI评分"""
        score = self.deai.calculate_ai_score("")
        self.assertEqual(score, 0.0)

    def test_remove_ai_traces(self):
        """测试去除AI痕迹"""
        text = "总之，这是一个重要的决定。他继续前行。"
        result = self.deai.remove_ai_traces(text)
        self.assertNotIn("总之", result)
        self.assertIn("他继续前行", result)

    def test_replace_ai_vocabulary(self):
        """测试AI词汇替换"""
        text = "综上所述，这是一个值得注意的问题。与此同时，另一个问题也出现了。"
        result = self.deai.replace_ai_vocabulary(text)
        self.assertNotIn("综上所述", result)
        self.assertNotIn("与此同时", result)

    def test_replace_ai_vocabulary_clean(self):
        """测试干净文本的词汇替换"""
        text = "他抬起头，目光如炬，手中的长剑泛着寒光。"
        result = self.deai.replace_ai_vocabulary(text)
        self.assertEqual(result, text)

    def test_abstract_to_concrete(self):
        """测试抽象到具体的转换"""
        text = "她有着美丽的容貌，站在古老的城墙下。"
        result = self.deai.abstract_to_concrete(text)
        # 至少有一个抽象词被替换
        self.assertNotEqual(result, text)
        # 替换后的文本应包含具体表达
        self.assertTrue(len(result) > 0)

    def test_abstract_to_concrete_no_match(self):
        """测试无匹配的抽象到具体转换"""
        text = "他抬起头，目光如炬，手中的长剑泛着寒光。"
        result = self.deai.abstract_to_concrete(text)
        # 没有匹配的抽象词，文本不变
        self.assertEqual(result, text)


# ============================================================
# 测试3: 版权检测功能
# ============================================================

class TestCopyrightDetector(unittest.TestCase):
    """测试 CopyrightDetector 的纯Python方法"""

    def setUp(self):
        from backend.services.copyright import CopyrightDetector
        self.detector = CopyrightDetector()

    def test_ngram_similarity_identical(self):
        """测试完全相同文本的N-gram相似度"""
        text = "这是一个测试文本，用于检测版权相似度。"
        result = self.detector.check_ngram_similarity(text, text)
        self.assertEqual(result["similarity"], 1.0)
        self.assertEqual(result["risk_level"], "high")

    def test_ngram_similarity_different(self):
        """测试完全不同文本的N-gram相似度"""
        text1 = "他拿起长剑，向敌人冲去。"
        text2 = "今天天气很好，阳光明媚。"
        result = self.detector.check_ngram_similarity(text1, text2)
        self.assertTrue(result["similarity"] < 0.3)
        self.assertIn(result["risk_level"], ["safe", "low"])

    def test_ngram_similarity_empty(self):
        """测试空文本的N-gram相似度"""
        result = self.detector.check_ngram_similarity("", "some text")
        self.assertEqual(result["similarity"], 0.0)
        self.assertEqual(result["risk_level"], "safe")

    def test_ngram_similarity_partial(self):
        """测试部分相似文本的N-gram相似度"""
        text1 = "他拿起长剑，向敌人冲去，剑光如虹。"
        text2 = "他拿起长剑，向敌人冲去，气势如虹。"
        result = self.detector.check_ngram_similarity(text1, text2, n=3)
        # 应该有一定相似度
        self.assertTrue(result["similarity"] > 0.0)
        self.assertTrue(result["similarity"] <= 1.0)

    def test_sentence_similarity(self):
        """测试句子级相似度"""
        text1 = "他拿起长剑，向敌人冲去。剑光闪烁之间，敌人纷纷倒下。"
        text2 = "他拿起长剑，向敌人冲去。剑光闪烁之间，敌人纷纷倒下。"
        result = self.detector.check_sentence_similarity(text1, text2)
        self.assertTrue(result["identical_sentences"] > 0)

    def test_sentence_similarity_different(self):
        """测试不同文本的句子级相似度"""
        text1 = "他拿起长剑，向敌人冲去。"
        text2 = "今天天气很好，阳光明媚。"
        result = self.detector.check_sentence_similarity(text1, text2)
        self.assertEqual(result["identical_sentences"], 0)

    def test_paragraph_similarity(self):
        """测试段落级相似度"""
        text1 = "他拿起长剑，向敌人冲去。剑光闪烁之间，敌人纷纷倒下。" * 5
        text2 = "他拿起长剑，向敌人冲去。剑光闪烁之间，敌人纷纷倒下。" * 5
        result = self.detector.check_paragraph_similarity(text1, text2)
        self.assertTrue(result["similarity"] > 0.0)

    def test_character_name_similarity(self):
        """测试角色名称相似度"""
        names1 = ["张三", "李四", "王五"]
        names2 = ["张三", "赵六", "钱七"]
        result = self.detector.check_character_name_similarity(names1, names2)
        self.assertEqual(len(result["identical_names"]), 1)
        self.assertIn("张三", result["identical_names"])

    def test_character_name_similarity_all_different(self):
        """测试完全不同角色名的相似度"""
        names1 = ["张三", "李四", "王五"]
        names2 = ["赵六", "钱七", "孙八"]
        result = self.detector.check_character_name_similarity(names1, names2)
        self.assertEqual(len(result["identical_names"]), 0)
        self.assertTrue(result["similarity"] < 0.5)

    def test_assess_risk(self):
        """测试风险评估"""
        self.assertEqual(
            self.detector.assess_risk(0.05).value, "safe"
        )
        self.assertEqual(
            self.detector.assess_risk(0.20).value, "low"
        )
        self.assertEqual(
            self.detector.assess_risk(0.35).value, "medium"
        )
        self.assertEqual(
            self.detector.assess_risk(0.60).value, "high"
        )


# ============================================================
# 测试4: 字数控制功能
# ============================================================

class TestChapterControllerWordCount(unittest.TestCase):
    """测试 ChapterController.check_word_count 方法"""

    def setUp(self):
        from backend.services.chapter_ctrl import ChapterController
        from backend.services.writer import Writer
        from backend.services.context_mgr import ContextManager
        from backend.services.llm_client import LLMClient
        from backend.models.schemas import NovelInfo

        # 创建 mock 对象
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.reset_chapter_cost = MagicMock()
        mock_writer = MagicMock(spec=Writer)
        mock_novel_info = MagicMock(spec=NovelInfo)
        mock_novel_info.chapter_words_target = 3000

        mock_context = MagicMock(spec=ContextManager)
        mock_context._novel_info = mock_novel_info

        self.controller = ChapterController(
            llm_client=mock_llm,
            writer=mock_writer,
            context_manager=mock_context,
        )

    def test_check_word_count_pass(self):
        """测试字数在范围内"""
        # 生成约3000字的文本
        text = "这是一段测试文本。" * 300  # 约3000字
        result = self.controller.check_word_count(text, 3000)
        self.assertTrue(result["pass"])
        self.assertIn("current", result)
        self.assertIn("target", result)
        self.assertIn("min", result)
        self.assertIn("max", result)

    def test_check_word_count_too_short(self):
        """测试字数不足"""
        text = "短文本"
        result = self.controller.check_word_count(text, 3000)
        self.assertFalse(result["pass"])
        self.assertTrue(result["diff"] < 0)

    def test_check_word_count_too_long(self):
        """测试字数超出"""
        text = "这是一段很长的测试文本。" * 500  # 约5000字
        result = self.controller.check_word_count(text, 3000)
        self.assertFalse(result["pass"])
        self.assertTrue(result["diff"] > 0)

    def test_check_word_count_exact(self):
        """测试精确字数"""
        # 创建恰好3000字的文本
        text = "字" * 3000
        result = self.controller.check_word_count(text, 3000)
        self.assertTrue(result["pass"])
        self.assertEqual(result["diff"], 0)

    def test_check_word_count_empty(self):
        """测试空文本"""
        result = self.controller.check_word_count("", 3000)
        self.assertFalse(result["pass"])
        self.assertEqual(result["current"], 0)

    def test_check_word_count_tolerance(self):
        """测试自定义容差"""
        text = "字" * 2500  # 2500字
        result = self.controller.check_word_count(text, 3000, tolerance=0.2)
        # 20%容差: 2400-3600, 2500在范围内
        self.assertTrue(result["pass"])


# ============================================================
# 测试5: 节奏曲线设计
# ============================================================

class TestRhythmCurve(unittest.TestCase):
    """测试 ChapterController.design_rhythm_curve 方法"""

    def setUp(self):
        from backend.services.chapter_ctrl import ChapterController, RHYTHM_TYPES
        from backend.services.writer import Writer
        from backend.services.context_mgr import ContextManager
        from backend.services.llm_client import LLMClient
        from backend.models.schemas import NovelInfo

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.reset_chapter_cost = MagicMock()
        mock_writer = MagicMock(spec=Writer)
        mock_novel_info = MagicMock(spec=NovelInfo)
        mock_novel_info.chapter_words_target = 3000
        mock_context = MagicMock(spec=ContextManager)
        mock_context._novel_info = mock_novel_info

        self.controller = ChapterController(
            llm_client=mock_llm,
            writer=mock_writer,
            context_manager=mock_context,
        )
        self.RHYTHM_TYPES = RHYTHM_TYPES

    def test_design_rhythm_curve_10_chapters(self):
        """测试10章节奏曲线"""
        curve = self.controller.design_rhythm_curve(10)
        self.assertEqual(len(curve), 10)
        # 应包含所有节奏类型
        unique_types = set(curve)
        self.assertIn("setup", unique_types)
        self.assertIn("development", unique_types)
        self.assertIn("rising", unique_types)
        self.assertIn("climax", unique_types)
        self.assertIn("falling", unique_types)
        self.assertIn("resolution", unique_types)

    def test_design_rhythm_curve_30_chapters(self):
        """测试30章节奏曲线（3个完整周期）"""
        curve = self.controller.design_rhythm_curve(30)
        self.assertEqual(len(curve), 30)
        # 每个周期应有高潮
        climax_count = curve.count("climax")
        self.assertTrue(climax_count >= 3)

    def test_design_rhythm_curve_5_chapters(self):
        """测试5章节奏曲线（不足10章）"""
        curve = self.controller.design_rhythm_curve(5)
        self.assertEqual(len(curve), 5)
        # 所有类型都应是有效的
        for r in curve:
            self.assertIn(r, self.RHYTHM_TYPES)

    def test_design_rhythm_curve_1_chapter(self):
        """测试1章节奏曲线"""
        curve = self.controller.design_rhythm_curve(1)
        self.assertEqual(len(curve), 1)
        self.assertIn(curve[0], self.RHYTHM_TYPES)

    def test_design_rhythm_curve_0_chapters(self):
        """测试0章节奏曲线"""
        curve = self.controller.design_rhythm_curve(0)
        self.assertEqual(len(curve), 0)

    def test_design_rhythm_curve_25_chapters(self):
        """测试25章节奏曲线（2个完整周期+5章余数）"""
        curve = self.controller.design_rhythm_curve(25)
        self.assertEqual(len(curve), 25)
        # 应有至少2个高潮
        climax_count = curve.count("climax")
        self.assertTrue(climax_count >= 2)

    def test_design_rhythm_curve_100_chapters(self):
        """测试100章节奏曲线"""
        curve = self.controller.design_rhythm_curve(100)
        self.assertEqual(len(curve), 100)
        # 应有至少10个高潮（每10章至少1个）
        climax_count = curve.count("climax")
        self.assertTrue(climax_count >= 10)

    def test_rhythm_curve_ends_with_resolution(self):
        """测试节奏曲线是否以收束结尾（10章周期）"""
        curve = self.controller.design_rhythm_curve(10)
        # 最后一个周期应以resolution结尾
        self.assertEqual(curve[-1], "resolution")


# ============================================================
# 测试6: 文本工具函数
# ============================================================

class TestTextUtils(unittest.TestCase):
    """测试 text_utils.py 的所有函数"""

    def test_count_chinese_chars(self):
        """测试中文字符统计"""
        from backend.utils.text_utils import count_chinese_chars
        self.assertEqual(count_chinese_chars("你好世界"), 4)
        self.assertEqual(count_chinese_chars("Hello"), 0)
        self.assertEqual(count_chinese_chars("你好Hello世界"), 4)
        self.assertEqual(count_chinese_chars(""), 0)

    def test_count_words(self):
        """测试总字数统计"""
        from backend.utils.text_utils import count_words
        self.assertEqual(count_words("你好世界"), 4)
        self.assertEqual(count_words("Hello World"), 2)
        self.assertEqual(count_words("你好Hello世界"), 5)  # 4中文 + 1英文词
        self.assertEqual(count_words(""), 0)

    def test_split_into_paragraphs(self):
        """测试段落分割"""
        from backend.utils.text_utils import split_into_paragraphs
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        result = split_into_paragraphs(text)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "第一段内容。")

    def test_split_into_paragraphs_single(self):
        """测试单段落分割"""
        from backend.utils.text_utils import split_into_paragraphs
        text = "只有一段内容。"
        result = split_into_paragraphs(text)
        self.assertEqual(len(result), 1)

    def test_split_into_sentences(self):
        """测试句子分割"""
        from backend.utils.text_utils import split_into_sentences
        text = "这是第一句。这是第二句！这是第三句？这是第四句。"
        result = split_into_sentences(text)
        self.assertEqual(len(result), 4)

    def test_split_into_sentences_empty(self):
        """测试空文本的句子分割"""
        from backend.utils.text_utils import split_into_sentences
        result = split_into_sentences("")
        self.assertEqual(len(result), 0)

    def test_extract_dialogues_double_quote(self):
        """测试双引号对话提取"""
        from backend.utils.text_utils import extract_dialogues
        text = '他说："你好啊。"她回答："你也好。"'
        result = extract_dialogues(text)
        self.assertEqual(len(result), 2)
        self.assertIn("你好啊。", result)
        self.assertIn("你也好。", result)

    def test_extract_dialogues_japanese_quote(self):
        """测试日式引号对话提取"""
        from backend.utils.text_utils import extract_dialogues
        text = '他说：「你好啊。」她回答：「你也好。」'
        result = extract_dialogues(text)
        self.assertEqual(len(result), 2)

    def test_extract_dialogues_no_dialogue(self):
        """测试无对话文本"""
        from backend.utils.text_utils import extract_dialogues
        text = "这是一段没有对话的纯叙述文本。"
        result = extract_dialogues(text)
        self.assertEqual(len(result), 0)

    def test_clean_text(self):
        """测试文本清理"""
        from backend.utils.text_utils import clean_text
        text = "  第一行  \n\n\n  第二行  \n  第三行  "
        result = clean_text(text)
        # 多余空行应被合并
        self.assertNotIn("\n\n\n", result)

    def test_clean_text_fullwidth_space(self):
        """测试全角空格替换"""
        from backend.utils.text_utils import clean_text
        text = "这是\u3000全角空格"
        result = clean_text(text)
        self.assertNotIn("\u3000", result)
        self.assertIn(" ", result)

    def test_truncate_text_short(self):
        """测试短文本截断（不截断）"""
        from backend.utils.text_utils import truncate_text
        text = "短文本"
        result = truncate_text(text, max_length=100)
        self.assertEqual(result, text)

    def test_truncate_text_long(self):
        """测试长文本截断"""
        from backend.utils.text_utils import truncate_text
        text = "这是一段很长的文本" * 50
        result = truncate_text(text, max_length=20)
        self.assertTrue(len(result) <= 20)
        self.assertTrue(result.endswith("..."))

    def test_truncate_text_custom_suffix(self):
        """测试自定义截断后缀"""
        from backend.utils.text_utils import truncate_text
        text = "这是一段很长的文本" * 50
        result = truncate_text(text, max_length=20, suffix="...")
        self.assertTrue(result.endswith("..."))

    def test_calculate_reading_time(self):
        """测试阅读时间估算"""
        from backend.utils.text_utils import calculate_reading_time
        # 500字/分钟，1000字应约为2分钟
        text = "字" * 1000
        result = calculate_reading_time(text, chars_per_minute=500)
        self.assertEqual(result, 2)

    def test_calculate_reading_time_minimum(self):
        """测试阅读时间最小值"""
        from backend.utils.text_utils import calculate_reading_time
        result = calculate_reading_time("短", chars_per_minute=500)
        self.assertEqual(result, 1)  # 最小1分钟

    def test_normalize_chapter_title(self):
        """测试章节标题标准化"""
        from backend.utils.text_utils import normalize_chapter_title
        self.assertEqual(normalize_chapter_title("一章 开始"), "第一章 开始")
        self.assertEqual(normalize_chapter_title("第一章 开始"), "第一章 开始")

    def test_is_chapter_title(self):
        """测试章节标题判断"""
        from backend.utils.text_utils import is_chapter_title
        self.assertTrue(is_chapter_title("第一章 开始"))
        self.assertTrue(is_chapter_title("第100章 大结局"))
        self.assertFalse(is_chapter_title("第三章"))  # 需要章后面有内容
        self.assertFalse(is_chapter_title("这不是章节标题"))
        self.assertFalse(is_chapter_title("1. 一些内容"))
        self.assertFalse(is_chapter_title(""))


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == "__main__":
    # 使用 unittest 运行
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTextParserPreprocess))
    suite.addTests(loader.loadTestsFromTestCase(TestDeAIService))
    suite.addTests(loader.loadTestsFromTestCase(TestCopyrightDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestChapterControllerWordCount))
    suite.addTests(loader.loadTestsFromTestCase(TestRhythmCurve))
    suite.addTests(loader.loadTestsFromTestCase(TestTextUtils))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "=" * 60)
    print(f"测试总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)
