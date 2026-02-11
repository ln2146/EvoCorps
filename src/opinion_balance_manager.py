"""
Opinion balance system manager - Integrated into the existing social simulation system
Monitor extreme content and automatically trigger agent group responses
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import sqlite3

from agents.simple_coordination_system import SimpleCoordinationSystem, workflow_logger


class OpinionBalanceManager:
    """Opinion balance system manager"""
    
    def __init__(self, config: Dict[str, Any], db_connection: sqlite3.Connection):
        self.config = config
        self.conn = db_connection

        # Read directly from the passed config to ensure user selection takes effect
        self.balance_config = config.get('opinion_balance_system', {})

        # System switches - using user selection from passed config
        self.enabled = self.balance_config.get('enabled', False)
        self.monitoring_enabled = self.balance_config.get('monitoring_enabled', True)
        self.feedback_enabled = self.balance_config.get('feedback_system_enabled', True)  # Feedback and iteration system switch

        # Config parameters
        self.intervention_threshold = self.balance_config.get('intervention_threshold', 2)
        self.max_responses_per_post = self.balance_config.get('max_responses_per_post', 5)
        self.effectiveness_tracking = self.balance_config.get('effectiveness_tracking', True)
        # Separate trending posts scan interval and feedback monitoring interval
        self.trending_posts_scan_interval = self.balance_config.get('trending_posts_scan_interval', 1)  # Default 1 minute
        self.feedback_monitoring_interval = self.balance_config.get('feedback_monitoring_interval', 30)  # Default 30 minutes

        # Display system config status
        print(f"📊 Opinion Balance System Config:")
        print(f"   System Enabled: {'✅' if self.enabled else '❌'}")
        print(f"   Monitoring Enabled: {'✅' if self.monitoring_enabled else '❌'}")
        print(f"   Feedback Iteration: {'✅' if self.feedback_enabled else '❌'}")
        print(f"   Trending Posts Scan Interval: {self.trending_posts_scan_interval} minutes")
        print(f"   Feedback Monitoring Interval: {self.feedback_monitoring_interval} minutes")

        # Display corresponding information based on user selection
        if not self.enabled:
            print("   ⚠️  Opinion balance system is disabled")
        elif not self.monitoring_enabled:
            print("   ⚠️  Monitoring function is disabled, using basic function only")
        
        # Initialize agent coordination system
        if self.enabled:
            self.coordination_system = SimpleCoordinationSystem(db_connection=self.conn)
            logging.info("Opinion balance system enabled")
        else:
            self.coordination_system = None
            logging.info("Opinion balance system disabled")
        
        # Monitor status
        self.monitored_posts = {}  # post_id -> monitoring_data
        self.intervention_history = []
        
        # Create database tables
        self._init_database_tables()
    
    def _init_database_tables(self):
        """Initialize database tables related to the opinion balance system."""
        try:
            cursor = self.conn.cursor()

            # Monitoring records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS opinion_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                content TEXT,
                extremism_level INTEGER,
                sentiment TEXT,
                requires_intervention BOOLEAN,
                monitoring_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Intervention records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS opinion_interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_post_id INTEGER,
                action_id TEXT,
                strategy_id TEXT,
                leader_response_id INTEGER,
                intervention_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                effectiveness_score REAL
            )
            ''')

            # Agent response records table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intervention_id INTEGER,
                agent_role TEXT,
                response_post_id INTEGER,
                response_comment_id TEXT,
                response_delay_minutes INTEGER,
                authenticity_score REAL,
                response_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Add missing columns to existing tables (if absent)
            try:
                # Check whether the column already exists
                cursor.execute("PRAGMA table_info(agent_responses)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'response_comment_id' not in columns:
                    cursor.execute('ALTER TABLE agent_responses ADD COLUMN response_comment_id TEXT')
            except Exception as e:
                # Column already exists or other error; ignore
                pass

            self.conn.commit()

        except sqlite3.OperationalError as e:
            logging.error(f"Database error in _init_database_tables: {e}")
            # If this is a database connection issue, skip table initialization
            if "unable to open database file" in str(e):
                logging.warning(f"Skipping database table initialization due to connection issue")
                return
            else:
                raise e
    
    async def monitor_post(self, post_id: int, content: str, user_id: int, force_intervention: bool = False) -> Optional[Dict[str, Any]]:
        """Monitor a single post to determine if intervention is required."""
        if not self.enabled or not self.monitoring_enabled:
            return None
       
        try:
            # If an external source already flagged extreme content, skip analysis
            if force_intervention:
                print(f"\n🚨 External system flagged extreme content; forcing intervention!")
                print("=" * 60)
                print(f"📍 Post ID: {post_id}")
                print(f"👤 User: {user_id}")
                print(f"📝 Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                print("=" * 60)
                
                # Construct a synthetic alert for intervention
                alert = {
                    "urgency_level": "high",
                    "requires_immediate_action": True,
                    "detected_issues": ["extreme_content"]
                }
                
                # Trigger intervention
                intervention_result = await self._trigger_intervention(post_id, content, user_id, alert)
                return intervention_result
           
            # Use the Analyst Agent to analyze the content
            analysis_result = await self.coordination_system.analyst.analyze_content(
                content, f"post_{post_id}"
            )
            
            if not analysis_result["success"]:
                logging.warning(f"Post {post_id} analysis failed: {analysis_result.get('error', 'Unknown error')}")
                return None
           
            analysis = analysis_result["analysis"]
           
            # Record monitoring results
            self._record_monitoring(post_id, content, analysis)
           
            # Determine if intervention is required
            if analysis_result["alert_generated"]:
                alert = analysis_result["alert"]

                # Display detected extreme content information
                print(f"\n🚨 Extreme content detected!")
                print("=" * 60)
                print(f"📍 Post ID: {post_id}")
                print(f"👤 User: {user_id}")
                print(f"📝 Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                print(f"⚠️  Extremism level: {analysis['extremism_level']}")
                print(f"🎯 Urgency: {alert.get('urgency_level', 'N/A')}")
                print("=" * 60)

                logging.info(f"Detected content requiring intervention - Post ID: {post_id}, Extremism level: {analysis['extremism_level']}")

                # Trigger intervention
                intervention_result = await self._trigger_intervention(post_id, content, user_id, alert)
                return intervention_result
            else:
                logging.debug(f"Post {post_id} does not require intervention - Extremism level: {analysis['extremism_level']}")
                return None
               
        except Exception as e:
            logging.error(f"Error while monitoring post {post_id}: {e}")
            return None
    
    def _record_monitoring(self, post_id: int, content: str, analysis: Dict[str, Any]):
        """Record monitoring results to the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO opinion_monitoring 
            (post_id, content, extremism_level, sentiment, requires_intervention)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            post_id,
            content,
            analysis.get('extremism_level', 0),
            analysis.get('sentiment', 'neutral'),
            analysis.get('requires_intervention', False)
        ))
        self.conn.commit()
    
    async def _trigger_intervention(
        self,
        original_post_id: str,
        content: str,
        original_user_id: str,
        alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger an opinion balance intervention using the full three-phase workflow."""
        try:
            workflow_logger.info(f"Starting opinion balance intervention for post {original_post_id}")

            # Fetch the current time step (when the comment was posted)
            current_time_step = None
            try:
                cursor = self.conn.cursor()
                cursor.execute('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                result = cursor.fetchone()
                if result and result[0] is not None:
                    current_time_step = result[0]
            except Exception:
                pass
            
            # === Step 1: Use the pre-analyzed alert to skip redundant analysis ===
            workflow_result = await self.coordination_system.execute_workflow(
                content,
                f"intervention_post_{original_post_id}",
                monitoring_interval=self.feedback_monitoring_interval,
                enable_feedback=self.feedback_enabled,
                force_intervention=True,  # Force intervention, skip additional analysis
                pre_analyzed_alert=alert,  # Pass the already-analyzed alert
                time_step=current_time_step  # Supply the current time step
            )

            if not workflow_result["success"]:
                workflow_logger.error(f"Intervention workflow failed: {workflow_result.get('error', 'Unknown error')}")
                return {"success": False, "error": workflow_result.get("error")}

            # === Step 2: Extract workflow results (skip redundant checks) ===
            phases = workflow_result.get("phases", {})
            phase2 = phases.get("phase_2", {})
            phase3 = phases.get("phase_3", {})

            leader_content = phase2.get("leader_content", {})
            leader_post_id = None

            # Retrieve the leader comment ID from phase2 results (if _save_leader_comment_to_database succeeded)
            if leader_content and leader_content.get("success", False):
                leader_post_id = leader_content.get("comment_id") or None

            amplifier_responses = phase2.get("amplifier_responses", [])
            successful_responses = [r for r in amplifier_responses if r.get("success")]

            effectiveness_score = phase3.get("effectiveness_score", 0)

            # === Step 4: Log to the database ===
            intervention_id = self._record_intervention(
                original_post_id=original_post_id,
                action_id=workflow_result["action_id"],
                strategy_id=phases.get("phase_1", {}).get("strategy", {}).get("strategy", {}).get("strategy_id"),
                leader_response_id=leader_post_id,
                effectiveness_score=effectiveness_score
            )

            # === Step 5: Compile and return results ===
            return {
                "success": True,
                "intervention_id": intervention_id,
                "leader_post_id": leader_post_id,
                "amplifier_responses_count": len(successful_responses),
                "total_responses": len(successful_responses) + (1 if leader_post_id else 0),
                "effectiveness_score": effectiveness_score,
                "coordination_system": "SimpleCoordinationSystem"
            }

        except Exception as e:
            logging.error(f"Error while triggering intervention: {e}")
            return {"success": False, "error": str(e)}

    
    def _create_agent_post(self, content: str, agent_role: str, original_post_id: int, response_type: str = "amplifier") -> Optional[int]:
        """Create a post that represents an agent response."""
        try:
            cursor = self.conn.cursor()
            
            # Create a virtual agent-user ID (use negative IDs to distinguish)
            agent_user_id = self._get_or_create_agent_user(agent_role)
            
            # Fetch the intervention ID
            intervention_id = None
            if original_post_id:
                cursor.execute('''
                    SELECT id FROM opinion_interventions 
                    WHERE original_post_id = ? 
                    ORDER BY intervention_timestamp DESC 
                    LIMIT 1
                ''', (original_post_id,))
                result = cursor.fetchone()
                if result:
                    intervention_id = result[0]
            
            # Generate a formatted post ID first
            from utils import Utils
            post_id = Utils.generate_formatted_id("post", self.conn)
            
            # Insert the post and mark it as an agent response
            summary_text = " ".join(content.split()[:20])
            try:
                cursor.execute('''
                INSERT INTO posts (
                    post_id, author_id, content, summary, created_at, is_news, status, original_post_id,
                    is_agent_response, agent_role, agent_response_type, intervention_id,
                    num_likes, num_shares, num_flags, num_comments
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_id,
                agent_user_id,
                content,
                summary_text,
                datetime.now().isoformat(),
                False,
                'active',
                original_post_id,
                True,  # Flag as agent response
                agent_role,
                response_type,
                intervention_id,
                0, 0, 0, 0  # Initialize counters
            ))
            except sqlite3.OperationalError:
                cursor.execute('''
                    INSERT INTO posts (
                        post_id, author_id, content, created_at, is_news, status, original_post_id,
                        is_agent_response, agent_role, agent_response_type, intervention_id,
                        num_likes, num_shares, num_flags, num_comments
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_id,
                    agent_user_id,
                    content,
                    datetime.now().isoformat(),
                    False,
                    'active',
                    original_post_id,
                    True,
                    agent_role,
                    response_type,
                    intervention_id,
                    0, 0, 0, 0
                ))
            
            self.conn.commit()

            logging.debug(f"createAgent post - ID: {post_id}, Role: {agent_role}, response type: {response_type}")

            # Trigger auto-export
            try:
                try:
                    from src.auto_export_manager import on_post_created
                except ImportError:
                    from auto_export_manager import on_post_created
                on_post_created(post_id, agent_user_id)
            except Exception as e:
                pass  # Silently ignore export errors so the main function continues

            # Trigger scenario-specific export
            try:
                try:
                    from src.scenario_export_manager import on_post_created_scenario
                except ImportError:
                    from scenario_export_manager import on_post_created_scenario
                on_post_created_scenario(post_id, agent_user_id)
            except Exception as e:
                pass  # Silently ignore export errors so the main function continues

            return post_id
            
        except Exception as e:
            logging.error(f"Agent post creation failed: {e}")
            return None

    def _create_agent_comment(self, content: str, agent_role: str, original_post_id: str) -> Optional[str]:
        """
        [Deprecated] Create an agent comment. Handled centrally via SimpleCoordinationSystem.
        Kept for backward compatibility but not used in practice.
        """
        try:
            from utils import Utils
            cursor = self.conn.cursor()

            # Create a virtual agent user ID
            agent_user_id = self._get_or_create_agent_user(agent_role)

            # Generate a comment ID
            comment_id = Utils.generate_formatted_id("comment", self.conn)

            # Use the supplied post ID directly (should already be correctly formatted)
            actual_post_id = original_post_id

            # Validate that the post exists and fetch content
            cursor.execute('SELECT post_id, content FROM posts WHERE post_id = ?', (actual_post_id,))
            post_result = cursor.fetchone()
            if not post_result:
                logging.error(f"Missing post: {actual_post_id}")
                return None

            post_content = post_result[1]

            # Use the original LLM content directly, without enhanced generation
            final_content = content

            # Insert the comment into the comments table
            cursor.execute('''
                INSERT INTO comments (comment_id, content, post_id, author_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                comment_id,
                final_content,  # Using the enhanced content
                actual_post_id,  # Using the actual post ID
                agent_user_id,
                datetime.now()
            ))

            # Update the original post's comment count
            cursor.execute('''
                UPDATE posts
                SET num_comments = num_comments + 1
                WHERE post_id = ?
            ''', (actual_post_id,))

            self.conn.commit()

            # Validate that the comment creation succeeded
            cursor.execute('SELECT COUNT(*) FROM comments WHERE comment_id = ?', (comment_id,))
            comment_exists = cursor.fetchone()[0] > 0

            if comment_exists:
                logging.debug(f"✅ Agent comment created successfully - ID: {comment_id}, Role: {agent_role}, Post: {original_post_id}")

                # Trigger auto-export
                try:
                    try:
                        from src.auto_export_manager import on_comment_created
                    except ImportError:
                        from auto_export_manager import on_comment_created
                    on_comment_created(comment_id, agent_user_id)
                except Exception as e:
                    pass  # Silently ignore export errors so the main function continues

                # Trigger scenario-specific export
                try:
                    try:
                        from src.scenario_export_manager import on_comment_created_scenario
                    except ImportError:
                        from scenario_export_manager import on_comment_created_scenario
                    on_comment_created_scenario(comment_id, agent_user_id)
                except Exception as e:
                    pass  # Silently ignore export errors so the main function continues
            else:
                logging.error(f"❌ Agent comment creation validation failed - ID: {comment_id}")

            return comment_id

        except Exception as e:
            logging.error(f"Agent comment creation failed: {e}")
            return None
    
    def _get_or_create_agent_user(self, agent_role: str) -> str:
        """Retrieve or create a virtual agent user."""
        cursor = self.conn.cursor()

        # Use a user- prefix to masquerade as a regular user
        import hashlib
        seed = f"amplifier_{agent_role}_{datetime.now().strftime('%Y%m%d')}"
        hash_obj = hashlib.md5(seed.encode())
        user_suffix = hash_obj.hexdigest()[:6]
        agent_user_id = f"user-{user_suffix}"

        # Check whether the user already exists
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (agent_user_id,))
        if cursor.fetchone():
            return agent_user_id

        # Create a new virtual agent user with a regular persona format
        fake_persona = {
            "name": f"User{user_suffix}",
            "type": "balanced",  # Marked as a balanced user
            "profession": "Various",
            "age_range": "25-45",
            "personality_traits": ["Balanced", "Thoughtful", "Constructive"],
            "agent_role": agent_role,  # Internal tag, not exposed externally
            "is_system_agent": True
        }
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, persona, creation_time)
            VALUES (?, ?, datetime('now'))
        ''', (
            agent_user_id,
            json.dumps(fake_persona, ensure_ascii=False)
        ))

        self.conn.commit()
        return agent_user_id

    def _record_intervention(self, original_post_id: int, action_id: str, strategy_id: str,
                           leader_response_id: Optional[int], effectiveness_score: float) -> int:
        """Record the intervention details in the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO opinion_interventions
            (original_post_id, action_id, strategy_id, leader_response_id, effectiveness_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            original_post_id,
            action_id,
            strategy_id,
            leader_response_id,
            effectiveness_score
        ))

        intervention_id = cursor.lastrowid
        self.conn.commit()
        return intervention_id
    
    def _calculate_basic_effectiveness_score(self, leader_post_id: int, successful_responses: list, phase2: dict) -> float:
        """Calculate a basic effectiveness score independent of monitoring data."""
        try:
            score = 0.0
            
            # 1. Leader response success (0-3 points)
            if leader_post_id:
                score += 3.0
                print(f"      ✅ Leader response success: +3.0 points")
            else:
                print(f"      ❌ Leader response failed: +0.0 points")
            
            # 2. amplifier Agent response count (0-4 points)
            amplifier_count = len(successful_responses)
            amplifier_score = min(4.0, amplifier_count * 0.8)  # 0.8 points per successful response, max 4 points
            score += amplifier_score
            print(f"      📊 amplifier responses ({amplifier_count}): +{amplifier_score:.1f} points")
            
            # 3. Content quality evaluation (0-2 points)
            quality_score = 0.0
            if phase2 and leader_post_id:
                # Check whether strategy guidance exists
                leader_content = phase2.get("leader_content", {})
                if leader_content:
                    quality_score += 1.0  # Content generated
                    # Check for strategic guidance
                    if "strategy" in phase2 or "leader_instruction" in leader_content:
                        quality_score += 1.0  # Strategic guidance present
            
            score += quality_score
            print(f"      📝 Content quality: +{quality_score:.1f} points")
            
            # 4. System integrity (0-1 point)
            system_score = 1.0 if (leader_post_id or amplifier_count > 0) else 0.0
            score += system_score
            print(f"      ⚙️ System integrity: +{system_score:.1f} points")
            
            # Clamp within a 0-10 range
            final_score = min(10.0, max(0.0, score))
            print(f"      🎯 Basic effectiveness score: {final_score:.1f}/10")
            
            return final_score
            
        except Exception as e:
            print(f"      ⚠️  Basic effectiveness score calculation failed: {e}")
            return 5.0  # Default: moderate score

    def _record_agent_response(self, intervention_id: int, agent_role: str, response_post_id: int,
                             response_comment_id: str = None, response_delay: int = 0, authenticity_score: float = 0.8):
        """Record an agent response in the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO agent_responses
            (intervention_id, agent_role, response_post_id, response_comment_id, response_delay_minutes, authenticity_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            intervention_id,
            agent_role,
            response_post_id,
            response_comment_id,
            response_delay,
            authenticity_score
        ))
        self.conn.commit()

    def get_system_stats(self) -> Dict[str, Any]:
        """Gather opinion balance system statistics."""
        if not self.enabled:
            return {"enabled": False}

        # Verify that the database connection is valid
        try:
            # Use service-mode database access
            cursor = self.conn.execute('SELECT COUNT(*) FROM opinion_monitoring')
            total_monitored = cursor.fetchone()[0]
        except Exception as e:
            return {
            "enabled": False,  # fix: return False on database errors
                "error": f"Database connection error: {e}",
                "monitoring": {"total_posts_monitored": 0},
                "interventions": {"total_interventions": 0}
            }

        # Monitoring statistics
        cursor = self.conn.execute('SELECT COUNT(*) FROM opinion_monitoring')
        total_monitored = cursor.fetchone()[0]

        cursor = self.conn.execute('SELECT COUNT(*) FROM opinion_monitoring WHERE requires_intervention = 1')
        intervention_needed = cursor.fetchone()[0]

        # Intervention statistics
        cursor = self.conn.execute('SELECT COUNT(*) FROM opinion_interventions')
        total_interventions = cursor.fetchone()[0]

        cursor = self.conn.execute('SELECT AVG(effectiveness_score) FROM opinion_interventions WHERE effectiveness_score IS NOT NULL')
        avg_effectiveness = cursor.fetchone()[0] or 0

        # Agent response statistics
        cursor = self.conn.execute('SELECT COUNT(*) FROM agent_responses')
        total_agent_responses = cursor.fetchone()[0]

        cursor = self.conn.execute('SELECT agent_role, COUNT(*) FROM agent_responses GROUP BY agent_role')
        responses_by_role = dict(cursor.fetchall())

        return {
            "enabled": True,
            "monitoring": {
                "total_posts_monitored": total_monitored,
                "intervention_needed": intervention_needed,
                "intervention_rate": intervention_needed / max(total_monitored, 1)
            },
            "interventions": {
                "total_interventions": total_interventions,
                "average_effectiveness": avg_effectiveness,
                "total_agent_responses": total_agent_responses,
                "responses_by_role": responses_by_role
            },
            "recent_interventions": len(self.intervention_history)
        }

    def print_system_summary(self):
        """Print a summary of the opinion balance system."""
        stats = self.get_system_stats()

        if not stats["enabled"]:
            logging.info("opinion_balancesystem: disabled")
            return

        logging.info("=" * 60)
        logging.info("opinion_balancesystem runtime summary")
        logging.info("=" * 60)

        monitoring = stats["monitoring"]
        logging.info("Monitoring statistics:")
        logging.info(f"  - Total monitored posts: {monitoring['total_posts_monitored']}")
        logging.info(f"  - Posts requiring intervention: {monitoring['intervention_needed']}")
        logging.info(f"  - Intervention rate: {monitoring['intervention_rate']:.1%}")

        interventions = stats["interventions"]
        logging.info("Intervention statistics:")
        logging.info(f"  - Total interventions: {interventions['total_interventions']}")
        logging.info(f"  - Average effectiveness score: {interventions['average_effectiveness']:.1f}/10")
        logging.info(f"  - Total agent responses: {interventions['total_agent_responses']}")

        if interventions["responses_by_role"]:
            logging.info("  - Responses by role:")
            for role, count in interventions["responses_by_role"].items():
                logging.info(f"    * {role}: {count}")

        logging.info("=" * 60)
