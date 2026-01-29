# Embedding Model Wiring (RAG) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure `AdvancedRAGSystem` uses the model returned by the embedding client instead of a hardcoded constant.

**Architecture:** Use `MultiModelSelector` as the single source of truth for the embedding model and feed its result into `AdvancedRAGSystem` initialization to avoid direct hardcoded references.

**Tech Stack:** Python, pytest

### Task 1: Add failing tests for RAG embedding model wiring

**Files:**
- Create: `tests/test_advanced_rag_embedding_model.py`

**Step 1: Write the failing tests**

```python
# tests/test_advanced_rag_embedding_model.py
import sys
import types
from pathlib import Path


def _import_rag_with_dummy_selector():
    dummy_module = types.SimpleNamespace(
        multi_model_selector=types.SimpleNamespace(
            create_embedding_client=lambda: (object(), "embedding-3"),
        )
    )
    sys.modules["multi_model_selector"] = dummy_module
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    import advanced_rag_system as ars
    return ars


def test_rag_uses_embedding_client_model(tmp_path):
    ars = _import_rag_with_dummy_selector()
    rag = ars.AdvancedRAGSystem(data_path=str(tmp_path))
    assert rag.model_name == "embedding-3"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_advanced_rag_embedding_model.py -v`

Expected: FAIL because `AdvancedRAGSystem` still sets `self.model_name` from the class constant, not the embedding client result.

### Task 2: Implement minimal changes

**Files:**
- Modify: `src/advanced_rag_system.py`

**Step 1: Set model_name from embedding client**

In `AdvancedRAGSystem._initialize_openai_client()`, assign `self.model_name` from the returned model and ensure the log uses that value.

**Step 3: Run tests**

Run: `pytest tests/test_advanced_rag_embedding_model.py -v`

Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_advanced_rag_embedding_model.py src/advanced_rag_system.py
git commit -m "fix: wire rag embedding model selection"
```
