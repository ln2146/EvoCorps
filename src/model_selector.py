"""
Legacy model selector - unified via MultiModelSelector.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from multi_model_selector import MultiModelSelector, multi_model_selector


class ModelSelector:
    """Unified model selection system"""

    # Backward-compatible aliases
    AVAILABLE_MODELS = MultiModelSelector.ALL_MODELS
    FALLBACK_PRIORITY = MultiModelSelector.FALLBACK_PRIORITY

    @classmethod
    def select_random_model(cls) -> str:
        """Select a random model"""
        return multi_model_selector.select_random_model(role="regular")

    @classmethod
    def create_client(cls, model_name: Optional[str] = None):
        """Create OpenAI client and select model name"""
        return multi_model_selector.create_openai_client(model_name=model_name, role="regular")

    @classmethod
    def create_client_with_fallback(cls, preferred_model: Optional[str] = None):
        """Create client with fallback support"""
        return multi_model_selector.create_client_with_fallback(
            preferred_model=preferred_model,
            client_type="openai",
            role="regular",
        )

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Get configuration parameters for a specific model"""
        return multi_model_selector.get_model_config(model_name)


# Global model selector instance
model_selector = ModelSelector()
