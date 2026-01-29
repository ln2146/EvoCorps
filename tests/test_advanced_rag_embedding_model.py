import sys
import types
from pathlib import Path


def _import_rag_with_dummy_selector():
    dummy_module = types.SimpleNamespace(
        MultiModelSelector=types.SimpleNamespace(
            EMBEDDING_MODEL="embedding-3",
        ),
        multi_model_selector=types.SimpleNamespace(
            create_embedding_client=lambda model_name=None: (object(), "embedding-xyz"),
        ),
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
    assert rag.model_name == "embedding-xyz"
