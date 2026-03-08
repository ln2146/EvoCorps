"""
MOSAIC Agent System
Multi-Agent Opinion Sentiment Analysis and Intervention Coordination

This module provides a comprehensive multi-agent system for opinion balance
and sentiment analysis with automatic defense mechanisms.
"""

# Core agents
from .simple_coordination_system import (
    SimpleCoordinationSystem,
    SimpleAnalystAgent,
    SimpleStrategistAgent,
    SimpleLeaderAgent,
    SimpleamplifierAgent
)

# Enhanced leader agent with USC workflow
try:
    from .enhanced_leader_agent import EnhancedLeaderAgent, ArgumentDatabase
except ImportError:
    pass

# Defense system components (automatic role enhancement)
try:
    from .defense_agent_types import (
        DefenseAgentType,
        DefenseAgentConfig,
        AgentAllocationStrategy,
        get_recommended_agent_type,
        calculate_agent_effectiveness
    )
except ImportError:
    pass

try:
    from .defense_evolution_system import (
        EvolutionEngine,
        EvolutionParameters,
        FeedbackMetrics,
        AgentPerformance,
        DefenseCoordinator
    )
except ImportError:
    pass

try:
    from .defense_monitoring_center import (
        DefenseMonitoringCenter,
        TopicData,
        AccountMetrics,
        NicheOccupancyTracker,
        create_monitoring_center
    )
except ImportError:
    pass

try:
    from .defense_integration import (
        IntegratedDefenseSystem,
        create_integrated_defense_system
    )
except ImportError:
    pass

try:
    from .amplifier_role_enhancer import (
        AmplifierRole,
        RoleAllocationStrategy,
        get_recommended_role_distribution,
        get_role_instructions,
        convert_old_role_to_new
    )
except ImportError:
    pass

try:
    from .role_enhancement_patch import (
        calculate_context_parameters,
        enhanced_assign_roles_to_agents,
        enhanced_generate_fallback_instruction,
        integrate_with_coordination_system,
        _ROLE_ENHANCEMENT_AVAILABLE
    )
except ImportError:
    _ROLE_ENHANCEMENT_AVAILABLE = False

# Defense agent prompts (specialized prompts for each defense role)
try:
    from .defense_agent_prompts import (
        DefenseAgentRole,
        EmpathPrompts,
        FactCheckerPrompts,
        AmplifierPrompts,
        NicheFillerPrompts,
        DefensePromptManager,
        get_empath_system_prompt,
        get_fact_checker_system_prompt,
        get_amplifier_system_prompt,
        get_niche_filler_system_prompt
    )
except ImportError:
    pass

# Version info
__version__ = "1.0.0"
__author__ = "MOSAIC Team"

# Public API
__all__ = [
    # Core coordination
    "SimpleCoordinationSystem",
    "SimpleAnalystAgent", 
    "SimpleStrategistAgent",
    "SimpleLeaderAgent",
    "SimpleamplifierAgent",
    
    # Enhanced leader
    "EnhancedLeaderAgent",
    "ArgumentDatabase",
    
    # Defense system
    "DefenseAgentType",
    "DefenseAgentConfig",
    "AgentAllocationStrategy",
    "get_recommended_agent_type",
    "calculate_agent_effectiveness",

    # Evolution system
    "EvolutionEngine",
    "EvolutionParameters",
    "FeedbackMetrics",
    "AgentPerformance",
    "DefenseCoordinator",

    # Monitoring
    "DefenseMonitoringCenter",
    "TopicData",
    "AccountMetrics",
    "NicheOccupancyTracker",
    "create_monitoring_center",

    # Integration
    "IntegratedDefenseSystem",
    "create_integrated_defense_system",

    # Role enhancement
    "AmplifierRole",
    "RoleAllocationStrategy",
    "get_recommended_role_distribution",
    "get_role_instructions",
    "convert_old_role_to_new",
    
    # Auto-integration
    "calculate_context_parameters",
    "enhanced_assign_roles_to_agents",
    "enhanced_generate_fallback_instruction",
    "integrate_with_coordination_system",
    "_ROLE_ENHANCEMENT_AVAILABLE",
    
    # Defense prompts
    "DefenseAgentRole",
    "EmpathPrompts",
    "FactCheckerPrompts",
    "AmplifierPrompts",
    "NicheFillerPrompts",
    "DefensePromptManager",
    "get_empath_system_prompt",
    "get_fact_checker_system_prompt",
    "get_amplifier_system_prompt",
    "get_niche_filler_system_prompt"
]