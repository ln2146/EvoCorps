"""
EvoCorps Active Defense System - Monitoring Center
Real-time metrics dashboard for defense system performance
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json


@dataclass
class TopicData:
    """Data structure for a single topic"""
    topic_id: str
    topic_name: str
    engagement_count: int = 0
    malicious_posts: int = 0
    defense_posts: int = 0
    neutral_posts: int = 0
    total_likes: int = 0
    total_comments: int = 0
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AccountMetrics:
    """Metrics for a single account"""
    account_id: str
    account_type: str  # "malicious", "defense", "neutral"
    followers: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_posts: int = 0
    engagement_rate: float = 0.0
    extreme_score: float = 0.0  # 0-1, higher = more extreme


class NicheOccupancyTracker:
    """
    Tracks niche occupancy - which topics are dominated by malicious bots vs EvoCorps
    """
    
    def __init__(self, top_n_topics: int = 10):
        self.top_n_topics = top_n_topics
        self.topics: Dict[str, TopicData] = {}
        self.topic_rankings: List[str] = []  # Sorted by engagement
        self.history: List[Dict[str, Any]] = []
    
    def update_topic(self, topic_data: TopicData):
        """Update or add a topic"""
        self.topics[topic_data.topic_id] = topic_data
        self._recalculate_rankings()
    
    def _recalculate_rankings(self):
        """Recalculate topic rankings by engagement"""
        sorted_topics = sorted(
            self.topics.values(),
            key=lambda t: t.engagement_count,
            reverse=True
        )
        self.topic_rankings = [t.topic_id for t in sorted_topics[:self.top_n_topics]]
    
    def get_dominance_for_topic(self, topic_id: str) -> Dict[str, float]:
        """Calculate dominance percentages for a topic"""
        topic = self.topics.get(topic_id)
        if not topic:
            return {"malicious": 0.0, "defense": 0.0, "neutral": 0.0}
        
        total = topic.malicious_posts + topic.defense_posts + topic.neutral_posts
        if total == 0:
            return {"malicious": 0.0, "defense": 0.0, "neutral": 0.0}
        
        return {
            "malicious": topic.malicious_posts / total,
            "defense": topic.defense_posts / total,
            "neutral": topic.neutral_posts / total
        }
    
    def get_topic_controller(self, topic_id: str) -> str:
        """Determine which faction controls a topic"""
        dominance = self.get_dominance_for_topic(topic_id)

        if dominance["malicious"] > 0.5:
            return "malicious"
        elif dominance["defense"] > 0.5:
            return "defense"
        elif dominance["neutral"] > 0.6:
            # Truly quiet topic — neither side is active enough to matter
            return "neutral_dominant"
        elif dominance["malicious"] > dominance["defense"]:
            return "malicious_leaning"
        elif dominance["defense"] > dominance["malicious"]:
            return "defense_leaning"
        else:
            return "contested"
    
    def calculate_niche_occupancy(self) -> Dict[str, Any]:
        """
        Calculate niche occupancy metrics for top N topics
        
        Returns:
            Dictionary with occupancy statistics
        """
        if not self.topic_rankings:
            return {
                "total_topics": 0,
                "malicious_dominant": 0,
                "malicious_leaning": 0,
                "defense_dominant": 0,
                "defense_leaning": 0,
                "neutral_dominant": 0,
                "contested": 0,
                "malicious_percentage": 0.0,
                "defense_percentage": 0.0,
                "malicious_side_percentage": 0.0,
                "defense_side_percentage": 0.0,
                "topics_detail": []
            }

        malicious_dominant = 0
        malicious_leaning = 0
        defense_dominant = 0
        defense_leaning = 0
        neutral_dominant = 0
        contested = 0
        topics_detail = []

        for topic_id in self.topic_rankings:
            controller = self.get_topic_controller(topic_id)
            topic = self.topics.get(topic_id)
            dominance = self.get_dominance_for_topic(topic_id)

            if controller == "malicious":
                malicious_dominant += 1
            elif controller == "malicious_leaning":
                malicious_leaning += 1
            elif controller == "defense":
                defense_dominant += 1
            elif controller == "defense_leaning":
                defense_leaning += 1
            elif controller == "neutral_dominant":
                neutral_dominant += 1
            else:  # "contested"
                contested += 1

            topics_detail.append({
                "topic_id": topic_id,
                "topic_name": topic.topic_name if topic else "Unknown",
                "controller": controller,
                "malicious_ratio": dominance["malicious"],
                "defense_ratio": dominance["defense"],
                "neutral_ratio": dominance["neutral"],
                "engagement_count": topic.engagement_count if topic else 0
            })

        total = len(self.topic_rankings)
        # "effectively malicious" = dominant + leaning
        malicious_side = malicious_dominant + malicious_leaning
        defense_side = defense_dominant + defense_leaning
        return {
            "total_topics": total,
            "malicious_dominant": malicious_dominant,
            "malicious_leaning": malicious_leaning,
            "defense_dominant": defense_dominant,
            "defense_leaning": defense_leaning,
            "neutral_dominant": neutral_dominant,
            "contested": contested,
            "malicious_percentage": malicious_dominant / total * 100 if total > 0 else 0.0,
            "defense_percentage": defense_dominant / total * 100 if total > 0 else 0.0,
            "malicious_side_percentage": malicious_side / total * 100 if total > 0 else 0.0,
            "defense_side_percentage": defense_side / total * 100 if total > 0 else 0.0,
            "topics_detail": topics_detail,
            "timestamp": datetime.now().isoformat()
        }
    
    def record_snapshot(self):
        """Record current state to history"""
        snapshot = self.calculate_niche_occupancy()
        self.history.append(snapshot)
        return snapshot


class AlgorithmicBiasCalculator:
    """
    Calculates Algorithmic Bias Gini Coefficient
    Measures if traffic is overly concentrated on a few extreme accounts
    """
    
    def __init__(self):
        self.accounts: Dict[str, AccountMetrics] = {}
        self.history: List[Dict[str, Any]] = []
    
    def update_account(self, account_metrics: AccountMetrics):
        """Update or add an account"""
        self.accounts[account_metrics.account_id] = account_metrics
    
    def calculate_gini_coefficient(self, values: List[float]) -> float:
        """
        Calculate Gini coefficient for a list of values
        
        Args:
            values: List of non-negative values
        
        Returns:
            Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        if not values or all(v == 0 for v in values):
            return 0.0
        
        # Sort values
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        # Calculate Gini coefficient
        cumsum = 0.0
        for i, v in enumerate(sorted_values):
            cumsum += (2 * (i + 1) - n - 1) * v
        
        total = sum(sorted_values)
        if total == 0:
            return 0.0
        
        gini = cumsum / (n * total)
        return max(0.0, min(1.0, gini))
    
    def calculate_traffic_concentration(self) -> Dict[str, Any]:
        """
        Calculate traffic concentration metrics
        
        Returns:
            Dictionary with concentration statistics
        """
        if not self.accounts:
            return {
                "gini_coefficient": 0.0,
                "top_10_percent_share": 0.0,
                "top_1_percent_share": 0.0,
                "extreme_account_share": 0.0,
                "total_accounts": 0,
                "total_engagement": 0
            }
        
        # Get engagement values — only active accounts (avoid zero-inflation of Gini)
        engagements = [
            acc.total_likes + acc.total_comments
            for acc in self.accounts.values()
            if acc.total_likes + acc.total_comments > 0
        ]
        total_engagement = sum(engagements)
        
        if total_engagement == 0:
            return {
                "gini_coefficient": 0.0,
                "top_10_percent_share": 0.0,
                "top_1_percent_share": 0.0,
                "extreme_account_share": 0.0,
                "total_accounts": len(self.accounts),
                "total_engagement": 0
            }
        
        # Calculate Gini coefficient
        gini = self.calculate_gini_coefficient(engagements)
        
        # Sort active accounts by engagement
        sorted_accounts = sorted(
            (acc for acc in self.accounts.values() if acc.total_likes + acc.total_comments > 0),
            key=lambda a: a.total_likes + a.total_comments,
            reverse=True
        )
        n = len(sorted_accounts)
        
        # Top 10% share
        top_10_percent_count = max(1, int(n * 0.1))
        top_10_engagement = sum(
            acc.total_likes + acc.total_comments 
            for acc in sorted_accounts[:top_10_percent_count]
        )
        top_10_share = top_10_engagement / total_engagement * 100
        
        # Top 1% share
        top_1_percent_count = max(1, int(n * 0.01))
        top_1_engagement = sum(
            acc.total_likes + acc.total_comments 
            for acc in sorted_accounts[:top_1_percent_count]
        )
        top_1_share = top_1_engagement / total_engagement * 100
        
        # Extreme account share (accounts with extreme_score > 0.7)
        extreme_accounts = [acc for acc in self.accounts.values() if acc.extreme_score > 0.7]
        extreme_engagement = sum(
            acc.total_likes + acc.total_comments 
            for acc in extreme_accounts
        )
        extreme_share = extreme_engagement / total_engagement * 100
        
        return {
            "gini_coefficient": round(gini, 4),
            "top_10_percent_share": round(top_10_share, 2),
            "top_1_percent_share": round(top_1_share, 2),
            "extreme_account_share": round(extreme_share, 2),
            "extreme_account_count": len(extreme_accounts),
            "total_accounts": n,
            "total_engagement": total_engagement,
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_algorithmic_bias_gini(self) -> Dict[str, Any]:
        """
        Calculate algorithmic bias specifically for extreme vs moderate content
        
        Returns:
            Dictionary with bias metrics
        """
        if not self.accounts:
            return {
                "overall_gini": 0.0,
                "malicious_gini": 0.0,
                "defense_gini": 0.0,
                "neutral_gini": 0.0,
                "bias_assessment": "unknown"
            }
        
        # Separate by account type — only active accounts (avoid zero-inflation of Gini)
        malicious_engagements = [
            acc.total_likes + acc.total_comments
            for acc in self.accounts.values()
            if acc.account_type == "malicious" and acc.total_likes + acc.total_comments > 0
        ]
        defense_engagements = [
            acc.total_likes + acc.total_comments
            for acc in self.accounts.values()
            if acc.account_type == "defense" and acc.total_likes + acc.total_comments > 0
        ]
        neutral_engagements = [
            acc.total_likes + acc.total_comments
            for acc in self.accounts.values()
            if acc.account_type == "neutral" and acc.total_likes + acc.total_comments > 0
        ]

        all_engagements = [
            acc.total_likes + acc.total_comments
            for acc in self.accounts.values()
            if acc.total_likes + acc.total_comments > 0
        ]
        
        overall_gini = self.calculate_gini_coefficient(all_engagements)
        malicious_gini = self.calculate_gini_coefficient(malicious_engagements)
        defense_gini = self.calculate_gini_coefficient(defense_engagements)
        neutral_gini = self.calculate_gini_coefficient(neutral_engagements)
        
        # Assess bias level
        if overall_gini > 0.7:
            bias_assessment = "severe_concentration"
        elif overall_gini > 0.5:
            bias_assessment = "high_concentration"
        elif overall_gini > 0.3:
            bias_assessment = "moderate_concentration"
        else:
            bias_assessment = "healthy_distribution"
        
        return {
            "overall_gini": round(overall_gini, 4),
            "malicious_gini": round(malicious_gini, 4),
            "defense_gini": round(defense_gini, 4),
            "neutral_gini": round(neutral_gini, 4),
            "bias_assessment": bias_assessment,
            "timestamp": datetime.now().isoformat()
        }
    
    def record_snapshot(self) -> Dict[str, Any]:
        """Record current state to history"""
        concentration = self.calculate_traffic_concentration()
        bias = self.calculate_algorithmic_bias_gini()
        
        snapshot = {
            **concentration,
            **bias
        }
        self.history.append(snapshot)
        return snapshot


class DefenseMonitoringCenter:
    """
    Central monitoring hub for EvoCorps defense system
    Aggregates all metrics and provides real-time dashboard
    """
    
    def __init__(self, top_n_topics: int = 10):
        self.niche_tracker = NicheOccupancyTracker(top_n_topics)
        self.bias_calculator = AlgorithmicBiasCalculator()
        self.dashboard_history: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
    
    def update_topic_data(self, topic_data: TopicData):
        """Update topic data"""
        self.niche_tracker.update_topic(topic_data)
    
    def update_account_data(self, account_metrics: AccountMetrics):
        """Update account data"""
        self.bias_calculator.update_account(account_metrics)
    
    def generate_dashboard(self) -> Dict[str, Any]:
        """
        Generate comprehensive dashboard with all metrics
        
        Returns:
            Complete dashboard data
        """
        niche_occupancy = self.niche_tracker.calculate_niche_occupancy()
        traffic_concentration = self.bias_calculator.calculate_traffic_concentration()
        algorithmic_bias = self.bias_calculator.calculate_algorithmic_bias_gini()
        
        # Generate alerts if needed
        self._check_alerts(niche_occupancy, traffic_concentration, algorithmic_bias)
        
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "niche_occupancy": niche_occupancy,
            "traffic_concentration": traffic_concentration,
            "algorithmic_bias": algorithmic_bias,
            "alerts": self.alerts[-5:] if self.alerts else [],  # Last 5 alerts
            "summary": {
                "defense_health": self._calculate_defense_health(
                    niche_occupancy, algorithmic_bias
                ),
                "recommendations": self._generate_recommendations(
                    niche_occupancy, algorithmic_bias, traffic_concentration
                )
            }
        }
        
        self.dashboard_history.append(dashboard)
        return dashboard
    
    def _check_alerts(
        self, 
        niche_occupancy: Dict[str, Any],
        traffic_concentration: Dict[str, Any],
        algorithmic_bias: Dict[str, Any]
    ):
        """Check for alert conditions"""
        # Alert: Malicious dominance in too many topics (dominant + leaning)
        if niche_occupancy["malicious_side_percentage"] > 60:
            self.alerts.append({
                "level": "warning",
                "type": "malicious_dominance",
                "message": (
                    f"Malicious actors control {niche_occupancy['malicious_side_percentage']:.1f}% of top topics "
                    f"({niche_occupancy['malicious_dominant']} dominant + {niche_occupancy['malicious_leaning']} leaning)"
                ),
                "timestamp": datetime.now().isoformat()
            })
        
        # Alert: High traffic concentration
        if traffic_concentration["gini_coefficient"] > 0.7:
            self.alerts.append({
                "level": "warning",
                "type": "high_concentration",
                "message": f"Traffic highly concentrated (Gini: {traffic_concentration['gini_coefficient']:.2f})",
                "timestamp": datetime.now().isoformat()
            })
        
        # Alert: Extreme accounts getting too much engagement
        if traffic_concentration["extreme_account_share"] > 30:
            self.alerts.append({
                "level": "critical",
                "type": "extreme_amplification",
                "message": f"Extreme accounts receiving {traffic_concentration['extreme_account_share']:.1f}% of engagement",
                "timestamp": datetime.now().isoformat()
            })
    
    def _calculate_defense_health(
        self,
        niche_occupancy: Dict[str, Any],
        algorithmic_bias: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall defense system health score"""
        
        # Niche occupancy score (0-100): use defense_side (dominant + leaning)
        niche_score = niche_occupancy["defense_side_percentage"]
        
        # Bias health score (0-100)
        # Lower Gini is better
        bias_score = max(0, 100 - algorithmic_bias["overall_gini"] * 100)
        
        # Combined health score
        health_score = (niche_score * 0.5 + bias_score * 0.5)
        
        if health_score >= 70:
            status = "healthy"
        elif health_score >= 50:
            status = "moderate"
        elif health_score >= 30:
            status = "concerning"
        else:
            status = "critical"
        
        return {
            "score": round(health_score, 1),
            "status": status,
            "niche_score": round(niche_score, 1),
            "bias_score": round(bias_score, 1)
        }
    
    def _generate_recommendations(
        self,
        niche_occupancy: Dict[str, Any],
        algorithmic_bias: Dict[str, Any],
        traffic_concentration: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Topic-based recommendations
        if niche_occupancy["malicious_side_percentage"] > 50:
            recommendations.append(
                "Deploy more Amplifier agents to contested topics"
            )

        if niche_occupancy["contested"] + niche_occupancy["defense_leaning"] > niche_occupancy["defense_dominant"]:
            recommendations.append(
                "Increase Fact Checker presence in contested discussions"
            )

        # Bias-based recommendations
        if algorithmic_bias["overall_gini"] > 0.6:
            recommendations.append(
                "Niche Fillers should introduce alternative topics to diversify engagement"
            )

        # extreme_account_share is 0-100 (percentage)
        if traffic_concentration.get("extreme_account_share", 0) > 25:
            recommendations.append(
                "Empaths should engage with extreme content audiences to reduce polarization"
            )
        
        if not recommendations:
            recommendations.append("Defense system operating within normal parameters")
        
        return recommendations
    
    def get_historical_trend(self, metric: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get historical trend data
        
        Args:
            metric: "niche_occupancy", "algorithmic_bias", or "all"
            limit: Number of historical entries to return
        
        Returns:
            List of historical data points
        """
        history = self.dashboard_history[-limit:]
        
        if metric == "niche_occupancy":
            return [{
                "timestamp": h["timestamp"],
                "niche_occupancy": h["niche_occupancy"]
            } for h in history]
        elif metric == "algorithmic_bias":
            return [{
                "timestamp": h["timestamp"],
                "algorithmic_bias": h["algorithmic_bias"]
            } for h in history]
        else:
            return history
    
    def sync_from_db(self, conn) -> None:
        """
        Pull live data from the simulation SQLite connection and refresh all metrics.

        Topic classification (based on author persona JSON):
          malicious  = persona type contains 'negative'/'malicious' OR fake news post
          defense    = persona type contains 'amplifier'/'defense', OR posts.is_agent_response=1
                       Defense agents save COMMENTS (not posts), so we UNION the comments table.
          neutral    = everything else

        Account classification follows the same persona logic.
        extreme_score = 0.85 for malicious users (opinion_monitoring may be empty).
        """
        cursor = conn.cursor()

        # Helper macro: is_malicious expression for a persona column alias
        _MAL_PERSONA = (
            "(u.persona LIKE '%\"type\": \"negative\"%'"
            " OR u.persona LIKE '%''type'': ''negative''%'"
            " OR u.persona LIKE '%\"type\": \"malicious\"%'"
            " OR u.persona LIKE '%''type'': ''malicious''%')"
        )
        _DEF_PERSONA = (
            "(u.persona LIKE '%amplifier%'"
            " OR u.persona LIKE '%defense%')"
        )

        # --- Topics: UNION posts + defense comments, grouped by root post ---
        cursor.execute(f"""
            SELECT
                topic_id,
                SUBSTR(MIN(COALESCE(topic_name, '')), 1, 60) AS topic_name,
                SUM(engagement)    AS engagement_count,
                SUM(mal_cnt)       AS malicious_posts,
                SUM(def_cnt)       AS defense_posts,
                SUM(neu_cnt)       AS neutral_posts,
                SUM(likes)         AS total_likes,
                SUM(coms)          AS total_comments
            FROM (
                -- Posts
                SELECT
                    COALESCE(p.original_post_id, p.post_id)     AS topic_id,
                    p.content                                    AS topic_name,
                    p.num_likes + p.num_comments + p.num_shares  AS engagement,
                    CASE WHEN {_MAL_PERSONA}
                              OR p.agent_type = 'malicious_agent'
                              OR (p.is_news = 1 AND p.news_type = 'fake')
                         THEN 1 ELSE 0 END                       AS mal_cnt,
                    CASE WHEN {_DEF_PERSONA}
                              OR p.agent_type = 'amplifier_agent'
                              OR p.agent_type = 'leader_agent'
                              OR COALESCE(p.is_agent_response, 0) = 1
                         THEN 1 ELSE 0 END                       AS def_cnt,
                    CASE WHEN NOT ({_MAL_PERSONA}
                                   OR p.agent_type = 'malicious_agent'
                                   OR (p.is_news = 1 AND p.news_type = 'fake'))
                          AND NOT ({_DEF_PERSONA}
                                   OR p.agent_type = 'amplifier_agent'
                                   OR COALESCE(p.is_agent_response, 0) = 1)
                         THEN 1 ELSE 0 END                       AS neu_cnt,
                    p.num_likes                                  AS likes,
                    p.num_comments                               AS coms
                FROM posts p
                LEFT JOIN users u ON p.author_id = u.user_id
                WHERE p.status IS NULL OR p.status = 'active'

                UNION ALL

                -- Comments (all roles: malicious, defense, neutral)
                SELECT
                    COALESCE(pp.original_post_id, c.post_id)    AS topic_id,
                    NULL                                         AS topic_name,
                    c.num_likes                                  AS engagement,
                    CASE WHEN {_MAL_PERSONA}
                              OR c.agent_type = 'malicious_agent'
                         THEN 1 ELSE 0 END                       AS mal_cnt,
                    CASE WHEN {_DEF_PERSONA}
                              OR c.agent_type = 'amplifier_agent'
                              OR c.agent_type = 'leader_agent'
                         THEN 1 ELSE 0 END                       AS def_cnt,
                    CASE WHEN NOT ({_MAL_PERSONA} OR c.agent_type = 'malicious_agent')
                          AND NOT ({_DEF_PERSONA} OR c.agent_type = 'amplifier_agent' OR c.agent_type = 'leader_agent')
                         THEN 1 ELSE 0 END                       AS neu_cnt,
                    c.num_likes                                  AS likes,
                    0                                            AS coms
                FROM comments c
                LEFT JOIN users u  ON c.author_id  = u.user_id
                LEFT JOIN posts pp ON c.post_id     = pp.post_id
            )
            GROUP BY topic_id
            ORDER BY engagement_count DESC
            LIMIT ?
        """, (self.niche_tracker.top_n_topics,))

        self.niche_tracker.topics.clear()
        for row in cursor.fetchall():
            td = TopicData(
                topic_id=row[0] or "",
                topic_name=row[1] or "",
                engagement_count=row[2] or 0,
                malicious_posts=row[3] or 0,
                defense_posts=row[4] or 0,
                neutral_posts=row[5] or 0,
                total_likes=row[6] or 0,
                total_comments=row[7] or 0,
            )
            self.niche_tracker.topics[td.topic_id] = td
        self.niche_tracker._recalculate_rankings()

        # --- Accounts: per user (including malicious bots from comments) ---
        # First, get all users with their basic metrics
        cursor.execute(f"""
            SELECT
                u.user_id,
                u.total_likes_received,
                u.total_comments_received,
                u.follower_count,
                CASE
                    WHEN {_MAL_PERSONA} THEN 'malicious'
                    WHEN {_DEF_PERSONA} THEN 'defense'
                    ELSE 'neutral'
                END AS account_type
            FROM users u
            WHERE u.persona NOT LIKE '%"type": "news_org"%'
              AND u.persona NOT LIKE '%''type'': ''news_org''%'
        """)
        
        users_data = {}
        for row in cursor.fetchall():
            users_data[row[0]] = {
                'user_id': row[0] or "",
                'total_likes': row[1] or 0,
                'total_comments': row[2] or 0,
                'followers': row[3] or 0,
                'account_type': row[4] or "neutral"
            }
        
        # Also include malicious bot accounts from comments table
        # These may have been created with persona type "negative" but stored differently
        cursor.execute("""
            SELECT DISTINCT 
                c.author_id,
                SUM(c.num_likes) as total_likes,
                COUNT(*) as total_comments
            FROM comments c
            WHERE c.agent_type = 'malicious'
               OR c.author_id IN (SELECT user_id FROM users WHERE persona LIKE '%"type": "negative"%')
               OR c.author_id IN (SELECT author_id FROM malicious_comments mc JOIN comments cc ON mc.comment_id = cc.comment_id)
            GROUP BY c.author_id
        """)
        
        malicious_commenters = {}
        for row in cursor.fetchall():
            author_id = row[0]
            if author_id not in users_data:
                users_data[author_id] = {
                    'user_id': author_id,
                    'total_likes': row[1] or 0,
                    'total_comments': row[2] or 0,
                    'followers': 0,
                    'account_type': 'malicious'
                }
            else:
                # Update existing user to malicious if they have malicious comments
                users_data[author_id]['account_type'] = 'malicious'
                # Also update engagement from comments if not already tracked
                if users_data[author_id]['total_likes'] == 0:
                    users_data[author_id]['total_likes'] = row[1] or 0
                if users_data[author_id]['total_comments'] == 0:
                    users_data[author_id]['total_comments'] = row[2] or 0
        
        # Get engagement from posts for all users
        cursor.execute("""
            SELECT author_id, SUM(num_likes) as post_likes, COUNT(*) as post_count
            FROM posts
            WHERE (status IS NULL OR status = 'active')
            GROUP BY author_id
        """)
        
        for row in cursor.fetchall():
            author_id = row[0]
            if author_id in users_data:
                users_data[author_id]['total_likes'] = (users_data[author_id]['total_likes'] or 0) + (row[1] or 0)
        
        # Get extreme scores from opinion_monitoring for non-malicious users
        cursor.execute("""
            SELECT p2.author_id, AVG(CAST(om.extremism_level AS FLOAT)) / 4.0 as avg_extreme
            FROM opinion_monitoring om
            JOIN posts p2 ON CAST(om.post_id AS TEXT) = p2.post_id
            GROUP BY p2.author_id
        """)
        
        extreme_scores = {}
        for row in cursor.fetchall():
            extreme_scores[row[0]] = row[1]
        
        # Clear and rebuild accounts
        self.bias_calculator.accounts.clear()
        for user_id, data in users_data.items():
            # Determine extreme score
            if data['account_type'] == 'malicious':
                extreme_score = 0.85  # Malicious bots are always extreme
            else:
                extreme_score = extreme_scores.get(user_id, 0.0)
            
            am = AccountMetrics(
                account_id=data['user_id'],
                account_type=data['account_type'],
                followers=data['followers'],
                total_likes=data['total_likes'],
                total_comments=data['total_comments'],
                total_posts=0,
                engagement_rate=0.0,
                extreme_score=min(1.0, max(0.0, extreme_score)),
            )
            self.bias_calculator.accounts[am.account_id] = am

    def export_dashboard(self, format: str = "json") -> str:
        """Export dashboard data"""
        dashboard = self.generate_dashboard()
        
        if format == "json":
            return json.dumps(dashboard, indent=2, ensure_ascii=False)
        else:
            return str(dashboard)
    
    def print_dashboard_summary(self):
        """Print a formatted summary of the dashboard"""
        dashboard = self.generate_dashboard()
        
        print("\n" + "="*60)
        print("       EvoCorps Defense System Dashboard")
        print("="*60)
        print(f"\nTimestamp: {dashboard['timestamp']}")
        
        # Niche Occupancy
        no = dashboard["niche_occupancy"]
        print("\n--- Niche Occupancy (Top Topics) ---")
        print(f"  Total Topics Monitored: {no['total_topics']}")
        print(f"  Defense  — Dominant: {no['defense_dominant']}  Leaning: {no['defense_leaning']}  ({no['defense_side_percentage']:.1f}% total)")
        print(f"  Malicious— Dominant: {no['malicious_dominant']}  Leaning: {no['malicious_leaning']}  ({no['malicious_side_percentage']:.1f}% total)")
        print(f"  Contested: {no['contested']}")
        
        # Traffic Concentration
        tc = dashboard["traffic_concentration"]
        print("\n--- Traffic Concentration ---")
        print(f"  Gini Coefficient: {tc['gini_coefficient']:.4f}")
        print(f"  Top 10% Share: {tc['top_10_percent_share']:.1f}%")
        print(f"  Top 1% Share: {tc['top_1_percent_share']:.1f}%")
        print(f"  Extreme Account Share: {tc['extreme_account_share']:.1f}%")
        
        # Algorithmic Bias
        ab = dashboard["algorithmic_bias"]
        print("\n--- Algorithmic Bias Assessment ---")
        print(f"  Overall Gini: {ab['overall_gini']:.4f}")
        print(f"  Assessment: {ab['bias_assessment']}")
        
        # Health Summary
        health = dashboard["summary"]["defense_health"]
        print("\n--- Defense Health ---")
        print(f"  Overall Score: {health['score']}/100")
        print(f"  Status: {health['status'].upper()}")
        
        # Alerts
        if dashboard["alerts"]:
            print("\n--- Recent Alerts ---")
            for alert in dashboard["alerts"][-3:]:
                print(f"  [{alert['level'].upper()}] {alert['message']}")
        
        # Recommendations
        print("\n--- Recommendations ---")
        for rec in dashboard["summary"]["recommendations"]:
            print(f"  • {rec}")
        
        print("\n" + "="*60)


# Convenience function for quick dashboard creation
def create_monitoring_center(top_n_topics: int = 10) -> DefenseMonitoringCenter:
    """Create and return a new monitoring center instance"""
    return DefenseMonitoringCenter(top_n_topics=top_n_topics)