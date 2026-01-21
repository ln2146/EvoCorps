"""
Database Connection Manager for handling concurrent database operations
Resolve SQLite database lock issues
"""
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional, Generator
import queue
import os

class DatabaseConnectionManager:
    """Database connection manager - resolves SQLite locks under concurrent access"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.db_path = "database/simulation.db"
        self._connection_pool = queue.Queue(maxsize=10)  # Connection pool size
        self._active_connections = 0
        self._max_connections = 10
        self._pool_lock = threading.Lock()
        self._operation_queue = queue.Queue()  # Operation queue
        self._worker_thread = None
        self._shutdown = False
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize connection pool
        self._initialize_connection_pool()
        
        # Start worker thread to handle database operations
        self._start_worker_thread()
        
        logging.info("✅ Database connection manager initialized")
    
    def _initialize_connection_pool(self):
        """Initialize connection pool"""
        try:
            # Create initial connections
            for _ in range(3):  # Create 3 initial connections
                conn = self._create_connection()
                if conn:
                    self._connection_pool.put(conn)
                    self._active_connections += 1
        except Exception as e:
            logging.error(f"❌ Failed to initialize connection pool: {e}")
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # 30-second timeout
                check_same_thread=False  # Allow cross-thread use
            )
            
            # Configure SQLite for concurrency
            conn.execute("PRAGMA journal_mode=WAL")  # Use WAL mode for concurrent reads
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance performance and safety
            conn.execute("PRAGMA cache_size=10000")  # Increase cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Store temp data in memory
            conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
            conn.execute("PRAGMA busy_timeout=30000")  # 30-second busy wait timeout
            
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logging.error(f"❌ Failed to create database connection: {e}")
            return None
    
    def _start_worker_thread(self):
        """Start worker thread to handle database operations"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
    
    def _worker_loop(self):
        """Worker loop for database operations"""
        while not self._shutdown:
            try:
                # Get operation (with timeout)
                operation = self._operation_queue.get(timeout=1.0)
                
                if operation is None:  # Shutdown signal
                    break
                
                # Execute operation
                operation()
                self._operation_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"❌ Worker thread operation failed: {e}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for acquiring a database connection"""
        conn = None
        try:
            # Try to get a connection from the pool
            try:
                conn = self._connection_pool.get(timeout=5.0)
            except queue.Empty:
                # If pool is empty, create a new connection
                with self._pool_lock:
                    if self._active_connections < self._max_connections:
                        conn = self._create_connection()
                        if conn:
                            self._active_connections += 1
                    else:
                        # Wait for a connection to become available
                        conn = self._connection_pool.get(timeout=10.0)
            
            if conn is None:
                raise Exception("Unable to acquire database connection")
            
            yield conn
            
        except Exception as e:
            logging.error(f"❌ Failed to acquire database connection: {e}")
            raise
        finally:
            # Return connection to the pool
            if conn:
                try:
                    # Check if connection is still valid
                    conn.execute("SELECT 1").fetchone()
                    self._connection_pool.put(conn)
                except:
                    # Connection invalid, create a new one
                    try:
                        conn.close()
                    except:
                        pass
                    with self._pool_lock:
                        if self._active_connections > 0:
                            self._active_connections -= 1
    
    def execute_with_retry(self, operation_func, max_retries=3, retry_delay=1.0):
        """Execute database operation with retry mechanism"""
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    return operation_func(conn)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    logging.warning(f"⚠️ Database locked, retry {attempt + 1}/{max_retries}: {e}")
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"⚠️ Database operation failed, retry {attempt + 1}/{max_retries}: {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise
    
    def queue_operation(self, operation_func):
        """Queue operation (asynchronous)"""
        self._operation_queue.put(operation_func)
    
    def close_all_connections(self):
        """Close all connections"""
        self._shutdown = True
        
        # Stop worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._operation_queue.put(None)  # Send shutdown signal
            self._worker_thread.join(timeout=5.0)
        
        # Close all connections in the pool
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except:
                pass
        
        self._active_connections = 0
        logging.info("✅ All database connections closed")

# Global connection manager instance
db_manager = DatabaseConnectionManager()

def get_db_manager() -> DatabaseConnectionManager:
    """Get database connection manager instance"""
    return db_manager
