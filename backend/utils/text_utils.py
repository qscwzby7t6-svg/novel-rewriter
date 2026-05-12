"""
文本工具函数

提供文本处理相关的通用工具函数。
"""

import re
from typing import Optional


def count_chinese_chars(text: str) -> int:
    """
    统计中文字符数。

    Args:
        text: 输入文本

    Returns:
        int: 中文字符数
    """
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def count_words(text: str) -> int:
    """
    统计总字数（中文+英文单词）。

    Args:
        text: 输入文本

    Returns:
        int: 总字数
    """
    chinese_chars = count_chinese_chars(text)
    # 英文单词数
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    return chinese_chars + english_words


def split_into_paragraphs(text: str) -> list[str]:
    """
    将文本按段落分割。

    Args:
        text: 输入文本

    Returns:
        list[str]: 段落列表
    """
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def split_into_sentences(text: str) -> list[str]:
    """
    将文本按句子分割。

    Args:
        text: 输入文本

    Returns:
        list[str]: 句子列表
    """
    sentences = re.split(r"[。！？；…]+", text)
    return [s.strip() for s in sentences if s.strip()]


def extract_dialogues(text: str) -> list[str]:
    """
    提取文本中的对话内容。

    Args:
        text: 输入文本

    Returns:
        list[str]: 对话列表
    """
    patterns = [
        r"[\"""](.*?)[\"""]",   # 双引号
        r"[「『](.*?)[」』]",     # 日式引号
        r"'(.*?)'",               # 单引号
    ]
    dialogues = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        dialogues.extend(matches)
    return dialogues


def clean_text(text: str) -> str:
    """
    清理文本中的多余空白和特殊字符。

    Args:
        text: 输入文本

    Returns:
        str: 清理后的文本
    """
    # 替换全角空格
    text = text.replace("\u3000", " ")
    # 去除行首行尾空白
    lines = [line.strip() for line in text.split("\n")]
    # 合并连续空行
    result: list[str] = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return "\n".join(result)


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    截断文本到指定长度。

    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_reading_time(text: str, chars_per_minute: int = 500) -> int:
    """
    估算阅读时间（分钟）。

    Args:
        text: 输入文本
        chars_per_minute: 每分钟阅读字数

    Returns:
        int: 预估阅读时间（分钟）
    """
    word_count = count_words(text)
    return max(1, word_count // chars_per_minute)


def normalize_chapter_title(title: str) -> str:
    """
    标准化章节标题格式。

    Args:
        title: 原始标题

    Returns:
        str: 标准化后的标题
    """
    title = title.strip()
    # 确保以"第"开头
    if not title.startswith("第"):
        title = "第" + title
    return title


def is_chapter_title(line: str) -> bool:
    """
    判断一行是否是章节标题。

    Args:
        line: 文本行

    Returns:
        bool: 是否是章节标题
    """
    pattern = r"^第[一二三四五六七八九十百千万零\d]+章\s*.+$"
    return bool(re.match(pattern, line.strip()))
