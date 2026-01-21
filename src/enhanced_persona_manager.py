"""
Enhanced persona management system.
Supports deep persona modeling, intelligent selection, and adaptive learning.
"""

import json
import random
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from agents.agent_models import PersonaProfile

logger = logging.getLogger(__name__)


@dataclass
class PersonaSelectionCriteria:
    """Persona selection criteria."""
    target_sentiment: Optional[str] = None  # Target sentiment
    content_type: Optional[str] = None  # Content type
    audience_type: Optional[str] = None  # Audience type
    urgency_level: float = 0.5  # Urgency level (0-1)
    diversity_requirement: float = 0.7  # Diversity requirement (0-1)
    effectiveness_threshold: float = 0.6  # Effectiveness threshold (0-1)


@dataclass
class PersonaUsageRecord:
    """Persona usage record."""
    persona_id: str
    usage_timestamp: datetime
    context: Dict[str, Any]
    effectiveness_score: float
    feedback_metrics: Dict[str, float]


class EnhancedPersonaManager:
    """Enhanced persona manager."""
    
    def __init__(self, persona_data_path: str = "personas/"):
        self.persona_data_path = Path(persona_data_path)
        self.personas: Dict[str, PersonaProfile] = {}
        self.usage_records: List[PersonaUsageRecord] = []
        self.selection_history: List[Dict[str, Any]] = []
        
        # Configuration parameters
        self.config = {
            "diversity_weight": 0.3,
            "effectiveness_weight": 0.4,
            "freshness_weight": 0.2,
            "relevance_weight": 0.1,
            "learning_rate": 0.1,
            "min_usage_gap": timedelta(hours=1),  # Minimum usage gap
            "effectiveness_decay": 0.95  # Effectiveness decay rate
        }
        
        # Load persona data
        self._load_personas()
        
        # Initialize selection algorithms
        self._initialize_selection_algorithms()
    
    def _load_personas(self):
        """Load persona data."""
        try:
            # Load persona files of different types
            persona_files = [
                "positive_personas_database.json",
                "neutral_personas_database.json", 
                "negative_personas_database.json"
            ]
            
            for file_name in persona_files:
                file_path = self.persona_data_path / file_name
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._process_persona_data(data, file_name)
                        
            logger.info(f"✅ Loaded {len(self.personas)} persona profiles")
            
        except Exception as e:
            logger.error(f"❌ Persona data load failed: {e}")
            self._create_default_personas()
    
    def _process_persona_data(self, data: Dict, source_file: str):
        """Process persona data and convert to enhanced format."""
        personas_list = data.get('personas', [])
        
        for persona_data in personas_list:
            try:
                # Enhance persona data
                enhanced_persona = self._enhance_persona_data(persona_data, source_file)
                
                # Create PersonaProfile object
                persona_profile = PersonaProfile(**enhanced_persona)
                self.personas[persona_profile.persona_id] = persona_profile
                
            except Exception as e:
                logger.warning(f"⚠️ Persona data processing failed: {e}")
    
    def _enhance_persona_data(self, original_data: Dict, source_file: str) -> Dict:
        """Enhance raw persona data."""
        # Basic information
        enhanced = {
            "persona_id": original_data.get("id", f"persona_{random.randint(1000, 9999)}"),
            "persona_name": original_data.get("name", "Unknown"),
            "description": original_data.get("description", ""),
            "speaking_style": original_data.get("speaking_style", "casual"),
            "background": original_data.get("background", ""),
        }
        
        # Enhanced features
        enhanced.update({
            "personality_traits": self._extract_personality_traits(original_data),
            "values_system": self._generate_values_system(original_data, source_file),
            "behavioral_patterns": self._generate_behavioral_patterns(original_data),
            "language_habits": self._generate_language_habits(original_data),
            
            "sample_responses": original_data.get("sample_responses", []),
            "typical_topics": original_data.get("typical_topics", []),
            "preferred_content_types": self._infer_content_preferences(original_data),
            "emotional_triggers": self._identify_emotional_triggers(original_data),
            
            "activity_pattern": original_data.get("activity_pattern", {}),
            "interaction_style": self._determine_interaction_style(original_data),
            "influence_level": random.uniform(0.3, 0.9),
            "credibility_score": random.uniform(0.4, 0.95),
            
            "adaptation_rate": random.uniform(0.05, 0.2),
        })
        
        return enhanced
    
    def _extract_personality_traits(self, data: Dict) -> Dict[str, float]:
        """Extract personality traits."""
        traits = {
            "openness": random.uniform(0.2, 0.9),
            "conscientiousness": random.uniform(0.3, 0.9),
            "extraversion": random.uniform(0.2, 0.8),
            "agreeableness": random.uniform(0.3, 0.9),
            "neuroticism": random.uniform(0.1, 0.7),
            "assertiveness": random.uniform(0.2, 0.8),
            "empathy": random.uniform(0.3, 0.9),
            "analytical_thinking": random.uniform(0.2, 0.9)
        }
        
        # Adjust traits based on persona description
        description = data.get("description", "").lower()
        if "rational" in description or "logical" in description:
            traits["analytical_thinking"] = min(0.9, traits["analytical_thinking"] + 0.2)
        if "emotional" in description or "passionate" in description:
            traits["neuroticism"] = min(0.8, traits["neuroticism"] + 0.2)
            
        return traits
    
    def _generate_values_system(self, data: Dict, source_file: str) -> Dict[str, float]:
        """Generate a values system."""
        base_values = {
            "truth_seeking": 0.7,
            "fairness": 0.6,
            "compassion": 0.6,
            "achievement": 0.5,
            "tradition": 0.4,
            "innovation": 0.5,
            "security": 0.5,
            "freedom": 0.6
        }
        
        # Adjust values based on persona type
        if "positive" in source_file:
            base_values["compassion"] += 0.2
            base_values["fairness"] += 0.2
        elif "negative" in source_file:
            base_values["achievement"] += 0.2
            base_values["tradition"] += 0.1
        
        # Add random variation
        for key in base_values:
            base_values[key] = max(0.1, min(0.9, base_values[key] + random.uniform(-0.2, 0.2)))
            
        return base_values
    
    def _generate_behavioral_patterns(self, data: Dict) -> Dict[str, Any]:
        """Generate behavioral patterns."""
        return {
            "posting_frequency": random.choice(["low", "medium", "high"]),
            "response_speed": random.choice(["slow", "medium", "fast"]),
            "engagement_style": random.choice(["lurker", "commenter", "sharer", "creator"]),
            "controversy_tolerance": random.uniform(0.1, 0.9),
            "fact_checking_tendency": random.uniform(0.2, 0.9),
            "emotional_expression": random.choice(["reserved", "moderate", "expressive"])
        }
    
    def _generate_language_habits(self, data: Dict) -> Dict[str, Any]:
        """Generate language habits."""
        return {
            "formality_level": random.choice(["casual", "semi-formal", "formal"]),
            "emoji_usage": random.choice(["none", "minimal", "moderate", "heavy"]),
            "hashtag_usage": random.choice(["none", "minimal", "moderate", "heavy"]),
            "sentence_length": random.choice(["short", "medium", "long", "varied"]),
            "technical_vocabulary": random.uniform(0.1, 0.8),
            "slang_usage": random.uniform(0.0, 0.7)
        }
    
    def _infer_content_preferences(self, data: Dict) -> List[str]:
        """Infer content preferences."""
        all_types = ["news", "opinion", "personal", "educational", "entertainment", "debate"]
        return random.sample(all_types, random.randint(2, 4))
    
    def _identify_emotional_triggers(self, data: Dict) -> List[str]:
        """Identify emotional triggers."""
        triggers = ["injustice", "misinformation", "personal_attacks", "political_issues", 
                   "social_issues", "economic_concerns", "health_topics"]
        return random.sample(triggers, random.randint(1, 3))
    
    def _determine_interaction_style(self, data: Dict) -> str:
        """Determine interaction style."""
        styles = ["collaborative", "competitive", "supportive", "challenging", "neutral"]
        return random.choice(styles)
    
    def _create_default_personas(self):
        """Create default personas when loading fails."""
        logger.warning("⚠️ Creating default persona profiles")
        
        default_personas = [
            {
                "persona_id": "default_rational",
                "persona_name": "Rational analyst",
                "description": "A rational user focused on logic and facts",
                "speaking_style": "analytical",
                "background": "Well-educated, accustomed to critical thinking"
            },
            {
                "persona_id": "default_emotional", 
                "persona_name": "Emotional expresser",
                "description": "An expressive user with rich emotions",
                "speaking_style": "expressive",
                "background": "Values relationships and emotional communication"
            }
        ]
        
        for persona_data in default_personas:
            enhanced = self._enhance_persona_data(persona_data, "default")
            persona_profile = PersonaProfile(**enhanced)
            self.personas[persona_profile.persona_id] = persona_profile
    
    def _initialize_selection_algorithms(self):
        """Initialize selection algorithms."""
        self.selection_algorithms = {
            "weighted_random": self._weighted_random_selection,
            "effectiveness_based": self._effectiveness_based_selection,
            "diversity_optimized": self._diversity_optimized_selection,
            "context_aware": self._context_aware_selection
        }

    def select_optimal_persona(
        self,
        criteria: PersonaSelectionCriteria,
        algorithm: str = "context_aware",
        exclude_recent: bool = True
    ) -> Optional[PersonaProfile]:
        """Select the optimal persona."""
        try:
            # Filter available personas
            available_personas = self._filter_available_personas(criteria, exclude_recent)

            if not available_personas:
                logger.warning("⚠️ No available personas, using random selection")
                return random.choice(list(self.personas.values())) if self.personas else None

            # Select using the specified algorithm
            selection_func = self.selection_algorithms.get(algorithm, self._context_aware_selection)
            selected_persona = selection_func(available_personas, criteria)

            # Record selection history
            self._record_selection(selected_persona, criteria, algorithm)

            logger.info(f"🎭 Selected persona: {selected_persona.persona_name} (algorithm: {algorithm})")
            return selected_persona

        except Exception as e:
            logger.error(f"❌ Persona selection failed: {e}")
            return None

    def _filter_available_personas(
        self,
        criteria: PersonaSelectionCriteria,
        exclude_recent: bool
    ) -> List[PersonaProfile]:
        """Filter available personas."""
        available = []
        current_time = datetime.now()

        for persona in self.personas.values():
            # Check recent usage time
            if exclude_recent and persona.last_used:
                time_since_last_use = current_time - persona.last_used
                if time_since_last_use < self.config["min_usage_gap"]:
                    continue

            # Check effectiveness threshold
            if persona.effectiveness_scores:
                avg_effectiveness = np.mean(persona.effectiveness_scores[-5:])  # Average of last 5
                if avg_effectiveness < criteria.effectiveness_threshold:
                    continue

            available.append(persona)

        return available

    def _weighted_random_selection(
        self,
        personas: List[PersonaProfile],
        criteria: PersonaSelectionCriteria
    ) -> PersonaProfile:
        """Weighted random selection."""
        weights = []

        for persona in personas:
            weight = 1.0

            # Effectiveness weight
            if persona.effectiveness_scores:
                avg_effectiveness = np.mean(persona.effectiveness_scores[-3:])
                weight *= (1 + avg_effectiveness * self.config["effectiveness_weight"])

            # Freshness weight
            if persona.last_used:
                hours_since_use = (datetime.now() - persona.last_used).total_seconds() / 3600
                freshness_factor = min(1.0, hours_since_use / 24)  # Linear growth within 24 hours
                weight *= (1 + freshness_factor * self.config["freshness_weight"])

            weights.append(weight)

        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(personas)

        weights = [w / total_weight for w in weights]
        return np.random.choice(personas, p=weights)

    def _effectiveness_based_selection(
        self,
        personas: List[PersonaProfile],
        criteria: PersonaSelectionCriteria
    ) -> PersonaProfile:
        """Effectiveness-based selection."""
        scored_personas = []

        for persona in personas:
            score = 0.0

            # Historical effectiveness scores
            if persona.effectiveness_scores:
                recent_scores = persona.effectiveness_scores[-5:]
                avg_score = np.mean(recent_scores)
                score += avg_score * 0.6

                # Stability bonus
                if len(recent_scores) >= 3:
                    stability = 1.0 - np.std(recent_scores)
                    score += stability * 0.2
            else:
                score += 0.5  # Give new persona a medium score

            # Influence and credibility
            score += persona.influence_level * 0.1
            score += persona.credibility_score * 0.1

            scored_personas.append((persona, score))

        # Select the highest score
        scored_personas.sort(key=lambda x: x[1], reverse=True)
        return scored_personas[0][0]

    def _diversity_optimized_selection(
        self,
        personas: List[PersonaProfile],
        criteria: PersonaSelectionCriteria
    ) -> PersonaProfile:
        """Diversity-optimized selection."""
        # Analyze recently used persona traits
        recent_selections = self.selection_history[-10:]  # Last 10 selections
        used_traits = {}

        for selection in recent_selections:
            persona_id = selection.get("persona_id")
            if persona_id in self.personas:
                persona = self.personas[persona_id]
                for trait, value in persona.personality_traits.items():
                    used_traits[trait] = used_traits.get(trait, 0) + value

        # Select the persona with the largest trait differences
        best_persona = None
        max_diversity_score = -1

        for persona in personas:
            diversity_score = 0.0

            for trait, value in persona.personality_traits.items():
                used_value = used_traits.get(trait, 0)
                diversity_score += abs(value - used_value / len(recent_selections)) if recent_selections else value

            if diversity_score > max_diversity_score:
                max_diversity_score = diversity_score
                best_persona = persona

        return best_persona or random.choice(personas)

    def _context_aware_selection(
        self,
        personas: List[PersonaProfile],
        criteria: PersonaSelectionCriteria
    ) -> PersonaProfile:
        """Context-aware selection."""
        scored_personas = []

        for persona in personas:
            score = 0.0

            # Base effectiveness score
            if persona.effectiveness_scores:
                score += np.mean(persona.effectiveness_scores[-3:]) * 0.3
            else:
                score += 0.5

            # Content type match
            if criteria.content_type and criteria.content_type in persona.preferred_content_types:
                score += 0.2

            # Sentiment match
            if criteria.target_sentiment:
                sentiment_match = self._calculate_sentiment_match(persona, criteria.target_sentiment)
                score += sentiment_match * 0.2

            # Urgency adaptation
            urgency_adaptation = self._calculate_urgency_adaptation(persona, criteria.urgency_level)
            score += urgency_adaptation * 0.15

            # Diversity consideration
            diversity_bonus = self._calculate_diversity_bonus(persona, criteria.diversity_requirement)
            score += diversity_bonus * 0.15

            scored_personas.append((persona, score))

        # Select the highest score
        scored_personas.sort(key=lambda x: x[1], reverse=True)
        return scored_personas[0][0]

    def _calculate_sentiment_match(self, persona: PersonaProfile, target_sentiment: str) -> float:
        """Calculate sentiment match score."""
        sentiment_traits = {
            "positive": ["agreeableness", "extraversion"],
            "negative": ["neuroticism"],
            "neutral": ["conscientiousness", "analytical_thinking"]
        }

        relevant_traits = sentiment_traits.get(target_sentiment, [])
        if not relevant_traits:
            return 0.5

        match_score = np.mean([persona.personality_traits.get(trait, 0.5) for trait in relevant_traits])
        return match_score

    def _calculate_urgency_adaptation(self, persona: PersonaProfile, urgency_level: float) -> float:
        """Calculate urgency adaptability."""
        response_speed_map = {"fast": 0.9, "medium": 0.6, "slow": 0.3}
        speed_score = response_speed_map.get(persona.behavioral_patterns.get("response_speed", "medium"), 0.6)

        # Prefer fast responders in urgent situations
        adaptation = speed_score if urgency_level > 0.7 else (1.0 - speed_score)
        return adaptation

    def _calculate_diversity_bonus(self, persona: PersonaProfile, diversity_requirement: float) -> float:
        """Calculate diversity bonus."""
        # Check recent persona types in selections
        recent_types = []
        for selection in self.selection_history[-5:]:
            if selection.get("persona_id") in self.personas:
                recent_persona = self.personas[selection["persona_id"]]
                recent_types.append(recent_persona.interaction_style)

        # Reward if current type appears less often in recent selections
        current_type = persona.interaction_style
        type_frequency = recent_types.count(current_type) / len(recent_types) if recent_types else 0

        diversity_bonus = (1.0 - type_frequency) * diversity_requirement
        return diversity_bonus

    def _record_selection(
        self,
        persona: PersonaProfile,
        criteria: PersonaSelectionCriteria,
        algorithm: str
    ):
        """Record selection history."""
        selection_record = {
            "timestamp": datetime.now(),
            "persona_id": persona.persona_id,
            "persona_name": persona.persona_name,
            "algorithm": algorithm,
            "criteria": asdict(criteria)
        }

        self.selection_history.append(selection_record)

        # Update persona last used time
        persona.last_used = datetime.now()

        # Limit history record length
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-500:]

    def record_usage_feedback(
        self,
        persona_id: str,
        effectiveness_score: float,
        context: Dict[str, Any],
        feedback_metrics: Dict[str, float]
    ):
        """Record usage feedback."""
        if persona_id not in self.personas:
            logger.warning(f"⚠️ Persona {persona_id} does not exist")
            return

        persona = self.personas[persona_id]

        # Record effectiveness score
        persona.effectiveness_scores.append(effectiveness_score)

        # Limit history length
        if len(persona.effectiveness_scores) > 50:
            persona.effectiveness_scores = persona.effectiveness_scores[-30:]

        # Record usage entry
        usage_record = PersonaUsageRecord(
            persona_id=persona_id,
            usage_timestamp=datetime.now(),
            context=context,
            effectiveness_score=effectiveness_score,
            feedback_metrics=feedback_metrics
        )

        self.usage_records.append(usage_record)
        persona.usage_history.append(asdict(usage_record))

        # Adaptive learning
        self._adaptive_learning(persona, usage_record)

        logger.info(f"📊 Recorded usage feedback for {persona.persona_name}: {effectiveness_score:.2f}")

    def _adaptive_learning(self, persona: PersonaProfile, usage_record: PersonaUsageRecord):
        """Adaptive learning mechanism."""
        try:
            # Analyze successful patterns
            if usage_record.effectiveness_score > 0.7:
                self._learn_success_patterns(persona, usage_record)
            elif usage_record.effectiveness_score < 0.3:
                self._learn_failure_patterns(persona, usage_record)

            # Update persona traits
            self._update_persona_traits(persona, usage_record)

        except Exception as e:
            logger.error(f"❌ Adaptive learning failed: {e}")

    def _learn_success_patterns(self, persona: PersonaProfile, usage_record: PersonaUsageRecord):
        """Learn successful patterns."""
        context = usage_record.context

        # Record successful context features
        success_key = "successful_contexts"
        if success_key not in persona.learned_patterns:
            persona.learned_patterns[success_key] = []

        success_context = {
            "content_type": context.get("content_type"),
            "target_sentiment": context.get("target_sentiment"),
            "urgency_level": context.get("urgency_level", 0.5),
            "effectiveness": usage_record.effectiveness_score
        }

        persona.learned_patterns[success_key].append(success_context)

        # Limit record count
        if len(persona.learned_patterns[success_key]) > 20:
            persona.learned_patterns[success_key] = persona.learned_patterns[success_key][-15:]

    def _learn_failure_patterns(self, persona: PersonaProfile, usage_record: PersonaUsageRecord):
        """Learn failure patterns."""
        context = usage_record.context

        # Record failure context features
        failure_key = "failure_contexts"
        if failure_key not in persona.learned_patterns:
            persona.learned_patterns[failure_key] = []

        failure_context = {
            "content_type": context.get("content_type"),
            "target_sentiment": context.get("target_sentiment"),
            "urgency_level": context.get("urgency_level", 0.5),
            "effectiveness": usage_record.effectiveness_score
        }

        persona.learned_patterns[failure_key].append(failure_context)

        # Limit record count
        if len(persona.learned_patterns[failure_key]) > 10:
            persona.learned_patterns[failure_key] = persona.learned_patterns[failure_key][-8:]

    def _update_persona_traits(self, persona: PersonaProfile, usage_record: PersonaUsageRecord):
        """Update persona traits."""
        # Adjust traits based on feedback
        feedback_metrics = usage_record.feedback_metrics
        learning_rate = persona.adaptation_rate

        # Adjust influence level
        if "engagement_rate" in feedback_metrics:
            engagement_impact = (feedback_metrics["engagement_rate"] - 0.5) * learning_rate
            persona.influence_level = max(0.1, min(0.9, persona.influence_level + engagement_impact))

        # Adjust credibility score
        if "credibility_feedback" in feedback_metrics:
            credibility_impact = (feedback_metrics["credibility_feedback"] - 0.5) * learning_rate
            persona.credibility_score = max(0.1, min(0.9, persona.credibility_score + credibility_impact))

        # Adjust personality traits
        if usage_record.effectiveness_score > 0.7:
            # Slightly enhance traits on success
            for trait in ["agreeableness", "conscientiousness"]:
                if trait in persona.personality_traits:
                    adjustment = learning_rate * 0.1
                    persona.personality_traits[trait] = min(0.9, persona.personality_traits[trait] + adjustment)

    def get_persona_analytics(self, persona_id: str) -> Dict[str, Any]:
        """Get persona analytics data."""
        if persona_id not in self.personas:
            return {}

        persona = self.personas[persona_id]

        analytics = {
            "persona_info": {
                "id": persona.persona_id,
                "name": persona.persona_name,
                "description": persona.description
            },
            "performance_metrics": {
                "total_uses": len(persona.usage_history),
                "average_effectiveness": np.mean(persona.effectiveness_scores) if persona.effectiveness_scores else 0,
                "effectiveness_trend": self._calculate_effectiveness_trend(persona),
                "last_used": persona.last_used.isoformat() if persona.last_used else None
            },
            "characteristics": {
                "personality_traits": persona.personality_traits,
                "values_system": persona.values_system,
                "behavioral_patterns": persona.behavioral_patterns,
                "influence_level": persona.influence_level,
                "credibility_score": persona.credibility_score
            },
            "learned_patterns": persona.learned_patterns,
            "recommendations": self._generate_usage_recommendations(persona)
        }

        return analytics

    def _calculate_effectiveness_trend(self, persona: PersonaProfile) -> str:
        """Calculate effectiveness trend."""
        if len(persona.effectiveness_scores) < 3:
            return "insufficient_data"

        recent_scores = persona.effectiveness_scores[-5:]
        older_scores = persona.effectiveness_scores[-10:-5] if len(persona.effectiveness_scores) >= 10 else []

        if not older_scores:
            return "insufficient_data"

        recent_avg = np.mean(recent_scores)
        older_avg = np.mean(older_scores)

        if recent_avg > older_avg + 0.1:
            return "improving"
        elif recent_avg < older_avg - 0.1:
            return "declining"
        else:
            return "stable"

    def _generate_usage_recommendations(self, persona: PersonaProfile) -> List[str]:
        """Generate usage recommendations."""
        recommendations = []

        # Recommendations based on effectiveness score
        if persona.effectiveness_scores:
            avg_effectiveness = np.mean(persona.effectiveness_scores)
            if avg_effectiveness < 0.4:
                recommendations.append("Consider reducing usage frequency and analyze failure causes")
            elif avg_effectiveness > 0.8:
                recommendations.append("High-performing persona, increase usage frequency")

        # Recommendations based on learned patterns
        if "successful_contexts" in persona.learned_patterns:
            success_contexts = persona.learned_patterns["successful_contexts"]
            if success_contexts:
                common_types = {}
                for ctx in success_contexts:
                    content_type = ctx.get("content_type")
                    if content_type:
                        common_types[content_type] = common_types.get(content_type, 0) + 1

                if common_types:
                    best_type = max(common_types, key=common_types.get)
                    recommendations.append(f"Performs best in {best_type} content types")

        # Recommendations based on traits
        if persona.personality_traits.get("analytical_thinking", 0) > 0.7:
            recommendations.append("Suitable for content requiring logical analysis")

        if persona.personality_traits.get("empathy", 0) > 0.7:
            recommendations.append("Suitable for emotionally sensitive content")

        return recommendations

    def export_persona_data(self, output_path: str):
        """Export persona data."""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_personas": len(self.personas),
                "personas": {},
                "usage_statistics": {
                    "total_usage_records": len(self.usage_records),
                    "total_selections": len(self.selection_history)
                }
            }

            # Export persona data
            for persona_id, persona in self.personas.items():
                export_data["personas"][persona_id] = {
                    "basic_info": {
                        "persona_id": persona.persona_id,
                        "persona_name": persona.persona_name,
                        "description": persona.description,
                        "speaking_style": persona.speaking_style,
                        "background": persona.background
                    },
                    "enhanced_features": {
                        "personality_traits": persona.personality_traits,
                        "values_system": persona.values_system,
                        "behavioral_patterns": persona.behavioral_patterns,
                        "language_habits": persona.language_habits
                    },
                    "performance_data": {
                        "effectiveness_scores": persona.effectiveness_scores,
                        "usage_count": len(persona.usage_history),
                        "last_used": persona.last_used.isoformat() if persona.last_used else None,
                        "learned_patterns": persona.learned_patterns
                    }
                }

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Persona data exported to: {output_path}")

        except Exception as e:
            logger.error(f"❌ Persona data export failed: {e}")

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system statistics information."""
        stats = {
            "total_personas": len(self.personas),
            "total_usage_records": len(self.usage_records),
            "total_selections": len(self.selection_history),
            "average_effectiveness": 0.0,
            "top_performers": [],
            "usage_distribution": {}
        }

        # Calculate average effectiveness
        all_scores = []
        for persona in self.personas.values():
            all_scores.extend(persona.effectiveness_scores)

        if all_scores:
            stats["average_effectiveness"] = np.mean(all_scores)

        # Find top-performing personas
        persona_performance = []
        for persona in self.personas.values():
            if persona.effectiveness_scores:
                avg_score = np.mean(persona.effectiveness_scores)
                persona_performance.append((persona.persona_name, avg_score, len(persona.effectiveness_scores)))

        persona_performance.sort(key=lambda x: x[1], reverse=True)
        stats["top_performers"] = persona_performance[:5]

        # Usage distribution
        for record in self.usage_records:
            persona_name = self.personas.get(record.persona_id, {}).persona_name or "Unknown"
            stats["usage_distribution"][persona_name] = stats["usage_distribution"].get(persona_name, 0) + 1

        return stats
