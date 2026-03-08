"""
Malicious bot subsystem for EvoCorps.

Simulates coordinated adversarial agents for research purposes.

Public API:
    MaliciousBotManager  - top-level manager, called by simulation.py
    SimpleMaliciousCluster - bot cluster that generates malicious content
    MaliciousPersona       - data class for a single bot's identity
"""

from .malicious_bot_manager import MaliciousBotManager
from .simple_malicious_agent import SimpleMaliciousCluster, MaliciousPersona
from .bot_role_overlay import BotRole, RoleOverlay, assign_bot_roles, get_role_overlay
from .coordination_strategies import CoordinationMode
from .config import MaliciousBotConfig, AttackModeConfig, ChainConfig, AdaptiveConfig, DEFAULT_CONFIG
from .attack_orchestrator import AttackOrchestrator
from .adaptive_controller import AdaptiveController, PressureLevel

__all__ = [
    "MaliciousBotManager",
    "SimpleMaliciousCluster",
    "MaliciousPersona",
    "BotRole",
    "RoleOverlay",
    "assign_bot_roles",
    "get_role_overlay",
    "CoordinationMode",
    "MaliciousBotConfig",
    "AttackModeConfig",
    "ChainConfig",
    "AdaptiveConfig",
    "DEFAULT_CONFIG",
    "AttackOrchestrator",
    "AdaptiveController",
    "PressureLevel",
]
