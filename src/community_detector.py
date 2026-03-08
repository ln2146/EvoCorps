"""
派系分析模块

使用语义向量表示用户和内容，通过向量相似度进行社区发现和派系分析：
- 用户行为向量（评论、点赞、分享）
- 内容语义向量（帖子、评论文本）
- 社交网络向量（关注关系）
- 立场向量（支持/反对/中立）
- 影响向量（传播路径、反应时间）
"""

import sqlite3
from typing import Dict, List, Tuple, Optional, Set, Any
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import networkx as nx


@dataclass
class UserVector:
    """用户的特征向量表示"""
    user_id: str
    # 内容偏好向量（基于交互的帖子内容）
    content_preference: np.ndarray
    # 社交模式向量（基于关注网络）
    social_pattern: np.ndarray
    # 立场倾向向量（支持/反对/中立）
    stance_bias: np.ndarray
    # 活跃度向量（发帖、评论、点赞频率）
    activity_pattern: np.ndarray
    # 综合向量（以上所有维度的组合）
    combined: np.ndarray

    # 元数据
    total_posts: int = 0
    total_comments: int = 0
    total_likes: int = 0
    bubble_index: float = 0.5


@dataclass
class CommunityVector:
    """社区的特征向量表示"""
    community_id: int
    name: str
    members: List[str]
    # 中心向量（所有成员向量的平均）
    centroid: np.ndarray
    # 内容主题向量
    topic_vector: np.ndarray
    # 立场倾向
    stance_distribution: Dict[str, float] = field(default_factory=dict)
    # 紧密度（成员间平均相似度）
    cohesion: float = 0.0
    # 是否为回声室
    is_echo_chamber: bool = False


@dataclass
class PostStanceAnalysis:
    """帖子的立场分析"""
    post_id: str
    total_interactions: int
    # 交互用户的embedding中心
    interaction_centroid: np.ndarray
    # 基于语义相似度的立场分布
    support_ratio: float
    neutral_ratio: float
    oppose_ratio: float
    # 具体评论数量
    support_count: int = 0
    neutral_count: int = 0
    oppose_count: int = 0
    # 高影响力用户列表
    high_influence_users: List[Dict] = field(default_factory=list)
    # 高茧房用户支持比例
    high_bubble_support_ratio: float = 0.0
    # 是否为最火帖子
    is_hottest: bool = False


class CommunityDetector:
    """社区发现与派系分析器"""

    def __init__(self, db_path: str, vector_dim: int = 128):
        """
        Args:
            db_path: 数据库路径
            vector_dim: 向量维度
        """
        self.db_path = db_path
        self.vector_dim = vector_dim
        self.user_vectors: Dict[str, UserVector] = {}
        self.scaler = StandardScaler()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    # ==================== 向量生成 ====================

    def _get_text_vector(self, text: str, model_type: str = 'tfidf') -> np.ndarray:
        """获取文本的特征向量

        Args:
            text: 输入文本
            model_type: 'tfidf', 'bow', 'random', 'hybrid'

        Returns:
            特征向量
        """
        if not text or not text.strip():
            return np.zeros(self.vector_dim)

        # 简化版：使用词频和哈希映射生成向量
        # 实际项目中应该使用预训练的模型

        # 方法1：基于字符哈希的简单向量
        text_bytes = text.encode('utf-8')
        vector = np.zeros(self.vector_dim)

        for i, byte in enumerate(text_bytes):
            # 使用字节值和位置生成哈希
            idx = (byte * (i + 1) * 37) % self.vector_dim
            vector[idx] += 1.0

        # 归一化
        if np.linalg.norm(vector) > 0:
            vector = vector / np.linalg.norm(vector)

        # 方法2：加入词频特征
        words = text.lower().split()
        for word in words:
            word_hash = hash(word) % self.vector_dim
            vector[word_hash] += 0.5

        # L2 归一化
        if np.linalg.norm(vector) > 0:
            vector = vector / np.linalg.norm(vector)

        return vector

    def _generate_content_preference_vector(
        self,
        user_id: str,
        conn: sqlite3.Connection
    ) -> np.ndarray:
        """生成用户内容偏好向量

        基于用户交互的帖子内容
        """
        cursor = conn.cursor()

        # 获取用户发布的帖子
        cursor.execute("""
            SELECT content FROM posts
            WHERE author_id = ?
            LIMIT 20
        """, (user_id,))
        posts = [row[0] for row in cursor.fetchall()]

        # 获取用户评论的帖子
        cursor.execute("""
            SELECT p.content FROM posts p
            JOIN comments c ON p.post_id = c.post_id
            WHERE c.author_id = ?
            LIMIT 20
        """, (user_id,))
        commented_posts = [row[0] for row in cursor.fetchall()]

        # 获取用户点赞的帖子（如果有likes表）
        all_texts = posts + commented_posts

        if not all_texts:
            return np.zeros(self.vector_dim)

        # 计算所有文本embedding的平均
        vectors = [self._get_text_vector(text) for text in all_texts]
        return np.mean(vectors, axis=0)

    def _generate_social_pattern_vector(
        self,
        user_id: str,
        conn: sqlite3.Connection
    ) -> np.ndarray:
        """生成社交模式 embedding

        基于用户的关注网络
        """
        cursor = conn.cursor()

        # 获取关注的人
        cursor.execute("""
            SELECT followed_id FROM follows
            WHERE follower_id = ?
            LIMIT 50
        """, (user_id,))
        following = [row[0] for row in cursor.fetchall()]

        # 获取粉丝
        cursor.execute("""
            SELECT follower_id FROM follows
            WHERE followed_id = ?
            LIMIT 50
        """, (user_id,))
        followers = [row[0] for row in cursor.fetchall()]

        if not following and not followers:
            return np.zeros(self.vector_dim)

        # 基于用户ID生成社交向量
        embedding = np.zeros(self.vector_dim)

        for user in following:
            idx = hash(user) % self.vector_dim
            embedding[idx] += 1.0

        for user in followers:
            idx = hash(user) % self.vector_dim
            embedding[idx] += 0.5  # 粉丝权重稍低

        # 归一化
        if np.linalg.norm(embedding) > 0:
            embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def _generate_stance_bias_vector(
        self,
        user_id: str,
        conn: sqlite3.Connection
    ) -> np.ndarray:
        """生成立场倾向 embedding

        [支持强度, 反对强度, 中立强度, 情绪极化程度]
        """
        cursor = conn.cursor()

        # 获取用户的所有评论
        cursor.execute("""
            SELECT content FROM comments
            WHERE author_id = ?
            LIMIT 50
        """, (user_id,))
        comments = [row[0] for row in cursor.fetchall()]

        if not comments:
            return np.array([0.33, 0.33, 0.34, 0.0])

        # 分析每条评论的立场
        support_count = 0
        oppose_count = 0
        neutral_count = 0
        emotional_intensity = []

        for comment in comments:
            stance, intensity = self._analyze_stance_with_intensity(comment)
            if stance == 'support':
                support_count += 1
            elif stance == 'oppose':
                oppose_count += 1
            else:
                neutral_count += 1
            emotional_intensity.append(intensity)

        total = len(comments)
        stance_vector = np.array([
            support_count / total,
            oppose_count / total,
            neutral_count / total,
            np.mean(emotional_intensity) if emotional_intensity else 0
        ])

        return stance_vector

    def _generate_activity_pattern_vector(
        self,
        user_id: str,
        conn: sqlite3.Connection
    ) -> np.ndarray:
        """生成活跃度模式 embedding

        [发帖频率, 评论频率, 点赞频率, 时段偏好]
        """
        cursor = conn.cursor()

        # 统计活动
        cursor.execute("""
            SELECT
                COUNT(DISTINCT p.post_id) as post_count,
                COUNT(DISTINCT c.comment_id) as comment_count
            FROM users u
            LEFT JOIN posts p ON u.user_id = p.author_id
            LEFT JOIN comments c ON u.user_id = c.author_id
            WHERE u.user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        post_count = result[0] if result else 0
        comment_count = result[1] if result else 0

        # 估算点赞数（从帖子表）
        cursor.execute("""
            SELECT SUM(num_likes) FROM posts
            WHERE author_id = ?
        """, (user_id,))
        received_likes = cursor.fetchone()[0] or 0

        # 归一化到 [0, 1]
        activity_vector = np.array([
            min(post_count / 100.0, 1.0),
            min(comment_count / 500.0, 1.0),
            min(received_likes / 1000.0, 1.0),
            0.5  # 时段偏好（可以进一步细化）
        ])

        return activity_vector

    def _generate_user_vector(
        self,
        user_id: str,
        conn: sqlite3.Connection
    ) -> UserVector:
        """生成用户的综合 embedding

        组合内容偏好、社交模式、立场倾向、活跃度四个维度
        """
        # 生成各维度向量
        content_pref = self._generate_content_preference_vector(user_id, conn)
        social_pattern = self._generate_social_pattern_vector(user_id, conn)
        stance_bias = self._generate_stance_bias_vector(user_id, conn)
        activity_pattern = self._generate_activity_pattern_vector(user_id, conn)

        # 拼接成综合向量
        combined = np.concatenate([
            content_pref,
            social_pattern,
            stance_bias,
            activity_pattern
        ])

        # 确保维度正确
        if len(combined) < self.vector_dim:
            # 填充到指定维度
            combined = np.pad(combined, (0, self.vector_dim - len(combined)))
        elif len(combined) > self.vector_dim:
            # 截断
            combined = combined[:self.vector_dim]

        # 归一化
        if np.linalg.norm(combined) > 0:
            combined = combined / np.linalg.norm(combined)

        # 获取元数据
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM posts WHERE author_id = ?) as post_count,
                (SELECT COUNT(*) FROM comments WHERE author_id = ?) as comment_count
        """, (user_id, user_id))
        row = cursor.fetchone()
        total_posts = row[0] if row else 0
        total_comments = row[1] if row else 0

        # 获取茧房指数
        try:
            from src.filter_bubble_analyzer import FilterBubbleAnalyzer
            analyzer = FilterBubbleAnalyzer(self.db_path)
            metrics = analyzer.analyze_user_bubble(user_id)
            bubble_index = metrics.echo_chamber_index
        except:
            bubble_index = 0.5

        return UserVector(
            user_id=user_id,
            content_preference=content_pref,
            social_pattern=social_pattern,
            stance_bias=stance_bias,
            activity_pattern=activity_pattern,
            combined=combined,
            total_posts=total_posts,
            total_comments=total_comments,
            total_likes=0,
            bubble_index=bubble_index
        )

    # ==================== 立场分析 ====================

    def _analyze_stance_with_intensity(self, text: str) -> Tuple[str, float]:
        """分析文本立场和情绪强度（基于EvoCorps人格数据集的多维度分析）

        Returns:
            (stance, intensity)
            stance: 'support', 'neutral', 'oppose'
            intensity: [0, 1] 情绪强度
        """
        if not text or not text.strip():
            return 'neutral', 0.0

        # ========== 关键词库（基于EvoCorps数据集分析） ==========

        # 强支持关键词 (score +3)
        strong_support = [
            'absolutely', 'definitely', 'strongly support', 'fully support',
            'completely agree', 'totally agree', 'essential', 'critical',
            'crucial', 'imperative', 'unequivocally', 'without reservation',
            'wholeheartedly', 'emphatically', '100%', 'strongly agree',
            'firmly believe', 'no doubt', 'must', 'important'
        ]

        # 支持关键词 (score +1)
        support = [
            'good', 'great', 'agree', 'support', 'yes', 'right', 'correct',
            'excellent', 'perfect', 'love it', 'like', 'approve', 'favor',
            'positive', 'thumbs up', 'endorse', 'back', 'exactly', 'precisely',
            'well said', 'makes sense', 'valid point', 'fair point', 'spot on',
            'thank you', 'thanks', 'helpful', 'useful', 'insightful',
            'appreciate', 'valuable', 'true', 'indeed'
        ]

        # 强反对关键词 (score -3)
        strong_oppose = [
            'strongly oppose', 'absolutely not', 'terrible', 'horrible',
            'disgusting', 'unacceptable', 'reject', 'vehemently oppose',
            'firmly against', 'completely disagree', 'totally disagree',
            'no way', 'never', 'under no circumstances', 'impossible',
            'absurd', 'ridiculous', 'preposterous', 'ludicrous',
            # 愤怒表达（粗口）
            'fuck', 'shit', 'bullshit', 'dammit', 'damn', 'ass'
        ]

        # 反对关键词 (score -1)
        oppose = [
            'disagree', 'problem', 'question', 'issue', 'concern', 'doubt',
            'skeptical', 'suspicious', 'wary', 'hesitant', 'uncertain',
            'unsure', 'not sure', 'bad idea', 'against', 'critical of',
            'troubled', 'unconvinced', 'objection', 'disapprove',
            'fail to see', 'wrong', 'not true', 'incorrect',
            # 质疑/批评
            'side-eye', 'scandal', 'corrupt', 'lying', 'fake',
            'shady', 'sus', 'conspiracy', 'shut up', 'spineless'
        ]

        # 中立关键词 (score 0，但影响判定)
        neutral = [
            'maybe', 'possibly', 'perhaps', 'might be', 'could be',
            'depends', 'it depends', 'not entirely sure', 'need more info',
            'unclear', 'on the fence', 'waiting for evidence', 'interesting',
            'thought', 'wonder', 'curious', 'interesting point'
        ]

        # ========== 语调分析 ==========

        # Hostile/Aggressive语调特征 (反对倾向)
        hostile_indicators = [
            'hate', 'stupid', 'idiot', 'dumb', 'ignorant', 'sheep',
            'scam', 'steal', 'stealing', 'bleed', 'suffer', 'corrupt',
            'bullshit', 'lying', 'fake', 'shut up', 'spineless'
        ]

        # Warm/Friendly语调特征 (支持倾向)
        warm_indicators = ['friendly', 'kind', 'respect', 'understand', 'appreciate']

        # ========== 行为模式 ==========

        # 建设性对话模式 (支持倾向)
        constructive_patterns = [
            'i understand', 'i see your point', 'that makes sense',
            'let me understand', 'fair enough', 'good perspective',
            'valid point', 'respect', 'constructive'
        ]

        # 讽刺挖苦模式 (反对倾向)
        taunting_patterns = [
            'yeah right', 'sure', 'lol', 'sarcasm', 'mock', 'ridicule',
            'you must be joking', 'give me a break', 'whatever'
        ]

        # ========== 开始计算 ==========

        text_lower = text.lower()

        # 1. 关键词得分
        score = 0
        intensity = 0

        for kw in strong_support:
            if kw in text_lower:
                score += 3
                intensity += 0.3
        for kw in support:
            if kw in text_lower:
                score += 1
                intensity += 0.1
        for kw in strong_oppose:
            if kw in text_lower:
                score -= 3
                intensity += 0.3
        for kw in oppose:
            if kw in text_lower:
                score -= 1
                intensity += 0.1

        # 2. 语调分析
        tone_bonus = 0

        # 检测hostile语调（粗口、敌对词汇）
        hostile_count = 0
        for indicator in hostile_indicators:
            if indicator in text_lower:
                hostile_count += text_lower.count(indicator)

        if hostile_count > 0:
            tone_bonus -= hostile_count * 0.8  # 每个敌对词汇-0.8分
            intensity += min(hostile_count * 0.3, 0.6)  # 增加强度

        # 检测warm语调
        for indicator in warm_indicators:
            if indicator in text_lower:
                tone_bonus += 0.5

        # 3. 行为模式分析
        behavior_bonus = 0

        # 建设性对话
        for pattern in constructive_patterns:
            if pattern in text_lower:
                behavior_bonus += 2
                intensity += 0.2

        # 讽刺挖苦
        for pattern in taunting_patterns:
            if pattern in text_lower:
                behavior_bonus -= 2
                intensity += 0.3

        # 4. 情绪强度计算（标点符号密度）
        punctuation_count = text.count('!') + text.count('?')
        word_count = len(text.split())
        if word_count > 0:
            punctuation_density = punctuation_count / word_count
            intensity += min(punctuation_density * 0.5, 0.4)

        # 全大写检测（表示强烈情绪）
        is_all_caps = text.isupper() and len(text) > 3
        if is_all_caps:
            intensity += 0.5
            # 如果全大写且有粗口，强烈倾向于oppose
            if hostile_count > 0:
                tone_bonus -= 2.0

        # 5. 愤怒质问模式（全大写 + 多个!? + 粗口）
        has_angry_rant = (
            is_all_caps and
            punctuation_count > 3 and
            hostile_count > 0
        )
        if has_angry_rant:
            tone_bonus -= 3.0  # 强烈反对
            intensity = min(intensity + 0.3, 1.0)

        # ========== 综合判定 ==========

        # 归一化强度
        intensity = min(intensity, 1.0)

        # 计算总分
        total_score = score + tone_bonus + (behavior_bonus * 0.3)

        # 判定阈值（调整后）
        if total_score > 0.5:
            return 'support', intensity
        elif total_score < -0.3:  # 降低反对阈值，更容易识别反对
            return 'oppose', intensity
        else:
            return 'neutral', intensity * 0.5

    # ==================== 社区发现（基于Embedding） ====================

    def detect_communities(
        self,
        method: str = 'dbscan',
        n_clusters: int = 5,
        min_samples: int = 3
    ) -> List[CommunityVector]:
        """基于用户 embedding 进行社区发现

        Args:
            method: 聚类方法 ('dbscan', 'kmeans', 'hierarchical')
            n_clusters: KMeans的簇数量
            min_samples: DBSCAN的最小样本数

        Returns:
            社区列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取所有用户
            cursor.execute("SELECT user_id FROM users")
            users = [row[0] for row in cursor.fetchall()]

            if not users:
                return []

            # 生成所有用户的embedding
            print(f"正在为 {len(users)} 个用户生成 embedding...")
            user_vectors = []
            user_ids = []

            for user_id in users:
                vector = self._generate_user_vector(user_id, conn)
                user_vectors.append(vector)
                user_ids.append(user_id)
                self.user_vectors[user_id] = vector

            # 转换为矩阵
            X = np.array([e.combined for e in user_vectors])

            # 标准化
            X_scaled = self.scaler.fit_transform(X)

            # 聚类
            if method == 'dbscan':
                # DBSCAN（自动确定社区数量），放宽 eps 以适应仿真数据
                clusterer = DBSCAN(eps=0.8, min_samples=min(min_samples, 2), metric='cosine')
                labels = clusterer.fit_predict(X_scaled)
                # 如果 DBSCAN 全部标为噪声（无社区），自动回退到 KMeans
                if all(l == -1 for l in labels):
                    print("[CommunityDetector] DBSCAN 未发现社区，回退到 KMeans")
                    actual_k = min(n_clusters, len(users))
                    clusterer = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
                    labels = clusterer.fit_predict(X_scaled)
            elif method == 'kmeans':
                # K-Means（需要指定社区数量）
                clusterer = KMeans(n_clusters=min(n_clusters, len(users)), random_state=42, n_init=10)
                labels = clusterer.fit_predict(X_scaled)
            elif method == 'hierarchical':
                # 层次聚类
                clusterer = AgglomerativeClustering(
                    n_clusters=n_clusters,
                    metric='cosine',
                    linkage='average'
                )
                labels = clusterer.fit_predict(X_scaled)
            else:
                raise ValueError(f"未知的聚类方法: {method}")

            # 组织结果
            communities = defaultdict(list)
            for user_id, label in zip(user_ids, labels):
                if label >= 0:  # 忽略噪声点（DBSCAN中的-1）
                    communities[label].append(user_id)

            # 为每个社区生成embedding
            community_list = []
            for cluster_id, members in communities.items():
                if len(members) < 2:  # 跳过太小社区
                    continue

                # 计算社区中心
                member_embeddings = [self.user_vectors[m] for m in members]
                centroid = np.mean([v.combined for v in member_embeddings], axis=0)

                # 计算紧密度（成员间平均相似度）
                similarities = cosine_similarity(
                    [v.combined for v in member_embeddings]
                )
                # 取上三角矩阵的平均值（排除对角线）
                cohesion = np.mean(np.triu(similarities, k=1))

                # 分析主题和立场
                topic_vector = self._compute_community_topic(members, conn)
                stance_dist = self._compute_community_stance(members, conn)

                # 判断是否为回声室
                is_echo_chamber = cohesion > 0.7 and stance_dist.get('dominant', 0) > 0.8

                # 命名社区
                name = self._name_community_from_embedding(
                    topic_vector, stance_dist, len(members)
                )

                community = CommunityVector(
                    community_id=cluster_id,
                    name=name,
                    members=members,
                    centroid=centroid,
                    topic_vector=topic_vector,
                    stance_distribution=stance_dist,
                    cohesion=cohesion,
                    is_echo_chamber=is_echo_chamber
                )
                community_list.append(community)

            return community_list

        finally:
            conn.close()

    def _compute_community_topic(
        self,
        members: List[str],
        conn: sqlite3.Connection
    ) -> np.ndarray:
        """计算社区的话题向量"""
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in members])
        cursor.execute(f"""
            SELECT content FROM posts
            WHERE author_id IN ({placeholders})
            LIMIT 50
        """, members)

        texts = [row[0] for row in cursor.fetchall()]

        if not texts:
            return np.zeros(self.vector_dim)

        vectors = [self._get_text_vector(text) for text in texts]
        return np.mean(vectors, axis=0)

    def _compute_community_stance(
        self,
        members: List[str],
        conn: sqlite3.Connection
    ) -> Dict[str, float]:
        """计算社区的立场分布"""
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in members])
        cursor.execute(f"""
            SELECT content FROM comments
            WHERE author_id IN ({placeholders})
            LIMIT 100
        """, members)

        comments = [row[0] for row in cursor.fetchall()]

        if not comments:
            return {'support': 0.33, 'neutral': 0.34, 'oppose': 0.33, 'dominant': 0}

        stance_counts = {'support': 0, 'neutral': 0, 'oppose': 0}

        for comment in comments:
            stance, _ = self._analyze_stance_with_intensity(comment)
            stance_counts[stance] += 1

        total = sum(stance_counts.values())
        distribution = {k: v/total for k, v in stance_counts.items()}

        # 计算主导立场
        distribution['dominant'] = max(distribution['support'],
                                       distribution['neutral'],
                                       distribution['oppose'])

        return distribution

    def _name_community_from_embedding(
        self,
        topic_vector: np.ndarray,
        stance_dist: Dict[str, float],
        size: int
    ) -> str:
        """基于embedding给社区命名"""
        # 根据大小
        if size > 50:
            size_label = "大众群体"
        elif size > 20:
            size_label = "活跃社群"
        elif size > 5:
            size_label = "核心圈层"
        else:
            size_label = "小团体"

        # 根据立场
        dominant = stance_dist.get('dominant', 0)
        if dominant > 0.7:
            if stance_dist['support'] > 0.7:
                stance_label = "支持派"
            elif stance_dist['oppose'] > 0.7:
                stance_label = "反对派"
            else:
                stance_label = "中立派"
            return f"{size_label}-{stance_label}"
        else:
            return size_label

    # ==================== 帖子派系分析（基于Embedding） ====================

    def analyze_post_stances(
        self,
        limit: int = 15,
        min_comments: int = 3
    ) -> List[PostStanceAnalysis]:
        """基于embedding分析帖子的派系分布（智能选择帖子）

        智能选择策略：
        1. 选取15条帖子，涵盖支持多、中立多、反对多的不同类型
        2. 单独标记最火帖子（按总互动数）

        使用交互用户的embedding相似度来判断立场
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取所有有足够评论的帖子
            cursor.execute("""
                SELECT post_id, num_comments, num_likes, num_shares
                FROM posts
                WHERE num_comments >= ?
                ORDER BY num_comments DESC
            """, (min_comments,))

            all_posts = cursor.fetchall()

            if not all_posts:
                return []

            # 第一步：对所有帖子进行快速立场分析
            post_analysis_cache = {}
            support_dominant = []
            neutral_dominant = []
            oppose_dominant = []

            for post_id, num_comments, num_likes, num_shares in all_posts:
                result = self._analyze_single_post_stance(post_id, conn)
                if result:
                    post_analysis_cache[post_id] = result
                    total_interactions = num_comments + num_likes + num_shares
                    result.total_interactions = total_interactions

                    # 按主导立场分类（使用相对主导，而非绝对阈值）
                    # 策略：找到最高的比例，且该比例至少达到30%
                    max_ratio = max(result.support_ratio, result.neutral_ratio, result.oppose_ratio)

                    if max_ratio < 0.30:
                        # 如果没有明显主导，归为中立
                        neutral_dominant.append((post_id, result, total_interactions))
                    elif result.support_ratio == max_ratio:
                        support_dominant.append((post_id, result, total_interactions))
                    elif result.oppose_ratio == max_ratio:
                        oppose_dominant.append((post_id, result, total_interactions))
                    else:
                        neutral_dominant.append((post_id, result, total_interactions))

            # 第二步：从每个类别中选择代表性帖子
            selected_posts = []

            # 策略：尽量平衡选择，每类至少5条，总共15条
            # 按互动数排序，选择每类中最火的帖子
            support_dominant.sort(key=lambda x: x[2], reverse=True)
            neutral_dominant.sort(key=lambda x: x[2], reverse=True)
            oppose_dominant.sort(key=lambda x: x[2], reverse=True)

            # 分配配额：根据各类别数量动态分配
            total_available = len(support_dominant) + len(neutral_dominant) + len(oppose_dominant)

            if total_available <= limit:
                # 如果总帖子数不足limit，全部返回
                for post_id, result, _ in support_dominant + neutral_dominant + oppose_dominant:
                    selected_posts.append(result)
            else:
                # 智能分配配额：确保每类至少5条，且按实际数量比例分配
                def allocate_quota(support_count, neutral_count, oppose_count, total_limit):
                    """智能分配每类别的帖子配额，确保涵盖所有立场类型"""
                    # 基础配额：每类至少5条（15条/3类）
                    base_quota = 5
                    remaining = total_limit - (base_quota * 3)

                    if remaining <= 0:
                        return (min(support_count, base_quota),
                                min(neutral_count, base_quota),
                                min(oppose_count, base_quota))

                    # 剩余配额按比例分配
                    total = support_count + neutral_count + oppose_count
                    support_extra = int((support_count / total) * remaining)
                    neutral_extra = int((neutral_count / total) * remaining)
                    oppose_extra = remaining - support_extra - neutral_extra  # 确保总和正确

                    return (
                        min(support_count, base_quota + support_extra),
                        min(neutral_count, base_quota + neutral_extra),
                        min(oppose_count, base_quota + oppose_extra)
                    )

                support_quota, neutral_quota, oppose_quota = allocate_quota(
                    len(support_dominant),
                    len(neutral_dominant),
                    len(oppose_dominant),
                    limit
                )

                # 选择帖子
                selected_posts.extend([r for _, r, _ in support_dominant[:support_quota]])
                selected_posts.extend([r for _, r, _ in neutral_dominant[:neutral_quota]])
                selected_posts.extend([r for _, r, _ in oppose_dominant[:oppose_quota]])

            # 第三步：找出最火的帖子并标记
            if selected_posts:
                hottest_post = max(selected_posts, key=lambda p: p.total_interactions)
                hottest_post.is_hottest = True  # 添加标记

            return selected_posts

        finally:
            conn.close()

    def _analyze_single_post_stance(
        self,
        post_id: str,
        conn: sqlite3.Connection
    ) -> Optional[PostStanceAnalysis]:
        """分析单个帖子的立场分布

        优化：综合考虑评论内容、点赞行为、关注关系来判定立场
        """
        cursor = conn.cursor()

        # 获取帖子内容
        cursor.execute("SELECT content, author_id, created_at FROM posts WHERE post_id = ?", (post_id,))
        post_data = cursor.fetchone()
        if not post_data:
            return None

        post_content, post_author, post_created_at = post_data

        # 生成帖子的embedding
        post_vector = self._get_text_vector(post_content)

        # 获取所有评论
        cursor.execute("""
            SELECT author_id, content, created_at FROM comments
            WHERE post_id = ?
            ORDER BY created_at
        """, (post_id,))

        comments = cursor.fetchall()

        if not comments:
            return None

        # 分析每条评论的立场和embedding
        user_vectors = []
        stance_scores = []

        for author_id, content, comment_created_at in comments:
            # 1. 基于评论内容的初始立场分析
            stance, intensity = self._analyze_stance_with_intensity(content)

            # 2. 获取点赞行为（如果likes表存在）
            has_liked = False
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM likes
                    WHERE user_id = ? AND post_id = ?
                """, (author_id, post_id))
                has_liked = cursor.fetchone()[0] > 0
            except sqlite3.OperationalError:
                # likes表不存在，跳过点赞检测
                pass

            # 3. 获取关注关系及时间
            cursor.execute("""
                SELECT created_at FROM follows
                WHERE follower_id = ? AND followed_id = ?
                ORDER BY created_at ASC
                LIMIT 1
            """, (author_id, post_author))
            follow_result = cursor.fetchone()

            # 4. 综合行为加权调整立场
            if has_liked:
                # 点赞：强烈支持信号，大幅加权
                if stance == 'support':
                    intensity = min(1.0, intensity + 0.4)  # 提升情绪强度
                elif stance == 'neutral':
                    stance = 'support'  # 中立转支持
                    intensity = 0.6
                elif stance == 'oppose':
                    # 反对但点赞，转为中立
                    stance = 'neutral'
                    intensity = intensity * 0.5

            if follow_result:
                follow_created_at = follow_result[0]

                # 判断关注时间与帖子创建时间的关系
                if follow_created_at and post_created_at:
                    try:
                        follow_time = datetime.fromisoformat(follow_created_at.replace('Z', '+00:00'))
                        post_time = datetime.fromisoformat(post_created_at.replace('Z', '+00:00'))

                        if follow_time > post_time:
                            # 帖子发布后才关注：通过帖子关注，高支持权重
                            if stance == 'support':
                                intensity = min(1.0, intensity + 0.3)
                            elif stance == 'neutral':
                                stance = 'support'
                                intensity = 0.5
                            elif stance == 'oppose':
                                # 反对但关注了，转为中立
                                stance = 'neutral'
                                intensity = intensity * 0.6
                        else:
                            # 帖子发布前就关注：已有关系，少量支持权重
                            if stance == 'neutral':
                                stance = 'support'
                                intensity = 0.3
                            elif stance == 'support':
                                intensity = min(1.0, intensity + 0.1)
                    except:
                        # 时间解析失败，忽略时间因素
                        pass
                else:
                    # 无法判断时间，给予少量支持权重
                    if stance == 'neutral':
                        stance = 'support'
                        intensity = 0.2

            # 生成用户的embedding（如果还没生成）
            if author_id not in self.user_vectors:
                user_vec = self._generate_user_vector(author_id, conn)
                self.user_vectors[author_id] = user_vec
            else:
                user_vec = self.user_vectors[author_id]

            user_vectors.append((author_id, user_vec, stance, intensity))
            stance_scores.append(stance)

        # 计算立场分布
        total = len(stance_scores)
        support_count = stance_scores.count('support')
        oppose_count = stance_scores.count('oppose')
        neutral_count = stance_scores.count('neutral')

        # 计算交互中心向量
        interaction_vectors = [emb.combined for _, emb, _, _ in user_vectors]
        interaction_centroid = np.mean(interaction_vectors, axis=0)

        # 计算影响力
        high_influence = self._calculate_influence_by_vector(
            post_vector, user_vectors
        )

        # 计算高茧房用户支持比例
        high_bubble_users = [
            (uid, emb, stance) for uid, emb, stance, _ in user_vectors
            if emb.bubble_index > 0.6
        ]

        high_bubble_support = (
            sum(1 for _, _, stance in high_bubble_users if stance == 'support') /
            len(high_bubble_users) if high_bubble_users else 0
        )

        return PostStanceAnalysis(
            post_id=post_id,
            total_interactions=total,
            support_ratio=support_count / total,
            neutral_ratio=neutral_count / total,
            oppose_ratio=oppose_count / total,
            support_count=support_count,
            neutral_count=neutral_count,
            oppose_count=oppose_count,
            interaction_centroid=interaction_centroid,
            high_influence_users=high_influence,
            high_bubble_support_ratio=high_bubble_support
        )

    def _calculate_influence_by_vector(
        self,
        post_vec: np.ndarray,
        user_vectors: List[Tuple[str, UserVector, str, float]]
    ) -> List[Dict]:
        """基于embedding计算影响力

        用户embedding与帖子embedding的相似度越高，受影响越大
        """
        influence_list = []

        # 计算每个用户与帖子的余弦相似度
        post_vec_norm = post_vec / (np.linalg.norm(post_vec) + 1e-8)

        for user_id, user_vec, stance, intensity in user_vectors:
            # 内容偏好相似度
            content_sim = np.dot(user_vec.content_preference, post_vec_norm)

            # 立场一致性
            stance_score = 1.0 if stance == 'support' else (0.5 if stance == 'neutral' else 0.0)

            # 综合影响力分数
            influence = (
                content_sim * 0.6 +  # 内容相似度
                stance_score * 0.3 +  # 立场一致性
                intensity * 0.1 +      # 情绪强度
                user_vec.bubble_index * 0.2  # 茧房指数加成
            )

            influence = max(0, min(1, influence))

            if influence > 0.6:  # 只保留高影响力用户
                influence_list.append({
                    'user_id': user_id,
                    'score': influence,
                    'stance': stance,
                    'bubble_index': user_vec.bubble_index
                })

        # 排序并返回前5个
        influence_list.sort(key=lambda x: x['score'], reverse=True)
        return influence_list[:5]

    # ==================== 工具方法 ====================

    def get_user_similarity(self, user_id1: str, user_id2: str) -> float:
        """计算两个用户的相似度

        Returns:
            余弦相似度 [0, 1]
        """
        conn = self._get_connection()

        try:
            # 获取或生成embedding
            if user_id1 not in self.user_vectors:
                self.user_vectors[user_id1] = self._generate_user_vector(user_id1, conn)
            if user_id2 not in self.user_vectors:
                self.user_vectors[user_id2] = self._generate_user_vector(user_id2, conn)

            emb1 = self.user_vectors[user_id1].combined
            emb2 = self.user_vectors[user_id2].combined

            # 余弦相似度
            similarity = np.dot(emb1, emb2) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
            )

            return float(similarity)

        finally:
            conn.close()

    def find_similar_users(
        self,
        user_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """找到与指定用户最相似的用户

        Returns:
            [(user_id, similarity), ...]
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 生成目标用户的embedding
            if user_id not in self.user_vectors:
                self.user_vectors[user_id] = self._generate_user_vector(user_id, conn)

            target_emb = self.user_vectors[user_id].combined

            # 获取所有其他用户
            cursor.execute("SELECT user_id FROM users WHERE user_id != ?", (user_id,))
            other_users = [row[0] for row in cursor.fetchall()]

            similarities = []
            for other_id in other_users:
                if other_id not in self.user_vectors:
                    self.user_vectors[other_id] = self._generate_user_vector(other_id, conn)

                other_emb = self.user_vectors[other_id].combined

                sim = np.dot(target_emb, other_emb) / (
                    np.linalg.norm(target_emb) * np.linalg.norm(other_emb) + 1e-8
                )

                similarities.append((other_id, float(sim)))

            # 排序并返回top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

        finally:
            conn.close()

    def get_community_report(self) -> Dict:
        """获取完整的社区分析报告"""
        communities = self.detect_communities()

        if not communities:
            return {
                'num_communities': 0,
                'communities': [],
                'total_users': len(self.user_vectors)
            }

        # 统计信息
        total_users = sum(len(c.members) for c in communities)

        # 按大小排序
        communities_sorted = sorted(communities, key=lambda x: len(x.members), reverse=True)

        return {
            'num_communities': len(communities),
            'total_users': total_users,
            'avg_community_size': total_users / len(communities) if communities else 0,
            'max_community_size': max(len(c.members) for c in communities) if communities else 0,
            'num_echo_chambers': sum(1 for c in communities if c.is_echo_chamber),
            'avg_cohesion': float(np.mean([c.cohesion for c in communities])),
            'communities': [
                {
                    'id': int(c.community_id),
                    'name': c.name,
                    'size': len(c.members),
                    'cohesion': float(c.cohesion),
                    'stance_distribution': {k: float(v) for k, v in c.stance_distribution.items()},
                    'is_echo_chamber': bool(c.is_echo_chamber),
                    'members': c.members
                }
                for c in communities_sorted
            ]
        }

    def get_post_stances_summary(
        self,
        limit: int = 10,
        min_comments: int = 3
    ) -> Dict:
        """获取帖子立场分析汇总（智能选择10条帖子+最火帖子特别分析）"""
        post_stances = self.analyze_post_stances(limit, min_comments)

        if not post_stances:
            return {
                'total_posts_analyzed': 0,
                'post_stances': [],
                'hottest_post': None,
                'method': 'embedding'
            }

        # 计算平均统计
        avg_support = np.mean([p.support_ratio for p in post_stances])
        avg_neutral = np.mean([p.neutral_ratio for p in post_stances])
        avg_oppose = np.mean([p.oppose_ratio for p in post_stances])
        avg_bubble_support = np.mean([p.high_bubble_support_ratio for p in post_stances])

        # 找出最火的帖子
        hottest_post = next((p for p in post_stances if p.is_hottest), None)

        # 找出最具分歧和共识的帖子
        most_divisive = max(
            post_stances,
            key=lambda p: min(p.support_ratio, p.oppose_ratio)
        )

        most_consensus = max(
            post_stances,
            key=lambda p: max(p.support_ratio, p.neutral_ratio, p.oppose_ratio)
        )

        return {
            'total_posts_analyzed': len(post_stances),
            'avg_support_ratio': float(avg_support),
            'avg_neutral_ratio': float(avg_neutral),
            'avg_oppose_ratio': float(avg_oppose),
            'high_bubble_support_ratio': float(avg_bubble_support),
            'hottest_post': {
                'post_id': hottest_post.post_id,
                'total_interactions': hottest_post.total_interactions,
                'support_ratio': float(hottest_post.support_ratio),
                'neutral_ratio': float(hottest_post.neutral_ratio),
                'oppose_ratio': float(hottest_post.oppose_ratio),
                'high_influence_users': hottest_post.high_influence_users,
                'high_bubble_support_ratio': float(hottest_post.high_bubble_support_ratio)
            } if hottest_post else None,
            'most_divisive_post': {
                'post_id': most_divisive.post_id,
                'support_ratio': float(most_divisive.support_ratio),
                'oppose_ratio': float(most_divisive.oppose_ratio),
                'total_interactions': most_divisive.total_interactions
            },
            'most_consensus_post': {
                'post_id': most_consensus.post_id,
                'dominant_stance': 'support' if most_consensus.support_ratio > 0.5 else
                                   'neutral' if most_consensus.neutral_ratio > 0.5 else 'oppose',
                'ratio': float(max(most_consensus.support_ratio,
                                  most_consensus.neutral_ratio,
                                  most_consensus.oppose_ratio)),
                'total_interactions': most_consensus.total_interactions
            },
            'post_stances': [
                {
                    'post_id': p.post_id,
                    'total_interactions': p.total_interactions,
                    'total_comments': int(p.support_count + p.neutral_count + p.oppose_count),  # 添加评论总数
                    'support_ratio': float(p.support_ratio),
                    'neutral_ratio': float(p.neutral_ratio),
                    'oppose_ratio': float(p.oppose_ratio),
                    'support_count': p.support_count,
                    'neutral_count': p.neutral_count,
                    'oppose_count': p.oppose_count,
                    'high_influence_users': p.high_influence_users,
                    'high_bubble_support_ratio': float(p.high_bubble_support_ratio),
                    'is_hottest': p.is_hottest
                }
                for p in post_stances
            ],
            'method': 'embedding'
        }
