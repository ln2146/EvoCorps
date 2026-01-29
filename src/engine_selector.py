import types
from typing import Optional


def select_engine_from_selector(selector_module: Optional[object] = None) -> str:
    if selector_module is None:
        from multi_model_selector import multi_model_selector
        selector_module = types.SimpleNamespace(multi_model_selector=multi_model_selector)

    return selector_module.multi_model_selector.select_random_model(role="regular")


def apply_selector_engine(config: dict, selector_module: Optional[object] = None) -> None:
    engine = select_engine_from_selector(selector_module=selector_module)
    config["engine"] = engine
