#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend API Server for EvoCorps
提供前端所需的数据库查询接口
"""

import sys
import io
import datetime

# 设置标准输出为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import glob
import subprocess
import signal
import psutil
import json

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

@app.route('/api/services/status', methods=['GET'])
def get_services_status():
    """获取所有服务的状态"""
    try:
        status = {}
        scripts = {
            'database': 'start_database_service.py',
            'platform': 'main.py',
            'balance': 'opinion_balance_launcher.py'
        }
        
        for service_name, script_name in scripts.items():
            # 检查是否有运行该脚本的Python进程
            is_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any(script_name in str(cmd) for cmd in cmdline):
                        is_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            status[service_name] = 'running' if is_running else 'stopped'
        
        return jsonify({'services': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/cleanup', methods=['POST'])
def cleanup_services():
    """清理所有服务进程和端口占用"""
    try:
        cleaned = []
        
        # 清理所有服务脚本的进程
        scripts = {
            'database': 'start_database_service.py',
            'platform': 'main.py',
            'balance': 'opinion_balance_launcher.py'
        }
        
        for service_name, script_name in scripts.items():
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any(script_name in str(cmd) for cmd in cmdline):
                        parent = psutil.Process(proc.info['pid'])
                        for child in parent.children(recursive=True):
                            try:
                                child.kill()
                            except:
                                pass
                        parent.kill()
                        cleaned.append(f'{service_name} (PID: {proc.info["pid"]})')
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        # 清理端口5000（数据库服务）
        import time
        time.sleep(0.5)
        for conn in psutil.net_connections():
            try:
                if conn.laddr.port == 5000 and conn.status == 'LISTEN':
                    proc = psutil.Process(conn.pid)
                    proc.kill()
                    cleaned.append(f'Port 5000 (PID: {conn.pid})')
            except:
                pass
        
        return jsonify({
            'message': 'Cleanup completed',
            'cleaned': cleaned
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<service_name>/start', methods=['POST'])
def start_service(service_name):
    """启动服务"""
    try:
        if service_name not in ['database', 'platform', 'balance']:
            return jsonify({'error': 'Invalid service name'}), 400
        
        # 获取conda环境名称（如果提供）
        data = request.get_json() or {}
        conda_env = data.get('conda_env', '').strip()
        
        # 根据服务名称启动对应的脚本
        scripts = {
            'database': 'src/start_database_service.py',
            'platform': 'src/main.py',
            'balance': 'src/opinion_balance_launcher.py'
        }
        
        script_path = scripts[service_name]
        if not os.path.exists(script_path):
            return jsonify({'error': f'Script not found: {script_path}'}), 404
        
        # 检查是否已经在运行
        script_name = os.path.basename(script_path)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(script_name in str(cmd) for cmd in cmdline):
                    return jsonify({'error': 'Service already running'}), 400
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 如果是数据库服务，先清理端口5000
        if service_name == 'database':
            import time
            # 清理可能占用端口5000的进程
            for conn in psutil.net_connections():
                try:
                    if conn.laddr.port == 5000 and conn.status == 'LISTEN':
                        proc = psutil.Process(conn.pid)
                        proc.kill()
                        time.sleep(0.5)  # 等待端口释放
                except:
                    pass
        
        # 启动进程 - 在新的终端窗口中运行，使用/K保持窗口打开
        if os.name == 'nt':  # Windows
            title = f"EvoCorps-{service_name}"
            # 如果提供了conda环境，先激活环境
            if conda_env:
                # Windows上使用conda run命令，这是最可靠的方式
                # conda run会自动处理环境激活
                cmd = f'cmd /c start "{title}" cmd /k "conda run -n {conda_env} python {script_path}"'
            else:
                cmd = f'cmd /c start "{title}" cmd /k python {script_path}'
            subprocess.Popen(cmd, shell=True)
        else:  # Linux/Mac
            if conda_env:
                # Linux/Mac上使用conda run
                cmd = f'conda run -n {conda_env} python {script_path}'
                subprocess.Popen(cmd, shell=True, executable='/bin/bash')
            else:
                subprocess.Popen(['python', script_path])
        
        return jsonify({'message': f'Service {service_name} started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<service_name>/stop', methods=['POST'])
def stop_service(service_name):
    """停止服务"""
    try:
        if service_name not in ['database', 'platform', 'balance']:
            return jsonify({'error': 'Invalid service name'}), 400
        
        # 根据脚本名称查找并终止进程
        scripts = {
            'database': 'start_database_service.py',
            'platform': 'main.py',
            'balance': 'opinion_balance_launcher.py'
        }
        
        script_name = scripts[service_name]
        killed_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(script_name in str(cmd) for cmd in cmdline):
                    parent = psutil.Process(proc.info['pid'])
                    # 终止子进程
                    for child in parent.children(recursive=True):
                        try:
                            child.kill()  # 使用kill而不是terminate，更强制
                        except:
                            pass
                    # 终止主进程
                    try:
                        parent.kill()  # 使用kill而不是terminate
                    except:
                        pass
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        # 如果是数据库服务，额外检查并清理端口5000上的进程
        if service_name == 'database':
            import time
            time.sleep(1)  # 等待进程完全终止
            for conn in psutil.net_connections():
                if conn.laddr.port == 5000 and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        proc.kill()
                        killed_count += 1
                    except:
                        pass
        
        if killed_count == 0:
            return jsonify({'error': 'Service not running'}), 400
        
        return jsonify({'message': f'Service {service_name} stopped', 'killed_count': killed_count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiments', methods=['GET'])
def get_experiments():
    """获取所有已保存的实验"""
    try:
        experiments_dir = 'experiments'
        if not os.path.exists(experiments_dir):
            os.makedirs(experiments_dir)
            return jsonify({'experiments': []})
        
        experiments = []
        for exp_dir in os.listdir(experiments_dir):
            exp_path = os.path.join(experiments_dir, exp_dir)
            if os.path.isdir(exp_path):
                metadata_file = os.path.join(exp_path, 'metadata.json')
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        import json
                        metadata = json.load(f)
                        experiments.append(metadata)
        
        # 按时间戳降序排序
        experiments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({'experiments': experiments})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiments/save', methods=['POST'])
def save_experiment():
    """保存当前实验"""
    try:
        data = request.get_json()
        experiment_name = data.get('experiment_name', '')
        scenario_type = data.get('scenario_type', 'scenario_1')
        database_name = data.get('database_name', 'simulation.db')
        
        if not experiment_name:
            return jsonify({'error': 'Experiment name is required'}), 400
        
        # 创建实验目录
        import datetime
        import json
        import shutil
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        exp_id = f"experiment_{timestamp}"
        experiments_dir = 'experiments'
        exp_path = os.path.join(experiments_dir, exp_id)
        
        os.makedirs(exp_path, exist_ok=True)
        
        # 保存数据库快照
        db_source = os.path.join(DATABASE_DIR, database_name)
        if os.path.exists(db_source):
            db_dest = os.path.join(exp_path, 'database.db')
            shutil.copy2(db_source, db_dest)
            
            # 同时复制 WAL 和 SHM 文件
            for suffix in ['-wal', '-shm']:
                aux_file = db_source + suffix
                if os.path.exists(aux_file):
                    shutil.copy2(aux_file, os.path.join(exp_path, f'database.db{suffix}'))
        else:
            return jsonify({'error': f'Database not found: {database_name}'}), 404
        
        # 保存情绪数据（如果存在）
        emotion_dir = 'cognitive_memory'
        if os.path.exists(emotion_dir):
            emotion_dest = os.path.join(exp_path, 'cognitive_memory')
            os.makedirs(emotion_dest, exist_ok=True)
            for file in os.listdir(emotion_dir):
                if file.endswith('.json'):
                    shutil.copy2(os.path.join(emotion_dir, file), os.path.join(emotion_dest, file))
        
        # 保存元信息
        metadata = {
            'experiment_id': exp_id,
            'experiment_name': experiment_name,
            'scenario_type': scenario_type,
            'database_name': database_name,
            'timestamp': timestamp,
            'saved_at': datetime.datetime.now().isoformat(),
            'database_saved': os.path.exists(os.path.join(exp_path, 'database.db')),
            'emotion_data_saved': os.path.exists(os.path.join(exp_path, 'cognitive_memory'))
        }
        
        with open(os.path.join(exp_path, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'message': 'Experiment saved successfully',
            'experiment_id': exp_id,
            'metadata': metadata
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiments/<experiment_id>/load', methods=['POST'])
def load_experiment(experiment_id):
    """加载历史实验"""
    try:
        exp_path = os.path.join('experiments', experiment_id)
        
        if not os.path.exists(exp_path):
            return jsonify({'error': 'Experiment not found'}), 404
        
        # 读取元信息
        metadata_file = os.path.join(exp_path, 'metadata.json')
        if not os.path.exists(metadata_file):
            return jsonify({'error': 'Metadata not found'}), 404
        
        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 恢复数据库
        db_source = os.path.join(exp_path, 'database.db')
        if os.path.exists(db_source):
            import shutil
            # 备份当前数据库
            current_db = os.path.join(DATABASE_DIR, 'simulation.db')
            if os.path.exists(current_db):
                backup_name = f"simulation_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(current_db, os.path.join(DATABASE_DIR, backup_name))
            
            # 恢复实验数据库
            shutil.copy2(db_source, current_db)
            
            # 恢复 WAL 和 SHM 文件
            for suffix in ['-wal', '-shm']:
                aux_file = db_source + suffix
                if os.path.exists(aux_file):
                    shutil.copy2(aux_file, current_db + suffix)
        
        # 恢复情绪数据
        emotion_source = os.path.join(exp_path, 'cognitive_memory')
        if os.path.exists(emotion_source):
            import shutil
            emotion_dest = 'cognitive_memory'
            # 备份当前情绪数据
            if os.path.exists(emotion_dest):
                backup_name = f"cognitive_memory_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(emotion_dest, backup_name)
            
            # 清空并恢复
            if os.path.exists(emotion_dest):
                shutil.rmtree(emotion_dest)
            shutil.copytree(emotion_source, emotion_dest)
        
        return jsonify({
            'message': 'Experiment loaded successfully',
            'metadata': metadata
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/experiments/<experiment_id>', methods=['DELETE'])
def delete_experiment(experiment_id):
    """删除实验"""
    try:
        exp_path = os.path.join('experiments', experiment_id)
        
        if not os.path.exists(exp_path):
            return jsonify({'error': 'Experiment not found'}), 404
        
        import shutil
        shutil.rmtree(exp_path)
        
        return jsonify({'message': 'Experiment deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization/<db_name>/emotion', methods=['GET'])
def get_emotion_data(db_name):
    """获取情绪分析数据 - 每个时间步的情绪度"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否有情绪相关的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%emotion%'")
        emotion_tables = cursor.fetchall()
        
        # 如果有情绪表，从中获取数据
        if emotion_tables:
            # 假设有一个emotion_tracking表
            cursor.execute("""
                SELECT timestep, AVG(emotion_score) as avg_emotion
                FROM emotion_tracking
                GROUP BY timestep
                ORDER BY timestep
            """)
            emotion_data = [{'timestep': row[0], 'emotion': round(row[1], 2)} for row in cursor.fetchall()]
        else:
            # 如果没有情绪表，从用户行为推断情绪（基于互动频率）
            cursor.execute("""
                SELECT 
                    CAST((julianday(created_at) - julianday((SELECT MIN(created_at) FROM posts))) AS INTEGER) as timestep,
                    COUNT(*) as activity_count
                FROM posts
                GROUP BY timestep
                ORDER BY timestep
                LIMIT 50
            """)
            rows = cursor.fetchall()
            
            # 将活动数量归一化为情绪分数（0-100）
            if rows:
                max_activity = max(row[1] for row in rows)
                emotion_data = [
                    {
                        'timestep': row[0],
                        'emotion': round((row[1] / max_activity) * 100, 2) if max_activity > 0 else 50
                    }
                    for row in rows
                ]
            else:
                emotion_data = []
        
        conn.close()
        return jsonify({'emotion_data': emotion_data})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization/<db_name>/top-users', methods=['GET'])
def get_top_users(db_name):
    """获取Top10活跃用户"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 计算用户活跃度（发帖数 + 评论数 + 获赞数）
        cursor.execute("""
            SELECT 
                u.user_id,
                COALESCE(post_count, 0) as posts,
                COALESCE(comment_count, 0) as comments,
                COALESCE(u.total_likes_received, 0) as likes,
                (COALESCE(post_count, 0) + COALESCE(comment_count, 0) + COALESCE(u.total_likes_received, 0)) as total_activity
            FROM users u
            LEFT JOIN (
                SELECT author_id, COUNT(*) as post_count
                FROM posts
                GROUP BY author_id
            ) p ON u.user_id = p.author_id
            LEFT JOIN (
                SELECT author_id, COUNT(*) as comment_count
                FROM comments
                GROUP BY author_id
            ) c ON u.user_id = c.author_id
            ORDER BY total_activity DESC
            LIMIT 10
        """)
        
        top_users = []
        for row in cursor.fetchall():
            top_users.append({
                'user_id': row[0],
                'posts': row[1],
                'comments': row[2],
                'likes': row[3],
                'total_activity': row[4]
            })
        
        conn.close()
        return jsonify({'top_users': top_users})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization/<db_name>/network', methods=['GET'])
def get_network_data(db_name):
    """获取关系网络数据 - 知识图谱格式（所有用户、帖子、评论）"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        nodes = []
        edges = []
        
        # 1. 获取所有用户节点
        cursor.execute("""
            SELECT 
                u.user_id,
                u.follower_count,
                u.influence_score,
                u.creation_time,
                u.persona,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(c.comment_count, 0) as comment_count
            FROM users u
            LEFT JOIN (
                SELECT author_id, COUNT(*) as post_count
                FROM posts
                GROUP BY author_id
            ) p ON u.user_id = p.author_id
            LEFT JOIN (
                SELECT author_id, COUNT(*) as comment_count
                FROM comments
                GROUP BY author_id
            ) c ON u.user_id = c.author_id
            ORDER BY u.influence_score DESC
        """)
        
        user_ids = set()
        for row in cursor.fetchall():
            user_id = row[0]
            user_ids.add(user_id)
            
            # 解析persona获取角色信息
            persona_str = row[4] or '{}'
            try:
                import ast
                persona = ast.literal_eval(persona_str) if isinstance(persona_str, str) else {}
            except:
                persona = {}
            
            nodes.append({
                'id': user_id,
                'type': 'user',
                'name': user_id,
                'follower_count': row[1] or 0,
                'influence_score': row[2] or 0,
                'creation_time': row[3],
                'persona': persona,
                'post_count': row[5],
                'comment_count': row[6],
                'role': persona.get('personality_traits', {}).get('role', 'User') if isinstance(persona.get('personality_traits'), dict) else 'User'
            })
        
        # 2. 获取所有帖子
        cursor.execute("""
            SELECT 
                post_id,
                author_id,
                content,
                created_at,
                num_likes,
                num_comments,
                num_shares,
                news_type
            FROM posts
            ORDER BY (num_likes + num_comments + num_shares) DESC
        """)
        
        post_ids = set()
        for row in cursor.fetchall():
            post_id = row[0]
            author_id = row[1]
            post_ids.add(post_id)
            
            nodes.append({
                'id': post_id,
                'type': 'post',
                'name': post_id,
                'author_id': author_id,
                'content': (row[2] or '')[:100] + '...' if row[2] and len(row[2]) > 100 else (row[2] or ''),
                'created_at': row[3],
                'num_likes': row[4] or 0,
                'num_comments': row[5] or 0,
                'num_shares': row[6] or 0,
                'topic': row[7] or 'General'
            })
            
            # 添加用户->帖子的边（发布关系）
            if author_id in user_ids:
                edges.append({
                    'source': author_id,
                    'target': post_id,
                    'type': 'published',
                    'label': '发布'
                })
        
        # 3. 获取所有评论
        cursor.execute("""
            SELECT 
                comment_id,
                post_id,
                author_id,
                content,
                created_at,
                num_likes
            FROM comments
            ORDER BY num_likes DESC
        """)
        
        for row in cursor.fetchall():
            comment_id = row[0]
            post_id = row[1]
            author_id = row[2]
            
            nodes.append({
                'id': comment_id,
                'type': 'comment',
                'name': comment_id,
                'post_id': post_id,
                'author_id': author_id,
                'content': (row[3] or '')[:100] + '...' if row[3] and len(row[3]) > 100 else (row[3] or ''),
                'created_at': row[4],
                'num_likes': row[5] or 0
            })
            
            # 添加用户->评论的边
            if author_id in user_ids:
                edges.append({
                    'source': author_id,
                    'target': comment_id,
                    'type': 'commented',
                    'label': '评论'
                })
            
            # 添加评论->帖子的边
            if post_id in post_ids:
                edges.append({
                    'source': comment_id,
                    'target': post_id,
                    'type': 'comment_on',
                    'label': '评论于'
                })
        
        # 4. 获取所有关注关系
        cursor.execute("""
            SELECT follower_id, followed_id
            FROM follows
        """)
        
        for row in cursor.fetchall():
            if row[0] in user_ids and row[1] in user_ids:
                edges.append({
                    'source': row[0],
                    'target': row[1],
                    'type': 'follows',
                    'label': '关注'
                })
        
        # 5. 获取所有点赞关系（用户点赞帖子）
        cursor.execute("""
            SELECT user_id, target_id
            FROM user_actions
            WHERE action_type IN ('like_post', 'like')
        """)
        
        for row in cursor.fetchall():
            if row[0] in user_ids and row[1] in post_ids:
                edges.append({
                    'source': row[0],
                    'target': row[1],
                    'type': 'liked',
                    'label': '点赞'
                })
        
        # 6. 获取所有分享关系（用户分享帖子）
        cursor.execute("""
            SELECT user_id, target_id
            FROM user_actions
            WHERE action_type = 'share_post'
        """)
        
        for row in cursor.fetchall():
            if row[0] in user_ids and row[1] in post_ids:
                edges.append({
                    'source': row[0],
                    'target': row[1],
                    'type': 'shared',
                    'label': '分享'
                })
        
        # 计算统计信息
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
        total_users = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM comments")
        total_comments = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM follows")
        total_follows = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_users': total_users,
                'total_posts': total_posts,
                'total_comments': total_comments,
                'total_follows': total_follows,
                'displayed_nodes': len(nodes),
                'displayed_edges': len(edges)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization/<db_name>/opinion-balance', methods=['GET'])
def get_opinion_balance_data(db_name):
    """获取舆论平衡数据"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否有舆论平衡相关的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND (name LIKE '%opinion%' OR name LIKE '%intervention%')
        """)
        opinion_tables = [row[0] for row in cursor.fetchall()]
        
        result = {
            'has_data': len(opinion_tables) > 0,
            'tables': opinion_tables,
            'monitoring_stats': {},
            'intervention_stats': {},
            'timeline': []
        }
        
        if 'opinion_monitoring' in opinion_tables:
            # 监控统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_monitored,
                    SUM(CASE WHEN requires_intervention = 1 THEN 1 ELSE 0 END) as intervention_needed
                FROM opinion_monitoring
            """)
            row = cursor.fetchone()
            result['monitoring_stats'] = {
                'total_monitored': row[0] or 0,
                'intervention_needed': row[1] or 0,
                'intervention_rate': round((row[1] or 0) / max(row[0] or 1, 1) * 100, 1)
            }
        
        if 'opinion_interventions' in opinion_tables:
            # 干预统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_interventions,
                    AVG(effectiveness_score) as avg_effectiveness
                FROM opinion_interventions
            """)
            row = cursor.fetchone()
            result['intervention_stats'] = {
                'total_interventions': row[0] or 0,
                'avg_effectiveness': round(row[1] or 0, 2)
            }
            
            # 时间线数据
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as intervention_count
                FROM opinion_interventions
                GROUP BY date
                ORDER BY date
                LIMIT 30
            """)
            result['timeline'] = [
                {'date': row[0], 'interventions': row[1]}
                for row in cursor.fetchall()
            ]
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/experiment', methods=['GET'])
def get_experiment_config():
    """获取实验配置"""
    try:
        config_path = 'configs/experiment_config.json'
        if not os.path.exists(config_path):
            return jsonify({'error': 'Config file not found'}), 404
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return jsonify(config)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/experiment', methods=['POST'])
def save_experiment_config():
    """保存实验配置"""
    try:
        config_path = 'configs/experiment_config.json'
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 备份原配置
        if os.path.exists(config_path):
            import shutil
            backup_path = config_path + '.backup'
            shutil.copy(config_path, backup_path)
        
        # 保存新配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return jsonify({'message': 'Config saved successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting EvoCorps Frontend API Server...")
    print("Database directory:", os.path.abspath(DATABASE_DIR))
    app.run(host='127.0.0.1', port=5001, debug=True)
