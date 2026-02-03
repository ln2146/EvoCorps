#!/usr/bin/env python3
"""
Enhanced opinion processing system tailored to user requirements.
Supports FAISS vector search, precise workflow control, and Wikipedia API integration.
"""

import json
import sqlite3
import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import time

# Import configuration
try:
    from .config import (
        TOPICS,
        KEYWORD_SIMILARITY_THRESHOLD, VIEWPOINT_SIMILARITY_THRESHOLD,
        MAX_WIKIPEDIA_RESULTS, MAX_EVIDENCE_PER_VIEWPOINT, DEFAULT_DB_PATH
    )
except ImportError:
    from config import (
        TOPICS,
        KEYWORD_SIMILARITY_THRESHOLD, VIEWPOINT_SIMILARITY_THRESHOLD,
        MAX_WIKIPEDIA_RESULTS, MAX_EVIDENCE_PER_VIEWPOINT, DEFAULT_DB_PATH
    )

# FAISS vector search
try:
    import faiss  # type: ignore
except ModuleNotFoundError:
    try:
        from . import faiss_fallback as faiss  # type: ignore
    except ImportError:
        import faiss_fallback as faiss  # type: ignore

# Wikipedia API
import wikipediaapi

# OpenAI clients
import sys

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from keys import OPENAI_BASE_URL, OPENAI_API_KEY
from multi_model_selector import multi_model_selector
import math

# Import network configuration
try:
    from .network_config import configure_network_for_wikipedia, test_wikipedia_connection
except ImportError:
    try:
        from network_config import configure_network_for_wikipedia, test_wikipedia_connection
    except ImportError:
        # If both imports fail, define fallback functions
        def configure_network_for_wikipedia():
            print("🔧 Using simplified network configuration...")
            return True

        def test_wikipedia_connection():
            print("🔍 Skipping Wikipedia connection test...")
            return True

class EnhancedOpinionSystem:
    """Enhanced opinion processing system"""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        # Ensure database path is absolute and directories exist
        if not os.path.isabs(db_path):
            # Capture current script directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(current_dir, db_path)
        else:
            self.db_path = db_path
        
        # Ensure the database directory exists
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"✅ Created database directory: {db_dir}")
        
        self.model_selector = multi_model_selector
        self.llm_base_url = OPENAI_BASE_URL
        self.llm_api_key = OPENAI_API_KEY
        self.llm_client, self.llm_model_name = self.model_selector.create_openai_client_with_base_url(
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            role="fact_checker",
        )
        self.embedding_client, self.embedding_model_name = self.model_selector.create_embedding_client()
        self.embedding_dim = None
        
        # 14 topics (loaded from config)
        self.topics = TOPICS
        
        # Threshold settings (from config)
        self.keyword_similarity_threshold = KEYWORD_SIMILARITY_THRESHOLD
        self.viewpoint_similarity_threshold = VIEWPOINT_SIMILARITY_THRESHOLD
        
        if not self.llm_client:
            raise RuntimeError("Failed to initialize LLM client for evidence system.")
        if not self.embedding_client:
            raise RuntimeError("Failed to initialize embedding client for evidence system.")
        
        self.keyword_vectors = None
        self.viewpoint_vectors = None
        self.faiss_keyword_index = None
        self.faiss_viewpoint_index = None
        
        # Use FAISS as embedding cache
        self.embedding_cache_index = None
        self.embedding_cache_metadata = {}
        
        # Configure network environment
        print("🔧 Configuring network environment...")
        configure_network_for_wikipedia()

        # Initialize the database
        self._init_database()
        self._load_vectors()

        # Test the Wikipedia connection
        print("🔍 Testing Wikipedia connection...")
        if not test_wikipedia_connection():
            print("⚠️ Wikipedia connection test failed, continuing anyway")
        
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Retrieve embedding vector for text using FAISS cache."""
        # Initialize embedding cache index if missing
        if self.embedding_cache_index is None:
            self._init_embedding_cache()  # auto-detects dimensions
        
        # Check whether text already exists in FAISS index
        if self.embedding_cache_index.ntotal > 0:
            # First check for exact matches to skip extra API calls
            for idx, metadata in self.embedding_cache_metadata.items():
                if metadata.get('text') == text:
                    # Grab embeddings from cache
                    cached_embedding = self.embedding_cache_index.reconstruct(int(idx))
                    return cached_embedding
        
        # Generate a new embedding if cache miss
        embedding = self._get_embedding_from_api(text)
        
        # Add to FAISS cache
        self._add_to_embedding_cache(text, embedding)
        
        return embedding
    
    def _get_embedding_from_api(self, text: str) -> np.ndarray:
        """Fetch embedding vector from the API."""
        response = self.embedding_client.embeddings.create(
            input=text,
            model=self.embedding_model_name
        )
        # Keep dtype stable; faiss expects float32 vectors.
        return np.asarray(response.data[0].embedding, dtype='float32')

    def _init_embedding_cache(self, dimension: int = None):
        """Initialize the embedding cache index."""
        try:
            # If no dimension provided, generate an embedding to detect it
            if dimension is None:
                test_embedding = self._get_embedding_from_api("test")
                dimension = test_embedding.shape[0]
                print(f"🔍 Auto-detected embedding dimension: {dimension}")
            self.embedding_dim = int(dimension)
            
            # Create FAISS index (inner product)
            self.embedding_cache_index = faiss.IndexFlatIP(dimension)
            
            # Try to load an existing cache
            cache_path = os.path.join(os.path.dirname(self.db_path), "embedding_cache.faiss")
            metadata_path = os.path.join(os.path.dirname(self.db_path), "embedding_cache_metadata.json")
            
            if os.path.exists(cache_path) and os.path.exists(metadata_path):
                loaded_index = faiss.read_index(cache_path)
                # If the embedding model changed (dimension changed), the old cache is invalid.
                if int(loaded_index.d) != int(dimension):
                    print(f"⚠️ Embedding cache dimension mismatch: cache.d={int(loaded_index.d)} vs current={int(dimension)}; ignoring old cache")
                    self.embedding_cache_index = faiss.IndexFlatIP(dimension)
                    self.embedding_cache_metadata = {}
                else:
                    self.embedding_cache_index = loaded_index
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        self.embedding_cache_metadata = json.load(f)
                    print(f"✅ Loaded embedding cache: {self.embedding_cache_index.ntotal} vectors")
            else:
                print("📝 Creating a new embedding cache index")
                
        except Exception as e:
            print(f"❌ Failed to initialize the embedding cache: {e}")
            # Fall back to default dimension on failure
            default_dimension = 768  # common embedding dimension
            self.embedding_cache_index = faiss.IndexFlatIP(default_dimension)
            self.embedding_cache_metadata = {}
            self.embedding_dim = int(default_dimension)

    def _ensure_embedding_dim(self) -> int:
        """Ensure we know the active embedding dimension (may trigger a single API call)."""
        if self.embedding_dim is not None:
            return int(self.embedding_dim)
        if self.embedding_cache_index is not None:
            self.embedding_dim = int(self.embedding_cache_index.d)
            return int(self.embedding_dim)
        self._init_embedding_cache()
        return int(self.embedding_dim) if self.embedding_dim is not None else int(self.embedding_cache_index.d)

    def _rebuild_faiss_indexes_from_db(self):
        """Rebuild viewpoint/keyword FAISS indexes from the DB using the current embedding model."""
        try:
            dim = self._ensure_embedding_dim()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, viewpoint, key_words FROM viewpoints ORDER BY id")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.faiss_viewpoint_index = None
                self.faiss_keyword_index = None
                self.viewpoint_ids = []
                print("📝 No viewpoints in DB; cleared FAISS indexes")
                return

            viewpoint_vectors = []
            keyword_vectors = []
            viewpoint_ids = []

            for viewpoint_id, viewpoint, keywords in rows:
                v = self._get_embedding(viewpoint)
                k = self._get_embedding(keywords)

                if int(v.shape[0]) != dim or int(k.shape[0]) != dim:
                    raise ValueError(f"Embedding dim mismatch while rebuilding: expected {dim}, got v={int(v.shape[0])}, k={int(k.shape[0])}")

                v = np.asarray(v, dtype='float32')
                k = np.asarray(k, dtype='float32')

                v_norm = np.linalg.norm(v)
                k_norm = np.linalg.norm(k)
                if not np.isfinite(v_norm) or v_norm <= 0:
                    raise ValueError(f"Invalid viewpoint embedding norm during rebuild: {v_norm}")
                if not np.isfinite(k_norm) or k_norm <= 0:
                    raise ValueError(f"Invalid keyword embedding norm during rebuild: {k_norm}")

                viewpoint_vectors.append(v / v_norm)
                keyword_vectors.append(k / k_norm)
                viewpoint_ids.append(int(viewpoint_id))

            viewpoint_arr = np.stack(viewpoint_vectors, axis=0).astype('float32')
            keyword_arr = np.stack(keyword_vectors, axis=0).astype('float32')

            self.faiss_viewpoint_index = faiss.IndexFlatIP(dim)
            self.faiss_viewpoint_index.add(viewpoint_arr)

            self.faiss_keyword_index = faiss.IndexFlatIP(dim)
            self.faiss_keyword_index.add(keyword_arr)

            self.viewpoint_ids = viewpoint_ids

            # Persist indexes + mapping.
            faiss.write_index(self.faiss_viewpoint_index, self.faiss_viewpoint_index_path)
            faiss.write_index(self.faiss_keyword_index, self.faiss_keyword_index_path)
            import json
            with open(self.viewpoint_ids_path, 'w', encoding='utf-8') as f:
                json.dump(self.viewpoint_ids, f, ensure_ascii=False)

            print(f"✅ Rebuilt FAISS indexes from DB: dim={dim}, viewpoints={self.faiss_viewpoint_index.ntotal}, keywords={self.faiss_keyword_index.ntotal}")

        except Exception as e:
            print(f"❌ Failed to rebuild FAISS indexes from DB: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    def _add_to_embedding_cache(self, text: str, embedding: np.ndarray):
        """Add embeddings to the cache."""
        try:
            # Ensure the embedding cache index exists and matches dimensions
            if self.embedding_cache_index is None:
                # Initialize using current embedding dimension
                self._init_embedding_cache(embedding.shape[0])
            
            # Check dimension compatibility
            if self.embedding_cache_index.d != embedding.shape[0]:
                print(f"⚠️ Dimension mismatch, reinitializing FAISS index: {self.embedding_cache_index.d} -> {embedding.shape[0]}")
                # Reinitialize with current embedding dimension
                self._init_embedding_cache(embedding.shape[0])
            
            # Normalize the vector
            normalized_embedding = embedding / np.linalg.norm(embedding)
            
            # Add to the FAISS index
            self.embedding_cache_index.add(normalized_embedding.reshape(1, -1))
            
            # Save metadata
            index_id = self.embedding_cache_index.ntotal - 1
            self.embedding_cache_metadata[str(index_id)] = {
                'text': text,
                'timestamp': datetime.now().isoformat()
            }
            
            # Periodically persist cache to disk (every 100 vectors)
            if self.embedding_cache_index.ntotal % 100 == 0:
                self._save_embedding_cache()
                
        except Exception as e:
            print(f"❌ Failed to add embedding to cache: {e}")
    
    def _save_embedding_cache(self):
        """Persist the embedding cache to disk."""
        try:
            cache_path = os.path.join(os.path.dirname(self.db_path), "embedding_cache.faiss")
            metadata_path = os.path.join(os.path.dirname(self.db_path), "embedding_cache_metadata.json")
            
            # Save FAISS index
            faiss.write_index(self.embedding_cache_index, cache_path)
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.embedding_cache_metadata, f, ensure_ascii=False, indent=2)
                
            print(f"💾 Embedding cache saved: {self.embedding_cache_index.ntotal} vectors")
            
        except Exception as e:
            print(f"❌ Failed to save embedding cache: {e}")
    
    def close(self):
        """Save cache when closing the system."""
        try:
            if self.embedding_cache_index and self.embedding_cache_index.ntotal > 0:
                self._save_embedding_cache()
                print("💾 Saved embedding cache while closing the system")
        except Exception as e:
            print(f"❌ Failed to save cache on close: {e}")
    
    def set_api_key(self, api_key: str):
        """Set the API key."""
        self.llm_api_key = api_key
        self.llm_client, self.llm_model_name = self.model_selector.create_openai_client_with_base_url(
            base_url=self.llm_base_url,
            api_key=self.llm_api_key,
            role="fact_checker",
        )
        print("✅ API key configured successfully")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Return embedding and FAISS cache statistics."""
        return {
            "embedding_cache_size": self.embedding_cache_index.ntotal if self.embedding_cache_index else 0,
            "faiss_viewpoint_index_size": self.faiss_viewpoint_index.ntotal if self.faiss_viewpoint_index else 0,
            "faiss_keyword_index_size": self.faiss_keyword_index.ntotal if self.faiss_keyword_index else 0
        }
    
    def _init_database(self):
        """Initialize database table structures."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create the main viewpoints table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS viewpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    viewpoint TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    key_words TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    viewpoint_id INTEGER,
                    evidence TEXT NOT NULL,
                    acceptance_rate REAL NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (viewpoint_id) REFERENCES viewpoints (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to initialize the database: {e}")
    
    def _load_vectors(self):
        """Load vector indexes from FAISS files."""
        try:
            # Determine the current embedding dimension early so we can validate persisted FAISS indexes.
            self._ensure_embedding_dim()

            # Set FAISS index file paths
            db_dir = os.path.dirname(self.db_path)
            self.faiss_viewpoint_index_path = os.path.join(db_dir, "faiss_viewpoint_index.bin")
            self.faiss_keyword_index_path = os.path.join(db_dir, "faiss_keyword_index.bin")
            self.viewpoint_ids_path = os.path.join(db_dir, "viewpoint_ids.json")
            
            # Attempt to load the viewpoint index
            if os.path.exists(self.faiss_viewpoint_index_path):
                self.faiss_viewpoint_index = faiss.read_index(self.faiss_viewpoint_index_path)
                faiss_index_size = self.faiss_viewpoint_index.ntotal
                if self.embedding_dim is not None and int(self.faiss_viewpoint_index.d) != int(self.embedding_dim):
                    print(f"⚠️ Viewpoint FAISS index dim mismatch: index.d={int(self.faiss_viewpoint_index.d)} vs embedding_dim={int(self.embedding_dim)}; rebuilding")
                    self._rebuild_faiss_indexes_from_db()
                    return
                
                # Load viewpoint ID mapping
                if os.path.exists(self.viewpoint_ids_path):
                    import json
                    with open(self.viewpoint_ids_path, 'r', encoding='utf-8') as f:
                        self.viewpoint_ids = json.load(f)
                    
                    # Verify FAISS index and viewpoint IDs are synced
                    if len(self.viewpoint_ids) != faiss_index_size:
                        print(f"⚠️ FAISS index ({faiss_index_size}) and viewpoint_ids ({len(self.viewpoint_ids)}) are out of sync; rebuilding from the database...")
                        self._rebuild_viewpoint_ids_from_db()
                else:
                    # Rebuild IDs if the JSON is missing
                    print(f"⚠️ viewpoint_ids.json missing while FAISS index exists ({faiss_index_size} vectors); rebuilding IDs from the database...")
                    self._rebuild_viewpoint_ids_from_db()
            else:
                # Initialize empty viewpoint index
                self.faiss_viewpoint_index = None
                self.viewpoint_ids = []
                print("📝 Viewpoint FAISS index file missing; a new index will be created")
            
            # Attempt to load the keyword index
            if os.path.exists(self.faiss_keyword_index_path):
                self.faiss_keyword_index = faiss.read_index(self.faiss_keyword_index_path)
                if self.embedding_dim is not None and self.faiss_keyword_index and int(self.faiss_keyword_index.d) != int(self.embedding_dim):
                    print(f"⚠️ Keyword FAISS index dim mismatch: index.d={int(self.faiss_keyword_index.d)} vs embedding_dim={int(self.embedding_dim)}; rebuilding")
                    self._rebuild_faiss_indexes_from_db()
                    return
            else:
                # Initialize empty keyword index
                self.faiss_keyword_index = None
                print("📝 Keyword FAISS index file missing; a new index will be created")
            
            # Log loading results
            if self.faiss_viewpoint_index:
                print(f"✅ Viewpoint FAISS index loaded: {self.faiss_viewpoint_index.ntotal} vectors, {len(self.viewpoint_ids)} ID mappings")
            if self.faiss_keyword_index:
                print(f"✅ Keyword FAISS index loaded: {self.faiss_keyword_index.ntotal} vectors")
                        
        except Exception as e:
            print(f"❌ Failed to load FAISS indexes: {e}")
            import traceback
            traceback.print_exc()
            self.faiss_viewpoint_index = None
            self.faiss_keyword_index = None
            self.viewpoint_ids = []
    
    def _rebuild_viewpoint_ids_from_db(self):
        """Rebuild the viewpoint_ids list from the database to keep FAISS indexes synchronized."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Retrieve all viewpoint IDs in order to match the FAISS index sequence
            cursor.execute("SELECT id FROM viewpoints ORDER BY id")
            db_viewpoint_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # Check whether the database ID count matches the FAISS index
            faiss_size = self.faiss_viewpoint_index.ntotal if self.faiss_viewpoint_index else 0
            
            if len(db_viewpoint_ids) == 0:
                # Database is empty but FAISS index may still contain vectors (inconsistent state)
                print(f"⚠️ No viewpoints in the database, but FAISS index has {faiss_size} vectors")
                print(f"   This indicates data inconsistency; clearing viewpoint_ids")
                self.viewpoint_ids = []
                # If the FAISS index has vectors but the DB is empty, consider rebuilding
                if faiss_size > 0:
                    print(f"   Suggestion: rebuild the FAISS index for consistency")
            elif len(db_viewpoint_ids) < faiss_size:
                # Database contains fewer records than the FAISS index (partial loss)
                print(f"⚠️ Database has {len(db_viewpoint_ids)} viewpoints; FAISS index has {faiss_size} vectors")
                print(f"   Using all {len(db_viewpoint_ids)} IDs from the database")
                self.viewpoint_ids = db_viewpoint_ids
            elif len(db_viewpoint_ids) > faiss_size:
                # Database has more records than the FAISS index (index incomplete)
                print(f"⚠️ Database has {len(db_viewpoint_ids)} viewpoints; FAISS index has only {faiss_size} vectors")
                print(f"   Truncating to the first {faiss_size} IDs to match the index size")
                self.viewpoint_ids = db_viewpoint_ids[:faiss_size]
            else:
                # Perfect match
                self.viewpoint_ids = db_viewpoint_ids
            
            # Persist the rebuilt viewpoint_ids back to the JSON file
            import json
            with open(self.viewpoint_ids_path, 'w', encoding='utf-8') as f:
                json.dump(self.viewpoint_ids, f, ensure_ascii=False)
            
            print(f"✅ Rebuilt viewpoint_ids from database: {len(self.viewpoint_ids)} entries")
            
        except Exception as e:
            print(f"❌ Failed to rebuild viewpoint_ids from the database: {e}")
            import traceback
            traceback.print_exc()
            # If rebuild fails, reset to an empty list
            self.viewpoint_ids = []
    
    def _add_vector_to_faiss(self, viewpoint_id: int, viewpoint: str, keyword: str):
        """Add new vectors incrementally to the FAISS indexes and save them."""
        try:
            # Vectorize new content
            viewpoint_embedding = self._get_embedding(viewpoint)
            keyword_embedding = self._get_embedding(keyword)

            # If existing indexes were built with a different embedding model (dimension),
            # rebuild from DB to keep indexes consistent (and include this newly inserted row).
            if self.faiss_viewpoint_index is not None and int(self.faiss_viewpoint_index.d) != int(viewpoint_embedding.shape[0]):
                print(f"⚠️ Viewpoint index dim mismatch on add: index.d={int(self.faiss_viewpoint_index.d)} vs embedding_dim={int(viewpoint_embedding.shape[0])}; rebuilding from DB")
                self._rebuild_faiss_indexes_from_db()
                return
            if self.faiss_keyword_index is not None and int(self.faiss_keyword_index.d) != int(keyword_embedding.shape[0]):
                print(f"⚠️ Keyword index dim mismatch on add: index.d={int(self.faiss_keyword_index.d)} vs embedding_dim={int(keyword_embedding.shape[0])}; rebuilding from DB")
                self._rebuild_faiss_indexes_from_db()
                return
            
            # Normalize vectors
            viewpoint_norm = np.linalg.norm(viewpoint_embedding)
            keyword_norm = np.linalg.norm(keyword_embedding)

            if not np.isfinite(viewpoint_norm) or viewpoint_norm <= 0:
                raise ValueError(f"Invalid viewpoint embedding norm: {viewpoint_norm}")
            if not np.isfinite(keyword_norm) or keyword_norm <= 0:
                raise ValueError(f"Invalid keyword embedding norm: {keyword_norm}")

            normalized_viewpoint = viewpoint_embedding / viewpoint_norm
            normalized_keyword = keyword_embedding / keyword_norm
            
            # Create or update the viewpoint index
            if self.faiss_viewpoint_index is None:
                # Build a new viewpoint index
                dimension = viewpoint_embedding.shape[0]
                self.faiss_viewpoint_index = faiss.IndexFlatIP(dimension)
                print(f"✅ Created new FAISS viewpoint index (dimension: {dimension})")
            
            # Add the viewpoint vector to the index
            self.faiss_viewpoint_index.add(normalized_viewpoint.reshape(1, -1).astype('float32'))
            
            # Update the viewpoint ID mapping
            self.viewpoint_ids.append(viewpoint_id)
            
            # Persist viewpoint index to disk
            faiss.write_index(self.faiss_viewpoint_index, self.faiss_viewpoint_index_path)
            
            # Persist viewpoint ID mapping
            import json
            with open(self.viewpoint_ids_path, 'w', encoding='utf-8') as f:
                json.dump(self.viewpoint_ids, f, ensure_ascii=False)
            
            # Create or update the keyword index
            if self.faiss_keyword_index is None:
                # Build a new keyword index
                dimension = keyword_embedding.shape[0]
                self.faiss_keyword_index = faiss.IndexFlatIP(dimension)
                print(f"✅ Created new FAISS keyword index (dimension: {dimension})")
            
            # Add the keyword vector to the index
            self.faiss_keyword_index.add(normalized_keyword.reshape(1, -1).astype('float32'))
            
            # Persist keyword index to disk
            faiss.write_index(self.faiss_keyword_index, self.faiss_keyword_index_path)
            
            print(f"✅ New vectors added to FAISS indexes and saved (ID: {viewpoint_id})")
            print(f"   Viewpoint index vectors: {self.faiss_viewpoint_index.ntotal}")
            print(f"   Keyword index vectors: {self.faiss_keyword_index.ntotal}")
            
        except Exception as e:
            print(f"⚠️ Failed to add vectors to FAISS: {e!r}")
            print(f"   Viewpoint embedding shape={getattr(viewpoint_embedding, 'shape', None)}, dtype={getattr(viewpoint_embedding, 'dtype', None)}")
            print(f"   Keyword embedding shape={getattr(keyword_embedding, 'shape', None)}, dtype={getattr(keyword_embedding, 'dtype', None)}")
            import traceback
            traceback.print_exc()
    
    def process_opinion(self, opinion: str) -> Dict[str, Any]:
        """Execute the full opinion processing workflow as required."""
        print(f"🎯 Processing opinion: {opinion}")
        print("-" * 80)
        
        # Display cache statistics
        cache_stats = self.get_cache_stats()
        print(f"📊 Cache status: embedding={cache_stats['embedding_cache_size']}, FAISS viewpoints={cache_stats['faiss_viewpoint_index_size']}, FAISS keywords={cache_stats['faiss_keyword_index_size']}")
        
        start_time = time.time()
        
        try:
            # Step 1: LLM topic classification and keyword extraction
            classification_result = self._llm_classify_and_extract(opinion)
            theme = classification_result['theme']
            keyword = classification_result['keyword']
            
            print(f"📂 Classified theme: {theme}")
            print(f"🔑 Extracted keyword: {keyword}")
            
            # Step 2: Theme match check
            theme_matched = self._check_theme_match(theme)
            if not theme_matched:
                print(f"⚠️ Theme '{theme}' has no matching records in the database")
                # Case (2): similarity below threshold, new-keyword flow
                return self._handle_completely_new_opinion(opinion, theme, keyword)
            
            # Step 3: FAISS keyword matching
            keyword_match_result = self._faiss_search_keywords(keyword)
            
            if keyword_match_result['similarity'] >= self.keyword_similarity_threshold:
                print(f"✅ Keyword match succeeded (similarity: {keyword_match_result['similarity']:.3f})")
                matched_keywords = keyword_match_result['matched_keywords']

                # Check whether matched_keywords is empty
                if not matched_keywords or matched_keywords.strip() == '':
                    print(f"❌ Matched keywords empty; falling back to original keyword: {keyword}")
                    matched_keywords = keyword

                # Step 4: FAISS viewpoint matching
                viewpoint_match_result = self._faiss_search_viewpoints(opinion, matched_keywords)

                if viewpoint_match_result['similarity'] >= self.viewpoint_similarity_threshold:
                    print(f"✅ Viewpoint match succeeded (similarity: {viewpoint_match_result['similarity']:.3f})")
                    # Case 1.1: Return the top evidence for the matched viewpoint
                    viewpoint_id = viewpoint_match_result.get('viewpoint_id')
                    if viewpoint_id is None:
                        print(f"⚠️ Viewpoint ID missing; switching to existing-keyword flow")
                        return self._handle_new_viewpoint_existing_keywords(
                            opinion, theme, matched_keywords
                        )
                    return self._return_top5_evidence(viewpoint_id)
                else:
                    print(f"❌ Viewpoint match failed (similarity: {viewpoint_match_result['similarity']:.3f})")
                    # Case 1.2: new viewpoint but keywords exist
                    return self._handle_new_viewpoint_existing_keywords(
                        opinion, theme, matched_keywords
                    )
            else:
                print(f"❌ Keyword match failed (similarity: {keyword_match_result['similarity']:.3f})")
                # Case (2): similarity below threshold, new keyword flow
                return self._handle_completely_new_opinion(opinion, theme, keyword)
        
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _llm_classify_and_extract(self, opinion: str) -> Dict[str, str]:
        """Use an LLM to classify the topic and extract keywords."""
        
        try:
            prompt = f"""
Please analyze the following opinion:
Opinion: "{opinion}"

Complete two tasks:
1. Choose the best matching topic from the list below:
{', '.join(self.topics)}

2. Identify the keyword that best represents the opinion in two steps:
   - First list 2-4 related keywords.
   - Then select the single core keyword among them.

Return the result as JSON:
{{"theme": "selected topic", "keywords_full": "2-4 keywords", "keyword": "core keyword"}}

Example:
- Opinion: "Artificial intelligence will change medical diagnosis"
- Return: {{"theme": "Technology & Future", "keywords_full": "artificial intelligence healthcare diagnosis", "keyword": "intelligence"}}
"""
            
            response = self.llm_client.chat.completions.create(
                model=self.llm_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            if response and response.choices:
                content = response.choices[0].message.content
                
                try:
                    # Clean the response and strip markdown if present
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    content = content.strip()
                    
                    classification = json.loads(content)
                    # Prefer the single keyword if present; otherwise derive one from the full list.
                    single_keyword = (classification.get('keyword') or '').strip()
                    if not single_keyword:
                        keywords_full = (classification.get('keywords_full') or '').strip()
                        # Pick the first token as a stable fallback (avoids empty keyword causing downstream "unknown").
                        first = keywords_full.split()[0] if keywords_full else ''
                        if first:
                            print(f"⚠️ LLM returned empty 'keyword'; falling back to first token from 'keywords_full': {first}")
                            single_keyword = first
                        else:
                            print("⚠️ LLM returned empty 'keyword' and 'keywords_full'; falling back to 'general'")
                            single_keyword = 'general'
                    
                    # Confirm the returned theme matches the predefined list
                    theme = classification.get('theme', 'Society & Ethics')
                    if theme not in self.topics:
                        print(f"⚠️ Theme '{theme}' not in the predefined list; defaulting to Society & Ethics")
                        theme = 'Society & Ethics'
                    
                    return {
                        'theme': theme,
                        'keyword': single_keyword
                    }
                except json.JSONDecodeError as e:
                    print(f"⚠️ Failed to parse LLM response: {e}")
                    print(f"Original response snippet: {content[:200]}...")
                    return {'theme': 'Society & Ethics', 'keyword': 'general'}
            print(f"⚠️ LLM API request failed: empty response")
            return {'theme': 'Society & Ethics', 'keyword': 'general'}
                
        except Exception as e:
            print(f"⚠️ LLM request exception: {e}")
            return {'theme': 'Society & Ethics', 'keyword': 'general'}
    

    
    def _check_theme_match(self, theme: str) -> bool:
        """Check whether the theme exists in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM viewpoints WHERE theme = ?", (theme,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            print(f"⚠️ Theme match check failed: {e}")
            return False
    
    def _faiss_search_keywords(self, keyword: str) -> Dict[str, Any]:
        """Use FAISS to search for matching keywords."""
        try:
            if self.faiss_keyword_index is None or self.faiss_keyword_index.ntotal == 0:
                return {'similarity': 0.0, 'matched_keywords': None}
            
            # Vectorize the keyword query
            query_vector = self._get_embedding(keyword).reshape(1, -1)
            if int(self.faiss_keyword_index.d) != int(query_vector.shape[1]):
                print(f"⚠️ Keyword FAISS dim mismatch on search: index.d={int(self.faiss_keyword_index.d)} vs query_dim={int(query_vector.shape[1])}; rebuilding")
                self._rebuild_faiss_indexes_from_db()
                return {'similarity': 0.0, 'matched_keywords': None}
            query_norm = np.linalg.norm(query_vector)
            query_vector_normalized = query_vector / query_norm
            
            # Search the FAISS index for the most similar vector
            similarities, indices = self.faiss_keyword_index.search(
                query_vector_normalized.astype('float32'), 1
            )
            
            max_similarity = float(similarities[0][0])
            
            # Retrieve the corresponding keyword from the database via the index ID
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Collect all keywords in the order they were indexed
            cursor.execute("SELECT key_words FROM viewpoints ORDER BY id")
            db_keywords = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # Ensure the index does not exceed the list bounds
            best_match = None
            if indices[0][0] < len(db_keywords):
                best_match = db_keywords[indices[0][0]]
            
            return {
                'similarity': float(max_similarity),
                'matched_keywords': best_match
            }
            
        except Exception as e:
            print(f"⚠️ Keyword FAISS search failed: {e}")
            return {'similarity': 0.0, 'matched_keywords': None}
    
    def _faiss_search_viewpoints(self, opinion: str, keywords: str) -> Dict[str, Any]:
        """Use FAISS to search for matching viewpoints."""
        try:
            if self.faiss_viewpoint_index is None or self.faiss_viewpoint_index.ntotal == 0:
                return {'similarity': 0.0, 'viewpoint_id': None}
            
            # Ensure viewpoint_ids is initialized and synced with the index
            if not hasattr(self, 'viewpoint_ids') or self.viewpoint_ids is None:
                print("⚠️ viewpoint_ids not initialized; rebuilding from the database...")
                self._rebuild_viewpoint_ids_from_db()
            
            if len(self.viewpoint_ids) != self.faiss_viewpoint_index.ntotal:
                print(f"⚠️ viewpoint_ids ({len(self.viewpoint_ids)}) and FAISS index ({self.faiss_viewpoint_index.ntotal}) out of sync; rebuilding...")
                self._rebuild_viewpoint_ids_from_db()
            
            # If rebuild leaves the list empty, data is inconsistent
            if len(self.viewpoint_ids) == 0:
                print("⚠️ viewpoint_ids still empty after rebuild; cannot continue viewpoint search")
                return {'similarity': 0.0, 'viewpoint_id': None}
            
            # Vectorize the opinion query
            query_vector = self._get_embedding(opinion).reshape(1, -1)
            if int(self.faiss_viewpoint_index.d) != int(query_vector.shape[1]):
                print(f"⚠️ Viewpoint FAISS dim mismatch on search: index.d={int(self.faiss_viewpoint_index.d)} vs query_dim={int(query_vector.shape[1])}; rebuilding")
                self._rebuild_faiss_indexes_from_db()
                return {'similarity': 0.0, 'viewpoint_id': None}
            query_vector_normalized = query_vector / np.linalg.norm(query_vector)
            
            # Search the FAISS index for the closest viewpoint
            similarities, indices = self.faiss_viewpoint_index.search(
                query_vector_normalized.astype('float32'), 1
            )
            
            max_similarity = float(similarities[0][0])
            best_match_idx = int(indices[0][0])
            
            # Convert the index to the corresponding viewpoint ID
            best_match_id = None
            if 0 <= best_match_idx < len(self.viewpoint_ids):
                best_match_id = self.viewpoint_ids[best_match_idx]
            else:
                print(f"⚠️ Index out of range: best_match_idx={best_match_idx}, viewpoint_ids length={len(self.viewpoint_ids)}")
                # Try one last rebuild
                self._rebuild_viewpoint_ids_from_db()
                # Re-check after rebuild
                if len(self.viewpoint_ids) > 0 and 0 <= best_match_idx < len(self.viewpoint_ids):
                    best_match_id = self.viewpoint_ids[best_match_idx]
                else:
                    print(f"⚠️ Unable to resolve viewpoint_id after rebuild; returning None")
                    best_match_id = None
            
            # Verify the viewpoint_id still exists in the database
            if best_match_id is not None:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM viewpoints WHERE id = ?", (best_match_id,))
                exists = cursor.fetchone()[0] > 0
                conn.close()
                
                if not exists:
                    print(f"⚠️ FAISS index returned viewpoint_id {best_match_id} which is missing in the database; searching for similar records")
                    # Search the database for similar viewpoints based on keywords
                    best_match_id = self._find_similar_viewpoint_in_db(opinion, keywords)
            
            return {
                'similarity': float(max_similarity),
                'viewpoint_id': best_match_id
            }
            
        except Exception as e:
            print(f"⚠️ Viewpoint FAISS search failed: {e}")
            import traceback
            traceback.print_exc()
            return {'similarity': 0.0, 'viewpoint_id': None}
    
    def _find_similar_viewpoint_in_db(self, opinion: str, keywords: str) -> Optional[int]:
        """Search the database for a similar viewpoint record."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First try keyword matching
            if keywords:
                cursor.execute("""
                    SELECT id FROM viewpoints 
                    WHERE key_words LIKE ? 
                    ORDER BY id DESC 
                    LIMIT 1
                """, (f"%{keywords}%",))
                result = cursor.fetchone()
                if result:
                    conn.close()
                    print(f"✅ Found a similar viewpoint via keyword matching: ID {result[0]}")
                    return result[0]
            
            # If keyword matching fails, look for the most recent valid record
            cursor.execute("SELECT id FROM viewpoints ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"✅ Found the latest viewpoint record: ID {result[0]}")
                return result[0]
            
            return None
            
        except Exception as e:
            print(f"⚠️ Failed to find a similar viewpoint record: {e}")
            return None
    
    def _return_top5_evidence(self, viewpoint_id: int) -> Dict[str, Any]:
        """Return the top-ranked evidences for a given viewpoint by acceptance rate."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate parameters
            if viewpoint_id is None:
                conn.close()
                return {'error': 'viewpoint_id cannot be None'}
            
            # Retrieve viewpoint information
            cursor.execute("SELECT viewpoint, theme, key_words FROM viewpoints WHERE id = ?", (viewpoint_id,))
            viewpoint_info = cursor.fetchone()
            
            if viewpoint_info is None:
                conn.close()
                print(f"⚠️ No viewpoint record for ID {viewpoint_id}; rebuilding the index mapping...")
                self._rebuild_viewpoint_ids_from_db()
                
                # Try again after rebuilding
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT viewpoint, theme, key_words FROM viewpoints WHERE id = ?", (viewpoint_id,))
                viewpoint_info = cursor.fetchone()
                
                if viewpoint_info is None:
                    print(f"⚠️ Still cannot find record for ID {viewpoint_id}; searching for any available record...")
                    cursor.execute("SELECT id, viewpoint, theme, key_words FROM viewpoints ORDER BY id DESC LIMIT 1")
                    fallback_result = cursor.fetchone()
                    
                    if fallback_result:
                        viewpoint_id = fallback_result[0]
                        viewpoint_info = (fallback_result[1], fallback_result[2], fallback_result[3])
                        print(f"✅ Found an alternative viewpoint record: ID {viewpoint_id}")
                    else:
                        conn.close()
                        return {'error': f'No viewpoint found for ID {viewpoint_id} and the database has no records'}
            
            # Fetch the top acceptance_rate evidences
            cursor.execute("""
                SELECT evidence, acceptance_rate, source 
                FROM evidence 
                WHERE viewpoint_id = ? 
                ORDER BY acceptance_rate DESC 
                LIMIT ?
            """, (viewpoint_id, MAX_EVIDENCE_PER_VIEWPOINT))
            evidence_list = cursor.fetchall()
            
            conn.close()
            
            result = {
                'status': 'existing_match',
                'viewpoint': viewpoint_info[0],
                'theme': viewpoint_info[1],
                'keywords': viewpoint_info[2],
                # Backward-compat: some callers historically used 'keyword' (singular).
                # Keep it identical to 'keywords' to avoid "unknown" in downstream logs/UI.
                'keyword': viewpoint_info[2],
                'evidence_count': len(evidence_list),
                'evidence': []
            }
            
            print(f"📋 Returning the top {MAX_EVIDENCE_PER_VIEWPOINT} evidences (sorted by acceptance_rate)")
            for i, (evidence, rate, source) in enumerate(evidence_list, 1):
                result['evidence'].append({
                    'rank': i,
                    'evidence': evidence,
                    'acceptance_rate': rate,
                    'source': source
                })
                print(f"  {i}. [Acceptance rate: {rate:.3f}] {evidence[:60]}...")
            
            return result
            
        except Exception as e:
            print(f"❌ Failed to retrieve top 5 evidences: {e}")
            return {'error': str(e)}
    
    def _handle_new_viewpoint_existing_keywords(self, opinion: str, theme: str, keywords: str) -> Dict[str, Any]:
        """Handle a new viewpoint when the keywords already exist."""
        print("🆕 New viewpoint detected; using existing keywords")

        # Validate parameters
        if not keywords or keywords.strip() == '':
            print("❌ Keywords empty; cannot perform Wikipedia search")
            return {'error': 'keywords required'}

        # Use the first keyword for the Wikipedia search if multiple are provided
        search_keyword = keywords.split(',')[0].strip() if ',' in keywords else keywords.strip()

        # Retrieve 15 evidence pieces via the Wikipedia API
        evidence_list = self._search_wikipedia_evidence_15(search_keyword)
        print(f"🔍 Wikipedia returned {len(evidence_list)} evidences")
        
        if not evidence_list:
            return {'error': 'no relevant evidence found'}
        
        # Score via the LLM
        scored_evidence = self._llm_score_evidence(opinion, evidence_list)
        print(f"📊 LLM scored {len(scored_evidence)} evidences")
        
        # Take the top entries by acceptance_rate
        top_evidence = scored_evidence[:MAX_EVIDENCE_PER_VIEWPOINT]
        
        # Store the entries in the database
        viewpoint_id = self._save_to_database(opinion, theme, keywords, top_evidence)
        
        result = {
            'status': 'new_viewpoint_existing_keywords',
            'viewpoint': opinion,
            'theme': theme,
            'keywords': keywords,
            'keyword': keywords,
            'evidence_count': len(top_evidence),
            'evidence': []
        }
        
        print(f"📋 Returning top {MAX_EVIDENCE_PER_VIEWPOINT} evidences (sorted by acceptance_rate)")
        for i, item in enumerate(top_evidence, 1):
            result['evidence'].append({
                'rank': i,
                'evidence': item['evidence'],
                'acceptance_rate': item['acceptance_rate'],
                'source': item.get('source', 'Wikipedia')
            })
            print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")
        
        print(f"💾 Stored the new viewpoint with ID: {viewpoint_id}")
        
        # Reload FAISS indexes
        self._load_vectors()
        
        return result
    
    def _handle_completely_new_opinion(self, opinion: str, theme: str, keyword: str) -> Dict[str, Any]:
        """Handle a completely new viewpoint and keyword pair."""
        print("🆕 Completely new viewpoint and keyword")

        # Validate parameters
        if not keyword or keyword.strip() == '':
            print("❌ Keyword empty; cannot perform Wikipedia search")
            return {'error': 'keywords required'}

        # Clean the keyword
        search_keyword = keyword.strip()

        # Retrieve 15 evidence snippets via Wikipedia API
        evidence_list = self._search_wikipedia_evidence_15(search_keyword)
        print(f"🔍 Wikipedia returned {len(evidence_list)} evidences")
        
        if not evidence_list:
            return {'error': 'no relevant evidence found'}
        
        # Score using the LLM
        scored_evidence = self._llm_score_evidence(opinion, evidence_list)
        print(f"📊 LLM scored {len(scored_evidence)} evidences")
        
        # Take top entries by acceptance_rate
        top_evidence = scored_evidence[:MAX_EVIDENCE_PER_VIEWPOINT]
        
        # Store into the database
        viewpoint_id = self._save_to_database(opinion, theme, keyword, top_evidence)
        
        result = {
            'status': 'completely_new',
            'viewpoint': opinion,
            'theme': theme,
            'keywords': keyword,
            'keyword': keyword,
            'evidence_count': len(top_evidence),
            'evidence': []
        }
        
        print(f"📋 Returning top {MAX_EVIDENCE_PER_VIEWPOINT} evidences (sorted by acceptance_rate)")
        for i, item in enumerate(top_evidence, 1):
            result['evidence'].append({
                'rank': i,
                'evidence': item['evidence'],
                'acceptance_rate': item['acceptance_rate'],
                'source': item.get('source', 'Wikipedia')
            })
            print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")
        
        print(f"💾 Stored the new viewpoint with ID: {viewpoint_id}")
        
        # Reload FAISS indexes
        self._load_vectors()
        
        return result
    
    def _search_wikipedia_evidence_15(self, keyword: str) -> List[str]:
        """Search the Wikipedia API for supporting evidence."""
        evidence_list = []

        try:
            # Validate the keyword to avoid None or empty strings
            if keyword is None or not isinstance(keyword, str) or not keyword.strip():
                print("❌ Invalid search keyword (None or empty)")
                return []

            keyword = keyword.strip()
            print(f"🔍 Starting Wikipedia search: {keyword}")

            # Configure the Wikipedia client
            wiki = wikipediaapi.Wikipedia(
                language='en',
                extract_format=wikipediaapi.ExtractFormat.WIKI,
                user_agent='EnhancedEvidenceDatabase/1.0 (https://example.com/contact)'
            )

            search_terms = [
                keyword,
                keyword + " research",
                keyword + " study",
                keyword + " benefits",
                keyword + " impact",
                keyword + " analysis",
                keyword + " effects"
            ]

            for term in search_terms:
                try:
                    print(f"   🔍 Search term: {term}")
                    page = wiki.page(term)

                    if page.exists():
                        print(f"   ✅ Found page: {page.title}")
                        content = page.text

                        if content:
                            paragraphs = content.split('\n\n')

                            for paragraph in paragraphs:
                                if len(paragraph) > 100:
                                    cleaned_paragraph = self._clean_wikipedia_text(paragraph)
                                    if len(cleaned_paragraph) > 100:
                                        evidence_list.append(cleaned_paragraph)

                                        if len(evidence_list) >= MAX_WIKIPEDIA_RESULTS:
                                            print(f"✅ Collected enough evidence: {len(evidence_list)} entries")
                                            return evidence_list[:MAX_WIKIPEDIA_RESULTS]

                            if len(evidence_list) >= 10:
                                break
                    else:
                        print(f"   ⚠️ Page missing: {term}")

                except Exception as e:
                    print(f"   ❌ Search term '{term}' failed: {e}")
                    continue

        except Exception as e:
            print(f"❌ Failed to initialize the Wikipedia API: {e}")
            print("💡 Possible troubleshooting steps:")
            print("   1. Check the network connection")
            print("   2. Inspect firewall settings")
            print("   3. Try using a VPN")
            print("   4. Verify DNS configuration")
            print("   5. Ensure the keyword parameter is valid")

            # Return an empty list instead of raising an error
            return []

        print(f"✅ Wikipedia search complete; collected {len(evidence_list)} evidences")
        return evidence_list



    def _clean_wikipedia_text(self, text: str) -> str:
        """Clean up Wikipedia text snippets."""
        import re
        # Remove reference markers
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Limit the length
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text
    
    def _llm_score_evidence(self, viewpoint: str, evidence_list: List[str]) -> List[Dict[str, Any]]:
        """Rate each evidence item using the LLM."""
        scored_evidence = []
        
        for evidence in evidence_list:
            prompt = f"""
Rate the following evidence for its support of the viewpoint on a 0.0-1.0 scale:

Viewpoint: "{viewpoint}"
Evidence: "{evidence}"

Please evaluate using the following dimensions:
1. Relevance – How closely does the evidence relate to the viewpoint?
2. Credibility – How trustworthy is the source and its phrasing?
3. Persuasiveness – How logically compelling is the argument?
4. Specificity – Does it include concrete data, cases, or studies?

Return a single number between 0.0 and 1.0 with no explanation.
"""
            
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                content = response.choices[0].message.content.strip()
                score = float(content)
                score = max(0.0, min(1.0, score))
            except Exception as e:
                print(f"⚠️ LLM scoring API failed: {e}")
                score = 0.5  # default score
            
            scored_evidence.append({
                'evidence': evidence,
                'acceptance_rate': score,
                'source': 'Wikipedia'
            })
            
            time.sleep(0.1)  # Throttle requests
        
        # Sort by acceptance_rate in descending order
        scored_evidence.sort(key=lambda x: x['acceptance_rate'], reverse=True)
        return scored_evidence
    
    
    def _save_to_database(self, viewpoint: str, theme: str, keywords: str, evidence_list: List[Dict]) -> int:
        """Save the viewpoint and evidences into the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert viewpoint record
            cursor.execute('''
                INSERT INTO viewpoints (viewpoint, theme, key_words)
                VALUES (?, ?, ?)
            ''', (viewpoint, theme, keywords))
            
            viewpoint_id = cursor.lastrowid
            
            # Insert evidence records
            for item in evidence_list[:MAX_EVIDENCE_PER_VIEWPOINT]:
                cursor.execute('''
                    INSERT INTO evidence (viewpoint_id, evidence, acceptance_rate, source)
                    VALUES (?, ?, ?, ?)
                ''', (viewpoint_id, item['evidence'], item['acceptance_rate'], item.get('source', 'Wikipedia')))
            
            conn.commit()
            conn.close()
            
            # Incrementally add new vectors to FAISS indexes
            self._add_vector_to_faiss(viewpoint_id, viewpoint, keywords)
            
            return viewpoint_id
            
        except Exception as e:
            print(f"❌ Failed to save to the database: {e}")
            return -1

# Usage example
def main():
    """Main entry point demonstrating system capabilities."""
    print("🚀 Enhanced opinion processing system demo")
    print("=" * 80)
    
    # Create the system instance
    system = EnhancedOpinionSystem()
    
    # API key loaded from configuration
    print("✅ API key loaded from configuration")
    
    # Test viewpoint
    test_opinion = "Artificial intelligence will revolutionize healthcare in the next decade"
    
    print(f"🧪 Processing test opinion:")
    result = system.process_opinion(test_opinion)
    
    if 'error' not in result:
        print(f"✅ Processing succeeded")
        print(f"Status: {result['status']}")
        print(f"Theme: {result['theme']}")
        print(f"Keywords: {result['keywords']}")
        print(f"Evidence count: {result['evidence_count']}")
    else:
        print(f"❌ Processing failed: {result['error']}")

if __name__ == "__main__":
    main()
