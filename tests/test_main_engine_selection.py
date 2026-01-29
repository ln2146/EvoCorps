import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from engine_selector import select_engine_from_selector, apply_selector_engine


def test_select_engine_from_selector_uses_selector():
    class DummySelector:
        def select_random_model(self, role="regular"):
            assert role == "regular"
            return "dummy-model"

    dummy_module = types.SimpleNamespace(multi_model_selector=DummySelector())

    assert select_engine_from_selector(selector_module=dummy_module) == "dummy-model"


def test_apply_selector_engine_sets_config_engine():
    config = {}

    class DummySelector:
        def select_random_model(self, role="regular"):
            return "dummy-model"

    dummy_module = types.SimpleNamespace(multi_model_selector=DummySelector())

    apply_selector_engine(config, selector_module=dummy_module)

    assert config["engine"] == "dummy-model"
