#!/usr/bin/env python3
"""
Perfect opinion processor tailored to user needs.
Implements FAISS vector search, 15 Wikipedia evidence retrieval, and complete workflow control.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_opinion_system import EnhancedOpinionSystem

class PerfectOpinionProcessor:
    """Perfect opinion processor."""
    
    def __init__(self, api_key: str = None, db_path: str = "opinion_database.db"):
        """
        Initialize the processor.
        
        Args:
            api_key: Gemini API key (base_url="https://aihubmix.com/v1", model="gemini-2.0-flash")
            db_path: Database path
        """
        self.system = EnhancedOpinionSystem(db_path)
        if api_key:
            self.system.set_api_key(api_key)
        
        print("✅ Perfect opinion processor initialized")
        print("📋 Workflow overview:")
        print("  1. LLM topic classification (14 topics)")
        print("  2. Keyword extraction (store the most central word)")
        print("  3. Theme matching check")
        print("  4. FAISS vector search for keywords (threshold=0.7)")
        print("     (1) Similarity >= threshold -> FAISS viewpoint search (threshold=0.7)")
        print("         1. similarity >= threshold -> return top 5 by acceptance_rate")
        print("         2. similarity < threshold -> new viewpoint, existing keywords, fetch 15 Wikipedia entries")
        print("     (2) similarity < threshold -> new keywords, fetch 15 Wikipedia entries")
        print("  5. LLM scoring, keep top 5 entries")
        print("  🔑 Keyword storage: keep only the most central single term (e.g., 'intelligence', 'climate')")
        print()
    
    def process(self, opinion: str) -> dict:
        """
        Process an opinion following the complete workflow described for full customization.
        
        Args:
            opinion: Input opinion text
            
        Returns:
            dict: Result dictionary containing:
                - status: Processing state ('existing_match', 'new_viewpoint_existing_keywords', 'completely_new')
                - viewpoint: The opinion text
                - theme: Topic classification
                - keywords: Extracted keywords
                - evidence_count: Number of evidence items returned
                - evidence: List of evidences including rank, evidence text, acceptance_rate, source
        """
        return self.system.process_opinion(opinion)
    
    def set_api_key(self, api_key: str):
    """Set the API key."""
        self.system.set_api_key(api_key)
    
    def get_evidence(self, opinion: str, top_k: int = 5) -> list:
    """
    Retrieve evidence list for an opinion (sorted by acceptance_rate).
    
    Args:
        opinion: Opinion text
        top_k: Number of evidence items to return (default 5)
        
    Returns:
        list: Evidence list sorted high-to-low by acceptance_rate
    """
        result = self.process(opinion)
        if 'evidence' in result:
            return result['evidence'][:top_k]
        return []
    
    def get_classification(self, opinion: str) -> tuple:
    """
    Get classification info for the opinion.
    
    Args:
        opinion: Opinion text
        
    Returns:
        tuple: (theme, keywords)
    """
        result = self.process(opinion)
        return result.get('theme', ''), result.get('keywords', '')

# Convenience helpers
def process_opinion(opinion: str, api_key: str = None) -> dict:
    """
    Quickly process an opinion.
    
    Args:
        opinion: Opinion text
        api_key: Optional API key
        
    Returns:
        dict: Full processing results
    """
    processor = PerfectOpinionProcessor(api_key)
    return processor.process(opinion)

def get_evidence_only(opinion: str, api_key: str = None) -> list:
    """
    Fetch evidence only (sorted by acceptance_rate).
    
    Args:
        opinion: Opinion text
        api_key: Optional API key
        
    Returns:
        list: Top 5 evidence entries
    """
    processor = PerfectOpinionProcessor(api_key)
    return processor.get_evidence(opinion)

if __name__ == "__main__":
    print("🧪 Perfect opinion processor test")
    print("=" * 80)
    
    # Create a processor instance
    processor = PerfectOpinionProcessor()
    
    # Test opinions covering varied scenarios
    test_opinions = [
        "Artificial intelligence will dramatically improve the accuracy of medical diagnostics",  # new opinion test
        "Immediate carbon taxation is needed to combat global warming",  # new opinion test
        "Renewable energy storage technology is crucial for sustainable development",  # may match existing keywords
    ]

    print("🔬 Testing opinion processing in different scenarios:")

    for i, opinion in enumerate(test_opinions, 1):
        print(f"\n{'='*15} Test case {i} {'='*15}")
        print(f"📝 Opinion: {opinion}")
        
        try:
            result = processor.process(opinion)
            
            if 'error' not in result:
                print(f"✅ Processing succeeded")
                print(f"📊 Status: {result['status']}")
                print(f"📂 Theme: {result['theme']}")
                print(f"🔑 Keywords: {result['keywords']}")
                print(f"📋 Evidence count: {result['evidence_count']}")
                
                if result.get('evidence'):
                    print(f"🏆 Top 2 evidences:")
                    for j, evidence in enumerate(result['evidence'][:2], 1):
                        print(f"  {j}. [Acceptance rate: {evidence['acceptance_rate']:.3f}] {evidence['evidence'][:80]}...")
            else:
                print(f"❌ Processing failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ System exception: {e}")
    
    print(f"\n" + "="*80)
    print("💡 Instructions:")
    print("1. Set the API key: processor.set_api_key('your_api_key')")
    print("2. Process an opinion: result = processor.process('your opinion')")
    print("3. Fetch evidence: evidence = processor.get_evidence('your opinion')")
    print("4. Get classification: theme, keywords = processor.get_classification('your opinion')")
    print()
    print("🎯 Workflow highlights:")
    print("✅ FAISS vector retrieval when available")
    print("✅ Wikipedia API search for 15 pieces of evidence")
    print("✅ LLM scoring sorted by acceptance_rate")
    print("✅ Persist top 5 high-scoring evidences")
    print("✅ Precise classification across 14 topics")
    print("✅ Full alignment with user workflow requirements")
