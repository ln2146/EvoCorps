#!/usr/bin/env python3
"""
Auto-export manager - auto-update JSONL files when data is written
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

class AutoExportManager:
    """Auto-export manager - optimized version"""

    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.export_enabled = True

        # Ensure database connection uses Row factory
        if self.conn.row_factory != sqlite3.Row:
            self.conn.row_factory = sqlite3.Row

        # Export file path config - unify under exported_content/data
        self.export_files = {
            'normal_users': 'exported_content/data/normal_users_content.jsonl',
            'malicious_agents': 'exported_content/data/malicious_agents_content.jsonl',
            'echo_agents': 'exported_content/data/echo_agents_content.jsonl',
            'integrated': 'exported_content/data/output.jsonl'
        }

        # organized_comments_from_jsonl export config
        self.organized_export_dir = 'organized_comments_from_jsonl'
        self.organized_exported_posts = set()
        self.organized_exported_comments = set()

        # Ensure export directories exist
        os.makedirs('exported_content/data', exist_ok=True)
        os.makedirs(self.organized_export_dir, exist_ok=True)

        # Record exported content IDs to avoid duplicates
        self.exported_comments = set()
        self.exported_posts = set()
        self._load_exported_records()
        self._load_organized_exported_records()

    def _get_agent_info(self, author_id: str) -> tuple[str, str]:
        """Get agent type and model info"""
        agent_type = "unknown"
        selected_model = "unknown"
        from multi_model_selector import MultiModelSelector
        default_model = MultiModelSelector.DEFAULT_POOL[0]

        try:
            cursor = self.conn.cursor()

            # Check Echo Agent
            if author_id.startswith("echo_"):
                agent_type = "echo_agent"
                # Try to get actual model used from comments
                cursor.execute("""
                    SELECT selected_model FROM comments
                    WHERE author_id = ? AND selected_model IS NOT NULL AND selected_model != 'unknown'
                    ORDER BY created_at DESC LIMIT 1
                """, (author_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    selected_model = result[0]
                else:
                    # If not found, use default model
                    selected_model = default_model

            # Check malicious agents - confirm via malicious_comments table
            else:
                # Check whether in malicious_comments table
                cursor.execute("""
                    SELECT COUNT(*) FROM malicious_comments mc
                    JOIN comments c ON mc.comment_id = c.comment_id
                    WHERE c.author_id = ?
                """, (author_id,))
                is_malicious = cursor.fetchone()[0] > 0

                if is_malicious:
                    agent_type = "malicious_agent"
                    # Get model info from malicious_comments table
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
                        selected_model = default_model  # Default malicious model
                elif author_id.startswith("malicious_") or "malicious" in author_id:
                    agent_type = "malicious_agent"
                    selected_model = default_model  # Default malicious model
                else:
                    # Normal user
                    agent_type = "normal_user"
                    # Try to get from posts or comments
                    cursor.execute("""
                        SELECT selected_model FROM posts
                        WHERE author_id = ? AND selected_model IS NOT NULL
                        ORDER BY created_at DESC LIMIT 1
                    """, (author_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        selected_model = result[0]
                    else:
                        # Try to get from comments
                        cursor.execute("""
                            SELECT selected_model FROM comments
                            WHERE author_id = ? AND selected_model IS NOT NULL
                            ORDER BY created_at DESC LIMIT 1
                        """, (author_id,))
                        result = cursor.fetchone()
                        if result and result[0]:
                            selected_model = result[0]
                        else:
                            selected_model = default_model  # Default normal model

        except Exception as e:
            logging.warning(f"Unable to get agent info for user {author_id}: {e}")

        return agent_type, selected_model

    def _load_exported_records(self):
        """Load exported record IDs"""
        try:
            # Read exported IDs from existing files
            for file_path in [self.export_files['normal_users'],
                             self.export_files['malicious_agents'],
                             self.export_files['echo_agents']]:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    if 'comment_id' in data:
                                        self.exported_comments.add(data['comment_id'])
                                    elif 'post_id' in data:
                                        self.exported_posts.add(data['post_id'])
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            print(f"⚠️  Failed to load exported records: {e}")

    def _load_organized_exported_records(self):
        """Load exported records for organized_comments_from_jsonl"""
        try:
            if os.path.exists(self.organized_export_dir):
                for item in os.listdir(self.organized_export_dir):
                    if item.startswith('post-') and os.path.isdir(os.path.join(self.organized_export_dir, item)):
                        self.organized_exported_posts.add(item)

                        # Check comments file
                        comments_file = os.path.join(self.organized_export_dir, item, 'comments.jsonl')
                        if os.path.exists(comments_file):
                            with open(comments_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    try:
                                        comment = json.loads(line.strip())
                                        self.organized_exported_comments.add(comment.get('comment_id', ''))
                                    except json.JSONDecodeError:
                                        continue
        except Exception as e:
            print(f"⚠️  Failed to load organized exported records: {e}")

    def _append_to_jsonl(self, file_path: str, data: dict):
        """Append data to JSONL file"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  Failed to write file {file_path}: {e}")

    def _integrate_all_files(self):
        """Integrate all files into output.jsonl (incremental)"""
        try:
            # Record integrated content to avoid duplicates
            integrated_ids = set()

            # Read IDs from existing integrated file
            if os.path.exists(self.export_files['integrated']):
                with open(self.export_files['integrated'], 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if 'comment_id' in data:
                                    integrated_ids.add(data['comment_id'])
                            except json.JSONDecodeError:
                                continue

            # Append new content to integrated file
            new_entries_count = 0
            with open(self.export_files['integrated'], 'a', encoding='utf-8') as output_file:
                # Read and merge new content from all source files
                for source_file in [self.export_files['normal_users'],
                                   self.export_files['malicious_agents'],
                                   self.export_files['echo_agents']]:
                    if os.path.exists(source_file):
                        with open(source_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        data = json.loads(line)
                                        comment_id = data.get('comment_id')
                                        if comment_id and comment_id not in integrated_ids:
                                            output_file.write(line)
                                            integrated_ids.add(comment_id)
                                            new_entries_count += 1
                                    except json.JSONDecodeError:
                                        continue

            if new_entries_count > 0:
                # Silent integration - no need to display success message
                pass
        except Exception as e:
            print(f"⚠️  Failed to integrate files: {e}")

    def export_all_content(self):
        """Export all user content to JSONL files (incremental)"""
        if not self.export_enabled:
            return

        try:
            # Export new content
            self._export_new_normal_user_content()
            self._export_new_malicious_content()
            self._export_new_echo_agent_content()

            # Integrate all files into output.jsonl
            self._integrate_all_files()



        except Exception as e:
            print(f"⚠️  Auto export failed: {e}")

    def _export_new_normal_user_content(self):
        """Export new normal user content"""
        # Export new comments
        new_comments = self._get_new_normal_user_comments()
        for comment in new_comments:
            self._append_to_jsonl(self.export_files['normal_users'], comment)
            self.exported_comments.add(comment['comment_id'])

        # Export new posts
        new_posts = self._get_new_normal_user_posts()
        for post in new_posts:
            # Convert post format to comment format (unified format)
            post_as_comment = {
                'comment_id': post['post_id'],
                'user_query': post['content'],
                'author_id': post['author_id'],
                'created_at': post['created_at'],
                'post_id': post['post_id'],  # The post_id for a post is itself
                'num_likes': post.get('num_likes', 0),
                'selected_model': post.get('selected_model', 'unknown'),  # Add model field
                'exported_at': datetime.now().isoformat()
            }
            self._append_to_jsonl(self.export_files['normal_users'], post_as_comment)
            self.exported_posts.add(post['post_id'])

    def _export_new_malicious_content(self):
        """Export new malicious agent content"""
        new_comments = self._get_new_malicious_comments()
        for comment in new_comments:
            self._append_to_jsonl(self.export_files['malicious_agents'], comment)
            self.exported_comments.add(comment['comment_id'])

    def _export_new_echo_agent_content(self):
        """Export new echo agent content"""
        # Export new comments
        new_comments = self._get_new_echo_agent_comments()
        for comment in new_comments:
            self._append_to_jsonl(self.export_files['echo_agents'], comment)
            self.exported_comments.add(comment['comment_id'])

        # Export new posts
        new_posts = self._get_new_echo_agent_posts()
        for post in new_posts:
            # Get agent type and model info
            agent_type, selected_model = self._get_agent_info(post['author_id'])

            # Convert post format to comment format (unified format)
            post_as_comment = {
                'comment_id': post['post_id'],
                'user_query': post['content'],
                'author_id': post['author_id'],
                'created_at': post['created_at'],
                'post_id': post['post_id'],  # The post_id for a post is itself
                'num_likes': post.get('num_likes', 0),
                'agent_type': agent_type,
                'selected_model': selected_model,
                'exported_at': datetime.now().isoformat()
            }
            self._append_to_jsonl(self.export_files['echo_agents'], post_as_comment)
            self.exported_posts.add(post['post_id'])

    def _get_new_normal_user_posts(self) -> List[Dict[str, Any]]:
        """Get new normal user posts (not exported)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT post_id, content, author_id, created_at, num_likes, num_shares, num_flags, num_comments, original_post_id, is_news, news_type, status, takedown_timestamp, takedown_reason, fact_check_status, fact_checked_at, is_agent_response, agent_role, agent_response_type, intervention_id, selected_model, agent_type FROM posts
            WHERE is_agent_response = 0 AND is_news = 0
            AND author_id NOT LIKE '%malicious_agent%'
            AND author_id NOT LIKE '%echo_%'
            AND author_id != 'agentverse_news'
            ORDER BY created_at DESC
        """)
        all_posts = [dict(row) for row in cursor.fetchall()]
        # Return only unexported posts
        return [post for post in all_posts if post['post_id'] not in self.exported_posts]

    def _get_new_normal_user_comments(self) -> List[Dict[str, Any]]:
        """Get new normal user comments (not exported)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.content as post_content
            FROM comments c LEFT JOIN posts p ON c.post_id = p.post_id
            WHERE c.author_id NOT LIKE '%malicious_agent%'
            AND c.author_id NOT LIKE '%echo_%'
            AND c.comment_id NOT IN (
                SELECT comment_id FROM malicious_comments WHERE comment_id IS NOT NULL
            )
            ORDER BY c.created_at DESC
        """)
        all_comments = [dict(row) for row in cursor.fetchall()]
        # Convert to unified format and filter unexported
        new_comments = []
        for comment in all_comments:
            if comment['comment_id'] not in self.exported_comments:
                # Get agent type and model info
                agent_type, selected_model = self._get_agent_info(comment['author_id'])

                # Safely get field values to avoid KeyError
                try:
                    formatted_comment = {
                        'comment_id': comment.get('comment_id', ''),
                        'user_query': comment.get('content', ''),
                        'author_id': comment.get('author_id', ''),
                        'created_at': comment.get('created_at', ''),
                        'post_id': comment.get('post_id', ''),
                        'num_likes': comment.get('num_likes', 0),
                        'selected_model': selected_model,
                        'agent_type': agent_type,
                        'exported_at': datetime.now().isoformat()
                    }
                except Exception as e:
                    print(f"⚠️ Error formatting comment: {e}, comment keys: {list(comment.keys()) if hasattr(comment, 'keys') else 'not dict'}")
                    continue
                new_comments.append(formatted_comment)
        return new_comments

    def _get_new_malicious_comments(self) -> List[Dict[str, Any]]:
        """Get new malicious bot comments (not exported)"""
        cursor = self.conn.cursor()

        # First try to fetch from malicious_comments table
        cursor.execute("""
            SELECT mc.*, c.post_id, c.created_at, c.num_likes, p.content as post_content
            FROM malicious_comments mc
            LEFT JOIN comments c ON mc.comment_id = c.comment_id
            LEFT JOIN posts p ON c.post_id = p.post_id
            WHERE mc.comment_id IS NOT NULL
            ORDER BY c.created_at DESC
        """)

        malicious_comments = cursor.fetchall()

        # If malicious_comments table is empty, find malicious comments from comments table
        if not malicious_comments:
            cursor.execute("""
                SELECT c.*, p.content as post_content
                FROM comments c
                LEFT JOIN posts p ON c.post_id = p.post_id
                WHERE (c.content IN ('False!', 'Wrong!', 'JOKE!', 'Ridiculous!', 'Lies!', 'BS!', 'Fake!', 'Garbage!', 'Nope!', 'Absurd!', 'NONSENSE!', 'IDIOTIC!', 'Nuts!', 'Crazy!', 'PATHETIC!', 'Delusional!')
                     OR c.content LIKE '%PATHETIC%'
                     OR c.content LIKE '%Delusional%'
                     OR c.content LIKE '%🔥[malicious bot]%'
                     OR c.content LIKE '%False!%'
                     OR c.content LIKE '%Wrong!%'
                     OR c.content LIKE '%Ridiculous!%'
                     OR c.content LIKE '%Lies!%'
                     OR c.content LIKE '%BS!%'
                     OR c.content LIKE '%Fake!%'
                     OR c.author_id LIKE '%malicious%')
                ORDER BY c.created_at DESC
            """)
            malicious_comments = cursor.fetchall()

        new_comments = []
        for row in malicious_comments:
            # Convert sqlite3.Row to dict to enable .get() method
            row_dict = dict(row)
            comment_id = row_dict.get("comment_id")
            if comment_id and comment_id not in self.exported_comments:
                # Data fetched from malicious_comments table
                if "persona_used" in row_dict and row_dict.get("persona_used"):
                    author_id = f"malicious_agent_{row_dict.get('persona_used', 'unknown')}"
                    content = row_dict.get("content") if row_dict.get("content") else row_dict.get("user_query", "")
                else:
                    # Data fetched from comments table
                    author_id = row_dict.get("author_id", "unknown")
                    content = row_dict.get("content", "")

                # Safely get field values
                try:
                    formatted_comment = {
                        'comment_id': comment_id,
                        'user_query': content,
                        'author_id': author_id,
                        'created_at': row_dict.get("created_at", ""),
                        'post_id': row_dict.get("post_id", ""),
                        'num_likes': row_dict.get("num_likes", 0) or 0,
                        'selected_model': row_dict.get("selected_model", "unknown"),
                        'agent_type': 'malicious',
                        'persona_used': row_dict.get("persona_used", "unknown"),
                        'exported_at': datetime.now().isoformat()
                    }
                except Exception as e:
                    print(f"⚠️ Error formatting malicious comment: {e}, row keys: {list(row_dict.keys()) if hasattr(row_dict, 'keys') else 'not dict'}")
                    continue
                new_comments.append(formatted_comment)
        return new_comments

    def _get_new_echo_agent_posts(self) -> List[Dict[str, Any]]:
        """Get new echo agent posts (not exported)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT post_id, content, author_id, created_at, num_likes, num_shares, num_flags, num_comments, original_post_id, is_news, news_type, status, takedown_timestamp, takedown_reason, fact_check_status, fact_checked_at, is_agent_response, agent_role, agent_response_type, intervention_id, selected_model, agent_type FROM posts
            WHERE author_id LIKE '%echo_%'
            ORDER BY created_at DESC
        """)
        all_posts = [dict(row) for row in cursor.fetchall()]
        # Return only unexported posts
        return [post for post in all_posts if post['post_id'] not in self.exported_posts]

    def _get_new_echo_agent_comments(self) -> List[Dict[str, Any]]:
        """Get new echo agent comments (not exported)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.content as post_content
            FROM comments c LEFT JOIN posts p ON c.post_id = p.post_id
            WHERE c.author_id LIKE '%echo_%'
            ORDER BY c.created_at DESC
        """)
        all_comments = [dict(row) for row in cursor.fetchall()]
        # Convert to unified format and filter unexported
        new_comments = []
        for comment in all_comments:
            comment_id = comment.get('comment_id')

            # Skip records with empty comment_id
            if not comment_id or comment_id in self.exported_comments:
                continue

            # Ensure all required fields exist
            content = comment.get('content', '')
            author_id = comment.get('author_id', '')
            created_at = comment.get('created_at', '')
            post_id = comment.get('post_id', '')

            # Skip records missing key info
            if not content or not author_id:
                continue

            # Get agent type and model info
            agent_type, selected_model = self._get_agent_info(author_id)

            formatted_comment = {
                'comment_id': comment_id,
                'user_query': content,
                'author_id': author_id,
                'created_at': created_at,
                'post_id': post_id,
                'num_likes': comment.get('num_likes', 0),
                'agent_type': agent_type,
                'selected_model': selected_model,
                'exported_at': datetime.now().isoformat()
            }
            new_comments.append(formatted_comment)
        return new_comments

    def _get_normal_user_posts(self) -> List[Dict[str, Any]]:
        """Get normal user posts"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT post_id, content, author_id, created_at, num_likes, num_shares, num_flags, num_comments, original_post_id, is_news, news_type, status, takedown_timestamp, takedown_reason, fact_check_status, fact_checked_at, is_agent_response, agent_role, agent_response_type, intervention_id, selected_model, agent_type FROM posts
            WHERE is_agent_response = 0 AND is_news = 0
            AND author_id NOT LIKE '%malicious_agent%'
            AND author_id != 'agentverse_news'
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_normal_user_comments(self) -> List[Dict[str, Any]]:
        """Get normal user comments"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.content as post_content
            FROM comments c LEFT JOIN posts p ON c.post_id = p.post_id
            WHERE c.author_id NOT LIKE '%malicious_agent%'
            AND c.author_id NOT LIKE '%echo_%'
            AND c.comment_id NOT IN (
                SELECT comment_id FROM malicious_comments WHERE comment_id IS NOT NULL
            )
            ORDER BY c.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_malicious_comments(self) -> List[Dict[str, Any]]:
        """Get malicious bot comments"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mc.*, c.post_id, c.created_at, c.num_likes, p.content as post_content
            FROM malicious_comments mc
            LEFT JOIN comments c ON mc.comment_id = c.comment_id
            LEFT JOIN posts p ON c.post_id = p.post_id
            ORDER BY c.created_at DESC
        """)
        
        malicious_comments = []
        for row in cursor.fetchall():
            comment = {
                "comment_id": row["comment_id"],
                "post_id": row["post_id"],
                "author_id": f"malicious_agent_{row['persona_used']}",
                "content": row["content"],
                "created_at": row["created_at"],
                "num_likes": row["num_likes"] or 0,
                "attack_id": row["attack_id"],
                "persona_used": row["persona_used"],
                "attack_type": row["attack_type"],
                "intensity_level": row["intensity_level"],
                "post_content": row["post_content"]
            }
            malicious_comments.append(comment)
        
        return malicious_comments
    
    def _get_echo_agent_posts(self) -> List[Dict[str, Any]]:
        """Get echo group posts"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT post_id, content, author_id, created_at, num_likes, num_shares, num_flags, num_comments, original_post_id, is_news, news_type, status, takedown_timestamp, takedown_reason, fact_check_status, fact_checked_at, is_agent_response, agent_role, agent_response_type, intervention_id, selected_model, agent_type FROM posts
            WHERE is_agent_response = 1
            AND author_id NOT LIKE '%malicious_agent%'
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_echo_agent_comments(self) -> List[Dict[str, Any]]:
        """Get echo group comments"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.content as post_content
            FROM comments c LEFT JOIN posts p ON c.post_id = p.post_id
            WHERE c.author_id LIKE '%echo_%'
            ORDER BY c.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def _write_json_file(self, filename: str, data: Dict[str, Any]):
        """Write JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to write file {filename}: {e}")
    
    def on_comment_created(self, comment_id: str, author_id: str):
        """Callback when comment is created - incremental export"""
        if comment_id not in self.exported_comments:
            self.export_single_comment(comment_id)
            print(f"📁 Comment auto-saved - ID: {comment_id}")

    def on_post_created(self, post_id: str, author_id: str):
        """Callback when post is created - incremental export"""
        # Skip news posts; only process user posts
        if author_id == 'agentverse_news':
            return  # Do not export news posts

        if post_id not in self.exported_posts:
            self.export_single_post(post_id)


    def on_comment_printed(self, comment_id: str, author_id: str, content: str):
        """Callback when comment is printed - export immediately"""
        if comment_id not in self.exported_comments:
            self.export_single_comment(comment_id)
            print(f"💾 Comment saved in real time - ID: {comment_id}")

    def export_single_comment(self, comment_id: str):
        """Export a single comment (incremental update to JSONL format)"""
        if not self.export_enabled or comment_id in self.exported_comments:
            return

        try:
            # Get comment info
            cursor = self.conn.cursor()

            # First check whether it's a malicious comment
            cursor.execute("""
                SELECT mc.*, c.post_id, c.created_at, c.num_likes, c.author_id
                FROM malicious_comments mc
                LEFT JOIN comments c ON mc.comment_id = c.comment_id
                WHERE mc.comment_id = ?
            """, (comment_id,))

            malicious_row = cursor.fetchone()
            if malicious_row:
                try:
                    # Malicious comment - safe field access
                    malicious_dict = dict(malicious_row)
                    comment_id_safe = malicious_dict.get("comment_id", comment_id)
                    real_author_id = malicious_dict.get("author_id") or f"malicious_{comment_id_safe}"

                    # Set agent_type and selected_model for malicious bot
                    agent_type = 'malicious_agent'
                    selected_model = malicious_dict.get("selected_model") or default_model

                    formatted_comment = {
                        'comment_id': comment_id_safe,
                        'user_query': malicious_dict.get("content", ""),
                        'author_id': real_author_id,
                        'created_at': malicious_dict.get("created_at", datetime.now().isoformat()),
                        'post_id': malicious_dict.get("post_id", ""),
                        'num_likes': malicious_dict.get("num_likes", 0) or 0,
                        'agent_type': agent_type,
                        'selected_model': selected_model,
                        'persona_used': malicious_dict.get("persona_used"),
                        'exported_at': datetime.now().isoformat()
                    }
                except Exception as e:
                    logging.error(f"Error processing malicious comment data: {e}, data: {dict(malicious_row)}")
                    return
                self._append_to_jsonl(self.export_files['malicious_agents'], formatted_comment)
            else:
                # Normal comment or echo agent comment
                cursor.execute("""
                    SELECT c.*, p.content as post_content, p.author_id as post_author_id
                    FROM comments c
                    LEFT JOIN posts p ON c.post_id = p.post_id
                    WHERE c.comment_id = ?
                """, (comment_id,))

                comment_row = cursor.fetchone()
                if not comment_row:
                    print(f"⚠️  Comment {comment_id} does not exist in comments table")
                    return

                comment = dict(comment_row)

                # Skip comments on news posts
                if comment.get('post_author_id') == 'agentverse_news':
                    self.exported_comments.add(comment_id)  # Mark as processed
                    return

                # Get agent type and model info
                agent_type, selected_model = self._get_agent_info(comment["author_id"])

                # Prefer model record from database
                if comment.get("selected_model"):
                    selected_model = comment["selected_model"]

                formatted_comment = {
                    'comment_id': comment["comment_id"],
                    'user_query': comment["content"],
                    'author_id': comment["author_id"],
                    'created_at': comment["created_at"],
                    'post_id': comment["post_id"],
                    'num_likes': comment.get("num_likes", 0),
                    'agent_type': agent_type,
                    'selected_model': selected_model,
                    'exported_at': datetime.now().isoformat()
                }

                # Determine type based on author_id
                if 'echo_' in comment["author_id"]:
                    self._append_to_jsonl(self.export_files['echo_agents'], formatted_comment)
                elif 'malicious_agent' in comment["author_id"]:
                    # This should not happen because we already checked for malicious comments above
                    self._append_to_jsonl(self.export_files['malicious_agents'], formatted_comment)
                else:
                    self._append_to_jsonl(self.export_files['normal_users'], formatted_comment)

            # Record exported
            self.exported_comments.add(comment_id)

            # Update integrated file
            self._integrate_all_files()

        except Exception as e:
            print(f"⚠️  Auto export failed: {e}")
            import traceback
            traceback.print_exc()

    def export_single_post(self, post_id: str):
        """Export a single post (incremental update to JSONL format)"""
        if not self.export_enabled or post_id in self.exported_posts:
            return

        try:
            # Get post info
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT post_id, content, author_id, created_at, num_likes, num_shares, num_flags, num_comments, original_post_id, is_news, news_type, status, takedown_timestamp, takedown_reason, fact_check_status, fact_checked_at, is_agent_response, agent_role, agent_response_type, intervention_id, selected_model, agent_type FROM posts WHERE post_id = ?
            """, (post_id,))

            post_row = cursor.fetchone()
            if not post_row:
                return

            post = dict(post_row)

            # Skip news posts - do not export news content
            if post['author_id'] == 'agentverse_news':
                self.exported_posts.add(post_id)  # Mark as processed to avoid duplicate checks
                return

            # Only export user posts, not as comment format
            # Note: per requirements, we only export comments, not post content
            # So we only mark as processed here, no actual export

            # Record exported
            self.exported_posts.add(post_id)

        except Exception as e:
            print(f"⚠️  Single post export failed: {e}")

    # Old update method has been replaced by new JSONL format method
    
    def enable_auto_export(self):
        """Enable auto export"""
        self.export_enabled = True
    
    def disable_auto_export(self):
        """Disable auto export"""
        self.export_enabled = False

    def export_to_organized_format(self):
        """Export to organized_comments_from_jsonl format (incremental mode)"""
        if not self.export_enabled:
            return

        try:
            cursor = self.conn.cursor()

            # 1. Export new posts
            new_posts = self._export_new_posts_organized(cursor)

            # 2. Export new comments
            new_comments = self._export_new_comments_organized(cursor)

            if new_posts or new_comments:
                pass  # Silent process

        except Exception as e:
            print(f"❌ Failed to export to organized format: {e}")

    def _export_new_posts_organized(self, cursor) -> int:
        """Export new posts to organized format"""
        cursor.execute('''
            SELECT post_id, content, author_id, created_at, num_likes, num_shares,
                   num_flags, num_comments, is_news, news_type, status,
                   is_agent_response, agent_role, agent_response_type,
                   selected_model, agent_type
            FROM posts
        ''')
        posts = cursor.fetchall()

        new_posts_count = 0
        for post_row in posts:
            post = dict(post_row)
            post_id = post['post_id']

            # Skip records where post_id is None
            if post_id is None:
                continue

            # Skip already exported posts
            if post_id in self.organized_exported_posts:
                continue

            # Create post folder
            post_dir = os.path.join(self.organized_export_dir, post_id)
            os.makedirs(post_dir, exist_ok=True)

            # Get agent type and model info
            agent_type, selected_model = self._get_agent_info(post['author_id'])

            # Prefer records from database
            if post.get("selected_model"):
                selected_model = post["selected_model"]
            if post.get("agent_type"):
                agent_type = post["agent_type"]

            # Create post info file
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
                'data_source': 'real_post_from_database',
                'exported_at': datetime.now().isoformat()
            }

            post_file = os.path.join(post_dir, 'post.json')
            with open(post_file, 'w', encoding='utf-8') as f:
                json.dump(post_info, f, indent=2, ensure_ascii=False)

            # Record exported
            self.organized_exported_posts.add(post_id)
            new_posts_count += 1

        return new_posts_count

    def _export_new_comments_organized(self, cursor) -> int:
        """Export new comments to organized format"""
        cursor.execute('''
            SELECT comment_id, content, author_id, created_at, post_id, num_likes, selected_model, agent_type
            FROM comments
            ORDER BY created_at
        ''')
        comments = cursor.fetchall()

        new_comments_count = 0
        comments_by_post = {}

        # Group comments by post
        for comment_row in comments:
            comment = dict(comment_row)
            comment_id = comment['comment_id']
            post_id = comment['post_id']

            # Skip already exported comments
            if comment_id in self.organized_exported_comments:
                continue

            if post_id not in comments_by_post:
                comments_by_post[post_id] = []

            # Get agent type and model info
            agent_type, selected_model = self._get_agent_info(comment['author_id'])

            # Prefer records from database
            if comment.get("selected_model"):
                selected_model = comment["selected_model"]
            if comment.get("agent_type"):
                agent_type = comment["agent_type"]

            comment_info = {
                'comment_id': comment['comment_id'],
                'user_query': comment['content'],  # Keep compatibility
                'content': comment['content'],
                'author_id': comment['author_id'],
                'created_at': comment['created_at'],
                'post_id': comment['post_id'],
                'num_likes': comment['num_likes'] or 0,
                'agent_type': agent_type,
                'selected_model': selected_model,
                'exported_at': datetime.now().isoformat()
            }

            comments_by_post[post_id].append(comment_info)
            self.organized_exported_comments.add(comment_id)
            new_comments_count += 1

        # Append new comments to corresponding files
        for post_id, new_comments in comments_by_post.items():
            post_dir = os.path.join(self.organized_export_dir, post_id)
            os.makedirs(post_dir, exist_ok=True)

            comments_file = os.path.join(post_dir, 'comments.jsonl')

            # Append new comments in append mode
            with open(comments_file, 'a', encoding='utf-8') as f:
                for comment in new_comments:
                    f.write(json.dumps(comment, ensure_ascii=False) + '\n')

        return new_comments_count

# Global auto export manager instance
_auto_export_manager: Optional[AutoExportManager] = None

def initialize_auto_export(db_connection: sqlite3.Connection):
    """Initialize auto export manager"""
    global _auto_export_manager
    _auto_export_manager = AutoExportManager(db_connection)

def get_auto_export_manager() -> Optional[AutoExportManager]:
    """Get auto export manager instance"""
    return _auto_export_manager

def trigger_auto_export():
    """Trigger auto export"""
    if _auto_export_manager:
        _auto_export_manager.export_all_content()

def on_comment_created(comment_id: str, author_id: str):
    """Comment created callback"""
    if _auto_export_manager:
        _auto_export_manager.on_comment_created(comment_id, author_id)

def on_post_created(post_id: str, author_id: str):
    """Post created callback"""
    if _auto_export_manager:
        _auto_export_manager.on_post_created(post_id, author_id)

def on_comment_printed(comment_id: str, author_id: str, content: str):
    """Comment printed callback"""
    if _auto_export_manager:
        _auto_export_manager.on_comment_printed(comment_id, author_id, content)

def export_to_organized_format():
    """Export to organized_comments_from_jsonl format (standalone function)"""
    import sqlite3
    import json
    import os
    from datetime import datetime

    # Dynamically determine path
    if os.path.exists('database/simulation.db'):
        db_path = 'database/simulation.db'
        export_dir = 'organized_comments_from_jsonl'
    else:
        db_path = '../database/simulation.db'
        export_dir = '../organized_comments_from_jsonl'

    if not os.path.exists(db_path):
        print(f"❌ Database file does not exist: {db_path}")
        return

    # Ensure export directory exists
    os.makedirs(export_dir, exist_ok=True)

    # Record exported content
    exported_posts = set()
    exported_comments = set()

    # Load exported records
    if os.path.exists(export_dir):
        for item in os.listdir(export_dir):
            if item.startswith('post-') and os.path.isdir(os.path.join(export_dir, item)):
                exported_posts.add(item)

                # Check comments file
                comments_file = os.path.join(export_dir, item, 'comments.jsonl')
                if os.path.exists(comments_file):
                    try:
                        with open(comments_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                try:
                                    comment = json.loads(line.strip())
                                    exported_comments.add(comment.get('comment_id', ''))
                                except json.JSONDecodeError:
                                    continue
                    except Exception:
                        continue

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Export new posts
        cursor.execute('''
            SELECT post_id, content, author_id, created_at, num_likes, num_shares,
                   num_flags, num_comments, is_news, news_type, status,
                   is_agent_response, agent_role, agent_response_type
            FROM posts
        ''')
        posts = cursor.fetchall()

        new_posts_count = 0
        for post in posts:
            post_id = post['post_id']

            # Skip invalid post_id
            if not post_id:
                continue

            # Skip already exported posts
            if post_id in exported_posts:
                continue

            # Create post folder
            post_dir = os.path.join(export_dir, post_id)
            os.makedirs(post_dir, exist_ok=True)

            # Create post info file
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
                'data_source': 'real_post_from_database',
                'exported_at': datetime.now().isoformat()
            }

            post_file = os.path.join(post_dir, 'post.json')
            with open(post_file, 'w', encoding='utf-8') as f:
                json.dump(post_info, f, indent=2, ensure_ascii=False)

            exported_posts.add(post_id)
            new_posts_count += 1

        # Export new comments (package includes malicious flag)
        cursor.execute('''
            SELECT c.comment_id, c.content, c.author_id, c.created_at, c.post_id, c.num_likes,
                   CASE WHEN mc.comment_id IS NOT NULL THEN 1 ELSE 0 END as is_malicious,
                   mc.persona_used
            FROM comments c
            LEFT JOIN malicious_comments mc ON c.comment_id = mc.comment_id
            ORDER BY c.created_at
        ''')
        comments = cursor.fetchall()

        new_comments_count = 0
        comments_by_post = {}

        # Group comments by post
        for comment in comments:
            comment_id = comment['comment_id']
            post_id = comment['post_id']

            # Skip invalid ID
            if not comment_id or not post_id:
                continue

            # Skip already exported comments
            if comment_id in exported_comments:
                continue

            if post_id not in comments_by_post:
                comments_by_post[post_id] = []

            comment_info = {
                'comment_id': comment['comment_id'],
                'user_query': comment['content'],  # Keep compatibility
                'content': comment['content'],
                'author_id': comment['author_id'],
                'created_at': comment['created_at'],
                'post_id': comment['post_id'],
                'num_likes': comment['num_likes'] or 0,
                'is_malicious': bool(comment['is_malicious']),
                'persona_used': comment['persona_used'] if comment['persona_used'] else None,
                'exported_at': datetime.now().isoformat()
            }

            comments_by_post[post_id].append(comment_info)
            exported_comments.add(comment_id)
            new_comments_count += 1

        # Append new comments to corresponding files
        for post_id, new_comments in comments_by_post.items():
            post_dir = os.path.join(export_dir, post_id)
            os.makedirs(post_dir, exist_ok=True)

            comments_file = os.path.join(post_dir, 'comments.jsonl')

            # Append new comments in append mode
            with open(comments_file, 'a', encoding='utf-8') as f:
                for comment in new_comments:
                    f.write(json.dumps(comment, ensure_ascii=False) + '\n')

        conn.close()

        print(f"✅ Incremental export complete: {new_posts_count} new posts, {new_comments_count} new comments")

    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()

def export_single_comment(comment_id: str):
    """Export a single comment"""
    if _auto_export_manager:
        _auto_export_manager.export_single_comment(comment_id)
