"""
用户数据仓库

封装用户相关的数据库查询
"""

import sys
import os
from typing import List, Dict, Any, Optional, Set

# 添加 src 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database_manager import fetch_all, fetch_one


class UserRepository:
    """
    用户数据仓库

    提供用户相关的数据库查询方法
    """

    def get_followed_ids(self, user_id: str) -> Set[str]:
        """
        获取用户关注列表

        Args:
            user_id: 用户 ID

        Returns:
            关注的用户 ID 集合
        """
        query = 'SELECT followed_id FROM follows WHERE follower_id = ?'
        rows = fetch_all(query, (user_id,)) or []
        return {str(r['followed_id']) for r in rows}

    def get_user_persona(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户画像

        Args:
            user_id: 用户 ID

        Returns:
            用户信息字典
        """
        query = '''
            SELECT user_id, persona, follower_count, influence_score
            FROM users
            WHERE user_id = ?
        '''
        return fetch_one(query, (user_id,))

    def get_exposed_post_ids(self, user_id: str) -> Set[str]:
        """
        获取用户已曝光的帖子 ID

        Args:
            user_id: 用户 ID

        Returns:
            已曝光的帖子 ID 集合
        """
        query = 'SELECT DISTINCT post_id FROM feed_exposures WHERE user_id = ?'
        rows = fetch_all(query, (user_id,)) or []
        return {str(r['post_id']) for r in rows}

    def get_recent_interactions(self, user_id: str, limit: int = 50) -> List[str]:
        """
        获取用户最近交互的帖子 ID

        包括点赞、评论、转发等行为

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            帖子 ID 列表
        """
        # 从评论表获取交互
        query = '''
            SELECT DISTINCT post_id
            FROM comments
            WHERE author_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        '''
        rows = fetch_all(query, (user_id, limit)) or []
        return [str(r['post_id']) for r in rows]

    def get_author_profiles_batch(self, author_ids: List[str]) -> Dict[str, Dict]:
        """
        批量获取作者的粉丝数与信誉分

        单次 IN 查询，避免 N+1 问题。

        Args:
            author_ids: 作者 ID 列表

        Returns:
            {author_id: {'follower_count': int, 'influence_score': float}}
            数据库不可用时返回 {}
        """
        if not author_ids:
            return {}
        placeholders = ','.join('?' * len(author_ids))
        query = f'''
            SELECT user_id, follower_count, influence_score
            FROM users
            WHERE user_id IN ({placeholders})
        '''
        rows = fetch_all(query, tuple(author_ids)) or []
        return {
            str(r['user_id']): {
                'follower_count': r['follower_count'] or 0,
                'influence_score': r['influence_score'] or 0.0,
            }
            for r in rows
        }

    def get_blocked_users(self, user_id: str) -> Set[str]:
        """
        获取用户屏蔽的用户列表

        注意: 当前数据库可能没有 blocked_users 表，返回空集合

        Args:
            user_id: 用户 ID

        Returns:
            屏蔽的用户 ID 集合
        """
        # TODO: 激活路径——建表 blocked_users(blocker_id, blocked_id)，
        #       然后将此处替换为:
        #         query = 'SELECT blocked_id FROM blocked_users WHERE blocker_id = ?'
        #         rows = fetch_all(query, (user_id,)) or []
        #         return {str(r['blocked_id']) for r in rows}
        return set()

    def get_muted_keywords(self, user_id: str) -> List[str]:
        """
        获取用户屏蔽的关键词列表

        注意: 当前数据库可能没有 muted_keywords 表，返回空列表

        Args:
            user_id: 用户 ID

        Returns:
            屏蔽的关键词列表
        """
        # TODO: 激活路径——建表 muted_keywords(user_id, keyword)，
        #       然后将此处替换为:
        #         query = 'SELECT keyword FROM muted_keywords WHERE user_id = ?'
        #         rows = fetch_all(query, (user_id,)) or []
        #         return [r['keyword'] for r in rows]
        return []
