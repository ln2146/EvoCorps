"""
审核系统类型定义

遵循 AGENT_ENVIRONMENT_SPEC.md: 所有边界数据必须有类型验证
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field, validator


class ModerationAction(str, Enum):
    """审核动作类型 - 三种干预手段"""
    NONE = "none"                       # 无干预
    VISIBILITY_DEGRADATION = "visibility_degradation"  # 可见性降级
    WARNING_LABEL = "warning_label"       # 警告标签
    HARD_TAKEDOWN = "hard_takedown"     # 硬性打击（删帖/封号）


class ModerationSeverity(str, Enum):
    """审核严重程度 - 用于确定干预力度"""
    LOW = "low"          # 轻微 - 降权处理
    MEDIUM = "medium"    # 中等 - 警告标签
    HIGH = "high"        # 严重 - 警告标签
    CRITICAL = "critical" # 极其严重 - 删帖/封号


class ModerationCategory(str, Enum):
    """审核分类"""
    HATE_SPEECH = "hate_speech"       # 仇恨言论
    SPAM = "spam"                     # 垃圾信息
    VIOLENCE = "violence"             # 暴力内容
    SEXUAL = "sexual"                 # 色情内容
    CONTROVERSIAL = "controversial"     # 有争议内容
    OTHER = "other"                    # 其他


class ModerationVerdict(BaseModel):
    """
    审核裁决 - 核心数据结构

    由审核提供者生成，经过服务层决策后，传递给动作执行器
    """
    # 基础标识
    post_id: str = Field(..., description="帖子ID")
    user_id: str = Field(..., description="用户ID")
    content: str = Field(..., description="原始内容")

    # 审核结果 - 由提供者生成
    category: ModerationCategory = Field(..., description="违规分类")
    severity: ModerationSeverity = Field(..., description="严重程度")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0.0-1.0")
    reason: str = Field(..., description="审核原因")
    detected_keywords: List[str] = Field(default_factory=list, description="检测到的关键词")

    # 元数据
    provider: str = Field(..., description="审核提供者标识")
    checked_at: datetime = Field(default_factory=datetime.now, description="审核时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    # 决策结果 - 由服务层填充
    action: Optional[ModerationAction] = None
    appealable: bool = True
    degradation_factor: Optional[float] = None
    label_text: Optional[str] = None

    # 记录相关
    record_id: Optional[int] = None

    class Config:
        use_enum_values = True

    @validator('confidence')
    def validate_confidence(cls, v):
        """确保置信度在有效范围内"""
        return max(0.0, min(1.0, v))


class ModerationStats(BaseModel):
    """审核统计 - 用于监控和评估"""
    total_checked: int = 0
    total_flagged: int = 0
    action_counts: Dict[ModerationAction, int] = Field(default_factory=dict)
    severity_counts: Dict[ModerationSeverity, int] = Field(default_factory=dict)
    category_counts: Dict[ModerationCategory, int] = Field(default_factory=dict)

    @property
    def flag_rate(self) -> float:
        """违规率"""
        if self.total_checked == 0:
            return 0.0
        return self.total_flagged / self.total_checked


class ModerationFilterConfig(BaseModel):
    """
    审核过滤配置 - 传递给推荐系统

    推荐系统使用此配置决定如何处理已审核内容
    """
    enabled: bool = False
    apply_degradation: bool = True
    filter_taken_down: bool = True
    show_warning_labels: bool = True

    # 严重程度到可见性系数的映射
    visibility_factors: Dict[ModerationSeverity, float] = Field(default_factory=lambda: {
        ModerationSeverity.LOW: 0.8,
        ModerationSeverity.MEDIUM: 0.5,
        ModerationSeverity.HIGH: 0.2,
        ModerationSeverity.CRITICAL: 0.0,
    })
