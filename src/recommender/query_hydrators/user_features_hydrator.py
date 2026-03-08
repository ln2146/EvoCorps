"""
用户特征水合器

阶段1: 获取用户画像和 Embedding
"""

import ast
import logging
from typing import Optional, List
from ..types import UserContext
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserFeaturesHydrator:
    """
    用户特征水合器

    获取用户画像信息，可选计算 persona embedding
    """

    def __init__(self, embedding_manager=None):
        """
        初始化

        Args:
            embedding_manager: 可选的 EmbeddingManager 实例
        """
        self.user_repo = UserRepository()
        self.embedding_manager = embedding_manager

    def set_embedding_manager(self, embedding_manager):
        """设置 EmbeddingManager"""
        self.embedding_manager = embedding_manager

    def hydrate(self, user_context: UserContext) -> UserContext:
        """
        水合用户特征

        Args:
            user_context: 已有的用户上下文

        Returns:
            填充了画像信息的 UserContext
        """
        # 获取用户画像
        persona_data = self.user_repo.get_user_persona(user_context.user_id)

        if persona_data:
            raw_persona = persona_data.get('persona')
            if raw_persona:
                # 将 persona 转换为有意义的文本（提取 background 等关键字段）
                user_context.persona = self._extract_persona_text(raw_persona)

            # 如果有 embedding manager，计算 persona embedding
            if self.embedding_manager and user_context.persona:
                user_context.persona_embedding = self._compute_persona_embedding(
                    user_context.persona
                )

        return user_context

    def _extract_persona_text(self, raw_persona) -> str:
        """
        从原始 persona 数据中提取有意义的文本

        数据库中存储的 persona 可能是字典字符串格式，需要提取
        background、personality_traits 等关键字段用于 embedding 计算。

        Args:
            raw_persona: 原始 persona 数据（可能是字符串或字典）

        Returns:
            用于 embedding 计算的有意义文本
        """
        import ast

        # 如果已经是字符串，尝试解析为字典
        persona_dict = raw_persona
        if isinstance(raw_persona, str):
            try:
                persona_dict = ast.literal_eval(raw_persona)
            except (ValueError, SyntaxError):
                # 如果解析失败，直接返回原始字符串
                return raw_persona

        # 如果是字典，提取关键字段
        if isinstance(persona_dict, dict):
            parts = []

            # 提取 background（核心描述）
            if 'background' in persona_dict:
                parts.append(persona_dict['background'])

            # 提取 personality_traits
            if 'personality_traits' in persona_dict:
                traits = persona_dict['personality_traits']
                if isinstance(traits, list):
                    parts.extend(traits)

            # 提取 name 和 profession 作为上下文
            if 'name' in persona_dict and 'profession' in persona_dict:
                parts.insert(0, f"{persona_dict['name']}, a {persona_dict['profession']}")

            return '. '.join(parts) if parts else str(persona_dict)

        # 其他情况，直接返回字符串形式
        return str(raw_persona)

    def _compute_persona_embedding(self, persona: str) -> Optional[List[float]]:
        """
        计算 persona 的 embedding

        Args:
            persona: 用户画像文本

        Returns:
            embedding 向量

        Raises:
            RuntimeError: If embedding_manager is not set or encoding fails
        """
        # NO FALLBACK: Require embedding_manager to be set
        if not self.embedding_manager:
            raise RuntimeError(
                "UserFeaturesHydrator._compute_persona_embedding() called but embedding_manager is None. "
                "Either disable embedding in config or ensure embedding_manager is properly initialized."
            )

        # NO FALLBACK: Propagate encoding errors instead of returning None
        return self.embedding_manager.encode_text(persona)
