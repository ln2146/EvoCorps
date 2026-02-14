"""
Intelligent learning system.
Implements a full action-outcome learning loop, auto-extracts successful patterns, and applies them to new scenarios.
"""

import json
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict

try:
    from .advanced_rag_system import AdvancedRAGSystem, HistoricalCase, StrategyPattern, RetrievalQuery, context_to_query
except ImportError:
    from advanced_rag_system import AdvancedRAGSystem, HistoricalCase, StrategyPattern, RetrievalQuery, context_to_query
logger = logging.getLogger(__name__)


@dataclass
class ActionOutcome:
    """Action outcome."""
    action_id: str
    timestamp: datetime
    context: Dict[str, Any]
    strategy_applied: Dict[str, Any]
    actions_executed: List[Dict[str, Any]]
    immediate_results: Dict[str, Any]
    long_term_effects: Dict[str, Any]
    effectiveness_metrics: Dict[str, float]
    success_indicators: Dict[str, bool]
    lessons_learned: List[str]
    failure_points: List[str]


@dataclass
class SuccessPattern:
    """Successful pattern."""
    pattern_id: str
    pattern_name: str
    description: str
    conditions: Dict[str, Any]
    key_actions: List[Dict[str, Any]]
    success_probability: float
    confidence_level: float
    supporting_cases: List[str]
    variations: List[Dict[str, Any]]
    last_validated: datetime


@dataclass
class LearningInsight:
    """Learning insight."""
    insight_id: str
    insight_type: str  # "pattern", "correlation", "causation", "optimization"
    description: str
    evidence: List[str]
    confidence_score: float
    actionable_recommendations: List[str]
    potential_impact: str
    validation_status: str


class IntelligentLearningSystem:
    """Intelligent learning system."""
    
    def __init__(self, data_path: str = "learning_data/"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        # Initialize RAG system
        self.rag_system = AdvancedRAGSystem(str(self.data_path / "rag"))

        # Data storage - initialize required attributes
        self.action_outcomes: Dict[str, ActionOutcome] = {}
        self.success_patterns: Dict[str, SuccessPattern] = {}
        self.learning_insights: Dict[str, LearningInsight] = {}

        # Configuration parameters
        self.config = {
            "success_threshold": 0.5,
            "min_cases_for_pattern": 3,
            "pattern_confidence_threshold": 0.6,
            "learning_rate": 0.1,
            "max_patterns": 100,
            "insight_generation_threshold": 5
        }

        # Database
        self.db_path = self.data_path / "learning_database.db"
    
    def _initialize_database(self):
        """Initialize the learning database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Action outcomes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_outcomes (
                    action_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    context TEXT,
                    strategy_applied TEXT,
                    actions_executed TEXT,
                    immediate_results TEXT,
                    long_term_effects TEXT,
                    effectiveness_metrics TEXT,
                    success_indicators TEXT,
                    lessons_learned TEXT,
                    failure_points TEXT
                )
            ''')

            # Success patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS success_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_name TEXT,
                    description TEXT,
                    conditions TEXT,
                    key_actions TEXT,
                    success_probability REAL,
                    confidence_level REAL,
                    supporting_cases TEXT,
                    variations TEXT,
                    last_validated TEXT
                )
            ''')

            # Learning insights table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_insights (
                    insight_id TEXT PRIMARY KEY,
                    insight_type TEXT,
                    description TEXT,
                    evidence TEXT,
                    confidence_score REAL,
                    actionable_recommendations TEXT,
                    potential_impact TEXT,
                    validation_status TEXT,
                    created_at TEXT
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("✅ Learning database initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Learning database initialization failed: {e}")

    def _load_all_data(self):
        """Load all data."""
        try:
            self._load_action_outcomes()
            self._load_success_patterns()
            self._load_learning_insights()
            logger.info("✅ All learning data loaded")
        except Exception as e:
            logger.error(f"❌ Data loading failed: {e}")

    def _load_success_patterns(self):
        """Load success patterns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM success_patterns")
            rows = cursor.fetchall()

            for row in rows:
                pattern = self._parse_pattern_row(row)
                if pattern:
                    self.success_patterns[pattern.pattern_id] = pattern

            conn.close()
            logger.info(f"✅ Loaded {len(self.success_patterns)} success patterns")

        except Exception as e:
            logger.warning(f"⚠️ Failed to load success patterns: {e}")

    def _load_learning_insights(self):
        """Load learning insights."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM learning_insights")
            rows = cursor.fetchall()

            for row in rows:
                insight = self._parse_insight_row(row)
                if insight:
                    self.learning_insights[insight.insight_id] = insight

            conn.close()
            logger.info(f"✅ Loaded {len(self.learning_insights)} learning insights")

        except Exception as e:
            logger.warning(f"⚠️ Failed to load learning insights: {e}")

    def _load_action_outcomes(self):
        """Load action outcome data only."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load action outcomes only
            cursor.execute("SELECT * FROM action_outcomes")
            for row in cursor.fetchall():
                outcome = self._parse_outcome_row(row)
                if outcome:
                    self.action_outcomes[outcome.action_id] = outcome
            
            conn.close()
            
            logger.info(f"✅ Loaded {len(self.action_outcomes)} action outcomes")
            
        except Exception as e:
            logger.error(f"❌ Action outcome data load failed: {e}")
    
    def _parse_outcome_row(self, row) -> Optional[ActionOutcome]:
        """Parse an action outcome row."""
        try:
            return ActionOutcome(
                action_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                context=json.loads(row[2]),
                strategy_applied=json.loads(row[3]),
                actions_executed=json.loads(row[4]),
                immediate_results=json.loads(row[5]),
                long_term_effects=json.loads(row[6]),
                effectiveness_metrics=json.loads(row[7]),
                success_indicators=json.loads(row[8]),
                lessons_learned=json.loads(row[9]),
                failure_points=json.loads(row[10])
            )
        except Exception as e:
            logger.warning(f"⚠️ Action outcome parsing failed: {e}")
            return None
    
    def _parse_pattern_row(self, row) -> Optional[SuccessPattern]:
        """Parse a success pattern row."""
        try:
            return SuccessPattern(
                pattern_id=row[0],
                pattern_name=row[1],
                description=row[2],
                conditions=json.loads(row[3]),
                key_actions=json.loads(row[4]),
                success_probability=row[5],
                confidence_level=row[6],
                supporting_cases=json.loads(row[7]),
                variations=json.loads(row[8]),
                last_validated=datetime.fromisoformat(row[9])
            )
        except Exception as e:
            logger.warning(f"⚠️ Success pattern parsing failed: {e}")
            return None
    
    def _parse_insight_row(self, row) -> Optional[LearningInsight]:
        """Parse a learning insight row."""
        try:
            return LearningInsight(
                insight_id=row[0],
                insight_type=row[1],
                description=row[2],
                evidence=json.loads(row[3]),
                confidence_score=row[4],
                actionable_recommendations=json.loads(row[5]),
                potential_impact=row[6],
                validation_status=row[7]
            )
        except Exception as e:
            logger.warning(f"⚠️ Learning insight parsing failed: {e}")
            return None
    
    def record_action_outcome(self, outcome: ActionOutcome):
        """Record an action outcome."""
        try:
            # Store in memory
            self.action_outcomes[outcome.action_id] = outcome
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO action_outcomes 
                (action_id, timestamp, context, strategy_applied, actions_executed,
                 immediate_results, long_term_effects, effectiveness_metrics, 
                 success_indicators, lessons_learned, failure_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                outcome.action_id,
                outcome.timestamp.isoformat(),
                json.dumps(outcome.context),
                json.dumps(outcome.strategy_applied),
                json.dumps(outcome.actions_executed),
                json.dumps(outcome.immediate_results),
                json.dumps(outcome.long_term_effects),
                json.dumps(outcome.effectiveness_metrics),
                json.dumps(outcome.success_indicators),
                json.dumps(outcome.lessons_learned),
                json.dumps(outcome.failure_points)
            ))
            
            conn.commit()
            conn.close()
            
            # Add to RAG system
            historical_case = self._convert_outcome_to_case(outcome)
            self.rag_system.add_historical_case(historical_case)
            
            # Trigger learning process
            self._trigger_learning_process(outcome)
            
            logger.info(f"✅ Recorded action outcome: {outcome.action_id}")
            
        except Exception as e:
            logger.error(f"❌ Recording action outcome failed: {e}")
    
    def _convert_outcome_to_case(self, outcome: ActionOutcome) -> HistoricalCase:
        """Convert an action outcome into a historical case."""
        # Calculate overall effectiveness score
        effectiveness_score = np.mean(list(outcome.effectiveness_metrics.values())) if outcome.effectiveness_metrics else 0.5
        
        # Extract tags
        tags = []
        if outcome.context.get("content_type"):
            tags.append(f"content_{outcome.context['content_type']}")
        if outcome.strategy_applied.get("strategy_type"):
            tags.append(f"strategy_{outcome.strategy_applied['strategy_type']}")
        
        return HistoricalCase(
            case_id=outcome.action_id,
            timestamp=outcome.timestamp,
            context=outcome.context,
            strategy_used=outcome.strategy_applied,
            actions_taken=outcome.actions_executed,
            results={
                "immediate": outcome.immediate_results,
                "long_term": outcome.long_term_effects,
                "metrics": outcome.effectiveness_metrics
            },
            effectiveness_score=effectiveness_score,
            lessons_learned=outcome.lessons_learned,
            tags=tags
        )

    def _trigger_learning_process(self, outcome: ActionOutcome):
        """Trigger the learning process."""
        try:
            # 1. Identify patterns
            self._identify_patterns(outcome)

            # 2. Update existing patterns
            self._update_existing_patterns(outcome)

            # 3. Generate new insights
            self._generate_insights(outcome)

            # 4. Validate pattern effectiveness
            self._validate_patterns()

        except Exception as e:
            logger.error(f"❌ Learning process trigger failed: {e}")

    def _identify_patterns(self, outcome: ActionOutcome):
        """Identify new successful patterns."""
        try:
            # Only process successful cases
            overall_success = self._calculate_overall_success(outcome)
            if overall_success < self.config["success_threshold"]:
                return

            # Find similar successful cases
            similar_cases = self._find_similar_successful_cases(outcome)

            if len(similar_cases) >= self.config["min_cases_for_pattern"]:
                # Extract common pattern
                pattern = self._extract_common_pattern(similar_cases + [outcome])

                if pattern and pattern.confidence_level >= self.config["pattern_confidence_threshold"]:
                    self._save_success_pattern(pattern)
                    logger.info(f"🎯 Identified new successful pattern: {pattern.pattern_name}")

        except Exception as e:
            logger.error(f"❌ Pattern identification failed: {e}")

    def _calculate_overall_success(self, outcome: ActionOutcome) -> float:
        """Calculate overall success score."""
        success_score = 0.0

        # Based on effectiveness metrics
        if outcome.effectiveness_metrics:
            success_score += np.mean(list(outcome.effectiveness_metrics.values())) * 0.6

        # Based on success indicators
        if outcome.success_indicators:
            success_rate = sum(outcome.success_indicators.values()) / len(outcome.success_indicators)
            success_score += success_rate * 0.4

        return min(1.0, success_score)

    def _find_similar_successful_cases(self, outcome: ActionOutcome) -> List[ActionOutcome]:
        """Find similar successful cases."""
        similar_cases = []

        for case_id, case_outcome in self.action_outcomes.items():
            if case_id == outcome.action_id:
                continue

            # Check if successful
            if self._calculate_overall_success(case_outcome) < self.config["success_threshold"]:
                continue

            # Calculate similarity
            similarity = self._calculate_outcome_similarity(outcome, case_outcome)

            if similarity > 0.7:  # similarity_score threshold
                similar_cases.append(case_outcome)

        return similar_cases

    def _calculate_outcome_similarity(self, outcome1: ActionOutcome, outcome2: ActionOutcome) -> float:
        """Calculate similarity score between two outcomes."""
        similarity = 0.0

        # Context similarity
        context_sim = self._calculate_dict_similarity(outcome1.context, outcome2.context)
        similarity += context_sim * 0.4

        # Strategy similarity
        strategy_sim = self._calculate_dict_similarity(outcome1.strategy_applied, outcome2.strategy_applied)
        similarity += strategy_sim * 0.3

        # Action similarity
        action_sim = self._calculate_action_similarity(outcome1.actions_executed, outcome2.actions_executed)
        similarity += action_sim * 0.3

        return similarity

    def _calculate_dict_similarity(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> float:
        """Calculate dictionary similarity score."""
        if not dict1 or not dict2:
            return 0.0

        common_keys = set(dict1.keys()) & set(dict2.keys())
        if not common_keys:
            return 0.0

        matches = 0
        for key in common_keys:
            if dict1[key] == dict2[key]:
                matches += 1

        return matches / len(common_keys)

    def _calculate_action_similarity(self, actions1: List[Dict[str, Any]], actions2: List[Dict[str, Any]]) -> float:
        """Calculate action sequence similarity score."""
        if not actions1 or not actions2:
            return 0.0

        # Simplified: compare action types
        types1 = [action.get("type", "") for action in actions1]
        types2 = [action.get("type", "") for action in actions2]

        common_types = set(types1) & set(types2)
        all_types = set(types1) | set(types2)

        return len(common_types) / len(all_types) if all_types else 0.0

    def _extract_common_pattern(self, outcomes: List[ActionOutcome]) -> Optional[SuccessPattern]:
        """Extract a common pattern from similar cases."""
        try:
            if len(outcomes) < self.config["min_cases_for_pattern"]:
                return None

            # Extract common conditions
            common_conditions = self._extract_common_conditions(outcomes)

            # Extract key actions
            key_actions = self._extract_key_actions(outcomes)

            # Calculate success probability
            success_probability = np.mean([self._calculate_overall_success(outcome) for outcome in outcomes])

            # Calculate confidence score
            confidence_level = self._calculate_pattern_confidence(outcomes, common_conditions, key_actions)

            if confidence_level < self.config["pattern_confidence_threshold"]:
                return None

            # Generate pattern ID and name
            pattern_id = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            pattern_name = self._generate_pattern_name(common_conditions, key_actions)

            return SuccessPattern(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                description=self._generate_pattern_description(common_conditions, key_actions),
                conditions=common_conditions,
                key_actions=key_actions,
                success_probability=success_probability,
                confidence_level=confidence_level,
                supporting_cases=[outcome.action_id for outcome in outcomes],
                variations=self._identify_pattern_variations(outcomes),
                last_validated=datetime.now()
            )

        except Exception as e:
            logger.error(f"❌ Pattern extraction failed: {e}")
            return None

    def _extract_common_conditions(self, outcomes: List[ActionOutcome]) -> Dict[str, Any]:
        """Extract common conditions."""
        common_conditions = {}

        # Count frequency of each condition
        condition_counts = defaultdict(lambda: defaultdict(int))

        for outcome in outcomes:
            for key, value in outcome.context.items():
                if isinstance(value, (str, int, float, bool)):
                    condition_counts[key][value] += 1

        # Select high-frequency conditions
        threshold = len(outcomes) * 0.7  # Conditions present in 70%+ of cases

        for key, value_counts in condition_counts.items():
            for value, count in value_counts.items():
                if count >= threshold:
                    common_conditions[key] = value
                    break

        return common_conditions

    def _extract_key_actions(self, outcomes: List[ActionOutcome]) -> List[Dict[str, Any]]:
        """Extract key actions."""
        action_counts = defaultdict(int)
        action_details = {}

        # Count action type frequency
        for outcome in outcomes:
            for action in outcome.actions_executed:
                action_type = action.get("type", "unknown")
                action_counts[action_type] += 1
                if action_type not in action_details:
                    action_details[action_type] = action

        # Select high-frequency actions
        threshold = len(outcomes) * 0.6  # Actions present in 60%+ of cases
        key_actions = []

        for action_type, count in action_counts.items():
            if count >= threshold:
                key_actions.append(action_details[action_type])

        return key_actions

    def _calculate_pattern_confidence(
        self,
        outcomes: List[ActionOutcome],
        conditions: Dict[str, Any],
        actions: List[Dict[str, Any]]
    ) -> float:
        """Calculate pattern confidence score."""
        confidence = 0.0

        # Based on case count
        case_count_factor = min(1.0, len(outcomes) / 10)  # Full score at 10 cases
        confidence += case_count_factor * 0.3

        # Based on success rate consistency
        success_scores = [self._calculate_overall_success(outcome) for outcome in outcomes]
        success_consistency = 1.0 - np.std(success_scores)
        confidence += success_consistency * 0.4

        # Based on condition coverage
        condition_coverage = len(conditions) / max(1, np.mean([len(outcome.context) for outcome in outcomes]))
        confidence += min(1.0, condition_coverage) * 0.2

        # Based on action consistency
        action_consistency = len(actions) / max(1, np.mean([len(outcome.actions_executed) for outcome in outcomes]))
        confidence += min(1.0, action_consistency) * 0.1

        return min(1.0, confidence)

    def _generate_pattern_name(self, conditions: Dict[str, Any], actions: List[Dict[str, Any]]) -> str:
        """Generate a pattern name."""
        # Simplified: name based on main conditions and actions
        condition_parts = []
        for key, value in list(conditions.items())[:2]:  # Take first two conditions
            condition_parts.append(f"{key}_{value}")

        action_parts = []
        for action in actions[:2]:  # Take first two actions
            action_type = action.get("type", "action")
            action_parts.append(action_type)

        name_parts = condition_parts + action_parts
        return "_".join(name_parts)[:50]  # Limit length

    def _generate_pattern_description(self, conditions: Dict[str, Any], actions: List[Dict[str, Any]]) -> str:
        """Generate a pattern description."""
        desc_parts = []

        if conditions:
            condition_desc = ", ".join([f"{k}={v}" for k, v in conditions.items()])
            desc_parts.append(f"Under conditions {condition_desc}")

        if actions:
            action_desc = ", ".join([action.get("type", "unknown_action") for action in actions])
            desc_parts.append(f"Execute {action_desc}")

        desc_parts.append("Typically achieves good results")

        return ", ".join(desc_parts)

    def _identify_pattern_variations(self, outcomes: List[ActionOutcome]) -> List[Dict[str, Any]]:
        """Identify pattern variations."""
        variations = []

        # Simplified: identify variations based on parameter combinations
        param_combinations = defaultdict(list)

        for outcome in outcomes:
            # Extract key parameters
            key_params = {}
            if "urgency_level" in outcome.context:
                key_params["urgency"] = outcome.context["urgency_level"]
            if "target_audience" in outcome.context:
                key_params["audience"] = outcome.context["target_audience"]

            param_key = json.dumps(key_params, sort_keys=True)
            param_combinations[param_key].append(outcome)

        # Create a variation for each parameter combination
        for param_key, group_outcomes in param_combinations.items():
            if len(group_outcomes) >= 2:  # At least 2 cases
                variation = {
                    "parameters": json.loads(param_key),
                    "case_count": len(group_outcomes),
                    "avg_success": np.mean([self._calculate_overall_success(o) for o in group_outcomes])
                }
                variations.append(variation)

        return variations

    def _save_success_pattern(self, pattern: SuccessPattern):
        """Save a successful pattern."""
        try:
            # Store in memory
            self.success_patterns[pattern.pattern_id] = pattern

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO success_patterns
                (pattern_id, pattern_name, description, conditions, key_actions,
                 success_probability, confidence_level, supporting_cases, variations, last_validated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id,
                pattern.pattern_name,
                pattern.description,
                json.dumps(pattern.conditions),
                json.dumps(pattern.key_actions),
                pattern.success_probability,
                pattern.confidence_level,
                json.dumps(pattern.supporting_cases),
                json.dumps(pattern.variations),
                pattern.last_validated.isoformat()
            ))

            conn.commit()
            conn.close()

            # Add to RAG system
            strategy_pattern = self._convert_pattern_to_strategy(pattern)
            self.rag_system.add_strategy_pattern(strategy_pattern)

            logger.info(f"✅ Saved success pattern: {pattern.pattern_name}")

        except Exception as e:
            logger.error(f"❌ Saving success pattern failed: {e}")

    def _convert_pattern_to_strategy(self, pattern: SuccessPattern) -> StrategyPattern:
        """Convert a success pattern to a strategy pattern."""
        return StrategyPattern(
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.pattern_name,
            description=pattern.description,
            conditions=pattern.conditions,
            actions=pattern.key_actions,
            success_rate=pattern.success_probability,
            usage_count=len(pattern.supporting_cases),
            last_updated=pattern.last_validated,
            variations=pattern.variations
        )

    def recommend_strategy(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Recommend a strategy based on context."""
        try:
            # Use context_to_query for retrieval
            
            # Convert context to retrieval query
            query = context_to_query(
                context=context,
                query_type="mixed",  # Retrieve cases and strategies
                similarity_threshold=0.5,
                max_results=5
            )
            
            # Execute retrieval
            results = self.rag_system.retrieve(query)
            
            if not results:
                logger.info("🔍 No relevant historical cases or strategies found")
                return None
            
            # Analyze retrieval results and recommend the best strategy
            best_result = max(results, key=lambda r: r.relevance_score)
            
            # Build recommended strategy
            recommended_strategy = {
                "strategy_type": best_result.item_type,
                "content": best_result.content,
                "confidence": best_result.relevance_score,
                "similarity": best_result.similarity_score,
                "metadata": best_result.metadata
            }
            
            logger.info(f"🎯 Recommended strategy: {best_result.item_type}, confidence: {best_result.relevance_score:.3f}")
            return recommended_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy recommendation failed: {e}")
            return None

    def _extract_actions_from_strategic_decision(self, strategic_decision: str) -> List[Dict[str, Any]]:
        """Extract recommended actions from strategic_decision."""
        try:
            if not strategic_decision:
                return []
            
            import json
            decision_data = json.loads(strategic_decision)
            
            actions = []
            
            # Extract actions from leader_instruction
            if "leader_instruction" in decision_data:
                leader_inst = decision_data["leader_instruction"]
                if "key_points" in leader_inst and isinstance(leader_inst["key_points"], list):
                    for i, point in enumerate(leader_inst["key_points"]):
                        actions.append({
                            "type": "leader_instruction",
                            "description": point,
                            "order": i + 1,
                            "tone": leader_inst.get("tone", "neutral"),
                            "target_audience": leader_inst.get("target_audience", "general")
                        })
            
            # Extract actions from amplifier_plan
            if "amplifier_plan" in decision_data:
                amplifier_plan = decision_data["amplifier_plan"]
                if "role_distribution" in amplifier_plan:
                    role_dist = amplifier_plan["role_distribution"]
                    for role, count in role_dist.items():
                        actions.append({
                            "type": "amplifier_agent",
                            "description": f"Deploy {count} {role} agents",
                            "role": role,
                            "count": count,
                            "timing_strategy": amplifier_plan.get("timing_strategy", "immediate")
                        })
                
                if "coordination_notes" in amplifier_plan:
                    actions.append({
                        "type": "coordination",
                        "description": amplifier_plan["coordination_notes"],
                        "category": "coordination"
                    })
            
            # Extract action from core_counter_argument
            if "core_counter_argument" in decision_data:
                actions.append({
                    "type": "counter_argument",
                    "description": decision_data["core_counter_argument"],
                    "category": "response"
                })
            
            return actions
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"⚠️ Failed to extract actions from strategic_decision: {e}")
            return []

    def _context_to_query_text(self, context: Dict[str, Any]) -> str:
        """
        Convert context to query text using core fields and f-strings for embedding-friendly text.
        Core fields: core_viewpoint, post_theme, threat_assessment, recommended_approach.
        """
        core_viewpoint = context.get("core_viewpoint", "")
        post_theme = context.get("post_theme", "")
        threat_assessment = context.get("threat_assessment", "")

        # Use a fixed format for embeddings
        query_text = (
            f"Core Viewpoint: {core_viewpoint}, "
            f"Post Theme: {post_theme}, "
            f"Threat Assessment: {threat_assessment}"
        )

        return query_text


    def _get_default_strategy(self) -> Dict[str, Any]:
        """Get the default strategy."""
        return {
            "strategy_id": "default_strategy",
            "strategy_name": "default_balance_strategy",
            "description": "Default strategy used when no learning patterns match",
            "recommended_actions": [
                {"type": "analyze_content", "description": "Analyze content sentiment and extremity"},
                {"type": "generate_balanced_response", "description": "Generate a balanced response"},
                {"type": "deploy_amplifier_agents", "description": "Deploy amplifier agents"}
            ],
            "expected_success_rate": 0.6,
            "confidence": 0.5,
            "source": "default"
        }

    def _update_existing_patterns(self, outcome: ActionOutcome):
        """Update existing patterns."""
        try:
            for pattern_id, pattern in self.success_patterns.items():
                # Check if outcome matches the pattern
                if self._outcome_matches_pattern(outcome, pattern):
                    # Update pattern statistics
                    self._update_pattern_statistics(pattern, outcome)

                    # Save updated pattern
                    self._save_success_pattern(pattern)

                    logger.info(f"🔄 Updated pattern: {pattern.pattern_name}")

        except Exception as e:
            logger.error(f"❌ Updating existing patterns failed: {e}")

    def _outcome_matches_pattern(self, outcome: ActionOutcome, pattern: SuccessPattern) -> bool:
        """Check whether an action outcome matches a pattern."""
        # Check condition match
        condition_match = True
        for key, expected_value in pattern.conditions.items():
            if key not in outcome.context or outcome.context[key] != expected_value:
                condition_match = False
                break

        if not condition_match:
            return False

        # Check action match
        outcome_action_types = {action.get("type") for action in outcome.actions_executed}
        pattern_action_types = {action.get("type") for action in pattern.key_actions}

        # At least 50% of pattern actions appear in the outcome
        overlap = len(outcome_action_types & pattern_action_types)
        return overlap >= len(pattern_action_types) * 0.5

    def _update_pattern_statistics(self, pattern: SuccessPattern, outcome: ActionOutcome):
        """Update pattern statistics information."""
        # Add supporting case
        if outcome.action_id not in pattern.supporting_cases:
            pattern.supporting_cases.append(outcome.action_id)

        # Recalculate success probability
        success_scores = []
        for case_id in pattern.supporting_cases:
            if case_id in self.action_outcomes:
                case_outcome = self.action_outcomes[case_id]
                success_scores.append(self._calculate_overall_success(case_outcome))

        if success_scores:
            pattern.success_probability = np.mean(success_scores)

        # Update confidence score based on more cases
        pattern.confidence_level = min(1.0, pattern.confidence_level + 0.05)

        # Update validation time
        pattern.last_validated = datetime.now()

    def _generate_insights(self, outcome: ActionOutcome):
        """Generate learning insights."""
        try:
            insights = []

            # 1. Analyze effectiveness correlations
            correlation_insight = self._analyze_effectiveness_correlations(outcome)
            if correlation_insight:
                insights.append(correlation_insight)

            # 2. Analyze failure points
            if outcome.failure_points:
                failure_insight = self._analyze_failure_points(outcome)
                if failure_insight:
                    insights.append(failure_insight)

            # 3. Optimization suggestions
            optimization_insight = self._generate_optimization_suggestions(outcome)
            if optimization_insight:
                insights.append(optimization_insight)

            # Save insights
            for insight in insights:
                self._save_learning_insight(insight)

        except Exception as e:
            logger.error(f"❌ Learning insight generation failed: {e}")

    def _analyze_effectiveness_correlations(self, outcome: ActionOutcome) -> Optional[LearningInsight]:
        """Analyze correlations between effectiveness metrics and context."""
        try:
            # Identify the best-performing metric
            if not outcome.effectiveness_metrics:
                return None

            best_metric = max(outcome.effectiveness_metrics.items(), key=lambda x: x[1])

            # Evaluate correlation with contextual factors
            correlations = []
            for key, value in outcome.context.items():
                if isinstance(value, (int, float)):
                # Simplified correlation calculation
                    correlation_strength = abs(value - 0.5) * best_metric[1]
                    if correlation_strength > 0.3:
                        correlations.append(f"{key} positively correlates with {best_metric[0]}")

            if correlations:
                insight_id = f"correlation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return LearningInsight(
                    insight_id=insight_id,
                    insight_type="correlation",
                    description=f"Identified contextual factors related to metric {best_metric[0]}",
                    evidence=correlations,
                    confidence_score=0.7,
                    actionable_recommendations=[
                        f"Focus on metric {best_metric[0]} in similar contexts",
                        "Optimize relevant contextual factors to improve outcomes"
                    ],
                    potential_impact="medium",
                    validation_status="pending"
                )

        except Exception as e:
            logger.warning(f"⚠️ Effectiveness correlation analysis failed: {e}")

        return None

    def _analyze_failure_points(self, outcome: ActionOutcome) -> Optional[LearningInsight]:
        """Analyze failure points in the action outcome."""
        if not outcome.failure_points:
            return None

        insight_id = f"failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return LearningInsight(
            insight_id=insight_id,
            insight_type="failure_analysis",
            description="Identify common failure patterns",
            evidence=outcome.failure_points,
            confidence_score=0.8,
            actionable_recommendations=[
                "Avoid these failure points in future actions",
                "Design targeted preventative measures"
            ],
            potential_impact="high",
            validation_status="validated"
        )

    def _generate_optimization_suggestions(self, outcome: ActionOutcome) -> Optional[LearningInsight]:
        """Generate optimization suggestions."""
        suggestions = []

        # Generate suggestions based on effectiveness metrics
        if outcome.effectiveness_metrics:
            low_metrics = [k for k, v in outcome.effectiveness_metrics.items() if v < 0.5]
            if low_metrics:
                suggestions.extend([f"Improve performance of {metric}" for metric in low_metrics])

        # Generate suggestions derived from lessons learned
        if outcome.lessons_learned:
            suggestions.extend([f"Application insight: {lesson}" for lesson in outcome.lessons_learned[:2]])

        if suggestions:
            insight_id = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return LearningInsight(
                insight_id=insight_id,
                insight_type="optimization",
                description="Strategy optimization recommendations",
                evidence=suggestions,
                confidence_score=0.6,
                actionable_recommendations=suggestions,
                potential_impact="medium",
                validation_status="pending"
            )

        return None

    def _save_learning_insight(self, insight: LearningInsight):
        """Save learning insight to memory and database."""
        try:
            # Store in memory
            self.learning_insights[insight.insight_id] = insight

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO learning_insights
                (insight_id, insight_type, description, evidence, confidence_score,
                 actionable_recommendations, potential_impact, validation_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                insight.insight_id,
                insight.insight_type,
                insight.description,
                json.dumps(insight.evidence),
                insight.confidence_score,
                json.dumps(insight.actionable_recommendations),
                insight.potential_impact,
                insight.validation_status,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            logger.info(f"💡 Saved learning insight: {insight.description}")

        except Exception as e:
            logger.error(f"❌ Saving learning insight failed: {e}")

    def _validate_patterns(self):
        """Validate pattern effectiveness."""
        try:
            current_time = datetime.now()

            for pattern_id, pattern in list(self.success_patterns.items()):
                # Check pattern age
                age_days = (current_time - pattern.last_validated).days

                if age_days > self.config["max_pattern_age_days"]:
                    # Pattern expired, revalidate or delete
                    if self._revalidate_pattern(pattern):
                        pattern.last_validated = current_time
                        self._save_success_pattern(pattern)
                        logger.info(f"✅ Revalidated pattern: {pattern.pattern_name}")
                    else:
                        # Delete invalid pattern
                        del self.success_patterns[pattern_id]
                        self._delete_pattern_from_db(pattern_id)
                        logger.info(f"🗑️ Deleted expired pattern: {pattern.pattern_name}")

        except Exception as e:
            logger.error(f"❌ Pattern validation failed: {e}")

    def _revalidate_pattern(self, pattern: SuccessPattern) -> bool:
        """Revalidate an existing pattern."""
        # Check the validity of supporting cases
        valid_cases = 0
        total_success = 0.0

        for case_id in pattern.supporting_cases:
            if case_id in self.action_outcomes:
                outcome = self.action_outcomes[case_id]
                success_score = self._calculate_overall_success(outcome)

                if success_score >= self.config["success_threshold"]:
                    valid_cases += 1
                    total_success += success_score

        if valid_cases < self.config["min_cases_for_pattern"]:
            return False

        # Update success probability
        pattern.success_probability = total_success / valid_cases

        # Apply decay to confidence level
        pattern.confidence_level *= self.config["pattern_decay_rate"]

        return pattern.confidence_level >= self.config["pattern_confidence_threshold"]

    def _delete_pattern_from_db(self, pattern_id: str):
        """Delete a pattern from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM success_patterns WHERE pattern_id = ?", (pattern_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to delete pattern: {e}")

    def get_learning_summary(self) -> Dict[str, Any]:
        """Gather summarized learning insights and statistics."""
        summary = {
            "data_statistics": {
                "total_outcomes": len(self.action_outcomes),
                "success_patterns": len(self.success_patterns),
                "learning_insights": len(self.learning_insights)
            },
            "performance_metrics": {
                "avg_success_rate": 0.0,
                "pattern_confidence_avg": 0.0,
                "learning_effectiveness": 0.0
            },
            "top_patterns": [],
            "recent_insights": [],
            "recommendations": []
        }

        # Calculate average success rate
        if self.action_outcomes:
            success_scores = [self._calculate_overall_success(outcome) for outcome in self.action_outcomes.values()]
            summary["performance_metrics"]["avg_success_rate"] = np.mean(success_scores)

        # Calculate average pattern confidence score
        if self.success_patterns:
            confidence_scores = [pattern.confidence_level for pattern in self.success_patterns.values()]
            summary["performance_metrics"]["pattern_confidence_avg"] = np.mean(confidence_scores)

        # Get top patterns
        top_patterns = sorted(
            self.success_patterns.values(),
            key=lambda p: p.success_probability * p.confidence_level,
            reverse=True
        )[:5]

        summary["top_patterns"] = [
            {
                "name": pattern.pattern_name,
                "success_rate": pattern.success_probability,
                "confidence": pattern.confidence_level,
                "usage_count": len(pattern.supporting_cases)
            }
            for pattern in top_patterns
        ]

        # Get recent insights
        recent_insights = sorted(
            self.learning_insights.values(),
            key=lambda i: i.insight_id,  # Sort by insight ID (includes timestamp)
            reverse=True
        )[:5]

        summary["recent_insights"] = [
            {
                "type": insight.insight_type,
                "description": insight.description,
                "confidence": insight.confidence_score,
                "impact": insight.potential_impact
            }
            for insight in recent_insights
        ]

        # Generate recommendations
        summary["recommendations"] = self._generate_system_recommendations()

        return summary

    def _generate_system_recommendations(self) -> List[str]:
        """Generate system-level recommendations."""
        recommendations = []

        # Recommendations based on data volume
        if len(self.action_outcomes) < 10:
            recommendations.append("Collect more action outcome data to improve learning")

        # Recommendations based on pattern quality
        if self.success_patterns:
            low_confidence_patterns = [p for p in self.success_patterns.values() if p.confidence_level < 0.7]
            if len(low_confidence_patterns) > len(self.success_patterns) * 0.3:
                recommendations.append("Several patterns have low confidence scores; gather more supporting cases")

        # Recommendations based on recent success rate
        if self.action_outcomes:
            recent_outcomes = sorted(self.action_outcomes.values(), key=lambda x: x.timestamp, reverse=True)[:10]
            recent_success_rate = np.mean([self._calculate_overall_success(o) for o in recent_outcomes])

            if recent_success_rate < 0.6:
                recommendations.append("Recent success rate is low; adjust strategy selection")

        return recommendations
