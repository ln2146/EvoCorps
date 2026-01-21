"""
MOSAIC Utils Package
Utility package module containing persona loader and user generator helpers.
"""

# Avoid circular imports by not importing Utils here.
# Import the Utils class directly from src/utils.py when needed.

try:
    from .persona_loader import (
        PersonaLoader,
        persona_loader,
        load_echo_agent_personas,
        load_regular_user_personas,
        load_malicious_agent_personas
    )
    PERSONA_LOADER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Persona loader unavailable: {e}")
    PERSONA_LOADER_AVAILABLE = False

try:
    from .user_generator import (
        UserGenerator,
        user_generator
    )
    USER_GENERATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  User generator unavailable: {e}")
    USER_GENERATOR_AVAILABLE = False

# Basic exports (does not include Utils to avoid circular import)
__all__ = []

# Conditional exports
if PERSONA_LOADER_AVAILABLE:
    __all__.extend([
        'PersonaLoader',
        'persona_loader',
        'load_echo_agent_personas',
        'load_regular_user_personas',
        'load_malicious_agent_personas'
    ])

if USER_GENERATOR_AVAILABLE:
    __all__.extend([
        'UserGenerator',
        'user_generator'
    ])
