import os
import logging
import sqlite3
import time
import shutil
import json
from typing import Dict, List
import requests


class ServiceConnection:
    """Simulate sqlite3 connection via HTTP requests to the database service"""
    
    def __init__(self, service_url: str):
        self.service_url = service_url
        self.row_factory = None
        self._current_cursor = None
        self.description = None  # Add description attribute
    
    def execute(self, query: str, params: tuple = ()):
        """Execute SQL query"""
        try:
            response = requests.post(f"{self.service_url}/execute", json={
                'query': query,
                'params': list(params)
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    columns = result.get('columns', [])
                    # Set description attribute
                    self.description = [(col, None, None, None, None, None, None) for col in columns] if columns else None
                    
                    if result.get('data'):
                        # Return simulated cursor object
                        self._current_cursor = ServiceCursor(result.get('data', []), columns)
                        return self._current_cursor
                    else:
                        # Non-SELECT query
                        self._current_cursor = ServiceCursor([], columns)
                        return self._current_cursor
                else:
                    raise Exception(result.get('error', 'Unknown error'))
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logging.error(f"Database service request failed: {e}")
            raise
    
    def cursor(self):
        """Return cursor object (compatibility method)"""
        # Return a ServiceCursor object that can execute via execute()
        return ServiceCursor([], [], self.service_url)
    
    def fetchone(self):
        """Fetch one row (compatibility method)"""
        if self._current_cursor:
            return self._current_cursor.fetchone()
        return None
    
    def fetchall(self):
        """Fetch all rows (compatibility method)"""
        if self._current_cursor:
            return self._current_cursor.fetchall()
        return []
    
    def commit(self):
        """Commit transaction (auto-commit in service mode)"""
        pass
    
    def rollback(self):
        """Rollback transaction (handled automatically in service mode)"""
        pass
    
    def close(self):
        """Close connection (no-op in service mode)"""
        pass


class ServiceCursor:
    """Simulate sqlite3 cursor object"""
    
    def __init__(self, data: List, columns: List, service_url: str = "http://127.0.0.1:5000"):
        self.data = data
        self.columns = columns
        self.index = 0
        self.service_url = service_url
        self.lastrowid = None  # Add lastrowid attribute
        # Set description attribute
        self.description = [(col, None, None, None, None, None, None) for col in columns] if columns else None
    
    def execute(self, query: str, params: tuple = ()):
        """Execute SQL query"""
        try:
            import requests
            response = requests.post(f"{self.service_url}/execute", json={
                'query': query,
                'params': list(params)
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    columns = result.get('columns', [])
                    # Update description attribute
                    self.description = [(col, None, None, None, None, None, None) for col in columns] if columns else None
                    
                    # Update lastrowid attribute
                    self.lastrowid = result.get('lastrowid', None)
                    
                    if result.get('data'):
                        # Update data
                        self.data = result.get('data', [])
                        self.columns = columns
                        self.index = 0
                        return self
                    else:
                        # Non-SELECT query
                        self.data = []
                        self.columns = columns
                        self.index = 0
                        return self
                else:
                    raise Exception(result.get('error', 'Unknown error'))
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            import logging
            logging.error(f"Database service request failed: {e}")
            raise
    
    def fetchone(self):
        """Fetch one row"""
        if self.index < len(self.data):
            row = self.data[self.index]
            self.index += 1
            return ServiceRow(row, self.columns)
        return None
    
    def fetchall(self):
        """Fetch all rows"""
        result = self.data[self.index:]
        self.index = len(self.data)
        return [ServiceRow(row, self.columns) for row in result]
    
    def __iter__(self):
        """Support iteration"""
        return iter([ServiceRow(row, self.columns) for row in self.data])
    
    def executemany(self, query: str, params_list: List[tuple]):
        """Execute batch SQL queries"""
        try:
            import requests
            response = requests.post(f"{self.service_url}/executemany", json={
                'query': query,
                'params_list': [list(params) for params in params_list]
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    columns = result.get('columns', [])
                    # Update description attribute
                    self.description = [(col, None, None, None, None, None, None) for col in columns] if columns else None
                    
                    # Update lastrowid attribute
                    self.lastrowid = result.get('lastrowid', None)
                    
                    # Update data
                    self.data = result.get('data', [])
                    self.columns = columns
                    self.index = 0
                    return self
                else:
                    raise Exception(result.get('error', 'Unknown error'))
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            import logging
            logging.error(f"Database service batch request failed: {e}")
            raise
    
    def close(self):
        """Close cursor (no-op in service mode)"""
        pass


class ServiceRow:
    """Simulate sqlite3 row object with dict interface"""
    
    def __init__(self, row_data: List, columns: List):
        self.row_data = row_data
        self.columns = columns
    
    def values(self):
        """Return list of row values"""
        return self.row_data
    
    def __getitem__(self, key):
        """Support index access"""
        if isinstance(key, int):
            return self.row_data[key]
        elif isinstance(key, str):
            if key in self.columns:
                return self.row_data[self.columns.index(key)]
            else:
                raise KeyError(f"Column '{key}' not found")
        else:
            raise TypeError("Invalid key type")
    
    def __iter__(self):
        """Support iteration"""
        return iter(self.row_data)
    
    def __len__(self):
        """Return number of columns"""
        return len(self.row_data)

class DatabaseManager:
    def __init__(self, db_path: str, reset_db: bool = True, use_service: bool = True, service_url: str = "http://127.0.0.1:5000"):
        self.db_path = db_path
        self.reset_db = reset_db
        self.use_service = use_service
        self.service_url = service_url
        self.conn = None

        if self.use_service:
            # Use database service
            self._init_service_connection()
        else:
            # Use direct database connection
            self._init_direct_connection()

        if self.reset_db:
            self.reset_database()
    
    def _init_service_connection(self):
        """Initialize service connection"""
        try:
            # Check if service is available
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                logging.info(f"✅ Using database service: {self.service_url}")
                # Create virtual connection for compatibility
                self.conn = ServiceConnection(self.service_url)
            else:
                logging.warning("⚠️ Database service unavailable, falling back to direct connection")
                self._init_direct_connection()
        except Exception as e:
            logging.warning(f"⚠️ Database service connection failed: {e}, falling back to direct connection")
            self._init_direct_connection()
    
    def _init_direct_connection(self):
        """Initialize direct database connection"""
        try:
            # Ensure database directory exists
            import os
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # If database is locked, wait and retry
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    # Use longer timeout
                    self.conn = sqlite3.connect(self.db_path, timeout=60.0)
                    # Use more relaxed locking settings
                    self.conn.execute("PRAGMA journal_mode=DELETE")  # Use DELETE mode to avoid WAL locks
                    self.conn.execute("PRAGMA synchronous=NORMAL")   # Reduce sync requirements
                    self.conn.execute("PRAGMA temp_store=MEMORY")    # Store temporary data in memory
                    self.conn.execute("PRAGMA cache_size=10000")     # Increase cache

                    # Test connection
                    self.conn.execute("SELECT 1").fetchone()
                    logging.info(f"✅ Using file database: {self.db_path} ")
                    break

                except sqlite3.OperationalError as e:
                    if attempt < max_attempts - 1:
                        logging.warning(f"⚠️  Database connect failed, retry {attempt + 1}/{max_attempts}: {e}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise e

        except Exception as e:
            logging.error(f"❌ Unable to connect to database: {e}")
            # Last resort: create new database file
            try:
                backup_path = f"{self.db_path}.backup_{int(time.time())}"
                if os.path.exists(self.db_path):
                    shutil.move(self.db_path, backup_path)
                    logging.warning(f"⚠️  Original database backed up to: {backup_path}")

                self.conn = sqlite3.connect(self.db_path, timeout=60.0)
                # Apply same settings as normal initialization
                self.conn.execute("PRAGMA journal_mode=DELETE")
                self.conn.execute("PRAGMA synchronous=NORMAL")
                self.conn.execute("PRAGMA temp_store=MEMORY")
                self.conn.execute("PRAGMA cache_size=10000")
                logging.info(f"✅ Created new database: {self.db_path}")
            except Exception as final_e:
                logging.error(f"❌ Unable to create new database: {final_e}")
                raise final_e

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Initialize database
        if self.reset_db:
            self.reset_database()
        else:
            self.create_tables()

    def reset_database(self):
        """Reset the database and create new tables."""
        logging.info("Resetting database...")

        try:
            if self.use_service:
                # Reset database via service
                response = requests.post(f"{self.service_url}/reset_database", timeout=30)
                if response.status_code == 200:
                    logging.info("Database reset via service.")
                    # Recreate tables
                    self.create_tables()
                else:
                    raise Exception(f"Service reset failed: {response.text}")
            else:
                # Direct connection mode
                # Close the existing connection
                self.conn.close()

                # Remove existing database file and any related files
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                    logging.info("Existing database removed.")

                # Also remove WAL and SHM files if they exist
                for suffix in ['-wal', '-shm', '-journal']:
                    aux_file = self.db_path + suffix
                    if os.path.exists(aux_file):
                        os.remove(aux_file)
                        logging.info(f"Removed auxiliary file: {aux_file}")

                logging.info("No existing database found." if not os.path.exists(self.db_path) else "Database cleaned.")

                # Recreate the connection with proper settings
                self.conn = sqlite3.connect(self.db_path, timeout=60.0)
                self.conn.execute("PRAGMA journal_mode=DELETE")
                self.conn.execute("PRAGMA synchronous=NORMAL")
                self.conn.execute("PRAGMA temp_store=MEMORY")
                self.conn.execute("PRAGMA cache_size=10000")
                self.conn.execute("PRAGMA foreign_keys = ON")

                self.create_tables()
                logging.info("New tables created.")

        except Exception as e:
            logging.error(f"Error resetting database: {str(e)}")
            raise

    def create_tables(self):
        """Create the database tables."""
        cursor = self.conn.cursor()

        if self.reset_db:
            # Disable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Drop tables in reverse order of dependencies
            cursor.execute("DROP TABLE IF EXISTS agent_responses")
            cursor.execute("DROP TABLE IF EXISTS opinion_interventions")
            cursor.execute("DROP TABLE IF EXISTS opinion_monitoring")
            cursor.execute("DROP TABLE IF EXISTS malicious_comments")
            cursor.execute("DROP TABLE IF EXISTS malicious_attacks")
            cursor.execute("DROP TABLE IF EXISTS spread_metrics")
            cursor.execute("DROP TABLE IF EXISTS feed_exposures")
            cursor.execute("DROP TABLE IF EXISTS note_ratings")
            cursor.execute("DROP TABLE IF EXISTS community_notes")
            cursor.execute("DROP TABLE IF EXISTS moderation_logs")
            cursor.execute("DROP TABLE IF EXISTS fact_checks")
            cursor.execute("DROP TABLE IF EXISTS comments")
            cursor.execute("DROP TABLE IF EXISTS agent_memories")
            cursor.execute("DROP TABLE IF EXISTS user_actions")
            cursor.execute("DROP TABLE IF EXISTS follows")
            cursor.execute("DROP TABLE IF EXISTS posts")
            cursor.execute("DROP TABLE IF EXISTS users")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")

        # Create tables
        tables = {
            'users': '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    persona TEXT,
                    background_labels JSON,
                    creation_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    follower_count INTEGER DEFAULT 0,
                    total_likes_received INTEGER DEFAULT 0,
                    total_shares_received INTEGER DEFAULT 0,
                    total_comments_received INTEGER DEFAULT 0,
                    influence_score FLOAT DEFAULT 0.0,
                    is_influencer BOOLEAN DEFAULT FALSE,
                    last_influence_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'posts': '''
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    summary TEXT,
                    author_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    num_likes INTEGER DEFAULT 0,
                    num_shares INTEGER DEFAULT 0,
                    num_flags INTEGER DEFAULT 0,
                    num_comments INTEGER DEFAULT 0,
                    original_post_id TEXT,
                    is_news BOOLEAN DEFAULT FALSE,
                    news_type TEXT,
                    status TEXT CHECK(status IN ('active', 'taken_down')),
                    takedown_timestamp TIMESTAMP,
                    takedown_reason TEXT,
                    fact_check_status TEXT,
                    fact_checked_at TIMESTAMP,
                    is_agent_response BOOLEAN DEFAULT FALSE,
                    agent_role TEXT,
                    agent_response_type TEXT,
                    intervention_id INTEGER,
                    selected_model TEXT DEFAULT 'unknown',
                    agent_type TEXT DEFAULT 'normal',
                    FOREIGN KEY (author_id) REFERENCES users(user_id),
                    FOREIGN KEY (original_post_id) REFERENCES posts(post_id)
                )
            ''',
            'moderation_logs': '''
            CREATE TABLE IF NOT EXISTS moderation_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    action_type TEXT,
                    reason TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'community_notes': '''
                CREATE TABLE IF NOT EXISTS community_notes (
                    note_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    helpful_ratings INTEGER DEFAULT 0,
                    not_helpful_ratings INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id),
                    FOREIGN KEY (author_id) REFERENCES users(user_id)
                )
            ''',
            'note_ratings': '''
                CREATE TABLE IF NOT EXISTS note_ratings (
                    note_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    rating TEXT CHECK(rating IN ('helpful', 'not_helpful')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (note_id, user_id),
                    FOREIGN KEY (note_id) REFERENCES community_notes(note_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''',
            'user_actions': '''
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_id TEXT,
                    content TEXT,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''',
            'follows': '''
                CREATE TABLE IF NOT EXISTS follows (
                    follower_id TEXT NOT NULL,
                    followed_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (follower_id, followed_id),
                    FOREIGN KEY (follower_id) REFERENCES users(user_id),
                    FOREIGN KEY (followed_id) REFERENCES users(user_id)
                )
            ''',
            'comments': '''
                CREATE TABLE IF NOT EXISTS comments (
                    comment_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    num_likes INTEGER DEFAULT 0,
                    selected_model TEXT DEFAULT 'unknown',
                    agent_type TEXT DEFAULT 'normal',
                    FOREIGN KEY (post_id) REFERENCES posts(post_id),
                    FOREIGN KEY (author_id) REFERENCES users(user_id)
                )
            ''',
            'agent_memories': '''
                CREATE TABLE IF NOT EXISTS agent_memories (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decay_factor FLOAT DEFAULT 1.0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''',
            'spread_metrics': '''
                CREATE TABLE IF NOT EXISTS spread_metrics (
                    post_id TEXT NOT NULL,
                    time_step INTEGER NOT NULL,
                    views INTEGER NOT NULL,
                    diffusion_depth INTEGER NOT NULL,
                    num_likes INTEGER NOT NULL,
                    num_shares INTEGER NOT NULL,
                    num_flags INTEGER NOT NULL,
                    num_comments INTEGER NOT NULL,
                    num_notes INTEGER NOT NULL,
                    num_note_ratings INTEGER NOT NULL,
                    total_interactions INTEGER NOT NULL,
                    should_takedown BOOLEAN,
                    takedown_reason TEXT,
                    takedown_executed BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (post_id, time_step),
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'feed_exposures': '''
                CREATE TABLE IF NOT EXISTS feed_exposures (
                    user_id TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    time_step INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, post_id, time_step),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'post_timesteps': '''
                CREATE TABLE IF NOT EXISTS post_timesteps (
                    post_id TEXT PRIMARY KEY,
                    time_step INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'comment_timesteps': '''
                CREATE TABLE IF NOT EXISTS comment_timesteps (
                    comment_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    post_id TEXT,
                    time_step INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'fact_checks': '''
                CREATE TABLE IF NOT EXISTS fact_checks (
                    post_id TEXT NOT NULL,
                    checker_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    sources TEXT NOT NULL,
                    groundtruth TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (post_id),
                    FOREIGN KEY (post_id) REFERENCES posts(post_id)
                )
            ''',
            'malicious_attacks': '''
                CREATE TABLE IF NOT EXISTS malicious_attacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_post_id TEXT,
                    target_user_id TEXT,
                    attack_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cluster_size INTEGER,
                    successful_attacks INTEGER,
                    attack_details TEXT,
                    triggered_intervention BOOLEAN DEFAULT FALSE
                )
            ''',
            'malicious_comments': '''
                CREATE TABLE IF NOT EXISTS malicious_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attack_id INTEGER,
                    comment_id TEXT,
                    content TEXT,
                    persona_used TEXT,
                    attack_type TEXT,
                    intensity_level TEXT,
                    selected_model TEXT DEFAULT 'unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (attack_id) REFERENCES malicious_attacks (id)
                )
            ''',
            'opinion_monitoring': '''
                CREATE TABLE IF NOT EXISTS opinion_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    content TEXT,
                    extremism_level INTEGER,
                    sentiment TEXT,
                    requires_intervention BOOLEAN,
                    monitoring_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'opinion_interventions': '''
                CREATE TABLE IF NOT EXISTS opinion_interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_post_id INTEGER,
                    action_id TEXT,
                    strategy_id TEXT,
                    leader_response_id INTEGER,
                    intervention_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    effectiveness_score REAL
                )
            ''',
            'agent_responses': '''
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
            '''
        }

        for table_name, create_statement in tables.items():
            cursor.execute(create_statement)

        # Optional database migration: add new fields only when needed
        # self._migrate_database(cursor)  # Temporarily disable forced migration

        self.conn.commit()
        logging.info("Database tables created successfully.")

    def _migrate_database(self, cursor):
        """Database migration: add new fields to existing tables"""
        migrations = [
            # Add selected_model and agent_type to comments table
            {
                'table': 'comments',
                'column': 'selected_model',
                'definition': 'TEXT DEFAULT "unknown"'
            },
            {
                'table': 'comments',
                'column': 'agent_type',
                'definition': 'TEXT DEFAULT "normal"'
            },
            # Add selected_model and agent_type to posts table
            {
                'table': 'posts',
                'column': 'selected_model',
                'definition': 'TEXT DEFAULT "unknown"'
            },
            {
                'table': 'posts',
                'column': 'agent_type',
                'definition': 'TEXT DEFAULT "normal"'
            },
            # Add selected_model to malicious_comments table
            {
                'table': 'malicious_comments',
                'column': 'selected_model',
                'definition': 'TEXT DEFAULT "unknown"'
            }
        ]

        for migration in migrations:
            try:
                # Check if column exists
                cursor.execute(f"SELECT {migration['column']} FROM {migration['table']} LIMIT 1")
            except Exception as e:
                # Column doesn't exist, add it
                print(f"🔧 Adding column {migration['column']} to table {migration['table']}...")
                cursor.execute(f"ALTER TABLE {migration['table']} ADD COLUMN {migration['column']} {migration['definition']}")
                print(f"✅ Column {migration['column']} added successfully")

    def save_simulation_db(self, timestamp: str):
        """Save a timestamped copy of the simulation database."""
        if self.use_service:
            # In service mode, cannot copy file directly
            logging.warning("Service mode cannot copy database file; skipping backup")
            return
        
        # Original logic for direct connection mode
        # Close the connection to ensure all data is written
        self.conn.close()

        # Create archive directory if it doesn't exist
        archive_dir = f"experiment_outputs/database_copies"
        os.makedirs(archive_dir, exist_ok=True)

        # Copy the database file
        archived_db = f"{archive_dir}/{timestamp}.db"
        shutil.copy2(self.db_path, archived_db)
        logging.info(f"Saved simulation database to {archived_db}")


    def add_user(self, user_id: str, user_config: dict):
        """Add a new user to the database.

        Args:
            user_id: Unique identifier for the user
            user_config: Standardized user configuration containing:
                - background_labels: Dict of arbitrary user attributes
                - persona: Dict with 'background' and 'labels' keys
        """
        # Convert background labels to JSON string
        background_labels = user_config.get('background_labels', {})

        # Add retry for temporary I/O errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.conn.execute('''
                    INSERT INTO users (
                        user_id,
                        persona,
                        background_labels
                    )
                    VALUES (?, ?, ?)
                ''', (
                    user_id,
                    str(user_config['persona']),
                    json.dumps(background_labels)
                ))

                self.conn.commit()
                # Use a simple emoji-based counter instead of verbose logging
                pass  # Removed verbose logging
                return  # Successful, exit retry loop

            except Exception as e:
                if "disk I/O error" in str(e) and attempt < max_retries - 1:
                    logging.warning(f"Disk I/O error on attempt {attempt + 1}, retrying...")
                    import time
                    time.sleep(0.1)  # Brief wait
                    continue
                else:
                    # Final attempt failed or not an I/O error
                    logging.error(f"Failed to add user {user_id} after {attempt + 1} attempts: {e}")
                    raise

    def get_connection(self):
        """Get the database connection."""
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn and hasattr(self.conn, 'close'):
            self.conn.close()


    def get_total_posts_count(self) -> int:
        """Get the total number of original posts in the database (excluding shares)."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM posts WHERE original_post_id IS NULL")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logging.error(f"Error counting posts: {e}")
            return 0

    def get_posts_with_comment_count(self, min_comments: int) -> int:
        """Get the number of posts with at least a certain number of comments."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM posts WHERE num_comments >= ?", (min_comments,))
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logging.error(f"Error counting posts with high comment count: {e}")
            return 0

def get_schema_info(db_path: str) -> Dict[str, List[tuple]]:
    """
    Get schema information for all tables in the database.
    Returns a dictionary with table names as keys and list of column information as values.
    """
    # Note: this function uses sqlite3 directly, not DatabaseManager
    # If schema via service is needed, extend the database service API
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    schema_info = {}
    for (table_name,) in tables:
        # Get column information for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        schema_info[table_name] = columns

    conn.close()
    return schema_info

def print_schema(schema_info: Dict[str, List[tuple]]):
    """
    Print a text representation of the schema.
    """
    for table_name, columns in schema_info.items():
        print(f"\n=== {table_name} ===")
        for col in columns:
            col_id, col_name, col_type, notnull, default, pk = col
            pk_str = "PRIMARY KEY" if pk else ""
            null_str = "NOT NULL" if notnull else "NULL"
            default_str = f"DEFAULT {default}" if default else ""
            print(f"  {col_name}: {col_type} {pk_str} {null_str} {default_str}".strip())

if __name__ == "__main__":
    db_path = "/Users/genglinliu/Documents/GitHub/social-simulation/database/simulation.db"

    # Get schema information
    schema_info = get_schema_info(db_path)

    # Print text representation
    print_schema(schema_info)
