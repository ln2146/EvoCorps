"""
信息茧房观测分析器 - 多参数优化版

核心公式（2个显示参数 + 3个隐藏参数）：
信息茧房指数 = f(同质化, 活跃广度, 网络中心性, 互动倾向性, 时间集中度)

说明：
【显示参数】
- 同质化：关注的人之间的紧密程度 → 越高越严重
- 活跃广度：用户在不同活动类型上的参与 → 越高越轻微

【隐藏参数（后台计算）】
- 网络中心性：用户在社交网络中的位置 → 边缘用户更易茧房化
- 互动倾向性：与同质人群vs异质人群的互动比例 → 倾向同质则茧房化
- 时间集中度：活动的时间分布 → 集中在短期说明茧房化
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import networkx as nx


@dataclass
class UserBubbleMetrics:
    """单个用户的信息茧房指标"""
    user_id: str
    homogeneity_index: float           # 同质化指数：关注人群的相似程度 [0, 1]
    activity_breadth: float            # 活跃广度：用户在不同类型活动上的参与程度 [0, 1]
    echo_chamber_index: float          # 回声室指数：综合评估 [0, 1]
    bubble_severity: str               # 严重程度：none/mild/moderate/severe

    # 隐藏参数（不返回给前端，仅用于后台计算）
    _network_centrality: float = 0.0   # 网络中心性 [0, 1]
    _interaction_bias: float = 0.0     # 互动倾向性 [0, 1]
    _temporal_concentration: float = 0.0  # 时间集中度 [0, 1]

    def to_dict(self) -> Dict:
        """转换为字典格式（用于API返回）- 只返回显示参数"""
        return {
            'user_id': self.user_id,
            'homogeneity_index': round(self.homogeneity_index, 3),
            'activity_breadth': round(self.activity_breadth, 3),
            'echo_chamber_index': round(self.echo_chamber_index, 3),
            'bubble_severity': self.bubble_severity
        }


@dataclass
class GlobalBubbleStats:
    """全局信息茧房统计"""
    total_users: int
    avg_homogeneity: float
    avg_echo_index: float
    severe_bubble_users: int
    moderate_bubble_users: int
    mild_bubble_users: int
    network_density: float


class SimpleBubbleIndexCalculator:
    """
    信息茧房指数计算器（平衡偏严重版本）

    目标：让分布向严重方向偏移，但不要过于极端
    """

    # 严重程度阈值（平衡偏严重版本）
    SEVERITY_THRESHOLDS = {
        "none": 0.15,
        "mild": 0.35,
        "moderate": 0.60
    }

    def calculate(
        self,
        homogeneity: float,
        activity_breadth: float,
        network_centrality: float = 0.5,
        interaction_bias: float = 0.5,
        temporal_concentration: float = 0.5
    ) -> UserBubbleMetrics:
        """计算信息茧房指数（平衡偏严重版本）"""
        # 同质化处理
        if homogeneity > 0.5:
            homogeneity_effective = 0.5 + 0.5 * ((homogeneity - 0.5) / 0.5) ** 1.4
        elif homogeneity < 0.2:
            homogeneity_effective = homogeneity ** 0.9
        else:
            homogeneity_effective = homogeneity

        # 活跃缓解（削弱）
        activity_relief = np.sqrt(activity_breadth) * 0.6

        # 交互效应
        interaction_factor = homogeneity_effective ** 1.8
        activity_relief = activity_relief * (1 - 0.5 * interaction_factor)
        activity_relief = np.clip(activity_relief, 0.0, 0.6)

        # 基础茧房指数（适中偏移）
        base_echo = (
            0.10 +  # 适中基准
            0.88 * homogeneity_effective -
            0.06 * activity_relief
        )

        # 隐藏参数微调
        hidden_influence = (
            (1 - network_centrality) * 0.02 +
            interaction_bias * 0.01 +
            temporal_concentration * 0.01
        )
        base_echo += hidden_influence

        echo_index = np.clip(base_echo, 0.0, 1.0)
        severity = self._determine_severity(echo_index)

        return UserBubbleMetrics(
            user_id="",
            homogeneity_index=homogeneity,
            activity_breadth=activity_breadth,
            echo_chamber_index=float(echo_index),
            bubble_severity=severity,
            _network_centrality=network_centrality,
            _interaction_bias=interaction_bias,
            _temporal_concentration=temporal_concentration
        )

    def _determine_severity(self, index: float) -> str:
        """确定严重程度"""
        if index < self.SEVERITY_THRESHOLDS["none"]:
            return "none"
        elif index < self.SEVERITY_THRESHOLDS["mild"]:
            return "mild"
        elif index < self.SEVERITY_THRESHOLDS["moderate"]:
            return "moderate"
        else:
            return "severe"


class FilterBubbleAnalyzer:
    """信息茧房分析器 - 使用多参数优化公式"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.calculator = SimpleBubbleIndexCalculator()
        self._network_cache = None  # 缓存网络结构

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def analyze_user_bubble(self, user_id: str) -> UserBubbleMetrics:
        """分析单个用户的信息茧房指标"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取关注列表
            cursor.execute("SELECT followed_id FROM follows WHERE follower_id = ?", (user_id,))
            following = [row[0] for row in cursor.fetchall()]

            # 计算显示参数
            homogeneity = self._calculate_homogeneity(cursor, user_id, following)
            activity_breadth = self._calculate_activity_breadth(cursor, user_id)

            # 计算隐藏参数
            network_centrality = self._calculate_network_centrality(cursor, user_id)
            interaction_bias = self._calculate_interaction_bias(cursor, user_id, following)
            temporal_concentration = self._calculate_temporal_concentration(cursor, user_id)

            # 使用多参数公式计算茧房指数
            metrics = self.calculator.calculate(
                homogeneity=homogeneity,
                activity_breadth=activity_breadth,
                network_centrality=network_centrality,
                interaction_bias=interaction_bias,
                temporal_concentration=temporal_concentration
            )

            metrics.user_id = user_id
            return metrics

        finally:
            conn.close()

    def _calculate_homogeneity(self, cursor, user_id: str, following: List[str]) -> float:
        """
        计算同质化指数：关注的人之间的相似程度

        值越高，说明关注的人之间联系越紧密，圈子越封闭
        """
        # 无关注时，返回中等值
        if len(following) == 0:
            return 0.4

        # 只有1个关注时，无法计算同质化
        if len(following) == 1:
            return 0.3

        # 计算关注人之间的互相关注比例
        placeholders = ','.join(['?' for _ in following])
        cursor.execute(f"""
            SELECT followed_id FROM follows
            WHERE follower_id IN ({placeholders})
            AND followed_id IN ({placeholders})
        """, following + following)

        mutual_follows = len(cursor.fetchall())

        # 可能的互相关注对数
        possible_pairs = len(following) * (len(following) - 1)

        if possible_pairs == 0:
            return 0.3

        # 同质化 = 实际互相关注数 / 可能的对数
        homogeneity = mutual_follows / possible_pairs
        return float(np.clip(homogeneity, 0.0, 1.0))

    def _calculate_activity_breadth(self, cursor, user_id: str) -> float:
        """
        计算活跃广度：用户在不同类型活动上的参与程度

        基于发帖、评论、关注数量综合计算
        """
        # 获取各类活动数量
        cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = ?", (user_id,))
        post_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM comments WHERE author_id = ?", (user_id,))
        comment_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,))
        follow_count = cursor.fetchone()[0]

        # 计算活动类型的多样性
        activity_types = 0
        if post_count > 0:
            activity_types += 1
        if comment_count > 0:
            activity_types += 1
        if follow_count > 0:
            activity_types += 1

        # 归一化到 0-1
        type_breadth = activity_types / 3.0

        # 考虑活动总量
        total_activity = post_count + comment_count + follow_count
        volume_score = min(total_activity / 50.0, 1.0)

        # 综合分数：50%类型多样性 + 50%活动量
        breadth = type_breadth * 0.5 + volume_score * 0.5

        # 确保最小值不为0
        return float(np.clip(breadth, 0.1, 1.0))

    def _calculate_network_centrality(self, cursor, user_id: str) -> float:
        """
        计算网络中心性（隐藏参数）：用户在社交网络中的位置

        值越低，说明用户越边缘，越容易茧房化
        """
        try:
            import networkx as nx

            # 构建社交网络图
            cursor.execute("SELECT user_id FROM users")
            all_users = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT follower_id, followed_id FROM follows")
            all_follows = cursor.fetchall()

            G = nx.DiGraph()
            G.add_nodes_from(all_users)
            G.add_edges_from(all_follows)

            # 计算PageRank中心性
            centrality_dict = nx.pagerank(G, alpha=0.85)

            # 获取当前用户的中心性
            centrality = centrality_dict.get(user_id, 0.0)

            # 归一化到 [0, 1]
            max_centrality = max(centrality_dict.values()) if centrality_dict else 1.0
            if max_centrality > 0:
                centrality = centrality / max_centrality

            return float(np.clip(centrality, 0.0, 1.0))

        except Exception:
            # 如果计算失败，返回中等值
            return 0.5

    def _calculate_interaction_bias(self, cursor, user_id: str, following: List[str]) -> float:
        """
        计算互动倾向性（隐藏参数）：用户与同质人群vs异质人群的互动比例

        值越高，说明用户越倾向于与同类互动，茧房风险越高
        """
        if len(following) == 0:
            return 0.5

        # 获取用户关注的人的关注列表（二级网络）
        placeholders = ','.join(['?' for _ in following])
        cursor.execute(f"""
            SELECT followed_id FROM follows
            WHERE follower_id IN ({placeholders})
        """, following)

        friends_of_friends = [row[0] for row in cursor.fetchall()]

        if len(friends_of_friends) == 0:
            return 0.5

        # 计算重合度：用户关注的人之间互相关注的比例
        # 这反映了用户是否处于紧密的圈子中
        overlap = len(set(friends_of_friends) & set(following))
        total_unique = len(set(friends_of_friends) | set(following))

        if total_unique == 0:
            return 0.5

        # 重合度越高，说明圈子越封闭，互动倾向性越高
        bias = overlap / total_unique

        # 放大差异
        bias = bias ** 0.7

        return float(np.clip(bias, 0.0, 1.0))

    def _calculate_temporal_concentration(self, cursor, user_id: str) -> float:
        """
        计算时间集中度（隐藏参数）：用户活动的时间分布

        值越高，说明活动越集中在短期，茧房风险越高
        """
        # 获取用户所有活动的时间戳
        cursor.execute("""
            SELECT created_at FROM posts WHERE author_id = ?
            UNION ALL
            SELECT created_at FROM comments WHERE author_id = ?
            ORDER BY created_at
        """, (user_id, user_id))

        timestamps = [row[0] for row in cursor.fetchall()]

        if len(timestamps) < 2:
            return 0.5

        # 计算活动时间跨度（天）
        from datetime import datetime

        try:
            # 尝试解析时间戳
            dates = []
            for ts in timestamps:
                if isinstance(ts, str):
                    try:
                        dates.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    except:
                        continue
                else:
                    dates.append(ts)

            if len(dates) < 2:
                return 0.5

            # 计算时间跨度
            time_span = (max(dates) - min(dates)).days

            # 如果活动跨度很短，说明集中度高
            if time_span == 0:
                concentration = 1.0
            elif time_span < 7:
                concentration = 0.8
            elif time_span < 30:
                concentration = 0.5
            else:
                concentration = 0.2

            return float(concentration)

        except Exception:
            return 0.5

    def get_global_stats(self) -> GlobalBubbleStats:
        """获取全局信息茧房统计"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 只获取前20个初始普通用户（按创建时间排序，排除Agent和后来添加的角色用户）
            cursor.execute("""
                SELECT user_id FROM users
                WHERE user_id NOT LIKE 'agent%'
                ORDER BY creation_time
                LIMIT 20
            """)
            all_users = [row[0] for row in cursor.fetchall()]

            if not all_users:
                return GlobalBubbleStats(
                    total_users=0,
                    avg_homogeneity=0.0,
                    avg_echo_index=0.0,
                    severe_bubble_users=0,
                    moderate_bubble_users=0,
                    mild_bubble_users=0,
                    network_density=0.0
                )

            # 计算每个用户的指标
            homogeneity_list = []
            echo_index_list = []
            severe_count = 0
            moderate_count = 0
            mild_count = 0

            for user_id in all_users:
                metrics = self.analyze_user_bubble(user_id)
                homogeneity_list.append(metrics.homogeneity_index)
                echo_index_list.append(metrics.echo_chamber_index)

                if metrics.bubble_severity == "severe":
                    severe_count += 1
                elif metrics.bubble_severity == "moderate":
                    moderate_count += 1
                elif metrics.bubble_severity == "mild":
                    mild_count += 1

            # 计算网络密度
            cursor.execute("SELECT COUNT(*) FROM follows")
            total_follows = cursor.fetchone()[0]
            total_users = len(all_users)
            possible_connections = total_users * (total_users - 1)
            network_density = total_follows / possible_connections if possible_connections > 0 else 0.0

            return GlobalBubbleStats(
                total_users=total_users,
                avg_homogeneity=np.mean(homogeneity_list),
                avg_echo_index=np.mean(echo_index_list),
                severe_bubble_users=severe_count,
                moderate_bubble_users=moderate_count,
                mild_bubble_users=mild_count,
                network_density=network_density
            )

        finally:
            conn.close()

    def get_all_user_metrics(self) -> List[UserBubbleMetrics]:
        """获取所有用户的指标"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 只获取前20个初始普通用户（按创建时间排序）
            cursor.execute("""
                SELECT user_id FROM users
                WHERE user_id NOT LIKE 'agent%'
                ORDER BY creation_time
                LIMIT 20
            """)
            all_users = [row[0] for row in cursor.fetchall()]

            return [self.analyze_user_bubble(user_id) for user_id in all_users]

        finally:
            conn.close()
