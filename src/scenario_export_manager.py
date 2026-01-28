#!/usr/bin/env python3
"""
Scenario export manager - exports content to the appropriate scenario folders based on user configuration selections
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

class ScenarioExportManager:
    """Scenario export manager"""

    def __init__(self, db_connection: sqlite3.Connection, config: Dict[str, Any]):
        self.conn = db_connection
        self.config = config
        self.export_enabled = True

        # Configuration option: whether news-related content should be exported (defaults to exporting for debugging)
        self.export_news_content = config.get('export_news_content', True)

        # Ensure the database connection uses the Row factory
        if self.conn.row_factory != sqlite3.Row:
            self.conn.row_factory = sqlite3.Row

        # Configure the five scenario folders
        self.scenario_dirs = {
            'scenario_1': 'organized_comments_from_jsonl/scenario_1',
            'scenario_2': 'organized_comments_from_jsonl/scenario_2',
            'scenario_3': 'organized_comments_from_jsonl/scenario_3',
            'scenario_4': 'organized_comments_from_jsonl/scenario_4',
            'scenario_5': 'organized_comments_from_jsonl/scenario_5'
        }

        # Ensure all scenario directories exist
        for scenario_dir in self.scenario_dirs.values():
            os.makedirs(scenario_dir, exist_ok=True)

        # Determine the current scenario from the configuration
        self.current_scenario = self._determine_scenario()
        self.current_export_dir = self.scenario_dirs[self.current_scenario]

        # Record exported content IDs to prevent duplicates
        self.exported_posts = set()
        self.exported_comments = set()
        self._load_exported_records()

        print(f"📁 Scenario export manager initialized - current scenario: {self.current_scenario}")
        print(f"   Export directory: {self.current_export_dir}")

    def _determine_scenario(self) -> str:
        """Determine the current scenario based on configuration"""
        # Get the enabled status of each system (five yes/no options)
        malicious_enabled = self.config.get('malicious_bot_system', {}).get('enabled', False)
        opinion_balance_enabled = self.config.get('opinion_balance_system', {}).get('enabled', False)
        feedback_iteration_enabled = self.config.get('feedback_iteration_system', {}).get('enabled', False)
        fact_check_enabled = self.config.get('fact_checking', {}).get('enabled', False)
        prebunking_enabled = self.config.get('prebunking_system', {}).get('enabled', False)

        # Determine the scenario based on combinations of the five features
        # 1. nnnnn - only normal users
        if (not malicious_enabled and not opinion_balance_enabled and
            not feedback_iteration_enabled and not fact_check_enabled and not prebunking_enabled):
            return 'scenario_1'

        # 2. ynnnn - normal users and malicious bots
        elif (malicious_enabled and not opinion_balance_enabled and
              not feedback_iteration_enabled and not fact_check_enabled and not prebunking_enabled):
            return 'scenario_2'

        # 3. ynnyy - normal users and malicious bots plus prebunking and fact-checking
        elif (malicious_enabled and not opinion_balance_enabled and
              not feedback_iteration_enabled and fact_check_enabled and prebunking_enabled):
            return 'scenario_3'

        # 4. yyynn - normal users, malicious bots, and opinion balancing
        elif (malicious_enabled and opinion_balance_enabled and
              feedback_iteration_enabled and not fact_check_enabled and not prebunking_enabled):
            return 'scenario_4'

        # 5. yyyyy - normal users, malicious bots, opinion balancing, prebunking, and fact-checking
        elif (malicious_enabled and opinion_balance_enabled and
              feedback_iteration_enabled and fact_check_enabled and prebunking_enabled):
            return 'scenario_5'

        # Additional logic for other combinations
        else:
            # Choose the closest-fitting scenario based on the enabled features
            if not malicious_enabled:
                return 'scenario_1'  # No malicious bots, treat as normal user scenario
            elif malicious_enabled and opinion_balance_enabled:
                if fact_check_enabled or prebunking_enabled:
                    return 'scenario_5'  # Malicious bots plus opinion balancing and fact-check/prebunking
                else:
                    return 'scenario_4'  # Malicious bots with opinion balancing
            elif malicious_enabled and (fact_check_enabled or prebunking_enabled):
                return 'scenario_3'  # Malicious bots with fact-check/prebunking
            else:
                return 'scenario_2'  # Malicious bots without additional mitigation

    def _load_exported_records(self):
        """Load exported record IDs"""
        try:
            if os.path.exists(self.current_export_dir):
                for item in os.listdir(self.current_export_dir):
                    if item.startswith('post-') and os.path.isdir(os.path.join(self.current_export_dir, item)):
                        self.exported_posts.add(item)

                        # Check for comment files
                        comments_file = os.path.join(self.current_export_dir, item, 'comments.jsonl')
                        if os.path.exists(comments_file):
                            with open(comments_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    try:
                                        comment = json.loads(line.strip())
                                        self.exported_comments.add(comment.get('comment_id', ''))
                                    except json.JSONDecodeError:
                                        continue
        except Exception as e:
            print(f"⚠️  Failed to load exported records: {e}")

    def _get_agent_info(self, author_id: str) -> tuple[str, str]:
        """Get agent type and model information"""
        agent_type = "unknown"
        selected_model = "unknown"
        from multi_model_selector import MultiModelSelector
        default_model = MultiModelSelector.DEFAULT_POOL[0]

        try:
            cursor = self.conn.cursor()

            # First check the comments table for agent_type (most accurate method)
            cursor.execute("""
                SELECT agent_type, selected_model FROM comments
                WHERE author_id = ? AND agent_type IS NOT NULL
                ORDER BY created_at DESC LIMIT 1
            """, (author_id,))
            result = cursor.fetchone()

            if result:
                db_agent_type = result[0]
                db_model = result[1] if result[1] else default_model

                # Use the agent_type stored in the database without remapping
                agent_type = db_agent_type

                selected_model = db_model
            else:
                # If the comments table lacks agent_type info, infer from the author_id pattern
                if author_id.startswith("echo_"):
                    agent_type = "echo_agent"
                    selected_model = default_model
                elif author_id.startswith("leader_agent") or "leader_agent" in author_id:
                    agent_type = "leader_agent"
                    selected_model = default_model
                elif author_id.startswith("malicious_") or "malicious" in author_id:
                    agent_type = "malicious_agent"
                    selected_model = default_model
                else:
                    # Check the malicious_comments table
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) FROM malicious_comments mc
                            JOIN comments c ON mc.comment_id = c.comment_id
                            WHERE c.author_id = ?
                        """, (author_id,))
                        is_malicious = cursor.fetchone()[0] > 0

                        if is_malicious:
                            agent_type = "malicious_agent"
                            cursor.execute("""
                                SELECT mc.selected_model FROM malicious_comments mc
                                JOIN comments c ON mc.comment_id = c.comment_id
                                WHERE c.author_id = ? AND mc.selected_model IS NOT NULL
                                ORDER BY c.created_at DESC LIMIT 1
                            """, (author_id,))
                            result = cursor.fetchone()
                            if result and result[0]:
                                selected_model = result[0]
                            else:
                                selected_model = default_model
                        else:
                            # Regular user
                            agent_type = "normal_user"
                    except:
                        # If the malicious_comments table does not exist, default to regular user
                        agent_type = "normal_user"
                    cursor.execute("""
                        SELECT selected_model FROM posts
                        WHERE author_id = ? AND selected_model IS NOT NULL
                        ORDER BY created_at DESC LIMIT 1
                    """, (author_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        selected_model = result[0]
                    else:
                        cursor.execute("""
                            SELECT selected_model FROM comments
                            WHERE author_id = ? AND selected_model IS NOT NULL
                            ORDER BY created_at DESC LIMIT 1
                        """, (author_id,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            selected_model = result[0]
                        else:
                            selected_model = default_model

        except Exception as e:
            logging.warning(f"Unable to get agent information for user {author_id}: {e}")

        return agent_type, selected_model

    def export_post(self, post_id: str):
        """Export a single post to the current scenario folder"""
        if not self.export_enabled or post_id in self.exported_posts:
            return

        try:
            cursor = self.conn.cursor()

            # Try to fetch the full record first; fall back to a basic query if columns are missing
            try:
                cursor.execute("""
                    SELECT post_id, content, author_id, created_at, num_likes, num_shares,
                           num_flags, num_comments, is_news, news_type, status,
                           is_agent_response, agent_role, agent_response_type,
                           selected_model, agent_type
                    FROM posts WHERE post_id = ?
                """, (post_id,))
                post_row = cursor.fetchone()
            except sqlite3.OperationalError:
                # If some columns are missing, fall back to a simple query
                cursor.execute("""
                    SELECT post_id, content, author_id, created_at
                    FROM posts WHERE post_id = ?
                """, (post_id,))
                basic_row = cursor.fetchone()
                if basic_row:
                    # Build a dictionary with default values
                    post_row = {
                        'post_id': basic_row[0],
                        'content': basic_row[1],
                        'author_id': basic_row[2],
                        'created_at': basic_row[3],
                        'num_likes': 0,
                        'num_shares': 0,
                        'num_flags': 0,
                        'num_comments': 0,
                        'is_news': False,
                        'news_type': None,
                        'status': 'active',
                        'is_agent_response': False,
                        'agent_role': None,
                        'agent_response_type': None,
                        'selected_model': None,
                        'agent_type': None
                    }
                else:
                    post_row = None
            if not post_row:
                return

            # If post_row is already a dict, use it; otherwise convert it
            if isinstance(post_row, dict):
                post = post_row
            else:
                post = dict(post_row)

            # Skip news posts based on configuration
            if post['author_id'] == 'agentverse_news' and not self.export_news_content:
                self.exported_posts.add(post_id)
                return

            # Create the directory for this post
            post_dir = os.path.join(self.current_export_dir, post_id)
            os.makedirs(post_dir, exist_ok=True)

            # Get agent classification and model information
            agent_type, selected_model = self._get_agent_info(post['author_id'])

            # Prefer the values stored in the database when available
            if post.get("selected_model"):
                selected_model = post["selected_model"]
            if post.get("agent_type"):
                agent_type = post["agent_type"]

            # Build the post info file
            post_info = {
                'post_id': post['post_id'],
                'content': post['content'],
                'author_id': post['author_id'],
                'created_at': post['created_at'],
                'num_likes': post['num_likes'] or 0,
                'num_shares': post['num_shares'] or 0,
                'num_flags': post['num_flags'] or 0,
                'num_comments': post['num_comments'] or 0,
                'is_news': bool(post['is_news']) if post['is_news'] is not None else False,
                'news_type': post['news_type'],
                'status': post['status'],
                'is_agent_response': bool(post['is_agent_response']) if post['is_agent_response'] is not None else False,
                'agent_role': post['agent_role'],
                'agent_response_type': post['agent_response_type'],
                'agent_type': agent_type,
                'selected_model': selected_model,
                'scenario': self.current_scenario,
                'data_source': 'real_post_from_database',
                'exported_at': datetime.now().isoformat()
            }

            post_file = os.path.join(post_dir, 'post.json')
            with open(post_file, 'w', encoding='utf-8') as f:
                json.dump(post_info, f, indent=2, ensure_ascii=False)

            # Record the exported post
            self.exported_posts.add(post_id)


        except Exception as e:
            print(f"⚠️  Failed to export post: {e}")

    def export_comment(self, comment_id: str):
        """Export a single comment to the current scenario folder"""
        if not self.export_enabled or comment_id in self.exported_comments:
            return

        try:
            cursor = self.conn.cursor()

            # First check if the comment is malicious (if the table exists)
            malicious_row = None
            try:
                cursor.execute("""
                    SELECT mc.*, c.post_id, c.created_at, c.num_likes, c.author_id
                    FROM malicious_comments mc
                    LEFT JOIN comments c ON mc.comment_id = c.comment_id
                    WHERE mc.comment_id = ?
                """, (comment_id,))
                malicious_row = cursor.fetchone()
            except sqlite3.OperationalError:
                # If the malicious_comments table does not exist, continue with regular comment processing
                pass

            if malicious_row:
                # Process malicious comment
                malicious_dict = dict(malicious_row)
                post_id = malicious_dict.get("post_id")
                
                if post_id:
                    self._append_comment_to_file(post_id, {
                        'comment_id': malicious_dict["comment_id"],
                        'user_query': malicious_dict.get("content", ""),
                        'content': malicious_dict.get("content", ""),
                        'author_id': malicious_dict.get("author_id") or f"malicious_{malicious_dict['comment_id']}",
                        'created_at': malicious_dict.get("created_at", datetime.now().isoformat()),
                        'post_id': post_id,
                        'num_likes': malicious_dict.get("num_likes", 0) or 0,
                        'is_malicious': True,
                        'persona_used': malicious_dict.get("persona_used"),
                        'agent_type': 'malicious_agent',
                        'selected_model': malicious_dict.get("selected_model", default_model),
                        'scenario': self.current_scenario,
                        'exported_at': datetime.now().isoformat()
                    })
            else:
                # Handle regular comments or agent echo responses
                cursor.execute("""
                    SELECT c.*, p.content as post_content, p.author_id as post_author_id
                    FROM comments c
                    LEFT JOIN posts p ON c.post_id = p.post_id
                    WHERE c.comment_id = ?
                """, (comment_id,))

                comment_row = cursor.fetchone()
                if not comment_row:
                    return

                comment = dict(comment_row)

                # Skip comments on news posts based on configuration
                if comment.get('post_author_id') == 'agentverse_news' and not self.export_news_content:
                    self.exported_comments.add(comment_id)
                    return

                # Get agent classification and model information
                agent_type, selected_model = self._get_agent_info(comment["author_id"])

                # Prefer existing database records for agent/model info
                if comment.get("selected_model"):
                    selected_model = comment["selected_model"]
                if comment.get("agent_type"):
                    agent_type = comment["agent_type"]

                self._append_comment_to_file(comment["post_id"], {
                    'comment_id': comment["comment_id"],
                    'user_query': comment["content"],
                    'content': comment["content"],
                    'author_id': comment["author_id"],
                    'created_at': comment["created_at"],
                    'post_id': comment["post_id"],
                    'num_likes': comment.get("num_likes", 0),
                    'is_malicious': False,
                    'persona_used': None,
                    'agent_type': agent_type,
                    'selected_model': selected_model,
                    'scenario': self.current_scenario,
                    'exported_at': datetime.now().isoformat()
                })

            # Record the exported comment
            self.exported_comments.add(comment_id)

        except Exception as e:
            print(f"⚠️  Failed to export comment: {e}")

    def _append_comment_to_file(self, post_id: str, comment_data: dict):
        """Append comments to the corresponding post file"""
        post_dir = os.path.join(self.current_export_dir, post_id)
        os.makedirs(post_dir, exist_ok=True)

        # Check if the post file exists; export the post if it does not
        post_file = os.path.join(post_dir, 'post.json')
        if not os.path.exists(post_file) and post_id not in self.exported_posts:
            # Attempt to export the corresponding post
            self.export_post(post_id)

        comments_file = os.path.join(post_dir, 'comments.jsonl')
        with open(comments_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(comment_data, ensure_ascii=False) + '\n')

    def on_post_created(self, post_id: str, author_id: str):
        """Callback when a post is created"""
        # Apply centralized filtering logic
        if author_id == 'agentverse_news' and not self.export_news_content:
            return
        self.export_post(post_id)

    def on_comment_created(self, comment_id: str, author_id: str):
        """Callback when a comment is created"""
        self.export_comment(comment_id)

    def get_scenario_info(self) -> dict:
        """Get current scenario information"""
        return {
            'current_scenario': self.current_scenario,
            'export_directory': self.current_export_dir,
            'config_summary': {
                'malicious_bots': self.config.get('malicious_bot_system', {}).get('enabled', False),
                'opinion_balance': self.config.get('opinion_balance_system', {}).get('enabled', False),
                'fact_checking': self.config.get('fact_checking', {}).get('enabled', False),
                'prebunking': self.config.get('prebunking_system', {}).get('enabled', False)
            }
        }

    def force_export_all_data(self):
        """Force export all database data to the current scenario folder"""
        print(f"🔄 Starting forced export of all data into {self.current_scenario}...")

        try:
            cursor = self.conn.cursor()

            # Clear exported records to force a fresh export
            self.exported_posts.clear()
            self.exported_comments.clear()

            # Export all posts
            if self.export_news_content:
                cursor.execute('SELECT post_id, author_id FROM posts ORDER BY created_at')
            else:
                cursor.execute('SELECT post_id, author_id FROM posts WHERE author_id != "agentverse_news" ORDER BY created_at')

            posts = cursor.fetchall()
            print(f"📝 Found {len(posts)} posts to export")

            for post_row in posts:
                post_id = post_row[0]
                author_id = post_row[1]
                self.export_post(post_id)
                print(f"  ✅ Exported post: {post_id}")

            # Export all comments
            if self.export_news_content:
                cursor.execute('SELECT comment_id, author_id FROM comments ORDER BY created_at')
            else:
                cursor.execute('''
                    SELECT c.comment_id, c.author_id
                    FROM comments c
                    JOIN posts p ON c.post_id = p.post_id
                    WHERE p.author_id != "agentverse_news"
                    ORDER BY c.created_at
                ''')

            comments = cursor.fetchall()
            print(f"💬 Found {len(comments)} comments to export")

            for comment_row in comments:
                comment_id = comment_row[0]
                author_id = comment_row[1]
                self.export_comment(comment_id)
                print(f"  ✅ Exported comment: {comment_id}")

            print(f"🎉 Forced export complete! Data saved to {self.current_export_dir}")

        except Exception as e:
            print(f"❌ Forced export failed: {e}")
            import traceback
            traceback.print_exc()

# Global scenario export manager instance
_scenario_export_manager: Optional[ScenarioExportManager] = None

def initialize_scenario_export(db_connection: sqlite3.Connection, config: Dict[str, Any]):
    """Initialize the scenario export manager"""
    global _scenario_export_manager
    _scenario_export_manager = ScenarioExportManager(db_connection, config)

def get_scenario_export_manager() -> Optional[ScenarioExportManager]:
    """Get the scenario export manager instance"""
    return _scenario_export_manager

def on_post_created_scenario(post_id: str, author_id: str):
    """Post creation callback (scenario version)"""
    if _scenario_export_manager:
        _scenario_export_manager.on_post_created(post_id, author_id)

def on_comment_created_scenario(comment_id: str, author_id: str):
    """Comment creation callback (scenario version)"""
    if _scenario_export_manager:
        _scenario_export_manager.on_comment_created(comment_id, author_id)
