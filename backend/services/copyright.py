"""
版权检测服务

负责检测生成文本与源小说之间的相似度，避免版权风险。
提供多维度检测：N-gram、句子级、段落级、角色名称相似度。
所有检测方法均为纯Python实现，不调用LLM，低成本运行。
"""

import logging
import re
from collections import Counter
from typing import Optional

from backend.models.enums import CopyrightRisk, QualityLevel
from backend.models.schemas import (
    Chapter,
    Character,
    NovelInfo,
    QualityIssue,
    QualityReport,
)

logger = logging.getLogger(__name__)


class CopyrightDetector:
    """
    版权检测器（完整版）

    提供多层次的版权检测能力：
    - N-gram 相似度检测
    - 句子级相似度检测（Jaccard + 编辑距离）
    - 段落级相似度检测
    - 角色名称相似度检测
    - 综合版权检测
    - 原创性报告生成
    """

    # 版权风险阈值
    NGRAM_HIGH_RISK = 0.30
    NGRAM_MEDIUM_RISK = 0.20
    NGRAM_SAFE = 0.10

    def __init__(self):
        """初始化版权检测器"""
        self._stop_words = self._load_stop_words()

    # ================================================================
    # 公开检测方法
    # ================================================================

    def check_ngram_similarity(self, text1: str, text2: str, n: int = 5) -> dict:
        """
        N-gram 相似度检测。

        使用字符级 N-gram 配合 Counter 计算两段文本的相似度。

        Args:
            text1: 待检测文本（生成文本）
            text2: 参考文本（源小说文本）
            n: N-gram 的 N 值，默认为 5

        Returns:
            dict: {
                "similarity": float,        # 相似度 0~1
                "matching_ngrams": int,     # 匹配的 n-gram 数量
                "total_ngrams": int,        # text1 的总 n-gram 数量
                "risk_level": str,          # 风险等级
            }
        """
        if not text1 or not text2:
            return {
                "similarity": 0.0,
                "matching_ngrams": 0,
                "total_ngrams": 0,
                "risk_level": CopyrightRisk.SAFE.value,
            }

        ngrams1 = self._build_ngram_counter(text1, n)
        ngrams2 = self._build_ngram_counter(text2, n)

        if not ngrams1 or not ngrams2:
            return {
                "similarity": 0.0,
                "matching_ngrams": 0,
                "total_ngrams": len(ngrams1),
                "risk_level": CopyrightRisk.SAFE.value,
            }

        # 计算匹配的 n-gram 数量（交集）
        matching = sum((ngrams1 & ngrams2).values())
        total = sum(ngrams1.values())
        similarity = matching / total if total > 0 else 0.0

        risk_level = self._assess_ngram_risk(similarity)

        return {
            "similarity": round(similarity, 4),
            "matching_ngrams": matching,
            "total_ngrams": total,
            "risk_level": risk_level.value,
        }

    def check_sentence_similarity(self, text1: str, text2: str) -> dict:
        """
        句子级相似度检测。

        将两段文本分句后，使用 Jaccard 相似度和编辑距离逐句比较。

        Args:
            text1: 待检测文本
            text2: 参考文本

        Returns:
            dict: {
                "similarity": float,           # 综合相似度 0~1
                "identical_sentences": int,    # 完全相同的句子数
                "similar_sentences": int,      # 相似（非完全相同）的句子数
                "total_sentences": int,        # text1 的总句子数
                "risk_level": str,
            }
        """
        if not text1 or not text2:
            return {
                "similarity": 0.0,
                "identical_sentences": 0,
                "similar_sentences": 0,
                "total_sentences": 0,
                "risk_level": CopyrightRisk.SAFE.value,
            }

        sentences1 = self._split_sentences(text1)
        sentences2 = self._split_sentences(text2)

        if not sentences1 or not sentences2:
            return {
                "similarity": 0.0,
                "identical_sentences": 0,
                "similar_sentences": 0,
                "total_sentences": len(sentences1),
                "risk_level": CopyrightRisk.SAFE.value,
            }

        identical = 0
        similar = 0
        matched_indices = set()

        for s1 in sentences1:
            best_sim = 0.0
            best_idx = -1
            for idx, s2 in enumerate(sentences2):
                if idx in matched_indices:
                    continue
                sim = self._sentence_jaccard(s1, s2)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_sim >= 1.0:
                identical += 1
                if best_idx >= 0:
                    matched_indices.add(best_idx)
            elif best_sim >= 0.6:
                # 进一步用编辑距离确认
                for idx, s2 in enumerate(sentences2):
                    if idx in matched_indices:
                        continue
                    edit_sim = self._edit_distance_similarity(s1, s2)
                    if edit_sim >= 0.7:
                        similar += 1
                        matched_indices.add(idx)
                        break

        total = len(sentences1)
        # 加权相似度：完全相同权重更高
        similarity = (identical * 1.0 + similar * 0.5) / total if total > 0 else 0.0
        similarity = min(similarity, 1.0)

        risk_level = self._assess_sentence_risk(similarity)

        return {
            "similarity": round(similarity, 4),
            "identical_sentences": identical,
            "similar_sentences": similar,
            "total_sentences": total,
            "risk_level": risk_level.value,
        }

    def check_paragraph_similarity(self, text1: str, text2: str) -> dict:
        """
        段落级相似度检测。

        将两段文本分段后，逐段比较 N-gram 相似度。

        Args:
            text1: 待检测文本
            text2: 参考文本

        Returns:
            dict: {
                "similarity": float,           # 最高段落相似度
                "avg_similarity": float,       # 平均段落相似度
                "high_risk_paragraphs": int,   # 高风险段落数
                "total_paragraphs": int,       # text1 的总段落数
                "risk_level": str,
            }
        """
        if not text1 or not text2:
            return {
                "similarity": 0.0,
                "avg_similarity": 0.0,
                "high_risk_paragraphs": 0,
                "total_paragraphs": 0,
                "risk_level": CopyrightRisk.SAFE.value,
            }

        paragraphs1 = self._split_paragraphs(text1)
        paragraphs2 = self._split_paragraphs(text2)

        if not paragraphs1 or not paragraphs2:
            return {
                "similarity": 0.0,
                "avg_similarity": 0.0,
                "high_risk_paragraphs": 0,
                "total_paragraphs": len(paragraphs1),
                "risk_level": CopyrightRisk.SAFE.value,
            }

        max_sim = 0.0
        total_sim = 0.0
        high_risk_count = 0

        for p1 in paragraphs1[:30]:  # 限制计算量
            best_sim = 0.0
            for p2 in paragraphs2[:30]:
                sim = self._ngram_similarity(p1, p2, n=5)
                if sim > best_sim:
                    best_sim = sim
            total_sim += best_sim
            if best_sim > max_sim:
                max_sim = best_sim
            if best_sim >= self.NGRAM_HIGH_RISK:
                high_risk_count += 1

        avg_sim = total_sim / len(paragraphs1[:30]) if paragraphs1 else 0.0
        risk_level = self._assess_paragraph_risk(max_sim, high_risk_count)

        return {
            "similarity": round(max_sim, 4),
            "avg_similarity": round(avg_sim, 4),
            "high_risk_paragraphs": high_risk_count,
            "total_paragraphs": len(paragraphs1),
            "risk_level": risk_level.value,
        }

    def check_character_name_similarity(
        self, names1: list[str], names2: list[str]
    ) -> dict:
        """
        角色名称相似度检测。

        比较两个角色名称列表之间的相似度，检测是否使用了过于相似的角色名。

        Args:
            names1: 生成小说的角色名列表
            names2: 源小说的角色名列表

        Returns:
            dict: {
                "similarity": float,           # 名称相似度 0~1
                "identical_names": list[str],  # 完全相同的名称
                "similar_names": list[dict],   # 相似的名称对 [{"name1": ..., "name2": ..., "score": ...}]
                "total_names1": int,
                "total_names2": int,
                "risk_level": str,
            }
        """
        if not names1 or not names2:
            return {
                "similarity": 0.0,
                "identical_names": [],
                "similar_names": [],
                "total_names1": len(names1),
                "total_names2": len(names2),
                "risk_level": CopyrightRisk.SAFE.value,
            }

        # 标准化名称（去空格、统一大小写无关处理）
        norm1 = [n.strip() for n in names1 if n.strip()]
        norm2 = [n.strip() for n in names2 if n.strip()]

        set1 = set(norm1)
        set2 = set(norm2)

        # 完全相同的名称
        identical = list(set1 & set2)

        # 相似的名称对
        similar_pairs = []
        for n1 in norm1:
            if n1 in set2:
                continue  # 已在 identical 中
            for n2 in norm2:
                score = self._name_similarity(n1, n2)
                if score >= 0.7:
                    similar_pairs.append({
                        "name1": n1,
                        "name2": n2,
                        "score": round(score, 4),
                    })

        # 计算综合相似度
        total = len(norm1)
        if total > 0:
            similarity = (len(identical) + len(similar_pairs) * 0.5) / total
        else:
            similarity = 0.0
        similarity = min(similarity, 1.0)

        risk_level = self._assess_name_risk(similarity, identical, similar_pairs)

        return {
            "similarity": round(similarity, 4),
            "identical_names": identical,
            "similar_names": similar_pairs,
            "total_names1": len(norm1),
            "total_names2": len(norm2),
            "risk_level": risk_level.value,
        }

    def full_copyright_check(
        self, generated_text: str, original_text: str
    ) -> QualityReport:
        """
        完整的版权检测。

        综合所有检测维度，生成版权风险报告。

        Args:
            generated_text: 生成的文本
            original_text: 原始参考文本

        Returns:
            QualityReport: 包含版权相似度和风险建议的质量报告
        """
        logger.info("执行完整版权检测...")

        # 1. N-gram 相似度
        ngram_result = self.check_ngram_similarity(generated_text, original_text, n=5)

        # 2. 句子级相似度
        sentence_result = self.check_sentence_similarity(generated_text, original_text)

        # 3. 段落级相似度
        paragraph_result = self.check_paragraph_similarity(generated_text, original_text)

        # 综合评分（加权平均）
        overall_similarity = (
            0.4 * ngram_result["similarity"]
            + 0.3 * sentence_result["similarity"]
            + 0.3 * paragraph_result["similarity"]
        )

        # 确定风险等级
        risk = self._assess_overall_risk(overall_similarity)

        # 收集问题
        issues = []
        suggestions = []

        if ngram_result["risk_level"] == CopyrightRisk.HIGH.value:
            issues.append(QualityIssue(
                type="copyright_ngram",
                description=(
                    f"N-gram 相似度过高: {ngram_result['similarity']:.1%}, "
                    f"匹配 {ngram_result['matching_ngrams']}/{ngram_result['total_ngrams']} 个片段"
                ),
                severity="error",
                suggestion="建议大幅改写该章节，替换关键表达和句式",
            ))
            suggestions.append("N-gram 相似度超过30%，需要大幅改写")
        elif ngram_result["risk_level"] == CopyrightRisk.MEDIUM.value:
            issues.append(QualityIssue(
                type="copyright_ngram",
                description=(
                    f"N-gram 相似度中等: {ngram_result['similarity']:.1%}, "
                    f"匹配 {ngram_result['matching_ngrams']}/{ngram_result['total_ngrams']} 个片段"
                ),
                severity="warning",
                suggestion="建议修改部分相似段落，降低版权风险",
            ))
            suggestions.append("N-gram 相似度在20%-30%之间，建议局部改写")

        if sentence_result["identical_sentences"] > 0:
            issues.append(QualityIssue(
                type="copyright_sentence",
                description=(
                    f"发现 {sentence_result['identical_sentences']} 个完全相同的句子"
                ),
                severity="error",
                suggestion="请修改所有与原文完全相同的句子",
            ))
            suggestions.append(f"有 {sentence_result['identical_sentences']} 个句子与原文完全一致，必须修改")

        if sentence_result["similar_sentences"] > 5:
            issues.append(QualityIssue(
                type="copyright_sentence",
                description=(
                    f"发现 {sentence_result['similar_sentences']} 个高度相似的句子"
                ),
                severity="warning",
                suggestion="建议改写相似句子，增加差异化表达",
            ))

        if paragraph_result["high_risk_paragraphs"] > 0:
            issues.append(QualityIssue(
                type="copyright_paragraph",
                description=(
                    f"有 {paragraph_result['high_risk_paragraphs']} 个段落与原文高度相似"
                ),
                severity="error",
                suggestion="请重写高风险段落，确保原创性",
            ))
            suggestions.append(
                f"有 {paragraph_result['high_risk_paragraphs']} 个段落与原文高度相似，需要重写"
            )

        if not issues:
            suggestions.append("版权检测通过，文本原创性良好")

        # 确定质量等级
        if risk == CopyrightRisk.HIGH:
            quality_level = QualityLevel.UNACCEPTABLE
        elif risk == CopyrightRisk.MEDIUM:
            quality_level = QualityLevel.POOR
        elif risk == CopyrightRisk.LOW:
            quality_level = QualityLevel.ACCEPTABLE
        else:
            quality_level = QualityLevel.GOOD

        report = QualityReport(
            overall_score=round(1.0 - overall_similarity, 4),  # 越高越好
            quality_level=quality_level,
            copyright_similarity=round(overall_similarity, 4),
            issues=issues,
            suggestions=suggestions,
        )

        logger.info(
            f"版权检测完成: 综合相似度={overall_similarity:.4f}, "
            f"风险等级={risk.value}"
        )

        return report

    def generate_originality_report(
        self, generated: NovelInfo, original: NovelInfo
    ) -> dict:
        """
        生成原创性报告。

        对比生成小说与源小说在世界观、角色、力量体系、情节等维度的原创性。

        Args:
            generated: 生成的小说信息
            original: 源小说信息

        Returns:
            dict: 各维度的原创性评分和详细分析
        """
        logger.info("生成原创性报告...")

        report = {
            "overall_originality": 0.0,
            "dimensions": {},
            "high_risk_items": [],
            "suggestions": [],
        }

        scores = []

        # 1. 世界观原创性
        world_score = self._compare_world_setting(generated, original)
        report["dimensions"]["world_setting"] = world_score
        scores.append(world_score["score"])

        # 2. 角色原创性
        character_score = self._compare_characters(generated, original)
        report["dimensions"]["characters"] = character_score
        scores.append(character_score["score"])

        # 3. 力量体系原创性
        power_score = self._compare_power_system(generated, original)
        report["dimensions"]["power_system"] = power_score
        scores.append(power_score["score"])

        # 4. 情节原创性（基于章节内容抽样比较）
        plot_score = self._compare_plot(generated, original)
        report["dimensions"]["plot"] = plot_score
        scores.append(plot_score["score"])

        # 综合原创性评分
        overall = sum(scores) / len(scores) if scores else 0.0
        report["overall_originality"] = round(overall, 4)

        # 收集高风险项
        for dim_name, dim_data in report["dimensions"].items():
            if dim_data["score"] < 0.5:
                report["high_risk_items"].append({
                    "dimension": dim_name,
                    "score": dim_data["score"],
                    "reason": dim_data.get("reason", "与源小说相似度过高"),
                })

        # 生成建议
        if report["high_risk_items"]:
            report["suggestions"].append(
                f"发现 {len(report['high_risk_items'])} 个高风险维度，建议重点修改"
            )
            for item in report["high_risk_items"]:
                report["suggestions"].append(
                    f"  - {item['dimension']}: 原创性评分 {item['score']:.1%}, {item['reason']}"
                )
        else:
            report["suggestions"].append("各维度原创性良好，未发现明显版权风险")

        logger.info(f"原创性报告完成: 综合评分={overall:.4f}")

        return report

    # ================================================================
    # 兼容旧接口
    # ================================================================

    def check_similarity(
        self,
        generated_text: str,
        source_text: str,
    ) -> float:
        """
        计算生成文本与源文本的综合相似度（兼容旧接口）。

        Returns:
            float: 相似度分数（0-1，越低越安全）
        """
        if not generated_text or not source_text:
            return 0.0

        ngram_sim = self._ngram_similarity(generated_text, source_text, n=3)
        sentence_sim = self._sentence_similarity_old(generated_text, source_text)
        paragraph_sim = self._paragraph_similarity_old(generated_text, source_text)

        overall = 0.4 * ngram_sim + 0.3 * sentence_sim + 0.3 * paragraph_sim
        return round(min(overall, 1.0), 4)

    def assess_risk(self, similarity_score: float) -> CopyrightRisk:
        """根据相似度评分评估版权风险（兼容旧接口）"""
        if similarity_score < 0.15:
            return CopyrightRisk.SAFE
        elif similarity_score < 0.30:
            return CopyrightRisk.LOW
        elif similarity_score < 0.50:
            return CopyrightRisk.MEDIUM
        else:
            return CopyrightRisk.HIGH

    async def check_chapter(
        self,
        chapter: Chapter,
        source_text: str = "",
    ) -> tuple[CopyrightRisk, float]:
        """检测章节的版权风险（兼容旧接口）"""
        if not source_text:
            logger.warning("未提供源文本，跳过版权检测")
            return CopyrightRisk.SAFE, 0.0

        logger.info(f"检测第{chapter.chapter_number}章版权风险...")

        similarity = self.check_similarity(chapter.content, source_text)
        risk = self.assess_risk(similarity)

        logger.info(
            f"第{chapter.chapter_number}章版权检测结果: "
            f"相似度={similarity:.4f}, 风险等级={risk.value}"
        )

        return risk, similarity

    # ================================================================
    # N-gram 工具方法
    # ================================================================

    @staticmethod
    def _build_ngram_counter(text: str, n: int) -> Counter:
        """
        构建字符级 N-gram 的 Counter。

        Args:
            text: 输入文本
            n: N-gram 的 N 值

        Returns:
            Counter: N-gram 频次统计
        """
        # 过滤空白字符，保留中文、标点等
        chars = [c for c in text if c.strip()]
        if len(chars) < n:
            return Counter()
        ngrams = ["".join(chars[i:i + n]) for i in range(len(chars) - n + 1)]
        return Counter(ngrams)

    def _ngram_similarity(self, text1: str, text2: str, n: int = 3) -> float:
        """计算 N-gram 相似度（内部方法）"""
        ngrams1 = self._build_ngram_counter(text1, n)
        ngrams2 = self._build_ngram_counter(text2, n)

        if not ngrams1 or not ngrams2:
            return 0.0

        intersection = ngrams1 & ngrams2
        return len(intersection) / min(len(ngrams1), len(ngrams2))

    # ================================================================
    # 句子工具方法
    # ================================================================

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        将文本分割为句子列表。

        Args:
            text: 输入文本

        Returns:
            list[str]: 句子列表（过滤掉过短的句子）
        """
        # 按中文标点分句
        parts = re.split(r"[。！？\n]+", text)
        sentences = [s.strip() for s in parts if len(s.strip()) > 10]
        return sentences

    @staticmethod
    def _sentence_jaccard(s1: str, s2: str) -> float:
        """
        计算两个句子的 Jaccard 相似度（字符级 bigram）。

        Args:
            s1: 句子1
            s2: 句子2

        Returns:
            float: Jaccard 相似度 0~1
        """
        def get_bigrams(text: str) -> set:
            chars = [c for c in text if c.strip()]
            return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}

        bg1 = get_bigrams(s1)
        bg2 = get_bigrams(s2)

        if not bg1 or not bg2:
            return 0.0

        intersection = bg1 & bg2
        union = bg1 | bg2
        return len(intersection) / len(union)

    @staticmethod
    def _edit_distance_similarity(s1: str, s2: str) -> float:
        """
        基于编辑距离的句子相似度。

        使用动态规划计算 Levenshtein 编辑距离，然后归一化为相似度。

        Args:
            s1: 句子1
            s2: 句子2

        Returns:
            float: 相似度 0~1
        """
        len1, len2 = len(s1), len(s2)

        # 限制长度，避免过长句子的计算开销
        if len1 > 200 or len2 > 200:
            # 截取前200字符比较
            s1, s2 = s1[:200], s2[:200]
            len1, len2 = 200, min(len2, 200)

        # 动态规划计算编辑距离
        dp = list(range(len2 + 1))
        for i in range(1, len1 + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, len2 + 1):
                temp = dp[j]
                if s1[i - 1] == s2[j - 1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j - 1])
                prev = temp

        distance = dp[len2]
        max_len = max(len1, len2)
        if max_len == 0:
            return 1.0

        return 1.0 - (distance / max_len)

    def _sentence_similarity_old(self, text1: str, text2: str) -> float:
        """句子级相似度（旧接口内部方法）"""
        sentences1 = set(re.split(r"[。！？\n]", text1))
        sentences2 = set(re.split(r"[。！？\n]", text2))

        sentences1 = {s.strip() for s in sentences1 if len(s.strip()) > 10}
        sentences2 = {s.strip() for s in sentences2 if len(s.strip()) > 10}

        if not sentences1 or not sentences2:
            return 0.0

        exact_matches = sentences1 & sentences2
        return len(exact_matches) / min(len(sentences1), len(sentences2))

    # ================================================================
    # 段落工具方法
    # ================================================================

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """
        将文本分割为段落列表。

        Args:
            text: 输入文本

        Returns:
            list[str]: 段落列表（过滤掉过短的段落）
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        return paragraphs

    def _paragraph_similarity_old(self, text1: str, text2: str) -> float:
        """段落级相似度（旧接口内部方法）"""
        paragraphs1 = [p.strip() for p in text1.split("\n\n") if len(p.strip()) > 50]
        paragraphs2 = [p.strip() for p in text2.split("\n\n") if len(p.strip()) > 50]

        if not paragraphs1 or not paragraphs2:
            return 0.0

        max_sim = 0.0
        for p1 in paragraphs1[:20]:
            for p2 in paragraphs2[:20]:
                sim = self._ngram_similarity(p1, p2, n=5)
                max_sim = max(max_sim, sim)

        return max_sim

    # ================================================================
    # 角色名称工具方法
    # ================================================================

    @staticmethod
    def _name_similarity(name1: str, name2: str) -> float:
        """
        计算两个角色名称的相似度。

        综合使用 Jaccard 相似度和编辑距离。

        Args:
            name1: 名称1
            name2: 名称2

        Returns:
            float: 相似度 0~1
        """
        # 完全相同
        if name1 == name2:
            return 1.0

        # 包含关系
        if name1 in name2 or name2 in name1:
            shorter = min(len(name1), len(name2))
            longer = max(len(name1), len(name2))
            return shorter / longer

        # 编辑距离
        len1, len2 = len(name1), len(name2)
        dp = list(range(len2 + 1))
        for i in range(1, len1 + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, len2 + 1):
                temp = dp[j]
                if name1[i - 1] == name2[j - 1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j - 1])
                prev = temp

        distance = dp[len2]
        max_len = max(len1, len2)
        if max_len == 0:
            return 1.0

        return 1.0 - (distance / max_len)

    # ================================================================
    # 风险评估方法
    # ================================================================

    def _assess_ngram_risk(self, similarity: float) -> CopyrightRisk:
        """根据 N-gram 相似度评估风险"""
        if similarity >= self.NGRAM_HIGH_RISK:
            return CopyrightRisk.HIGH
        elif similarity >= self.NGRAM_MEDIUM_RISK:
            return CopyrightRisk.MEDIUM
        elif similarity >= self.NGRAM_SAFE:
            return CopyrightRisk.LOW
        else:
            return CopyrightRisk.SAFE

    @staticmethod
    def _assess_sentence_risk(similarity: float) -> CopyrightRisk:
        """根据句子级相似度评估风险"""
        if similarity >= 0.30:
            return CopyrightRisk.HIGH
        elif similarity >= 0.15:
            return CopyrightRisk.MEDIUM
        elif similarity >= 0.05:
            return CopyrightRisk.LOW
        else:
            return CopyrightRisk.SAFE

    @staticmethod
    def _assess_paragraph_risk(max_sim: float, high_risk_count: int) -> CopyrightRisk:
        """根据段落级相似度评估风险"""
        if max_sim >= 0.50 or high_risk_count >= 3:
            return CopyrightRisk.HIGH
        elif max_sim >= 0.30 or high_risk_count >= 1:
            return CopyrightRisk.MEDIUM
        elif max_sim >= 0.15:
            return CopyrightRisk.LOW
        else:
            return CopyrightRisk.SAFE

    @staticmethod
    def _assess_name_risk(
        similarity: float,
        identical: list[str],
        similar_pairs: list[dict],
    ) -> CopyrightRisk:
        """根据角色名称相似度评估风险"""
        if len(identical) >= 3 or similarity >= 0.50:
            return CopyrightRisk.HIGH
        elif len(identical) >= 1 or len(similar_pairs) >= 3 or similarity >= 0.30:
            return CopyrightRisk.MEDIUM
        elif len(similar_pairs) >= 1 or similarity >= 0.15:
            return CopyrightRisk.LOW
        else:
            return CopyrightRisk.SAFE

    @staticmethod
    def _assess_overall_risk(similarity: float) -> CopyrightRisk:
        """根据综合相似度评估整体风险"""
        if similarity >= 0.30:
            return CopyrightRisk.HIGH
        elif similarity >= 0.20:
            return CopyrightRisk.MEDIUM
        elif similarity >= 0.10:
            return CopyrightRisk.LOW
        else:
            return CopyrightRisk.SAFE

    # ================================================================
    # 原创性报告辅助方法
    # ================================================================

    def _compare_world_setting(
        self, generated: NovelInfo, original: NovelInfo
    ) -> dict:
        """比较世界观设定的原创性"""
        result = {"score": 0.8, "reason": "", "details": {}}

        ws_gen = generated.world_setting
        ws_orig = original.world_setting

        if not ws_gen or not ws_orig:
            result["reason"] = "缺少世界观数据，无法比较"
            return result

        # 比较世界名称
        if ws_gen.geography.world_name and ws_orig.geography.world_name:
            name_sim = self._name_similarity(
                ws_gen.geography.world_name, ws_orig.geography.world_name
            )
            result["details"]["world_name_similarity"] = round(name_sim, 4)
            if name_sim > 0.8:
                result["score"] -= 0.3
                result["reason"] = "世界名称过于相似"

        # 比较魔法/修炼体系描述
        if ws_gen.magic_system and ws_orig.magic_system:
            magic_sim = self._ngram_similarity(
                ws_gen.magic_system, ws_orig.magic_system, n=3
            )
            result["details"]["magic_system_similarity"] = round(magic_sim, 4)
            if magic_sim > 0.3:
                result["score"] -= 0.2
                result["reason"] += "；修炼体系描述相似度较高" if result["reason"] else "修炼体系描述相似度较高"

        # 比较规则
        if ws_gen.rules and ws_orig.rules:
            rules_text1 = " ".join(ws_gen.rules)
            rules_text2 = " ".join(ws_orig.rules)
            rules_sim = self._ngram_similarity(rules_text1, rules_text2, n=3)
            result["details"]["rules_similarity"] = round(rules_sim, 4)
            if rules_sim > 0.3:
                result["score"] -= 0.2

        result["score"] = max(min(result["score"], 1.0), 0.0)
        return result

    def _compare_characters(
        self, generated: NovelInfo, original: NovelInfo
    ) -> dict:
        """比较角色设定的原创性"""
        result = {"score": 0.8, "reason": "", "details": {}}

        names_gen = [c.name for c in generated.characters]
        names_orig = [c.name for c in original.characters]

        if not names_gen or not names_orig:
            result["reason"] = "缺少角色数据，无法比较"
            return result

        name_check = self.check_character_name_similarity(names_gen, names_orig)
        result["details"] = name_check

        # 根据名称检测结果调整评分
        if name_check["risk_level"] == CopyrightRisk.HIGH.value:
            result["score"] = 0.3
            result["reason"] = f"角色名称高度相似，相同名称: {name_check['identical_names']}"
        elif name_check["risk_level"] == CopyrightRisk.MEDIUM.value:
            result["score"] = 0.5
            result["reason"] = "部分角色名称与源小说相似"
        elif name_check["risk_level"] == CopyrightRisk.LOW.value:
            result["score"] = 0.7
            result["reason"] = "少量角色名称有一定相似性"

        return result

    def _compare_power_system(
        self, generated: NovelInfo, original: NovelInfo
    ) -> dict:
        """比较力量体系的原创性"""
        result = {"score": 0.8, "reason": "", "details": {}}

        ps_gen = generated.power_system
        ps_orig = original.power_system

        if not ps_gen or not ps_orig:
            result["reason"] = "缺少力量体系数据，无法比较"
            return result

        # 比较体系名称
        if ps_gen.name and ps_orig.name:
            name_sim = self._name_similarity(ps_gen.name, ps_orig.name)
            result["details"]["system_name_similarity"] = round(name_sim, 4)
            if name_sim > 0.8:
                result["score"] -= 0.3
                result["reason"] = "力量体系名称过于相似"

        # 比较等级名称
        levels_gen = [lv.level_name for lv in ps_gen.levels]
        levels_orig = [lv.level_name for lv in ps_orig.levels]
        if levels_gen and levels_orig:
            level_check = self.check_character_name_similarity(levels_gen, levels_orig)
            result["details"]["level_name_check"] = level_check
            if level_check["identical_names"]:
                result["score"] -= 0.2
                result["reason"] += (
                    f"；相同等级名称: {level_check['identical_names']}"
                    if result["reason"]
                    else f"相同等级名称: {level_check['identical_names']}"
                )

        result["score"] = max(min(result["score"], 1.0), 0.0)
        return result

    def _compare_plot(
        self, generated: NovelInfo, original: NovelInfo
    ) -> dict:
        """比较情节的原创性（基于章节内容抽样）"""
        result = {"score": 0.8, "reason": "", "details": {}}

        chapters_gen = generated.chapters
        chapters_orig = original.chapters

        if not chapters_gen or not chapters_orig:
            result["reason"] = "缺少章节数据，无法比较"
            return result

        # 抽样比较（最多取5章）
        sample_count = min(5, len(chapters_gen), len(chapters_orig))
        if sample_count == 0:
            result["reason"] = "章节数不足，无法比较"
            return result

        total_sim = 0.0
        for i in range(sample_count):
            content_gen = chapters_gen[i].content if i < len(chapters_gen) else ""
            content_orig = chapters_orig[i].content if i < len(chapters_orig) else ""
            if content_gen and content_orig:
                sim = self._ngram_similarity(content_gen, content_orig, n=5)
                total_sim += sim

        avg_sim = total_sim / sample_count if sample_count > 0 else 0.0
        result["details"]["avg_chapter_similarity"] = round(avg_sim, 4)
        result["details"]["sample_chapters"] = sample_count

        if avg_sim > 0.30:
            result["score"] = 0.3
            result["reason"] = "章节内容与源小说相似度过高"
        elif avg_sim > 0.20:
            result["score"] = 0.5
            result["reason"] = "部分章节内容与源小说有一定相似性"
        elif avg_sim > 0.10:
            result["score"] = 0.7
            result["reason"] = "少量相似片段，整体原创性尚可"

        return result

    # ================================================================
    # 停用词
    # ================================================================

    @staticmethod
    def _load_stop_words() -> set:
        """加载停用词"""
        return {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这",
        }
