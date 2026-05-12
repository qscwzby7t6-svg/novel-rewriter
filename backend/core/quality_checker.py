"""
质量检查器

负责对生成的章节进行多维度质量评估。
"""

import logging
import re
from typing import Optional

from backend.models.enums import QualityLevel
from backend.models.schemas import (
    Chapter,
    QualityIssue,
    QualityReport,
)

logger = logging.getLogger(__name__)


class QualityChecker:
    """质量检查器"""

    def __init__(self, threshold: float = 0.7):
        """
        初始化质量检查器。

        Args:
            threshold: 质量阈值（0-1）
        """
        self._threshold = threshold

    def check_chapter(
        self,
        chapter: Chapter,
        novel_context: str = "",
    ) -> QualityReport:
        """
        对章节进行全面质量检查。

        Args:
            chapter: 待检查的章节
            novel_context: 小说上下文信息

        Returns:
            QualityReport: 质量报告
        """
        logger.info(f"质量检查: 第{chapter.chapter_number}章")

        content = chapter.content
        if not content:
            return QualityReport(
                chapter_number=chapter.chapter_number,
                quality_level=QualityLevel.UNACCEPTABLE,
                issues=[QualityIssue(
                    type="empty_content",
                    description="章节内容为空",
                    severity="error",
                )],
            )

        # 各维度评分
        coherence = self._check_coherence(content, novel_context)
        character_consistency = self._check_character_consistency(content)
        plot_logic = self._check_plot_logic(content)
        language_quality = self._check_language_quality(content)

        # 综合评分
        overall = (
            0.25 * coherence +
            0.25 * character_consistency +
            0.25 * plot_logic +
            0.25 * language_quality
        )

        # 收集问题
        issues = self._collect_issues(content, chapter.chapter_number)
        suggestions = self._generate_suggestions(issues)

        # 确定质量等级
        quality_level = self._determine_quality_level(overall)

        report = QualityReport(
            chapter_number=chapter.chapter_number,
            overall_score=round(overall, 4),
            quality_level=quality_level,
            coherence_score=round(coherence, 4),
            character_consistency=round(character_consistency, 4),
            plot_logic=round(plot_logic, 4),
            language_quality=round(language_quality, 4),
            issues=issues,
            suggestions=suggestions,
        )

        logger.info(
            f"质量检查完成: 第{chapter.chapter_number}章, "
            f"评分={overall:.2f}, 等级={quality_level.value}"
        )

        return report

    def is_acceptable(self, report: QualityReport) -> bool:
        """
        判断质量报告是否达标。

        Args:
            report: 质量报告

        Returns:
            bool: 是否达标
        """
        return report.overall_score >= self._threshold

    def _check_coherence(self, content: str, context: str) -> float:
        """检查连贯性"""
        # TODO: 实现更复杂的连贯性检查
        # 当前使用简单启发式方法
        score = 0.7  # 基础分

        # 检查段落过渡
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            # 段落间是否有逻辑连接
            score += 0.1

        # 检查句子长度变化
        sentences = re.split(r"[。！？]", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            lengths = [len(s) for s in sentences]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            # 有一定变化说明句式多样
            if variance > 10:
                score += 0.1

        return min(score, 1.0)

    def _check_character_consistency(self, content: str) -> float:
        """检查角色一致性"""
        # TODO: 实现角色一致性检查
        return 0.8

    def _check_plot_logic(self, content: str) -> float:
        """检查情节逻辑"""
        # TODO: 实现情节逻辑检查
        return 0.8

    def _check_language_quality(self, content: str) -> float:
        """检查语言质量"""
        score = 0.8

        # 检查重复用词
        words = re.findall(r"[\u4e00-\u9fff]{2,4}", content)
        if words:
            from collections import Counter
            word_counts = Counter(words)
            # 高频词比例
            top_10_count = sum(c for _, c in word_counts.most_common(10))
            total_count = len(words)
            if total_count > 0:
                repeat_ratio = top_10_count / total_count
                if repeat_ratio > 0.15:
                    score -= 0.2
                elif repeat_ratio > 0.10:
                    score -= 0.1

        # 检查句子长度合理性
        sentences = re.split(r"[。！？]", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            too_long = sum(1 for s in sentences if len(s) > 100)
            if too_long / len(sentences) > 0.1:
                score -= 0.1

        return max(min(score, 1.0), 0.0)

    def _collect_issues(self, content: str, chapter_num: int) -> list[QualityIssue]:
        """收集质量问题"""
        issues = []

        # 检查字数
        word_count = len(re.findall(r"[\u4e00-\u9fff]", content))
        if word_count < 1000:
            issues.append(QualityIssue(
                type="word_count",
                description=f"章节字数过少: {word_count}字",
                location=f"第{chapter_num}章",
                severity="warning",
                suggestion="建议每章至少2000字",
            ))

        # 检查AI痕迹
        ai_patterns = [
            r"总之[，,]",
            r"综上所述",
            r"值得注意的是",
            r"众所周知",
        ]
        for pattern in ai_patterns:
            matches = re.findall(pattern, content)
            if matches:
                issues.append(QualityIssue(
                    type="ai_trace",
                    description=f"发现AI痕迹表达: {matches[0]}",
                    location=f"第{chapter_num}章",
                    severity="info",
                    suggestion="建议替换为更自然的表达",
                ))

        return issues

    def _generate_suggestions(self, issues: list[QualityIssue]) -> list[str]:
        """生成改进建议"""
        suggestions = []
        for issue in issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)
        return list(set(suggestions))  # 去重

    @staticmethod
    def _determine_quality_level(score: float) -> QualityLevel:
        """根据评分确定质量等级"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.75:
            return QualityLevel.GOOD
        elif score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
