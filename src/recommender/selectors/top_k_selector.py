"""
Top-K 选择器

阶段6: 分层采样选择最终 Feed
"""

import random
from typing import List, Tuple
from ..types import PostCandidate, FeedSource
from ..config import SelectionConfig


class TopKSelector:
    """
    Top-K 选择器

    分层加权采样策略:
    - 新闻: top10 加权采样 5 个 + 11-20 加权采样 3 个
    - 非新闻: top10 加权采样 2 个
    分数越高被选中概率越大，同时保留一定探索性
    """

    def __init__(self, config: SelectionConfig):
        self.config = config

    def select(self, candidates: List[PostCandidate]) -> List[PostCandidate]:
        """
        执行分层采样选择

        Args:
            candidates: 候选帖子列表 (已评分)

        Returns:
            选中的帖子列表
        """
        # 分离新闻和非新闻
        news = [c for c in candidates if c.is_news]
        non_news = [c for c in candidates if not c.is_news]

        # 按分数排序
        news.sort(key=lambda c: c.final_score, reverse=True)
        non_news.sort(key=lambda c: c.final_score, reverse=True)

        selected = []
        seen_ids = set()

        # 1. 新闻 Top-K 采样
        news_primary = self._rank_and_sample(
            news,
            pick_n=self.config.news_pick_n,
            top_k=self.config.news_top_k,
            offset=0,
            include_ties=self.config.include_ties
        )
        for p in news_primary:
            if p.post_id not in seen_ids:
                p.feed_segment = 'primary'
                selected.append(p)
                seen_ids.add(p.post_id)

        # 2. 新闻次级采样 (11-20)
        news_secondary = self._rank_and_sample(
            news,
            pick_n=self.config.news_secondary_pick_n,
            top_k=self.config.news_secondary_top_k,
            offset=self.config.news_secondary_offset,
            include_ties=self.config.include_ties
        )
        for p in news_secondary:
            if p.post_id not in seen_ids:
                p.feed_segment = 'secondary'
                selected.append(p)
                seen_ids.add(p.post_id)

        # 3. 非新闻采样
        non_news_selected = self._rank_and_sample(
            non_news,
            pick_n=self.config.non_news_pick_n,
            top_k=self.config.non_news_top_k,
            offset=0,
            include_ties=self.config.include_ties
        )
        for p in non_news_selected:
            if p.post_id not in seen_ids:
                p.feed_segment = 'secondary'
                selected.append(p)
                seen_ids.add(p.post_id)

        return selected

    def _rank_and_sample(
        self,
        candidates: List[PostCandidate],
        pick_n: int,
        top_k: int,
        offset: int = 0,
        include_ties: bool = True
    ) -> List[PostCandidate]:
        """
        排名并采样

        Args:
            candidates: 已排序的候选列表
            pick_n: 采样数量
            top_k: Top-K 池大小
            offset: 起始偏移
            include_ties: 是否包含边界并列项

        Returns:
            采样结果
        """
        if not candidates:
            return []

        # 取窗口 [offset, offset+top_k)
        start = max(0, offset)
        end = min(len(candidates), start + top_k)
        pool = candidates[start:end]

        # 包含边界并列项
        if include_ties and end < len(candidates) and pool:
            last_score = pool[-1].final_score
            i = end
            while i < len(candidates) and candidates[i].final_score == last_score:
                pool.append(candidates[i])
                i += 1

        # 加权采样（分数越高越可能被选中）
        return self._weighted_sample(pool, pick_n)

    def _weighted_sample(
        self,
        candidates: List[PostCandidate],
        pick_n: int
    ) -> List[PostCandidate]:
        """
        加权随机采样 (分数越高越可能被选中)

        Args:
            candidates: 候选列表
            pick_n: 采样数量

        Returns:
            采样结果
        """
        if not candidates:
            return []

        if len(candidates) <= pick_n:
            return candidates

        # 无放回加权采样：每次按当前权重抽 1 个并从池中移除
        # 这样可避免重复样本导致的去重后数量下降。
        pool = list(candidates)
        selected: List[PostCandidate] = []
        draws = min(pick_n, len(pool))

        for _ in range(draws):
            weights = [max(0.0001, c.final_score) for c in pool]
            total = sum(weights)
            if total <= 0:
                break

            r = random.uniform(0, total)
            cumulative = 0.0
            picked_idx = len(pool) - 1  # 浮点边界时兜底最后一个

            for idx, w in enumerate(weights):
                cumulative += w
                if r <= cumulative:
                    picked_idx = idx
                    break

            selected.append(pool.pop(picked_idx))

        return selected
