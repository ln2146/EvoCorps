"""
EvoCorps Active Defense System - Evolution and Strategy Adjustment Mechanism
Dynamically adjusts agent ratios and speaking styles based on feedback
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from .defense_agent_types import (
    DefenseAgentType,
    DefenseAgentConfig,
    DEFENSE_AGENT_CONFIGS,
    AgentAllocationStrategy,
    EvolutionParameters,
    get_recommended_agent_type,
    calculate_agent_effectiveness
)


@dataclass
class FeedbackMetrics:
    """反馈指标 - 增强版"""
    likes_received: int = 0
    sentiment_improvement: float = 0.0  # 情绪改善值 (-1 to 1)
    engagement_rate: float = 0.0        # 互动率
    polarization_reduction: float = 0.0 # 极化指数降低
    # 新增指标
    niche_occupancy: float = 0.5        # 生态位占有率 (0-1)，己方观点在讨论中的占比
    algorithm_gini_change: float = 0.0  # 算法倾斜基尼系数变化 (-1 to 1)，负值表示更公平
    our_posts_avg_likes: float = 0.0    # 己方帖子平均点赞数
    enemy_posts_avg_likes: float = 0.0  # 对方帖子平均点赞数
    discourse_dominance: float = 0.5    # 话语权占比 (0-1)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentPerformance:
    """Single Agent Performance Record"""
    agent_type: DefenseAgentType
    total_actions: int = 0
    successful_actions: int = 0
    total_likes: int = 0
    total_sentiment_improvement: float = 0.0
    feedback_history: List[FeedbackMetrics] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_actions == 0:
            return 0.5
        return self.successful_actions / self.total_actions
    
    @property
    def average_sentiment_improvement(self) -> float:
        if len(self.feedback_history) == 0:
            return 0.0
        return sum(f.sentiment_improvement for f in self.feedback_history) / len(self.feedback_history)


class EvolutionEngine:
    """Evolution Engine - Dynamically adjusts agent ratios and speaking styles"""
    
    def __init__(self, params: Optional[EvolutionParameters] = None):
        self.params = params or EvolutionParameters()
        self.allocation_strategy = AgentAllocationStrategy()
        self.performance_records: Dict[DefenseAgentType, AgentPerformance] = {
            agent_type: AgentPerformance(agent_type=agent_type)
            for agent_type in DefenseAgentType
        }
        self.adjustment_history: List[Dict[str, Any]] = []
    
    def record_feedback(
        self,
        agent_type: DefenseAgentType,
        metrics: FeedbackMetrics
    ):
        """Record feedback"""
        performance = self.performance_records[agent_type]
        performance.total_actions += 1
        performance.total_likes += metrics.likes_received
        performance.total_sentiment_improvement += metrics.sentiment_improvement
        performance.feedback_history.append(metrics)
        
        # Determine if successful
        success_score = (
            min(metrics.likes_received / self.params.max_likes_normalization, 1.0) * self.params.like_weight +
            (metrics.sentiment_improvement + 1) / 2 * self.params.sentiment_weight +
            metrics.engagement_rate * self.params.engagement_weight
        )
        if success_score >= self.params.success_threshold:
            performance.successful_actions += 1
    
    def analyze_performance(self) -> Dict[DefenseAgentType, float]:
        """Analyze performance of each agent type, return adjustment coefficients"""
        adjustments = {}
        
        for agent_type, performance in self.performance_records.items():
            if performance.total_actions < 5:
                adjustments[agent_type] = 0.0
                continue
            
            # Calculate composite performance score
            success_rate = performance.success_rate
            avg_sentiment = performance.average_sentiment_improvement
            
            # Calculate adjustment based on performance
            if success_rate >= self.params.success_threshold:
                adjustment = min(self.params.max_adjustment, 
                               self.params.learning_rate * success_rate)
            elif success_rate <= self.params.failure_threshold:
                adjustment = -min(self.params.max_adjustment,
                                self.params.learning_rate * (1 - success_rate))
            else:
                adjustment = 0.0
            
            # Consider sentiment improvement
            if avg_sentiment > 0.1:
                adjustment += self.params.learning_rate * 0.5
            elif avg_sentiment < -0.1:
                adjustment -= self.params.learning_rate * 0.5
            
            adjustments[agent_type] = max(-self.params.max_adjustment,
                                         min(self.params.max_adjustment, adjustment))
        
        return adjustments
    
    def analyze_advanced_metrics(self, metrics: FeedbackMetrics) -> Dict[str, Any]:
        """
        分析高级指标并生成调整建议
        
        基于以下指标动态调整：
        1. 己方帖子点赞数 vs 对方帖子点赞数
        2. 生态位占有率（己方观点在讨论中的占比）
        3. 算法倾斜基尼系数变化
        4. 话语权占比
        """
        analysis = {
            "likes_ratio": 0.5,
            "niche_status": "balanced",
            "algorithm_fairness": "neutral",
            "discourse_status": "balanced",
            "recommended_adjustments": {}
        }
        
        # 1. 点赞比率分析
        if metrics.enemy_posts_avg_likes > 0:
            likes_ratio = metrics.our_posts_avg_likes / metrics.enemy_posts_avg_likes
            analysis["likes_ratio"] = likes_ratio
            
            if likes_ratio < 0.5:
                # 己方点赞明显落后，需要增强影响力
                analysis["recommended_adjustments"]["amplifier"] = 0.1  # 增加扩音者
                analysis["recommended_adjustments"]["empath"] = 0.05   # 增加共情者
            elif likes_ratio > 2.0:
                # 己方点赞领先，可以转向事实核查
                analysis["recommended_adjustments"]["fact_checker"] = 0.05
        
        # 2. 生态位占有率分析
        if metrics.niche_occupancy < 0.3:
            # 生态位被挤压，需要快速填充
            analysis["niche_status"] = "threatened"
            analysis["recommended_adjustments"]["niche_filler"] = 0.15
            analysis["recommended_adjustments"]["amplifier"] = 0.05
        elif metrics.niche_occupancy > 0.7:
            # 生态位占优，可以转向深度影响
            analysis["niche_status"] = "dominant"
            analysis["recommended_adjustments"]["fact_checker"] = 0.1
            analysis["recommended_adjustments"]["empath"] = 0.05
        
        # 3. 算法倾斜基尼系数分析
        if metrics.algorithm_gini_change > 0.1:
            # 算法更加倾斜，需要多元化策略
            analysis["algorithm_fairness"] = "more_biased"
            analysis["recommended_adjustments"]["niche_filler"] = 0.1  # 填充更多生态位
        elif metrics.algorithm_gini_change < -0.1:
            # 算法更公平，可以集中力量
            analysis["algorithm_fairness"] = "more_fair"
            analysis["recommended_adjustments"]["amplifier"] = 0.1  # 集中扩音
        
        # 4. 话语权占比分析
        if metrics.discourse_dominance < 0.4:
            # 话语权不足，需要全面增强
            analysis["discourse_status"] = "weak"
            analysis["recommended_adjustments"]["amplifier"] = 0.1
            analysis["recommended_adjustments"]["fact_checker"] = 0.05
        elif metrics.discourse_dominance > 0.6:
            # 话语权占优，可以维持或微调
            analysis["discourse_status"] = "strong"
        
        return analysis
    
    def evolve_with_advanced_metrics(
        self,
        metrics: FeedbackMetrics,
        context: Dict[str, Any] = None
    ) -> AgentAllocationStrategy:
        """
        基于高级指标的进化策略
        
        综合考虑：
        - 基础性能指标（成功率、情绪改善）
        - 高级指标（点赞比、生态位、算法倾斜、话语权）
        - 上下文信息（愤怒水平、虚假信息风险等）
        """
        # 1. 获取基础性能调整
        base_adjustments = self.analyze_performance()
        
        # 2. 分析高级指标
        advanced_analysis = self.analyze_advanced_metrics(metrics)
        
        # 3. 合并调整建议
        final_adjustments = dict(base_adjustments)
        
        for agent_type_str, adjustment in advanced_analysis.get("recommended_adjustments", {}).items():
            # 转换字符串到枚举
            type_mapping = {
                "empath": DefenseAgentType.EMPATH,
                "fact_checker": DefenseAgentType.FACT_CHECKER,
                "amplifier": DefenseAgentType.AMPLIFIER,
                "niche_filler": DefenseAgentType.NICHE_FILLER
            }
            agent_type = type_mapping.get(agent_type_str)
            if agent_type and agent_type in final_adjustments:
                final_adjustments[agent_type] += adjustment
        
        # 4. 考虑上下文信息
        if context:
            anger_level = context.get("anger_level", 0.5)
            misinformation_risk = context.get("misinformation_risk", 0.5)
            viral_potential = context.get("viral_potential", 0.5)
            discussion_vacuum = context.get("discussion_vacuum", 0.5)
            
            # 高愤怒 → 增加共情者
            if anger_level > 0.7:
                final_adjustments[DefenseAgentType.EMPATH] += 0.1
            
            # 高虚假信息风险 → 增加事实核查者
            if misinformation_risk > 0.6:
                final_adjustments[DefenseAgentType.FACT_CHECKER] += 0.1
            
            # 高病毒传播潜力 → 增加扩音者
            if viral_potential > 0.7:
                final_adjustments[DefenseAgentType.AMPLIFIER] += 0.1
            
            # 高讨论真空 → 增加空位填充者
            if discussion_vacuum > 0.6:
                final_adjustments[DefenseAgentType.NICHE_FILLER] += 0.1
        
        # 5. 应用调整
        new_ratios = {
            DefenseAgentType.EMPATH: self.allocation_strategy.empath_ratio,
            DefenseAgentType.FACT_CHECKER: self.allocation_strategy.fact_checker_ratio,
            DefenseAgentType.AMPLIFIER: self.allocation_strategy.amplifier_ratio,
            DefenseAgentType.NICHE_FILLER: self.allocation_strategy.niche_filler_ratio
        }
        
        for agent_type, adjustment in final_adjustments.items():
            new_ratios[agent_type] = max(0.1, min(0.5, 
                new_ratios[agent_type] + adjustment))
        
        # 6. 归一化
        total = sum(new_ratios.values())
        new_ratios = {k: v / total for k, v in new_ratios.items()}
        
        # 7. 更新策略
        self.allocation_strategy.empath_ratio = new_ratios[DefenseAgentType.EMPATH]
        self.allocation_strategy.fact_checker_ratio = new_ratios[DefenseAgentType.FACT_CHECKER]
        self.allocation_strategy.amplifier_ratio = new_ratios[DefenseAgentType.AMPLIFIER]
        self.allocation_strategy.niche_filler_ratio = new_ratios[DefenseAgentType.NICHE_FILLER]
        
        # 8. 记录调整历史
        self.adjustment_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "advanced_evolution",
            "base_adjustments": {k.value: v for k, v in base_adjustments.items()},
            "advanced_analysis": advanced_analysis,
            "final_ratios": {k.value: v for k, v in new_ratios.items()},
            "input_metrics": {
                "niche_occupancy": metrics.niche_occupancy,
                "algorithm_gini_change": metrics.algorithm_gini_change,
                "discourse_dominance": metrics.discourse_dominance,
                "likes_ratio": metrics.our_posts_avg_likes / max(metrics.enemy_posts_avg_likes, 1)
            }
        })
        
        return self.allocation_strategy
    
    def evolve_strategy(self) -> AgentAllocationStrategy:
        """Evolve strategy based on performance"""
        adjustments = self.analyze_performance()
        
        # Apply adjustments
        new_ratios = {
            DefenseAgentType.EMPATH: self.allocation_strategy.empath_ratio,
            DefenseAgentType.FACT_CHECKER: self.allocation_strategy.fact_checker_ratio,
            DefenseAgentType.AMPLIFIER: self.allocation_strategy.amplifier_ratio,
            DefenseAgentType.NICHE_FILLER: self.allocation_strategy.niche_filler_ratio
        }
        
        for agent_type, adjustment in adjustments.items():
            new_ratios[agent_type] = max(0.1, min(0.5, 
                new_ratios[agent_type] + adjustment))
        
        # Normalize
        total = sum(new_ratios.values())
        new_ratios = {k: v / total for k, v in new_ratios.items()}
        
        # Update strategy
        self.allocation_strategy.empath_ratio = new_ratios[DefenseAgentType.EMPATH]
        self.allocation_strategy.fact_checker_ratio = new_ratios[DefenseAgentType.FACT_CHECKER]
        self.allocation_strategy.amplifier_ratio = new_ratios[DefenseAgentType.AMPLIFIER]
        self.allocation_strategy.niche_filler_ratio = new_ratios[DefenseAgentType.NICHE_FILLER]
        
        # Record adjustment history
        self.adjustment_history.append({
            "timestamp": datetime.now().isoformat(),
            "adjustments": {k.value: v for k, v in adjustments.items()},
            "new_ratios": {k.value: v for k, v in new_ratios.items()}
        })
        
        return self.allocation_strategy
    
    def get_speaking_style_adjustment(
        self,
        agent_type: DefenseAgentType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get speaking style adjustment suggestions"""
        config = DEFENSE_AGENT_CONFIGS[agent_type]
        performance = self.performance_records[agent_type]
        
        style_adjustments = {
            "tone": "neutral",
            "formality": "medium",
            "emotional_intensity": "medium",
            "evidence_level": "medium"
        }
        
        # Adjust based on performance
        if performance.success_rate > 0.7:
            # Maintain current style
            pass
        elif performance.success_rate < 0.3:
            # Need adjustment
            anger_level = context.get("anger_level", 0.5)
            if anger_level > 0.6:
                style_adjustments["tone"] = "more_empathetic"
                style_adjustments["emotional_intensity"] = "higher"
            else:
                style_adjustments["evidence_level"] = "higher"
        
        return style_adjustments
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get status report"""
        return {
            "current_allocation": {
                "empath": self.allocation_strategy.empath_ratio,
                "fact_checker": self.allocation_strategy.fact_checker_ratio,
                "amplifier": self.allocation_strategy.amplifier_ratio,
                "niche_filler": self.allocation_strategy.niche_filler_ratio
            },
            "performance": {
                agent_type.value: {
                    "total_actions": perf.total_actions,
                    "success_rate": perf.success_rate,
                    "avg_sentiment_improvement": perf.average_sentiment_improvement
                }
                for agent_type, perf in self.performance_records.items()
            },
            "adjustment_count": len(self.adjustment_history)
        }


class DefenseCoordinator:
    """Defense Coordinator - Unified scheduling of all agent types"""
    
    def __init__(self):
        self.evolution_engine = EvolutionEngine()
        self.active_agents: Dict[str, DefenseAgentType] = {}
    
    def select_agent_for_situation(
        self,
        context: Dict[str, Any]
    ) -> DefenseAgentType:
        """Select the most suitable agent for a specific situation"""
        return get_recommended_agent_type(
            anger_level=context.get("anger_level", 0.5),
            misinformation_risk=context.get("misinformation_risk", 0.5),
            viral_potential=context.get("viral_potential", 0.5),
            discussion_vacuum=context.get("discussion_vacuum", 0.5)
        )
    
    def generate_response(
        self,
        agent_type: DefenseAgentType,
        context: Dict[str, Any]
    ) -> str:
        """Generate response"""
        config = DEFENSE_AGENT_CONFIGS[agent_type]
        style = self.evolution_engine.get_speaking_style_adjustment(agent_type, context)
        
        # Generate response based on config and style
        import random
        response = random.choice(config.sample_responses)
        
        return response
    
    def report_action_result(
        self,
        agent_type: DefenseAgentType,
        likes: int,
        sentiment_change: float,
        engagement: float
    ):
        """Report action result"""
        metrics = FeedbackMetrics(
            likes_received=likes,
            sentiment_improvement=sentiment_change,
            engagement_rate=engagement
        )
        self.evolution_engine.record_feedback(agent_type, metrics)
    
    def trigger_evolution(self) -> Dict[str, Any]:
        """Trigger evolution"""
        new_strategy = self.evolution_engine.evolve_strategy()
        return self.evolution_engine.get_status_report()