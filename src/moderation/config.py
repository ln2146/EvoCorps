"""
审核系统配置定义

遵循 AGENT_ENVIRONMENT_SPEC.md: Config 层定义所有可配置参数
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .types import ModerationAction, ModerationSeverity


@dataclass
class ModerationProviderConfig:
    """
    审核提供者配置

    每个审核提供者（LLM、关键词等）的配置
    """
    # 开关
    enabled: bool = False
    weight: float = 1.0  # 多提供者时的权重

    # 触发阈值
    threshold: float = 0.7  # 触发审核的最小置信度

    # LLM API 配置
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    model: str = "gemini-2.0-flash"

    # 关键词配置
    keywords: Dict[str, List[str]] = field(default_factory=dict)
    # 格式: {"category_name": ["keyword1", "keyword2", ...]}


@dataclass
class ModerationActionConfig:
    """
    干预动作配置

    定义不同严重程度对应的干预方式和参数
    """
    # 封号豁免用户列表 - 这些用户只处理帖子（删帖/降权/警告），不封禁账号
    # 典型用途：新闻发布账号需要持续运作，即使某条新闻违规也不应封禁账号
    ban_exempt_users: List[str] = field(
        default_factory=lambda: [
            "agentverse_news",  # 系统新闻发布账号
        ]
    )

    # 可见性降级系数 - 严重程度 -> 推荐权重系数
    visibility_degradation_factors: Dict[ModerationSeverity, float] = field(
        default_factory=lambda: {
            ModerationSeverity.LOW: 0.8,       # 轻微: 降低 20%
            ModerationSeverity.MEDIUM: 0.5,     # 中等: 降低 50%
            ModerationSeverity.HIGH: 0.2,       # 严重: 降低 80%
            ModerationSeverity.CRITICAL: 0.0,    # 极其严重: 完全隐藏
        }
    )

    # 警告标签文字 - 分类 -> 标签文字
    warning_labels: Dict[str, str] = field(
        default_factory=lambda: {
            "hate_speech": "⚠️ 此内容包含敏感信息",
            "violence": "⚠️ 此内容涉及暴力内容",
            "spam": "⚠️ 此内容被标记为广告或垃圾信息",
            "controversial": "ℹ️ 此内容存在争议，建议多方核实",
            "other": "⚠️ 此内容需谨慎参考",
        }
    )

    # 硬性打击阈值 - 严重程度 -> 触发删帖的最小置信度
    takedown_thresholds: Dict[ModerationSeverity, float] = field(
        default_factory=lambda: {
            ModerationSeverity.HIGH: 0.8,      # 严重且置信度 > 0.8 删帖
            ModerationSeverity.CRITICAL: 0.6,   # 极其严重且置信度 > 0.6 删帖
        }
    )

    # 封号阈值
    ban_thresholds: Dict[ModerationSeverity, float] = field(
        default_factory=lambda: {
            ModerationSeverity.CRITICAL: 0.8,   # 极其严重且置信度 > 0.8 封号
        }
    )

    # 严重程度到默认动作的映射
    severity_to_action: Dict[ModerationSeverity, ModerationAction] = field(
        default_factory=lambda: {
            ModerationSeverity.LOW: ModerationAction.WARNING_LABEL,
            ModerationSeverity.MEDIUM: ModerationAction.VISIBILITY_DEGRADATION,
            ModerationSeverity.HIGH: ModerationAction.VISIBILITY_DEGRADATION,
            ModerationSeverity.CRITICAL: ModerationAction.HARD_TAKEDOWN,
        }
    )


@dataclass
class ModerationConfig:
    """
    审核系统总配置

    整合所有子配置，作为单一配置入口
    """
    # 全局开关
    enabled: bool = False

    # 审核提供者配置
    keyword_provider: ModerationProviderConfig = field(
        default_factory=lambda: ModerationProviderConfig(
            enabled=True,   # 启用关键词审核（发布前）
            threshold=0.5,  # 关键词置信度阈值
            keywords={
                "hate_speech": [
                    # 中文
                    "仇恨", "歧视", "种族主义", "纳粹",
                    "人渣", "贱人", "畜生", "该死", "去死",
                    "低等", "劣等", "下等人", "垃圾人",
                    # 英文
                    "should die", "kill yourself", "hate speech", "kys",
                    "racist", "nazi", "subhuman",
                    "scum", "trash", "vermin", "filth",
                    "inferior race", "white supremacy", "ethnic cleansing",
                    "go back to", "you people", "your kind",
                ],
                "violence": [
                    # 中文
                    "暴力", "杀人", "砍人", "袭击", "爆炸",
                    "屠杀", "血洗", "灭门", "枪击", "刺杀",
                    "炸弹", "恐袭", "武器", "刀砍", "枪杀",
                    "恐怖分子",
                    # 英文
                    "violence", "murder", "attack", "bomb", "massacre",
                    "kill", "shoot", "stab", "assassinate",
                    "blow up", "gun down", "mass shooting",
                    "terrorist attack", "terrorist", "suicide bomber", "school shooter",
                    "lynch", "execute", "slaughter", "butcher",
                ],
                "sexual": [
                    # 中文
                    "色情", "淫秽", "裸聊", "约炮", "性交易",
                    "卖淫", "嫖娼", "援交", "包养",
                    # 英文
                    "porn", "nude", "sex video", "prostitution",
                    "escort", "hookup", "nsfw", "xxx",
                    "onlyfans leak", "sex tape", "nudes leaked",
                    "sexual content", "adult content", "explicit",
                    "cam girl", "sugar daddy", "sex work",
                ],
                "spam": [
                    # 中文
                    "加微信", "扫码", "代购", "兼职", "赚钱",
                    "刷单", "贷款", "办证", "发票", "推广",
                    "加群", "私聊", "咨询", "点击链接",
                    # 英文
                    "buy now", "click here", "free money", "limited offer",
                    "earn cash", "work from home", "make money fast",
                    "dm me", "check bio", "link in bio", "click link",
                    "crypto scam", "investment opportunity", "get rich quick",
                    "follow for follow", "like for like", "sub for sub",
                    "drop shipping", "mlm", "pyramid scheme",
                ],
            }
        )
    )
    llm_provider: ModerationProviderConfig = field(
        default_factory=lambda: ModerationProviderConfig(
            enabled=False,   # 由 simulation.py 在运行时注入 api_key/endpoint/model 后启用
            threshold=0.6,
            model="gemini-2.0-flash",
        )
    )

    # 干预动作配置
    actions: ModerationActionConfig = field(
        default_factory=ModerationActionConfig
    )

    # 审核触发条件
    keyword_check_threshold: int = 0  # 关键词审核：发布时检查（互动数 = 0）
    llm_check_threshold: int = 10     # LLM 审核：互动数 ≥ 10 时检查

    # 异步批处理配置
    batch_size: int = 10
    batch_interval_seconds: int = 60

    # 统计保留
    keep_stats: bool = True
    max_stats_entries: int = 10000

    @classmethod
    def from_dict(cls, config_dict: Optional[Dict[str, Any]] = None) -> "ModerationConfig":
        """
        从字典创建配置

        支持部分配置覆盖，未指定的使用默认值
        """
        if not config_dict:
            return cls()

        def parse_dataclass(dc_cls, data: Optional[Dict] = None):
            if not data:
                return dc_cls()
            # 只取 dataclass 定义的字段
            valid_fields = {f.name for f in dc_cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return dc_cls(**filtered)

        # 解析 severity 字符串到枚举
        action_config_data = config_dict.get('actions', {})
        if 'severity_to_action' in action_config_data:
            severity_map = {}
            for severity_str, action_str in action_config_data['severity_to_action'].items():
                severity = ModerationSeverity(severity_str)
                action = ModerationAction(action_str)
                severity_map[severity] = action
            action_config_data['severity_to_action'] = severity_map

        return cls(
            enabled=config_dict.get('enabled', False),
            keyword_provider=parse_dataclass(
                ModerationProviderConfig,
                config_dict.get('keyword_provider')
            ),
            llm_provider=parse_dataclass(
                ModerationProviderConfig,
                config_dict.get('llm_provider')
            ),
            actions=parse_dataclass(
                ModerationActionConfig,
                action_config_data
            ) if action_config_data else ModerationActionConfig(),
            keyword_check_threshold=config_dict.get('keyword_check_threshold', 0),
            llm_check_threshold=config_dict.get('llm_check_threshold', 10),
            batch_size=config_dict.get('batch_size', 10),
            batch_interval_seconds=config_dict.get('batch_interval_seconds', 60),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化和 API 响应"""
        from dataclasses import asdict
        return {
            'enabled': self.enabled,
            'keyword_provider': asdict(self.keyword_provider),
            'llm_provider': asdict(self.llm_provider),
            'actions': asdict(self.actions),
            'keyword_check_threshold': self.keyword_check_threshold,
            'llm_check_threshold': self.llm_check_threshold,
            'batch_size': self.batch_size,
            'batch_interval_seconds': self.batch_interval_seconds,
        }


# 默认配置实例
DEFAULT_CONFIG = ModerationConfig()


def load_config_from_env() -> ModerationConfig:
    """
    从环境变量加载配置

    支持通过环境变量覆盖配置
    """
    config = ModerationConfig()

    # 启用状态
    if 'MODERATION_ENABLED' in os.environ:
        config.enabled = os.environ['MODERATION_ENABLED'].lower() in ('true', '1', 'yes')

    return config
