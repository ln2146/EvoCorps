import logging
from typing import List, Optional
import sqlite3


def calculate_dynamic_like_increment(conn, current_timestep: Optional[int] = None) -> int:
    """Dynamic like increment per timestep.

    Heuristic:
    - Base = 1
    - If current_timestep is provided, slowly increase with time and cap at 5:
      increment = min(5, 1 + (current_timestep // 2))
    """
    try:
        if current_timestep is None:
            return 1
        inc = 1 + (int(current_timestep) // 2)
        return 5 if inc > 5 else (inc if inc > 1 else 1)
    except Exception:
        return 1


def apply_like_increment_to_comments(conn, comment_ids: List[str], increment: int, context: str = "") -> int:
    """Apply +increment likes to each comment_id. Returns count of updated comments."""
    if not comment_ids or increment <= 0:
        return 0

    try:
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(comment_ids))
        cur.execute(
            f"""
            UPDATE comments
            SET num_likes = COALESCE(num_likes, 0) + ?
            WHERE comment_id IN ({placeholders})
            """,
            [increment, *comment_ids],
        )
        conn.commit()
        # 某些驱动（如 ServiceCursor）无 rowcount，保守以目标数量作为更新数估计
        try:
            updated = cur.rowcount
        except Exception:
            updated = len(comment_ids)
        # 仅做轻量日志，避免噪声
        try:
            logging.debug(f"[DynamicLikes]{'['+context+']' if context else ''} updated={updated}, inc={increment}, targets={len(comment_ids)}")
        except Exception:
            pass
        return updated
    except Exception as e:
        try:
            logging.warning(f"[DynamicLikes]{'['+context+']' if context else ''} failed: {e}")
        except Exception:
            pass
        return 0


def _get_post_engagement(conn, post_id: str) -> int:
    """Compute post engagement = comments + likes + shares."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COALESCE(num_comments,0) + COALESCE(num_likes,0) + COALESCE(num_shares,0)
            FROM posts WHERE post_id = ?
            """,
            (post_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


 
