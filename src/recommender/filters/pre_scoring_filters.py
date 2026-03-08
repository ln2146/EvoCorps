"""
预评分过滤器

阶段4: 在评分前过滤不合格的候选帖子
"""

from collections import Counter
from typing import Any, Dict, List, Tuple
from ..types import PostCandidate, UserContext
from ..config import FilterConfig


class PreScoringFilters:
    """
    预评分过滤器

    在评分阶段之前过滤掉不合格的候选帖子
    """

    def filter(
        self,
        candidates: List[PostCandidate],
        user_context: UserContext,
        config: FilterConfig
    ) -> List[PostCandidate]:
        """
        应用所有预评分过滤器

        Args:
            candidates: 候选帖子列表
            user_context: 用户上下文
            config: 过滤器配置

        Returns:
            过滤后的候选帖子列表
        """
        filtered = candidates

        # 1. 去重过滤
        filtered = self._drop_duplicates(filtered)

        # 2. 自己帖子过滤
        if config.filter_self_posts:
            filtered = self._filter_self_posts(filtered, user_context.user_id)

        # 3. 已下架过滤
        if config.filter_taken_down:
            filtered = self._filter_taken_down(filtered)

        # 4. 屏蔽作者过滤
        if config.filter_blocked_authors:
            filtered = self._filter_blocked_authors(filtered, user_context.blocked_ids)

        # 5. 已曝光过滤 (可选)
        if config.filter_seen_posts:
            filtered = self._filter_seen_posts(filtered, user_context.seen_post_ids)

        # 6. 屏蔽关键词过滤
        if user_context.muted_keywords:
            filtered = self._filter_muted_keywords(filtered, user_context.muted_keywords)

        # 7. 最小内容长度过滤
        if config.min_content_length > 0:
            filtered = self._filter_min_content_length(filtered, config.min_content_length)

        return filtered

    def filter_with_audit(
        self,
        candidates: List[PostCandidate],
        user_context: UserContext,
        config: FilterConfig
    ) -> Tuple[List[PostCandidate], List[Dict[str, Any]]]:
        """
        应用所有预评分过滤器，同时返回每条过滤原因的审计日志

        Returns:
            (filtered_candidates, audit_log)
            audit_log 每项: {post_id, author_id, reason}
        """
        audit: List[Dict[str, Any]] = []
        current = list(candidates)

        # 1. 去重
        seen_ids: set = set()
        after: List[PostCandidate] = []
        for c in current:
            if c.post_id in seen_ids:
                audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'duplicate'})
            else:
                seen_ids.add(c.post_id)
                after.append(c)
        current = after

        # 2. 自己帖子
        if config.filter_self_posts:
            after = []
            for c in current:
                if c.author_id == user_context.user_id:
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'self_post'})
                else:
                    after.append(c)
            current = after

        # 3. 已下架
        if config.filter_taken_down:
            after = []
            for c in current:
                if c.status == 'taken_down':
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'taken_down'})
                else:
                    after.append(c)
            current = after

        # 4. 屏蔽作者
        if config.filter_blocked_authors and user_context.blocked_ids:
            after = []
            for c in current:
                if c.author_id in user_context.blocked_ids:
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'blocked_author'})
                else:
                    after.append(c)
            current = after

        # 5. 已曝光
        if config.filter_seen_posts and user_context.seen_post_ids:
            after = []
            for c in current:
                if c.post_id in user_context.seen_post_ids:
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'already_seen'})
                else:
                    after.append(c)
            current = after

        # 6. 屏蔽关键词
        if user_context.muted_keywords:
            def _has_muted(content: str) -> bool:
                cl = (content or '').lower()
                return any(kw.lower() in cl for kw in user_context.muted_keywords)
            after = []
            for c in current:
                if _has_muted(c.content):
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'muted_keyword'})
                else:
                    after.append(c)
            current = after

        # 7. 最小内容长度
        if config.min_content_length > 0:
            after = []
            for c in current:
                if len(c.content or '') < config.min_content_length:
                    audit.append({'post_id': c.post_id, 'author_id': c.author_id, 'reason': 'too_short'})
                else:
                    after.append(c)
            current = after

        return current, audit

    def _drop_duplicates(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """去重过滤"""
        seen = set()
        unique = []
        for c in candidates:
            if c.post_id not in seen:
                seen.add(c.post_id)
                unique.append(c)
        return unique

    def _filter_self_posts(
        self,
        candidates: List[PostCandidate],
        user_id: str
    ) -> List[PostCandidate]:
        """过滤自己的帖子"""
        return [c for c in candidates if c.author_id != user_id]

    def _filter_taken_down(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """过滤已下架帖子"""
        return [c for c in candidates if c.status != 'taken_down']

    def _filter_blocked_authors(
        self,
        candidates: List[PostCandidate],
        blocked_ids: set
    ) -> List[PostCandidate]:
        """过滤屏蔽作者的帖子"""
        if not blocked_ids:
            return candidates
        return [c for c in candidates if c.author_id not in blocked_ids]

    def _filter_seen_posts(
        self,
        candidates: List[PostCandidate],
        seen_post_ids: set
    ) -> List[PostCandidate]:
        """过滤已曝光帖子"""
        if not seen_post_ids:
            return candidates
        return [c for c in candidates if c.post_id not in seen_post_ids]

    def _filter_muted_keywords(
        self,
        candidates: List[PostCandidate],
        muted_keywords: List[str]
    ) -> List[PostCandidate]:
        """过滤包含屏蔽关键词的帖子"""
        if not muted_keywords:
            return candidates

        def contains_muted_keyword(content: str) -> bool:
            content_lower = (content or '').lower()
            return any(kw.lower() in content_lower for kw in muted_keywords)

        return [c for c in candidates if not contains_muted_keyword(c.content)]

    def _filter_min_content_length(
        self,
        candidates: List[PostCandidate],
        min_length: int
    ) -> List[PostCandidate]:
        """过滤内容长度不足的帖子"""
        return [c for c in candidates if len(c.content or '') >= min_length]
