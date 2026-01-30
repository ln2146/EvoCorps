import importlib
import sqlite3
import sys
import types
from pathlib import Path

import numpy as np


def _import_rag_with_dummy_selector(monkeypatch):
    dummy_module = types.ModuleType("multi_model_selector")
    dummy_module.MultiModelSelector = types.SimpleNamespace(
        EMBEDDING_MODEL="embedding-3",
    )
    dummy_module.multi_model_selector = types.SimpleNamespace(
        create_embedding_client=lambda model_name=None: (object(), "embedding-xyz"),
    )
    monkeypatch.setitem(sys.modules, "multi_model_selector", dummy_module)

    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    monkeypatch.delitem(sys.modules, "advanced_rag_system", raising=False)
    import advanced_rag_system as ars
    return importlib.reload(ars)


def test_query_text_index_dim_mismatch_triggers_rebuild(monkeypatch, tmp_path):
    ars = _import_rag_with_dummy_selector(monkeypatch)
    rag = ars.AdvancedRAGSystem(data_path=str(tmp_path))

    # Force encoder output to be 1536-d vectors (current embedding dim).
    rag._encode_text = lambda _text: np.zeros((1536,), dtype="float32")

    # Seed DB with one action_log row so rebuilding has something to index.
    conn = sqlite3.connect(rag.db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO action_logs
          (action_id, timestamp, execution_time, success, effectiveness_score,
           situation_context, strategic_decision, execution_details, lessons_learned, full_log)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "action_test_1",
            "2026-01-30 00:00:00",
            1.23,
            1,
            0.9,
            "some situation context",
            "{}",
            "{}",
            "[]",
            "full log",
        ),
    )
    conn.commit()
    conn.close()

    # Create a mismatched FAISS index on disk: index dim 2048 but metadata claims 1536.
    import faiss
    import pickle

    bad_index = faiss.IndexFlatIP(2048)
    bad_index.add(np.zeros((1, 2048), dtype="float32"))

    faiss.write_index(bad_index, str(rag.query_text_index_path))
    with open(rag.query_text_metadata_path, "wb") as f:
        pickle.dump(
            {
                "query_text_ids": [1],
                "vector_dimension": 1536,
                "index_type": "query_text",
                "created_at": "2026-01-30T00:00:00",
                "vector_count": 1,
            },
            f,
        )

    assert rag._load_query_text_index() is True
    assert rag.query_text_index.d == 2048

    # This retrieve would previously fail due to dimension mismatch when searching/adding.
    query = ars.RetrievalQuery(
        query_text="test query",
        query_type="mixed",
        context_filters={},
        similarity_threshold=0.0,
        max_results=1,
        include_metadata=True,
    )
    rag.retrieve(query)

    # After fix, the index should be rebuilt to match the current embedding dimension.
    assert rag.query_text_index is not None
    assert rag.query_text_index.d == 1536
