# Embedding Model Pool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the embedding role pool derive from `EMBEDDING_MODEL` and ensure `create_embedding_client()` uses `self.EMBEDDING_MODEL` by default.

**Architecture:** Keep `MultiModelSelector` as the single source of truth for embedding model selection by wiring the embedding role pool to `EMBEDDING_MODEL` and verifying the default path via unit tests.

**Tech Stack:** Python, pytest

### Task 1: Add failing tests for embedding model defaults

**Files:**
- Create: `tests/test_multi_model_selector_embedding.py`

**Step 1: Write the failing test**

```python
import importlib
import sys
import types


def _load_selector_with_dummy_keys():
    dummy_keys = types.SimpleNamespace(
        OPENAI_API_KEY="dummy",
        OPENAI_BASE_URL="http://localhost",
        EMBEDDING_API_KEY="dummy",
        EMBEDDING_BASE_URL="http://localhost",
    )
    sys.modules["keys"] = dummy_keys
    import multi_model_selector as mms
    return importlib.reload(mms)


def test_embedding_pool_uses_embedding_model():
    mms = _load_selector_with_dummy_keys()
    selector = mms.MultiModelSelector()
    assert selector.ROLE_MODEL_POOLS["embedding"] == [selector.EMBEDDING_MODEL]


def test_create_embedding_client_defaults_to_embedding_model():
    mms = _load_selector_with_dummy_keys()
    selector = mms.MultiModelSelector()
    _, model_name = selector.create_embedding_client()
    assert model_name == selector.EMBEDDING_MODEL
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_model_selector_embedding.py -v`

Expected: FAIL because the embedding pool currently uses `DEFAULT_POOL`.

### Task 2: Implement minimal changes

**Files:**
- Modify: `src/multi_model_selector.py`

**Step 1: Update embedding role pool**

```python
"embedding": [EMBEDDING_MODEL],
```

**Step 2: Ensure `create_embedding_client()` defaults to `self.EMBEDDING_MODEL`**

Confirm `model_name` default path uses the instance attribute and does not hardcode a literal.

**Step 3: Run tests**

Run: `pytest tests/test_multi_model_selector_embedding.py -v`

Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_multi_model_selector_embedding.py src/multi_model_selector.py
git commit -m "fix: use EMBEDDING_MODEL for embedding role pool"
```
