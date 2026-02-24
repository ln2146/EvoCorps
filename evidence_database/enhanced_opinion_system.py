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
import re

# Import configuration
try:
    from .config import (
        TOPICS,
        KEYWORD_SIMILARITY_THRESHOLD, VIEWPOINT_SIMILARITY_THRESHOLD,
        MAX_WIKIPEDIA_RESULTS,
        MAX_EVIDENCE_PER_VIEWPOINT,
        MIN_EVIDENCE_ACCEPTANCE_RATE,
        FALLBACK_EVIDENCE_COUNT,
        DEFAULT_DB_PATH,
    )
except ImportError:
    from config import (
        TOPICS,
        KEYWORD_SIMILARITY_THRESHOLD, VIEWPOINT_SIMILARITY_THRESHOLD,
        MAX_WIKIPEDIA_RESULTS,
        MAX_EVIDENCE_PER_VIEWPOINT,
        MIN_EVIDENCE_ACCEPTANCE_RATE,
        FALLBACK_EVIDENCE_COUNT,
        DEFAULT_DB_PATH,
    )


def select_top_evidence(scored_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Select evidences for persistence/return.

    Rules:
    - Keep only items with acceptance_rate >= MIN_EVIDENCE_ACCEPTANCE_RATE
    - Sort by acceptance_rate descending
    - Cap at MAX_EVIDENCE_PER_VIEWPOINT
    """
    if scored_evidence is None:
        raise ValueError("scored_evidence cannot be None")

    filtered: List[Dict[str, Any]] = []
    for item in scored_evidence:
        if not isinstance(item, dict):
            raise ValueError(f"evidence item must be a dict, got {type(item)}")
        if "acceptance_rate" not in item:
            raise ValueError("evidence item missing 'acceptance_rate'")
        if "evidence" not in item:
            raise ValueError("evidence item missing 'evidence'")

        rate = item["acceptance_rate"]
        try:
            rate_float = float(rate)
        except Exception as e:
            raise ValueError(f"invalid acceptance_rate: {rate!r}") from e

        if rate_float >= MIN_EVIDENCE_ACCEPTANCE_RATE:
            normalized = dict(item)
            normalized["acceptance_rate"] = rate_float
            filtered.append(normalized)

    filtered.sort(key=lambda x: x["acceptance_rate"], reverse=True)
    return filtered[:MAX_EVIDENCE_PER_VIEWPOINT]


def _parse_llm_score(content: str) -> float:
    if content is None:
        raise ValueError("LLM score content cannot be None")
    text = str(content).strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"LLM returned non-numeric score: {text!r}")
    score = float(match.group(1))
    if not (0.0 <= score <= 1.0):
        raise ValueError(f"LLM score out of range [0,1]: {score!r}")
    return score


def llm_score_single_evidence(
    llm_client: Any,
    llm_model_name: str,
    viewpoint: str,
    evidence: str,
) -> float:
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
    response = llm_client.chat.completions.create(
        model=llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    return _parse_llm_score(content)


def llm_generate_fallback_evidence_list(
    llm_client: Any,
    llm_model_name: str,
    viewpoint: str,
    seed_evidence: Optional[str],
    count: int = FALLBACK_EVIDENCE_COUNT,
) -> List[str]:
    seed_text = (seed_evidence or "").strip()
    seed_part = f'Seed evidence: "{seed_text}"' if seed_text else "Seed evidence: (none)"

    prompt = f"""
You are generating high-quality fallback evidence statements for an opinion system.

Task:
- Produce exactly {count} distinct evidence statements supporting the viewpoint.

Hard constraints:
- If seed evidence exists: every statement MUST be grounded ONLY in seed information. Do NOT add new facts, numbers, studies, names, places, dates, or events.
- If seed evidence does not exist: do NOT fabricate concrete facts. Use rigorous, viewpoint-aligned reasoning only.
- Each statement must be specific, argument-ready, and tightly linked to the viewpoint (not abstract slogans).
- Each statement must contain a clear claim and a concrete reason/mechanism/implication.
- Maximize practical persuasive quality for comment drafting.
- Avoid weak or generic templates, including phrases like "based on goals", "shows commitment", "important to note", "generally speaking".
- Statements must be mutually non-duplicate with different angles (e.g., mechanism, risk, governance process, public impact).
- Output MUST be valid JSON: a list of {count} strings.
- Each string: plain text only, no markdown, no quotes, no bullet points inside the string.
- Length per string: 80-240 characters.

Quality checklist (must satisfy all):
1) Directly supports the viewpoint.
2) Contains concrete argumentative value (claim + reason).
3) No empty rhetoric.
4) No invented facts.

Viewpoint: "{viewpoint}"
{seed_part}

Generate {count} fallback evidence statements as JSON.
Return only JSON.
"""
    response = llm_client.chat.completions.create(
        model=llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned empty fallback evidence list")

    text = str(content).strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"LLM returned invalid JSON for fallback evidence list: {text!r}") from e

    if not isinstance(data, list) or len(data) != count:
        raise ValueError(f"LLM returned non-{count}-item list for fallback evidence list: {data!r}")

    evidences: List[str] = []
    for item in data:
        s = str(item).strip()
        if not s:
            raise ValueError("LLM returned blank fallback evidence item")
        evidences.append(s)
    return evidences


def generate_fallback_evidence_items(
    llm_client: Any,
    llm_model_name: str,
    viewpoint: str,
    scored_evidence: Optional[List[Dict[str, Any]]],
    min_acceptance_rate: float = MIN_EVIDENCE_ACCEPTANCE_RATE,
) -> List[Dict[str, Any]]:
    seed_text: Optional[str] = None
    seed_source: Optional[str] = None
    seed_acceptance_rate: Optional[float] = None

    if scored_evidence:
        seed = scored_evidence[0]
        if "evidence" not in seed:
            raise ValueError("seed evidence missing 'evidence'")
        seed_text = str(seed["evidence"]).strip()
        if not seed_text:
            seed_text = None
        seed_source = seed.get("source")
        seed_acceptance_rate = seed.get("acceptance_rate")

    generated_list = llm_generate_fallback_evidence_list(
        llm_client=llm_client,
        llm_model_name=llm_model_name,
        viewpoint=viewpoint,
        seed_evidence=seed_text,
        count=FALLBACK_EVIDENCE_COUNT,
    )

    scored_items: List[Dict[str, Any]] = []
    for generated in generated_list:
        score_error: Optional[str] = None
        try:
            score = llm_score_single_evidence(
                llm_client=llm_client,
                llm_model_name=llm_model_name,
                viewpoint=viewpoint,
                evidence=generated,
            )
        except Exception as e:
            score = 0.0
            score_error = str(e)
        scored_items.append(
            {
                "evidence": generated,
                "acceptance_rate": score,
                "source": "LLMGenerated",
                "low_confidence": score < min_acceptance_rate,
                "score_error": score_error,
                "seed_source": seed_source,
                "seed_acceptance_rate": seed_acceptance_rate,
            }
        )

    scored_items.sort(key=lambda x: x["acceptance_rate"], reverse=True)
    return scored_items[:FALLBACK_EVIDENCE_COUNT]

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS evidence_score_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id INTEGER NOT NULL,
                    old_score REAL NOT NULL,
                    new_score REAL NOT NULL,
                    usage_status TEXT,
                    reward REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (evidence_id) REFERENCES evidence (id)
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

        trace: Dict[str, Any] = {
            "retrieval_path": [],
            "min_acceptance_rate": MIN_EVIDENCE_ACCEPTANCE_RATE,
        }

        def _attach_trace(result: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(result, dict):
                return result

            outer_path = trace.get("retrieval_path", [])
            outer_min_rate = trace.get("min_acceptance_rate")
            existing_trace = result.get("trace")

            if not isinstance(existing_trace, dict):
                result["trace"] = {
                    "retrieval_path": list(outer_path) if isinstance(outer_path, list) else [],
                    "min_acceptance_rate": outer_min_rate,
                }
                return result

            existing_path = existing_trace.get("retrieval_path")
            merged_path: List[Dict[str, Any]] = []
            if isinstance(outer_path, list):
                merged_path.extend([step for step in outer_path if isinstance(step, dict)])
            if isinstance(existing_path, list):
                merged_path.extend([step for step in existing_path if isinstance(step, dict)])

            deduped_path: List[Dict[str, Any]] = []
            seen = set()
            for step in merged_path:
                key = tuple(sorted(step.items()))
                if key in seen:
                    continue
                seen.add(key)
                deduped_path.append(step)

            existing_trace["retrieval_path"] = deduped_path
            if existing_trace.get("min_acceptance_rate") is None:
                existing_trace["min_acceptance_rate"] = outer_min_rate
            result["trace"] = existing_trace
            return result
        
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
                trace["retrieval_path"].append(
                    {"step": "theme_match", "matched": False, "theme": theme}
                )
                result = self._handle_completely_new_opinion(opinion, theme, keyword)
                return _attach_trace(result)

            trace["retrieval_path"].append(
                {"step": "theme_match", "matched": True, "theme": theme}
            )
            
            # Step 3: FAISS keyword matching
            keyword_match_result = self._faiss_search_keywords(keyword)
            trace["retrieval_path"].append(
                {
                    "step": "faiss_keyword",
                    "keyword": keyword,
                    "similarity": keyword_match_result.get("similarity"),
                    "threshold": self.keyword_similarity_threshold,
                    "matched_keywords": keyword_match_result.get("matched_keywords"),
                }
            )
            
            if keyword_match_result['similarity'] >= self.keyword_similarity_threshold:
                print(f"✅ Keyword match succeeded (similarity: {keyword_match_result['similarity']:.3f})")
                matched_keywords = keyword_match_result['matched_keywords']

                # Check whether matched_keywords is empty
                if not matched_keywords or matched_keywords.strip() == '':
                    print(f"❌ Matched keywords empty; falling back to original keyword: {keyword}")
                    matched_keywords = keyword

                # Step 4: FAISS viewpoint matching
                viewpoint_match_result = self._faiss_search_viewpoints(opinion, matched_keywords)
                trace["retrieval_path"].append(
                    {
                        "step": "faiss_viewpoint",
                        "similarity": viewpoint_match_result.get("similarity"),
                        "threshold": self.viewpoint_similarity_threshold,
                        "viewpoint_id": viewpoint_match_result.get("viewpoint_id"),
                    }
                )

                if viewpoint_match_result['similarity'] >= self.viewpoint_similarity_threshold:
                    print(f"✅ Viewpoint match succeeded (similarity: {viewpoint_match_result['similarity']:.3f})")
                    # Case 1.1: Return the top evidence for the matched viewpoint
                    viewpoint_id = viewpoint_match_result.get('viewpoint_id')
                    if viewpoint_id is None:
                        print(f"⚠️ Viewpoint ID missing; switching to existing-keyword flow")
                        result = self._handle_new_viewpoint_existing_keywords(
                            opinion, theme, matched_keywords
                        )
                        return _attach_trace(result)
                    result = self._return_top5_evidence(viewpoint_id, requested_viewpoint=opinion)
                    return _attach_trace(result)
                else:
                    print(f"❌ Viewpoint match failed (similarity: {viewpoint_match_result['similarity']:.3f})")
                    # Case 1.2: new viewpoint but keywords exist
                    result = self._handle_new_viewpoint_existing_keywords(
                        opinion, theme, matched_keywords
                    )
                    return _attach_trace(result)
            else:
                print(f"❌ Keyword match failed (similarity: {keyword_match_result['similarity']:.3f})")
                # Case (2): similarity below threshold, new keyword flow
                result = self._handle_completely_new_opinion(opinion, theme, keyword)
                return _attach_trace(result)
        
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
                You are a strict classifier and discriminative keyword generator.

                Analyze the following opinion:
                Opinion: "{opinion}"

                Task 1) Topic classification
                Choose exactly ONE best-matching topic from the list below. The returned theme MUST be an exact string from the list:
                {', '.join(self.topics)}

                Task 2) Discriminative keyword generation
                Generate ONE concise keyword/phrase that accurately captures the specific meaning of the opinion and distinguishes it from other opinions that may share the same common term(s).

                Keyword rules (must follow all):
                - The keyword may be a short phrase or a short sentence (not just a single word).
                - It must be specific and descriptive, not a generic label.
                - If the opinion mentions a broad subject (e.g., "AI", "artificial intelligence"), the keyword MUST include the distinguishing target/aspect.
                - Do NOT output only generic terms such as: "AI", "artificial intelligence", "technology", "innovation".
                - Keep it concise but informative: usually 6–14 words in English.
                - Do not use quotation marks. Avoid unnecessary punctuation.

                Return ONLY valid JSON (no markdown, no explanations, no extra text):
                {{"theme":"<one topic from the list>","keyword":"<one concise, discriminative description>"}}

                Example1:
                Opinion: "Artificial intelligence will reshape education over the next decade by personalizing lessons for each student, automating grading and feedback, and helping teachers identify learning gaps earlier."
                Return: {{"theme":"Technology & Future","keyword":"AI persArtificial intelligence will change education"}}

                Example2:
                Opinion: "Artificial intelligence is likely to transform medical diagnosis by detecting subtle patterns in imaging and lab data, assisting clinicians with differential diagnoses, and reducing missed or late detections."
                Return: {{"theme":"Technology & Future","keyword":"AI enhances diagnostic accuracy through data pattern detection"}}
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
                    # Extract the single keyword
                    single_keyword = (classification.get('keyword') or '').strip()
                    if not single_keyword:
                        print("⚠️ LLM returned empty 'keyword'; falling back to 'general'")
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
    
    def _return_top5_evidence(self, viewpoint_id: int, requested_viewpoint: Optional[str] = None) -> Dict[str, Any]:
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

            db_scored = [
                {"evidence": evidence, "acceptance_rate": rate, "source": source}
                for (evidence, rate, source) in evidence_list
            ]
            db_selected = select_top_evidence(db_scored)

            # If DB contains no acceptable evidence, try Wikipedia retrieval for this existing viewpoint.
            if not db_selected:
                keywords = (viewpoint_info[2] or "").strip()
                search_keyword = keywords.split(",")[0].strip() if "," in keywords else keywords

                if search_keyword:
                    print(
                        f"🛟 Existing viewpoint has no acceptable DB evidence (>= {MIN_EVIDENCE_ACCEPTANCE_RATE}); trying Wikipedia refresh: {search_keyword}"
                    )
                    evidence_snippets = self._search_wikipedia_evidence_15(search_keyword)
                    print(f"🔍 Wikipedia returned {len(evidence_snippets)} evidences")

                    if evidence_snippets:
                        scoring_viewpoint = (
                            requested_viewpoint.strip()
                            if isinstance(requested_viewpoint, str) and requested_viewpoint.strip()
                            else viewpoint_info[0]
                        )
                        scored_wiki = self._llm_score_evidence(scoring_viewpoint, evidence_snippets)
                        wiki_selected = select_top_evidence(scored_wiki)
                        if wiki_selected:
                            print("✅ Wikipedia refresh found acceptable evidences (not persisted)")
                            result = {
                                'status': 'existing_match_wikipedia_refresh',
                                'viewpoint': viewpoint_info[0],
                                'theme': viewpoint_info[1],
                                'keywords': viewpoint_info[2],
                                'keyword': viewpoint_info[2],
                                'evidence_count': len(wiki_selected),
                                'persisted': False,
                                'fallback_reason': 'db_below_threshold_then_wikipedia_ok',
                                'evidence': [
                                    {
                                        'rank': i + 1,
                                        'evidence': item['evidence'],
                                        'acceptance_rate': item['acceptance_rate'],
                                        'source': item.get('source', 'Wikipedia'),
                                    }
                                    for i, item in enumerate(wiki_selected)
                                ],
                            }
                            result["trace"] = {
                                "retrieval_path": [
                                    {
                                        "step": "db_evidence",
                                        "selected_count": 0,
                                        "min_acceptance_rate": MIN_EVIDENCE_ACCEPTANCE_RATE,
                                    },
                                    {
                                        "step": "wikipedia_refresh",
                                        "keyword": search_keyword,
                                        "retrieved_count": len(evidence_snippets),
                                        "selected_count": len(wiki_selected),
                                    },
                                ]
                            }
                            return result

                # Wikipedia didn't help; generate LLM fallback evidences (not persisted)
                print(
                    f"🛟 Wikipedia refresh did not yield acceptable evidences; generating fallback evidences via LLM (not persisted)"
                )
                fallback_items = generate_fallback_evidence_items(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=(requested_viewpoint or viewpoint_info[0]),
                    scored_evidence=None,
                    min_acceptance_rate=MIN_EVIDENCE_ACCEPTANCE_RATE,
                )
                self._save_evidence_items(
                    viewpoint_id=viewpoint_id,
                    evidence_items=fallback_items,
                    allow_below_threshold=True,
                )
                result = {
                    'status': 'llm_fallback_evidence',
                    'viewpoint': viewpoint_info[0],
                    'theme': viewpoint_info[1],
                    'keywords': viewpoint_info[2],
                    'keyword': viewpoint_info[2],
                    'evidence_count': len(fallback_items),
                    'persisted': True,
                    'viewpoint_id': viewpoint_id,
                    'fallback_reason': 'db_below_threshold_then_wikipedia_below_threshold',
                    'evidence': [
                        {
                            'rank': i + 1,
                            'evidence': item['evidence'],
                            'acceptance_rate': item['acceptance_rate'],
                            'source': item['source'],
                            'low_confidence': item.get('low_confidence', True),
                        }
                        for i, item in enumerate(fallback_items)
                    ],
                }
                result["trace"] = {
                    "retrieval_path": [
                        {
                            "step": "db_evidence",
                            "selected_count": 0,
                            "min_acceptance_rate": MIN_EVIDENCE_ACCEPTANCE_RATE,
                        },
                        {
                            "step": "wikipedia_refresh",
                            "keyword": search_keyword,
                            "retrieved_count": 0 if not search_keyword else None,
                            "selected_count": 0,
                        },
                        {
                            "step": "llm_fallback",
                            "count": len(fallback_items),
                            "low_confidence_count": sum(1 for x in fallback_items if x.get("low_confidence")),
                        },
                    ]
                }
                return result
            
            result = {
                'status': 'existing_match',
                'viewpoint': viewpoint_info[0],
                'theme': viewpoint_info[1],
                'keywords': viewpoint_info[2],
                # Backward-compat: some callers historically used 'keyword' (singular).
                # Keep it identical to 'keywords' to avoid "unknown" in downstream logs/UI.
                'keyword': viewpoint_info[2],
                'evidence_count': len(db_selected),
                'evidence': []
            }
            result["trace"] = {
                "retrieval_path": [
                    {
                        "step": "db_evidence",
                        "selected_count": len(db_selected),
                        "min_acceptance_rate": MIN_EVIDENCE_ACCEPTANCE_RATE,
                    }
                ]
            }
            
            print(f"📋 Returning the top {MAX_EVIDENCE_PER_VIEWPOINT} evidences (sorted by acceptance_rate)")
            for i, item in enumerate(db_selected, 1):
                result['evidence'].append({
                    'rank': i,
                    'evidence': item['evidence'],
                    'acceptance_rate': item['acceptance_rate'],
                    'source': item.get('source', 'Wikipedia')
                })
                print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")
            
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
            print("🛟 No Wikipedia evidence found; generating fallback evidences via LLM (not persisted)")
            try:
                fallback_items = generate_fallback_evidence_items(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=opinion,
                    scored_evidence=None,
                    min_acceptance_rate=MIN_EVIDENCE_ACCEPTANCE_RATE,
                )
            except Exception as e:
                return {'error': f'no relevant evidence found; fallback generation failed: {e}'}

            for i, item in enumerate(fallback_items, 1):
                print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")

            viewpoint_id = self._save_to_database(
                opinion,
                theme,
                keywords,
                fallback_items,
                allow_below_threshold=True,
            )

            return {
                'status': 'llm_fallback_evidence',
                'viewpoint': opinion,
                'theme': theme,
                'keywords': keywords,
                'keyword': keywords,
                'evidence_count': len(fallback_items),
                'persisted': True,
                'viewpoint_id': viewpoint_id,
                'fallback_reason': 'wikipedia_empty',
                'trace': {
                    'retrieval_path': [
                        {'step': 'wikipedia', 'keyword': search_keyword, 'retrieved_count': 0},
                        {'step': 'llm_fallback', 'count': len(fallback_items)},
                    ],
                    'min_acceptance_rate': MIN_EVIDENCE_ACCEPTANCE_RATE,
                },
                'evidence': [
                    {
                        'rank': i + 1,
                        'evidence': item['evidence'],
                        'acceptance_rate': item['acceptance_rate'],
                        'source': item['source'],
                        'seed_source': item.get('seed_source'),
                        'seed_acceptance_rate': item.get('seed_acceptance_rate'),
                    }
                    for i, item in enumerate(fallback_items)
                ],
            }
        
        # Score via the LLM
        scored_evidence = self._llm_score_evidence(opinion, evidence_list)
        print(f"📊 LLM scored {len(scored_evidence)} evidences")
        
        # Take the top entries by acceptance_rate, with a minimum acceptance threshold
        top_evidence = select_top_evidence(scored_evidence)
        if not top_evidence:
            print(
                f"🛟 No evidence met acceptance threshold (>= {MIN_EVIDENCE_ACCEPTANCE_RATE}); generating fallback evidences via LLM (not persisted)"
            )
            try:
                fallback_items = generate_fallback_evidence_items(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=opinion,
                    scored_evidence=scored_evidence,
                    min_acceptance_rate=MIN_EVIDENCE_ACCEPTANCE_RATE,
                )
            except Exception as e:
                return {
                    'error': f'no evidence met acceptance threshold (>= {MIN_EVIDENCE_ACCEPTANCE_RATE}); fallback generation failed: {e}'
                }

            for i, item in enumerate(fallback_items, 1):
                print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")

            viewpoint_id = self._save_to_database(
                opinion,
                theme,
                keywords,
                fallback_items,
                allow_below_threshold=True,
            )

            return {
                'status': 'llm_fallback_evidence',
                'viewpoint': opinion,
                'theme': theme,
                'keywords': keywords,
                'keyword': keywords,
                'evidence_count': len(fallback_items),
                'persisted': True,
                'viewpoint_id': viewpoint_id,
                'fallback_reason': 'below_threshold',
                'trace': {
                    'retrieval_path': [
                        {'step': 'wikipedia', 'keyword': search_keyword, 'retrieved_count': len(evidence_list), 'selected_count': 0},
                        {'step': 'llm_fallback', 'count': len(fallback_items)},
                    ],
                    'min_acceptance_rate': MIN_EVIDENCE_ACCEPTANCE_RATE,
                },
                'evidence': [
                    {
                        'rank': i + 1,
                        'evidence': item['evidence'],
                        'acceptance_rate': item['acceptance_rate'],
                        'source': item['source'],
                        'seed_source': item.get('seed_source'),
                        'seed_acceptance_rate': item.get('seed_acceptance_rate'),
                    }
                    for i, item in enumerate(fallback_items)
                ],
            }
        
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
            print("🛟 No Wikipedia evidence found; generating fallback evidences via LLM (not persisted)")
            try:
                fallback_items = generate_fallback_evidence_items(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=opinion,
                    scored_evidence=None,
                    min_acceptance_rate=MIN_EVIDENCE_ACCEPTANCE_RATE,
                )
            except Exception as e:
                return {'error': f'no relevant evidence found; fallback generation failed: {e}'}

            for i, item in enumerate(fallback_items, 1):
                print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")

            viewpoint_id = self._save_to_database(
                opinion,
                theme,
                keyword,
                fallback_items,
                allow_below_threshold=True,
            )

            return {
                'status': 'llm_fallback_evidence',
                'viewpoint': opinion,
                'theme': theme,
                'keywords': keyword,
                'keyword': keyword,
                'evidence_count': len(fallback_items),
                'persisted': True,
                'viewpoint_id': viewpoint_id,
                'fallback_reason': 'wikipedia_empty',
                'trace': {
                    'retrieval_path': [
                        {'step': 'wikipedia', 'keyword': search_keyword, 'retrieved_count': 0},
                        {'step': 'llm_fallback', 'count': len(fallback_items)},
                    ],
                    'min_acceptance_rate': MIN_EVIDENCE_ACCEPTANCE_RATE,
                },
                'evidence': [
                    {
                        'rank': i + 1,
                        'evidence': item['evidence'],
                        'acceptance_rate': item['acceptance_rate'],
                        'source': item['source'],
                        'seed_source': item.get('seed_source'),
                        'seed_acceptance_rate': item.get('seed_acceptance_rate'),
                    }
                    for i, item in enumerate(fallback_items)
                ],
            }
        
        # Score using the LLM
        scored_evidence = self._llm_score_evidence(opinion, evidence_list)
        print(f"📊 LLM scored {len(scored_evidence)} evidences")
        
        # Take the top entries by acceptance_rate, with a minimum acceptance threshold
        top_evidence = select_top_evidence(scored_evidence)
        if not top_evidence:
            print(
                f"🛟 No evidence met acceptance threshold (>= {MIN_EVIDENCE_ACCEPTANCE_RATE}); generating fallback evidences via LLM (not persisted)"
            )
            try:
                fallback_items = generate_fallback_evidence_items(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=opinion,
                    scored_evidence=scored_evidence,
                    min_acceptance_rate=MIN_EVIDENCE_ACCEPTANCE_RATE,
                )
            except Exception as e:
                return {
                    'error': f'no evidence met acceptance threshold (>= {MIN_EVIDENCE_ACCEPTANCE_RATE}); fallback generation failed: {e}'
                }

            for i, item in enumerate(fallback_items, 1):
                print(f"  {i}. [Acceptance rate: {item['acceptance_rate']:.3f}] {item['evidence'][:60]}...")

            viewpoint_id = self._save_to_database(
                opinion,
                theme,
                keyword,
                fallback_items,
                allow_below_threshold=True,
            )

            return {
                'status': 'llm_fallback_evidence',
                'viewpoint': opinion,
                'theme': theme,
                'keywords': keyword,
                'keyword': keyword,
                'evidence_count': len(fallback_items),
                'persisted': True,
                'viewpoint_id': viewpoint_id,
                'fallback_reason': 'below_threshold',
                'trace': {
                    'retrieval_path': [
                        {'step': 'wikipedia', 'keyword': search_keyword, 'retrieved_count': len(evidence_list), 'selected_count': 0},
                        {'step': 'llm_fallback', 'count': len(fallback_items)},
                    ],
                    'min_acceptance_rate': MIN_EVIDENCE_ACCEPTANCE_RATE,
                },
                'evidence': [
                    {
                        'rank': i + 1,
                        'evidence': item['evidence'],
                        'acceptance_rate': item['acceptance_rate'],
                        'source': item['source'],
                        'seed_source': item.get('seed_source'),
                        'seed_acceptance_rate': item.get('seed_acceptance_rate'),
                    }
                    for i, item in enumerate(fallback_items)
                ],
            }
        
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
            score_error = None
            try:
                score = llm_score_single_evidence(
                    llm_client=self.llm_client,
                    llm_model_name=self.llm_model_name,
                    viewpoint=viewpoint,
                    evidence=evidence,
                )
            except Exception as e:
                print(f"⚠️ LLM scoring failed for one evidence: {e}")
                score = 0.0
                score_error = str(e)
            
            scored_evidence.append({
                'evidence': evidence,
                'acceptance_rate': score,
                'source': 'Wikipedia',
                'score_error': score_error,
            })
            
            time.sleep(0.1)  # Throttle requests
        
        # Sort by acceptance_rate in descending order
        scored_evidence.sort(key=lambda x: x['acceptance_rate'], reverse=True)
        return scored_evidence
    
    
    def _save_evidence_items(
        self,
        viewpoint_id: int,
        evidence_items: List[Dict[str, Any]],
        *,
        allow_below_threshold: bool = False,
    ) -> None:
        if viewpoint_id is None:
            raise ValueError("viewpoint_id cannot be None")

        evidence_to_save = (
            evidence_items[:MAX_EVIDENCE_PER_VIEWPOINT]
            if allow_below_threshold
            else select_top_evidence(evidence_items)
        )
        if not evidence_to_save:
            raise ValueError(
                f"no evidence to save for viewpoint_id={viewpoint_id} (allow_below_threshold={allow_below_threshold})"
            )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for item in evidence_to_save:
            cursor.execute(
                '''
                    INSERT INTO evidence (viewpoint_id, evidence, acceptance_rate, source)
                    VALUES (?, ?, ?, ?)
                ''',
                (
                    viewpoint_id,
                    item['evidence'],
                    float(item['acceptance_rate']),
                    item.get('source', 'Wikipedia'),
                ),
            )
        conn.commit()
        conn.close()

    def _save_to_database(
        self,
        viewpoint: str,
        theme: str,
        keywords: str,
        evidence_list: List[Dict],
        *,
        allow_below_threshold: bool = False,
    ) -> int:
        """Save the viewpoint and evidences into the database."""
        try:
            evidence_to_save = (
                evidence_list[:MAX_EVIDENCE_PER_VIEWPOINT]
                if allow_below_threshold
                else select_top_evidence(evidence_list)
            )
            if not evidence_to_save:
                raise ValueError(
                    f"refusing to save viewpoint without evidence meeting acceptance threshold (>= {MIN_EVIDENCE_ACCEPTANCE_RATE})"
                )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert viewpoint record
            cursor.execute('''
                INSERT INTO viewpoints (viewpoint, theme, key_words)
                VALUES (?, ?, ?)
            ''', (viewpoint, theme, keywords))
            
            viewpoint_id = cursor.lastrowid
            
            # Insert evidence records
            for item in evidence_to_save:
                cursor.execute(
                    '''
                        INSERT INTO evidence (viewpoint_id, evidence, acceptance_rate, source)
                        VALUES (?, ?, ?, ?)
                    ''',
                    (viewpoint_id, item['evidence'], float(item['acceptance_rate']), item.get('source', 'Wikipedia')),
                )
            
            conn.commit()
            conn.close()
            
            # Incrementally add new vectors to FAISS indexes
            self._add_vector_to_faiss(viewpoint_id, viewpoint, keywords)
            
            return viewpoint_id
            
        except Exception as e:
            print(f"❌ Failed to save to the database: {e}")
            return -1

    def update_argument_score(
        self,
        arg_id: str,
        new_score: float,
        usage_status: str,
        reward: float,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Persist argument score updates for DB-backed evidence rows.

        Returns:
            bool: True if an evidence row was updated, False if skipped/not found.
        """
        evidence_id: Optional[int] = None
        if isinstance(arg_id, int):
            evidence_id = arg_id
        elif isinstance(arg_id, str) and arg_id.strip().isdigit():
            evidence_id = int(arg_id.strip())
        else:
            print(f"ℹ️ Skip argument score update for non-DB argument id: {arg_id!r}")
            return False

        if evidence_id is None or evidence_id <= 0:
            print(f"⚠️ Invalid evidence id for score update: {arg_id!r}")
            return False

        target_score = max(0.0, min(1.0, float(new_score)))
        update_time = (
            timestamp.isoformat(sep=" ", timespec="seconds")
            if isinstance(timestamp, datetime)
            else datetime.now().isoformat(sep=" ", timespec="seconds")
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT acceptance_rate FROM evidence WHERE id = ?",
                (evidence_id,),
            )
            row = cursor.fetchone()
            if row is None:
                print(f"ℹ️ Evidence not found for score update: id={evidence_id}")
                return False

            old_score = float(row[0])
            cursor.execute(
                "UPDATE evidence SET acceptance_rate = ? WHERE id = ?",
                (target_score, evidence_id),
            )
            cursor.execute(
                """
                INSERT INTO evidence_score_updates
                (evidence_id, old_score, new_score, usage_status, reward, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (evidence_id, old_score, target_score, usage_status, float(reward), update_time),
            )
            conn.commit()
            print(
                f"✅ Updated evidence score: id={evidence_id}, "
                f"{old_score:.4f}->{target_score:.4f}, usage_status={usage_status}, reward={float(reward):.4f}"
            )
            return True
        finally:
            conn.close()

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
