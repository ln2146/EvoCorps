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
        # Only create the default configuration when the file is completely missing
        # Only create defaults when the configuration file is entirely missing
        # OpinionBalanceManager will fall back to its built-in defaults in that case
        default_config = {
            "opinion_balance_system": {
                "enabled": True,
                "monitoring_enabled": True
                # Let OpinionBalanceManager use its default values for other settings
            },
            "engine": "gemini-2.0-flash",
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
            print(f"   monitoring_interval: {self.config.get('opinion_balance_system', {}).get('monitoring_interval', 'not_set')}")
            
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
                # Wait for the trending posts scan interval
                await asyncio.sleep(self.opinion_balance_manager.trending_posts_scan_interval * 60)
                
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
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    return loop.run_until_complete(
                                        self.opinion_balance_manager.coordination_system.execute_workflow(
                                            content_text=formatted_content,
                                            content_id=post_id,
                                            monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                            enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                            force_intervention=False,
                                            time_step=current_time_step  # Pass current time step
                                        )
                                    )
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
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    return loop.run_until_complete(
                                        self.opinion_balance_manager.coordination_system.execute_workflow(
                                            content_text=formatted_content,
                                            content_id=post_id,
                                            monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                            enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                            force_intervention=False,
                                            time_step=current_time_step  # Pass current time step
                                        )
                                    )
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
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        if not self.opinion_balance_manager:
            return {"status": "not_initialized"}
        
        stats = self.opinion_balance_manager.get_system_stats()
        return {
            "status": "running" if self.monitoring_task and not self.monitoring_task.done() else "stopped",
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
    
    try:
        # Initialize system
        if not launcher.initialize_system():
            print("❌ System initialization failed, exiting")
            return
        
        if args.monitor_only:
            # Monitor-only mode
            print("🔍 Starting monitor-only mode...")
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
                        try:
                            import time
                            import asyncio
                            cycle_count = 0
                            
                            while True:
                                time.sleep(30)
                                cycle_count += 1
                                
                                print(f"\n⏰ [{time.strftime('%H:%M:%S')}] Timed status update (cycle {cycle_count}):")
                                status = launcher.get_system_status()
                                print(f"📊 System status: {status['status']}")
                                
                                if 'opinion_balance_stats' in status:
                                    stats = status['opinion_balance_stats']
                                    if stats.get('enabled'):
                                        monitoring = stats.get('monitoring', {})
                                        interventions = stats.get('interventions', {})
                                        print(f"   📊 Posts monitored: {monitoring.get('total_posts_monitored', 0)}")
                                        print(f"   🚨 Interventions needed: {monitoring.get('intervention_needed', 0)}")
                                        print(f"   ⚖️ Total interventions: {interventions.get('total_interventions', 0)}")
                                        print(f"   📈 Average effectiveness: {interventions.get('average_effectiveness', 0):.1f}/10")
                                        launcher._show_monitoring_details()
                                
                                # Run monitoring logic on the configured interval
                                if launcher.opinion_balance_manager:
                                    monitoring_interval_minutes = launcher.opinion_balance_manager.trending_posts_scan_interval
                                    # Check every 30 seconds; run monitoring when interval is reached
                                    if cycle_count * 30 >= monitoring_interval_minutes * 60:
                                        print(f"\n🔍 Running opinion balance monitoring (interval: {monitoring_interval_minutes} minutes)")
                                        try:
                                            # Use the synchronous monitoring method
                                            launcher._monitor_trending_posts_sync()
                                            cycle_count = 0  # Reset counter
                                        except Exception as e:
                                            print(f"   ❌ Monitoring execution failed: {e}")
                                            
                        except KeyboardInterrupt:
                            print("\n🛑 Timed status printing stopped")
                    
                    elif command == "stop":
                        launcher.stop_monitoring()
                    
                    elif command == "quit":
                        print("👋 Exiting system")
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
