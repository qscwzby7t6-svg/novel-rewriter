"""
文件工具函数

提供文件读写、路径处理等通用工具函数。
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


def ensure_dir(path: str) -> Path:
    """
    确保目录存在，不存在则创建。

    Args:
        path: 目录路径

    Returns:
        Path: 目录Path对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def read_text_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取文本文件。

    Args:
        file_path: 文件路径
        encoding: 文件编码

    Returns:
        str: 文件内容

    Raises:
        FileNotFoundError: 文件不存在
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    return path.read_text(encoding=encoding)


def write_text_file(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
) -> Path:
    """
    写入文本文件。

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码

    Returns:
        Path: 文件Path对象
    """
    path = Path(file_path)
    ensure_dir(str(path.parent))
    path.write_text(content, encoding=encoding)
    return path


def read_json_file(file_path: str, encoding: str = "utf-8") -> dict:
    """
    读取JSON文件。

    Args:
        file_path: 文件路径
        encoding: 文件编码

    Returns:
        dict: JSON数据
    """
    content = read_text_file(file_path, encoding)
    return json.loads(content)


def write_json_file(
    file_path: str,
    data: Any,
    encoding: str = "utf-8",
    indent: int = 2,
) -> Path:
    """
    写入JSON文件。

    Args:
        file_path: 文件路径
        data: 要写入的数据
        encoding: 文件编码
        indent: 缩进空格数

    Returns:
        Path: 文件Path对象
    """
    content = json.dumps(data, ensure_ascii=False, indent=indent)
    return write_text_file(file_path, content, encoding)


def find_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False,
) -> list[Path]:
    """
    查找文件。

    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归查找

    Returns:
        list[Path]: 匹配的文件列表
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    if recursive:
        return list(dir_path.rglob(pattern))
    return list(dir_path.glob(pattern))


def get_file_size(file_path: str) -> int:
    """
    获取文件大小（字节）。

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小
    """
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小。

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化后的大小字符串
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def generate_output_path(
    output_dir: str,
    novel_name: str,
    chapter_number: Optional[int] = None,
    extension: str = "txt",
) -> Path:
    """
    生成输出文件路径。

    Args:
        output_dir: 输出目录
        novel_name: 小说名称
        chapter_number: 章节号（可选）
        extension: 文件扩展名

    Returns:
        Path: 输出文件路径
    """
    ensure_dir(output_dir)

    # 清理文件名中的非法字符
    safe_name = "".join(
        c for c in novel_name if c not in r'\/:*?"<>|'
    )

    if chapter_number is not None:
        filename = f"{safe_name}_第{chapter_number:04d}章.{extension}"
    else:
        filename = f"{safe_name}.{extension}"

    return Path(output_dir) / filename


def list_novel_files(directory: str) -> list[Path]:
    """
    列出目录中的小说文件。

    Args:
        directory: 目录路径

    Returns:
        list[Path]: 小说文件列表
    """
    extensions = {".txt", ".json"}
    files = find_files(directory, pattern="*", recursive=True)
    return [f for f in files if f.suffix.lower() in extensions]
