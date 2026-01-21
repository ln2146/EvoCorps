#!/usr/bin/env python3
import sqlite3
import os
import json
from datetime import datetime
from collections import defaultdict

# --- CONFIGURATION ---
# Define database and output directory paths
DB_PATH = "database/simulation.db"
OUTPUT_DIR = "result"  # Base output directory

# Selection criteria: export only posts with comment count >= threshold
MIN_COMMENTS_THRESHOLD = 0
# --- END CONFIGURATION ---

def export_posts_and_comments_by_id():
    """
    Export data from the database by:
    1. Selecting "hot" posts whose comment counts meet the threshold.
    2. Creating a dedicated folder for each hot post.
    3. Saving all comments to comments.jsonl and post info to post.json within each folder.
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at '{DB_PATH}'")
        return

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"🔗 Connected to database: {DB_PATH}")
        print(f"📂 Exporting to base directory: {OUTPUT_DIR}")
        print(f"Selection criteria: Posts with comment counts >= {MIN_COMMENTS_THRESHOLD}")

        # 1. Retrieve all post records
        cursor.execute('SELECT post_id, content, author_id, created_at FROM posts')
        all_posts = cursor.fetchall()
        print(f"🔍 Found {len(all_posts)} posts in the database.")

        # 2. Retrieve all comment records
        cursor.execute('''
            SELECT comment_id, content, author_id, created_at, post_id, num_likes, selected_model, agent_type
            FROM comments
            ORDER BY created_at ASC
        ''')
        all_comments = cursor.fetchall()
        print(f"🔍 Found {len(all_comments)} comments in the database.")

        # 3. Group comments by post_id
        comments_by_post = defaultdict(list)
        for comment in all_comments:
            comments_by_post[comment['post_id']].append(dict(comment))

        print("🔄 Processing posts according to the selection criteria...")

        # 4. Iterate posts, filter them, and create directories/files
        exported_posts_count = 0
        skipped_posts_count = 0
        exported_comments_count = 0
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        for post in all_posts:
            post_id = post['post_id']
            comments_for_this_post = comments_by_post.get(post_id, [])
            comment_count = len(comments_for_this_post)

            # Core filtering logic: check whether the comment count meets the threshold
            if comment_count < MIN_COMMENTS_THRESHOLD:
                skipped_posts_count += 1
                continue

            # --- Threshold met; begin export process ---
            exported_posts_count += 1
            post_data = dict(post)
            
            post_dir = os.path.join(OUTPUT_DIR, post_id)
            os.makedirs(post_dir, exist_ok=True)

            # Write post.json
            post_file_path = os.path.join(post_dir, 'post.json')
            with open(post_file_path, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, ensure_ascii=False, indent=4)

            # Write all comments for the current post into comments.jsonl
            comments_file_path = os.path.join(post_dir, 'comments.jsonl')
            with open(comments_file_path, 'w', encoding='utf-8') as f:
                for comment in comments_for_this_post:
                    exported_comments_count += 1
                    record = {
                        'comment_id': comment['comment_id'],
                        'user_query': comment['content'],
                        'content': comment['content'],
                        'author_id': comment['author_id'],
                        'created_at': comment['created_at'],
                        'post_id': comment['post_id'],
                        'num_likes': comment['num_likes'] or 0,
                        'selected_model': comment['selected_model'] or "unknown",
                        'agent_type': comment['agent_type'] or "unknown",
                        'exported_at': datetime.now().isoformat(),
                        'label': ''
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print("\n" + "="*50)
        print("✅ Export completed!")
        print(f"   - Selection: comments >= {MIN_COMMENTS_THRESHOLD}")
        print(f"   - Successfully exported {exported_posts_count} posts.")
        print(f"   - Exported {exported_comments_count} related comments.")
        print(f"   - All comments saved into comments.jsonl.")
        print(f"   - Skipped {skipped_posts_count} posts due to insufficient comment counts.")
        print(f"   - All files stored under '{OUTPUT_DIR}'.")
        print("="*50)

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred during export: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("\n🔌 Database connection closed.")

if __name__ == "__main__":
    export_posts_and_comments_by_id()
