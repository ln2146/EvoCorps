from datetime import datetime
import logging
import os
import random
import time
from utils import Utils, resolve_engine
import json
import csv
from homophily_analysis import HomophilyAnalysis
from tqdm import tqdm
from news_manager import NewsManager
from database_manager import DatabaseManager
from user_manager import UserManager
from news_spread_analyzer import NewsSpreadAnalyzer
from fact_checker import FactChecker, FactCheckVerdict
from prompts import FactCheckerPrompts
from opinion_balance_manager import OpinionBalanceManager
# Remove the complex user selector
import asyncio

import control_flags
from tracked_opinion_helper import (
    ensure_opinion_tracking_initialized,
    discover_first_malicious_news_if_needed,
    init_opinions_log,
    ask_tracked_users_about_first_malicious_news,
    preload_first_fake_news_from_dataset,
)


class Simulation:
    """
    A simulation of a social media platform.
    """
    def __init__(self, config: dict):
        self.config = config  # Store the entire config dictionary
        self.reset_db = config.get('reset_db', True)
        self.num_users = config['num_users']
        self.engine = resolve_engine(config)
        self.generate_own_post = config.get('generate_own_post', True)  # New parameter with default True

        # Generate timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Track injected fake-news timesteps (used for delayed official explanation attachment)
        # {post_id: injection_timestep (1-based)}
        self.fake_news_injection_timesteps = {}

        # Initialize database manager
        self.db_manager = DatabaseManager('database/simulation.db', self.reset_db)
        self.conn = self.db_manager.get_connection()
        self.db_path = self.db_manager.db_path

        # Replace user management with UserManager
        self.user_manager = UserManager(config, self.db_manager)
        self.users = self.user_manager.users

        # Initialize posts list
        self.posts = []

        # Create news agent
        self.news_manager = NewsManager(self.config, self.conn)
        self.news_agent = self.news_manager.news_agent

        # Simplified user selection logic - rely directly on the user manager

        # Create initial follows
        self.user_manager.create_initial_follows()

        # Initialize the OpenAI client using MultiModelSelector for 502 error prevention
        try:
            from multi_model_selector import multi_model_selector
            self.multi_model_selector = multi_model_selector
            # Create an optimized client using the MultiModelSelector configuration
            self.openai_client, _ = multi_model_selector.create_openai_client()
            print(f"✅ Simulation created an optimized client via MultiModelSelector")
        except Exception as e:
            print(f"⚠️ MultiModelSelector initialization failed: {e}, falling back to selector-only client")
            from multi_model_selector import MultiModelSelector
            # Unified model selection via MultiModelSelector (regular role)
            self.multi_model_selector = MultiModelSelector()
            # Fall back to selector-managed setup
            if self.engine.startswith("gpt") or self.engine.startswith("gemini"):
                self.openai_client, _ = self.multi_model_selector.create_openai_client(role="regular")
            else:
                self.openai_client, _ = self.multi_model_selector.create_openai_client_with_base_url(
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                    role="regular",
                )

        # Initialize news spread analyzer with config
        self.news_spread_analyzer = NewsSpreadAnalyzer(self.db_manager, self.config)

        # Initialize fact checker - always initialize regardless of config
        # Actual execution is controlled by control_flags.aftercare_enabled
        self.experiment_type = config.get('experiment', {}).get('type', 'none')
        self.experiment_settings = config.get('experiment', {}).get('settings', {})
        
        # Always initialize fact checker infrastructure
        fact_checker_engine = self.experiment_settings.get("fact_checker_engine")
        if not fact_checker_engine:
            if self.multi_model_selector:
                fact_checker_engine = self.multi_model_selector.select_random_model(role="fact_checker")
            else:
                fact_checker_engine = self.engine
        
        self.fact_checker_engine = fact_checker_engine
        self.fact_checker = FactChecker(
            checker_id="main_checker",
            temperature=self.experiment_settings.get('fact_checker_temperature', 0.3)
        )
        logging.info(f"🔍 Fact-check infrastructure initialized using model: {fact_checker_engine}")
        logging.info(f"🔍 Fact-check execution controlled by control_flags.aftercare_enabled (current: {control_flags.aftercare_enabled})")

        # Initialize opinion balance manager (only if enabled)
        if config.get("opinion_balance_system", {}).get("enabled", False):
            self.opinion_balance_manager = OpinionBalanceManager(config, self.conn)
        else:
            self.opinion_balance_manager = None

        # Initialize malicious bot manager.
        #
        # Whether attacks actually run is now controlled *only* by
        # control_flags.attack_enabled, so we always construct the
        # manager when possible and let the global flag decide.
        try:
            from malicious_bot_manager import MaliciousBotManager
            self.malicious_bot_manager = MaliciousBotManager(config, self.db_manager)
        except Exception as e:
            logging.error(f"Failed to initialize MaliciousBotManager: {e}")
            self.malicious_bot_manager = None


        # Initialize pre-bunking system
        self.prebunking_enabled = config.get("prebunking_system", {}).get("enabled", False)
        self.safety_prompts_db = {}
        if self.prebunking_enabled:
            self.safety_prompts_db = Utils.load_safety_prompts("safety_prompts.json")
            if self.safety_prompts_db:
                logging.info("🛡️ Pre-bunking system enabled and prompts loaded.")
            else:
                logging.error("🛡️ Pre-bunking system enabled but failed to load prompts.")
                self.prebunking_enabled = False
    
    async def run(self, num_time_steps: int):
        """Run the simulation."""
        new_user_config = self.config.get('new_users', {})
        add_new_users_probability = new_user_config.get('add_probability', 0.9)
        new_user_follow_probability = new_user_config.get('follow_probability', 0.0)
        news_start_step = self.config.get('news_injection', {}).get('start_step', 1)

        # Initialize timers for opinion balance monitoring
        self.last_opinion_balance_check = 0  # Start at zero so the first check runs immediately
        
        # Get the monitoring interval from the configuration to align with user selection
        opinion_balance_config = self.config.get('opinion_balance_system', {})
        monitoring_interval_minutes = opinion_balance_config.get('feedback_monitoring_interval', 30)
        self.opinion_balance_interval = monitoring_interval_minutes * 60  # Convert to seconds

        # Save a copy of the experiment configuration
        # Create directory if it doesn't exist
        config_dir = f"experiment_outputs/configs"
        os.makedirs(config_dir, exist_ok=True)

        # Save the configuration with the same timestamp used for other outputs
        config_path = f"{config_dir}/{self.timestamp}_config.json"
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

        logging.info(f"Saved experiment configuration to {config_path}")

        # Ensure opinion tracking fields exist (lazy init)
        ensure_opinion_tracking_initialized(self)

        # Preload the first malicious news directly from dataset and ask tracked users before step 1
        try:
            if not getattr(self, '_first_malicious_news_content', None):
                preload_first_fake_news_from_dataset(self)
            if getattr(self, '_first_malicious_news_content', None):
                init_opinions_log(self)
                # Ask once before the loop for timestep 1
                await ask_tracked_users_about_first_malicious_news(self, 1)
        except Exception as e:
            logging.error(f"Failed to preload/ask first malicious news before timestep 1: {e}")

        # Get fact checking settings if applicable for both third-party and hybrid
        # 始终使用第三方事实核查的设置，实际执行由 control_flags.aftercare_enabled 控制
        fact_check_limit = self.experiment_settings.get('posts_per_step', 5)
        fact_check_start_delay = self.experiment_settings.get('start_delay_minutes', 5)

        # Track all injected news post IDs
        injected_news_posts = []

        # Launch the opinion balance background monitoring task using the user-configured interval
        opinion_balance_task = None
        if self.opinion_balance_manager and self.opinion_balance_manager.enabled:
            # Check if standalone opinion balance mode is enabled
            standalone_mode = self.config.get('opinion_balance_system', {}).get('standalone_mode', False)
            if standalone_mode:
                print("🔍 Standalone opinion balance mode detected - skipping the built-in monitoring task")
                print("💡 Make sure the standalone opinion balance system is running: python src/opinion_balance_launcher.py")
            else:
                opinion_balance_task = asyncio.create_task(self._background_opinion_balance_monitor())
                monitoring_interval_minutes = self.opinion_balance_interval // 60
                print(f"🔍 Starting background opinion balance monitoring every {monitoring_interval_minutes} minutes")

        # Add tqdm progress bar
        progress_bar = tqdm(range(num_time_steps), desc="Running simulation")

        for step in progress_bar:
            logging.info(f"Time step: {step + 1}")

            # Update progress bar description with current step
            progress_bar.set_description(f"Time step {step + 1}/{num_time_steps}")

            # Run fact checking at the START of each step (checks news from 3 timesteps ago)
            # e.g., timestep 4 checks news from timestep 1, timestep 5 checks news from timestep 2
            # 完全由全局开关 control_flags.aftercare_enabled 控制（CLI 输入或 API 修改）
            if self.fact_checker and step >= 3 and control_flags.aftercare_enabled:
                logging.info(f"🔍 Time step {step + 1}: starting third-party fact check (checking news from time step {step - 2})")
                # 始终使用 "third_party_fact_checking" 作为 experiment_type，不受 CLI 输入影响
                await self._run_fact_checking_async(step, fact_check_limit, current_timestep=step, experiment_type="third_party_fact_checking")

            # Discover the very first malicious news if not yet captured
            try:
                discovered_now = False
                if not getattr(self, '_first_malicious_news_content', None):
                    discover_first_malicious_news_if_needed(self)
                    if self._first_malicious_news_content:
                        init_opinions_log(self)
                        await ask_tracked_users_about_first_malicious_news(self, step + 1)
                        discovered_now = True
                if getattr(self, '_first_malicious_news_content', None) and not discovered_now:
                    await ask_tracked_users_about_first_malicious_news(self, step + 1)
            except Exception as e:
                logging.error(f"Failed to discover or ask tracked users: {e}")

            # Inject news at specified step
            if step >= news_start_step:
                # Check if the total number of posts exceeds the limit
                current_post_count = self._get_current_post_count()
                max_posts = self.config.get('max_total_posts', 10)

                if current_post_count < max_posts:
                    logging.info(f"Time step {step + 1}: preparing to inject news (posts: {current_post_count}/{max_posts})")
                    
                    # Receive negative news information
                    news_post_ids, negative_news_info = await self.news_manager.inject_news(time_step=step)
                    
                    if news_post_ids:
                        injected_news_posts.extend(news_post_ids)
                        
                        # Track injected fake/opinion news post injection timestep (1-based)
                        for neg_info in negative_news_info:
                            post_id = neg_info.get('post_id')
                            if post_id and post_id not in self.fake_news_injection_timesteps:
                                self.fake_news_injection_timesteps[post_id] = step + 1
                        
                        new_post_count = self._get_current_post_count()
                        logging.info(f"Time step {step + 1}: injected {len(news_post_ids)} news posts (count: {current_post_count} → {new_post_count})")
                    else:
                        logging.info(f"Time step {step + 1}: news injection created no posts")
                else:
                    logging.info(f"Time step {step + 1}: skipped news injection - post limit reached ({current_post_count}/{max_posts})")

            # New user logic - add the same number of users as the initial batch
            new_user_start_step = new_user_config.get('start_step', 1)

            if step >= new_user_start_step and random.random() < add_new_users_probability:
                # Check if we've reached the maximum user limit
                max_users = self.config.get('max_total_users', 180)
                current_user_count = len(self.users)

                if current_user_count >= max_users:
                    logging.info(f"⚠️ Time step {step + 1}: maximum user limit reached ({max_users}); skipping new user addition")
                else:
                    # Calculate the number of new users - match the initial user count
                    users_per_step = new_user_config.get('users_per_step', 'same_as_initial')

                    if users_per_step == 'same_as_initial':
                        num_new_users = self.config['num_users']  # use the initial user count
                    else:
                        num_new_users = int(users_per_step)  # use the specified number

                    # Ensure we do not exceed the maximum users
                    if current_user_count + num_new_users > max_users:
                        num_new_users = max_users - current_user_count
                        logging.info(f"⚠️ Time step {step + 1}: adjusted new user count to {num_new_users} to avoid exceeding the limit")

                    if num_new_users > 0:
                        logging.info(f"🆕 Time step {step + 1}: preparing to add {num_new_users} new users")

                        self.user_manager.add_random_users(num_new_users, follow_probability=new_user_follow_probability)
                        # Update our reference to users
                        self.users = self.user_manager.users

                        logging.info(f"✅ Time step {step + 1}: successfully added {num_new_users} new users, total users: {len(self.users)}")
                    else:
                        logging.info(f"⚠️ Time step {step + 1}: cannot add users; max user limit reached")

            # Each user creates a post (only if generate_own_post is True)
            if self.generate_own_post:
                # Allow each user to attempt posting while enforcing limits
                post_tasks = []
                for i, user in enumerate(self.users):
                    task = self._async_user_post_creation(user, step, i)
                    post_tasks.append(task)

                # Execute all post-creation tasks concurrently
                if post_tasks:
                    current_post_count_before = self._get_current_post_count()
                    await asyncio.gather(*post_tasks, return_exceptions=True)
                    new_post_count = self._get_current_post_count()
                    actual_created = new_post_count - current_post_count_before
                    max_posts = self.config.get('max_total_posts', 10)
                    if actual_created > 0:
                        logging.info(f"Time step {step + 1}: user posting completed, created {actual_created} posts (post count: {current_post_count_before} → {new_post_count}/{max_posts})")

            # Each user reacts to their feed and may create posts
            # Execute user reactions concurrently (asynchronously)
            reaction_tasks = []
            for i, user in enumerate(self.users):
                # Provide current timestep context to user for accurate comment timestamping
                try:
                    setattr(user, 'current_time_step', step)
                except Exception:
                    pass
                task = self._async_user_reaction(user, step, i)
                reaction_tasks.append(task)
            
            # Run all user reaction tasks in parallel
            if reaction_tasks:
                await asyncio.gather(*reaction_tasks, return_exceptions=True)

            # Clear timestep context
            for user in self.users:
                if hasattr(user, 'current_time_step'):
                    try:
                        delattr(user, 'current_time_step')
                    except Exception:
                        pass

            # Analyze spread for all injected news posts (logging disabled)
            for news_post_id in injected_news_posts:
                spread_metrics = self.news_spread_analyzer.analyze_spread(news_post_id, step)

            # Update influence scores
            Utils.update_user_influence(self.conn, self.db_path)

            # Execute malicious attacks concurrently，完全依赖全局开关
            # control_flags.attack_enabled（终端/端口统一控制）。
            tasks = []

            # 只要存在 malicious_bot_manager，并且全局开关为 True，就执行攻击；
            # 当 attack_enabled 为 False 时，完全关闭攻击。
            if self.malicious_bot_manager:
                malicious_effective = control_flags.attack_enabled
            else:
                malicious_effective = False

            # ========== Deprecated: threshold-based real-time attack mechanism removed ==========

            # Legacy news-based malicious post generation (retained for compatibility)
            if malicious_effective:
                tasks.append(self._news_based_malicious_posts(step))

            # Execute all tasks concurrently
            if tasks:
                await asyncio.gather(*tasks)

            # Run batch malicious attacks mid-timestep (no longer at the end)
            # Pass timestep to malicious manager for accurate comment timestamping
            if malicious_effective:
                try:
                    setattr(self.malicious_bot_manager, 'current_time_step', step)
                except Exception:
                    pass
                await self._run_malicious_batch_attack(step)

            # After malicious attacks and opinion balance system triggers, let regular users keep interacting
            # await self._continue_user_activities(step)

            # Negative news heat tracking removed
            
            # Display current time step post statistics
            current_post_count = self._get_current_post_count()
            max_posts = self.config.get('max_total_posts', 10)
            remaining_posts = max_posts - current_post_count

            if remaining_posts <= 0:
                logging.info(f"⚠️ Time step {step + 1} complete - reached max post limit: {current_post_count}/{max_posts}")
            else:
                logging.debug(f"📊 Time step {step + 1} complete - post count: {current_post_count}/{max_posts}")

            logging.info("")  # Add a newline for readability between time steps

    async def _run_malicious_batch_attack(self, step: int):
        """Run malicious bot batch attack around the middle of each timestep."""
        if (not hasattr(self, 'malicious_bot_manager') or
                not self.malicious_bot_manager or
                not control_flags.attack_enabled):
            return

        try:
            logging.info(f"🤖 Time step {step + 1}: starting malicious bot batch attack...")
            attack_result = await self.malicious_bot_manager.attack_top_hot_posts(
                top_n=10
            )

            if attack_result.get("success"):
                attacked_count = attack_result.get("attacked_count", 0)
                skipped_count = attack_result.get("skipped_count", 0)
                total_targets = attack_result.get("total_targets", 0)

                if attacked_count > 0:
                    # Minimal display: no longer output comment addition details per post
                    pass
                else:
                    logging.info("📊 Malicious bots: no qualifying target posts")
            else:
                # 同时检查 error 和 reason 字段
                error_msg = attack_result.get('error') or attack_result.get('reason', 'unknown')
                logging.warning(f"⚠️ Malicious bot batch attack failed: {error_msg}")

        except Exception as e:
            logging.error(f"❌ Malicious bot batch attack exception: {e}")

    async def _run_fact_checking_async(self, step: int, fact_check_limit: int, current_timestep: int = None, experiment_type: str = "third_party_fact_checking"):
        """
        Run fact checking asynchronously without blocking the main flow
        
        Args:
            step: Current simulation step
            fact_check_limit: Maximum number of posts to check
            current_timestep: Current timestep for filtering posts
            experiment_type: Type of fact checking experiment (default: "third_party_fact_checking")
        """
        try:
            if current_timestep is not None:
                logging.info(f"📊 Time step {step + 1}: starting async fact checking for this time step's news (checking {fact_check_limit} items)")
            else:
                logging.info(f"📊 Time step {step + 1}: starting async fact checking (checking {fact_check_limit} items)")

            posts_to_check = self.fact_checker.get_posts_to_check(
                limit=fact_check_limit,
                experiment_type=experiment_type,  # 使用传入的 experiment_type
                current_timestep=current_timestep
            )

            if not posts_to_check:
                logging.info(f"📊 Time step {step + 1}: no content needs fact checking")
                return
            logging.info(f"📊 Time step {step + 1}: found {len(posts_to_check)} items requiring fact checking")

            # Process multiple posts concurrently for fact checking while limiting database write concurrency
            # Use Semaphore(1) to ensure only one database write at a time and avoid locking
            if not hasattr(self, '_db_write_semaphore'):
                self._db_write_semaphore = asyncio.Semaphore(1)  # Serial writes to prevent locking

            fact_check_tasks = []
            for post in posts_to_check:
                task = self._fact_check_single_post_async(post, step, experiment_type)
                fact_check_tasks.append(task)

            # Wait for all fact-checking tasks to finish
            results = await asyncio.gather(*fact_check_tasks, return_exceptions=True)

            # Aggregate the results
            success_count = 0
            error_count = 0
            takedown_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logging.error(f"Fact-check task {i} failed: {result}")
                else:
                    success_count += 1
                    if result and result.get('taken_down', False):
                        takedown_count += 1

            logging.info(f"📊 Time step {step + 1}: fact checking complete - success: {success_count}, errors: {error_count}, takedowns: {takedown_count}")

        except Exception as e:
            logging.error(f"Error occurred during async fact checking: {e}")

    async def _fact_check_single_post_async(self, post, step: int, experiment_type: str = "third_party_fact_checking"):
        """
        Asynchronously check a single post
        
        Args:
            post: Post object to check
            step: Current simulation step
            experiment_type: Type of fact checking experiment
        """
        try:
            # LLM call section (can run concurrently and is time-consuming)
            # Use asyncio.to_thread to run the synchronous LLM call asynchronously while avoiding SQLite access across threads
            import asyncio

            # Prepare the prompt (no database access)
            prompt = self.fact_checker._create_fact_check_prompt(post)
            system_prompt = FactCheckerPrompts.get_system_prompt()

            # LLM invocation (safe to run in a thread pool)
            verdict = await asyncio.to_thread(
                Utils.generate_llm_response,
                openai_client=self.openai_client,
                engine=self.fact_checker_engine,
                prompt=prompt,
                system_message=system_prompt,
                temperature=self.fact_checker.temperature,
                response_model=FactCheckVerdict
            )

            # Database write section (executed on the main thread with semaphore protection)
            async with self._db_write_semaphore:
                # Invoke directly on the main thread without using to_thread
                self.fact_checker._record_verdict(
                    post.post_id,
                    verdict,
                    experiment_type  # 使用传入的 experiment_type
                )

            # NOTE: Takedown mechanism disabled (see src/fact_checker.py).
            taken_down = False

            logging.info(f"📊 Time step {step + 1}: fact check {post.post_id} - {verdict.verdict} ({verdict.confidence:.0%})" +
                        (f" [takedown]" if taken_down else ""))

            return {
                'post_id': post.post_id,
                'verdict': verdict.verdict,
                'confidence': verdict.confidence,
                'taken_down': taken_down
            }

        except Exception as e:
            logging.error(f"Error during fact check for post {post.post_id}: {e}")
            raise

        # Stop the opinion balance background monitoring task
        if opinion_balance_task and not opinion_balance_task.done():
            opinion_balance_task.cancel()
            try:
                await opinion_balance_task
            except asyncio.CancelledError:
                print(f"🔍 Opinion balance background monitoring stopped")

        # Wait for the opinion balance monitor to complete (only when feedback system is enabled)
        if (self.opinion_balance_manager and self.opinion_balance_manager.enabled and
            self.config.get('opinion_balance_system', {}).get('feedback_system_enabled', False)):
            await self._wait_for_monitoring_completion()

        # Print the simulation statistics
        logging.info("\nSimulation complete. Printing statistics...")
        Utils.print_simulation_stats(self.conn)

        # Then save and close the database as the last step
        self.db_manager.save_simulation_db(timestamp=self.timestamp)

        # Run homophily analysis after simulation completes
        homophily_analyzer = HomophilyAnalysis(self.db_path)
        homophily_analyzer.run_analysis(output_dir=f"experiment_outputs/homophily_analysis/{self.timestamp}")

    async def _async_user_post_creation(self, user, step, user_index):
        """Async user post creation helper with simplified limit checks"""
        try:
            # Let user decide whether to post based on news, identity, and memory
            should_post = self._should_user_create_post(user, step)

            if should_post:
                post_payload = await user._generate_post_content(self.openai_client, self.engine, max_tokens=256)
                content_text = post_payload.get("content", "") if isinstance(post_payload, dict) else str(post_payload)
                summary_text = post_payload.get("summary") if isinstance(post_payload, dict) else None
                post_id = await user.create_post(content_text, summary=summary_text, is_news=False, news_type=None, status='active', time_step=step)

                if post_id:
                    logging.debug(f"User {user.user_id} successfully created post {post_id}")
                else:
                    # When create_post returns None (limit reached), log the skip
                    max_posts = self.config.get('max_total_posts', 10)
                    current_count = self._get_current_post_count()

                # Pre-bunking check
                if self.prebunking_enabled and self.safety_prompts_db and post_id:
                    topic = Utils.identify_topic(content_text, self.safety_prompts_db)
                    if topic:
                        message = Utils.generate_prebunking_message(topic, self.safety_prompts_db)
                        print(message)  # Print the pre-bunking message to the console

        except Exception as e:
            logging.error(f"User {user.user_id} async post creation failed: {e}")

    def _get_current_post_count(self):
        """Get the current number of original posts (excluding reposts)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts WHERE original_post_id IS NULL")
        return cursor.fetchone()[0]

    async def _async_user_reaction(self, user, step, user_index):
        """Async user reaction handler"""
        try:
            # User reacts to their feed — even in fact-check mode, show the full feed (including user posts)
            feed = user.get_feed(experiment_config=self.config, time_step=step)

            # 真相拼接机制：到达规定时间步后无条件执行，不受 aftercare_enabled 控制
            if step >= 4 and self.news_manager:
                feed = self._append_truth_to_fake_news_posts_with_delay(feed, step)

            await user.react_to_feed(self.openai_client, self.engine, feed)

            # ========== Deprecated: replaced the real-time check mechanism with batch attacks at the end of the timestep ==========
            # await self._check_comment_based_interventions(user.user_id, step)

        except Exception as e:
            logging.error(f"User {user.user_id} async reaction failed: {e}")

    async def _wait_for_monitoring_completion(self):
        """Wait for the opinion balance monitoring cycle to finish"""
        try:
            print(f"\n⏳ Waiting for opinion balance monitoring to finish...")
            print(f"   Trending posts scan interval: {self.opinion_balance_manager.trending_posts_scan_interval} minutes")
            print(f"   Feedback monitoring interval: {self.opinion_balance_manager.feedback_monitoring_interval} minutes")
            print(f"   Will wait at least {self.opinion_balance_manager.feedback_monitoring_interval + 1} minutes to ensure the first briefing is generated")

            # Wait long enough for the monitoring loop to complete at least one cycle (using the feedback interval)
            wait_time = (self.opinion_balance_manager.feedback_monitoring_interval + 1) * 60  # Convert to seconds

            import asyncio
            await asyncio.sleep(wait_time)

            print(f"✅ Monitoring wait complete")

            # Check if any briefings were generated
            import os
            if os.path.exists("logs"):
                briefing_files = [f for f in os.listdir("logs") if f.startswith("effect_briefing")]
                if briefing_files:
                    print(f"📋 Found {len(briefing_files)} briefing files:")
                    for file in briefing_files[:3]:  # Show the first 3
                        print(f"   - {file}")
                else:
                    print(f"⚠️  No briefing files found; the monitoring loop might not be running correctly")
            else:
                print(f"⚠️  'logs' directory missing; briefings may not have been generated")

        except Exception as e:
            logging.error(f"Error while waiting for monitor completion: {e}")

    async def _parallel_content_generation(self):
        """Parallel content generation for regular users, malicious bots, and amplifier agents"""
        import asyncio

        print(f"\n🚀 Launching the parallel content generation system")
        print("=" * 60)

        # Collect all available posts from the database
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT post_id, content, author_id FROM posts WHERE status = 'active'")
            post_rows = cursor.fetchall()

            if not post_rows:
                print("⚠️  No available posts for comment generation")
                return

            # Create a simple post object
            class SimplePost:
                def __init__(self, post_id, content, author_id):
                    self.post_id = post_id
                    self.content = content
                    self.author_id = author_id
                    self.status = 'active'

            available_posts = [SimplePost(row[0], row[1], row[2]) for row in post_rows]
            print(f"📊 Found {len(available_posts)} available posts")

        except Exception as e:
            print(f"❌ Failed to fetch posts: {e}")
            return

        # Build the list of parallel tasks
        tasks = []

        # 1. Regular user comment generation tasks
        normal_user_tasks = self._create_normal_user_tasks(available_posts)
        tasks.extend(normal_user_tasks)

        # 2. Malicious bot attack tasks (if enabled)
        # 完全依赖全局恶意攻击开关 control_flags.attack_enabled
        if self.malicious_bot_manager and bool(control_flags.attack_enabled):
            malicious_tasks = self._create_malicious_tasks(available_posts)
            tasks.extend(malicious_tasks)

        # 3. amplifier agent tasks (if the opinion balance system is enabled)
        if self.opinion_balance_manager and self.opinion_balance_manager.enabled:
            amplifier_tasks = self._create_amplifier_tasks(available_posts)
            tasks.extend(amplifier_tasks)

        print(f"📊 Total parallel tasks: {len(tasks)}")
        print(f"   👥 Regular user tasks: {len(normal_user_tasks)}")
        if self.malicious_bot_manager and self.malicious_bot_manager.enabled:
            print(f"   🔥 Malicious bot tasks: {len([t for t in tasks if 'malicious' in str(t)])}")
        if self.opinion_balance_manager and self.opinion_balance_manager.enabled:
            print(f"   🔄 amplifier agent tasks: {len([t for t in tasks if 'amplifier' in str(t)])}")

        # Execute all tasks in parallel
        if tasks:
            print(f"⚡ Starting parallel execution...")
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Statistics from the execution
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                error_count = len(results) - success_count

                print(f"✅ Parallel generation complete!")
                print(f"   📊 Successes: {success_count} tasks")
                print(f"   ❌ Failures: {error_count} tasks")
                print("=" * 60)

            except Exception as e:
                print(f"❌ Parallel execution failed: {e}")
        else:
            print("⚠️  No tasks to execute")

    def _create_normal_user_tasks(self, available_posts):
        """Create normal user comment generation tasks for concurrent execution"""
        tasks = []

        # Select active users for concurrent commenting
        active_users = []
        for user in self.users:
            # Skip news users
            if hasattr(user, 'is_news_agent') and user.is_news_agent:
                continue

            # Boost the activity probability so more users participate concurrently
            activity_prob = getattr(user, 'activity_level', 0.8)
            if random.random() < activity_prob:
                active_users.append(user)

        # If there aren't enough active users, select at least half of them
        normal_users = [u for u in self.users if not (hasattr(u, 'is_news_agent') and u.is_news_agent)]
        if len(active_users) < len(normal_users) // 2:
            active_users = random.sample(normal_users, max(1, len(normal_users) // 2))

        print(f"   👥 Selected {len(active_users)} users for concurrent commenting")

        # Create a comment task for each active user (one comment per user, multiple concurrent)
        for user in active_users:
            if available_posts:
                # Randomly select a post for each user to comment on
                target_post = random.choice(available_posts)
                task = self._generate_normal_user_comment(user, target_post)
                tasks.append(task)

        print(f"   📊 Created {len(tasks)} concurrent comment tasks")
        return tasks

    def _get_post_comments_for_prompt(self, post_id: str):
        """Fetch top-liked and latest comments for prompt context."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT comment_id, content, author_id, num_likes, created_at
            FROM comments
            WHERE post_id = ?
            ORDER BY num_likes DESC, created_at DESC
            LIMIT 2
            """,
            (post_id,),
        )
        hot_rows = cursor.fetchall()

        hot_ids = [row[0] for row in hot_rows]
        if hot_ids:
            placeholders = ",".join("?" * len(hot_ids))
            cursor.execute(
                f"""
                SELECT comment_id, content, author_id, num_likes, created_at
                FROM comments
                WHERE post_id = ? AND comment_id NOT IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [post_id] + hot_ids,
            )
        else:
            cursor.execute(
                """
                SELECT comment_id, content, author_id, num_likes, created_at
                FROM comments
                WHERE post_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (post_id,),
            )
        recent_rows = cursor.fetchall()

        combined = []
        seen = set()
        for row in list(hot_rows) + list(recent_rows):
            comment_id, content, author_id, num_likes, created_at = row
            if comment_id in seen:
                continue
            combined.append(
                {
                    "comment_id": comment_id,
                    "content": content,
                    "author_id": author_id,
                    "num_likes": num_likes,
                    "created_at": created_at,
                }
            )
            seen.add(comment_id)
            if len(combined) == 3:
                break
        return combined

    @staticmethod
    def _format_comment_context_for_prompt(comments):
        if not comments:
            return ""

        lines = []
        for idx, comment in enumerate(comments, 1):
            label = "Hot Comment" if idx <= 2 else "Latest Comment"
            suffix = f" {idx}" if idx <= 2 else ""
            preview = comment["content"].replace("\n", " ").strip()
            lines.append(
                f"{label}{suffix}: {preview} (by {comment['author_id']}, likes: {comment['num_likes']})"
            )
        return "\n".join(lines)

    def _create_malicious_tasks(self, available_posts):
        """Create malicious bot attack tasks - target all available posts without comment count limits"""
        tasks = []
        
        print(f"   🔥 Malicious bot activation - targeting all available posts")

        # Attack every available post without checking comment counts
        for post in available_posts:
            comment_count = self._get_post_comment_count(post.post_id)
            print(f"   🎯 Targeting post {post.post_id}: current comments {comment_count}")

            # ========== Deprecated: replaced with batch attacks at the end of each timestep ==========
            # task = self.malicious_bot_manager.monitor_post(
            #     post.post_id, post.content, post.author_id
            # )
            # tasks.append(task)
            # print(f"   ✅ Created malicious attack task for post {post.post_id}")

        print(f"   📊 Live attack mechanism deprecated; now execute batch attacks at the end of each timestep")
        return tasks

    def _create_amplifier_tasks(self, available_posts):
        """Opinion balance system - real-time intervention disabled, only scheduled monitoring remains"""
        tasks = []

        print(f"\n⚖️  Opinion balance system: real-time intervention disabled")
        print(f"   💡 Only scheduled monitoring will be used to detect trending posts")
        print("=" * 50)

        # Real-time intervention mechanism removed; only scheduled monitoring is retained
        return tasks


    async def _generate_normal_user_comment(self, user, post):
        """Generate a normal user comment asynchronously"""
        try:
            # Dynamically select models for multi-model concurrency
            import asyncio
            if hasattr(user, 'get_dynamic_model'):
                selected_model = user.get_dynamic_model()
            else:
                selected_model = self.engine

            # Generate comment content
            comment_context_items = self._get_post_comments_for_prompt(post.post_id)
            comment_context_text = self._format_comment_context_for_prompt(comment_context_items)
            comment_content = await user._generate_comment_content(
                self.openai_client,
                selected_model,
                post.content,
                comment_context=comment_context_text,
                max_tokens=150,
            )

            if comment_content:
                comment_id = user.create_comment(post.post_id, comment_content)
                print(f"👤 User {user.user_id} concurrently commented on post {post.post_id} (model: {selected_model})")
                return {"success": True, "comment_id": comment_id, "model": selected_model}
            else:
                return {"success": False, "error": "comment generation failed"}

        except Exception as e:
            print(f"❌ User {user.user_id} concurrent comment generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _background_opinion_balance_monitor(self):
        """Background opinion balance monitor running with the user-selected interval"""
        monitor_count = 0
        try:
            print(f"🔍 Opinion balance monitoring system started in continuous monitoring mode")

            while True:
                # Main monitoring loop: continuous watch
                await asyncio.sleep(1)

                monitor_count += 1
                print(f"\n🔍 [Monitoring cycle {monitor_count}] starting opinion balance scan...")

                # Execute the monitoring scan
                await self._monitor_trending_posts_background()

                print(f"✅ [Monitoring cycle {monitor_count}] scan complete")

        except asyncio.CancelledError:
            print(f"🔍 Opinion balance background monitoring stopped (ran for {monitor_count} cycles)")
            pass
        except Exception as e:
            logging.error(f"Opinion balance background monitoring error: {e}")
            import traceback
            traceback.print_exc()

    async def _monitor_trending_posts_background(self):
        """Background monitoring of trending posts"""
        try:
            cursor = self.conn.cursor()

            print(f"\n🔍 Opinion balance background monitoring - auto-checking every 2 minutes")

            # Find trending posts: comments + likes + shares >= 20, ordered by heat, include news and user posts
            cursor.execute("""
                SELECT p.post_id, p.content, p.author_id, p.num_comments, p.num_likes, p.num_shares, p.created_at
                FROM posts p
                WHERE (p.num_comments + p.num_likes + p.num_shares >= 50)
                AND p.post_id NOT IN (
                    SELECT DISTINCT original_post_id
                    FROM opinion_interventions
                    WHERE original_post_id IS NOT NULL
                )  -- Exclude posts that already had interventions
                ORDER BY (p.num_comments + p.num_likes + p.num_shares) DESC
                limit 10
            """)

            trending_posts = cursor.fetchall()

            if trending_posts:
                print(f"   Found {len(trending_posts)} trending posts; analyzing from highest to lowest heat (includes news and user posts)")

                for post_row in trending_posts:
                    post_id, content, author_id, num_comments, num_likes, num_shares, created_at = post_row
                    total_engagement = num_comments + num_likes + num_shares

                    print(f"\n📊 Monitoring trending post: {post_id}")
                    print(f"   👤 Author: {author_id}")
                    print(f"   💬 Comments: {num_comments}, 👍 Likes: {num_likes}, 🔄 Shares: {num_shares}")
                    print(f"   🔥 Total heat: {total_engagement}")
                    print(f"   📝 Content: {content[:80]}...")

                    # Collect four comments for this post: two for hottest, two for latest (matching regular user logic)
                    # First get the two highest-heat comments
                    cursor.execute("""
                        SELECT comment_id, content, author_id, num_likes, created_at
                        FROM comments
                        WHERE post_id = ?
                        ORDER BY num_likes DESC, created_at DESC
                        LIMIT 2
                    """, (post_id,))
                    hot_comment_rows = cursor.fetchall()

                    # Fetch two most recent comments (excluding the ones already retrieved as hottest)
                    hot_comment_ids = [row[0] for row in hot_comment_rows]
                    if hot_comment_ids:
                        placeholders = ','.join('?' * len(hot_comment_ids))
                        cursor.execute(f"""
                            SELECT comment_id, content, author_id, num_likes, created_at
                            FROM comments
                            WHERE post_id = ? AND comment_id NOT IN ({placeholders})
                            ORDER BY created_at DESC
                            LIMIT 2
                        """, [post_id] + hot_comment_ids)
                    else:
                        cursor.execute("""
                            SELECT comment_id, content, author_id, num_likes, created_at
                            FROM comments
                            WHERE post_id = ?
                            ORDER BY created_at DESC
                            LIMIT 2
                        """, (post_id,))
                    recent_comment_rows = cursor.fetchall()

                    # Merge comments: first by heat, then by recency
                    all_comment_rows = hot_comment_rows + recent_comment_rows
                    top_comments = []
                    for comment_row in all_comment_rows:
                        comment_id, content_c, author_id_c, num_likes_c, created_at_c = comment_row
                        top_comments.append({
                            "comment_id": comment_id,
                            "content": content_c,
                            "author_id": author_id_c,
                            "num_likes": num_likes_c,
                            "created_at": created_at_c
                        })

                    print(f"   💬 Total comments collected: {len(top_comments)} (2 hottest + 2 latest)")
                    hot_comments_count = len(hot_comment_rows)
                    recent_comments_count = len(recent_comment_rows)
                    for i, comment in enumerate(top_comments, 1):
                        comment_type = "🔥 Hot" if i <= hot_comments_count else "🕒 New"
                        print(f"      {comment_type} comment {i}: {comment['content'][:50]}... (👍{comment['num_likes']})")

                    # Invoke the full opinion balance workflow
                    if self.opinion_balance_manager and self.opinion_balance_manager.enabled:
                        try:
                            print(f"   🔍 Launching opinion balance analysis and intervention workflow...")

                            # Build formatted content for the workflow (distinguish hot and latest comments)
                            formatted_content = f"""[Trending Post Opinion Analysis]
Post ID: {post_id}
Author: {author_id}
Total heat: {total_engagement}
Post content: {content}

Top comments (sorted by likes):"""

                            # Display the hottest comments
                            for i, comment in enumerate(hot_comment_rows, 1):
                                comment_id, content_c, author_id_c, num_likes_c, created_at_c = comment
                                formatted_content += f"""
🔥 Hot comment {i}: {content_c}
- Author: {author_id_c}
- Likes: {num_likes_c}"""

                            formatted_content += """

Latest comments (chronological):"""

                            # Display the latest comments
                            for i, comment in enumerate(recent_comment_rows, 1):
                                comment_id, content_c, author_id_c, num_likes_c, created_at_c = comment
                                formatted_content += f"""
🕒 Recent comment {i}: {content_c}
- Author: {author_id_c}
- Likes: {num_likes_c}"""

                            coordination_system = self.opinion_balance_manager.coordination_system
                            if coordination_system:
                                # Determine the current time step (when the comments were posted)
                                current_time_step = None
                                try:
                                # Get the maximum time step from the feed_exposures table
                                    cursor.execute('SELECT MAX(time_step) AS max_step FROM feed_exposures')
                                    result = cursor.fetchone()
                                    if result and result[0] is not None:
                                        current_time_step = result[0]
                                except Exception:
                                    pass
                                
                                # Launch the opinion balance workflow asynchronously without blocking the simulation
                                print(f"   🚀 Starting the asynchronous opinion balance workflow...")
                                
                                # Create the async task without awaiting the result
                                intervention_task = asyncio.create_task(
                                    coordination_system.execute_workflow(
                                        content_text=formatted_content,
                                        content_id=post_id,
                                        monitoring_interval=self.opinion_balance_manager.feedback_monitoring_interval,
                                        enable_feedback=self.opinion_balance_manager.feedback_enabled,
                                        force_intervention=False,  # Leave the intervention decision to the internal analysts
                                        time_step=current_time_step  # Pass the current time step
                                    )
                                )
                                
                                # Add the task to the tracking list for later follow-up
                                if not hasattr(self, 'intervention_tasks'):
                                    self.intervention_tasks = []
                                self.intervention_tasks.append({
                                    'task': intervention_task,
                                    'post_id': post_id,
                                    'start_time': datetime.now(),
                                    'content_preview': formatted_content[:100] + "..." if len(formatted_content) > 100 else formatted_content
                                })
                                
                                print(f"   ✅ Opinion balance workflow launched asynchronously")
                                print(f"   📋 Task ID: {post_id}")
                                print(f"   ⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
                                print("="*60)
                            else:
                                print(f"   ⚠️  Coordination system component not found")

                        except Exception as e:
                            print(f"   ❌ Analyst workflow encountered an error: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        # Check and display the status of asynchronous tasks
                        await self._check_intervention_tasks_status()
                    else:
                        print(f"   ⚠️  Opinion balance system not enabled")
                else:
                    # Remain silent when no trending posts are found
                    pass

        except Exception as e:
            logging.error(f"Error during background trending post monitoring: {e}")
            import traceback
            traceback.print_exc()

    async def _check_intervention_tasks_status(self):
        """Check the status of asynchronous intervention tasks"""
        if not hasattr(self, 'intervention_tasks') or not self.intervention_tasks:
            return
        
        completed_tasks = []
        for i, task_info in enumerate(self.intervention_tasks):
            task = task_info['task']
            post_id = task_info['post_id']
            start_time = task_info['start_time']
            
            if task.done():
                try:
                    result = task.result()
                    if result and result.get("success"):
                        if result.get("intervention_triggered"):
                            print(f"   ✅ Async intervention task completed - post ID: {post_id}")
                            print(f"   📋 Intervention ID: {result.get('intervention_id')}")
                            print(f"   🤖 Agent responses: {result.get('total_responses', 0)}")
                        else:
                            print(f"   ✅ Async analysis complete - post ID: {post_id} (no intervention needed)")
                    else:
                        print(f"   ⚠️ Async intervention task failed - post ID: {post_id}")
                        print(f"   ❌ Error: {result.get('error', 'unknown error') if result else 'unknown error'}")
                except Exception as e:
                    print(f"   ❌ Async task exception - post ID: {post_id}: {e}")
                
                completed_tasks.append(i)
            else:
                # Display the status of running tasks
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 30:  # Show status after 30 seconds
                    print(f"   🔄 Async task still running - post ID: {post_id} (running for {elapsed:.0f} seconds)")
        
        # Remove completed tasks
        for i in reversed(completed_tasks):
            self.intervention_tasks.pop(i)

    async def _monitor_trending_posts(self, step):
        """Legacy monitoring function (currently unused but kept for compatibility)"""
        # This function is no longer in use; background monitoring replaces it
        pass

    async def _news_based_malicious_posts(self, step):
        """News-based malicious post generation is disabled (kept for compatibility)."""
        # No malicious posts are auto-generated anymore, so just return.
        return

    async def _continue_user_activities(self, step):
        """Let regular users continue their activities after malicious attacks and opinion balance triggers"""
        try:
            # Let a subset of users continue reacting to new content
            active_users = random.sample(self.users, min(len(self.users) // 3, 15))  # Randomly select 1/3 of users or up to 15

            for user in active_users:
                try:
                    # Skip news agents
                    if user.is_news_agent:
                        continue

                    # Check if the user can still comment
                    if user.comment_count >= user.comment_limit:
                        continue

                    # Get the user's feed (full feed even during third-party fact checking; news items will carry fact-check tags)
                    # Do not record exposures again in the same timestep
                    feed = user.get_feed(experiment_config=self.config, time_step=None)

                    # Have the user react to the feed
                    if feed:
                        await user.react_to_feed(self.openai_client, self.engine, feed)

                except Exception as e:
                    logging.error(f"user {user.user_id} continuation activity failed: {e}")
                    continue

            # Silently complete user activities

        except Exception as e:
            logging.error(f"Error while users continued activity: {e}")
            import traceback
            traceback.print_exc()

    def _should_user_create_post(self, user, step):
        """
        Decide whether a user should create a post based on context, news, identity, and memory.
        This replaces forced post creation with intelligent decision-making.
        """
        import random

        # Base probability starts lower
        base_probability = 0.2

        # Factors that influence posting decision (enhanced for news reactivity)
        factors = {
            'has_recent_news': 0.5,      # Recent news increases posting urge (increased)
            'negative_news_boost': 0.6,   # Negative news creates stronger urge to post (increased)
            'emotional_personality': 0.5, # Emotional personalities react more (increased)
            'user_activity': 0.2,        # Active users post more
            'personality_factor': 0.25,   # Some personas are more vocal (increased)
            'memory_influence': 0.1,      # Recent memories influence posting
            'social_engagement': 0.15     # Following/follower ratio affects posting
        }
        
        # Check recent news exposure and sentiment (users react to news they've seen)
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), p.news_type FROM feed_exposures fe
            JOIN posts p ON fe.post_id = p.post_id
            WHERE fe.user_id = ? AND p.is_news = 1
            AND fe.time_step >= ? - 1
            GROUP BY p.news_type
        """, (user.user_id, step))

        news_exposure = cursor.fetchall()
        has_recent_news = len(news_exposure) > 0
        has_negative_news = any(news_type in ['fake', 'opinion'] for _, news_type in news_exposure)

        # Also check recent news posts in general (even if not in feed_exposures)
        cursor.execute("""
            SELECT COUNT(*), p.news_type FROM posts p
            WHERE p.is_news = 1 AND p.created_at > datetime('now', '-2 hours')
            GROUP BY p.news_type
        """)
        recent_news_general = cursor.fetchall()
        if not has_recent_news and recent_news_general:
            has_recent_news = True
            has_negative_news = any(news_type in ['fake', 'opinion'] for _, news_type in recent_news_general)
        
        # Check user's posting activity
        cursor.execute("""
            SELECT COUNT(*) FROM posts 
            WHERE author_id = ? AND created_at > datetime('now', '-1 hour')
        """, (user.user_id,))
        
        recent_posts = cursor.fetchone()[0]
        is_active_poster = recent_posts < 2  # Don't spam posts
        
        # Check personality (some personas are more vocal and emotional)
        persona = getattr(user, 'persona', {})
        is_vocal_personality = False
        is_emotional_personality = False

        if isinstance(persona, dict):
            background = persona.get('background', '').lower()
            is_vocal_personality = any(trait in background for trait in
                                     ['outspoken', 'activist', 'leader', 'social', 'engaged'])

            # Check for emotional traits
            personality_traits = persona.get('personality_traits', [])
            emotional_keywords = [
                'easily swayed', 'emotional', 'anxious', 'reactive', 'impulsive',
                'quick to react', 'trending topics', 'viral content', 'peer pressure',
                'highly emotional', 'easily influenced', 'sensational', 'triggers emotional'
            ]

            traits_text = ' '.join(personality_traits).lower()
            is_emotional_personality = any(keyword in traits_text for keyword in emotional_keywords)

            # Check communication style for emotional indicators
            comm_style = persona.get('communication_style', {})
            emotional_tones = ['concerned', 'anxious', 'reactive', 'passionate', 'worried']
            is_emotional_personality = is_emotional_personality or comm_style.get('tone', '').lower() in emotional_tones
        else:
            is_vocal_personality = False
            is_emotional_personality = False
        
        # Calculate final probability
        final_probability = base_probability

        if has_recent_news:
            final_probability += factors['has_recent_news']

        # Extra boost for negative news (fake news, controversial content)
        if has_negative_news:
            final_probability += factors['negative_news_boost']

        # Emotional personalities are much more likely to post when exposed to news
        if is_emotional_personality and has_recent_news:
            final_probability += factors['emotional_personality']

        if is_active_poster:
            final_probability += factors['user_activity']

        if is_vocal_personality:
            final_probability += factors['personality_factor']

        # Cap at reasonable maximum (higher for emotional reactions)
        final_probability = min(final_probability, 0.9)
        
        return random.random() < final_probability

    def _get_post_comment_count(self, post_id: str) -> int:
        """Get the number of comments for a post"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT num_comments FROM posts WHERE post_id = ?', (post_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logging.error(f"Failed to get post comment count: {e}")
            return 0

    def _append_truth_to_fake_news_posts(self, feed, step):
        """After time step 5, continuously append corresponding real news to fake posts"""
        try:
            if not feed:
                return feed
            
            if not self.news_manager:
                return feed
            
            # For each post in the feed, if it's trending and has a mapping, append the truth note
            # Use a list to preserve the original order, avoiding index-access errors later
            modified_feed = []
            posts_modified = 0
            
            for post in feed:
                # Check if [OFFICIAL EXPLANATION] already exists to prevent duplicates
                if "[OFFICIAL EXPLANATION]" in post.content:
                    modified_feed.add(post)
                    continue
                
                # Check if it's a trending post (engagement >= a threshold, e.g., 5)
                engagement = (post.num_comments or 0) + (post.num_likes or 0) + (post.num_shares or 0)
                
                # Check if it has a mapping in the truth table
                real_news = self.news_manager.get_real_news_for_post(post.post_id)
                
                if real_news and engagement >= 5:  # Trending post threshold
                    # Append the truth note to the post content
                    truth_note = f"\n\n[OFFICIAL EXPLANATION] This is the OFFICIAL EXPLANATION corresponding to this post: {real_news}"
                    post.content = post.content + truth_note
                    posts_modified += 1
                    logging.debug(f"✅ Time step {step + 1}: appended official explanation to trending post {post.post_id} (engagement: {engagement})")
                
                modified_feed.add(post)
            
            if posts_modified > 0:
                logging.info(f"📊 Time step {step + 1}: appended official explanations to {posts_modified} trending fake news posts")
            
            return modified_feed
            
        except Exception as e:
            logging.error(f"Error while appending truth notes to posts: {e}")
            import traceback
            traceback.print_exc()
            return feed

    def _append_truth_to_fake_news_posts_with_delay(self, feed, step):
        """Append official explanations to fake news posts after a per-post time delay."""
        try:
            if not feed or not self.news_manager:
                return feed

            # Convert to 1-based timestep to align with injection_timestep tracking
            current_timestep = step + 1
            # Minimum delay (in timesteps) between fake news injection and explanation
            # Example: injection at step 2 -> explanations start at step 6 (delay = 4)
            MIN_DELAY_STEPS = 4

            modified_feed = []  # Use a list instead of a set to keep the order
            posts_modified = 0

            for post in feed:
                # Skip if explanation already attached
                if "[OFFICIAL EXPLANATION]" in getattr(post, "content", ""):
                    modified_feed.append(post)
                    continue

                injection_timestep = None
                try:
                    injection_timestep = getattr(self, "fake_news_injection_timesteps", {}).get(post.post_id)

                    # We intentionally avoid falling back to a DB time_step column here,
                    # because some deployments do not have that schema. If the tracker
                    # does not contain an injection_timestep, we simply skip the delay
                    # logic and treat this post as not eligible for timed explanation.
                except Exception as e:
                    logging.error(f"Failed to get injection timestep for post {post.post_id}: {e}")
                    injection_timestep = None

                # If we know when this fake news was injected, enforce per-post delay
                if injection_timestep is not None:
                    if current_timestep - injection_timestep < MIN_DELAY_STEPS:
                        modified_feed.append(post)
                        continue

                # Compute engagement: likes + comments + shares
                engagement = (getattr(post, "num_comments", 0) or 0) + \
                             (getattr(post, "num_likes", 0) or 0) + \
                             (getattr(post, "num_shares", 0) or 0)

                # Check if there is mapped real news
                real_news = self.news_manager.get_real_news_for_post(post.post_id)

                if real_news:
                    truth_note = (
                        "\n\n[OFFICIAL EXPLANATION] "
                        f": {real_news}"
                    )
                    new_content = (post.content or "") + truth_note
                    post.content = new_content
                    
                    # Save the appended content back to the database
                    try:
                        from database.database_manager import execute_query
                        update_success = execute_query(
                            'UPDATE posts SET content = ? WHERE post_id = ?',
                            (new_content, post.post_id)
                        )
                        if update_success:
                            logging.debug(
                                f"✅ timestep {current_timestep}: appended and saved official explanation to post {post.post_id} "
                                f"(engagement: {engagement}, injection_timestep: {injection_timestep})"
                            )
                        else:
                            logging.warning(
                                f"⚠️ timestep {current_timestep}: failed to save official explanation to database for post {post.post_id}"
                            )
                    except Exception as e:
                        logging.error(f"Error saving official explanation to database for post {post.post_id}: {e}")
                    
                    posts_modified += 1

                modified_feed.append(post)

            if posts_modified > 0:
                logging.info(
                    f"✅ timestep {current_timestep}: appended official explanations to "
                    f"{posts_modified} fake news posts"
                )

            return modified_feed

        except Exception as e:
            logging.error(f"Error while appending truth notes with delay: {e}")
            import traceback
            traceback.print_exc()
            return feed

    async def _check_comment_based_interventions(self, user_id: str, step: int):
        """Deprecated: replaced by batch attacks; retained as a no-op for compatibility."""
        return
