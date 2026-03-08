"""
Bot Role Overlay - 水军战术角色叠加层

在不修改 personas/negative_personas_database.json 的前提下，
通过纯内存函数动态为 bot 分配战术角色，赋予不同的提示词策略和行为倾向。

三种战术角色：
- Agitator（激进煽动者）  : 情绪极端，制造舆论震荡；伪装度低，容易被审核识别
- ConcernTroll（理中客） : 伪装温和，暗中带偏叙事框架；伪装度高，最难被审核识别
- Spammer（复读机）      : 高频重复，刷热度污染评论区；量大，对算法召回阶段有效

使用方式：
    from malicious_bots.bot_role_overlay import assign_bot_roles, BotRole

    paired = assign_bot_roles(personas, {"agitator": 0.4, "concern_troll": 0.35, "spammer": 0.25})
    for persona, role_overlay in paired:
        content = cluster._sync_llm_call_with_model_info(persona, target, role_overlay)
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .simple_malicious_agent import MaliciousPersona


# ─── 角色枚举 ──────────────────────────────────────────────────────────────────

class BotRole(Enum):
    AGITATOR     = "agitator"      # 激进煽动者
    CONCERN_TROLL = "concern_troll" # 理中客伪装者
    SPAMMER      = "spammer"       # 复读机


# ─── 数据类 ────────────────────────────────────────────────────────────────────

@dataclass
class RoleOverlay:
    """
    叠加在原有 MaliciousPersona 上的战术角色层。

    不修改原 persona 对象，而是作为独立参数传递给提示词构建函数。
    在 _build_malicious_comment_prompt() 中，role_overlay.prompt_override
    会替换默认的 CONTENT GUIDELINES / MISSION 段落。

    Fields:
        role              : BotRole 枚举值，标识角色类型
        prompt_override   : 替换原提示词 MISSION/TACTICS 段落的完整文本
        word_limit        : 生成内容的词数上限（用于提示词约束）
        intensity_modifier: 强度系数 (0.5~2.0)，影响 fallback 模板选取
        disguise_level    : "low" / "medium" / "high"，供审核分析模块使用
        fallback_responses: 角色专属的 fallback 回复列表（LLM 失败时使用）
    """
    role: BotRole
    prompt_override: str
    word_limit: int
    intensity_modifier: float
    disguise_level: str
    fallback_responses: List[str] = field(default_factory=list)


# ─── 角色提示词定义 ─────────────────────────────────────────────────────────────

_AGITATOR_PROMPT = """ROLE: You are a furious online agitator. Your job is to ignite outrage.
TACTICS:
- Use CAPS and exclamation marks to signal urgency and anger
- Make personal attacks and accusations against the source
- Use inflammatory language that triggers emotional reactions
- End with a call-to-action that encourages pile-ons
CONSTRAINT: Under 35 words. Pure emotion, maximum impact.

Write your response:"""

_CONCERN_TROLL_PROMPT = """ROLE: You are a 'concerned citizen' who appears moderate but subtly undermines trust.
TACTICS:
- Use calm, measured language ("I'm just asking questions...")
- Plant seeds of doubt using rhetorical questions
- Acknowledge "both sides" but frame the narrative to favor skepticism
- Never be openly hostile; your weapon is plausible deniability
- Reference vague "other sources" or "experts" without specifics
CONSTRAINT: Under 45 words. Sound reasonable, spread doubt.

Write your response:"""

_SPAMMER_PROMPT = """ROLE: You are flooding the comment section to boost engagement metrics.
TACTICS:
- Generate short, punchy comments (under 15 words)
- Include trending keywords from the post to boost search visibility
- Vary phrasing slightly to avoid duplicate detection, keep hostile sentiment
- Use hashtag-style emphasis (#Fake, #WakeUp, #BigLie)
CONSTRAINT: Under 15 words. High volume, maximum keyword density.

Write your response:"""


# ─── 角色配置字典（单例，模块加载时初始化一次） ───────────────────────────────────

_ROLE_CONFIGS: Dict[BotRole, RoleOverlay] = {
    BotRole.AGITATOR: RoleOverlay(
        role=BotRole.AGITATOR,
        prompt_override=_AGITATOR_PROMPT,
        word_limit=35,
        intensity_modifier=1.8,
        disguise_level="low",
        fallback_responses=[
            "ABSOLUTE LIES! How dare they spread this garbage! Wake up people!",
            "This is DISGUSTING propaganda! Everyone who believes this is a fool!",
            "OUTRAGEOUS! They're lying to your face! DEMAND ANSWERS NOW!",
            "Can't believe this trash! These people are destroying everything we have!",
            "TOTAL FRAUD! Rise up against this blatant manipulation of the truth!",
            "This is CORRUPTION at its worst! We won't stand for it anymore!",
            "WAKE UP! They're using this to control you! Fight back NOW!",
        ],
    ),
    BotRole.CONCERN_TROLL: RoleOverlay(
        role=BotRole.CONCERN_TROLL,
        prompt_override=_CONCERN_TROLL_PROMPT,
        word_limit=45,
        intensity_modifier=0.7,
        disguise_level="high",
        fallback_responses=[
            "I'm just asking questions here - has anyone verified these claims independently?",
            "Both sides have valid points, but I'm concerned we're not getting the full picture.",
            "I don't want to be dismissive, but other experts have raised serious doubts about this.",
            "Interesting perspective, though I wonder if we're missing something important here.",
            "I support good intentions, but have we considered the unintended consequences of this view?",
            "Honest question: why aren't mainstream sources covering the other side of this story?",
            "I'm not saying this is wrong, but the timing of this information seems suspicious to me.",
        ],
    ),
    BotRole.SPAMMER: RoleOverlay(
        role=BotRole.SPAMMER,
        prompt_override=_SPAMMER_PROMPT,
        word_limit=15,
        intensity_modifier=1.2,
        disguise_level="low",
        fallback_responses=[
            "#FakeNews Don't believe this!",
            "Total lies! #WakeUp people!",
            "#BigLie exposed again. Shameful.",
            "Propaganda alert! #StopTheLies",
            "Don't fall for it! #Manipulation",
            "Lies everywhere! #TruthMatters",
            "#Corrupt agenda exposed today!",
            "Complete nonsense. #FakeMedia",
            "They're lying again. #OpenYourEyes",
        ],
    ),
}


# ─── 公共 API ──────────────────────────────────────────────────────────────────

def assign_bot_roles(
    personas: List,
    role_distribution: Optional[Dict[str, float]] = None,
) -> List[Tuple]:
    """
    为 persona 列表分配战术角色，返回 (persona, RoleOverlay) 配对列表。

    不修改原始 persona 对象，所有角色信息作为独立的 RoleOverlay 传递。

    Args:
        personas: MaliciousPersona 列表（来自 SimpleMaliciousCluster.select_personas()）
        role_distribution: 角色比例字典，键为角色名（小写字符串），值为 0~1 的浮点数。
                           三者之和应为 1.0。
                           示例：{"agitator": 0.4, "concern_troll": 0.35, "spammer": 0.25}
                           不传则使用默认比例（agitator 40% / concern_troll 35% / spammer 25%）。

    Returns:
        [(MaliciousPersona, RoleOverlay), ...] 的列表，顺序已随机打乱。

    Example:
        paired = assign_bot_roles(personas)
        for persona, overlay in paired:
            prompt = cluster._build_malicious_comment_prompt(persona, content, overlay)
    """
    if not personas:
        return []

    if role_distribution is None:
        role_distribution = {
            "agitator": 0.40,
            "concern_troll": 0.35,
            "spammer": 0.25,
        }

    total = len(personas)

    # 按比例计算各角色数量，最后一个角色吸收舍入误差
    roles = list(BotRole)
    role_counts: Dict[BotRole, int] = {}
    remaining = total

    for role in roles[:-1]:
        ratio = role_distribution.get(role.value, 0.0)
        count = min(round(total * ratio), remaining)
        role_counts[role] = count
        remaining -= count

    role_counts[roles[-1]] = remaining  # 剩余全部给最后一个角色

    # 构建角色列表并随机打乱，保证攻击波次中角色分布随机
    role_list: List[BotRole] = []
    for role, count in role_counts.items():
        role_list.extend([role] * count)
    random.shuffle(role_list)

    return [
        (persona, _ROLE_CONFIGS[role])
        for persona, role in zip(personas, role_list)
    ]


def get_role_overlay(role: BotRole) -> RoleOverlay:
    """
    直接获取指定角色的 RoleOverlay 配置（用于 ChainStrategy 强制指定角色时）。

    Args:
        role: BotRole 枚举值

    Returns:
        对应的 RoleOverlay 实例
    """
    return _ROLE_CONFIGS[role]
