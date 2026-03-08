"""
MaliciousBotConfig - 恶意水军攻击模式配置

所有攻击模式相关参数集中在此文件管理，不写入 experiment_config.json。
MaliciousBotManager 直接实例化 DEFAULT_CONFIG 使用。

快速上手 — 只需修改 AttackModeConfig.mode 字段：

    DEFAULT_CONFIG.attack_mode.mode = "swarm"      # 蜂群式（默认）
    DEFAULT_CONFIG.attack_mode.mode = "dispersed"  # 游离式
    DEFAULT_CONFIG.attack_mode.mode = "chain"      # 链式传播
"""

from dataclasses import dataclass, field
from typing import Dict


# ─── 攻击模式配置（用户主要修改入口） ─────────────────────────────────────────

@dataclass
class AttackModeConfig:
    """
    ================================================================
    攻击协同模式配置 — 在这里选择水军的组织方式
    ================================================================

    修改 mode 字段即可切换策略，无需导入任何枚举：

        mode = "swarm"      蜂群式（默认）
                            全部 bot 集中攻击同一目标帖子。
                            执行互点赞（cross-like）操控推荐算法热度。
                            角色分布由 MaliciousBotConfig.role_distribution 控制。

        mode = "dispersed"  游离式
                            bot 随机分散到多条帖子，模拟低组织度自发舆论攻击。
                            每条帖子最多 3~5 个 bot，不执行 cross-like。
                            角色以 Agitator 60% + Spammer 40% 为主。

        mode = "chain"      链式传播（Step 4 待实现）
                            三层水军结构，参考 MultiAgent4Collusion：
                              Layer 1 LeaderBot     : 伪造大V身份，首先发帖
                              Layer 2 AmplifierBot  : 转发 LeaderBot 帖子并评论
                              Layer 3 CommentFlood  : 在 LeaderBot 帖子下批量刷评论
                            层级比例由 ChainConfig 控制。
    """

    # 攻击协同模式，可选 "swarm" / "dispersed" / "chain"
    mode: str = "swarm"

    def get_coordination_mode(self):
        """将字符串 mode 转换为 CoordinationMode 枚举（供内部路由层使用）。"""
        from .coordination_strategies import CoordinationMode
        try:
            return CoordinationMode(self.mode)
        except ValueError:
            raise ValueError(
                f"Invalid attack mode: '{self.mode}'. "
                f"Valid options: 'swarm', 'dispersed', 'chain'"
            )


# ─── 链式传播配置 ──────────────────────────────────────────────────────────────

@dataclass
class ChainConfig:
    """
    链式传播（ChainStrategy）专属配置。

    仅在 coordination_mode = CoordinationMode.CHAIN 时生效。
    三层水军比例（leader_ratio 从 cluster_size 计算）：
        LeaderBot  : 由 leader_bot_count 直接指定数量
        AmplifierBot : amplifier_ratio × (cluster_size - leader_bot_count)
        CommentFloodBot : comment_flood_ratio × (cluster_size - leader_bot_count)
    """

    # LeaderBot（大V水军）数量，通常 1~2 个
    leader_bot_count: int = 1

    # 伪造大V粉丝数范围（写入 users 表的 followers_count 字段）
    leader_followers_count_min: int = 10
    leader_followers_count_max: int = 50

    # 中层扩散水军（AmplifierBot）在剩余 bot 中的占比
    # 注：amplifier_ratio + comment_flood_ratio 应等于 1.0
    amplifier_ratio: float = 0.40

    # 底层控评水军（CommentFloodBot）在剩余 bot 中的占比
    comment_flood_ratio: float = 0.50


# ─── 自适应控制器配置 ──────────────────────────────────────────────────────────

@dataclass
class AdaptiveConfig:
    """
    自适应控制器（AdaptiveController）配置。

    控制器根据审核压力系数动态调整攻击策略：
        LOW    (0 ~ low_pressure_threshold)  : 保持当前策略不变
        MEDIUM (low ~ high_pressure_threshold): 提升 ConcernTroll 比例，降低 Agitator 比例
        HIGH   (> high_pressure_threshold)   : 策略切换 + 敏感词规避 + 降低攻击频率

    审核压力系数计算公式：
        pressure = (removed_count × 2 + warned_count × 1) / total_malicious_comments
    """

    # 是否启用自适应控制器（False 时控制器不执行任何调整）
    enabled: bool = True

    # LOW / MEDIUM 分界线（压力系数低于此值视为 LOW）
    low_pressure_threshold: float = 0.10

    # MEDIUM / HIGH 分界线（压力系数超过此值视为 HIGH）
    high_pressure_threshold: float = 0.50

    # 是否启用 LLM 反思（HIGH 压力时调用 LLM 生成战术建议，False 则跳过以节省成本）
    reflection_enabled: bool = True

    # LLM 反思触发间隔（每 N 个时间步最多触发一次，避免频繁调用）
    reflection_interval_steps: int = 5


# ─── 主配置类 ──────────────────────────────────────────────────────────────────

@dataclass
class MaliciousBotConfig:
    """
    恶意水军攻击模式总配置。

    ┌─────────────────────────────────────────────────────────────┐
    │  用户配置入口（常用修改点）                                   │
    │                                                             │
    │  attack_mode.mode     : 攻击协同模式（见 AttackModeConfig）  │
    │  role_distribution    : 三种战术角色的比例（见下方说明）       │
    └─────────────────────────────────────────────────────────────┘

    role_distribution 控制 Agitator / ConcernTroll / Spammer 三种战术角色的分配比例：
        - 三者之和必须为 1.0
        - 仅在 swarm 和 dispersed 模式下直接使用
        - chain 模式按固定分层比例分配（见 ChainConfig）

    角色说明：
        agitator      (激进煽动者) : 情绪极端，CAPS + 感叹号，容易被审核识别
        concern_troll (理中客)     : 伪装温和，暗中植入质疑，最难被审核识别
        spammer       (复读机)     : 短评论高频刷量，关键词密集，量大但内容雷同
    """

    # ── 攻击协同模式（主要配置入口，详见 AttackModeConfig） ──────────────────
    attack_mode: AttackModeConfig = field(default_factory=AttackModeConfig)

    # ── 角色分布比例（agitator + concern_troll + spammer = 1.0） ─────────────
    role_distribution: Dict[str, float] = field(default_factory=lambda: {
        "agitator": 0.40,       # 40% 激进煽动者：制造情绪爆点
        "concern_troll": 0.35,  # 35% 理中客伪装者：植入质疑，规避审核
        "spammer": 0.25,        # 25% 复读机：刷热度，污染评论区
    })

    # ── 链式传播专属配置（仅 chain 模式使用） ─────────────────────────────────
    chain_config: ChainConfig = field(default_factory=ChainConfig)

    # ── 自适应控制器配置 ────────────────────────────────────────────────────
    adaptive: AdaptiveConfig = field(default_factory=AdaptiveConfig)

    @property
    def coordination_mode(self):
        """供内部路由层（AttackOrchestrator）读取，将字符串 mode 转换为枚举。"""
        return self.attack_mode.get_coordination_mode()


# ─── 全局默认实例 ──────────────────────────────────────────────────────────────

# 默认蜂群式配置，与现有行为一致。
# 切换模式只需：DEFAULT_CONFIG.attack_mode.mode = "dispersed"
DEFAULT_CONFIG = MaliciousBotConfig()
