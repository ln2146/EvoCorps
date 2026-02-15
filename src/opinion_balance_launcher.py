#!/usr/bin/env python3
"""
Standalone opinion balance system launcher.
Can run the opinion balance system independently or be invoked by main.py.
"""

import os
import sys
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
import argparse
import threading

import control_flags

# HTTP control API for launcher
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Add src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database_manager import DatabaseManager
    from opinion_balance_manager import OpinionBalanceManager
    from agents.simple_coordination_system import SimpleCoordinationSystem
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    print("💡 Ensure you are running the script from the correct directory")
    sys.exit(1)


# Global launcher reference for HTTP handlers
GLOBAL_LAUNCHER = None
_auto_status_thread = None


def _auto_status_loop():
    """Timed auto-status loop shared by CLI and HTTP control.

    Runs every 30 seconds while control_flags.auto_status is True,
    printing monitoring details and running a synchronous monitoring
    pass. Exits automatically when auto_status is no longer True.
    """
    global GLOBAL_LAUNCHER

    if GLOBAL_LAUNCHER is None:
        print("❌ GLOBAL_LAUNCHER is not initialized; auto-status loop cannot run")
        return

    launcher = GLOBAL_LAUNCHER

    import time
    import traceback

    cycle_count = 0
    print("🔄 Auto-status loop started (every 30 seconds; controlled by control_flags.auto_status)")

    while True:
        if not control_flags.auto_status:
            print("🔍 auto_status is not True; stopping auto-status loop")
            break

        time.sleep(30)
        cycle_count += 1

        print(f"\n⏰ [{time.strftime('%H:%M:%S')}] Timed status update (cycle {cycle_count}):")
        print(f"📊 System status: {'running' if control_flags.auto_status else 'stopped'}")

        # 每个周期都执行详情展示和同步监控
        print("\n🔍 Current monitoring details (auto-status loop):")
        try:
            launcher._show_monitoring_details()
        except Exception as e:
            print(f"   ❌ Failed to get monitoring details: {e}")
            traceback.print_exc()

        if launcher.opinion_balance_manager:
            print("\n🔍 Running opinion balance monitoring (auto-status loop)")
            try:
                launcher._monitor_trending_posts_sync()
            except Exception as e:
                print(f"   ❌ Monitoring execution failed: {e}")
                traceback.print_exc()


# FastAPI app for external control of the launcher
launcher_control_app = FastAPI(title="Opinion Balance Launcher Control API", version="1.0.0")


class AutoStatusRequest(BaseModel):
    enabled: bool


@launcher_control_app.post("/launcher/auto-status")
def set_launcher_auto_status(body: AutoStatusRequest):
    """HTTP endpoint to control auto-status loop.

    - enabled = true: set control_flags.auto_status = True and start
      the auto-status background loop if not already running.
    - enabled = false: set control_flags.auto_status = False, loop
      will exit on the next check.
    """
    global _auto_status_thread

    # 通过端口同时支持开启和关闭：
    # enabled = true  -> 设置 auto_status=True，并确保循环在运行
    # enabled = false -> 设置 auto_status=False，循环在下一轮检查时自行退出

    control_flags.auto_status = bool(body.enabled)

    if control_flags.auto_status:
        started = False
        if _auto_status_thread is None or not _auto_status_thread.is_alive():
            _auto_status_thread = threading.Thread(
                target=_auto_status_loop,
                daemon=True,
                name="launcher-auto-status-loop",
            )
            _auto_status_thread.start()
            started = True
        return {"auto_status": True, "loop_started": started}
    else:
        loop_running = _auto_status_thread is not None and _auto_status_thread.is_alive()
        return {"auto_status": False, "loop_started": loop_running}


def start_launcher_control_api_server(host: str = "0.0.0.0", port: int = 8100) -> Optional[threading.Thread]:
    """Start the FastAPI control server for the launcher in a background thread."""

    def _run() -> None:
        config = uvicorn.Config(launcher_control_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()

    try:
        thread = threading.Thread(target=_run, daemon=True, name="launcher-control-api-server")
        thread.start()
        print(f"📡 Launcher Control API server started at http://{host}:{port}")
        return thread
    except Exception as e:
        print(f"⚠️  Failed to start Launcher Control API server: {e}")
        return None


class OpinionBalanceLauncher:
    """Standalone opinion balance system launcher."""
    
    def __init__(self, config_path: str = None, db_path: str = None):
        """
        Initialize the opinion balance system launcher.
        
        Args:
            config_path: Path to the configuration file (default: configs/experiment_config.json)
            db_path: Path to the database (default: database/simulation.db)
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'configs', 
            'experiment_config.json'
        )
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'database', 
            'simulation.db'
        )
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize the database manager
        self.db_manager = DatabaseManager(self.db_path, reset_db=False)
        self.conn = self.db_manager.get_connection()
        
        # Initialize the opinion balance manager
        self.opinion_balance_manager = None
        self.monitoring_task = None
        self.inflight_post_ids = set()
        
        # Configure logging
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ Configuration loaded: {self.config_path}")
            
            # Force-enable the opinion balance system in standalone mode
            if 'opinion_balance_system' not in config:
                config['opinion_balance_system'] = {}
            
            print(f"📋 Original config: opinion_balance_system.enabled = {config['opinion_balance_system'].get('enabled', 'not_set')}")
            print(f"📋 Original config: trending_posts_scan_interval = {config['opinion_balance_system'].get('trending_posts_scan_interval', 'not_set')}")
            print(f"📋 Original config: feedback_monitoring_interval = {config['opinion_balance_system'].get('feedback_monitoring_interval', 'not_set')}")
            print(f"📋 Original config: feedback_system_enabled = {config['opinion_balance_system'].get('feedback_system_enabled', 'not_set')}")
            
            # Force-enable the opinion balance system while keeping other settings unchanged
            config['opinion_balance_system']['enabled'] = True
            config['opinion_balance_system']['monitoring_enabled'] = True
            # Keep other configuration settings as provided
            
            print("🔧 Standalone mode: forcing the opinion balance system on")
            print(f"📋 Updated config: opinion_balance_system.enabled = {config['opinion_balance_system']['enabled']}")
            print(f"📋 Retaining config: trending_posts_scan_interval = {config['opinion_balance_system'].get('trending_posts_scan_interval', 'not_set')}")
            print(f"📋 Retaining config: feedback_monitoring_interval = {config['opinion_balance_system'].get('feedback_monitoring_interval', 'not_set')}")
            print(f"📋 Retaining config: feedback_system_enabled = {config['opinion_balance_system'].get('feedback_system_enabled', 'not_set')}")
            return config
        except FileNotFoundError:
            print(f"❌ Configuration file missing: {self.config_path}")
            # Create default config
            return self._create_default_config()
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create a default configuration."""
        # Only create defaults when the configuration file is entirely missing.
        # Keep all required opinion_balance_system fields explicit.
        from multi_model_selector import MultiModelSelector
        default_config = {
            "opinion_balance_system": {
                "enabled": True,
                "monitoring_enabled": True,
                "feedback_system_enabled": True,
                "trending_posts_scan_interval": 5,
                "feedback_monitoring_interval": 30,
                "feedback_monitoring_cycles": 3
            },
            "engine": MultiModelSelector.DEFAULT_POOL[0],
            "temperature": 0.7
        }
        
        # Save the default configuration
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Default configuration created: {self.config_path}")
        return default_config
    
    def _setup_logging(self):
        """Configure logging."""
        # Create log directory
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "opinion_balance")
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"opinion_balance_{timestamp}.log")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ],
            force=True
        )
        
        print(f"📁 Log file: {log_file}")
        logging.info("Opinion balance system logging initialized")
    
    def initialize_system(self) -> bool:
        """Initialize the opinion balance system."""
        try:
            print("\n" + "="*60)
            print("🚀 Initializing opinion balance system")
            print("="*60)
            
            # Verify the database connection
            if not self._check_database_connection():
                return False
            
            # Debug: print the configuration passed to the OpinionBalanceManager
            print(f"🔍 Debug: config passed to OpinionBalanceManager:")
            print(f"   opinion_balance_system: {self.config.get('opinion_balance_system', {})}")
            print(f"   feedback_monitoring_interval: {self.config.get('opinion_balance_system', {}).get('feedback_monitoring_interval', 'not_set')}")
            
            # Instantiate the opinion balance manager
            self.opinion_balance_manager = OpinionBalanceManager(self.config, self.conn)
            
            if not self.opinion_balance_manager.enabled:
                print("❌ Opinion balance system is disabled")
                return False
            
            # Ensure database tables are created
            self.opinion_balance_manager._init_database_tables()
            
            print("✅ Opinion balance system initialized successfully")
            print(f"   📊 Trending posts scan interval: {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
            print(f"   📊 Feedback monitoring interval: {self.opinion_balance_manager.feedback_monitoring_interval} minutes")
            print(f"   🔄 Feedback system: {'Enabled' if self.opinion_balance_manager.feedback_enabled else 'Disabled'}")
            print(f"   🎯 Intervention threshold: {self.opinion_balance_manager.intervention_threshold}")
            
            return True
            
        except Exception as e:
            print(f"❌ Opinion balance system initialization failed: {e}")
            logging.error(f"Opinion balance system initialization failed: {e}")
            return False
    
    def _check_database_connection(self) -> bool:
        """Check the database connection."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            print("✅ Database connection is healthy")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def start_monitoring(self):
        """Start opinion balance monitoring."""
        if not self.opinion_balance_manager:
            print("❌ Opinion balance system not initialized")
            return
        
        print("\n" + "="*60)
        print("🔍 Starting opinion balance monitoring")
        print("="*60)
        
        try:
            # Launch the background monitoring task
            self.monitoring_task = asyncio.create_task(self._background_monitoring())
            
            print(f"✅ Opinion balance monitoring started")
            print(f"   ⏰ Trending posts scan interval: {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
            print(f"   ⏰ Feedback monitoring interval: {self.opinion_balance_manager.feedback_monitoring_interval} minutes")
            print(f"   📊 Database: {self.db_path}")
            print(f"   🔄 Feedback system: {'Enabled' if self.opinion_balance_manager.feedback_enabled else 'Disabled'}")
            
            # Wait for the monitoring task to complete
            await self.monitoring_task
            
        except Exception as e:
            print(f"❌ Monitoring start failed: {e}")
            logging.error(f"Monitoring start failed: {e}")
    
    def start_monitoring_background(self):
        """Start the opinion balance monitoring in the background (non-blocking)."""
        if not self.opinion_balance_manager:
            print("❌ Opinion balance system not initialized")
            return False
        
        if self.monitoring_task and not self.monitoring_task.done():
            print("⚠️ Monitoring is already running")
            return True
        
        try:
            print("🔄 Launching opinion balance monitoring task...")
            
            # Start the background monitoring task
            self.monitoring_task = asyncio.create_task(self._background_monitoring())
            
            # Check that the task is actually running
            if self.monitoring_task and not self.monitoring_task.done():
                print("✅ Opinion balance monitoring has started")
                print(f"   ⏰ Trending posts scan interval: {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
                print(f"   ⏰ Feedback monitoring interval: {self.opinion_balance_manager.feedback_monitoring_interval} minutes")
                print(f"   📊 Database: {self.db_path}")
                print(f"   🔄 Feedback system: {'Enabled' if self.opinion_balance_manager.feedback_enabled else 'Disabled'}")
                print("   🔄 Monitoring task status: running")
                print(f"   📋 Task ID: {id(self.monitoring_task)}")
                print("="*60)
                return True
            else:
                print("❌ Monitoring task failed to start - unexpected task state")
                if self.monitoring_task:
                    try:
                        result = self.monitoring_task.result()
                        print(f"   📋 Task result: {result}")
                    except Exception as e:
                        print(f"   ❌ Task exception: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Monitoring start failed: {e}")
            logging.error(f"Monitoring start failed: {e}")
            return False
    
    async def _background_monitoring(self):
        """Background monitoring loop."""
        monitor_count = 0
        try:
            print(f"🔍 Opinion balance monitoring loop started – first check in {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
            print(f"   📊 Trending posts scan interval: {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
            print(f"   📊 Feedback monitoring interval: {self.opinion_balance_manager.feedback_monitoring_interval} minutes")
            print(f"   🔄 Feedback system: {'Enabled' if self.opinion_balance_manager.feedback_enabled else 'Disabled'}")
            print(f"   🎯 Intervention threshold: {self.opinion_balance_manager.intervention_threshold}")
            print("   🔄 Monitoring loop is running...")
            print("="*60)
            
            while True:
                # 全局 auto_status 是监控是否应当继续运行的唯一判定来源：
                #   True  -> 继续自动监控
                #   False/None -> 视为关闭，优雅地退出循环
                if not control_flags.auto_status:
                    print("🔍 auto_status is disabled; stopping opinion balance monitoring loop")
                    break

                # Wait for the trending posts scan interval
                await asyncio.sleep(self.opinion_balance_manager.trending_posts_scan_interval * 60)
                
                # Re-check after sleep in case auto_status was changed
                if not control_flags.auto_status:
                    print("🔍 auto_status is disabled after sleep; stopping opinion balance monitoring loop")
                    break

                monitor_count += 1
                print(f"\n🔍 [Monitoring cycle {monitor_count}] Starting opinion balance check...")
                
                # Execute monitoring checks
                await self._monitor_trending_posts()
                
                print(f"✅ [Monitoring cycle {monitor_count}] Check complete")
                
        except asyncio.CancelledError:
            print(f"🔍 Opinion balance background monitoring stopped after {monitor_count} cycles")
        except Exception as e:
            logging.error(f"Opinion balance background monitoring error: {e}")
            print(f"❌ Monitoring encountered an error: {e}")
    
    def _monitor_trending_posts_sync(self):
        """Monitor trending posts (synchronous version)."""
        try:
            cursor = self.conn.cursor()
            
            # Check that the required tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('posts', 'opinion_interventions')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'posts' not in tables:
                print("   ⚠️ 'posts' table missing; skipping monitoring")
                return
            
            # Find trending posts: those with (comments + likes + shares) >= 20
            if 'opinion_interventions' in tables:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.num_comments + p.num_likes + p.num_shares >= 20)
                    AND p.post_id NOT IN (
                        SELECT DISTINCT original_post_id
                        FROM opinion_interventions
                        WHERE original_post_id IS NOT NULL
                    )  -- Exclude already-intervened posts
                    ORDER BY (p.num_comments + p.num_likes + p.num_shares) DESC
                    LIMIT 10
                """)
            else:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.num_comments + p.num_likes + p.num_shares >= 20)
                    ORDER BY (p.num_comments + p.num_likes + p.num_shares) DESC
                    LIMIT 10
                """)
            
            trending_posts = cursor.fetchall()
            
            if trending_posts:
                print(f"   Found {len(trending_posts)} trending posts; starting analysis...")
                
                for post_row in trending_posts:
                    post_id, content, author_id, num_comments, num_likes, num_shares, created_at = post_row
                    total_engagement = num_comments + num_likes + num_shares
                    
                    # Compute the engagement delta relative to the threshold of 20
                    engagement_diff = total_engagement - 20
                    
                    print(f"\n📊 Analyzing trending post: {post_id}")
                    print(f"   👤 Author: {author_id}")
                    print(f"   💬 Comments: {num_comments}, 👍 Likes: {num_likes}, 🔄 Shares: {num_shares}")
                    print(f"   🔥 Total engagement: {total_engagement}")
                    print(f"   📈 Engagement delta: +{engagement_diff} (above threshold 20)")
                    print(f"   📝 Content preview: {content[:80]}...")
                    
                    # Decide whether to analyze based on engagement delta
                    if engagement_diff >= 0:
                        print(f"   ✅ Engagement delta {engagement_diff} meets the analysis threshold")
                    else:
                        print(f"   ⚠️ Engagement delta {engagement_diff} below threshold; skipping")
                        continue
                    
                    # Invoke the opinion balance workflow (sync version)
                    if self.opinion_balance_manager.coordination_system:
                        try:
                            print(f"   🔍 Starting opinion balance analysis and intervention flow...")
                            print(f"   🔧 Coordination system status: {type(self.opinion_balance_manager.coordination_system).__name__}")
                            
                            # Build formatted content
                            formatted_content = f"""【Trending Post Opinion Analysis】
Post ID: {post_id}
Author: {author_id}
Total engagement: {total_engagement}
Post content: {content}

Please analyze the opinion tendency of this post and whether intervention is needed."""
                            
                            print(f"   📝 Formatted content length: {len(formatted_content)} chars")
                            
                            # Get current time step (comment publication time step)
                            current_time_step = None
                            try:
                                cursor.execute('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                                result = cursor.fetchone()
                                if result and result[0] is not None:
                                    current_time_step = result[0]
                            except Exception:
                                pass
                            
                            # Execute workflow synchronously
                            print(f"   🔄 Executing opinion balance workflow...")
                            
                            # Use a thread pool to run the async workflow
                            import concurrent.futures
                            import asyncio
                            
                            def run_async_workflow():
                                async def execute_and_wait_for_monitoring():
                                    workflow_result = await self.opinion_balance_manager.coordination_system.execute_workflow(
                                        content_text=formatted_content,
                                        content_id=post_id,
                                        monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                        enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                        force_intervention=False,
                                        time_step=current_time_step
                                    )

                                    phase_3 = (
                                        workflow_result.get("phases", {}).get("phase_3", {})
                                        if isinstance(workflow_result, dict) else {}
                                    )
                                    monitoring_task_id = phase_3.get("monitoring_task_id")
                                    if monitoring_task_id:
                                        handles = getattr(
                                            self.opinion_balance_manager.coordination_system,
                                            "monitoring_task_handles",
                                            {},
                                        )
                                        handle = handles.get(monitoring_task_id) if isinstance(handles, dict) else None
                                        if handle is not None and not handle.done():
                                            print(f"   ⏳ Waiting monitoring task completion: {monitoring_task_id}")
                                            await asyncio.gather(handle, return_exceptions=True)
                                            print(f"   ✅ Monitoring task completion observed: {monitoring_task_id}")

                                    return workflow_result

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    return loop.run_until_complete(execute_and_wait_for_monitoring())
                                finally:
                                    loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async_workflow)
                                result = future.result()  # Remove timeout limit
                            
                            # Check if result is None
                            if result is None:
                                print(f"   ❌ Opinion balance workflow failed: workflow returned None")
                                print(f"   📋 Task ID: {post_id}")
                                print(f"   💡 Suggestion: check workflow logs")
                                continue
                            
                            print(f"   ✅ Opinion balance workflow completed")
                            print(f"   📋 Task ID: {post_id}")
                            
                            # Show intervention summary
                            if isinstance(result, dict):
                                intervention_summary = result.get('intervention_summary', 'No intervention summary')
                                print(f"   📊 Intervention summary: {intervention_summary}")
                            else:
                                print(f"   📊 Workflow result: {result}")
                                
                        except Exception as e:
                            print(f"   ❌ Opinion balance workflow execution failed: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"   ❌ Coordination system not initialized")
            else:
                print("   📊 No trending posts to monitor right now")
                
        except Exception as e:
            print(f"❌ Failed to monitor trending posts: {e}")
            import traceback
            traceback.print_exc()

    def _compute_feed_score(self, post_id: str, num_comments: int, num_likes: int, num_shares: int, time_step: int = None) -> float:
        """Compute feed score (same logic as AgentUser.get_feed)"""
        try:
            # Get post -> time_step mapping
            cursor = self.conn.cursor()
            try:
                cursor.execute('SELECT time_step FROM post_timesteps WHERE post_id = ?', (post_id,))
                row = cursor.fetchone()
                pstep = row[0] if row else None
            except:
                pstep = None
            
            # Get current time step
            if time_step is None:
                try:
                    cursor.execute('SELECT MAX(time_step) AS max_step FROM post_timesteps')
                    row = cursor.fetchone()
                    current_step = row[0] if row and row[0] is not None else 0
                except:
                    current_step = 0
            else:
                current_step = time_step
            
            # Feed scoring parameters (same as feed)
            lambda_decay = 0.1
            beta_bias = 180
            
            # Compute score
            eng = num_comments + num_shares + num_likes
            age = max(0, (current_step - pstep)) if (pstep is not None) else 0
            freshness = max(0.1, 1.0 - lambda_decay * age)
            score = (eng + beta_bias) * freshness
            
            return score
        except Exception as e:
            # If computation fails, return base engagement count
            return num_comments + num_likes + num_shares

    async def _monitor_trending_posts(self):
        """Monitor trending posts - using feed scoring logic"""
        try:
            cursor = self.conn.cursor()
            
            # Check required tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('posts', 'opinion_interventions', 'post_timesteps')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'posts' not in tables:
                print("   ⚠️ 'posts' table missing, skip monitoring")
                return
            
            # Fetch all posts (excluding intervened)
            if 'opinion_interventions' in tables:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.status IS NULL OR p.status != 'taken_down')
                    AND p.post_id NOT IN (
                        SELECT DISTINCT original_post_id
                        FROM opinion_interventions
                        WHERE original_post_id IS NOT NULL
                    )
                """)
            else:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.status IS NULL OR p.status != 'taken_down')
                """)
            
            all_posts = cursor.fetchall()
            
            if not all_posts:
                print("   📊 No posts to monitor right now")
                return
            
            # Compute feed score for each post and filter engagement >= 20
            posts_with_scores = []
            for post_row in all_posts:
                post_id, content, author_id, num_comments, num_likes, num_shares, created_at = post_row
                total_engagement = num_comments + num_likes + num_shares
                
                # Filter: engagement must be >= 20
                if total_engagement < 20:
                    continue
                
                feed_score = self._compute_feed_score(post_id, num_comments, num_likes, num_shares)
                
                posts_with_scores.append({
                    'post_id': post_id,
                    'content': content,
                    'author_id': author_id,
                    'num_comments': num_comments,
                    'num_likes': num_likes,
                    'num_shares': num_shares,
                    'created_at': created_at,
                    'feed_score': feed_score,
                    'total_engagement': total_engagement
                })
            
            # Sort by feed score, take top 15
            posts_with_scores.sort(key=lambda x: x['feed_score'], reverse=True)
            trending_posts = posts_with_scores[:15]
            
            if trending_posts:
                print(f"   ✅ Selected {len(trending_posts)} trending posts using feed scoring (engagement>=20, top 15 by score); starting analysis...")
                
                for post_data in trending_posts:
                    post_id = post_data['post_id']
                    content = post_data['content']
                    author_id = post_data['author_id']
                    num_comments = post_data['num_comments']
                    num_likes = post_data['num_likes']
                    num_shares = post_data['num_shares']
                    feed_score = post_data['feed_score']
                    total_engagement = post_data['total_engagement']
                    
                    print(f"\n📊 Detected trending post: {post_id}")
                    print(f"   👤 Author: {author_id}")
                    print(f"   💬 Comments: {num_comments}, 👍 Likes: {num_likes}, 🔄 Shares: {num_shares}")
                    print(f"   🔥 Total engagement: {total_engagement}")
                    print(f"   📈 Feed score: {feed_score:.2f} (based on engagement at feed time)")
                    print(f"   📝 Content: {content[:80]}...")
                    print(f"   ✅ Included for analysis (based on feed scoring)")

                    if self._should_skip_post_for_active_monitoring(post_id):
                        print(f"   ⏭️ Skip post {post_id}: workflow/monitoring already in progress")
                        continue
                    
                    # Invoke the opinion balance workflow
                    if self.opinion_balance_manager.coordination_system:
                        try:
                            print(f"   🔍 Starting opinion balance analysis and intervention flow...")
                            print(f"   🔧 Coordination system status: {type(self.opinion_balance_manager.coordination_system).__name__}")
                            
                            # Build formatted content
                            formatted_content = f"""【Trending Post Opinion Analysis】
Post ID: {post_id}
Author: {author_id}
Total engagement: {total_engagement}
Feed score: {feed_score:.2f}
Post content: {content}

Please analyze the opinion tendency of this post and whether intervention is needed."""
                            
                            print(f"   📝 Formatted content length: {len(formatted_content)} chars")
                            
                            # Start opinion balance workflow asynchronously
                            print(f"   🔄 Starting opinion balance workflow...")
                            
                            # Wait directly for the workflow to finish
                            print(f"   🔄 Executing opinion balance workflow...")
                            
                            # Get current time step (comment publication time step)
                            current_time_step = None
                            try:
                                cursor.execute('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                                result = cursor.fetchone()
                                if result and result[0] is not None:
                                    current_time_step = result[0]
                            except Exception:
                                pass
                            
                            try:
                                self.inflight_post_ids.add(post_id)
                                # Call directly and await result
                                result = await self.opinion_balance_manager.coordination_system.execute_workflow(
                                    content_text=formatted_content,
                                    content_id=post_id,
                                    monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                    enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                    force_intervention=False,
                                    time_step=current_time_step  # Pass current time step
                                )
                                
                                # Check if result is None
                                if result is None:
                                    print(f"   ❌ Opinion balance workflow returned None - possible internal error")
                                    print(f"   💡 Suggestion: check logs/workflow/workflow_*.log for details")
                                elif result.get('success'):
                                    print(f"   ✅ Opinion balance workflow completed: {result.get('action_id', 'unknown')}")
                                    print(f"   📊 Intervention result: {result.get('intervention_summary', 'No details')}")
                                else:
                                    print(f"   ❌ Opinion balance workflow failed: {result.get('error', 'unknown error')}")
                                    
                            except Exception as e:
                                print(f"   ❌ Opinion balance workflow execution exception: {e}")
                                import traceback
                                traceback.print_exc()
                            finally:
                                self.inflight_post_ids.discard(post_id)

                            print(f"   📋 Task ID: {post_id}")
                            print("="*60)
                            
                        except Exception as e:
                            print(f"   ❌ Failed to start workflow: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"   ❌ Coordination system not initialized")
            else:
                print("   📊 No trending posts to monitor right now")
                
        except Exception as e:
            print(f"❌ Failed to monitor trending posts: {e}")
            import traceback
            traceback.print_exc()

    def _monitor_trending_posts_sync(self):
        """Monitor trending posts (sync version) - using feed scoring logic"""
        try:
            cursor = self.conn.cursor()
            
            # Check required tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('posts', 'opinion_interventions', 'post_timesteps')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'posts' not in tables:
                print("   ⚠️ 'posts' table missing, skip monitoring")
                return
            
            # Fetch all posts (excluding intervened)
            if 'opinion_interventions' in tables:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.status IS NULL OR p.status != 'taken_down')
                    AND p.post_id NOT IN (
                        SELECT DISTINCT original_post_id
                        FROM opinion_interventions
                        WHERE original_post_id IS NOT NULL
                    )
                """)
            else:
                cursor.execute("""
                    SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                    FROM posts p
                    WHERE (p.status IS NULL OR p.status != 'taken_down')
                """)
            
            all_posts = cursor.fetchall()
            
            if not all_posts:
                print("   📊 No posts to monitor right now")
                return
            
            # Compute feed score for each post and filter engagement > 20
            posts_with_scores = []
            for post_row in all_posts:
                post_id, content, author_id, num_comments, num_likes, num_shares, created_at = post_row
                total_engagement = num_comments + num_likes + num_shares
                
                # Filter: engagement must be > 20
                if total_engagement <= 20:
                    continue
                
                feed_score = self._compute_feed_score(post_id, num_comments, num_likes, num_shares)
                
                posts_with_scores.append({
                    'post_id': post_id,
                    'content': content,
                    'author_id': author_id,
                    'num_comments': num_comments,
                    'num_likes': num_likes,
                    'num_shares': num_shares,
                    'created_at': created_at,
                    'feed_score': feed_score,
                    'total_engagement': total_engagement
                })
            
            # Sort by feed score, take top 15
            posts_with_scores.sort(key=lambda x: x['feed_score'], reverse=True)
            trending_posts = posts_with_scores[:15]
            
            if trending_posts:
                print(f"   ✅ Selected {len(trending_posts)} trending posts using feed scoring (engagement>20, top 15 by score); starting analysis...")
                
                for post_data in trending_posts:
                    post_id = post_data['post_id']
                    content = post_data['content']
                    author_id = post_data['author_id']
                    num_comments = post_data['num_comments']
                    num_likes = post_data['num_likes']
                    num_shares = post_data['num_shares']
                    feed_score = post_data['feed_score']
                    total_engagement = post_data['total_engagement']
                    
                    print(f"\n📊 Detected trending post: {post_id}")
                    print(f"   👤 Author: {author_id}")
                    print(f"   💬 Comments: {num_comments}, 👍 Likes: {num_likes}, 🔄 Shares: {num_shares}")
                    print(f"   🔥 Total engagement: {total_engagement}")
                    print(f"   📈 Feed score: {feed_score:.2f} (based on engagement at feed time)")
                    print(f"   📝 Content: {content[:80]}...")
                    print(f"   ✅ Included for analysis (based on feed scoring)")

                    if self._should_skip_post_for_active_monitoring(post_id):
                        print(f"   ⏭️ Skip post {post_id}: workflow/monitoring already in progress")
                        continue
                    
                    # Invoke the opinion balance workflow (sync version)
                    if self.opinion_balance_manager.coordination_system:
                        try:
                            print(f"   🔍 Starting opinion balance analysis and intervention flow...")
                            print(f"   🔧 Coordination system status: {type(self.opinion_balance_manager.coordination_system).__name__}")
                            
                            # Build formatted content
                            formatted_content = f"""【Trending Post Opinion Analysis】
Post ID: {post_id}
Author: {author_id}
Total engagement: {total_engagement}
Feed score: {feed_score:.2f}
Post content: {content}

Please analyze the opinion tendency of this post and whether intervention is needed."""
                            
                            print(f"   📝 Formatted content length: {len(formatted_content)} chars")
                            
                            # Get current time step (comment publication time step)
                            current_time_step = None
                            try:
                                cursor.execute('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                                result = cursor.fetchone()
                                if result and result[0] is not None:
                                    current_time_step = result[0]
                            except Exception:
                                pass
                            
                            # Execute workflow synchronously
                            print(f"   🔄 Executing opinion balance workflow...")
                            
                            # Use a thread pool to run the async workflow
                            import concurrent.futures
                            import asyncio
                            
                            def run_async_workflow():
                                async def execute_and_wait_for_monitoring():
                                    workflow_result = await self.opinion_balance_manager.coordination_system.execute_workflow(
                                        content_text=formatted_content,
                                        content_id=post_id,
                                        monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                        enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                        force_intervention=False,
                                        time_step=current_time_step
                                    )

                                    phase_3 = (
                                        workflow_result.get("phases", {}).get("phase_3", {})
                                        if isinstance(workflow_result, dict) else {}
                                    )
                                    monitoring_task_id = phase_3.get("monitoring_task_id")
                                    if monitoring_task_id:
                                        handles = getattr(
                                            self.opinion_balance_manager.coordination_system,
                                            "monitoring_task_handles",
                                            {},
                                        )
                                        handle = handles.get(monitoring_task_id) if isinstance(handles, dict) else None
                                        if handle is not None and not handle.done():
                                            print(f"   ⏳ Waiting monitoring task completion: {monitoring_task_id}")
                                            await asyncio.gather(handle, return_exceptions=True)
                                            print(f"   ✅ Monitoring task completion observed: {monitoring_task_id}")

                                    return workflow_result

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    return loop.run_until_complete(execute_and_wait_for_monitoring())
                                finally:
                                    loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                self.inflight_post_ids.add(post_id)
                                future = executor.submit(run_async_workflow)
                                result = future.result()  # Remove timeout limit
                            
                            # Check if result is None
                            if result is None:
                                print(f"   ❌ Opinion balance workflow failed: workflow returned None")
                                print(f"   📋 Task ID: {post_id}")
                                print(f"   💡 Suggestion: check workflow logs")
                                continue
                            
                            print(f"   ✅ Opinion balance workflow completed")
                            print(f"   📋 Task ID: {post_id}")
                            
                            # Show intervention summary
                            if isinstance(result, dict):
                                intervention_summary = result.get('intervention_summary', 'No intervention summary')
                                print(f"   📊 Intervention summary: {intervention_summary}")
                            else:
                                print(f"   📊 Workflow result: {result}")
                                
                        except Exception as e:
                            print(f"   ❌ Opinion balance workflow execution failed: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            self.inflight_post_ids.discard(post_id)
                    else:
                        print(f"   ❌ Coordination system not initialized")
            else:
                print("   📊 No trending posts to monitor right now")
                
        except Exception as e:
            print(f"❌ Failed to monitor trending posts: {e}")
            import traceback
            traceback.print_exc()

    def _should_skip_post_for_active_monitoring(self, post_id: str) -> bool:
        """Skip re-triggering a post if it is already in workflow execution or feedback monitoring."""
        if post_id in self.inflight_post_ids:
            return True

        if not self.opinion_balance_manager or not self.opinion_balance_manager.coordination_system:
            return False

        monitoring_tasks = getattr(self.opinion_balance_manager.coordination_system, "monitoring_tasks", {})
        if not isinstance(monitoring_tasks, dict):
            return False

        for task in monitoring_tasks.values():
            if not isinstance(task, dict):
                continue
            if task.get("target_post_id") != post_id:
                continue
            status = task.get("status")
            if status not in {"completed", "failed", "cancelled"}:
                return True
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        if not self.opinion_balance_manager:
            return {"status": "not_initialized"}
        
        stats = self.opinion_balance_manager.get_system_stats()
        # 运行状态完全依赖全局 control_flags.auto_status：
        #   True  -> running
        #   False/None -> stopped
        run_status = "running" if control_flags.auto_status else "stopped"
        return {
            "status": run_status,
            "opinion_balance_stats": stats
        }
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            print("🛑 Opinion balance monitoring stopped")
    
    def _show_monitoring_details(self):
        """Show current monitored post details - using feed scoring logic"""
        try:
            cursor = self.conn.cursor()
            
            # Check whether posts table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('posts', 'post_timesteps')")
            tables = [row[0] for row in cursor.fetchall()]
            if 'posts' not in tables:
                print("   ⚠️ 'posts' table missing")
                return
            
            # Fetch all posts
            cursor.execute("""
                SELECT post_id, content, author_id, num_comments, num_likes, num_shares, created_at
                FROM posts 
                WHERE (status IS NULL OR status != 'taken_down')
            """)
            
            all_posts = cursor.fetchall()
            
            if not all_posts:
                print("   📭 No post data available")
                return
            
            # Compute feed score for each post and filter engagement > 20
            posts_with_scores = []
            for post_row in all_posts:
                post_id, content, author_id, num_comments, num_likes, num_shares, created_at = post_row
                total_engagement = num_comments + num_likes + num_shares
                
                # Filter: engagement must be > 20
                if total_engagement <= 20:
                    continue
                
                feed_score = self._compute_feed_score(post_id, num_comments, num_likes, num_shares)
                
                posts_with_scores.append({
                    'post_id': post_id,
                    'content': content,
                    'author_id': author_id,
                    'num_comments': num_comments,
                    'num_likes': num_likes,
                    'num_shares': num_shares,
                    'feed_score': feed_score,
                    'total_engagement': total_engagement
                })
            
            # Sort by feed score, take top 15
            posts_with_scores.sort(key=lambda x: x['feed_score'], reverse=True)
            top_posts = posts_with_scores[:15]
            
            print(f"   📋 Current feed score ranking (engagement>20, top 15 by score, based on engagement at feed time):")
            for i, post_data in enumerate(top_posts, 1):
                post_id = post_data['post_id']
                content = post_data['content']
                author_id = post_data['author_id']
                num_comments = post_data['num_comments']
                num_likes = post_data['num_likes']
                num_shares = post_data['num_shares']
                feed_score = post_data['feed_score']
                total_engagement = post_data['total_engagement']
                
                status_icon = "🔥"
                analysis_status = "✅ Included for analysis (based on feed scoring)"
                
                print(f"   {i:2d}. {status_icon} {post_id[:12]}... | Feed score: {feed_score:7.2f} | Engagement: {total_engagement:3d} | {analysis_status}")
                print(f"       👤 {author_id[:20]}... | 💬{num_comments} 👍{num_likes} 🔄{num_shares}")
                print(f"       📝 {content[:60]}...")
                print()
                
        except Exception as e:
            print(f"   ❌ Failed to get monitoring details: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_monitoring()
        if self.conn:
            self.conn.close()
        print("🧹 Resource cleanup complete")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Standalone opinion balance system launcher')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--monitor-only', action='store_true', help='Monitor only; no interactive mode')
    
    args = parser.parse_args()
    
    # Create launcher
    launcher = OpinionBalanceLauncher(
        config_path=args.config,
        db_path=args.db
    )
    # Expose launcher instance to HTTP handlers
    global GLOBAL_LAUNCHER
    GLOBAL_LAUNCHER = launcher
    
    try:
        # Initialize system
        if not launcher.initialize_system():
            print("❌ System initialization failed, exiting")
            return
        
        # Start HTTP control API for auto-status on a separate port
        start_launcher_control_api_server()
        
        if args.monitor_only:
            # Monitor-only mode
            print("🔍 Starting monitor-only mode...")
            # 在监控专用模式下，显式开启全局 auto_status，
            # 使端口/其他组件可通过该变量控制自动监控开关。
            control_flags.auto_status = True
            await launcher.start_monitoring()
        else:
            # Interactive mode
            print("\n" + "="*60)
            print("🎮 Opinion balance system interactive mode")
            print("="*60)
            print("Available commands:")
            print("  start        - Start monitoring")
            print("  status       - View status")
            print("  test         - Manually test monitoring logic")
            print("  check        - Check monitoring task status")
            print("  auto-status  - Print status on a timer (every 30 seconds)")
            print("  stop         - Stop monitoring")
            print("  quit         - Exit system")
            print("="*60)
            
            while True:
                try:
                    command = input("\nEnter command: ").strip().lower()
                    
                    if command == "start":
                        if launcher.monitoring_task and not launcher.monitoring_task.done():
                            print("⚠️ Monitoring is already running")
                        else:
                            print("🚀 Starting monitoring...")
                            # Ensure global auto_status is on when user
                            # explicitly starts monitoring from CLI.
                            control_flags.auto_status = True
                            # Call sync method directly
                            try:
                                result = launcher.start_monitoring_background()
                                if result:
                                    print("✅ Monitoring started successfully")
                                else:
                                    print("❌ Monitoring start failed")
                            except Exception as e:
                                print(f"❌ Monitoring start exception: {e}")
                                import traceback
                                traceback.print_exc()
                    
                    elif command == "status":
                        status = launcher.get_system_status()
                        print(f"\n📊 System status: {status['status']}")
                        if 'opinion_balance_stats' in status:
                            stats = status['opinion_balance_stats']
                            if stats.get('enabled'):
                                monitoring = stats.get('monitoring', {})
                                interventions = stats.get('interventions', {})
                                print(f"   📊 Posts monitored: {monitoring.get('total_posts_monitored', 0)}")
                                print(f"   🚨 Interventions needed: {monitoring.get('intervention_needed', 0)}")
                                print(f"   ⚖️ Total interventions: {interventions.get('total_interventions', 0)}")
                                print(f"   📈 Average effectiveness: {interventions.get('average_effectiveness', 0):.1f}/10")
                                
                                # Show details of currently monitored posts
                                print(f"\n🔍 Current monitoring details:")
                                launcher._show_monitoring_details()
                    
                    elif command == "test":
                        print("🧪 Manually testing monitoring logic...")
                        try:
                            # Call monitoring logic directly
                            await launcher._monitor_trending_posts()
                            print("✅ Monitoring logic test completed")
                        except Exception as e:
                            print(f"❌ Monitoring logic test failed: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    elif command == "check":
                        print("🔍 Checking monitoring task status...")
                        if launcher.monitoring_task:
                            if launcher.monitoring_task.done():
                                print("   📊 Monitoring task status: completed")
                                try:
                                    result = launcher.monitoring_task.result()
                                    print(f"   📋 Task result: {result}")
                                except Exception as e:
                                    print(f"   ❌ Task exception: {e}")
                            else:
                                print("   📊 Monitoring task status: running")
                                print(f"   🔄 Task type: {type(launcher.monitoring_task).__name__}")
                        else:
                            print("   📊 Monitoring task status: not started")
                        
                        # Check coordination system status
                        if launcher.opinion_balance_manager and launcher.opinion_balance_manager.coordination_system:
                            print("   ✅ Coordination system: initialized")
                            print(f"   🔧 Coordination system type: {type(launcher.opinion_balance_manager.coordination_system).__name__}")
                        else:
                            print("   ❌ Coordination system: not initialized")
                    
                    elif command == "auto-status":
                            print("🔄 Starting timed status printing and monitoring (every 30 seconds, Ctrl+C to stop)")
                            # 进入定时监控模式时，将全局 auto_status 标记为开启，
                            # 并在当前线程中运行共享的 auto-status 循环。
                            control_flags.auto_status = True
                            try:
                                _auto_status_loop()
                            except KeyboardInterrupt:
                                print("\n🛑 Timed status printing stopped by user")
                    
                    elif command == "stop":
                        launcher.stop_monitoring()
                        # Reflect stopped state in global flag
                        control_flags.auto_status = False
                    
                    elif command == "quit":
                        print("👋 Exiting system")
                        # Ensure auto_status is turned off on exit
                        control_flags.auto_status = False
                        break
                    
                    else:
                        print("❌ Unknown command, please enter start, status, stop, or quit")
                
                except KeyboardInterrupt:
                    print("\n👋 User interrupted, exiting system")
                    break
                except Exception as e:
                    print(f"❌ Command execution failed: {e}")
    
    finally:
        launcher.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
