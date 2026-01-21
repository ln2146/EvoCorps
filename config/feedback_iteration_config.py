#!/usr/bin/env python3
"""
Feedback and iteration system configuration file.
Centralizes system parameters and settings.
"""

from typing import Dict, Any, List
from enum import Enum


class MonitoringMode(Enum):
    """Monitoring modes"""
    PASSIVE = "passive"      # Passive monitoring, data collection only
    ACTIVE = "active"        # Active monitoring that includes alerts
    INTELLIGENT = "intelligent"  # Intelligent monitoring with auto-adjusting policies
    ADAPTIVE = "adaptive"    # Adaptive monitoring that learns over time


class FeedbackSensitivity(Enum):
    """Feedback sensitivity levels"""
    LOW = "low"         # Low sensitivity with fewer triggers
    MEDIUM = "medium"   # Medium sensitivity with balanced triggers
    HIGH = "high"       # High sensitivity, frequent triggers
    CUSTOM = "custom"   # Custom sensitivity settings


class IterationStrategy(Enum):
    """Iteration strategies"""
    CONSERVATIVE = "conservative"  # Conservative adjustments with small changes
    BALANCED = "balanced"         # Balanced adjustments with moderate changes
    AGGRESSIVE = "aggressive"     # Aggressive adjustments for major shifts
    EXPERIMENTAL = "experimental" # Experimental adjustments exploring innovations


# Base configuration
BASE_CONFIG = {
    # Monitoring system configuration
    "monitoring": {
        "default_mode": MonitoringMode.INTELLIGENT,
        "collection_interval": 30,  # Data collection interval (seconds)
        "analysis_interval": 60,    # Analysis interval (seconds)
        "alert_cooldown": 120,      # Alert cooldown (seconds)
        "data_retention_days": 30,  # Data retention period (days)
        "max_concurrent_tasks": 10, # Max concurrent monitoring tasks
        
        # Monitoring metrics configuration
        "metrics": {
            "basic": ["likes", "comments", "shares", "sentiment_score"],
            "standard": [
                "likes", "comments", "shares", "sentiment_score",
                "engagement_rate", "reach", "impressions"
            ],
            "comprehensive": [
                "likes", "comments", "shares", "sentiment_score",
                "engagement_rate", "reach", "impressions", "click_rate",
                "sentiment_distribution", "topic_relevance", "virality_score"
            ],
            "real_time": [
                "real_time_mentions", "trending_score", "influence_spread",
                "reaction_velocity", "controversy_level", "viral_potential"
            ]
        },
        
        # Threshold configuration - triggers approx. 20 comments or 10 likes/shares
        "thresholds": {
            "likes": {"warning": 15, "critical": 10},
            "comments": {"warning": 25, "critical": 20},
            "shares": {"warning": 15, "critical": 10},
            "sentiment_score": {"warning": 0.3, "critical": 0.1},
            "engagement_rate": {"warning": 0.02, "critical": 0.01},
            "controversy_level": {"warning": 0.7, "critical": 0.9}
        }
    },
    
    # Feedback system configuration
    "feedback": {
        "default_sensitivity": FeedbackSensitivity.MEDIUM,
        "feedback_threshold": 0.1,      # Change threshold to trigger feedback
        "confidence_threshold": 0.7,    # Confidence threshold
        "max_feedback_history": 1000,   # Maximum feedback history entries
        "insight_generation_interval": 300,  # Insight generation interval (seconds)
        
        # Sensitivity configuration
        "sensitivity_settings": {
            FeedbackSensitivity.LOW: {
                "change_threshold": 0.2,
                "confidence_required": 0.8,
                "min_data_points": 10
            },
            FeedbackSensitivity.MEDIUM: {
                "change_threshold": 0.1,
                "confidence_required": 0.7,
                "min_data_points": 5
            },
            FeedbackSensitivity.HIGH: {
                "change_threshold": 0.05,
                "confidence_required": 0.6,
                "min_data_points": 3
            }
        }
    },
    
    # Iteration system configuration
    "iteration": {
        "default_strategy": IterationStrategy.BALANCED,
        "iteration_cooldown": 300,      # Iteration cooldown (seconds)
        "max_concurrent_iterations": 3, # Maximum concurrent iterations
        "max_iteration_history": 500,   # Maximum iteration history entries
        
        # Strategy settings
        "strategy_settings": {
            IterationStrategy.CONSERVATIVE: {
                "adjustment_magnitude": 0.1,
                "risk_tolerance": 0.2,
                "rollback_threshold": 0.05
            },
            IterationStrategy.BALANCED: {
                "adjustment_magnitude": 0.2,
                "risk_tolerance": 0.4,
                "rollback_threshold": 0.1
            },
            IterationStrategy.AGGRESSIVE: {
                "adjustment_magnitude": 0.4,
                "risk_tolerance": 0.7,
                "rollback_threshold": 0.2
            },
            IterationStrategy.EXPERIMENTAL: {
                "adjustment_magnitude": 0.6,
                "risk_tolerance": 0.9,
                "rollback_threshold": 0.3
            }
        },
        
        # Adjustment type configuration
        "adjustment_types": {
            "content_modification": {
                "enabled": True,
                "max_changes_per_hour": 3,
                "parameters": {
                    "tone_adjustment": ["more_positive", "more_neutral", "more_professional"],
                    "intensity_levels": ["low", "medium", "high"],
                    "sentiment_targets": [0.6, 0.7, 0.8]
                }
            },
            "timing_adjustment": {
                "enabled": True,
                "max_changes_per_hour": 2,
                "parameters": {
                    "delay_options": [5, 10, 15, 30, 60],  # Minutes
                    "optimal_times": ["morning", "afternoon", "evening"],
                    "frequency_adjustments": ["increase", "decrease", "maintain"]
                }
            },
            "audience_targeting": {
                "enabled": True,
                "max_changes_per_hour": 2,
                "parameters": {
                    "demographics": ["18-25", "26-35", "36-45", "46-55", "55+"],
                    "interests": ["politics", "technology", "social_issues", "education"],
                    "engagement_levels": ["high", "medium", "low"]
                }
            },
            "response_intensity": {
                "enabled": True,
                "max_changes_per_hour": 5,
                "parameters": {
                    "intensity_levels": ["minimal", "moderate", "strong", "maximum"],
                    "response_types": ["supportive", "corrective", "educational"],
                    "agent_counts": [3, 5, 8, 10]
                }
            }
        }
    },
    
    # Learning system configuration
    "learning": {
        "enabled": True,
        "learning_rate": 0.1,
        "pattern_recognition_threshold": 0.8,
        "min_samples_for_learning": 10,
        "max_patterns_stored": 100,
        "pattern_decay_rate": 0.05,  # Pattern decay rate
        
        # Learning objectives
        "learning_objectives": {
            "effectiveness_optimization": 0.4,
            "efficiency_improvement": 0.3,
            "risk_minimization": 0.2,
            "user_satisfaction": 0.1
        }
    },
    
    # Prediction system configuration
    "prediction": {
        "enabled": True,
        "prediction_horizon": 3600,    # Prediction horizon (seconds)
        "min_data_points": 10,         # Minimum data points
        "confidence_threshold": 0.6,   # Prediction confidence threshold
        "update_interval": 300,        # Prediction update interval (seconds)
        
        # Prediction model configuration
        "models": {
            "linear_trend": {"weight": 0.3, "enabled": True},
            "moving_average": {"weight": 0.2, "enabled": True},
            "exponential_smoothing": {"weight": 0.3, "enabled": True},
            "pattern_matching": {"weight": 0.2, "enabled": True}
        }
    }
}


# Scenario-specific configurations
SCENARIO_CONFIGS = {
    # Controversial content handling
    "controversial_content": {
        "monitoring_mode": MonitoringMode.INTELLIGENT,
        "feedback_sensitivity": FeedbackSensitivity.HIGH,
        "iteration_strategy": IterationStrategy.CONSERVATIVE,
        "special_metrics": ["controversy_level", "sentiment_polarization"],
        "alert_thresholds": {
            "controversy_level": {"warning": 0.6, "critical": 0.8}
        }
    },
    
    # Viral content handling
    "viral_content": {
        "monitoring_mode": MonitoringMode.ADAPTIVE,
        "feedback_sensitivity": FeedbackSensitivity.MEDIUM,
        "iteration_strategy": IterationStrategy.BALANCED,
        "special_metrics": ["viral_potential", "spread_velocity"],
        "prediction_focus": ["reach", "engagement_rate"]
    },
    
    # Crisis management handling
    "crisis_management": {
        "monitoring_mode": MonitoringMode.INTELLIGENT,
        "feedback_sensitivity": FeedbackSensitivity.HIGH,
        "iteration_strategy": IterationStrategy.AGGRESSIVE,
        "special_metrics": ["crisis_severity", "reputation_impact"],
        "emergency_thresholds": {
            "crisis_severity": 0.8,
            "reputation_impact": 0.7
        }
    },
    
    # Routine content management
    "routine_content": {
        "monitoring_mode": MonitoringMode.ACTIVE,
        "feedback_sensitivity": FeedbackSensitivity.LOW,
        "iteration_strategy": IterationStrategy.CONSERVATIVE,
        "special_metrics": ["engagement_consistency"],
        "optimization_focus": ["efficiency", "cost_effectiveness"]
    }
}


# Experimental configurations
EXPERIMENTAL_CONFIG = {
    # A/B testing configuration
    "ab_testing": {
        "enabled": False,
        "test_duration": 3600,  # Test duration (seconds)
        "sample_size": 1000,    # Sample size
        "significance_level": 0.05,
        "test_metrics": ["engagement_rate", "sentiment_score"]
    },
    
    # Reinforcement learning configuration
    "reinforcement_learning": {
        "enabled": False,
        "exploration_rate": 0.1,
        "discount_factor": 0.9,
        "learning_episodes": 1000
    },
    
    # Multi-objective optimization
    "multi_objective": {
        "enabled": False,
        "objectives": {
            "maximize_engagement": 0.4,
            "minimize_controversy": 0.3,
            "optimize_sentiment": 0.3
        }
    }
}


def get_config(scenario: str = "default") -> Dict[str, Any]:
    """Retrieve the configuration for the given scenario."""
    if scenario == "default":
        return BASE_CONFIG.copy()
    elif scenario in SCENARIO_CONFIGS:
        config = BASE_CONFIG.copy()
        scenario_config = SCENARIO_CONFIGS[scenario]
        
        # Merge scenario-specific configuration
        for key, value in scenario_config.items():
            if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value
        
        return config
    else:
        raise ValueError(f"Unknown scenario: {scenario}")


def get_experimental_config() -> Dict[str, Any]:
    """Retrieve experimental configuration."""
    return EXPERIMENTAL_CONFIG.copy()


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate that the configuration is complete and consistent."""
    required_sections = ["monitoring", "feedback", "iteration", "learning"]
    
    for section in required_sections:
        if section not in config:
            return False
    
    # Validate numeric ranges
    if config["feedback"]["confidence_threshold"] < 0 or config["feedback"]["confidence_threshold"] > 1:
        return False
    
    if config["learning"]["learning_rate"] < 0 or config["learning"]["learning_rate"] > 1:
        return False
    
    return True


# Configuration examples
if __name__ == "__main__":
    # Test configuration retrieval
    default_config = get_config()
    print("Default configuration loaded successfully")
    
    controversial_config = get_config("controversial_content")
    print("Controversial content configuration loaded successfully")
    
    experimental_config = get_experimental_config()
    print("Experimental configuration loaded successfully")

    # Validate configuration
    is_valid = validate_config(default_config)
    print(f"Configuration validation result: {'pass' if is_valid else 'fail'}")
