"""
Role Enhancement Patch for SimpleCoordinationSystem
This module provides enhanced role assignment functionality
that automatically uses the new 4 defense roles.

To integrate into simple_coordination_system.py:
1. Import this module at the top
2. Replace _assign_roles_to_agents method with the enhanced version
"""

from typing import Dict, Any, List
from .amplifier_role_enhancer import (
    get_recommended_role_distribution,
    get_role_instructions,
    convert_old_role_to_new,
    AmplifierRole,
    ROLE_CONFIGS
)


def calculate_context_parameters(analysis_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate context parameters from analysis data for role distribution
    
    Args:
        analysis_data: Analysis result from analyst agent
    
    Returns:
        Dictionary with anger_level, misinformation_risk, viral_potential, discussion_vacuum
    """
    # Extract sentiment score (inverse for anger)
    sentiment_score = analysis_data.get("sentiment_score", 0.5)
    anger_level = 1.0 - sentiment_score  # Lower sentiment = higher anger
    
    # Extract extremism level for misinformation risk
    extremism_level = analysis_data.get("extremism_level", 0)
    # Normalize extremism (assuming 0-4 scale)
    misinformation_risk = min(extremism_level / 4.0, 1.0)
    
    # Extract engagement metrics for viral potential
    engagement_metrics = analysis_data.get("engagement_metrics", {})
    intensity_level = engagement_metrics.get("intensity_level", "MODERATE")
    intensity_map = {"LOW": 0.2, "MODERATE": 0.4, "HIGH": 0.7, "VIRAL": 0.9}
    viral_potential = intensity_map.get(intensity_level, 0.4)
    
    # Read discussion_vacuum directly from analysis_data (set by NicheFiller trigger or analyst)
    discussion_vacuum = float(analysis_data.get("discussion_vacuum", 0.3))

    return {
        "anger_level": anger_level,
        "misinformation_risk": misinformation_risk,
        "viral_potential": viral_potential,
        "discussion_vacuum": discussion_vacuum
    }


def enhanced_assign_roles_to_agents(
    agents: List,
    role_distribution: Dict[str, int],
    analysis_data: Dict[str, Any] = None,
    use_smart_distribution: bool = True,
    total_agents: int = 5,
    base_ratios: Dict[str, float] = None
) -> List:
    """
    Enhanced role assignment that uses new defense roles

    This replaces the original _assign_roles_to_agents method

    Args:
        agents: List of amplifier agents
        role_distribution: Original role distribution from strategist
        analysis_data: Analysis data for smart distribution
        use_smart_distribution: Whether to use smart distribution
        total_agents: Total number of agents
        base_ratios: Evolved base ratios from EvolutionEngine (optional)

    Returns:
        List of agents with assigned roles
    """
    if use_smart_distribution and analysis_data:
        # Calculate context parameters
        context = calculate_context_parameters(analysis_data)

        # Get smart role distribution, using evolved base ratios when available
        new_distribution = get_recommended_role_distribution(
            anger_level=context["anger_level"],
            misinformation_risk=context["misinformation_risk"],
            viral_potential=context["viral_potential"],
            discussion_vacuum=context["discussion_vacuum"],
            total_agents=total_agents,
            evolved_base_ratios=base_ratios
        )

        # Use new distribution instead of original
        role_distribution = new_distribution
    
    if not role_distribution:
        # Default distribution: use standard role distribution with neutral context
        role_distribution = get_recommended_role_distribution(total_agents=total_agents)
    
    # Assign agents by role type
    agent_index = 0
    for role_type, count in role_distribution.items():
        # Ensure count is int
        try:
            count = int(count) if count is not None else 0
        except (ValueError, TypeError):
            count = 0

        if count <= 0:
            continue

        # Assign agents for this role type
        assigned_count = 0
        while assigned_count < count and agent_index < len(agents):
            agents[agent_index].assigned_role = role_type
            
            # Assign enhanced role instructions
            role_instructions = get_role_instructions(role_type)
            agents[agent_index].role_instructions = role_instructions
            
            # Assign sample responses for this role
            if role_instructions.get("sample_responses"):
                agents[agent_index].role_sample_responses = role_instructions["sample_responses"]
            
            agent_index += 1
            assigned_count += 1

    # Remaining agents get general role
    while agent_index < len(agents):
        agents[agent_index].assigned_role = "empath"  # Default to empath
        agents[agent_index].role_instructions = get_role_instructions("empath")
        agent_index += 1

    return agents


# Enhanced _generate_fallback_instruction with new role support
def enhanced_generate_fallback_instruction(role_type: str, index: int, target_content: str) -> Dict[str, Any]:
    """
    Generate fallback instructions with new role support
    """
    # Get base instructions from role config
    role_config = get_role_instructions(role_type)
    
    instructions = {
        "role_type": role_type,
        "agent_index": index,
        "response_style": role_config.get("speaking_styles", ["neutral response"])[0],
        "key_message": role_config.get("description", "Participate in discussion"),
        "tone": "supportive",
        "typical_phrases": role_config.get("sample_responses", ["I understand this point"]),
        "focus_points": [],
        "response_length": "60-120 words"
    }
    
    # Add role-specific focus points
    if role_type == "empath":
        instructions["focus_points"] = [
            "Acknowledge emotional concerns",
            "Validate feelings without agreeing with misinformation",
            "Guide toward constructive discussion"
        ]
        instructions["tone"] = "empathetic and supportive"
    elif role_type == "fact_checker":
        instructions["focus_points"] = [
            "Provide evidence-based counterpoints",
            "Cite credible sources",
            "Avoid emotional language"
        ]
        instructions["tone"] = "objective and factual"
    elif role_type == "amplifier":
        instructions["focus_points"] = [
            "Use established credibility",
            "Provide authoritative perspective",
            "Amplify accurate information"
        ]
        instructions["tone"] = "authoritative and professional"
    elif role_type == "niche_filler":
        instructions["focus_points"] = [
            "Introduce alternative topics",
            "Redirect attention constructively",
            "Fill discussion vacuum"
        ]
        instructions["tone"] = "engaging and redirective"
    
    return instructions


# Integration helper function
def integrate_with_coordination_system(coordination_system):
    """
    Integrate role enhancement with existing coordination system
    
    Usage:
        from src.agents.role_enhancement_patch import integrate_with_coordination_system
        integrate_with_coordination_system(coordination_system)
    """
    def enhanced_assign_roles(agents, role_distribution):
        # Get analysis data from latest workflow
        analysis_data = None
        if coordination_system.action_history:
            latest_action = coordination_system.action_history[-1]
            if "phases" in latest_action:
                phase_1 = latest_action["phases"].get("phase_1", {})
                analysis_data = phase_1.get("analysis", {}).get("analysis", {})
        
        # Use enhanced assignment
        return enhanced_assign_roles_to_agents(
            agents=agents,
            role_distribution=role_distribution,
            analysis_data=analysis_data,
            use_smart_distribution=True,
            total_agents=len(agents)
        )
    
    # Replace method
    coordination_system._assign_roles_to_agents = enhanced_assign_roles
    
    def enhanced_fallback(role_type, index, target_content):
        # Convert old role names if needed
        new_role_type = convert_old_role_to_new(role_type)
        return enhanced_generate_fallback_instruction(new_role_type, index, target_content)
    
    coordination_system._generate_fallback_instruction = enhanced_fallback
    
    return coordination_system