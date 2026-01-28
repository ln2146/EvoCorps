import os
import sys
import types

import pytest


def _add_src_to_syspath() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(repo_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def _ensure_keys_module() -> None:
    if "keys" in sys.modules:
        return
    keys_module = types.ModuleType("keys")
    keys_module.OPENAI_API_KEY = "test-key"
    keys_module.OPENAI_BASE_URL = "https://example.test"
    sys.modules["keys"] = keys_module


def _prepare_imports() -> None:
    _add_src_to_syspath()
    _ensure_keys_module()


def test_import_does_not_require_langchain_openai() -> None:
    _prepare_imports()
    import multi_model_selector  # noqa: F401


def test_models_lists_include_deepseek_chat() -> None:
    _prepare_imports()
    from multi_model_selector import MultiModelSelector

    assert "deepseek-chat" in MultiModelSelector.ALL_MODELS
    assert "deepseek-chat" in MultiModelSelector.AVAILABLE_MODELS
    assert "deepseek-chat" in MultiModelSelector.MALICIOUS_ECHO_MODELS
    assert "deepseek-chat" in MultiModelSelector.FALLBACK_PRIORITY
    assert "deepseek-chat" in MultiModelSelector.MALICIOUS_ECHO_FALLBACK


def test_removed_models_not_present() -> None:
    _prepare_imports()
    from multi_model_selector import MultiModelSelector

    # Cleaned up references to models not present in this repo.
    assert "claude-3-5-sonnet" not in MultiModelSelector.ALL_MODELS
    assert "DeepSeek-V3" not in MultiModelSelector.ALL_MODELS


@pytest.mark.parametrize("model_name", ["gpt-4.1-nano", "gemini-2.0-flash", "deepseek-chat"])
def test_get_safe_model_config_supports_all_available_models(model_name: str) -> None:
    _prepare_imports()
    from multi_model_selector import MultiModelSelector

    selector = MultiModelSelector()
    cfg = selector.get_safe_model_config(model_name)
    assert "temperature" in cfg
    assert "max_tokens" in cfg


def test_create_langchain_client_dependency_handling() -> None:
    _prepare_imports()
    from multi_model_selector import MultiModelSelector

    selector = MultiModelSelector()
    try:
        import langchain_openai  # noqa: F401
    except ModuleNotFoundError:
        with pytest.raises(ModuleNotFoundError):
            selector.create_langchain_client(model_name="deepseek-chat")
    else:
        client, model = selector.create_langchain_client(model_name="deepseek-chat")
        assert model == "deepseek-chat"
        assert client is not None


def test_role_pools_include_memory_and_fact_checker() -> None:
    _prepare_imports()
    from multi_model_selector import MultiModelSelector

    assert "memory" in MultiModelSelector.ROLE_MODEL_POOLS
    assert "fact_checker" in MultiModelSelector.ROLE_MODEL_POOLS
    assert "embedding" in MultiModelSelector.ROLE_MODEL_POOLS
    assert MultiModelSelector.ROLE_MODEL_POOLS["memory"] == MultiModelSelector.DEFAULT_POOL
    assert MultiModelSelector.ROLE_MODEL_POOLS["fact_checker"] == MultiModelSelector.DEFAULT_POOL
    assert MultiModelSelector.ROLE_MODEL_POOLS["embedding"] == MultiModelSelector.DEFAULT_POOL
