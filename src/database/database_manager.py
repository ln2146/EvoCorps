"""
Global SQLite3 single-threaded database operation manager

This module provides a thread-safe SQLite3 database manager to ensure
all database operations execute on a single thread to avoid concurrency conflicts.
"""

import sqlite3
import threading
import queue
import logging
import time
import os
import requests
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
import json
from datetime import datetime
import asyncio
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Global SQLite3 single-threaded database manager
    
    Features:
    1. Execute all DB operations on a single thread to avoid conflicts
    2. Support sync and async operations
    3. Automatic retry
    4. Connection management
    5. Transaction support
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._closed = False  # Track closed state
        self.db_path = None
        self.connection = None
        self.operation_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.retry_count = 3
        self.retry_delay = 0.1
        
        # Database service config
        self.use_service = True
        self.service_url = "http://127.0.0.1:5000"
        
        # Do not start worker thread by default (service mode)
        logger.info("Database service mode - skip worker thread startup")
    
    def _make_service_request(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """Send a request to the database service"""
        try:
            response = requests.post(f"{self.service_url}/execute", json={
                'query': query,
                'params': list(params)
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # Convert raw data to dict format
                    data = result.get('data', [])
                    columns = result.get('columns', [])
                    
                    # If SELECT query, convert to list of dicts
                    if data and columns:
                        dict_data = []
                        for row in data:
                            row_dict = {}
                            for i, value in enumerate(row):
                                if i < len(columns):
                                    row_dict[columns[i]] = value
                            dict_data.append(row_dict)
                        data = dict_data
                    
                    return {
                        'success': True,
                        'result': data,
                        'columns': columns,
                        'affected_rows': result.get('affected_rows', 0),
                        'lastrowid': result.get('lastrowid', 0)
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Database service request failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _start_worker_thread(self):
        """Start database operation worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Database worker thread started")
    
    def _worker_loop(self):
        """Worker thread main loop"""
        while not self.shutdown_event.is_set():
            try:
                # Wait for operation request, 1s timeout
                operation = self.operation_queue.get(timeout=1.0)
                
                if operation is None:  # Shutdown signal
                    break
                
                # Execute operation
                result = self._execute_operation(operation)
                
                # Return result
                self.result_queue.put(result)
                self.operation_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker thread error while executing operation: {e}")
                # Return error result
                self.result_queue.put({
                    'success': False,
                    'error': str(e),
                    'operation_id': getattr(operation, 'get', lambda x: None)('operation_id')
                })
    
    def _execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a database operation"""
        operation_type = operation.get('type')
        operation_id = operation.get('operation_id')
        
        try:
            # Ensure database connection
            if not self._ensure_connection():
                return {
                    'success': False,
                    'error': 'Unable to establish database connection',
                    'operation_id': operation_id
                }
            
            # Execute based on operation type
            if operation_type == 'execute':
                return self._execute_query(operation)
            elif operation_type == 'fetch':
                return self._fetch_data(operation)
            elif operation_type == 'transaction':
                return self._execute_transaction(operation)
            elif operation_type == 'close':
                return self._close_connection()
            else:
                return {
                    'success': False,
                    'error': f'Unknown operation type: {operation_type}',
                    'operation_id': operation_id
                }
                
        except Exception as e:
            logger.error(f"Error executing operation {operation_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation_id': operation_id
            }
    
    def _ensure_connection(self) -> bool:
        """Ensure database connection is available"""
        try:
            if self.connection is None or not self._is_connection_alive():
                if self.db_path is None:
                    # Use default database path
                    self.db_path = self._get_default_db_path()
                
                # Create database directory
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Establish connection
                self.connection = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    isolation_level=None,  # Autocommit mode
                    check_same_thread=False
                )
                self.connection.row_factory = sqlite3.Row
                
                logger.info(f"Database connection established: {self.db_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            return False
    
    def _is_connection_alive(self) -> bool:
        """Check if connection is alive"""
        try:
            if self.connection is None:
                return False
            self.connection.execute("SELECT 1")
            return True
        except:
            return False
    
    def _get_default_db_path(self) -> str:
        """Get default database path"""
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
    
    def _execute_query(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query operation"""
        query = operation.get('query')
        params = operation.get('params', ())
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            
            return {
                'success': True,
                'result': None,
                'operation_id': operation.get('operation_id')
            }
            
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def _fetch_data(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data fetch operation"""
        query = operation.get('query')
        params = operation.get('params', ())
        fetch_type = operation.get('fetch_type', 'all')  # all, one, many
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            if fetch_type == 'one':
                result = cursor.fetchone()
                if result:
                    result = dict(result)
            elif fetch_type == 'many':
                count = operation.get('count', 1)
                result = [dict(row) for row in cursor.fetchmany(count)]
            else:  # all
                result = [dict(row) for row in cursor.fetchall()]
            
            return {
                'success': True,
                'result': result,
                'operation_id': operation.get('operation_id')
            }
            
        except Exception as e:
            raise e
    
    def _execute_transaction(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute transaction"""
        operations = operation.get('operations', [])
        
        try:
            self.connection.execute("BEGIN")
            
            results = []
            for op in operations:
                if op['type'] == 'execute':
                    cursor = self.connection.cursor()
                    cursor.execute(op['query'], op.get('params', ()))
                elif op['type'] == 'fetch':
                    cursor = self.connection.cursor()
                    cursor.execute(op['query'], op.get('params', ()))
                    fetch_type = op.get('fetch_type', 'all')
                    if fetch_type == 'one':
                        result = cursor.fetchone()
                        if result:
                            result = dict(result)
                    elif fetch_type == 'many':
                        count = op.get('count', 1)
                        result = [dict(row) for row in cursor.fetchmany(count)]
                    else:
                        result = [dict(row) for row in cursor.fetchall()]
                    results.append(result)
            
            self.connection.commit()
            
            return {
                'success': True,
                'result': results,
                'operation_id': operation.get('operation_id')
            }
            
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def _close_connection(self) -> Dict[str, Any]:
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                logger.info("Database connection closed")
            
            return {
                'success': True,
                'result': None,
                'operation_id': 'close'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation_id': 'close'
            }
    
    def _submit_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Submit operation to queue and wait for result"""
        operation_id = f"op_{int(time.time() * 1000)}"
        operation['operation_id'] = operation_id
        
        # Submit operation
        self.operation_queue.put(operation)
        
        # Wait for result
        try:
            result = self.result_queue.get(timeout=30.0)
            return result
        except queue.Empty:
            return {
                'success': False,
                'error': 'Operation timed out',
                'operation_id': operation_id
            }
    
    def set_database_path(self, db_path: str):
        """Set database path"""
        if self.use_service:
            # Service mode does not require setting path; service handles it
            self.db_path = db_path
            # Remove log output to avoid duplication
        else:
            # If path changes, force reconnect
            if self.db_path != db_path:
                # Close existing connection
                if self.connection:
                    try:
                        self.connection.close()
                    except:
                        pass
                    self.connection = None
                
                # Set new path
                self.db_path = db_path
                logger.info(f"Database path set to: {db_path}")
            else:
                logger.info(f"Database path set to: {db_path}")
    
    def execute_with_temp_connection(self, db_path: str, query: str, params: tuple = ()) -> bool:
        """Execute SQL with a temporary connection, without affecting global connection"""
        try:
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary connection
            temp_conn = sqlite3.connect(
                db_path,
                timeout=30.0,
                isolation_level=None,
                check_same_thread=False
            )
            temp_conn.row_factory = sqlite3.Row
            
            try:
                cursor = temp_conn.cursor()
                cursor.execute(query, params)
                temp_conn.commit()
                return True
            finally:
                temp_conn.close()
                
        except Exception as e:
            logger.error(f"Temporary connection execution failed: {e}")
            return False
    
    def fetch_with_temp_connection(self, db_path: str, query: str, params: tuple = (), fetch_type: str = 'all', count: int = 1) -> List[Dict[str, Any]]:
        """Fetch data with a temporary connection, without affecting global connection"""
        try:
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary connection
            temp_conn = sqlite3.connect(
                db_path,
                timeout=30.0,
                isolation_level=None,
                check_same_thread=False
            )
            temp_conn.row_factory = sqlite3.Row
            
            try:
                cursor = temp_conn.cursor()
                cursor.execute(query, params)
                
                if fetch_type == 'one':
                    result = cursor.fetchone()
                    if result:
                        result = dict(result)
                elif fetch_type == 'many':
                    result = [dict(row) for row in cursor.fetchmany(count)]
                else:  # all
                    result = [dict(row) for row in cursor.fetchall()]
                
                return result if result else []
                
            finally:
                temp_conn.close()
                
        except Exception as e:
            logger.error(f"Temporary connection fetch failed: {e}")
            return []
    
    def execute(self, query: str, params: tuple = ()) -> bool:
        """Execute SQL statement"""
        if self.use_service:
            result = self._make_service_request(query, params)
            return result.get('success', False)
        else:
            operation = {
                'type': 'execute',
                'query': query,
                'params': params
            }
            result = self._submit_operation(operation)
            return result.get('success', False)
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one record"""
        if self.use_service:
            result = self._make_service_request(query, params)
            if result.get('success') and result.get('result'):
                # Return first record
                data = result.get('result', [])
                if data:
                    return data[0]
            return None
        else:
            operation = {
                'type': 'fetch',
                'query': query,
                'params': params,
                'fetch_type': 'one'
            }
            result = self._submit_operation(operation)
            if result.get('success'):
                return result.get('result')
            return None
    
    def fetch_many(self, query: str, params: tuple = (), count: int = 1) -> List[Dict[str, Any]]:
        """Fetch multiple records"""
        if self.use_service:
            result = self._make_service_request(query, params)
            if result.get('success') and result.get('result'):
                # Return specified number of records
                data = result.get('result', [])
                return data[:count]
            return []
        else:
            operation = {
                'type': 'fetch',
                'query': query,
                'params': params,
                'fetch_type': 'many',
                'count': count
            }
            result = self._submit_operation(operation)
            if result.get('success'):
                return result.get('result', [])
            return []
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all records"""
        if self.use_service:
            result = self._make_service_request(query, params)
            if result.get('success') and result.get('result'):
                return result.get('result', [])
            return []
        else:
            operation = {
                'type': 'fetch',
                'query': query,
                'params': params,
                'fetch_type': 'all'
            }
            result = self._submit_operation(operation)
            if result.get('success'):
                return result.get('result', [])
            return []
    
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Execute transaction"""
        operation = {
            'type': 'transaction',
            'operations': operations
        }
        
        result = self._submit_operation(operation)
        if result.get('success'):
            return result.get('result', [])
        return []
    
    def close(self):
        """Close database manager"""
        # Prevent duplicate close
        if self._closed:
            return

        try:
            self._closed = True

            # If using database service mode, no need to close queue
            if self.use_service:
                logger.info("Database manager closed (service mode)")
                return

            # Submit close operation
            operation = {'type': 'close'}
            self.operation_queue.put(operation)

            # Wait for close to complete
            try:
                self.result_queue.get(timeout=5.0)
            except queue.Empty:
                pass  # Ignore timeout

            # Stop worker thread
            self.shutdown_event.set()
            self.operation_queue.put(None)  # Send shutdown signal

            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5.0)

            logger.info("Database manager closed")

        except Exception as e:
            if str(e):  # Only log when error message exists
                logger.error(f"Error closing database manager: {e}")

    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except Exception:
            pass  # Ignore all errors in destructor


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    return db_manager


def async_db_operation(func):
    """Async database operation decorator"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Execute DB operation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return wrapper


# Convenience functions
def execute_query(query: str, params: tuple = ()) -> bool:
    """Execute SQL query"""
    return db_manager.execute(query, params)


def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch one record"""
    return db_manager.fetch_one(query, params)


def fetch_many(query: str, params: tuple = (), count: int = 1) -> List[Dict[str, Any]]:
    """Fetch multiple records"""
    return db_manager.fetch_many(query, params, count)


def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all records"""
    return db_manager.fetch_all(query, params)


def execute_transaction(operations: List[Dict[str, Any]]) -> List[Any]:
    """Execute transaction"""
    return db_manager.execute_transaction(operations)


# Temporary connection convenience functions
def execute_with_temp_connection(db_path: str, query: str, params: tuple = ()) -> bool:
    """Execute SQL query using a temporary connection"""
    return db_manager.execute_with_temp_connection(db_path, query, params)


def fetch_one_with_temp_connection(db_path: str, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Fetch one record using a temporary connection"""
    result = db_manager.fetch_with_temp_connection(db_path, query, params, 'one')
    return result if result else None


def fetch_many_with_temp_connection(db_path: str, query: str, params: tuple = (), count: int = 1) -> List[Dict[str, Any]]:
    """Fetch multiple records using a temporary connection"""
    return db_manager.fetch_with_temp_connection(db_path, query, params, 'many', count)


def fetch_all_with_temp_connection(db_path: str, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Fetch all records using a temporary connection"""
    return db_manager.fetch_with_temp_connection(db_path, query, params, 'all')


# Import required modules
import os
