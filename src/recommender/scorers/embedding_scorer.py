"""
Embedding 评分器

阶段5: 基于 Embedding 相似度计算分数
替代 X 算法的 Grok Transformer 实时预测

支持双层 Embedding:
- 本地 sentence-transformers (默认)
- OpenAI Embedding API (可选)
"""

from typing import List, Optional
from ..types import PostCandidate, UserContext
from ..config import EmbeddingConfig
from ..embedding.embedding_manager import get_embedding_manager


class EmbeddingScorer:
    """
    Embedding 评分器

    双层架构:
    - 本地层: sentence-transformers 轻量模型，CPU 友好
    - 云端层: OpenAI Embedding API，精度更高

    替代 X 算法的 Grok Transformer 实时预测概率
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.embedding_manager = None

        if config.enabled:
            self._init_embedding_manager()

    def _init_embedding_manager(self):
        """延迟初始化 EmbeddingManager"""
        self.embedding_manager = get_embedding_manager(
            model_name=self.config.model_name,
            cache_embeddings=self.config.cache_embeddings,
            max_cache_size=self.config.max_cache_size,
            use_openai_embedding=self.config.use_openai_embedding,
            openai_model_name=self.config.openai_model_name
        )

    def score(
        self,
        candidates: List[PostCandidate],
        user_context: UserContext
    ) -> List[PostCandidate]:
        """
        计算 Embedding 相似度分数

        Args:
            candidates: 候选帖子列表
            user_context: 用户上下文

        Returns:
            填充了 embedding_score 的候选帖子列表
        """
        if not self.config.enabled or not self.embedding_manager:
            return candidates

        # 如果用户没有 persona embedding，尝试从 persona 文本计算
        user_embedding = user_context.persona_embedding
        if user_embedding is None and user_context.persona:
            user_embedding = self.embedding_manager.encode_text(user_context.persona)

        if user_embedding is None:
            return candidates

        for c in candidates:
            # 获取帖子 embedding
            post_embedding = self.embedding_manager.get_or_compute_embedding(
                c.post_id,
                c.content
            )

            if post_embedding is not None:
                # 计算余弦相似度
                similarity = self._cosine_similarity(user_embedding, post_embedding)
                c.embedding_score = similarity

                # 融合到最终分数
                # final_score = weighted_score × (1 - weight) + similarity × weight × weighted_score
                c.final_score = (
                    c.weighted_score * (1 - self.config.embedding_weight) +
                    similarity * self.config.embedding_weight * c.weighted_score
                )

        return candidates

    def _cosine_similarity(
        self,
        a: List[float],
        b: List[float]
    ) -> float:
        """
        计算余弦相似度

        Args:
            a: 向量 a
            b: 向量 b

        Returns:
            相似度 [-1, 1]
        """
        import numpy as np
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot_product = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))
