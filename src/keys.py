# API Keys Configuration - DO NOT SHARE and DO NOT UPLOAD TO GITHUB

# OpenAI API key
OPENAI_API_KEY = "YOUR_API_KEY"

# OpenAI API base URL - use this for API proxies/mirrors
OPENAI_BASE_URL = "BASE-URL"



# Multi-Model Selection System
import random
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ModelSelector:
    """Unified model selection system"""

    # Four available models
    AVAILABLE_MODELS = [
        "gpt-4.1-nano",      # OpenAI-compatible model
        # "DeepSeek-V3",       # DeepSeek model
        "gemini-2.0-flash",  # Google Gemini model
        "grok-3-mini"        # xAI Grok model
    ]

    # Fallback priority (high to low)
    FALLBACK_PRIORITY = [
        "gemini-2.0-flash",
        # "DeepSeek-V3",
        "gpt-4.1-nano",
        "grok-3-mini"
    ]

    @classmethod
    def select_random_model(cls) -> str:
        """Select a random model"""
        return random.choice(cls.AVAILABLE_MODELS)

    @classmethod
    def create_client(cls, model_name: str = None):
        """Create OpenAI client and select model name"""
        if model_name is None:
            model_name = cls.select_random_model()

        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=120
        )

        return client, model_name

    @classmethod
    def create_client_with_fallback(cls, preferred_model: str = None):
        """Create client with fallback support"""
        models_to_try = cls.FALLBACK_PRIORITY.copy() if preferred_model is None else [preferred_model] + cls.FALLBACK_PRIORITY

        for model in models_to_try:
            try:
                client, selected_model = cls.create_client(model)
                # Optional: add simple connection test here
                return client, selected_model
            except Exception as e:
                print(f"⚠️ Model {model} connection failed: {e}")
                continue

        # If all models fail, use default model
        print("⚠️ All models failed, using default model")
        return cls.create_client("gemini-2.0-flash")

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Get configuration parameters for a specific model"""
        model_configs = {
            "gpt-4.1-nano": {
                "temperature": 0.8,
                "max_tokens": 150,
                "frequency_penalty": 0.3,
                "presence_penalty": 0.3
            },
            "DeepSeek-V3": {
                "temperature": 0.7,
                "max_tokens": 200,
                "frequency_penalty": 0.2,
                "presence_penalty": 0.2
            },
            "gemini-2.0-flash": {
                "temperature": 0.75,
                "max_tokens": 180,
                "frequency_penalty": 0.25,
                "presence_penalty": 0.25
            },
            "grok-3-mini": {
                "temperature": 0.85,
                "max_tokens": 160,
                "frequency_penalty": 0.4,
                "presence_penalty": 0.3
            }
        }

        return model_configs.get(model_name, model_configs["gemini-2.0-flash"])

# Global model selector instance
model_selector = ModelSelector()
