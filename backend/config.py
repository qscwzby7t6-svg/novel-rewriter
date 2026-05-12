"""
配置加载模块

负责从 config.yaml 加载配置，提供全局配置访问。
支持环境变量覆盖配置项。
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


# ============================================================
# 配置数据模型
# ============================================================

class LLMCostConfig(BaseModel):
    """LLM成本控制配置"""
    chapter_budget: float = Field(default=0.5, description="每章预算上限（元）")
    total_budget: float = Field(default=100.0, description="总预算上限（元）")
    primary_price_per_1k: float = Field(default=0.002, description="主模型每千token价格（元）")
    fallback_price_per_1k: float = Field(default=0.001, description="备用模型每千token价格（元）")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="deepseek", description="LLM提供商")
    api_key: str = Field(default="", description="API密钥")
    base_url: str = Field(default="https://api.deepseek.com/v1", description="API基础URL")
    model: str = Field(default="deepseek-chat", description="模型名称")
    fallback_provider: str = Field(default="deepseek", description="备用提供商")
    fallback_model: str = Field(default="deepseek-chat", description="备用模型")
    fallback_api_key: str = Field(default="", description="备用API密钥")
    fallback_base_url: str = Field(default="https://api.deepseek.com/v1", description="备用API基础URL")
    max_tokens_per_call: int = Field(default=4000, description="单次调用最大token数")
    temperature: float = Field(default=0.8, description="生成温度")
    top_p: float = Field(default=0.9, description="Top-P采样")
    max_retries: int = Field(default=3, description="重试次数")
    retry_delay: float = Field(default=2.0, description="重试间隔（秒）")
    timeout: int = Field(default=60, description="请求超时（秒）")
    stream: bool = Field(default=False, description="是否启用流式输出")
    cost: LLMCostConfig = Field(default_factory=LLMCostConfig, description="成本控制配置")


class NovelConfig(BaseModel):
    """小说配置"""
    default_genre: str = Field(default="玄幻", description="默认类型")
    default_chapter_words: int = Field(default=3000, description="默认每章目标字数")
    default_total_chapters: int = Field(default=300, description="默认总章数")
    genres: list[str] = Field(
        default_factory=lambda: ["玄幻", "仙侠", "都市", "科幻", "历史", "游戏", "悬疑", "言情"],
        description="支持的类型列表"
    )


class WorldBuildingConfig(BaseModel):
    """世界观构建配置"""
    detail_level: str = Field(default="moderate", description="世界观详细程度")
    auto_generate_map: bool = Field(default=True, description="是否自动生成地图描述")
    auto_generate_power_system: bool = Field(default=True, description="是否自动生成力量体系")


class WritingConfig(BaseModel):
    """写作配置"""
    paragraph_level: bool = Field(default=True, description="段落级生成开关")
    deai_enabled: bool = Field(default=True, description="去AI化处理开关")
    copyright_check: bool = Field(default=True, description="版权检测开关")
    quality_check: bool = Field(default=True, description="质量检查开关")
    quality_threshold: float = Field(default=0.7, description="质量检查阈值")
    context_window: int = Field(default=5, description="上下文窗口大小（章节数）")


class OutputConfig(BaseModel):
    """输出配置"""
    path: str = Field(default="./data/output", description="输出路径")
    format: str = Field(default="txt", description="输出格式")
    split_by_chapter: bool = Field(default=True, description="是否按章节分文件")


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="127.0.0.1", description="监听地址")
    port: int = Field(default=8000, description="监听端口")
    debug: bool = Field(default=False, description="是否开启调试模式")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    file: str = Field(default="./data/output/novel-rewriter.log", description="日志文件路径")


class AppConfig(BaseModel):
    """应用总配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    novel: NovelConfig = Field(default_factory=NovelConfig, description="小说配置")
    world_building: WorldBuildingConfig = Field(default_factory=WorldBuildingConfig, description="世界观构建配置")
    writing: WritingConfig = Field(default_factory=WritingConfig, description="写作配置")
    output: OutputConfig = Field(default_factory=OutputConfig, description="输出配置")
    server: ServerConfig = Field(default_factory=ServerConfig, description="服务器配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")


# ============================================================
# 配置加载器
# ============================================================

class ConfigLoader:
    """配置加载器，支持YAML文件和环境变量覆盖"""

    _instance: Optional["ConfigLoader"] = None
    _config: Optional[AppConfig] = None

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[str] = None) -> AppConfig:
        """
        加载配置文件。

        Args:
            config_path: 配置文件路径，默认为 config/config.yaml

        Returns:
            AppConfig: 应用配置对象
        """
        if config_path is None:
            # 从项目根目录查找配置文件
            project_root = Path(__file__).parent.parent
            config_path = str(project_root / "config" / "config.yaml")

        raw_config = self._load_yaml(config_path)
        self._apply_env_overrides(raw_config)
        self._config = AppConfig(**raw_config)
        return self._config

    @staticmethod
    def _load_yaml(path: str) -> dict[str, Any]:
        """加载YAML文件"""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}

    @staticmethod
    def _apply_env_overrides(config: dict[str, Any]) -> None:
        """
        应用环境变量覆盖。

        环境变量命名规则: NOVEL_REWRITER_<section>_<key>
        例如: NOVEL_REWRITER_LLM_API_KEY=sk-xxx
        """
        env_mapping = {
            "NOVEL_REWRITER_LLM_PROVIDER": ("llm", "provider"),
            "NOVEL_REWRITER_LLM_API_KEY": ("llm", "api_key"),
            "NOVEL_REWRITER_LLM_BASE_URL": ("llm", "base_url"),
            "NOVEL_REWRITER_LLM_MODEL": ("llm", "model"),
            "NOVEL_REWRITER_LLM_TEMPERATURE": ("llm", "temperature"),
            "NOVEL_REWRITER_LLM_MAX_TOKENS": ("llm", "max_tokens_per_call"),
            "NOVEL_REWRITER_SERVER_HOST": ("server", "host"),
            "NOVEL_REWRITER_SERVER_PORT": ("server", "port"),
            "NOVEL_REWRITER_LOG_LEVEL": ("logging", "level"),
        }

        for env_key, (section, key) in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                if section not in config:
                    config[section] = {}
                # 尝试转换为数值类型
                if key in ("temperature", "port", "max_tokens_per_call"):
                    try:
                        value = int(value) if key in ("port", "max_tokens_per_call") else float(value)
                    except ValueError:
                        pass
                elif key in ("stream", "debug"):
                    value = value.lower() in ("true", "1", "yes")
                config[section][key] = value

    @property
    def config(self) -> AppConfig:
        """获取当前配置"""
        if self._config is None:
            raise RuntimeError("配置尚未加载，请先调用 load() 方法")
        return self._config

    def reload(self, config_path: Optional[str] = None) -> AppConfig:
        """重新加载配置"""
        self._config = None
        return self.load(config_path)


# ============================================================
# 全局配置访问
# ============================================================

_loader = ConfigLoader()


def get_config() -> AppConfig:
    """获取全局配置（自动加载）"""
    if _loader._config is None:
        _loader.load()
    return _loader.config


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """加载配置文件"""
    return _loader.load(config_path)


def reload_config(config_path: Optional[str] = None) -> AppConfig:
    """重新加载配置文件"""
    return _loader.reload(config_path)


# 兼容别名
Settings = AppConfig
