import importlib
import sys
import types
from pathlib import Path


def _load_selector_with_dummy_keys():
    dummy_keys = types.SimpleNamespace(
        OPENAI_API_KEY="dummy",
        OPENAI_BASE_URL="http://localhost",
        EMBEDDING_API_KEY="dummy",
        EMBEDDING_BASE_URL="http://localhost",
    )
    sys.modules["keys"] = dummy_keys
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
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
