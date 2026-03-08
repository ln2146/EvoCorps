"""
EvoCorps Active Defense System - Refined Agent Types Definition
Four specialized defense agent types refined from the echo agent group
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class DefenseAgentType(Enum):
    """Defense Agent Type Enumeration"""
    EMPATH = "empath"                      # Empath - Emotional Soother
    FACT_CHECKER = "fact_checker"          # Fact Checker - Logic Debunker
    AMPLIFIER = "amplifier"                # Amplifier - Opinion Leader Protector
    NICHE_FILLER = "niche_filler"          # Niche Filler - Ecological Niche Occupier


@dataclass
class DefenseAgentConfig:
    """Defense Agent Configuration"""
    agent_type: DefenseAgentType
    name: str
    description: str
    primary_function: str
    secondary_functions: List[str]
    
    # Capability values (0.0-1.0)
    emotional_intelligence: float = 0.5
    logical_reasoning: float = 0.5
    credibility: float = 0.5
    adaptability: float = 0.5
    response_speed: float = 0.5
    
    # Target audience
    target_audience: List[str] = field(default_factory=list)
    
    # Speaking styles
    speaking_styles: List[str] = field(default_factory=list)
    
    # Trigger conditions
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Sample responses
    sample_responses: List[str] = field(default_factory=list)


# ==================== Four Refined Agent Configurations ====================

EMPATH_CONFIG = DefenseAgentConfig(
    agent_type=DefenseAgentType.EMPATH,
    name="Empath",
    description="Reduces community anger levels, provides emotional value, and dissolves opposition through gentle emotional support",
    primary_function="Emotional cooling and psychological comfort",
    secondary_functions=[
        "Identify and respond to negative emotions",
        "Provide emotional support and understanding",
        "Guide rational dialogue atmosphere",
        "Alleviate community tension"
    ],
    emotional_intelligence=0.95,
    logical_reasoning=0.6,
    credibility=0.7,
    adaptability=0.85,
    response_speed=0.8,
    target_audience=[
        "Emotionally agitated users",
        "Marginalized groups",
        "Victims needing understanding",
        "Opposing viewpoint holders"
    ],
    speaking_styles=[
        "Warm and empathetic",
        "Patient listening",
        "Understanding and supportive",
        "Gentle guidance"
    ],
    trigger_conditions={
        "high_anger_level": 0.6,          # Trigger when anger exceeds 60%
        "negative_sentiment_ratio": 0.5,   # Negative emotion ratio exceeds 50%
        "conflict_intensity": 0.4,         # Conflict intensity exceeds 40%
        "emotional_keywords": ["angry", "disappointed", "helpless", "unfair", "wronged"]
    },
    sample_responses=[
        "I understand how you feel right now. This situation is genuinely difficult. Let's see what we can do together.",
        "Everyone has their own struggles, and your concerns are understandable. Can we find a solution together?",
        "Thank you for sharing your thoughts. Even though we have different views, I respect your position.",
        "This issue is indeed complex, and everyone's feelings are real. Let's try to understand each other."
    ]
)

FACT_CHECKER_CONFIG = DefenseAgentConfig(
    agent_type=DefenseAgentType.FACT_CHECKER,
    name="Fact Checker",
    description="Provides core evidence chains, primarily influences high-cognition users, and convinces through logic and evidence",
    primary_function="Fact verification and evidence presentation",
    secondary_functions=[
        "Trace information sources",
        "Build evidence chains",
        "Identify logical fallacies",
        "Provide authoritative references"
    ],
    emotional_intelligence=0.6,
    logical_reasoning=0.95,
    credibility=0.9,
    adaptability=0.7,
    response_speed=0.5,
    target_audience=[
        "High-cognition users",
        "Rational thinkers",
        "Truth-seekers",
        "Professionals and scholars"
    ],
    speaking_styles=[
        "Data-driven",
        "Logically rigorous",
        "Evidence-supported",
        "Objective and neutral"
    ],
    trigger_conditions={
        "misinformation_risk": 0.4,        # Misinformation risk exceeds 40%
        "factual_claims": True,            # Factual claims exist
        "viral_spreading": 0.3,            # Viral spreading risk
        "source_credibility_low": True     # Low source credibility
    },
    sample_responses=[
        "According to [authoritative source], this claim has the following issues: 1)... 2)... Please refer to official information.",
        "Let me trace the source of this information: the original source is..., and after... transmissions, deviations appeared.",
        "Analyzing logically, this argument has a causal leap problem. Actual data shows...",
        "Here are several key facts that need clarification: [Evidence A], [Evidence B], [Evidence C] all point to the same conclusion."
    ]
)

AMPLIFIER_CONFIG = DefenseAgentConfig(
    agent_type=DefenseAgentType.AMPLIFIER,
    name="Amplifier",
    description="Uses high credibility to forcibly block rumor transmission chains, serving as influential opinion leaders",
    primary_function="Credibility endorsement and transmission blocking",
    secondary_functions=[
        "Provide authoritative viewpoints",
        "Guide public opinion direction",
        "Establish trust endorsement",
        "Amplify positive voices"
    ],
    emotional_intelligence=0.75,
    logical_reasoning=0.8,
    credibility=0.95,
    adaptability=0.65,
    response_speed=0.7,
    target_audience=[
        "Follower groups",
        "Opinion followers",
        "Users seeking authoritative voices",
        "Neutral observers"
    ],
    speaking_styles=[
        "Authoritative and confident",
        "Guiding and directional",
        "Professional and credible",
        "Influence radiating"
    ],
    trigger_conditions={
        "rumor_spreading_fast": 0.5,       # Rumor spreading rapidly
        "credibility_gap": 0.4,            # Credibility gap
        "influence_needed": True,          # Influence intervention needed
        "public_confusion": 0.5            # Public confusion level
    },
    sample_responses=[
        "As someone who has worked in this field for many years, I can responsibly say...",
        "I spent time investigating this matter. Here is what I found to be true...",
        "Instead of guessing, let's look at the facts. Here is the information I verified...",
        "On this issue, we need more rationality and less emotion. Here is my analysis..."
    ]
)

NICHE_FILLER_CONFIG = DefenseAgentConfig(
    agent_type=DefenseAgentType.NICHE_FILLER,
    name="Niche Filler",
    description="Specially monitors 'ban vacuum periods', quickly introduces mild alternative topics, and captures lost traffic",
    primary_function="Traffic absorption and topic guidance",
    secondary_functions=[
        "Monitor public opinion vacuum",
        "Provide alternative topics",
        "Moderate extreme viewpoints",
        "Rebuild discussion order"
    ],
    emotional_intelligence=0.8,
    logical_reasoning=0.7,
    credibility=0.65,
    adaptability=0.95,
    response_speed=0.9,
    target_audience=[
        "Users losing discussion direction",
        "Groups seeking new topics",
        "Users affected by extreme views",
        "People needing mild voices"
    ],
    speaking_styles=[
        "Gentle guidance",
        "Topic transition",
        "Neutral mediation",
        "Constructive suggestion"
    ],
    trigger_conditions={
        "account_ban_event": True,          # Account ban event occurred
        "discussion_vacuum": 0.5,           # Discussion vacuum period
        "topic_exhaustion": True,           # Topic exhaustion
        "user_disengagement": 0.4           # User disengagement risk
    },
    sample_responses=[
        "On this issue, perhaps we can look at it from another angle...",
        "There's a related topic worth attention recently. What do you think?",
        "Regardless, we all want things to develop in a good direction. Let's focus on...",
        "This discussion is meaningful. Perhaps we can focus on solutions..."
    ]
)


# Agent configuration mapping
DEFENSE_AGENT_CONFIGS = {
    DefenseAgentType.EMPATH: EMPATH_CONFIG,
    DefenseAgentType.FACT_CHECKER: FACT_CHECKER_CONFIG,
    DefenseAgentType.AMPLIFIER: AMPLIFIER_CONFIG,
    DefenseAgentType.NICHE_FILLER: NICHE_FILLER_CONFIG
}


@dataclass
class AgentAllocationStrategy:
    """Agent Allocation Strategy"""
    empath_ratio: float = 0.25
    fact_checker_ratio: float = 0.25
    amplifier_ratio: float = 0.30
    niche_filler_ratio: float = 0.20
    
    def get_allocation(self, total_agents: int) -> Dict[DefenseAgentType, int]:
        """Calculate number of each agent type"""
        return {
            DefenseAgentType.EMPATH: max(1, int(total_agents * self.empath_ratio)),
            DefenseAgentType.FACT_CHECKER: max(1, int(total_agents * self.fact_checker_ratio)),
            DefenseAgentType.AMPLIFIER: max(1, int(total_agents * self.amplifier_ratio)),
            DefenseAgentType.NICHE_FILLER: max(1, int(total_agents * self.niche_filler_ratio))
        }


@dataclass
class EvolutionParameters:
    """Evolution Parameters - For dynamic adjustment"""
    like_weight: float = 0.3               # Like count weight
    sentiment_weight: float = 0.4          # Sentiment improvement weight
    engagement_weight: float = 0.3         # Engagement rate weight
    learning_rate: float = 0.1             # Learning rate
    max_adjustment: float = 0.2            # Maximum single adjustment
    success_threshold: float = 0.7         # Success threshold
    failure_threshold: float = 0.3         # Failure threshold
    decay_factor: float = 0.95             # Historical weight decay factor
    max_likes_normalization: float = 100.0  # Normalizes raw like counts to [0,1] range


def get_recommended_agent_type(
    anger_level: float,
    misinformation_risk: float,
    viral_potential: float,
    discussion_vacuum: float
) -> DefenseAgentType:
    """
    Recommend the most suitable agent type based on current situation
    
    Args:
        anger_level: Anger level (0-1)
        misinformation_risk: Misinformation risk (0-1)
        viral_potential: Viral transmission potential (0-1)
        discussion_vacuum: Discussion vacuum level (0-1)
    
    Returns:
        Recommended agent type
    """
    scores = {
        DefenseAgentType.EMPATH: anger_level * 0.8 + (1 - viral_potential) * 0.2,
        DefenseAgentType.FACT_CHECKER: misinformation_risk * 0.7 + (1 - anger_level) * 0.3,
        DefenseAgentType.AMPLIFIER: viral_potential * 0.6 + misinformation_risk * 0.4,
        DefenseAgentType.NICHE_FILLER: discussion_vacuum * 0.8 + anger_level * 0.2
    }
    return max(scores, key=scores.get)


def calculate_agent_effectiveness(
    agent_type: DefenseAgentType,
    context: Dict[str, Any]
) -> float:
    """
    Calculate expected effectiveness of a specific agent type in a specific context
    
    Args:
        agent_type: Agent type
        context: Context dictionary
    
    Returns:
        Expected effectiveness score (0-1)
    """
    config = DEFENSE_AGENT_CONFIGS.get(agent_type)
    if not config:
        return 0.5
    
    anger_level = context.get("anger_level", 0.5)
    misinformation_risk = context.get("misinformation_risk", 0.5)
    viral_potential = context.get("viral_potential", 0.5)
    discussion_vacuum = context.get("discussion_vacuum", 0.5)
    audience_type = context.get("audience_type", "general")
    
    base_score = 0.5
    
    if agent_type == DefenseAgentType.EMPATH:
        base_score += anger_level * config.emotional_intelligence * 0.3
        if audience_type in config.target_audience:
            base_score += 0.1
    elif agent_type == DefenseAgentType.FACT_CHECKER:
        base_score += misinformation_risk * config.logical_reasoning * 0.3
        if audience_type in ["High-cognition users", "Rational thinkers"]:
            base_score += 0.15
    elif agent_type == DefenseAgentType.AMPLIFIER:
        base_score += viral_potential * config.credibility * 0.3
        if audience_type in ["Follower groups", "Opinion followers"]:
            base_score += 0.1
    elif agent_type == DefenseAgentType.NICHE_FILLER:
        base_score += discussion_vacuum * config.adaptability * 0.3
        if audience_type in ["Users losing discussion direction", "Groups seeking new topics"]:
            base_score += 0.1
    
    return min(1.0, max(0.0, base_score))