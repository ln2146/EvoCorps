"""
Amplifier Role Enhancement Module
Integrates 4 new defense roles into the existing Amplifier Agents system
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class AmplifierRole(Enum):
    """Refined amplifier agent role types"""
    EMPATH = "empath"           # Emotional soother - reduces anger
    FACT_CHECKER = "fact_checker"  # Logic debunker - provides evidence
    AMPLIFIER = "amplifier"     # Credibility blocker - uses reputation
    NICHE_FILLER = "niche_filler"  # Vacuum filler - fills discussion gaps


@dataclass
class RoleAllocationStrategy:
    """Role allocation strategy configuration"""
    empath_ratio: float = 0.25        # Empath ratio
    fact_checker_ratio: float = 0.25  # Fact checker ratio
    amplifier_ratio: float = 0.25     # Amplifier ratio
    niche_filler_ratio: float = 0.25  # Niche filler ratio


# Role configuration mapping
ROLE_CONFIGS = {
    AmplifierRole.EMPATH: {
        "name": "Empath",
        "description": "Reduces community anger through emotional resonance, provides emotional value",
        "speaking_styles": [
            "empathetic response",
            "emotional support",
            "gentle suggestion"
        ],
        "sample_responses": [
            "I understand everyone's concerns, this is indeed not an easy topic",
            "I can feel everyone's care about this matter, we all hope things develop in a good direction",
            "Everyone's worries are reasonable, let's find constructive solutions together"
        ],
        "trigger_conditions": {
            "anger_level": 0.6,       # Trigger when anger > 60%
            "sentiment_threshold": 0.4  # Trigger when sentiment < 0.4
        },
        "metrics": {
            "emotional_iq": 0.95,
            "logic": 0.6,
            "credibility": 0.7,
            "adaptability": 0.8
        }
    },
    
    AmplifierRole.FACT_CHECKER: {
        "name": "Fact Checker",
        "description": "Provides evidence chains, uses logic and facts to influence high-cognition users",
        "speaking_styles": [
            "data-backed",
            "logical analysis",
            "fact checking"
        ],
        "sample_responses": [
            "According to public data, this claim differs from the actual situation",
            "I checked the original sources, the facts are...",
            "Analyzing logically, this conclusion has some issues"
        ],
        "trigger_conditions": {
            "misinformation_risk": 0.4,  # Trigger when misinformation risk > 40%
            "factuality_concern": True
        },
        "metrics": {
            "emotional_iq": 0.6,
            "logic": 0.95,
            "credibility": 0.9,
            "adaptability": 0.7
        }
    },
    
    AmplifierRole.AMPLIFIER: {
        "name": "Amplifier",
        "description": "Uses established credibility to block rumor spread, suitable for viral periods",
        "speaking_styles": [
            "authoritative statement",
            "professional endorsement",
            "reputation guarantee"
        ],
        "sample_responses": [
            "Based on my professional experience, I think this claim needs more verification",
            "As someone who has worked in this field for many years, my view is...",
            "I have deep understanding of this topic, the actual situation may be more complex"
        ],
        "trigger_conditions": {
            "viral_potential": 0.7,     # Viral potential > 70%
            "amplification_needed": True
        },
        "metrics": {
            "emotional_iq": 0.7,
            "logic": 0.8,
            "credibility": 0.95,
            "adaptability": 0.75
        }
    },
    
    AmplifierRole.NICHE_FILLER: {
        "name": "Niche Filler",
        "description": "Quickly fills discussion vacuum after bans, captures traffic",
        "speaking_styles": [
            "rapid response",
            "topic guidance",
            "niche occupation"
        ],
        "sample_responses": [
            "This topic is interesting, let's look at it from another angle",
            "Rather than dwelling on this issue, why not discuss...",
            "I think we can steer the discussion in a more constructive direction"
        ],
        "trigger_conditions": {
            "discussion_vacuum": 0.5,   # Discussion vacuum > 50%
            "ban_event": True
        },
        "metrics": {
            "emotional_iq": 0.75,
            "logic": 0.7,
            "credibility": 0.65,
            "adaptability": 0.95,
            "speed": 0.9
        }
    }
}


def get_recommended_role_distribution(
    anger_level: float = 0.5,
    misinformation_risk: float = 0.3,
    viral_potential: float = 0.3,
    discussion_vacuum: float = 0.2,
    total_agents: int = 5,
    evolved_base_ratios: Optional[Dict[str, float]] = None
) -> Dict[str, int]:
    """
    Recommend role distribution based on context parameters

    Args:
        anger_level: Anger level (0-1)
        misinformation_risk: Misinformation risk (0-1)
        viral_potential: Viral potential (0-1)
        discussion_vacuum: Discussion vacuum level (0-1)
        total_agents: Total number of agents
        evolved_base_ratios: Evolved allocation ratios from EvolutionEngine (optional)

    Returns:
        Role distribution dictionary {role_type: count}
    """
    # Base allocation ratios - use evolved ratios when available
    if evolved_base_ratios:
        base_ratios = RoleAllocationStrategy(
            empath_ratio=evolved_base_ratios.get("empath", 0.25),
            fact_checker_ratio=evolved_base_ratios.get("fact_checker", 0.25),
            amplifier_ratio=evolved_base_ratios.get("amplifier", 0.25),
            niche_filler_ratio=evolved_base_ratios.get("niche_filler", 0.25),
        )
    else:
        base_ratios = RoleAllocationStrategy()
    
    # Adjust ratios based on context
    adjustments = {
        "empath": 0.0,
        "fact_checker": 0.0,
        "amplifier": 0.0,
        "niche_filler": 0.0
    }
    
    # High anger -> increase empaths
    if anger_level > 0.6:
        adjustments["empath"] += (anger_level - 0.5) * 0.5
    elif anger_level < 0.3:
        adjustments["empath"] -= 0.1
    
    # High misinformation risk -> increase fact checkers
    if misinformation_risk > 0.4:
        adjustments["fact_checker"] += (misinformation_risk - 0.3) * 0.5
    elif misinformation_risk < 0.2:
        adjustments["fact_checker"] -= 0.1
    
    # High viral potential -> increase amplifiers
    if viral_potential > 0.7:
        adjustments["amplifier"] += (viral_potential - 0.6) * 0.4
    
    # High discussion vacuum -> increase niche fillers
    if discussion_vacuum > 0.5:
        adjustments["niche_filler"] += (discussion_vacuum - 0.4) * 0.4
    
    # Apply adjustments and normalize
    final_ratios = {
        "empath": max(0.1, min(0.5, base_ratios.empath_ratio + adjustments["empath"])),
        "fact_checker": max(0.1, min(0.5, base_ratios.fact_checker_ratio + adjustments["fact_checker"])),
        "amplifier": max(0.1, min(0.5, base_ratios.amplifier_ratio + adjustments["amplifier"])),
        "niche_filler": max(0.05, min(0.4, base_ratios.niche_filler_ratio + adjustments["niche_filler"]))
    }
    
    # Normalize
    total_ratio = sum(final_ratios.values())
    normalized_ratios = {k: v / total_ratio for k, v in final_ratios.items()}
    
    # Calculate specific counts
    distribution = {}
    remaining = total_agents
    
    for role, ratio in normalized_ratios.items():
        count = int(total_agents * ratio)
        distribution[role] = count
        remaining -= count
    
    # Distribute remainder to most important role
    if remaining > 0:
        # Find role with highest adjustment
        max_adjust_role = max(adjustments, key=adjustments.get)
        if adjustments[max_adjust_role] > 0:
            distribution[max_adjust_role] += remaining
        else:
            # Default to empath
            distribution["empath"] += remaining
    
    return distribution


def get_role_instructions(role_type: str) -> Dict[str, Any]:
    """Get detailed instruction configuration for a role"""
    try:
        role_enum = AmplifierRole(role_type)
        config = ROLE_CONFIGS.get(role_enum, {})
        
        return {
            "role_type": role_type,
            "name": config.get("name", role_type),
            "description": config.get("description", ""),
            "speaking_styles": config.get("speaking_styles", []),
            "sample_responses": config.get("sample_responses", []),
            "metrics": config.get("metrics", {})
        }
    except ValueError:
        return {
            "role_type": role_type,
            "name": role_type,
            "description": "General role",
            "speaking_styles": ["neutral response"],
            "sample_responses": ["I understand this point"],
            "metrics": {}
        }


def convert_old_role_to_new(old_role: str) -> str:
    """Map old role types to new role types"""
    mapping = {
        "technical_experts": "fact_checker",
        "balanced_moderates": "empath",
        "community_voices": "niche_filler",
        "fact_checkers": "fact_checker",
        "general": "empath"
    }
    return mapping.get(old_role, "empath")
