"""
用户行为水合器

阶段1: 获取用户关注列表和屏蔽列表
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import ClassVar

from ..types import UserContext
from ..repositories.user_repository import UserRepository


class UserActionHydrator:
    """
    用户行为水合器

    获取用户的社交图谱信息（关注、屏蔽）

    支持并行查询以提升性能
    """

    # 类级别线程池（所有实例共享）
    _executor: ClassVar[ThreadPoolExecutor] = None
    _parallel_enabled: ClassVar[bool] = True
    _max_workers: ClassVar[int] = 4

    def __init__(self):
        self.user_repo = UserRepository()

    @classmethod
    def configure_parallel(cls, enabled: bool = True, max_workers: int = 4):
        """
        配置并行查询参数

        Args:
            enabled: 是否启用并行查询
            max_workers: 线程池最大工作线程数
        """
        cls._parallel_enabled = enabled
        cls._max_workers = max_workers

        # 如果禁用并行，关闭现有线程池
        if not enabled and cls._executor is not None:
            cls._executor.shutdown(wait=False)
            cls._executor = None

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """获取或创建线程池（惰性初始化）"""
        if cls._executor is None and cls._parallel_enabled:
            cls._executor = ThreadPoolExecutor(max_workers=cls._max_workers)
        return cls._executor

    def hydrate(self, user_id: str) -> UserContext:
        """
        水合用户上下文

        Args:
            user_id: 用户 ID

        Returns:
            填充了关注和屏蔽信息的 UserContext
        """
        if self._parallel_enabled:
            return self._hydrate_parallel(user_id)
        else:
            return self._hydrate_serial(user_id)

    def _hydrate_serial(self, user_id: str) -> UserContext:
        """串行水合（传统方式）"""
        followed_ids = self.user_repo.get_followed_ids(user_id)
        blocked_ids = self.user_repo.get_blocked_users(user_id)
        muted_keywords = self.user_repo.get_muted_keywords(user_id)
        seen_post_ids = self.user_repo.get_exposed_post_ids(user_id)
        recent_interactions = self.user_repo.get_recent_interactions(user_id)

        return UserContext(
            user_id=user_id,
            followed_ids=followed_ids,
            blocked_ids=blocked_ids,
            muted_keywords=muted_keywords,
            seen_post_ids=seen_post_ids,
            recent_interactions=recent_interactions,
        )

    def _hydrate_parallel(self, user_id: str) -> UserContext:
        """
        并行水合（使用线程池）

        将 5 个独立的数据库查询并行执行
        """
        executor = self._get_executor()
        if executor is None:
            return self._hydrate_serial(user_id)

        # 提交所有查询任务
        futures = {
            executor.submit(self.user_repo.get_followed_ids, user_id): 'followed',
            executor.submit(self.user_repo.get_blocked_users, user_id): 'blocked',
            executor.submit(self.user_repo.get_muted_keywords, user_id): 'muted',
            executor.submit(self.user_repo.get_exposed_post_ids, user_id): 'seen',
            executor.submit(self.user_repo.get_recent_interactions, user_id): 'recent',
        }

        # 收集结果
        results = {}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception:
                # 查询失败时使用默认值
                if key == 'followed':
                    results[key] = set()
                elif key == 'blocked':
                    results[key] = set()
                elif key == 'muted':
                    results[key] = set()
                elif key == 'seen':
                    results[key] = set()
                elif key == 'recent':
                    results[key] = []

        return UserContext(
            user_id=user_id,
            followed_ids=results.get('followed', set()),
            blocked_ids=results.get('blocked', set()),
            muted_keywords=results.get('muted', set()),
            seen_post_ids=results.get('seen', set()),
            recent_interactions=results.get('recent', []),
        )
