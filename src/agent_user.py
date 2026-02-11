from __future__ import annotations

import json
import logging
import time
from pydantic import BaseModel
from typing import List, Literal, Optional, TYPE_CHECKING
import sys
import os
# Import from the database subdirectory
from database.database_manager import get_db_manager, execute_query, fetch_one, fetch_all

if TYPE_CHECKING:
    from openai import OpenAI



# Use absolute imports to avoid module path issues
try:
    from comment import Comment
    from post import Post, CommunityNote
    from utils import Utils
    from agent_memory import AgentMemory
    from prompts import AgentPrompts
except ImportError:
    # If absolute imports fail, try relative imports
    from comment import Comment
    from post import Post, CommunityNote
    from utils import Utils
    from agent_memory import AgentMemory
    from prompts import AgentPrompts


class FeedAction(BaseModel):
    """
    An action to take on a post in the feed.
    This class is used to validate the action taken by the agent, and to enforce structured output from the LLM.
    """
    action: Literal[
        "like-post", "share-post", "flag-post", "follow-user",
        "unfollow-user", "comment-post", "like-comment", "ignore",
        "add-note", "rate-note"
    ]
    target: Optional[str] = None  # Made optional since 'ignore' doesn't need a target
    content: Optional[str] = None
    # reasoning: Optional[str] = None # only include reasoning if include_reasoning is true
    note_rating: Optional[Literal["helpful", "not-helpful"]] = None  # For rating notes


class FeedReaction(BaseModel):
    """
    A reaction to the feed.
    This class is used to enforce structured output from the LLM.
    """
    actions: List[FeedAction]


class AgentUser:
    """
    An LLM agent in the simulation.

    Attributes (a dict):
        user_id: unique id of the agent.
        persona: The persona / backstory of the agent.
            - background: The background of the agent.
            - labels: The interest labels of the agent.

    Actions:
        create_post: Create a post.
        like_post: Like a post.
        share_post: Share a post (retweet)
        flag_post: Flag a post (report)
        follow_user: Follow another user.
        unfollow_user: Unfollow another user.
    """
    MEMORY_TYPE_INTERACTION = 'interaction'
    MEMORY_TYPE_REFLECTION = 'reflection'
    VALID_MEMORY_TYPES = {MEMORY_TYPE_INTERACTION, MEMORY_TYPE_REFLECTION}

    def __init__(
        self,
        user_id: str,
        user_config: dict,
        temperature: float = None,  # Optional to support auto-setting
        is_news_agent: bool = False,
        experiment_config: dict = None,  # Add experiment_config parameter
        db_connection = None  # Add database connection parameter (deprecated, use global db_manager)
    ):
        self.user_id = user_id

        # Ensure persona is always a dict, even if stored as string in database
        persona = user_config['persona']
        if isinstance(persona, str):
            # Parse string representation of dict back to dict
            import ast
            try:
                self.persona = ast.literal_eval(persona)
            except (ValueError, SyntaxError):
                # If parsing fails, try json
                import json
                try:
                    self.persona = json.loads(persona)
                except:
                    # Fallback: if persona is just a name string, create a minimal dict
                    logging.warning(f"Persona for {user_id} is a plain string ('{persona}'), creating minimal dict")
                    self.persona = {
                        'name': persona,
                        'type': user_config.get('background_labels', {}).get('type', 'neutral'),
                        'profession': user_config.get('background_labels', {}).get('profession', 'Unknown'),
                        'personality_traits': [],
                        'interests': []
                    }
        else:
            self.persona = persona

        self.is_news_agent = is_news_agent
        self.experiment_config = experiment_config or {}

        # Use global database manager
        self.db_manager = get_db_manager()
        self.db_manager.set_database_path('database/simulation.db')
        self._owns_connection = False  # No longer manage connection directly

        # Import multi-model selection system
        try:
            from multi_model_selector import multi_model_selector, get_random_model
            self.multi_model_selector = multi_model_selector
            # Select an initial model; subsequent calls may select dynamically
            self.selected_model = get_random_model()
            # Removed verbose model selection logging
        except ImportError as e:
            print(f"⚠️ Multi-model selector import failed: {e}, using default model")
            self.multi_model_selector = None
            from multi_model_selector import MultiModelSelector
            self.selected_model = MultiModelSelector.DEFAULT_POOL[0]

        # Optimize: set temperature by persona type to increase differentiation
        if temperature is None:
            persona_type = user_config.get('persona', {}).get('type', 'neutral')
            personality_traits = user_config.get('persona', {}).get('personality_traits', [])
            
            # Base temperature map - balance creativity and logic
            base_temperature_map = {
                'positive': 0.7,   # Positive users: lower temperature, more stable
                'neutral': 0.8,    # Neutral users: medium temperature, balanced
                'negative': 0.9     # Negative users: higher temperature, more personality
            }
            
            base_temp = base_temperature_map.get(persona_type, 0.8)
            
            # Adjust temperature further by personality traits
            if isinstance(personality_traits, list):
                if any(trait in ['Creative', 'Artistic', 'Imaginative'] for trait in personality_traits):
                    base_temp += 0.1  # Increase for creative users
                elif any(trait in ['Analytical', 'Logical', 'Rational'] for trait in personality_traits):
                    base_temp -= 0.05  # Decrease for rational users
                elif any(trait in ['Emotional', 'Passionate', 'Intense'] for trait in personality_traits):
                    base_temp += 0.15  # Increase more for emotional users
                elif any(trait in ['Conservative', 'Traditional', 'Cautious'] for trait in personality_traits):
                    base_temp -= 0.1  # Decrease for conservative users
            
            # Keep temperature within a reasonable range
            self.temperature = max(0.3, min(1.0, base_temp))
            print(f"🌡️ User {user_id} ({persona_type}) temperature set to: {self.temperature}")
        else:
            self.temperature = temperature

        # Initialize memory manager with the database manager
        from agent_memory import AgentMemory
        self.memory = AgentMemory(
            user_id=self.user_id,
            persona=self.persona,
            db_manager=self.db_manager,
            memory_decay_rate=0.1
        )
        
        # Each agent maintains its own reflection cache without DB lookups
        self._reflection_cache = None  # Simple instance var storing reflection memory

        # Store the config for later use
        self.user_config = user_config
        # Store experiment config and type
        self.experiment_config = experiment_config or {}
        self.experiment_type = self.experiment_config.get('experiment', {}).get('type', 'default')

        # Remove comment limit; allow unlimited comments
        self.comment_limit = float('inf')  # Unlimited
        self.comment_count = 0

    def __del__(self):
        """Destructor; DB connection managed globally, no manual close needed"""
        pass  # DB connection managed globally

    def get_dynamic_model(self) -> str:
        """Select model dynamically; each call may return a different model"""
        if self.multi_model_selector:
            # Re-select model each time to increase diversity
            from multi_model_selector import get_random_model
            new_model = get_random_model()
            return new_model
        else:
            return self.selected_model

    async def create_post(self, content: str, summary: str = None, is_news: bool = False, news_type: str = None, status: str = 'active', time_step: int = None) -> str:
        """
        Create a post for the user.
        """
        # Check original post limit (non-news agents only)
        if not self.is_news_agent:
            # Get max post limit from config
            try:
                import json
                with open('configs/experiment_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                max_posts = config.get('max_total_posts', 10)

                # Check current original post count
                result = fetch_one("SELECT COUNT(*) as count FROM posts WHERE original_post_id IS NULL")
                current_count = result['count'] if result else 0

                if current_count >= max_posts:
                    # Silently skip, no log
                    return None
            except Exception as e:
                logging.warning(f"Error checking post limit, continuing to post: {e}")

        post_id = Utils.generate_formatted_id("post")

        # Create the post, marking it as news if from news agent, and include model info - compatible with old schema
        selected_model = getattr(self, 'selected_model', 'unknown')
        agent_type = 'news' if self.is_news_agent else 'normal'

        def _fallback_summary(text: str, existing: str = None) -> str:
            if existing:
                words = existing.split()
                if len(words) > 30:
                    return " ".join(words[:30])
                return existing
            words = text.split()
            return " ".join(words[:30])

        summary_value = _fallback_summary(content, summary)

        try:
            success = execute_query('''
                INSERT INTO posts (post_id, content, summary, author_id, is_news, news_type, status, selected_model, agent_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post_id, content, summary_value, self.user_id, is_news, news_type, status, selected_model, agent_type))
            
            if not success:
                # If new fields are unavailable, use legacy insert
                success = execute_query('''
                    INSERT INTO posts (post_id, content, author_id, is_news, news_type, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (post_id, content, self.user_id, is_news, news_type, status))
                if success:
                    print(f"⚠️ User {self.user_id} created post using compatibility mode")
                else:
                    logging.warning(f"Skipping post creation due to database connection issue, returning dummy post_id")
                    return post_id
        except Exception as e:
            logging.error(f"Database connection error in create_post: {e}")
            logging.warning(f"Skipping post creation due to database connection issue, returning dummy post_id")
            return post_id

        # Record the post creation action
        execute_query('''
            INSERT INTO user_actions (user_id, action_type, target_id, content)
            VALUES (?, 'post', ?, ?)
        ''', (self.user_id, post_id, content))

        # If time_step is provided, record mapping for this post
        try:
            if time_step is not None:
                execute_query('''
                    INSERT OR REPLACE INTO post_timesteps (post_id, time_step)
                    VALUES (?, ?)
                ''', (post_id, int(time_step)))
        except Exception as e:
            logging.warning(f"Failed to record post timestep for {post_id}: {e}")
        # Get current model info
        current_model = getattr(self, 'selected_model', 'unknown')
        if hasattr(self, 'get_dynamic_model'):
            try:
                current_model = self.get_dynamic_model()
            except:
                pass  # Use default if retrieval fails
        
        if self.is_news_agent:
            # Avoid duplicate logs at INFO; keep a concise DEBUG line for diagnostics
            logging.debug(f"📰 News Agent {self.user_id} ({current_model}) created a post: {post_id}")
        else:
            logging.info(f"📝 User {self.user_id} ({current_model}) created a post: {post_id} | {content}")

        # Trigger auto export
        try:
            from auto_export_manager import on_post_created
            on_post_created(post_id, self.user_id)
        except Exception as e:
            pass  # Silence export errors to avoid affecting main flow

        # Trigger scenario class export
        try:
            from scenario_export_manager import on_post_created_scenario
            on_post_created_scenario(post_id, self.user_id)
        except Exception as e:
            pass  # Silence export errors to avoid affecting main flow

        # Update "integrated memory" after posting (normal users only)
        try:
            if not getattr(self, 'is_news_agent', False):
                await self._update_memory_after_action(
                    action_type="post",
                    content=content,
                    post_id=post_id
                )
        except Exception as e:
            logging.error(f"Memory update after post creation failed: {e}")

        return post_id

    def like_post(self, post_id: str) -> None:
        """
        Like a post.
        """
        # if an user has already liked this post, don't like it again
        result = fetch_one('''
            SELECT COUNT(*) as count FROM user_actions
            WHERE user_id = ? AND action_type = 'like' AND target_id = ?
        ''', (self.user_id, post_id))
        if result and result['count'] > 0:
            logging.info(f"👍 User {self.user_id} already liked post {post_id}")
            return

        # Update post likes count
        execute_query('UPDATE posts SET num_likes = num_likes + 1 WHERE post_id = ?', (post_id,))

        # Update author's total likes received
        execute_query('''
            UPDATE users
            SET total_likes_received = total_likes_received + 1
            WHERE user_id = (
                SELECT author_id
                FROM posts
                WHERE post_id = ?
            )
        ''', (post_id,))
        model_info = getattr(self, 'selected_model', 'unknown')
        # Logging moved to _process_reaction method

    def create_comment(self, post_id: str, content: str) -> str:
        """
        Create a comment on a post and update the post's comment count.
        """
        comment_id = Utils.generate_formatted_id("comment")

        # Get post author and content for diversity enhancement
        result = fetch_one('SELECT author_id, content FROM posts WHERE post_id = ?', (post_id,))
        if not result:
            return None
        post_author = result['author_id']
        post_content = result['content']

        # Get model info
        model_info = getattr(self, 'selected_model', 'unknown')

        # Check comment diversity - call async method from sync context
        # Use thread pool to avoid event loop conflicts
        import asyncio
        import concurrent.futures
        
        def run_async():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self._validate_comment_diversity(content, post_id, model_info)
            )
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            final_content = future.result()

        # Insert comment with timestamp and model info - compatible with old schema
        from datetime import datetime
        selected_model = getattr(self, 'selected_model', 'unknown')
        agent_type = 'normal'  # Normal user agent

        try:
            success = execute_query('''
                INSERT INTO comments (comment_id, content, post_id, author_id, created_at, num_likes, selected_model, agent_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (comment_id, final_content, post_id, self.user_id, datetime.now().isoformat(), 0, selected_model, agent_type))
            
            if not success:
                # If new fields are unavailable, use legacy insert
                success = execute_query('''
                    INSERT INTO comments (comment_id, content, post_id, author_id, created_at, num_likes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (comment_id, final_content, post_id, self.user_id, datetime.now().isoformat(), 0))
                if success:
                    print(f"⚠️ User {self.user_id} created comment using compatibility mode")
                else:
                    return None
        except Exception as e:
            logging.error(f"Database error in create_comment: {e}")
            return None

        # Update post's comment count
        execute_query('''
            UPDATE posts
            SET num_comments = num_comments + 1
            WHERE post_id = ?
        ''', (post_id,))

        # Record comment -> timestep mapping if current time step is available
        try:
            current_step = getattr(self, 'current_time_step', None)
            if current_step is not None:
                execute_query('''
                    INSERT OR REPLACE INTO comment_timesteps (comment_id, user_id, post_id, time_step)
                    VALUES (?, ?, ?, ?)
                ''', (comment_id, self.user_id, post_id, int(current_step)))
        except Exception:
            # Non-fatal: mapping is best-effort
            pass

        # Update total comments received for post author
        execute_query('''
            UPDATE users
            SET total_comments_received = total_comments_received + 1
            WHERE user_id = ?
        ''', (post_author,))
        # Logging moved to _process_reaction method

        # Trigger scenario class export
        try:
            from scenario_export_manager import on_comment_created_scenario
            on_comment_created_scenario(comment_id, self.user_id)
        except Exception as e:
            pass  # Silence export errors to avoid affecting main flow

        # Update "integrated memory" after commenting (normal users only)
        try:
            import asyncio
            if not getattr(self, 'is_news_agent', False):
                # create_comment is sync; schedule async task here
                asyncio.create_task(self._update_memory_after_action(
                    action_type="comment",
                    content=final_content,
                    post_id=post_id
                ))
        except Exception as e:
            logging.error(f"Memory update after comment creation failed: {e}")

        return comment_id

    async def _validate_comment_diversity(self, content: str, post_id: str,model_info:str) -> str:
        """
        Validate comment diversity to avoid repetition - async version
        """
        try:
            # Get existing comments for this post
            results = fetch_all('''
                SELECT content FROM comments 
                WHERE post_id = ? AND author_id != ?
                ORDER BY created_at DESC LIMIT 10
            ''', (post_id, self.user_id))
            existing_comments = [row['content'] for row in results]
            
            # Check if too similar to existing comments
            if self._is_comment_too_similar(content, existing_comments):
                # If similarity is too high, try regenerating
                return await self._regenerate_diverse_comment(content, post_id,model_info)
            
            return content
            
        except Exception as e:
            logging.warning(f"Comment diversity validation failed: {e}")
            return content
    
    def _is_comment_too_similar(self, new_comment: str, existing_comments: list) -> bool:
        """
        Check whether new comment is too similar to existing comments
        """
        if not existing_comments:
            return False
            
        new_comment_lower = new_comment.lower().strip()
        
        # Check common repetitive phrases
        generic_phrases = [
            "this is concerning", "this is important", "i agree", "interesting",
            "i think", "in my opinion", "i believe", "this is", "that's"
        ]
        
        # If common repeated phrases are present, mark as similar
        for phrase in generic_phrases:
            if phrase in new_comment_lower:
                return True
        
        # Check similarity with existing comments
        for existing in existing_comments:
            if existing:
                existing_lower = existing.lower().strip()
                # Simple similarity check
                if len(new_comment_lower) > 10 and len(existing_lower) > 10:
                    # Compute word overlap
                    new_words = set(new_comment_lower.split())
                    existing_words = set(existing_lower.split())
                    if len(new_words) > 0 and len(existing_words) > 0:
                        overlap = len(new_words.intersection(existing_words))
                        similarity = overlap / min(len(new_words), len(existing_words))
                        if similarity > 0.7:  # Consider duplicate if >70% similar
                            return True
        
        return False
    
    async def _regenerate_diverse_comment(self, original_content: str, post_id: str,model_info:str) -> str:
        """
        Regenerate a more diverse comment - async version with concurrent prompt creation
        """
        try:
            # Get post content
            post_result = fetch_one('SELECT content FROM posts WHERE post_id = ?', (post_id,))
            if not post_result:
                return original_content
                
            post_content = post_result['content']
            
            # Create enhanced diversity prompt
            diversity_prompt = f"""Your Persona:
{self.persona}

Here is a post from the platform:
--- POST START ---
{post_content}
--- POST END ---

🎯 **CRITICAL DIVERSITY REQUIREMENTS**:
- NEVER use generic phrases like "This is concerning", "This is important", "I agree", "Interesting"
- AVOID starting with "I think", "In my opinion", "I believe" - be more creative and direct
- USE unique opening phrases that reflect YOUR specific personality and background
- INCLUDE specific details from your personal experience, profession, or interests
- VARY your comment style - sometimes short and punchy, sometimes detailed and thoughtful
- SHOW your unique perspective - what makes YOU different from other users?
- REFERENCE specific aspects of the post that resonate with YOUR worldview
- BE AUTHENTIC to your persona - let your personality shine through your words

Your previous attempt was: "{original_content}"

Now write a COMPLETELY DIFFERENT comment that avoids the generic patterns above. Be creative, personal, and authentic to your unique personality.

Your Comment:"""

            # Regenerate with higher temperature
            enhanced_temperature = min(1.0, self.temperature + 0.1)
            
            import asyncio
            from multi_model_selector import MultiModelSelector

            # Unified model selection via MultiModelSelector (comment diversity role)
            selector = self.multi_model_selector or MultiModelSelector()
            client, _ = selector.create_openai_client(role="comment_diversity")
            
            # Fetch system prompt asynchronously (concurrent)
            system_prompt = await self._create_personalized_system_prompt()
            
            # Use asyncio.to_thread to run sync OpenAI call asynchronously
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=self.selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": diversity_prompt}
                ],
                temperature=enhanced_temperature,
                max_tokens=150,
                timeout=120
            )
            
            new_content = response.choices[0].message.content.strip()
            logging.info(f"💬 User {self.user_id} （{model_info}）: {new_content[:50]}...")
            return new_content
            
        except Exception as e:
            logging.warning(f"Failed to regenerate comment: {e}")
            return original_content

    async def _generate_comment_content(self, client, engine: str, post_content: str, comment_context: str = None, max_tokens: int = 150) -> str:
        """
        Generate comment content (for concurrent system) - async version with concurrent prompt creation
        """
        try:
            # Build prompt, include comment_context if provided
            context_section = ""
            if comment_context:
                context_section = f"\n\nRecent comments on this post:\n{comment_context}\n"
            
            prompt = f"""Based on your persona and the following post content, write a thoughtful and engaging comment.

Post content: {post_content}{context_section}

Your comment should be:
- Relevant to the post content
- Engaging and thoughtful
- Written in English only
- Concise but meaningful

Your comment:"""

            # Fetch system prompt asynchronously (concurrent)
            system_prompt = await self._create_personalized_system_prompt()
            
            # Use asyncio.to_thread to run sync OpenAI call asynchronously
            import asyncio
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=engine,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens,
                timeout=120
            )
            
            return completion.choices[0].message.content

        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                logging.warning(f"⚠️ User {self.user_id} hit rate limit generating comment; model {engine} temporarily unavailable")
                return "I'm having some technical issues right now."
            else:
                logging.error(f"Comment generation failed: {e}")
                return ""

    def like_comment(self, comment_id: str) -> None:
        """
        Like a comment and track the action.
        """
        try:
            # Check if user already liked this comment
            result = fetch_one('''
                SELECT COUNT(*) as count FROM user_actions
                WHERE user_id = ? AND action_type = 'like_comment'
                AND target_id = ?
            ''', (self.user_id, comment_id))
            if result and result['count'] > 0:
                return

            # Update comment likes count
            execute_query('''
                UPDATE comments
                SET num_likes = num_likes + 1
                WHERE comment_id = ?
            ''', (comment_id,))

            # Record the action
            execute_query('''
                INSERT INTO user_actions (user_id, action_type, target_id)
                VALUES (?, 'like_comment', ?)
            ''', (self.user_id, comment_id))
            model_info = getattr(self, 'selected_model', 'unknown')
            # Logging moved to _process_reaction method

        except Exception as e:
            logging.error(f"Database operation error: {e}")

    def share_post(self, post_id: str) -> None:
        """
        Share a post (repost it to user's own feed).
        """
        # Check if user already shared this post
        result = fetch_one('''
            SELECT COUNT(*) as count FROM user_actions
            WHERE user_id = ? AND action_type = 'share' AND target_id = ?
        ''', (self.user_id, post_id))
        if result and result['count'] > 0:
            return

        # Get the original post content
        original_post = fetch_one('SELECT content, summary, author_id FROM posts WHERE post_id = ?', (post_id,))
        if not original_post:
            logging.warning(f"Post {post_id} not found")
            return

        original_content = original_post['content']
        original_summary = original_post.get('summary') if isinstance(original_post, dict) else None
        original_author = original_post['author_id']

        # Create a new post as a share
        new_post_id = Utils.generate_formatted_id("post")
        # shared_content = f"Reposted from @{original_author}: {original_content}"
        shared_content = original_content # hide the @original_author

        def _fallback_summary(text: str, summary: str = None) -> str:
            if summary:
                words = summary.split()
                if len(words) > 30:
                    return " ".join(words[:30])
                return summary
            return " ".join(text.split()[:30])

        shared_summary = _fallback_summary(shared_content, original_summary)
        # Insert the new post
        try:
            success = execute_query('''
                INSERT INTO posts (post_id, content, summary, author_id, original_post_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (new_post_id, shared_content, shared_summary, self.user_id, post_id))
            if not success:
                success = execute_query('''
                    INSERT INTO posts (post_id, content, author_id, original_post_id)
                    VALUES (?, ?, ?, ?)
                ''', (new_post_id, shared_content, self.user_id, post_id))
                if success:
                    logging.debug(f"Share fallback insert without summary for post {new_post_id}")
        except Exception as e:
            logging.error(f"Database error when sharing post {post_id}: {e}")
            execute_query('''
                INSERT INTO posts (post_id, content, author_id, original_post_id)
                VALUES (?, ?, ?, ?)
            ''', (new_post_id, shared_content, self.user_id, post_id))

        # Increment share count on original post
        execute_query('UPDATE posts SET num_shares = num_shares + 1 WHERE post_id = ?', (post_id,))

        # Update total shares received for original author
        execute_query('''
            UPDATE users
            SET total_shares_received = total_shares_received + 1
            WHERE user_id = ?
        ''', (original_author,))
        # Logging moved to _process_reaction method

        # Trigger scenario class export (sharing also creates a new post)
        try:
            from scenario_export_manager import on_post_created_scenario
            on_post_created_scenario(new_post_id, self.user_id)
        except Exception as e:
            pass  # Silence export errors to avoid affecting main flow

    def flag_post(self, post_id: str) -> None:
        """
        Flag a post.
        """
        # Check if user already flagged this post
        result = fetch_one('''
            SELECT COUNT(*) as count FROM user_actions
            WHERE user_id = ? AND action_type = 'flag' AND target_id = ?
        ''', (self.user_id, post_id))
        if result and result['count'] > 0:
            return

        execute_query('UPDATE posts SET num_flags = num_flags + 1 WHERE post_id = ?', (post_id,))
        logging.info(f"User {self.user_id} flagged post {post_id}")

    def follow_user(self, target_user_id: str) -> None:
        """
        Follow another user.
        """
        try:
            # First check if already following
            result = fetch_one('''
                SELECT 1 FROM follows
                WHERE follower_id = ? AND followed_id = ?
            ''', (self.user_id, target_user_id))

            if result is not None:
                return

            # If not already following, create the relationship
            execute_query('''
                INSERT INTO follows (follower_id, followed_id)
                VALUES (?, ?)
            ''', (self.user_id, target_user_id))

            # Update follower count for target user
            execute_query('''
                UPDATE users
                SET follower_count = follower_count + 1
                WHERE user_id = ?
            ''', (target_user_id,))
            # Removed verbose individual follow logging

        except Exception as e:
            logging.error(f"Database error in follow_user: {e}")
            # If database connection issue, skip follow operation
            if "unable to open database file" in str(e):
                logging.warning(f"Skipping follow operation due to database connection issue")
                return
            else:
                raise e

    def unfollow_user(self, target_user_id: str) -> None:
        """
        Unfollow a user.
        """
        # First check if actually following
        result = fetch_one('''
            SELECT 1 FROM follows
            WHERE follower_id = ? AND followed_id = ?
        ''', (self.user_id, target_user_id))

        if result is None:
            return

        # delete the follow from the database
        execute_query('''
            DELETE FROM follows
            WHERE follower_id = ? AND followed_id = ?
        ''', (self.user_id, target_user_id))

        # Update follower count for target user
        execute_query('''
            UPDATE users
            SET follower_count = follower_count - 1
            WHERE user_id = ?
        ''', (target_user_id,))
        logging.info(f"User {self.user_id} unfollowed user {target_user_id}")


    def ignore(self) -> None:
        """
        Record that the agent chose to ignore their feed.
        """
        pass  # Silently ignore without logging


    async def _generate_post_content(
        self,
        openai_client: OpenAI,
        engine: str,
        max_tokens: int = 512
    ) -> dict:
        """
        Generate a post content for the user using direct client LLM calls.
        Args:
            openai_client: The OpenAI client to use for generating content.
            engine: The engine to use for generation.
            max_tokens: The maximum number of tokens to generate.
        Returns:
            dict: {'content': post text, 'summary': <=30-word summary}
        """

        # Get prompt and system message
        prompt = self._create_post_prompt()
        system_prompt = await self._create_personalized_system_prompt()
        actual_engine = self.get_dynamic_model() if hasattr(self, 'get_dynamic_model') else (self.selected_model if hasattr(self, 'selected_model') else engine)

        max_retries = 3  # Retry up to 3 times to avoid duplicates
        temperature_to_use = self.temperature

        def _fallback_summary(text: str) -> str:
            """Create <=30 word summary fallback from text."""
            words = text.split()
            truncated = " ".join(words[:30])
            return truncated

        for attempt in range(max_retries):
            try:
                # Use asyncio.to_thread to run sync OpenAI calls asynchronously
                import asyncio
                completion = await asyncio.to_thread(
                    openai_client.chat.completions.create,
                    model=actual_engine,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{prompt}\n\nReturn JSON with keys 'post' and 'summary'. The summary must be an English sentence with no more than 30 words (plain text, no markdown)."}
                    ],
                    temperature=temperature_to_use,
                    max_tokens=max_tokens,
                    timeout=120
                )

                raw_output = completion.choices[0].message.content.strip()
                post_content = raw_output
                summary = ""

                try:
                    parsed = json.loads(raw_output)
                    post_content = parsed.get("post") or parsed.get("content") or post_content
                    summary = parsed.get("summary", "") if isinstance(parsed, dict) else ""
                except json.JSONDecodeError:
                    logging.debug(f"User {self.user_id}: Failed to parse JSON post output, using raw text.")

                if not post_content:
                    post_content = raw_output

                # Check if content is too similar to recent posts (dedupe)
                if self._check_content_similarity(post_content):
                    if attempt < max_retries - 1:
                        logging.info(f"⚠️ User {self.user_id} generated content similar to existing posts, regenerating (attempt {attempt+1}/{max_retries})")
                        # Increase temperature to boost diversity
                        temperature_to_use = min(1.0, temperature_to_use + 0.1)
                        continue
                    else:
                        logging.warning(f"⚠️ User {self.user_id} repeatedly generated similar content, accepting current version")

                if not summary:
                    summary = _fallback_summary(post_content)
                else:
                    summary_words = summary.split()
                    if len(summary_words) > 30:
                        summary = " ".join(summary_words[:30])

                return {"content": post_content, "summary": summary}

            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    logging.warning(f"⚠️ User {self.user_id} hit rate limit; model {actual_engine} temporarily unavailable")
                    # For rate limits, return a short fallback instead of error
                    fallback_text = "I'm experiencing some technical difficulties right now."
                    return {"content": fallback_text, "summary": _fallback_summary(fallback_text)}
                else:
                    logging.error(f"❌ User {self.user_id} post generation failed: {e}")
                    fallback_text = "Unable to generate content due to technical issues."
                    return {"content": fallback_text, "summary": _fallback_summary(fallback_text)}

        # If all attempts fail, return the last generated content
        if 'post_content' in locals():
            return {"content": post_content, "summary": _fallback_summary(post_content)}
        fallback_text = "Unable to generate unique content."
        return {"content": fallback_text, "summary": _fallback_summary(fallback_text)}

    def _check_content_similarity(self, new_content: str, similarity_threshold: float = 0.75) -> bool:
        """
        Check whether new content is too similar to existing posts
        Args:
            new_content: Newly generated content
            similarity_threshold: Similarity threshold (0.75 = 75% similarity counts as duplicate)
        Returns:
            bool: True if content is too similar (needs regen), False if unique enough
        """
        try:
            from difflib import SequenceMatcher

            # Get recent posts by the user for comparison
            recent_posts_results = fetch_all('''
                SELECT content FROM posts
                WHERE author_id = ? AND is_news = 0
                ORDER BY created_at DESC
                LIMIT 10
            ''', (self.user_id,))

            recent_posts = [row['content'] for row in recent_posts_results]

            # Also check recent posts from all users (avoid duplicates across users)
            all_recent_posts_results = fetch_all('''
                SELECT content FROM posts
                WHERE is_news = 0
                ORDER BY created_at DESC
                LIMIT 50
            ''')

            all_recent_posts = [row['content'] for row in all_recent_posts_results]

            # Check similarity with own posts
            for content in recent_posts:
                similarity = SequenceMatcher(None, new_content.lower(), content.lower()).ratio()
                if similarity > similarity_threshold:
                    logging.debug(f"User {self.user_id} content similarity with own post: {similarity:.2%}")
                    return True

            # Check similarity with other users' posts (stricter threshold)
            for content in all_recent_posts:
                similarity = SequenceMatcher(None, new_content.lower(), content.lower()).ratio()
                if similarity > 0.85:  # Higher threshold for other users
                    logging.debug(f"User {self.user_id} content similarity with other users: {similarity:.2%}")
                    return True

            return False

        except Exception as e:
            logging.error(f"Error checking content similarity: {e}")
            # On error, allow content through
            return False


    async def _create_personalized_system_prompt(self) -> str:
        """
        Create a personalized system prompt that incorporates the agent's persona and memories.
        This method is async to allow concurrent memory retrieval for better performance.
        Returns:
            str: Personalized system prompt
        """
        base_prompt = AgentPrompts.get_system_prompt()

        # Parse standard persona format
        persona = getattr(self, 'persona', {})

        if isinstance(persona, dict) and 'name' in persona:
            # Build identity info using new format
            # First try demographics.profession, then fall back to top-level
            profession = persona.get('demographics', {}).get('profession', 
                      persona.get('profession', 'Unknown'))
            
            persona_info = {
                "name": persona['name'],
                "profession": profession
            }
            
            # Add demographics
            if 'demographics' in persona:
                persona_info["demographics"] = persona['demographics']
            
            # Add background
            if 'background' in persona:
                persona_info["background"] = persona['background']

            # Add personality_traits
            if 'personality_traits' in persona and isinstance(persona['personality_traits'], list):
                persona_info["personality_traits"] = persona['personality_traits']
            
            # Add communication_style
            if 'communication_style' in persona:
                persona_info["communication_style"] = persona['communication_style']

            # Append persona info to base prompt
            import json
            persona_text = json.dumps(persona_info, indent=2)
            base_prompt += f"\n\nYOUR PERSONA:\n{persona_text}\n\n"

        elif isinstance(persona, str):
            persona_info = f"Your persona: {persona}"
            base_prompt += f"\n\n{persona_info}"
        else:
            persona_info = f"Your persona: {self.user_id}"
            base_prompt += f"\n\n{persona_info}"

        # Add memory info - use instance cache, do not block
        try:
            # Inject only a single integrated memory (reflection)
            # Use instance cache directly; if none, return empty without DB query
            if self._reflection_cache:
                base_prompt += f"\n\nYOUR MEMORIES:\n{self._reflection_cache}\n"
                logging.debug(f"User {self.user_id}: Added cached memory to system prompt")
            else:
                # If no cache, start background query to update cache without waiting
                import asyncio
                asyncio.create_task(self._update_reflection_cache_background())
                logging.debug(f"User {self.user_id}: No cached memory, started background query")
        except Exception as e:
            logging.warning(f"Failed to load cached memory for system prompt: {e}")

        return base_prompt

    async def _update_reflection_cache_background(self) -> None:
        """Update reflection cache in background without blocking main flow"""
        try:
            # Query DB asynchronously for latest reflection memory
            reflection_memories = await self.memory.get_relevant_memories_async("reflection", limit=1)
            if reflection_memories:
                self._reflection_cache = reflection_memories[0]['content']
                logging.debug(f"User {self.user_id}: Reflection cache updated in background")
            else:
                # Cache empty value to avoid repeated queries
                self._reflection_cache = None
        except Exception as e:
            logging.warning(f"Failed to update reflection cache for user {self.user_id}: {e}")

    async def _integrate_memory_after_content_creation(self, content_type: str, content: str, target_id: str, post_id: str = None):
        """Integrate memory immediately after post/comment - core mechanism"""
        try:
            # Rate limit: at least 15 seconds between integrations
            import time, asyncio
            current_time = time.time()
            if hasattr(self, '_last_memory_integration_time') and (current_time - self._last_memory_integration_time < 15):
                logging.info(f"User {self.user_id}: Skipping memory integration due to rate limit.")
                return
            self._last_memory_integration_time = current_time

            # Fetch existing memories concurrently (interaction and reflection)
            interaction_memories, reflection_memories = await asyncio.gather(
                self.memory.get_relevant_memories_async("interaction", limit=20),
                self.memory.get_relevant_memories_async("reflection", limit=5),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(interaction_memories, Exception):
                logging.error(f"User {self.user_id}: Failed to get interaction memories: {interaction_memories}")
                interaction_memories = []
            if isinstance(reflection_memories, Exception):
                logging.error(f"User {self.user_id}: Failed to get reflection memories: {reflection_memories}")
                reflection_memories = []
            
            # Build current action info
            current_action = f"I created a {content_type}: '{content[:100]}{'...' if len(content) > 100 else ''}'"
            if post_id and content_type == "comment":
                current_action += f" on post {post_id}"
            
            # Build memory integration prompt
            existing_memories_text = ""
            if interaction_memories:
                existing_memories_text += "Recent Interactions:\n" + "\n".join([f"- {mem['content']}" for mem in interaction_memories[:10]])
            if reflection_memories:
                existing_memories_text += "\n\nPrevious Reflections:\n" + "\n".join([f"- {mem['content']}" for mem in reflection_memories])
            
            integration_prompt = f"""You are helping an AI agent update their memory based on new actions and existing memories.

Current Action: {current_action}

Existing Memories:
{existing_memories_text}

User Persona: {self.persona.get('name', 'Unknown')} - {self.persona.get('demographics', {}).get('profession', 'Unknown')}
Personality: {self.persona.get('personality_traits', [])}

Please create an updated memory that:
1. Integrates the new action with existing memories
2. Identifies patterns and preferences that emerge
3. Updates or expands existing insights (e.g., "I like basketball" → "I like basketball and football")
4. Maintains continuity while incorporating new information
5. Creates a coherent, comprehensive memory summary

Format your response as a single, updated memory that replaces and integrates multiple individual memories. Focus on behavioral patterns, preferences, and insights about the user's identity and interests."""

            # Call LLM to integrate (with retries and timeout)
            import asyncio

            logging.info(f"User {self.user_id}: Starting memory integration LLM call")
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (memory role)
            if self.multi_model_selector:
                client, model = self.multi_model_selector.create_openai_client(role="memory")
            else:
                logging.warning("MultiModelSelector unavailable; using selector fallback for memory integration.")
                selector = MultiModelSelector()
                client, model = selector.create_openai_client(role="memory")

            async def _do_call():
                logging.info(f"User {self.user_id}: Making LLM call with prompt length: {len(integration_prompt)}")
                return await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are helping an AI agent integrate their memories to form coherent insights about their behavior, preferences, and identity. Focus on creating comprehensive memory summaries that capture patterns and preferences."},
                        {"role": "user", "content": integration_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=400
                )

            response = await _do_call()
            
            integrated_memory = response.choices[0].message.content.strip()
            
            # Write as the single integrated memory (async)
            await self.memory.upsert_integrated_memory_async(integrated_memory, importance_score=0.95)
            
            # Update instance cache for next use (non-blocking, immediate)
            self._reflection_cache = integrated_memory
            
            logging.info(f"User {self.user_id}: Memory integrated after {content_type} creation: {integrated_memory[:150]}...")
            
        except Exception as e:
            logging.error(f"Memory integration after {content_type} creation failed for user {self.user_id}: {e}")

    async def _integrate_memories_with_llm(self):
        """Periodic memory integration - kept as a fallback"""
        try:
            import time, asyncio
            last_ts = getattr(self, "_last_memory_integration_ts", 0.0)
            now_ts = time.time()
            if now_ts - last_ts < 15.0:
                logging.info(f"User {self.user_id}: Skip periodic memory integration due to rate limit")
                return
            # Fetch recent memories asynchronously
            recent_memories = await self.memory.get_relevant_memories_async("interaction", limit=10)
            if not recent_memories:
                return
            
            # Build memory integration prompt
            memories_text = "\n".join([f"- {mem['content']}" for mem in recent_memories])
            
            integration_prompt = f"""Based on the following recent interactions and memories, create a comprehensive summary that integrates new insights with existing patterns:

Recent Memories:
{memories_text}

Your Persona: {self.persona.get('name', 'Unknown')} - {self.persona.get('demographics', {}).get('profession', 'Unknown')}

Please create an integrated memory summary that:
1. Identifies patterns in behavior and preferences
2. Highlights new insights or changes in perspective
3. Combines related memories into coherent themes
4. Maintains continuity with past experiences

Format your response as a single, comprehensive memory entry that can replace multiple individual memories."""

            # Call LLM to integrate (with retries and timeout)
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (memory role)
            if self.multi_model_selector:
                client, model = self.multi_model_selector.create_openai_client(role="memory")
            else:
                logging.warning("MultiModelSelector unavailable; using selector fallback for memory integration.")
                selector = MultiModelSelector()
                client, model = selector.create_openai_client(role="memory")

            async def _do_call2():
                return await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are helping an AI agent integrate and summarize their memories to form coherent insights about their behavior and preferences."},
                        {"role": "user", "content": integration_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=300
                )

            response = await _do_call2()
            
            integrated_memory = response.choices[0].message.content.strip()
            
            # Write as the single integrated memory (async)
            await self.memory.upsert_integrated_memory_async(integrated_memory, importance_score=0.9)
            
            # Update instance cache for next use (non-blocking, immediate)
            self._reflection_cache = integrated_memory
            
            logging.info(f"User {self.user_id}: Integrated memories with LLM, created reflection: {integrated_memory[:100]}...")
            # Update rate limit timestamp
            self._last_memory_integration_ts = time.time()
            
        except Exception as e:
            logging.error(f"Memory integration failed for user {self.user_id}: {e}")


    async def _update_memory_after_action(self, action_type: str, content: str, post_id: str = None):
        """
        After posting/commenting, generate a new integrated memory based on current content,
        recent actions, and existing integrated memory, then overwrite the old one.
        Always output a single integrated memory sentence, e.g.:
        Existing: "I like basketball"; current shows "likes football" -> New: "I like basketball and football".
        """
        try:
            import asyncio
            import time, hashlib

            # Debounce + dedup + simple in-progress guard to avoid duplicate updates
            # - Debounce: skip if calls happen within a short interval
            # - Dedup: skip if the same (action_type, post_id, content_hash) appears again
            # - In-progress: skip if a previous update is still running
            try:
                state = getattr(self, '_mem_update_state', None)
                if state is None:
                    state = {'ts': 0.0, 'key': None, 'running': False}
                    setattr(self, '_mem_update_state', state)

                now = time.time()
                content_str = content or ''
                content_hash = hashlib.sha1(content_str.encode('utf-8')).hexdigest()[:16]
                dedup_key = f"{action_type}:{post_id or ''}:{content_hash}"

                # In-progress guard
                if state.get('running', False):
                    logging.info(f"User {self.user_id}: Skip memory update due to in-progress run")
                    return

                # Debounce window (seconds)
                min_interval = 12.0
                if (now - state.get('ts', 0.0)) < min_interval:
                    logging.info(f"User {self.user_id}: Skip memory update due to rate limit")
                    return

                # Duplicate key check
                if state.get('key') == dedup_key:
                    logging.info(f"User {self.user_id}: Skip memory update due to duplicate key")
                    return

                # Mark running and record timestamp/key
                state['running'] = True
                state['ts'] = now
                state['key'] = dedup_key
            except Exception as guard_e:
                # Guard should not block main logic if it fails
                logging.warning(f"User {self.user_id}: Memory update guard init failed: {guard_e}")

            # 1) and 2) read current integrated memory and recent user actions concurrently
            async def get_reflection():
                try:
                    reflections = await self.memory.get_relevant_memories_async("reflection", limit=1)
                    return reflections[0]['content'] if reflections else ""
                except Exception as e:
                    logging.warning(f"User {self.user_id}: Failed to load existing reflection memory: {e}")
                    return ""
            
            async def get_recent_actions():
                try:
                    rows = await asyncio.to_thread(
                        fetch_all,
                        '''SELECT action_type, target_id, content, reasoning, created_at
                           FROM user_actions
                           WHERE user_id = ?
                           ORDER BY created_at DESC
                           LIMIT 5''',
                        (self.user_id,)
                    )
                    actions = []
                    for r in rows:
                        # Compatibility for row-like access
                        r_content = r['content'] if isinstance(r, dict) else getattr(r, 'content', None)
                        actions.append({
                            'type': r['action_type'] if isinstance(r, dict) else getattr(r, 'action_type', ''),
                            'target': r['target_id'] if isinstance(r, dict) else getattr(r, 'target_id', ''),
                            'content': r_content,
                            'created_at': r['created_at'] if isinstance(r, dict) else getattr(r, 'created_at', '')
                        })
                    return actions
                except Exception as e:
                    logging.warning(f"User {self.user_id}: Failed to load recent actions: {e}")
                    return []
            
            # Fetch reflection and actions concurrently
            reflection_mem, recent_actions = await asyncio.gather(
                get_reflection(),
                get_recent_actions(),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(reflection_mem, Exception):
                logging.error(f"User {self.user_id}: Exception getting reflection: {reflection_mem}")
                reflection_mem = ""
            if isinstance(recent_actions, Exception):
                logging.error(f"User {self.user_id}: Exception getting recent actions: {recent_actions}")
                recent_actions = []

            actions_text = "\n".join([
                f"- {a['type']} -> {a['content'] or ''}" for a in recent_actions if a
            ])

            # 3) Assemble prompt
            user_name = self.persona.get('name', 'Unknown')
            profession = self.persona.get('demographics', {}).get('profession', 'Unknown')
            integration_prompt = f"""
You are an assistant that maintains a user's integrated memory as a single concise paragraph.

Current persona: {user_name} - {profession}
Previous integrated memory (may be empty):
{reflection_mem}

New action just completed:
- type: {action_type}
- content: {content}

Recent actions (latest up to 5):
{actions_text}

Task:
- Update the integrated memory as a single short paragraph.
- Merge new insights with existing ones; keep it coherent, avoid duplication.
- If a new preference/topic emerges (e.g., football) and previous memory has basketball, produce something like: "I like basketball and soccer."
- Keep it human-readable, avoid bullets and meta text.
- Output ONLY the updated memory text.
"""

            # 4) Call LLM to generate new integrated memory (consistent with global keys/agent)
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (memory role)
            if self.multi_model_selector:
                client, model = self.multi_model_selector.create_openai_client(role="memory")
            else:
                logging.warning("MultiModelSelector unavailable; using selector fallback for memory integration.")
                selector = MultiModelSelector()
                client, model = selector.create_openai_client(role="memory")
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": "You update and maintain a user's integrated memory as one concise paragraph."},
                    {"role": "user", "content": integration_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )

            integrated_memory = response.choices[0].message.content.strip()

            # 5) Overwrite integrated memory (async)
            await self.memory.upsert_integrated_memory_async(integrated_memory, importance_score=0.95)
            
            # Update instance cache for next use (non-blocking, immediate)
            self._reflection_cache = integrated_memory
            
            logging.info(f"User {self.user_id}: Updated integrated memory after {action_type}: {integrated_memory[:150]}...")
            try:
                # Reset running flag after successful update
                state = getattr(self, '_mem_update_state', None)
                if isinstance(state, dict):
                    state['running'] = False
            except Exception:
                pass

        except Exception as e:
            # Ensure running flag is cleared on error as well
            try:
                state = getattr(self, '_mem_update_state', None)
                if isinstance(state, dict):
                    state['running'] = False
            except Exception:
                pass
            logging.error(f"User {self.user_id}: Memory update after {action_type} failed: {e}")
    def _get_recent_posts(self, limit=5):
        """
        Get the user's recent posts.
        Returns:
            list[str]: List of recent post contents
        """
        try:
            results = fetch_all('''
                SELECT content FROM posts
                WHERE author_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (self.user_id, limit))
            return [row['content'] for row in results]
        except Exception as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in _get_recent_posts, returning empty list")
                return []
            else:
                raise e


    def _create_post_prompt(self) -> str:
        """
        Create a post prompt for the user.
        Returns:
            prompt: The prompt for the post.
        """
        # Get recent posts from the user
        recent_posts = self._get_recent_posts()
        recent_posts_text = "\n".join([f"- {post}" for post in recent_posts]) if recent_posts else ""

        # Get recent feed posts
        feed = self.get_feed(experiment_config=self.experiment_config, time_step=None)
        feed_text = "\n".join([
            f"- {self._clean_post_content_for_inspiration(post.content)}"
            f"{' [BREAKING NEWS]' if hasattr(post, 'is_news') and post.is_news else ''}"
            f"{' [FLAGGED BY COMMUNITY]' if hasattr(post, 'is_flagged') and post.is_flagged else ''}"
            + (f"\n  FACT CHECK: {post.fact_check_verdict.upper()} "
               f"(Confidence: {post.fact_check_confidence:.0%})"
               if hasattr(post, 'fact_check_verdict') and post.fact_check_verdict else "")
            + (f"\n  Community Notes:\n" + "\n".join([
                f"  • note_id: {note.note_id} | {note.content} (Helpful: {note.helpful_ratings}, Not Helpful: {note.not_helpful_ratings})"
                for note in post.community_notes if note.is_visible
            ]) if any(note.is_visible for note in post.community_notes) else "")
            for post in feed
        ]) if feed else ""

        # Check if prebunking is enabled
        # Only enable prebunking for neutral users (most vulnerable to misinformation)
        prebunking_enabled = (
            self.experiment_config.get('prebunking_system', {}).get('enabled', False)
            and not self.is_news_agent
            and self.persona.get('type') == 'neutral'  # Only neutral users
        )

        prompt = AgentPrompts.create_post_prompt(
            self.persona,
            recent_posts_text,
            feed_text,
            prebunking_enabled
        )
        token_count = Utils.estimate_token_count(prompt)
        # Removed verbose token count logging

        return prompt

    def _clean_post_content_for_inspiration(self, content: str) -> str:
        """
        Clean post content to remove format indicators that might influence user post generation.
        This helps prevent users from copying news formats when creating their own posts.
        Enhanced to remove more news-style formatting while preserving core content.
        """
        if not content:
            return content

        cleaned = content

        # Remove various news format prefixes and tags
        news_prefixes = [
            "NEWS: ", "[NEWS] ", "[BREAKING] ", "[BOMBSHELL] ", "[REVEALED] ",
            "[EXPOSED] ", "[SCANDAL] ", "[INVESTIGATION] ", "[CENSORED] ",
            "[SUPPRESSED] ", "BREAKING: ", "BOMBSHELL: ", "REVEALED: ",
            "EXPOSED: ", "SCANDAL: ", "INVESTIGATION: ", "CENSORED: ", "SUPPRESSED: "
        ]

        for prefix in news_prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break

        # Remove news-style formatting patterns
        import re
        # Remove patterns like "CITY - " at the beginning
        cleaned = re.sub(r'^[A-Z\s]+ - ', '', cleaned)

        # If the content starts with a title followed by colon, extract the main content
        if ": " in cleaned and len(cleaned.split(": ", 1)) == 2:
            title, main_content = cleaned.split(": ", 1)
            # If the main content is substantial, use it; otherwise keep the title
            if len(main_content.strip()) > 20:
                cleaned = main_content.strip()

        # Convert to more personal/conversational tone for inspiration
        # Remove formal journalism language patterns
        cleaned = re.sub(r'according to (sources|reports|officials)', 'people are saying', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'officials (said|stated|announced)', 'they said', cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _get_initial_news_feed(self, limit: int = 5):
        """Fetch the first batch of news posts for timestep 0."""
        try:
            results = fetch_all('''
                SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                       p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                       p.is_news, p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                FROM posts p
                WHERE p.is_news = TRUE
                AND (p.status IS NULL OR p.status != 'taken_down')
                ORDER BY p.created_at ASC
                LIMIT ?
            ''', (limit,))
            return [Post.from_row(row) for row in results]
        except Exception as e:
            if "unable to open database file" in str(e):
                logging.warning("Database connection error in _get_initial_news_feed, returning empty set")
                return []
            raise e

    def _get_initial_news_feed_mixed(self, normal_count: int = 9, extreme_count: int = 1):
        """
        Fetch initial feed with a mix of normal and extreme news.
        - normal: is_news = TRUE and (news_type IS NULL OR news_type != 'fake')
        - extreme: is_news = TRUE and news_type = 'fake'
        Fallback: if not enough posts in either category, top up from all news.
        """
        try:
            # Normal news (exclude 'fake')
            normal_rows = fetch_all('''
                SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                       p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                       p.is_news, p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                FROM posts p
                WHERE p.is_news = TRUE
                  AND (p.status IS NULL OR p.status != 'taken_down')
                  AND (p.news_type IS NULL OR p.news_type != 'fake')
                ORDER BY p.created_at ASC
                LIMIT ?
            ''', (normal_count,))

            # Extreme news (news_type = 'fake')
            extreme_rows = fetch_all('''
                SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                       p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                       p.is_news, p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                FROM posts p
                WHERE p.is_news = TRUE
                  AND p.news_type = 'fake'
                  AND (p.status IS NULL OR p.status != 'taken_down')
                ORDER BY p.created_at ASC
                LIMIT ?
            ''', (extreme_count,))

            selected = [Post.from_row(r) for r in (normal_rows + extreme_rows)]

            # Top up if needed
            target = normal_count + extreme_count
            if len(selected) < target:
                selected_ids = {p.post_id for p in selected}
                need = target - len(selected)
                topup_rows = fetch_all('''
                    SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                           p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                           p.is_news, p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                    FROM posts p
                    WHERE p.is_news = TRUE
                      AND (p.status IS NULL OR p.status != 'taken_down')
                    ORDER BY p.created_at ASC
                ''')
                for r in topup_rows:
                    pid = r['post_id'] if isinstance(r, dict) else r[0]
                    if pid in selected_ids:
                        continue
                    selected.append(Post.from_row(r))
                    selected_ids.add(pid)
                    if len(selected) >= target:
                        break

            # Ensure deterministic ordering by created_at ASC as initial batch
            try:
                selected.sort(key=lambda p: p.created_at)
            except Exception:
                pass

            return selected

        except Exception as e:
            if "unable to open database file" in str(e):
                logging.warning("Database connection error in _get_initial_news_feed_mixed, returning empty set")
                return []
            raise e

    def _enrich_feed_posts(self, posts, time_step):
        """Attach comments, community notes, fact-checks, and track exposures."""
        if not posts:
            return posts

        for post in posts:
            results = fetch_all('''
                SELECT c.comment_id, c.content, c.post_id, c.author_id,
                       c.created_at, c.num_likes
                FROM comments c
                WHERE c.post_id = ?
                ORDER BY c.num_likes DESC, c.created_at DESC
                LIMIT 2
            ''', (post.post_id,))
            hot_comments = [Comment(*list(row.values())) for row in results]

            hot_comment_ids = [c.comment_id for c in hot_comments]
            if hot_comment_ids:
                placeholders = ','.join('?' * len(hot_comment_ids))
                results = fetch_all(f'''
                    SELECT c.comment_id, c.content, c.post_id, c.author_id,
                           c.created_at, c.num_likes
                    FROM comments c
                    WHERE c.post_id = ? AND c.comment_id NOT IN ({placeholders})
                    ORDER BY c.created_at DESC
                    LIMIT 2
                ''', [post.post_id] + hot_comment_ids)
            else:
                results = fetch_all('''
                    SELECT c.comment_id, c.content, c.post_id, c.author_id,
                           c.created_at, c.num_likes
                    FROM comments c
                    WHERE c.post_id = ?
                    ORDER BY c.created_at DESC
                    LIMIT 2
                ''', (post.post_id,))
            recent_comments = [Comment(*list(row.values())) for row in results]
            post.comments = hot_comments + recent_comments

        for post in posts:
            results = fetch_all('''
                SELECT note_id, content, author_id, helpful_ratings, not_helpful_ratings
                FROM community_notes
                WHERE post_id = ?
                ORDER BY helpful_ratings DESC
            ''', (post.post_id,))
            post.community_notes = [CommunityNote(*row.values()) for row in results]

        for post in posts:
            fact_check = fetch_one('''
                SELECT verdict, explanation, confidence
                FROM fact_checks
                WHERE post_id = ?
            ''', (post.post_id,))
            if fact_check:
                post.fact_check_verdict = fact_check['verdict']
                post.fact_check_explanation = fact_check['explanation']
                post.fact_check_confidence = fact_check['confidence']

        if time_step is not None:
            for post in posts:
                execute_query('''
                    INSERT OR IGNORE INTO feed_exposures (user_id, post_id, time_step)
                    VALUES (?, ?, ?)
                ''', (self.user_id, post.post_id, time_step))

        return posts

    def get_feed(self, experiment_config: dict, time_step=None):
        """
        Get the user's feed and track post exposures.
        - time_step == 0: cold start (up to 5 news items).
        - time_step > 0: scoring score = (engagement + β) × (1 - λ × age_steps)
          • News: sample 5 from top 10 + 3 from ranks 11-20
          • Non-news: sample 2 from top 10 by score (including ties)
        - time_step is None: return lightweight snapshot (no exposure tracking) for post inspiration.
        """

        import random

        # Step 0: cold start
        if time_step == 0 and not self.is_news_agent:
            # Show 10 posts on the first timestep: 9 normal + 1 extreme
            initial_feed = self._get_initial_news_feed_mixed(normal_count=9, extreme_count=1)
            if initial_feed:
                return self._enrich_feed_posts(initial_feed, time_step)

        # If no time_step (for inspiration/no exposure tracking), fallback to lightweight strategy
        if time_step is None:
            try:
                results = fetch_all('''
                    SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                           p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                           p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                    FROM posts p
                    WHERE p.is_news = TRUE AND (p.status IS NULL OR p.status != 'taken_down')
                    ORDER BY p.created_at DESC
                    LIMIT 6
                ''')
                snapshot = [Post.from_row(row) for row in results]
            except Exception as e:
                if "unable to open database file" in str(e):
                    snapshot = []
                else:
                    raise e
            return self._enrich_feed_posts(snapshot, time_step)

        # Scoring parameters
        lambda_decay = 0.1 
        beta_bias = 180   

        # Get post->timestep mapping (age=0 if missing)
        try:
            pt_rows = fetch_all('SELECT post_id, time_step FROM post_timesteps')
            post_step_map = {r['post_id']: r['time_step'] for r in pt_rows}
        except Exception as e:
            if "unable to open database file" in str(e):
                post_step_map = {}
            else:
                raise e

        def compute_score(row):
            # Engagement uses comment count only
            eng = (row.get('num_comments') or 0)
            pstep = post_step_map.get(row['post_id'])
            age = max(0, (time_step - pstep)) if (pstep is not None) else 0
            freshness = max(0.1, 1.0 - lambda_decay * age)
            return (eng + beta_bias) * freshness

        # Override engagement as comments + shares + likes
        def compute_score(row):
            eng = (row.get('num_comments') or 0) + (row.get('num_shares') or 0) + (row.get('num_likes') or 0)
            pstep = post_step_map.get(row['post_id'])
            age = max(0, (time_step - pstep)) if (pstep is not None) else 0
            freshness = max(0.1, 1.0 - lambda_decay * age)
            return (eng + beta_bias) * freshness

        def rank_and_sample(query_sql, params, pick_n, top_k=10, offset=0, include_ties=True):
            try:
                rows = fetch_all(query_sql, params)
            except Exception as e:
                if "unable to open database file" in str(e):
                    return []
                else:
                    raise e
            # Convert to list of dicts
            dict_rows = [dict(r) if not isinstance(r, dict) else r for r in rows]
            for r in dict_rows:
                r['__score'] = compute_score(r)
            # Sort by score desc, created_at desc
            dict_rows.sort(key=lambda r: (r['__score'], r.get('created_at')), reverse=True)
            if not dict_rows:
                return []
            # Take window [offset, offset+top_k)
            start = max(0, int(offset))
            end = max(start, start + int(top_k))
            top_pool = dict_rows[start:end]
            # Include boundary ties in pool (optional)
            if include_ties and end < len(dict_rows) and top_pool:
                last_score = top_pool[-1]['__score']
                i = end
                while i < len(dict_rows) and dict_rows[i]['__score'] == last_score:
                    top_pool.append(dict_rows[i])
                    i += 1
            # Randomly sample pick_n
            if len(top_pool) <= pick_n:
                chosen = top_pool
            else:
                chosen = random.sample(top_pool, pick_n)
            return [Post.from_row(r) for r in chosen]

        # News pool: active news
        news_sql = '''
            SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                   p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                   p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
            FROM posts p
            WHERE p.is_news = TRUE AND (p.status IS NULL OR p.status != 'taken_down')
        '''
        news_top10 = rank_and_sample(news_sql, (), pick_n=5, top_k=10, offset=0, include_ties=False)
        news_11_20 = rank_and_sample(news_sql, (), pick_n=3, top_k=10, offset=10, include_ties=False)

        # Add 1 extra negative news item (news_type='fake'), no duplicates; score-weighted sampling
        negative_selected = []
        try:
            # Base candidate set: all valid negative news
            neg_rows = fetch_all('''
                SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                       p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                       p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
                FROM posts p
                WHERE p.is_news = TRUE AND p.news_type = 'fake' AND (p.status IS NULL OR p.status != 'taken_down')
            ''')
            # Compute scores and exclude already selected news
            neg_candidates = []
            selected_ids = {p.post_id for p in (news_top10 + news_11_20)}
            for r in neg_rows:
                rdict = dict(r) if not isinstance(r, dict) else r
                if rdict['post_id'] in selected_ids:
                    continue
                rdict['__score'] = compute_score(rdict)
                neg_candidates.append(rdict)

            if neg_candidates:
                # Score-weighted random sampling (higher score more likely)
                import random
                weights = [max(0.0001, c['__score']) for c in neg_candidates]
                choice = random.choices(neg_candidates, weights=weights, k=1)[0]
                negative_selected = [Post.from_row(choice)]
        except Exception as e:
            if "unable to open database file" in str(e):
                negative_selected = []
            else:
                raise e

        # Non-news pool: active non-news
        non_news_sql = '''
            SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                   p.num_likes, p.num_shares, p.num_flags, p.num_comments, p.original_post_id,
                   p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id
            FROM posts p
            WHERE (p.is_news IS NULL OR p.is_news != TRUE) AND (p.status IS NULL OR p.status != 'taken_down')
        '''
        non_news_selected = rank_and_sample(non_news_sql, (), pick_n=2, top_k=10, offset=0, include_ties=True)

        # Merge and dedupe
        final_feed = []
        seen = set()
        segment_sources = [
            ('primary', news_top10),
            ('secondary', news_11_20),
            ('secondary', negative_selected),
            ('secondary', non_news_selected),
        ]
        for segment_label, posts in segment_sources:
            for post in posts:
                if post.post_id not in seen:
                    setattr(post, 'feed_segment', 'primary' if segment_label == 'primary' else 'secondary')
                    final_feed.append(post)
                    seen.add(post.post_id)

        return self._enrich_feed_posts(final_feed, time_step)

    def get_news_only_feed(self, experiment_config: dict, time_step=None):
        """Optimized feed generation for news-only simulation."""
        total_news_posts = experiment_config['feed']['total_news_posts']

        # Get all news posts, prioritizing followed sources
        results = fetch_all('''
            SELECT p.post_id, p.content, p.summary, p.author_id, p.created_at,
                   p.num_likes, p.num_shares, p.num_flags, p.original_post_id,
                   p.is_agent_response, p.agent_role, p.agent_response_type, p.intervention_id,
                   CASE WHEN f.followed_id IS NOT NULL THEN 1 ELSE 0 END AS is_followed
            FROM posts p
            LEFT JOIN follows f ON p.author_id = f.followed_id AND f.follower_id = ?
            WHERE p.is_news = TRUE
            AND p.author_id != ?
            AND (p.status IS NULL OR p.status != 'taken_down')
            ORDER BY is_followed DESC, p.created_at DESC
            LIMIT ?
        ''', (self.user_id, self.user_id, total_news_posts))

        news_posts = []
        for row in results:
            row_dict = dict(row)
            row_dict.pop('is_followed', None)
            news_posts.append(Post.from_row(row_dict))

        # Combine all posts into a set to remove any remaining duplicates
        final_feed = sorted(news_posts, key=lambda x: x.created_at, reverse=True)

        # Fetch comments for each post - 4 comments: 2 by popularity, 2 by recency
        for post in final_feed:
            # Get 2 most popular comments
            results = fetch_all('''
                SELECT c.comment_id, c.content, c.post_id, c.author_id,
                       c.created_at, c.num_likes
                FROM comments c
                WHERE c.post_id = ?
                ORDER BY c.num_likes DESC, c.created_at DESC
                LIMIT 2
            ''', (post.post_id,))
            hot_comments = [Comment(*list(row.values())) for row in results]

            # Get 2 most recent comments (excluding already selected popular ones)
            hot_comment_ids = [c.comment_id for c in hot_comments]
            if hot_comment_ids:
                placeholders = ','.join('?' * len(hot_comment_ids))
                results = fetch_all(f'''
                    SELECT c.comment_id, c.content, c.post_id, c.author_id,
                           c.created_at, c.num_likes
                    FROM comments c
                    WHERE c.post_id = ? AND c.comment_id NOT IN ({placeholders})
                    ORDER BY c.created_at DESC
                    LIMIT 2
                ''', [post.post_id] + hot_comment_ids)
            else:
                results = fetch_all('''
                    SELECT c.comment_id, c.content, c.post_id, c.author_id,
                           c.created_at, c.num_likes
                    FROM comments c
                    WHERE c.post_id = ?
                    ORDER BY c.created_at DESC
                    LIMIT 2
                ''', (post.post_id,))
            recent_comments = [Comment(*list(row.values())) for row in results]

            # Merge comments: popularity first, then recency
            post.comments = hot_comments + recent_comments

        # Fetch community notes for each post
        for post in final_feed:
            results = fetch_all('''
                SELECT note_id, content, author_id, helpful_ratings, not_helpful_ratings
                FROM community_notes
                WHERE post_id = ?
                ORDER BY helpful_ratings DESC
            ''', (post.post_id,))

            post.community_notes = [CommunityNote(*row.values()) for row in results]

        # Add fact-check information to posts
        for post in final_feed:
            fact_check = fetch_one('''
                SELECT verdict, explanation, confidence
                FROM fact_checks
                WHERE post_id = ?
            ''', (post.post_id,))
            fact_check = fetch_one('''
                SELECT verdict, explanation, confidence
                FROM fact_checks
                WHERE post_id = ?
            ''', (post.post_id,))
            if fact_check:
                post.fact_check_verdict = fact_check['verdict']
                post.fact_check_explanation = fact_check['explanation']
                post.fact_check_confidence = fact_check['confidence']

        # Track exposures for all posts in the final feed
        if time_step is not None:
            for post in final_feed:
                execute_query('''
                    INSERT OR IGNORE INTO feed_exposures (user_id, post_id, time_step)
                    VALUES (?, ?, ?)
                ''', (self.user_id, post.post_id, time_step))

        return final_feed

    def _intelligent_comment_liking(self, feed):
        """
        Intelligent comment like system - choose comments to like based on user identity, values, and memory
        Returns list of comment IDs to like
        """
        try:
            # Parse user persona with improved error handling
            persona_dict = {}
            if isinstance(self.persona, str):
                if self.persona.strip():  # Check for empty string
                    # Check for simple string identifier (e.g., "NeutralUser029")
                    if self.persona.startswith('{') and self.persona.endswith('}'):
                        # Looks like JSON; try parsing
                        try:
                            persona_dict = json.loads(self.persona)
                        except json.JSONDecodeError as json_error:
                            logging.warning(f"User {self.user_id} persona JSON parse failed: {json_error}, persona content: '{self.persona[:100]}...'")
                            # Use default persona
                            persona_dict = {
                                'political_stance': 'moderate',
                                'important_values': [],
                                'personality': [],
                                'social_tendency': []
                            }
                    else:
                        # Simple string identifier; infer persona traits
                        persona_dict = self._parse_persona_identifier(self.persona)
                else:
                    logging.warning(f"User {self.user_id} persona is empty string, using default")
                    persona_dict = {
                        'political_stance': 'moderate',
                        'important_values': [],
                        'personality': [],
                        'social_tendency': []
                    }
            elif isinstance(self.persona, dict):
                persona_dict = self.persona
            else:
                logging.warning(f"User {self.user_id} persona type invalid: {type(self.persona)}, using default")
                persona_dict = {
                    'political_stance': 'moderate',
                    'important_values': [],
                    'personality': [],
                    'social_tendency': []
                }

            # Extract user traits
            political_stance = persona_dict.get('political_stance', 'moderate').lower()
            important_values = persona_dict.get('important_values', [])
            personality_traits = persona_dict.get('personality', [])
            social_tendency = persona_dict.get('social_tendency', [])

            # Normalize to list format
            if isinstance(important_values, str):
                important_values = [v.strip() for v in important_values.split(',')]
            if isinstance(personality_traits, str):
                personality_traits = [t.strip() for t in personality_traits.split(',')]
            if isinstance(social_tendency, str):
                social_tendency = [t.strip() for t in social_tendency.split(',')]

            # Get user-related memories
            relevant_memories = self.memory.get_relevant_memories("interaction", limit=10)
            memory_keywords = set()
            for memory in relevant_memories:
                content = memory.get('content', '').lower()
                memory_keywords.update(content.split())

            # Dynamically adjust like threshold based on traits and activity
            base_threshold = 0.5  # Lowered from 0.6 so more comments get liked

            # Adjust threshold by political stance
            political_adjustment = 0.0
            if 'very liberal' in political_stance or 'very conservative' in political_stance:
                political_adjustment = -0.05  # Extreme stances like aligned comments more
            elif 'moderate' in political_stance:
                political_adjustment = 0.05   # Moderates are more selective

            # Adjust threshold by personality traits
            personality_adjustment = 0.0
            if 'extroverted' in str(personality_traits).lower():
                personality_adjustment -= 0.05  # Extroverts are more active
            if 'optimistic' in str(personality_traits).lower():
                personality_adjustment -= 0.03  # Optimists like more
            if 'analytical' in str(personality_traits).lower():
                personality_adjustment += 0.02  # Analysts are more strict
            if 'empathetic' in str(personality_traits).lower():
                personality_adjustment -= 0.04  # Empathetic users like more
            if 'social' in str(personality_traits).lower():
                personality_adjustment -= 0.03  # Social users are more active

            # Adjust by memory richness
            memory_adjustment = 0.0
            if len(memory_keywords) > 50:
                memory_adjustment = -0.02  # Rich memory finds resonance more easily
            elif len(memory_keywords) < 10:
                memory_adjustment = 0.02   # Sparse memory is more cautious

            # Compute final threshold
            dynamic_threshold = max(0.45, min(0.75, base_threshold + political_adjustment + personality_adjustment + memory_adjustment))

            logging.debug(f"🎯 User {self.user_id} dynamic threshold: {dynamic_threshold:.2f} (base: {base_threshold}, political: {political_adjustment:+.2f}, personality: {personality_adjustment:+.2f}, memory: {memory_adjustment:+.2f})")

            liked_comments = []
            comment_scores_cache = {}  # Cache scoring results
            total_comments_analyzed = 0

            for post in feed:
                for comment in post.comments:
                    total_comments_analyzed += 1
                    # Compute and cache score
                    score = self._calculate_comment_affinity_score(
                        comment, political_stance, important_values,
                        personality_traits, social_tendency, memory_keywords
                    )
                    comment_scores_cache[comment.comment_id] = (score, comment)

                    # Use dynamic threshold to decide like
                    if score >= dynamic_threshold:
                        liked_comments.append(comment.comment_id)
                        logging.debug(f"💖 User {self.user_id} selected comment {comment.comment_id} (affinity: {score:.2f}, threshold: {dynamic_threshold:.2f}) - content: '{comment.content[:50]}...'")

            # Sort and select using cached scores
            if liked_comments:
                # Get scores from cache to avoid recompute
                comment_scores = [(cid, comment_scores_cache[cid][0]) for cid in liked_comments]

                # Sort and select - aim to reduce like frequency
                comment_scores.sort(key=lambda x: x[1], reverse=True)

                # Dynamically adjust selection count - increase like frequency
                min_selection = 2  # Increased from 1 to 2
                max_selection = 5  # Increased from 3 to 5
                if 'extroverted' in str(personality_traits).lower():
                    max_selection = 6  # Increased from 3 to 6
                if 'introverted' in str(personality_traits).lower():
                    min_selection = 1  # Introverts like at least 1
                    max_selection = 3  # Increased from 2 to 3

                final_likes = [cid for cid, score in comment_scores[:min(max_selection, max(min_selection, len(comment_scores)))]]

                logging.info(f"🎯 User {self.user_id} intelligently selected {len(final_likes)} comment likes (threshold: {dynamic_threshold:.2f}, analyzed {total_comments_analyzed} comments)")
                return final_likes
            else:
                # Silent handling: no suitable comments
                return []

        except Exception as e:
            logging.error(f"❌ User {self.user_id} intelligent comment liking failed: {e}")
            return []

    def _parse_persona_identifier(self, persona_str: str) -> dict:
        """
        Parse simple persona identifier string to infer user traits
        Example: "NeutralUser029" -> neutral user traits
        """
        persona_str = persona_str.lower()

        # Default persona structure
        default_persona = {
            'political_stance': 'moderate',
            'important_values': [],
            'personality': [],
            'social_tendency': []
        }

        # Infer traits from identifier
        if 'neutral' in persona_str:
            default_persona['political_stance'] = 'moderate'
            default_persona['personality'] = ['balanced', 'thoughtful']
        elif 'liberal' in persona_str:
            default_persona['political_stance'] = 'liberal'
            default_persona['important_values'] = ['equality', 'social_justice']
            default_persona['personality'] = ['progressive', 'empathetic']
        elif 'conservative' in persona_str:
            default_persona['political_stance'] = 'conservative'
            default_persona['important_values'] = ['tradition', 'stability']
            default_persona['personality'] = ['traditional', 'cautious']
        elif 'activist' in persona_str:
            default_persona['political_stance'] = 'very liberal'
            default_persona['important_values'] = ['social_change', 'activism']
            default_persona['personality'] = ['passionate', 'outspoken']
            default_persona['social_tendency'] = ['community_oriented']
        elif 'skeptical' in persona_str or 'critic' in persona_str:
            default_persona['personality'] = ['analytical', 'skeptical']
            default_persona['important_values'] = ['truth', 'transparency']

        logging.debug(f"User {self.user_id} inferred persona from identifier '{persona_str}': {default_persona}")
        return default_persona

    def _calculate_comment_affinity_score(self, comment, political_stance: str, important_values: list,
                                        personality_traits: list, social_tendency: list, memory_keywords: set) -> float:
        """Calculate user's affinity score for a comment (0.0-1.0)"""
        try:
            content = comment.content.lower()
            score = 0.0
            factors = 0

            # 1. Political stance match (weight: 0.3)
            political_score = self._match_political_stance(content, political_stance)
            score += political_score * 0.3
            factors += 1

            # 2. Values match (weight: 0.25)
            values_score = self._match_values(content, important_values)
            score += values_score * 0.25
            factors += 1

            # 3. Personality trait match (weight: 0.2)
            personality_score = self._match_personality(content, personality_traits)
            score += personality_score * 0.2
            factors += 1

            # 4. Social tendency match (weight: 0.15)
            social_score = self._match_social_tendency(content, social_tendency)
            score += social_score * 0.15
            factors += 1

            # 5. Memory relevance (weight: 0.1)
            memory_score = self._match_memory_keywords(content, memory_keywords)
            score += memory_score * 0.1
            factors += 1

            return min(1.0, score) if factors > 0 else 0.0

        except Exception as e:
            logging.error(f"Error calculating comment affinity score: {e}")
            return 0.0

    def _match_political_stance(self, content: str, stance: str) -> float:
        """Match political stance - enhanced version"""
        if 'very liberal' in stance or 'liberal' in stance:
            liberal_keywords = [
                'equality', 'justice', 'progressive', 'inclusive', 'diversity', 'social', 'environment', 'climate',
                'reform', 'change', 'rights', 'fairness', 'equity', 'tolerance', 'acceptance', 'minority',
                'sustainable', 'renewable', 'universal', 'healthcare', 'education', 'regulation',
                'government support', 'social programs', 'welfare', 'collective action'
            ]
            # Weighted match: core words carry higher weight
            core_words = ['equality', 'justice', 'progressive', 'rights', 'fairness', 'diversity']
            matches = 0
            for keyword in liberal_keywords:
                if keyword in content:
                    weight = 1.5 if keyword in core_words else 1.0
                    matches += weight
            return min(1.0, matches * 0.2)
        elif 'very conservative' in stance or 'conservative' in stance:
            conservative_keywords = [
                'traditional', 'family', 'freedom', 'security', 'responsibility', 'values', 'heritage',
                'order', 'stability', 'discipline', 'respect', 'authority', 'individual responsibility',
                'free market', 'capitalism', 'private', 'enterprise', 'self-reliance', 'constitution',
                'patriotism', 'defense', 'law and order', 'moral', 'virtue'
            ]
            # Weighted match
            core_words = ['traditional', 'family', 'freedom', 'responsibility', 'values', 'security']
            matches = 0
            for keyword in conservative_keywords:
                if keyword in content:
                    weight = 1.5 if keyword in core_words else 1.0
                    matches += weight
            return min(1.0, matches * 0.2)
        else:  # moderate, libertarian, etc.
            moderate_keywords = [
                'balanced', 'reasonable', 'practical', 'compromise', 'solution', 'both sides',
                'middle ground', 'pragmatic', 'nuanced', 'complex', 'depends', 'context',
                'evidence-based', 'measured', 'careful', 'thoughtful', 'bi-partisan'
            ]
            matches = sum(1 for keyword in moderate_keywords if keyword in content)
            return min(1.0, matches * 0.25)

    def _match_values(self, content: str, values: list) -> float:
        """Match important values - enhanced version"""
        if not values:
            return 0.0

        value_keywords = {
            'integrity': ['honest', 'truth', 'authentic', 'genuine', 'reliable', 'trustworthy', 'transparent', 'sincere', 'credible'],
            'compassion': ['caring', 'kind', 'empathy', 'understanding', 'support', 'helping', 'gentle', 'nurturing', 'sympathetic'],
            'independence': ['freedom', 'choice', 'autonomy', 'self', 'individual', 'liberty', 'personal', 'own decision'],
            'community': ['together', 'collective', 'shared', 'group', 'society', 'cooperation', 'unity', 'solidarity'],
            'ambition': ['goal', 'achieve', 'success', 'drive', 'excel', 'accomplish', 'aspire', 'determination'],
            'fairness': ['equal', 'just', 'fair', 'impartial', 'balanced', 'equitable', 'unbiased'],
            'respect': ['respectful', 'dignity', 'honor', 'courtesy', 'polite', 'considerate'],
            'innovation': ['creative', 'innovative', 'new', 'progress', 'advancement', 'breakthrough'],
            'tradition': ['heritage', 'history', 'customs', 'established', 'time-tested', 'legacy'],
            'security': ['safe', 'protect', 'secure', 'stability', 'certainty', 'predictable']
        }

        total_matches = 0
        matched_values = 0
        for value in values:
            value_lower = value.lower()
            if value_lower in value_keywords:
                matched_values += 1
                keywords = value_keywords[value_lower]
                matches = sum(1 for keyword in keywords if keyword in content)
                if matches > 0:
                    total_matches += min(matches, 3)  # Cap individual value matches at 3

        # Bonus for multiple value alignment
        alignment_bonus = 1.2 if matched_values >= 2 else 1.0
        return min(1.0, (total_matches * 0.15 * alignment_bonus))

    def _match_personality(self, content: str, traits: list) -> float:
        """Match personality traits - enhanced version"""
        if not traits:
            return 0.0

        trait_keywords = {
            'introverted': ['quiet', 'thoughtful', 'careful', 'deep', 'reflect', 'introspective', 'reserved', 'contemplative'],
            'extroverted': ['exciting', 'social', 'outgoing', 'energy', 'active', 'enthusiastic', 'vibrant', 'engaging'],
            'thoughtful': ['consider', 'think', 'analyze', 'careful', 'wise', 'deliberate', 'mindful', 'reflective'],
            'analytical': ['data', 'evidence', 'logic', 'reason', 'fact', 'systematic', 'methodical', 'rational'],
            'creative': ['innovative', 'artistic', 'imaginative', 'original', 'unique', 'inventive', 'expressive'],
            'optimistic': ['positive', 'hopeful', 'bright', 'upbeat', 'encouraging', 'confident', 'cheerful'],
            'pragmatic': ['practical', 'realistic', 'sensible', 'down-to-earth', 'workable', 'feasible'],
            'empathetic': ['understanding', 'compassionate', 'sensitive', 'caring', 'supportive', 'kind'],
            'decisive': ['determined', 'firm', 'resolute', 'clear', 'definitive', 'strong-willed'],
            'curious': ['interested', 'questioning', 'explore', 'wonder', 'investigate', 'learn']
        }

        total_matches = 0
        for trait in traits:
            trait_lower = trait.lower()
            if trait_lower in trait_keywords:
                keywords = trait_keywords[trait_lower]
                matches = sum(1 for keyword in keywords if keyword in content)
                total_matches += min(matches, 2)  # Cap matches per trait at 2

        return min(1.0, total_matches * 0.2)

    def _match_social_tendency(self, content: str, tendencies: list) -> float:
        """Match social tendency"""
        if not tendencies:
            return 0.0

        tendency_keywords = {
            'friendly': ['nice', 'kind', 'welcome', 'positive', 'good'],
            'reserved': ['careful', 'thoughtful', 'consider', 'maybe', 'perhaps'],
            'confident': ['sure', 'definitely', 'absolutely', 'certain', 'believe'],
            'neutral': ['balanced', 'both', 'depends', 'various', 'different']
        }

        total_matches = 0
        for tendency in tendencies:
            tendency_lower = tendency.lower()
            if tendency_lower in tendency_keywords:
                keywords = tendency_keywords[tendency_lower]
                matches = sum(1 for keyword in keywords if keyword in content)
                total_matches += matches

        return min(1.0, total_matches * 0.2)

    def _match_memory_keywords(self, content: str, memory_keywords: set) -> float:
        """Match memory keywords - enhanced version"""
        if not memory_keywords:
            return 0.0

        content_words = set(content.lower().split())

        # Direct keyword match
        direct_matches = len(content_words & memory_keywords)

        # Semantic match - check related concepts
        semantic_matches = 0
        memory_concepts = {
            'political': {'election', 'vote', 'government', 'policy', 'politics'},
            'social': {'community', 'society', 'people', 'group', 'social'},
            'economic': {'money', 'economy', 'business', 'work', 'financial'},
            'environmental': {'climate', 'environment', 'nature', 'green', 'sustainable'},
            'technology': {'tech', 'digital', 'online', 'internet', 'computer'},
            'health': {'health', 'medical', 'doctor', 'medicine', 'care'},
            'education': {'school', 'learn', 'education', 'teacher', 'study'}
        }

        # Check whether memory includes terms from a concept domain
        for concept, concept_words in memory_concepts.items():
            if memory_keywords & concept_words:  # Memory includes this concept's words
                content_concept_matches = len(content_words & concept_words)
                if content_concept_matches > 0:
                    semantic_matches += content_concept_matches * 0.5  # Lower weight for semantic match

        total_score = direct_matches + semantic_matches
        return min(1.0, total_score * 0.08)  # Adjust weight to balance total score

    async def react_to_feed(
            self,
            openai_client: OpenAI,
            engine: str,
            feed
        ):
            """
            React to the feed using LLM-driven decisions.
            News agents don't react to feeds - they only publish news.

            Args:
                openai_client: The OpenAI client to use for generating content.
                engine: The engine to use for generation.
                feed: A list of Post objects representing the user's feed.
            """
            # Skip feed reactions for news agents or if comment limit is reached
            if self.is_news_agent or self.comment_count >= self.comment_limit:
                if self.comment_count >= self.comment_limit:
                    logging.info(f"User {self.user_id} has reached their comment limit of {self.comment_limit}.")
                return

            feed_segments = self._split_feed_segments(feed)
            if not feed_segments:
                return
    
            # Get the reasoning configuration
            include_reasoning = self.experiment_config.get('experiment', {}).get('settings', {}).get('include_reasoning', False)
    
            system_prompt = await self._create_personalized_system_prompt()
    
                # Create a dynamic FeedAction class based on whether reasoning is included
            if include_reasoning:
                class FeedActionWithReasoning(BaseModel):
                    action: Literal[
                        "like-post", "share-post", "flag-post", "follow-user",
                        "unfollow-user", "comment-post", "like-comment", "ignore",
                        "add-note", "rate-note"
                    ]
                    target: Optional[str] = None
                    content: Optional[str] = None
                    reasoning: Optional[str] = None
                    note_rating: Optional[Literal["helpful", "not-helpful"]] = None

                class FeedReactionWithReasoning(BaseModel):
                    actions: List[FeedActionWithReasoning]

                response_model = FeedReactionWithReasoning
            else:
                response_model = FeedReaction

            import asyncio
            actual_engine = self.get_dynamic_model() if hasattr(self, 'get_dynamic_model') else (self.selected_model if hasattr(self, 'selected_model') else engine)

            # Use LLM to generate reactions for each feed segment sequentially
            for segment_index, segment_feed in enumerate(feed_segments, start=1):
                if not segment_feed:
                    continue

                if self.comment_count >= self.comment_limit:
                    logging.info(f"User {self.user_id} has reached their comment limit of {self.comment_limit}.")
                    break

                prompt = self._create_feed_reaction_prompt(segment_feed)

                try:
                    reaction = await asyncio.to_thread(
                        Utils.generate_llm_response,
                        openai_client=openai_client,
                        engine=actual_engine,
                        prompt=prompt,
                        system_message=system_prompt,
                        response_model=response_model,
                        temperature=self.temperature
                    )

                    if reaction and reaction.actions:

                        # <<< Logging prompt & actions to JSONL >>>
                        import json
                        import datetime

                        EXPORT_FILE_NAME = "temp_reaction_log.jsonl"

                        try:
                            try:
                                actions_list = [action.model_dump() for action in reaction.actions]
                            except AttributeError:
                                actions_list = [action.dict() for action in reaction.actions]

                            feed_content = "\n".join([
                                f"post_id: {post.post_id} | content: {(post.summary or post.content)} "
                                f"(by User {str(post.author_id)}) "
                                f"[Likes: {post.num_likes or 0}, Shares: {post.num_shares or 0}, Comments: {post.num_comments or 0}]"
                                + (f" {post.agent_response_display}" if hasattr(post, 'is_agent_response') and post.is_agent_response else "")
                                + (f"\nFACT CHECK: {post.fact_check_verdict.upper()} "
                                   f"(Confidence: {post.fact_check_confidence:.0%})"
                                   if hasattr(post, 'fact_check_verdict') else "")
                                + f"\nComments:\n" + "\n".join([
                                    f"- comment_id: {comment.comment_id} | content: {comment.content} (by User {str(comment.author_id)}) [Likes: {comment.num_likes or 0}]"
                                    for comment in post.comments[:3]
                                ])
                                + (f"\n  Community Notes:\n" + "\n".join([
                                    f"  ? note_id: {note.note_id} | content: {note.content} (Helpful: {str(note.helpful_ratings)}, Not Helpful: {str(note.not_helpful_ratings)})"
                                    for note in post.community_notes[:3] if note.is_visible
                                ]) if any(note.is_visible for note in post.community_notes[:3]) else "")
                                for _, post in enumerate(segment_feed)
                            ])

                            spacing = " " * 50
                            log_pairs = [
                                ("timestamp", datetime.datetime.now().isoformat()),
                                ("user_id", self.user_id),
                                ("feed_segment_index", segment_index),
                                ("system prompt", system_prompt),
                                ("prompt", prompt),
                                ("feed_content", feed_content),
                                ("actions", actions_list)
                            ]
                            serialized = spacing.join(
                                f"\"{key}\":{json.dumps(value, ensure_ascii=False)}"
                                for key, value in log_pairs
                            )

                            with open(EXPORT_FILE_NAME, 'a', encoding='utf-8') as f:
                                f.write("{" + serialized + "}\n")

                        except Exception as log_e:
                            logging.warning(f"User {self.user_id} - Failed to write to reaction log: {log_e}")

                        # <<< Process reactions >>>

                        self._process_reaction(reaction, segment_feed)
                    else:
                        logging.warning(f"User {self.user_id} generated empty reaction for segment {segment_index}")

                except Exception as e:
                    # Special handling for Pydantic validation errors
                    if "ValidationError" in str(type(e)) or "validation error" in str(e).lower():
                        logging.error(f"Validation error for user {self.user_id}: {e}")
                        logging.error("This might be due to invalid actions in LLM response. The error has been logged for debugging.")
                    else:
                        logging.error(f"Error generating reaction for user {self.user_id}: {e}")

                    # Add detailed traceback for debugging
                    import traceback
                    logging.error(f"Full traceback for user {self.user_id}:")
                    logging.error(traceback.format_exc())

                    return
            # Check for reflection after processing reactions
            try:
                result = fetch_one('''
                    SELECT COUNT(*) as count FROM agent_memories
                    WHERE user_id = ? AND memory_type = 'interaction'
                ''', (self.user_id,))

                if result and result['count'] % 2 == 0:  # every 2 interactions
                    self.memory.reflect(openai_client, engine, self.temperature)
            except Exception as e:
                if "unable to open database file" in str(e):
                    logging.warning(f"Database connection error in react_to_feed reflection check, skipping reflection")
                else:
                    raise e

    def _create_feed_reaction_prompt(self, feed) -> str:
        """
        Create a prompt for the LLM to decide how to react to the feed.
        """

        def _build_post_feed_line(post):
            """
            Build a single feed line for a post.
            - Use summary by default (shorter, saves tokens)
            - If content includes [OFFICIAL EXPLANATION], ensure that clarification appears too
            """
            base_text = (post.summary or post.content or "")
            content_text = base_text

            full_content = getattr(post, "content", "") or ""
            marker = "[OFFICIAL EXPLANATION]"
            if marker in full_content and marker not in base_text:
                # Extract a short official explanation snippet to keep prompt short
                idx = full_content.find(marker)
                # Take a segment starting at marker (e.g., ~300 chars)
                explanation_snippet = full_content[idx:idx + 300]
                content_text = f"{base_text}\n{explanation_snippet}".strip()

            line = (
                f"post_id: {post.post_id} | content: {content_text} "
                f"(by User {str(post.author_id)}) "
                f"[Likes: {post.num_likes or 0}, Shares: {post.num_shares or 0}, Comments: {post.num_comments or 0}]"
            )

            if hasattr(post, "is_agent_response") and post.is_agent_response:
                line += f" {post.agent_response_display}"

            # Fact-check info
            if hasattr(post, "fact_check_verdict") and post.fact_check_verdict:
                line += (
                    f"\nFACT CHECK: {post.fact_check_verdict.upper()} "
                    f"(Confidence: {post.fact_check_confidence:.0%})"
                )

            # Comments
            if post.comments:
                comments_text = "\n".join(
                    [
                        f"- comment_id: {comment.comment_id} | content: {comment.content} "
                        f"(by User {str(comment.author_id)}) [Likes: {comment.num_likes or 0}]"
                        for comment in post.comments[:3]
                    ]
                )
            else:
                comments_text = "No comments yet"
            line += f"\nComments:\n{comments_text}"

            # Community notes
            visible_notes = [note for note in post.community_notes[:3] if note.is_visible]
            if visible_notes:
                notes_text = "\n".join(
                    [
                        f"  • note_id: {note.note_id} | content: {note.content} "
                        f"(Helpful: {str(note.helpful_ratings)}, Not Helpful: {str(note.not_helpful_ratings)})"
                        for note in visible_notes
                    ]
                )
                line += f"\n  Community Notes:\n{notes_text}"

            return line

        # Check if prebunking is enabled
        # Only enable prebunking for neutral users (most vulnerable to misinformation)
        prebunking_enabled = (
            self.experiment_config.get('prebunking_system', {}).get('enabled', False)
            and not self.is_news_agent
            and self.persona.get('type') == 'neutral'  # Only neutral users
        )

        # Generate prebunking warnings if enabled
        prebunking_warnings = []
        if prebunking_enabled:
            prebunking_warnings = self._generate_prebunking_warnings(feed)

        feed_content = "\n".join([_build_post_feed_line(post) for _, post in enumerate(feed)])

        # Get the reasoning configuration
        include_reasoning = self.experiment_config.get('experiment', {}).get('settings', {}).get('include_reasoning', False)

        # Check if prebunking is enabled
        prebunking_enabled = self.experiment_config.get('prebunking_system', {}).get('enabled', False)

        prompt = AgentPrompts.create_feed_reaction_prompt(
            self.persona,
            feed_content,
            self.experiment_type,
            include_reasoning,
            prebunking_warnings,  # Add prebunking warnings to the prompt
            prebunking_enabled    # Add prebunking enabled flag
        )

        # logging.info(f"Feed reaction prompt: {prompt}")

        return prompt

    def _split_feed_segments(self, feed):
        """
        Split the current feed into two segments so prompts can cover the
        "first half" and "second half" separately.
        To keep behavior predictable, use a minimal split tied to post order:
        - If post count <= 5: return a single segment (avoid over-splitting)
        - If post count > 5: first 5 posts as segment one, remainder as segment two

        This achieves the desired effect:
        - First prompt sees only the first 5 posts
        - Second prompt sees only the remaining posts
        """
        if not feed:
            return []

        if len(feed) <= 5:
            # If few posts, use a single segment to avoid sparse prompts
            return [feed]

        # Fixed: first 5 = segment one, rest = segment two
        primary_segment = feed[:5]
        secondary_segment = feed[5:]
        return [primary_segment, secondary_segment] if secondary_segment else [feed]

    def _generate_prebunking_warnings(self, feed):
        """
        Generate prebunking warnings - if prebunking is enabled, always add safety prompts.
        Simplified version that just adds the general safety prompt.
        """
        warnings = []

        # Check if prebunking is enabled
        prebunking_enabled = self.experiment_config.get('prebunking_system', {}).get('enabled', False)

        if not prebunking_enabled:
            return warnings

        try:
            # Load safety prompts
            import json
            import os

            safety_prompts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'safety_prompts.json')
            if not os.path.exists(safety_prompts_path):
                return warnings

            with open(safety_prompts_path, 'r', encoding='utf-8') as f:
                safety_prompts = json.load(f)

            # Always add general safety warning if prebunking is enabled
            if 'general_prebunking' in safety_prompts:
                warning = safety_prompts['general_prebunking']['prebunking_prompt']
                warnings.append(warning['content'])

        except Exception as e:
            logging.error(f"Failed to load safety prompts: {e}")

        return warnings

    def _process_reaction(self, reaction: FeedReaction, feed):
        """Process the reaction generated by the LLM - simplified and streamlined."""
        try:
            # Get valid targets from feed
            valid_targets = {
                'post': {post.post_id for post in feed},
                'comment': {comment.comment_id for post in feed for comment in post.comments},
                'user': {row['user_id'] for row in fetch_all('SELECT user_id FROM users WHERE user_id != ?', (self.user_id,))},
                'note': {note.note_id for post in feed for note in post.community_notes if note.is_visible}
            }

            processed_actions = set()
            include_reasoning = self.experiment_config.get('experiment', {}).get('settings', {}).get('include_reasoning', False)

            for action_data in reaction.actions:
                action = action_data.action
                target = action_data.target
                content = action_data.content
                action_reasoning = getattr(action_data, 'reasoning', None)

                # Process all actions - no filtering

                # Skip duplicate actions
                action_key = f"{action}:{target}"
                if action_key in processed_actions:
                    continue
                processed_actions.add(action_key)

                # Execute action
                time.sleep(0.5)  # Rate limiting
                
                # Log the action being processed
                model_info = getattr(self, 'selected_model', 'unknown')
                
                try:
                    # Record to database
                    if action == 'comment-post' or action == 'add-note':
                        if include_reasoning and action_reasoning:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type, target_id, content, reasoning)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (self.user_id, action.replace('-', '_'), target, content, action_reasoning))
                        else:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type, target_id, content)
                                VALUES (?, ?, ?, ?)
                            ''', (self.user_id, action.replace('-', '_'), target, content))
                    elif action == 'ignore':
                        if include_reasoning and action_reasoning:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type, reasoning)
                                VALUES (?, 'ignore', ?)
                            ''', (self.user_id, action_reasoning))
                        else:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type)
                                VALUES (?, 'ignore')
                            ''', (self.user_id,))
                    else:
                        if include_reasoning and action_reasoning:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type, target_id, reasoning)
                                VALUES (?, ?, ?, ?)
                            ''', (self.user_id, action.replace('-', '_'), target, action_reasoning))
                        else:
                            execute_query('''
                                INSERT INTO user_actions (user_id, action_type, target_id)
                                VALUES (?, ?, ?)
                            ''', (self.user_id, action.replace('-', '_'), target))

                    # Execute the actual action
                    if action == 'comment-post':
                        if self.comment_count < self.comment_limit:
                            self.create_comment(target, content)
                            self.comment_count += 1
                            logging.info(f"💬 User {self.user_id} commented on post {target}: {content}")
                        else:
                            logging.warning(f"⚠️ User {self.user_id} reached comment limit, skipping comment")
                    elif action == 'add-note':
                        self.add_community_note(target, content)
                        logging.info(f"📝 User {self.user_id} added note to post {target}: {content}")
                    elif action == 'rate-note':
                        is_helpful = action_data.note_rating == "helpful"
                        self.rate_community_note(target, is_helpful)
                        logging.info(f"⭐ User {self.user_id} rated note {target} as {action_data.note_rating}")
                    elif action == 'like-comment':
                        # Record the action to user_actions table (INSERT OR IGNORE to handle duplicates)
                        execute_query('''
                            INSERT OR IGNORE INTO user_actions (user_id, action_type, target_id)
                            VALUES (?, 'like_comment', ?)
                        ''', (self.user_id, target))
                        
                        # Update comment likes count only if the action was actually inserted
                        # Use a subquery to check if the action exists and update accordingly
                        execute_query('''
                            UPDATE comments 
                            SET num_likes = num_likes + 1 
                            WHERE comment_id = ? 
                            AND EXISTS (
                                SELECT 1 FROM user_actions 
                                WHERE user_id = ? AND action_type = 'like_comment' AND target_id = ?
                            )
                        ''', (target, self.user_id, target))
                        
                        # Update author's total likes received
                        execute_query('''
                            UPDATE users
                            SET total_likes_received = total_likes_received + 1
                            WHERE user_id = (
                                SELECT author_id
                                FROM comments
                                WHERE comment_id = ?
                            )
                            AND EXISTS (
                                SELECT 1 FROM user_actions 
                                WHERE user_id = ? AND action_type = 'like_comment' AND target_id = ?
                            )
                        ''', (target, self.user_id, target))
                        
                        logging.info(f"👍 User {self.user_id} liked comment {target}")
                    elif action == 'like-post':
                        # Record the action to user_actions table (INSERT OR IGNORE to handle duplicates)
                        execute_query('''
                            INSERT OR IGNORE INTO user_actions (user_id, action_type, target_id)
                            VALUES (?, 'like', ?)
                        ''', (self.user_id, target))
                        
                        # Update post likes count (only if post exists)
                        execute_query('''
                            UPDATE posts 
                            SET num_likes = num_likes + 1 
                            WHERE post_id = ?
                        ''', (target,))
                        
                        # Update author's total likes received (only if post exists)
                        execute_query('''
                            UPDATE users
                            SET total_likes_received = total_likes_received + 1
                            WHERE user_id = (
                                SELECT author_id
                                FROM posts
                                WHERE post_id = ?
                            )
                        ''', (target,))
                        
                        logging.info(f"👍 User {self.user_id} liked post {target} (post_id: {target})")
                    elif action == 'share-post':
                        self.share_post(target)
                        logging.info(f"🔄 User {self.user_id} shared post {target}")
                    elif action == 'flag-post':
                        self.flag_post(target)
                        logging.info(f"🚩 User {self.user_id} flagged post {target}")
                    elif action == 'follow-user':
                        self.follow_user(target)
                        logging.info(f"👥 User {self.user_id} followed user {target}")
                    elif action == 'unfollow-user':
                        self.unfollow_user(target)
                        logging.info(f"👥 User {self.user_id} unfollowed user {target}")
                    elif action == 'ignore':
                        self.ignore()
                        logging.info(f"😴 User {self.user_id} chose to ignore")
                    else:
                        # Try to call action method for any other action
                        method_name = action.replace('-', '_')
                        if hasattr(self, method_name):
                            getattr(self, method_name)(target)
                            logging.info(f"⚡ User {self.user_id} executed {action} on {target}")
                        else:
                            # For unknown actions, just log and continue
                            logging.debug(f"❓ Unknown action method '{method_name}' for action '{action}' - skipping execution")

                    # Stop writing interaction memories; integrate into a single memory after post/comment
                    
                    # Remove periodic integration every 5 actions (now update at end of post/comment)

                except Exception as e:
                    logging.error(f"Error executing action {action}: {e}")

        except Exception as e:
            logging.error(f"Error processing reaction: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def add_community_note(self, post_id: str, content: str) -> str:
        """
        Add a community note to a post.
        Returns the note_id.
        """
        note_id = Utils.generate_formatted_id("note")

        execute_query('''
            INSERT INTO community_notes (
                note_id, post_id, author_id, content,
                helpful_ratings, not_helpful_ratings
            )
            VALUES (?, ?, ?, ?, 0, 0)
        ''', (note_id, post_id, self.user_id, content))

        # Record the note creation action
        execute_query('''
            INSERT INTO user_actions (user_id, action_type, target_id, content)
            VALUES (?, 'add_note', ?, ?)
        ''', (self.user_id, post_id, content))
        logging.info(f"User {self.user_id} added note to post {post_id}: {content}")
        return note_id

    def rate_community_note(self, note_id: str, is_helpful: bool) -> None:
        """
        Rate a community note as helpful or not helpful.
        """
        # First check if the note exists
        result = fetch_one('''
            SELECT COUNT(*) as count FROM community_notes
            WHERE note_id = ?
        ''', (note_id,))

        if not result or result['count'] == 0:
            logging.warning(f"Note {note_id} does not exist")
            return

        # Check if user already rated this note
        result = fetch_one('''
            SELECT COUNT(*) as count FROM note_ratings
            WHERE note_id = ? AND user_id = ?
        ''', (note_id, self.user_id))
        
        if result and result['count'] > 0:
            return

        # Add rating
        rating_type = "helpful" if is_helpful else "not_helpful"
        execute_query('''
            INSERT INTO note_ratings (note_id, user_id, rating)
            VALUES (?, ?, ?)
        ''', (note_id, self.user_id, rating_type))

        # Update note rating counts
        field = "helpful_ratings" if is_helpful else "not_helpful_ratings"
        execute_query(f'''
            UPDATE community_notes
            SET {field} = {field} + 1
            WHERE note_id = ?
        ''', (note_id,))

        self.conn.commit()
        logging.info(f"User {self.user_id} rated note {note_id} as {rating_type}")


    def _create_single_post_comment_prompt(self, post: Post) -> str:
        """
        Create a prompt for the LLM to generate a comment for a single post.
        """
        post_content = (
            f"post_id: {post.post_id} | content: {post.content} "
            f"(by User {str(post.author_id)})"
            + (f" {post.agent_response_display}" if hasattr(post, 'is_agent_response') and post.is_agent_response else "")
            + (f"\nFACT CHECK: {post.fact_check_verdict.upper()} "
                f"(Confidence: {post.fact_check_confidence:.0%})"
                if hasattr(post, 'fact_check_verdict') else "")
            + f"\nComments:\n" + "\n".join([
                f"- comment_id: {comment.comment_id} | content: {comment.content} (by User {str(comment.author_id)})"
                for comment in post.comments[:3]
            ])
        )

        # Use a simplified prompt for generating a single comment
        prompt = f"""Your Persona:
{self.persona}

Here is a post from the platform:
--- POST START ---
{post_content}
--- POST END ---

🎯 **COMMENT DIVERSITY REQUIREMENTS**:
- NEVER use generic phrases like "This is concerning", "This is important", "I agree", "Interesting"
- AVOID starting with "I think", "In my opinion", "I believe" - be more creative and direct
- USE unique opening phrases that reflect YOUR specific personality and background
- INCLUDE specific details from your personal experience, profession, or interests
- VARY your comment style - sometimes short and punchy, sometimes detailed and thoughtful
- SHOW your unique perspective - what makes YOU different from other users?
- REFERENCE specific aspects of the post that resonate with YOUR worldview
- BE AUTHENTIC to your persona - let your personality shine through your words

Based on your persona, memories, and reflections, write a single, concise, and engaging comment for this post. Your comment should be a direct response to the post's content.

Your Comment:"""

        return prompt
