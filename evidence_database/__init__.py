#!/usr/bin/env python3
"""
Evidence Database - Opinion Argument Processing System
Provides full capabilities for argument classification, retrieval, scoring, and storage.

Core features:
- LLM topic classification (14 topic categories)
- Intelligent keyword extraction
- FAISS vector retrieval matching
- Wikipedia argument search
- LLM scoring system
- Database storage management
"""

from .opinion_processing_system import OpinionProcessingSystem

# Version info
__version__ = "1.0.0"
__author__ = "Claude"
__description__ = "Opinion Argument Processing System"

# Exported classes
__all__ = [
    'OpinionProcessingSystem',
    'create_system',
    'process_opinion_quick'
]

def create_system(db_path: str = "opinion_database.db", api_key: str = None) -> OpinionProcessingSystem:
    """
    Create an OpinionProcessingSystem instance.
    
    Args:
        db_path: Path to the database file
        api_key: Optional API key
    
    Returns:
        OpinionProcessingSystem: System instance
    """
    system = OpinionProcessingSystem(db_path)
    if api_key:
        system.set_api_key(api_key)
    return system

def process_opinion_quick(opinion: str, api_key: str = None, db_path: str = "opinion_database.db") -> dict:
    """
    Process an opinion quickly (one-line call).
    
    Args:
        opinion: Opinion text input
        api_key: Optional API key
        db_path: Database path
    
    Returns:
        dict: Processing results
    """
    system = create_system(db_path, api_key)
    return system.process_opinion(opinion)

# Usage examples
if __name__ == "__main__":
    print("🎯 Evidence Database Opinion Argument Processing System")
    print("=" * 50)
    print("Usage examples:")
    print()
    print("# Option 1: Create a system instance")
    print("from evidence_database import create_system")
    print("system = create_system(api_key='your_key')")
    print("result = system.process_opinion('your opinion')")
    print()
    print("# Option 2: Quick invocation")
    print("from evidence_database import process_opinion_quick") 
    print("result = process_opinion_quick('your opinion', api_key='your_key')")
    print()
    print("# Option 3: Direct import")
    print("from evidence_database import OpinionProcessingSystem")
    print("system = OpinionProcessingSystem()")
