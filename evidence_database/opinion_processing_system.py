#!/usr/bin/env python3
"""
Compatibility wrapper for `evidence_database.__init__`.

The repo's `evidence_database/__init__.py` expects `OpinionProcessingSystem`.
The main implementation is `EnhancedOpinionSystem`, so we alias it here.
"""

from __future__ import annotations

from .enhanced_opinion_system import EnhancedOpinionSystem


class OpinionProcessingSystem(EnhancedOpinionSystem):
    pass

