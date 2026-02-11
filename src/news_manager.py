import logging
import sqlite3
import jsonlines
import asyncio
import json
import os
import random
from utils import Utils
from agent_user import AgentUser
# Remove complex user engagement mechanism

class NewsManager:
    def __init__(self, config: dict, conn: sqlite3.Connection):
        self.config = config
        self.conn = conn
        self.news_agent = self._create_news_agent()

        # Simplified news selection mode
        self.news_selection_mode = 'sequential_ordered'

        # News index tracking and bucket info
        self.current_news_index = 0  # Total published news count
        self.ordered_news = []
        self.normal_news = []
        self.extreme_news = []
        self.normal_index = 0
        self.extreme_index = 0
        self.news_mix_pattern = ['normal'] * 9 + ['extreme']
        self.news_mix_index = 0
        self._first_injection_pending = True
        # First injection should be 10 posts: 9 normal + 1 extreme
        self._first_injection_pattern = ['normal'] * 9 + ['extreme']
        # Unified model selection via MultiModelSelector (summary role)
        from multi_model_selector import multi_model_selector
        self._summary_client, self._summary_model = multi_model_selector.create_openai_client(role="summary")

        # Optional knob: strictly use precomputed summaries and avoid LLM
        self.use_precomputed_summary_only = self.config.get('news_injection', {}).get('use_precomputed_summary_only', False)

        # Mapping file path (define upfront)
        self.mapping_file_path = 'data/fake_news_truth_mapping.json'
        
        # Load COVID-19 fake news data
        self.covid_fake_news = []
        self.covid_fake_news_index = 0
        self.covid_fake_news_used_indices = set()  # Track used indices to avoid duplicates
        self._load_covid_fake_news()

        # Reset mapping file each run (overwrite old file)
        self._ensure_mapping_file_exists()

        # Load ordered news database
        self._load_ordered_news()
        self._initialize_news_buckets()
        print(f"📰 News selection mode: sequential push (from low controversy to high)")
        print(f"📊 Loaded {len(self.ordered_news)} ordered news items")
        print(f"📰 Loaded {len(self.covid_fake_news)} COVID-19 fake news items")
    
    def _create_news_agent(self) -> AgentUser:
        """Create a specialized news agent."""
        news_config = {
            'persona': {
                'name': 'Agentverse News',
                'type': 'news_org',
                'profession': 'News Organization',
                'background': 'Professional outlet focused on accurate, timely reporting and public-safety updates.',
                'personality_traits': [
                    'Verifies information before posting',
                    'Highlights actionable steps for readers',
                    'Balances calm tone with urgency during crises'
                ],
                'communication_style': {
                    'tone': 'Measured and factual',
                    'engagement_level': 'high'
                }
            },
        }
        
        news_agent_id = "agentverse_news"
        
        # Register news agent in database
        self.conn.execute('''
            INSERT INTO users (
                user_id, persona, creation_time
            )
            VALUES (?, ?, datetime('now'))
        ''', (news_agent_id, json.dumps(news_config['persona'], ensure_ascii=False)))
        self.conn.commit()
        
        return AgentUser(
            user_id=news_agent_id,
            user_config=news_config,
            temperature=0.3,  # Lower temperature for more consistent news reporting
            is_news_agent=True
        )

    def _load_ordered_news(self):
        """Load ordered news database"""
        try:
            import jsonlines
            with jsonlines.open('data/neutral-news.jsonl') as reader:
                self.ordered_news = list(reader)
            print(f"✅ Loaded {len(self.ordered_news)} ordered news items")
        except FileNotFoundError as e:
            raise FileNotFoundError(
                "Required news dataset missing: data/neutral-news.jsonl"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load data/neutral-news.jsonl: {e}") from e

    def _load_covid_fake_news(self):
        """Load COVID-19 fake news data"""
        try:
            # Try relative paths; if that fails, use absolute path
            covid_file_paths = [
                'data/misinformation-news.json',
                '../data/misinformation-news.json',
                '/mnt/c/Users/lms/Desktop/Public-opinion-balance/data/misinformation-news.json'
            ]
            
            covid_file_path = None
            for path in covid_file_paths:
                if os.path.exists(path):
                    covid_file_path = path
                    break
            
            if not covid_file_path:
                print(f"⚠️ COVID-19 fake news file not found, tried paths: {covid_file_paths}")
                self.covid_fake_news = []
                return
            
            with open(covid_file_path, 'r', encoding='utf-8') as f:
                self.covid_fake_news = json.load(f)
            print(f"✅ Loaded {len(self.covid_fake_news)} COVID-19 fake news items (from {covid_file_path})")
        except Exception as e:
            print(f"❌ Failed to load COVID-19 fake news: {e}")
            self.covid_fake_news = []

    def _ensure_mapping_file_exists(self):
        """Ensure mapping file exists; reset to empty each run"""
        os.makedirs(os.path.dirname(self.mapping_file_path), exist_ok=True)
        # Overwrite mapping file each run, reset to empty
        with open(self.mapping_file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        logging.info(f"📝 Reset mapping file: {self.mapping_file_path} (restart each run)")

    def _load_truth_mapping(self):
        """Load real news mapping table"""
        try:
            if os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Failed to load mapping file: {e}")
            return {}

    def _save_truth_mapping(self, mapping):
        """Save real news mapping table"""
        try:
            with open(self.mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save mapping file: {e}")

    def _get_next_covid_fake_narrative(self):
        """Get next COVID-19 fake news item (avoid duplicates)"""
        if not self.covid_fake_news:
            return None, None
        
        # If all data used, reset used list (start over)
        if len(self.covid_fake_news_used_indices) >= len(self.covid_fake_news):
            logging.info(f"📰 COVID-19 fake news data fully used, resetting used list")
            self.covid_fake_news_used_indices.clear()
            self.covid_fake_news_index = 0
        
        # Starting from current index, find next unused entry
        start_index = self.covid_fake_news_index
        max_iterations = len(self.covid_fake_news)
        iterations = 0
        
        while iterations < max_iterations:
            if self.covid_fake_news_index >= len(self.covid_fake_news):
                self.covid_fake_news_index = 0
            
            # Check if current index is used
            if self.covid_fake_news_index not in self.covid_fake_news_used_indices:
                # Found unused entry
                entry = self.covid_fake_news[self.covid_fake_news_index]
                # Mark as used
                self.covid_fake_news_used_indices.add(self.covid_fake_news_index)
                # Move to next index
                self.covid_fake_news_index += 1
                
                fake_narrative = entry.get('Fake Narrative')
                real_news = entry.get('Real News')
                logging.debug(f"📰 Using COVID-19 fake news index {self.covid_fake_news_index - 1} (used: {len(self.covid_fake_news_used_indices)}/{len(self.covid_fake_news)})")
                return fake_narrative, real_news
            
            # If current index is used, move to next
            self.covid_fake_news_index += 1
            iterations += 1
        
        # If no unused entry found (should not happen because we reset above)
        logging.warning("⚠️ Unable to find unused COVID-19 fake news, returning None")
        return None, None

    def _add_engagement_to_post(self, post_id: str, likes: int = None, comments: int = None, shares: int = None):
        """Add engagement counts to a post"""
        try:
            cursor = self.conn.cursor()
            
            # Randomly generate 10-20 engagement counts
            if likes is None:
                likes = random.randint(10, 20)
            if comments is None:
                comments = random.randint(0, 5)  # Fewer comment counts
            if shares is None:
                shares = random.randint(0, 5)   # Fewer share counts
            
            # Update database
            cursor.execute('''
                UPDATE posts 
                SET num_likes = COALESCE(num_likes, 0) + ?,
                    num_comments = COALESCE(num_comments, 0) + ?,
                    num_shares = COALESCE(num_shares, 0) + ?
                WHERE post_id = ?
            ''', (likes, comments, shares, post_id))
            
            self.conn.commit()
            logging.info(f"📊 Added engagement to fake news post {post_id}: likes+{likes}, comments+{comments}, shares+{shares}")
            
        except Exception as e:
            logging.error(f"Failed to add engagement: {e}")

    def _initialize_news_buckets(self):
        """Split news by extremism level and reset indices."""
        if not self.ordered_news:
            self.normal_news = []
            self.extreme_news = []
            print("⚠️ No available news; cannot initialize 9:1 buckets")
            return

        self.normal_news = [article for article in self.ordered_news if article.get('extremism_trigger', 1) <= 2]
        self.extreme_news = [article for article in self.ordered_news if article.get('extremism_trigger', 1) > 2]
        self.normal_index = 0
        self.extreme_index = 0
        self.news_mix_index = 0

        print(f"📘 Normal news: {len(self.normal_news)} items | 🔥 Extreme news: {len(self.extreme_news)} items")

    def _next_article_from_bucket(self, bucket_type: str):
        """Fetch the next news item from a bucket in order."""
        bucket = self.normal_news if bucket_type == 'normal' else self.extreme_news
        index_attr = 'normal_index' if bucket_type == 'normal' else 'extreme_index'

        if not bucket:
            return None

        idx = getattr(self, index_attr)
        if idx >= len(bucket):
            idx = 0
            setattr(self, index_attr, 0)
            logging.info(f"{bucket_type} news exhausted, restarting from the beginning")

        article = bucket[idx]
        setattr(self, index_attr, idx + 1)
        return article

    def _pick_article_with_ratio(self):
        """Select news based on 9:1 pattern; fall back if bucket is empty."""
        desired_type = self.news_mix_pattern[self.news_mix_index]
        self.news_mix_index = (self.news_mix_index + 1) % len(self.news_mix_pattern)

        article = self._next_article_from_bucket(desired_type)
        if article:
            return article, desired_type

        fallback_type = 'normal' if desired_type == 'extreme' else 'extreme'
        article = self._next_article_from_bucket(fallback_type)
        if article:
            logging.warning(f"🪙 {desired_type} bucket empty, using {fallback_type} news as fallback")
            return article, fallback_type

        return None, None

    async def inject_news(self, time_step: int = None):
        """Inject multiple news articles through the specialized news agent."""
        num_articles = self.config['news_injection'].get('articles_per_injection', 1)
        max_total_posts = self.config.get('max_total_posts', 10)
        post_ids = []
        negative_news_posts = []  # Track negative news posts

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts WHERE original_post_id IS NULL")
        current_post_count = cursor.fetchone()[0]
        remaining_posts = max_total_posts - current_post_count

        if remaining_posts <= 0:
            logging.info(f"Reached max post limit ({max_total_posts}); skipping news injection")
            return post_ids

        actual_articles = min(num_articles, remaining_posts)
        if actual_articles < num_articles:
            logging.info(f"Due to post limit, news injection count adjusted from {num_articles} to {actual_articles}")

        if not (self.normal_news or self.extreme_news):
            logging.warning("❌ No available news, skipping injection")
            return post_ids

        special_sequence = None
        if self._first_injection_pending:
            desired_count = min(10, remaining_posts)
            if desired_count == 0:
                logging.info("First injection skipped due to post limit")
                return post_ids
            if desired_count < 5:
                logging.info(f"First injection limited, only pushing {desired_count}/10 items")
            actual_articles = desired_count
            special_sequence = self._first_injection_pattern[:actual_articles]

        for _ in range(actual_articles):
            requested_bucket = None
            selected_article = None

            if special_sequence:
                requested_bucket = special_sequence.pop(0)
                selected_article = self._next_article_from_bucket(requested_bucket)
                actual_bucket = requested_bucket
                if not selected_article:
                    fallback_bucket = 'normal' if requested_bucket == 'extreme' else 'extreme'
                    selected_article = self._next_article_from_bucket(fallback_bucket)
                    actual_bucket = fallback_bucket if selected_article else None
            else:
                selected_article, actual_bucket = self._pick_article_with_ratio()

            if not selected_article:
                logging.warning("❌ No news to dispatch, ending this injection early")
                break

            extremism_level = selected_article.get('extremism_trigger', 1)
            news_type = 'real' if extremism_level <= 2 else 'opinion'
            
            # Determine if fake news
            is_fake_news = extremism_level > 2
            summary = None
            
            # If fake news, use COVID-19 fake news data
            if is_fake_news and self.covid_fake_news:
                fake_narrative, real_news = self._get_next_covid_fake_narrative()
                if fake_narrative:
                    content = f"[NEWS] {fake_narrative}"
                    summary = fake_narrative
                    # Real news uses original content
                else:
                    # If no COVID data, use original content
                    content = f"[NEWS] {selected_article['title']}: {selected_article['content']}"
                    real_news = None
            else:
                # Real news uses original content
                content = f"[NEWS] {selected_article['title']}: {selected_article['content']}"
                real_news = None

            db_news_type = 'fake' if news_type == 'opinion' else news_type
            if summary is None:
                summary = selected_article.get('summary')
            if not summary:
                if self.use_precomputed_summary_only:
                    summary = " ".join(content.split()[:30])
                else:
                    summary = await self._generate_summary(content)

            post_id = await self.news_agent.create_post(
                content,
                summary=summary,
                is_news=True,
                news_type=db_news_type,
                status='active',
                time_step=time_step
            )

            try:
                label = 'FAKE' if is_fake_news else 'REAL'
                logging.info(f"📰 News Content ({label}; level {extremism_level}): {post_id} | {content}")
            except Exception:
                pass

            # If fake news, save mapping and add engagement
            if is_fake_news and real_news:
                # Save to mapping (dedupe: check if same Real News already exists)
                mapping = self._load_truth_mapping()
                
                # Check if same Real News mapping exists
                existing_post_id = None
                for pid, rn in mapping.items():
                    if rn == real_news:
                        existing_post_id = pid
                        break
                
                if existing_post_id:
                    logging.info(f"📝 Real News mapping already exists ({existing_post_id}), skipping new mapping to avoid duplicates")
                    # No longer add engagement - do not add likes at fake news start
                    # self._add_engagement_to_post(post_id)
                else:
                    # Only save new mapping when no duplicate Real News exists
                    mapping[post_id] = real_news
                    self._save_truth_mapping(mapping)
                    logging.info(f"📝 Saved fake news mapping: {post_id} -> Real News")
                    
                    # No longer add engagement - do not add likes at fake news start
                    # self._add_engagement_to_post(post_id)

            # If fake news, record post_id and related info
            if is_fake_news:
                negative_news_posts.append({
                    'post_id': post_id,
                    'extremism_level': extremism_level,
                    'news_type': db_news_type,
                    'bucket': actual_bucket or requested_bucket or "mixed"
                })
            
            self.current_news_index += 1
            post_ids.append(post_id)

            total_pool = len(self.normal_news) + len(self.extreme_news)
            total_pool_display = total_pool if total_pool else '?'
            bucket_label = actual_bucket or requested_bucket or "mixed"
            news_source = "COVID-19 Fake" if (is_fake_news and self.covid_fake_news) else "Original"
            print(f"📰 Published news #{self.current_news_index} (target {bucket_label}, controversy {extremism_level}, source: {news_source}) | pool size {total_pool_display}")

        if self._first_injection_pending:
            self._first_injection_pending = False

        self.conn.commit()
        logging.info(f"Successfully injected {len(post_ids)} news articles, expected total posts: {current_post_count + len(post_ids)}")

        # Return normal post ID list and negative news info list
        return post_ids, negative_news_posts

    async def _generate_summary(self, content: str, max_words: int = 30) -> str:
        """Generate a concise summary for news content using LLM."""
        try:
            prompt = f"""Summarize the following news update in at most {max_words} English words. Use a single plain sentence without markdown or bullet points.

News content:
{content}"""

            response = await asyncio.to_thread(
                self._summary_client.chat.completions.create,
                model=self._summary_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes concise English summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=120
            )

            summary = response.choices[0].message.content.strip()
            words = summary.split()
            if len(words) > max_words:
                summary = " ".join(words[:max_words])
            return summary
        except Exception as e:
            logging.warning(f"News summary generation failed, falling back to truncation: {e}")
            return " ".join(content.split()[:max_words])

    def get_news_stats(self, news_post_id: str) -> dict:
        """Get statistics for a specific news post."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                p.num_likes, 
                p.num_shares, 
                p.num_comments, 
                p.num_flags,
                COUNT(cn.note_id) as total_notes,
                SUM(cn.helpful_ratings) as total_helpful_ratings
            FROM posts p
            LEFT JOIN community_notes cn ON p.post_id = cn.post_id
            WHERE p.post_id = ?
            GROUP BY p.post_id
        ''', (news_post_id,))
        
        stats = cursor.fetchone()
        
        if stats:
            return {
                'likes': stats[0],
                'shares': stats[1],
                'comments': stats[2],
                'flags': stats[3],
                'notes': stats[4] or 0,
                'helpful_ratings': stats[5] or 0
            }
        return None

    def get_real_news_for_post(self, post_id: str) -> str:
        """Get real news for a post"""
        mapping = self._load_truth_mapping()
        return mapping.get(post_id, None)
