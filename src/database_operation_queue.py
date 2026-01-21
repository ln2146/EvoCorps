"""
Database operation queue manager
Solve database lock issues caused by concurrent writes
Avoid conflicts by serializing database operations
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Any, Dict
from datetime import datetime
import threading
from queue import Queue, Empty

class DatabaseOperationQueue:
    """Database operation queue - serialize all DB write operations"""

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
        self.operation_queue = Queue()
        self.worker_thread = None
        self.shutdown_flag = threading.Event()
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_wait_time': 0.0,
            'queue_size': 0
        }
        self.start_worker()

        logging.info("🚀 Database operation queue started")

    def start_worker(self):
        """Start worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.shutdown_flag.clear()
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logging.info("✅ Database operation worker thread started")

    def _worker_loop(self):
        """Worker thread main loop - serially process DB operations"""
        logging.info("🔄 Database operation worker thread started running")

        while not self.shutdown_flag.is_set():
            try:
                # Wait for operation request, with timeout to check shutdown
                operation_request = self.operation_queue.get(timeout=1.0)

                if operation_request is None:  # Shutdown signal
                    break

                self._execute_operation(operation_request)
                self.operation_queue.task_done()

            except Empty:
                continue  # Timeout; keep checking shutdown flag
            except Exception as e:
                logging.error(f"❌ Database operation worker thread error: {e}")

        logging.info("🛑 Database operation worker thread stopped")

    def _execute_operation(self, operation_request: Dict[str, Any]):
        """Execute a single database operation"""
        operation_func = operation_request['operation']
        future = operation_request['future']
        operation_id = operation_request['id']
        enqueue_time = operation_request['enqueue_time']

        start_time = time.time()
        wait_time = start_time - enqueue_time

        try:
            # Execute DB operation
            result = operation_func()

            # Update stats
            self.stats['total_operations'] += 1
            self.stats['successful_operations'] += 1
            self._update_average_wait_time(wait_time)

            execution_time = time.time() - start_time
            logging.debug(f"✅ DB operation {operation_id} complete (wait: {wait_time:.3f}s, exec: {execution_time:.3f}s)")

            # Set result in a thread-safe way
            if future and not future.cancelled():
                # Safely set future result from worker thread
                loop = future.get_loop()
                loop.call_soon_threadsafe(future.set_result, result)

        except Exception as e:
            self.stats['total_operations'] += 1
            self.stats['failed_operations'] += 1

            execution_time = time.time() - start_time
            logging.error(f"❌ DB operation {operation_id} failed (wait: {wait_time:.3f}s, exec: {execution_time:.3f}s): {e}")

            # Set exception in a thread-safe way
            if future and not future.cancelled():
                # Safely set future exception from worker thread
                loop = future.get_loop()
                loop.call_soon_threadsafe(future.set_exception, e)

    def _update_average_wait_time(self, wait_time: float):
        """Update average wait time"""
        current_avg = self.stats['average_wait_time']
        total_ops = self.stats['successful_operations']

        if total_ops == 1:
            self.stats['average_wait_time'] = wait_time
        else:
            # Moving average
            self.stats['average_wait_time'] = (current_avg * (total_ops - 1) + wait_time) / total_ops

    async def enqueue_operation(self, operation_func: Callable, operation_id: str = None) -> Any:
        """Enqueue a database operation and wait for result"""
        if self.shutdown_flag.is_set():
            raise RuntimeError("Database operation queue is shut down")

        # Generate operation ID
        if operation_id is None:
            operation_id = f"op_{int(time.time() * 1000)}"

        # Create future to await result
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        # Create operation request
        operation_request = {
            'id': operation_id,
            'operation': operation_func,
            'future': future,
            'enqueue_time': time.time()
        }

        # Enqueue
        self.operation_queue.put(operation_request)
        self.stats['queue_size'] = self.operation_queue.qsize()

        logging.debug(f"📝 DB operation {operation_id} enqueued (queue size: {self.stats['queue_size']})")

        # Await execution result
        return await future

    def enqueue_operation_sync(self, operation_func: Callable, operation_id: str = None) -> Any:
        """Sync version: enqueue DB operation and wait for result"""
        if self.shutdown_flag.is_set():
            raise RuntimeError("Database operation queue is shut down")

        # Generate operation ID
        if operation_id is None:
            operation_id = f"op_sync_{int(time.time() * 1000)}"

        # Use threading.Event to synchronize
        result_event = threading.Event()
        result_container = {'result': None, 'exception': None}

        def wrapped_operation():
            try:
                result = operation_func()
                result_container['result'] = result
            except Exception as e:
                result_container['exception'] = e
            finally:
                result_event.set()

        # Create operation request
        operation_request = {
            'id': operation_id,
            'operation': wrapped_operation,
            'future': None,  # Sync version does not need a future
            'enqueue_time': time.time()
        }

        # Enqueue
        self.operation_queue.put(operation_request)
        self.stats['queue_size'] = self.operation_queue.qsize()

        logging.debug(f"📝 Sync DB operation {operation_id} enqueued (queue size: {self.stats['queue_size']})")

        # Wait for result
        result_event.wait(timeout=30.0)  # 30s timeout

        if result_container['exception']:
            raise result_container['exception']

        return result_container['result']

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        self.stats['queue_size'] = self.operation_queue.qsize()
        return self.stats.copy()

    def is_busy(self) -> bool:
        """Check whether the queue is busy"""
        return self.operation_queue.qsize() > 5

    def shutdown(self, timeout: float = 10.0):
        """Shut down queue and worker thread"""
        logging.info("🛑 Starting shutdown of database operation queue...")

        # Set shutdown flag
        self.shutdown_flag.set()

        # Send shutdown signal
        self.operation_queue.put(None)

        # Wait for worker thread to end
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)

            if self.worker_thread.is_alive():
                logging.warning("⚠️ Database operation worker thread did not shut down in time")
            else:
                logging.info("✅ Database operation queue shut down")

        # Log final statistics
        stats = self.get_stats()
        logging.info(f"📊 Queue stats: total {stats['total_operations']}, "
                    f"success {stats['successful_operations']}, "
                    f"failed {stats['failed_operations']}, "
                    f"avg wait {stats['average_wait_time']:.3f}s")

# Global queue instance
_db_queue = None

def get_database_queue() -> DatabaseOperationQueue:
    """Get global database operation queue instance"""
    global _db_queue
    if _db_queue is None:
        _db_queue = DatabaseOperationQueue()
    return _db_queue

def shutdown_database_queue():
    """Shut down global database operation queue"""
    global _db_queue
    if _db_queue is not None:
        _db_queue.shutdown()
        _db_queue = None

# Convenience functions
async def execute_db_operation(operation_func: Callable, operation_id: str = None) -> Any:
    """Convenience function: execute a database operation"""
    queue = get_database_queue()
    return await queue.enqueue_operation(operation_func, operation_id)

def execute_db_operation_sync(operation_func: Callable, operation_id: str = None) -> Any:
    """Convenience function: execute a database operation synchronously"""
    queue = get_database_queue()
    return queue.enqueue_operation_sync(operation_func, operation_id)
