"""
Realtime evaluation system
Development of precise evaluation metrics covering sentiment shifts, engagement, influence, and other multi-dimensional measures
"""

import json
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict, deque
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class EffectMetrics:
    """Effect metrics"""
    metric_id: str
    timestamp: datetime
    action_id: str
    
    # Sentiment metrics
    sentiment_before: float  # -1 to 1
    sentiment_after: float
    sentiment_change: float
    emotional_intensity: float
    
    # Engagement metrics
    engagement_rate: float
    interaction_count: int
    share_rate: float
    comment_quality_score: float
    
    # Influence metrics
    reach_expansion: float
    influence_propagation: float
    opinion_shift_rate: float
    credibility_impact: float
    
    # Balance metrics
    discourse_balance: float
    extremism_reduction: float
    constructive_dialogue_rate: float
    
    # Composite metrics
    overall_effectiveness: float
    confidence_level: float


@dataclass
class EvaluationContext:
    """Evaluation context"""
    action_id: str
    content_id: str
    target_metrics: List[str]
    baseline_data: Dict[str, float]
    evaluation_window: timedelta
    sampling_interval: timedelta


class RealtimeEvaluationSystem:
    """Realtime evaluation system"""
    
    def __init__(self, data_path: str = "evaluation_data/"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        # Data storage
        self.metrics_history: Dict[str, List[EffectMetrics]] = defaultdict(list)
        self.active_evaluations: Dict[str, EvaluationContext] = {}
        self.baseline_cache: Dict[str, Dict[str, float]] = {}
        
        # Realtime data stream
        self.realtime_data_queue = deque(maxlen=1000)
        self.evaluation_threads: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        
        # database
        self.db_path = self.data_path / "evaluation_database.db"
        self._initialize_database()
        
        # Configuration parameters
        self.config = {
            "sentiment_analysis_model": "simple",  # scalable for a more complex model
            "engagement_weight": 0.25,
            "sentiment_weight": 0.25,
            "influence_weight": 0.25,
            "balance_weight": 0.25,
            "evaluation_interval": 30,  # seconds
            "baseline_window": 300,  # 5-minute baseline window
            "confidence_threshold": 0.7,
            "min_data_points": 5
        }
        
        # Load historical data
        self._load_evaluation_data()
    
    def _initialize_database(self):
        """Initialize evaluation database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Effect metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS effect_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    action_id TEXT,
                    sentiment_before REAL,
                    sentiment_after REAL,
                    sentiment_change REAL,
                    emotional_intensity REAL,
                    engagement_rate REAL,
                    interaction_count INTEGER,
                    share_rate REAL,
                    comment_quality_score REAL,
                    reach_expansion REAL,
                    influence_propagation REAL,
                    opinion_shift_rate REAL,
                    credibility_impact REAL,
                    discourse_balance REAL,
                    extremism_reduction REAL,
                    constructive_dialogue_rate REAL,
                    overall_effectiveness REAL,
                    confidence_level REAL
                )
            ''')
            
            # Baseline data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS baseline_data (
                    content_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    baseline_metrics TEXT,
                    context_info TEXT
                )
            ''')
            
            # Evaluation sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS evaluation_sessions (
                    session_id TEXT PRIMARY KEY,
                    action_id TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    target_metrics TEXT,
                    final_results TEXT,
                    session_status TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Evaluation database initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Evaluation database initialization failed: {e}")
    
    def _load_evaluation_data(self):
        """Load evaluation data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load effect metrics
            cursor.execute("SELECT * FROM effect_metrics ORDER BY timestamp DESC LIMIT 1000")
            for row in cursor.fetchall():
                metrics = self._parse_metrics_row(row)
                if metrics:
                    self.metrics_history[metrics.action_id].append(metrics)
            
            # Load baseline data
            cursor.execute("SELECT * FROM baseline_data")
            for row in cursor.fetchall():
                content_id, timestamp, baseline_metrics, context_info = row
                self.baseline_cache[content_id] = json.loads(baseline_metrics)
            
            conn.close()
            
            total_metrics = sum(len(metrics) for metrics in self.metrics_history.values())
            logger.info(f"✅ Loaded {total_metrics} effect metrics and {len(self.baseline_cache)} baseline records")
            
        except Exception as e:
            logger.error(f"❌ Evaluation data load failed: {e}")
    
    def _parse_metrics_row(self, row) -> Optional[EffectMetrics]:
        """Parse effect metrics data row"""
        try:
            return EffectMetrics(
                metric_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                action_id=row[2],
                sentiment_before=row[3],
                sentiment_after=row[4],
                sentiment_change=row[5],
                emotional_intensity=row[6],
                engagement_rate=row[7],
                interaction_count=row[8],
                share_rate=row[9],
                comment_quality_score=row[10],
                reach_expansion=row[11],
                influence_propagation=row[12],
                opinion_shift_rate=row[13],
                credibility_impact=row[14],
                discourse_balance=row[15],
                extremism_reduction=row[16],
                constructive_dialogue_rate=row[17],
                overall_effectiveness=row[18],
                confidence_level=row[19]
            )
        except Exception as e:
            logger.warning(f"⚠️ Effect metrics row parsing failed: {e}")
            return None
    
    def start_realtime_evaluation(
        self, 
        action_id: str, 
        content_id: str,
        target_metrics: List[str] = None,
        evaluation_duration: timedelta = timedelta(hours=1)
    ) -> str:
        """Start realtime evaluation"""
        try:
            # Set default target metrics
            if target_metrics is None:
                target_metrics = [
                    "sentiment_change", "engagement_rate", "influence_propagation", 
                    "discourse_balance", "overall_effectiveness"
                ]
            
            # Collect baseline data
            baseline_data = self._collect_baseline_data(content_id)
            
            # Create evaluation context
            evaluation_context = EvaluationContext(
                action_id=action_id,
                content_id=content_id,
                target_metrics=target_metrics,
                baseline_data=baseline_data,
                evaluation_window=evaluation_duration,
                sampling_interval=timedelta(seconds=self.config["evaluation_interval"])
            )
            
            self.active_evaluations[action_id] = evaluation_context
            
            # Start evaluation thread
            stop_flag = threading.Event()
            self.stop_flags[action_id] = stop_flag
            
            evaluation_thread = threading.Thread(
                target=self._evaluation_loop,
                args=(action_id, evaluation_context, stop_flag)
            )
            evaluation_thread.daemon = True
            evaluation_thread.start()
            
            self.evaluation_threads[action_id] = evaluation_thread
            
            logger.info(f"🚀 Started realtime evaluation: {action_id} (duration: {evaluation_duration})")
            return action_id
            
        except Exception as e:
            logger.error(f"❌ startrealtimeevaluatefailed: {e}")
            return ""
    
    def _collect_baseline_data(self, content_id: str) -> Dict[str, float]:
        """Collect baseline data"""
        try:
            # Check cache
            if content_id in self.baseline_cache:
                return self.baseline_cache[content_id]
            
            # Simulate baseline data collection (connect to real data sources in production)
            baseline_data = {
                "sentiment_score": np.random.uniform(-0.2, 0.2),
                "engagement_rate": np.random.uniform(0.1, 0.3),
                "interaction_count": np.random.randint(10, 100),
                "share_rate": np.random.uniform(0.05, 0.15),
                "comment_quality": np.random.uniform(0.4, 0.7),
                "reach_count": np.random.randint(100, 1000),
                "influence_score": np.random.uniform(0.3, 0.6),
                "discourse_balance": np.random.uniform(0.4, 0.6),
                "extremism_level": np.random.uniform(0.2, 0.8)
            }
            
            # Cache baseline data
            self.baseline_cache[content_id] = baseline_data
            
            # Save to database
            self._save_baseline_data(content_id, baseline_data)
            
            logger.info(f"📊 Collected baseline data: {content_id}")
            return baseline_data
            
        except Exception as e:
            logger.error(f"❌ Baseline data collection failed: {e}")
            return {}
    
    def _save_baseline_data(self, content_id: str, baseline_data: Dict[str, float]):
        """Save baseline data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO baseline_data 
                (content_id, timestamp, baseline_metrics, context_info)
                VALUES (?, ?, ?, ?)
            ''', (
                content_id,
                datetime.now().isoformat(),
                json.dumps(baseline_data),
                json.dumps({"collection_method": "simulated"})
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Baseline data save failed: {e}")
    
    def _evaluation_loop(self, action_id: str, context: EvaluationContext, stop_flag: threading.Event):
        """Evaluation main loop"""
        start_time = datetime.now()
        end_time = start_time + context.evaluation_window
        
        logger.info(f"🔄 Starting evaluation loop: {action_id}")
        
        while not stop_flag.is_set() and datetime.now() < end_time:
            try:
                # Collect current data
                current_data = self._collect_current_data(context.content_id)
                
                # Calculate effect metrics
                metrics = self._calculate_effect_metrics(action_id, context, current_data)
                
                if metrics:
                    # Save metrics
                    self._save_effect_metrics(metrics)
                    
                    # Append to historical records
                    self.metrics_history[action_id].append(metrics)
                    
                    # Check if alerts are needed
                    self._check_evaluation_alerts(metrics)
                
                # Wait for the next sampling interval
                time.sleep(context.sampling_interval.total_seconds())
                
            except Exception as e:
                logger.error(f"❌ Evaluation loop error: {e}")
                time.sleep(context.sampling_interval.total_seconds())
        
        # Generate final report
        final_report = self._generate_final_evaluation_report(action_id, context)
        logger.info(f"✅ evaluatecomplete: {action_id}")
        
        # clean
        self._cleanup_evaluation(action_id)
    
    def _collect_current_data(self, content_id: str) -> Dict[str, Any]:
        """Collect current data"""
        # Simulate realtime data collection (connect to real data sources in production)
        current_data = {
            "timestamp": datetime.now(),
            "sentiment_score": np.random.uniform(-1, 1),
            "engagement_rate": np.random.uniform(0.1, 0.8),
            "interaction_count": np.random.randint(5, 200),
            "share_rate": np.random.uniform(0.02, 0.3),
            "comment_quality": np.random.uniform(0.2, 0.9),
            "reach_count": np.random.randint(50, 2000),
            "influence_score": np.random.uniform(0.2, 0.9),
            "discourse_balance": np.random.uniform(0.2, 0.9),
            "extremism_level": np.random.uniform(0.1, 0.9),
            "constructive_comments": np.random.randint(0, 50),
            "total_comments": np.random.randint(10, 100)
        }
        
        return current_data

    def _calculate_effect_metrics(
        self,
        action_id: str,
        context: EvaluationContext,
        current_data: Dict[str, Any]
    ) -> Optional[EffectMetrics]:
        """Calculate effect metrics"""
        try:
            baseline = context.baseline_data

            # Sentiment metrics
            sentiment_before = baseline.get("sentiment_score", 0.0)
            sentiment_after = current_data.get("sentiment_score", 0.0)
            sentiment_change = sentiment_after - sentiment_before
            emotional_intensity = abs(sentiment_after)

            # Engagement metrics
            baseline_engagement = baseline.get("engagement_rate", 0.1)
            current_engagement = current_data.get("engagement_rate", 0.1)
            engagement_rate = current_engagement / max(baseline_engagement, 0.01)

            interaction_count = current_data.get("interaction_count", 0)

            baseline_share = baseline.get("share_rate", 0.05)
            current_share = current_data.get("share_rate", 0.05)
            share_rate = current_share / max(baseline_share, 0.01)

            comment_quality_score = current_data.get("comment_quality", 0.5)

            # Influence metrics
            baseline_reach = baseline.get("reach_count", 100)
            current_reach = current_data.get("reach_count", 100)
            reach_expansion = current_reach / max(baseline_reach, 1)

            baseline_influence = baseline.get("influence_score", 0.3)
            current_influence = current_data.get("influence_score", 0.3)
            influence_propagation = current_influence / max(baseline_influence, 0.1)

            # Opinion shift rate (based on sentiment change)
            opinion_shift_rate = min(1.0, abs(sentiment_change) * 2)

            # Credibility impact (based on comment quality)
            credibility_impact = comment_quality_score

            # Balance metrics
            discourse_balance = current_data.get("discourse_balance", 0.5)

            baseline_extremism = baseline.get("extremism_level", 0.5)
            current_extremism = current_data.get("extremism_level", 0.5)
            extremism_reduction = max(0, baseline_extremism - current_extremism)

            # Constructive dialogue rate
            constructive_comments = current_data.get("constructive_comments", 0)
            total_comments = current_data.get("total_comments", 1)
            constructive_dialogue_rate = constructive_comments / max(total_comments, 1)

            # Composite effectiveness score
            overall_effectiveness = self._calculate_overall_effectiveness(
                sentiment_change, engagement_rate, influence_propagation, discourse_balance
            )

            # confidence_scoreevaluate
            confidence_level = self._calculate_confidence_level(current_data, baseline)

            # Create effect metrics object
            metric_id = f"metrics_{action_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            return EffectMetrics(
                metric_id=metric_id,
                timestamp=datetime.now(),
                action_id=action_id,
                sentiment_before=sentiment_before,
                sentiment_after=sentiment_after,
                sentiment_change=sentiment_change,
                emotional_intensity=emotional_intensity,
                engagement_rate=engagement_rate,
                interaction_count=interaction_count,
                share_rate=share_rate,
                comment_quality_score=comment_quality_score,
                reach_expansion=reach_expansion,
                influence_propagation=influence_propagation,
                opinion_shift_rate=opinion_shift_rate,
                credibility_impact=credibility_impact,
                discourse_balance=discourse_balance,
                extremism_reduction=extremism_reduction,
                constructive_dialogue_rate=constructive_dialogue_rate,
                overall_effectiveness=overall_effectiveness,
                confidence_level=confidence_level
            )

        except Exception as e:
            logger.error(f"❌ Effect metrics calculation failed: {e}")
            return None

    def _calculate_overall_effectiveness(
        self,
        sentiment_change: float,
        engagement_rate: float,
        influence_propagation: float,
        discourse_balance: float
    ) -> float:
        """Calculate composite effectiveness score"""
        # Sentiment improvement score (positive change is good)
        sentiment_score = max(0, sentiment_change) if sentiment_change > 0 else max(0, -sentiment_change * 0.5)

        # Engagement score (moderate increase is good)
        engagement_score = min(1.0, max(0, engagement_rate - 1) * 0.5 + 0.5)

        # Influence score (greater propagation is good)
        influence_score = min(1.0, max(0, influence_propagation - 1) * 0.3 + 0.5)

        # Balance score (closer to 0.5 is best)
        balance_score = 1.0 - abs(discourse_balance - 0.5) * 2

        # Weighted aggregation
        overall = (
            sentiment_score * self.config["sentiment_weight"] +
            engagement_score * self.config["engagement_weight"] +
            influence_score * self.config["influence_weight"] +
            balance_score * self.config["balance_weight"]
        )

        return min(1.0, max(0.0, overall))

    def _calculate_confidence_level(self, current_data: Dict[str, Any], baseline: Dict[str, float]) -> float:
        """Calculate confidence score level"""
        confidence = 0.0

        # Based on data completeness
        expected_fields = ["sentiment_score", "engagement_rate", "interaction_count", "reach_count"]
        available_fields = sum(1 for field in expected_fields if field in current_data)
        data_completeness = available_fields / len(expected_fields)
        confidence += data_completeness * 0.4

        # Based on data change magnitude (big swings may be unreliable)
        changes = []
        for key in expected_fields:
            if key in current_data and key in baseline:
                current_val = current_data[key]
                baseline_val = baseline[key]
                if baseline_val != 0:
                    change_ratio = abs(current_val - baseline_val) / abs(baseline_val)
                    # Reward changes within a reasonable range (0-300%) with higher confidence
                    if change_ratio <= 3.0:
                        changes.append(1.0 - change_ratio / 3.0)
                    else:
                        changes.append(0.1)  # Large variance yields lower confidence

        if changes:
            confidence += np.mean(changes) * 0.4

        # Based on data consistency (simplified)
        consistency_score = 0.8  # Assume data is mostly consistent
        confidence += consistency_score * 0.2

        return min(1.0, max(0.1, confidence))

    def _save_effect_metrics(self, metrics: EffectMetrics):
        """Save effect metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO effect_metrics
                (metric_id, timestamp, action_id, sentiment_before, sentiment_after,
                 sentiment_change, emotional_intensity, engagement_rate, interaction_count,
                 share_rate, comment_quality_score, reach_expansion, influence_propagation,
                 opinion_shift_rate, credibility_impact, discourse_balance, extremism_reduction,
                 constructive_dialogue_rate, overall_effectiveness, confidence_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.metric_id, metrics.timestamp.isoformat(), metrics.action_id,
                metrics.sentiment_before, metrics.sentiment_after, metrics.sentiment_change,
                metrics.emotional_intensity, metrics.engagement_rate, metrics.interaction_count,
                metrics.share_rate, metrics.comment_quality_score, metrics.reach_expansion,
                metrics.influence_propagation, metrics.opinion_shift_rate, metrics.credibility_impact,
                metrics.discourse_balance, metrics.extremism_reduction, metrics.constructive_dialogue_rate,
                metrics.overall_effectiveness, metrics.confidence_level
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Effect metrics save failed: {e}")

    def _check_evaluation_alerts(self, metrics: EffectMetrics):
        """Check evaluation alerts"""
        alerts = []

        # Alert for low overall effectiveness
        if metrics.overall_effectiveness < 0.3:
            alerts.append(f"Overall effectiveness is low: {metrics.overall_effectiveness:.2f}")

        # Alert for sentiment deterioration
        if metrics.sentiment_change < -0.5:
            alerts.append(f"Sentiment worsened significantly: {metrics.sentiment_change:.2f}")

        # Alert for increasing extremism
        if metrics.extremism_reduction < -0.2:
            alerts.append("Extremism level is rising")

        # Alert for extreme engagement spikes
        if metrics.engagement_rate > 3.0:
            alerts.append(f"Engagement spike detected: {metrics.engagement_rate:.2f}")

        # Alert for low confidence score
        if metrics.confidence_level < self.config["confidence_threshold"]:
            alerts.append(f"Data confidence score is low: {metrics.confidence_level:.2f}")

        if alerts:
            logger.warning(f"⚠️ Evaluation alerts [{metrics.action_id}]: {'; '.join(alerts)}")

    def _generate_final_evaluation_report(self, action_id: str, context: EvaluationContext) -> Dict[str, Any]:
        """Generate final evaluation report"""
        try:
            metrics_list = self.metrics_history.get(action_id, [])

            if not metrics_list:
                return {"error": "No evaluation data available"}

            # Calculate summary statistics
            report = {
                "action_id": action_id,
                "evaluation_period": {
                    "start": metrics_list[0].timestamp.isoformat(),
                    "end": metrics_list[-1].timestamp.isoformat(),
                    "duration_minutes": (metrics_list[-1].timestamp - metrics_list[0].timestamp).total_seconds() / 60
                },
                "data_points": len(metrics_list),
                "summary_statistics": {},
                "trend_analysis": {},
                "performance_assessment": {},
                "recommendations": []
            }

            # Aggregate statistics
            metrics_fields = [
                "overall_effectiveness", "sentiment_change", "engagement_rate",
                "influence_propagation", "discourse_balance", "extremism_reduction",
                "constructive_dialogue_rate", "confidence_level"
            ]

            for field in metrics_fields:
                values = [getattr(m, field) for m in metrics_list]
                report["summary_statistics"][field] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "final": values[-1] if values else 0
                }

            # Trend analysis
            report["trend_analysis"] = self._analyze_trends(metrics_list)

            # Performance assessment
            report["performance_assessment"] = self._assess_performance(metrics_list, context)

            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(metrics_list, context)

            logger.info(f"📊 Generated final evaluation report: {action_id}")
            return report

        except Exception as e:
            logger.error(f"❌ Generating final evaluation report failed: {e}")
            return {"error": str(e)}

    def _analyze_trends(self, metrics_list: List[EffectMetrics]) -> Dict[str, str]:
        """Analyze trends"""
        trends = {}

        if len(metrics_list) < 3:
            return {"note": "Insufficient data points to analyze trends"}

        # Analyze each metrics trend
        fields = ["overall_effectiveness", "sentiment_change", "engagement_rate", "discourse_balance"]

        for field in fields:
            values = [getattr(m, field) for m in metrics_list]

            # Simple linear trend analysis
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0]

            if slope > 0.01:
                trends[field] = "rising"
            elif slope < -0.01:
                trends[field] = "falling"
            else:
                trends[field] = "stable"

        return trends

    def _assess_performance(self, metrics_list: List[EffectMetrics], context: EvaluationContext) -> Dict[str, Any]:
        """Evaluate performance"""
        assessment = {}

        # Overall effectiveness rating
        avg_effectiveness = np.mean([m.overall_effectiveness for m in metrics_list])

        if avg_effectiveness >= 0.8:
            assessment["overall_grade"] = "Excellent"
        elif avg_effectiveness >= 0.6:
            assessment["overall_grade"] = "Good"
        elif avg_effectiveness >= 0.4:
            assessment["overall_grade"] = "Average"
        else:
            assessment["overall_grade"] = "Needs improvement"

        assessment["average_effectiveness"] = avg_effectiveness

        # Target achievement status
        target_achievement = {}
        for target in context.target_metrics:
            if hasattr(metrics_list[-1], target):
                final_value = getattr(metrics_list[-1], target)
                target_achievement[target] = {
                    "final_value": final_value,
                    "status": "achieved" if final_value > 0.6 else "not achieved"
                }

        assessment["target_achievement"] = target_achievement

        return assessment

    def _generate_recommendations(self, metrics_list: List[EffectMetrics], context: EvaluationContext) -> List[str]:
        """Generate recommendations"""
        recommendations = []

        final_metrics = metrics_list[-1]

        # Based on final effectiveness
        if final_metrics.overall_effectiveness < 0.5:
            recommendations.append("Overall effectiveness is low; consider adjusting the strategy")

        if final_metrics.sentiment_change < 0:
            recommendations.append("Sentiment metrics are declining; use a more measured tone")

        if final_metrics.discourse_balance < 0.4:
            recommendations.append("Discussion imbalance detected; add more diverse perspectives")

        if final_metrics.extremism_reduction < 0.1:
            recommendations.append("Extremism level shows little improvement; strengthen interventions")

        if final_metrics.constructive_dialogue_rate < 0.3:
            recommendations.append("Constructive dialogue is insufficient; steer toward rational discussion")

        # Based on confidence score
        avg_confidence = np.mean([m.confidence_level for m in metrics_list])
        if avg_confidence < 0.7:
            recommendations.append("Average confidence score is low; improve data collection practices")

        return recommendations

    def _cleanup_evaluation(self, action_id: str):
        """Cleanup evaluation resources"""
        try:
            # Stop threads
            if action_id in self.stop_flags:
                del self.stop_flags[action_id]

            if action_id in self.evaluation_threads:
                del self.evaluation_threads[action_id]

            # Remove active evaluation entry
            if action_id in self.active_evaluations:
                del self.active_evaluations[action_id]

            logger.info(f"🧹 Cleaned up evaluation resources: {action_id}")

        except Exception as e:
            logger.error(f"❌ Cleaning evaluation resources failed: {e}")

    def stop_evaluation(self, action_id: str) -> Dict[str, Any]:
        """Stop evaluation"""
        try:
            if action_id in self.stop_flags:
                self.stop_flags[action_id].set()

                # Wait for the thread to finish
                if action_id in self.evaluation_threads:
                    self.evaluation_threads[action_id].join(timeout=5)

                # Generate final report
                context = self.active_evaluations.get(action_id)
                if context:
                    final_report = self._generate_final_evaluation_report(action_id, context)
                    logger.info(f"⏹️ stopevaluate: {action_id}")
                    return final_report

            return {"error": "Evaluation does not exist or has been stopped"}

        except Exception as e:
            logger.error(f"❌ Stopping evaluation failed: {e}")
            return {"error": str(e)}

    def get_realtime_metrics(self, action_id: str) -> Optional[EffectMetrics]:
        """Get realtime metrics"""
        metrics_list = self.metrics_history.get(action_id, [])
        return metrics_list[-1] if metrics_list else None

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get evaluation system summary"""
        summary = {
            "active_evaluations": len(self.active_evaluations),
            "total_metrics_collected": sum(len(metrics) for metrics in self.metrics_history.values()),
            "average_effectiveness": 0.0,
            "system_performance": {
                "data_collection_rate": "normal",
                "evaluation_accuracy": "good",
                "system_load": "light"
            }
        }

        # Calculate average effectiveness
        all_effectiveness = []
        for metrics_list in self.metrics_history.values():
            all_effectiveness.extend([m.overall_effectiveness for m in metrics_list])

        if all_effectiveness:
            summary["average_effectiveness"] = np.mean(all_effectiveness)

        return summary

    def generate_improvement_suggestions(self, metrics: EffectMetrics) -> List[str]:
        """Generate improvement suggestions based on realtime metrics"""
        suggestions = []

        try:
            # Based on overall effectiveness
            if metrics.overall_effectiveness < 0.3:
                suggestions.extend([
                    "Overall effectiveness is poor; reconsider the strategy direction",
                    "Consider adding more specialized agents",
                    "Shorten response intervals to increase interaction frequency"
                ])
            elif metrics.overall_effectiveness < 0.6:
                suggestions.extend([
                    "Performance is average; adjust the agent mix",
                    "Optimize content quality and persuasiveness",
                    "Strengthen emotional guidance techniques"
                ])

            # Based on sentiment change
            if metrics.sentiment_change < -0.3:
                suggestions.append("Sentiment is deteriorating; adopt a gentler tone")
            elif metrics.sentiment_change > 0.5:
                suggestions.append("Sentiment improved significantly; consider easing intervention intensity")

            # Based on engagement
            if metrics.engagement_rate < 0.8:
                suggestions.append("Engagement is low; add more interactive elements")
            elif metrics.engagement_rate > 2.5:
                suggestions.append("Engagement is very high; manage the discussion pace")

            # Based on balance
            if metrics.discourse_balance < 0.3:
                suggestions.append("Discussion is severely imbalanced; add diverse voices")
            elif metrics.discourse_balance > 0.7:
                suggestions.append("Discussion is too uniform; intentionally introduce contrasting viewpoints")

            # Based on constructive dialogue
            if metrics.constructive_dialogue_rate < 0.3:
                suggestions.append("Constructive dialogue is lacking; steer toward more rational exchanges")

            # Based on confidence score
            if metrics.confidence_level < 0.5:
                suggestions.append("Confidence score is low; validate data sources")

            return suggestions[:5]  # Return the top 5 suggestions

        except Exception as e:
            return [f"Error generating suggestions: {e}"]

    def predict_trend(self, action_id: str, prediction_horizon: int = 30) -> Dict[str, Any]:
        """Predict future trends"""
        try:
            metrics_list = self.metrics_history.get(action_id, [])

            if len(metrics_list) < 3:
                return {"error": "Insufficient data for prediction"}

            # Get recent metrics
            recent_metrics = metrics_list[-min(5, len(metrics_list)):]

            # Simple linear prediction
            predictions = {}
            fields = ["overall_effectiveness", "sentiment_change", "engagement_rate", "discourse_balance"]

            for field in fields:
                values = [getattr(m, field) for m in recent_metrics]

                # Calculate trend slope
                x = np.arange(len(values))
                slope, intercept = np.polyfit(x, values, 1)

                # Predict future value
                future_x = len(values) + prediction_horizon / 5  # Assume one data point every 5 minutes
                predicted_value = slope * future_x + intercept

                # Limit the predicted value to a reasonable range
                predicted_value = max(-1, min(1, predicted_value))

                predictions[field] = {
                    "current": values[-1],
                    "predicted": predicted_value,
                    "trend": "rising" if slope > 0.01 else "falling" if slope < -0.01 else "stable",
                    "confidence": min(1.0, len(values) / 5.0)  # More data increases confidence
                }

            # Generate prediction summary
            summary = {
                "prediction_horizon_minutes": prediction_horizon,
                "predictions": predictions,
                "overall_trend": self._determine_overall_trend(predictions),
                "risk_assessment": self._assess_prediction_risks(predictions),
                "recommended_actions": self._recommend_actions_based_on_prediction(predictions)
            }

            return summary

        except Exception as e:
            return {"error": f"Prediction failed: {e}"}

    def _determine_overall_trend(self, predictions: Dict[str, Any]) -> str:
        """Determine overall trend"""
        effectiveness_trend = predictions.get("overall_effectiveness", {}).get("trend", "stable")
        sentiment_trend = predictions.get("sentiment_change", {}).get("trend", "stable")

        if effectiveness_trend == "rising" and sentiment_trend == "rising":
            return "Positive outlook"
        elif effectiveness_trend == "falling" or sentiment_trend == "falling":
            return "Needs attention"
        else:
            return "Generally stable"

    def _assess_prediction_risks(self, predictions: Dict[str, Any]) -> List[str]:
        """Assess prediction risks"""
        risks = []

        effectiveness_pred = predictions.get("overall_effectiveness", {})
        if effectiveness_pred.get("predicted", 0) < 0.3:
            risks.append("Overall effectiveness might decline sharply")

        sentiment_pred = predictions.get("sentiment_change", {})
        if sentiment_pred.get("predicted", 0) < -0.5:
            risks.append("Sentiment could deteriorate significantly")

        engagement_pred = predictions.get("engagement_rate", {})
        if engagement_pred.get("predicted", 1) > 3.0:
            risks.append("Engagement might spike excessively")

        balance_pred = predictions.get("discourse_balance", {})
        if balance_pred.get("predicted", 0.5) < 0.2 or balance_pred.get("predicted", 0.5) > 0.8:
            risks.append("Discussion balance could become unstable")

        return risks

    def _recommend_actions_based_on_prediction(self, predictions: Dict[str, Any]) -> List[str]:
        """Recommend actions based on prediction"""
        actions = []

        effectiveness_pred = predictions.get("overall_effectiveness", {})
        if effectiveness_pred.get("trend") == "falling":
            actions.append("Consider adjusting the current strategy")

        sentiment_pred = predictions.get("sentiment_change", {})
        if sentiment_pred.get("trend") == "falling":
            actions.append("Strengthen emotional guidance and empathy")

        engagement_pred = predictions.get("engagement_rate", {})
        if engagement_pred.get("trend") == "rising" and engagement_pred.get("predicted", 1) > 2.0:
            actions.append("Be ready to manage discussion pace to avoid excessive escalation")

        balance_pred = predictions.get("discourse_balance", {})
        if balance_pred.get("trend") == "falling":
            actions.append("Introduce diverse perspectives to keep the discussion balanced")

        return actions
