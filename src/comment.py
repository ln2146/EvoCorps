from datetime import datetime

class Comment:
    """
    A DTO representing a comment in the simulation.
    """
    def __init__(
        self,
        comment_id: str,
        content: str,
        post_id: str,
        author_id: str,
        created_at: datetime,
        num_likes: int = 0
    ):
        self.comment_id = comment_id
        self.content = content
        self.post_id = post_id
        self.author_id = author_id
        self.created_at = created_at
        self.num_likes = num_likes

    def to_dict(self) -> dict:
        """Convert comment to dictionary for serialization."""
        return {
            'comment_id': self.comment_id,
            'content': self.content,
            'post_id': self.post_id,
            'author_id': self.author_id,
            'created_at': self.created_at.isoformat(),
            'num_likes': self.num_likes
        }