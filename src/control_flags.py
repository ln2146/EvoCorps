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

from typing import Dict, Optional


# Whether malicious bot attacks are allowed to run.
# True  -> enable all malicious attack logic
# False -> completely disable malicious attacks
attack_enabled: bool = False


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


def as_dict() -> Dict[str, Optional[bool]]:
    """Return current flag values as a simple dict for APIs."""

    return {
        "attack_enabled": attack_enabled,
        "aftercare_enabled": aftercare_enabled,
        "auto_status": auto_status,
    }
