"""
Advanced RAG retrieval system
Semantic retrieval based on a vector database, supports historical cases and strategy pattern retrieval
"""

import json
import numpy as np
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import pickle

# Remove SentenceTransformer dependency, use OpenAI embedding API
SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ faiss unavailable, using simplified vector retrieval")

logger = logging.getLogger(__name__)


@dataclass
class HistoricalCase:
    """Historical case"""
    case_id: str
    timestamp: datetime
    context: Dict[str, Any]
    strategy_used: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    results: Dict[str, Any]
    effectiveness_score: float
    lessons_learned: List[str]
    tags: List[str]


@dataclass
class StrategyPattern:
    """Strategy pattern"""
    pattern_id: str
    pattern_name: str
    description: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    success_rate: float
    usage_count: int
    last_updated: datetime
    variations: List[Dict[str, Any]]


@dataclass
class RetrievalQuery:
    """Retrieval query"""
    query_text: str
    query_type: str  # "case", "strategy", "mixed"
    context_filters: Dict[str, Any]
    similarity_threshold: float = 0.5  # Cosine similarity threshold (normalized vectors)
    max_results: int = 5
    include_metadata: bool = True


def context_to_query(context: Dict[str, Any], query_type: str = "mixed", 
                     similarity_threshold: float = 0.5, max_results: int = 5) -> RetrievalQuery:
    """
    Convert a context dict to a retrieval query object
    
    Args:
        context: Context dict containing various context info
        query_type: Query type ("case", "strategy", "mixed")
        similarity_threshold: Similarity threshold
        max_results: Maximum result count
    
    Returns:
        RetrievalQuery: Retrieval query object
    """
    # Extract key info from context to build query text - use specified format
    core_viewpoint = context.get("core_viewpoint", "")
    post_theme = context.get("post_theme", "")
    threat_assessment = context.get("threat_assessment", "")
    
    # Use specified format: Core Viewpoint: {xxx}, Post Theme: {xxx}, Threat Assessment: {xxx}
    query_text = (
        f"Core Viewpoint: {core_viewpoint}, "
        f"Post Theme: {post_theme}, "
        f"Threat Assessment: {threat_assessment}"
    )
    
    # Build context filters
    context_filters = {}
    
    # Add time range filter
    if "time_range" in context:
        context_filters["time_range"] = context["time_range"]
    
    # Add effectiveness filter
    if "min_effectiveness" in context:
        context_filters["min_effectiveness"] = context["min_effectiveness"]
    
    # Add success-only filter
    if "success_only" in context:
        context_filters["success_only"] = context["success_only"]
    
    # Add tag filter
    if "tags" in context:
        context_filters["tags"] = context["tags"]
    
    # Add domain filter
    if "domain" in context:
        context_filters["domain"] = context["domain"]
    
    return RetrievalQuery(
        query_text=query_text,
        query_type=query_type,
        context_filters=context_filters,
        similarity_threshold=similarity_threshold,
        max_results=max_results,
        include_metadata=True
    )


@dataclass
class RetrievalResult:
    """Retrieval result"""
    item_id: str
    item_type: str  # "case" or "strategy"
    content: Dict[str, Any]
    similarity_score: float
    relevance_score: float
    metadata: Dict[str, Any]


class AdvancedRAGSystem:
    """Advanced RAG retrieval system"""
    
    def __init__(self, data_path: str = "database/action_log", model_name: str = None):
        # Ensure path is absolute and create required directories
        if not os.path.isabs(data_path):
            # Get current script directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_path = Path(os.path.join(current_dir, "..", data_path))
        else:
            self.data_path = Path(data_path)
        
        # Ensure path has no extra whitespace
        self.data_path = Path(str(self.data_path).strip())
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize vectorization model
        self.model_name = model_name
        self.encoder = None
        self._initialize_openai_client()
        
        # Data storage - keep only action_logs-related attributes
        # Remove historical cases and strategy pattern related attributes
        
        # FAISS index persistence path
        self.index_dir = self.data_path / "faiss_indices"
        # Ensure path has no extra whitespace
        self.index_dir = Path(str(self.index_dir).strip())
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Index file path - keep only query_text index
        self.query_text_index_path = self.index_dir / "query_text_index.faiss"
        # Ensure path has no extra whitespace
        self.query_text_index_path = Path(str(self.query_text_index_path).strip())
        
        # Index metadata file path - keep only query_text metadata
        self.query_text_metadata_path = self.index_dir / "query_text_metadata.pkl"
        # Ensure path has no extra whitespace
        self.query_text_metadata_path = Path(str(self.query_text_metadata_path).strip())

        # Database connection
        self.db_path = self.data_path / "rag_database.db"
        # Ensure path has no extra whitespace
        self.db_path = Path(str(self.db_path).strip())
        self._initialize_database()

        # Load existing data
        self._load_data()

        # Config parameters
        self.config = {
            "vector_dimension": 1536,  # Default embedding dimension (kept in sync with current embedding model)
            "index_update_threshold": 10,  # Update index after how many new records
            "similarity_weight": 0.6,
            "relevance_weight": 0.4,
            "max_cache_size": 1000
        }
    
    def _initialize_openai_client(self):
        """Initialize OpenAI client for embeddings"""
        try:
            from multi_model_selector import multi_model_selector

            # Unified model selection via MultiModelSelector (embedding role)
            self.encoder, selected_model = multi_model_selector.create_embedding_client(
                model_name=self.model_name
            )
            self.model_name = selected_model
            logger.info(f"✅ Initialized OpenAI embedding client: {self.model_name}")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI client initialization failed: {e}")
            self.encoder = None
    
    def _initialize_database(self):
        """Initialize database - only create action_logs table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Only create action_logs table
            cursor.execute('''
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
            
            conn.commit()
            conn.close()
            logger.info("✅ RAG database initialization complete - action_logs only")
            
        except Exception as e:
            logger.error(f"❌ RAG database initialization failed: {e}")
    
    def _load_data(self):
        """Load action_logs data"""
        try:
            # Only try loading query_text index
            logger.info("🔄 Attempting to load saved query_text index...")
            query_text_index_loaded = self._load_query_text_index()
            
            if query_text_index_loaded:
                logger.info("✅ query_text index loaded successfully")
            else:
                logger.info("📋 query_text index not found, will build on first retrieval")

        except Exception as e:
            logger.warning(f"⚠️ Data load failed: {e}")
    
    # Removed unnecessary parsing methods; keep only action_logs-related functionality
    
    def add_historical_case(self, case: HistoricalCase):
        """Add a historical case"""
        try:
            # Generate vector embedding
            case_text = self._extract_case_text(case)
            vector_embedding = self._encode_text(case_text)
            
            # Store in memory
            self.historical_cases[case.case_id] = case
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO historical_cases 
                (case_id, timestamp, context, strategy_used, actions_taken, 
                 results, effectiveness_score, lessons_learned, tags, vector_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case.case_id,
                case.timestamp.isoformat(),
                json.dumps(case.context),
                json.dumps(case.strategy_used),
                json.dumps(case.actions_taken),
                json.dumps(case.results),
                case.effectiveness_score,
                json.dumps(case.lessons_learned),
                json.dumps(case.tags),
                pickle.dumps(vector_embedding) if vector_embedding is not None else None
            ))
            
            conn.commit()
            conn.close()
            
            # Update vector index
            self._update_case_index()
            
            logger.info(f"✅ Added historical case: {case.case_id}")
            
        except Exception as e:
            logger.error(f"❌ Add historical case failed: {e}")
    
    def add_strategy_pattern(self, pattern: StrategyPattern):
        """Add a strategy pattern"""
        try:
            # Generate vector embedding
            pattern_text = self._extract_pattern_text(pattern)
            vector_embedding = self._encode_text(pattern_text)
            
            # Store in memory
            self.strategy_patterns[pattern.pattern_id] = pattern
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO strategy_patterns 
                (pattern_id, pattern_name, description, conditions, actions, 
                 success_rate, usage_count, last_updated, variations, vector_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id,
                pattern.pattern_name,
                pattern.description,
                json.dumps(pattern.conditions),
                json.dumps(pattern.actions),
                pattern.success_rate,
                pattern.usage_count,
                pattern.last_updated.isoformat(),
                json.dumps(pattern.variations),
                pickle.dumps(vector_embedding) if vector_embedding is not None else None
            ))
            
            conn.commit()
            conn.close()
            
            # Update vector index
            self._update_strategy_index()
            
            logger.info(f"✅ Added strategy pattern: {pattern.pattern_name}")
            
        except Exception as e:
            logger.error(f"❌ Add strategy pattern failed: {e}")
    
    def _extract_case_text(self, case: HistoricalCase) -> str:
        """Extract case text content for vectorization"""
        text_parts = []
        
        # Context info
        if case.context:
            context_text = " ".join([f"{k}: {v}" for k, v in case.context.items() if isinstance(v, (str, int, float))])
            text_parts.append(context_text)
        
        # Strategy description
        if case.strategy_used:
            strategy_text = " ".join([f"{k}: {v}" for k, v in case.strategy_used.items() if isinstance(v, (str, int, float))])
            text_parts.append(strategy_text)
        
        # Lessons learned
        if case.lessons_learned:
            text_parts.extend(case.lessons_learned)
        
        # Tags
        if case.tags:
            text_parts.extend(case.tags)
        
        return " ".join(text_parts)
    
    def _extract_pattern_text(self, pattern: StrategyPattern) -> str:
        """Extract strategy pattern text content for vectorization"""
        text_parts = [
            pattern.pattern_name,
            pattern.description
        ]
        
        # Condition description
        if pattern.conditions:
            conditions_text = " ".join([f"{k}: {v}" for k, v in pattern.conditions.items() if isinstance(v, (str, int, float))])
            text_parts.append(conditions_text)
        
        # Action description
        for action in pattern.actions:
            if isinstance(action, dict) and "description" in action:
                text_parts.append(action["description"])
        
        return " ".join(text_parts)

    def _encode_text(self, text: str) -> Optional[np.ndarray]:
        """Encode text to a vector"""
        if not text.strip():
            return None

        if self.encoder:
            try:
                # Encode with OpenAI embedding API
                response = self.encoder.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                embedding = np.array(response.data[0].embedding)
                # Normalize vector for cosine similarity
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding
            except Exception as e:
                logger.warning(f"⚠️ OpenAI embedding encode failed: {e}")
                logger.info(f"   Model: {self.model_name}, text length: {len(text)}")
                # Auto-fallback to simplified vectorization
                return self._simple_text_vectorization(text)
        else:
            # Simplified text vectorization (bag-of-words)
            return self._simple_text_vectorization(text)

    def _simple_text_vectorization(self, text: str) -> np.ndarray:
        """Simplified text vectorization"""
        # This is a simplified implementation; production should use better methods
        words = text.lower().split()
        # Create a fixed-dimension vector
        vector = np.zeros(self.config["vector_dimension"])

        for i, word in enumerate(words[:self.config["vector_dimension"]]):
            # Simple hash mapping to vector dimensions
            hash_val = hash(word) % self.config["vector_dimension"]
            vector[hash_val] += 1.0

        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def _rebuild_vector_indices(self):
        """Rebuild vector indices"""
        try:
            if FAISS_AVAILABLE and self.encoder:
                self._rebuild_faiss_indices()
            else:
                self._rebuild_simple_indices()
        except Exception as e:
            logger.error(f"❌ Vector index rebuild failed: {e}")

    def _rebuild_faiss_indices(self):
        """Rebuild FAISS vector indices"""
        # Rebuild case index
        if self.historical_cases:
            case_vectors = []
            case_ids = []

            for case_id, case in self.historical_cases.items():
                case_text = self._extract_case_text(case)
                vector = self._encode_text(case_text)
                if vector is not None:
                    case_vectors.append(vector)
                    case_ids.append(case_id)

            if case_vectors:
                case_vectors = np.array(case_vectors).astype('float32')
                self.case_index = faiss.IndexFlatIP(case_vectors.shape[1])  # Inner product index
                self.case_index.add(case_vectors)
                self.case_ids = case_ids
                
                # Save index to disk
                self._save_case_index()

        # Rebuild strategy index
        if self.strategy_patterns:
            strategy_vectors = []
            strategy_ids = []

            for pattern_id, pattern in self.strategy_patterns.items():
                pattern_text = self._extract_pattern_text(pattern)
                vector = self._encode_text(pattern_text)
                if vector is not None:
                    strategy_vectors.append(vector)
                    strategy_ids.append(pattern_id)

            if strategy_vectors:
                strategy_vectors = np.array(strategy_vectors).astype('float32')
                self.strategy_index = faiss.IndexFlatIP(strategy_vectors.shape[1])
                self.strategy_index.add(strategy_vectors)
                self.strategy_ids = strategy_ids
                
                # Save index to disk
                self._save_strategy_index()

    def _rebuild_simple_indices(self):
        """Rebuild simplified vector indices"""
        # Simplified implementation: store all vectors for linear search
        self.case_vectors = {}
        self.strategy_vectors = {}

        # Rebuild case vectors
        case_success = 0
        for case_id, case in self.historical_cases.items():
            try:
                case_text = self._extract_case_text(case)
                if case_text.strip():  # Ensure text is not empty
                    vector = self._encode_text(case_text)
                    if vector is not None:
                        self.case_vectors[case_id] = vector
                        case_success += 1
                    else:
                        logger.warning(f"⚠️ Case {case_id} vector encoding returned None")
                else:
                    logger.warning(f"⚠️ Case {case_id} text is empty")
            except Exception as e:
                logger.warning(f"⚠️ Case {case_id} vector build failed: {e}")

        # Rebuild strategy vectors
        strategy_success = 0
        for pattern_id, pattern in self.strategy_patterns.items():
            try:
                pattern_text = self._extract_pattern_text(pattern)
                if pattern_text.strip():  # Ensure text is not empty
                    vector = self._encode_text(pattern_text)
                    if vector is not None:
                        self.strategy_vectors[pattern_id] = vector
                        strategy_success += 1
                    else:
                        logger.warning(f"⚠️ Strategy {pattern_id} vector encoding returned None")
                else:
                    logger.warning(f"⚠️ Strategy {pattern_id} text is empty")
            except Exception as e:
                logger.warning(f"⚠️ Strategy {pattern_id} vector build failed: {e}")

        logger.info(f"✅ Vector index rebuild complete: {case_success}/{len(self.historical_cases)} cases, {strategy_success}/{len(self.strategy_patterns)} strategies")

    def _update_case_index(self):
        """Update case vector index"""
        try:
            if not hasattr(self, 'case_vectors') or self.case_vectors is None:
                self.case_vectors = {}
            
            # Rebuild case vector index
            for case_id, case in self.historical_cases.items():
                if case_id not in self.case_vectors:
                    case_text = self._extract_case_text(case)
                    vector = self._encode_text(case_text)
                    if vector is not None:
                        self.case_vectors[case_id] = vector
            
            logger.info(f"✅ Case vector index updated, current case count: {len(self.case_vectors)}")
            
        except Exception as e:
            logger.error(f"❌ Case vector index update failed: {e}")

    def _update_strategy_index(self):
        """Update strategy vector index"""
        try:
            if not hasattr(self, 'strategy_vectors') or self.strategy_vectors is None:
                self.strategy_vectors = {}
            
            # Rebuild strategy vector index
            for pattern_id, pattern in self.strategy_patterns.items():
                if pattern_id not in self.strategy_vectors:
                    pattern_text = self._extract_pattern_text(pattern)
                    vector = self._encode_text(pattern_text)
                    if vector is not None:
                        self.strategy_vectors[pattern_id] = vector
            
            logger.info(f"✅ Strategy vector index updated, current strategy count: {len(self.strategy_vectors)}")
            
        except Exception as e:
            logger.error(f"❌ Strategy vector index update failed: {e}")

    def retrieve(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Execute retrieval - search similar query and strategic_decision from action_logs"""
        start_time = datetime.now()
        results = []

        try:
            # Check for incremental data and update FAISS index if needed
            self._check_and_update_faiss_index_if_needed()
            
            # Retrieve similar queries from action_logs
            action_logs_results = self._retrieve_from_action_logs(query)
            results.extend(action_logs_results)

            # If no results from action_logs, return empty
            if not results:
                logger.info("🔍 No results in action_logs, returning empty")
                return []

            # Sort and filter results
            results = self._rank_and_filter_results(results, query)

            # Compute execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"🔍 Retrieval complete: query='{query.query_text}', results={len(results)}, time={execution_time:.3f}s")

        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            # Return default strategies on failure
            return self._get_default_strategies(query)

        return results

    def _retrieve_from_action_logs(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Retrieve similar query and strategic_decision from action_logs"""
        results = []
        
        try:
            # Connect to database using self.db_path
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if action_logs table exists, create if not
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='action_logs'")
            if not cursor.fetchone():
                logger.info("📝 action_logs table does not exist, creating...")
                cursor.execute('''
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
                conn.commit()
                logger.info("✅ action_logs table created successfully")
            
            # If table is empty, return empty
            cursor.execute("SELECT COUNT(*) FROM action_logs")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.info("📊 action_logs table is empty, returning empty")
                conn.close()
                return results
            
            # Encode query text
            query_vector = self._encode_text(query.query_text)
            if query_vector is None:
                logger.warning("⚠️ Query text encoding failed, using keyword match")
                return self._fallback_action_logs_search(query, conn)
            
            # Build or load FAISS index for query_text
            if not hasattr(self, 'query_text_index') or self.query_text_index is None:
                # First try loading saved query_text index
                if not self._load_query_text_index():
                    # Rebuild if loading fails
                    self._build_query_text_faiss_index(conn)

            # If embedding dimension changed since the index was built, faiss will hard-fail.
            # Rebuild the index from DB to match the current query embedding dimension.
            if hasattr(self, 'query_text_index') and self.query_text_index is not None:
                qdim = int(query_vector.shape[0])
                if int(self.query_text_index.d) != qdim:
                    logger.warning(
                        f"⚠️ query_text FAISS dim mismatch: index.d={int(self.query_text_index.d)} vs query_dim={qdim}. Rebuilding index..."
                    )
                    self.query_text_index = None
                    self.query_text_ids = []
                    self._build_query_text_faiss_index(conn)
            
            # Use FAISS to search similar query_text
            if hasattr(self, 'query_text_index') and self.query_text_index is not None:
                # Search for most similar query_text
                scores, indices = self.query_text_index.search(
                    query_vector.reshape(1, -1).astype('float32'), 
                    min(query.max_results, len(self.query_text_ids))
                )
                
                # Get matched action_logs ids
                matched_ids = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx < len(self.query_text_ids) and score >= query.similarity_threshold:
                        action_log_id = self.query_text_ids[idx]
                        matched_ids.append((action_log_id, float(score)))
                
                # Query action_logs by matched ids
                if matched_ids:
                    # Build IN query
                    id_list = [str(id_score[0]) for id_score in matched_ids]
                    placeholders = ','.join(['?' for _ in id_list])
                    
                    cursor.execute(f"""
                        SELECT id, action_id, timestamp, execution_time, success, effectiveness_score,
                               situation_context, strategic_decision, execution_details, lessons_learned,
                               full_log, created_at
                        FROM action_logs
                        WHERE id IN ({placeholders})
                        ORDER BY effectiveness_score DESC, created_at DESC
                    """, id_list)
                    
                    action_logs = cursor.fetchall()
                    
                    # Build results, keep similarity order
                    id_to_score = {id_score[0]: id_score[1] for id_score in matched_ids}
                    
                    for action_log in action_logs:
                        action_log_id = action_log[0]
                        similarity_score = id_to_score.get(action_log_id, 0.0)
                        
                        # Parse strategic_decision
                        strategic_decision = action_log[7]  # strategic_decision column
                        
                        # Parse key content from strategic_decision
                        parsed_content = self._parse_strategic_decision(strategic_decision)
                        
                        # Create RetrievalResult
                        result = RetrievalResult(
                            item_id=str(action_log[0]),  # id
                            item_type="action_log",
                            content={
                                "action_id": action_log[1],
                                "timestamp": action_log[2],
                                "execution_time": action_log[3],
                                "success": action_log[4],
                                "effectiveness_score": action_log[5],
                                "situation_context": action_log[6],
                                "strategic_decision": strategic_decision,
                                "parsed_content": parsed_content,  # Parsed key content
                                "execution_details": action_log[8],
                                "lessons_learned": action_log[9],
                                "full_log": action_log[10],
                                "created_at": action_log[11]
                            },
                            similarity_score=similarity_score,
                            relevance_score=similarity_score,  # Use FAISS similarity score directly
                            metadata={
                                "action_id": action_log[1],
                                "effectiveness_score": action_log[5],
                                "success": action_log[4],
                                "timestamp": action_log[2]
                            }
                        )
                        results.append(result)
            
            conn.close()
            logger.info(f"🔍 Retrieved {len(results)} results from action_logs")
            
        except Exception as e:
            logger.error(f"❌ action_logs retrieval failed: {type(e).__name__}: {e}")
        
        return results
    
    def _check_and_update_faiss_index_if_needed(self):
        """Check for incremental data and update FAISS index if needed"""
        try:
            # Get total action_logs count
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM action_logs")
            current_count = cursor.fetchone()[0]
            conn.close()
            
            # Get indexed record count
            indexed_count = 0
            if hasattr(self, 'query_text_ids') and self.query_text_ids:
                indexed_count = len(self.query_text_ids)
            
            # Update index if new data exists
            if current_count > indexed_count:
                logger.info(f"🔄 Incremental data detected: db {current_count} records, indexed {indexed_count}, updating index...")
                self._rebuild_query_text_index_with_incremental_data()
            else:
                logger.debug(f"📊 No incremental data: db {current_count} records, indexed {indexed_count}")
                
        except Exception as e:
            logger.error(f"❌ Incremental data check failed: {e}")
    
    def _rebuild_query_text_index_with_incremental_data(self):
        """Incrementally update query_text index, only handle new data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get indexed ID list
            indexed_ids = set()
            if hasattr(self, 'query_text_ids') and self.query_text_ids:
                indexed_ids = set(self.query_text_ids)
            
            # Get all records with situation_context
            cursor.execute("""
                SELECT id, situation_context
                FROM action_logs
                WHERE situation_context IS NOT NULL AND situation_context != ''
                ORDER BY created_at DESC
            """)
            
            query_records = cursor.fetchall()
            
            if not query_records:
                logger.info("📋 No valid situation_context data found")
                conn.close()
                return
            
            # Filter new records
            new_records = []
            for record in query_records:
                action_log_id, situation_context = record
                if action_log_id not in indexed_ids and situation_context.strip():
                    new_records.append((action_log_id, situation_context))
            
            if not new_records:
                logger.info("📊 No new incremental data to process")
                conn.close()
                return
            
            logger.info(f"🔄 Found {len(new_records)} new incremental records, processing...")
            
            # Process new data
            new_vectors = []
            new_ids = []
            
            for action_log_id, situation_context in new_records:
                vector = self._encode_text(situation_context)
                if vector is not None:
                    new_vectors.append(vector)
                    new_ids.append(action_log_id)
            
            if new_vectors:
                new_vectors = np.array(new_vectors).astype('float32')
                
                # Create index if it does not exist
                if not hasattr(self, 'query_text_index') or self.query_text_index is None:
                    self.query_text_index = faiss.IndexFlatIP(new_vectors.shape[1])
                    self.query_text_ids = []
                elif int(self.query_text_index.d) != int(new_vectors.shape[1]):
                    logger.warning(
                        f"⚠️ query_text FAISS dim mismatch during incremental update: index.d={int(self.query_text_index.d)} vs new_dim={int(new_vectors.shape[1])}. Rebuilding full index..."
                    )
                    self.query_text_index = None
                    self.query_text_ids = []
                    self._build_query_text_faiss_index(conn)
                    conn.close()
                    return
                
                # Add new vectors to existing index
                self.query_text_index.add(new_vectors)
                self.query_text_ids.extend(new_ids)
                
                # Save updated index
                self._save_query_text_index()
                
                logger.info(f"✅ Incremental update to query_text FAISS index complete: added {len(new_vectors)} vectors, total {len(self.query_text_ids)} vectors")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Incremental update of query_text FAISS index failed: {type(e).__name__}: {e}")

    def _parse_strategic_decision(self, strategic_decision: str) -> str:
        """Parse key content in strategic_decision: core_counter_argument, leader_instruction, amplifier_plan"""
        try:
            if not strategic_decision or not isinstance(strategic_decision, str):
                return ""
            
            # Try parsing strategic_decision as JSON
            try:
                import json
                decision_data = json.loads(strategic_decision)
                
                # Extract key content
                parsed_parts = []
                
                # 1. core_counter_argument
                if "core_counter_argument" in decision_data:
                    parsed_parts.append(f"Core counter-argument: {decision_data['core_counter_argument']}")
                
                # 2. leader_instruction
                if "leader_instruction" in decision_data:
                    leader_inst = decision_data["leader_instruction"]
                    leader_parts = []
                    
                    if "tone" in leader_inst:
                        leader_parts.append(f"Tone: {leader_inst['tone']}")
                    if "speaking_style" in leader_inst:
                        leader_parts.append(f"Speaking style: {leader_inst['speaking_style']}")
                    if "key_points" in leader_inst and isinstance(leader_inst["key_points"], list):
                        leader_parts.append(f"Key points: {'; '.join(leader_inst['key_points'])}")
                    if "target_audience" in leader_inst:
                        leader_parts.append(f"Target audience: {leader_inst['target_audience']}")
                    if "core_message" in leader_inst:
                        leader_parts.append(f"Core message: {leader_inst['core_message']}")
                    if "approach" in leader_inst:
                        leader_parts.append(f"Approach: {leader_inst['approach']}")
                    
                    if leader_parts:
                        parsed_parts.append(f"Leader guidance: {'; '.join(leader_parts)}")
                
                # 3. amplifier_plan
                if "amplifier_plan" in decision_data:
                    amplifier_plan = decision_data["amplifier_plan"]
                    amplifier_parts = []
                    
                    if "total_agents" in amplifier_plan:
                        amplifier_parts.append(f"Total agents: {amplifier_plan['total_agents']}")
                    if "role_distribution" in amplifier_plan:
                        role_dist = amplifier_plan["role_distribution"]
                        role_parts = [f"{k}: {v}" for k, v in role_dist.items()]
                        amplifier_parts.append(f"Role distribution: {', '.join(role_parts)}")
                    if "timing_strategy" in amplifier_plan:
                        amplifier_parts.append(f"Timing strategy: {amplifier_plan['timing_strategy']}")
                    if "coordination_notes" in amplifier_plan:
                        amplifier_parts.append(f"Coordination notes: {amplifier_plan['coordination_notes']}")
                    if "decision_factors" in amplifier_plan:
                        decision_factors = amplifier_plan["decision_factors"]
                        factor_parts = [f"{k}: {v}" for k, v in decision_factors.items()]
                        amplifier_parts.append(f"Decision factors: {', '.join(factor_parts)}")
                    
                    if amplifier_parts:
                        parsed_parts.append(f"Amplifier plan: {'; '.join(amplifier_parts)}")
                
                # 4. expected_outcome
                if "expected_outcome" in decision_data:
                    parsed_parts.append(f"Expected outcome: {decision_data['expected_outcome']}")
                
                # 5. risk_assessment
                if "risk_assessment" in decision_data:
                    parsed_parts.append(f"Risk assessment: {decision_data['risk_assessment']}")
                
                return " | ".join(parsed_parts)
                
            except json.JSONDecodeError:
                # If not JSON, return original content
                return strategic_decision
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse strategic_decision: {e}")
            return strategic_decision if strategic_decision else ""

    def _build_query_text_faiss_index(self, conn):
        """Build FAISS index for query_text; store query_text to action_logs.id mapping"""
        try:
            cursor = conn.cursor()
            
            # Get all records with situation_context, use situation_context as query_text
            cursor.execute("""
                SELECT id, situation_context
                FROM action_logs
                WHERE situation_context IS NOT NULL AND situation_context != ''
                ORDER BY created_at DESC
            """)
            
            query_records = cursor.fetchall()
            
            if not query_records:
                logger.info("📋 No valid situation_context data found")
                return
            
            vectors = []
            query_text_ids = []
            
            for record in query_records:
                action_log_id, situation_context = record
                
                if situation_context.strip():
                    # Vectorize using situation_context as query_text
                    vector = self._encode_text(situation_context)
                    if vector is not None:
                        vectors.append(vector)
                        query_text_ids.append(action_log_id)
            
            if vectors:
                vectors = np.array(vectors).astype('float32')
                self.query_text_index = faiss.IndexFlatIP(vectors.shape[1])
                self.query_text_index.add(vectors)
                self.query_text_ids = query_text_ids

                # Keep config/metadata consistent with the actual embedding dimension.
                self.config["vector_dimension"] = int(vectors.shape[1])
                
                logger.info(f"✅ Built query_text FAISS index with {len(vectors)} vectors")
                
                # Save index to disk
                self._save_query_text_index()
            
        except Exception as e:
            logger.error(f"❌ Build query_text FAISS index failed: {e}")
    
    def _save_faiss_index(self, index, index_path: Path, metadata: Dict[str, Any], metadata_path: Path):
        """Save FAISS index to disk"""
        try:
            if index is not None:
                # Save FAISS index
                faiss.write_index(index, str(index_path))
                
                # Save metadata
                with open(metadata_path, 'wb') as f:
                    pickle.dump(metadata, f)
                
                logger.info(f"✅ FAISS index saved to: {index_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save FAISS index: {e}")
            return False
    
    def _load_faiss_index(self, index_path: Path, metadata_path: Path) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """Load FAISS index from disk"""
        try:
            if index_path.exists() and metadata_path.exists():
                # Load FAISS index
                index = faiss.read_index(str(index_path))
                
                # Load metadata
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                
                logger.info(f"✅ FAISS index loaded from disk: {index_path}")
                return index, metadata
            else:
                logger.info(f"📋 Index file not found, will rebuild: {index_path}")
                return None, None
        except Exception as e:
            logger.error(f"❌ Failed to load FAISS index: {e}")
            return None, None
    
    def _save_case_index(self):
        """Save case index"""
        if self.case_index is not None and hasattr(self, 'case_ids'):
            metadata = {
                'case_ids': self.case_ids,
                'vector_dimension': self.config["vector_dimension"],
                'index_type': 'case',
                'created_at': datetime.now().isoformat(),
                'vector_count': len(self.case_ids)
            }
            return self._save_faiss_index(self.case_index, self.case_index_path, metadata, self.case_metadata_path)
        return False
    
    def _load_case_index(self):
        """Load case index"""
        index, metadata = self._load_faiss_index(self.case_index_path, self.case_metadata_path)
        if index is not None and metadata is not None:
            self.case_index = index
            self.case_ids = metadata.get('case_ids', [])
            logger.info(f"✅ Case index loaded, contains {len(self.case_ids)} vectors")
            return True
        return False
    
    def _save_strategy_index(self):
        """Save strategy index"""
        if self.strategy_index is not None and hasattr(self, 'strategy_ids'):
            metadata = {
                'strategy_ids': self.strategy_ids,
                'vector_dimension': self.config["vector_dimension"],
                'index_type': 'strategy',
                'created_at': datetime.now().isoformat(),
                'vector_count': len(self.strategy_ids)
            }
            return self._save_faiss_index(self.strategy_index, self.strategy_index_path, metadata, self.strategy_metadata_path)
        return False
    
    def _load_strategy_index(self):
        """Load strategy index"""
        index, metadata = self._load_faiss_index(self.strategy_index_path, self.strategy_metadata_path)
        if index is not None and metadata is not None:
            self.strategy_index = index
            self.strategy_ids = metadata.get('strategy_ids', [])
            logger.info(f"✅ Strategy index loaded, contains {len(self.strategy_ids)} vectors")
            return True
        return False
    
    def _save_query_text_index(self):
        """Save query text index"""
        if hasattr(self, 'query_text_index') and self.query_text_index is not None and hasattr(self, 'query_text_ids'):
            index_dim = int(getattr(self.query_text_index, "d", self.config["vector_dimension"]))
            metadata = {
                'query_text_ids': self.query_text_ids,
                'vector_dimension': index_dim,
                'index_type': 'query_text',
                'created_at': datetime.now().isoformat(),
                'vector_count': len(self.query_text_ids)
            }
            return self._save_faiss_index(self.query_text_index, self.query_text_index_path, metadata, self.query_text_metadata_path)
        return False
    
    def _load_query_text_index(self):
        """Load query text index"""
        index, metadata = self._load_faiss_index(self.query_text_index_path, self.query_text_metadata_path)
        if index is not None and metadata is not None:
            self.query_text_index = index
            self.query_text_ids = metadata.get('query_text_ids', [])
            try:
                self.config["vector_dimension"] = int(self.query_text_index.d)
            except Exception:
                pass
            meta_dim = metadata.get('vector_dimension')
            if meta_dim is not None and int(meta_dim) != int(getattr(self.query_text_index, "d", meta_dim)):
                logger.warning(
                    f"⚠️ Query text index metadata dim mismatch: meta={meta_dim} vs index.d={int(self.query_text_index.d)}. Using index.d."
                )
            logger.info(f"✅ Query text index loaded, contains {len(self.query_text_ids)} vectors")
            return True
        return False
    
    def save_all_indices(self):
        """Manually save all indices"""
        saved_count = 0
        
        if self._save_case_index():
            saved_count += 1
            logger.info("✅ Case index saved")
        
        if self._save_strategy_index():
            saved_count += 1
            logger.info("✅ Strategy index saved")
        
        if self._save_query_text_index():
            saved_count += 1
            logger.info("✅ Query text index saved")
        
        logger.info(f"📊 Saved {saved_count} indices in total")
        return saved_count > 0
    
    def load_all_indices(self):
        """Manually load all indices"""
        loaded_count = 0
        
        if self._load_case_index():
            loaded_count += 1
            logger.info("✅ Case index loaded")
        
        if self._load_strategy_index():
            loaded_count += 1
            logger.info("✅ Strategy index loaded")
        
        if self._load_query_text_index():
            loaded_count += 1
            logger.info("✅ Query text index loaded")
        
        logger.info(f"📊 Loaded {loaded_count} indices in total")
        return loaded_count > 0

    def _calculate_action_log_relevance(self, action_log, query: RetrievalQuery) -> float:
        """Calculate action_log relevance score - mainly similarity with supporting weights"""
        relevance = 0.0
        
        # 1. Base relevance score (primary weight)
        base_relevance = 0.6  # 60% base score
        
        # 2. effectiveness_score weight (20%)
        effectiveness_score = action_log[5] if action_log[5] is not None else 0.5
        relevance += effectiveness_score * 0.2
        
        # 3. success weight (10%)
        success = action_log[4] if action_log[4] is not None else False
        if success:
            relevance += 0.1
        
        # 4. Freshness weight (10%)
        try:
            if action_log[11]:  # created_at
                created_at = datetime.fromisoformat(action_log[11].replace('Z', '+00:00'))
                days_old = (datetime.now() - created_at.replace(tzinfo=None)).days
                freshness = max(0, 1.0 - days_old / 30)  # Reward freshness within 30 days
                relevance += freshness * 0.1
        except:
            relevance += 0.05  # Default score
        
        # 5. Execution time weight (5%)
        execution_time = action_log[3] if action_log[3] is not None else 1.0
        time_score = max(0, 1.0 - execution_time / 10.0)  # Full score within 10 seconds
        relevance += time_score * 0.05
        
        # 6. Base relevance score
        relevance += base_relevance
        
        return min(1.0, relevance)

    def _fallback_action_logs_search(self, query: RetrievalQuery, conn) -> List[RetrievalResult]:
        """Keyword match search on action_logs (when vector retrieval fails)"""
        results = []
        query_words = set(query.query_text.lower().split())
        
        try:
            cursor = conn.cursor()
            
            # Fetch all action_logs records for keyword matching
            cursor.execute("""
                SELECT id, action_id, timestamp, execution_time, success, effectiveness_score,
                       situation_context, strategic_decision, execution_details, lessons_learned,
                       full_log, created_at
                FROM action_logs
                WHERE strategic_decision IS NOT NULL AND strategic_decision != ''
                ORDER BY effectiveness_score DESC, created_at DESC
            """)
            
            action_logs = cursor.fetchall()
            
            for action_log in action_logs:
                # Use situation_context for keyword matching
                situation_context = action_log[6] if action_log[6] else ""
                text_words = set(situation_context.lower().split())
                
                # Compute keyword overlap
                overlap = len(query_words & text_words)
                if overlap > 0:
                    similarity = overlap / len(query_words | text_words)
                    
                    if similarity >= 0.1:  # Lower threshold to get more results
                        strategic_decision = action_log[7]  # strategic_decision column
                        
                        # Parse key content from strategic_decision
                        parsed_content = self._parse_strategic_decision(strategic_decision)
                        
                        result = RetrievalResult(
                            item_id=str(action_log[0]),  # id
                            item_type="action_log",
                            content={
                                "action_id": action_log[1],
                                "timestamp": action_log[2],
                                "execution_time": action_log[3],
                                "success": action_log[4],
                                "effectiveness_score": action_log[5],
                                "situation_context": action_log[6],
                                "strategic_decision": strategic_decision,
                                "parsed_content": parsed_content,  # Parsed key content
                                "execution_details": action_log[8],
                                "lessons_learned": action_log[9],
                                "full_log": action_log[10],
                                "created_at": action_log[11]
                            },
                            similarity_score=similarity,
                            relevance_score=self._calculate_action_log_relevance(action_log, query),
                            metadata={
                                "action_id": action_log[1],
                                "effectiveness_score": action_log[5],
                                "success": action_log[4],
                                "timestamp": action_log[2]
                            }
                        )
                        results.append(result)
            
            logger.info(f"🔍 action_logs keyword match found {len(results)} results")
            
        except Exception as e:
            logger.error(f"❌ action_logs keyword match failed: {e}")
        
        return results

    def get_strategic_decisions(self, query: RetrievalQuery) -> List[str]:
        """Get parsed strategic_decision list"""
        results = self.retrieve(query)
        strategic_decisions = []
        
        for result in results:
            if result.item_type == "action_log" and "parsed_content" in result.content:
                parsed_content = result.content["parsed_content"]
                if parsed_content:
                    strategic_decisions.append(parsed_content)
        
        return strategic_decisions

    def _retrieve_cases(self, query: RetrievalQuery, query_vector: np.ndarray) -> List[RetrievalResult]:
        """Retrieve historical cases"""
        results = []

        # Use simplified retrieval (linear search)
        if hasattr(self, 'case_vectors') and self.case_vectors:
            for case_id, case_vector in self.case_vectors.items():
                # Use cosine similarity (dot product of normalized vectors)
                similarity = np.dot(query_vector, case_vector)

                if similarity >= query.similarity_threshold:
                    case = self.historical_cases[case_id]

                    result = RetrievalResult(
                        item_id=case_id,
                        item_type="case",
                        content=asdict(case),
                        similarity_score=float(similarity),
                        relevance_score=self._calculate_case_relevance(case, query),
                        metadata=self._extract_case_metadata(case) if query.include_metadata else {}
                    )
                    results.append(result)

        return results

    def _retrieve_strategies(self, query: RetrievalQuery, query_vector: np.ndarray) -> List[RetrievalResult]:
        """Retrieve strategy patterns"""
        results = []

        # Use simplified retrieval (linear search)
        if hasattr(self, 'strategy_vectors') and self.strategy_vectors:
            for pattern_id, pattern_vector in self.strategy_vectors.items():
                # Use cosine similarity (dot product of normalized vectors)
                similarity = np.dot(query_vector, pattern_vector)

                if similarity >= query.similarity_threshold:
                    pattern = self.strategy_patterns[pattern_id]

                    result = RetrievalResult(
                        item_id=pattern_id,
                        item_type="strategy",
                        content=asdict(pattern),
                        similarity_score=float(similarity),
                        relevance_score=self._calculate_strategy_relevance(pattern, query),
                        metadata=self._extract_strategy_metadata(pattern) if query.include_metadata else {}
                    )
                    results.append(result)

        return results

    def _calculate_case_relevance(self, case: HistoricalCase, query: RetrievalQuery) -> float:
        """Calculate case relevance"""
        relevance = 0.0

        # effectiveness_score weight
        relevance += case.effectiveness_score * 0.4

        # Context match
        context_match = self._calculate_context_match(case.context, query.context_filters)
        relevance += context_match * 0.3

        # Freshness
        days_old = (datetime.now() - case.timestamp).days
        freshness = max(0, 1.0 - days_old / 365)  # Reward freshness within a year
        relevance += freshness * 0.2

        # Tag match
        if query.context_filters.get("tags"):
            query_tags = set(query.context_filters["tags"])
            case_tags = set(case.tags)
            tag_overlap = len(query_tags & case_tags) / len(query_tags | case_tags) if query_tags | case_tags else 0
            relevance += tag_overlap * 0.1

        return min(1.0, relevance)

    def _calculate_strategy_relevance(self, pattern: StrategyPattern, query: RetrievalQuery) -> float:
        """Calculate strategy relevance"""
        relevance = 0.0

        # success_rate weight
        relevance += pattern.success_rate * 0.5

        # Usage frequency (validated strategies)
        usage_factor = min(1.0, pattern.usage_count / 10)  # Full score after 10 uses
        relevance += usage_factor * 0.2

        # Condition match
        condition_match = self._calculate_context_match(pattern.conditions, query.context_filters)
        relevance += condition_match * 0.2

        # Update freshness
        days_since_update = (datetime.now() - pattern.last_updated).days
        update_freshness = max(0, 1.0 - days_since_update / 180)  # Reward updates within 6 months
        relevance += update_freshness * 0.1

        return min(1.0, relevance)

    def _calculate_context_match(self, item_context: Dict[str, Any], query_filters: Dict[str, Any]) -> float:
        """Calculate context match score"""
        if not query_filters or not item_context:
            return 0.5  # Default medium match

        matches = 0
        total_filters = 0

        for key, query_value in query_filters.items():
            if key in item_context:
                item_value = item_context[key]

                if isinstance(query_value, (str, int, float)) and query_value == item_value:
                    matches += 1
                elif isinstance(query_value, list) and item_value in query_value:
                    matches += 1
                elif isinstance(query_value, dict) and isinstance(item_value, dict):
                    # Recursively match nested dicts
                    nested_match = self._calculate_context_match(item_value, query_value)
                    matches += nested_match

                total_filters += 1

        return matches / total_filters if total_filters > 0 else 0.5

    def _extract_case_metadata(self, case: HistoricalCase) -> Dict[str, Any]:
        """Extract case metadata"""
        return {
            "timestamp": case.timestamp.isoformat(),
            "effectiveness_score": case.effectiveness_score,
            "tags": case.tags,
            "actions_count": len(case.actions_taken),
            "lessons_count": len(case.lessons_learned)
        }

    def _extract_strategy_metadata(self, pattern: StrategyPattern) -> Dict[str, Any]:
        """Extract strategy metadata"""
        return {
            "success_rate": pattern.success_rate,
            "usage_count": pattern.usage_count,
            "last_updated": pattern.last_updated.isoformat(),
            "actions_count": len(pattern.actions),
            "variations_count": len(pattern.variations)
        }

    def _rank_and_filter_results(self, results: List[RetrievalResult], query: RetrievalQuery) -> List[RetrievalResult]:
        """Sort and filter results - primarily by similarity score"""
        # Sort by similarity score because relevance_score now equals similarity_score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit result count
        return results[:query.max_results]

    # Retrieval log recording removed

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system statistics information"""
        stats = {
            "data_counts": {
                "historical_cases": len(self.historical_cases),
                "strategy_patterns": len(self.strategy_patterns)
            },
            "index_status": {
                "case_vectors": len(self.case_vectors) if hasattr(self, 'case_vectors') and self.case_vectors else 0,
                "strategy_vectors": len(self.strategy_vectors) if hasattr(self, 'strategy_vectors') and self.strategy_vectors else 0
            },
            "performance": {
                "encoder_available": self.encoder is not None,
                "faiss_available": FAISS_AVAILABLE
            }
        }

        # Get retrieval statistics
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM retrieval_logs")
            stats["retrieval_stats"] = {
                "total_queries": cursor.fetchone()[0]
            }

            cursor.execute("SELECT AVG(execution_time) FROM retrieval_logs")
            avg_time = cursor.fetchone()[0]
            stats["retrieval_stats"]["avg_execution_time"] = avg_time if avg_time else 0.0

            conn.close()

        except Exception as e:
            logger.warning(f"⚠️ Failed to get statistics information: {e}")
            stats["retrieval_stats"] = {"total_queries": 0, "avg_execution_time": 0.0}

        return stats

    def _get_default_strategies(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Get default strategy suggestions (when database is empty)"""
        default_strategies = [
            {
                "pattern_id": "default_1",
                "pattern_name": "Basic Balance Strategy",
                "description": "Use a basic viewpoint-balance strategy when historical data is lacking",
                "conditions": {"context": "empty_database"},
                "actions": [
                    {"type": "monitor", "description": "Continuously monitor user interactions"},
                    {"type": "analyze", "description": "Analyze viewpoint distribution"},
                    {"type": "intervene", "description": "Apply mild intervention when necessary"}
                ],
                "success_rate": 0.5,
                "usage_count": 0,
                "last_updated": datetime.now(),
                "variations": []
            },
            {
                "pattern_id": "default_2", 
                "pattern_name": "Learning-Oriented Strategy",
                "description": "Focus on collecting data and learning user behavior patterns",
                "conditions": {"context": "learning_phase"},
                "actions": [
                    {"type": "observe", "description": "Observe user behavior patterns"},
                    {"type": "collect", "description": "Collect interaction data"},
                    {"type": "adapt", "description": "Adjust strategy based on observations"}
                ],
                "success_rate": 0.6,
                "usage_count": 0,
                "last_updated": datetime.now(),
                "variations": []
            }
        ]
        
        results = []
        for strategy_data in default_strategies:
            pattern = StrategyPattern(**strategy_data)
            result = RetrievalResult(
                item_id=pattern.pattern_id,
                item_type="strategy",
                content=asdict(pattern),
                similarity_score=0.5,  # Default similarity
                relevance_score=0.6,   # Default relevance
                metadata={"is_default": True}
            )
            results.append(result)
        
        logger.info(f"📋 Returned {len(results)} default strategy suggestions")
        return results[:query.max_results]

    def _fallback_keyword_search(self, query: RetrievalQuery) -> List[RetrievalResult]:
        """Keyword match retrieval (when vector retrieval fails)"""
        results = []
        query_words = set(query.query_text.lower().split())
        
        # Search in historical cases
        if query.query_type in ["case", "mixed"]:
            for case_id, case in self.historical_cases.items():
                case_text = self._extract_case_text(case).lower()
                case_words = set(case_text.split())
                
                # Compute keyword overlap
                overlap = len(query_words & case_words)
                if overlap > 0:
                    similarity = overlap / len(query_words | case_words)
                    
                    if similarity >= 0.1:  # Lower threshold to get more results
                        result = RetrievalResult(
                            item_id=case_id,
                            item_type="case",
                            content=asdict(case),
                            similarity_score=similarity,
                            relevance_score=self._calculate_case_relevance(case, query),
                            metadata=self._extract_case_metadata(case) if query.include_metadata else {}
                        )
                        results.append(result)
        
        # Search in strategy patterns
        if query.query_type in ["strategy", "mixed"]:
            for pattern_id, pattern in self.strategy_patterns.items():
                pattern_text = self._extract_pattern_text(pattern).lower()
                pattern_words = set(pattern_text.split())
                
                # Compute keyword overlap
                overlap = len(query_words & pattern_words)
                if overlap > 0:
                    similarity = overlap / len(query_words | pattern_words)
                    
                    if similarity >= 0.1:  # Lower threshold to get more results
                        result = RetrievalResult(
                            item_id=pattern_id,
                            item_type="strategy",
                            content=asdict(pattern),
                            similarity_score=similarity,
                            relevance_score=self._calculate_strategy_relevance(pattern, query),
                            metadata=self._extract_strategy_metadata(pattern) if query.include_metadata else {}
                        )
                        results.append(result)
        
        logger.info(f"🔍 Keyword match found {len(results)} results")
        return results

    def learn_from_intervention(self, intervention_data: Dict[str, Any]):
        """Learn from intervention results and update knowledge base"""
        try:
            # Create historical case
            case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            case = HistoricalCase(
                case_id=case_id,
                timestamp=datetime.now(),
                context=intervention_data.get("context", {}),
                strategy_used=intervention_data.get("strategy", {}),
                actions_taken=intervention_data.get("actions", []),
                results=intervention_data.get("results", {}),
                effectiveness_score=intervention_data.get("effectiveness_score", 0.5),
                lessons_learned=intervention_data.get("lessons_learned", []),
                tags=intervention_data.get("tags", [])
            )
            
            # Add to knowledge base
            self.add_historical_case(case)
            
            # If effectiveness is good, try extracting strategy pattern
            if case.effectiveness_score >= 0.7:
                self._extract_strategy_pattern(case)
            
            logger.info(f"✅ Learning from intervention complete: {case_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to learn from intervention: {e}")

    def _extract_strategy_pattern(self, case: HistoricalCase):
        """Extract strategy pattern from successful case"""
        try:
            # Check if similar strategy exists
            existing_patterns = self._find_similar_patterns(case)
            
            if existing_patterns:
                # Update existing strategies
                for pattern_id in existing_patterns:
                    self._update_existing_pattern(pattern_id, case)
            else:
                # Create new strategy pattern
                pattern_id = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                
                pattern = StrategyPattern(
                    pattern_id=pattern_id,
                    pattern_name=f"Case-Based Strategy_{case.case_id[:8]}",
                    description=f"Successful strategy extracted from case {case.case_id}",
                    conditions=case.context,
                    actions=case.actions_taken,
                    success_rate=case.effectiveness_score,
                    usage_count=1,
                    last_updated=datetime.now(),
                    variations=[]
                )
                
                self.add_strategy_pattern(pattern)
                logger.info(f"✅ Created new strategy pattern: {pattern_id}")
                
        except Exception as e:
            logger.error(f"❌ Strategy pattern extraction failed: {e}")

    def _find_similar_patterns(self, case: HistoricalCase) -> List[str]:
        """Find similar strategy patterns"""
        similar_patterns = []
        
        for pattern_id, pattern in self.strategy_patterns.items():
            # Simple similarity calculation (condition match)
            condition_match = self._calculate_context_match(pattern.conditions, case.context)
            if condition_match >= 0.6:  # 60%+ match
                similar_patterns.append(pattern_id)
        
        return similar_patterns

    def _update_existing_pattern(self, pattern_id: str, case: HistoricalCase):
        """Update existing strategy pattern"""
        try:
            pattern = self.strategy_patterns[pattern_id]
            
            # Update success rate (weighted average)
            total_usage = pattern.usage_count + 1
            new_success_rate = (pattern.success_rate * pattern.usage_count + case.effectiveness_score) / total_usage
            
            # Update pattern
            pattern.success_rate = new_success_rate
            pattern.usage_count = total_usage
            pattern.last_updated = datetime.now()
            
            # Add variation
            if case.actions_taken not in pattern.variations:
                pattern.variations.append(case.actions_taken)
            
            # Save update
            self.add_strategy_pattern(pattern)
            
            logger.info(f"✅ Updated strategy pattern: {pattern_id}, new success rate: {new_success_rate:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update strategy pattern: {e}")

    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get learning statistics"""
        stats = {
            "total_cases": len(self.historical_cases),
            "total_patterns": len(self.strategy_patterns),
            "avg_effectiveness": 0.0,
            "recent_learning": []
        }
        
        if self.historical_cases:
            # Compute average effectiveness
            total_effectiveness = sum(case.effectiveness_score for case in self.historical_cases.values())
            stats["avg_effectiveness"] = total_effectiveness / len(self.historical_cases)
            
            # Recent learning records
            recent_cases = sorted(
                self.historical_cases.values(),
                key=lambda x: x.timestamp,
                reverse=True
            )[:5]
            
            stats["recent_learning"] = [
                {
                    "case_id": case.case_id,
                    "timestamp": case.timestamp.isoformat(),
                    "effectiveness": case.effectiveness_score,
                    "tags": case.tags
                }
                for case in recent_cases
            ]
        
        return stats
