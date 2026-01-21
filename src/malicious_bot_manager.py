"""
Malicious bot manager – exercises the opinion balance system by launching counterattacks.
Triggers simulated malicious bot attacks automatically after regular users post to help evaluate defenses.
⚠️ For testing and research purposes only.
"""

import asyncio
import logging
import sqlite3
import random
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

# Simplified import path for the malicious agent modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simple_malicious_agent import SimpleMaliciousCluster, MaliciousPersona

class MaliciousBotManager:
    """Manages scheduled malicious bot activity and supporting utilities."""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        self.config = config.get("malicious_bot_system", {})
        self.enabled = self.config.get("enabled", False)
        self.db_manager = db_manager
        self.conn = db_manager.conn

        # Malicious bot configuration - use cluster size from the config
        self.cluster_size = self.config.get("cluster_size")  # Number of personas to use per attack
        # self.attack_probability = self.config.get("attack_probability", 0.8)  # Probability control removed; attacks fire immediately
        self.target_post_types = self.config.get("target_post_types", ["user_post"])
        self.attack_delay_range = self.config.get("attack_delay_range", [1, 5])  # Delay range in minutes (1-5)
        self.initial_attack_threshold = self.config.get("initial_attack_threshold", 15)  # Initial attack threshold
        self.subsequent_attack_interval = self.config.get("subsequent_attack_interval", 30)  # Interval between subsequent attacks
        self.malicious_prefix = ""  # Remove obvious prefix to make malicious comments less obvious
       
        # Initialize the malicious bot cluster using the dynamic persona extraction version
        if self.enabled:
            self.bot_cluster = SimpleMaliciousCluster(self.cluster_size)
            self._create_database_tables()
            logging.info(f"🔥 Malicious bot system enabled – selecting {self.cluster_size} personas per attack")
            print(f"Malicious bot cluster initialized. Cluster size: {self.cluster_size}")
            # Threshold-based prints removed to avoid confusion; thresholds are not used in batch mode
        else:
            self.bot_cluster = None
            logging.info("Malicious bot system disabled")
    
    def _create_database_tables(self):
        """Create and validate tables that support the malicious bot workflows."""
        # Notes for the within-batch amplification logic (kept for reference):
        # 1) Randomly select up to 5 target comments (or all if fewer exist)
        # 2) Have other authors from the same batch like the targets (up to 10 likes, guaranteed)
        # 3) Commit the batch and proceed with the rest of the workflow
        try:
            cursor = self.conn.cursor()
            # Initialize DB tables for malicious attacks/comments

            # Malicious attack record table – ensure schema completeness
            cursor.execute('DROP TABLE IF EXISTS malicious_attacks')
            cursor.execute('''
            CREATE TABLE malicious_attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_post_id TEXT,
                target_user_id TEXT,
                attack_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cluster_size INTEGER,
                successful_attacks INTEGER,
                attack_details TEXT,
                triggered_intervention BOOLEAN DEFAULT FALSE,
                attack_round INTEGER DEFAULT 1,
                engagement_at_attack INTEGER DEFAULT 0
            )
            ''')

            # Malicious comments table – ensure schema completeness
            cursor.execute('DROP TABLE IF EXISTS malicious_comments')
            cursor.execute('''
            CREATE TABLE malicious_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attack_id INTEGER,
                comment_id TEXT,
                content TEXT,
                persona_used TEXT,
                attack_type TEXT,
                intensity_level TEXT,
                selected_model TEXT DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attack_id) REFERENCES malicious_attacks (id)
            )
            ''')

            self.conn.commit()
            logging.debug("Malicious bot database tables created successfully")

        except sqlite3.OperationalError as e:
            logging.error(f"Database error in _create_database_tables: {e}")
            # If this is a database connection issue, skip table creation
            if "unable to open database file" in str(e):
                logging.warning("Skipping malicious bot database table creation due to connection issue")
                # Do not attempt additional fixes; the time-step logic will handle likes later
            else:
                raise e

    def _manual_export_comment(self, comment_id: str, content: str, author_id: str, post_id: str, selected_model: str = 'unknown', persona_used: str = 'Unknown'):
        """Export a single malicious comment to the archive for analysis."""
        try:
            import os
            from datetime import datetime
            import json

            # Ensure the export directory exists
            os.makedirs("exported_content/data", exist_ok=True)

            # Format the comment data
            formatted_comment = {
                'comment_id': comment_id,
                'user_query': content,
                'author_id': author_id,
                'created_at': datetime.now().isoformat(),
                'post_id': post_id,
                'num_likes': 0,
                'selected_model': selected_model,
                'agent_type': 'malicious_agent',
                'persona_used': persona_used,
                'exported_at': datetime.now().isoformat()
            }

            # Append to the malicious agent export file
            malicious_file = "exported_content/data/malicious_agents_content.jsonl"
            with open(malicious_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(formatted_comment, ensure_ascii=False) + '\n')



        except Exception as e:
            pass  # Silently ignore storage errors

    async def create_malicious_post(self, news_content: str, time_step: int) -> Optional[Dict[str, Any]]:
        """
        (Disabled) Previous mechanism to generate a malicious post from a news item.
        Retained for interface compatibility but no longer produces content; always returns None.
        """
        logging.info("create_malicious_post was called but malicious posting is disabled. No post will be created.")
        return None

    async def _generate_malicious_post_content(self, news_content: str, persona: Optional[MaliciousPersona]) -> str:
        """Generate a malicious response draft using persona context."""
        try:
            # Use the bot cluster's LLM capabilities
            import asyncio
            persona_details = []
            if persona and persona.name:
                persona_details.append(f"Name: {persona.name}")
            if persona and persona.malicious_type:
                persona_details.append(f"Type: {persona.malicious_type}")
            if persona and persona.age_range:
                persona_details.append(f"Age: {persona.age_range}")
            if persona and persona.profession:
                persona_details.append(f"Profession: {persona.profession}")
            if persona and persona.region:
                persona_details.append(f"Region: {persona.region}")
            if persona and persona.personality_traits:
                persona_details.append(f"Traits: {', '.join(persona.personality_traits)}")
            if persona and persona.background:
                persona_details.append(f"Background: {persona.background}")

            communication_style = persona.communication_style if persona else {}
            tone = communication_style.get('tone') if isinstance(communication_style, dict) else None
            engagement = communication_style.get('engagement_level') if isinstance(communication_style, dict) else None
            content_pref = communication_style.get('content_preference') if isinstance(communication_style, dict) else None
            argument_approach = communication_style.get('argument_approach') if isinstance(communication_style, dict) else None

            if tone:
                persona_details.append(f"Tone: {tone}")
            if engagement:
                persona_details.append(f"Engagement: {engagement}")
            if content_pref:
                persona_details.append(f"Content Preference: {content_pref}")
            if argument_approach:
                persona_details.append(f"Argument Approach: {argument_approach}")

            persona_section = "\n".join(f"- {item}" for item in persona_details) if persona_details else "- Anonymous agitator"

            # Construct the prompt for generating the malicious post
            prompt = f"""Persona Context:
{persona_section}

Target News: "{news_content[:200]}"

MISSION:
- Exploit fears around this topic to inflame outrage and distrust
- Twist details into conspiracy-flavored narratives that feel urgent and undeniable
- Rally like-minded readers by sounding like a grassroots insider exposing hidden truth

CONTENT GUIDELINES:
- Start with a charged hook that signals outrage or betrayal
- Accuse mainstream sources of lies, cover-ups, or manipulative agendas
- Use CAPS or punctuation for emphasis; swear naturally when it heightens impact
- Blend confident misinformation with emotional storytelling and broad accusations
- Encourage readers to doubt, retaliate, or “wake up” others

OUTPUT REQUIREMENTS:
- Keep it under 45 words so it reads like a punchy social media screed
- End with a rallying or accusatory punchline to spark further spreading
- Prioritize emotional manipulation over factual accuracy—certainty matters more than truth

Write your hostile post:"""

            # Use SimpleMaliciousCluster's model selector
            client, model_name = self.bot_cluster.model_selector.create_langchain_client()

            # Execute the LLM call in a thread pool
            def sync_llm_call():
                try:
                    response = client.invoke(prompt)
                    content = response.content.strip() if response and hasattr(response, 'content') else ""
                    # Limit to a moderate length
                    words = content.split()[:40]
                    return ' '.join(words)
                except Exception as e:
                    logging.warning(f"LLM failed to generate a malicious post: {e}")
                    return None

            # Invoke asynchronously
            content = await asyncio.to_thread(sync_llm_call)

            if content and len(content.strip()) > 10:
                logging.info(f"🤖 LLM generated malicious post: {content[:80]}...")
                return content
            else:
                # Fallback to English templates
                logging.warning("⚠️ LLM generation failed, falling back to the English template")
                return self._get_fallback_malicious_post(news_content)

        except Exception as e:
            logging.error(f"Failed to generate malicious post content: {e}")
            return self._get_fallback_malicious_post(news_content)

    def _get_fallback_malicious_post(self, news_content: str) -> str:
        """Return a canned malicious post when generation fails."""
        controversial_starters = [
            "This news is completely misleading!",
            "The media is manipulating public opinion again...",
            "The truth is being covered up, wake up people!",
            "There's definitely a hidden agenda behind this",
            "Mainstream media never reports the real truth",
            "This kind of reporting is brainwashing the masses",
            "Don't be fooled by this fake news",
            "This is obviously an organized propaganda campaign",
            "These idiotic journalists don't understand the real truth!",
            "Anyone supporting this garbage news is brain-dead!",
            "This stupid reporting is an insult to intelligence!"
        ]

        controversial_endings = [
            "Everyone needs to think independently!",
            "Don't believe blindly!",
            "The truth will surface eventually",
            "Open your eyes and see reality",
            "This is the true face of media today",
            "Hope more people can see this issue",
            "We can't be fooled anymore",
            "It's time to question everything",
            "Only fools would believe this garbage!",
            "These idiots will never understand the truth!",
            "People who support this are brainless trash!"
        ]

        starter = random.choice(controversial_starters)
        ending = random.choice(controversial_endings)

        return f"{starter} {ending}"

    async def monitor_post(self, post_id: str, content: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Cross-like among malicious users within the current attack batch."""
        if not self.enabled or not self.bot_cluster:
            return {"success": False, "reason": "malicious_bot_system_disabled"}

        try:
            # Determine whether this post should be targeted
            should_attack = self._should_attack_post(post_id, content, user_id)

            if not should_attack:
                return {"success": False, "reason": "conditions_not_met", "post_id": post_id}

            logging.info(f"Malicious bot preparing to attack post: {post_id}")

            # Execute the attack immediately without delay
            attack_result = await self._execute_attack(post_id, content, user_id)

            return attack_result

        except Exception as e:
            logging.error(f"Malicious bot monitor failed: {e}")
            return {"success": False, "reason": "exception", "error": str(e), "post_id": post_id}
    
    def _should_attack_post(self, post_id: str, content: str, user_id: str) -> bool:
        """Determine whether a post should be targeted."""

        cursor = self.conn.cursor()

        # 1. Check if the post is published by malicious bot itself (by checking if user has published malicious comments)
        cursor.execute('''
            SELECT COUNT(*) FROM malicious_comments mc
            JOIN comments c ON mc.comment_id = c.comment_id
            WHERE c.author_id = ?
        ''', (user_id,))

        if cursor.fetchone()[0] > 0:
            # This user has published malicious comments before, is a malicious bot, don't attack their posts
            return False

        # 2. Check content length (don't attack posts that are too short)
        if len(content.strip()) < 20:
            return False

        # 3. Get current post engagement
        cursor.execute('''
            SELECT num_comments, num_likes, num_shares
            FROM posts
            WHERE post_id = ?
        ''', (post_id,))

        post_data = cursor.fetchone()
        if not post_data:
            return False  # Post doesn't exist

        num_comments, num_likes, num_shares = post_data
        current_engagement = (num_comments or 0) + (num_likes or 0) + (num_shares or 0)

        # 4. Get historical attack records for this post
        cursor.execute('''
            SELECT attack_round, engagement_at_attack
            FROM malicious_attacks
            WHERE target_post_id = ?
            ORDER BY attack_round DESC
            LIMIT 1
        ''', (post_id,))

        last_attack = cursor.fetchone()

        if last_attack is None:
            # First attack: check if initial attack threshold is reached
            if current_engagement >= self.initial_attack_threshold:
                return self._reserve_attack_slot(post_id, user_id, 1, current_engagement)
            else:
                if current_engagement > 0:  # Only print when there's some engagement to avoid spam
                    pass
                return False
        else:
            # Subsequent attack: check if incremental threshold is reached
            last_round, last_engagement = last_attack
            next_round = last_round + 1
            required_engagement = last_engagement + self.subsequent_attack_interval

            # Debug information
            pass

            if current_engagement >= required_engagement:
                pass
                return self._reserve_attack_slot(post_id, user_id, next_round, current_engagement)
            else:
                if current_engagement >= last_engagement:  # Engagement has increased or remained the same
                    pass
                else:
                    pass
                return False

    def _reserve_attack_slot(self, post_id: str, user_id: str, attack_round: int, current_engagement: int) -> bool:
        """Cross-like among malicious users within the current attack batch."""
        cursor = self.conn.cursor()

        try:
            cursor.execute('BEGIN IMMEDIATE TRANSACTION')

            # Check whether an attack for this round already exists
            cursor.execute('''
                SELECT COUNT(*) FROM malicious_attacks
                WHERE target_post_id = ? AND attack_round = ?
            ''', (post_id, attack_round))

            if cursor.fetchone()[0] > 0:
                cursor.execute('ROLLBACK')
                return False  # This round has already been attacked

            # Insert a placeholder record immediately to prevent concurrent attacks
            cursor.execute('''
                INSERT INTO malicious_attacks (
                    target_post_id, target_user_id, cluster_size,
                    successful_attacks, attack_details, attack_round, engagement_at_attack
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (post_id, user_id, 0, 0, '{"status": "reserved"}', attack_round, current_engagement))

            cursor.execute('COMMIT')
            return True

        except Exception as e:
            cursor.execute('ROLLBACK')
            logging.error(f"Error occurred while reserving attack slot: {e}")
            return False
    
    async def _execute_attack(self, post_id: str, content: str, user_id: str, override_cluster_size: int = None) -> Dict[str, Any]:
        """Cross-like among malicious users within the current attack batch."""
        try:

            # Coordinate cluster size: prioritize override size, fallback to configured cluster_size
            used_cluster_size = override_cluster_size if override_cluster_size is not None else self.cluster_size

            # Coordinate cluster attack - use the selected attack size
            attack_results = await self.bot_cluster.coordinate_attack(post_id, content, used_cluster_size)

            # Record the attack
            attack_id = self._record_attack(post_id, user_id, attack_results, used_cluster_size)

            # Generate malicious comments
            comment_ids = self._create_malicious_comments(post_id, attack_results, attack_id)

            return {
                "success": True,
                "attack_id": attack_id,
                "target_post_id": post_id,
                "successful_attacks": len(attack_results),
                "comment_ids": comment_ids,
                "attack_details": attack_results
            }

        except Exception as e:
            logging.error(f"Execute malicious attack failed: {e}")
            return {"success": False, "error": str(e)}
    def _record_attack(self, post_id: str, user_id: str, attack_results: List[Dict[str, Any]], used_cluster_size: int) -> int:
        """Cross-like among malicious users within the current attack batch."""
        cursor = self.conn.cursor()

        # Update the placeholder record inserted earlier in _reserve_attack_slot
        # Find the latest placeholder record (cluster_size = 0 indicates placeholder record)
        cursor.execute('''
            UPDATE malicious_attacks SET
                cluster_size = ?,
                successful_attacks = ?,
                attack_details = ?,
                attack_timestamp = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM malicious_attacks
                WHERE target_post_id = ? AND cluster_size = 0
                ORDER BY id DESC
                LIMIT 1
            )
        ''', (
            used_cluster_size,
            len(attack_results),
            str(attack_results),  # JSON string storage
            post_id
        ))

        # Get the updated record ID
        cursor.execute('''
            SELECT id, attack_round, engagement_at_attack FROM malicious_attacks
            WHERE target_post_id = ?
            ORDER BY attack_timestamp DESC
            LIMIT 1
        ''', (post_id,))

        result = cursor.fetchone()
        if result:
            attack_id, attack_round, engagement = result
        else:
            attack_id = None

        self.conn.commit()

        if not attack_id:
            # If no record found, fallback to inserting new record (backward compatibility)
            cursor.execute('''
                INSERT INTO malicious_attacks (
                    target_post_id, target_user_id, cluster_size,
                    successful_attacks, attack_details, attack_round, engagement_at_attack
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_id,
                user_id,
                used_cluster_size,
                len(attack_results),
                str(attack_results),
                1,  # Default round 1
                0   # Default engagement
            ))
            attack_id = cursor.lastrowid
            self.conn.commit()

        return attack_id
    
    def _create_malicious_comments(self, post_id: str, attack_results: List[Dict[str, Any]], attack_id: int) -> List[str]:
        """Cross-like among malicious users within the current attack batch."""
        cursor = self.conn.cursor()
        comment_ids = []
        batch_comments = []
        batch_malicious_records = []

        for i, attack in enumerate(attack_results):
            # Fix: check if attack result is valid (has content means successful)
            content = attack.get("content", "")

            # Strict validation: content must not be empty and length after trimming must be greater than 0
            if not content or not content.strip():
                logging.warning(f"⚠️  Skipping invalid attack result {i}: content is empty")
                continue

            # Use cleaned content (trimmed)
            content = content.strip()
            persona_info = attack.get("persona_info", {})
            persona_used = persona_info.get("name", "unknown")

            # Generate comment ID and user ID
            from utils import Utils
            comment_id = Utils.generate_formatted_id("comment", self.conn)

            # Generate seemingly random userID based on persona and time
            seed = f"{persona_used}_{i}_{datetime.now().strftime('%Y%m%d')}"
            hash_obj = hashlib.md5(seed.encode())
            user_suffix = hash_obj.hexdigest()[:6]
            malicious_user_id = f"user-{user_suffix}"

            # Batch check and create user (if not exists)
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (malicious_user_id,))
            if not cursor.fetchone():
                fake_persona = {
                    "name": f"User{user_suffix}",
                    "type": "negative",
                    "profession": "Various",
                    "age_range": "25-45",
                    "personality_traits": ["Critical", "Skeptical"],
                    "interests": ["Politics", "Current Events"]
                }

                cursor.execute('''
                    INSERT INTO users (user_id, persona, creation_time)
                    VALUES (?, ?, ?)
                ''', (
                    malicious_user_id,
                    json.dumps(fake_persona),
                    datetime.now().isoformat()
                ))

            # Prepare batch insertion data
            selected_model = attack.get("model_used", "unknown")

            # Comment data
            comment_data = (
                comment_id,
                content,
                post_id,
                malicious_user_id,
                datetime.now().isoformat(),
                0,  # Remove fake likes, start from 0, rely only on real mutual likes among malicious bots
                selected_model,
                'malicious'
            )
            batch_comments.append(comment_data)

            # Malicious comment record data
            malicious_record = (
                attack_id,
                comment_id,
                content,
                persona_used,
                attack.get("attack_type", "unknown"),
                attack.get("intensity", "medium"),
                selected_model
            )
            batch_malicious_records.append(malicious_record)

            comment_ids.append(comment_id)

            # Debug: check content integrity
            char_count = len(content)

            if char_count < 20:
                try:
                    import logging
                    logging.debug(f"Short malicious comment ({char_count} chars) generated: {comment_id}")
                except Exception:
                    pass

            # Display malicious comment (consistent with regular user format, show full content)
            try:
                # Console output format consistent with regular users, with prefix marker
                print(f"🔥 {malicious_user_id} ({selected_model}) commented on post {post_id}: {content}")
            except Exception:
                pass

        # Batch insert comments
        if batch_comments:
            try:
                cursor.executemany('''
                    INSERT INTO comments (comment_id, content, post_id, author_id, created_at, num_likes, selected_model, agent_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch_comments)
            except sqlite3.OperationalError as e:
                if "no column named" in str(e):
                    # Compatibility mode: schema lacks the newer columns
                    cursor.executemany('''
                        INSERT INTO comments (comment_id, content, post_id, author_id, created_at, num_likes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', [(c[0], c[1], c[2], c[3], c[4], c[5]) for c in batch_comments])

            # Record comment->timestep mappings if current_time_step is provided
            try:
                current_step = getattr(self, 'current_time_step', None)
                if current_step is not None and batch_comments:
                    mappings = [(c[0], c[3], c[2], int(current_step)) for c in batch_comments]
                    cursor.executemany('''
                        INSERT OR REPLACE INTO comment_timesteps (comment_id, user_id, post_id, time_step)
                        VALUES (?, ?, ?, ?)
                    ''', mappings)
            except Exception:
                pass

        # Batch insert malicious comment records
        if batch_malicious_records:
            try:
                cursor.executemany('''
                    INSERT INTO malicious_comments (
                        attack_id, comment_id, content, persona_used,
                        attack_type, intensity_level, selected_model
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', batch_malicious_records)
            except sqlite3.OperationalError as e:
                if "no column named selected_model" in str(e):
                    # Compatibility mode: selected_model column not present
                    cursor.executemany('''
                        INSERT INTO malicious_comments (
                            attack_id, comment_id, content, persona_used,
                            attack_type, intensity_level
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in batch_malicious_records])

        # Batch update post comment counts
        if comment_ids:
            cursor.execute('''
                UPDATE posts
                SET num_comments = num_comments + ?
                WHERE post_id = ?
            ''', (len(comment_ids), post_id))
            # Also increment post likes (each attacker adds one like)
            try:
                cursor.execute('''
                    UPDATE posts
                    SET num_likes = COALESCE(num_likes, 0) + ?
                    WHERE post_id = ?
                ''', (len(comment_ids), post_id))
            except Exception:
                pass

        # Commit all batched operations at once
        self.conn.commit()

        # Cross-liking mechanism within the current attack batch (only target these comments)
        if comment_ids:
            try:
                # Step 1: Run the in-batch cross-like (15 bots liking two comments)
                self._current_attack_cross_like_sync(comment_ids, batch_comments, post_id)
            except Exception as e:
                logging.warning(f"Malicious bot cross-like mechanism failed: {e}")

        # Simplified batch export (async, non-blocking)
        try:
            import asyncio
            asyncio.create_task(self._async_batch_export(comment_ids, batch_comments, batch_malicious_records))
        except Exception:
            pass  # Silently ignore export errors

        return comment_ids

    async def _async_batch_export(self, comment_ids: List[str], batch_comments: List, batch_malicious_records: List):
        """Asynchronously export the batch comments and malicious records."""
        try:
            import os
            import json
            from datetime import datetime

            # Ensure the export directory exists
            os.makedirs("exported_content/data", exist_ok=True)

            # Batch format the comment data
            malicious_file = "exported_content/data/malicious_agents_content.jsonl"
            with open(malicious_file, 'a', encoding='utf-8') as f:
                for i, comment_data in enumerate(batch_comments):
                    if i < len(batch_malicious_records):
                        malicious_record = batch_malicious_records[i]
                        formatted_comment = {
                            'comment_id': comment_data[0],
                            'user_query': comment_data[1],
                            'author_id': comment_data[3],
                            'created_at': comment_data[4],
                            'post_id': comment_data[2],
                            'num_likes': comment_data[5],
                            'selected_model': comment_data[6] if len(comment_data) > 6 else 'unknown',
                            'agent_type': 'malicious_agent',
                            'persona_used': malicious_record[3],
                            'exported_at': datetime.now().isoformat()
                        }
                        f.write(json.dumps(formatted_comment, ensure_ascii=False) + '\n')

        except Exception as e:
            # Silently ignore export errors without impacting the main flow
            pass

    def _current_attack_cross_like_sync(self, comment_ids: List[str], batch_comments: List, post_id: str):
        """Synchronous version of the in-batch cross-like (15 agents like two malicious comments)."""
        try:
            if len(comment_ids) < 2:
                return  # need at least 2 comments to cross-like

            cursor = self.conn.cursor()
            import random

            # Select two target comments
            target_count = min(2, len(comment_ids))
            target_indices = random.sample(range(len(comment_ids)), target_count)
            selected_targets = [comment_ids[idx] for idx in target_indices]

            # Gather all malicious user IDs (up to 15)
            all_agent_ids = [batch_comments[i][3] for i in range(len(batch_comments))]  # c[3]=author_id
            max_likers = min(15, len(all_agent_ids))

            successful_likes = 0
            for target_comment_id in selected_targets:
                # Select up to 15 distinct likers for each target comment
                likers = random.sample(all_agent_ids, min(max_likers, len(all_agent_ids)))
                
                for liker_user_id in likers:
                    try:
                        # Check if this liker has already liked the comment
                        cursor.execute('''
                            SELECT COUNT(*) FROM user_actions
                            WHERE user_id = ? AND action_type = 'like_comment' AND target_id = ?
                        ''', (liker_user_id, target_comment_id))

                        if cursor.fetchone()[0] == 0:  # Not liked yet
                            # Increment the comment's like count
                            cursor.execute('''
                                UPDATE comments
                                SET num_likes = num_likes + 1
                                WHERE comment_id = ?
                            ''', (target_comment_id,))

                            # Record the like action
                            cursor.execute('''
                                INSERT INTO user_actions (user_id, action_type, target_id)
                                VALUES (?, 'like_comment', ?)
                            ''', (liker_user_id, target_comment_id))

                            successful_likes += 1
                    except sqlite3.Error:
                        continue  # Skip failed like attempts

            self.conn.commit()

            # Log the results of the cross-like
            if successful_likes > 0:
                logging.info(
                    f"👍 Cross-like completed: {successful_likes} likes across {len(selected_targets)} malicious comments"
                )

            # The platform-level extra-like mechanism for malicious comments has been removed

        except Exception as e:
            logging.warning(f"Cross-like operation failed: {e}")

    async def _current_attack_cross_like(self, comment_ids: List[str], batch_comments: List):
        """Cross-like among malicious users within the current attack batch."""
        try:
            await asyncio.sleep(0.3)  # allow comments to persist before liking

            if len(comment_ids) < 2:
                return  # need at least 2 comments to perform cross-likes

            cursor = self.conn.cursor()

            like_actions = []
            # Select a couple of target comments randomly (or all if only two)
            target_count = min(2, len(comment_ids))
            target_indices = random.sample(range(len(comment_ids)), target_count)

            for target_index in target_indices:
                target_comment_id = comment_ids[target_index]

                # Other agents from the same batch act as likers
                other_agents = [batch_comments[i][3] for i in range(len(batch_comments)) if i != target_index]
                if not other_agents:
                    continue

                # Choose one different attacker per target to provide a like
                selected_agents = random.sample(other_agents, 1)
                for other_author in selected_agents:
                    like_actions.append((target_comment_id, other_author))

            # Execute the queued like actions
            try:
                selected_targets = [comment_ids[idx] for idx in target_indices if 0 <= idx < len(comment_ids)]
                counts = {}
                for cid, _ in like_actions:
                    counts[cid] = counts.get(cid, 0) + 1
                # Do not top up like operations with synthetic accounts
            except Exception:
                pass

            if like_actions:
                successful_likes = 0
                for comment_id, liker_user_id in like_actions:
                    try:
                        # Ensure the liker exists in the user table
                        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (liker_user_id,))
                        if cursor.fetchone()[0] == 0:
                            fake_persona = {
                                "name": f"MaliciousUser{liker_user_id[-6:]}",
                                "type": "malicious",
                                "profession": "Various",
                                "age_range": "25-45",
                                "personality_traits": ["Manipulative", "Coordinated", "Deceptive"],
                                "agent_role": "malicious",
                                "is_system_agent": True
                            }
                            cursor.execute('''
                                INSERT OR IGNORE INTO users (user_id, persona, creation_time)
                                VALUES (?, ?, datetime('now'))
                            ''', (liker_user_id, json.dumps(fake_persona, ensure_ascii=False)))

                        cursor.execute('''
                            SELECT COUNT(*) FROM user_actions
                            WHERE user_id = ? AND action_type = 'like_comment' AND target_id = ?
                        ''', (liker_user_id, comment_id))

                        if cursor.fetchone()[0] == 0:
                            cursor.execute('''
                                UPDATE comments
                                SET num_likes = num_likes + 1
                                WHERE comment_id = ?
                            ''', (comment_id,))

                            cursor.execute('''
                                INSERT INTO user_actions (user_id, action_type, target_id)
                                VALUES (?, 'like_comment', ?)
                            ''', (liker_user_id, comment_id))

                            successful_likes += 1
                    except sqlite3.Error:
                        continue  # Skip failed like attempts

                self.conn.commit()

                if successful_likes > 0:
                    self._verify_likes_increased(comment_ids)
                    try:
                        logging.info(
                            f"👍 Cross-like completed: {successful_likes} likes distributed across {len(selected_targets)} malicious comments"
                        )
                    except Exception:
                        pass

                # Platform-level extra-like and dynamic leader comment increments are disabled

        except Exception:
            # Silently ignore errors so we do not disturb the main simulation
            pass

    def _verify_likes_increased(self, comment_ids: List[str]):
        """Verify and print like counts for each comment in the batch."""
        try:
            cursor = self.conn.cursor()
            total_likes = 0
            print("   Likes summary:")
            for i, comment_id in enumerate(comment_ids, 1):
                cursor.execute('SELECT num_likes FROM comments WHERE comment_id = ?', (comment_id,))
                result = cursor.fetchone()
                if result:
                    likes = result[0]
                    total_likes += likes
                    print(f"      Comment {i}: {comment_id} -> {likes} likes")
                else:
                    print(f"      Comment {i}: {comment_id} -> not found")
            print(f"   Total: {len(comment_ids)} comments, {total_likes} likes")
        except Exception as e:
            print(f"   Like verification failed: {e}")
    def get_attack_statistics(self) -> Dict[str, Any]:
        """Collect basic statistics about past malicious bot activity."""
        if not self.enabled:
            return {"enabled": False}

        cursor = self.conn.cursor()
        
        # Total attack count
        cursor.execute('SELECT COUNT(*) FROM malicious_attacks')
        total_attacks = cursor.fetchone()[0]
        
        # Total successful attacks
        cursor.execute('SELECT SUM(successful_attacks) FROM malicious_attacks')
        total_successful = cursor.fetchone()[0] or 0
        
        # Total malicious comments
        cursor.execute('SELECT COUNT(*) FROM malicious_comments')
        total_comments = cursor.fetchone()[0]
        
        # Attacks that triggered interventions
        cursor.execute('SELECT COUNT(*) FROM malicious_attacks WHERE triggered_intervention = TRUE')
        triggered_interventions = cursor.fetchone()[0]
        
        # Cluster statistics
        cluster_stats = self.bot_cluster.get_attack_statistics() if self.bot_cluster else {}
        
        return {
            "enabled": True,
            "cluster_size": self.cluster_size,
            "total_attacks": total_attacks,
            "total_successful_attacks": total_successful,
            "total_malicious_comments": total_comments,
            "triggered_interventions": triggered_interventions,
            "intervention_rate": triggered_interventions / total_attacks if total_attacks > 0 else 0,
            "cluster_statistics": cluster_stats,
            # "attack_probability": self.attack_probability,  # Probability control has been removed
        }
    
    def mark_intervention_triggered(self, post_id: str):
        """Record that an intervention was triggered for a specific post."""
        if not self.enabled:
            return
        
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE malicious_attacks 
            SET triggered_intervention = TRUE 
            WHERE target_post_id = ?
        ''', (post_id,))
        self.conn.commit()

    async def attack_top_hot_posts(self, min_engagement: int = 15, top_n: int = 10) -> Dict[str, Any]:
        """
        Launch batch attacks against the top hot posts at the end of the timestep.

        Args:
            min_engagement: minimum engagement threshold (default 15)
            top_n: number of top posts to target (default 10)

        Returns:
            A summary of the attack results
        """
        if not self.enabled or not self.bot_cluster:
            return {"success": False, "reason": "malicious_bot_system_disabled"}

        try:
            # Unified result collection
            attacked_posts: List[Dict[str, Any]] = []
            skipped_posts: List[Dict[str, Any]] = []
            attack_results: List[Dict[str, Any]] = []
            max_allowed = 0

            # Current timestep (used to find fake news within the last three steps)
            current_step = getattr(self, 'current_time_step', None)

            # === Step 1: Attack fake news published within the last three time steps with 15 comments each ===
            recent_fake_ids: List[str] = []
            if current_step is not None:
                try:
                    cur0 = self.conn.cursor()
                    cur0.execute(
                        '''
                        SELECT p.post_id, p.content, p.author_id,
                               (COALESCE(p.num_comments,0)+COALESCE(p.num_likes,0)+COALESCE(p.num_shares,0)) AS engagement
                        FROM posts p
                        JOIN post_timesteps pt ON p.post_id = pt.post_id
                        WHERE p.is_news = 1 AND p.news_type = 'fake'
                          AND (? - pt.time_step) < 3
                          AND (p.status IS NULL OR p.status='active')
                        ''',
                        (int(current_step),),
                    )
                    rf_rows = cur0.fetchall()
                    for row in rf_rows:
                        try:
                            pid, content, author_id, engagement = row[0], row[1], row[2], row[3]
                        except Exception:
                            pid, content, author_id, engagement = (
                                row['post_id'],
                                row['content'],
                                row['author_id'],
                                row['engagement'],
                            )
                        if not pid:
                            continue
                        recent_fake_ids.append(pid)

                        # Each recent fake news item receives 15 hostile comments
                        res = await self._execute_attack(
                            pid,
                            content,
                            author_id,
                            override_cluster_size=15,
                        )
                        if res.get('success'):
                            attacked_posts.append(
                                {
                                    'post_id': pid,
                                    'engagement': engagement,
                                    'comments_added': len(res.get('comment_ids', [])),
                                }
                            )
                            attack_results.append(res)
                        else:
                            skipped_posts.append(
                                {
                                    'post_id': pid,
                                    'engagement': engagement,
                                    'reason': res.get('error', 'unknown'),
                                }
                            )
                except Exception:
                    # Stay resilient: if the fake news query fails, continue with other hot posts
                    pass

            # Step 2 removed: no additional hot posts are attacked
            max_allowed = len(recent_fake_ids)

            # Time-step wrap-up: do not increment leader comments dynamically on the platform

            # Remove the batch completion logging per your request

            return {
                "success": True,
                "total_targets": len(recent_fake_ids),
                "max_allowed": max_allowed,
                "attacked_count": len(attacked_posts),
                "skipped_count": len(skipped_posts),
                "attacked_posts": attacked_posts,
                "skipped_posts": skipped_posts,
                "attack_results": attack_results
            }

        except Exception as e:
            logging.error(f"Batch attack failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_top_hot_posts(self, top_n: int) -> List[Dict[str, Any]]:
        """
        Retrieve the top n posts by engagement; duplicates from previous attacks are allowed.

        Note: Already attacked posts are not excluded; each timestep the top N candidates are reassessed.

        Returns:
            A list of dictionaries describing each hot post.
        """
        cursor = self.conn.cursor()

        # Query the top N posts by engagement (re-attacks are allowed)
        # Includes both news and regular user posts; malicious bots attack any trending content
        cursor.execute('''
            SELECT
                p.post_id,
                p.content,
                p.author_id,
                (COALESCE(p.num_comments, 0) + COALESCE(p.num_likes, 0) + COALESCE(p.num_shares, 0)) as engagement
            FROM posts p
            WHERE (p.status IS NULL OR p.status = 'active')
            ORDER BY engagement DESC
            LIMIT ?
        ''', (top_n,))

        results = cursor.fetchall()

        hot_posts = []
        for row in results:
            hot_posts.append({
                'post_id': row[0],
                'content': row[1],
                'author_id': row[2],
                'engagement': row[3]
            })

        return hot_posts

    def _should_attack_post_simple(self, post_id: str, content: str, user_id: str) -> bool:
        """
        Simplified attack filter: basic checks that allow repeat attacks.
        Designed for batch mode where the top candidates are re-evaluated each timestep.
        """
        cursor = self.conn.cursor()

        # 1. Check whether the post was created by a malicious bot account
        cursor.execute('''
            SELECT COUNT(*) FROM malicious_comments mc
            JOIN comments c ON mc.comment_id = c.comment_id
            WHERE c.author_id = ?
        ''', (user_id,))

        if cursor.fetchone()[0] > 0:
            return False

        # 2. Check the content length to avoid attacking very short posts
        if len(content.strip()) < 20:
            return False

        # 3. Do not enforce anti-repeat checks; repeat attacks are allowed
        # The top posts are re-evaluated every timestep and attacked if they satisfy the conditions

        return True












