#!/usr/bin/env python3
"""
Database service - provide database access via HTTP API
Avoid multi-process file lock conflicts
"""

import os
import sys
import json
import sqlite3
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify
import logging

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class DatabaseService:
    """Database service class"""
    
    def _log_success(self, success_msg: str, **kwargs):
        """Record success logs - output disabled"""
        # Fully disable success log output
        pass
    
    def _log_error(self, error_msg: str, exception: Exception, **kwargs):
        """Unified error logging method"""
        import inspect
        
        try:
            # Get call stack info
            stack = inspect.stack()
            
            # Log error info
            self.app.logger.error(f"❌ {error_msg}: {str(exception)}")
            self.app.logger.error(f"📍 Error type: {type(exception).__name__}")
            
            # Log extra context info
            for key, value in kwargs.items():
                if value is not None:
                    # Limit log length to avoid overly long params
                    value_str = str(value)
                    if len(value_str) > 200:
                        value_str = value_str[:200] + "..."
                    self.app.logger.error(f"📊 {key}: {value_str}")
            
            # Only log key file and line info
            if len(stack) > 2:
                frame = stack[2]  # Skip current method and caller
                filename = frame.filename.split('\\')[-1] if '\\' in frame.filename else frame.filename
                self.app.logger.error(f"📍 Error location: {filename}:{frame.lineno} in {frame.function}")
            
        except Exception as log_error:
            # If logging itself fails, at least log basic info
            print(f"❌ Log recording failed: {log_error}")
            print(f"❌ Original error: {error_msg}: {str(exception)}")
    
    def __init__(self, db_path: str = None, port: int = 5000):
        """
        Initialize database service
        
        Args:
            db_path: Database file path
            port: Service port
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'database', 
            'simulation.db'
        )
        self.port = port
        
        # Initialize database connection
        self._init_database()
        
        # Create Flask app
        self.app = Flask(__name__)
        
        # Configure log file output
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'database_service')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler
        log_file = os.path.join(log_dir, f'database_service_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Configure Flask app logger - file handler only, no console output
        self.app.logger.setLevel(logging.INFO)
        self.app.logger.addHandler(file_handler)
        
        # Prevent duplicate logs
        self.app.logger.propagate = False
        
        # Keep Flask request logs, disable only business log console output
        # werkzeug_logger stays default to allow 200 OK request logs
        
        # Only disable Flask app business logs to console; keep request logs
        # self.app.logger outputs to file only, does not affect werkzeug request logs
        
        # Test log
        self.app.logger.info("✅ Database service logging system initialized")
        
        # Configure JSON encoder for datetime objects
        self.app.json_encoder = DateTimeEncoder
        
        # Set up routes
        self._setup_routes()
        
        # Service status
        self.is_running = False
        self.server_thread = None
        
        print("✅ Database service initialized")
        print(f"   📊 Database path: {self.db_path}")
        print(f"   🌐 Service port: {self.port}")
    
    def _init_database(self):
        """Initialize database connection"""
        try:
            # Ensure database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Test database connection
            test_conn = sqlite3.connect(self.db_path, timeout=60.0)
            test_conn.execute("PRAGMA journal_mode=WAL")
            test_conn.execute("PRAGMA synchronous=NORMAL")
            test_conn.execute("PRAGMA foreign_keys = ON")
            test_conn.execute("SELECT 1").fetchone()
            test_conn.close()
            
            print(f"✅ Database connection successful: {self.db_path}")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def _get_connection(self):
        """Get database connection (thread-safe)"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA busy_timeout = 30000")  # 30s busy wait timeout
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                raise
    
    def _setup_routes(self):
        """Set up API routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check"""
            try:
                # Test database connection
                conn = self._get_connection()
                conn.execute("SELECT 1").fetchone()
                conn.close()
                return jsonify({
                    "status": "healthy",
                    "database": self.db_path,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/execute', methods=['POST'])
        def execute_query():
            """Execute SQL query"""
            conn = None
            try:
                data = request.get_json()
                query = data.get('query')
                params = data.get('params', [])
                
                if not query:
                    return jsonify({"error": "Query cannot be empty"}), 400
                
                # Clean params: remove extra quotes from string params
                cleaned_params = []
                for param in params:
                    if isinstance(param, str):
                        # If string is wrapped by extra quotes (e.g. "'value'"), remove them
                        cleaned_param = param.strip()
                        if (cleaned_param.startswith("'") and cleaned_param.endswith("'")) or \
                           (cleaned_param.startswith('"') and cleaned_param.endswith('"')):
                            # Remove surrounding quotes without touching internal quotes
                            if len(cleaned_param) >= 2:
                                cleaned_param = cleaned_param[1:-1]
                        cleaned_params.append(cleaned_param)
                    else:
                        cleaned_params.append(param)
                params = cleaned_params
                
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                # Determine query type
                query_upper = query.strip().upper()
                
                if query_upper.startswith('SELECT') or query_upper.startswith('PRAGMA'):
                    # SELECT/PRAGMA queries return data
                    results = cursor.fetchall()
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                    self._log_success("Database query executed successfully", QueryType="SELECT/PRAGMA", ResultCount=len(results))
                    return jsonify({
                        "success": True,
                        "data": results,
                        "columns": columns
                    })
                else:
                    # Other queries (INSERT/UPDATE/DELETE/CREATE/DROP), commit transaction
                    conn.commit()
                    self._log_success("Database query executed successfully", QueryType="DML/DDL", AffectedRows=cursor.rowcount, LastInsertId=cursor.lastrowid)
                    return jsonify({
                        "success": True,
                        "affected_rows": cursor.rowcount,
                        "lastrowid": cursor.lastrowid
                    })
                    
            except sqlite3.IntegrityError as e:
                # Foreign key constraint or other integrity errors
                error_msg = str(e)
                if "FOREIGN KEY constraint failed" in error_msg:
                    # Try to identify which foreign key failed
                    if "follows" in query.upper() or "followed_id" in query.upper():
                        error_msg = f"Foreign key constraint failed: followed user may not exist. Original error: {error_msg}"
                    elif "follower_id" in query.upper():
                        error_msg = f"Foreign key constraint failed: follower user may not exist. Original error: {error_msg}"
                self._log_error("Database query execution failed", e, Query=query, Params=params)
                return jsonify({"error": error_msg, "type": "IntegrityError"}), 500
            except sqlite3.OperationalError as e:
                # Database lock or other operational errors
                error_msg = str(e)
                if "database is locked" in error_msg.lower():
                    error_msg = f"Database is locked, please retry later. Original error: {error_msg}"
                self._log_error("Database query execution failed", e, Query=query, Params=params)
                return jsonify({"error": error_msg, "type": "OperationalError"}), 500
            except Exception as e:
                # Log detailed error info
                self._log_error("Database query execution failed", e, Query=query, Params=params)
                return jsonify({"error": str(e)}), 500
            finally:
                if conn:
                    conn.close()
        
        @self.app.route('/executemany', methods=['POST'])
        def execute_many():
            """Execute batch SQL queries"""
            conn = None
            try:
                data = request.get_json()
                query = data.get('query')
                params_list = data.get('params_list', [])
                
                if not query:
                    return jsonify({"error": "Query cannot be empty"}), 400
                
                if not params_list:
                    return jsonify({"error": "Params list cannot be empty"}), 400
                
                # Clean params list: remove extra quotes from string params
                cleaned_params_list = []
                for params in params_list:
                    cleaned_params = []
                    for param in params:
                        if isinstance(param, str):
                            # If string is wrapped by extra quotes (e.g. "'value'"), remove them
                            cleaned_param = param.strip()
                            if (cleaned_param.startswith("'") and cleaned_param.endswith("'")) or \
                               (cleaned_param.startswith('"') and cleaned_param.endswith('"')):
                                # Remove surrounding quotes
                                if len(cleaned_param) >= 2:
                                    cleaned_param = cleaned_param[1:-1]
                            cleaned_params.append(cleaned_param)
                        else:
                            cleaned_params.append(param)
                    cleaned_params_list.append(cleaned_params)
                params_list = cleaned_params_list
                
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                
                # Determine query type
                query_upper = query.strip().upper()
                
                if query_upper.startswith('SELECT') or query_upper.startswith('PRAGMA'):
                    # SELECT/PRAGMA queries return data
                    results = cursor.fetchall()
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                    self._log_success("Batch query executed successfully", QueryType="SELECT/PRAGMA", ResultCount=len(results), ParamCount=len(params_list))
                    return jsonify({
                        "success": True,
                        "data": results,
                        "columns": columns
                    })
                else:
                    # Other queries (INSERT/UPDATE/DELETE/CREATE/DROP), commit transaction
                    conn.commit()
                    self._log_success("Batch query executed successfully", QueryType="DML/DDL", AffectedRows=cursor.rowcount, ParamCount=len(params_list))
                    return jsonify({
                        "success": True,
                        "affected_rows": cursor.rowcount,
                        "lastrowid": cursor.lastrowid
                    })
                    
            except sqlite3.IntegrityError as e:
                # Foreign key constraint or other integrity errors
                error_msg = str(e)
                if "FOREIGN KEY constraint failed" in error_msg:
                    error_msg = f"Foreign key constraint failed: referenced record may not exist. Original error: {error_msg}"
                self._log_error("Batch query execution failed", e, Query=query, ParamsList=params_list)
                return jsonify({"error": error_msg, "type": "IntegrityError"}), 500
            except sqlite3.OperationalError as e:
                # Database lock or other operational errors
                error_msg = str(e)
                if "database is locked" in error_msg.lower():
                    error_msg = f"Database is locked, please retry later. Original error: {error_msg}"
                self._log_error("Batch query execution failed", e, Query=query, ParamsList=params_list)
                return jsonify({"error": error_msg, "type": "OperationalError"}), 500
            except Exception as e:
                # Log detailed error info
                self._log_error("Batch query execution failed", e, Query=query, ParamsList=params_list)
                return jsonify({"error": str(e)}), 500
            finally:
                if conn:
                    conn.close()
        
        @self.app.route('/posts', methods=['GET'])
        def get_posts():
            """Get post list"""
            conn = None
            try:
                limit = request.args.get('limit', 10, type=int)
                offset = request.args.get('offset', 0, type=int)
                
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT post_id, content, author_id, num_comments, num_likes, num_shares, created_at
                    FROM posts 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                self._log_success("Fetched post list", PostCount=len(results), Limit=limit, Offset=offset)
                return jsonify({
                    "success": True,
                    "data": results,
                    "columns": columns
                })
                
            except Exception as e:
                # Log detailed error info
                self._log_error("Failed to fetch post list", e)
                return jsonify({"error": str(e)}), 500
            finally:
                if conn:
                    conn.close()
        
        @self.app.route('/posts/trending', methods=['GET'])
        def get_trending_posts():
            """Get trending posts"""
            try:
                min_engagement = request.args.get('min_engagement', 50, type=int)
                limit = request.args.get('limit', 10, type=int)
                
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at,
                           (p.num_comments + p.num_likes + p.num_shares) as total_engagement
                    FROM posts p
                    WHERE (p.num_comments + p.num_likes + p.num_shares) >= ?
                    ORDER BY (p.num_comments + p.num_likes + p.num_shares) DESC
                    LIMIT ?
                """, (min_engagement, limit))
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return jsonify({
                    "success": True,
                    "data": results,
                    "columns": columns
                })
                
            except Exception as e:
                # Log detailed error info
                self._log_error("Failed to fetch trending posts", e)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/reset_database', methods=['POST'])
        def reset_database():
            """Reset database with retry mechanism for file lock issues"""
            import time
            
            max_retries = 5
            retry_delay = 1.0  # 初始延迟 1 秒
            
            for attempt in range(max_retries):
                try:
                    # Close existing connections if any
                    # Note: using thread-safe connections, no global connection to close
                    
                    # 等待一小段时间，让其他进程释放文件锁
                    if attempt > 0:
                        wait_time = retry_delay * (2 ** (attempt - 1))  # 指数退避
                        print(f"⏳ Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                    
                    # Delete database file
                    if os.path.exists(self.db_path):
                        try:
                            os.remove(self.db_path)
                            print(f"🗑️ Deleted database file: {self.db_path}")
                        except PermissionError as e:
                            if attempt < max_retries - 1:
                                print(f"⚠️ Database file locked, retry {attempt + 1}/{max_retries}: {e}")
                                continue
                            else:
                                raise
                    
                    # Delete related files
                    for suffix in ['-wal', '-shm', '-journal']:
                        aux_file = self.db_path + suffix
                        if os.path.exists(aux_file):
                            try:
                                os.remove(aux_file)
                                print(f"🗑️ Deleted auxiliary file: {aux_file}")
                            except (PermissionError, OSError) as e:
                                # 辅助文件删除失败不是致命错误
                                print(f"⚠️ Could not delete {aux_file}: {e}")
                    
                    # Reinitialize database connection
                    self._init_database()
                    
                    return jsonify({
                        "success": True,
                        "message": "Database reset successfully"
                    })
                    
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        # 继续重试
                        continue
                    else:
                        # 最后一次尝试失败
                        error_msg = f"Database file is locked after {max_retries} attempts. Please ensure all processes are stopped before starting a new demo."
                        self._log_error(error_msg, e)
                        return jsonify({
                            "success": False,
                            "error": error_msg,
                            "details": str(e)
                        }), 500
                        
                except Exception as e:
                    # 其他错误，不重试
                    self._log_error("Failed to reset database", e)
                    return jsonify({
                        "success": False,
                        "error": str(e)
                    }), 500
            
            # 理论上不会到达这里
            return jsonify({
                "success": False,
                "error": "Unexpected error in reset_database"
            }), 500
        
        @self.app.route('/opinion_balance/stats', methods=['GET'])
        def get_opinion_balance_stats():
            """Get opinion balance system stats"""
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Check if tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('opinion_monitoring', 'opinion_interventions', 'agent_responses')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                stats = {
                    "enabled": True,
                    "monitoring": {"total_posts_monitored": 0, "intervention_needed": 0, "intervention_rate": 0},
                    "interventions": {"total_interventions": 0, "average_effectiveness": 0, "total_agent_responses": 0}
                }
                
                if 'opinion_monitoring' in tables:
                    cursor.execute('SELECT COUNT(*) FROM opinion_monitoring')
                    total_monitored = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT COUNT(*) FROM opinion_monitoring WHERE requires_intervention = 1')
                    intervention_needed = cursor.fetchone()[0]
                    
                    stats["monitoring"] = {
                        "total_posts_monitored": total_monitored,
                        "intervention_needed": intervention_needed,
                        "intervention_rate": intervention_needed / max(total_monitored, 1)
                    }
                
                if 'opinion_interventions' in tables:
                    cursor.execute('SELECT COUNT(*) FROM opinion_interventions')
                    total_interventions = cursor.fetchone()[0]
                    
                    cursor.execute('SELECT AVG(effectiveness_score) FROM opinion_interventions WHERE effectiveness_score IS NOT NULL')
                    avg_effectiveness = cursor.fetchone()[0] or 0
                    
                    stats["interventions"]["total_interventions"] = total_interventions
                    stats["interventions"]["average_effectiveness"] = avg_effectiveness
                
                if 'agent_responses' in tables:
                    cursor.execute('SELECT COUNT(*) FROM agent_responses')
                    total_agent_responses = cursor.fetchone()[0]
                    stats["interventions"]["total_agent_responses"] = total_agent_responses
                
                return jsonify({
                    "success": True,
                    "stats": stats
                })
                
            except Exception as e:
                # Log detailed error info
                self._log_error("Failed to fetch opinion balance stats", e)
                return jsonify({"error": str(e)}), 500
    
    def start(self):
        """Start database service"""
        if self.is_running:
            print("⚠️ Database service is already running")
            return
        
        def run_server():
            try:
                # 使用 werkzeug 的 serving 来避免 socket 问题
                from werkzeug.serving import make_server
                server = make_server('127.0.0.1', self.port, self.app, threaded=True)
                print("🚀 Database service started")
                print(f"   🌐 URL: http://127.0.0.1:{self.port}")
                print(f"   📊 Health check: http://127.0.0.1:{self.port}/health")
                server.serve_forever()
            except Exception as e:
                print(f"❌ Failed to start database service: {e}")
                import traceback
                traceback.print_exc()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for service to start
        time.sleep(2)
        
        self.is_running = True
    
    def stop(self):
        """Stop database service"""
        if not self.is_running:
            print("⚠️ Database service is not running")
            return
        
        self.is_running = False
        print("🛑 Database service stopped")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        # Note: using thread-safe connections, no global connection to close
        print("🧹 Database service cleanup complete")


def start_database_service(db_path: str = None, port: int = 5000):
    """Start database service"""
    service = DatabaseService(db_path, port)
    service.start()
    return service


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database service')
    parser.add_argument('--db', type=str, help='Database file path')
    parser.add_argument('--port', type=int, default=5000, help='Service port')
    
    args = parser.parse_args()
    
    # Start database service
    service = start_database_service(args.db, args.port)
    
    try:
        print("📊 Database service running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping database service...")
        service.cleanup()
