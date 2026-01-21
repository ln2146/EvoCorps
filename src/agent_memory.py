import sqlite3
from utils import Utils
from openai import OpenAI
from prompts import AgentPrompts
import logging
import time
import sys
import os
import asyncio
from typing import List, Dict, Optional, Tuple, Any

# Add database path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))
try:
    from database_manager import execute_query, fetch_all
except ImportError:
    try:
        from database.database_manager import execute_query, fetch_all
    except ImportError:
        # Last-resort fallback
        import importlib.util
        spec = importlib.util.spec_from_file_location("database_manager", os.path.join(os.path.dirname(__file__), 'database', 'database_manager.py'))
        database_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database_manager)
        execute_query = database_manager.execute_query
        fetch_all = database_manager.fetch_all

class AgentMemory:
    """Handles memory and reflection functionality for agent users."""
    
    MEMORY_TYPE_INTERACTION = 'interaction'
    MEMORY_TYPE_REFLECTION = 'reflection'
    VALID_MEMORY_TYPES = {MEMORY_TYPE_INTERACTION, MEMORY_TYPE_REFLECTION}
    
    # Class-level cache: store reflection memory per user to avoid frequent DB queries
    _reflection_cache = {}  # {user_id: str} simple in-memory cache, no TTL
    
    def __init__(self, user_id: str, persona: dict, db_manager=None, memory_decay_rate: float = 0.1):
        self.user_id = user_id
        self.db_manager = db_manager
        self.persona = persona
        self.memory_decay_rate = memory_decay_rate
        self.memory_importance_threshold = 0.3
    
    def add_memory(self, content: str, memory_type: str = MEMORY_TYPE_INTERACTION, importance_score: float = 0.0) -> str:
        """Add a new memory for the agent."""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory_type. Must be one of: {', '.join(self.VALID_MEMORY_TYPES)}")
        
        memory_id = Utils.generate_formatted_id("memory")
        
        if importance_score == 0.0:
            importance_score = self._evaluate_memory_importance(content)
        
        execute_query('''
            INSERT INTO agent_memories (
                memory_id, user_id, memory_type, content, 
                importance_score, created_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (memory_id, self.user_id, memory_type, content, importance_score))
        
        return memory_id
    
    async def add_memory_async(self, content: str, memory_type: str = MEMORY_TYPE_INTERACTION, importance_score: float = 0.0) -> str:
        """Add memory asynchronously (non-blocking)"""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory_type. Must be one of: {', '.join(self.VALID_MEMORY_TYPES)}")
        
        memory_id = Utils.generate_formatted_id("memory")
        
        if importance_score == 0.0:
            # Importance evaluation is CPU-intensive; run in thread pool
            importance_score = await asyncio.to_thread(self._evaluate_memory_importance, content)
        
        # Run DB operation asynchronously in thread pool
        await asyncio.to_thread(
            execute_query,
            '''
            INSERT INTO agent_memories (
                memory_id, user_id, memory_type, content, 
                importance_score, created_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''',
            (memory_id, self.user_id, memory_type, content, importance_score)
        )
        
        return memory_id
    
    async def add_memories_batch_async(
        self, 
        memories: List[Dict[str, Any]], 
        memory_type: str = MEMORY_TYPE_INTERACTION,
        max_concurrent: int = 10
    ) -> List[str]:
        """
        Batch add memories asynchronously with concurrency
        
        Args:
            memories: Memory list; each memory is a dict with 'content' and optional 'importance_score'
            memory_type: Memory type
            max_concurrent: Max concurrency to avoid excessive DB pressure
        
        Returns:
            List of added memory IDs
        """
        if not memories:
            return []
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def add_single_memory(memory_data: Dict[str, Any]) -> str:
            """Async task to add a single memory"""
            async with semaphore:
                content = memory_data.get('content', '')
                importance_score = memory_data.get('importance_score', 0.0)
                return await self.add_memory_async(content, memory_type, importance_score)
        
        # Run all memory add tasks concurrently
        memory_ids = await asyncio.gather(
            *[add_single_memory(mem) for mem in memories],
            return_exceptions=True
        )
        
        # Handle exceptions, log errors but keep successful IDs
        result_ids = []
        for i, mem_id in enumerate(memory_ids):
            if isinstance(mem_id, Exception):
                logging.error(f"Failed to add memory (index {i}): {mem_id}")
            else:
                result_ids.append(mem_id)
        
        logging.info(f"Batch add memories complete: {len(result_ids)}/{len(memories)} succeeded")
        return result_ids

    def upsert_integrated_memory(self, content: str, importance_score: float = 0.95) -> None:
        """Store a single integrated reflection memory per user by replacing existing reflections."""
        # Remove existing reflections for this user
        execute_query(
            '''
            DELETE FROM agent_memories 
            WHERE user_id = ? AND memory_type = ?
            ''', (self.user_id, self.MEMORY_TYPE_REFLECTION)
        )

        # Insert the new integrated reflection
        self.add_memory(content, memory_type=self.MEMORY_TYPE_REFLECTION, importance_score=importance_score)
    
    async def upsert_integrated_memory_async(self, content: str, importance_score: float = 0.95) -> None:
        """Async version: store a single integrated memory"""
        # Delete existing reflection memories asynchronously
        await asyncio.to_thread(
            execute_query,
            '''
            DELETE FROM agent_memories 
            WHERE user_id = ? AND memory_type = ?
            ''',
            (self.user_id, self.MEMORY_TYPE_REFLECTION)
        )

        # Insert new integrated memory asynchronously
        await self.add_memory_async(content, memory_type=self.MEMORY_TYPE_REFLECTION, importance_score=importance_score)
    
    def get_cached_reflection(self) -> Optional[str]:
        """Get cached reflection memory without DB query (non-blocking)"""
        cache_key = self.user_id
        return AgentMemory._reflection_cache.get(cache_key)
    
    async def update_reflection_cache(self) -> None:
        """Update reflection cache asynchronously; non-blocking for main flow"""
        try:
            # Query DB asynchronously for latest reflection memory
            reflection_memories = await self.get_relevant_memories_async("reflection", limit=1)
            cache_key = self.user_id
            if reflection_memories:
                AgentMemory._reflection_cache[cache_key] = reflection_memories[0]['content']
                logging.debug(f"User {self.user_id}: Reflection cache updated")
            else:
                # Cache empty value to avoid repeated queries
                AgentMemory._reflection_cache[cache_key] = None
        except Exception as e:
            logging.warning(f"Failed to update reflection cache for user {self.user_id}: {e}")
    
    def get_relevant_memories(self, memory_type: str = MEMORY_TYPE_INTERACTION, limit: int = 5):
        """Retrieve relevant memories, optionally filtered by memory type."""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory_type. Must be one of: {', '.join(self.VALID_MEMORY_TYPES)}")
        
        self._decay_memories()
        
        query = '''
            SELECT memory_id, content, memory_type, importance_score, created_at, decay_factor
            FROM agent_memories
            WHERE user_id = ? 
            AND importance_score * decay_factor >= ?
            AND memory_type = ?
            ORDER BY importance_score * decay_factor DESC 
            LIMIT ?
        '''
        
        try:
            results = fetch_all(query, (
                self.user_id,
                self.memory_importance_threshold,
                memory_type,
                limit
            ))

            return [{
                'id': row['memory_id'],
                'content': row['content'],
                'type': row['memory_type'],
                'importance': row['importance_score'],
                'created_at': row['created_at'],
                'decay_factor': row['decay_factor']
            } for row in results]
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in get_relevant_memories, returning empty list")
                return []
            else:
                raise e
    
    async def get_relevant_memories_async(self, memory_type: str = MEMORY_TYPE_INTERACTION, limit: int = 5):
        """Get relevant memories asynchronously"""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory_type. Must be one of: {', '.join(self.VALID_MEMORY_TYPES)}")
        
        # Run memory decay asynchronously
        await asyncio.to_thread(self._decay_memories)
        
        query = '''
            SELECT memory_id, content, memory_type, importance_score, created_at, decay_factor
            FROM agent_memories
            WHERE user_id = ? 
            AND importance_score * decay_factor >= ?
            AND memory_type = ?
            ORDER BY importance_score * decay_factor DESC 
            LIMIT ?
        '''
        
        try:
            # Execute DB query asynchronously
            results = await asyncio.to_thread(
                fetch_all,
                query,
                (
                    self.user_id,
                    self.memory_importance_threshold,
                    memory_type,
                    limit
                )
            )

            return [{
                'id': row['memory_id'],
                'content': row['content'],
                'type': row['memory_type'],
                'importance': row['importance_score'],
                'created_at': row['created_at'],
                'decay_factor': row['decay_factor']
            } for row in results]
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in get_relevant_memories_async, returning empty list")
                return []
            else:
                raise e
    
    def reflect(self, openai_client: OpenAI, engine: str, temperature: float):
        """Generate reflections based on recent memories and experiences."""
        recent_memories = self.get_relevant_memories(memory_type=self.MEMORY_TYPE_INTERACTION, limit=10)
        
        if not recent_memories:
            return
        
        memory_text = "\n".join([
            f"- {mem['content']} ({mem['type']})"
            for mem in recent_memories
        ])
        
        prompt = AgentPrompts.create_reflection_prompt(self.persona, memory_text)
        reflection = Utils.generate_llm_response(
            openai_client,
            engine,
            prompt,
            "You are helping an AI agent reflect on its recent experiences and form insights.",
            temperature=temperature,
            max_tokens=200
        )
        
        self.add_memory(reflection, memory_type=self.MEMORY_TYPE_REFLECTION, importance_score=0.8)
    
    def _decay_memories(self):
        """Apply decay to all memories based on time passed."""
        try:
            execute_query('''
                UPDATE agent_memories
                SET decay_factor = MAX(0, decay_factor - ? * 
                    (julianday('now') - julianday(last_accessed))),
                    last_accessed = datetime('now')  -- Update last_accessed time
                WHERE user_id = ?
            ''', (self.memory_decay_rate, self.user_id))
        except sqlite3.OperationalError as e:
            logging.error(f"Error in decay_memories: {e}")
            # Check if it's a database connection issue
            if "unable to open database file" in str(e):
                logging.warning(f"Database connection error in _decay_memories, skipping memory decay")
                return
            # Retry once after a short delay for other errors
            time.sleep(0.5)
            try:
                execute_query('''
                    UPDATE agent_memories
                    SET decay_factor = MAX(0, decay_factor - ? *
                        (julianday('now') - julianday(last_accessed))),
                        last_accessed = datetime('now')
                    WHERE user_id = ?
                ''', (self.memory_decay_rate, self.user_id))
            except sqlite3.OperationalError as e2:
                if "unable to open database file" in str(e2):
                    logging.warning(f"Database connection error in _decay_memories retry, skipping memory decay")
                    return
                else:
                    raise e2
    
    def _evaluate_memory_importance(self, content: str) -> float:
        """Evaluate the importance of a memory based on its content."""
        importance_factors = {
            'emotional_words': ['love', 'hate', 'angry', 'happy', 'sad'],
            'action_words': ['achieved', 'failed', 'learned', 'discovered'],
            'relationship_words': ['friend', 'follow', 'connect', 'share'],
            'goal_words': ['objective', 'target', 'aim', 'purpose']
        }
        
        score = 0.5  # Base score
        content_lower = content.lower()
        
        for category, words in importance_factors.items():
            for word in words:
                if word in content_lower:
                    score += 0.1
        
        return min(1.0, max(0.0, score)) 
