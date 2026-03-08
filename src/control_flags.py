"""Global control flags for runtime features.

These flags are intended to be the *single source of truth* for
runtime switches that affect the simulation and related components.

They are mutated in three main ways:
    • CLI / terminal choices in main.py
    • HTTP control API (FastAPI in main.py)
    • Standalone tools such as opinion_balance_launcher.py

Simulation code and launchers should *only* look at these flags when
deciding whether to run malicious attacks, post‑hoc intervention, etc.
"""

from typing import Dict, Optional, Literal


# Whether malicious bot attacks are allowed to run.
# True  -> enable all malicious attack logic
# False -> completely disable malicious attacks
attack_enabled: bool = False


# 当前恶意攻击协同模式。
# 可选值：
# - "swarm": 蜂群式
# - "dispersed": 游离式
# - "chain": 链式传播
attack_mode: Literal["swarm", "dispersed", "chain"] = "swarm"


# Whether post‑hoc intervention (third-party fact checking) is enabled.
# This flag controls the third-party fact checking system.
#
# True  -> enable third-party fact checking (_run_fact_checking_async)
# False -> completely disable third-party fact checking
#
# NOTE: Truth appending (_append_truth_to_fake_news_posts_with_delay) 
# executes unconditionally and is NOT controlled by this flag.
aftercare_enabled: bool = True


# Global auto-status for opinion balance monitoring / interventions.
# True  -> auto monitoring ON
# False/None -> auto monitoring OFF
#
# NOTE: All components should treat this flag as the single
#       source of truth for whether automatic opinion-balance
#       monitoring is considered "running".
auto_status: Optional[bool] = False


# Whether moderation system (content review & intervention) is enabled.
# True  -> enable moderation system (visibility degradation, warning labels, takedowns)
# False -> completely disable moderation system
#
# The moderation system maintains ecological boundaries through:
# - Visibility degradation: reducing weight in recommendation algorithm
# - Warning labels: marking content with official warnings
# - Hard takedowns: removing posts and banning users
moderation_enabled: bool = False


def as_dict() -> Dict[str, object]:
    """Return current flag values as a simple dict for APIs."""

    return {
        "attack_enabled": attack_enabled,
        "attack_mode": attack_mode,
        "aftercare_enabled": aftercare_enabled,
        "auto_status": auto_status,
        "moderation_enabled": moderation_enabled,
    }
