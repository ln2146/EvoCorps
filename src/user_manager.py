from agent_user import AgentUser
from utils import Utils
import random
import jsonlines
import json
import logging
import time
import os
from database_manager import DatabaseManager
class UserManager:
    def __init__(self, config: dict, db_manager: DatabaseManager):
        self.experiment_config = config
        self.num_users = config['num_users']
        self.db_manager = db_manager
        self.conn = db_manager.get_connection()
        # Simplified user selection mechanism
        self.current_user_index = 0
        self.all_user_configs = None
        self.used_configs = set()  # Maintain compatibility
        self.users = self.create_users()
        
    def load_agent_configs(self):
        """Load agent configurations either from a JSONL file or generate them dynamically."""
        try:
            generation_method = self.experiment_config.get('agent_config_generation', 'file')
            
            if generation_method == 'file':
                # Load all configs if not already loaded
                if self.all_user_configs is None:
                    config_file = self.experiment_config.get('agent_config_path')
                    if not config_file:
                        raise ValueError("No agent_config_path specified in experiment config")
                    
                    self.all_user_configs = self._load_persona_file(config_file)
                
                # Reset if we've used all configs
                if len(self.used_configs) >= len(self.all_user_configs):
                    self.used_configs.clear()
                
                # Select configs sequentially instead of randomly
                num_to_sample = min(self.num_users, len(self.all_user_configs))

                # Select in order starting from the current index
                configs = []
                for i in range(num_to_sample):
                    config_index = (self.current_user_index + i) % len(self.all_user_configs)
                    configs.append(self.all_user_configs[config_index])
                    self.used_configs.add(config_index)

                # Update the current index
                self.current_user_index = (self.current_user_index + num_to_sample) % len(self.all_user_configs)

                print(f"🎭 Selecting users {self.current_user_index-num_to_sample+1}-{self.current_user_index} in sequence (gradual emotional evolution)")
                
            # elif generation_method == 'agent_bank':
            #     from agent_config_generator_persona import generate_agent_configs_agent_bank
            #     configs = generate_agent_configs_agent_bank(num_agents=self.num_users)
                
            # elif generation_method == 'fine_persona':
            #     from agent_config_generator_persona import generate_agent_configs_fine_persona
            #     configs = generate_agent_configs_fine_persona(num_agents=self.num_users)
                
            # elif generation_method == 'simple':
            #     from agent_config_generator_persona import generate_agent_configs_simple
            #     configs = generate_agent_configs_simple(num_agents=self.num_users)
                
            else:
                raise ValueError(f"Unknown agent config generation method: {generation_method}")
            
            # Standardize all configs to ensure consistent format
            standardized_configs = []
            for config in configs:
                standardized_config = {
                    'background_labels': {},
                    'persona': {},
                }
                
                # Handle background information
                standardized_config['background_labels'] = {
                    **{k:v for k,v in config.items()
                    if k not in ['persona', 'id']}
                }
                
                # Handle persona information
                if 'persona' in config:
                    standardized_config['persona'] = config['persona']
                else:
                    logging.warning("No persona found in config")
                
                standardized_configs.append(standardized_config)
            
            logging.info(f"Generated {len(standardized_configs)} agent configurations using {generation_method} method")
            return standardized_configs
                
        except Exception as e:
            logging.error(f"Error loading/generating agent configs: {str(e)}")
            raise
    
    def _load_persona_file(self, config_file: str):
        """Load persona configurations from various file types with support for separate positive/negative personas."""
        try:
            # Check if the config requests separate persona files
            if config_file == "separate" or "separate" in config_file.lower():
                return self._load_separate_personas()
            
            # Check if the file exists
            if not os.path.exists(config_file):
                # Try backup file paths
                backup_files = [
                    "personas/extreme_personas.jsonl", 
                    "personas/personas_from_prolific_description.jsonl"
                ]
                
                for backup_file in backup_files:
                    if os.path.exists(backup_file):
                        logging.warning(f"Original file {config_file} not found, using backup: {backup_file}")
                        config_file = backup_file
                        break
                else:
                    raise FileNotFoundError(f"Persona file not found: {config_file}")
            
            # Load JSONL file
            with jsonlines.open(config_file) as reader:
                personas = list(reader)
            
            logging.info(f"Loaded {len(personas)} personas from {config_file}")
            return personas
            
        except Exception as e:
            logging.error(f"Error loading persona file {config_file}: {str(e)}")
            raise
    
    def _load_separate_personas(self):
        """Load personas - normal users only use neutral personas, while bots can use positive/negative."""
        all_personas = []

        # Retrieve sampling ratios and file paths from the configuration
        separate_config = self.experiment_config.get('separate_personas', {})
        neutral_file = separate_config.get('neutral_file', "personas/neutral_personas_database.json")

        # Calculate the required user count
        total_users = self.experiment_config.get('num_users', 3)

        # Regular users exclusively use neutral personas
        num_neutral = total_users
        num_positive = 0  # Regular users do not use positive personas
        num_negative = 0  # Regular users do not use negative personas

        # Only load neutral personas for regular users
        if os.path.exists(neutral_file):
            try:
                with open(neutral_file, 'r', encoding='utf-8') as f:
                    neutral_personas = json.load(f)

                # Randomly sample neutral personas and convert format
                selected_neutral = neutral_personas

                # Convert to the expected format
                for persona in selected_neutral:
                    formatted_persona = {
                    'persona': persona,  # Store the complete persona data under the 'persona' key
                        'background_labels': {
                            'type': persona.get('type', 'neutral'),
                            'profession': persona.get('demographics', {}).get('profession', ''),
                            'age_range': persona.get('demographics', {}).get('age', ''),
                            'education': persona.get('demographics', {}).get('education', ''),
                            'region': persona.get('demographics', {}).get('region', '')
                        }
                    }
                    all_personas.append(formatted_persona)

                logging.info(f"Loaded {len(selected_neutral)} neutral personas for normal users")

            except Exception as e:
                logging.warning(f"Failed to load neutral personas: {str(e)}")
        else:
            logging.warning(f"Neutral personas file not found: {neutral_file}")

        # If no personas were loaded, fall back to the default file
        if not all_personas:
            logging.warning("No separate personas loaded, falling back to default file")
            default_file = "personas/personas_from_prolific_description.jsonl"
            if os.path.exists(default_file):
                with jsonlines.open(default_file) as reader:
                    all_personas = list(reader)

        # Decide whether to shuffle based on the configuration
        # Keep them ordered: no longer shuffling

        logging.info(f"Loaded {len(all_personas)} neutral personas total for normal users (all neutral: {num_neutral})")
        return all_personas
    
    def create_users(self):
        """Create users and register them in the database using configs."""
        users = []
        
        try:
            configs = self.load_agent_configs()
            total_users = len(configs)
            print(f"👥 Creating {total_users} users...")
            
            for i, user_config in enumerate(configs, 1):
                # Display the progress bar
                progress = i / total_users
                bar_length = 30
                filled_length = int(bar_length * progress)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                percentage = int(progress * 100)
                print(f"\r👥 User creation progress: [{bar}] {percentage}% ({i}/{total_users})", end='', flush=True)
                
                user_id = Utils.generate_formatted_id("user")
                self.db_manager.add_user(user_id, user_config)
                user = AgentUser(
                    user_id=user_id,
                    user_config=user_config,
                    temperature=self.experiment_config['temperature'],
                    experiment_config=self.experiment_config,
                    db_connection=self.db_manager.get_connection()
                )
                users.append(user)
            
            # Finalize the progress bar
            print(f"\r👥 User creation progress: [{'█' * 30}] 100% ({total_users}/{total_users})")
            print()  # newline
            
            cursor = self.conn.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"✅ Successfully created {count} users")
            
        except Exception as e:
            logging.error(f"Error creating users: {str(e)}")
            # ServiceConnection does not provide rollback; the service mode handles transactions automatically
            raise
        
        return users
        
    def create_initial_follows(self):
        """Create initial follow relationships between users based on Barabási-Albert model.
        
        This implements a preferential attachment model where:
        1. We start with a small initial connected network
        2. New connections are made with probability proportional to node degree
        """
        # Parameters
        m0 = min(5, len(self.users))  # Initial complete network size
        m = min(3, len(self.users) - m0)  # New edges per node
        
        if len(self.users) <= 1:
            logging.warning("Not enough users to create a network")
            return
        
        follow_count = 0
        total_users = len(self.users)
        print(f"🔗 Building user follow relationships...")

        # Estimate the number of follow edges to create
        remaining_users = self.users[m0:]
        expected_total = m0 * (m0 - 1) + (len(remaining_users) * m if m > 0 else 0)
        expected_total = max(expected_total, 1)  # Avoid division by zero

        def _print_progress():
            bar_length = 30
            ratio = min(1.0, follow_count / expected_total)
            filled_length = int(bar_length * ratio)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            percentage = int(ratio * 100)
            print(f"\r🔗 Follow creation: [{bar}] {percentage}% ({follow_count}/{expected_total})", end='', flush=True)
            
        # Step 1: Create initial connected network with m0 nodes
        initial_users = self.users[:m0]
        for i, user in enumerate(initial_users):
            for j in range(i+1, len(initial_users)):
                other_user = initial_users[j]
                user.follow_user(other_user.user_id)
                other_user.follow_user(user.user_id)
                follow_count += 2  # Each pair creates 2 follows
                _print_progress()
        
        # Step 2: Add remaining nodes with preferential attachment
        if m > 0:  # Only proceed if we have parameters for preferential attachment
            for user_idx, new_user in enumerate(remaining_users, 1):
                # Calculate current degree distribution
                user_degrees = {}
                for user in self.users:
                    # Get number of followers for each user
                    cursor = self.conn.execute("SELECT COUNT(*) FROM follows WHERE followed_id = ?", (user.user_id,))
                    followers_count = cursor.fetchone()[0]
                    # Add 1 to avoid zero probability for new nodes
                    user_degrees[user.user_id] = followers_count + 1
                
                # Remove users that are already being followed to avoid duplicates
                cursor = self.conn.execute("SELECT followed_id FROM follows WHERE follower_id = ?", (new_user.user_id,))
                already_following = [row[0] for row in cursor.fetchall()]
                for user_id in already_following:
                    if user_id in user_degrees:
                        del user_degrees[user_id]
                
                # Skip if no available users to follow
                if not user_degrees:
                    continue
                
                # Select m users to follow based on preferential attachment
                total_degree = sum(user_degrees.values())
                available_users = list(user_degrees.keys())
                probabilities = [user_degrees[uid]/total_degree for uid in available_users]
                
                # Select users to follow (without replacement)
                users_to_follow = []
                for _ in range(min(m, len(available_users))):
                    if not available_users:
                        break
                    # Choose based on probability
                    chosen_idx = random.choices(range(len(available_users)), weights=probabilities, k=1)[0]
                    chosen_user_id = available_users.pop(chosen_idx)
                    probabilities.pop(chosen_idx)
                    users_to_follow.append(chosen_user_id)
                
                # Create follow relationships
                for user_id in users_to_follow:
                    new_user.follow_user(user_id)
                    follow_count += 1
                    _print_progress()

        # Complete the progress bar (overwrite the line and add newline)
        print(f"\r🔗 Follow creation: [{'█' * 30}] 100% ({follow_count}/{expected_total})")
        print()  # newline
        
        print(f"✅ Created {follow_count} follow relationships")
        
    def add_random_users(self, num_users_to_add: int = 1, follow_probability: float = 0.0):
        """Add new random users to the simulation with balanced persona distribution."""
        new_users = []

        # Check whether we're using the separate personas mode
        agent_config_path = self.experiment_config.get('agent_config_path', 'N/A')

        if agent_config_path == "separate":
            # Separate mode: generate positive, neutral, and negative users in proportion
            new_users = self._add_users_separate_mode(num_users_to_add)
        else:
            # Traditional mode: randomly select from the configuration file
            new_users = self._add_users_traditional_mode(num_users_to_add)

        # Establish follow relationships for new users
        for user in new_users:
            self._establish_follows_for_new_user(user, follow_probability)

        # Add to the users list
        self.users.extend(new_users)

        # recordlog
        logging.info(f"✅ Added {len(new_users)} users to the simulation (total users: {len(self.users)})")

        # Log the distribution of new user classes
        self._log_new_users_distribution(new_users)

        # Log user growth statistics
        self._log_user_growth_stats(len(new_users))

    def _add_users_separate_mode(self, num_users_to_add: int) -> list:
        """Add users in separate mode - regular users only use neutral personas"""
        new_users = []

        # Regular users all use neutral personas
        num_neutral = num_users_to_add
        num_positive = 0  # Regular users do not use positive personas
        num_negative = 0  # Regular users do not use negative personas

        # Fetch configuration settings
        separate_config = self.experiment_config.get('separate_personas', {})

        # Load neutral personas from the database
        neutral_personas = self._load_personas_from_file(separate_config.get('neutral_file', 'personas/neutral_personas_database.json'))

        # Create neutral users - select sequentially instead of randomly
        for _ in range(num_neutral):
            if neutral_personas:
                # Select personas sequentially for gradual sentiment evolution
                persona = neutral_personas[self.current_user_index % len(neutral_personas)]
                self.current_user_index += 1
                user = self._create_user_from_persona(persona, "neutral")
                new_users.append(user)

        return new_users

    def _add_users_traditional_mode(self, num_users_to_add: int) -> list:
        """Add new users using the traditional mode"""
        new_users = []
        user_configs = self.load_agent_configs()

        for _ in range(num_users_to_add):
            time.sleep(0.1)
            user_config = random.choice(user_configs)
            user_id = Utils.generate_formatted_id("user")
            user = AgentUser(
                user_id=user_id,
                user_config=user_config,
                temperature=self.experiment_config['temperature'],
                experiment_config=self.experiment_config,
                db_connection=self.db_manager.get_connection()
            )
            new_users.append(user)

            # Add to database
            self.db_manager.add_user(user_id, user_config)
            logging.info(f"Added new user {user_id} to the simulation")

        return new_users

    def _load_personas_from_file(self, file_path: str) -> list:
        """Load persona data from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get('personas', [])
        except Exception as e:
            logging.warning(f"Unable to load persona file {file_path}: {e}")
            return []

    def _create_user_from_persona(self, persona: dict, persona_type: str):
        """Create a user from persona data"""
        user_id = Utils.generate_formatted_id("user")

        # Convert persona format into a user configuration - keep it consistent
        user_config = {
            "persona": persona,  # Store the complete persona dict, not just the name
            "background_labels": {
                "type": persona_type,
                "profession": persona.get("demographics", {}).get("profession", "Unknown"),
                "age_range": persona.get("demographics", {}).get("age", "26-35"),
                "education": persona.get("demographics", {}).get("education", ""),
                "region": persona.get("demographics", {}).get("region", "")
            }
        }

        user = AgentUser(
            user_id=user_id,
            user_config=user_config,
            temperature=self.experiment_config['temperature'],
            experiment_config=self.experiment_config,
            db_connection=self.db_manager.get_connection()
        )

        # Add to database
        self.db_manager.add_user(user_id, user_config)
        logging.info(f"Created new user {user_id} ({persona_type}): {persona.get('name', 'Unknown')}")

        return user

    def _establish_follows_for_new_user(self, user, follow_probability: float):
        """Establish follow relationships for a new user"""
        follows_created = 0
        followers_gained = 0

        for existing_user in self.users:
            # New user follows existing users
            if random.random() < follow_probability:
                user.follow_user(existing_user.user_id)
                follows_created += 1

            # Existing users follow the new user
            if random.random() < follow_probability:
                existing_user.follow_user(user.user_id)
                followers_gained += 1

        # Removed verbose individual user follow logging

    def _log_new_users_distribution(self, new_users: list):
        """Log the class-type distribution of new users"""
        if not new_users:
            return

        # Count users by class type
        type_counts = {}
        for user in new_users:
            user_type = getattr(user, 'user_config', {}).get('persona_type', 'unknown')
            type_counts[user_type] = type_counts.get(user_type, 0) + 1

        if type_counts:
            logging.info(f"New user class distribution: {dict(type_counts)}")

    def _log_user_growth_stats(self, new_users_count: int):
        """Log user growth statistics"""
        initial_users = self.experiment_config.get('num_users', 4)
        current_total = len(self.users)
        growth_multiple = current_total / initial_users

        logging.info(f"📊 User growth statistics:")
        logging.info(f"   Initial user count: {initial_users}")
        logging.info(f"   Current user count: {current_total}")
        logging.info(f"   Users added this round: {new_users_count}")
