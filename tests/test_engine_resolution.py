import os
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def test_resolve_engine_prefers_config():
    from utils import resolve_engine

    config = {"engine": "deepseek-chat"}
    assert resolve_engine(config) == "deepseek-chat"


def test_resolve_engine_uses_selector_when_missing():
    from utils import resolve_engine

    class DummySelector:
        def select_random_model(self, role="regular"):
            return "dummy-model"

    assert resolve_engine({}, selector=DummySelector()) == "dummy-model"
