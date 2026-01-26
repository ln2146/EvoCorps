#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend API Server for EvoCorps
提供前端所需的数据库查询接口
"""

import sys
import io

# 设置标准输出为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os
import glob

app = Flask(__name__)
CORS(app)

DATABASE_DIR = 'database'

@app.route('/api/databases', methods=['GET'])
def get_databases():
    """获取所有可用的数据库列表"""
    try:
        db_files = glob.glob(os.path.join(DATABASE_DIR, '*.db'))
        databases = [os.path.basename(f) for f in db_files]
        return jsonify({'databases': databases})
    except Exception as e:
        return jsonify({'error': str(e), 'databases': []}), 500

@app.route('/api/stats/<db_name>', methods=['GET'])
def get_stats(db_name):
    """获取指定数据库的统计信息"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取活跃用户数
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
        active_users = cursor.fetchone()[0] or 0
        
        # 获取发布内容数
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0] or 0
        
        # 获取用户评论数
        cursor.execute("SELECT COUNT(*) FROM comments")
        total_comments = cursor.fetchone()[0] or 0
        
        # 获取互动点赞数（num_likes + num_shares）
        cursor.execute("""
            SELECT 
                COALESCE(SUM(num_likes), 0) + COALESCE(SUM(num_shares), 0) 
            FROM posts
        """)
        total_likes = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'activeUsers': active_users,
            'totalPosts': total_posts,
            'totalComments': total_comments,
            'totalLikes': int(total_likes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})

@app.route('/api/users/<db_name>', methods=['GET'])
def get_users(db_name):
    """获取用户列表"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, persona, creation_time, influence_score
            FROM users
            ORDER BY influence_score DESC
            LIMIT 100
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'persona': row[1],
                'creation_time': row[2],
                'influence_score': row[3]
            })
        
        conn.close()
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<db_name>/<user_id>', methods=['GET'])
def get_user_detail(db_name, user_id):
    """获取用户详细信息"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 基本信息
        cursor.execute("""
            SELECT user_id, persona, background_labels, creation_time, 
                   follower_count, total_likes_received, total_shares_received,
                   total_comments_received, influence_score, is_influencer
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # 发帖数
        cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = ?", (user_id,))
        post_count = cursor.fetchone()[0]
        
        # 评论数
        cursor.execute("SELECT COUNT(*) FROM comments WHERE author_id = ?", (user_id,))
        comment_count = cursor.fetchone()[0]
        
        # 获赞数
        cursor.execute("""
            SELECT COALESCE(SUM(num_likes), 0) 
            FROM posts 
            WHERE author_id = ?
        """, (user_id,))
        likes_received = cursor.fetchone()[0]
        
        # 平均互动（每篇帖子的平均点赞+评论+分享）
        cursor.execute("""
            SELECT COALESCE(AVG(num_likes + num_comments + num_shares), 0)
            FROM posts
            WHERE author_id = ?
        """, (user_id,))
        avg_engagement = cursor.fetchone()[0]
        
        # 关注列表
        cursor.execute("""
            SELECT followed_id, created_at
            FROM follows
            WHERE follower_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        following = [{'user_id': row[0], 'followed_at': row[1]} for row in cursor.fetchall()]
        
        # 粉丝列表
        cursor.execute("""
            SELECT follower_id, created_at
            FROM follows
            WHERE followed_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        followers = [{'user_id': row[0], 'followed_at': row[1]} for row in cursor.fetchall()]
        
        # 评论历史
        cursor.execute("""
            SELECT comment_id, post_id, content, created_at, num_likes
            FROM comments
            WHERE author_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        comments = []
        for row in cursor.fetchall():
            comments.append({
                'comment_id': row[0],
                'post_id': row[1],
                'content': row[2],
                'created_at': row[3],
                'num_likes': row[4]
            })
        
        # 发布的帖子
        cursor.execute("""
            SELECT post_id, content, created_at, num_likes, num_comments, num_shares
            FROM posts
            WHERE author_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        posts = []
        for row in cursor.fetchall():
            posts.append({
                'post_id': row[0],
                'content': row[1],
                'created_at': row[2],
                'num_likes': row[3],
                'num_comments': row[4],
                'num_shares': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'basic_info': {
                'user_id': user_row[0],
                'persona': user_row[1],
                'background_labels': user_row[2],
                'creation_time': user_row[3],
                'influence_score': user_row[8],
                'is_influencer': bool(user_row[9])
            },
            'activity_stats': {
                'post_count': post_count,
                'comment_count': comment_count,
                'follower_count': user_row[4],
                'likes_received': int(likes_received),
                'avg_engagement': round(float(avg_engagement), 2)
            },
            'following': following,
            'followers': followers,
            'comments': comments,
            'posts': posts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/<db_name>', methods=['GET'])
def get_posts(db_name):
    """获取帖子列表"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT post_id, author_id, content, created_at, 
                   num_likes, num_comments, num_shares,
                   (num_likes + num_comments + num_shares) as total_engagement
            FROM posts
            ORDER BY total_engagement DESC, created_at DESC
            LIMIT 100
        """)
        
        posts = []
        for row in cursor.fetchall():
            posts.append({
                'post_id': row[0],
                'author_id': row[1],
                'content': row[2],
                'created_at': row[3],
                'num_likes': row[4] or 0,
                'num_comments': row[5] or 0,
                'num_shares': row[6] or 0,
                'total_engagement': row[7] or 0
            })
        
        conn.close()
        return jsonify({'posts': posts})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/post/<db_name>/<post_id>', methods=['GET'])
def get_post_detail(db_name, post_id):
    """获取帖子详细信息"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 基本信息
        cursor.execute("""
            SELECT post_id, author_id, content, created_at,
                   num_likes, num_comments, num_shares, news_type
            FROM posts
            WHERE post_id = ?
        """, (post_id,))
        
        post_row = cursor.fetchone()
        if not post_row:
            conn.close()
            return jsonify({'error': 'Post not found'}), 404
        
        # 获取评论列表
        cursor.execute("""
            SELECT comment_id, author_id, content, created_at, num_likes
            FROM comments
            WHERE post_id = ?
            ORDER BY created_at DESC
        """, (post_id,))
        comments = []
        for row in cursor.fetchall():
            comments.append({
                'comment_id': row[0],
                'author_id': row[1],
                'content': row[2],
                'created_at': row[3],
                'num_likes': row[4]
            })
        
        # 获取点赞列表
        cursor.execute("""
            SELECT user_id, created_at
            FROM user_actions
            WHERE action_type IN ('like_post', 'like') AND target_id = ?
            ORDER BY created_at DESC
        """, (post_id,))
        likes = []
        for row in cursor.fetchall():
            likes.append({
                'user_id': row[0],
                'created_at': row[1]
            })
        
        # 获取分享列表
        cursor.execute("""
            SELECT user_id, created_at
            FROM user_actions
            WHERE action_type = 'share_post' AND target_id = ?
            ORDER BY created_at DESC
        """, (post_id,))
        shares = []
        for row in cursor.fetchall():
            shares.append({
                'user_id': row[0],
                'created_at': row[1]
            })
        
        conn.close()
        
        return jsonify({
            'basic_info': {
                'post_id': post_row[0],
                'author_id': post_row[1],
                'content': post_row[2],
                'created_at': post_row[3],
                'topic': post_row[7] or 'General'
            },
            'engagement_stats': {
                'num_likes': post_row[4] or 0,
                'num_comments': post_row[5] or 0,
                'num_shares': post_row[6] or 0,
                'total_engagement': (post_row[4] or 0) + (post_row[5] or 0) + (post_row[6] or 0)
            },
            'comments': comments,
            'likes': likes,
            'shares': shares
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting EvoCorps Frontend API Server...")
    print("Database directory:", os.path.abspath(DATABASE_DIR))
    app.run(host='127.0.0.1', port=5000, debug=True)
