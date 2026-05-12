"""
枚举类型定义

定义系统中使用的所有枚举类型。
"""

from enum import Enum


class Genre(str, Enum):
    """小说类型"""
    FANTASY = "玄幻"
    XIANXIA = "仙侠"
    URBAN = "都市"
    SCIFI = "科幻"
    HISTORICAL = "历史"
    GAME = "游戏"
    MYSTERY = "悬疑"
    ROMANCE = "言情"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 等待开始
    PARSING = "parsing"           # 解析源小说
    BUILDING_WORLD = "building_world"  # 构建世界观
    GENERATING = "generating"     # 生成章节
    CHECKING_QUALITY = "checking_quality"  # 质量检查
    OPTIMIZING = "optimizing"     # 优化中
    PAUSED = "paused"             # 已暂停
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


class ChapterStatus(str, Enum):
    """章节状态"""
    PENDING = "pending"           # 待生成
    GENERATING = "generating"     # 生成中
    DRAFT = "draft"               # 草稿
    REVIEWING = "reviewing"       # 审核中
    REVISION = "revision"         # 修改中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败


class LLMProvider(str, Enum):
    """LLM提供商"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    LOCAL = "local"


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"       # 优秀
    GOOD = "good"                 # 良好
    ACCEPTABLE = "acceptable"     # 可接受
    POOR = "poor"                 # 较差
    UNACCEPTABLE = "unacceptable" # 不可接受


class DetailLevel(str, Enum):
    """详细程度"""
    SIMPLE = "simple"             # 简单
    MODERATE = "moderate"         # 适中
    DETAILED = "detailed"         # 详细


class OutputFormat(str, Enum):
    """输出格式"""
    TXT = "txt"
    JSON = "json"
    DOCX = "docx"


class ForeshadowStatus(str, Enum):
    """伏笔状态"""
    PLANTED = "planted"           # 已设置
    HINTED = "hinted"             # 已暗示
    RESOLVED = "resolved"         # 已回收
    ABANDONED = "abandoned"       # 已放弃


class CopyrightRisk(str, Enum):
    """版权风险等级"""
    SAFE = "safe"                 # 安全
    LOW = "low"                   # 低风险
    MEDIUM = "medium"             # 中风险
    HIGH = "high"                 # 高风险
