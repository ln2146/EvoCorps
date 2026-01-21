from datetime import datetime
from comment import Comment
from typing import List

class CommunityNote:
    def __init__(self, note_id, content, author_id, helpful_ratings, not_helpful_ratings):
        self.note_id = note_id
        self.content = content
        self.author_id = author_id
        self.helpful_ratings = helpful_ratings
        self.not_helpful_ratings = not_helpful_ratings
        
    @property
    def is_visible(self) -> bool:
        """Note becomes visible when it has sufficient helpful ratings"""
        # return self.helpful_ratings >= 3 and self.helpful_ratings > self.not_helpful_ratings * 2
        return True
class Post:
    """
    A DTO representing a post in the simulation.
    """
    def __init__(self, 
        post_id: str, 
        content: str, 
        summary: str = None,
        author_id: str = None, 
        created_at: datetime = None,
        num_likes: int = 0,
        num_shares: int = 0,
        num_flags: int = 0,
        num_comments: int = 0,
        original_post_id: str = None,
        is_news: bool = False,
        news_type: str = None,
        status: str = 'active',
        takedown_timestamp: datetime = None,
        takedown_reason: str = None,
        comments = None,
        is_agent_response: bool = False,
        agent_role: str = None,
        agent_response_type: str = None,
        intervention_id: int = None,
    ):
        self.post_id = post_id
        self.content = content
        self.summary = summary
        self.author_id = author_id
        self.created_at = created_at
        self.num_likes = num_likes
        self.num_shares = num_shares
        self.num_flags = num_flags
        self.num_comments = num_comments
        self.original_post_id = original_post_id
        self.is_news = is_news
        self.news_type = news_type
        self.status = status
        self.takedown_timestamp = takedown_timestamp
        self.takedown_reason = takedown_reason
        self.comments = comments or []
        self.community_notes: List[CommunityNote] = []
        self.is_agent_response = is_agent_response
        self.agent_role = agent_role
        self.agent_response_type = agent_response_type
        self.intervention_id = intervention_id
    
    @property
    def is_flagged(self) -> bool:
        """Returns True if the post has been flagged multiple times."""
        return self.num_flags >= 2
    
    @property
    def agent_response_display(self) -> str:
        """Returns a display string for agent responses."""
        if not self.is_agent_response:
            return ""
        
        role_display = {
            "leader": "🎯 Leader Response",
            "tech_rational": "🔬 Tech Rational",
            "moderate_neutral": "⚖️ Moderate Neutral",
            "concerned_citizen": "👥 Concerned Citizens",
            "echo": "🔄 Echo Response"
        }
        
        return role_display.get(self.agent_role, f"🤖 {self.agent_role}")
    
    @property
    def is_leader_response(self) -> bool:
        """Returns True if this is a leader response."""
        return self.is_agent_response and self.agent_response_type == "leader"
    
    @property
    def is_echo_response(self) -> bool:
        """Returns True if this is an echo response."""
        return self.is_agent_response and self.agent_response_type == "echo"

    def to_dict(self) -> dict:
        """Convert post to dictionary for serialization."""
        return {
            'post_id': self.post_id,
            'content': self.content,
            'summary': self.summary,
            'author_id': self.author_id,
            'created_at': self.created_at.isoformat(),
            'num_likes': self.num_likes,
            'num_shares': self.num_shares,
            'num_flags': self.num_flags,
            'num_comments': self.num_comments,
            'original_post_id': self.original_post_id,
            'is_news': self.is_news,
            'news_type': self.news_type,
            'status': self.status,
            'takedown_timestamp': self.takedown_timestamp.isoformat() if self.takedown_timestamp else None,
            'takedown_reason': self.takedown_reason,
            'comments': [comment.to_dict() for comment in self.comments],
            'is_agent_response': self.is_agent_response,
            'agent_role': self.agent_role,
            'agent_response_type': self.agent_response_type,
            'intervention_id': self.intervention_id,
            'agent_response_display': self.agent_response_display
        }

    @classmethod
    def from_row(cls, row):
        """Factory to build Post from sqlite row, gracefully handling missing fields."""
        data = dict(row) if not isinstance(row, dict) else row
        summary = data.get('summary')
        return cls(
            post_id=data['post_id'],
            content=data['content'],
            summary=summary,
            author_id=data.get('author_id'),
            created_at=data.get('created_at'),
            num_likes=data.get('num_likes', 0),
            num_shares=data.get('num_shares', 0),
            num_flags=data.get('num_flags', 0),
            num_comments=data.get('num_comments', 0),
            original_post_id=data.get('original_post_id'),
            is_news=data.get('is_news', False),
            news_type=data.get('news_type'),
            status=data.get('status', 'active'),
            takedown_timestamp=data.get('takedown_timestamp'),
            takedown_reason=data.get('takedown_reason'),
            comments=None,
            is_agent_response=data.get('is_agent_response', False),
            agent_role=data.get('agent_role'),
            agent_response_type=data.get('agent_response_type'),
            intervention_id=data.get('intervention_id')
        )
    
    
