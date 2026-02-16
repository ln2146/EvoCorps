"""
Simplified Agent Coordination System - Based on successful testing version
Implements complete three-phase workflow without LangGraph dependency
"""

import asyncio
import json
import os
import random
import logging
import uuid
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

try:
    from src.action_logs_store import ActionLogRecord, persist_action_log_record
except Exception:
    try:
        from action_logs_store import ActionLogRecord, persist_action_log_record
    except Exception:
        ActionLogRecord = None
        persist_action_log_record = None

# Add database path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
try:
    from database_manager import get_db_manager, execute_query, fetch_one, fetch_all, execute_transaction, execute_with_temp_connection
    # Import dynamic like increment module
    try:
        import sys
        import os
        src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from dynamic_like_increment import calculate_dynamic_like_increment, apply_like_increment_to_comments
    except ImportError:
        # If import fails, define no-op functions
        def calculate_dynamic_like_increment(conn, current_timestep=None):
            return 0
        def apply_like_increment_to_comments(conn, comment_ids, increment, context=""):
            return 0
except ImportError:
    try:
        # If import fails, try relative import
        from database.database_manager import get_db_manager, execute_query, fetch_one, fetch_all, execute_transaction, execute_with_temp_connection
    except ImportError:
        # Final fallback - direct import
        import importlib.util
        import sys
        database_path = os.path.join(os.path.dirname(__file__), '..', 'database')
        if database_path not in sys.path:
            sys.path.insert(0, database_path)
        try:
            from database_manager import get_db_manager, execute_query, fetch_one, fetch_all, execute_transaction, execute_with_temp_connection
        except ImportError:
            # If still fails, use dynamic import
            spec = importlib.util.spec_from_file_location("database_manager", os.path.join(os.path.dirname(__file__), '..', 'database', 'database_manager.py'))
            database_manager = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(database_manager)
            get_db_manager = database_manager.get_db_manager
            execute_query = database_manager.execute_query
            fetch_one = database_manager.fetch_one
            fetch_all = database_manager.fetch_all
            execute_transaction = database_manager.execute_transaction
            execute_with_temp_connection = database_manager.execute_with_temp_connection

# Configure workflow-specific logging
def setup_workflow_logger():
    """Set up workflow-specific logger."""
    # Ensure logs/workflow directory exists - fix path
    script_dir = Path(__file__).parent.parent.parent  # Public-opinion-balance directory
    workflow_log_dir = script_dir / "logs" / "workflow"
    workflow_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create workflow-specific logger
    workflow_logger = logging.getLogger('workflow')
    workflow_logger.setLevel(logging.INFO)
    
    # Disable propagation to parent logger to avoid terminal output
    workflow_logger.propagate = False
    
    # Avoid adding duplicate handlers
    if not workflow_logger.handlers:
        # Create file handler using absolute path
        log_file = workflow_log_dir.absolute() / f"workflow_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler
        workflow_logger.addHandler(file_handler)
        
        # Ensure log file is created
        workflow_logger.info(f"📁 Workflow log file: {log_file}")
    
    return workflow_logger

# Initialize workflow logger
workflow_logger = setup_workflow_logger()

# Test whether workflow logger works
workflow_logger.info("🔧 Workflow logging system initialized")

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_leader_agent import EnhancedLeaderAgent, ArgumentDatabase



class SimpleAnalystAgent:
    """Simplified Analyst Agent - Supports continuous monitoring"""
    
    def __init__(self, agent_id: str = "analyst_main"):
        self.agent_id = agent_id
        # Use MultiModelSelector to create optimized client
        try:
            from multi_model_selector import multi_model_selector
            self.client, self.model = multi_model_selector.create_openai_client(role="analyst")
            workflow_logger.info(f"✅ AnalystAgent using MultiModelSelector to create optimized client")
        except Exception as e:
            workflow_logger.info(f"⚠️ AnalystAgent MultiModelSelector init failed: {e}, using selector fallback")
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (analyst role)
            selector = MultiModelSelector()
            self.client, self.model = selector.create_openai_client(role="analyst")
        self.analysis_history = []

        # Continuous monitoring related attributes
        self.monitoring_active = False
        self.monitoring_tasks = {}
        self.extremism_threshold = 2  # Default extremism standard
        
    async def start_continuous_monitoring(self, extremism_threshold: int = 2,
                                        monitoring_interval: int = 0) -> str:
        """Start continuous monitoring system

        Args:
            extremism_threshold: Extremism standard (0-4 level)
            monitoring_interval: Monitoring interval (seconds)
        """
        self.extremism_threshold = extremism_threshold

        monitor_id = f"monitor_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        workflow_logger.info(f"🔍 Start analyst continuous monitoring system")
        workflow_logger.info(f"   📋 Monitor ID: {monitor_id}")
        workflow_logger.info(f"   📊 Extremism threshold: {extremism_threshold} and above")
        workflow_logger.info(f"   ⏰ Monitoring interval: {monitoring_interval} seconds")

        monitoring_task = {
            "monitor_id": monitor_id,
            "extremism_threshold": extremism_threshold,
            "monitoring_interval": monitoring_interval,
            "start_time": datetime.now(),
            "alerts_generated": [],
            "total_analyzed": 0
        }

        self.monitoring_tasks[monitor_id] = monitoring_task
        self.monitoring_active = True
        
        # startasyncmonitoring_loop
        asyncio.create_task(self._continuous_monitoring_loop(monitor_id))
        
        return monitor_id
    
    async def _continuous_monitoring_loop(self, monitor_id: str):
        """Continuous monitoring loop"""
        task = self.monitoring_tasks.get(monitor_id)
        if not task:
            return
        
        try:
            monitoring_count = 0
            
            # Continuous monitoring, no cycle limit until stop_monitoring is called explicitly
            while self.monitoring_active:
                monitoring_count += 1
                
                workflow_logger.info(f"\n🔍 Monitoring cycle {monitoring_count} - Task: {monitor_id}")
                
                # Scan new content
                new_content = await self._scan_for_new_content(task)
                
                if new_content:
                    workflow_logger.info(f"   📋 Found {len(new_content)} new items")
                    
                    # Analyze each new item
                    for content_data in new_content:
                        try:
                            analysis_result = await self.analyze_content(
                                content_data["content"], 
                                content_data["content_id"]
                            )
                            
                            task["total_analyzed"] += 1
                            
                            if analysis_result.get("alert_generated"):
                                task["alerts_generated"].append({
                                    "timestamp": datetime.now(),
                                    "content_id": content_data["content_id"],
                                    "alert": analysis_result["alert"]
                                })
                                
                                workflow_logger.info(f"   ⚠️  Generated alert: {content_data['content_id']}")
                                
                                # Trigger downstream system (Strategist Agent)
                                await self._trigger_downstream_systems(analysis_result["alert"])
                            
                        except Exception as e:
                            workflow_logger.info(f"   ❌ Failed to analyze content: {e}")
                            continue
                else:
                    workflow_logger.info(f"   ✅ No new extreme content found")
                
                # Wait for the next monitoring cycle
                await asyncio.sleep(task["monitoring_interval"])
                
        except Exception as e:
            workflow_logger.info(f"❌ Monitoring loop error: {e}")
        finally:
            workflow_logger.info(f"⏹️  Monitoring task {monitor_id} completed")
            workflow_logger.info(f"   📊 Total monitoring cycles: {monitoring_count}")
            workflow_logger.info(f"   📋 Analyzed content count: {task['total_analyzed']}")
            workflow_logger.info(f"   ⚠️  Alerts generated: {len(task['alerts_generated'])}")
    
    async def _scan_for_new_content(self, monitoring_task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan new content - directly analyze all hot posts based on AI judgment."""
        try:
            workflow_logger.info(f"   🔍 Scanning hot posts...")

            # Find hot posts
            hot_posts = await self._find_hot_posts()

            if not hot_posts:
                workflow_logger.info(f"   📋 No hot posts found")
                return []

            workflow_logger.info(f"   📊 Found {len(hot_posts)} hot posts")

            # Return all hot posts for AI analysis
            suspicious_content = []
            for post in hot_posts:
                suspicious_content.append({
                    "content_id": post["content_id"],
                    "content": post["content"],
                    "timestamp": post["timestamp"],
                    "content_type": post["content_type"],
                    "engagement_metrics": post.get("engagement_metrics", {}),
                    "is_hot_post": True
                })

            workflow_logger.info(f"   🎯 Ready to analyze {len(suspicious_content)} hot posts")

            return suspicious_content

        except Exception as e:
            workflow_logger.info(f"   ❌ Failed to scan content: {e}")
            return []
    
    async def _find_hot_posts(self) -> List[Dict[str, Any]]:
        """Step 1: find popular posts (based on engagement, time, and other metrics)."""
        try:
            # Try to get popular posts from the database
            try:
                from pathlib import Path
                
                db_path = "database/simulation.db"
                if Path(db_path).exists():
                    # Use global database manager
                    db_manager = get_db_manager()
                    db_manager.set_database_path(db_path)
                    
                    # Define hot standard: high engagement posts within last 24 hours
                    hot_posts = fetch_all("""
                        SELECT 
                            post_id, 
                            content, 
                            created_at,
                            num_likes,
                            num_comments, 
                            num_shares,
                            'post' as content_type,
                            (num_likes + num_comments * 2 + num_shares * 3) as engagement_score
                        FROM posts 
                        WHERE created_at >= datetime('now', '-24 hours')
                        AND (num_likes + num_comments + num_shares) >= 5  -- at least 5 interactions
                        ORDER BY engagement_score DESC
                        LIMIT 20  -- top 20 hottest posts
                    """)
                    
                    if hot_posts:
                        formatted_posts = []
                        for row in hot_posts:
                            formatted_posts.append({
                                "content_id": row['post_id'],
                                "content": row['content'],
                                "timestamp": row['created_at'],
                                "content_type": row['content_type'],
                                "engagement_metrics": {
                                    "likes": row['num_likes'] or 0,
                                    "comments": row['num_comments'] or 0,
                                    "shares": row['num_shares'] or 0,
                                    "engagement_score": row['engagement_score'] or 0
                                }
                            })
                        
                        workflow_logger.info(f"      📈 Fetched {len(formatted_posts)} hot posts from database")
                        return formatted_posts
                    
            except Exception as e:
                workflow_logger.info(f"      ⚠️  Database query failed: {e}")
                return []
        
        except Exception as e:
            workflow_logger.info(f"      ❌ Failed to find hot posts: {e}")
            return []
    
    async def _trigger_downstream_systems(self, alert: Dict[str, Any]):
        """Trigger downstream system (Strategist Agent, etc.)."""
        try:
            # Should notify coordination_system to start full workflow
            workflow_logger.info(f"   🚀 Trigger downstream system to handle alert: {alert.get('content_id', 'unknown')}")
            
            # In a real application, this would call coordination_system.execute method
            # Example: coordination_system.execute_workflow(alert_content, alert['content_id'])
            
        except Exception as e:
            workflow_logger.info(f"   ❌ Failed to trigger downstream system: {e}")
    
    def stop_monitoring(self, monitor_id: str = None):
        """Stop monitoring"""
        if monitor_id:
            if monitor_id in self.monitoring_tasks:
                workflow_logger.info(f"⏹️  Stop monitoring task: {monitor_id}")
            else:
                workflow_logger.info(f"⚠️  Monitoring task does not exist: {monitor_id}")
        else:
            workflow_logger.info("⏹️  Stop all monitoring tasks")
        
        self.monitoring_active = False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "monitoring_active": self.monitoring_active,
            "active_tasks": len(self.monitoring_tasks),
            "tasks": {
                task_id: {
                    "extremism_threshold": task["extremism_threshold"],
                    "monitoring_interval": task["monitoring_interval"],
                    "alerts_generated": len(task["alerts_generated"]),
                    "total_analyzed": task["total_analyzed"],
                    "start_time": task["start_time"].isoformat()
                }
                for task_id, task in self.monitoring_tasks.items()
            }
        }
    
    async def analyze_content(self, content_data, content_id: str = None) -> Dict[str, Any]:
        """Analyze content and generate alerts - supports structured data analysis."""
        try:
            # Process structured data format
            if isinstance(content_data, dict):
                post_content = content_data.get("post_content", "")
                malicious_comments = content_data.get("malicious_comments", [])
                engagement_data = content_data.get("engagement_data", {})

                # Build analysis text, including comment like counts
                analysis_text = f"Original Post: {post_content}"
                if malicious_comments:
                    analysis_text += "\n\nMalicious Comments with Like Counts:"
                    for i, comment in enumerate(malicious_comments):
                        if isinstance(comment, dict):
                            comment_text = comment.get("content", comment.get("text", str(comment)))
                            like_count = comment.get("likes", comment.get("like_count", 0))
                            analysis_text += f"\n- Comment {i+1} (👍 {like_count} likes): {comment_text}"
                        else:
                            # If string format, default to 0 likes
                            analysis_text += f"\n- Comment {i+1} (👍 0 likes): {comment}"

                engagement_info = f"Engagement: {engagement_data.get('comments', 0)} comments, {engagement_data.get('likes', 0)} likes, {engagement_data.get('shares', 0)} shares"
                analysis_text += f"\n\n{engagement_info}"
            else:
                # Process string format
                analysis_text = str(content_data)
                engagement_data = {}
                malicious_comments = []
                post_content = analysis_text

            # Clean input text to avoid encoding issues
            cleaned_content = self._clean_text(analysis_text)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional social media content analyst. Analyze posts with comments using LIKE-BASED WEIGHTING for ALL analysis dimensions.

CRITICAL LIKE-BASED ANALYSIS FRAMEWORK:
All analysis (core viewpoint extraction, extremism assessment, sentiment calculation) must be weighted by comment like counts.

Your analysis should include:

1. CORE VIEWPOINT EXTRACTION WITH LIKE-WEIGHTING:
   - Identify the main topic/viewpoint from the original post
   - Extract viewpoints from comments, weighted by their like counts
   - HIGH-LIKED COMMENTS heavily influence the perceived core viewpoint
   - If high-liked comments shift the discussion direction, prioritize that shift
   - The final "core viewpoint" should reflect what the audience (through likes) actually cares about

2. MALICIOUS CONTENT ANALYSIS WITH LIKE-WEIGHTING:
   - Analyze extremism level (0-4 scale) with like-based weighting
   - HIGH-LIKED EXTREME COMMENTS significantly increase overall extremism level
   - Weight each comment's extremism contribution by: (comment_likes + 1) / total_weighted_likes
   - A single high-liked extreme comment (50+ likes) can push extremism from 1 to 3
   - Focus on attack patterns and rhetoric in HIGH-LIKED comments
   - LOW-LIKED extreme comments have minimal impact on overall assessment

3. ENGAGEMENT INTENSITY ASSESSMENT:
   - Evaluate how like distribution amplifies negative impact
   - High-liked negative content = HIGH amplification risk
   - Many low-liked comments = MODERATE risk

4. CONTENT ANALYSIS SUMMARY:
   - Provide a comprehensive summary of the content and discussion
   - Identify key themes and patterns in the comments
   - Note any significant shifts in discussion direction due to high-liked comments

5. INTERVENTION NECESSITY:
   - Determine if intervention is needed based on sentiment score and extremism level
   - High-liked extreme/negative content should trigger intervention even if other metrics are moderate
   - Provide specific reasoning for intervention decision

Extremism Scale (LIKE-WEIGHTED):
- 0: No extreme content (normal discussion)
- 1: Mild negative (complaints, dissatisfaction)
- 2: Moderate extreme (strong criticism, bias) → INTERVENTION THRESHOLD
- 3: High extreme (inflammatory speech, panic spreading)
- 4: Extremely dangerous (hate speech, violence incitement)

LIKE-WEIGHTING PRINCIPLE: Every analysis dimension (viewpoint, extremism, sentiment) must prioritize high-liked content. A few high-liked extreme comments are more dangerous than many low-liked ones."""
                    },
                    {
                        "role": "user",
                        "content": f"""Please analyze the following social media content and malicious comments:

{cleaned_content}

Please provide a comprehensive analysis in JSON format:
{{
    "core_viewpoint": "Main topic/viewpoint influenced by high-liked comments",
    "post_theme": "Primary theme shaped by audience engagement",
    "viewpoint_analysis": {{
        "original_post_viewpoint": "Original post perspective",
        "high_liked_comments_influence": "How high-liked comments shifted the viewpoint",
        "final_weighted_viewpoint": "Viewpoint after considering like-weighted comments"
    }},

    "malicious_analysis": {{
        "extremism_level": 0,
        "like_weighted_extremism": {{
            "post_extremism": 0,
            "comment_extremism_breakdown": [
                {{"comment_index": 1, "likes": 0, "extremism_level": 1, "weighted_contribution": 0.1}},
                {{"comment_index": 2, "likes": 50, "extremism_level": 3, "weighted_contribution": 2.5}}
            ],
            "final_calculation": "weighted average extremism calculation"
        }},
        "attack_patterns": ["pattern1", "pattern2"],
        "threat_assessment": "detailed threat analysis with like weighting"
    }},

    "engagement_metrics": {{
        "intensity_level": "LOW/MODERATE/HIGH/VIRAL",
        "amplification_risk": "assessment based on like distribution",
        "viral_potential": "potential influenced by high-liked negative content"
    }},

    "content_summary": {{
        "key_themes": "identify main discussion themes",
        "discussion_patterns": "note patterns in the conversation",
        "audience_focus": "what the audience (through likes) actually cares about"
    }},

    "intervention_analysis": {{
        "requires_intervention": false,
        "urgency_level": 1,
        "reasoning": "detailed reasoning considering all like-weighted factors",
        "recommended_approach": "specific intervention strategy",
        "trigger_factors": ["extremism_level >= 2", "sentiment_score < 0.35", "high_liked_negative_content"]
    }},

    "key_topics": ["topic1", "topic2"],
    "emotional_indicators": ["emotion1", "emotion2"]
}}"""
                    }
                ],
                temperature=0.85,  # Increase to 0.85 for more diverse analysis outputs
                response_format={"type": "json_object"}
            )

            # Safe JSON parsing response
            analysis = self._safe_json_parse(response.choices[0].message.content)

            # Process new nested JSON format data extraction with enhanced error handling
            try:
                # Extract core data - using new format
                if "malicious_analysis" in analysis:
                    # New format data extraction
                    extremism_level = analysis.get("malicious_analysis", {}).get("extremism_level", 0)
                    requires_intervention = analysis.get("intervention_analysis", {}).get("requires_intervention", False)
                    urgency_level = analysis.get("intervention_analysis", {}).get("urgency_level", 1)
                    reasoning = analysis.get("intervention_analysis", {}).get("reasoning", "")
                    recommended_action = analysis.get("intervention_analysis", {}).get("recommended_approach", "")

                    # Extract sentiment score data with enhanced parsing
                    sentiment_score = analysis.get("sentiment_distribution", {}).get("overall_sentiment_score", 0.5)
                    sentiment_reasoning = analysis.get("sentiment_distribution", {}).get("sentiment_reasoning", "")

                    # Enhanced data type conversion with validation
                    try:
                        analysis["extremism_level"] = int(float(extremism_level)) if extremism_level is not None else 0
                    except (ValueError, TypeError):
                        analysis["extremism_level"] = 0
                    
                    try:
                        analysis["urgency_level"] = int(float(urgency_level)) if urgency_level is not None else 1
                    except (ValueError, TypeError):
                        analysis["urgency_level"] = 1
                    
                    analysis["requires_intervention"] = bool(requires_intervention) if requires_intervention is not None else False
                    
                    try:
                        analysis["sentiment_score"] = float(sentiment_score) if sentiment_score is not None else 0.5
                        # Ensure sentiment score is within valid range
                        analysis["sentiment_score"] = max(0.0, min(1.0, analysis["sentiment_score"]))
                    except (ValueError, TypeError):
                        analysis["sentiment_score"] = 0.5
                    
                    analysis["sentiment_reasoning"] = str(sentiment_reasoning) if sentiment_reasoning else "No reasoning provided"
                    analysis["reasoning"] = str(reasoning) if reasoning else "Analysis completed"
                    analysis["recommended_action"] = str(recommended_action) if recommended_action else "no_action_needed"
                
                # Fallback data type conversion and validation
                if "extremism_level" not in analysis:
                    analysis["extremism_level"] = 0
                if "urgency_level" not in analysis:
                    analysis["urgency_level"] = 1
                if "requires_intervention" not in analysis:
                    analysis["requires_intervention"] = False
                if "sentiment_score" not in analysis:
                    analysis["sentiment_score"] = 0.5

            except Exception as e:
                workflow_logger.info(f"Data type processing error: {e}")
                # Using default values with enhanced error handling
                analysis["extremism_level"] = 0
                analysis["urgency_level"] = 1
                analysis["requires_intervention"] = False
                analysis["sentiment_score"] = 0.5
                analysis["sentiment_reasoning"] = "Data processing error"
                analysis["reasoning"] = "Data processing error"
                analysis["recommended_action"] = "no_action_needed"

            # Ensure list type
            if not isinstance(analysis.get("key_topics"), list):
                analysis["key_topics"] = []
            if not isinstance(analysis.get("emotional_indicators"), list):
                analysis["emotional_indicators"] = []

            # Ensure string type
            if not isinstance(analysis.get("sentiment_reasoning"), str):
                analysis["sentiment_reasoning"] = "No reasoning provided"
            if not isinstance(analysis.get("recommended_action"), str):
                analysis["recommended_action"] = "no_action_needed"
            if not isinstance(analysis.get("reasoning"), str):
                analysis["reasoning"] = "analysis_completed"

            # Record analysis history
            self.analysis_history.append({
                "timestamp": datetime.now(),
                "content_id": content_id or f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "analysis": analysis
            })

            # Restore original trigger logic - based on analyst judgment
            return {
                "success": True,
                "analysis": analysis,
                "alert_generated": analysis.get("requires_intervention", False),
                "alert": {
                    "content_id": content_id,
                    "urgency_level": analysis.get("urgency_level", 1),
                    "recommended_action": analysis.get("recommended_action", ""),
                    "trigger_content": analysis
                } if analysis.get("requires_intervention", False) else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _clean_text(self, text: str) -> str:
        """Clean text to avoid encoding issues."""
        try:
            if not text:
                return ""

            import re

            # Remove control characters but keep common whitespace
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

            # Only process actual emojis, do not affect CJK text
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "]+", flags=re.UNICODE)

            # Replace emojis with description
            cleaned = emoji_pattern.sub('[emoji]', cleaned)

            # Secure encoding process - use ignore instead of replace to avoid replacement chars
            cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')

            # Clean extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)

            # Limit length - increased to preserve more comment info
            if len(cleaned) > 5000:
                cleaned = cleaned[:5000] + "..."

            return cleaned.strip()

        except Exception:
            # If clean fails, return a safe version of original text
            try:
                return text.encode('utf-8', errors='ignore').decode('utf-8')[:5000]
            except:
                return "Content contains special characters, safely processed"

    def _safe_json_parse(self, content: str) -> Dict[str, Any]:
        """Safe JSON parsing, provide default values."""
        try:
            # First try direct parsing
            parsed = json.loads(content)

            # Ensure return type is dict
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                # If list of dicts, take the first
                return parsed[0]
            else:
                # If format is unexpected, return default values
                raise ValueError("Unexpected JSON format")

        except (json.JSONDecodeError, ValueError):
            # Try to fix common JSON format issues
            try:
                import re
                # Remove possible markdown formatting
                cleaned = re.sub(r'```json\s*|\s*```', '', content.strip())

                # Try to extract JSON portion
                json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, dict):
                        return parsed
                    elif isinstance(parsed, list) and len(parsed) > 0:
                        return parsed[0]

                # Try to fix common JSON errors
                # Remove trailing commas
                cleaned = re.sub(r',\s*}', '}', cleaned)
                cleaned = re.sub(r',\s*]', ']', cleaned)

                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return parsed

            except Exception as e:
                workflow_logger.info(f"JSON parse debug info: {e}")
                workflow_logger.info(f"Original content: {content[:200]}...")

            # Return default analysis result
            return {
                "sentiment": "neutral",
                "extremism_level": 0,
                "key_topics": ["Content parsing failed"],
                "emotional_indicators": [],
                "requires_intervention": False,
                "urgency_level": 1,
                "recommended_action": "no_action_needed",
                "reasoning": "JSON parsing failed, using default values"
            }


class SimpleStrategistAgent:
    """Simplified Strategist Agent"""

    def __init__(self, agent_id: str = "strategist_main"):
        self.agent_id = agent_id
        # Use MultiModelSelector for strategist
        try:
            from multi_model_selector import multi_model_selector
            self.client, self.model = multi_model_selector.create_openai_client(role="strategist")
            workflow_logger.info(f"✅ StrategistAgent using model: {self.model}")
        except Exception as e:
            workflow_logger.info(f"⚠️ StrategistAgent MultiModelSelector init failed: {e}, using selector fallback")
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (strategist role)
            selector = MultiModelSelector()
            self.client, self.model = selector.create_openai_client(role="strategist")
        
        # Initialize learning system related attributes
        self.learning_system = None
        self._learning_system_initialized = False
        self.strategy_history = []
        self.max_retries = 3
        self.retry_delay = 2
        # Database connection for action logging
        self.db_path = Path("learning_data/rag/rag_database.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def create_strategy(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create response strategy based on alert - Using historical experience and tree of thought reasoning"""
        action_id = f"strategist_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        for attempt in range(self.max_retries):
            try:
                result = await self._create_strategy_attempt(alert, attempt)
                # Only record successfully created strategies
                if result.get("success", False):
                    await self._log_strategist_action(action_id, "strategy_creation_completed", result, attempt + 1)
                return result
            except Exception as e:
                workflow_logger.info(f"Strategist strategy creation attempt {attempt + 1} failed: {e}")
                
                if attempt == self.max_retries - 1:
                    workflow_logger.info("All retry attempts exhausted, returning default strategy")
                    fallback_result = {
                        "success": False,
                        "error": f"After {self.max_retries} attempts: {str(e)}",
                        "strategy": self._get_default_strategy()
                    }
                    return fallback_result
                await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def _create_strategy_attempt(self, alert: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """Single attempt to create strategy"""
        try:
            workflow_logger.info("📋 Strategist Agent - start intelligent strategy creation workflow")
            
            # Step 1: Confirm received alert information
            workflow_logger.info("  ✅ Step 1: Confirm alert information")
            if not isinstance(alert, dict):
                return {"success": False, "error": "Invalid alert format"}
            
            workflow_logger.info(f"     📊 Alert ID: {alert.get('content_id', 'unknown')}")
            workflow_logger.info(f"     🚨 Urgency: {alert.get('urgency_level', 'unknown')}/4")
            workflow_logger.info(f"     📝 Recommended action: {alert.get('recommended_action', 'unknown')}")
            
            # Step 2: Query historical action result logs
            workflow_logger.info("  📚 Step 2: Query historical successful strategies")
            historical_strategies = await self._query_historical_strategies(alert)
            workflow_logger.info(f"     🔍 Found {len(historical_strategies)} related historical strategies")
            
            # Extract new-format data provided by analyst
            trigger_content = alert.get("trigger_content", {})
            
            # Extract core data from the new format
            core_viewpoint = trigger_content.get("core_viewpoint", "Unknown topic")
            post_theme = trigger_content.get("post_theme", "General discussion")
            engagement_metrics = trigger_content.get("engagement_metrics", {})
            sentiment_analysis = trigger_content.get("sentiment_distribution", {})
            malicious_analysis = trigger_content.get("malicious_analysis", {})
            
            # Ensure core viewpoint info is complete
            if not core_viewpoint or core_viewpoint == "Unknown topic":
                key_topics = trigger_content.get("key_topics", [])
                if key_topics:
                    core_viewpoint = f"Discussion about {', '.join(key_topics[:2])}"
            
            # Extract urgency_level and recommended_action from alert
            urgency_level = alert.get("urgency_level", 2)
            recommended_action = alert.get("recommended_action", "balanced_response")
            
            # Step 3: Use tree of thought to formulate step-by-step plan
            workflow_logger.info("  🧠 Step 3: Use Tree-of-Thought to plan steps")
            tot_plan = await self._create_tot_strategic_plan(alert, historical_strategies)
            workflow_logger.info(f"     ✅ Generated {len(tot_plan.get('strategic_options', []))} strategy options")
            workflow_logger.info(f"     🎯 Selected optimal option: {tot_plan.get('selected_strategy', {}).get('name', 'unknown')}")
            
            # Step 4: Format as Agent instructions
            workflow_logger.info("  📋 Step 4: Format as agent instructions")
            agent_instructions = await self._format_agent_instructions(tot_plan)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a senior strategic planner for opinion balance operations with access to historical action logs and Tree-of-Thought reasoning capabilities.

            Your enhanced role:
            - Analyze the current situation with historical context
            - Apply proven successful patterns from past actions
            - Use systematic strategic reasoning to develop multi-layered plans
            - Generate precise agent instructions based on experience

            HISTORICAL INTELLIGENCE INTEGRATION:
            - Leverage successful strategies from similar past situations
            - Adapt proven tactics to current context
            - Avoid patterns that led to failures in historical data

            TREE-OF-THOUGHT STRATEGIC FRAMEWORK:
            1. SITUATION ANALYSIS: Current context + Historical patterns
            2. STRATEGIC OPTIONS: Generate multiple strategic branches
            3. EVALUATION: Score each option against success criteria
            4. SELECTION: Choose optimal strategy with highest expected success
            5. EXECUTION PLAN: Detailed agent coordination instructions

            DYNAMIC PARAMETER DETERMINATION:
            - You MUST fully determine all output values yourself; do NOT use example numbers or placeholders
            - Determine the optimal number of agents within a fixed range:
              
              AGENT COUNT RANGE:
              * Total number of agents should be between 8 and 15 (inclusive)
              * Select a specific number within this range based on the situation severity
              
            - Decide role distribution (balanced_moderates, technical_experts, community_voices, fact_checkers) based on content analysis, risk assessment, and heat level
            - Choose timing strategy (immediate/staggered/progressive) based on urgency and heat level
            - Provide concrete coordination instructions and risk assessments
            - All values must be actionable and specific

            CRITICAL REQUIREMENT:
            - All outputs must be generated dynamically based on the scenario and historical context"""
                    },
                    {
                        "role": "user",
                        "content": f"""ENHANCED STRATEGIC INTELLIGENCE REPORT:

            CURRENT SITUATION ANALYSIS:
            - Core Viewpoint: {core_viewpoint}
            - Post Theme: {post_theme}
            - Urgency Level: {urgency_level}/4
            - Recommended Action: {recommended_action}

            MALICIOUS ATTACK INTELLIGENCE:
            - Extremism Level: {malicious_analysis.get('extremism_level', 'Unknown')}/4
            - Attack Patterns: {malicious_analysis.get('attack_patterns', ['Unknown patterns'])}
            - Threat Assessment: {malicious_analysis.get('threat_assessment', 'Moderate concern')}

            ENGAGEMENT INTELLIGENCE:
            - Intensity Level: {engagement_metrics.get('intensity_level', 'MODERATE')}
            - Amplification Risk: {engagement_metrics.get('amplification_risk', 'Standard monitoring required')}
            - Viral Potential: {engagement_metrics.get('viral_potential', 'Low to moderate spread expected')}
            
            HEAT LEVEL ANALYSIS:
            - Engagement Score: {self._calculate_heat_level(engagement_metrics, malicious_analysis)}
            - Heat Level: {self._determine_heat_level(engagement_metrics, malicious_analysis)}
            - Heat Multiplier: {self._get_heat_multiplier(engagement_metrics, malicious_analysis)}

            SENTIMENT DISTRIBUTION:
            - Overall Sentiment: {sentiment_analysis.get('overall_sentiment', 'mixed')}
            - Emotional Triggers: {sentiment_analysis.get('emotional_triggers', ['Unknown triggers'])}
            - Polarization Risk: {sentiment_analysis.get('polarization_risk', 'Moderate division potential')}

            HISTORICAL STRATEGY INTELLIGENCE:
            {self._format_historical_context(historical_strategies)}

            TREE-OF-THOUGHT STRATEGIC PLAN:
            {self._format_tot_context(tot_plan)}

            AGENT COORDINATION INSTRUCTIONS:
            {self._format_instruction_context(agent_instructions)}

            MISSION: Generate a comprehensive response strategy integrating historical intelligence and Tree-of-Thought reasoning.

            CRITICAL: You must fully determine all output values yourself. Each parameter (total_agents, role distribution, timing, risk assessment, etc.) must be dynamically generated based on the scenario. Do NOT use placeholders or example numbers.

            Return an enhanced JSON strategy in English, filling all fields with your own calculated values:
            {{
                "strategy_id": "",
                "historical_basis": {{
                    "similar_cases_count": "",
                    "best_historical_strategy": "",
                    "success_probability_estimate": ""
                }},
                "tot_reasoning": {{
                    "options_evaluated": "",
                    "selected_approach": "",
                    "decision_rationale": ""
                }},
                "situation_assessment": {{
                    "threat_level": "",
                    "primary_concern": "",
                    "strategic_priority": ""
                }},
                "core_counter_argument": "",
                "leader_instruction": {{
                    "tone": "",
                    "speaking_style": "",
                    "key_points": ["", "", ""],
                    "target_audience": "",
                    "content_length": "",
                    "style": "",
                    "core_message": "",
                    "approach": ""
                }},
                "amplifier_plan": {{
                    "total_agents": "",
                    "role_distribution": {{
                        "balanced_moderates": "",
                        "technical_experts": "",
                        "community_voices": "",
                        "fact_checkers": ""
                    }},
                    "timing_strategy": "",
                    "coordination_notes": "",
                    "decision_factors": {{
                        "urgency_level": "",
                        "controversy_level": "",
                        "misinformation_risk": "",
                        "community_impact": ""
                    }}
                }},
                "expected_outcome": "",
                "risk_assessment": ""
            }}"""
                    }
                ],
                temperature=0.88,
                response_format={"type": "json_object"}
            )

            
            strategy = self._safe_strategy_parse(response.choices[0].message.content)
            strategy["strategy_id"] = f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Add history and ToT info to strategy
            strategy["historical_basis"] = {
                "referenced_strategies": len(historical_strategies),
                "best_match_score": historical_strategies[0].get("similarity_score", 0) if historical_strategies else 0
            }
            strategy["tot_reasoning"] = tot_plan.get("reasoning_summary", {})
            strategy["agent_instructions"] = agent_instructions
            
            # Record strategy history
            self.strategy_history.append({
                "timestamp": datetime.now(),
                "alert": alert,
                "strategy": strategy,
                "historical_strategies": historical_strategies,
                "tot_plan": tot_plan
            })
            
            workflow_logger.info("  ✅ Intelligent strategy creation completed")
            workflow_logger.info(f"     📊 Strategy ID: {strategy['strategy_id']}")
            workflow_logger.info(f"     🎯 Historical references: {len(historical_strategies)} related cases")
            workflow_logger.info(f"     🧠 ToT reasoning: {len(tot_plan.get('strategic_options', []))} options evaluated")
            
            return {
                "success": True,
                "strategy": strategy,
                "leader_instruction": strategy["leader_instruction"],
                "amplifier_plan": strategy["amplifier_plan"],
                "agent_instructions": agent_instructions
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def develop_strategy(self, instruction: Dict[str, Any], content_text: str = "") -> Dict[str, Any]:
        """Develop strategy based on instruction and content - Enhanced with retry mechanism"""
        # Record strategist strategy development start action
        action_id = f"strategist_dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        # No longer record start state, only record successful results
        
        for attempt in range(self.max_retries):
            try:
                result = await self._develop_strategy_attempt(instruction, content_text, attempt)
                # Only record successfully developed strategies
                if result.get("success", False):
                    await self._log_strategist_action(action_id, "strategy_development_completed", result, attempt + 1)
                return result
            except Exception as e:
                workflow_logger.info(f"Strategist strategy development attempt {attempt + 1} failed: {e}")
                # Record failed attempts
                # Do not record failures
                
                if attempt == self.max_retries - 1:
                    workflow_logger.info("All retry attempts exhausted, returning basic fallback strategy")
                    fallback_result = {
                        "success": False,
                        "error": f"After {self.max_retries} attempts: {str(e)}",
                        "strategy": self._get_fallback_strategy(instruction, content_text)
                    }
                    # Do not record failures
                    return fallback_result
                await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def _develop_strategy_attempt(self, instruction: Dict[str, Any], content_text: str, attempt: int) -> Dict[str, Any]:
        """Single attempt to develop strategy without mock data"""
        try:
            task_type = instruction.get("task", "strategy_development")
            prompt = instruction.get("prompt", "")

            if task_type == "feedback_evaluation":
                return await self._evaluate_feedback_directly(prompt)
            elif task_type == "effectiveness_evaluation":
                return await self._evaluate_effectiveness_directly(prompt)
            else:
                return await self._develop_general_strategy(instruction, content_text)

        except Exception as e:
            raise Exception(f"Strategy development attempt {attempt + 1} failed: {str(e)}")

    async def _evaluate_feedback_directly(self, prompt: str) -> Dict[str, Any]:
        """Direct feedback evaluation without mock alert"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an experienced opinion balance strategist. Analyze the feedback report and provide strategic decisions. Respond ONLY in JSON format with English text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        strategy_data = json.loads(response.choices[0].message.content)
        return {
            "success": True,
            "strategy": strategy_data
        }

    async def _evaluate_effectiveness_directly(self, prompt: str) -> Dict[str, Any]:
        """Direct effectiveness evaluation without mock alert"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an experienced strategist evaluating action effectiveness. Provide clear evaluation and recommendations. Respond ONLY in JSON format with English text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        strategy_data = json.loads(response.choices[0].message.content)
        return {
            "success": True,
            "strategy": strategy_data
        }

    async def _develop_general_strategy(self, instruction: Dict[str, Any], content_text: str) -> Dict[str, Any]:
        """Develop general strategy based on real instruction data"""
        task_type = instruction.get("task", "general_strategy")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strategic planner. Develop strategies based on real context without using mock data. Respond ONLY in JSON format with English text."
                },
                {
                    "role": "user",
                    "content": f"""
Task Type: {task_type}
Content Context: {content_text[:500] if content_text else "No specific content provided"}
Instruction Details: {instruction}

Develop an appropriate strategy for this context. Return a JSON response with relevant strategic elements.
                    """
                }
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        strategy_data = json.loads(response.choices[0].message.content)
        return {
            "success": True,
            "strategy": strategy_data
        }

    def _get_fallback_strategy(self, instruction: Dict[str, Any], content_text: str) -> Dict[str, Any]:
        """Generate fallback strategy when all retries fail"""
        return {
            "assessment": "Strategy development failed after retries, using fallback approach",
            "needs_adjustment": False,
            "decision_type": "maintain_observation",
            "rationale": "Unable to generate dynamic strategy, maintaining current approach",
            "task_type": instruction.get("task", "unknown"),
            "context_length": len(content_text) if content_text else 0
        }

    def _safe_strategy_parse(self, content: str) -> Dict[str, Any]:
        """Safe parsing of strategy JSON - supports enhanced format."""
        try:
            strategy = json.loads(content)
            
            # Ensure return type is dict
            if isinstance(strategy, dict):
                # Validate required fields and provide default values
                if "leader_instruction" not in strategy:
                    strategy["leader_instruction"] = {
                        "tone": "professional",
                        "key_points": ["balanced perspective", "factual information", "constructive dialogue"],
                        "target_audience": "rational discussants",
                        "content_length": "150-300 characters",
                        "style": "explanatory"
                    }
                
                if "amplifier_plan" not in strategy:
                    strategy["amplifier_plan"] = {
                        "total_agents": 5,
                        "timing_strategy": "progressive",
                        "coordination_notes": "Use diverse positive personas"
                    }
                
                # Ensure amplifier_plan includes new enhanced fields
                amplifier_plan = strategy.get("amplifier_plan", {})
                if "role_distribution" not in amplifier_plan:
                    amplifier_plan["role_distribution"] = {
                        "technical_experts": 1,
                        "balanced_moderates": 2,
                        "community_voices": 1,
                        "fact_checkers": 1
                    }
                
                if "decision_factors" not in amplifier_plan:
                    amplifier_plan["decision_factors"] = {
                        "urgency_level": "moderate",
                        "controversy_level": "standard"
                    }
                
                return strategy
            
            return self._get_default_strategy()
            
        except json.JSONDecodeError:
            try:
                import re
                # Clean and fix common JSON errors
                cleaned = re.sub(r'```json\s*|\s*```', '', content.strip())
                json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if json_match:
                    strategy = json.loads(json_match.group())
                    if isinstance(strategy, dict):
                        return self._validate_and_enhance_strategy(strategy)
            except Exception as e:
                workflow_logger.info(f"JSON parse debug info: {e}")
                workflow_logger.info(f"Original content: {content[:200]}...")

            # Return enhanced default strategy
            return self._get_default_strategy()

    def _validate_and_enhance_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance strategy structure"""
        # Ensure all required fields exist
        required_fields = {
            "core_counter_argument": "Respond based on rational analysis and objective facts",
            "expected_outcome": "Guide rational discussion",
            "risk_assessment": "low_risk"
        }
        
        for field, default_value in required_fields.items():
            if field not in strategy:
                strategy[field] = default_value
        
        return strategy

    def _get_default_strategy(self) -> Dict[str, Any]:
        """Get enhanced default strategy"""
        return {
            "strategy_id": f"default_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "situation_assessment": {
                "threat_level": "moderate",
                "primary_concern": "maintaining balanced discussion",
                "strategic_priority": "balanced"
            },
            "core_counter_argument": "Respond based on rational analysis and objective facts",
            "leader_instruction": {
                "tone": "professional_rational",
                "speaking_style": "fact-based",
                "key_points": ["objective_analysis", "rational_discussion", "balanced_perspective"],
                "target_audience": "rational users",
                "content_length": "150-300 words",
                "style": "argumentative_essay",
                "core_message": "Provide balanced perspectives and factual information",
                "approach": "diplomatic and informative"
            },
            "amplifier_plan": {
                "total_agents": 5,
                "role_distribution": {
                    "technical_experts": 1,
                    "balanced_moderates": 2,
                    "community_voices": 1,
                    "fact_checkers": 1
                },
                "timing_strategy": "gradual_release",
                "coordination_notes": "using diverse positive community roles",
                "decision_factors": {
                    "urgency_level": "moderate",
                    "controversy_level": "standard"
                }
            },
            "expected_outcome": "Guide rational discussion",
            "risk_assessment": "low_risk"
        }

    async def _query_historical_strategies(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query historical action result logs, find most successful strategies for similar cases."""
        try:
            def _get_thresholds() -> tuple[float, float]:
                sim_th = 0.7
                eff_th = 0.7

                diagnosis = getattr(self.learning_system, "last_recommendation_diagnosis", None)
                if isinstance(diagnosis, dict):
                    try:
                        if diagnosis.get("similarity_threshold") is not None:
                            sim_th = float(diagnosis.get("similarity_threshold"))
                    except Exception:
                        pass
                    try:
                        if diagnosis.get("effectiveness_threshold") is not None:
                            eff_th = float(diagnosis.get("effectiveness_threshold"))
                    except Exception:
                        pass

                cfg = getattr(self.learning_system, "config", None)
                if isinstance(cfg, dict):
                    try:
                        if cfg.get("success_threshold") is not None:
                            eff_th = float(cfg.get("success_threshold"))
                    except Exception:
                        pass

                return sim_th, eff_th

            def _cmp_expr(v: float, th: float) -> str:
                op = ">=" if v >= th else "<"
                return f"{v:.3f}{op}{th:.3f}"

            # Use initialized learning system to avoid re-initialization
            if not self._learning_system_initialized:
                self._initialize_learning_system()
            
            if not self.learning_system:
                workflow_logger.info("  ⚠️ Learning system unavailable, skip historical strategy query")
                return []

            # Build context for strategy recommendation - fully use rich info in alert
            trigger_content = alert.get("trigger_content", {})
            
            # Extract core viewpoint and theme info
            core_viewpoint = trigger_content.get("core_viewpoint", "")
            post_theme = trigger_content.get("post_theme", "")
            
            # Extract malicious/extremism analysis
            malicious_analysis = trigger_content.get("malicious_analysis", {})
            extremism_level = malicious_analysis.get("extremism_level", 1)
            attack_patterns = malicious_analysis.get("attack_patterns", [])
            threat_assessment = malicious_analysis.get("threat_assessment", "")
            
            # Extract engagement and spread risk
            engagement_metrics = trigger_content.get("engagement_metrics", {})
            intensity_level = engagement_metrics.get("intensity_level", "MODERATE")
            amplification_risk = engagement_metrics.get("amplification_risk", "MODERATE")
            viral_potential = engagement_metrics.get("viral_potential", "MODERATE")
            
            # Extract sentiment and polarization risk
            sentiment_distribution = trigger_content.get("sentiment_distribution", {})
            sentiment_score = sentiment_distribution.get("overall_sentiment_score", 0.5)
            emotional_triggers = sentiment_distribution.get("emotional_triggers", [])
            polarization_risk = sentiment_distribution.get("polarization_risk", "MODERATE")
            
            # Extract intervention analysis
            intervention_analysis = trigger_content.get("intervention_analysis", {})
            reasoning = intervention_analysis.get("reasoning", "")
            recommended_approach = intervention_analysis.get("recommended_approach", "")
            trigger_factors = intervention_analysis.get("trigger_factors", [])
            
            # Extract key topics and emotional indicators
            key_topics = trigger_content.get("key_topics", [])
            emotional_indicators = trigger_content.get("emotional_indicators", [])
            
            # Build rich context
            context = {
                # Basic info
                "urgency_level": alert.get("urgency_level", 2),
                "extremism_level": extremism_level,
                "content_type": "social_media_post",
                "threat_level": alert.get("threat_level", "moderate"),
                "requires_intervention": True,
                
                # Content analysis
                "core_viewpoint": core_viewpoint,
                "post_theme": post_theme,
                "sentiment_score": sentiment_score,
                "viewpoint_extremism": trigger_content.get("viewpoint_extremism", 0),
                
                # Risk analysis
                "intensity_level": intensity_level,
                "amplification_risk": amplification_risk,
                "viral_potential": viral_potential,
                "polarization_risk": polarization_risk,
                
                # Attack patterns
                "attack_patterns": attack_patterns,
                "threat_assessment": threat_assessment,
                "emotional_triggers": emotional_triggers,
                
                # Intervention info
                "intervention_reasoning": reasoning,
                "recommended_approach": recommended_approach,
                "trigger_factors": trigger_factors,
                
                # Topics and emotions
                "key_topics": key_topics,
                "emotional_indicators": emotional_indicators,
                
                # Raw data (for debugging and further analysis)
                "raw_trigger_content": trigger_content
            }

            # Use intelligent learning system to recommend strategies
            recommendation = self.learning_system.recommend_strategy(context)

            if recommendation:
                # Check recommendation type and handle different data structures
                if recommendation.get("strategy_type") == "action_log":
                    # Handle action log recommendations
                    content = recommendation.get("content", {})
                    confidence = recommendation.get("confidence", 0.3)
                    similarity = recommendation.get("similarity", 0.5)
                    # effectiveness score should come from historical effectiveness_score, not retrieval confidence/similarity.
                    effectiveness = content.get("effectiveness_score", None)
                    effectiveness_score = None
                    try:
                        if isinstance(effectiveness, (int, float)):
                            eff = float(effectiveness)
                            if 0.0 <= eff <= 1.0:
                                effectiveness_score = eff
                            elif 0.0 <= eff <= 10.0:
                                workflow_logger.warning(
                                    f"     ⚠️ Detected effectiveness_score on 0-10 scale ({eff:.2f}); converting to [0,1] effectiveness score"
                                )
                                effectiveness_score = eff / 10.0
                    except Exception:
                        effectiveness_score = None
                    if effectiveness_score is None:
                        workflow_logger.warning("     ⚠️ Missing effectiveness_score; using confidence as a proxy for effectiveness score")
                        effectiveness_score = float(confidence) if isinstance(confidence, (int, float)) else 0.3
                    
                    # Extract strategy info from action logs
                    strategic_decision = content.get("strategic_decision", "{}")
                    try:
                        import json
                        decision_data = json.loads(strategic_decision) if isinstance(strategic_decision, str) else strategic_decision
                        strategy_id = decision_data.get("strategy_id", "learned_strategy")
                        action_type = decision_data.get("action_type", "unknown")
                    except:
                        strategy_id = "learned_strategy"
                        action_type = "unknown"
                    
                    strategy = {
                        "strategy_id": strategy_id,
                        "strategy_name": f"Learning-based strategy ({action_type})",
                        "description": f"Strategy recommendation based on historical action logs (similarity: {similarity:.1%})",
                        "recommended_actions": [action_type] if action_type != "unknown" else [],
                        "effectiveness_score": effectiveness_score,
                        "expected_success_rate": effectiveness_score,
                        "confidence": confidence,
                        "source": "intelligent_learning",
                        "similarity_score": similarity
                    }
                    sim_th, eff_th = _get_thresholds()
                    sim_v = float(similarity) if isinstance(similarity, (int, float)) else 0.0
                    eff_v = float(effectiveness_score) if isinstance(effectiveness_score, (int, float)) else 0.0
                    workflow_logger.info(
                        "     ✅ Top matching strategy: {sid}, similarity={sim_expr}, effectiveness score={eff_expr}".format(
                            sid=strategy_id,
                            sim_expr=_cmp_expr(sim_v, sim_th),
                            eff_expr=_cmp_expr(eff_v, eff_th),
                        )
                    )
                    if sim_v >= sim_th and eff_v >= eff_th:
                        workflow_logger.info("     ✅ Use this strategy")
                        return [strategy]
                    workflow_logger.info("     ⏭️ Strategy not suitable, use a new strategy")
                    return []
                
                elif recommendation.get("strategy_name"):
                    # Handle traditional strategy recommendation format
                    strategy = {
                        "strategy_id": recommendation.get("strategy_id", "learned_strategy"),
                        "strategy_name": recommendation.get("strategy_name", "Learning-based strategy"),
                        "description": recommendation.get("description", ""),
                        "recommended_actions": recommendation.get("recommended_actions", []),
                        "effectiveness_score": recommendation.get("effectiveness_score", recommendation.get("expected_success_rate", 0.6)),
                        "expected_success_rate": recommendation.get("effectiveness_score", recommendation.get("expected_success_rate", 0.6)),
                        "confidence": recommendation.get("confidence", 0.5),
                        "source": recommendation.get("source", "intelligent_learning"),
                        "similarity_score": recommendation.get("similarity_score", 0.9)
                    }
                    sim_th, eff_th = _get_thresholds()
                    sim_v = float(strategy.get("similarity_score", 0.0) or 0.0)
                    eff_v = float(strategy.get("effectiveness_score", 0.0) or 0.0)
                    workflow_logger.info(
                        "     ✅ Top matching strategy: {sid}, similarity={sim_expr}, effectiveness score={eff_expr}".format(
                            sid=strategy.get("strategy_id"),
                            sim_expr=_cmp_expr(sim_v, sim_th),
                            eff_expr=_cmp_expr(eff_v, eff_th),
                        )
                    )
                    if sim_v >= sim_th and eff_v >= eff_th:
                        workflow_logger.info("     ✅ Use this strategy")
                        return [strategy]
                    workflow_logger.info("     ⏭️ Strategy not suitable, use a new strategy")
                    return []
                else:
                    workflow_logger.info("     ❌ Intelligent learning system returned an unknown format recommendation")
                    return []
            else:
                diagnosis = getattr(self.learning_system, "last_recommendation_diagnosis", None)
                if isinstance(diagnosis, dict):
                    reason = diagnosis.get("reason", "no_results")
                    top_candidates = diagnosis.get("top_candidates", [])
                    try:
                        threshold = float(diagnosis.get("similarity_threshold", 0.7))
                    except Exception:
                        threshold = diagnosis.get("similarity_threshold", 0.7)
                    try:
                        eff_th = float(diagnosis.get("effectiveness_threshold", getattr(getattr(self.learning_system, "config", {}), "get", lambda *_: 0.7)("success_threshold", 0.7)))
                    except Exception:
                        eff_th = 0.7

                    if isinstance(top_candidates, list) and top_candidates:
                        best = top_candidates[0] if isinstance(top_candidates[0], dict) else {}
                        sim = best.get("similarity")
                        eff = best.get("effectiveness_score")
                        try:
                            sim_f = float(sim)
                            eff_f = float(eff) if eff is not None else None
                            eff_v = eff_f if eff_f is not None else 0.0
                            workflow_logger.info(
                                "     🔍 Top strategy candidate: {aid}, similarity={sim_expr}, effectiveness score={eff_expr}, decision=new_strategy".format(
                                    aid=best.get("action_id"),
                                    sim_expr=_cmp_expr(sim_f, float(threshold)),
                                    eff_expr=_cmp_expr(eff_v, float(eff_th)),
                                )
                            )
                        except Exception:
                            workflow_logger.info(
                                f"     🔍 Top strategy candidate: {best.get('action_id')}, similarity={sim}<{threshold}, effectiveness score={eff}<{eff_th}, decision=new_strategy"
                            )
                    else:
                        workflow_logger.info(f"     ℹ️ No strategy candidate available (similarity_threshold={threshold})")
                workflow_logger.info("     ⏭️ Strategy not suitable, use a new strategy")
                return []

        except Exception as e:
            workflow_logger.info(f"     ❌ Intelligent learning system query failed: {e}")
            import traceback
            workflow_logger.info(f"     Detailed error: {traceback.format_exc()}")
            return []

    def _calculate_heat_level(self, engagement_metrics: Dict[str, Any], malicious_analysis: Dict[str, Any]) -> float:
        """Calculate heat score (0-100)."""
        try:
            # Base heat score
            base_heat = 0
            
            # Calculate heat from engagement metrics
            intensity_level = engagement_metrics.get('intensity_level', 'MODERATE')
            if intensity_level == 'HIGH':
                base_heat += 40
            elif intensity_level == 'MODERATE':
                base_heat += 25
            elif intensity_level == 'LOW':
                base_heat += 10
            
            # Calculate heat from viral potential
            viral_potential = engagement_metrics.get('viral_potential', 'Low to moderate spread expected')
            if 'high' in viral_potential.lower() or 'viral' in viral_potential.lower():
                base_heat += 30
            elif 'moderate' in viral_potential.lower():
                base_heat += 20
            elif 'low' in viral_potential.lower():
                base_heat += 10
            
            # Calculate heat from amplification risk
            amplification_risk = engagement_metrics.get('amplification_risk', 'Standard monitoring required')
            if 'high' in amplification_risk.lower():
                base_heat += 25
            elif 'moderate' in amplification_risk.lower():
                base_heat += 15
            elif 'low' in amplification_risk.lower():
                base_heat += 5
            
            # Calculate heat from extremism
            extremism_level = malicious_analysis.get('extremism_level', 1)
            if extremism_level >= 4:
                base_heat += 20
            elif extremism_level >= 3:
                base_heat += 15
            elif extremism_level >= 2:
                base_heat += 10
            elif extremism_level >= 1:
                base_heat += 5
            
            return min(base_heat, 100)  # Cap within 0-100
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Heat calculation failed: {e}")
            return 25  # Default medium heat

    def _determine_heat_level(self, engagement_metrics: Dict[str, Any], malicious_analysis: Dict[str, Any]) -> str:
        """Determine heat level."""
        try:
            heat_score = self._calculate_heat_level(engagement_metrics, malicious_analysis)
            
            if heat_score >= 70:
                return "HIGH"
            elif heat_score >= 40:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Heat level determination failed: {e}")
            return "MEDIUM"

    def _get_heat_multiplier(self, engagement_metrics: Dict[str, Any], malicious_analysis: Dict[str, Any]) -> str:
        """Get heat multiplier rule description."""
        try:
            heat_level = self._determine_heat_level(engagement_metrics, malicious_analysis)
            
            if heat_level == "HIGH":
                return "Multiply base count by 1.5-2.0x (high heat response)"
            elif heat_level == "MEDIUM":
                return "Multiply base count by 1.2-1.5x (medium heat response)"
            else:
                return "Use base count (1.0x multiplier, low heat response)"
                
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Heat multiplier calculation failed: {e}")
            return "Use base count (1.0x multiplier, default response)"

    def _initialize_learning_system(self):
        """Initialize intelligent learning system."""
        if self._learning_system_initialized:
            return
            
        try:
            from intelligent_learning_system import IntelligentLearningSystem
            self.learning_system = IntelligentLearningSystem()
            self._learning_system_initialized = True
            workflow_logger.info(f"  🧠 Intelligent learning system initialized successfully")
        except Exception as e:
            workflow_logger.info(f"  ⚠️  Intelligent learning system initialization failed: {e}")
            self.learning_system = None

    def _calculate_situation_similarity(self, current_alert: Dict[str, Any], historical_strategy: Dict[str, Any]) -> float:
        """Calculate similarity score between current situation and historical strategy - enhanced version."""
        try:
            similarity = 0.0
            
            # 1. Compare urgency level (weight: 0.25)
            current_urgency = current_alert.get("urgency_level", 2)
            historical_urgency = historical_strategy.get("situation_assessment", {}).get("urgency_level", 2)
            if isinstance(historical_urgency, str):
                urgency_map = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
                historical_urgency = urgency_map.get(historical_urgency.lower(), 2)
            
            urgency_similarity = 1.0 - abs(current_urgency - historical_urgency) / 4.0
            similarity += urgency_similarity * 0.25
            
            # 2. Compare threat level (weight: 0.25)
            current_threat = current_alert.get("trigger_content", {}).get("malicious_analysis", {}).get("extremism_level", 1)
            historical_threat = historical_strategy.get("situation_assessment", {}).get("threat_level", "moderate")
            threat_map = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
            
            if isinstance(historical_threat, str):
                historical_threat_num = threat_map.get(historical_threat.lower(), 2)
            else:
                historical_threat_num = historical_threat
            
            threat_similarity = 1.0 - abs(current_threat - historical_threat_num) / 4.0
            similarity += threat_similarity * 0.25
            
            # 3. Compare content topic (weight: 0.3)
            current_viewpoint = current_alert.get("trigger_content", {}).get("core_viewpoint", "")
            historical_argument = historical_strategy.get("core_counter_argument", "")
            
            topic_similarity = self._calculate_semantic_similarity(current_viewpoint, historical_argument)
            similarity += topic_similarity * 0.3
            
            # 4. Compare engagement level (weight: 0.15)
            current_engagement = current_alert.get("trigger_content", {}).get("engagement_metrics", {}).get("intensity_level", "MODERATE")
            historical_engagement = historical_strategy.get("situation_assessment", {}).get("engagement_intensity", "MODERATE")
            
            engagement_similarity = self._compare_engagement_levels(current_engagement, historical_engagement)
            similarity += engagement_similarity * 0.15
            
            # 5. Compare sentiment distribution (weight: 0.05)
            current_sentiment = current_alert.get("trigger_content", {}).get("sentiment_distribution", {}).get("overall_sentiment", "mixed")
            historical_sentiment = historical_strategy.get("situation_assessment", {}).get("primary_sentiment", "mixed")
            
            sentiment_similarity = 1.0 if current_sentiment == historical_sentiment else 0.5
            similarity += sentiment_similarity * 0.05
            
            return min(1.0, max(0.0, similarity))
            
        except Exception as e:
            workflow_logger.info(f"     ❌ Similarity calculation error: {e}")
            return 0.3  # defaultsimilarity_score
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity score between two texts."""
        try:
            if not text1 or not text2:
                return 0.0
            
            # Clean and preprocess text
            import re
            text1_clean = re.sub(r'[^\w\s]', '', text1.lower())
            text2_clean = re.sub(r'[^\w\s]', '', text2.lower())
            
            words1 = set(text1_clean.split())
            words2 = set(text2_clean.split())
            
            if not words1 or not words2:
                return 0.0
            
            # Jaccardsimilarity_score
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            jaccard = intersection / union if union > 0 else 0.0
            
            # Length similarity score (avoid mismatch for different lengths)
            len1, len2 = len(words1), len(words2)
            length_similarity = 1.0 - abs(len1 - len2) / max(len1, len2)
            
            # Combined similarity score
            semantic_similarity = (jaccard * 0.8) + (length_similarity * 0.2)
            
            return min(1.0, semantic_similarity)
            
        except Exception as e:
            return 0.1
    
    def _compare_engagement_levels(self, level1: str, level2: str) -> float:
        """Compare engagement levels."""
        engagement_map = {"LOW": 1, "MODERATE": 2, "HIGH": 3, "VIRAL": 4}
        
        try:
            val1 = engagement_map.get(level1.upper(), 2)
            val2 = engagement_map.get(level2.upper(), 2)
            
            return 1.0 - abs(val1 - val2) / 3.0  # Normalize to 0-1 range
            
        except Exception:
            return 0.5

    async def _create_tot_strategic_plan(self, alert: Dict[str, Any], historical_strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use Tree-of-Thought (ToT) to build step-by-step strategic plan."""
        try:
            workflow_logger.info("     🌳 Start Tree-of-Thought reasoning...")
            
            # Step 1: Generate multiple strategy options
            strategic_options = await self._generate_strategic_options(alert, historical_strategies)
            workflow_logger.info(f"        🔄 Generated {len(strategic_options)} strategy options")
            
            # Step 2: Evaluate each option
            evaluated_options = await self._evaluate_strategic_options(strategic_options, alert)
            workflow_logger.info(f"        ⚖️  Completed option evaluation")
            
            # Step 3: Select optimal strategy and provide detailed explanation
            best_option = max(evaluated_options, key=lambda x: x["total_score"])
            
            # Generate decision explanation
            decision_explanation = self._generate_decision_explanation(
                evaluated_options, best_option, alert
            )
            
            workflow_logger.info(f"        🎯 Selected optimal strategy: {best_option['name']}")
            workflow_logger.info(f"        📝 Decision rationale: {decision_explanation['primary_reason']}")
            
            return {
                "strategic_options": strategic_options,
                "evaluated_options": evaluated_options,
                "selected_strategy": best_option,
                "decision_explanation": decision_explanation,
                "reasoning_summary": {
                    "options_considered": len(strategic_options),
                    "evaluation_criteria": ["effectiveness", "risk", "feasibility", "historical_success"],
                    "decision_rationale": f"Selected '{best_option['name']}' with score {best_option['total_score']:.2f}",
                    "decision_confidence": decision_explanation["confidence_level"]
                }
            }
            
        except Exception as e:
            workflow_logger.info(f"     ❌ ToT reasoning failed: {e}")
            return {"strategic_options": [], "selected_strategy": {"name": "default", "total_score": 0.5}}

    async def _generate_strategic_options(self, alert: Dict[str, Any], historical_strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate multiple strategy options using LLM - dynamic version"""
        try:
            # Get key characteristics of the current situation
            urgency_level = alert.get("urgency_level", 2)
            trigger_content = alert.get("trigger_content", {})
            extremism_level = trigger_content.get("malicious_analysis", {}).get("extremism_level", 1) if isinstance(trigger_content, dict) else 1
            engagement_intensity = trigger_content.get("engagement_metrics", {}).get("intensity_level", "MODERATE") if isinstance(trigger_content, dict) else "MODERATE"
            
            # Use LLM to generate strategy options
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a strategic planning expert. Generate 3-5 diverse strategy options for opinion balance operations based on the given situation.

Each option should include:
- name: unique strategy identifier
- description: brief strategy description  
- approach: tactical approach name
- core_argument: main argument/response
- agent_count: number of agents needed (3-10)
- timing: response timing (immediate/measured/gradual)
- basis: strategy foundation
- confidence_score: 0.0-1.0
- risk_factors: list of potential risks

Generate diverse options considering different risk levels, response speeds, and resource requirements."""
                    },
                    {
                        "role": "user",
                        "content": f"""Generate strategic options for this situation:

URGENCY LEVEL: {urgency_level}/4
EXTREMISM LEVEL: {extremism_level}/4
ENGAGEMENT INTENSITY: {engagement_intensity}
HISTORICAL STRATEGIES AVAILABLE: {len(historical_strategies)}

SITUATION CONTEXT:
{trigger_content}

Generate 3-5 diverse strategy options as JSON array."""
                    }
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            # Parse LLM response
            content = response.choices[0].message.content
            try:
                import json
                result = json.loads(content)
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and "options" in result:
                    return result["options"]
                else:
                    # Fallback to default options if parsing fails
                    return self._get_default_strategy_options(alert)
            except json.JSONDecodeError:
                return self._get_default_strategy_options(alert)
                
        except Exception as e:
            workflow_logger.info(f"     ❌ LLM strategy generation failed: {e}")
            return self._get_default_strategy_options(alert)

    def _get_default_strategy_options(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback default strategy options"""
        return [
            {
                "name": "balanced_response",
                "description": "Standard balanced response strategy",
                "approach": "measured_response",
                "core_argument": "Provide balanced, factual perspective",
                "agent_count": 4,
                "timing": "measured",
                "basis": "standard_protocol",
                "confidence_score": 0.7,
                "risk_factors": ["limited_impact"]
            }
        ]
    
    def _adapt_agent_count(self, historical_count: int, extremism_level: int, urgency_level: int) -> int:
        """Adapt agent count intelligently."""
        try:
            # Adjust based on historical count
            base_count = historical_count
            
            # Adjust based on extremism level
            if extremism_level >= 4:
                base_count = int(base_count * 1.5)  # Increase by 50%
            elif extremism_level >= 3:
                base_count = int(base_count * 1.3)  # Increase by 30%
            elif extremism_level <= 1:
                base_count = int(base_count * 0.8)  # Decrease by 20%
            
            # Adjust based on urgency_level
            if urgency_level >= 4:
                base_count = int(base_count * 1.2)  # Increase by 20%
            elif urgency_level <= 1:
                base_count = int(base_count * 0.9)  # Decrease by 10%
            
            # Ensure within a reasonable range
            return max(3, min(12, base_count))
            
        except Exception:
            return 5  # Default value
    
    def _adapt_strategic_approach(self, historical_approach: str, current_content: Dict[str, Any]) -> str:
        """Intelligent adaptive strategymethod"""
        try:
            if not historical_approach:
                return "Provide balanced viewpoints and constructive discussion"
            
            # Get characteristics of current content
            current_sentiment = current_content.get("sentiment_distribution", {}).get("overall_sentiment", "mixed")
            current_theme = current_content.get("post_theme", "")
            
            # Adjust historical approach based on current content
            adapted_approach = historical_approach
            
            # Adjust based on sentiment
            if "negative" in current_sentiment:
                adapted_approach = f"Address negative sentiment, {adapted_approach.lower()}"
            elif "positive" in current_sentiment:
                adapted_approach = f"Support positive discussion, {adapted_approach.lower()}"
            
            # Adjust based on theme (if theme info is available)
            if current_theme and len(current_theme) > 10:
                adapted_approach = f"Around {current_theme[:20]}{'...' if len(current_theme) > 20 else ''}, {adapted_approach.lower()}"
            
            return adapted_approach
            
        except Exception:
            return historical_approach or "Provide balanced perspective"
    
    def _determine_optimal_timing(self, urgency_level: int, extremism_level: int) -> str:
        """Determine optimal timing strategy."""
        total_urgency = urgency_level + extremism_level
        
        if total_urgency >= 7:
            return "immediate"
        elif total_urgency >= 5:
            return "rapid_progressive"
        elif total_urgency >= 3:
            return "measured_progressive"
        else:
            return "gradual_introduction"
    
    def _identify_adaptation_risks(self, historical_strategy: Dict[str, Any], current_alert: Dict[str, Any]) -> List[str]:
        """Identify strategy adaptation risks."""
        risks = []
        
        try:
            # Check context difference risks (can extend with more detailed risk analysis)
            
            # Time difference risk
            risks.append("context_adaptation_uncertainty")
            
            # Scale difference risk
            historical_agents = historical_strategy.get("amplifier_plan", {}).get("total_agents", 5)
            if historical_agents > 8:
                risks.append("high_resource_requirement")
            
            # Complexity risk
            if len(historical_strategy.get("core_counter_argument", "")) > 200:
                risks.append("complex_message_adaptation")
            
            return risks
            
        except Exception:
            return ["general_adaptation_risk"]
    
    def _calculate_response_intensity(self, urgency_level: int, extremism_level: int, engagement_intensity: str) -> float:
        """Calculate response intensity."""
        try:
            # Base intensity from urgency level and extremism level
            base_intensity = (urgency_level + extremism_level) / 8.0
            
            # Engagement adjustment
            engagement_multiplier = {
                "LOW": 0.8,
                "MODERATE": 1.0,
                "HIGH": 1.2,
                "VIRAL": 1.4
            }.get(engagement_intensity, 1.0)
            
            intensity = base_intensity * engagement_multiplier
            
            return min(1.0, max(0.1, intensity))
            
        except Exception:
            return 0.5
    
    def _calculate_optimal_agent_count(self, extremism_level: int, engagement_intensity: str) -> int:
        """Calculate optimal agent count."""
        try:
            # Base count
            base_count = 3 + extremism_level
            
            # Engagement adjustment
            if engagement_intensity == "VIRAL":
                base_count += 3
            elif engagement_intensity == "HIGH":
                base_count += 2
            elif engagement_intensity == "LOW":
                base_count -= 1
            
            return max(3, min(10, base_count))
            
        except Exception:
            return 5
    
    def _generate_contextual_argument(self, trigger_content: Dict[str, Any], style: str) -> str:
        """Generate a contextual argument."""
        try:
            # Extract specific info from trigger_content
            core_viewpoint = trigger_content.get("core_viewpoint", "unknown topic")
            post_theme = trigger_content.get("post_theme", "general discussion")
            
            if style == "balanced":
                return f"For topic '{core_viewpoint}', provide balanced, rational viewpoints and constructive analysis to promote rational discussion of '{post_theme}'"
            elif style == "diplomatic":
                return f"Handle the '{core_viewpoint}' controversy in a gentle diplomatic manner, promoting understanding and dialogue around '{post_theme}'"
            elif style == "authoritative":
                return f"Based on authoritative info and professional analysis, provide an objective response to '{core_viewpoint}' to ensure accuracy in '{post_theme}' discussion"
            else:
                return f"Provide a balanced perspective on '{core_viewpoint}' to promote rational discussion of '{post_theme}'"
                
        except Exception:
            return "Provide balanced perspective to promote rational discussion"
    
    def _assess_dynamic_risks(self, extremism_level: int, engagement_intensity: str) -> List[str]:
        """Evaluate dynamic strategy risks."""
        risks = []
        
        if extremism_level >= 4:
            risks.append("high_polarization_risk")
        
        if engagement_intensity == "VIRAL":
            risks.append("rapid_escalation_risk")
        
        risks.append("real_time_adjustment_complexity")
        
        return risks
    
    def _design_experimental_approach(self, historical_strategies: List[Dict[str, Any]], alert: Dict[str, Any]) -> Dict[str, Any]:
        """Design experimental approach."""
        try:
            # Analyze successful patterns in historical strategies
            successful_patterns = []
            for strategy in historical_strategies:
                if strategy.get("success_rate", 0) > 0.7:
                    successful_patterns.append(strategy.get("strategy", {}))
            
            # Innovative combination
            if len(successful_patterns) >= 2:
                # Combine elements from different successful strategies
                combined_agent_count = int(sum(
                    s.get("amplifier_plan", {}).get("total_agents", 5) for s in successful_patterns
                ) / len(successful_patterns) * 1.1)  # Increase by 10%
                
                return {
                    "argument": "Innovative experimental approach combining historical successful patterns",
                    "agent_count": max(4, min(8, combined_agent_count)),
                    "timing": "adaptive_phased"
                }
            
            # Default experimental approach
            return {
                "argument": "Exploratory innovative discussion approach",
                "agent_count": 6,
                "timing": "cautious_experimental"
            }
            
        except Exception:
            return {"argument": "basic experimental approach", "agent_count": 5, "timing": "standard"}
    
    def _filter_and_rank_options(self, options: List[Dict[str, Any]], alert: Dict[str, Any], 
                                historical_strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and sort strategy options"""
        try:
            # Calculate composite score for each option
            for option in options:
                score = 0.0
                
                # confidence_score weight (30%)
                score += option.get("confidence_score", 0.5) * 0.3
                
                # historical success_rate weight (25%)
                if option.get("basis") == "proven_success":
                    score += 0.25
                elif option.get("basis") == "real_time_analysis":
                    score += 0.2
                else:
                    score += 0.15
                
                # risk_assessment weight (20%)
                risk_count = len(option.get("risk_factors", []))
                risk_penalty = min(0.2, risk_count * 0.05)
                score += (0.2 - risk_penalty)
                
                # applicability score (25%)
                urgency = alert.get("urgency_level", 2)
                extremism = alert.get("trigger_content", {}).get("malicious_analysis", {}).get("extremism_level", 1) if isinstance(alert.get("trigger_content", {}), dict) else 1
                
                if urgency >= 3 and "immediate" in option.get("timing", ""):
                    score += 0.1
                if extremism >= 3 and option.get("agent_count", 5) >= 7:
                    score += 0.1
                
                option["total_evaluation_score"] = score
            
            # Sort by score
            ranked_options = sorted(options, key=lambda x: x.get("total_evaluation_score", 0), reverse=True)
            
            return ranked_options
            
        except Exception:
            return options

    async def _evaluate_strategic_options(self, options: List[Dict[str, Any]], alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate strategy options - enhanced multi-dimensional evaluation."""
        evaluated = []
        
        for option in options:
            # Core evaluation dimensions
            effectiveness_score = self._evaluate_effectiveness(option, alert)
            risk_score = self._evaluate_risk(option, alert)  
            feasibility_score = self._evaluate_feasibility(option, alert)
            historical_score = self._evaluate_historical_success(option, alert)
            
            # Additional evaluation dimensions
            adaptability_score = self._evaluate_adaptability(option, alert)
            resource_efficiency_score = self._evaluate_resource_efficiency(option)
            innovation_score = self._evaluate_innovation_potential(option)
            
            # Weighted total score calculation - more granular weights
            total_score = (
                effectiveness_score * 0.25 +      # Expected effectiveness
                (1 - risk_score) * 0.20 +        # Risk control (lower is better)
                feasibility_score * 0.15 +       # Feasibility
                historical_score * 0.15 +        # historical_validation
                adaptability_score * 0.10 +      # adaptability
                resource_efficiency_score * 0.10 + # resource_efficiency
                innovation_score * 0.05           # innovation_potential
            )
            
            # Build enhanced evaluation result
            evaluated_option = option.copy()
            evaluated_option.update({
                "effectiveness_score": effectiveness_score,
                "risk_score": risk_score,
                "feasibility_score": feasibility_score,
                "historical_score": historical_score,
                "adaptability_score": adaptability_score,
                "resource_efficiency_score": resource_efficiency_score,
                "innovation_score": innovation_score,
                "total_score": total_score,
                "evaluation_breakdown": {
                    "strengths": self._identify_strengths(option, {
                        "effectiveness": effectiveness_score,
                        "risk_control": 1 - risk_score,
                        "feasibility": feasibility_score,
                        "historical_validation": historical_score
                    }),
                    "potential_risks": self._identify_weaknesses(option, {
                        "risk_level": risk_score,
                        "complexity": 1 - feasibility_score,
                        "uncertainty": 1 - historical_score
                    }),
                    "applicable_scenarios": self._determine_best_scenarios(option, alert)
                }
            })
            
            evaluated.append(evaluated_option)
        
        return evaluated
    
    def _evaluate_adaptability(self, option: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Evaluate strategy adaptability."""
        try:
            adaptability = 0.5
            
            # Adaptability based on strategy type
            if option.get("basis") == "real_time_analysis":
                adaptability += 0.3  # Real-time analysis strategy has strong adaptability
            elif option.get("basis") == "proven_success":
                adaptability += 0.2  # Historical successful strategies have some adaptability
            elif option.get("basis") == "innovation_exploration":
                adaptability += 0.4  # Innovation strategy has strongest adaptability
            
            # Flexibility based on agent count
            agent_count = option.get("agent_count", 5)
            if 4 <= agent_count <= 7:
                adaptability += 0.1  # Medium scale is most flexible
            elif agent_count > 10:
                adaptability -= 0.1  # Large scale is harder to adjust
            
            # Adaptability based on timing strategy
            timing = option.get("timing", "")
            if "progressive" in timing or "adaptive" in timing:
                adaptability += 0.1
            elif "immediate" in timing:
                adaptability -= 0.05  # Immediate execution strategy is less adaptable
            
            return min(1.0, max(0.0, adaptability))
            
        except Exception:
            return 0.5
    
    def _evaluate_resource_efficiency(self, option: Dict[str, Any]) -> float:
        """Evaluate resource usage efficiency."""
        try:
            efficiency = 0.5
            
            # Agent count efficiency evaluation
            agent_count = option.get("agent_count", 5)
            extremism_level = 1  # Default extremism level when alert is not available
            
            # Calculate ideal agent count
            ideal_count = 3 + extremism_level
            
            # Efficiency score based on deviation from ideal count
            deviation = abs(agent_count - ideal_count) / ideal_count
            efficiency += (1 - deviation) * 0.3
            
            # Efficiency based on strategy complexity
            if option.get("approach") in ["measured_balanced_response", "gradual_sentiment_shift"]:
                efficiency += 0.2  # Simple strategies have higher efficiency
            elif "experimental" in option.get("approach", ""):
                efficiency -= 0.1  # Experimental strategies have lower efficiency
            
            return min(1.0, max(0.0, efficiency))
            
        except Exception:
            return 0.5
    
    def _evaluate_innovation_potential(self, option: Dict[str, Any]) -> float:
        """Evaluate innovation potential."""
        try:
            innovation = 0.3  # Base score
            
            # Based on strategy type
            if option.get("basis") == "innovation_exploration":
                innovation += 0.6
            elif option.get("basis") == "real_time_analysis":
                innovation += 0.3
            elif option.get("basis") == "proven_success":
                innovation += 0.1  # Historical strategies have low innovation
            
            # Based on method innovativeness
            approach = option.get("approach", "")
            if "experimental" in approach or "innovative" in approach:
                innovation += 0.2
            elif "adaptive" in approach or "intelligent" in approach:
                innovation += 0.1
            
            return min(1.0, max(0.0, innovation))
            
        except Exception:
            return 0.3
    
    def _identify_strengths(self, option: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
        """Identify strategy strengths."""
        strengths = []
        
        for dimension, score in scores.items():
            if score >= 0.8:
                dimension_names = {
                    "effectiveness": "Strong expected effectiveness",
                    "risk_control": "Excellent risk control", 
                    "feasibility": "High execution feasibility",
                    "historical_validation": "Strong historical validation"
                }
                strengths.append(dimension_names.get(dimension, f"Excellent {dimension} performance"))
        
        # Add strengths based on strategy characteristics
        if option.get("confidence_score", 0) >= 0.8:
            strengths.append("High strategy confidence score")
        
        if option.get("agent_count", 5) <= 6:
            strengths.append("Reasonable resource requirements")
        
        return strengths if strengths else ["Overall performance is balanced"]
    
    def _identify_weaknesses(self, option: Dict[str, Any], risk_scores: Dict[str, float]) -> List[str]:
        """Identify strategy risks."""
        weaknesses = []
        
        for dimension, score in risk_scores.items():
            if score >= 0.6:
                risk_names = {
                    "risk_level": "High execution risk",
                    "complexity": "High implementation complexity",
                    "uncertainty": "High outcome uncertainty"
                }
                weaknesses.append(risk_names.get(dimension, f"{dimension} risk is worth attention"))
        
        # Add risks based on strategy characteristics
        if option.get("agent_count", 5) > 8:
            weaknesses.append("High resource consumption")
        
        if "experimental" in option.get("approach", ""):
            weaknesses.append("Method not fully validated")
        
        return weaknesses if weaknesses else ["Overall risk is controllable"]
    
    def _determine_best_scenarios(self, option: Dict[str, Any], alert: Dict[str, Any]) -> List[str]:
        """Determine best-fit scenarios for the strategy."""
        scenarios = []
        
        urgency = alert.get("urgency_level", 2)
        extremism = alert.get("trigger_content", {}).get("malicious_analysis", {}).get("extremism_level", 1) if isinstance(alert.get("trigger_content", {}), dict) else 1
        
        # Based on urgency level
        if urgency >= 3 and "immediate" in option.get("timing", ""):
            scenarios.append("High-urgency scenarios")
        elif urgency <= 2 and "gradual" in option.get("timing", ""):
            scenarios.append("Low-urgency long-term adjustment")
        
        # Based on extremism level
        if extremism >= 3 and option.get("agent_count", 5) >= 7:
            scenarios.append("High-extremism content response")
        elif extremism <= 2 and option.get("agent_count", 5) <= 6:
            scenarios.append("Routine content balancing")
        
        # Based on strategy type
        if option.get("basis") == "proven_success":
            scenarios.append("Validated similar cases")
        elif option.get("basis") == "innovation_exploration":
            scenarios.append("Complex cases requiring innovative methods")
        
        return scenarios if scenarios else ["Applicable to general scenarios"]

    def _evaluate_effectiveness(self, option: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Evaluate strategy effectiveness."""
        score = 0.5
        
        urgency = alert.get("urgency_level", 2)
        approach = option.get("approach", "")
        
        # Match urgency_level and approach
        if urgency >= 3 and "immediate" in approach:
            score += 0.3
        elif urgency <= 2 and "gradual" in approach:
            score += 0.2
            
        # Agent count suitability
        agent_count = option.get("agent_count", 5)
        extremism = alert.get("trigger_content", {}).get("malicious_analysis", {}).get("extremism_level", 1)
        
        if extremism >= 3 and agent_count >= 6:
            score += 0.2
        elif extremism <= 2 and agent_count <= 5:
            score += 0.1
            
        return min(1.0, score)

    def _evaluate_risk(self, option: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Evaluate strategy risk."""
        risk = 0.3
        
        approach = option.get("approach", "")
        
        # Aggressive strategies have higher risk
        if "immediate" in approach or "rapid" in approach:
            risk += 0.2
            
        # Too many agents increases risk
        if option.get("agent_count", 5) > 7:
            risk += 0.1
            
        return min(1.0, risk)

    def _evaluate_feasibility(self, option: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Evaluate strategy feasibility."""
        feasibility = 0.7
        
        # Agent count feasibility
        agent_count = option.get("agent_count", 5)
        if agent_count <= 8:  # Assume up to 8 agents supported
            feasibility += 0.2
        else:
            feasibility -= 0.3
            
        return min(1.0, max(0.0, feasibility))

    def _evaluate_historical_success(self, option: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Evaluate based on historical success rate."""
        if option.get("basis") == "historical_success":
            return 0.8
        elif option.get("basis") == "balanced_approach":
            return 0.6
        else:
            return 0.4

    async def _format_agent_instructions(self, tot_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Format Agent instructions"""
        selected_strategy = tot_plan.get("selected_strategy", {})
        
        return {
            "leader_instructions": {
                "approach": selected_strategy.get("approach", "balanced_response"),
                "core_message": selected_strategy.get("core_argument", "Provide balanced perspective"),
                "tone": "professional" if "authority" in selected_strategy.get("name", "") else "empathetic",
                "speaking_style": "fact-based" if "expert" in selected_strategy.get("name", "") else "diplomatic"
            },
            "amplifier_instructions": self._generate_amplifier_instructions(selected_strategy),
            "coordination_strategy": selected_strategy.get("timing", "progressive"),
            "timing_plan": {
                "strategy": selected_strategy.get("timing", "progressive"),
                "interval_minutes": 2 if selected_strategy.get("timing") == "immediate" else 5
            }
        }

    def _generate_amplifier_instructions(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific amplifier Agent instructions"""
        agent_count = strategy.get("agent_count", 5)
        approach = strategy.get("approach", "balanced")
        
        instructions = []
        
        # Generate different role instructions based on strategy type
        if "expert" in approach or "authority" in approach:
            role_distribution = {
                "technical_experts": 2,
                "balanced_moderates": 1,
                "fact_checkers": 2,
                "community_voices": 1
            }
        elif "rapid" in approach or "immediate" in approach:
            role_distribution = {
                "balanced_moderates": 3,
                "community_voices": 2,
                "fact_checkers": 1,
                "technical_experts": 0
            }
        else:  # gradual/balanced approach
            role_distribution = {
                "balanced_moderates": 2,
                "community_voices": 1,
                "fact_checkers": 1,
                "technical_experts": 1
            }
        
        # Generate specific instructions
        for i in range(min(agent_count, 8)):  # Limit to at most 8
            role_types = list(role_distribution.keys())
            role_type = role_types[i % len(role_types)]
            
            instructions.append({
                "agent_index": i,
                "role_type": role_type,
                "response_style": self._get_response_style(role_type, approach),
                "key_message": strategy.get("core_argument", "balanced discussion"),
                "tone": self._get_role_tone(role_type),
                "timing_delay": i * 3 if strategy.get("timing") == "staggered" else 1
            })
        
        return instructions

    def _get_response_style(self, role_type: str, approach: str) -> str:
        """Get response style based on role type and strategy."""
        style_map = {
            "technical_experts": "data-driven analysis",
            "balanced_moderates": "diplomatic discussion",
            "fact_checkers": "evidence-based clarification", 
            "community_voices": "relatable community perspective"
        }
        return style_map.get(role_type, "balanced discussion")

    def _get_role_tone(self, role_type: str) -> str:
        """Get tone based on role type."""
        tone_map = {
            "technical_experts": "professional",
            "balanced_moderates": "empathetic",
            "fact_checkers": "authoritative",
            "community_voices": "conversational"
        }
        return tone_map.get(role_type, "professional")

    def _format_historical_context(self, strategies: List[Dict[str, Any]]) -> str:
        """Format historical strategy context."""
        if not strategies:
            return "No relevant historical strategies found."
        
        context = f"Found {len(strategies)} relevant historical strategies:\n"
        for i, strategy in enumerate(strategies[:2], 1):
            # Compatible with different ID field names
            strategy_id = strategy.get('action_id', strategy.get('strategy_id', f'strategy_{i}'))
            success_rate = strategy.get('success_rate', strategy.get('expected_success_rate', 0.0))
            effectiveness = strategy.get('effectiveness_score', strategy.get('confidence', 0.0))
            context += f"{i}. Action {strategy_id}: Success rate {success_rate:.2f}, "
            context += f"Effectiveness {effectiveness:.2f}\n"
        
        return context

    def _format_tot_context(self, tot_plan: Dict[str, Any]) -> str:
        """Format ToT reasoning context."""
        if not tot_plan.get("strategic_options"):
            return "No ToT reasoning performed."
        
        selected = tot_plan.get("selected_strategy", {})
        return f"ToT Evaluation: {len(tot_plan['strategic_options'])} options evaluated. " + \
               f"Selected '{selected.get('name', 'unknown')}' with score {selected.get('total_score', 0):.2f}"

    def _format_instruction_context(self, instructions: Dict[str, Any]) -> str:
        """Format instruction context."""
        if not instructions:
            return "Default coordination instructions will be applied."
        
        leader = instructions.get("leader_instructions", {})
        amplifier_count = len(instructions.get("amplifier_instructions", []))
        
        return f"Leader approach: {leader.get('approach', 'balanced')}. " + \
               f"amplifier agents: {amplifier_count} coordinated agents with {instructions.get('coordination_strategy', 'progressive')} timing."

    def _generate_decision_explanation(self, evaluated_options: List[Dict[str, Any]], 
                                     best_option: Dict[str, Any], alert: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed decision explanation."""
        try:
            # Calculate decision confidence score
            scores = [opt["total_score"] for opt in evaluated_options]
            best_score = best_option["total_score"]
            second_best_score = sorted(scores, reverse=True)[1] if len(scores) > 1 else 0
            
            confidence_level = "high" if best_score - second_best_score > 0.2 else \
                             "medium" if best_score - second_best_score > 0.1 else "low"
            
            # Analyze strengths of the best strategy
            primary_strengths = []
            if best_option.get("effectiveness_score", 0) > 0.7:
                primary_strengths.append("High expected effectiveness")
            if best_option.get("risk_score", 1) < 0.4:
                primary_strengths.append("Low risk")
            if best_option.get("historical_score", 0) > 0.6:
                primary_strengths.append("historical_validation")
            if best_option.get("feasibility_score", 0) > 0.8:
                primary_strengths.append("High feasibility")
            
            # Generate primary decision rationale
            primary_reason = f"Select {best_option['name']} based on {', '.join(primary_strengths[:2])}"
            
            # risk_assessment
            risk_analysis = self._analyze_decision_risks(best_option, evaluated_options, alert)
            
            # Analyze alternatives
            alternative_analysis = self._analyze_alternatives(evaluated_options, best_option)
            
            return {
                "primary_reason": primary_reason,
                "confidence_level": confidence_level,
                "confidence_score": best_score,
                "score_gap": best_score - second_best_score,
                "key_advantages": primary_strengths,
                "risk_analysis": risk_analysis,
                "alternative_analysis": alternative_analysis,
                "decision_factors": {
                    "urgency_match": best_option.get("effectiveness_score", 0),
                    "risk_tolerance": 1 - best_option.get("risk_score", 1),
                    "resource_efficiency": best_option.get("feasibility_score", 0),
                    "proven_success": best_option.get("historical_score", 0)
                }
            }
            
        except Exception as e:
            logging.warning(f"Decision explanation generation failed: {e}")
            return {
                "primary_reason": "Select based on overall score",
                "confidence_level": "medium",
                "confidence_score": best_option.get("total_score", 0.5),
                "key_advantages": ["Overall performance is good"]
            }

    def _analyze_decision_risks(self, best_option: Dict[str, Any], 
                              all_options: List[Dict[str, Any]], alert: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze decision risks."""
        risks = []
        mitigations = []
        
        # Risk 1: Strategy risk too high
        if best_option.get("risk_score", 0) > 0.6:
            risks.append("High strategy execution risk")
            mitigations.append("Strengthen monitoring and rapid adjustment mechanism")
        
        # Risk 2: Insufficient historical validation
        if best_option.get("historical_score", 0) < 0.5:
            risks.append("Lack sufficient historical validation")
            mitigations.append("Increase experimental execution and effectiveness evaluation")
        
        # Risk 3: Resource feasibility concerns
        if best_option.get("feasibility_score", 0) < 0.7:
            risks.append("Resource allocation feasibility is in doubt")
            mitigations.append("Optimize agent configuration and timing")
        
        # Risk 4: Low decision confidence score
        scores = [opt["total_score"] for opt in all_options]
        if len(scores) > 1 and max(scores) - sorted(scores, reverse=True)[1] < 0.15:
            risks.append("Multiple options have close scores; decision is unclear")
            mitigations.append("Use human judgment for final confirmation")
        
        return {
            "identified_risks": risks,
            "risk_level": "high" if len(risks) > 2 else "medium" if risks else "low",
            "mitigation_strategies": mitigations,
            "monitoring_requirements": [
                "Real-time effectiveness monitoring",
                "Rapid feedback mechanism",
                "Prepare alternative plans"
            ]
        }

    def _analyze_alternatives(self, evaluated_options: List[Dict[str, Any]], 
                            selected: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze alternatives."""
        alternatives = [opt for opt in evaluated_options if opt != selected]
        
        if not alternatives:
            return {"Alternatives": "No other viable options"}
        
        # Find second-best option
        second_best = max(alternatives, key=lambda x: x["total_score"])
        
        # Comparative analysis
        comparison = {
            "Second-best option": second_best["name"],
            "Score gap": selected["total_score"] - second_best["total_score"],
            "Advantage comparison": {
                "Selected option advantages": self._extract_option_advantages(selected),
                "Alternative option advantages": self._extract_option_advantages(second_best)
            },
            "Switch conditions": [
                f"If {selected['name']} failure rate exceeds 30%",
                "If major obstacles occur during execution",
                "If risk assessment changes significantly"
            ]
        }
        
        return comparison

    def _extract_option_advantages(self, option: Dict[str, Any]) -> List[str]:
        """Extract option advantages."""
        advantages = []
        
        if option.get("effectiveness_score", 0) > 0.7:
            advantages.append("Strong expected effectiveness")
        if option.get("risk_score", 1) < 0.4:
            advantages.append("Lower execution risk")
        if option.get("feasibility_score", 0) > 0.8:
            advantages.append("Moderate implementation difficulty")
        if option.get("historical_score", 0) > 0.6:
            advantages.append("Good historical success record")
            
        if option.get("basis") == "historical_success":
            advantages.append("Based on successful cases")
        elif option.get("basis") == "urgency_requirements":
            advantages.append("Matches urgency requirements")
        elif option.get("basis") == "expertise_requirement":
            advantages.append("Professional, authority-oriented")
        
        return advantages if advantages else ["Overall performance is balanced"]

    async def get_strategy_performance_report(self) -> Dict[str, Any]:
        """Get strategy performance report - added function."""
        try:
            if not self.strategy_history:
                return {"message": "No strategy history data"}
            
            recent_strategies = self.strategy_history[-10:]  # Most recent 10 strategies
            
            # calculateperformancemetrics
            avg_historical_references = sum(
                len(s.get("historical_strategies", [])) for s in recent_strategies
            ) / len(recent_strategies)
            
            tot_usage_rate = sum(
                1 for s in recent_strategies 
                if s.get("tot_plan", {}).get("strategic_options", [])
            ) / len(recent_strategies)
            
            # Strategy type distribution
            strategy_types = {}
            for strategy in recent_strategies:
                selected = strategy.get("tot_plan", {}).get("selected_strategy", {})
                strategy_name = selected.get("name", "unknown")
                strategy_types[strategy_name] = strategy_types.get(strategy_name, 0) + 1
            
            return {
                "total_strategies": len(self.strategy_history),
                "recent_analysis": {
                    "average_historical_references": round(avg_historical_references, 2),
                    "tot_reasoning_usage_rate": f"{tot_usage_rate:.1%}",
                    "strategy_type_distribution": strategy_types
                },
                "performance_trends": {
                    "increasing_complexity": tot_usage_rate > 0.8,
                    "historical_learning_active": avg_historical_references > 1,
                    "decision_quality": "improving" if tot_usage_rate > 0.7 else "stable"
                },
                "recommendations": self._generate_performance_recommendations(
                    avg_historical_references, tot_usage_rate, strategy_types
                )
            }
            
        except Exception as e:
            return {"error": f"performancereportgeneratefailed: {e}"}

    def _generate_performance_recommendations(self, historical_refs: float, 
                                           tot_rate: float, strategy_dist: Dict) -> List[str]:
        """Generate performance improvement suggestions"""
        recommendations = []
        
        if historical_refs < 1:
            recommendations.append("Recommend collecting more historical strategy data to improve decision quality")
        
        if tot_rate < 0.5:
            recommendations.append("Recommend using ToT reasoning more frequently to optimize strategy selection")
        
        if len(strategy_dist) < 3:
            recommendations.append("Recommend expanding strategy type diversity to handle different scenarios")
        
        most_used = max(strategy_dist, key=strategy_dist.get) if strategy_dist else "none"
        if strategy_dist.get(most_used, 0) > len(self.strategy_history[-10:]) * 0.6:
            recommendations.append(f"Over-reliance on {most_used}; recommend balancing strategy usage")
        
        return recommendations if recommendations else ["Current strategy system is running well"]

    async def _log_strategist_action(self, action_id: str, action_type: str, data: Dict[str, Any], attempt: int = 1) -> bool:
        """
        Record strategist actions to action_logs and parse data['strategy'] in detail.
        """
        try:
            # Use temporary connection to avoid affecting global database path
            # Ensure action_logs table exists
            # In real applications, the schema is usually created at startup, not checked each call
            execute_with_temp_connection(self.db_path, '''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE,
                    timestamp TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    effectiveness_score REAL,
                    situation_context TEXT,
                    strategic_decision TEXT,
                    execution_details TEXT,
                    lessons_learned TEXT,
                    full_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Prepare record data
            timestamp = datetime.now().isoformat()
            strategy_data = data.get("strategy", {}) if isinstance(data, dict) else {}
            
            success = data.get("success", False) if isinstance(data, dict) else False
            effectiveness_score = strategy_data.get("effectiveness_score", 0.0) # Assume effectiveness_score is in strategy

            # 1. Build situation_context
            # Includes threat assessment and trigger info
            situation_context = {
                "action_type": action_type,
                "attempt": attempt,
                "situation_assessment": strategy_data.get("situation_assessment", {}),
                "alert_data": data.get("alert", {}),
                "trigger_content": data.get("trigger_content", {})
            }

            # 2. Build strategic_decision
            # Includes decision process, rationale, and core argument
            strategic_decision = {
                "strategy_id": strategy_data.get("strategy_id", f"strategist_{action_id}"),
                "reasoning_process": strategy_data.get("tot_reasoning", {}),
                "core_counter_argument": strategy_data.get("core_counter_argument", ""),
                "outcome_prediction": strategy_data.get("expected_outcome", ""),
                "outcome_result": "successful" if success else "failed"
            }

            # 3. Build execution_details
            # Includes leader and agent instructions, plus amplifier plan
            execution_details = {
                "agent_type": "strategist",
                "action_phase": action_type,
                "leader_instruction": strategy_data.get("leader_instruction", {}),
                "agent_instructions": strategy_data.get("agent_instructions", {}),
                "amplifier_plan": strategy_data.get("amplifier_plan", {})
            }

            # 4. Build lessons_learned
            # Includes risk assessment and historical basis
            lessons_learned = {
                "summary": f"Strategist {action_type} attempt {attempt} {'succeeded' if success else 'failed'}",
                "risk_assessment": strategy_data.get("risk_assessment", "No risk assessment provided."),
                "historical_basis": strategy_data.get("historical_basis", {})
            }

            # 5. Build full_log (full log)
            # Includes all above info and full original data object
            full_log = {
                "metadata": {
                    "action_id": action_id,
                    "timestamp": timestamp,
                    "agent_type": "strategist",
                    "action_type": action_type,
                    "attempt": attempt
                },
                "situation_context": situation_context,
                "strategic_decision": strategic_decision,
                "execution_details": execution_details,
                "effectiveness_results": {
                    "overall_score": effectiveness_score,
                    "success": success
                },
                "lessons_learned": lessons_learned,
                "original_data": data  # Store full original data object
            }

            # Insert record
            execute_with_temp_connection(self.db_path, '''
                INSERT OR REPLACE INTO action_logs (
                    action_id, timestamp, execution_time, success, effectiveness_score,
                    situation_context, strategic_decision, execution_details, 
                    lessons_learned, full_log
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_id,
                timestamp,
                0.0,  # execution_time, can be calculated as needed
                success,
                effectiveness_score,
                json.dumps(situation_context, ensure_ascii=False, indent=2),
                json.dumps(strategic_decision, ensure_ascii=False, indent=2),
                json.dumps(execution_details, ensure_ascii=False, indent=2),
                json.dumps(lessons_learned, ensure_ascii=False, indent=2),
                json.dumps(full_log, ensure_ascii=False, default=str, indent=2) # Use default=str for non-serializable objects
            ))

            workflow_logger.info(f"📝 Strategist action logged in detail: {action_type} (ID: {action_id})")
            return True

        except Exception as e:
            workflow_logger.error(f"❌ Strategist action logging failed: {e}")
            return False


class SimpleLeaderAgent:
    """Simplified Leader Agent."""
    
    def __init__(self, agent_id: str = "leader_main"):
        self.agent_id = agent_id
        try:
            from multi_model_selector import multi_model_selector
            self.client, self.model = multi_model_selector.create_openai_client(role="leader")
        except Exception:
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (leader role)
            selector = MultiModelSelector()
            self.client, self.model = selector.create_openai_client(role="leader")
        self.content_history = []
    
    async def generate_content(self, instruction: Dict[str, Any], target_content: str = "") -> Dict[str, Any]:
        """Generate high-quality content based on instructions."""
        try:
            # Ensure instruction is a dict
            if not isinstance(instruction, dict):
                instruction = {}

            # Clean target content
            cleaned_target = self._clean_text(target_content)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a top-tier content creation expert. Create high-quality, impactful content based on instructions.

Creation Requirements:
- Tone: {instruction.get('tone', 'professional_rational')}
- Target Audience: {instruction.get('target_audience', 'rational users')}
- Content Length: {instruction.get('content_length', '150-300 words')}
- Style: {instruction.get('style', 'argumentative essay')}

Ensure content is original, persuasive, and logically clear. Generate content ONLY in English."""
                    },
                    {
                        "role": "user",
                        "content": f"""Creation Instructions:
Key Points: {instruction.get('key_points', [])}
Target Content: {cleaned_target}

                Please create a high-quality response content in English:"""
                    }
                ],
                temperature=0.9  # Increase to 0.9 for more diverse content generation
            )
            
            content = response.choices[0].message.content
            
            # Record content history
            content_record = {
                "content_id": f"leader_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "final_content": content,
                "instruction": instruction,
                "target_content": target_content,
                "timestamp": datetime.now()
            }
            
            self.content_history.append(content_record)
            
            return {
                "success": True,
                "content_generated": True,
                "content": content_record
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _clean_text(self, text: str) -> str:
        """Clean text to avoid encoding issues."""
        try:
            import re
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
            cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
            if len(cleaned) > 1000:
                cleaned = cleaned[:1000] + "..."
            return cleaned.strip()
        except Exception:
            return "Content contains special characters and cannot be displayed properly"

    async def _log_strategist_action(self, action_id: str, action_type: str, data: Dict[str, Any], attempt: int = 1) -> bool:
        """Record strategist action to action_logs table."""
        try:
            import json
            from datetime import datetime
            
            # Use global database manager
            db_manager = get_db_manager()
            db_manager.set_database_path(self.db_path)
            
            # Ensure action_logs table exists
            execute_query('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE,
                    timestamp TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    effectiveness_score REAL,
                    situation_context TEXT,
                    strategic_decision TEXT,
                    execution_details TEXT,
                    lessons_learned TEXT,
                    full_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Prepare record data
            timestamp = datetime.now().isoformat()
            success = data.get("success", False) if isinstance(data, dict) else False
            effectiveness_score = data.get("strategy", {}).get("effectiveness_score", 0.0) if isinstance(data, dict) else 0.0
            
            # Build situation_context
            situation_context = {
                "action_type": action_type,
                "attempt": attempt,
                "alert_data": data.get("alert", {}) if isinstance(data, dict) else {},
                "trigger_content": data.get("trigger_content", {}) if isinstance(data, dict) else {}
            }
            
            # Build strategic_decision
            strategic_decision = {
                "strategy_id": f"strategist_{action_id}",
                "action_type": action_type,
                "decision_making_process": f"Strategist {action_type}",
                "reasoning": f"Attempt {attempt}",
                "outcome": "successful" if success else "failed"
            }
            
            # Build execution_details
            execution_details = {
                "agent_type": "strategist",
                "action_phase": action_type,
                "attempt_number": attempt,
                "data_summary": str(data)[:500] if data else "No data"
            }
            
            # Build lessons_learned
            lessons_learned = [
                f"Strategist {action_type} attempt {attempt}",
                f"Result: {'succeeded' if success else 'failed'}",
                f"Time: {timestamp}"
            ]
            
            # Build full log
            full_log = {
                "metadata": {
                    "action_id": action_id,
                    "timestamp": timestamp,
                    "agent_type": "strategist",
                    "action_type": action_type,
                    "attempt": attempt
                },
                "situation_context": situation_context,
                "strategic_decision": strategic_decision,
                "execution_details": execution_details,
                "effectiveness_results": {
                    "overall_score": effectiveness_score,
                    "success": success
                },
                "lessons_learned": lessons_learned
            }
            
            # Insert record
            execute_query('''
                INSERT OR REPLACE INTO action_logs (
                    action_id, timestamp, execution_time, success, effectiveness_score,
                    situation_context, strategic_decision, execution_details, 
                    lessons_learned, full_log
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_id,
                timestamp,
                0.0,  # execution_time
                success,
                effectiveness_score,
                json.dumps(situation_context, ensure_ascii=False),
                json.dumps(strategic_decision, ensure_ascii=False),
                json.dumps(execution_details, ensure_ascii=False),
                json.dumps(lessons_learned, ensure_ascii=False),
                json.dumps(full_log, ensure_ascii=False, default=str)
            ))
            
            
            workflow_logger.info(f"📝 Strategist action recorded: {action_type} (ID: {action_id})")
            return True
            
        except Exception as e:
            workflow_logger.error(f"❌ Strategist action logging failed: {e}")
            return False


class SimpleamplifierAgent:
    """Simplified amplifier Agent - uses identities from positive_personas.jsonl."""

    def __init__(self, agent_id: str, persona_data: Dict[str, Any], coordination_system=None):
        self.agent_id = agent_id
        self.persona_data = persona_data
        self.coordination_system = coordination_system

        # Adapt to new database structure
        self.persona_id = persona_data.get("id", f"unknown_{agent_id}")
        self.name = persona_data.get("name", f"User_{agent_id}")
        self.persona_type = persona_data.get("type", "positive")
        self.profession = persona_data.get("demographics", {}).get("profession", "User")
        self.age_range = persona_data.get("demographics", {}).get("age", "Unknown")
        self.education = persona_data.get("demographics", {}).get("education", "Unknown")
        self.region = persona_data.get("demographics", {}).get("region", "Unknown")

        # Build display name
        self.persona_name = f"{self.age_range} {self.profession}"

        # Import multi-model selection system
        try:
            import sys
            sys.path.append('src')
            from multi_model_selector import multi_model_selector, get_random_model
            self.multi_model_selector = multi_model_selector
            self.selected_model = get_random_model("amplifier")

        except ImportError as e:
            workflow_logger.info(f"⚠️ Multi-model selection system import failed: {e}, using default model")
            self.multi_model_selector = None
            from multi_model_selector import MultiModelSelector
            self.selected_model = MultiModelSelector.DEFAULT_POOL[0]

        # Optimization: use shared client pool to speed up creation
        try:
            # First check shared client pool
            if (self.coordination_system and 
                hasattr(self.coordination_system, '_shared_client_pool') and 
                self.coordination_system._shared_client_pool is not None):
                # Use shared client pool
                pool = self.coordination_system._shared_client_pool
                self.client = pool['client']
                self.selected_model = pool['model']
                # Simplify logs: only record shared pool info for the first agent
                if not hasattr(self.coordination_system, '_shared_pool_logged'):
                    workflow_logger.info(f"✅ Shared client pool initialized, model: {pool['model']}")
                    self.coordination_system._shared_pool_logged = True
            elif self.multi_model_selector:
                # Use multi-model selector to create independent client
                self.client, _ = self.multi_model_selector.create_openai_client(self.selected_model, role="amplifier")
                workflow_logger.info(f"⚠️ amplifier Agent {agent_id} using independent client (shared pool not found)")
            else:
                from multi_model_selector import MultiModelSelector
                # Unified model selection via MultiModelSelector (amplifier role)
                selector = MultiModelSelector()
                self.client, self.selected_model = selector.create_openai_client(role="amplifier")
                workflow_logger.info(f"⚠️ amplifier Agent {agent_id} using selector fallback client")
        except Exception as e:
            workflow_logger.info(f"⚠️ amplifier Agent {agent_id} client creation failed: {e}, using selector fallback")
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (amplifier role)
            selector = MultiModelSelector()
            self.client, self.selected_model = selector.create_openai_client(role="amplifier")

        # Extract key info from persona data
        self.personality_traits = persona_data.get("personality_traits", ["Friendly", "Supportive"])
        self.personality = ", ".join(self.personality_traits)
        self.interests = persona_data.get("interests", ["General topics"])

        # Generate description
        self.description = self._generate_description()

        # Set communication style (based on persona type and traits)
        self.tone, self.language_style, self.argument_approach = self._determine_communication_style()

        # Set social tendency (compatible with old code)
        self.social_tendency = self.profession

        # Set goals and values
        self.primary_goal = f"To contribute as a {self.profession} with {self.argument_approach.lower()}"
        self.values = f"{self.personality}, {self.persona_type.title()} perspective, Constructive dialogue"

        # Generate example responses (based on persona traits)
        self.examples = self._generate_examples_from_persona()



    def _generate_description(self) -> str:
        """Generate description based on persona data."""
        return f"A {self.age_range} year old {self.profession} from {self.region}. " \
               f"Known for being {', '.join(self.personality_traits[:3])}, with interests in " \
               f"{', '.join(self.interests[:3])}. Education: {self.education}."

    def _determine_communication_style(self) -> tuple:
        """Determine communication style based on persona type and traits."""
        if self.persona_type == "positive":
            if "Humble" in self.personality_traits:
                return "Gentle", "Supportive", "Encouraging discussion"
            elif "Rational" in self.personality_traits:
                return "Professional", "Analytical", "Evidence-based reasoning"
            else:
                return "Friendly", "Warm", "Positive engagement"
        elif self.persona_type == "neutral":
            return "Balanced", "Objective", "Neutral analysis"
        else:  # negative
            return "Critical", "Skeptical", "Challenging perspectives"

    def _generate_examples_from_persona(self) -> List[str]:
        """Generate example responses based on persona data."""
        profession = self.profession.lower()
        personality_traits = [trait.lower() for trait in self.personality_traits]

        # Generate different examples based on profession
        if "doctor" in profession or "physician" in profession:
            return [
                "From a medical perspective, it's important to consider evidence-based approaches.",
                "Health and well-being should be our priority in this discussion.",
                "Let's focus on factual information and professional standards."
            ]
        elif "teacher" in profession or "educator" in profession:
            return [
                "This is a great opportunity to learn and understand different perspectives.",
                "Education and open dialogue are key to solving complex issues.",
                "Let me share some factual information that might help clarify this topic."
            ]
        elif "artist" in profession or "musician" in profession:
            return [
                "Creative expression and diverse perspectives enrich our discussions.",
                "Art teaches us to see beauty and meaning in different viewpoints.",
                "Let's approach this with creativity and open minds."
            ]
        elif "engineer" in profession or "scientist" in profession:
            return [
                "Based on research and evidence, here's what we know...",
                "Let's look at this from a scientific and analytical perspective.",
                "Data and facts can help us understand this better."
            ]
        elif "lawyer" in profession or "attorney" in profession:
            return [
                "It's important to consider the legal framework and due process.",
                "Let's examine this issue through the lens of justice and fairness.",
                "Evidence and proper procedures are essential for fair outcomes."
            ]
        else:
            # Generate default responses based on personality traits
            if "rational" in personality_traits:
                return [
                    "Let's approach this rationally and consider all perspectives.",
                    "Evidence and logical thinking can help us find solutions.",
                    "I appreciate the opportunity for thoughtful discussion."
                ]
            elif "humble" in personality_traits:
                return [
                    "Thank you for sharing this perspective, I'm always learning.",
                    "I appreciate the chance to understand different viewpoints.",
                    "Let's approach this with humility and open minds."
                ]
            else:
                # Default positive responses
                return [
                    "Thank you for sharing this perspective.",
                    "This is an important topic that deserves thoughtful discussion.",
                    "Let's approach this with kindness and understanding."
                ]

    async def generate_response(self, target_content, timing_delay: int = 0, target_post_id: str = None) -> Dict[str, Any]:
        """Generate persona response - modified to support specified target post."""
        try:
            # Process enhanced format input
            if isinstance(target_content, dict):
                # New format: dict containing instructions
                actual_content = target_content.get("original_content", str(target_content))
                role_instruction = target_content.get("role_instruction", {})
                # Get target_post_id from dict if present
                if not target_post_id:
                    target_post_id = target_content.get("target_post_id")
                # Combined log record
                workflow_logger.info(f"🤖 Agent {self.agent_id} ({self.persona_name}) start generating response - enhanced format, instruction: {role_instruction.get('response_style', 'none')}")
            else:
                # Simple string content
                actual_content = str(target_content)
                role_instruction = {}
                # Combined log record
                workflow_logger.info(f"🤖 Agent {self.agent_id} ({self.persona_name}) start generating response - simple format")

            # Validate content is not empty
            if not actual_content or not actual_content.strip():
                # Log to workflow
                workflow_logger.warning(f"⚠️ Agent {self.agent_id}: target content is empty")
                # Terminal output
                logging.warning(f"⚠️ Agent {self.agent_id}: target content is empty")
                return {"success": False, "error": "target content is empty"}

            # Prepare role guidance and few-shot examples
            role_guidance = self._prepare_role_guidance(role_instruction)
            few_shot_examples_text = self._prepare_few_shot_examples()

            # Add timestamp and random seeds to increase diversity
            import time
            import random
            current_time = datetime.now()
            time_seed = int(time.time() * 1000) % 10000
            random_seed = random.randint(1000, 9999)

            # Add mood and time context
            mood_options = ["thoughtful", "enthusiastic", "curious", "supportive", "analytical",
                          "empathetic", "optimistic", "reflective", "engaged", "constructive",
                          "friendly", "encouraging", "insightful", "balanced", "understanding",
                          "positive", "collaborative", "open-minded", "respectful", "genuine"]
            current_mood = random.choice(mood_options)

            # Add diversified response styles
            response_styles = [
                "conversational and casual",
                "thoughtful and measured",
                "enthusiastic and energetic",
                "calm and balanced",
                "warm and supportive",
                "analytical and precise",
                "creative and expressive",
                "direct and honest",
                "diplomatic and nuanced",
                "passionate and engaged"
            ]
            response_style = random.choice(response_styles)

            time_context = current_time.strftime("%H:%M")
            unique_session = f"{time_seed}_{random_seed}"

            # Clean target content
            cleaned_content = self._clean_text(actual_content)
            # Remove examples so the model can be creative
            examples = ""

            # Try current selected model; fallback on failure
            current_model = self.selected_model
            max_retries = 3
            response = None

            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=current_model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are playing this character: {self.persona_name}

Character background:
{self.description}

Key traits:
- Values: {self.values}
- Personality: {self.personality}
- Social role: {self.social_tendency}
- Primary goal: {self.primary_goal}

{role_guidance}

{few_shot_examples_text}

NATURAL HUMAN CONVERSATION GUIDELINES

BE YOURSELF
- Speak as a real person with your own tone, rhythm, and perspective.  
- Let your background, interests, and quirks show naturally.  
- Be genuine, not formal or scripted. Avoid imitating others.

SOUND CONVERSATIONAL
- Talk like you’re chatting with a friend — relaxed, real, and spontaneous.  
- Use everyday language, contractions, or casual expressions when natural.  
- Mix sentence lengths and structures for flow, and react emotionally when it fits.  
- Ask questions, make observations, or share brief stories to keep it lively.

STAY DIVERSE
- Avoid repeating phrases, tone, or structure.  
- Change your style from response to response — sometimes curious, sometimes emotional, sometimes reflective.  
- Start and end messages differently.  
- Let different sides of your personality show across conversations.

BE THOUGHTFUL AND ENGAGED
- Show interest and curiosity — respond like you’re truly listening.  
- Build on what others say instead of just agreeing.  
- Ask follow-up questions or share insights that connect with the topic.  
- Show empathy, perspective, and genuine thought in your replies.

---

CONTEXT AWARENESS
- Time: {time_context} (adjust tone and energy accordingly)  
- Current mood: {current_mood}  
- Response style: {response_style}  
- Unique session: {unique_session}  

Each response should feel unique and spontaneous.  
Avoid patterns, repeated phrasing, or mechanical tone.  
Be authentic, emotionally aware, and conversational — like a real human interacting in the moment."""
                    },
                    {
                        "role": "user",
                        "content": f"""Please respond to the following content as your character:

{cleaned_content}

Requirements:
- Stay true to your character’s values and personality
- 30–120 characters (social media comment length — concise and expressive)

AUTHENTIC HUMAN RESPONSE GUIDELINES
- Speak naturally, as a real person would — spontaneous, genuine, and unscripted.
- Use your own voice, tone, and rhythm; don’t imitate templates or generic phrasing.
- Show your perspective, mood, and individuality through word choice and emotion.
- Use natural language and casual expressions; contractions or slang are fine if fitting.
- React genuinely — express surprise, humor, frustration, or curiosity when appropriate.
- Vary sentence length, tone, and structure; avoid repetition across responses.
- Sometimes ask a question, share a quick thought, or make an observation.
- Engage thoughtfully — show you’re actually thinking and responding to what was said.
- Keep it human: unpredictable, emotionally aware, and personal.

CRITICAL REQUIREMENTS
- Each response must be unique and natural — no repeated phrases or formats.
- Sound like a real conversation, not a script.
- Be concise, creative, and true to your persona.
- VARIETY IN AGREEMENT: If you agree, use diverse expressions instead of always saying "I agree":
  * "Exactly!", "Absolutely!", "You're right", "That makes sense", "I see what you mean"
  * "Spot on", "Well said", "Couldn't agree more", "That's a great point", "I'm with you on this"
  * "This resonates", "You nailed it", "Precisely", "I share that view", "That's spot-on"
  * Or start with a question, observation, or personal experience instead"""
                    }
                ],
                        temperature=0.95,  # Increase to 0.95 for more diverse amplifier responses
                        frequency_penalty=0.8,  # Reduce repeated content
                        presence_penalty=0.6   # Encourage new topics
                    )

                    # If successful, update selected model and break
                    self.selected_model = current_model
                    break

                except Exception as e:
                    workflow_logger.info(f"    ⚠️ Agent {self.agent_id} model {current_model} call failed: {e}")

                    # If multi-model selector is available, try fallback
                    if self.multi_model_selector and attempt < max_retries - 1:
                        fallback_model = self.multi_model_selector.handle_api_error(current_model, e)
                        if fallback_model:
                            current_model = fallback_model
                            workflow_logger.info(f"    🔄 Agent {self.agent_id} fallback to model: {current_model}")
                        else:
                            # No available fallback model, raise exception
                            raise e
                    else:
                        # Last attempt failed, raise exception
                        raise e

            # Check whether a response was obtained successfully
            if not response:
                raise Exception("All model attempts failed; no valid response")

            content = response.choices[0].message.content
            # Generate comment_id and save to database
            comment_id = self._save_comment_to_database(content, actual_content, target_post_id)
            
            # Simplify logs: do not record each agent response content, record in final display

            # If comment save failed, still return success (content generated successfully)
            if not comment_id:
                workflow_logger.info(f"    ⚠️  Agent {self.agent_id} comment save failed, but content generated successfully")
                comment_id = f"temp_comment_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            return {
                "success": True,
                "response_generated": True,
                "response": {
                    "response_id": f"amplifier_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "comment_id": comment_id,  # Add comment_id
                    "persona_id": self.persona_id,
                    "response_content": content,
                    "timing_delay": timing_delay,
                    "timestamp": datetime.now(),
                    "selected_model": self.selected_model  # Add model info
                },
                "persona_used": self.persona_name,
                "selected_model": self.selected_model  # Add model info
            }

        except Exception as e:
            workflow_logger.info(f"    ❌ Agent {self.agent_id} failed to generate response: {e}")
            import traceback
            workflow_logger.info(f"    📊 Error details: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    def _save_comment_to_database(self, content: str, target_content: str, target_post_id: str = None) -> str:
        """Save amplifier Agent comment to database."""
        try:
            from utils import Utils
            from datetime import datetime
            import json
            
            def save_comment_operation():
                # Generate comment_id
                comment_id = Utils.generate_formatted_id("comment")

                # Create amplifier Agent user ID (masquerade as a regular user)
                # Prefer sequential mapping from coordination system user pool for stable one-to-one mapping
                amplifier_agent_user_id = None
                user_suffix = None

                if self.coordination_system and hasattr(self.coordination_system, "_amplifier_user_id_pool"):
                    try:
                        # self.agent_id looks like "amplifier_000"
                        idx = int(str(self.agent_id).split("_")[1])
                    except (IndexError, ValueError):
                        idx = 0

                    # Defensive handling: modulo if index is out of pool range
                    pool = self.coordination_system._amplifier_user_id_pool
                    if pool:
                        amplifier_agent_user_id = pool[idx % len(pool)]
                        # Extract suffix for display name in fake_persona
                        try:
                            user_suffix = amplifier_agent_user_id.split("-", 1)[1]
                        except (IndexError, ValueError):
                            user_suffix = amplifier_agent_user_id

                # Fallback: if coordination system missing or pool abnormal, revert to original hash logic
                if amplifier_agent_user_id is None:
                    import hashlib
                    seed = f"amplifier_{self.agent_id}_{datetime.now().strftime('%Y%m%d')}"
                    hash_obj = hashlib.md5(seed.encode())
                    user_suffix = hash_obj.hexdigest()[:6]
                    amplifier_agent_user_id = f"user-{user_suffix}"

                # Ensure amplifier Agent user exists
                user_result = fetch_one('SELECT user_id FROM users WHERE user_id = ?', (amplifier_agent_user_id,))
                if not user_result:
                    # Create a persona that looks like a regular user
                    fake_persona = {
                        "name": f"User{user_suffix}",
                        "type": "amplifier",  # Internal marker
                        "profession": "Various",
                        "age_range": "25-40",
                        "personality_traits": ["Supportive", "Agreeable", "Constructive"],
                        "persona_name": self.persona_name,
                        "agent_role": "amplifier",
                        "is_system_agent": True
                    }
                    
                    execute_query('''
                        INSERT INTO users (user_id, persona, creation_time)
                        VALUES (?, ?, ?)
                    ''', (amplifier_agent_user_id, json.dumps(fake_persona, ensure_ascii=False), datetime.now().isoformat()))

                # Find target post (prefer provided target_post_id)
                final_target_post_id = None

                if target_post_id and target_post_id.strip():
                    # Validate provided target_post_id exists
                    result = fetch_one("SELECT COUNT(*) as count FROM posts WHERE post_id = ?", (target_post_id,))
                    if result and result['count'] > 0:
                        final_target_post_id = target_post_id
                        # Simplify logs: do not record each database operation
                    else:
                        # Simplified log record
                        workflow_logger.warning(f"⚠️ Specified target post {target_post_id} does not exist, searching fallback post")

                if not final_target_post_id:
                    # Prefer non-agent response posts (original user posts)
                    post_result = fetch_one('''
                        SELECT post_id FROM posts
                        WHERE is_agent_response IS NULL OR is_agent_response = 0
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''')

                    if not post_result:
                        # If no non-agent posts, find any post
                        post_result = fetch_one('''
                            SELECT post_id FROM posts
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''')

                    if post_result:
                        final_target_post_id = post_result['post_id']
                        # Simplified log record
                        workflow_logger.info(f"📍 amplifier Agent found fallback target post: {final_target_post_id}")
                    else:
                        # Simplified log record
                        workflow_logger.warning(f"❌ No posts found in database")
                        return None

                if final_target_post_id:
                    # Verify post exists before saving (avoid concurrency issues)
                    post_verify = fetch_one("SELECT COUNT(*) as count FROM posts WHERE post_id = ?", (final_target_post_id,))
                    if not post_verify or post_verify['count'] == 0:
                        workflow_logger.warning(f"    ⚠️  Simpleamplifier Agent {self.agent_id}: fallback post {final_target_post_id} no longer exists at save time, re-searching")
                        # Search fallback post again
                        post_result = fetch_one('''
                            SELECT post_id FROM posts
                            WHERE is_agent_response IS NULL OR is_agent_response = 0
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''')
                        if not post_result:
                            post_result = fetch_one('''
                                SELECT post_id FROM posts
                                ORDER BY created_at DESC
                            LIMIT 1
                        ''')
                        if post_result:
                            final_target_post_id = post_result['post_id']
                            workflow_logger.info(f"    📍 amplifier Agent {self.agent_id}: re-found fallback post {final_target_post_id}")
                        else:
                            workflow_logger.warning(f"    ⚠️  Simpleamplifier Agent {self.agent_id}: no posts in database, skip saving comment")
                            return None
                    
                    # Insert comment - includes model info
                    try:
                        execute_query('''
                            INSERT INTO comments (comment_id, content, post_id, author_id, created_at, selected_model, agent_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            comment_id,
                            content,
                            final_target_post_id,
                            amplifier_agent_user_id,
                            datetime.now().isoformat(),
                            self.selected_model,  # Model selected dynamically
                            "amplifier_agent"
                        ))
                        # Simplify logs: do not record each database operation
                    except Exception as e:
                        if "no column named" in str(e) or "no such column" in str(e):
                            # Simplified log record
                            workflow_logger.info(f"📊 Database missing new fields, using basic insert")
                            # If no new fields, use old insert
                            execute_query('''
                                INSERT INTO comments (comment_id, content, post_id, author_id, created_at)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                comment_id,
                                content,
                                final_target_post_id,
                                amplifier_agent_user_id,
                                datetime.now().isoformat()
                            ))
                            # Simplify logs: do not record each database operation
                        else:
                            workflow_logger.info(f"❌ Database operation error: {e}")
                            raise e

                    # Update post comment count
                    execute_query('''
                        UPDATE posts SET num_comments = num_comments + 1
                        WHERE post_id = ?
                    ''', (final_target_post_id,))

                    # Record comment -> timestep mapping
                    try:
                        # Get current time step from SimpleCoordinationSystem
                        current_step = getattr(self, 'current_time_step', None)
                        
                        if current_step is not None:
                            execute_query('''
                                INSERT OR REPLACE INTO comment_timesteps (comment_id, user_id, post_id, time_step)
                                VALUES (?, ?, ?, ?)
                            ''', (comment_id, amplifier_agent_user_id, final_target_post_id, int(current_step)))
                    except Exception as e:
                        # Non-fatal: mapping is best-effort
                        workflow_logger.debug(f"Failed to record comment timestep: {e}")

                    return comment_id
                else:
                    workflow_logger.info(f"⚠️ No posts in database, cannot save comment")
                    return None

            # Use database manager to execute operation
            result = save_comment_operation()
            if not result:
                workflow_logger.error("❌ Comment save failed")
                return None
            
            if result:
                # Trigger auto export
                try:
                    try:
                        from src.auto_export_manager import on_comment_created
                    except ImportError:
                        from auto_export_manager import on_comment_created
                    import hashlib
                    seed = f'amplifier_{self.agent_id}_{datetime.now().strftime("%Y%m%d")}'
                    user_id = f"user-{hashlib.md5(seed.encode()).hexdigest()[:6]}"
                    on_comment_created(result, user_id)
                except Exception as e:
                    pass

                # Trigger scenario class export
                try:
                    try:
                        from src.scenario_export_manager import get_scenario_export_manager
                    except ImportError:
                        from scenario_export_manager import get_scenario_export_manager
                    scenario_manager = get_scenario_export_manager()
                    if scenario_manager:
                        scenario_manager.export_comment(result)
                except Exception as e:
                    pass

                return result
            else:
                return None

        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to save amplifier comment: {e}")
            workflow_logger.info(f"    📊 Detailed error info: {str(e)}")
            import traceback
            workflow_logger.info(f"    📊 Error stack: {traceback.format_exc()}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean text to avoid encoding issues."""
        try:
            import re
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
            cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
            if len(cleaned) > 1000:
                cleaned = cleaned[:1000] + "..."
            return cleaned.strip()
        except Exception:
            return "Content contains special characters and cannot be displayed properly"

    def _prepare_role_guidance(self, role_instruction: Dict[str, Any]) -> str:
        """Prepare role guidance content."""
        try:
            if not role_instruction:
                return ""

            guidance_parts = []
            guidance_parts.append("CURRENT ROLE ASSIGNMENT:")

            if role_instruction.get("role_type"):
                guidance_parts.append(f"- Role: {role_instruction['role_type']}")

            if role_instruction.get("response_style"):
                guidance_parts.append(f"- Response Style: {role_instruction['response_style']}")

            if role_instruction.get("key_message"):
                guidance_parts.append(f"- Key Message: {role_instruction['key_message']}")

            if role_instruction.get("tone"):
                guidance_parts.append(f"- Tone: {role_instruction['tone']}")

            if role_instruction.get("typical_phrases"):
                phrases = ", ".join(role_instruction['typical_phrases'])
                guidance_parts.append(f"- Typical Phrases: {phrases}")

            return "\n".join(guidance_parts)

        except Exception as e:
            workflow_logger.error(f"       ❌ Failed to prepare role guidance: {e}")
            return ""

    def _prepare_few_shot_examples(self) -> str:
        """Prepare few-shot example content."""
        try:
            if not hasattr(self, 'few_shot_examples') or not self.few_shot_examples:
                return ""

            examples_text = ["FEW-SHOT EXAMPLES FOR YOUR ROLE:"]

            for i, example in enumerate(self.few_shot_examples[:3], 1):  # Show up to 3 examples
                scenario = example.get("scenario", f"Example {i}")
                response = example.get("response", "")
                style_notes = example.get("style_notes", "")

                examples_text.append(f"\nExample {i} - {scenario}:")
                examples_text.append(f'Response: "{response}"')
                if style_notes:
                    examples_text.append(f"Style Notes: {style_notes}")

            examples_text.append("\nUse these examples as inspiration for your response style and approach.")
            return "\n".join(examples_text)

        except Exception as e:
            workflow_logger.error(f"       ❌ Failed to prepare few-shot examples: {e}")
            return ""


class SimpleCoordinationSystem:
    """Simplified agent coordination system - supports auto trigger."""
    
    def _extract_post_id_from_content(self, content_text: str) -> Optional[str]:
        """Extract post ID from content_text.
        
        Args:
            content_text: Content text, may include "Post ID: post-xxxxx" format
            
        Returns:
            Extracted post ID, or None if not found
        """
        import re
        if not content_text:
            return None
        
        # Try to match "Post ID: post-xxxxx" format
        pattern = r'Post ID:\s*([a-zA-Z0-9_-]+)'
        match = re.search(pattern, content_text)
        if match:
            return match.group(1)
        
        # Try to match "post-xxxxx" format
        pattern = r'\bpost-[a-zA-Z0-9_-]+\b'
        match = re.search(pattern, content_text)
        if match:
            return match.group(0)
        
        return None

    def __init__(self, db_connection=None):
        # No longer manage DB connection directly; use database manager
        self.analyst = SimpleAnalystAgent()
        self.strategist = SimpleStrategistAgent()
        self.leader = EnhancedLeaderAgent()  # Use enhanced Leader Agent

        # Delay creating amplifier Agents - only create when intervention is needed
        self.amplifier_agents = []
        self._amplifier_agents_created = False
        # Load few-shot example config
        self.few_shot_examples = self._load_few_shot_examples()
        
        # Fixed pool of 100 amplifier agent IDs
        self._amplifier_agent_id_pool = [f"amplifier_{i:03d}" for i in range(100)]
        # Fixed pool of 100 external user-xxxxxx IDs mapped one-to-one with amplifier agents
        # Ensures each amplifier Agent has stable, traceable external user IDs across runs
        self._amplifier_user_id_pool = [f"user-{i:06d}" for i in range(100)]

        # Leader Agent uses a separate external ID pool
        # Following amplifier Agent design: internally only "Leader1/Leader2" roles,
        # externally mapped to the first two user-xxxxxx IDs for stability and traceability.
        self._leader_user_id_pool = [
            f"user-{900000 + i:06d}" for i in range(100)
        ]  # Current logic only uses indices 0/1
        
        # Initialize shared client pool to speed up amplifier Agent creation
        self._shared_client_pool = None
        self._initialize_shared_client_pool()
        
        # Unified threshold config - resolve mismatch between workflow and secondary intervention thresholds
        self.THRESHOLDS = {
            # Initial intervention thresholds
            "initial_intervention": {
                "extremism_threshold": 0.45,  # Viewpoint extremism threshold (0-1)
                "sentiment_threshold": 0.4   # Sentiment threshold (0-1)
            },
            # Secondary intervention thresholds
            "secondary_intervention": {
                "extremism_threshold": 0.45,  # Keep consistent with initial intervention
                "sentiment_threshold": 0.4   # Keep consistent with initial intervention
            },
            # Success criteria thresholds
            "success_criteria": {
                "extremism_threshold": 0.4,  # Success criteria: extremism should be below 0.4
                "sentiment_threshold": 0.4   # Success criteria: sentiment should be above 0.6
            },
            # Monitoring thresholds
            "monitoring": {
                "extremism_threshold": 0.2   # Monitoring threshold: 0-1 level
            }
        }

        # Initialize intelligent learning system as a core component
        self.learning_system = None
        self._learning_system_initialized = False

        self.action_history = []
        self.current_phase = "idle"

        # Phase three: feedback and iteration
        self.monitoring_active = False
        self.monitoring_tasks = {}
        self.monitoring_task_handles = {}
        self.feedback_history = []
        self.default_feedback_monitoring_interval = self._load_default_feedback_monitoring_interval()
        self.feedback_monitoring_cycles = self._load_feedback_monitoring_cycles()

        # Database connection
        self.db_path = self._get_database_path()
        self._init_database_connection()
        
        # Auto trigger configuration
        self.auto_trigger_enabled = False
        self.auto_trigger_callbacks = []
        
        workflow_logger.info("✅ Simplified coordination system initialized - using enhanced Leader Agent with USC workflow")
        workflow_logger.info(
            f"📊 Default feedback monitoring interval from configs/experiment_config.json: "
            f"{self.default_feedback_monitoring_interval} minutes"
        )
        workflow_logger.info(
            f"🔁 Feedback monitoring cycles from configs/experiment_config.json: "
            f"{self.feedback_monitoring_cycles} rounds"
        )

    def _load_default_feedback_monitoring_interval(self) -> int:
        """Load default feedback monitoring interval from configs/experiment_config.json."""
        config_path = Path(__file__).parent.parent.parent / "configs" / "experiment_config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"experiment config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)

        opinion_balance_cfg = config.get("opinion_balance_system")
        if not isinstance(opinion_balance_cfg, dict):
            raise ValueError(
                "opinion_balance_system section is missing in configs/experiment_config.json"
            )

        candidate = opinion_balance_cfg.get("feedback_monitoring_interval")
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if candidate.isdigit():
                candidate = int(candidate)
        if isinstance(candidate, (int, float)) and int(candidate) > 0:
            return int(candidate)

        raise ValueError(
            "opinion_balance_system.feedback_monitoring_interval must be a positive integer "
            f"in {config_path}, got: {opinion_balance_cfg.get('feedback_monitoring_interval')!r}"
        )

    def _load_feedback_monitoring_cycles(self) -> int:
        """Load feedback monitoring cycles from configs/experiment_config.json."""
        config_path = Path(__file__).parent.parent.parent / "configs" / "experiment_config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"experiment config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)

        opinion_balance_cfg = config.get("opinion_balance_system")
        if not isinstance(opinion_balance_cfg, dict):
            raise ValueError(
                "opinion_balance_system section is missing in configs/experiment_config.json"
            )

        candidate = opinion_balance_cfg.get("feedback_monitoring_cycles")
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if candidate.isdigit():
                candidate = int(candidate)
        if isinstance(candidate, (int, float)) and int(candidate) > 0:
            return int(candidate)

        raise ValueError(
            "opinion_balance_system.feedback_monitoring_cycles must be a positive integer "
            f"in {config_path}, got: {opinion_balance_cfg.get('feedback_monitoring_cycles')!r}"
        )
    
    def _get_fixed_amplifier_agent_ids(self, count: int) -> List[str]:
        """Allocate fixed number of IDs in order from the pool."""
        # Use first N fixed IDs to ensure the same IDs each run
        selected_ids = self._amplifier_agent_id_pool[:count]
        
        workflow_logger.info(f"  🔒 Allocated {len(selected_ids)} fixed Amplifier Agent IDs: {selected_ids[:5]}{'...' if len(selected_ids) > 5 else ''}")
        return selected_ids

    def _load_few_shot_examples(self) -> Dict[str, Any]:
        """Load few-shot example config."""
        try:
            script_dir = Path(__file__).parent.parent.parent  # Public-opinion-balance directory
            config_path = script_dir / "configs" / "few_shot_examples.json"

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    examples = json.load(f)
                workflow_logger.info(f"✅ Successfully loaded few-shot example config: {config_path}")
                return examples
            else:
                workflow_logger.warning(f"⚠️ Few-shot example config file not found: {config_path}")
                return self._get_default_few_shot_examples()

        except Exception as e:
            workflow_logger.error(f"❌ Failed to load few-shot example config: {e}")
            return self._get_default_few_shot_examples()

    def _get_default_few_shot_examples(self) -> Dict[str, Any]:
        """Get default few-shot examples."""
        return {
            "role_examples": {
                "technical_experts": {
                    "description": "Technical expert role - provide professional technical analysis",
                    "examples": [
                        {
                            "scenario": "Technical discussion",
                            "response": "From a technical perspective, this view is reasonable. Based on my engineering experience, modern systems do have such mechanisms.",
                            "style_notes": "Use technical terminology, based on professional experience"
                        }
                    ]
                },
                "balanced_moderates": {
                    "description": "Balanced moderates - provide rational, neutral viewpoints",
                    "examples": [
                        {
                            "scenario": "Controversial discussion",
                            "response": "This issue is indeed complex and requires multiple perspectives. Supporters and opponents both have reasonable concerns.",
                            "style_notes": "Acknowledge complexity, consider multiple perspectives"
                        }
                    ]
                },
                "community_voices": {
                    "description": "Community representative - speak from ordinary people's perspective",
                    "examples": [
                        {
                            "scenario": "Community issue",
                            "response": "As a member of the community, I care most about the real impact this has on our daily lives.",
                            "style_notes": "Start from personal experience, focus on practical impact"
                        }
                    ]
                },
                "fact_checkers": {
                    "description": "Fact checkers - emphasize evidence and accurate information",
                    "examples": [
                        {
                            "scenario": "Information verification",
                            "response": "I verified the source of this claim; reliable data shows the actual situation is...",
                            "style_notes": "Provide evidence sources, correct misinformation"
                        }
                    ]
                }
            },
            "timing_strategies": {
                "instant_consensus": {
                    "description": "Timing strategy to instantly build rational consensus",
                    "phases": [
                        {
                            "phase": "immediate_response",
                            "timing": "0-30 seconds",
                            "agent_count": "2-3 rapid responders",
                            "roles": ["community_voices", "balanced_moderates"],
                            "purpose": "Immediately establish a supportive tone"
                        }
                    ]
                }
            }
        }

    def _initialize_shared_client_pool(self):
        """Initialize shared client pool to speed up amplifier Agent creation."""
        try:
            # Try to use multi-model selector
            try:
                import sys
                sys.path.append('src')
                from multi_model_selector import multi_model_selector
                shared_client, shared_model = multi_model_selector.create_openai_client(role="amplifier")
                workflow_logger.info("✅ Shared client pool initialized successfully (multi-model selector)")
            except Exception as e:
                # If multi-model selector fails, use selector fallback
                from multi_model_selector import MultiModelSelector
                # Unified model selection via MultiModelSelector (amplifier role)
                selector = MultiModelSelector()
                shared_client, shared_model = selector.create_openai_client(role="amplifier")
                workflow_logger.info("✅ Shared client pool initialized successfully (selector fallback)")

            # Set shared client pool
            self._shared_client_pool = {
                'client': shared_client,
                'model': shared_model,
                'created_at': datetime.now()
            }
            
            workflow_logger.info(f"✅ Shared client pool initialized, model: {shared_model}")
            workflow_logger.info(f"🔍 Shared pool status: {self._shared_client_pool is not None}")

        except Exception as e:
            workflow_logger.error(f"❌ Failed to initialize shared client pool: {e}")
            self._shared_client_pool = None
            workflow_logger.info(f"🔍 Shared pool status: {self._shared_client_pool is not None}")

    def get_shared_client(self):
        """Get shared client for fast amplifier Agent creation."""
        if self._shared_client_pool:
            return self._shared_client_pool['client'], self._shared_client_pool['model']
        else:
            # If shared pool is unavailable, create a temporary client
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (amplifier role)
            selector = MultiModelSelector()
            return selector.create_openai_client(role="amplifier")
    
    def enable_auto_trigger(self, callback_function=None):
        """Enable auto-trigger mechanism.
        
        Args:
            callback_function: Custom callback to process triggered alerts
        """
        self.auto_trigger_enabled = True
        if callback_function:
            self.auto_trigger_callbacks.append(callback_function)
        
        # Set trigger callback for Analyst Agent
        self.analyst._trigger_downstream_systems = self._handle_analyst_trigger
        
        workflow_logger.info("✅ Auto-trigger mechanism enabled")
        workflow_logger.info(f"   📋 Callback count: {len(self.auto_trigger_callbacks)}")
    
    def disable_auto_trigger(self):
        """Disable auto-trigger mechanism."""
        self.auto_trigger_enabled = False
        self.auto_trigger_callbacks = []
        
        # Restore default trigger behavior
        async def default_trigger(alert):
            workflow_logger.info(f"   🚀 Trigger downstream system to handle alert: {alert.get('content_id', 'unknown')}")
        
        self.analyst._trigger_downstream_systems = default_trigger
        
        workflow_logger.info("❌ Auto-trigger mechanism disabled")
    
    async def _handle_analyst_trigger(self, alert: Dict[str, Any]):
        """Process alert triggered by analyst."""
        try:
            if not self.auto_trigger_enabled:
                workflow_logger.info(f"   ⚠️  Auto-trigger disabled, ignore alert: {alert.get('content_id', 'unknown')}")
                return
            
            workflow_logger.info(f"🚨 Analyst triggered auto-intervention alert")
            workflow_logger.info(f"   📋 Content ID: {alert.get('content_id', 'unknown')}")
            workflow_logger.info(f"   📊 Urgency: {alert.get('urgency_level', 'unknown')}")
            workflow_logger.info(f"   📝 Recommended action: {alert.get('recommended_action', 'unknown')}")
            
            # Extract alert content for workflow processing
            trigger_content = alert.get("trigger_content", {})
            content_for_workflow = ""
            
            if isinstance(trigger_content, dict):
                # Extract content from structured data
                content_for_workflow = trigger_content.get("core_viewpoint", "")
                if not content_for_workflow:
                    content_for_workflow = trigger_content.get("post_content", "")
                if not content_for_workflow:
                    content_for_workflow = str(trigger_content)
            else:
                content_for_workflow = str(trigger_content)
            
            if not content_for_workflow:
                content_for_workflow = f"Auto-triggered content from alert {alert.get('content_id', 'unknown')}"
            
            # Execute custom callbacks
            for callback in self.auto_trigger_callbacks:
                try:
                    await callback(alert, self)
                except Exception as e:
                    workflow_logger.info(f"   ❌ Callback execution failed: {e}")
            
            # Get current time step (when comment was posted)
            current_time_step = None
            try:
                from database.database_manager import fetch_one
                result = fetch_one('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                if result and result.get('max_step') is not None:
                    current_time_step = result.get('max_step')
            except Exception:
                pass
            
            # Start full three-phase workflow
            workflow_logger.info(f"🚀 Start automatic opinion balance workflow...")
            
            result = await self.execute_workflow(
                content_text=content_for_workflow,
                content_id=alert.get('content_id'),
                monitoring_interval=self.default_feedback_monitoring_interval,
                enable_feedback=True,
                force_intervention=False,  # Use analyst judgment result
                time_step=current_time_step  # Pass current time step
            )
            
            if result.get("success"):
                workflow_logger.info(f"✅ Auto workflow executed successfully")
                workflow_logger.info(f"   📋 Action ID: {result.get('action_id', 'unknown')}")
                workflow_logger.info(f"   📊 Effectiveness score: {result.get('phases', {}).get('phase_3', {}).get('effectiveness_score', 'N/A')}/10")
            else:
                workflow_logger.info(f"❌ Auto workflow execution failed: {result.get('error', 'unknown')}")
            
        except Exception as e:
            workflow_logger.info(f"❌ Failed to handle analyst trigger: {e}")
    
    async def start_auto_monitoring(self, extremism_threshold: int = 2,
                                  monitoring_interval: int = 0) -> str:
        """Start auto monitoring and intervention system.

        Args:
            extremism_threshold: Extremism standard (0-4 level)
            monitoring_interval: Monitoring interval (seconds)

        Returns:
            monitor_id: Monitoring task ID
        """

        # Enable auto-trigger mechanism
        self.enable_auto_trigger()

        # Start analyst continuous monitoring
        monitor_id = await self.analyst.start_continuous_monitoring(
            extremism_threshold=extremism_threshold,
            monitoring_interval=monitoring_interval
        )

        workflow_logger.info(f"🎯 Auto monitoring and intervention system started")
        workflow_logger.info(f"   📋 Monitor ID: {monitor_id}")
        workflow_logger.info("   🔄 Workflow: monitor -> analyze -> strategy -> execute -> feedback")
        
        return monitor_id
    
    def stop_auto_monitoring(self, monitor_id: str = None):
        """Stop auto monitoring and intervention system."""
        
        # Stop analyst monitoring
        self.analyst.stop_monitoring(monitor_id)
        
        # Disable auto-trigger
        self.disable_auto_trigger()
        
        # Stop coordination system monitoring
        if monitor_id:
            if monitor_id in self.monitoring_tasks:
                del self.monitoring_tasks[monitor_id]
        
        self.monitoring_active = False
        
        workflow_logger.info(f"⏹️  Auto monitoring and intervention system stopped")
    
    def get_auto_monitoring_status(self) -> Dict[str, Any]:
        """Get auto monitoring system status."""
        
        analyst_status = self.analyst.get_monitoring_status()
        coordination_status = self.get_monitoring_status()
        
        return {
            "auto_trigger_enabled": self.auto_trigger_enabled,
            "callback_count": len(self.auto_trigger_callbacks),
            "analyst_monitoring": analyst_status,
            "coordination_monitoring": coordination_status,
            "total_actions_completed": len(self.action_history),
            "current_phase": self.current_phase
        }

    def _get_database_path(self) -> str:
        """Get database path."""
        possible_paths = [
            "database/simulation.db",
            os.path.join("database", "simulation.db"),
            os.path.join(os.getcwd(), "database", "simulation.db"),
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "simulation.db")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # If none exist, return default path
        return "database/simulation.db"

    def _init_database_connection(self):
        """Initialize database connection."""
        try:
            # Use global database manager
            db_manager = get_db_manager()
            db_manager.set_database_path(self.db_path)
            workflow_logger.info(f"  📊 Database manager initialized successfully: {self.db_path}")
        except Exception as e:
            workflow_logger.info(f"  ⚠️  Database manager initialization failed: {e}")

    def _initialize_learning_system(self):
        """Initialize intelligent learning system."""
        if self._learning_system_initialized:
            return
            
        try:
            from intelligent_learning_system import IntelligentLearningSystem
            self.learning_system = IntelligentLearningSystem()
            self._learning_system_initialized = True
            workflow_logger.info(f"  🧠 Intelligent learning system initialized successfully")
        except Exception as e:
            workflow_logger.info(f"  ⚠️  Intelligent learning system initialization failed: {e}")
            self.learning_system = None

    def get_learning_system(self):
        """Get intelligent learning system instance (lazy init)."""
        if not self._learning_system_initialized:
            self._initialize_learning_system()
        return self.learning_system

    def _create_amplifier_agents_from_personas(self, max_agents: int = 10) -> List[SimpleamplifierAgent]:
        """Randomly select identities from positive_personas_database.json to create amplifier Agents."""
        import json
        import random
        import os

        try:
            # Directly load positive personas database
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", "personas", "positive_personas_database.json"),
                "personas/positive_personas_database.json",
                os.path.join("personas", "positive_personas_database.json"),
                os.path.join(os.getcwd(), "personas", "positive_personas_database.json")
            ]

            personas_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    personas_file = path
                    break

            if not personas_file:
                workflow_logger.info(f"  ⚠️  Cannot find positive_personas_database.json, using default config")
                return self._create_default_amplifier_agents(max_agents)

            # Read JSON database file
            with open(personas_file, 'r', encoding='utf-8') as f:
                personas = json.load(f)

            workflow_logger.info(f"  📋 Successfully read {len(personas)} positive roles")

            if not personas:
                workflow_logger.info(f"  ⚠️  No positive persona data loaded, using default config")
                return self._create_default_amplifier_agents(max_agents)

            # Randomly select specified number of personas
            selected_personas = random.sample(personas, min(max_agents, len(personas)))
            
            # Assign fixed IDs
            selected_ids = self._get_fixed_amplifier_agent_ids(len(selected_personas))

            # Create amplifier Agents
            amplifier_agents = []
            for i, (persona_data, agent_id) in enumerate(zip(selected_personas, selected_ids)):
                try:
                    agent = SimpleamplifierAgent(agent_id, persona_data, coordination_system=self)
                    amplifier_agents.append(agent)
                    # Simplify logs: do not record each agent creation
                except Exception as agent_error:
                    workflow_logger.info(f"    ❌ Failed to create amplifier Agent {i+1}: {agent_error}")
                    # Continue creating other agents without stopping the process

            if amplifier_agents:
                workflow_logger.info(f"  ✅ Successfully created {len(amplifier_agents)} amplifier Agents (target: {max_agents})")
                return amplifier_agents
            else:
                workflow_logger.info(f"  ⚠️  All amplifier Agent creation failed, using default config")
                return self._create_default_amplifier_agents(max_agents)

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to create agents from persona database: {e}")
            workflow_logger.info(f"  🔄 Create agents using default config")
            return self._create_default_amplifier_agents(max_agents)

    def _create_default_amplifier_agents(self, max_agents: int) -> List[SimpleamplifierAgent]:
        """Create default amplifier Agent configuration."""
        try:
            default_personas = [
                {
                    "id": f"default_{i}",
                    "name": f"DefaultUser{i+1:03d}",
                    "type": "positive",
                    "profession": ["Teacher", "Engineer", "Doctor", "Designer", "Writer"][i % 5],
                    "age_range": "25-45",
                    "education": "University",
                    "region": "General",
                    "personality_traits": ["Friendly", "Supportive", "Rational"],
                    "interests": ["Technology", "Discussion", "Community"]
                } for i in range(min(max_agents, 10))
            ]
            
            # Assign fixed IDs
            selected_ids = self._get_fixed_amplifier_agent_ids(len(default_personas))
            
            amplifier_agents = []
            for i, (persona_data, agent_id) in enumerate(zip(default_personas, selected_ids)):
                try:
                    agent = SimpleamplifierAgent(agent_id, persona_data, coordination_system=self)
                    amplifier_agents.append(agent)
                    workflow_logger.info(f"    ✅ Created default amplifier Agent {i+1}: {agent.persona_name} (ID: {agent_id})")
                except Exception as agent_error:
                    workflow_logger.info(f"    ❌ Failed to create default amplifier Agent {i+1}: {agent_error}")
                    continue
            
            workflow_logger.info(f"  ✅ Successfully created {len(amplifier_agents)} default amplifier Agents")
            return amplifier_agents
            
        except Exception as e:
            workflow_logger.info(f"  ❌ Failed to create default amplifier Agents as well: {e}")
            return []

    def _assign_roles_to_agents(self, agents: List, role_distribution: Dict[str, int]) -> List:
        """Assign roles to agents - simplified version, fix type comparison errors."""
        if not role_distribution:
            # If no role distribution, all agents use general role
            for i, agent in enumerate(agents):
                agent.assigned_role = "general"
            return agents

        workflow_logger.info(f"  🧠 Use role allocation strategy: {role_distribution}")

        # Assign agents by role type in a loop
        agent_index = 0
        for role_type, count in role_distribution.items():
            # Ensure count is int to fix type comparison errors
            try:
                count = int(count) if count is not None else 0
            except (ValueError, TypeError):
                workflow_logger.warning(f"  ⚠️ Role {role_type} count '{count}' is invalid, set to 0")
                count = 0

            if count <= 0:
                continue

            # Assign agents for this role type
            assigned_count = 0
            while assigned_count < count and agent_index < len(agents):
                agents[agent_index].assigned_role = role_type
                # Assign few-shot examples to each agent
                self._assign_few_shot_examples(agents[agent_index], role_type)
                agent_index += 1
                assigned_count += 1

            workflow_logger.info(f"     - {role_type}: assigned {assigned_count} agents")

        # Remaining agents use general role
        while agent_index < len(agents):
            agents[agent_index].assigned_role = "general"
            agent_index += 1

        return agents

    def _assign_few_shot_examples(self, agent, role_type: str):
        """Assign few-shot examples to agent."""
        try:
            role_examples = self.few_shot_examples.get("role_examples", {})
            if role_type in role_examples:
                examples = role_examples[role_type].get("examples", [])
                description = role_examples[role_type].get("description", "")

                # Assign few-shot examples to agent
                agent.few_shot_examples = examples
                agent.role_description = description

                # Simplify logs: only record few-shot assignment for the first agent
                if not hasattr(self, '_few_shot_logged'):
                    workflow_logger.info("📚 Few-shot examples assigned to all agents")
                    self._few_shot_logged = True
            else:
                # If no matching role examples found, use defaults
                agent.few_shot_examples = []
                agent.role_description = f"General {role_type} role"
                workflow_logger.info(f"       ⚠️ Agent {agent.agent_id} role examples not found, using default config")

        except Exception as e:
            workflow_logger.error(f"       ❌ Failed to assign few-shot examples to Agent {agent.agent_id}: {e}")
            agent.few_shot_examples = []
            agent.role_description = f"General {role_type} role"

    def _get_timing_strategy(self, amplifier_plan: Dict[str, Any], agent_count: int) -> Dict[str, Any]:
        """Get timing strategy configuration."""
        try:
            # Check whether instant consensus strategy is enabled
            timing_strategies = self.few_shot_examples.get("timing_strategies", {})
            instant_consensus_config = timing_strategies.get("instant_consensus", {})

            # If a specific timing strategy is configured or agent count fits
            if agent_count >= 3 and instant_consensus_config:
                phases = instant_consensus_config.get("phases", [])
                if phases:
                    return {
                        "strategy_type": "instant_consensus",
                        "phases": phases,
                        "total_agents": agent_count
                    }

            # Default to parallel strategy
            return {
                "strategy_type": "parallel",
                "total_agents": agent_count
            }

        except Exception as e:
            workflow_logger.error(f"       ❌ Failed to get timing strategy: {e}")
            return {"strategy_type": "parallel", "total_agents": agent_count}

    async def _execute_phased_consensus(self, selected_agents: List, target_content: str,
                                      timing_strategy: Dict[str, Any], target_post_id: str,
                                      agent_instructions: List, coordination_strategy: str) -> List[Dict[str, Any]]:
        """Execute phased consensus strategy."""
        all_results = []
        phases = timing_strategy.get("phases", [])

        for phase_index, phase_config in enumerate(phases):
            phase_name = phase_config.get("phase", f"phase_{phase_index}")
            timing = phase_config.get("timing", "0-30 seconds")
            preferred_roles = phase_config.get("roles", [])
            purpose = phase_config.get("purpose", "")

            workflow_logger.info(f"     🔄 Execute phase {phase_index + 1}: {phase_name} ({timing})")
            workflow_logger.info(f"        Purpose: {purpose}")

            # Select agents suitable for this phase
            phase_agents = self._select_agents_for_phase(selected_agents, preferred_roles, phase_config)

            if not phase_agents:
                workflow_logger.warning(f"        ⚠️ Phase {phase_name} has no suitable agents")
                continue

            # Execute agents in this phase
            phase_results = await self._execute_phase_agents(phase_agents, target_content, target_post_id,
                                                           agent_instructions, coordination_strategy, phase_config)
            all_results.extend(phase_results)

            # If not the last phase, wait for a while
            if phase_index < len(phases) - 1:
                delay_seconds = self._parse_timing_delay(timing)
                workflow_logger.info(f"        ⏳ Wait {delay_seconds} seconds before next phase")
                await asyncio.sleep(delay_seconds)

        return all_results

    def _select_agents_for_phase(self, all_agents: List, preferred_roles: List, phase_config: Dict) -> List:
        """Select suitable agents for a specific phase."""
        try:
            phase_agents = []
            agent_count_str = phase_config.get("agent_count", "1-2")

            # Parse agent count
            import re
            count_match = re.search(r'(\d+)', agent_count_str)
            target_count = int(count_match.group(1)) if count_match else 2

            # Prefer agents matching roles
            for role in preferred_roles:
                matching_agents = [agent for agent in all_agents
                                 if hasattr(agent, 'assigned_role') and agent.assigned_role == role
                                 and agent not in phase_agents]
                for agent in matching_agents[:target_count - len(phase_agents)]:
                    phase_agents.append(agent)
                    if len(phase_agents) >= target_count:
                        break

            # If still not enough, select other agents
            if len(phase_agents) < target_count:
                remaining_agents = [agent for agent in all_agents if agent not in phase_agents]
                for agent in remaining_agents[:target_count - len(phase_agents)]:
                    phase_agents.append(agent)

            workflow_logger.info(f"        ✅ Selected {len(phase_agents)} agents for this phase")
            return phase_agents

        except Exception as e:
            workflow_logger.error(f"        ❌ Failed to select phase agents: {e}")
            return all_agents[:2]  # Default to first 2

    async def _execute_phase_agents(self, phase_agents: List, target_content: str, target_post_id: str,
                                  agent_instructions: List, coordination_strategy: str,
                                  phase_config: Dict) -> List[Dict[str, Any]]:
        """Execute tasks for agents in a phase."""
        tasks = []
        for i, agent in enumerate(phase_agents):
            # Find corresponding specific instruction
            specific_instruction = self._find_or_generate_instruction(agent, i, target_content, agent_instructions)

            # Enhance content with phase info
            enhanced_content = {
                "original_content": target_content,
                "role_instruction": specific_instruction,
                "coordination_context": {
                    "strategy": coordination_strategy,
                    "phase": phase_config,
                    "agent_position": f"{i+1}/{len(phase_agents)}"
                },
                "target_post_id": target_post_id
            }

            task = agent.generate_response(enhanced_content, 0, target_post_id)
            tasks.append(task)

        # Execute tasks for this phase in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                workflow_logger.warning(f"        ⚠️ Phase agent {i+1} execution failed: {result}")
                continue
            if result and result.get("success"):
                successful_responses.append(result)

        workflow_logger.info(f"        ✅ Phase execution completed, {len(successful_responses)} successful responses")
        return successful_responses

    async def _execute_parallel_responses(self, selected_agents: List, target_content: str, target_post_id: str,
                                        agent_instructions: List, coordination_strategy: str) -> List[Dict[str, Any]]:
        """Execute traditional parallel response strategy."""
        tasks = []
        for i, agent in enumerate(selected_agents):
            timing_delay = (i + 1) * 2  # Each agent delayed by 2 seconds (log only, no actual delay)

            # Find corresponding specific instruction
            specific_instruction = self._find_or_generate_instruction(agent, i, target_content, agent_instructions)

            # Enhance content
            enhanced_content = {
                "original_content": target_content,
                "role_instruction": specific_instruction,
                "coordination_context": {
                    "strategy": coordination_strategy,
                    "agent_position": f"{i+1}/{len(selected_agents)}"
                },
                "target_post_id": target_post_id
            }

            task = agent.generate_response(enhanced_content, timing_delay, target_post_id)
            tasks.append(task)
            # Simplify logs: do not record each task creation

        workflow_logger.info(f"  🚀 Start parallel execution of {len(tasks)} agent tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results (reuse existing logic)
        return self._process_parallel_results(results)

    def _find_or_generate_instruction(self, agent, index: int, target_content: str, agent_instructions: List) -> Dict[str, Any]:
        """Find or generate agent instructions."""
        assigned_role = getattr(agent, 'assigned_role', 'general')

        # Find matching specific instruction
        for instruction in agent_instructions:
            if instruction.get("role_type") == assigned_role and instruction.get("agent_index") == index:
                return instruction

        # If no specific instruction found, generate a general one for this role
        if assigned_role != 'general':
            return self._generate_fallback_instruction(assigned_role, index, target_content)

        # Default instruction
        return {
            "role_type": "general",
            "response_style": "general support",
            "key_message": "Provide rational and constructive feedback"
        }

    def _parse_timing_delay(self, timing_str: str) -> int:
        """Parse timing delay string into seconds."""
        try:
            import re
            # Extract the first number
            match = re.search(r'(\d+)', timing_str)
            if match:
                return int(match.group(1))
            return 3  # Default 3 seconds
        except:
            return 3

    def _process_parallel_results(self, results: List) -> List[Dict[str, Any]]:
        """Process parallel execution results."""
        successful_responses = []
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                continue
            if result and result.get("success"):
                successful_responses.append(result)
            else:
                failed_count += 1

        # Simplify logs: record overall result only, not per-item
        workflow_logger.info(f"📊 Amplifier Agent results: {len(successful_responses)} succeeded, {failed_count} failed")
        return successful_responses

    def _generate_fallback_instruction(self, role_type: str, index: int, target_content: str) -> Dict[str, Any]:
        """Generate fallback instructions for a specific role."""
        try:
            if role_type == "technical_rational":
                return {
                    "role_type": role_type,
                    "agent_index": index,
                    "response_style": "professional analysis",
                    "key_message": "Provide objective analysis from a technical perspective",
                    "tone": "objective and professional",
                    "typical_phrases": ["From a technical perspective", "According to the data", "Research shows"],
                    "focus_points": ["Provide data support", "Clarify technical details"],
                    "response_length": "80-150 words"
                }
            elif role_type == "moderate_neutral":
                return {
                    "role_type": role_type,
                    "agent_index": index,
                    "response_style": "balanced and rational",
                    "key_message": "Provide balanced viewpoints and rational analysis",
                    "tone": "calm and balanced",
                    "typical_phrases": ["I think", "From another angle", "Rationally speaking"],
                    "focus_points": ["Ease opposing emotions", "Seek common ground"],
                    "response_length": "60-120 words"
                }
            elif role_type == "public_concern":
                return {
                    "role_type": role_type,
                    "agent_index": index,
                    "response_style": "express concern",
                    "key_message": "Express concerns and expectations from the public perspective",
                    "tone": "concerned but rational",
                    "typical_phrases": ["As an ordinary person", "What we care about is", "For everyone"],
                    "focus_points": ["Express public concerns", "Focus on real impact"],
                    "response_length": "70-130 words"
                }
            elif role_type == "skeptic":
                return {
                    "role_type": role_type,
                    "agent_index": index,
                    "response_style": "rational questioning",
                    "key_message": "Raise reasonable questions and request clarification",
                    "tone": "cautious skepticism",
                    "typical_phrases": ["Need more evidence", "This claim", "Have you considered"],
                    "focus_points": ["Raise reasonable questions", "Request evidence"],
                    "response_length": "50-100 words"
                }
            else:
                return {
                    "role_type": "general_support",
                    "agent_index": index,
                    "response_style": "general support",
                    "key_message": "Express support and understanding",
                    "tone": "neutral support",
                    "typical_phrases": ["I agree", "That makes sense", "Worth considering"],
                    "focus_points": ["Express support", "Increase discussion heat"],
                    "response_length": "40-80 words"
                }
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Failed to generate fallback instruction: {e}")
            return {
                "role_type": role_type,
                "response_style": "default",
                "key_message": "Participate in discussion",
                "tone": "neutral"
            }
    
    async def execute_workflow(self, content_text: str, content_id: str = None,
                             monitoring_interval: Optional[int] = None, enable_feedback: bool = True, 
                             force_intervention: bool = False, time_step: int = None) -> Dict[str, Any]:
        """Execute full three-phase workflow.

        Args:
            content_text: Content text to process
            content_id: Content ID (optional)
            monitoring_interval: Monitoring interval (minutes)
            enable_feedback: Whether to enable feedback and iteration system
            force_intervention: Whether to force intervention (skip analyst judgment)
            time_step: Current time step (when comments were posted)
        """

        # Input validation
        if not content_text or not content_text.strip():
            return {
                "success": False,
                "error": "input content cannot be empty",
                "action_id": "invalid_input"
            }

        # Set current time step (when comments were posted)
        if time_step is not None:
            self.current_time_step = time_step
            workflow_logger.debug(f"Set comment publish time step: {self.current_time_step}")

        if not isinstance(monitoring_interval, int) or monitoring_interval <= 0:
            raise ValueError(
                f"monitoring_interval must be a positive integer (minutes), got: {monitoring_interval!r}"
            )

        action_id = f"action_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        try:
            # Log to workflow
            workflow_logger.info(f"🚀 Start workflow execution - Action ID: {action_id}")
            workflow_logger.info(f"📋 Intervention ID: {action_id}")
            # Display full post content
            workflow_logger.info(f"🎯 Target content: {content_text}")
            workflow_logger.info(f"⚙️ Force intervention: {'yes' if force_intervention else 'no'}")
            workflow_logger.info(f"📊 Monitoring interval: {monitoring_interval} minutes")
            workflow_logger.info(f"🔄 Feedback iteration: {'enabled' if enable_feedback else 'disabled'}")
            
            # Verify post exists (if content_text includes post ID)
            extracted_post_id = self._extract_post_id_from_content(content_text) or content_id
            if extracted_post_id:
                try:
                    post_check = fetch_one("SELECT COUNT(*) as count FROM posts WHERE post_id = ?", (extracted_post_id,))
                    if post_check and post_check['count'] > 0:
                        workflow_logger.info(f"  ✅ Post exists: {extracted_post_id}")
                    else:
                        workflow_logger.warning(f"  ⚠️ Post {extracted_post_id} not found in database, continuing workflow")
                        # Log post statistics in database
                        try:
                            total_posts = fetch_one("SELECT COUNT(*) as count FROM posts")
                            recent_posts = fetch_all("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 5")
                            workflow_logger.info(f"  📊 Total posts in database: {total_posts['count'] if total_posts else 0}")
                            if recent_posts:
                                workflow_logger.info(f"  📋 Most recent 5 post IDs: {[p['post_id'] for p in recent_posts]}")
                        except Exception as e:
                            workflow_logger.warning(f"  ⚠️ Unable to query post statistics: {e}")
                except Exception as e:
                    workflow_logger.warning(f"  ⚠️ Error verifying post existence: {e}")
            
            # Simple startup info
            workflow_logger.info("🚨⚖️ Start opinion balance intervention system")
            
            # ===== Phase 1: perception and decision =====
            # Log to workflow
            workflow_logger.info("📊 Phase 1: perception and decision")
            workflow_logger.info("  🔍 Analyst is analyzing content...")
            analysis_result = await self.analyst.analyze_content(content_text, content_id)

            if not analysis_result or not analysis_result.get("success", False):
                self.current_phase = "error"
                error_msg = analysis_result.get('error', 'analysis failed') if analysis_result else 'analysis returned None'
                return {"success": False, "error": f"analyzefailed: {error_msg}", "action_id": action_id}

            # Display detailed analysis results
            analysis_data = analysis_result.get("analysis", {})
            workflow_logger.info("   📊 Analyst analysis completed:")
            # Full core viewpoint
            workflow_logger.info(f"      Core viewpoint: {analysis_data.get('core_viewpoint', 'unknown')}")

            # Calculate viewpoint extremism - based on LLM scores from comments
            try:
                viewpoint_extremism = await self._calculate_overall_viewpoint_extremism(content_text, content_id)
                if viewpoint_extremism is None:
                    viewpoint_extremism = 3.0  # Default medium value
            except Exception as e:
                workflow_logger.warning(f"  ⚠️ Failed to calculate viewpoint extremism: {e}")
                viewpoint_extremism = 3.0  # Default medium value

            # Calculate weighted sentiment per comment
            final_sentiment_score = await self._calculate_weighted_sentiment_from_comments(content_id)
            
            viewpoint_extremism_normalized = self._normalize_extremism_score(viewpoint_extremism)
            # Display viewpoint extremism and sentiment scores
            workflow_logger.info(f"      Viewpoint extremism: {viewpoint_extremism_normalized:.2f}/1.0")
            workflow_logger.info(f"      Overall sentiment: {final_sentiment_score:.2f}/1.0")

            # Get current engagement data as baseline
            try:
                baseline_engagement_data = await self._get_post_engagement_data(content_id)
                if baseline_engagement_data is None:
                    baseline_engagement_data = {"likes": 0, "comments": 0, "shares": 0}
            except Exception as e:
                workflow_logger.warning(f"  ⚠️ Failed to get post engagement data: {e}")
                baseline_engagement_data = {"likes": 0, "comments": 0, "shares": 0}
            
            # Save baseline data (real analysis at workflow start)
            baseline_analysis_data = {
                "analysis_result": analysis_data,
                "viewpoint_extremism": viewpoint_extremism_normalized,
                "sentiment_score": final_sentiment_score,  # Weighted sentiment from per-comment analysis
                "engagement_data": baseline_engagement_data,  # Use real database data
                "timestamp": datetime.now()
            }

            # Decide intervention need based on extremism and sentiment using unified thresholds
            EXTREMISM_THRESHOLD = self.THRESHOLDS["initial_intervention"]["extremism_threshold"]
            SENTIMENT_THRESHOLD = self.THRESHOLDS["initial_intervention"]["sentiment_threshold"]

            EXTREMISM_THRESHOLD_NORMALIZED = self._normalize_extremism_threshold(EXTREMISM_THRESHOLD)
            needs_intervention = (
                viewpoint_extremism_normalized >= EXTREMISM_THRESHOLD_NORMALIZED
                or final_sentiment_score <= SENTIMENT_THRESHOLD
            )

            workflow_logger.info(f"      Needs intervention: {'yes' if needs_intervention else 'no'}")

            # Override original intervention determination
            if not needs_intervention:
                analysis_result["alert_generated"] = False
            else:
                analysis_result["alert_generated"] = True
                # Update analysis data
                analysis_data["viewpoint_extremism"] = viewpoint_extremism_normalized
                analysis_data["needs_intervention"] = needs_intervention
                analysis_data["intervention_reason"] = (
                    f"Viewpoint extremism: {viewpoint_extremism_normalized:.2f}/1.0, "
                    f"sentiment: {final_sentiment_score:.2f}/1.0"
                )

            # If forced intervention, skip checks and execute directly
            if force_intervention:
                workflow_logger.info("   🔧 Force intervention mode: skip checks and execute intervention")
                analysis_result["alert_generated"] = True
                # If no alert, create a default alert
                if "alert" not in analysis_result or not analysis_result["alert"]:
                    analysis_result["alert"] = {
                        "content_id": content_id,
                        "post_id": content_id,
                        "core_viewpoint": analysis_data.get("core_viewpoint", "Force intervention mode"),
                        "extremism_level": viewpoint_extremism_normalized,
                        "sentiment_score": final_sentiment_score,
                        "urgency_level": 2,
                        "risk_level": "medium"
                    }
            
            if not analysis_result["alert_generated"]:
                self.current_phase = "completed"
                return {
                    "success": True,
                    "action_id": action_id,
                    "result": "no_intervention_needed",
                    "analysis": analysis_result["analysis"],
                    "intervention_triggered": False
                }

            # Display trigger reasons
            alert = analysis_result["alert"]
            urgency_level = alert.get("urgency_level", 1)
            workflow_logger.info(f"      Urgency level: {urgency_level}")

            # Show trigger reasons based on new decision logic
            trigger_reasons, _, _ = self._format_initial_intervention_trigger_reasons(
                viewpoint_extremism_raw=viewpoint_extremism,
                final_sentiment_score=final_sentiment_score,
                extremism_threshold_raw=EXTREMISM_THRESHOLD,
                sentiment_threshold=SENTIMENT_THRESHOLD,
            )

            if trigger_reasons:
                workflow_logger.info(f"      Trigger reasons: {' & '.join(trigger_reasons)}")
            else:
                workflow_logger.info("      Trigger reason: analyst determined intervention needed")

            workflow_logger.info("   🚨 Analyst determined opinion balance intervention needed!")
            workflow_logger.info(f"  ⚠️  Alert generated - Urgency: {alert['urgency_level']}")
            
            # 2. Strategist creates strategy
            strategy_result = await self.strategist.create_strategy(alert)

            # Check whether strategy result is None or invalid
            if strategy_result is None:
                self.current_phase = "error"
                return {"success": False, "error": "Strategy creation returned None", "action_id": action_id}

            if not strategy_result.get("success", False):
                self.current_phase = "error"
                return {"success": False, "error": f"Strategy creation failed: {strategy_result.get('error', 'unknown error')}", "action_id": action_id}
            
            strategy = strategy_result.get("strategy", {})
            if not strategy:
                self.current_phase = "error"
                return {"success": False, "error": "Strategy content is empty", "action_id": action_id}

            agent_instructions = strategy_result.get("agent_instructions", {})
            workflow_logger.info(f"  ✅ Strategy creation completed - Strategy ID: {strategy.get('strategy_id', 'unknown')}")

            # Display strategy details
            leader_instructions = agent_instructions.get("leader_instructions", {})
            amplifier_instructions = agent_instructions.get("amplifier_instructions", [])
            coordination_strategy = agent_instructions.get("coordination_strategy", "default coordination")

            # Get amplifier plan config
            amplifier_plan = strategy.get('amplifier_plan', {})
            planned_agents = amplifier_plan.get('total_agents', 5)
            role_distribution = amplifier_plan.get('role_distribution', {})

            # If role_distribution is empty, get from strategy_result
            if not role_distribution:
                strategy_amplifier_plan = strategy_result.get("amplifier_plan", {})
                role_distribution = strategy_amplifier_plan.get('role_distribution', {})

            workflow_logger.info("  📋 Strategy details:")
            workflow_logger.info(f"     🎯 Core argument: {strategy.get('core_counter_argument', 'balanced perspective')}")

            # Display leader style details
            leader_style = leader_instructions.get('speaking_style', 'rational and neutral')
            leader_tone = leader_instructions.get('tone', 'objective and fair')
            leader_approach = leader_instructions.get('approach', 'provide balanced perspective')
            workflow_logger.info(f"     👑 Leader style: {leader_style}")
            workflow_logger.info(f"        💬 Tone: {leader_tone}")
            workflow_logger.info(f"        🎯 Approach: {leader_approach}")

            # Phase 2: execution and amplification
            # Save leader content as comment to database
            # Prefer provided content_id as original post ID
            target_post_id = content_id

            # Clean possible prefix (e.g., "intervention_post_")
            if target_post_id and target_post_id.startswith("intervention_post_"):
                target_post_id = target_post_id.replace("intervention_post_", "")

            if not target_post_id:
                # Fallback: get from alert
                target_post_id = alert.get("post_id", "") or alert.get("target_post_id", "") or alert.get("content_id", "")
                if not target_post_id:
                    # Last fallback: get from alert_data
                    alert_data = alert.get("alert_data", {})
                    target_post_id = alert_data.get("post_id", "") or alert_data.get("content_id", "")
                
                # Clean possible prefix
                if target_post_id and target_post_id.startswith("intervention_post_"):
                    target_post_id = target_post_id.replace("intervention_post_", "")
            
            # Leader Agent runs USC process, generates candidates, and posts two comments
            workflow_logger.info("🎯 Leader Agent starts USC process and generates candidate comments...")
            content_result = await self.leader.generate_strategic_content(
                strategy,  # Pass full strategy object instead of leader_instruction
                content_text
            )

            if not content_result or not content_result.get("success", False):
                self.current_phase = "error"
                error_msg = content_result.get('error', 'content generation failed') if content_result else 'content generation returned None'
                return {"success": False, "error": f"Leader content generation failed: {error_msg}", "action_id": action_id}
            
            leader_content = content_result["content"]
            leader_model = leader_content.get("selected_model", "unknown")
            selected_comments = leader_content.get("selected_comments", [])

            # Prefer the first two comments returned by USC
            final_content_1 = ""
            final_content_2 = ""
            if len(selected_comments) >= 1:
                final_content_1 = selected_comments[0].get("content", "")
            if len(selected_comments) >= 2:
                final_content_2 = selected_comments[1].get("content", "")

            # Fallback: if selected_comments is missing, use final_content as at least one comment
            if not final_content_1:
                final_content_1 = leader_content.get("final_content", "")
            if not final_content_2:
                final_content_2 = leader_content.get("final_content", "")

            workflow_logger.info(f"✅ Leader USC core content generated (model: {leader_model})")
            workflow_logger.info(f"💬 👑 Leader comment 1 on post {target_post_id}: {final_content_1}")
            workflow_logger.info(f"💬 👑 Leader comment 2 on post {target_post_id}: {final_content_2}")
            
            # First leader posts a comment
            leader_comment_id = self._save_leader_comment_to_database(final_content_1, target_post_id, action_id)
            if leader_comment_id:
                # Log to workflow
                workflow_logger.info(f"💬 First leader comment ID: {leader_comment_id}")
                workflow_logger.info(f"🎯 Target post: {target_post_id}")
            else:
                # Log to workflow
                workflow_logger.warning("⚠️ First leader comment save failed")
                # Terminal output
                logging.warning("⚠️ First leader comment save failed")
            
            # Second leader posts a comment (use different action_id seed to generate different "user" ID)
            leader_comment_id_2 = self._save_leader_comment_to_database(final_content_2, target_post_id, f"{action_id}_leader2")
            if leader_comment_id_2:
                # Log to workflow
                workflow_logger.info(f"💬 Second leader comment ID: {leader_comment_id_2}")
                workflow_logger.info(f"🎯 Target post: {target_post_id}")
            else:
                # Log to workflow
                workflow_logger.warning("⚠️ Second leader comment save failed")
                # Terminal output
                logging.warning("⚠️ Second leader comment save failed")

            # 4. amplifier Agent responses
            # Activate amplifier Agent cluster
            # Log to workflow
            workflow_logger.info("⚖️ Activating Amplifier Agent cluster...")

            # Ensure amplifier_plan contains required fields
            if not isinstance(amplifier_plan, dict):
                amplifier_plan = {"total_agents": 5, "role_distribution": {}}

            # If role_distribution is missing, use defaults
            if not amplifier_plan.get("role_distribution"):
                amplifier_plan["role_distribution"] = {}

            workflow_logger.info(f"  📋 Amplifier plan: total={amplifier_plan.get('total_agents', 5)}, role distribution={amplifier_plan.get('role_distribution', {})}")

            # Enhance amplifier_plan with concrete instructions
            enhanced_amplifier_plan = amplifier_plan.copy()
            enhanced_amplifier_plan["agent_instructions"] = amplifier_instructions
            enhanced_amplifier_plan["coordination_strategy"] = coordination_strategy
            enhanced_amplifier_plan["timing_plan"] = agent_instructions.get("timing_plan", {})

            if amplifier_instructions:
                workflow_logger.info(f"  📋 Applying strategist amplifier instructions: {len(amplifier_instructions)} detailed instructions")
                workflow_logger.info(f"  🎯 Coordination strategy: {enhanced_amplifier_plan['coordination_strategy']}")

            try:
                # amplifier Agents generate responses based on the overall context of two leader comments
                amplifier_input_text = final_content_1 if not final_content_2 else f"{final_content_1}\n\n{final_content_2}"
                amplifier_responses = await self._coordinate_amplifier_agents(
                    amplifier_input_text,
                    enhanced_amplifier_plan,
                    target_post_id  # Pass target post ID to amplifier Agent
                )
                if amplifier_responses is None:
                    amplifier_responses = []
                    workflow_logger.warning("  ⚠️ amplifier coordination returned None, using empty list")
            except Exception as e:
                workflow_logger.warning(f"  ⚠️ amplifier coordination failed: {e}")
                amplifier_responses = []
            
            workflow_logger.info(f"  ✅ {len(amplifier_responses)} amplifier responses generated")

            # Highlighted amplifier agent content display
            for i, response in enumerate(amplifier_responses):
                if response.get("success") and "response" in response:
                    response_data = response["response"]
                    response_content = response_data.get("response_content", "")
                    comment_id = response_data.get("comment_id", f"amplifier-{i+1}")
                    persona_id = response_data.get("persona_id", f"persona-{i+1}")
                    selected_model = response_data.get("selected_model", "unknown")

                    # Highlighted amplifier agent content display
                    workflow_logger.info(f"💬 🤖 amplifier-{i+1} ({persona_id}) ({selected_model}) commented: {response_content}")

            # amplifier Agents like leader comments
            if leader_comment_id and amplifier_responses:
                workflow_logger.info("💖 amplifier Agents start liking leader comments...")
                likes_count = await self._amplifier_agents_like_leader_comment(leader_comment_id, amplifier_responses, leader_comment_id_2)
                if likes_count > 0:
                    workflow_logger.info(f"  ✅ {likes_count} amplifier Agents successfully liked leader comments")
                    workflow_logger.info(f"💖 {likes_count} amplifier Agents liked leader comments")
                    
                    # Based on amplifier agent count, add (amplifier_agent_count * 20) likes to each leader comment
                    amplifier_agent_count = len([r for r in amplifier_responses if r.get("success")])
                    workflow_logger.info(f"  📊 Prepare bulk likes: amplifier_agent_count={amplifier_agent_count}, will add {amplifier_agent_count * 20} likes")
                    if amplifier_agent_count > 0:
                        workflow_logger.info("  🔄 Starting bulk like operation...")
                        self._add_bulk_likes_to_leader_comments(leader_comment_id, leader_comment_id_2, amplifier_agent_count)
                        workflow_logger.info("  ✅ Bulk like operation completed")
                    else:
                        workflow_logger.warning("  ⚠️  amplifier_agent_count is 0, skipping bulk likes")
                else:
                    workflow_logger.info("  ⚠️  amplifier Agent likes failed or no valid responses")


            # ===== Calculate base effectiveness score =====
            workflow_logger.info("📊 Calculating base effectiveness score...")

            # Calculate base effectiveness score
            total_responses = len(amplifier_responses)
            successful_responses = len([r for r in amplifier_responses if r.get("success")])
            leader_success = content_result.get("success", False)

            # Base score calculation
            effectiveness_score = 5.0  # Base score
            if leader_success:
                effectiveness_score += 2.0  # Leader post success adds 2 points
            if total_responses > 0:
                success_rate = successful_responses / total_responses
                effectiveness_score += success_rate * 3.0  # amplifier success rate adds up to 3 points

            # Ensure score is within a reasonable range
            effectiveness_score = max(1.0, min(10.0, effectiveness_score))

            # Generate initial effectiveness report
            initial_effectiveness_report = {
                "effectiveness_score": effectiveness_score,
                "total_responses": total_responses,
                "successful_responses": successful_responses,
                "leader_success": leader_success,
                "success_rate": successful_responses / max(total_responses, 1),
                "timestamp": datetime.now()
            }

            workflow_logger.info(f"  📈 Base effectiveness score: {effectiveness_score:.1f}/10")
            workflow_logger.info(f"  📊 Response success rate: {successful_responses}/{total_responses}")

            # Ensure variables are defined in all branches
            strategist_supplementary_plan = {}
            supplementary_actions = []

            # ===== Phase 3: feedback and iteration (optional long-term monitor) =====
            if enable_feedback:
                # Log to workflow
                workflow_logger.info("📈 Phase 3: feedback and iteration")
                self.current_phase = "feedback"

                # Start continuous monitoring and feedback loop
                monitoring_task_id = await self.start_monitoring_and_feedback(
                    action_id=action_id,
                    leader_content=leader_content,
                    amplifier_responses=amplifier_responses,
                    monitoring_interval=monitoring_interval,
                    supplementary_plan=strategist_supplementary_plan,  # Pass supplementary plan for later monitoring
                    content_id=content_id,  # Pass content_id for monitoring
                    baseline_data=baseline_analysis_data,  # Pass the actual baseline analysis data
                    initial_strategy_result=strategy_result
                )

            else:
                workflow_logger.info("⏭️  Skip long-term monitoring phase (disabled by user)")
                self.current_phase = "completed"
                monitoring_task_id = None
    
            # Record full result
            action_result = {
                "action_id": action_id,
                "success": True,
                "intervention_triggered": True,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "phases": {
                    "phase_1": {
                        "analysis": analysis_result,
                        "strategy": strategy_result
                    },
                    "phase_2": {
                        "leader_content": content_result,
                        "amplifier_responses": amplifier_responses
                    },
                    "phase_3": {
                        "effectiveness_score": effectiveness_score,
                        "total_responses": len(amplifier_responses),
                        "monitoring_task_id": monitoring_task_id,
                        "monitoring_active": enable_feedback and monitoring_task_id is not None,
                        "feedback_enabled": enable_feedback,
                        "strategist_evaluation": strategist_supplementary_plan if enable_feedback else {},
                        "supplementary_actions": supplementary_actions if enable_feedback else [],
                        "initial_effectiveness_report": initial_effectiveness_report if enable_feedback else {}
                    }
                }
            }
            
            self.action_history.append(action_result)
            self.current_phase = "completed"
            
            workflow_logger.info(f"🎉 Workflow completed - effectiveness score: {effectiveness_score}/10")
            if enable_feedback and monitoring_task_id:
                workflow_logger.info(f"   📊 Monitoring task started: {monitoring_task_id}")
                workflow_logger.info("   🔄 Will continue monitoring and adjust dynamically")
            else:
                # Log to workflow
                workflow_logger.info("⏭️ Feedback and iteration disabled, workflow completed")
            
            return action_result
            
        except Exception as e:
            self.current_phase = "error"
            return {
                "success": False,
                "action_id": action_id,
                "error": f"Workflow execute failed: {str(e)}"
            }
    
    async def _archive_action_to_memory_core(self, action_result: Dict[str, Any]):
        """Archive the full action-result log to the cognitive memory core"""
        try:
            action_id = action_result.get("action_id")
            workflow_logger.info("\n📚 Archiving action logs to the cognitive memory core...")
            workflow_logger.info(f"   📋 Action ID: {action_id}")
            
            # Build full action-result log
            action_log = await self._create_comprehensive_action_log(action_result)
            
            # Extract learning insights
            learning_insights = await self._extract_learning_insights(action_log)
            
            # Save to multiple storage systems
            archive_results = await self._save_to_archive_systems(action_log, learning_insights)
            
            # Display archive results
            self._display_archive_results(action_id, archive_results)
            
        except Exception as e:
            workflow_logger.info(f"   ❌ Action log archive failed: {e}")
            logging.error(f"Action log archiving failed for {action_result.get('action_id', 'unknown')}: {e}")

    async def _create_comprehensive_action_log(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive action log"""
        try:
            action_id = action_result.get("action_id")
            phases = action_result.get("phases", {})
            
            # Extract detailed information from each phase
            phase1_data = phases.get("phase_1", {})
            phase2_data = phases.get("phase_2", {})
            phase3_data = phases.get("phase_3", {})
            
            analysis_data = phase1_data.get("analysis", {}).get("analysis", {})
            strategy_data = phase1_data.get("strategy", {}).get("strategy", {})
            leader_content = phase2_data.get("leader_content", {})
            amplifier_responses = phase2_data.get("amplifier_responses", [])
            
            # Build comprehensive log
            action_log = {
                "metadata": {
                    "action_id": action_id,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": action_result.get("execution_time", 0),
                    "system_version": "SimpleCoordinationSystem v1.0",
                    "workflow_type": "three_phase_opinion_balance"
                },
                
                "situation_context": {
                    "trigger_content": analysis_data.get("core_viewpoint", ""),
                    "post_theme": analysis_data.get("post_theme", ""),
                    "engagement_metrics": analysis_data.get("engagement_metrics", {}),
                    "sentiment_distribution": analysis_data.get("sentiment_distribution", {}),
                    "extremism_assessment": {
                        "level": analysis_data.get("extremism_level", 0),
                        "patterns": analysis_data.get("malicious_analysis", {}).get("attack_patterns", [])
                    }
                },
                
                "strategic_decision": {
                    "strategy_id": strategy_data.get("strategy_id", ""),
                    "situation_assessment": strategy_data.get("situation_assessment", {}),
                    "core_counter_argument": strategy_data.get("core_counter_argument", ""),
                    "leader_instruction": strategy_data.get("leader_instruction", {}),
                    "amplifier_plan": strategy_data.get("amplifier_plan", {}),
                    "expected_outcome": strategy_data.get("expected_outcome", ""),
                    "risk_assessment": strategy_data.get("risk_assessment", "")
                },
                
                "execution_details": {
                    "leader_response": {
                        "generated": leader_content.get("content_generated", False),
                        "content_length": len(str(leader_content.get("content", {}).get("final_content", ""))) if leader_content.get("content") else 0
                    },
                    "amplifier_responses": {
                        "total_planned": strategy_data.get("amplifier_plan", {}).get("total_agents", 0),
                        "successfully_generated": len([r for r in amplifier_responses if r.get("success")]),
                        "failed_generations": len([r for r in amplifier_responses if not r.get("success")]),
                        "role_distribution": strategy_data.get("amplifier_plan", {}).get("role_distribution", {}),
                        "models_used": list(set([r.get("selected_model") for r in amplifier_responses if r.get("selected_model")])),
                        "response_quality_scores": [r.get("response", {}).get("quality_score", 0.8) for r in amplifier_responses if r.get("success")]
                    }
                },
                
                "effectiveness_results": {
                    "overall_score": phase3_data.get("effectiveness_score", 0),
                    "total_responses": phase3_data.get("total_responses", 0),
                    "monitoring_active": phase3_data.get("monitoring_active", False),
                    "monitoring_task_id": phase3_data.get("monitoring_task_id"),
                    "feedback_enabled": phase3_data.get("feedback_enabled", False)
                },
                
                "outcome_analysis": {
                    "success_indicators": {
                        "workflow_completed": action_result.get("success", False),
                        "strategy_executed": bool(strategy_data),
                        "content_generated": leader_content.get("content_generated", False),
                        "amplifier_agents_activated": len(amplifier_responses) > 0,
                        "monitoring_initiated": phase3_data.get("monitoring_active", False)
                    },
                    "performance_metrics": {
                        "execution_efficiency": 1.0 if action_result.get("execution_time", 0) < 60 else 0.8,
                        "content_quality": sum(r.get("response", {}).get("authenticity_score", 0) for r in amplifier_responses if r.get("success")) / max(len(amplifier_responses), 1),
                        "strategic_coherence": 0.9 if strategy_data.get("situation_assessment") else 0.5
                    }
                },
                
                "lessons_learned": await self._extract_immediate_lessons(action_result),
                
                "future_improvements": await self._suggest_improvements(action_result)
            }
            
            return action_log
            
        except Exception as e:
            logging.error(f"Failed to create comprehensive action log: {e}")
            # Return basic log format
            return {
                "metadata": {
                    "action_id": action_result.get("action_id", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Log creation failed: {str(e)}"
                },
                "raw_result": action_result
            }

    async def _extract_immediate_lessons(self, action_result: Dict[str, Any]) -> List[str]:
        """Extract immediate lessons"""
        lessons = []
        
        try:
            phases = action_result.get("phases", {})
            
            # Extract lessons from execution result
            if action_result.get("success"):
                lessons.append("Three-phase workflow executed successfully")
                
                # Analyst phase lessons
                analysis_data = phases.get("phase_1", {}).get("analysis", {}).get("analysis", {})
                if analysis_data.get("extremism_level", 0) > 2:
                    lessons.append("High extremism content successfully identified and processed")
                
                # Strategist phase lessons
                strategy_data = phases.get("phase_1", {}).get("strategy", {}).get("strategy", {})
                if strategy_data.get("amplifier_plan", {}).get("role_distribution"):
                    lessons.append("Intelligent agent role distribution strategy applied")
                
                # Execution phase lessons
                amplifier_responses = phases.get("phase_2", {}).get("amplifier_responses", [])
                success_rate = len([r for r in amplifier_responses if r.get("success")]) / max(len(amplifier_responses), 1)
                if success_rate > 0.8:
                    lessons.append(f"High amplifier agent success rate achieved: {success_rate:.1%}")
                elif success_rate < 0.5:
                    lessons.append(f"Low amplifier agent success rate needs investigation: {success_rate:.1%}")
                
                # Monitoring phase lessons
                if phases.get("phase_3", {}).get("monitoring_active"):
                    lessons.append("Monitoring and feedback system successfully activated")
            else:
                lessons.append(f"Workflow failed: {action_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            lessons.append(f"Lesson extraction failed: {str(e)}")
            
        return lessons

    async def _suggest_improvements(self, action_result: Dict[str, Any]) -> List[str]:
        """Suggest improvements"""
        improvements = []
        
        try:
            phases = action_result.get("phases", {})
            amplifier_responses = phases.get("phase_2", {}).get("amplifier_responses", [])
            
            # Suggest improvements based on performance metrics
            if amplifier_responses:
                failed_responses = [r for r in amplifier_responses if not r.get("success")]
                if len(failed_responses) > len(amplifier_responses) * 0.2:  # Failure rate exceeds 20%
                    improvements.append("Consider improving amplifier agent error handling and retry mechanisms")
                
                # Analyze model usage
                models_used = [r.get("selected_model") for r in amplifier_responses if r.get("selected_model")]
                if len(set(models_used)) < 2:
                    improvements.append("Consider using more diverse models for better response variety")
            
            # Analyze execution time
            execution_time = action_result.get("execution_time", 0)
            if execution_time > 120:  # Over 2 minutes
                improvements.append("Consider optimizing workflow execution time for better responsiveness")
            
            # Analyze effectiveness score
            effectiveness_score = phases.get("phase_3", {}).get("effectiveness_score", 0)
            if effectiveness_score < 6:
                improvements.append("Low effectiveness score indicates need for strategy refinement")
            
        except Exception as e:
            improvements.append(f"Improvement analysis failed: {str(e)}")
            
        return improvements

    async def _extract_learning_insights(self, action_log: Dict[str, Any]) -> Dict[str, Any]:
        """Extract learning insights from action log"""
        try:
            insights = {
                "situation_patterns": {
                    "extremism_level": action_log.get("situation_context", {}).get("extremism_assessment", {}).get("level", 0),
                    "engagement_intensity": action_log.get("situation_context", {}).get("engagement_metrics", {}).get("intensity_level", "MODERATE"),
                    "sentiment_trend": action_log.get("situation_context", {}).get("sentiment_distribution", {}).get("overall_sentiment", "mixed")
                },
                
                "strategy_effectiveness": {
                    "chosen_approach": action_log.get("strategic_decision", {}).get("core_counter_argument", ""),
                    "agent_allocation": action_log.get("strategic_decision", {}).get("amplifier_plan", {}).get("role_distribution", {}),
                    "outcome_score": action_log.get("effectiveness_results", {}).get("overall_score", 0)
                },
                
                "execution_insights": {
                    "success_factors": action_log.get("lessons_learned", []),
                    "improvement_areas": action_log.get("future_improvements", []),
                    "performance_metrics": action_log.get("outcome_analysis", {}).get("performance_metrics", {})
                }
            }
            
            return insights
            
        except Exception as e:
            return {"extraction_error": str(e)}

    async def _save_to_archive_systems(self, action_log: Dict[str, Any], learning_insights: Dict[str, Any]) -> Dict[str, bool]:
        """Save to multiple archive systems"""
        results = {
            "file_system": False,
            "database": False,
            "intelligent_learning_system": False
        }
        
        # 1. Save to file system
        try:
            results["file_system"] = await self._save_to_file_system(action_log)
        except Exception as e:
            logging.error(f"File system archiving failed: {e}")
        
        # 2. Save to database
        try:
            results["database"] = await self._save_to_database(action_log)
        except Exception as e:
            logging.error(f"Database archiving failed: {e}")
        
        # 3. Save to intelligent learning system (if available)
        try:
            results["intelligent_learning_system"] = await self._save_to_learning_system(action_log, learning_insights)
        except Exception as e:
            logging.error(f"Learning system archiving failed: {e}")
        
        return results

    async def _save_to_file_system(self, action_log: Dict[str, Any]) -> bool:
        """Save to file system"""
        try:
            import os
            import json
            
            # Create archive directory - fix path
            script_dir = Path(__file__).parent.parent.parent  # Public-opinion-balance directory
            archive_dir = script_dir / "logs" / "action_archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            action_id = action_log.get("metadata", {}).get("action_id", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = archive_dir / f"action_log_{action_id}_{timestamp}.json"
            
            # Save log
            with open(str(filename), 'w', encoding='utf-8') as f:
                json.dump(action_log, f, indent=2, ensure_ascii=False, default=str)
            
            return True
            
        except Exception as e:
            logging.error(f"File system save failed: {e}")
            return False

    async def _save_to_database(self, action_log: Dict[str, Any]) -> bool:
        """Save to database with retry mechanism"""
        max_retries = 3
        retry_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                # Use database manager, no need to check connection

                # Use global database manager, cursor no longer needed

                # Ensure saved in action_logs table
                execute_query('''
                    CREATE TABLE IF NOT EXISTS action_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_id TEXT UNIQUE,
                        timestamp TEXT,
                        execution_time REAL,
                        success BOOLEAN,
                        effectiveness_score REAL,
                        situation_context TEXT,
                        strategic_decision TEXT,
                        execution_details TEXT,
                        lessons_learned TEXT,
                        full_log TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Insert log record
                metadata = action_log.get("metadata", {})
                effectiveness = action_log.get("effectiveness_results", {})

                execute_query('''
                    INSERT OR REPLACE INTO action_logs (
                        action_id, timestamp, execution_time, success, effectiveness_score,
                        situation_context, strategic_decision, execution_details,
                        lessons_learned, full_log
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.get("action_id"),
                    metadata.get("timestamp"),
                    metadata.get("execution_time", 0),
                    True,  # Archived records are all successful actions
                    effectiveness.get("overall_score", 0),
                    json.dumps(action_log.get("situation_context", {}), ensure_ascii=False),
                    json.dumps(action_log.get("strategic_decision", {}), ensure_ascii=False),
                    json.dumps(action_log.get("execution_details", {}), ensure_ascii=False),
                    json.dumps(action_log.get("lessons_learned", []), ensure_ascii=False),
                    json.dumps(action_log, ensure_ascii=False, default=str)
                ))

                # Database manager automatically handles transaction commits
                return True

            except Exception as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logging.warning(f"Database locked on attempt {attempt + 1}, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logging.error(f"Database save failed after {attempt + 1} attempts: {e}")
                    return False
            except Exception as e:
                logging.error(f"Database save failed: {e}")
                return False

        return False

    async def _save_to_learning_system(self, action_log: Dict[str, Any], learning_insights: Dict[str, Any]) -> bool:
        """Save to intelligent learning system"""
        try:
            # Use persistent learning system instance
            learning_system = self.get_learning_system()
            if not learning_system:
                logging.warning("Intelligent learning system unavailable, skipping learning data save")
                return False
            
            from intelligent_learning_system import ActionOutcome
            
            # Build ActionOutcome object
            metadata = action_log.get("metadata", {})
            situation = action_log.get("situation_context", {})
            strategic = action_log.get("strategic_decision", {})
            execution = action_log.get("execution_details", {})
            effectiveness = action_log.get("effectiveness_results", {})
            
            action_outcome = ActionOutcome(
                action_id=metadata.get("action_id", ""),
                timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                context=situation,
                strategy_applied=strategic,
                actions_executed=[execution],
                immediate_results=effectiveness,
                long_term_effects={},  # Empty for now, needs later monitoring data
                effectiveness_metrics={"overall_score": effectiveness.get("overall_score", 0)},
                success_indicators=action_log.get("outcome_analysis", {}).get("success_indicators", {}),
                lessons_learned=action_log.get("lessons_learned", []),
                failure_points=[]
            )
            
            # Record to learning system
            learning_system.record_action_outcome(action_outcome)
            
            return True
            
        except ImportError:
            # Intelligent learning system unavailable, skip
            return False
        except Exception as e:
            logging.error(f"Learning system save failed: {e}")
            return False

    def _display_archive_results(self, action_id: str, results: Dict[str, bool]):
        """Display archive results"""
        workflow_logger.info("   📊 Archive results:")
        
        for system, success in results.items():
            status = "✅" if success else "❌"
            system_name = {
                "file_system": "file system",
                "database": "database",
                "intelligent_learning_system": "intelligent learning system"
            }.get(system, system)
            
            workflow_logger.info(f"      {status} {system_name}")
        
        success_count = sum(results.values())
        total_count = len(results)
        
        if success_count == total_count:
            workflow_logger.info(f"   🎉 All systems archived successfully ({success_count}/{total_count})")
        elif success_count > 0:
            workflow_logger.info(f"   ⚠️  Partial archive success ({success_count}/{total_count})")
        else:
            workflow_logger.info(f"   ❌ All systems archive failed (0/{total_count})")
        
        workflow_logger.info(f"   📋 Action ID: {action_id} archive complete")
    
    async def _coordinate_amplifier_agents(self, target_content: str, amplifier_plan: Dict[str, Any], target_post_id: str = None) -> List[Dict[str, Any]]:
        """Coordinate amplifier Agent cluster - select agents based on strategic plan, supports target post"""

        # Get configuration from amplifier_plan and ensure correct type
        total_agents_raw = amplifier_plan.get("total_agents", 5)
        try:
            total_agents = int(total_agents_raw) if total_agents_raw is not None else 5
        except (ValueError, TypeError):
            workflow_logger.warning(f"  ⚠️ Invalid total_agents value '{total_agents_raw}', using default 5")
            total_agents = 5

        role_distribution = amplifier_plan.get("role_distribution", {})

        # If amplifier Agents are not created yet, create now
        if not self._amplifier_agents_created:
            workflow_logger.info("  🎭 First intervention needed, creating amplifier Agents...")
            # Create the required number of agents by role distribution
            try:
                self.amplifier_agents = self._create_amplifier_agents_from_personas(total_agents)
                if self.amplifier_agents:
                    workflow_logger.info(f"  ✅ Successfully created {len(self.amplifier_agents)} amplifier Agents")
                    self._amplifier_agents_created = True
                else:
                    workflow_logger.info("  ❌ amplifier Agent creation failed - returning empty list")
                    return []
            except Exception as e:
                workflow_logger.info(f"  ❌ amplifier Agent creation error: {e}")
                import traceback
                workflow_logger.info(f"  📊 Error details: {traceback.format_exc()}")
                return []
        else:
            # If counts mismatch, rely entirely on amplifier plan count and recreate
            if len(self.amplifier_agents) != total_agents:
                workflow_logger.info(f"  🔄 Agent count mismatch, relying on amplifier plan count (current: {len(self.amplifier_agents)}, need: {total_agents})")
                # Recreate required number of agents
                try:
                    self.amplifier_agents = self._create_amplifier_agents_from_personas(total_agents)
                    if self.amplifier_agents:
                        workflow_logger.info(f"  ✅ Recreated {len(self.amplifier_agents)} amplifier Agents")
                    else:
                        workflow_logger.info("  ❌ amplifier Agent recreation failed - returning empty list")
                        return []
                except Exception as e:
                    workflow_logger.info(f"  ❌ amplifier Agent recreation error: {e}")
                    return []

        # Use all created agents and assign roles
        try:
            selected_agents = self._assign_roles_to_agents(self.amplifier_agents, role_distribution)
            # Simplified logging: only record overall allocation
            workflow_logger.info(f"🎯 Agent role assignment complete: {len(selected_agents)} agents assigned roles")
        except Exception as e:
            workflow_logger.info(f"  ❌ Agent role assignment error: {e}")
            import traceback
            workflow_logger.info(f"  📊 Error details: {traceback.format_exc()}")
            return []

        workflow_logger.info(f"  ✅ Selected {len(selected_agents)} amplifier Agents for execution")

        if not selected_agents:
            workflow_logger.info("  ⚠️  Warning: no available amplifier Agents!")
            return []

        # Get strategist instructions
        agent_instructions = amplifier_plan.get("agent_instructions", [])
        coordination_strategy = amplifier_plan.get("coordination_strategy", "default coordination")
        timing_plan = amplifier_plan.get("timing_plan", {})



        # Implement instant consensus timing strategy
        timing_strategy = self._get_timing_strategy(amplifier_plan, len(selected_agents))

        # # Execute in groups based on timing strategy
        # if timing_strategy.get("strategy_type") == "instant_consensus":
        #     workflow_logger.info("  ⏱️ Using instant consensus strategy, executing in phases")
        #     results = await self._execute_phased_consensus(selected_agents, target_content, timing_strategy, target_post_id, agent_instructions, coordination_strategy)
        # else:
        workflow_logger.info("  ⏱️ Using traditional parallel execution strategy")
        results = await self._execute_parallel_responses(selected_agents, target_content, target_post_id, agent_instructions, coordination_strategy)

        # Use unified result processing to avoid duplicate logs
        return self._process_parallel_results(results)

    async def start_monitoring_and_feedback(self, action_id: str, leader_content: Dict[str, Any],
                                          amplifier_responses: List[Dict[str, Any]],
                                          monitoring_interval: Optional[int] = None,
                                          supplementary_plan: Dict[str, Any] = None,
                                          content_id: str = None,
                                          baseline_data: Dict[str, Any] = None,
                                          initial_strategy_result: Optional[Dict[str, Any]] = None) -> str:
        """Start phase 3: feedback and iteration monitoring

        Args:
            monitoring_interval: Monitoring interval (minutes), default comes from configs/experiment_config.json
        """

        if not isinstance(monitoring_interval, int) or monitoring_interval <= 0:
            raise ValueError(
                f"monitoring_interval must be a positive integer (minutes), got: {monitoring_interval!r}"
            )
        if not hasattr(self, "monitoring_task_handles") or not isinstance(self.monitoring_task_handles, dict):
            self.monitoring_task_handles = {}

        monitoring_task_id = f"monitor_{action_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        workflow_logger.info(f"  📊 Starting monitoring task: {monitoring_task_id}")
        workflow_logger.info(f"  ⏰ Monitoring interval: {monitoring_interval} minutes")

        # Show monitoring intensity based on interval
        if monitoring_interval <= 1:
            intensity_desc = "🔥 Ultra-high frequency monitoring"
        elif monitoring_interval <= 5:
            intensity_desc = "🚀 High frequency monitoring"
        elif monitoring_interval <= 10:
            intensity_desc = "⚡ Medium-high frequency monitoring"
        elif monitoring_interval <= 30:
            intensity_desc = "📊 Standard monitoring"
        else:
            intensity_desc = "🕐 Low frequency monitoring"
        workflow_logger.info(f"  📈 Monitoring intensity: {intensity_desc}")

        # Get target post ID (prefer content_id)
        target_post_id = content_id
        if not target_post_id and leader_content and "content" in leader_content:
            content_data = leader_content["content"]
            if isinstance(content_data, dict):
                target_post_id = content_data.get("content_id")
            else:
                target_post_id = "unknown_post_id"

        # Use provided baseline data (actual analysis results at workflow start)
        if not baseline_data:
            # If no baseline data provided, fetch from database (backward compatible)
            baseline_data = await self._get_baseline_from_workflow_result(target_post_id, action_id)
        
        # Create monitoring task
        monitoring_task = {
            "task_id": monitoring_task_id,
            "action_id": action_id,
            "target_post_id": target_post_id,  # Add target post ID
            "leader_content": leader_content,
            "amplifier_responses": amplifier_responses,
            "start_time": datetime.now(),
            "monitoring_interval": monitoring_interval,
            "feedback_reports": [],
            "adjustments_made": [],
            "supplementary_plan": supplementary_plan or {},  # Package strategist supplementary plan
            "strategist_enhanced": bool(supplementary_plan),   # Mark strategist enhancement
            "baseline_data": baseline_data,  # Save baseline data
            "initial_strategy_result": initial_strategy_result or {}
        }

        self.monitoring_tasks[monitoring_task_id] = monitoring_task
        self.monitoring_active = True

        # Start async monitoring loop and keep a trackable handle
        monitoring_task_handle = asyncio.create_task(self._monitoring_loop(monitoring_task_id))
        self.monitoring_task_handles[monitoring_task_id] = monitoring_task_handle
        monitoring_task_handle.add_done_callback(
            lambda completed_task, task_id=monitoring_task_id: self._on_monitoring_task_done(task_id, completed_task)
        )

        return monitoring_task_id

    def _on_monitoring_task_done(self, monitoring_task_id: str, task_handle: asyncio.Task):
        """Monitoring task completion callback for tracking/diagnostics."""
        try:
            task_meta = self.monitoring_tasks.get(monitoring_task_id)
            if isinstance(task_meta, dict):
                task_meta["completed_at"] = datetime.now()

            if task_handle.cancelled():
                workflow_logger.warning(f"  ⚠️ Monitoring task cancelled: {monitoring_task_id}")
                if isinstance(task_meta, dict):
                    task_meta["status"] = "cancelled"
                return

            exception = task_handle.exception()
            if exception is not None:
                workflow_logger.warning(f"  ⚠️ Monitoring task failed: {monitoring_task_id}, error={exception}")
                if isinstance(task_meta, dict):
                    task_meta["status"] = "failed"
                    task_meta["error"] = str(exception)
                return

            if isinstance(task_meta, dict):
                task_meta["status"] = "completed"
            workflow_logger.info(f"  ✅ Monitoring task finished: {monitoring_task_id}")
        except Exception as callback_error:
            workflow_logger.warning(
                f"  ⚠️ Monitoring task completion callback error ({monitoring_task_id}): {callback_error}"
            )
        finally:
            self.monitoring_task_handles.pop(monitoring_task_id, None)

    async def _monitoring_loop(self, monitoring_task_id: str):
        """Phase 3: feedback and iteration monitoring loop

        Flow:
        1. [Assess] Analyst Agent - monitor effectiveness
        2. [Iterate] Strategist Agent - dynamic adjustments
        3. [Learn] System - update memory
        """

        task = self.monitoring_tasks.get(monitoring_task_id)
        if not task:
            return

        monitoring_count = 0
        max_monitoring_cycles = self.feedback_monitoring_cycles

        # ========== Multi-round monitoring loop ==========
        while monitoring_count < max_monitoring_cycles:
            monitoring_count += 1
            workflow_logger.info(f"\n🔄 [Monitoring round {monitoring_count}/{max_monitoring_cycles}]")
            
            # No wait before first monitoring round
            
            # Analyst Agent generates effectiveness report
            is_baseline = (monitoring_count == 1)
            report_type = "baseline" if is_baseline else f"monitoring_round_{monitoring_count}"
            workflow_logger.info(f"  📊 Analyst Agent - generate {'baseline' if is_baseline else f'round {monitoring_count}'} effectiveness report")
            
            try:
                feedback_report = await self._analyst_monitor_effectiveness(task, is_baseline=is_baseline)
                if feedback_report is None:
                    workflow_logger.warning("  ⚠️ Analyst monitoring returned None, skipping this round")
                    continue
            except Exception as e:
                workflow_logger.warning(f"  ⚠️ Analyst monitoring failed: {e}")
                continue
            
            feedback_report["report_type"] = report_type
            task["feedback_reports"].append(feedback_report)
            
            # Check if success criteria are met
            success_achieved = self._check_success_criteria(feedback_report, task)
            
            if success_achieved:
                workflow_logger.info("  🎉 Monitoring goal achieved! Stopping monitoring loop")
                break
            
            # Check whether intervention is needed
            if success_achieved is False:
                workflow_logger.info(f"  🚨 {'Baseline' if is_baseline else f'Round {monitoring_count}'} report indicates intervention needed...")
                
                # Construct alert object from feedback report
                alert = self._construct_alert_from_report(feedback_report, task)
                if not alert:
                    workflow_logger.warning("  ⚠️ Failed to construct alert object, skipping intervention")
                    continue
                
                # Execute intervention and update baseline data
                try:
                    intervention_result = await self._execute_intervention_from_alert(alert, task)
                    if intervention_result is None:
                        workflow_logger.warning("  ⚠️ Intervention execution returned None")
                        continue
                except Exception as e:
                    workflow_logger.warning(f"  ⚠️ Intervention execution error: {e}")
                    continue
                
                if intervention_result.get("success"):
                    workflow_logger.info(f"  ✅ {'Baseline' if is_baseline else f'Round {monitoring_count}'} intervention executed successfully")
                else:
                    workflow_logger.warning(f"  ⚠️ {'Baseline' if is_baseline else f'Round {monitoring_count}'} intervention execution failed: {intervention_result.get('error', 'unknown error')}")
            else:
                workflow_logger.info(f"  ✅ {'Baseline' if is_baseline else f'Round {monitoring_count}'} report shows no intervention needed, continue monitoring...")
            
            # Wait for interval after each round (except the last)
            if monitoring_count < max_monitoring_cycles:
                monitoring_interval_minutes = task.get("monitoring_interval")
                if not isinstance(monitoring_interval_minutes, int) or monitoring_interval_minutes <= 0:
                    raise ValueError(
                        f"task.monitoring_interval must be a positive integer, got: {monitoring_interval_minutes!r}"
                    )
                monitoring_interval_seconds = monitoring_interval_minutes * 60     # Convert to seconds
                workflow_logger.info(f"  ⏰ Waiting {monitoring_interval_minutes} minutes ({monitoring_interval_seconds} seconds) before next round...")
                await asyncio.sleep(monitoring_interval_seconds)
        
        # End of monitoring loop
        if monitoring_count >= max_monitoring_cycles:
            workflow_logger.info(f"  ⏰ Max monitoring cycles reached ({max_monitoring_cycles}), stopping monitoring")
        
        workflow_logger.info(f"  📋 Monitoring task completed, {monitoring_count} rounds executed")

        # Persist monitoring-based effectiveness_score into learning action_logs.
        # NOTE: Do not persist the initial (leader+amplifier) base score; only persist monitoring score.
        try:
            if persist_action_log_record and ActionLogRecord and isinstance(task, dict):
                feedback_reports = task.get("feedback_reports", [])
                if feedback_reports:
                    final_report = feedback_reports[-1]
                    effectiveness_assessment = final_report.get("effectiveness_assessment", {}) if isinstance(final_report, dict) else {}
                    monitoring_score = effectiveness_assessment.get("overall_score", None)

                    if isinstance(monitoring_score, (int, float)):
                        current_metrics = final_report.get("current_metrics", {}) if isinstance(final_report, dict) else {}
                        success_threshold = task.get("success_criteria", {}).get("overall_score_threshold", 0.6)
                        success_extremism_threshold = self._normalize_extremism_threshold(
                            self.THRESHOLDS["success_criteria"]["extremism_threshold"]
                        )
                        success = (
                            float(monitoring_score) >= float(success_threshold)
                            and self._normalize_extremism_score(current_metrics.get("extremism_score", 0.5)) <= success_extremism_threshold
                            and float(current_metrics.get("sentiment_score", 0.5)) >= float(self.THRESHOLDS["success_criteria"]["sentiment_threshold"])
                        )

                        baseline_data = task.get("baseline_data", {}) if isinstance(task.get("baseline_data", {}), dict) else {}
                        analysis_result = baseline_data.get("analysis_result", {}) if isinstance(baseline_data.get("analysis_result", {}), dict) else {}

                        initial_strategy_result = task.get("initial_strategy_result", {}) if isinstance(task.get("initial_strategy_result", {}), dict) else {}
                        strategy_data = initial_strategy_result.get("strategy", {}) if isinstance(initial_strategy_result.get("strategy", {}), dict) else {}

                        situation_context = {
                            "core_viewpoint": analysis_result.get("core_viewpoint", ""),
                            "post_theme": analysis_result.get("post_theme", ""),
                            "viewpoint_extremism": self._normalize_extremism_score(baseline_data.get("viewpoint_extremism")),
                            "sentiment_score": baseline_data.get("sentiment_score"),
                            "target_post_id": task.get("target_post_id"),
                        }

                        strategic_decision = {
                            "strategy_id": strategy_data.get("strategy_id", ""),
                            "core_counter_argument": strategy_data.get("core_counter_argument", ""),
                            "leader_instruction": strategy_data.get("leader_instruction", {}),
                            "amplifier_plan": strategy_data.get("amplifier_plan", {}),
                            "source": "monitoring_final_report",
                        }

                        execution_details = {
                            "leader_content": task.get("leader_content", {}),
                            "amplifier_responses": task.get("amplifier_responses", []),
                            "monitoring_interval": task.get("monitoring_interval"),
                        }

                        record = ActionLogRecord(
                            action_id=str(task.get("action_id", monitoring_task_id)),
                            timestamp=datetime.now().isoformat(),
                            execution_time=0.0,
                            success=bool(success),
                            effectiveness_score=float(monitoring_score),
                            situation_context=situation_context,
                            strategic_decision=strategic_decision,
                            execution_details=execution_details,
                            lessons_learned={"monitoring_rounds": monitoring_count},
                            full_log={"final_effectiveness_report": final_report},
                        )
                        persist_action_log_record(Path("learning_data/rag/rag_database.db"), record)
                        self._persist_monitoring_score_to_opinion_interventions(
                            action_id=record.action_id,
                            monitoring_score=float(monitoring_score),
                        )
                        workflow_logger.info(
                            f"  ✅ Persisted monitoring effectiveness_score={monitoring_score:.2f} to action_logs (action_id={record.action_id})"
                        )
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Failed to persist monitoring effectiveness to action_logs: {e}")

    def _persist_monitoring_score_to_opinion_interventions(self, action_id: str, monitoring_score: float):
        """Sync monitoring effectiveness score to opinion_interventions by action_id."""
        execute_query(
            """
            UPDATE opinion_interventions
            SET effectiveness_score = ?
            WHERE action_id = ?
            """,
            (float(monitoring_score), str(action_id)),
        )

    async def _update_task_baseline_after_intervention(self, task: Dict[str, Any], leader_content: Dict[str, Any], amplifier_responses: List[Dict[str, Any]]):
        """Update task baseline data after intervention for later monitoring iterations
        
        Args:
            task: Monitoring task
            leader_content: Leader content
            amplifier_responses: amplifier response list
        """
        try:
            # Update baseline data in task, including latest intervention results
            updated_baseline = {
                "intervention_timestamp": datetime.now(),
                "leader_content": leader_content,
                "amplifier_responses": amplifier_responses,
                "intervention_count": task.get("intervention_count", 0) + 1
            }
            
            # Update task baseline data
            if "updated_baseline" not in task:
                task["updated_baseline"] = []
            task["updated_baseline"].append(updated_baseline)
            task["intervention_count"] = updated_baseline["intervention_count"]
            
            workflow_logger.info(f"  📊 Updated task baseline data, intervention count: {updated_baseline['intervention_count']}")
            
        except Exception as e:
            workflow_logger.error(f"  ❌ Failed to update task baseline data: {e}")

    def _construct_alert_from_report(self, report: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """Construct an alert object with valid information from a baseline report
        
        Args:
            report: Baseline report containing analysis data
            task: Monitoring task containing target post information
            
        Returns:
            Dict[str, Any]: Constructed alert object
        """
        try:
            target_post_id = task.get("target_post_id", "")
            action_id = task.get("action_id", "")
            
            # Extract key data from report - fix data structure access
            raw_data = report.get("raw_data", {})
            baseline_data = raw_data.get("baseline_data", {})
            current_data = raw_data.get("current_data", {})
            
            # Construct trigger_content, reusing execute_workflow structure
            # Ensure core_viewpoint always exists, prefer multiple sources
            core_viewpoint = (
                baseline_data.get("analysis_result", {}).get("core_viewpoint") or
                baseline_data.get("analysis", {}).get("core_viewpoint") or
                baseline_data.get("core_viewpoint") or
                self._get_fallback_core_viewpoint(target_post_id) or
                "Unknown topic"
            )
            
            post_theme = (
                baseline_data.get("analysis_result", {}).get("post_theme") or
                baseline_data.get("analysis", {}).get("post_theme") or
                baseline_data.get("post_theme") or
                self._get_fallback_post_theme(target_post_id) or
                "General discussion"
            )
            
            # Log data retrieval for debugging
            workflow_logger.info("  🔍 Data retrieval details:")
            workflow_logger.info(f"     core_viewpoint: {core_viewpoint}")
            workflow_logger.info(f"     post_theme: {post_theme}")
            workflow_logger.info(f"     baseline_data keys: {list(baseline_data.keys())}")
            if "analysis_result" in baseline_data:
                workflow_logger.info(f"     analysis_result keys: {list(baseline_data['analysis_result'].keys())}")
            
            baseline_extremism_norm = self._normalize_extremism_score(
                baseline_data.get("viewpoint_extremism", 0.5)
            )

            trigger_content = {
                "core_viewpoint": core_viewpoint,
                "post_theme": post_theme,
                "engagement_metrics": baseline_data.get("engagement_data", {}),
                "sentiment_distribution": {
                    "overall_sentiment_score": baseline_data.get("sentiment_score", 0.5),
                    "sentiment_reasoning": "Baseline sentiment analysis"
                },
                "malicious_analysis": {
                    "extremism_level": baseline_extremism_norm,
                    "threat_assessment": "Baseline threat assessment from monitoring"
                }
            }
            
            # Construct alert object, reusing execute_workflow structure
            alert = {
                "content_id": target_post_id,
                "post_id": target_post_id,
                "target_post_id": target_post_id,
                "urgency_level": 2,  # Monitoring-triggered intervention, urgency set to 2
                "recommended_action": "monitoring_triggered_intervention",
                "trigger_content": trigger_content,
                "alert_data": {
                    "post_id": target_post_id,
                    "content_id": target_post_id,
                    "analysis_result": baseline_data.get("analysis_result", {}),
                    "viewpoint_extremism": baseline_extremism_norm,
                    "sentiment_score": baseline_data.get("sentiment_score", 0.5),
                    "needs_intervention": True,
                    "intervention_reason": (
                        f"Monitoring baseline report triggered: viewpoint extremism {baseline_extremism_norm:.2f}, "
                        f"sentiment {baseline_data.get('sentiment_score', 0.5):.2f}"
                    )
                },
                "core_viewpoint": trigger_content["core_viewpoint"],
                "post_theme": trigger_content["post_theme"],
                "threat_assessment": trigger_content["malicious_analysis"]["threat_assessment"]
            }
            
            workflow_logger.info("  📋 Alert object constructed from baseline report")
            workflow_logger.info(f"     🎯 Target post: {target_post_id}")
            workflow_logger.info(f"     🚨 Urgency: {alert['urgency_level']}")
            workflow_logger.info(f"     📊 Viewpoint extremism: {baseline_extremism_norm:.2f}/1.0")
            workflow_logger.info(f"     😊 Sentiment: {baseline_data.get('sentiment_score', 0.5):.2f}")
            
            return alert
            
        except Exception as e:
            workflow_logger.error(f"  ❌ Failed to construct alert object: {e}")
            return {}

    async def _execute_intervention_from_alert(self, alert: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute full intervention flow based on alert, reusing execute_workflow logic
        
        Args:
            alert: Constructed alert object
            task: Monitoring task
            
        Returns:
            Dict[str, Any]: Execution result
        """
        try:
            target_post_id = task.get("target_post_id", "")
            action_id = task.get("action_id", "")
            
            workflow_logger.info("  🚀 Starting monitoring-based intervention flow...")
            workflow_logger.info(f"     🎯 Target post: {target_post_id}")
            workflow_logger.info(f"     📋 Action ID: {action_id}")
            
            # 1. Strategist creates strategy - reuse execute_workflow logic
            strategy_result = await self.strategist.create_strategy(alert)
            
            # Check whether strategy result is None or invalid
            if strategy_result is None:
                return {"success": False, "error": "Strategy creation returned None", "action_id": action_id}
            
            if not strategy_result.get("success", False):
                return {"success": False, "error": f"Strategy creation failed: {strategy_result.get('error', 'unknown error')}", "action_id": action_id}
            
            strategy = strategy_result.get("strategy", {})
            if not strategy:
                return {"success": False, "error": "Strategy content is empty", "action_id": action_id}
            
            agent_instructions = strategy_result.get("agent_instructions", {})
            workflow_logger.info(f"  ✅ Strategy creation completed - Strategy ID: {strategy.get('strategy_id', 'unknown')}")
            
            # Display strategy details
            leader_instructions = agent_instructions.get("leader_instructions", {})
            amplifier_instructions = agent_instructions.get("amplifier_instructions", [])
            coordination_strategy = agent_instructions.get("coordination_strategy", "default coordination")
            
            # Get amplifier plan configuration
            amplifier_plan = strategy.get('amplifier_plan', {})
            planned_agents = amplifier_plan.get('total_agents', 5)
            role_distribution = amplifier_plan.get('role_distribution', {})
            
            # If role_distribution is empty, get from strategy_result
            if not role_distribution:
                strategy_amplifier_plan = strategy_result.get("amplifier_plan", {})
                role_distribution = strategy_amplifier_plan.get('role_distribution', {})
            
            workflow_logger.info("  📋 Strategy details:")
            workflow_logger.info(f"     🎯 Core argument: {strategy.get('core_counter_argument', 'balanced perspective')}")
            
            # Display leader style details
            leader_style = leader_instructions.get('speaking_style', 'rational and neutral')
            leader_tone = leader_instructions.get('tone', 'objective and fair')
            leader_approach = leader_instructions.get('approach', 'provide balanced perspective')
            workflow_logger.info(f"     👑 Leader style: {leader_style}")
            workflow_logger.info(f"        💬 Tone: {leader_tone}")
            workflow_logger.info(f"        🎯 Approach: {leader_approach}")
            
            # 2. Phase 2: execution and amplification - reuse execute_workflow logic
            # Get original post content for leader agent to generate content
            original_post_data = await self._get_original_post_data(target_post_id)
            content_text = original_post_data.get("content", "") or alert.get("trigger_content", {}).get("core_viewpoint", "")
            
            # Save leader content as comment to database
            target_post_id_clean = target_post_id
            if target_post_id_clean and target_post_id_clean.startswith("intervention_post_"):
                target_post_id_clean = target_post_id_clean.replace("intervention_post_", "")
            
            # First leader uses LLM to generate content
            workflow_logger.info("🎯 First leader agent starts generating content...")
            content_result_1 = await self.leader.generate_strategic_content(
                strategy,  # Pass full strategy object
                content_text
            )
            
            if not content_result_1 or not content_result_1.get("success", False):
                error_msg = content_result_1.get('error', 'content generation failed') if content_result_1 else 'content generation returned None'
                return {"success": False, "error": f"First leader content generation failed: {error_msg}", "action_id": action_id}
            
            leader_content_1 = content_result_1["content"]
            final_content_1 = leader_content_1.get("final_content", "")
            leader_model_1 = leader_content_1.get("selected_model", "unknown")
            workflow_logger.info("✅ First leader core content generated")
            workflow_logger.info(f"💬 👑 First leader ({leader_model_1}) commented on post {target_post_id_clean}: {final_content_1}")
            
            # Second leader uses LLM to generate content
            workflow_logger.info("🎯 Second leader agent starts generating content...")
            content_result_2 = await self.leader.generate_strategic_content(
                strategy,  # Pass full strategy object
                content_text
            )
            
            if not content_result_2 or not content_result_2.get("success", False):
                workflow_logger.warning("⚠️ Second leader content generation failed, continue using first leader comment")
                final_content_2 = final_content_1  # If it fails, use the first content
            else:
                leader_content_2 = content_result_2["content"]
                final_content_2 = leader_content_2.get("final_content", "")
                leader_model_2 = leader_content_2.get("selected_model", "unknown")
                workflow_logger.info("✅ Second leader core content generated")
                workflow_logger.info(f"💬 👑 Second leader ({leader_model_2}) commented on post {target_post_id_clean}: {final_content_2}")
            
            # First leader posts a comment
            leader_comment_id = self._save_leader_comment_to_database(final_content_1, target_post_id_clean, action_id)
            if leader_comment_id:
                workflow_logger.info(f"💬 First leader comment ID: {leader_comment_id}")
                workflow_logger.info(f"🎯 Target post: {target_post_id_clean}")
            else:
                workflow_logger.warning("⚠️ First leader comment save failed")
            
            # Second leader posts a comment
            leader_comment_id_2 = self._save_leader_comment_to_database(final_content_2, target_post_id_clean, f"{action_id}_leader2")
            if leader_comment_id_2:
                workflow_logger.info(f"💬 Second leader comment ID: {leader_comment_id_2}")
                workflow_logger.info(f"🎯 Target post: {target_post_id_clean}")
            else:
                workflow_logger.warning("⚠️ Second leader comment save failed")
            
            # 3. amplifier Agent responses - reuse execute_workflow logic
            workflow_logger.info("⚖️ Activating Amplifier Agent cluster...")
            
            # Ensure amplifier_plan contains required fields
            if not isinstance(amplifier_plan, dict):
                amplifier_plan = {"total_agents": 5, "role_distribution": {}}
            
            # If role_distribution is missing, use defaults
            if not amplifier_plan.get("role_distribution"):
                amplifier_plan["role_distribution"] = {}
            
            workflow_logger.info(f"  📋 Amplifier plan: total={amplifier_plan.get('total_agents', 5)}, role distribution={amplifier_plan.get('role_distribution', {})}")
            
            # Enhance amplifier_plan with concrete instructions
            enhanced_amplifier_plan = amplifier_plan.copy()
            enhanced_amplifier_plan["agent_instructions"] = amplifier_instructions
            enhanced_amplifier_plan["coordination_strategy"] = coordination_strategy
            enhanced_amplifier_plan["timing_plan"] = agent_instructions.get("timing_plan", {})
            
            if amplifier_instructions:
                workflow_logger.info(f"  📋 Applying strategist amplifier instructions: {len(amplifier_instructions)} detailed instructions")
                workflow_logger.info(f"  🎯 Coordination strategy: {enhanced_amplifier_plan['coordination_strategy']}")
            
            # Reuse amplifier coordination logic from execute_workflow
            try:
                # Use combined leader comments as amplifier agent input context
                amplifier_input_text = final_content_1 if not final_content_2 else f"{final_content_1}\n\n{final_content_2}"
                amplifier_responses = await self._coordinate_amplifier_agents(
                    amplifier_input_text,
                    enhanced_amplifier_plan,
                    target_post_id_clean  # Pass target post ID to amplifier Agent
                )
                if amplifier_responses is None:
                    amplifier_responses = []
                    workflow_logger.warning("  ⚠️ amplifier coordination returned None, using empty list")
            except Exception as e:
                workflow_logger.warning(f"  ⚠️ amplifier coordination failed: {e}")
                amplifier_responses = []
            
            workflow_logger.info(f"  ✅ {len(amplifier_responses)} amplifier responses generated")
            
            # Highlighted amplifier agent content display
            for i, response in enumerate(amplifier_responses):
                if response.get("success") and "response" in response:
                    response_data = response["response"]
                    response_content = response_data.get("response_content", "")
                    comment_id = response_data.get("comment_id", f"amplifier-{i+1}")
                    persona_id = response_data.get("persona_id", f"persona-{i+1}")
                    selected_model = response_data.get("selected_model", "unknown")
                    
                    # Highlighted amplifier agent content display
                    workflow_logger.info(f"💬 🤖 amplifier-{i+1} ({persona_id}) ({selected_model}) commented: {response_content}")
            
            # amplifier Agents like leader comments
            if leader_comment_id and amplifier_responses:
                workflow_logger.info("💖 amplifier Agents start liking leader comments...")
                likes_count = await self._amplifier_agents_like_leader_comment(leader_comment_id, amplifier_responses, leader_comment_id_2)
                if likes_count > 0:
                    workflow_logger.info(f"  ✅ {likes_count} amplifier Agents successfully liked leader comments")
                    workflow_logger.info(f"💖 {likes_count} amplifier Agents liked leader comments")
                    
                    # Based on amplifier agent count, add (amplifier_agent_count * 20) likes to each leader comment
                    amplifier_agent_count = len([r for r in amplifier_responses if r.get("success")])
                    workflow_logger.info(f"  📊 Prepare bulk likes: amplifier_agent_count={amplifier_agent_count}, will add {amplifier_agent_count * 20} likes")
                    if amplifier_agent_count > 0:
                        workflow_logger.info("  🔄 Starting bulk like operation...")
                        self._add_bulk_likes_to_leader_comments(leader_comment_id, leader_comment_id_2, amplifier_agent_count)
                        workflow_logger.info("  ✅ Bulk like operation completed")
                    else:
                        workflow_logger.warning("  ⚠️  amplifier_agent_count is 0, skipping bulk likes")
                else:
                    workflow_logger.info("  ⚠️  amplifier Agent likes failed or no valid responses")
            
            # Update task baseline data for later monitoring iterations
            combined_leader_content = {
                "final_content": amplifier_input_text
            }
            await self._update_task_baseline_after_intervention(task, combined_leader_content, amplifier_responses)
            
            return {
                "success": True,
                "action_id": action_id,
                "strategy_result": strategy_result,
                "leader_content": combined_leader_content,
                "amplifier_responses": amplifier_responses,
                "intervention_triggered": True
            }
            
        except Exception as e:
            workflow_logger.error(f"  ❌ Monitoring-based intervention execution failed: {e}")
            return {"success": False, "error": str(e), "action_id": task.get("action_id", "")}

    def _check_success_criteria(self, feedback_report: Dict[str, Any], task: Dict[str, Any]) -> bool:
        """Check whether success criteria are met - consistent with effectiveness report scoring
        
        Args:
            feedback_report: Feedback report containing effectiveness scores and more
            task: Monitoring task containing success criteria configuration
            
        Returns:
            bool: Whether success criteria are met
        """
        try:
            # Get effectiveness assessment data (using new structured format)
            effectiveness_assessment = feedback_report.get('effectiveness_assessment', {})
            baseline_metrics = feedback_report.get('baseline_metrics', {})
            current_metrics = feedback_report.get('current_metrics', {})
            change_metrics = feedback_report.get('change_metrics', {})
            
            # Get metrics
            current_extremism = current_metrics.get('extremism_score', 0.5)
            current_sentiment = current_metrics.get('sentiment_score', 0.5)
            extremism_change = change_metrics.get('extremism_change', 0.0)
            sentiment_change = change_metrics.get('sentiment_change', 0.0)
            overall_score = effectiveness_assessment.get('overall_score', 0.0)
            
            # Get success criteria defined in task (supports multiple criteria)
            # Use unified threshold config, remove hard improvement requirements
            success_criteria = task.get('success_criteria', {
                'overall_score_threshold': 0.6,      # Effectiveness score threshold (0-1)
                'extremism_threshold': self.THRESHOLDS["success_criteria"]["extremism_threshold"],  # Use unified threshold
                'sentiment_threshold': self.THRESHOLDS["success_criteria"]["sentiment_threshold"]   # Use unified threshold
                # Remove hard requirements for extremism_improvement and sentiment_improvement
            })
            
            # Check success criteria - only thresholds, not improvement magnitude
            extremism_threshold_normalized = self._normalize_extremism_threshold(
                success_criteria.get('extremism_threshold', 4.5)
            )
            criteria_results = {
                'overall_score': overall_score >= success_criteria.get('overall_score_threshold', 0.6),
                'extremism_absolute': current_extremism <= extremism_threshold_normalized,
                'sentiment_absolute': current_sentiment >= success_criteria.get('sentiment_threshold', 0.4)
                # Completely remove extremism_improvement and sentiment_improvement checks
            }
            
            # Determine success (all conditions required)
            success_achieved = all(criteria_results.values())
            
            # Detailed log output - show threshold checks and improvement info
            workflow_logger.info("  📊 Success criteria check details:")
            workflow_logger.info(f"     Overall score: {overall_score:.2f}/1.0 (required: >= {success_criteria.get('overall_score_threshold', 0.6)}) {'✅' if criteria_results['overall_score'] else '❌'}")
            workflow_logger.info(f"     Extremism: {current_extremism:.2f}/1.0 (required: <= {extremism_threshold_normalized:.2f}) {'✅' if criteria_results['extremism_absolute'] else '❌'}")
            workflow_logger.info(f"     Sentiment: {current_sentiment:.2f}/1.0 (required: >= {success_criteria.get('sentiment_threshold', 0.4)}) {'✅' if criteria_results['sentiment_absolute'] else '❌'}")
            workflow_logger.info("  📈 Improvement info:")
            workflow_logger.info(f"     Extremism improvement: {extremism_change:+.2f} (reference only, not required)")
            workflow_logger.info(f"     Sentiment improvement: {sentiment_change:+.2f} (reference only, not required)")
            
            if success_achieved:
                workflow_logger.info("  🎉 All success criteria met!")
            else:
                failed_criteria = [k for k, v in criteria_results.items() if not v]
                workflow_logger.info(f"  ⏳ Criteria not met yet: {', '.join(failed_criteria)}")
            
            return success_achieved
            
        except Exception as e:
            workflow_logger.error(f"  ❌ Success criteria check failed: {e}")
            return False

    async def _analyst_monitor_effectiveness(self, monitoring_task: Dict[str, Any], is_baseline: bool = False) -> Dict[str, Any]:
        """[Assess] Analyst Agent - monitor effectiveness
        
        Simplified flow:
        1. Baseline data: based on execute_workflow analysis_result + viewpoint_extremism + engagement data
        2. Current data: re-analyze the same metrics
        3. Effectiveness brief: compare analysis, strategist decides if secondary intervention is needed
        """
        try:
            target_post_id = monitoring_task.get("target_post_id")
            action_id = monitoring_task.get("action_id")

            # Use database manager, no need to check connection

            if is_baseline:
                workflow_logger.info("  🔍 Analyst monitoring - establish baseline data")
            else:
                workflow_logger.info("  🔍 Analyst monitoring - current state analysis")
                workflow_logger.info(f"     📌 Target post ID: {target_post_id}")

            # ===== Step 1: Get baseline data =====
            if is_baseline:
                # Baseline data: use actual analysis results at workflow start
                baseline_data = monitoring_task.get("baseline_data", {})
                if not baseline_data:
                    # If no baseline data, fetch from database (backward compatible)
                    baseline_data = await self._get_baseline_from_workflow_result(target_post_id, action_id)
            else:
                # Current data: get stored baseline data from monitoring task
                baseline_data = monitoring_task.get("baseline_data", {})
            
            # ===== Step 2: Get current data =====
            # Re-analyze the same metrics: analysis_result + viewpoint_extremism + engagement data
            current_data = await self._get_current_analysis_data(target_post_id, action_id)
            
            # ===== Step 3: Generate effectiveness brief =====
            effectiveness_report = await self._generate_effectiveness_report(
                baseline_data, current_data, target_post_id, action_id
            )
            
            # ===== Step 4: Update argument scores based on effectiveness evaluation (reward-driven knowledge refinement) =====
            # Sync update as soon as an effectiveness report is available (including baseline round).
            await self._update_argument_scores_based_on_effectiveness(
                effectiveness_report, monitoring_task
            )

            return effectiveness_report

        except Exception as e:
            workflow_logger.info(f"  ❌ Analyst monitoring failed: {e}")
            return await self._generate_fallback_report(monitoring_task)


    async def _update_argument_scores_based_on_effectiveness(self, 
                                                            effectiveness_report: Dict[str, Any],
                                                            monitoring_task: Dict[str, Any]) -> None:
        """Update argument scores based on actual effectiveness evaluation (reward-driven knowledge refinement)
        
        This is the core step of reward-driven knowledge refinement:
        1. Retrieve argument information used from monitoring task
        2. Obtain actual effectiveness score from effectiveness report
        3. Call leader Agent's reward-driven knowledge refinement method to update argument scores
        """
        try:
            workflow_logger.info(f"\n🎓 Step 6: Reward-Driven Knowledge Refinement - Update argument scores based on actual effectiveness")
            
            # Get effectiveness score
            effectiveness_assessment = effectiveness_report.get('effectiveness_assessment', {})
            effectiveness_score = effectiveness_assessment.get('overall_score', 0.0)
            change_metrics = effectiveness_report.get('change_metrics', {})
            extremism_change = float(change_metrics.get('extremism_change', 0.0) or 0.0)  # baseline - current
            sentiment_change = float(change_metrics.get('sentiment_change', 0.0) or 0.0)  # current - baseline

            # Reward function:
            # R(s_t, a_t) = -λ1 * Δv_t + λ2 * Δe_t
            # where:
            #   Δv_t = current_extremism - baseline_extremism = -extremism_change
            #   Δe_t = current_sentiment - baseline_sentiment = sentiment_change
            lambda_1 = 1.0
            lambda_2 = 1.0
            delta_vt = -extremism_change
            delta_et = sentiment_change
            reward_score = (-lambda_1 * delta_vt) + (lambda_2 * delta_et)
            
            workflow_logger.info(f"   📊 Actual effectiveness score: {effectiveness_score:.4f}/1.0")
            workflow_logger.info(
                f"   🎯 Reward score R = -{lambda_1:.1f}*Δv_t + {lambda_2:.1f}*Δe_t = {reward_score:.4f} "
                f"(Δv_t={delta_vt:.4f}, Δe_t={delta_et:.4f})"
            )
            
            # Get leader-generated content information from monitoring task
            leader_content = monitoring_task.get("leader_content", {})
            
            # Check if leader_content contains argument information
            if not leader_content or "relevant_arguments" not in leader_content:
                workflow_logger.warning(f"   ⚠️  Argument information not found in monitoring task, skipping argument score update")
                return
            
            relevant_arguments = leader_content.get("relevant_arguments", [])
            best_candidate = leader_content.get("best_candidate", {})
            
            if not relevant_arguments:
                workflow_logger.warning(f"   ⚠️  No relevant arguments found, skipping argument score update")
                return
            
            workflow_logger.info(f"   📚 Found {len(relevant_arguments)} arguments to update")
            
            # Call leader Agent's reward-driven knowledge refinement method
            if hasattr(self, 'leader') and hasattr(self.leader, '_reward_driven_knowledge_refinement'):
                await self.leader._reward_driven_knowledge_refinement(
                    best_candidate,
                    relevant_arguments,
                    effectiveness_score,
                    reward_score
                )
                workflow_logger.info(f"   ✅ Argument score update completed")
            else:
                workflow_logger.warning(f"   ⚠️  Leader Agent does not support argument score update")
                
        except Exception as e:
            workflow_logger.error(f"   ❌ Argument score update failed: {e}")
            import traceback
            workflow_logger.error(traceback.format_exc())


    async def _get_baseline_from_workflow_result(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get baseline data from execute_workflow result"""
        try:
            # Fetch baseline data from database (pre-intervention state)
            # Use global database manager, cursor no longer needed
            
            # Get baseline post data
            result = fetch_one("""
                SELECT num_likes, num_comments, num_shares, created_at
                FROM posts 
                WHERE post_id = ?
            """, (target_post_id,))
            post_row = result
            
            if not post_row:
                workflow_logger.info(f"  ⚠️ Post not found {target_post_id}")
                # Log total posts in database for debugging
                try:
                    total_posts = fetch_one("SELECT COUNT(*) as count FROM posts")
                    recent_posts = fetch_all("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 5")
                    workflow_logger.info(f"  📊 Total posts in database: {total_posts['count'] if total_posts else 0}")
                    if recent_posts:
                        workflow_logger.info(f"  📋 Most recent 5 post IDs: {[p['post_id'] for p in recent_posts]}")
                except Exception as e:
                    workflow_logger.warning(f"  ⚠️ Unable to query post stats: {e}")
                return {}
            
            likes = post_row['num_likes']
            comments = post_row['num_comments'] 
            shares = post_row['num_shares']
            created_at = post_row['created_at']
            
            # Get baseline comment data
            result = fetch_one("""
                SELECT content, num_likes, created_at
                FROM comments 
                WHERE post_id = ? 
                ORDER BY created_at ASC
                LIMIT 10
            """, (target_post_id,))
            comment_rows = fetch_all("""
                SELECT content, num_likes, created_at
                FROM comments 
                WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (target_post_id,))
            
            # Get full post content for real analysis
            post_result = fetch_one("""
                SELECT content
                FROM posts 
                WHERE post_id = ?
            """, (target_post_id,))
            
            if not post_result:
                workflow_logger.info(f"  ⚠️ Post content not found {target_post_id}")
                return {}
            
            # Build full analysis content (post content)
            content_text = post_result['content'] or ""
            
            # Add comment content
            if comment_rows:
                comment_texts = [row['content'] for row in comment_rows if row['content']]
                if comment_texts:
                    content_text += f"\n\nComments:\n" + "\n".join(comment_texts[:10])  # Only take first 10 comments
            
            # Use analyst analysis to get baseline sentiment data
            analysis_result = await self.analyst.analyze_content(content_text, target_post_id)
            
            if not analysis_result.get('success'):
                workflow_logger.info(f"  ⚠️ Analyst analysis failed: {analysis_result.get('error', 'unknown error')}")
                return {}
            
            baseline_analysis = analysis_result.get('analysis', {})
            baseline_sentiment = baseline_analysis.get('sentiment_score', 0.5)
            sentiment_distribution = baseline_analysis.get('sentiment_distribution', {"positive": 0.3, "negative": 0.4, "neutral": 0.3})
            
            # Use actual method to compute baseline viewpoint extremism
            baseline_extremism = await self._calculate_overall_viewpoint_extremism(content_text, target_post_id)
            
            baseline_data = {
                "analysis_result": {
                    "core_viewpoint": baseline_analysis.get('core_viewpoint', 'baseline viewpoint analysis'),
                    "sentiment_distribution": sentiment_distribution
                },
                "viewpoint_extremism": baseline_extremism,
                "sentiment_score": baseline_sentiment,
                "engagement_data": {
                    "likes": likes,
                    "comments": comments,
                    "shares": shares
                },
                "timestamp": created_at or datetime.now()
            }
            
            workflow_logger.info(f"  📊 Baseline data retrieved - extremism: {baseline_extremism:.2f}, sentiment: {baseline_sentiment:.2f}")
            return baseline_data
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Baseline data fetch failed: {e}")
            return {}

    async def _get_post_engagement_data(self, post_id: str) -> Dict[str, int]:
        """Get post engagement data (likes, comments, shares)"""
        try:
            if not post_id:
                return {"likes": 0, "comments": 0, "shares": 0}
            
            # Query engagement data from database
            result = fetch_one("""
                SELECT num_likes, num_comments, num_shares
                FROM posts 
                WHERE post_id = ?
            """, (post_id,))
            
            if result:
                return {
                    "likes": result['num_likes'] or 0,
                    "comments": result['num_comments'] or 0,
                    "shares": result['num_shares'] or 0
                }
            else:
                # If post does not exist, return default values
                return {"likes": 0, "comments": 0, "shares": 0}
                
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Failed to get post engagement data: {e}")
            return {"likes": 0, "comments": 0, "shares": 0}

    async def _get_current_analysis_data(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get current analysis data - re-analyze the same metrics"""
        try:
            # Fetch current data from database (post-intervention state)
            # Use global database manager, cursor no longer needed
            
            # Get current post data
            result = fetch_one("""
                SELECT num_likes, num_comments, num_shares, created_at
                FROM posts 
                WHERE post_id = ?
            """, (target_post_id,))
            post_row = result
            
            if not post_row:
                workflow_logger.info(f"  ⚠️ Post not found {target_post_id}")
                # Log total posts in database for debugging
                try:
                    total_posts = fetch_one("SELECT COUNT(*) as count FROM posts")
                    recent_posts = fetch_all("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 5")
                    workflow_logger.info(f"  📊 Total posts in database: {total_posts['count'] if total_posts else 0}")
                    if recent_posts:
                        workflow_logger.info(f"  📋 Most recent 5 post IDs: {[p['post_id'] for p in recent_posts]}")
                except Exception as e:
                    workflow_logger.warning(f"  ⚠️ Unable to query post stats: {e}")
                return {}
            
            likes = post_row['num_likes']
            comments = post_row['num_comments'] 
            shares = post_row['num_shares']
            created_at = post_row['created_at']
            
            # Get current data for all comments (including post-intervention comments)
            result = fetch_one("""
                SELECT content, num_likes, created_at, author_id
                FROM comments 
                WHERE post_id = ? 
                ORDER BY created_at DESC
                LIMIT 20
            """, (target_post_id,))
            comment_rows = fetch_all("""
                SELECT content, num_likes, created_at
                FROM comments 
                WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (target_post_id,))
            
            # Get full post content for real analysis
            post_result = fetch_one("""
                SELECT content
                FROM posts 
                WHERE post_id = ?
            """, (target_post_id,))
            
            if not post_result:
                workflow_logger.info(f"  ⚠️ Post content not found {target_post_id}")
                return {}
            
            # Build full analysis content (post content)
            content_text = post_result['content'] or ""
            
            # Add recent comment content
            if comment_rows:
                comment_texts = [row['content'] for row in comment_rows if row['content']]
                if comment_texts:
                    content_text += f"\n\nRecent Comments:\n" + "\n".join(comment_texts[:5])  # Only take first 5 comments
            
            # Use analyst analysis to get current sentiment data
            analysis_result = await self.analyst.analyze_content(content_text, target_post_id)
            
            if not analysis_result.get('success'):
                workflow_logger.info(f"  ⚠️ Analyst analysis failed: {analysis_result.get('error', 'unknown error')}")
                return {}
            
            current_analysis = analysis_result.get('analysis', {})
            current_sentiment = current_analysis.get('sentiment_score', 0.5)
            sentiment_distribution = current_analysis.get('sentiment_distribution', {"positive": 0.4, "negative": 0.3, "neutral": 0.3})
            
            # Use actual method to compute current viewpoint extremism
            current_extremism = await self._calculate_overall_viewpoint_extremism(content_text, target_post_id)
            
            current_data = {
                "analysis_result": {
                    "core_viewpoint": current_analysis.get('core_viewpoint', 'current viewpoint analysis'),
                    "sentiment_distribution": sentiment_distribution
                },
                "viewpoint_extremism": current_extremism,
                "sentiment_score": current_sentiment,
                "engagement_data": {
                    "likes": likes,
                    "comments": comments,
                    "shares": shares
                },
                "timestamp": datetime.now()
            }
            
            workflow_logger.info(f"  📊 Current data analysis completed - extremism: {current_extremism:.2f}, sentiment: {current_sentiment:.2f}")
            return current_data
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Current data analysis failed: {e}")
            return {}

    async def _generate_effectiveness_report(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any], 
                                           target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Generate effectiveness brief - comparative analysis"""
        try:
            # Calculate key metric changes - fix data retrieval logic
            baseline_extremism_raw = baseline_data.get("viewpoint_extremism", 5.0)  # Default medium extremism
            current_extremism_raw = current_data.get("viewpoint_extremism", 5.0)
            
            # If extremism not in data, try recalculating
            if baseline_extremism_raw == 5.0 and target_post_id:
                baseline_extremism_raw = await self._calculate_extremism_from_database(target_post_id)
            if current_extremism_raw == 5.0 and target_post_id:
                current_extremism_raw = await self._calculate_extremism_from_database(target_post_id)

            baseline_extremism = self._normalize_extremism_score(baseline_extremism_raw)
            current_extremism = self._normalize_extremism_score(current_extremism_raw)
            
            extremism_change = baseline_extremism - current_extremism  # Lower extremism is better
            
            baseline_sentiment = baseline_data.get("sentiment_score", 0.5)
            current_sentiment = current_data.get("sentiment_score", 0.5)
            sentiment_change = current_sentiment - baseline_sentiment  # Improved sentiment is better
            
            # Calculate engagement data changes
            baseline_engagement = baseline_data.get("engagement_data", {})
            current_engagement = current_data.get("engagement_data", {})
            
            likes_change = current_engagement.get("likes", 0) - baseline_engagement.get("likes", 0)
            comments_change = current_engagement.get("comments", 0) - baseline_engagement.get("comments", 0)
            shares_change = current_engagement.get("shares", 0) - baseline_engagement.get("shares", 0)
            
            # Determine if secondary intervention is needed - use unified thresholds
            EXTREMISM_THRESHOLD = self.THRESHOLDS["secondary_intervention"]["extremism_threshold"]
            SENTIMENT_THRESHOLD = self.THRESHOLDS["secondary_intervention"]["sentiment_threshold"]
            EXTREMISM_THRESHOLD_NORMALIZED = self._normalize_extremism_threshold(EXTREMISM_THRESHOLD)
            
            # Intervention needed if extremism is still high or sentiment is still low
            needs_intervention = (
                (current_extremism > EXTREMISM_THRESHOLD_NORMALIZED)
                or (current_sentiment < SENTIMENT_THRESHOLD)
                or (extremism_change < 0.05 and sentiment_change < 0.1)
            )
            
            # Calculate effectiveness score
            effectiveness_score = self._calculate_simple_effectiveness_score(extremism_change, sentiment_change)
            
            # Calculate change percentages
            extremism_change_percent = (extremism_change / baseline_extremism * 100) if baseline_extremism > 0 else 0
            sentiment_change_percent = (sentiment_change / baseline_sentiment * 100) if baseline_sentiment > 0 else 0
            
            effectiveness_report = {
                "report_id": f"effectiveness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now(),
                "target_post_id": target_post_id,
                "action_id": action_id,
                
                # Baseline data
                "baseline_metrics": {
                    "extremism_score": baseline_extremism,
                    "sentiment_score": baseline_sentiment,
                    "extremism_max": 1.0,   # Extremism max
                    "sentiment_max": 1.0,   # Sentiment max
                    "extremism_score_raw": float(baseline_extremism_raw),
                    "extremism_level": self._convert_extremism_to_level(baseline_extremism),
                    "sentiment_level": self._convert_sentiment_to_level(baseline_sentiment)
                },
                
                # Current data
                "current_metrics": {
                    "extremism_score": current_extremism,
                    "sentiment_score": current_sentiment,
                    "extremism_score_raw": float(current_extremism_raw),
                    "extremism_level": self._convert_extremism_to_level(current_extremism),
                    "sentiment_level": self._convert_sentiment_to_level(current_sentiment)
                },
                
                # Change metrics
                "change_metrics": {
                    "extremism_change": extremism_change,
                    "sentiment_change": sentiment_change,
                    "extremism_change_percent": extremism_change_percent,
                    "sentiment_change_percent": sentiment_change_percent,
                    "improvement_direction": {
                        "extremism": "improved" if extremism_change > 0 else "worsened" if extremism_change < 0 else "unchanged",
                        "sentiment": "improved" if sentiment_change > 0 else "worsened" if sentiment_change < 0 else "unchanged"
                    }
                },
                
                # Effectiveness assessment
                "effectiveness_assessment": {
                    "overall_score": effectiveness_score,
                    "score_max": 1.0,  # Effectiveness score max
                    "score_level": self._convert_effectiveness_to_level(effectiveness_score),
                    "needs_intervention": needs_intervention,
                    "intervention_reasons": self._get_intervention_reasons(
                        current_extremism,
                        current_sentiment,
                        extremism_change,
                        sentiment_change,
                        EXTREMISM_THRESHOLD_NORMALIZED
                    )
                },
                
                # Engagement changes
                "engagement_changes": {
                    "likes_change": likes_change,
                    "comments_change": comments_change,
                    "shares_change": shares_change
                },
                
                # Raw data (for debugging)
                "raw_data": {
                    "baseline_data": baseline_data,
                    "current_data": current_data
                }
            }
            
            workflow_logger.info("  📊 Effectiveness brief generated")
            workflow_logger.info(f"     Extremism: {baseline_extremism:.2f} -> {current_extremism:.2f} (change: {extremism_change:+.2f}, {extremism_change_percent:+.1f}%)")
            workflow_logger.info(f"     Sentiment: {baseline_sentiment:.2f} -> {current_sentiment:.2f} (change: {sentiment_change:+.2f}, {sentiment_change_percent:+.1f}%)")
            workflow_logger.info(f"     Effectiveness score: {effectiveness_score:.2f}/1.0 ({self._convert_effectiveness_to_level(effectiveness_score)})")
            workflow_logger.info(f"     Needs intervention: {'yes' if needs_intervention else 'no'}")
            
            return effectiveness_report
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Effectiveness brief generation failed: {e}")
            return {"needs_intervention": False}

    def _calculate_simple_effectiveness_score(self, extremism_change: float, sentiment_change: float) -> float:
        """Calculate simplified effectiveness score - revised"""
        try:
            # Extremism reduction is the primary metric (higher weight)
            if extremism_change > 0:
                # Extremism reduction: larger change is better
                # Extremism range 0-1, use 0.5 reduction as full score baseline
                extremism_score = min(1.0, extremism_change / 0.5)
            else:
                # Extremism increase: negative score, but not too harsh
                extremism_score = max(0.0, 0.5 + extremism_change / 1.0)  # Deduct up to 0.5

            # Sentiment improvement is secondary
            if sentiment_change > 0:
                # Sentiment improvement: larger change is better
                # Sentiment range 0-1, max change is 1, use 0.5 as full score baseline
                sentiment_score = min(1.0, sentiment_change / 0.5)  # 0.5 as full score baseline
            else:
                # Sentiment worsening: negative score, but not too harsh
                sentiment_score = max(0.0, 0.5 + sentiment_change / 0.5)  # Deduct up to 0.5
            
            # Weighted calculation: 70% extremism reduction, 30% sentiment improvement
            final_score = (extremism_score * 0.7) + (sentiment_score * 0.3)
            
            # Ensure score is within 0-1
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Effectiveness score calculation failed: {e}")
            return 0.5  # Default medium score

    def _convert_extremism_to_level(self, score: float) -> str:
        """Convert extremism score to level description"""
        if score >= 0.8:
            return "Critical danger"
        elif score >= 0.6:
            return "Highly extreme"
        elif score >= 0.4:
            return "Moderately extreme"
        elif score >= 0.2:
            return "Mildly extreme"
        else:
            return "Normal"

    def _convert_sentiment_to_level(self, score: float) -> str:
        """Convert sentiment score to level description"""
        if score >= 0.8:
            return "Very positive"
        elif score >= 0.6:
            return "Positive"
        elif score >= 0.4:
            return "Neutral"
        elif score >= 0.2:
            return "Negative"
        else:
            return "Very negative"

    def _convert_effectiveness_to_level(self, score: float) -> str:
        """Convert effectiveness score to level description"""
        if score >= 0.8:
            return "Very effective"
        elif score >= 0.6:
            return "Effective"
        elif score >= 0.4:
            return "Fair"
        elif score >= 0.2:
            return "Poor effectiveness"
        else:
            return "Ineffective"

    def _normalize_extremism_score(self, score: float) -> float:
        """Normalize extremism score to 0-1 scale."""
        try:
            value = float(score)
        except (TypeError, ValueError):
            value = 0.5
        if value > 1.0:
            value = value / 10.0
        return max(0.0, min(1.0, value))

    def _normalize_extremism_threshold(self, threshold: float) -> float:
        """Normalize extremism threshold to 0-1 scale."""
        return self._normalize_extremism_score(threshold)

    def _format_initial_intervention_trigger_reasons(
        self,
        viewpoint_extremism_raw: float,
        final_sentiment_score: float,
        extremism_threshold_raw: float,
        sentiment_threshold: float
    ) -> tuple[List[str], float, float]:
        """Format Phase 1 trigger reasons using normalized 0-1 extremism scale."""
        current_extremism_norm = self._normalize_extremism_score(viewpoint_extremism_raw)
        threshold_norm = self._normalize_extremism_threshold(extremism_threshold_raw)

        reasons: List[str] = []
        if current_extremism_norm >= threshold_norm:
            reasons.append(
                f"Viewpoint extremism too high ({current_extremism_norm:.2f}/1.0 >= {threshold_norm:.2f})"
            )
        if final_sentiment_score <= sentiment_threshold:
            reasons.append(
                f"Sentiment too low ({final_sentiment_score:.2f}/1.0 <= {sentiment_threshold})"
            )
        return reasons, current_extremism_norm, threshold_norm

    def _get_intervention_reasons(self, current_extremism: float, current_sentiment: float, 
                                extremism_change: float, sentiment_change: float,
                                extremism_threshold: float = 0.6) -> List[str]:
        """Get intervention reason list"""
        reasons = []
        
        if current_extremism > extremism_threshold:
            reasons.append(f"Current extremism too high ({current_extremism:.2f}/1.0)")
        if current_sentiment < 0.4:
            reasons.append(f"Current sentiment too low ({current_sentiment:.2f}/1.0)")
        if extremism_change < 0.05:
            reasons.append(f"Insufficient extremism improvement ({extremism_change:+.2f})")
        if sentiment_change < 0.1:
            reasons.append(f"Insufficient sentiment improvement ({sentiment_change:+.2f})")
            
        return reasons if reasons else ["No intervention needed"]

    async def _execute_secondary_intervention_decision(self, effectiveness_report: Dict[str, Any], 
                                                     target_post_id: str, action_id: str) -> None:
        """Execute secondary intervention decision"""
        try:
            # Get full original post information
            original_post_data = await self._get_original_post_data(target_post_id)
            
            # Call strategist to create a new intervention strategy
            secondary_alert = {
                "urgency_level": 2,
                "post_id": target_post_id,
                "content_id": target_post_id,
                "analysis": effectiveness_report.get("current_data", {}),
                "intervention_reason": "Effectiveness below expectations, secondary intervention needed",
                # Add original post information
                "trigger_content": original_post_data.get("trigger_content", {}),
                "alert_data": original_post_data.get("alert_data", {}),
                "core_viewpoint": original_post_data.get("core_viewpoint", ""),
                "post_theme": original_post_data.get("post_theme", ""),
                "threat_assessment": original_post_data.get("threat_assessment", "")
            }
            
            secondary_strategy_result = await self.strategist.create_strategy(secondary_alert)

            # Check whether secondary strategy result is None or invalid
            if secondary_strategy_result is None:
                workflow_logger.info("  ⚠️ Secondary intervention strategy creation returned None")
                return

            if secondary_strategy_result.get("success"):
                workflow_logger.info("  ✅ Secondary intervention strategy created")
                # New intervention strategy can be executed here
            else:
                workflow_logger.info(f"  ⚠️ Secondary intervention strategy creation failed: {secondary_strategy_result.get('error', 'unknown error')}")
                
        except Exception as e:
            workflow_logger.info(f"  ❌ Secondary intervention decision execution failed: {e}")

    async def _get_original_post_data(self, target_post_id: str) -> Dict[str, Any]:
        """Get full original post information"""
        try:
            # Use database manager, no need to check connection
            
            # Use global database manager, cursor no longer needed
            
            # Get basic post info
            result = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts WHERE post_id = ?
            """, (target_post_id,))
            
            if not result:
                workflow_logger.info(f"  ⚠️ Post not found {target_post_id}")
                return {}
            
            post_data = {
                "post_id": result.get("post_id"),
                "content": result.get("content"),
                "author_id": result.get("author_id"),
                "created_at": result.get("created_at"),
                "num_likes": result.get("num_likes"),
                "num_comments": result.get("num_comments"),
                "num_shares": result.get("num_shares")
            }
            
            # Note: posts table has no analysis_data column, skip this query
            # Analysis data should come from other sources, such as analyst results
            
            # Extract core data from analysis
            analysis_result = post_data.get("analysis_result", {})
            core_viewpoint = analysis_result.get("core_viewpoint", post_data.get("content", ""))
            post_theme = analysis_result.get("post_theme", "General Discussion")
            
            # Extract threat assessment from malicious_analysis
            malicious_analysis = post_data.get("malicious_analysis", {})
            threat_assessment = malicious_analysis.get("threat_assessment", "Further analysis needed")
            
            # Build full trigger_content structure
            trigger_content = {
                "core_viewpoint": core_viewpoint,
                "post_theme": post_theme,
                "viewpoint_analysis": {
                    "original_post_viewpoint": post_data.get("content", ""),
                    "final_weighted_viewpoint": core_viewpoint
                },
                "malicious_analysis": {
                    "extremism_level": post_data.get("extremism_level", 0),
                    "attack_patterns": post_data.get("attack_patterns", []),
                    "threat_assessment": threat_assessment
                },
                "engagement_metrics": {
                    "intensity_level": "MODERATE",
                    "amplification_risk": "MODERATE",
                    "viral_potential": "MODERATE"
                },
                "sentiment_distribution": {
                    "overall_sentiment_score": post_data.get("sentiment_score", 0.5),
                    "emotional_triggers": post_data.get("emotional_triggers", []),
                    "polarization_risk": "MODERATE"
                }
            }
            
            return {
                "trigger_content": trigger_content,
                "alert_data": post_data,
                "core_viewpoint": core_viewpoint,
                "post_theme": post_theme,
                "threat_assessment": threat_assessment
            }
            
        except Exception as e:
            workflow_logger.info(f"  ⚠️ Failed to get original post data: {e}")
            return {}

    async def _strategist_evaluate_and_adjust(self, feedback_report: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """[Iterate] Strategist Agent - dynamic adjustment

        Input: Receives analyst effectiveness report.
        Flow: Evaluate whether current strategy is working based on latest report.
        If unexpected negative commentary appears, immediately create a supplementary action plan
        (e.g., activate a new batch of amplifier Agents to clarify, or have the leader post a follow-up).
        Output: Dynamic adjustment instructions, or a "keep observing" decision.
        """

        workflow_logger.info("    📊 Strategist agent received analyst effectiveness report")
        workflow_logger.info("    🎯 Evaluate whether the current strategy is effective")

        # Send report to strategist with retry mechanism
        strategic_decision = await self._send_report_to_strategist(feedback_report, task)

        # Record strategist evaluation results
        if strategic_decision.get("success"):
            workflow_logger.info("    ✅ Strategist evaluation complete")
            workflow_logger.info(f"       Decision: {strategic_decision.get('decision_type', 'unknown')}")
            workflow_logger.info(f"       Rationale: {strategic_decision.get('strategist_rationale', 'N/A')}")

            # If there is negative commentary, create a supplementary action plan
            if strategic_decision.get("needs_adjustment"):
                workflow_logger.info("    🚨 Unexpected negative commentary detected, creating supplementary action plan")
                supplementary_actions = strategic_decision.get("supplementary_actions", [])
                for i, action in enumerate(supplementary_actions, 1):
                    workflow_logger.info(f"       Action {i}: {action.get('type', 'unknown')} - {action.get('description', 'N/A')}")
        else:
            workflow_logger.info("    ⚠️ Strategist evaluation failed, using fallback decision")

        return strategic_decision

    async def _update_system_memory(self, feedback_report: Dict[str, Any], strategic_decision: Dict[str, Any], task: Dict[str, Any]):
        """[Learn] System - update memory

        After the action ends, the strategist agent triggers a summary process
        to archive the full action-result log to the cognitive memory core for future learning.
        """
        try:
            workflow_logger.info("    📚 Updating system memory...")

            # Build action-result log
            action_result_log = {
                "timestamp": datetime.now(),
                "cycle_data": {
                    "feedback_report": feedback_report,
                    "strategic_decision": strategic_decision,
                    "task_info": {
                        "task_id": task.get("task_id"),
                        "target_post_id": task.get("target_post_id"),
                        "action_id": task.get("action_id")
                    }
                },
                "learning_points": {
                    "effectiveness_score": feedback_report.get("effectiveness_score", 0),
                    "strategy_success": strategic_decision.get("success", False),
                    "adjustment_needed": strategic_decision.get("needs_adjustment", False),
                    "decision_type": strategic_decision.get("decision_type", "unknown")
                }
            }

            # Add to cognitive memory core
            if not hasattr(self, 'cognitive_memory_core'):
                self.cognitive_memory_core = []

            self.cognitive_memory_core.append(action_result_log)

            # Limit memory size, keep latest 100 records
            if len(self.cognitive_memory_core) > 100:
                self.cognitive_memory_core = self.cognitive_memory_core[-100:]

            workflow_logger.info("    ✅ Action-result log archived to cognitive memory core")
            workflow_logger.info(f"       Memory entries: {len(self.cognitive_memory_core)}")

        except Exception as e:
            workflow_logger.info(f"    ❌ System memory update failed: {e}")

    async def _archive_complete_action_cycle(self, task: Dict[str, Any], monitoring_task_id: str):
        """[Learn] System - final complete action cycle archive"""
        try:
            workflow_logger.info("    📚 Archiving complete action cycle to cognitive memory core")

            # Build complete action cycle record
            complete_cycle = {
                "cycle_id": monitoring_task_id,
                "timestamp": datetime.now(),
                "action_id": task.get("action_id"),
                "target_post_id": task.get("target_post_id"),
                "total_monitoring_cycles": len(task.get("feedback_reports", [])),
                "total_adjustments": len(task.get("adjustments_made", [])),
                "effectiveness_progression": [
                    report.get("effectiveness_score", 0)
                    for report in task.get("feedback_reports", [])
                ],
                "strategic_decisions": [
                    adjustment.get("decision_type", "unknown")
                    for adjustment in task.get("adjustments_made", [])
                ],
                "final_effectiveness": task.get("feedback_reports", [{}])[-1].get("effectiveness_score", 0) if task.get("feedback_reports") else 0
            }

            # Save to long-term memory
            if not hasattr(self, 'long_term_memory'):
                self.long_term_memory = []

            self.long_term_memory.append(complete_cycle)

            workflow_logger.info("    ✅ Complete action cycle archived")
            workflow_logger.info(f"       Final effectiveness score: {complete_cycle['final_effectiveness']:.1f}/10")

        except Exception as e:
            workflow_logger.info(f"    ❌ Complete cycle archive failed: {e}")

    async def _generate_analyst_summary(self, baseline_data: Dict, current_data: Dict,
                                      analyst_comparison: Dict, is_baseline: bool) -> str:
        """Generate analyst professional summary"""
        try:
            if is_baseline:
                return f"Baseline analysis completed - extremism: {baseline_data.get('analyst_analysis', {}).get('extremism_score', 0):.1f}, sentiment: {baseline_data.get('analyst_analysis', {}).get('sentiment_score', 0):.1f}"

            effectiveness = analyst_comparison.get("intervention_effectiveness_score", 0)
            changes = analyst_comparison.get("changes", {})
            extremism_change = changes.get("extremism_change", 0)
            sentiment_change = changes.get("sentiment_change", 0)

            return f"Intervention effectiveness evaluation - overall score: {effectiveness:.1f}/10, extremism change: {extremism_change:+.2f}, sentiment change: {sentiment_change:+.2f}"

        except Exception as e:
            return f"Analyst summary generation failed: {str(e)}"

    async def _generate_feedback_report(self, monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate effectiveness feedback brief from real data - includes analyst analysis"""

        try:
            target_post_id = monitoring_task.get("target_post_id")
            action_id = monitoring_task.get("action_id")

            # Use database manager, no need to check connection

            workflow_logger.info(f"  🔍 Phase 3 analyst analysis - post ID: {target_post_id}")

            # Get baseline data (pre-opinion_balance intervention) - include analyst baseline analysis
            baseline_data = await self._get_baseline_data_with_analyst(target_post_id, action_id)

            # Get current data (including all related posts and comments) - use analyst for current state analysis
            current_data = await self._get_current_data_with_analyst(target_post_id, action_id)

            # Use analyst for professional analysis - core viewpoint, extremism, sentiment
            analyst_comparison = await self._perform_analyst_comparison_analysis(
                baseline_data, current_data, target_post_id
            )

            # Analyze comment sentiment and maliciousness
            sentiment_analysis = await self._analyze_comments_sentiment(target_post_id, action_id)

            # Calculate change metrics
            engagement_growth = self._calculate_engagement_growth(baseline_data, current_data)
            sentiment_change = self._determine_sentiment_change(baseline_data, current_data, sentiment_analysis)

            # Calculate effectiveness score
            effectiveness_score = self._calculate_real_effectiveness_score(
                baseline_data, current_data, sentiment_analysis, engagement_growth
            )

            return {
                "report_id": f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now(),
                "monitoring_task_id": monitoring_task["task_id"],
                "target_post_id": target_post_id,
                "action_id": action_id,
                "baseline_data": baseline_data,
                "current_data": current_data,
                "analyst_comparison": analyst_comparison,  # New: analyst comparison result
                "sentiment_analysis": sentiment_analysis,
                "engagement_growth": round(engagement_growth, 1),
                "sentiment_change": sentiment_change,
                "effectiveness_score": round(effectiveness_score, 1),
                "recommendations": self._generate_recommendations(
                    effectiveness_score,
                    sentiment_change,
                    engagement_growth,
                    sentiment_analysis.get("malicious_comments_count", 0),
                    current_data.get("sentiment_score", 0.5),
                    baseline_data.get("sentiment_score", 0.5)
                ),
                "data_source": "real_database"
            }

        except Exception as e:
            workflow_logger.info(f"  ❌ Failed to generate real data brief: {e}")
            return await self._generate_fallback_report(monitoring_task)

    async def _get_baseline_data(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get baseline data (pre-intervention state)"""
        try:
            # Use global database manager, cursor no longer needed

            # If target post ID exists, get initial state of that post
            if target_post_id:
                result = fetch_one("""
                    SELECT num_likes, num_comments, num_shares, num_flags
                    FROM posts
                    WHERE post_id = ?
                """, (target_post_id,))

                result = fetch_one("""
                    SELECT num_likes, num_comments, num_shares, num_flags 
                    FROM posts WHERE post_id = ?
                """, (target_post_id,))
                if result:
                    return {
                        "likes": result.get("num_likes", 0) or 0,
                        "comments": result.get("num_comments", 0) or 0,
                        "shares": result.get("num_shares", 0) or 0,
                        "flags": result.get("num_flags", 0) or 0,
                        "sentiment_score": 0.5  # Initial neutral state
                    }

            # If no target post, use system average baseline
            result = fetch_one("""
                SELECT AVG(num_likes), AVG(num_comments), AVG(num_shares), AVG(num_flags)
                FROM posts
                WHERE created_at < datetime('now', '-1 hour')
                AND is_news = 1
            """)

            result = fetch_one("SELECT AVG(num_likes), AVG(num_comments), AVG(num_shares), AVG(num_flags) FROM posts")
            if result and result.get('AVG(num_likes)') is not None:
                return {
                    "likes": int(result.get('AVG(num_likes)', 5) or 5),
                    "comments": int(result.get('AVG(num_comments)', 3) or 3),
                    "shares": int(result.get('AVG(num_shares)', 1) or 1),
                    "flags": int(result.get('AVG(num_flags)', 0) or 0),
                    "sentiment_score": 0.5
                }

            # Default baseline
            return {
                "likes": 5,
                "comments": 3,
                "shares": 1,
                "flags": 0,
                "sentiment_score": 0.3
            }

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to get baseline data: {e}")
            return {"likes": 5, "comments": 3, "shares": 1, "flags": 0, "sentiment_score": 0.5}

    async def _get_current_data(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get current data (includes all post-intervention related data)"""
        try:
            # Use global database manager, cursor no longer needed

            # Get all posts related to this action (including leader posts and amplifier responses)
            result = fetch_one("""
                SELECT SUM(num_likes), SUM(num_comments), SUM(num_shares), SUM(num_flags), COUNT(*)
                FROM posts
                WHERE (intervention_id = ? OR post_id = ?)
                AND is_agent_response = 1
            """, (action_id, target_post_id))

            agent_result = fetch_one("SELECT SUM(num_likes), SUM(num_comments), SUM(num_shares), SUM(num_flags), COUNT(*) FROM posts WHERE author_id LIKE 'agent_%' AND created_at >= datetime('now', '-1 hour')")

            # Get current state of target post
            if target_post_id:
                result = fetch_one("""
                    SELECT num_likes, num_comments, num_shares, num_flags
                    FROM posts
                    WHERE post_id = ?
                """, (target_post_id,))

                target_result = fetch_one("SELECT num_likes, num_comments, num_shares, num_flags FROM posts WHERE post_id = ?", (target_post_id,))
            else:
                target_result = None

            # Merge data
            agent_likes = agent_result.get("num_likes", 0) or 0
            agent_comments = agent_result.get("num_comments", 0) or 0
            agent_shares = agent_result.get("num_shares", 0) or 0
            agent_flags = agent_result.get("num_flags", 0) or 0
            agent_posts = agent_result.get("post_count", 0) or 0

            target_likes = target_result.get("num_likes", 0) or 0 if target_result else 0
            target_comments = target_result.get("num_comments", 0) or 0 if target_result else 0
            target_shares = target_result.get("num_shares", 0) or 0 if target_result else 0
            target_flags = target_result.get("num_flags", 0) or 0 if target_result else 0

            # Calculate current sentiment score
            current_sentiment_score = await self._calculate_current_sentiment_score(target_post_id, action_id)
            
            return {
                "likes": target_likes + agent_likes,
                "comments": target_comments + agent_comments,
                "shares": target_shares + agent_shares,
                "flags": target_flags + agent_flags,
                "agent_posts": agent_posts,
                "target_post_engagement": target_likes + target_comments + target_shares,
                "sentiment_score": current_sentiment_score
            }

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to get current data: {e}")
            return {"likes": 10, "comments": 8, "shares": 3, "flags": 0, "agent_posts": 0, "target_post_engagement": 0, "sentiment_score": 0.5}

    async def _analyze_comments_sentiment(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Analyze comment sentiment and maliciousness - using Analyst Agent expertise"""
        try:
            # Use global database manager, cursor no longer needed

            # Get all comments for target post
            all_comments = []
            if target_post_id:
                result = fetch_one("""
                    SELECT c.content, c.author_id, c.created_at, c.num_likes
                    FROM comments c
                    WHERE c.post_id = ?
                    ORDER BY c.created_at DESC
                """, (target_post_id,))

                all_comments.extend(fetch_all("SELECT c.content, c.author_id, c.created_at, c.num_likes FROM comments c JOIN posts p ON c.post_id = p.post_id WHERE p.intervention_id = ?", (action_id,)))

            # Get comments for agent posts related to this action
            if action_id:
                result = fetch_one("""
                    SELECT c.content, c.author_id, c.created_at, c.num_likes
                    FROM comments c
                    JOIN posts p ON c.post_id = p.post_id
                    WHERE p.intervention_id = ?
                    AND p.is_agent_response = 1
                    ORDER BY c.created_at DESC
                """, (action_id,))

                all_comments.extend(fetch_all("SELECT c.content, c.author_id, c.created_at, c.num_likes FROM comments c JOIN posts p ON c.post_id = p.post_id WHERE p.intervention_id = ?", (action_id,)))

            # Get malicious comments
            if target_post_id:
                result = fetch_one("""
                    SELECT mc.content, mc.persona_used, mc.attack_type, mc.intensity_level
                    FROM malicious_comments mc
                    JOIN malicious_attacks ma ON mc.attack_id = ma.id
                    WHERE ma.target_post_id = ?
                    OR ma.attack_timestamp >= datetime('now', '-1 hour')
                """, (target_post_id,))
            else:
                result = fetch_one("""
                    SELECT mc.content, mc.persona_used, mc.attack_type, mc.intensity_level
                    FROM malicious_comments mc
                    JOIN malicious_attacks ma ON mc.attack_id = ma.id
                    WHERE ma.attack_timestamp >= datetime('now', '-1 hour')
                """)

            malicious_comments = fetch_all("SELECT mc.content, mc.persona_used, mc.attack_type, mc.intensity_level FROM malicious_comments mc WHERE mc.post_id = ?", (target_post_id,))

            # Analyze statistics
            total_comments = len(all_comments)
            malicious_count = len(malicious_comments)

            # Use Analyst Agent for professional sentiment analysis
            if total_comments > 0:
                # Build comment content for analysis
                comment_texts = [comment[0] for comment in all_comments[:10]]  # Take first 10 comments
                combined_content = "\n".join(comment_texts)
                
                # Use analyst professional analysis capability
                analyst_result = await self.analyst.analyze_content(
                    combined_content, f"sentiment_analysis_{action_id or target_post_id}"
                )
                
                if analyst_result.get("success") and analyst_result.get("analysis"):
                    analysis_data = analyst_result["analysis"]
                    
                    # Extract sentiment data from analyst result
                    if "sentiment_distribution" in analysis_data:
                        sentiment_dist = analysis_data["sentiment_distribution"]
                        analyst_sentiment_score = self._extract_sentiment_score_from_analyst(sentiment_dist)
                    else:
                        # Use analyst overall sentiment judgment
                        sentiment_str = analysis_data.get("sentiment", "neutral")
                        analyst_sentiment_score = self._convert_sentiment_string_to_score(sentiment_str)
                        
                    # Use analyst professional judgment
                    sentiment_score = analyst_sentiment_score
                    
                    # Calculate distribution based on analyst judgment
                    positive_count, negative_count, neutral_count = await self._calculate_sentiment_distribution(
                        all_comments, analyst_sentiment_score
                    )
                else:
                    # Analyst analysis failed, use fallback method
                    positive_count, negative_count, neutral_count, sentiment_score = await self._fallback_sentiment_analysis(all_comments)
            else:
                positive_count = negative_count = neutral_count = 0
                sentiment_score = 0.5

            # Calculate maliciousness ratio
            malicious_ratio = malicious_count / max(total_comments, 1)

            return {
                "total_comments": total_comments,
                "malicious_comments": malicious_count,
                "malicious_ratio": round(malicious_ratio, 3),
                "positive_comments": positive_count,
                "negative_comments": negative_count,
                "neutral_comments": neutral_count,
                "sentiment_score": round(sentiment_score, 3),
                "sentiment_distribution": {
                    "positive": round(positive_count / max(total_comments, 1), 3),
                    "negative": round(negative_count / max(total_comments, 1), 3),
                    "neutral": round(neutral_count / max(total_comments, 1), 3)
                },
                "analyst_enhanced": analyst_result.get("success", False)
            }

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Comment sentiment analysis failed: {e}")
            return self._get_default_sentiment_analysis()

    async def _calculate_current_sentiment_score(self, target_post_id: str, action_id: str) -> float:
        """Calculate current sentiment score"""
        try:
            sentiment_analysis = await self._analyze_comments_sentiment(target_post_id, action_id)
            return sentiment_analysis.get("sentiment_score", 0.5)
        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to calculate current sentiment score: {e}")
            return 0.5

    def _extract_sentiment_score_from_analyst(self, sentiment_dist: Dict[str, Any]) -> float:
        """Extract sentiment score from analyst sentiment distribution"""
        try:
            overall_sentiment = sentiment_dist.get("overall_sentiment", "neutral")
            return self._convert_sentiment_string_to_score(overall_sentiment)
        except Exception:
            return 0.5

    def _convert_sentiment_string_to_score(self, sentiment_str: str) -> float:
        """Convert sentiment string to numeric score"""
        sentiment_map = {
            "positive": 0.8,
            "very_positive": 0.9,
            "negative": 0.2,
            "very_negative": 0.1,
            "neutral": 0.5,
            "mixed": 0.5
        }
        return sentiment_map.get(sentiment_str.lower(), 0.5)

    async def _calculate_overall_viewpoint_extremism(self, content_text: str, content_id: str) -> float:
        """Calculate overall viewpoint extremism - based on comment analysis, weighted by likes"""
        try:
            # Extract comment content and likes from content_text
            import re

            # Find recent comments pattern - match "Recent Comments:\ncomment content" format
            recent_comment_pattern = r'Recent Comments:\n(.+?)(?=\n\n|$)'
            recent_comments_match = re.search(recent_comment_pattern, content_text, re.DOTALL)
            
            all_comments = []
            
            if recent_comments_match:
                comments_text = recent_comments_match.group(1)
                # Split comments by line, one comment per line
                comment_lines = [line.strip() for line in comments_text.split('\n') if line.strip()]
                
                for comment in comment_lines:
                    if len(comment) > 10:  # Filter out overly short comments
                        all_comments.append({
                            'content': comment,
                            'likes': 0,  # Default likes = 0
                            'type': 'recent'
                        })
            
            # If no comments found, try fetching from database
            if not all_comments:
                return await self._calculate_extremism_from_database(content_id)

            workflow_logger.info(f"    🔍 Analyzing viewpoint extremism for {len(all_comments)} comments...")

            if all_comments:
                extremism_scores = []
                weights = []

                for comment_data in all_comments:
                    if len(comment_data['content']) < 10:
                        continue

                    # Calculate extremism and sentiment
                    extremism_score, sentiment_score = await self._calculate_viewpoint_extremism_and_sentiment(comment_data['content'], log_details=False)
                    extremism_scores.append(extremism_score)

                    # Calculate weights: likes + type weight
                    like_weight = 1.0 + (comment_data['likes'] * 0.1)  # Each like adds 0.1 weight
                    type_weight = 1.0  # Same weight for all comments
                    final_weight = like_weight * type_weight
                    weights.append(final_weight)

                if extremism_scores and weights:
                    # Calculate weighted average
                    weighted_sum = sum(score * weight for score, weight in zip(extremism_scores, weights))
                    total_weight = sum(weights)
                    return weighted_sum / total_weight
                else:
                    workflow_logger.info("    ⚠️  No valid comments found, using default value")
                    return 3.0
            else:
                workflow_logger.info("    ⚠️  No valid comments found, using default value")
                return 3.0

        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to calculate viewpoint extremism: {e}")
            return 0.5  # Default medium value

    async def _calculate_extremism_from_database(self, content_id: str) -> float:
        """Get related comments from database and calculate extremism - aligned with analyst logic"""
        try:
            # Use global database manager, cursor no longer needed

            # Get 4 comments: 2 by popularity, 2 by time (aligned with analyst logic)
            # First get top 2 by likes
            hot_comment_rows = fetch_all("""
                SELECT c.comment_id, c.content, c.num_likes FROM comments c
                WHERE c.post_id = ?
                ORDER BY c.num_likes DESC, c.created_at DESC
                LIMIT 2
            """, (content_id,))

            # Get 2 most recent comments (excluding already selected hot comments)
            hot_comment_ids = [row['comment_id'] for row in hot_comment_rows]
            if hot_comment_ids:
                placeholders = ','.join('?' * len(hot_comment_ids))
                recent_comment_rows = fetch_all(f"""
                    SELECT c.comment_id, c.content, c.num_likes FROM comments c
                    WHERE c.post_id = ? AND c.comment_id NOT IN ({placeholders})
                    ORDER BY c.created_at DESC
                    LIMIT 2
                """, [content_id] + hot_comment_ids)
            else:
                recent_comment_rows = fetch_all("""
                    SELECT c.comment_id, c.content, c.num_likes FROM comments c
                    WHERE c.post_id = ?
                    ORDER BY c.created_at DESC
                    LIMIT 2
                """, (content_id,))

            # Merge comments: popularity first, then recency
            all_comment_rows = hot_comment_rows + recent_comment_rows

            if all_comment_rows:
                extremism_scores = []
                weights = []

                for i, comment_row in enumerate(all_comment_rows):
                    comment_id = comment_row['comment_id']
                    comment_content = comment_row['content']
                    num_likes = comment_row['num_likes']
                    
                    if len(comment_content.strip()) >= 10:
                        extremism_score, sentiment_score = await self._calculate_viewpoint_extremism_and_sentiment(comment_content, log_details=False)
                        extremism_scores.append(extremism_score)

                        # Determine weight by likes: more likes = higher weight
                        like_weight = 1.0 + (num_likes * 0.1)  # Base weight 1.0, each like adds 0.1
                        # Hot comments (top 2) get extra weight
                        position_weight = 1.5 if i < 2 else 1.0
                        final_weight = like_weight * position_weight
                        weights.append(final_weight)

                if extremism_scores and weights:
                    # Calculate weighted average
                    weighted_sum = sum(score * weight for score, weight in zip(extremism_scores, weights))
                    total_weight = sum(weights)
                    return weighted_sum / total_weight

            return 0.5  # Default value

        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to calculate extremism from database: {e}")
            return 0.5

    async def _calculate_viewpoint_extremism_and_sentiment(self, content: str, log_details: bool = False) -> tuple[float, float]:
        """Use LLM to calculate comment viewpoint extremism and sentiment (0-1, 0-1)"""
        try:
            if not content or len(content.strip()) < 5:
                return 0.0, 0.5

            # Build LLM rating prompt - calculate extremism and sentiment
            prompt = f"""Analyze the following comment and provide two ratings:

Comment: "{content}"

1. VIEWPOINT EXTREMISM (0-1 scale):
- 0.0-0.2: Neutral, balanced, or constructive viewpoint
- 0.2-0.4: Mild criticism or disagreement, still reasonable
- 0.4-0.6: Strong opinion with some bias or emotional language
- 0.6-0.8: Highly polarized, aggressive, or divisive viewpoint
- 0.8-1.0: Extremely toxic, hateful, or destructive viewpoint

2. SENTIMENT SCORE (0-1 scale):
- 0.0-0.2: Very negative (hateful, destructive)
- 0.2-0.4: Negative (critical, complaining)
- 0.4-0.6: Neutral (factual, balanced)
- 0.6-0.8: Positive (supportive, constructive)
- 0.8-1.0: Very positive (enthusiastic, celebratory)

Consider these factors for extremism:
1. Use of aggressive or attacking language
2. Absolute statements (always/never/completely)
3. Personal attacks or insults
4. Polarizing or divisive rhetoric
5. Emotional intensity and hostility
6. Conspiracy theories or extremist views

Consider these factors for sentiment:
1. Overall emotional tone (positive/negative/neutral)
2. Language positivity/negativity
3. Constructive vs destructive intent
4. Supportive vs critical stance

Respond with ONLY two numbers separated by a comma: extremism_score,sentiment_score
Examples:
- "I disagree with this approach" → 0.3,0.4
- "This is completely wrong and stupid" → 0.7,0.2
- "Great point, I agree!" → 0.2,0.8
- "You're an idiot and this is garbage" → 0.9,0.1

Your ratings:"""

            try:
                # Use analyst OpenAI client for scoring
                if hasattr(self.analyst, 'client') and self.analyst.client:
                    from multi_model_selector import MultiModelSelector
                    default_model = MultiModelSelector.DEFAULT_POOL[0]
                    if log_details:
                        # Only log details when requested and show full content
                        workflow_logger.info(f"    ℹ️  Using LLM client for viewpoint extremism scoring: {content}")
                    
                    try:
                        response = await asyncio.to_thread(
                            self.analyst.client.chat.completions.create,
                            model=getattr(self.analyst, 'model', default_model),  # Use analyst model
                            messages=[
                                {"role": "system", "content": "You are an expert at analyzing viewpoint extremism. Respond only with a numeric rating."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3,
                            max_tokens=10,
                            timeout=30
                        )

                        rating_text = response.choices[0].message.content.strip()

                        # Parse two ratings: extremism, sentiment
                        import re
                        # Find all numbers (including decimals)
                        numbers = re.findall(r'\d+\.?\d*', rating_text)
                        if len(numbers) >= 2:
                            extremism_rating = float(numbers[0])
                            sentiment_rating = float(numbers[1])
                            
                            # Clamp ranges
                            final_extremism = self._normalize_extremism_score(extremism_rating)  # 0-1
                            final_sentiment = min(max(sentiment_rating, 0.0), 1.0)   # 0-1
                            
                            if log_details:
                                workflow_logger.info(f"    ✅ LLM rating result: extremism={final_extremism:.2f}/1.0, sentiment={final_sentiment:.2f}/1.0 (raw: {rating_text})")
                            return final_extremism, final_sentiment
                        else:
                            workflow_logger.info(f"    ⚠️  LLM returned invalid ratings: {rating_text}")
                            return 0.5, 0.5  # Default medium value
                            
                    except Exception as llm_error:
                        workflow_logger.info(f"    ❌ LLM call failed: {llm_error}")
                        fallback_extremism = self._fallback_extremism_calculation(content)
                        return fallback_extremism, 0.5  # Default sentiment
                else:
                    workflow_logger.info("    ⚠️  LLM client unavailable, using fallback scoring")
                    fallback_extremism = self._fallback_extremism_calculation(content)
                    return fallback_extremism, 0.5  # Default sentiment

            except Exception as e:
                workflow_logger.info(f"    ❌ Viewpoint extremism calculation failed: {e}")
                fallback_extremism = self._fallback_extremism_calculation(content)
                return fallback_extremism, 0.5  # Default sentiment

        except Exception as e:
            logging.error(f"Failed to calculate viewpoint extremism: {e}")
            return 0.0, 0.5

    async def _calculate_weighted_sentiment_from_comments(self, post_id: str) -> float:
        """Calculate weighted sentiment based on individual comments"""
        try:
            # Get top 2 hottest comments and latest 2 comments
            hot_comments = fetch_all("""
                SELECT content, num_likes 
                FROM comments 
                WHERE post_id = ? 
                ORDER BY num_likes DESC
                LIMIT 2
            """, (post_id,))
            
            latest_comments = fetch_all("""
                SELECT content, num_likes 
                FROM comments 
                WHERE post_id = ? 
                ORDER BY created_at DESC
                LIMIT 2
            """, (post_id,))
            
            # Merge comments and deduplicate
            all_comments = []
            seen_comments = set()
            
            for comment in hot_comments + latest_comments:
                content = comment.get('content', '') if isinstance(comment, dict) else comment[0]
                if content not in seen_comments:
                    all_comments.append(comment)
                    seen_comments.add(content)
            
            if not all_comments:
                return 0.5  # Default neutral
            
            total_weighted_sentiment = 0.0
            total_weight = 0.0
            
            # Calculate total weight
            for comment in all_comments:
                # Check return format: dict uses keys, tuple uses index
                if isinstance(comment, dict):
                    likes = comment.get('num_likes', 0) or 0
                else:
                    likes = comment[1] or 0
                weight = likes + 1  # Base weight 1, each like +1
                total_weight += weight
            
            workflow_logger.info(f"    📊 Total weight calculated: {total_weight} (based on {len(all_comments)} comments: {len(hot_comments)} hot + {len(latest_comments)} latest)")
            
            # Calculate weighted sentiment per comment
            for i, comment in enumerate(all_comments):
                # Check return format: dict uses keys, tuple uses index
                if isinstance(comment, dict):
                    content = comment.get('content', '')
                    likes = comment.get('num_likes', 0) or 0
                else:
                    content = comment[0]
                    likes = comment[1] or 0
                
                if len(content.strip()) >= 5:  # Only analyze meaningful comments
                    try:
                        # Calculate sentiment for this comment
                        result = await self._calculate_viewpoint_extremism_and_sentiment(content, log_details=False)
                        # Log full comment content
                        workflow_logger.info(f"    📝 Comment {i+1} content: {content}")
                        workflow_logger.info(f"    🔍 Comment {i+1} LLM result: {result}")
                        
                        if isinstance(result, tuple) and len(result) == 2:
                            extremism_value, sentiment_value = result
                        else:
                            workflow_logger.info(f"    ⚠️ Comment {i+1} returned invalid format: {result}")
                            continue
                        
                        # Calculate weight
                        weight = (likes + 1) / total_weight
                        
                        # Accumulate weighted sentiment
                        weighted_contribution = sentiment_value * weight
                        total_weighted_sentiment += weighted_contribution
                        
                        # Detailed log
                        workflow_logger.info(f"    📊 Comment {i+1}: sentiment={sentiment_value:.2f}, likes={likes}, weight={weight:.3f}, contribution={weighted_contribution:.3f}")
                        
                    except Exception as e:
                        workflow_logger.info(f"    ⚠️ Comment sentiment calculation failed: {e}")
                        continue
            
            # Return weighted average sentiment
            final_sentiment = total_weighted_sentiment if total_weighted_sentiment > 0 else 0.5
            workflow_logger.info(f"    📊 Weighted per-comment sentiment: {final_sentiment:.2f}/1.0 (based on {len(all_comments)} selected comments: {len(hot_comments)} hot + {len(latest_comments)} latest)")
            
            return final_sentiment
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Weighted per-comment sentiment calculation failed: {e}")
            return 0.5

    def _fallback_extremism_calculation(self, content: str) -> float:
        """Fallback rule-based extremism calculation (0-1 scale)"""
        if not content:
            return 0.0

        content_lower = content.lower()
        extremism_score = 0.0

        # Simplified aggression detection
        aggressive_terms = ['stupid', 'idiot', 'garbage', 'trash', 'pathetic', 'disgusting', 'hate', 'disaster']
        aggressive_count = sum(1 for term in aggressive_terms if term in content_lower)
        extremism_score += min(aggressive_count * 1.5, 4.0)

        # Emotional intensity detection
        upper_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        exclamation_count = content.count('!')
        extremism_score += min(upper_ratio * 5 + exclamation_count * 0.5, 3.0)

        # Absolutist expressions
        absolute_terms = ['always', 'never', 'completely', 'totally', 'absolutely']
        absolute_count = sum(1 for term in absolute_terms if term in content_lower)
        extremism_score += min(absolute_count * 0.8, 2.0)

        return self._normalize_extremism_score(min(extremism_score, 10.0))

    async def _calculate_sentiment_distribution(self, all_comments: list, analyst_score: float) -> tuple:
        """Calculate sentiment distribution based on analyst score and extremism"""
        try:
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            # Analyze viewpoint extremism for first 3 comments
            extremism_values = []
            for i, comment in enumerate(all_comments[:3]):  # Only analyze first 3 comments
                content = comment[0]

                # Calculate extremism and sentiment (0-1, 0-1) - async call
                extremism_value, sentiment_value = await self._calculate_viewpoint_extremism_and_sentiment(content, log_details=False)
                extremism_value = self._normalize_extremism_score(extremism_value)
                extremism_values.append(extremism_value)

                # Log full comment content and scores
                workflow_logger.info(f"    📊 Comment {i+1} extremism: {extremism_value:.2f}/1.0")
                workflow_logger.info(f"    💬 Comment content: {content}")
                workflow_logger.info(f"    😊 Sentiment: {sentiment_value:.2f}/1.0")
                
                # Show category based on score
                if extremism_value >= 0.7:
                    category = "High extremism"
                elif extremism_value >= 0.4:
                    category = "Moderate extremism"
                else:
                    category = "Low extremism"
                workflow_logger.info(f"    🏷️  Category: {category}")

                # Classify based on extremism and analyst score
                if extremism_value >= 0.7:  # High extremism
                    negative_count += 1
                elif extremism_value >= 0.4:  # Moderate extremism
                    if analyst_score < 0.5:  # Analyst views as negative
                        negative_count += 1
                    else:
                        neutral_count += 1
                else:  # Low extremism
                    if analyst_score > 0.6:  # Analyst views as positive
                        positive_count += 1
                    elif analyst_score < 0.4:  # Analyst views as negative
                        neutral_count += 1
                    else:
                        positive_count += 1

            # Calculate average extremism as overall viewpoint extremism
            avg_extremism = sum(extremism_values) / len(extremism_values) if extremism_values else 0.0

            workflow_logger.info(f"    📈 Average viewpoint extremism: {avg_extremism:.2f}/1.0")

            # Set extremism threshold - use unified config
            EXTREMISM_THRESHOLD = self._normalize_extremism_threshold(
                self.THRESHOLDS["initial_intervention"]["extremism_threshold"]
            )

            if avg_extremism >= EXTREMISM_THRESHOLD:
                workflow_logger.info(f"    🚨 Viewpoint too extreme! (avg extremism {avg_extremism:.2f} >= threshold {EXTREMISM_THRESHOLD:.2f})")
                # Force increase negative count to trigger intervention
                negative_count += 2

            return positive_count, negative_count, neutral_count
        except Exception:
            return 0, 0, len(all_comments)

    async def _fallback_sentiment_analysis(self, all_comments: list) -> tuple:
        """Fallback sentiment analysis - based on extremism"""
        try:
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for comment in all_comments:
                content = comment[0]

                # Classify using extremism - async call
                extremism_value, sentiment_value = await self._calculate_viewpoint_extremism_and_sentiment(content, log_details=False)

                extremism_value = self._normalize_extremism_score(extremism_value)
                if extremism_value >= 0.6:  # High extremism
                    negative_count += 1
                elif extremism_value >= 0.3:  # Moderate extremism
                    neutral_count += 1
                else:  # Low extremism
                    positive_count += 1

            # Calculate sentiment score
            total_comments = len(all_comments)
            if total_comments > 0:
                sentiment_score = (positive_count - negative_count) / total_comments
                sentiment_score = max(-1, min(1, sentiment_score))  # Clamp to -1 to 1
                sentiment_score = (sentiment_score + 1) / 2  # Convert to 0-1 range
            else:
                sentiment_score = 0.5

            return positive_count, negative_count, neutral_count, sentiment_score
        except Exception:
            return 0, 0, len(all_comments), 0.5

    def _get_default_sentiment_analysis(self) -> Dict[str, Any]:
        """Get default sentiment analysis result"""
        return {
            "total_comments": 0,
            "malicious_comments": 0,
            "malicious_ratio": 0,
            "positive_comments": 0,
            "negative_comments": 0,
            "neutral_comments": 0,
            "sentiment_score": 0.5,
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
            "analyst_enhanced": False
        }

    def _calculate_engagement_growth(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any]) -> float:
        """Calculate engagement growth rate"""
        try:
            baseline_total = baseline_data.get("likes", 0) + baseline_data.get("comments", 0) + baseline_data.get("shares", 0)
            current_total = current_data.get("likes", 0) + current_data.get("comments", 0) + current_data.get("shares", 0)

            if baseline_total == 0:
                return current_total * 100  # If baseline is 0, return current value as growth

            growth = ((current_total - baseline_total) / baseline_total) * 100
            return growth

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to calculate engagement growth: {e}")
            return 0.0

    def _determine_sentiment_change(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any],
                                  sentiment_analysis: Dict[str, Any]) -> str:
        """Determine sentiment change"""
        try:
            baseline_sentiment = baseline_data.get("sentiment_score", 0.5)
            current_sentiment = sentiment_analysis.get("sentiment_score", 0.5)

            if current_sentiment > baseline_sentiment + 0.1:
                return "improved"
            elif current_sentiment < baseline_sentiment - 0.1:
                return "declined"
            else:
                return "stable"

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to determine sentiment change: {e}")
            return "unknown"

    def _calculate_real_effectiveness_score(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any],
                                          sentiment_analysis: Dict[str, Any], engagement_growth: float) -> float:
        """Calculate effectiveness score based on real data, with sentiment distribution"""
        try:
            score = 0.0

            # 1. Sentiment improvement score (0-3) - based on overall sentiment score
            sentiment_score = sentiment_analysis.get("sentiment_score", 0.5)
            baseline_sentiment = baseline_data.get("sentiment_score", 0.5)
            sentiment_improvement = sentiment_score - baseline_sentiment
            
            if sentiment_improvement >= 0.1:
                score += 3  # Significant improvement
            elif sentiment_improvement >= 0.05:
                score += 2  # Some improvement
            elif sentiment_improvement >= 0:
                score += 1  # Slight improvement
            # If worsening, no points

            # 2. Sentiment distribution improvement (0-2) - based on distribution change
            sentiment_distribution = sentiment_analysis.get("sentiment_distribution", {})
            baseline_distribution = baseline_data.get("sentiment_distribution", {})
            
            positive_improvement = sentiment_distribution.get("positive", 0) - baseline_distribution.get("positive", 0)
            negative_improvement = baseline_distribution.get("negative", 0) - sentiment_distribution.get("negative", 0)  # Less negative is good
            
            if positive_improvement >= 0.1 or negative_improvement >= 0.1:
                score += 2  # Significant distribution improvement
            elif positive_improvement >= 0.05 or negative_improvement >= 0.05:
                score += 1  # Some distribution improvement

            # 3. Extremism improvement score (0-2) - based on extremism change
            current_extremism = self._normalize_extremism_score(
                sentiment_analysis.get("viewpoint_extremism", 0.5)
            )
            baseline_extremism = self._normalize_extremism_score(
                baseline_data.get("viewpoint_extremism", 0.5)
            )
            extremism_improvement = baseline_extremism - current_extremism  # Lower extremism is good
            
            if extremism_improvement >= 0.1:
                score += 2  # Significant extremism reduction
            elif extremism_improvement >= 0.05:
                score += 1  # Some extremism reduction

            # 4. Engagement growth score (0-2) - based on engagement change
            if engagement_growth > 100:
                score += 2  # Major engagement growth
            elif engagement_growth > 50:
                score += 1.5  # Significant engagement growth
            elif engagement_growth > 20:
                score += 1  # Some engagement growth
            elif engagement_growth < -20:
                score -= 1  # Engagement decline, subtract

            # 5. Malicious comment control (0-1) - based on malicious ratio
            malicious_ratio = sentiment_analysis.get("malicious_ratio", 0)
            if malicious_ratio < 0.05:
                score += 1  # Very few malicious comments
            elif malicious_ratio < 0.15:
                score += 0.5  # Fewer malicious comments

            # 6. Agent response score (0-1) - based on response count
            agent_posts = current_data.get("agent_posts", 0)
            if agent_posts >= 3:
                score += 1  # Sufficient agent responses
            elif agent_posts >= 1:
                score += 0.5  # Some agent responses

            # 7. Sentiment balance score (0-1) - based on distribution balance
            positive_ratio = sentiment_distribution.get("positive", 0)
            negative_ratio = sentiment_distribution.get("negative", 0)
            neutral_ratio = sentiment_distribution.get("neutral", 0)
            
            # Calculate sentiment balance (ideally positive/negative balanced, neutral moderate)
            balance_score = 1 - abs(positive_ratio - negative_ratio)  # Closer to 0 means more balanced
            if balance_score >= 0.8:
                score += 1  # Very balanced distribution
            elif balance_score >= 0.6:
                score += 0.5  # Relatively balanced distribution

            return min(10, max(0, score))

        except Exception as e:
            workflow_logger.info(f"  ⚠️  Failed to calculate effectiveness score: {e}")
            return 5.0

    async def _generate_fallback_report(self, monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback report (when database is unavailable)"""
        try:
            # Try to get baseline data from monitoring task
            baseline_data = monitoring_task.get("baseline_data", {})
            if not baseline_data:
                # If baseline data unavailable, return error report
                return {
                    "report_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now(),
                    "monitoring_task_id": monitoring_task["task_id"],
                    "error": "Unable to get baseline data; cannot generate valid report",
                    "data_source": "error_fallback"
                }
            
            # Try to get current data
            target_post_id = monitoring_task.get("target_post_id")
            if target_post_id:
                current_data = await self._get_current_analysis_data(target_post_id, monitoring_task.get("action_id", ""))
            else:
                current_data = {}
            
            if not current_data:
                return {
                    "report_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now(),
                    "monitoring_task_id": monitoring_task["task_id"],
                    "error": "Unable to get current data; cannot generate valid report",
                    "data_source": "error_fallback"
                }
            
            # Calculate real changes
            baseline_engagement = baseline_data.get("engagement_data", {})
            current_engagement = current_data.get("engagement_data", {})
            
            baseline_total = baseline_engagement.get("likes", 0) + baseline_engagement.get("comments", 0) + baseline_engagement.get("shares", 0)
            current_total = current_engagement.get("likes", 0) + current_engagement.get("comments", 0) + current_engagement.get("shares", 0)
            
            if baseline_total > 0:
                engagement_growth = ((current_total - baseline_total) / baseline_total) * 100
            else:
                engagement_growth = 0
            
            baseline_sentiment = baseline_data.get("sentiment_score", 0.5)
            current_sentiment = current_data.get("sentiment_score", 0.5)
            sentiment_change = "improved" if current_sentiment > baseline_sentiment else "declined"
            
            # Calculate effectiveness score
            effectiveness_score = self._calculate_real_effectiveness_score(
                baseline_data, current_data, 
                {"sentiment_change": sentiment_change}, 
                engagement_growth
            )
            
            return {
                "report_id": f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now(),
                "monitoring_task_id": monitoring_task["task_id"],
                "baseline_data": baseline_data,
                "current_data": current_data,
                "engagement_growth": round(engagement_growth, 1),
                "sentiment_change": sentiment_change,
                "effectiveness_score": round(effectiveness_score, 1),
                "recommendations": self._generate_recommendations(
                    effectiveness_score, 
                    sentiment_change,
                    engagement_growth,
                    0,  # malicious_count
                    current_sentiment,
                    baseline_sentiment
                ),
                "data_source": "database_fallback"
            }
            
        except Exception as e:
            workflow_logger.info(f"  ❌ Failed to generate fallback report: {e}")
            return {
                "report_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now(),
                "monitoring_task_id": monitoring_task["task_id"],
                "error": f"Fallback report generation failed: {str(e)}",
                "data_source": "error_fallback"
            }

    def _generate_recommendations(self, effectiveness_score: float, sentiment_change: str, 
                                engagement_growth: float = 0, malicious_count: int = 0, 
                                current_sentiment: float = 0.5, baseline_sentiment: float = 0.5) -> List[str]:
        """Generate personalized recommendations based on multiple dimensions"""
        
        recommendations = []
        
        # Base recommendations from effectiveness score
        if effectiveness_score < 3:
            recommendations.extend([
                f"Low effectiveness score ({effectiveness_score:.1f}/10); consider activating more amplifier agents",
                "Reassess target audience fit for the messaging strategy",
                "Consider increasing interaction frequency with community responses"
            ])
        elif effectiveness_score < 6:
            recommendations.extend([
                f"Moderate effectiveness score ({effectiveness_score:.1f}/10); closely monitor negative developments",
                "Consider fine-tuning tone to improve resonance",
                "Maintain current engagement level and observe trends"
            ])
        else:
            recommendations.extend([
                f"Good effectiveness score ({effectiveness_score:.1f}/10); current strategy is effective",
                "Continue monitoring; no major adjustments needed",
                "Record successful approaches for future reference"
            ])
        
        # Recommendations based on sentiment change
        if sentiment_change == "declined":
            sentiment_drop = baseline_sentiment - current_sentiment
            recommendations.append(f"Sentiment dropped by {sentiment_drop:.2f}; review messaging immediately")
        elif sentiment_change == "improved":
            sentiment_gain = current_sentiment - baseline_sentiment
            recommendations.append(f"Sentiment improved by {sentiment_gain:.2f}; keep current positive strategy")
        
        # Recommendations based on engagement growth
        if engagement_growth < -20:
            recommendations.append(f"Engagement down {abs(engagement_growth):.1f}%; consider improving content appeal")
        elif engagement_growth > 100:
            recommendations.append(f"Engagement surged {engagement_growth:.1f}%; monitor content propagation quality")
        
        # Recommendations based on malicious comment count
        if malicious_count > 5:
            recommendations.append(f"Detected {malicious_count} malicious comments; strengthen defenses")
        elif malicious_count > 0:
            recommendations.append(f"Found {malicious_count} suspected malicious comments; stay alert")
            
        # Recommendations based on current sentiment score
        if current_sentiment < 0.3:
            recommendations.append("Current sentiment is negative; consider positive content to balance opinion")
        elif current_sentiment > 0.7:
            recommendations.append("Current sentiment is positive; consider reducing intervention intensity")
        
        return recommendations

    async def _save_effect_briefing(self, feedback_report: Dict[str, Any], monitoring_task_id: str, cycle: int) -> Optional[str]:
        """Save effectiveness brief to file"""
        try:
            import json
            import os

            # Create effectiveness report directory
            reports_dir = "logs/effectiveness_reports"
            os.makedirs(reports_dir, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"effectiveness_report_{monitoring_task_id}_cycle{cycle}_{timestamp}.json"
            filepath = os.path.join(reports_dir, filename)

            # Prepare effectiveness report data to save
            monitoring_interval_value = self.monitoring_tasks.get(monitoring_task_id, {}).get("monitoring_interval")
            monitoring_interval_text = (
                f"{monitoring_interval_value} minutes"
                if isinstance(monitoring_interval_value, int) and monitoring_interval_value > 0
                else "N/A"
            )
            report_data = {
                "report_id": f"effectiveness_report_{timestamp}",
                "monitoring_task_id": monitoring_task_id,
                "cycle": cycle,
                "timestamp": timestamp,
                "generated_at": datetime.now().isoformat(),
                "feedback_report": feedback_report,
                "system_info": {
                    "version": "MOSAIC v1.0",
                    "agent_system": "SimpleCoordinationSystem",
                    "monitoring_interval": monitoring_interval_text
                }
            }

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            return filepath

        except Exception as e:
            workflow_logger.info(f"     ❌ Effectiveness report save failed: {e}")
            return None

    async def _send_report_to_strategist(self, feedback_report: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """[Core method] Send analyst effectiveness report to strategist agent for evaluation - enhanced with retry mechanism"""

        for attempt in range(self.strategist.max_retries):
            try:
                return await self._send_report_attempt(feedback_report, task, attempt)
            except Exception as e:
                workflow_logger.info(f"    ❌ Failed to send report to strategist agent on attempt {attempt + 1}: {e}")
                if attempt == self.strategist.max_retries - 1:
                    workflow_logger.info("    ⚠️ Strategist agent retries exhausted, using fallback rules")
                    # Fall back to original simple rule evaluation
                    needs_adjustment = await self._evaluate_need_for_adjustment(feedback_report)
                    return {
                        "success": False,
                        "needs_adjustment": needs_adjustment,
                        "decision_type": "fallback_after_retries",
                        "assessment": f"Strategist agent failed after {self.strategist.max_retries} retries; using rule-based evaluation",
                        "error": f"Final error: {str(e)}"
                    }
                await asyncio.sleep(self.strategist.retry_delay * (attempt + 1))

    async def _send_report_attempt(self, feedback_report: Dict[str, Any], task: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """Single attempt to send report to strategist"""
        try:
            workflow_logger.info(f"    📊 Analyst Agent -> Strategist Agent: effectiveness report transfer (attempt {attempt + 1}/{self.strategist.max_retries})")

            # Build strategist Agent evaluation prompt (English)
            task_monitoring_interval = task.get("monitoring_interval")
            task_monitoring_interval_text = (
                f"{task_monitoring_interval} minutes"
                if isinstance(task_monitoring_interval, int) and task_monitoring_interval > 0
                else "N/A"
            )
            strategist_prompt = f"""
You are an experienced public-opinion balancing strategist. You have received a real-time effectiveness report from the Analyst Agent. Please evaluate whether the current strategy is working and decide the next step.

[Analyst Agent Effectiveness Report]
- Effectiveness score: {feedback_report.get('effectiveness_score', 0):.1f}/10
- Sentiment change: {feedback_report.get('sentiment_change', 'unknown')}
- Engagement growth: {feedback_report.get('engagement_growth', 0)}%
- Current sentiment score: {feedback_report.get('current_data', {}).get('sentiment_score', 0.5):.2f}
- Baseline sentiment score: {feedback_report.get('baseline_data', {}).get('sentiment_score', 0.5):.2f}
- Malicious comments count: {feedback_report.get('sentiment_analysis', {}).get('malicious_comments_count', 0)}

[Analyst's Professional Analysis]
{self._format_analyst_comparison_for_strategist(feedback_report.get('analyst_comparison', {}))}

[Current Monitoring State]
- Target post ID: {task.get('target_post_id', 'N/A')}
- Action ID: {task.get('action_id', 'N/A')}
- Monitoring interval: {task_monitoring_interval_text}

[Evaluation Requirements]
1. If unexpected negative discourse appears, immediately propose supplementary action plans.
2. Assess whether to activate a new batch of supportive Agents to provide clarification.
3. Assess whether the leader should post a supplementary comment.
4. Or decide to "maintain observation".

Please return the decision in JSON format:
{{
    "assessment": "Assessment of current strategy effectiveness",
    "needs_adjustment": true/false,
    "decision_type": "activate_agents/leader_clarification/increase_activity/maintain_observation",
    "rationale": "Reasoning for the decision",
    "supplementary_actions": [
        {{
            "type": "action_type",
            "description": "Specific action description",
            "priority": "high/medium/low"
        }}
    ]
}}
"""

            # Call strategist agent for evaluation
            strategist_result = await self.strategist.develop_strategy(
                {"task": "feedback_evaluation", "prompt": strategist_prompt},
                f"Monitoring task: {task.get('task_id', 'unknown')}"
            )

            if strategist_result.get("success"):
                strategy_data = strategist_result.get("strategy", {})
                workflow_logger.info(f"    🎯 Strategist agent decision: {strategy_data.get('decision_type', 'unknown')}")
                workflow_logger.info(f"    📋 Decision rationale: {strategy_data.get('rationale', 'N/A')}")

                return {
                    "success": True,
                    "needs_adjustment": strategy_data.get("needs_adjustment", False),
                    "decision_type": strategy_data.get("decision_type", "maintain_observation"),
                    "assessment": strategy_data.get("assessment", ""),
                    "supplementary_actions": strategy_data.get("supplementary_actions", []),
                    "strategist_rationale": strategy_data.get("rationale", ""),
                    "attempt_number": attempt + 1
                }
            else:
                raise Exception(f"Strategist agent evaluation failed: {strategist_result.get('error', 'Unknown error')}")

        except Exception as e:
            raise Exception(f"Send report attempt {attempt + 1} failed: {str(e)}")

    async def _execute_strategist_decision(self, monitoring_task: Dict[str, Any], 
                                         feedback_report: Dict[str, Any],
                                         strategic_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute adjustments based on strategist agent decision"""
        
        try:
            decision_type = strategic_decision.get("decision_type", "maintain_observation")
            supplementary_actions = strategic_decision.get("supplementary_actions", [])
            
            workflow_logger.info(f"    🚀 Executing strategist agent decision: {decision_type}")
            
            if decision_type == "activate_agents":
                # Activate a new batch of amplifier Agents to clarify
                result = await self._activate_additional_amplifier_agents(monitoring_task)
                adjustment_type = "activate_additional_agents"
            elif decision_type == "leader_clarification":
                # Have leader post a supplementary comment
                result = await self._generate_leader_clarification(monitoring_task)
                adjustment_type = "leader_clarification"
            elif decision_type == "increase_activity":
                # Increase current amplifier Agent activity
                result = await self._increase_amplifier_activity(monitoring_task)
                adjustment_type = "increase_amplifier_activity"
            elif decision_type == "maintain_observation":
                # Maintain observation, no adjustment
                result = {"message": "Strategist recommends maintaining observation; no adjustment needed", "actions_taken": 0}
                adjustment_type = "maintain_observation"
            else:
                # Execute custom supplementary actions
                result = await self._execute_custom_supplementary_actions(supplementary_actions, monitoring_task)
                adjustment_type = f"custom_actions_{len(supplementary_actions)}"
            
            return {
                "success": True,
                "adjustment_type": adjustment_type,
                "decision_type": decision_type,
                "timestamp": datetime.now(),
                "details": result,
                "strategist_decision": strategic_decision.get("assessment", ""),
                "supplementary_actions_executed": len(supplementary_actions)
            }
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to execute strategist decision: {e}")
            return {
                "success": False,
                "error": str(e),
                "decision_type": strategic_decision.get("decision_type", "unknown"),
                "timestamp": datetime.now()
            }

    async def _execute_custom_supplementary_actions(self, actions: List[Dict[str, Any]], 
                                                  monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom supplementary actions defined by strategist agent"""
        
        executed_actions = []
        total_success = 0
        
        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            description = action.get("description", "")
            priority = action.get("priority", "medium")
            
            workflow_logger.info(f"      🎯 Executing supplementary action {i+1}/{len(actions)}: {action_type} ({priority})")
            workflow_logger.info(f"         Description: {description}")
            
            try:
                # Execute corresponding operation based on action type
                if "agent" in action_type.lower():
                    result = await self._activate_additional_amplifier_agents(monitoring_task)
                elif "leader" in action_type.lower():
                    result = await self._generate_leader_clarification(monitoring_task)
                elif "activity" in action_type.lower():
                    result = await self._increase_amplifier_activity(monitoring_task)
                else:
                    # Generic handling: increase activity
                    result = await self._increase_amplifier_activity(monitoring_task)
                
                executed_actions.append({
                    "action": action_type,
                    "description": description,
                    "priority": priority,
                    "result": result,
                    "success": True
                })
                total_success += 1
                
            except Exception as e:
                workflow_logger.info(f"      ❌ Supplementary action execution failed: {e}")
                executed_actions.append({
                    "action": action_type,
                    "description": description,
                    "priority": priority,
                    "error": str(e),
                    "success": False
                })
        
        return {
            "total_actions": len(actions),
            "successful_actions": total_success,
            "executed_actions": executed_actions,
            "success_rate": total_success / max(len(actions), 1)
        }

    async def _evaluate_need_for_adjustment(self, feedback_report: Dict[str, Any]) -> bool:
        """Evaluate whether strategy adjustment is needed"""

        effectiveness_score = feedback_report.get("effectiveness_score", 0)
        sentiment_change = feedback_report.get("sentiment_change", "unknown")
        engagement_growth = feedback_report.get("engagement_growth", 0)

        # Adjustment trigger conditions
        needs_adjustment = (
            effectiveness_score < 4 or  # Effectiveness score too low
            sentiment_change == "declined" or  # Sentiment worsened
            engagement_growth < -10  # Engagement drops significantly
        )

        return needs_adjustment

    async def _make_strategic_adjustment(self, monitoring_task: Dict[str, Any],
                                       feedback_report: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy adjustment"""

        try:
            effectiveness_score = feedback_report.get("effectiveness_score", 0)
            sentiment_change = feedback_report.get("sentiment_change", "unknown")

            adjustment_type = "unknown"

            if effectiveness_score < 3:
                # Poor effectiveness, activate additional amplifier Agents
                adjustment_type = "activate_additional_agents"
                result = await self._activate_additional_amplifier_agents(monitoring_task)
            elif sentiment_change == "declined":
                # Sentiment worsened, have leader release clarification
                adjustment_type = "leader_clarification"
                result = await self._generate_leader_clarification(monitoring_task)
            else:
                # Minor adjustment, increase amplifier Agent activity
                adjustment_type = "increase_amplifier_activity"
                result = await self._increase_amplifier_activity(monitoring_task)

            return {
                "success": True,
                "adjustment_type": adjustment_type,
                "timestamp": datetime.now(),
                "details": result,
                "trigger_score": effectiveness_score,
                "trigger_sentiment": sentiment_change
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now()
            }

    async def _activate_additional_amplifier_agents(self, monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Activate additional amplifier Agents"""

        workflow_logger.info("    🚀 Activating additional amplifier Agents...")

        # Use remaining amplifier Agents to generate extra responses
        used_agents = len(monitoring_task.get("amplifier_responses", []))
        remaining_agents = self.amplifier_agents[used_agents:]

        if not remaining_agents:
            return {"message": "No additional agents available"}

        # Generate additional responses
        additional_responses = []
        for i, agent in enumerate(remaining_agents[:2]):  # Activate up to 2 additional agents
            try:
                # Safely get target content
                target_content = None
                if "leader_content" in monitoring_task:
                    leader_content = monitoring_task["leader_content"]
                    if isinstance(leader_content, dict):
                        if "content" in leader_content and isinstance(leader_content["content"], dict):
                            target_content = leader_content["content"].get("final_content")
                        elif "final_content" in leader_content:
                            target_content = leader_content["final_content"]
                        elif "content" in leader_content:
                            target_content = leader_content["content"]
                
                # If target content unavailable, use default content
                if not target_content:
                    target_content = "Continue discussing this topic and share your views and experience."
                    workflow_logger.info("    ⚠️ Target content unavailable, using default content")
                
                response = await agent.generate_response(
                    target_content,
                    timing_delay=1  # Fast response
                )
                if response.get("success"):
                    additional_responses.append(response)
            except Exception as e:
                workflow_logger.info(f"    ❌ Additional agent {agent.agent_id} failed: {e}")

        workflow_logger.info(f"    ✅ Activated {len(additional_responses)} additional agents")

        return {
            "additional_agents_activated": len(additional_responses),
            "responses": additional_responses
        }

    async def _generate_leader_clarification(self, monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate leader clarification content"""

        workflow_logger.info("    📝 Generating leader clarification content...")

        try:
            # Create clarification instructions
            clarification_instruction = {
                "tone": "calm and clarifying",
                "key_points": ["address misunderstandings", "provide additional context", "maintain positive dialogue"],
                "target_audience": "concerned community members",
                "content_length": "100-200 characters",
                "style": "explanatory"
            }

            # Use enhanced leader USC flow to generate clarification content
            clarification_result = await self.leader.generate_strategic_content(
                clarification_instruction,
                "Follow-up clarification needed based on community feedback"
            )

            if clarification_result.get("success"):
                workflow_logger.info("    ✅ Leader clarification content generated")
                return {
                    "clarification_generated": True,
                    "content": clarification_result["content"]
                }
            else:
                return {
                    "clarification_generated": False,
                    "error": clarification_result.get("error", "Unknown error")
                }

        except Exception as e:
            return {
                "clarification_generated": False,
                "error": str(e)
            }

    async def _increase_amplifier_activity(self, monitoring_task: Dict[str, Any]) -> Dict[str, Any]:
        """Increase amplifier Agent activity"""

        workflow_logger.info("    📈 Increasing amplifier Agent activity...")

        # Simulate increased activity (in real app this may include more replies, likes, etc.)
        return {
            "activity_increased": True,
            "actions_taken": ["increased_response_frequency", "enhanced_engagement"],
            "message": "amplifier agent activity has been increased"
        }

    async def stop_monitoring(self, monitoring_task_id: str = None):
        """Stop monitoring"""

        if monitoring_task_id:
            task = self.monitoring_tasks.get(monitoring_task_id)
            if task:
                workflow_logger.info(f"⏹️  Stopping monitoring task: {monitoring_task_id}")
                handle = self.monitoring_task_handles.get(monitoring_task_id)
                if handle and not handle.done():
                    handle.cancel()
                # Remove from monitoring task list
                if monitoring_task_id in self.monitoring_tasks:
                    del self.monitoring_tasks[monitoring_task_id]
                self.monitoring_task_handles.pop(monitoring_task_id, None)
            else:
                workflow_logger.info(f"⚠️  Monitoring task not found: {monitoring_task_id}")
        else:
            workflow_logger.info("⏹️  Stopping all monitoring tasks")
            for task_id, handle in list(self.monitoring_task_handles.items()):
                if handle and not handle.done():
                    handle.cancel()
                self.monitoring_task_handles.pop(task_id, None)
            # Clear all monitoring tasks
            self.monitoring_tasks.clear()

        self.monitoring_active = False

    def emergency_stop_all_monitoring(self):
        """Emergency stop for all monitoring tasks"""
        workflow_logger.info("🚨 Emergency stop for all monitoring tasks")
        self.monitoring_active = False
        self.monitoring_tasks.clear()
        for task_id, handle in list(self.monitoring_task_handles.items()):
            if handle and not handle.done():
                handle.cancel()
            self.monitoring_task_handles.pop(task_id, None)
        workflow_logger.info("✅ All monitoring tasks stopped")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status"""

        return {
            "monitoring_active": self.monitoring_active,
            "active_tasks": len(self.monitoring_tasks),
            "total_feedback_reports": len(self.feedback_history),
            "tasks": list(self.monitoring_tasks.keys())
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "current_phase": self.current_phase,
            "total_actions_completed": len(self.action_history),
            "agent_status": {
                "analyst": "active",
                "strategist": "active", 
                "leader": "active",
                "amplifier_agents": len(self.amplifier_agents)
            },
            "recent_performance": self._calculate_performance()
        }
    
    def _calculate_performance(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not self.action_history:
            return {"no_data": True}
        
        recent_actions = self.action_history[-5:]
        
        avg_effectiveness = sum(
            action["phases"]["phase_3"]["effectiveness_score"] 
            for action in recent_actions
        ) / len(recent_actions)
        
        success_rate = len([a for a in recent_actions if a["success"]]) / len(recent_actions)
        
        return {
            "average_effectiveness": avg_effectiveness,
            "success_rate": success_rate,
            "total_recent_actions": len(recent_actions)
        }

    def _calculate_effectiveness_score(self, original_content: str, amplifier_responses: list,
                                     strategy_result: dict, analysis_result: dict) -> float:
        """Calculate effectiveness score with heuristics"""
        import random
        import re

        # Base score
        base_score = 5.0

        # 1. Response count bonus (max +2)
        response_bonus = min(2.0, len(amplifier_responses) * 0.3)

        # 2. Extremism impact (higher extremism means harder intervention, higher bonus if successful)
        # Fix: access analysis result data structure correctly
        analysis = analysis_result.get("analysis", {})
        extremism_level = analysis.get("extremism_level", 1)
        
        # Ensure extremism_level is numeric
        if hasattr(extremism_level, 'value'):
            extremism_value = extremism_level.value
        else:
            extremism_value = int(extremism_level) if extremism_level else 1

        extremism_bonus = extremism_value * 0.5  # Levels 1-4 correspond to 0.5-2 points

        # 3. Strategy complexity bonus - fix: access correct strategy data
        strategy = strategy_result.get("strategy", {})
        # Calculate complexity by number of key_points
        leader_instruction = strategy.get("leader_instruction", {})
        key_points = leader_instruction.get("key_points", [])
        strategy_complexity = len(key_points) if key_points else 1
        complexity_bonus = min(1.0, strategy_complexity * 0.2)

        # 4. Content quality evaluation (based on AI semantics)
        quality_score = 0
        for response in amplifier_responses:
            if response.get("success", False):
                response_data = response.get("response", {})
                content = response_data.get("response_content", "")
                # Score based on length and structure (simplified quality evaluation)
                if content:
                    # Reasonable content length score
                    content_length = len(content)
                    if 50 <= content_length <= 300:  # Ideal length range
                        quality_score += 1.0
                    elif 30 <= content_length <= 500:  # Acceptable range
                        quality_score += 0.5

                    # Constructiveness score for questions
                    if '?' in content or '？' in content:
                        quality_score += 0.3

                    # Score for avoiding excessive repetition
                    words = content.split()
                    if len(set(words)) > len(words) * 0.7:  # Vocabulary diversity
                        quality_score += 0.2

        quality_bonus = min(1.5, quality_score * 0.1)

        # 5. Random factor (simulate uncertainty)
        random_factor = random.uniform(-0.5, 0.5)

        # Calculate final score
        final_score = base_score + response_bonus + extremism_bonus + complexity_bonus + quality_bonus + random_factor

        # Ensure score is within reasonable range
        final_score = max(3.0, min(10.0, final_score))

        # Round to one decimal
        return round(final_score, 1)


    def _classify_content_type(self, content: str) -> str:
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["news", "breaking", "report", "investigation"]):
            return "news"
        elif any(word in content_lower for word in ["opinion", "think", "believe", "feel"]):
            return "opinion"
        elif any(word in content_lower for word in ["conspiracy", "cover", "hide", "secret"]):
            return "conspiracy"
        elif any(word in content_lower for word in ["political", "election", "government", "policy"]):
            return "political"
        else:
            return "general"

    async def _strategist_evaluate_and_plan(self, effectiveness_report: Dict[str, Any],
                                          original_strategy: Dict[str, Any], content_text: str,
                                          action_id: str) -> Dict[str, Any]:
        """Strategist evaluates effectiveness report and plans supplements (phase 3) - enhanced with retry mechanism"""

        for attempt in range(self.strategist.max_retries):
            try:
                return await self._strategist_evaluate_attempt(
                    effectiveness_report, original_strategy, content_text, action_id, attempt
                )
            except Exception as e:
                workflow_logger.info(f"    ❌ Strategist evaluation attempt {attempt + 1} failed: {e}")
                if attempt == self.strategist.max_retries - 1:
                    workflow_logger.info("    ⚠️ Strategist evaluation retries exhausted, using rule-based judgment")
                    effectiveness_score = effectiveness_report.get("effectiveness_score", 0)
                    critical_issues = effectiveness_report.get("critical_issues", [])
                    needs_supplement = effectiveness_score < 5.0 or len(critical_issues) >= 2
                    return {
                        "needs_supplementary_action": needs_supplement,
                        "reason": f"Strategist evaluation failed after {self.strategist.max_retries} retries; using rule-based judgment",
                        "supplementary_actions": [],
                        "error": f"Final error: {str(e)}"
                    }
                await asyncio.sleep(self.strategist.retry_delay * (attempt + 1))

    async def _strategist_evaluate_attempt(self, effectiveness_report: Dict[str, Any],
                                         original_strategy: Dict[str, Any], content_text: str,
                                         action_id: str, attempt: int) -> Dict[str, Any]:
        """Single attempt to evaluate effectiveness and plan"""
        try:
            workflow_logger.info(f"    🎯 Strategist evaluating execution effectiveness... (attempt {attempt + 1}/{self.strategist.max_retries})")

            effectiveness_score = effectiveness_report.get("effectiveness_score", 0)
            critical_issues = effectiveness_report.get("critical_issues", [])
            execution_success = effectiveness_report.get("execution_success", {})

            # Strategist evaluation prompt
            evaluation_prompt = f"""
You are an experienced public-opinion balancing strategist. You need to evaluate the effectiveness of the current intervention and decide whether supplementary actions are needed.

[Execution Results]
- Effectiveness score: {effectiveness_score}/10
- Leader response: {'success' if execution_success.get('leader_success') else 'failed'}
- amplifier responses: {execution_success.get('successful_responses', 0)}/{execution_success.get('total_responses', 0)} (success rate: {execution_success.get('success_rate', 0)*100:.0f}%)
- Critical issues: {', '.join(critical_issues) if critical_issues else 'none'}

[Evaluation Requirements]
1. Evaluate whether the current effectiveness meets expectations
2. If effectiveness is poor, propose a concrete supplementary action plan
3. Provide clear action recommendations

Please return the evaluation result in JSON format:
{{
    "effectiveness_assessment": "Effectiveness assessment description",
    "supplementary_action_recommended": true/false,
    "supplementary_actions": [
        {{
            "type": "action_type",
            "description": "Specific action description",
            "priority": "high/medium/low"
        }}
    ],
    "strategic_recommendation": "Overall strategic recommendation"
}}
"""

            # Call strategist for evaluation
            strategist_result = await self.strategist.develop_strategy(
                {"task": "effectiveness_evaluation", "prompt": evaluation_prompt},
                content_text
            )

            if not strategist_result.get("success"):
                raise Exception(f"Strategist evaluation failed: {strategist_result.get('error', 'Unknown error')}")

            strategy_data = strategist_result.get("strategy", {})

            # Parse strategist decision
            needs_supplementary_action = (
                effectiveness_score < 6.0 or
                len(critical_issues) >= 2 or
                strategy_data.get("supplementary_action_recommended", False)
            )

            supplementary_plan = {
                "evaluation_id": f"eval_{action_id}",
                "timestamp": datetime.now().isoformat(),
                "effectiveness_assessment": strategy_data.get("effectiveness_assessment", "Effectiveness needs improvement"),
                "needs_supplementary_action": needs_supplementary_action,
                "supplementary_actions": strategy_data.get("supplementary_actions", []),
                "strategic_recommendation": strategy_data.get("strategic_recommendation", "Maintain status quo"),
                "attempt_number": attempt + 1
            }

            if needs_supplementary_action:
                action_count = len(supplementary_plan["supplementary_actions"])
                workflow_logger.info(f"    🔥 Strategist recommends supplementary actions ({action_count} items)")
            else:
                workflow_logger.info("    ✅ Strategist evaluation: current effectiveness meets requirements")

            return supplementary_plan

        except Exception as e:
            raise Exception(f"Strategist evaluation attempt {attempt + 1} failed: {str(e)}")

    async def _execute_supplementary_plan(self, supplementary_plan: Dict[str, Any], 
                                        action_id: str, content_text: str) -> List[Dict[str, Any]]:
        """Execute supplementary plan defined by strategist"""
        try:
            supplementary_actions = supplementary_plan.get("supplementary_actions", [])
            executed_actions = []
            
            workflow_logger.info(f"    🚀 Starting execution of {len(supplementary_actions)} supplementary actions...")
            
            for i, action in enumerate(supplementary_actions):
                action_type = action.get("action_type", "additional_response")
                priority = action.get("priority", "medium")
                
                workflow_logger.info(f"      {i+1}. Execute {action_type} (priority: {priority})")
                
                if action_type == "additional_response":
                    # Generate additional amplifier response
                    additional_response = await self._generate_additional_amplifier_response(
                        action, content_text, action_id
                    )
                    executed_actions.append(additional_response)
                    
                elif action_type == "leader_clarification":
                    # Leader provides clarification or supplementary information
                    clarification = await self._generate_leader_clarification(
                        action, content_text, action_id
                    )
                    executed_actions.append(clarification)
                    
                elif action_type == "strategy_adjustment":
                    # Adjust existing strategy
                    adjustment = await self._adjust_current_strategy(
                        action, supplementary_plan, action_id
                    )
                    executed_actions.append(adjustment)
                
                # Limit number of supplementary actions to avoid over-intervention
                if len(executed_actions) >= 3:
                    workflow_logger.info("      ⚠️  Supplementary action limit reached, stopping execution")
                    break
            
            successful_actions = [a for a in executed_actions if a.get("success")]
            workflow_logger.info(f"    ✅ Supplementary actions completed: {len(successful_actions)}/{len(executed_actions)} succeeded")
            
            return executed_actions
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to execute supplementary plan: {e}")
            return []

    async def _generate_additional_amplifier_response(self, action: Dict[str, Any], content_text: str, action_id: str) -> Dict[str, Any]:
        """Generate additional amplifier response"""
        try:
            workflow_logger.info("        🔊 Generating additional amplifier response...")
            
            # Build instructions
            amplifier_instruction = {
                "type": "supplementary_amplifier",
                "message_type": action.get("description", "additional supportive response"),
                "target_audience": action.get("target_audience", "general"),
                "tone": "supportive",
                "urgency": action.get("priority", "medium"),
                "context": "supplementary_intervention"
            }
            
            # Select an amplifier Agent
            selected_amplifier = self.amplifier_agents[0] if self.amplifier_agents else None
            if not selected_amplifier:
                return {"success": False, "error": "No amplifier agents available"}
            
            # Generate response
            response = await selected_amplifier.generate_content(amplifier_instruction, content_text)
            
            if response.get("success"):
                # Save to database
                comment_id = self._save_amplifier_comment_to_database(
                    response.get("content", {}).get("final_content", ""),
                    action_id,
                    None  # Use default latest-post strategy during strategic adjustment
                )
                workflow_logger.info(f"          ✅ Additional amplifier response generated and saved: {comment_id}")
                return {
                    "success": True,
                    "action_type": "additional_response",
                    "comment_id": comment_id,
                    "content": response.get("content", {})
                }
            else:
                workflow_logger.info("          ❌ Additional amplifier response generation failed")
                return {"success": False, "error": response.get("error")}
                
        except Exception as e:
            workflow_logger.info(f"        ❌ Failed to generate additional amplifier response: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_leader_clarification(self, action: Dict[str, Any], content_text: str, action_id: str) -> Dict[str, Any]:
        """Generate leader clarification information"""
        try:
            workflow_logger.info("        👑 Generating leader clarification...")
            
            # Build clarification instructions
            clarification_instruction = {
                "type": "clarification",
                "purpose": action.get("description", "provide clarification information"),
                "target_audience": action.get("target_audience", "concerned_users"),
                "tone": "authoritative_but_calm",
                "context": "addressing_concerns",
                "key_message": "provide factual clarification and reassurance"
            }
            
            # Use enhanced leader USC flow to generate clarification
            clarification_result = await self.leader.generate_strategic_content(
                clarification_instruction, content_text
            )
            
            if clarification_result.get("success"):
                # Save to database
                comment_id = self._save_leader_comment_to_database(
                    clarification_result.get("content", {}).get("final_content", ""),
                    "",  # Supplementary clarification, not tied to a specific post
                    action_id
                )
                workflow_logger.info(f"          ✅ Leader clarification generated and saved: {comment_id}")
                return {
                    "success": True,
                    "action_type": "leader_clarification",
                    "comment_id": comment_id,
                    "content": clarification_result.get("content", {})
                }
            else:
                workflow_logger.info("          ❌ Leader clarification generation failed")
                return {"success": False, "error": clarification_result.get("error")}
                
        except Exception as e:
            workflow_logger.info(f"        ❌ Failed to generate leader clarification: {e}")
            return {"success": False, "error": str(e)}

    async def _adjust_current_strategy(self, action: Dict[str, Any], supplementary_plan: Dict[str, Any], action_id: str) -> Dict[str, Any]:
        """Adjust current strategy"""
        try:
            workflow_logger.info("        ⚙️  Adjusting current strategy...")
            
            # Record strategy adjustment
            adjustment_record = {
                "adjustment_id": f"adj_{action_id}",
                "timestamp": datetime.now(),
                "adjustment_type": action.get("description", "strategy fine-tuning"),
                "reason": action.get("expected_impact", "improve effectiveness"),
                "priority": action.get("priority", "medium"),
                "original_assessment": supplementary_plan.get("strategist_analysis", {})
            }
            
            # Adjust monitoring parameters, response thresholds, etc., if needed
            # Currently only record adjustment intent
            workflow_logger.info(f"          📝 Strategy adjustment recorded: {adjustment_record['adjustment_type']}")
            
            return {
                "success": True,
                "action_type": "strategy_adjustment", 
                "adjustment_record": adjustment_record
            }
            
        except Exception as e:
            workflow_logger.info(f"        ❌ Strategy adjustment failed: {e}")
            return {"success": False, "error": str(e)}

    def _save_amplifier_comment_to_database(self, content: str, action_id: str, target_post_id: str = None) -> Optional[str]:
        """Save amplifier comment to database - supports target post"""
        try:
            from utils import Utils
            from datetime import datetime
            import json
            import hashlib
            
            def save_amplifier_comment_operation():
                # Generate comment ID
                comment_id = Utils.generate_formatted_id("comment")

                # Use provided target_post_id, or get latest post if empty
                if target_post_id and target_post_id.strip():
                    # Validate target post exists
                    result = fetch_one("SELECT COUNT(*) as count FROM posts WHERE post_id = ?", (target_post_id,))
                    if not result or result['count'] == 0:
                        workflow_logger.info(f"          ⚠️  amplifier Agent: target post {target_post_id} not found, using latest post")
                        target_post_id = None
                    else:
                        # Simplified logging: do not log each database operation
                        pass

                if not target_post_id:
                    # Fallback: get latest post as target
                    result = fetch_one("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 1")
                    if not result:
                        workflow_logger.info("          ❌ amplifier Agent: no posts found in database")
                        return None
                    target_post_id = result['post_id']
                    workflow_logger.info(f"          📍 amplifier Agent: using latest post as target {target_post_id}")

                # Create amplifier Agent user ID (masquerade as normal user)
                seed = f"amplifier_agent_{action_id}_{datetime.now().strftime('%Y%m%d')}"
                hash_obj = hashlib.md5(seed.encode())
                user_suffix = hash_obj.hexdigest()[:6]
                amplifier_user_id = f"user-{user_suffix}"

                # Check and create user if needed
                user_result = fetch_one("SELECT COUNT(*) as count FROM users WHERE user_id = ?", (amplifier_user_id,))
                if not user_result or user_result['count'] == 0:
                    # Create a persona that looks like a normal user
                    fake_persona = {
                        "name": f"User{user_suffix}",
                        "type": "amplifier",  # Internal marker
                        "profession": "Various",
                        "age_range": "25-40",
                        "personality_traits": ["Supportive", "Agreeable", "Constructive"],
                        "agent_role": "amplifier",
                        "is_system_agent": True
                    }

                    execute_query('''
                        INSERT INTO users (user_id, username, user_type, agent_role, created_at, persona)
                        VALUES (?, ?, ?, ?, datetime('now'), ?)
                    ''', (amplifier_user_id, f"User{user_suffix}", "agent", "amplifier", json.dumps(fake_persona, ensure_ascii=False)))

                # Insert comment
                execute_query('''
                    INSERT INTO comments (comment_id, post_id, content, author_id, created_at, is_agent_response)
                    VALUES (?, ?, ?, ?, datetime('now'), 1)
                ''', (comment_id, target_post_id, content, amplifier_user_id))

                # Record comment -> timestep mapping
                try:
                    # Get current time step from SimpleCoordinationSystem
                    current_step = getattr(self, 'current_time_step', None)
                    
                    if current_step is not None:
                        execute_query('''
                            INSERT OR REPLACE INTO comment_timesteps (comment_id, user_id, post_id, time_step)
                            VALUES (?, ?, ?, ?)
                        ''', (comment_id, amplifier_user_id, target_post_id, int(current_step)))
                except Exception as e:
                    # Non-fatal: mapping is best-effort
                    workflow_logger.debug(f"Failed to record amplifier comment timestep: {e}")

                # Database manager automatically handles transaction commits
                return comment_id

            # Use database manager to execute operation
            return save_amplifier_comment_operation()

        except Exception as e:
            workflow_logger.info(f"          ❌ Failed to save amplifier comment: {e}")
            return None

    def _update_monitoring_with_supplementary_plan(self, monitoring_task_id: str, supplementary_plan: Dict[str, Any]):
        """Update monitoring task to include supplementary plan information"""
        try:
            if monitoring_task_id and monitoring_task_id in self.monitoring_tasks:
                task = self.monitoring_tasks[monitoring_task_id]
                task["supplementary_plan"] = supplementary_plan
                task["enhanced_monitoring"] = True
                workflow_logger.info("    📈 Monitoring task updated to include strategist supplementary plan")
        except Exception as e:
            workflow_logger.info(f"    ⚠️  Failed to update monitoring task: {e}")

    def _save_leader_comment_to_database(self, leader_content: str, target_post_id: str, action_id: str) -> Optional[str]:
        """Save Leader Agent content as a comment to database"""
        try:
            from utils import Utils
            from datetime import datetime
            import json
            import hashlib
            
            def save_leader_comment_operation():
                # Generate comment ID
                comment_id = Utils.generate_formatted_id("comment")

                # Use provided target_post_id, or get latest post if empty
                final_target_post_id = target_post_id
                if not final_target_post_id or final_target_post_id.strip() == "":
                    result = fetch_one("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 1")
                    if not result:
                        workflow_logger.info("    ⚠️  Leader Agent: no posts in database, skipping comment save")
                        return None
                    final_target_post_id = result['post_id']

                # Validate target post exists
                post_result = fetch_one("SELECT COUNT(*) as count FROM posts WHERE post_id = ?", (final_target_post_id,))
                if not post_result or post_result['count'] == 0:
                    # If specified post not found, try latest post as fallback
                    workflow_logger.warning(f"    ⚠️  Leader Agent: target post {final_target_post_id} not found, trying latest post")
                    result = fetch_one("SELECT post_id FROM posts ORDER BY created_at DESC LIMIT 1")
                    if not result:
                        workflow_logger.info("    ⚠️  Leader Agent: no posts in database, skipping comment save")
                        return None
                    final_target_post_id = result['post_id']
                    workflow_logger.info(f"    📍 Leader Agent: using fallback post {final_target_post_id}")

                # Create or get Leader Agent user ID (masquerade as normal user)
                # To reduce network fragmentation, use a two-layer structure:
                # - Internal: leader1 / leader2 (distinguished by action_id ending with "_leader2")
                # - External: map from _leader_user_id_pool to user-xxxxxx for long-term stability
                leader_user_id = None
                user_suffix = None

                # Prefer leader ID pool in coordination system (similar to amplifier logic):
                # - Leader 1: always use index 0
                # - Leader 2: always use index 1 (action_id ends with "_leader2")
                if hasattr(self, "_leader_user_id_pool") and self._leader_user_id_pool:
                    pool = self._leader_user_id_pool
                    is_second_leader = str(action_id).endswith("_leader2")
                    idx = 1 if is_second_leader else 0
                    idx = idx % len(pool)
                    leader_user_id = pool[idx]
                    try:
                        user_suffix = leader_user_id.split("-", 1)[1]
                    except (IndexError, ValueError):
                        user_suffix = leader_user_id
                else:
                    # Fallback: if no pool configured, use original hash logic, still masquerade as user-xxxxxx
                    import hashlib
                    seed = f"leader_agent_{action_id}_{datetime.now().strftime('%Y%m%d')}"
                    hash_obj = hashlib.md5(seed.encode())
                    user_suffix = hash_obj.hexdigest()[:6]
                    leader_user_id = f"user-{user_suffix}"

                # Check user exists, create if needed
                leader_user_result = fetch_one("SELECT COUNT(*) as count FROM users WHERE user_id = ?", (leader_user_id,))
                if not leader_user_result or leader_user_result['count'] == 0:
                    # Create a persona that looks like a normal user
                    fake_persona = {
                        "name": f"User{user_suffix}",
                        "type": "leader",  # Internal marker
                        "profession": "Various",
                        "age_range": "30-50",
                        "personality_traits": ["Thoughtful", "Rational", "Leader"],
                        "agent_role": "leader",
                        "is_system_agent": True
                    }
                    
                    execute_query('''
                        INSERT INTO users (user_id, persona, background_labels, creation_time)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        leader_user_id,
                        json.dumps(fake_persona, ensure_ascii=False),
                        '["leader", "opinion_balance", "rational_discussion"]',
                        datetime.now().isoformat()
                    ))

                from multi_model_selector import MultiModelSelector
                # Insert leader comment
                execute_query('''
                    INSERT INTO comments (comment_id, content, post_id, author_id, created_at, num_likes, selected_model, agent_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    comment_id,
                    leader_content,
                    final_target_post_id,
                    leader_user_id,
                    datetime.now().isoformat(),
                    0,  # Initial like count
                    MultiModelSelector.DEFAULT_POOL[0],  # Model used by Leader Agent
                    'leader_agent'
                ))

                # Record comment -> timestep mapping
                try:
                    # Get current time step from SimpleCoordinationSystem
                    current_step = getattr(self, 'current_time_step', None)
                    
                    if current_step is not None:
                        execute_query('''
                            INSERT OR REPLACE INTO comment_timesteps (comment_id, user_id, post_id, time_step)
                            VALUES (?, ?, ?, ?)
                        ''', (comment_id, leader_user_id, final_target_post_id, int(current_step)))
                except Exception as e:
                    # Non-fatal: mapping is best-effort
                    workflow_logger.debug(f"Failed to record leader comment timestep: {e}")

                # Database manager automatically handles transaction commits
                return comment_id

            # Use database manager to execute operation
            result = save_leader_comment_operation()
            if not result:
                workflow_logger.error("❌ Leader comment save failed")
                return None
            
            if result:
                # Trigger auto export
                try:
                    try:
                        from src.auto_export_manager import on_comment_created
                    except ImportError:
                        from auto_export_manager import on_comment_created
                    import hashlib
                    seed = f'leader_agent_{action_id}_{datetime.now().strftime("%Y%m%d")}'
                    user_id = f"user-{hashlib.md5(seed.encode()).hexdigest()[:6]}"
                    on_comment_created(result, user_id)
                except Exception as e:
                    workflow_logger.info(f"   ⚠️  Leader comment auto-export failed: {e}")

                # Trigger scenario class export
                try:
                    try:
                        from src.scenario_export_manager import on_comment_created_scenario
                    except ImportError:
                        from scenario_export_manager import on_comment_created_scenario
                    import hashlib
                    seed = f'leader_agent_{action_id}_{datetime.now().strftime("%Y%m%d")}'
                    user_id = f"user-{hashlib.md5(seed.encode()).hexdigest()[:6]}"
                    on_comment_created_scenario(result, user_id)
                except Exception as e:
                    workflow_logger.info(f"   ⚠️  Leader comment scenario export failed: {e}")

                return result
            else:
                return None

        except Exception as e:
            workflow_logger.info(f"❌ Leader Agent comment save failed: {e}")
            import traceback
            workflow_logger.info(f"Error details: {traceback.format_exc()}")
            return None

    async def _amplifier_agents_like_leader_comment(self, leader_comment_id: str, amplifier_responses: List[Dict[str, Any]], leader_comment_id_2: Optional[str] = None) -> int:
        """amplifier agents like leader comments (like both leader comments)"""
        try:
            from datetime import datetime
            import hashlib

            successful_likes = 0
            
            def like_leader_comment_operation():
                nonlocal successful_likes

                # Verify first leader comment exists (use detailed query for debugging)
                comment_result = fetch_one("SELECT comment_id, post_id FROM comments WHERE comment_id = ?", (leader_comment_id,))
                if not comment_result:
                    workflow_logger.warning(f"  ⚠️  Leader comment {leader_comment_id} does not exist")
                    # Try to find other leader comments (may have been saved to fallback post)
                    all_leader_comments = fetch_all("SELECT comment_id, post_id FROM comments WHERE agent_type = 'leader_agent' ORDER BY created_at DESC LIMIT 5")
                    if all_leader_comments:
                        workflow_logger.info(f"  📋 Found {len(all_leader_comments)} leader comments, but target comment {leader_comment_id} is not among them")
                        workflow_logger.info("  💡 Possible reason: comment saved to fallback post, but query used original post ID")
                    return 0

                # For each successful amplifier response, increment likes on both leader comments
                for i, response in enumerate(amplifier_responses):
                    if response.get("success") and "response" in response:
                        try:
                            # Like the first leader comment
                            execute_query('''
                                UPDATE comments
                                SET num_likes = num_likes + 1
                                WHERE comment_id = ?
                            ''', (leader_comment_id,))
                            
                            # If second leader comment exists, like it too
                            if leader_comment_id_2:
                                execute_query('''
                                    UPDATE comments
                                    SET num_likes = num_likes + 1
                                    WHERE comment_id = ?
                                ''', (leader_comment_id_2,))

                            successful_likes += 1

                        except Exception as e:
                            workflow_logger.info(f"    ⚠️  amplifier Agent {i+1} like failed: {e}")
                            continue

                # Database manager automatically handles transaction commits
                return successful_likes

            # Use database manager to execute operation
            result = like_leader_comment_operation()
            if not result:
                workflow_logger.error("❌ Like operation failed")
                return 0
            
            if result and result > 0:
                self._verify_leader_comment_likes(leader_comment_id, result)

            return result or 0

        except Exception as e:
            workflow_logger.info(f"❌ amplifier Agent like operation failed: {e}")
            return 0

    def _verify_leader_comment_likes(self, leader_comment_id: str, expected_likes: int):
        """Verify leader comment likes increased correctly"""
        try:
            
            def verify_likes_operation():
                result = fetch_one('SELECT num_likes FROM comments WHERE comment_id = ?', (leader_comment_id,))
                if result:
                    actual_likes = result['num_likes']
                    workflow_logger.info(f"  📊 Leader comment {leader_comment_id} current likes: {actual_likes}")
                    return actual_likes
                else:
                    workflow_logger.info(f"  ❌ Leader comment {leader_comment_id} not found")
                    return 0

            # Use database manager to execute operation
            actual_likes = verify_likes_operation()
            return actual_likes

        except Exception as e:
            workflow_logger.info(f"  ❌ Failed to verify like count: {e}")
            return 0

    def _add_bulk_likes_to_leader_comments(self, leader_comment_id_1: Optional[str], leader_comment_id_2: Optional[str], amplifier_agent_count: int):
        """Add bulk likes to both leader comments based on amplifier agent count (count * 20)"""
        try:
            workflow_logger.info(f"  🔍 Bulk like method called: leader_comment_id_1={leader_comment_id_1}, leader_comment_id_2={leader_comment_id_2}, amplifier_agent_count={amplifier_agent_count}")
            
            if amplifier_agent_count <= 0:
                workflow_logger.warning("  ⚠️ amplifier_agent_count <= 0, skipping bulk likes")
                return
            
            additional_likes = amplifier_agent_count * 20
            workflow_logger.info(f"  📊 Calculated bulk likes: {amplifier_agent_count} * 20 = {additional_likes}")
            
            def add_bulk_likes_operation():
                likes_added = 0
                
                # Add likes to first leader comment
                if leader_comment_id_1:
                    try:
                        workflow_logger.info(f"  🔄 Adding {additional_likes} likes to first leader comment {leader_comment_id_1}...")
                        # Query current likes
                        before_result = fetch_one('SELECT num_likes FROM comments WHERE comment_id = ?', (leader_comment_id_1,))
                        before_likes = before_result['num_likes'] if before_result else 0
                        workflow_logger.info(f"  📊 First leader comment likes before: {before_likes}")
                        
                        # Perform database update
                        update_success = execute_query('''
                            UPDATE comments
                            SET num_likes = num_likes + ?
                            WHERE comment_id = ?
                        ''', (additional_likes, leader_comment_id_1))
                        
                        if not update_success:
                            workflow_logger.warning("  ⚠️ execute_query returned False, database update may have failed")
                            raise Exception(f"execute_query returned False, unable to update likes for comment {leader_comment_id_1}")
                        
                        # Verify likes after update
                        after_result = fetch_one('SELECT num_likes FROM comments WHERE comment_id = ?', (leader_comment_id_1,))
                        after_likes = after_result['num_likes'] if after_result else 0
                        actual_increment = after_likes - before_likes
                        workflow_logger.info(f"  📊 First leader comment likes after: {after_likes} (added {actual_increment})")
                        
                        # Verify actual like increment
                        if actual_increment != additional_likes:
                            workflow_logger.warning(f"  ⚠️ Like increment mismatch! Expected: {additional_likes}, actual: {actual_increment}")
                        else:
                            likes_added += 1
                            workflow_logger.info(f"  ✅ Added {additional_likes} likes to first leader comment {leader_comment_id_1} (amplifier_agent_count: {amplifier_agent_count})")
                    except Exception as e:
                        workflow_logger.warning(f"  ⚠️ Failed to add likes to first leader comment: {e}")
                        import traceback
                        workflow_logger.warning(f"  ⚠️ Error details: {traceback.format_exc()}")
                else:
                    workflow_logger.warning("  ⚠️ leader_comment_id_1 is empty, skipping first leader comment")
                
                # Add likes to second leader comment
                if leader_comment_id_2:
                    try:
                        workflow_logger.info(f"  🔄 Adding {additional_likes} likes to second leader comment {leader_comment_id_2}...")
                        # Query current likes
                        before_result = fetch_one('SELECT num_likes FROM comments WHERE comment_id = ?', (leader_comment_id_2,))
                        before_likes = before_result['num_likes'] if before_result else 0
                        workflow_logger.info(f"  📊 Second leader comment likes before: {before_likes}")
                        
                        # Perform database update
                        update_success = execute_query('''
                            UPDATE comments
                            SET num_likes = num_likes + ?
                            WHERE comment_id = ?
                        ''', (additional_likes, leader_comment_id_2))
                        
                        if not update_success:
                            workflow_logger.warning("  ⚠️ execute_query returned False, database update may have failed")
                            raise Exception(f"execute_query returned False, unable to update likes for comment {leader_comment_id_2}")
                        
                        # Verify likes after update
                        after_result = fetch_one('SELECT num_likes FROM comments WHERE comment_id = ?', (leader_comment_id_2,))
                        after_likes = after_result['num_likes'] if after_result else 0
                        actual_increment = after_likes - before_likes
                        workflow_logger.info(f"  📊 Second leader comment likes after: {after_likes} (added {actual_increment})")
                        
                        # Verify actual like increment
                        if actual_increment != additional_likes:
                            workflow_logger.warning(f"  ⚠️ Like increment mismatch! Expected: {additional_likes}, actual: {actual_increment}")
                        else:
                            likes_added += 1
                            workflow_logger.info(f"  ✅ Added {additional_likes} likes to second leader comment {leader_comment_id_2} (amplifier_agent_count: {amplifier_agent_count})")
                    except Exception as e:
                        workflow_logger.warning(f"  ⚠️ Failed to add likes to second leader comment: {e}")
                        import traceback
                        workflow_logger.warning(f"  ⚠️ Error details: {traceback.format_exc()}")
                else:
                    workflow_logger.warning("  ⚠️ leader_comment_id_2 is empty, skipping second leader comment")
                
                return likes_added
            
            # Use database manager to execute operation
            workflow_logger.info("  🔄 Starting bulk like database operation...")
            result = add_bulk_likes_operation()
            workflow_logger.info(f"  📊 Bulk like operation result: {result}")
            
            if result > 0:
                workflow_logger.info(f"  💖 Successfully added {additional_likes} likes to each of {result} leader comments (total: {result * additional_likes} likes)")
            else:
                workflow_logger.warning(f"  ⚠️ Failed to add bulk likes to any leader comments (result={result})")
            
        except Exception as e:
            workflow_logger.warning(f"  ⚠️ Bulk like operation failed: {e}")
            import traceback
            workflow_logger.warning(f"  ⚠️ Error details: {traceback.format_exc()}")

    async def _get_baseline_data_with_analyst(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get baseline data and run analyst analysis (phase 3 integrates phase 1)"""
        try:
            workflow_logger.info("    📊 Fetching baseline data and starting analyst analysis...")

            # Use global database manager, cursor no longer needed

            # Get target post and comments
            result = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts
                WHERE post_id = ?
            """, (target_post_id,))

            post_data = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts WHERE post_id = ?
            """, (target_post_id,))
            if not post_data:
                workflow_logger.info(f"    ⚠️  Target post not found: {target_post_id}")
                return {"error": "Target post does not exist"}

            post_id, content, author_id, created_at, num_likes, num_comments, num_shares = post_data

            # Get first 4 comments (sorted by creation time)
            result = fetch_one("""
                SELECT comment_id, content, author_id, num_likes, created_at
                FROM comments
                WHERE post_id = ?
                ORDER BY created_at ASC
                LIMIT 4
            """, (target_post_id,))

            comments_data = fetch_all("""
                SELECT comment_id, content, author_id, created_at, num_likes
                FROM comments WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (target_post_id,))

            # Build analyst input data
            baseline_content = {
                "post": {
                    "post_id": post_id,
                    "content": content,
                    "author_id": author_id,
                    "num_likes": num_likes,
                    "num_comments": num_comments,
                    "num_shares": num_shares,
                    "created_at": created_at
                },
                "comments": []
            }

            for comment_data in comments_data:
                comment_id, comment_content, comment_author_id, comment_likes, comment_created_at = comment_data
                baseline_content["comments"].append({
                    "comment_id": comment_id,
                    "content": comment_content,
                    "author_id": comment_author_id,
                    "num_likes": comment_likes,
                    "created_at": comment_created_at
                })

            # Build formatted analysis content (same as phase 1)
            formatted_content = f"Post content: {content}\n\nComments:\n"
            for i, comment in enumerate(baseline_content["comments"], 1):
                formatted_content += f"Comment {i}: {comment['content']}\n"

            # Run analyst baseline analysis (same mechanism as phase 1)
            if hasattr(self, 'analyst') and self.analyst:
                workflow_logger.info("    🔍 Starting analyst baseline analysis...")

                analyst_result = await self.analyst.analyze_content({
                    "content": formatted_content,
                    "analysis_type": "baseline_analysis",
                    "post_id": target_post_id,
                    "stage": "third_stage_baseline"
                })

                if analyst_result.get("success"):
                    analysis_data = analyst_result.get("analysis", {})
                    workflow_logger.info("    ✅ Analyst baseline analysis completed")

                    # Record baseline analysis result
                    baseline_data = {
                        "raw_data": baseline_content,
                        "analyst_analysis": {
                            "core_viewpoints": analysis_data.get("core_viewpoints", []),
                            "extremism_score": analysis_data.get("extremism_score", 0),
                            "sentiment_score": analysis_data.get("sentiment_score", 0),
                            "analysis_summary": analysis_data.get("summary", ""),
                            "timestamp": created_at
                        },
                        "engagement_metrics": {
                            "likes": num_likes,
                            "comments": num_comments,
                            "shares": num_shares
                        }
                    }

                    workflow_logger.info(f"    📋 Baseline extremism score: {analysis_data.get('extremism_score', 0)}")
                    workflow_logger.info(f"    📋 Baseline sentiment score: {analysis_data.get('sentiment_score', 0)}")

                    return baseline_data
                else:
                    workflow_logger.info(f"    ⚠️  Analyst baseline analysis failed: {analyst_result.get('error', 'unknown error')}")

            # If analyst unavailable, return traditional baseline data
            workflow_logger.info("    ⚠️  Analyst unavailable, using traditional baseline data")
            return {
                "raw_data": baseline_content,
                "engagement_metrics": {
                    "likes": num_likes,
                    "comments": num_comments,
                    "shares": num_shares
                },
                "fallback": True
            }

        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to get baseline data: {e}")
            return {"error": str(e)}

    async def _build_updated_content_for_analysis(self, target_post_id: str, action_id: str) -> str:
        """Build full content with original post + updated hot comments for secondary analysis"""
        try:
            # Use database manager, no need to check connection
            
            # Use global database manager, cursor no longer needed
            
            # Get original post content
            result = fetch_one("""
                SELECT content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts
                WHERE post_id = ?
            """, (target_post_id,))
            
            post_data = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts WHERE post_id = ?
            """, (target_post_id,))
            if not post_data:
                return "Original post content: [post does not exist]"
            
            content, author_id, created_at, num_likes, num_comments, num_shares = post_data
            
            # Get hot comments (sorted by likes, top 10)
            result = fetch_one("""
                SELECT content, author_id, num_likes, created_at, is_agent_response
                FROM comments
                WHERE post_id = ?
                ORDER BY num_likes DESC, created_at DESC
                LIMIT 10
            """, (target_post_id,))
            
            comments_data = fetch_all("""
                SELECT comment_id, content, author_id, created_at, num_likes
                FROM comments WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (target_post_id,))
            
            # Build full content
            updated_content = f"Original post content: {content}\n"
            updated_content += f"Post stats: likes {num_likes}, comments {num_comments}, shares {num_shares}\n\n"
            updated_content += "Hot comments:\n"
            
            for i, (comment_content, comment_author, comment_likes, comment_created, is_agent) in enumerate(comments_data, 1):
                agent_tag = " [Balance Agent]" if is_agent else ""
                updated_content += f"{i}. {comment_content} (likes: {comment_likes}){agent_tag}\n"
            
            workflow_logger.info(f"    📝 Updated content built, includes {len(comments_data)} hot comments")
            return updated_content
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to build updated content: {e}")
            return "Original post content: [build failed]\n\nHot comments:\n[unable to fetch comment data]"

    async def _get_baseline_data_with_analyst_and_extremism(self, target_post_id: str, action_id: str, content_text: str = None) -> Dict[str, Any]:
        """Get baseline data (analyst analysis + viewpoint extremism) - reused in phase 1 and 3"""
        try:
            if content_text is None:
                # Phase 1: get original content for baseline analysis
                workflow_logger.info("    📊 Phase 1: fetch original content for baseline analysis...")
                content_text = await self._build_updated_content_for_analysis(target_post_id, action_id)
            
            # Use analyst for analysis
            analysis_result = await self.analyst.analyze_content(content_text, target_post_id)
            
            if not analysis_result.get("success"):
                workflow_logger.info("    ⚠️ Analyst analysis failed, using fallback method")
                return await self._get_fallback_baseline_data(target_post_id, action_id)
            
            analysis_data = analysis_result.get("analysis", {})
            
            # Calculate viewpoint extremism
            viewpoint_extremism_raw = await self._calculate_overall_viewpoint_extremism(content_text, target_post_id)
            viewpoint_extremism = self._normalize_extremism_score(viewpoint_extremism_raw)
            
            # Get sentiment distribution
            sentiment_distribution = analysis_data.get('sentiment_distribution', {})
            sentiment_score = analysis_data.get('sentiment_score', 0.5)
            
            baseline_data = {
                "success": True,
                "analysis": analysis_data,
                "viewpoint_extremism": viewpoint_extremism,
                "sentiment_score": sentiment_score,
                "sentiment_distribution": sentiment_distribution,
                "content_analyzed": content_text[:200] + "..." if len(content_text) > 200 else content_text,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            workflow_logger.info("    ✅ Baseline data analysis completed:")
            workflow_logger.info(f"       Viewpoint extremism: {viewpoint_extremism:.2f}/1.0")
            workflow_logger.info(f"       Sentiment score: {sentiment_score:.2f}")
            workflow_logger.info(f"       Sentiment distribution: positive {sentiment_distribution.get('positive', 0):.1%}, negative {sentiment_distribution.get('negative', 0):.1%}")
            
            return baseline_data
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to get baseline data: {e}")
            return await self._get_fallback_baseline_data(target_post_id, action_id)

    async def _get_fallback_baseline_data(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get fallback baseline data"""
        return {
            "success": False,
            "analysis": {},
            "viewpoint_extremism": 0.5,
            "sentiment_score": 0.5,
            "sentiment_distribution": {"positive": 0.3, "negative": 0.3, "neutral": 0.4},
            "content_analyzed": "fallback data",
            "analysis_timestamp": datetime.now().isoformat(),
            "fallback": True
        }

    def _get_fallback_core_viewpoint(self, target_post_id: str) -> str:
        """Get fallback core viewpoint"""
        try:
            # Try to get basic post info from database
            from utils import Utils
            db_manager = Utils.get_db_manager()
            
            if db_manager:
                # Query post content
                query = "SELECT content FROM posts WHERE post_id = %s"
                result = db_manager.execute_query(query, (target_post_id,))
                
                if result and len(result) > 0:
                    content = result[0][0]
                    # Do not truncate: the UI can scroll and needs full context.
                    if content and len(content) > 0:
                        return content
        except Exception as e:
            workflow_logger.warning(f"Failed to get fallback core viewpoint: {e}")
        
        # Return default core viewpoint
        return f"Discussion about post {target_post_id}"

    def _get_fallback_post_theme(self, target_post_id: str) -> str:
        """Get fallback post theme"""
        try:
            # Try to get post theme from database
            from utils import Utils
            db_manager = Utils.get_db_manager()
            
            if db_manager:
                # Query post theme
                query = "SELECT theme FROM posts WHERE post_id = %s"
                result = db_manager.execute_query(query, (target_post_id,))
                
                if result and len(result) > 0:
                    theme = result[0][0]
                    if theme and theme.strip():
                        return theme
        except Exception as e:
            workflow_logger.warning(f"Failed to get fallback post theme: {e}")
        
        # Return default theme
        return "General discussion"

    async def _evaluate_improvement(self, extremism_improvement: float, sentiment_improvement: float,
                                   baseline_sentiment_dist: Dict, secondary_sentiment_dist: Dict,
                                   engagement_change: float) -> Dict[str, Any]:
        """Evaluate whether there is improvement"""
        try:
            has_improvement = False
            urgency_level = 1
            reasons = []
            
            # 1. Extremism improvement evaluation
            if extremism_improvement >= 1.0:
                has_improvement = True
                reasons.append(f"Significant extremism improvement ({extremism_improvement:+.1f})")
            elif extremism_improvement >= 0.5:
                has_improvement = True
                reasons.append(f"Some extremism improvement ({extremism_improvement:+.1f})")
            elif extremism_improvement < -0.5:
                urgency_level = max(urgency_level, 3)
                reasons.append(f"Extremism worsened ({extremism_improvement:+.1f})")
            elif extremism_improvement < 0:
                urgency_level = max(urgency_level, 2)
                reasons.append(f"No extremism improvement ({extremism_improvement:+.1f})")
            
            # 2. Sentiment improvement evaluation
            if sentiment_improvement >= 0.1:
                has_improvement = True
                reasons.append(f"Significant sentiment improvement ({sentiment_improvement:+.2f})")
            elif sentiment_improvement >= 0.05:
                has_improvement = True
                reasons.append(f"Some sentiment improvement ({sentiment_improvement:+.2f})")
            elif sentiment_improvement < -0.1:
                urgency_level = max(urgency_level, 3)
                reasons.append(f"Sentiment worsened ({sentiment_improvement:+.2f})")
            elif sentiment_improvement < 0:
                urgency_level = max(urgency_level, 2)
                reasons.append(f"No sentiment improvement ({sentiment_improvement:+.2f})")
            
            # 3. Sentiment distribution improvement evaluation
            baseline_positive = baseline_sentiment_dist.get('positive', 0)
            secondary_positive = secondary_sentiment_dist.get('positive', 0)
            positive_change = secondary_positive - baseline_positive
            
            baseline_negative = baseline_sentiment_dist.get('negative', 0)
            secondary_negative = secondary_sentiment_dist.get('negative', 0)
            negative_change = baseline_negative - secondary_negative  # Less negative is good
            
            if positive_change >= 0.1 or negative_change >= 0.1:
                has_improvement = True
                reasons.append(f"Sentiment distribution improved (positive +{positive_change:.1%}, negative -{negative_change:.1%})")
            elif positive_change < -0.1 or negative_change < -0.1:
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Sentiment distribution worsened (positive {positive_change:+.1%}, negative {negative_change:+.1%})")
            
            # 4. Engagement evaluation
            if engagement_change > 50:
                has_improvement = True
                reasons.append(f"Engagement grew significantly ({engagement_change:+.1f}%)")
            elif engagement_change < -20:
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Engagement decreased ({engagement_change:+.1f}%)")
            
            # 5. Overall evaluation
            if not has_improvement and len(reasons) >= 2:
                urgency_level = min(urgency_level + 1, 4)
            
            return {
                "has_improvement": has_improvement,
                "urgency_level": urgency_level,
                "reason": "; ".join(reasons) if reasons else "No clear improvement",
                "improvement_details": {
                    "extremism_improvement": extremism_improvement,
                    "sentiment_improvement": sentiment_improvement,
                    "positive_change": positive_change,
                    "negative_change": negative_change,
                    "engagement_change": engagement_change,
                    "trigger_count": len(reasons)
                }
            }
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Improvement evaluation failed: {e}")
            return {
                "has_improvement": False,
                "urgency_level": 2,
                "reason": f"Evaluation failed: {str(e)}",
                "improvement_details": {}
            }

    async def _evaluate_secondary_intervention_need(self, extremism: float, sentiment: float, 
                                                   positive_ratio: float, negative_ratio: float, neutral_ratio: float,
                                                   engagement_change: float, baseline_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Enhanced secondary intervention need evaluation combining sentiment distribution and engagement data"""
        try:
            extremism = self._normalize_extremism_score(extremism)
            needs_intervention = False
            urgency_level = 1
            reasons = []
            
            # 1. Extremism evaluation
            if extremism >= 0.7:
                needs_intervention = True
                urgency_level = max(urgency_level, 3)
                reasons.append(f"Viewpoint extremism too high ({extremism:.2f}/1.0)")
            elif extremism >= 0.5:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Viewpoint extremism high ({extremism:.2f}/1.0)")
            
            # 2. Sentiment distribution evaluation
            if negative_ratio >= 0.6:
                needs_intervention = True
                urgency_level = max(urgency_level, 3)
                reasons.append(f"Negative sentiment ratio too high ({negative_ratio:.1%})")
            elif negative_ratio >= 0.4 and positive_ratio < 0.2:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Negative sentiment dominates ({negative_ratio:.1%} negative vs {positive_ratio:.1%} positive)")
            
            # 3. Overall sentiment evaluation
            if sentiment <= 0.2:
                needs_intervention = True
                urgency_level = max(urgency_level, 3)
                reasons.append(f"Overall sentiment too low ({sentiment:.2f})")
            elif sentiment <= 0.3:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Overall sentiment low ({sentiment:.2f})")
            
            # 4. Engagement anomaly evaluation
            if engagement_change < -30:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Engagement dropped significantly ({engagement_change:+.1f}%)")
            elif engagement_change > 200 and negative_ratio > 0.3:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"High engagement but high negative ratio ({engagement_change:+.1f}% engagement, {negative_ratio:.1%} negative)")
            
            # 5. Sentiment deterioration evaluation
            baseline_sentiment = baseline_data.get('sentiment_score', 0.5)
            if sentiment < baseline_sentiment - 0.2:
                needs_intervention = True
                urgency_level = max(urgency_level, 2)
                reasons.append(f"Sentiment worsened significantly (baseline {baseline_sentiment:.2f} -> current {sentiment:.2f})")
            
            # 6. Overall evaluation
            if len(reasons) >= 2:
                urgency_level = min(urgency_level + 1, 4)
            
            return {
                "needs_intervention": needs_intervention,
                "urgency_level": urgency_level,
                "reason": "; ".join(reasons) if reasons else "No intervention needed",
                "assessment_details": {
                    "extremism": extremism,
                    "sentiment": sentiment,
                    "sentiment_distribution": {
                        "positive": positive_ratio,
                        "negative": negative_ratio,
                        "neutral": neutral_ratio
                    },
                    "engagement_change": engagement_change,
                    "trigger_count": len(reasons)
                }
            }
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Secondary intervention need evaluation failed: {e}")
            return {
                "needs_intervention": False,
                "urgency_level": 1,
                "reason": f"Evaluation failed: {str(e)}",
                "assessment_details": {}
            }

    async def _smart_cleanup_ineffective_strategies(self, action_id: str, intervention_info: Dict[str, Any]):
        """Smart cleanup of ineffective strategies, considering time and context"""
        try:
            workflow_logger.info("    🗑️ Smart cleanup of ineffective strategies in action_logs database...")
            
            # Use database manager to check if table exists
            from pathlib import Path
            from datetime import datetime, timedelta
            
            # Check if action_logs table exists
            table_result = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='action_logs'")
            if not table_result:
                workflow_logger.info("    📊 action_logs table does not exist, no cleanup needed")
                return
            
            # Query records related to current action_id
            result = fetch_one("""
                SELECT id, action_id, effectiveness_score, success, created_at, strategy_type, context
                FROM action_logs 
                WHERE action_id = ?
                ORDER BY created_at DESC
            """, (action_id,))
            
            related_records = fetch_all("""
                SELECT id, action_id, timestamp, success, effectiveness_score, 
                       situation_context, strategic_decision, execution_details, 
                       lessons_learned, full_log
                FROM action_logs 
                WHERE action_id = ?
            """, (action_id,))
            
            if not related_records:
                workflow_logger.info(f"    📊 No records found related to action_id {action_id}")
                # Database manager handles connection closing automatically
                return
            
            # Identify ineffective strategies intelligently
            invalid_records = []
            backup_records = []
            
            for record in related_records:
                record_id, record_action_id, effectiveness_score, success, created_at, strategy_type, context = record
                
                # Parse creation time
                try:
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_since_creation = datetime.now() - created_time.replace(tzinfo=None)
                except:
                    time_since_creation = timedelta(hours=1)  # Default 1 hour ago
                
                # Decide whether to delete
                should_delete = False
                delete_reason = ""
                
                # 1. Effectiveness score too low and enough time elapsed
                if effectiveness_score < 3.0 and time_since_creation > timedelta(hours=2):
                    should_delete = True
                    delete_reason = f"Effectiveness score too low ({effectiveness_score}) and time sufficient ({time_since_creation})"
                
                # 2. Execution failed and enough time elapsed
                elif not success and time_since_creation > timedelta(hours=1):
                    should_delete = True
                    delete_reason = f"Execution failed and time sufficient ({time_since_creation})"
                
                # 3. Moderate score but very old and high-urgency intervention needed
                elif (effectiveness_score < 5.0 and time_since_creation > timedelta(hours=4) and 
                      intervention_info.get('urgency_level', 1) >= 3):
                    should_delete = True
                    delete_reason = f"Moderate effectiveness but too old ({time_since_creation}) and high urgency needed"
                
                # 4. Strategy type mismatch with current intervention need
                elif (strategy_type and intervention_info.get('assessment_details', {}).get('trigger_count', 0) >= 2):
                    # If multiple intervention types are needed, delete mismatched strategies
                    if 'emotional' in intervention_info.get('reason', '') and 'balance' not in (strategy_type or ''):
                        should_delete = True
                        delete_reason = f"Strategy type mismatch with current need ({strategy_type})"
                
                if should_delete:
                    # Back up important info first
                    backup_records.append({
                        'id': record_id,
                        'action_id': record_action_id,
                        'effectiveness_score': effectiveness_score,
                        'success': success,
                        'created_at': created_at,
                        'strategy_type': strategy_type,
                        'delete_reason': delete_reason
                    })
                    invalid_records.append(record_id)
            
            if not invalid_records:
                workflow_logger.info("    ✅ No strategy records need cleanup")
                # Database manager handles connection closing automatically
                return
            
            # Save backup info
            if backup_records:
                backup_file = f"logs/strategy_cleanup_backup_{action_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                import json
                import os
                os.makedirs("logs", exist_ok=True)
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_records, f, indent=2, ensure_ascii=False, default=str)
                workflow_logger.info(f"    📁 Strategy cleanup backup saved: {backup_file}")
            
            # Delete ineffective strategy records
            placeholders = ','.join(['?' for _ in invalid_records])
            execute_query(f"""
                DELETE FROM action_logs 
                WHERE id IN ({placeholders})
            """, invalid_records)
            
            deleted_count = len(invalid_records)
            
            workflow_logger.info(f"    ✅ Deleted {deleted_count} ineffective strategy records from action_logs database")
            workflow_logger.info(f"    📊 Deleted record IDs: {invalid_records}")
            workflow_logger.info(f"    📋 Delete reasons: {[r['delete_reason'] for r in backup_records]}")
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Smart cleanup of action_logs ineffective strategies failed: {e}")
            import traceback
            workflow_logger.info(f"    📊 Error details: {traceback.format_exc()}")

    async def _cleanup_ineffective_strategies(self, action_id: str):
        """Delete ineffective strategy records from action_logs database table"""
        try:
            workflow_logger.info("    🗑️ Cleaning ineffective strategies in action_logs database...")
            
            # Connect to action_logs database
            import sqlite3
            from pathlib import Path
            
            action_logs_db_path = Path("database/rags.db")
            
            # Ensure database directory exists
            action_logs_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If database does not exist, return
            if not action_logs_db_path.exists():
                workflow_logger.info("    📊 action_logs database does not exist, no cleanup needed")
                return
            
            conn = sqlite3.connect(action_logs_db_path)
            cursor = conn.cursor()
            
            # Check if action_logs table exists
            table_result = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='action_logs'")
            if not table_result:
                workflow_logger.info("    📊 action_logs table does not exist, no cleanup needed")
                # Database manager handles connection closing automatically
                return
            
            # Query records related to current action_id
            result = fetch_one("""
                SELECT id, action_id, effectiveness_score, success, created_at
                FROM action_logs 
                WHERE action_id = ?
            """, (action_id,))
            
            related_records = fetch_all("""
                SELECT id, action_id, timestamp, success, effectiveness_score, 
                       situation_context, strategic_decision, execution_details, 
                       lessons_learned, full_log
                FROM action_logs 
                WHERE action_id = ?
            """, (action_id,))
            
            if not related_records:
                workflow_logger.info(f"    📊 No records found related to action_id {action_id}")
                # Database manager handles connection closing automatically
                return
            
            # Identify ineffective strategies (score < 5.0 or success is False)
            invalid_records = []
            for record in related_records:
                record_id, record_action_id, effectiveness_score, success, created_at = record
                if effectiveness_score < 5.0 or not success:
                    invalid_records.append(record_id)
            
            if not invalid_records:
                workflow_logger.info("    ✅ No ineffective strategy records found")
                # Database manager handles connection closing automatically
                return
            
            # Delete ineffective strategy records
            placeholders = ','.join(['?' for _ in invalid_records])
            execute_query(f"""
                DELETE FROM action_logs 
                WHERE id IN ({placeholders})
            """, invalid_records)
            
            deleted_count = len(invalid_records)
            
            workflow_logger.info(f"    ✅ Deleted {deleted_count} ineffective strategy records from action_logs database")
            workflow_logger.info(f"    📊 Deleted record IDs: {invalid_records}")
            
        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to clean ineffective strategies in action_logs database: {e}")
            import traceback
            workflow_logger.info(f"    📊 Error details: {traceback.format_exc()}")

    async def _execute_secondary_intervention(self, strategy_result: Dict[str, Any], target_post_id: str, action_id: str):
        """Execute secondary intervention strategy"""
        try:
            workflow_logger.info("    🎯 Executing secondary intervention strategy...")
            
            strategy = strategy_result.get("strategy", {})
            agent_instructions = strategy_result.get("agent_instructions", {})
            
            # Display secondary intervention strategy details
            workflow_logger.info("    📋 Secondary intervention strategy details:")
            workflow_logger.info(f"       Strategy ID: {strategy.get('strategy_id', 'unknown')}")
            workflow_logger.info(f"       Core argument: {strategy.get('core_counter_argument', 'balanced perspective')}")
            
            # Generate secondary intervention content
            content_result = await self.leader.generate_strategic_content(
                strategy, 
                f"Original post ID: {target_post_id}\nSecondary intervention content generation"
            )
            
            if content_result.get("success"):
                leader_content = content_result["content"]
                final_content = leader_content.get("final_content", "")
                
                workflow_logger.info("    ✅ Secondary intervention content generated")
                workflow_logger.info(f"    👑 Secondary intervention leader content: {final_content}")
                
                # Save secondary intervention comment to database
                secondary_comment_id = self._save_leader_comment_to_database(final_content, target_post_id, f"{action_id}_secondary")
                if secondary_comment_id:
                    workflow_logger.info(f"    💬 Secondary intervention comment ID: {secondary_comment_id}")
                    
                    # Execute secondary amplifier Agent responses
                    amplifier_plan = strategy.get('amplifier_plan', {})
                    enhanced_amplifier_plan = amplifier_plan.copy()
                    enhanced_amplifier_plan["agent_instructions"] = agent_instructions.get("amplifier_instructions", [])
                    enhanced_amplifier_plan["coordination_strategy"] = agent_instructions.get("coordination_strategy", "secondary_coordination")
                    
                    workflow_logger.info("    🤖 Launching secondary amplifier Agent cluster...")
                    secondary_amplifier_responses = await self._coordinate_amplifier_agents(
                        final_content,
                        enhanced_amplifier_plan,
                        target_post_id
                    )
                    
                    workflow_logger.info(f"    ✅ Secondary amplifier responses completed: {len(secondary_amplifier_responses)} responses")
                    
                    # Secondary amplifier Agents like secondary leader comment
                    if secondary_amplifier_responses:
                        workflow_logger.info("    💖 Secondary amplifier Agents like secondary leader comment...")
                        likes_count = await self._amplifier_agents_like_leader_comment(secondary_comment_id, secondary_amplifier_responses)
                        if likes_count > 0:
                            workflow_logger.info(f"    ✅ {likes_count} secondary amplifier Agents successfully liked")
                    
                    workflow_logger.info("    🎉 Secondary intervention strategy executed")
                else:
                    workflow_logger.info("    ⚠️ Secondary intervention comment save failed")
            else:
                workflow_logger.info(f"    ❌ Secondary intervention content generation failed: {content_result.get('error', 'unknown error')}")
                
        except Exception as e:
            workflow_logger.info(f"    ❌ Secondary intervention strategy execution failed: {e}")

    async def _get_current_data_with_analyst(self, target_post_id: str, action_id: str) -> Dict[str, Any]:
        """Get current data and run analyst analysis (phase 3 integrates phase 1)"""
        try:
            workflow_logger.info("    📊 Fetching current data and starting analyst analysis...")

            # Use global database manager, cursor no longer needed

            # Get current state of target post
            result = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts
                WHERE post_id = ?
            """, (target_post_id,))

            post_data = fetch_one("""
                SELECT post_id, content, author_id, created_at, num_likes, num_comments, num_shares
                FROM posts WHERE post_id = ?
            """, (target_post_id,))
            if not post_data:
                workflow_logger.info(f"    ⚠️  Target post not found: {target_post_id}")
                return {"error": "Target post does not exist"}

            post_id, content, author_id, created_at, num_likes, num_comments, num_shares = post_data

            # Get all comments for this post (including post-intervention comments)
            result = fetch_one("""
                SELECT comment_id, content, author_id, num_likes, created_at, is_agent_response
                FROM comments
                WHERE post_id = ?
                ORDER BY created_at ASC
            """, (target_post_id,))

            comments_data = fetch_all("""
                SELECT comment_id, content, author_id, created_at, num_likes
                FROM comments WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (target_post_id,))

            # Build current state data
            current_content = {
                "post": {
                    "post_id": post_id,
                    "content": content,
                    "author_id": author_id,
                    "num_likes": num_likes,
                    "num_comments": num_comments,
                    "num_shares": num_shares,
                    "created_at": created_at
                },
                "comments": [],
                "agent_responses": [],
                "total_comments": len(comments_data)
            }

            # Separate normal comments and agent responses
            for comment_data in comments_data:
                comment_id, comment_content, comment_author_id, comment_likes, comment_created_at, is_agent_response = comment_data
                comment_obj = {
                    "comment_id": comment_id,
                    "content": comment_content,
                    "author_id": comment_author_id,
                    "num_likes": comment_likes,
                    "created_at": comment_created_at,
                    "is_agent_response": bool(is_agent_response)
                }

                if is_agent_response:
                    current_content["agent_responses"].append(comment_obj)
                else:
                    current_content["comments"].append(comment_obj)

            # Build formatted analysis content (include all comments)
            formatted_content = f"Post content: {content}\n\nComments:\n"
            all_comments = current_content["comments"] + current_content["agent_responses"]
            for i, comment in enumerate(all_comments, 1):
                agent_tag = " [Balance Agent]" if comment.get("is_agent_response") else ""
                formatted_content += f"Comment {i}{agent_tag}: {comment['content']}\n"

            # Run analyst analysis for current state
            if hasattr(self, 'analyst') and self.analyst:
                workflow_logger.info("    🔍 Starting analyst current-state analysis...")

                analyst_result = await self.analyst.analyze_content({
                    "content": formatted_content,
                    "analysis_type": "current_analysis",
                    "post_id": target_post_id,
                    "stage": "third_stage_current",
                    "intervention_id": action_id
                })

                if analyst_result.get("success"):
                    analysis_data = analyst_result.get("analysis", {})
                    workflow_logger.info("    ✅ Analyst current-state analysis completed")

                    current_data = {
                        "raw_data": current_content,
                        "analyst_analysis": {
                            "core_viewpoints": analysis_data.get("core_viewpoints", []),
                            "extremism_score": analysis_data.get("extremism_score", 0),
                            "sentiment_score": analysis_data.get("sentiment_score", 0),
                            "analysis_summary": analysis_data.get("summary", ""),
                            "timestamp": datetime.now().isoformat()
                        },
                        "engagement_metrics": {
                            "likes": num_likes,
                            "comments": num_comments,
                            "shares": num_shares,
                            "agent_responses_count": len(current_content["agent_responses"])
                        }
                    }

                    workflow_logger.info(f"    📋 Current extremism score: {analysis_data.get('extremism_score', 0)}")
                    workflow_logger.info(f"    📋 Current sentiment score: {analysis_data.get('sentiment_score', 0)}")
                    workflow_logger.info(f"    📋 Agent responses count: {len(current_content['agent_responses'])}")

                    return current_data
                else:
                    workflow_logger.info(f"    ⚠️  Analyst current-state analysis failed: {analyst_result.get('error', 'unknown error')}")

            # If analyst unavailable, return traditional current data
            workflow_logger.info("    ⚠️  Analyst unavailable, using traditional current data")
            return {
                "raw_data": current_content,
                "engagement_metrics": {
                    "likes": num_likes,
                    "comments": num_comments,
                    "shares": num_shares,
                    "agent_responses_count": len(current_content["agent_responses"])
                },
                "fallback": True
            }

        except Exception as e:
            workflow_logger.info(f"    ❌ Failed to get current data: {e}")
            return {"error": str(e)}

    async def _perform_analyst_comparison_analysis(self, baseline_data: Dict[str, Any],
                                                 current_data: Dict[str, Any],
                                                 target_post_id: str) -> Dict[str, Any]:
        """Perform analyst comparison analysis (baseline vs current state)"""
        try:
            workflow_logger.info("    🔬 Performing analyst comparison analysis...")

            # Check for valid analyst data
            baseline_analysis = baseline_data.get("analyst_analysis")
            current_analysis = current_data.get("analyst_analysis")

            if not baseline_analysis or not current_analysis:
                workflow_logger.info("    ⚠️  Missing analyst data, using traditional comparison method")
                return self._fallback_comparison_analysis(baseline_data, current_data)

            # Extremism change analysis
            baseline_extremism = baseline_analysis.get("extremism_score", 0)
            current_extremism = current_analysis.get("extremism_score", 0)
            extremism_change = current_extremism - baseline_extremism

            # Sentiment change analysis
            baseline_sentiment = baseline_analysis.get("sentiment_score", 0)
            current_sentiment = current_analysis.get("sentiment_score", 0)
            sentiment_change = current_sentiment - baseline_sentiment

            # Viewpoint analysis
            baseline_viewpoints = baseline_analysis.get("core_viewpoints", [])
            current_viewpoints = current_analysis.get("core_viewpoints", [])

            # Engagement data changes
            baseline_metrics = baseline_data.get("engagement_metrics", {})
            current_metrics = current_data.get("engagement_metrics", {})

            likes_change = current_metrics.get("likes", 0) - baseline_metrics.get("likes", 0)
            comments_change = current_metrics.get("comments", 0) - baseline_metrics.get("comments", 0)
            agent_responses = current_metrics.get("agent_responses_count", 0)

            # Calculate intervention effectiveness score
            intervention_score = self._calculate_intervention_effectiveness(
                extremism_change, sentiment_change, likes_change, comments_change, agent_responses
            )

            # Generate comparison summary
            if hasattr(self, 'analyst') and self.analyst:
                comparison_prompt = f"""
Please provide a comprehensive analysis of the effectiveness of the following public-opinion balancing intervention:

[Baseline Data]
Extremism score: {baseline_extremism}
Sentiment score: {baseline_sentiment}
Core viewpoints: {', '.join(baseline_viewpoints) if baseline_viewpoints else 'none'}
Engagement: 👍{baseline_metrics.get('likes', 0)} 💬{baseline_metrics.get('comments', 0)} 🔄{baseline_metrics.get('shares', 0)}

[Current Data]
Extremism score: {current_extremism}
Sentiment score: {current_sentiment}
Core viewpoints: {', '.join(current_viewpoints) if current_viewpoints else 'none'}
Engagement: 👍{current_metrics.get('likes', 0)} 💬{current_metrics.get('comments', 0)} 🔄{current_metrics.get('shares', 0)}
Agent responses: {agent_responses}

[Change Metrics]
Extremism change: {extremism_change:+.2f}
Sentiment change: {sentiment_change:+.2f}
Likes change: {likes_change:+d}
Comments change: {comments_change:+d}

Please analyze the intervention effectiveness and provide an overall rating (1-10).
"""

                comparison_result = await self.analyst.analyze_content({
                    "content": comparison_prompt,
                    "analysis_type": "intervention_comparison",
                    "post_id": target_post_id,
                    "stage": "third_stage_comparison"
                })

                if comparison_result.get("success"):
                    comparison_analysis = comparison_result.get("analysis", {})
                    analyst_summary = comparison_analysis.get("summary", "")
                    analyst_score = comparison_analysis.get("effectiveness_score", intervention_score)
                else:
                    analyst_summary = "Analyst comparison analysis failed"
                    analyst_score = intervention_score
            else:
                analyst_summary = "Analyst unavailable, using traditional evaluation"
                analyst_score = intervention_score

            # Build full comparison result
            comparison_data = {
                "baseline_analysis": baseline_analysis,
                "current_analysis": current_analysis,
                "changes": {
                    "extremism_change": extremism_change,
                    "sentiment_change": sentiment_change,
                    "engagement_changes": {
                        "likes_change": likes_change,
                        "comments_change": comments_change,
                        "agent_responses": agent_responses
                    }
                },
                "effectiveness": {
                    "intervention_score": analyst_score,
                    "overall_assessment": self._get_intervention_assessment(analyst_score),
                    "analyst_summary": analyst_summary
                },
                "comparison_timestamp": datetime.now().isoformat()
            }

            workflow_logger.info("    📊 Comparison analysis completed")
            workflow_logger.info(f"    📈 Extremism change: {extremism_change:+.2f}")
            workflow_logger.info(f"    📈 Sentiment change: {sentiment_change:+.2f}")
            workflow_logger.info(f"    📈 Intervention effectiveness score: {analyst_score:.1f}/10")

            return comparison_data

        except Exception as e:
            workflow_logger.info(f"    ❌ Analyst comparison analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_intervention_effectiveness(self, extremism_change: float, sentiment_change: float,
                                            likes_change: int, comments_change: int, agent_responses: int) -> float:
        """Calculate intervention effectiveness score (1-10)"""
        try:
            # Base score
            base_score = 5.0

            # Extremism improvement bonus (lower extremism is good)
            if extremism_change < 0:
                base_score += min(abs(extremism_change) * 2, 2.0)
            else:
                base_score -= min(extremism_change * 1.5, 2.0)

            # Sentiment improvement bonus (higher positive sentiment)
            if sentiment_change > 0:
                base_score += min(sentiment_change * 1.5, 1.5)
            else:
                base_score -= min(abs(sentiment_change) * 1, 1.0)

            # Engagement growth bonus
            if likes_change > 0:
                base_score += min(likes_change * 0.1, 1.0)
            if comments_change > 0:
                base_score += min(comments_change * 0.05, 0.5)

            # Agent response effect
            if agent_responses > 0:
                base_score += min(agent_responses * 0.1, 1.0)

            # Ensure score is within 1-10
            return max(1.0, min(10.0, base_score))

        except Exception:
            return 5.0

    def _get_intervention_assessment(self, score: float) -> str:
        """Get intervention effectiveness assessment based on score"""
        if score >= 8.0:
            return "Excellent - intervention highly effective"
        elif score >= 6.0:
            return "Good - intervention clearly effective"
        elif score >= 4.0:
            return "Fair - intervention effect limited"
        else:
            return "Poor - intervention not effective"

    def _fallback_comparison_analysis(self, baseline_data: Dict[str, Any], current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traditional comparison analysis method (when analyst is unavailable)"""
        try:
            baseline_metrics = baseline_data.get("engagement_metrics", {})
            current_metrics = current_data.get("engagement_metrics", {})

            likes_change = current_metrics.get("likes", 0) - baseline_metrics.get("likes", 0)
            comments_change = current_metrics.get("comments", 0) - baseline_metrics.get("comments", 0)
            agent_responses = current_metrics.get("agent_responses_count", 0)

            # Simple effectiveness score
            effectiveness_score = 5.0
            if likes_change > 0:
                effectiveness_score += min(likes_change * 0.2, 2.0)
            if comments_change > 0:
                effectiveness_score += min(comments_change * 0.1, 1.5)
            if agent_responses > 0:
                effectiveness_score += min(agent_responses * 0.15, 1.5)

            effectiveness_score = max(1.0, min(10.0, effectiveness_score))

            return {
                "fallback_analysis": True,
                "changes": {
                    "engagement_changes": {
                        "likes_change": likes_change,
                        "comments_change": comments_change,
                        "agent_responses": agent_responses
                    }
                },
                "effectiveness": {
                    "intervention_score": effectiveness_score,
                    "overall_assessment": self._get_intervention_assessment(effectiveness_score),
                    "analyst_summary": "Assessed using traditional method; enable analyst for more accurate analysis"
                }
            }

        except Exception as e:
            return {"error": f"Traditional comparison analysis failed: {str(e)}"}

    def _format_analyst_comparison_for_strategist(self, analyst_comparison: Dict[str, Any]) -> str:
        """Format analyst comparison result for strategist agent"""
        try:
            if not analyst_comparison or analyst_comparison.get("error"):
                return "- Analyst comparison analysis unavailable or failed"

            if analyst_comparison.get("fallback_analysis"):
                return "- Using traditional comparison method (analyst unavailable)"

            # Get analyst comparison data
            changes = analyst_comparison.get("changes", {})
            effectiveness = analyst_comparison.get("effectiveness", {})
            baseline_analysis = analyst_comparison.get("baseline_analysis", {})
            current_analysis = analyst_comparison.get("current_analysis", {})

            # Build formatted report
            formatted_report = []

            # Basic change metrics
            extremism_change = changes.get("extremism_change", 0)
            sentiment_change = changes.get("sentiment_change", 0)
            engagement_changes = changes.get("engagement_changes", {})

            formatted_report.append(f"- Extremism change: {extremism_change:+.2f} (intervention {'reduced' if extremism_change < 0 else 'increased'} extremism)")
            formatted_report.append(f"- Sentiment change: {sentiment_change:+.2f} (sentiment {'improved' if sentiment_change > 0 else 'worsened'})")

            # Engagement data changes
            likes_change = engagement_changes.get("likes_change", 0)
            comments_change = engagement_changes.get("comments_change", 0)
            agent_responses = engagement_changes.get("agent_responses", 0)

            formatted_report.append(f"- Likes change: {likes_change:+d}")
            formatted_report.append(f"- Comments change: {comments_change:+d}")
            formatted_report.append(f"- Agent responses: {agent_responses}")

            # Effectiveness evaluation
            intervention_score = effectiveness.get("intervention_score", 0)
            assessment = effectiveness.get("overall_assessment", "Unknown")
            analyst_summary = effectiveness.get("analyst_summary", "")

            formatted_report.append(f"- Intervention effectiveness score: {intervention_score:.1f}/10 ({assessment})")

            if analyst_summary:
                formatted_report.append(f"- Analyst summary: {analyst_summary}")

            # Core viewpoint comparison
            baseline_viewpoints = baseline_analysis.get("core_viewpoints", [])
            current_viewpoints = current_analysis.get("core_viewpoints", [])

            if baseline_viewpoints or current_viewpoints:
                formatted_report.append("- Viewpoint changes:")
                formatted_report.append(f"  Baseline viewpoints: {', '.join(baseline_viewpoints) if baseline_viewpoints else 'none'}")
                formatted_report.append(f"  Current viewpoints: {', '.join(current_viewpoints) if current_viewpoints else 'none'}")

            return "\n".join(formatted_report)

        except Exception as e:
            return f"- Failed to format analyst comparison analysis: {str(e)}"

# === Align analyst hot-post selection with feed scoring logic ===

async def _analyst_find_hot_posts_with_feed_score(self) -> List[Dict[str, Any]]:
    """Find hot posts using the same scoring logic as AgentUser.get_feed."""
    try:
        from pathlib import Path

        db_path = "database/simulation.db"
        if not Path(db_path).exists():
            return []

        db_manager = get_db_manager()
        db_manager.set_database_path(db_path)

        # Get post -> time_step mapping
        try:
            pt_rows = fetch_all('SELECT post_id, time_step FROM post_timesteps')
            post_step_map = {r['post_id']: r['time_step'] for r in pt_rows}
        except Exception as e2:
            if "unable to open database file" in str(e2):
                post_step_map = {}
            else:
                raise e2

        # Current time step: use max time_step
        try:
            row = fetch_one('SELECT MAX(time_step) AS max_step FROM post_timesteps')
            current_step = row['max_step'] if row and row['max_step'] is not None else 0
        except Exception as e3:
            if "unable to open database file" in str(e3):
                current_step = 0
            else:
                raise e3

        lambda_decay = 0.1
        beta_bias = 180

        def compute_score(row: Dict[str, Any]) -> float:
            # Same as feed: engagement = comments + shares + likes
            eng = (row.get('num_comments') or 0) + (row.get('num_shares') or 0) + (row.get('num_likes') or 0)
            pstep = post_step_map.get(row['post_id'])
            age = max(0, (current_step - pstep)) if (pstep is not None) else 0
            freshness = max(0.1, 1.0 - lambda_decay * age)
            return (eng + beta_bias) * freshness

        # Candidates: last 24 hours and total engagement >= 5
        try:
            rows = fetch_all("""
                SELECT 
                    post_id, 
                    content, 
                    created_at,
                    num_likes,
                    num_comments, 
                    num_shares,
                    'post' AS content_type
                FROM posts 
                WHERE (status IS NULL OR status != 'taken_down')
            """)
        except Exception as e4:
            if "unable to open database file" in str(e4):
                return []
            else:
                raise e4

        if not rows:
            return []

        dict_rows: List[Dict[str, Any]] = [dict(r) if not isinstance(r, dict) else r for r in rows]
        for r in dict_rows:
            r['engagement_score'] = compute_score(r)

        # Sort by feed score and time, take top 20
        dict_rows.sort(key=lambda r: (r['engagement_score'], r.get('created_at')), reverse=True)
        top_rows = dict_rows[:15]

        formatted_posts: List[Dict[str, Any]] = []
        for row in top_rows:
            formatted_posts.append({
                "content_id": row['post_id'],
                "content": row['content'],
                "timestamp": row['created_at'],
                "content_type": row.get('content_type', 'post'),
                "engagement_metrics": {
                    "likes": row.get('num_likes') or 0,
                    "comments": row.get('num_comments') or 0,
                    "shares": row.get('num_shares') or 0,
                    "engagement_score": row.get('engagement_score') or 0.0
                }
            })

        workflow_logger.info(f"      ✅ Selected {len(formatted_posts)} hot posts using platform feed scoring for analyst review")
        return formatted_posts

    except Exception as e:
        workflow_logger.info(f"      ❌ Failed to find hot posts: {e}")
        return []


# Monkey-patch SimpleAnalystAgent to use the new implementation
try:
    SimpleAnalystAgent._find_hot_posts = _analyst_find_hot_posts_with_feed_score  # type: ignore
except Exception:
    pass
