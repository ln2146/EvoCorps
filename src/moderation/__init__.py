"""
EvoCorps Moderation System

审核/监管系统 - 维持生态底线的强制干预机制

功能:
- 可见性降级: 不删帖，但在推荐算法中降低权重
- 警告标签: 给违规内容打上官方标签
- 硬性打击: 封号、删帖（制造"生态位真空"）

架构遵循 AGENT_ENVIRONMENT_SPEC.md:
Types → Config → Repo → Service → Runtime
"""

from .types import (
    ModerationAction,
    ModerationSeverity,
    ModerationVerdict,
)
from .config import (
    ModerationConfig,
    ModerationProviderConfig,
    ModerationActionConfig,
    load_config_from_env,
)
from .service import ModerationService

__all__ = [
    "ModerationAction",
    "ModerationSeverity",
    "ModerationVerdict",
    "ModerationConfig",
    "ModerationProviderConfig",
    "ModerationActionConfig",
    "ModerationService",
    "load_config_from_env",
]
