"""
EvoCorps Defense System Integration Module
Integrates the new defense agents with the existing opinion balance system
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Import existing opinion balance components
from .simple_coordination_system import SimpleCoordinationSystem, workflow_logger

# Import new defense system components
from .defense_agent_types import (
    DefenseAgentType,
    DefenseAgentConfig,
    DEFENSE_AGENT_CONFIGS,
    get_recommended_agent_type,
    calculate_agent_effectiveness
)

from .defense_evolution_system import (
    FeedbackMetrics,
    EvolutionEngine,
    DefenseCoordinator
)

from .defense_monitoring_center import (
    TopicData,
    AccountMetrics,
    DefenseMonitoringCenter,
    create_monitoring_center
)


class IntegratedDefenseSystem:
    """
    Integrated defense system that connects new defense agents
    with the existing opinion balance system
    """
    
    def __init__(self, coordination_system: SimpleCoordinationSystem):
        self.coordination_system = coordination_system
        self.defense_coordinator = DefenseCoordinator()
        self.monitoring_center = create_monitoring_center(top_n_topics=10)
        
        # Track integration status
        self.integration_active = False
        self.defense_actions_count = 0
        
        workflow_logger.info("🔗 IntegratedDefenseSystem initialized")
    
    def activate_integration(self):
        """Activate the integration between defense agents and opinion balance system"""
        self.integration_active = True
        workflow_logger.info("✅ Defense integration activated")
        workflow_logger.info("   - Defense agents will augment opinion balance responses")
        workflow_logger.info("   - Monitoring center will track effectiveness")
    
    def deactivate_integration(self):
        """Deactivate the integration"""
        self.integration_active = False
        workflow_logger.info("❌ Defense integration deactivated")
    
    async def enhance_workflow_response(
        self,
        original_content: str,
        analysis_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance the workflow response using defense agents
        
        Args:
            original_content: The original content being addressed
            analysis_result: Analysis from the analyst agent
            context: Current context including anger level, misinformation risk, etc.
        
        Returns:
            Enhanced response configuration
        """
        if not self.integration_active:
            return {"enhanced": False, "reason": "Integration not active"}
        
        try:
            # Extract context parameters
            anger_level = context.get("anger_level", 
                self._calculate_anger_from_analysis(analysis_result))
            misinformation_risk = context.get("misinformation_risk",
                self._calculate_misinformation_risk(analysis_result))
            viral_potential = context.get("viral_potential", 0.5)
            discussion_vacuum = context.get("discussion_vacuum", 0.3)
            
            # Get recommended defense agent type
            recommended_type = get_recommended_agent_type(
                anger_level=anger_level,
                misinformation_risk=misinformation_risk,
                viral_potential=viral_potential,
                discussion_vacuum=discussion_vacuum
            )
            
            # Get agent configuration
            agent_config = DEFENSE_AGENT_CONFIGS.get(recommended_type)
            
            if not agent_config:
                return {"enhanced": False, "reason": "No suitable agent configuration"}
            
            # Calculate expected effectiveness
            effectiveness = calculate_agent_effectiveness(recommended_type, context)
            
            # Generate enhanced instructions
            enhanced_instructions = self._generate_enhanced_instructions(
                agent_config, analysis_result, context
            )
            
            # Deploy agents based on current allocation
            agent_allocation = self.defense_coordinator.evolution_engine.allocation_strategy
            
            self.defense_actions_count += 1
            
            workflow_logger.info(f"🛡️ Defense enhancement applied")
            workflow_logger.info(f"   - Agent type: {recommended_type.value}")
            workflow_logger.info(f"   - Expected effectiveness: {effectiveness:.2f}")
            workflow_logger.info(f"   - Anger level: {anger_level:.2f}")
            workflow_logger.info(f"   - Misinformation risk: {misinformation_risk:.2f}")
            
            return {
                "enhanced": True,
                "defense_agent_type": recommended_type.value,
                "agent_config": {
                    "name": agent_config.name,
                    "primary_function": agent_config.primary_function,
                    "speaking_styles": agent_config.speaking_styles,
                    "sample_responses": agent_config.sample_responses
                },
                "effectiveness_score": effectiveness,
                "enhanced_instructions": enhanced_instructions,
                "agent_allocation": {
                    "empath": agent_allocation.empath_ratio,
                    "fact_checker": agent_allocation.fact_checker_ratio,
                    "amplifier": agent_allocation.amplifier_ratio,
                    "niche_filler": agent_allocation.niche_filler_ratio
                }
            }
            
        except Exception as e:
            workflow_logger.error(f"❌ Defense enhancement failed: {e}")
            return {"enhanced": False, "reason": str(e)}
    
    def _calculate_anger_from_analysis(self, analysis: Dict[str, Any]) -> float:
        """Calculate anger level from analysis result"""
        try:
            sentiment_score = analysis.get("sentiment_score", 0.5)
            extremism_level = analysis.get("extremism_level", 0)
            
            # Higher extremism and lower sentiment = higher anger
            anger = (extremism_level / 4.0) * 0.6 + (1 - sentiment_score) * 0.4
            return min(1.0, max(0.0, anger))
        except Exception as e:
            logger.warning(f"_calculate_anger_from_analysis failed: {e}")
            raise
    
    def _calculate_misinformation_risk(self, analysis: Dict[str, Any]) -> float:
        """Calculate misinformation risk from analysis"""
        try:
            # Check for factual claims and their verification status
            requires_intervention = analysis.get("requires_intervention", False)
            extremism_level = analysis.get("extremism_level", 0)
            
            risk = extremism_level / 4.0
            if requires_intervention:
                risk += 0.2
            
            return min(1.0, max(0.0, risk))
        except Exception as e:
            logger.warning(f"_calculate_misinformation_risk failed: {e}")
            raise
    
    def _generate_enhanced_instructions(
        self,
        agent_config: DefenseAgentConfig,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate enhanced instructions based on defense agent type"""
        
        base_instructions = {
            "tone": agent_config.speaking_styles[0] if agent_config.speaking_styles else "neutral",
            "target_audience": agent_config.target_audience,
            "key_points": []
        }
        
        agent_type = agent_config.agent_type
        
        if agent_type == DefenseAgentType.EMPATH:
            base_instructions["key_points"] = [
                "Acknowledge emotional concerns",
                "Validate feelings without agreeing with misinformation",
                "Guide toward constructive discussion"
            ]
            base_instructions["approach"] = "emotional_support"
            
        elif agent_type == DefenseAgentType.FACT_CHECKER:
            base_instructions["key_points"] = [
                "Provide evidence-based counterpoints",
                "Cite credible sources",
                "Avoid emotional language"
            ]
            base_instructions["approach"] = "evidence_based"
            
        elif agent_type == DefenseAgentType.AMPLIFIER:
            base_instructions["key_points"] = [
                "Use established credibility",
                "Provide authoritative perspective",
                "Amplify accurate information"
            ]
            base_instructions["approach"] = "authoritative"
            
        elif agent_type == DefenseAgentType.NICHE_FILLER:
            base_instructions["key_points"] = [
                "Introduce alternative topics",
                "Redirect attention constructively",
                "Fill discussion vacuum"
            ]
            base_instructions["approach"] = "topic_redirection"
        
        return base_instructions
    
    def record_defense_outcome(
        self,
        agent_type: DefenseAgentType,
        likes: int,
        sentiment_change: float,
        engagement: float
    ):
        """Record the outcome of a defense action for evolution"""
        self.defense_coordinator.report_action_result(
            agent_type=agent_type,
            likes=likes,
            sentiment_change=sentiment_change,
            engagement=engagement
        )
        
        workflow_logger.info(f"📊 Defense outcome recorded for {agent_type.value}")
        workflow_logger.info(f"   - Likes: {likes}")
        workflow_logger.info(f"   - Sentiment change: {sentiment_change:+.2f}")
        workflow_logger.info(f"   - Engagement: {engagement:.2f}")
    
    def update_monitoring_data(
        self,
        topic_data: Optional[TopicData] = None,
        account_metrics: Optional[AccountMetrics] = None
    ):
        """Update the monitoring center with new data"""
        if topic_data:
            self.monitoring_center.update_topic_data(topic_data)
        
        if account_metrics:
            self.monitoring_center.update_account_data(account_metrics)
    
    def get_defense_dashboard(self) -> Dict[str, Any]:
        """Get the integrated defense dashboard"""
        dashboard = self.monitoring_center.generate_dashboard()
        
        # Add defense-specific metrics
        dashboard["defense_metrics"] = {
            "integration_active": self.integration_active,
            "total_defense_actions": self.defense_actions_count,
            "evolution_status": self.defense_coordinator.evolution_engine.get_status_report()
        }
        
        return dashboard
    
    def trigger_evolution(self) -> Dict[str, Any]:
        """Trigger the evolution of defense strategies"""
        result = self.defense_coordinator.trigger_evolution()
        
        workflow_logger.info("🧬 Defense evolution triggered")
        workflow_logger.info(f"   - New allocation ratios:")
        workflow_logger.info(f"     - Empath: {result['current_allocation']['empath']:.2%}")
        workflow_logger.info(f"     - Fact Checker: {result['current_allocation']['fact_checker']:.2%}")
        workflow_logger.info(f"     - Amplifier: {result['current_allocation']['amplifier']:.2%}")
        workflow_logger.info(f"     - Niche Filler: {result['current_allocation']['niche_filler']:.2%}")
        
        return result
    
    def print_defense_summary(self):
        """Print a summary of the defense system status"""
        print("\n" + "="*60)
        print("    EvoCorps Integrated Defense System Summary")
        print("="*60)
        print(f"\nIntegration Status: {'ACTIVE ✅' if self.integration_active else 'INACTIVE ❌'}")
        print(f"Total Defense Actions: {self.defense_actions_count}")
        
        # Print monitoring center summary
        self.monitoring_center.print_dashboard_summary()
        
        # Print evolution status
        evolution_status = self.defense_coordinator.evolution_engine.get_status_report()
        print("\n--- Evolution Status ---")
        allocation = evolution_status.get("current_allocation", {})
        print(f"  Empath Ratio: {allocation.get('empath', 0):.2%}")
        print(f"  Fact Checker Ratio: {allocation.get('fact_checker', 0):.2%}")
        print(f"  Amplifier Ratio: {allocation.get('amplifier', 0):.2%}")
        print(f"  Niche Filler Ratio: {allocation.get('niche_filler', 0):.2%}")
        
        print("\n" + "="*60)


def create_integrated_defense_system(
    coordination_system: SimpleCoordinationSystem,
    auto_activate: bool = True
) -> IntegratedDefenseSystem:
    """
    Factory function to create an integrated defense system
    
    Args:
        coordination_system: The existing SimpleCoordinationSystem
        auto_activate: Whether to automatically activate the integration
    
    Returns:
        Configured IntegratedDefenseSystem instance
    """
    system = IntegratedDefenseSystem(coordination_system)
    
    if auto_activate:
        system.activate_integration()
    
    return system