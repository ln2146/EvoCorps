#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend API Server for EvoCorps
提供前端所需的数据库查询接口
"""

import sys
import io
import datetime
from typing import Optional, List, Dict

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
import time

# 添加src目录到路径以导入项目模块
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 尝试导入AI模型相关模块
AI_AVAILABLE = False
try:
    from multi_model_selector import multi_model_selector
    from utils import Utils
    AI_AVAILABLE = True
    print("✅ AI模型模块加载成功")
except ImportError as e:
    print(f"⚠️ AI模型模块加载失败: {e}")
    print("⚠️ 采访功能将使用简化的模板回答")
    print("💡 提示：请确保已安装所有依赖: pip install -r requirements.txt")

app = Flask(__name__)
CORS(app)

DATABASE_DIR = 'database'
OPINION_BALANCE_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs', 'opinion_balance')
WORKFLOW_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs', 'workflow')


class ProcessManager:
    """管理演示系统的所有进程"""
    
    def __init__(self):
        """初始化 ProcessManager
        
        初始化进程字典、临时文件列表和 Python 解释器路径
        """
        self.processes = {
            'database': None,      # 存储进程 PID
            'main': None,
            'opinion_balance': None
        }
        self.temp_files = []       # 临时文件列表，用于清理
        self.python_exe = sys.executable  # 当前 Python 解释器路径
        
        # 启动时清理所有旧的临时文件
        self._cleanup_all_temp_files()
    
    def _is_process_running(self, process_name: str) -> bool:
        """检查进程是否运行（内部方法）
        
        Args:
            process_name: 进程名称 ('database', 'main', 'opinion_balance')
            
        Returns:
            bool: 进程是否正在运行
        """
        # 如果有记录的进程 PID
        if self.processes.get(process_name):
            pid = self.processes[process_name]
            try:
                proc = psutil.Process(pid)
                # 检查进程是否存活且命令行匹配
                if proc.is_running():
                    cmdline = ' '.join(proc.cmdline())
                    # 根据不同进程检查不同的关键字
                    keywords = {
                        'database': 'start_database_service.py',
                        'main': 'main.py',
                        'opinion_balance': 'opinion_balance_launcher.py'
                    }
                    if keywords[process_name] in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 如果没有记录，扫描所有进程
        keywords = {
            'database': 'start_database_service.py',
            'main': 'main.py',
            'opinion_balance': 'opinion_balance_launcher.py'
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(keywords[process_name] in str(cmd) for cmd in cmdline):
                    self.processes[process_name] = proc.info['pid']
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return False
    
    def _create_auto_input_script(
        self, 
        script_path: str, 
        inputs: List[str],
        conda_env: Optional[str] = None
    ) -> str:
        """创建自动输入的批处理脚本（内部方法）
        
        Args:
            script_path: 要运行的 Python 脚本路径
            inputs: 输入序列列表
            conda_env: conda 环境名称（已废弃，保留兼容性）
            
        Returns:
            str: 批处理文件路径
        """
        # 生成唯一的临时批处理文件名
        timestamp = int(time.time())
        bat_file = f"temp_input_{timestamp}.bat"
        
        with open(bat_file, 'w', encoding='utf-8') as f:
            # 不需要激活 conda 环境，直接使用当前 Python 解释器
            # 使用 sys.executable 确保使用当前 Python 解释器
            
            # 写入自动输入命令
            f.write('@echo off\n')
            f.write('(\n')
            for inp in inputs:
                if inp == '':  # 空字符串表示回车
                    f.write('echo.\n')
                else:
                    f.write(f'echo {inp}\n')
            f.write(f') | "{self.python_exe}" {script_path}\n')
            # 添加 exit 命令，确保批处理执行完毕后立即退出，不显示任何提示
            f.write('exit\n')
        
        # 记录临时文件路径用于后续清理
        self.temp_files.append(bat_file)
        return bat_file
    
    def _start_process_in_terminal(
        self, 
        script_path: str, 
        title: str,
        auto_inputs: Optional[List[str]] = None,
        conda_env: Optional[str] = None
    ) -> subprocess.Popen:
        """在新终端启动进程（内部方法）
        
        Args:
            script_path: 要运行的 Python 脚本路径
            title: 终端窗口标题
            auto_inputs: 自动输入序列（可选）
            conda_env: conda 环境名称（已废弃，保留兼容性）
            
        Returns:
            subprocess.Popen: 进程对象
        """
        if auto_inputs:
            # 创建临时批处理文件（包含 exit 命令）
            bat_file = self._create_auto_input_script(script_path, auto_inputs, conda_env)
            # 直接启动批处理文件
            cmd = f'cmd /c start "{title}" cmd /c "{bat_file}"'
        else:
            # 直接启动，使用当前 Python 解释器
            cmd = f'cmd /c start "{title}" cmd /c ""{self.python_exe}" {script_path} & exit"'
        
        process = subprocess.Popen(cmd, shell=True)
        return process
    
    def _cleanup_temp_files(self):
        """清理记录的临时文件（内部方法）"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except (FileNotFoundError, PermissionError) as e:
                # 记录错误但不中断清理过程
                print(f"警告: 无法删除临时文件 {temp_file}: {e}")
        
        # 清空临时文件列表
        self.temp_files = []
    
    def _cleanup_all_temp_files(self):
        """清理所有临时批处理文件（内部方法）
        
        扫描当前目录，删除所有 temp_input_*.bat 文件
        """
        try:
            import glob
            # 查找所有匹配的临时文件
            temp_files = glob.glob('temp_input_*.bat')
            
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    print(f"已清理临时文件: {temp_file}")
                except (FileNotFoundError, PermissionError) as e:
                    # 文件可能正在使用或已被删除
                    pass
        except Exception as e:
            # 清理失败不应影响程序运行
            print(f"清理临时文件时出错: {e}")
    
    def start_demo(self, conda_env: Optional[str] = None) -> dict:
        """启动演示（数据库 + 主程序）
        
        注意: conda_env 参数已废弃，系统自动使用当前 Python 环境
        
        Args:
            conda_env: conda 环境名称（已废弃，保留兼容性）
            
        Returns:
            dict: 启动结果
        """
        try:
            # 清理旧的临时文件
            self._cleanup_all_temp_files()
            
            # 检查数据库和主程序是否已运行
            if self._is_process_running('database'):
                return {
                    'success': False,
                    'message': 'Database service is already running',
                    'error': 'ProcessAlreadyRunning'
                }
            
            if self._is_process_running('main'):
                return {
                    'success': False,
                    'message': 'Main program is already running',
                    'error': 'ProcessAlreadyRunning'
                }
            
            # 启动数据库服务
            db_script = 'src/start_database_service.py'
            if not os.path.exists(db_script):
                return {
                    'success': False,
                    'message': f'Database script not found: {db_script}',
                    'error': 'FileNotFound'
                }
            
            db_process = self._start_process_in_terminal(
                script_path=db_script,
                title='EvoCorps-Database',
                auto_inputs=None,
                conda_env=conda_env
            )
            
            # 记录数据库进程（注意：由于是在新终端启动，我们无法直接获取子进程的 PID）
            # 我们需要等待进程启动后通过 _is_process_running 来获取 PID
            time.sleep(2)  # 等待进程启动
            
            # 尝试获取数据库进程 PID
            db_pid = None
            if self._is_process_running('database'):
                db_pid = self.processes.get('database')
            
            # 等待 5 秒让数据库初始化
            print("等待数据库服务初始化...")
            time.sleep(5)
            
            # 创建自动输入脚本并启动主程序
            main_script = 'src/main.py'
            if not os.path.exists(main_script):
                return {
                    'success': False,
                    'message': f'Main script not found: {main_script}',
                    'error': 'FileNotFound'
                }
            
            # 输入序列：n, y, n, n, Enter
            auto_inputs = ['n', 'y', 'n', 'n', '']
            
            main_process = self._start_process_in_terminal(
                script_path=main_script,
                title='EvoCorps-Main',
                auto_inputs=auto_inputs,
                conda_env=conda_env
            )
            
            # 等待主程序启动
            time.sleep(2)
            
            # 尝试获取主程序进程 PID
            main_pid = None
            if self._is_process_running('main'):
                main_pid = self.processes.get('main')
            
            return {
                'success': True,
                'message': 'Dynamic demo started successfully',
                'processes': {
                    'database': {
                        'pid': db_pid,
                        'status': 'running' if db_pid else 'starting'
                    },
                    'main': {
                        'pid': main_pid,
                        'status': 'running' if main_pid else 'starting'
                    }
                }
            }
            
        except FileNotFoundError as e:
            return {
                'success': False,
                'message': f'Script not found: {str(e)}',
                'error': 'FileNotFound'
            }
        except PermissionError as e:
            return {
                'success': False,
                'message': f'Permission denied: {str(e)}',
                'error': 'PermissionDenied'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to start demo: {str(e)}',
                'error': 'ProcessStartFailed'
            }
    
    def stop_all_processes(self) -> dict:
        """停止所有进程
        
        遍历所有已记录的进程，使用 psutil.Process.terminate() 优雅关闭，
        等待 3 秒后检查进程是否终止，对未终止的进程使用 kill() 强制关闭。
        清理所有临时文件，重置进程记录字典。
        
        Returns:
            dict: 停止结果（包含已停止进程列表和错误信息）
        """
        stopped = []
        errors = []
        
        for name, pid in self.processes.items():
            if pid is None:
                continue
                
            try:
                proc = psutil.Process(pid)
                
                # 获取父进程（通常是 cmd.exe）
                try:
                    parent = proc.parent()
                    parent_pid = parent.pid if parent else None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    parent_pid = None
                
                # 1. 尝试优雅关闭 Python 进程
                proc.terminate()
                
                # 2. 等待最多 3 秒
                try:
                    proc.wait(timeout=3)
                    stopped.append(name)
                except psutil.TimeoutExpired:
                    # 3. 强制关闭 Python 进程
                    proc.kill()
                    proc.wait(timeout=1)
                    stopped.append(name)
                
                # 4. 如果有父进程（cmd.exe），也关闭它以关闭终端窗口
                if parent_pid:
                    try:
                        parent_proc = psutil.Process(parent_pid)
                        # 检查父进程是否是 cmd.exe
                        if 'cmd.exe' in parent_proc.name().lower():
                            parent_proc.terminate()
                            try:
                                parent_proc.wait(timeout=2)
                            except psutil.TimeoutExpired:
                                parent_proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass  # 父进程可能已经关闭
                    
            except psutil.NoSuchProcess:
                # 进程已经不存在
                stopped.append(name)
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        # 清理临时文件
        self._cleanup_temp_files()
        self._cleanup_all_temp_files()  # 额外清理所有临时文件
        
        # 重置进程记录
        self.processes = {k: None for k in self.processes}
        
        return {
            'success': len(errors) == 0,
            'message': 'All processes stopped' if not errors else 'Some processes failed to stop',
            'stopped_processes': stopped,
            'errors': errors
        }
    
    def start_opinion_balance(self, conda_env: Optional[str] = None) -> dict:
        """启动舆论平衡系统
        
        注意: conda_env 参数已废弃，系统自动使用当前 Python 环境
        
        Args:
            conda_env: conda 环境名称（已废弃，保留兼容性）
            
        Returns:
            dict: 启动结果
        """
        try:
            # 清理旧的临时文件
            self._cleanup_all_temp_files()
            
            # 检查舆论平衡进程是否已运行
            if self._is_process_running('opinion_balance'):
                return {
                    'success': False,
                    'message': 'Opinion balance system is already running',
                    'error': 'ProcessAlreadyRunning'
                }
            
            # 启动舆论平衡启动器
            ob_script = 'src/opinion_balance_launcher.py'
            if not os.path.exists(ob_script):
                return {
                    'success': False,
                    'message': f'Opinion balance script not found: {ob_script}',
                    'error': 'FileNotFound'
                }
            
            # 创建自动输入脚本（输入序列：start, auto-status）
            auto_inputs = ['start', 'auto-status']
            
            ob_process = self._start_process_in_terminal(
                script_path=ob_script,
                title='EvoCorps-OpinionBalance',
                auto_inputs=auto_inputs,
                conda_env=conda_env
            )
            
            # 等待进程启动
            time.sleep(2)
            
            # 尝试获取进程 PID
            ob_pid = None
            if self._is_process_running('opinion_balance'):
                ob_pid = self.processes.get('opinion_balance')
            
            return {
                'success': True,
                'message': 'Opinion balance system started',
                'process': {
                    'pid': ob_pid,
                    'status': 'running' if ob_pid else 'starting'
                }
            }
            
        except FileNotFoundError as e:
            return {
                'success': False,
                'message': f'Script not found: {str(e)}',
                'error': 'FileNotFound'
            }
        except PermissionError as e:
            return {
                'success': False,
                'message': f'Permission denied: {str(e)}',
                'error': 'PermissionDenied'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to start opinion balance: {str(e)}',
                'error': 'ProcessStartFailed'
            }
    
    def stop_process(self, process_name: str) -> dict:
        """停止单个进程
        
        Args:
            process_name: 进程名称 ('database', 'main', 'opinion_balance')
            
        Returns:
            dict: 停止结果
        """
        if process_name not in self.processes:
            return {
                'success': False,
                'message': f'Unknown process name: {process_name}',
                'error': 'InvalidProcessName'
            }
        
        pid = self.processes.get(process_name)
        
        if pid is None:
            return {
                'success': False,
                'message': f'{process_name} is not running',
                'error': 'ProcessNotRunning'
            }
        
        try:
            proc = psutil.Process(pid)
            
            # 获取父进程（通常是 cmd.exe）
            try:
                parent = proc.parent()
                parent_pid = parent.pid if parent else None
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                parent_pid = None
            
            # 1. 尝试优雅关闭 Python 进程
            proc.terminate()
            
            # 2. 等待最多 3 秒
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                # 3. 强制关闭 Python 进程
                proc.kill()
                proc.wait(timeout=1)
            
            # 4. 如果有父进程（cmd.exe），也关闭它以关闭终端窗口
            if parent_pid:
                try:
                    parent_proc = psutil.Process(parent_pid)
                    # 检查父进程是否是 cmd.exe
                    if 'cmd.exe' in parent_proc.name().lower():
                        parent_proc.terminate()
                        try:
                            parent_proc.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            parent_proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # 父进程可能已经关闭
            
            # 重置该进程记录
            self.processes[process_name] = None
            
            return {
                'success': True,
                'message': f'{process_name} stopped successfully',
                'process': process_name
            }
            
        except psutil.NoSuchProcess:
            # 进程已经不存在
            self.processes[process_name] = None
            return {
                'success': True,
                'message': f'{process_name} was already stopped',
                'process': process_name
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to stop {process_name}: {str(e)}',
                'error': 'ProcessStopFailed'
            }
    
    def get_process_status(self) -> dict:
        """获取所有进程状态
        
        遍历所有进程记录，使用 _is_process_running 检查每个进程状态，
        计算进程运行时间（如果可能）。
        
        Returns:
            dict: 所有进程的状态信息（running/stopped, PID, uptime）
        """
        status = {}
        
        for name in self.processes.keys():
            # 使用 _is_process_running 检查进程状态
            is_running = self._is_process_running(name)
            pid = self.processes.get(name)
            
            if is_running and pid:
                try:
                    proc = psutil.Process(pid)
                    # 计算进程运行时间（秒）
                    create_time = proc.create_time()
                    uptime = int(time.time() - create_time)
                    
                    status[name] = {
                        'status': 'running',
                        'pid': pid,
                        'uptime': uptime
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # 进程不存在或无法访问
                    status[name] = {
                        'status': 'stopped',
                        'pid': None,
                        'uptime': 0
                    }
            else:
                status[name] = {
                    'status': 'stopped',
                    'pid': None,
                    'uptime': 0
                }
        
        return status


# 创建全局 ProcessManager 实例
process_manager = ProcessManager()


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
        
        # 启动进程 - 在新的终端窗口中运行
        if os.name == 'nt':  # Windows
            title = f"EvoCorps-{service_name}"
            
            if conda_env:
                # Windows上，创建一个临时批处理文件来执行命令
                # 这样可以确保命令按顺序执行
                import tempfile
                
                # 创建临时批处理文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as f:
                    batch_file = f.name
                    f.write('@echo off\n')
                    f.write(f'echo Activating conda environment: {conda_env}\n')
                    f.write(f'call conda activate {conda_env}\n')
                    f.write('if errorlevel 1 (\n')
                    f.write(f'    echo Failed to activate conda environment: {conda_env}\n')
                    f.write('    echo Please check if the environment exists: conda env list\n')
                    f.write('    pause\n')
                    f.write('    exit /b 1\n')
                    f.write(')\n')
                    f.write(f'echo Running: python {script_path}\n')
                    f.write(f'python {script_path}\n')
                    f.write('pause\n')
                
                # 启动新终端运行批处理文件
                cmd = f'cmd /c start "{title}" cmd /k "{batch_file}"'
            else:
                # 没有conda环境，直接运行
                cmd = f'cmd /c start "{title}" cmd /k "python {script_path}"'
            
            subprocess.Popen(cmd, shell=True)
        else:  # Linux/Mac
            if conda_env:
                # Linux/Mac上先激活环境再运行
                cmd = f'bash -c "source $(conda info --base)/etc/profile.d/conda.sh && conda activate {conda_env} && python {script_path}"'
                subprocess.Popen(cmd, shell=True)
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
                # 尝试JSON解析
                persona = json.loads(persona_str) if isinstance(persona_str, str) else {}
            except:
                try:
                    # 如果JSON失败，尝试ast.literal_eval
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
                'content': row[2] or '',
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
                'content': row[3] or '',
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
    """保存实验配置 - 只修改数值，完全保持原格式"""
    try:
        config_path = 'configs/experiment_config.json'
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 读取原文件内容（文本形式）
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 读取原配置（JSON形式）
        original_config = json.loads(content)
        
        # 只替换修改的字段值，使用正则表达式精确替换
        import re
        
        # 处理 num_users
        if 'num_users' in data and data['num_users'] != original_config.get('num_users'):
            pattern = r'("num_users":\s*)(\d+)'
            content = re.sub(pattern, r'\g<1>' + str(data['num_users']), content)
        
        # 处理 num_time_steps
        if 'num_time_steps' in data and data['num_time_steps'] != original_config.get('num_time_steps'):
            pattern = r'("num_time_steps":\s*)(\d+)'
            content = re.sub(pattern, r'\g<1>' + str(data['num_time_steps']), content)
        
        # 处理 engine
        if 'engine' in data and data['engine'] != original_config.get('engine'):
            pattern = r'("engine":\s*)"([^"]*)"'
            content = re.sub(pattern, r'\g<1>"' + data['engine'] + '"', content)
        
        # 处理 temperature
        if 'temperature' in data and data['temperature'] != original_config.get('temperature'):
            pattern = r'("temperature":\s*)(\d+\.?\d*)'
            content = re.sub(pattern, r'\g<1>' + str(data['temperature']), content)
        
        # 处理 reset_db
        if 'reset_db' in data and data['reset_db'] != original_config.get('reset_db'):
            pattern = r'("reset_db":\s*)(true|false)'
            content = re.sub(pattern, r'\g<1>' + ('true' if data['reset_db'] else 'false'), content)
        
        # 保存修改后的内容
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'message': 'Config saved successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/interview/send', methods=['POST'])
def send_interview():
    """向选中的用户发送采访问题并获取回答"""
    try:
        data = request.get_json()
        database = data.get('database')
        user_ids = data.get('user_ids', [])
        question = data.get('question', '')
        
        if not database or not user_ids or not question:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        db_path = os.path.join(DATABASE_DIR, database)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        responses = []
        
        for user_id in user_ids:
            # 获取用户信息
            cursor.execute("""
                SELECT user_id, persona, background_labels
                FROM users
                WHERE user_id = ?
            """, (user_id,))
            
            user_row = cursor.fetchone()
            if not user_row:
                continue
            
            user_persona = user_row[1]
            background = user_row[2] if user_row[2] else ''
            
            # 根据用户的persona和实际行为生成回答
            answer = generate_interview_answer(user_persona, background, question, user_id, db_path)
            
            responses.append({
                'user_id': user_id,
                'question': question,
                'answer': answer,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        
        return jsonify({
            'message': 'Interview sent successfully',
            'responses': responses
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/interview/send-stream', methods=['POST'])
def send_interview_stream():
    """流式发送采访问题并获取回答"""
    from flask import Response, stream_with_context
    
    data = request.get_json()
    database = data.get('database')
    user_ids = data.get('user_ids', [])
    question = data.get('question', '')
    
    if not database or not user_ids or not question:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    db_path = os.path.join(DATABASE_DIR, database)
    if not os.path.exists(db_path):
        return jsonify({'error': 'Database not found'}), 404
    
    def generate():
        """生成器函数，逐个用户流式返回回答"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            for user_id in user_ids:
                # 获取用户信息
                cursor.execute("""
                    SELECT user_id, persona, background_labels
                    FROM users
                    WHERE user_id = ?
                """, (user_id,))
                
                user_row = cursor.fetchone()
                if not user_row:
                    continue
                
                user_persona = user_row[1]
                background = user_row[2] if user_row[2] else ''
                
                # 发送开始标记
                yield f"data: {json.dumps({'type': 'start', 'user_id': user_id}, ensure_ascii=False)}\n\n"
                
                # 流式生成回答
                for chunk in generate_interview_answer_stream(user_persona, background, question, user_id, db_path):
                    yield f"data: {json.dumps({'type': 'chunk', 'user_id': user_id, 'content': chunk}, ensure_ascii=False)}\n\n"
                
                # 发送完成标记
                yield f"data: {json.dumps({'type': 'done', 'user_id': user_id, 'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, ensure_ascii=False)}\n\n"
            
            # 所有用户完成
            yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            conn.close()
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


def generate_interview_answer_stream(persona, background, question, user_id, db_path):
    """流式生成采访回答"""
    import json
    
    # 如果AI不可用，返回模板回答
    if not AI_AVAILABLE:
        # 获取用户数据
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content, num_likes, num_comments FROM posts WHERE author_id = ? LIMIT 5", (user_id,))
        user_posts = cursor.fetchall()
        cursor.execute("SELECT content FROM comments WHERE author_id = ? LIMIT 5", (user_id,))
        user_comments = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND action_type IN ('like_post', 'like')", (user_id,))
        like_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,))
        following_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,))
        follower_count = cursor.fetchone()[0]
        conn.close()
        
        # 解析persona
        persona_info = {}
        try:
            if isinstance(persona, str):
                try:
                    persona_info = json.loads(persona)
                except:
                    fixed_str = persona.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
                    persona_info = json.loads(fixed_str)
            else:
                persona_info = persona
        except:
            persona_info = {'description': str(persona)}
        
        # 生成模板回答并逐字返回
        answer = generate_template_answer(persona_info, user_posts, user_comments, like_count, following_count, follower_count, question)
        
        # 模拟流式输出，每次返回几个字
        import time
        for i in range(0, len(answer), 3):
            chunk = answer[i:i+3]
            yield chunk
            time.sleep(0.05)  # 模拟打字效果
        return
    
    # 使用AI流式生成
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取用户行为数据
    cursor.execute("SELECT content, num_likes, num_comments FROM posts WHERE author_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
    user_posts = cursor.fetchall()
    cursor.execute("SELECT content FROM comments WHERE author_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
    user_comments = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND action_type IN ('like_post', 'like')", (user_id,))
    like_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id,))
    following_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user_id,))
    follower_count = cursor.fetchone()[0]
    conn.close()
    
    # 解析persona
    persona_info = {}
    try:
        if isinstance(persona, str):
            try:
                persona_info = json.loads(persona)
            except:
                fixed_str = persona.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
                persona_info = json.loads(fixed_str)
        else:
            persona_info = persona
    except:
        persona_info = {'description': str(persona)}
    
    # 构建用户行为摘要
    behavior_summary = f"""
用户行为统计：
- 发帖数：{len(user_posts)}篇
- 评论数：{len(user_comments)}条
- 点赞数：{like_count}次
- 关注数：{following_count}人
- 粉丝数：{follower_count}人
"""
    
    if user_posts:
        behavior_summary += "\n最近发布的帖子：\n"
        for i, post in enumerate(user_posts[:3], 1):
            content = post[0][:100] + "..." if len(post[0]) > 100 else post[0]
            behavior_summary += f"{i}. {content} (获得{post[1]}个赞，{post[2]}条评论)\n"
    
    if user_comments:
        behavior_summary += "\n最近的评论：\n"
        for i, comment in enumerate(user_comments[:3], 1):
            content = comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0]
            behavior_summary += f"{i}. {content}\n"
    
    # 构建提示词
    system_prompt = """你是一个社交媒体平台的用户，正在接受采访。请根据你的个人背景、性格特征和在平台上的实际行为来回答问题。

要求：
1. 回答要自然、真实，符合你的人设和行为模式
2. 结合你在平台上的实际活动（发帖、评论、点赞等）来回答
3. 回答长度控制在100-200字之间
4. 用第一人称回答，展现个性化的语言风格
5. 如果问题与你的行为相关，要引用具体的数据或例子
6. 保持回答的多样性，避免千篇一律"""
    
    user_prompt = f"""我的个人信息：
{json.dumps(persona_info, ensure_ascii=False, indent=2)}

{behavior_summary}

现在请回答这个问题：{question}

请以第一人称回答，结合我的背景和在平台上的实际行为。"""
    
    try:
        # 使用流式API
        openai_client, selected_model = multi_model_selector.create_openai_client(role="interview")
        
        stream = openai_client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=300,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        print(f"⚠️ AI流式生成失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 回退到模板回答
        answer = generate_template_answer(persona_info, user_posts, user_comments, like_count, following_count, follower_count, question)
        import time
        for i in range(0, len(answer), 3):
            chunk = answer[i:i+3]
            yield chunk
            time.sleep(0.05)

def generate_interview_answer(persona, background, question, user_id, db_path):
    """使用AI模型根据用户persona和实际行为生成采访回答"""
    import json
    
    # 连接数据库获取用户行为数据
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取用户的发帖数据
    cursor.execute("""
        SELECT content, num_likes, num_comments, created_at
        FROM posts
        WHERE author_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (user_id,))
    user_posts = cursor.fetchall()
    
    # 获取用户的评论数据
    cursor.execute("""
        SELECT content, created_at
        FROM comments
        WHERE author_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (user_id,))
    user_comments = cursor.fetchall()
    
    # 获取用户点赞的帖子
    cursor.execute("""
        SELECT COUNT(*) FROM user_actions
        WHERE user_id = ? AND action_type IN ('like_post', 'like')
    """, (user_id,))
    like_count = cursor.fetchone()[0]
    
    # 获取用户关注的人数
    cursor.execute("""
        SELECT COUNT(*) FROM follows
        WHERE follower_id = ?
    """, (user_id,))
    following_count = cursor.fetchone()[0]
    
    # 获取用户被关注的人数
    cursor.execute("""
        SELECT COUNT(*) FROM follows
        WHERE followed_id = ?
    """, (user_id,))
    follower_count = cursor.fetchone()[0]
    
    conn.close()
    
    # 解析persona（如果是JSON格式）
    persona_info = {}
    try:
        if isinstance(persona, str):
            try:
                persona_info = json.loads(persona)
            except:
                fixed_str = persona.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
                persona_info = json.loads(fixed_str)
        else:
            persona_info = persona
    except:
        persona_info = {'description': str(persona)}
    
    # 如果AI模块不可用，使用改进的模板回答
    if not AI_AVAILABLE:
        return generate_template_answer(persona_info, user_posts, user_comments, like_count, following_count, follower_count, question)
    
    # 构建用户行为摘要
    behavior_summary = f"""
用户行为统计：
- 发帖数：{len(user_posts)}篇
- 评论数：{len(user_comments)}条
- 点赞数：{like_count}次
- 关注数：{following_count}人
- 粉丝数：{follower_count}人
"""
    
    # 添加最近的帖子内容
    if user_posts:
        behavior_summary += "\n最近发布的帖子：\n"
        for i, post in enumerate(user_posts[:3], 1):
            content = post[0][:100] + "..." if len(post[0]) > 100 else post[0]
            behavior_summary += f"{i}. {content} (获得{post[1]}个赞，{post[2]}条评论)\n"
    
    # 添加最近的评论内容
    if user_comments:
        behavior_summary += "\n最近的评论：\n"
        for i, comment in enumerate(user_comments[:3], 1):
            content = comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0]
            behavior_summary += f"{i}. {content}\n"
    
    # 构建AI提示词
    system_prompt = """你是一个社交媒体平台的用户，正在接受采访。请根据你的个人背景、性格特征和在平台上的实际行为来回答问题。

要求：
1. 回答要自然、真实，符合你的人设和行为模式
2. 结合你在平台上的实际活动（发帖、评论、点赞等）来回答
3. 回答长度控制在100-200字之间
4. 用第一人称回答，展现个性化的语言风格
5. 如果问题与你的行为相关，要引用具体的数据或例子
6. 保持回答的多样性，避免千篇一律"""
    
    user_prompt = f"""我的个人信息：
{json.dumps(persona_info, ensure_ascii=False, indent=2)}

{behavior_summary}

现在请回答这个问题：{question}

请以第一人称回答，结合我的背景和在平台上的实际行为。"""
    
    try:
        # 使用项目的多模型选择器创建客户端
        openai_client, selected_model = multi_model_selector.create_openai_client(role="interview")
        
        # 调用AI模型生成回答
        answer = Utils.generate_llm_response(
            openai_client=openai_client,
            engine=selected_model,
            prompt=user_prompt,
            system_message=system_prompt,
            temperature=0.8,  # 较高的温度以获得更多样化的回答
            max_tokens=300
        )
        
        return answer
        
    except Exception as e:
        # 如果AI调用失败，返回模板回答
        print(f"⚠️ AI生成回答失败: {e}")
        import traceback
        traceback.print_exc()
        
        return generate_template_answer(persona_info, user_posts, user_comments, like_count, following_count, follower_count, question)


def generate_template_answer(persona_info, user_posts, user_comments, like_count, following_count, follower_count, question):
    """生成基于模板的回答（当AI不可用时使用）"""
    question_lower = question.lower()
    
    # 获取用户基本信息
    name = persona_info.get('name', '用户')
    profession = persona_info.get('profession', '普通用户')
    background = persona_info.get('background', '各种话题')
    
    # 计算活跃度
    total_activity = len(user_posts) + len(user_comments)
    activity_level = "非常活跃" if total_activity > 10 else "活跃" if total_activity > 5 else "新手"
    
    # 根据问题类型生成回答
    if any(keyword in question_lower for keyword in ['发帖', '发布', '内容', '分享', '帖子', '发表']):
        if user_posts:
            avg_likes = sum(p[1] or 0 for p in user_posts) / len(user_posts)
            return f"我在平台上发布了{len(user_posts)}篇内容，平均每篇获得{avg_likes:.1f}个点赞。作为{profession}，我主要分享关于{background}的内容。我觉得通过发帖可以和大家交流想法，也能获得不同的观点。"
        else:
            return f"我目前还没有发布过内容，主要是在观察和学习。作为{name}，我更倾向于先了解平台氛围再参与。不过我对{background}相关的话题很感兴趣。"
    
    elif any(keyword in question_lower for keyword in ['互动', '评论', '交流', '讨论', '参与']):
        if user_comments:
            return f"我比较{activity_level}，发表过{len(user_comments)}条评论。我喜欢与他人真诚地交流想法。作为{profession}，我认为良好的互动能促进相互理解，也能让我学到新东西。"
        else:
            return f"我目前主要是浏览内容，还没有太多评论。不过我会在合适的时候参与讨论，特别是关于{background}的话题。"
    
    elif any(keyword in question_lower for keyword in ['喜欢', '偏好', '点赞', '关注', '兴趣']):
        if like_count > 0:
            return f"我点赞了{like_count}个内容，关注了{following_count}个用户，有{follower_count}个粉丝。我比较关注{background}相关的话题。我的兴趣比较广泛，喜欢从不同角度看问题。"
        else:
            return f"我还在探索平台，寻找感兴趣的内容。作为{profession}，我对{background}特别感兴趣，希望能找到更多志同道合的人。"
    
    elif any(keyword in question_lower for keyword in ['看法', '观点', '认为', '想法', '态度', '如何看待']):
        behavior_desc = f"发布了{len(user_posts)}篇内容" if user_posts else f"发表了{len(user_comments)}条评论" if user_comments else "还在观察"
        return f"从我在平台上的表现来看（{behavior_desc}），我倾向于理性地看待问题。我认为需要多角度思考。作为{profession}，我特别关注{background}相关的实际影响。"
    
    elif any(keyword in question_lower for keyword in ['经验', '经历', '遇到', '体验', '感受']):
        if total_activity > 0:
            return f"在平台上的{total_activity}次互动中，我学到了很多。{background}的背景让我对这些话题有独特的理解。我觉得这个平台很有价值，能接触到不同的观点。"
        else:
            return f"我刚开始使用平台，还在积累经验。我的{background}背景让我对某些话题特别感兴趣，期待未来有更多交流。"
    
    elif any(keyword in question_lower for keyword in ['建议', '推荐', '应该', '怎么做', '如何']):
        return f"基于我作为{profession}的经验和{background}的背景，我建议可以从实际情况出发。保持开放的心态很重要，同时也要有自己的判断。"
    
    else:
        return f"作为一个{activity_level}的用户（发布{len(user_posts)}篇内容，{len(user_comments)}条评论），我认为这个问题很有意思。我会继续关注相关讨论。我的{profession}背景让我对此有一些独特的看法。"


@app.route('/api/interview/users/<db_name>', methods=['GET'])
def get_all_users_for_interview(db_name):
    """获取所有用户用于采访（不限制数量）"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, persona, creation_time, influence_score, follower_count
            FROM users
            ORDER BY influence_score DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'persona': row[1],
                'creation_time': row[2],
                'influence_score': row[3] or 0,
                'follower_count': row[4] or 0
            })
        
        conn.close()
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/interview/posts-with-users/<db_name>', methods=['GET'])
def get_posts_with_users(db_name):
    """获取帖子及其互动用户，用于采访对象选择（支持分页）"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        # 获取分页参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        offset = (page - 1) * page_size
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取帖子总数
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        
        # 获取当前页的帖子（按互动量排序）
        cursor.execute("""
            SELECT post_id, author_id, content, num_likes, num_comments,
                   (num_likes + num_comments) as total_engagement
            FROM posts
            ORDER BY total_engagement DESC, created_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        
        posts = []
        all_interacted_user_ids = set()
        
        for row in cursor.fetchall():
            post_id = row[0]
            post_data = {
                'post_id': post_id,
                'author_id': row[1],
                'content': row[2],  # 完整内容
                'num_likes': row[3] or 0,
                'num_comments': row[4] or 0,
                'total_engagement': row[5] or 0,
                'interacted_users': []
            }
            
            # 获取该帖子的互动用户（评论者和点赞者）
            interacted_users = set()
            
            # 获取评论者
            cursor.execute("""
                SELECT DISTINCT c.author_id
                FROM comments c
                WHERE c.post_id = ?
            """, (post_id,))
            for comment_row in cursor.fetchall():
                interacted_users.add(comment_row[0])
            
            # 获取点赞者
            cursor.execute("""
                SELECT DISTINCT user_id
                FROM user_actions
                WHERE action_type IN ('like_post', 'like') AND target_id = ?
            """, (post_id,))
            for like_row in cursor.fetchall():
                interacted_users.add(like_row[0])
            
            # 获取这些用户的详细信息
            if interacted_users:
                placeholders = ','.join('?' * len(interacted_users))
                cursor.execute(f"""
                    SELECT user_id, persona, influence_score, follower_count
                    FROM users
                    WHERE user_id IN ({placeholders})
                    ORDER BY influence_score DESC
                """, list(interacted_users))
                
                for user_row in cursor.fetchall():
                    post_data['interacted_users'].append({
                        'user_id': user_row[0],
                        'persona': user_row[1],
                        'influence_score': user_row[2] or 0,
                        'follower_count': user_row[3] or 0
                    })
                    all_interacted_user_ids.add(user_row[0])
            
            posts.append(post_data)
        
        # 只在第一页时获取其他用户
        other_users = []
        if page == 1:
            cursor.execute("SELECT user_id, persona, influence_score, follower_count FROM users LIMIT 100")
            all_users = cursor.fetchall()
            
            for user_row in all_users:
                if user_row[0] not in all_interacted_user_ids:
                    other_users.append({
                        'user_id': user_row[0],
                        'persona': user_row[1],
                        'influence_score': user_row[2] or 0,
                        'follower_count': user_row[3] or 0
                    })
        
        # 计算总的唯一用户数
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
        total_unique_users = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'posts': posts,
            'other_users': other_users,
            'total_posts': total_posts,
            'current_page': page,
            'page_size': page_size,
            'total_pages': (total_posts + page_size - 1) // page_size,
            'total_unique_users': total_unique_users
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
        
        posts = []
        all_interacted_user_ids = set()
        
        for row in cursor.fetchall():
            post_id = row[0]
            post_data = {
                'post_id': post_id,
                'author_id': row[1],
                'content': row[2],  # 完整内容，不截断
                'num_likes': row[3] or 0,
                'num_comments': row[4] or 0,
                'total_engagement': row[5] or 0,
                'interacted_users': []
            }
            
            # 获取该帖子的互动用户（评论者和点赞者）
            interacted_users = {}  # user_id -> {user_info, interaction_types}
            
            # 获取评论者
            cursor.execute("""
                SELECT DISTINCT c.author_id
                FROM comments c
                WHERE c.post_id = ?
            """, (post_id,))
            for comment_row in cursor.fetchall():
                user_id = comment_row[0]
                if user_id not in interacted_users:
                    interacted_users[user_id] = {'types': []}
                interacted_users[user_id]['types'].append('comment')
            
            # 获取点赞者
            cursor.execute("""
                SELECT DISTINCT user_id
                FROM user_actions
                WHERE action_type IN ('like_post', 'like') AND target_id = ?
            """, (post_id,))
            for like_row in cursor.fetchall():
                user_id = like_row[0]
                if user_id not in interacted_users:
                    interacted_users[user_id] = {'types': []}
                interacted_users[user_id]['types'].append('like')
            
            # 获取这些用户的详细信息
            if interacted_users:
                placeholders = ','.join('?' * len(interacted_users))
                cursor.execute(f"""
                    SELECT user_id, persona, influence_score, follower_count
                    FROM users
                    WHERE user_id IN ({placeholders})
                    ORDER BY influence_score DESC
                """, list(interacted_users.keys()))
                
                for user_row in cursor.fetchall():
                    user_id = user_row[0]
                    post_data['interacted_users'].append({
                        'user_id': user_id,
                        'persona': user_row[1],
                        'influence_score': user_row[2] or 0,
                        'follower_count': user_row[3] or 0,
                        'interaction_type': interacted_users[user_id]['types']
                    })
                    all_interacted_user_ids.add(user_id)
            
            posts.append(post_data)
        
        # 获取没有互动的其他用户
        cursor.execute("SELECT user_id, persona, influence_score, follower_count FROM users")
        all_users = cursor.fetchall()
        
        other_users = []
        for user_row in all_users:
            if user_row[0] not in all_interacted_user_ids:
                other_users.append({
                    'user_id': user_row[0],
                    'persona': user_row[1],
                    'influence_score': user_row[2] or 0,
                    'follower_count': user_row[3] or 0
                })
        
        # 按影响力排序其他用户
        other_users.sort(key=lambda x: x['influence_score'], reverse=True)
        
        conn.close()
        
        return jsonify({
            'posts': posts,
            'other_users': other_users,
            'summary': {
                'total_posts': len(posts),
                'total_interacted_users': len(all_interacted_user_ids),
                'total_other_users': len(other_users),
                'total_users': len(all_interacted_user_ids) + len(other_users)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
        # 获取没有互动的其他用户
        cursor.execute("SELECT user_id, persona, influence_score, follower_count FROM users")
        all_users = cursor.fetchall()
        
        other_users = []
        for user_row in all_users:
            if user_row[0] not in all_interacted_user_ids:
                other_users.append({
                    'user_id': user_row[0],
                    'persona': user_row[1],
                    'influence_score': user_row[2] or 0,
                    'follower_count': user_row[3] or 0
                })
        
        # 按影响力排序其他用户
        other_users.sort(key=lambda x: x['influence_score'], reverse=True)
        
        conn.close()
        
        return jsonify({
            'posts': posts,
            'other_users': other_users,
            'summary': {
                'total_posts': len(posts),
                'total_interacted_users': len(all_interacted_user_ids),
                'total_other_users': len(other_users),
                'total_users': len(all_interacted_user_ids) + len(other_users)
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/interview/all-user-ids/<db_name>', methods=['GET'])
def get_all_user_ids(db_name):
    """获取所有用户ID，用于全选功能"""
    try:
        db_path = os.path.join(DATABASE_DIR, db_name)
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'user_ids': user_ids,
            'total': len(user_ids)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/opinion-balance/logs/stream', methods=['GET'])
def stream_opinion_balance_logs():
    """
    Stream the latest opinion balance log file using SSE (Server-Sent Events).

    Query params:
      - tail: number of last lines to emit first (default 300, max 2000)
      - follow_latest: whether to switch to a newer log file if it appears (default true)
    """
    from flask import Response, stream_with_context
    from log_tail import find_latest_file, tail_lines

    # source=workflow streams from logs/workflow (preferred for real-time UI);
    # source=opinion_balance streams from logs/opinion_balance (legacy).
    source = request.args.get('source', default='workflow')
    source = str(source).lower().strip()

    if source == 'opinion_balance':
        base_dir = OPINION_BALANCE_LOG_DIR
    else:
        base_dir = WORKFLOW_LOG_DIR

    tail = request.args.get('tail', default=0, type=int)
    tail = max(0, min(2000, tail))

    follow_latest = request.args.get('follow_latest', default='true')
    follow_latest = str(follow_latest).lower() not in ('0', 'false', 'no', 'off')

    poll_interval_sec = 0.25
    heartbeat_sec = 15.0

    def sse_data(line: str) -> str:
        safe = (line or '').replace('\r', '').rstrip('\n')
        return f"data: {safe}\n\n"

    def generate():
        os.makedirs(base_dir, exist_ok=True)

        current_path = find_latest_file(base_dir, pattern="*.log")
        if not current_path:
            # Don't silently fail: provide a visible error line to the UI.
            yield sse_data(f"ERROR: no log file found under {os.path.relpath(base_dir, os.path.dirname(__file__))} (start the workflow first)")
            return

        yield sse_data(f"INFO: connected to {os.path.basename(current_path)}")

        if tail > 0:
            try:
                for line in tail_lines(current_path, n=tail):
                    yield sse_data(line)
            except Exception as e:
                yield sse_data(f"ERROR: failed to read log tail: {e}")

        last_switch_check = time.time()
        last_heartbeat = time.time()

        # Tail-follow the active log file.
        try:
            f = open(current_path, 'r', encoding='utf-8', errors='replace')
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if line:
                    yield sse_data(line)
                    continue

                now = time.time()
                if now - last_heartbeat >= heartbeat_sec:
                    last_heartbeat = now
                    yield ": keep-alive\n\n"

                if follow_latest and (now - last_switch_check >= 2.0):
                    last_switch_check = now
                    latest = find_latest_file(base_dir, pattern="*.log")
                    if latest and latest != current_path:
                        current_path = latest
                        try:
                            f.close()
                        except Exception:
                            pass
                        f = open(current_path, 'r', encoding='utf-8', errors='replace')
                        # New run files are typically small; stream from the beginning.
                        yield sse_data(f"INFO: switched to new log file: {os.path.basename(current_path)}")
                        continue

                time.sleep(poll_interval_sec)
        except GeneratorExit:
            return
        except Exception as e:
            yield sse_data(f"ERROR: log stream stopped unexpectedly: {e}")
        finally:
            try:
                f.close()
            except Exception:
                pass

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/dynamic/start', methods=['POST'])
def start_dynamic_demo():
    """启动动态演示系统（数据库 + 主程序）
    
    自动使用当前 Python 环境（frontend_api.py 运行的环境）
    
    请求体:
        {
            "conda_env": "环境名称"  // 可选，已废弃，保留兼容性
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "processes": {
                "database": {"pid": 12345, "status": "running"},
                "main": {"pid": 12346, "status": "running"}
            }
        }
    """
    try:
        # 解析请求体（保留 conda_env 参数兼容性，但不使用）
        data = request.get_json() or {}
        conda_env = data.get('conda_env')  # 保留兼容性，但不使用
        
        # 调用 process_manager.start_demo()
        result = process_manager.start_demo(conda_env=conda_env)
        
        # 返回 JSON 响应
        return jsonify(result)
        
    except Exception as e:
        # 处理异常并返回错误响应
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Failed to start dynamic demo: {str(e)}',
            'error': 'UnexpectedError'
        }), 500


@app.route('/api/dynamic/stop', methods=['POST'])
def stop_dynamic_demo():
    """停止所有动态演示进程
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "stopped_processes": ["database", "main", "opinion_balance"],
            "errors": []
        }
    """
    try:
        # 调用 process_manager.stop_all_processes()
        result = process_manager.stop_all_processes()
        
        # 返回 JSON 响应
        return jsonify(result)
        
    except Exception as e:
        # 处理异常并返回错误响应
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Failed to stop processes: {str(e)}',
            'error': 'UnexpectedError',
            'stopped_processes': [],
            'errors': [str(e)]
        }), 500


@app.route('/api/dynamic/opinion-balance/start', methods=['POST'])
def start_opinion_balance_system():
    """启动舆论平衡系统
    
    自动使用当前 Python 环境
    
    请求体:
        {
            "conda_env": "环境名称"  // 可选，已废弃，保留兼容性
        }
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "process": {
                "pid": 12347,
                "status": "running"
            }
        }
    """
    try:
        # 解析请求体（保留 conda_env 参数兼容性）
        data = request.get_json() or {}
        conda_env = data.get('conda_env')  # 保留兼容性，但不使用
        
        # 调用 process_manager.start_opinion_balance()
        result = process_manager.start_opinion_balance(conda_env=conda_env)
        
        # 返回 JSON 响应
        return jsonify(result)
        
    except Exception as e:
        # 处理异常并返回错误响应
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Failed to start opinion balance: {str(e)}',
            'error': 'UnexpectedError'
        }), 500


@app.route('/api/dynamic/opinion-balance/stop', methods=['POST'])
def stop_opinion_balance_system():
    """停止舆论平衡系统
    
    响应:
        {
            "success": true/false,
            "message": "消息",
            "process": "opinion_balance"
        }
    """
    try:
        # 调用 process_manager.stop_process('opinion_balance')
        result = process_manager.stop_process('opinion_balance')
        
        # 返回 JSON 响应
        return jsonify(result)
        
    except Exception as e:
        # 处理异常并返回错误响应
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Failed to stop opinion balance: {str(e)}',
            'error': 'UnexpectedError'
        }), 500


@app.route('/api/dynamic/status', methods=['GET'])
def get_dynamic_demo_status():
    """获取动态演示系统状态
    
    响应:
        {
            "database": {
                "status": "running/stopped",
                "pid": 12345,
                "uptime": 120
            },
            "main": {
                "status": "running/stopped",
                "pid": 12346,
                "uptime": 115
            },
            "opinion_balance": {
                "status": "stopped",
                "pid": null,
                "uptime": 0
            }
        }
    """
    try:
        # 调用 process_manager.get_process_status()
        result = process_manager.get_process_status()
        
        # 返回 JSON 响应
        return jsonify(result)
        
    except Exception as e:
        # 处理异常并返回错误响应
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'database': {'status': 'unknown', 'pid': None, 'uptime': 0},
            'main': {'status': 'unknown', 'pid': None, 'uptime': 0},
            'opinion_balance': {'status': 'unknown', 'pid': None, 'uptime': 0}
        }), 500





# ============================================================================
# 帖子热度榜功能
# ============================================================================

class HeatScoreCalculator:
    """热度评分计算器 - 与 agent_user.py 的 get_feed() 评分算法完全一致
    
    该类负责计算帖子的热度评分，使用与 agent_user.py 中 get_feed() 函数
    完全相同的算法和参数，确保前后端数据的一致性。
    
    评分公式：
        score = (engagement + BETA_BIAS) × freshness
        engagement = num_comments + num_shares + num_likes
        freshness = max(MIN_FRESHNESS, 1.0 - LAMBDA_DECAY × age)
        age = max(0, current_time_step - post_time_step)
    """
    
    # 固定参数（与 agent_user.py 保持一致）
    LAMBDA_DECAY = 0.1      # 时间衰减系数
    BETA_BIAS = 180         # 基础偏置值
    MIN_FRESHNESS = 0.1     # 最小新鲜度
    
    def __init__(self, db_path: str):
        """初始化热度评分计算器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    def get_current_time_step(self) -> int:
        """获取当前时间步
        
        从 post_timesteps 表获取最大 time_step 值作为当前时间步。
        如果表为空或查询失败，返回 0。
        
        Returns:
            int: 当前时间步，如果表为空则返回 0
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COALESCE(MAX(time_step), 0) FROM post_timesteps')
            result = cursor.fetchone()
            current_step = result[0] if result else 0
            
            conn.close()
            return current_step
        except Exception as e:
            print(f'⚠️ 获取当前时间步失败: {e}')
            return 0
    
    def get_post_time_step(self, post_id: str) -> Optional[int]:
        """获取帖子的创建时间步
        
        Args:
            post_id: 帖子ID
            
        Returns:
            Optional[int]: 时间步，如果不存在则返回 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT time_step FROM post_timesteps WHERE post_id = ?', (post_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f'⚠️ 获取帖子时间步失败 (post_id={post_id}): {e}')
            return None
    
    def calculate_score(self, post: dict, current_time_step: int) -> float:
        """计算单个帖子的热度评分
        
        使用与 agent_user.py 完全一致的评分公式：
        1. 计算互动数：engagement = num_comments + num_shares + num_likes
        2. 计算年龄：age = max(0, current_time_step - post_time_step)
           如果 post_time_step 不存在，则 age = 0
        3. 计算新鲜度：freshness = max(0.1, 1.0 - 0.1 × age)
        4. 计算评分：score = (engagement + 180) × freshness
        
        Args:
            post: 帖子数据字典，必须包含：
                  - post_id: 帖子ID
                  - num_comments: 评论数
                  - num_shares: 分享数
                  - num_likes: 点赞数
            current_time_step: 当前时间步
            
        Returns:
            float: 热度评分
        """
        # 计算互动数（与 agent_user.py 保持一致）
        engagement = (
            (post.get('num_comments') or 0) +
            (post.get('num_shares') or 0) +
            (post.get('num_likes') or 0)
        )
        
        # 获取帖子的创建时间步
        post_time_step = self.get_post_time_step(post['post_id'])
        
        # 计算年龄（如果 post_time_step 为 None，则 age = 0）
        if post_time_step is not None:
            age = max(0, current_time_step - post_time_step)
        else:
            age = 0
        
        # 计算新鲜度
        freshness = max(self.MIN_FRESHNESS, 1.0 - self.LAMBDA_DECAY * age)
        
        # 计算最终评分
        score = (engagement + self.BETA_BIAS) * freshness
        
        return score
    
    @staticmethod
    def calculate_fingerprint(items: List[dict]) -> str:
        """计算榜单指纹，用于去重
        
        基于榜单中所有帖子的关键字段（postId, score, createdAt）计算 MD5 哈希值，
        用于判断榜单是否发生变化，避免无效的 SSE 推送。
        
        Args:
            items: 榜单项列表，每项包含 postId, score, createdAt 字段
            
        Returns:
            str: MD5 哈希值（32位十六进制字符串）
        """
        import hashlib
        import json
        
        # 提取关键字段：postId, score, createdAt
        key_data = [
            (item['postId'], item['score'], item['createdAt'])
            for item in items
        ]
        
        # 序列化为 JSON 字符串（确保键排序以保证一致性）
        json_str = json.dumps(key_data, sort_keys=True)
        
        # 计算 MD5 哈希
        fingerprint = hashlib.md5(json_str.encode()).hexdigest()
        
        return fingerprint


# ============================================================================
# 帖子热度榜 API
# ============================================================================

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """获取热度排行榜
    
    查询所有符合条件的帖子，计算热度评分，返回 Top N 个帖子。
    
    查询参数:
        limit: 返回数量，默认 20，最大 100
        
    返回:
        {
            "items": [
                {
                    "postId": str,
                    "excerpt": str,  # 优先使用 summary，否则截断 content 前 100 字符
                    "score": float,
                    "authorId": str,
                    "createdAt": str,  # ISO 8601 格式
                    "likeCount": int,
                    "shareCount": int,
                    "commentCount": int
                },
                ...
            ],
            "timeStep": int,
            "fingerprint": str  # 用于去重的哈希值
        }
    """
    try:
        # 获取 limit 参数（默认 20，最大 100）
        limit = request.args.get('limit', default=20, type=int)
        limit = min(max(1, limit), 100)  # 限制在 1-100 范围内
        
        # 获取数据库路径（默认使用 simulation.db）
        db_name = request.args.get('db', default='simulation.db', type=str)
        db_path = os.path.join(DATABASE_DIR, db_name)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        # 创建热度评分计算器
        calculator = HeatScoreCalculator(db_path)
        
        # 获取当前时间步
        current_time_step = calculator.get_current_time_step()
        
        # 查询所有符合条件的帖子
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 只查询必需字段，过滤条件：status IS NULL OR status != 'taken_down'
        cursor.execute("""
            SELECT 
                post_id,
                summary,
                content,
                author_id,
                created_at,
                num_likes,
                num_shares,
                num_comments
            FROM posts
            WHERE status IS NULL OR status != 'taken_down'
        """)
        
        # 计算每个帖子的热度评分
        posts_with_scores = []
        for row in cursor.fetchall():
            post = {
                'post_id': row[0],
                'summary': row[1],
                'content': row[2],
                'author_id': row[3],
                'created_at': row[4],
                'num_likes': row[5] or 0,
                'num_shares': row[6] or 0,
                'num_comments': row[7] or 0
            }
            
            # 计算热度评分
            score = calculator.calculate_score(post, current_time_step)
            
            # 处理 excerpt 字段（优先使用 summary，否则截断 content）
            if post['summary']:
                excerpt = post['summary']
            else:
                content = post['content'] or ''
                excerpt = content[:100] + ('...' if len(content) > 100 else '')
            
            posts_with_scores.append({
                'postId': post['post_id'],
                'excerpt': excerpt,
                'score': score,
                'authorId': post['author_id'],
                'createdAt': post['created_at'],
                'likeCount': post['num_likes'],
                'shareCount': post['num_shares'],
                'commentCount': post['num_comments']
            })
        
        conn.close()
        
        # 排序：主排序 score 降序，次排序 createdAt 降序，三级排序 postId 升序
        # 使用稳定排序的特性，从最低优先级到最高优先级依次排序
        
        # 第一步：按 postId 升序排序（最低优先级）
        posts_with_scores.sort(key=lambda x: x['postId'])
        
        # 第二步：按 createdAt 降序排序（次优先级，稳定排序保持 postId 顺序）
        posts_with_scores.sort(key=lambda x: x['createdAt'] or '', reverse=True)
        
        # 第三步：按 score 降序排序（最高优先级，稳定排序保持前两级顺序）
        posts_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回前 N 个结果
        top_posts = posts_with_scores[:limit]
        
        # 计算 fingerprint
        fingerprint = HeatScoreCalculator.calculate_fingerprint(top_posts)
        
        return jsonify({
            'items': top_posts,
            'timeStep': current_time_step,
            'fingerprint': fingerprint
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/leaderboard/posts/<post_id>', methods=['GET'])
def get_post_detail_by_id(post_id: str):
    """获取帖子详情（热度榜专用）
    
    查询指定 post_id 的帖子，返回完整的帖子信息。
    
    路径参数:
        post_id: 帖子ID
        
    查询参数:
        db: 数据库名称（默认 simulation.db）
        
    返回:
        {
            "postId": str,
            "content": str,
            "excerpt": str,  # summary 字段
            "authorId": str,
            "createdAt": str,  # ISO 8601 格式
            "likeCount": int,
            "shareCount": int,
            "commentCount": int
        }
        
    错误:
        404: 帖子不存在或已删除（status = 'taken_down'）
    """
    try:
        # 获取数据库路径（默认使用 simulation.db）
        db_name = request.args.get('db', default='simulation.db', type=str)
        db_path = os.path.join(DATABASE_DIR, db_name)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        # 查询帖子
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 过滤条件：status IS NULL OR status != 'taken_down'
        cursor.execute("""
            SELECT 
                post_id,
                content,
                summary,
                author_id,
                created_at,
                num_likes,
                num_shares,
                num_comments
            FROM posts
            WHERE post_id = ? AND (status IS NULL OR status != 'taken_down')
        """, (post_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        # 如果帖子不存在或已删除，返回 404
        if not row:
            return jsonify({'error': 'Post not found'}), 404
        
        # 构造响应数据（转换为 camelCase）
        response = {
            'postId': row[0],
            'content': row[1] or '',
            'excerpt': row[2] or '',  # summary 字段
            'authorId': row[3],
            'createdAt': row[4],
            'likeCount': row[5] or 0,
            'shareCount': row[6] or 0,
            'commentCount': row[7] or 0
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/leaderboard/posts/<post_id>/comments', methods=['GET'])
def get_post_comments_by_id(post_id: str):
    """获取帖子评论列表（热度榜专用）
    
    查询指定 post_id 的所有评论，支持按点赞数或时间排序。
    
    路径参数:
        post_id: 帖子ID
        
    查询参数:
        sort: 排序方式，'likes' 或 'time'，默认 'likes'
        limit: 返回数量，默认 100
        db: 数据库名称（默认 simulation.db）
        
    返回:
        {
            "comments": [
                {
                    "commentId": str,
                    "content": str,
                    "authorId": str,
                    "createdAt": str,  # ISO 8601 格式
                    "likeCount": int
                },
                ...
            ]
        }
        
    错误:
        400: 无效的 sort 参数
    """
    try:
        # 获取查询参数
        sort_param = request.args.get('sort', default='likes', type=str).lower()
        limit = request.args.get('limit', default=100, type=int)
        db_name = request.args.get('db', default='simulation.db', type=str)
        
        # 验证 sort 参数
        if sort_param not in ['likes', 'time']:
            return jsonify({'error': 'Invalid sort parameter. Must be "likes" or "time"'}), 400
        
        # 限制 limit 范围
        limit = min(max(1, limit), 100)
        
        # 获取数据库路径
        db_path = os.path.join(DATABASE_DIR, db_name)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database not found'}), 404
        
        # 查询评论
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 根据 sort 参数确定排序方式
        if sort_param == 'likes':
            order_by = 'num_likes DESC, created_at DESC'
        else:  # sort_param == 'time'
            order_by = 'created_at DESC'
        
        # 查询评论列表
        query = f"""
            SELECT 
                comment_id,
                content,
                author_id,
                created_at,
                num_likes
            FROM comments
            WHERE post_id = ?
            ORDER BY {order_by}
            LIMIT ?
        """
        
        cursor.execute(query, (post_id, limit))
        
        # 构造响应数据（转换为 camelCase）
        comments = []
        for row in cursor.fetchall():
            comments.append({
                'commentId': row[0],
                'content': row[1] or '',
                'authorId': row[2],
                'createdAt': row[3],
                'likeCount': row[4] or 0
            })
        
        conn.close()
        
        return jsonify({'comments': comments})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SSE 事件流 - 实时热度榜更新
# ============================================================================

@app.route('/api/events', methods=['GET'])
def event_stream():
    """SSE 事件流，推送热度榜更新
    
    建立 Server-Sent Events 连接，每 1 秒推送一次热度榜更新。
    使用 fingerprint 机制避免无效推送：只在榜单内容发生变化时才推送数据。
    
    事件格式:
        event: leaderboard-update
        data: {
            "items": [...],  # 与 GET /api/leaderboard 返回格式一致
            "timeStep": int,
            "fingerprint": str,
            "timestamp": str  # ISO 8601 格式
        }
        
    推送间隔: 1 秒
    推送策略: 仅当 fingerprint 变化时推送（避免无效更新）
    """
    # 在生成器外部获取请求参数（避免上下文问题）
    db_name = request.args.get('db', default='simulation.db', type=str)
    limit = request.args.get('limit', default=20, type=int)
    limit = min(max(1, limit), 100)  # 限制在 1-100 范围内
    
    def generate():
        """生成器函数，持续推送热度榜更新"""
        last_fingerprint = None  # 记录上次的 fingerprint
        
        try:
            while True:
                try:
                    # 获取数据库路径（使用外部变量）
                    db_path = os.path.join(DATABASE_DIR, db_name)
                    
                    if not os.path.exists(db_path):
                        # 数据库不存在，发送错误事件
                        yield f'event: error\ndata: {{"error": "Database not found"}}\n\n'
                        break
                    
                    # 创建热度评分计算器
                    calculator = HeatScoreCalculator(db_path)
                    
                    # 获取当前时间步
                    current_time_step = calculator.get_current_time_step()
                    
                    # 查询所有符合条件的帖子
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # 只查询必需字段，过滤条件：status IS NULL OR status != 'taken_down'
                    cursor.execute("""
                        SELECT 
                            post_id,
                            summary,
                            content,
                            author_id,
                            created_at,
                            num_likes,
                            num_shares,
                            num_comments
                        FROM posts
                        WHERE status IS NULL OR status != 'taken_down'
                    """)
                    
                    # 计算每个帖子的热度评分
                    posts_with_scores = []
                    for row in cursor.fetchall():
                        post = {
                            'post_id': row[0],
                            'summary': row[1],
                            'content': row[2],
                            'author_id': row[3],
                            'created_at': row[4],
                            'num_likes': row[5] or 0,
                            'num_shares': row[6] or 0,
                            'num_comments': row[7] or 0
                        }
                        
                        # 计算热度评分
                        score = calculator.calculate_score(post, current_time_step)
                        
                        # 处理 excerpt 字段（优先使用 summary，否则截断 content）
                        if post['summary']:
                            excerpt = post['summary']
                        else:
                            content = post['content'] or ''
                            excerpt = content[:100] + ('...' if len(content) > 100 else '')
                        
                        posts_with_scores.append({
                            'postId': post['post_id'],
                            'excerpt': excerpt,
                            'score': score,
                            'authorId': post['author_id'],
                            'createdAt': post['created_at'],
                            'likeCount': post['num_likes'],
                            'shareCount': post['num_shares'],
                            'commentCount': post['num_comments']
                        })
                    
                    conn.close()
                    
                    # 排序：主排序 score 降序，次排序 createdAt 降序，三级排序 postId 升序
                    # 使用稳定排序的特性，从最低优先级到最高优先级依次排序
                    
                    # 第一步：按 postId 升序排序（最低优先级）
                    posts_with_scores.sort(key=lambda x: x['postId'])
                    
                    # 第二步：按 createdAt 降序排序（次优先级，稳定排序保持 postId 顺序）
                    posts_with_scores.sort(key=lambda x: x['createdAt'] or '', reverse=True)
                    
                    # 第三步：按 score 降序排序（最高优先级，稳定排序保持前两级顺序）
                    posts_with_scores.sort(key=lambda x: x['score'], reverse=True)
                    
                    # 返回前 N 个结果
                    top_posts = posts_with_scores[:limit]
                    
                    # 计算 fingerprint
                    current_fingerprint = HeatScoreCalculator.calculate_fingerprint(top_posts)
                    
                    # 只在 fingerprint 变化时推送
                    if current_fingerprint != last_fingerprint:
                        # 构造事件数据
                        event_data = {
                            'items': top_posts,
                            'timeStep': current_time_step,
                            'fingerprint': current_fingerprint,
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                        
                        # 格式化为 SSE 格式
                        import json
                        data_json = json.dumps(event_data, ensure_ascii=False)
                        yield f'event: leaderboard-update\ndata: {data_json}\n\n'
                        
                        # 更新 last_fingerprint
                        last_fingerprint = current_fingerprint
                    
                    # 等待 1 秒
                    time.sleep(1)
                    
                except GeneratorExit:
                    # 客户端断开连接
                    print('✅ SSE 客户端断开连接，清理资源')
                    break
                except Exception as e:
                    # 发生错误，记录日志并发送错误事件
                    import traceback
                    traceback.print_exc()
                    yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'
                    break
                    
        except GeneratorExit:
            # 客户端断开连接
            print('✅ SSE 客户端断开连接（外层），清理资源')
        except Exception as e:
            # 发生错误，记录日志
            import traceback
            traceback.print_exc()
    
    # 返回流式响应
    from flask import Response
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # 禁用 nginx 缓冲
            'Connection': 'keep-alive'
        }
    )


if __name__ == '__main__':
    print("Starting EvoCorps Frontend API Server...")
    print("Database directory:", os.path.abspath(DATABASE_DIR))
    print("Server running at: http://127.0.0.1:5001")
    print("Press Ctrl+C to stop")
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)