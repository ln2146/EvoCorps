#!/usr/bin/env python3
"""
Persona loader - loads persona data from various database files.
"""

import json
import random
import os
from typing import List, Dict, Any, Optional


class PersonaLoader:
    """Persona data loader."""
    
    def __init__(self, base_path: str = "personas"):
        self.base_path = base_path
        self._cache = {}
        
        # Mapping of database files
        self.database_files = {
            "positive": "positive_personas_database.json",
            "neutral": "neutral_personas_database.json", 
            "negative": "negative_personas_database.json"
        }
    
    def _get_file_path(self, filename: str) -> Optional[str]:
        """Get the full path for the provided filename."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", self.base_path, filename),
            os.path.join(self.base_path, filename),
            os.path.join(os.getcwd(), self.base_path, filename),
            filename  # Direct path
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def load_personas(self, persona_type: str) -> List[Dict[str, Any]]:
        """Load persona data for the requested class type."""
        
        if persona_type not in self.database_files:
            raise ValueError(f"Unsupported persona class type: {persona_type}. Supported keys: {list(self.database_files.keys())}")
        
        # checkcache
        if persona_type in self._cache:
            return self._cache[persona_type]
        
        filename = self.database_files[persona_type]
        file_path = self._get_file_path(filename)
        
        if not file_path:
            raise FileNotFoundError(f"Cannot locate {persona_type} database file: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                personas = json.load(f)
            
            print(f"  📁 Loading {persona_type} database: {file_path}")
            print(f"  📋 Successfully read {len(personas)} {persona_type} personas")
            
            # Cache the data
            self._cache[persona_type] = personas
            
            return personas
            
        except Exception as e:
            raise Exception(f"Failed to load {persona_type} database: {e}")
    
    def sample_personas(self, persona_type: str, count: int) -> List[Dict[str, Any]]:
        """Randomly sample a number of personas from the specified class."""
        
        personas = self.load_personas(persona_type)
        
        if count > len(personas):
            print(f"  ⚠️  Requested {count} exceeds available {len(personas)} personas; returning all available.")
            return personas
        
        selected = random.sample(personas, count)
        print(f"  🎯 Selected {len(selected)} out of {len(personas)} {persona_type} personas")
        
        return selected
    
    def sample_mixed_personas(self, positive_count: int = 1, neutral_count: int = 1, 
                            negative_count: int = 1) -> List[Dict[str, Any]]:
        """Sample personas proportionally from all three databases for regular users."""
        
        mixed_personas = []
        
        if positive_count > 0:
            positive_personas = self.sample_personas("positive", positive_count)
            mixed_personas.extend(positive_personas)
        
        if neutral_count > 0:
            neutral_personas = self.sample_personas("neutral", neutral_count)
            mixed_personas.extend(neutral_personas)
        
        if negative_count > 0:
            negative_personas = self.sample_personas("negative", negative_count)
            mixed_personas.extend(negative_personas)
        
        # Shuffle the mixed personas to randomize order
        random.shuffle(mixed_personas)
        
        print(f"  🎭 Mix: {positive_count} positive + {neutral_count} neutral + {negative_count} negative = {len(mixed_personas)} total")
        
        return mixed_personas
    
    def get_persona_stats(self) -> Dict[str, Any]:
        """Get statistics across all persona databases."""
        
        stats = {}
        
        for persona_type in self.database_files.keys():
            try:
                personas = self.load_personas(persona_type)
                
                # Track profession distribution
                professions = {}
                age_ranges = {}
                regions = {}
                
                for persona in personas:
                    prof = persona.get("demographics", {}).get("profession", "Unknown")
                    age = persona.get("demographics", {}).get("age", "Unknown")
                    region = persona.get("demographics", {}).get("region", "Unknown")
                    
                    professions[prof] = professions.get(prof, 0) + 1
                    age_ranges[age] = age_ranges.get(age, 0) + 1
                    regions[region] = regions.get(region, 0) + 1
                
                stats[persona_type] = {
                    "total_count": len(personas),
                    "top_professions": sorted(professions.items(), key=lambda x: x[1], reverse=True)[:5],
                    "age_distribution": dict(sorted(age_ranges.items())),
                    "top_regions": sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]
                }
                
            except Exception as e:
                stats[persona_type] = {"error": str(e)}
        
        return stats
    
    def clear_cache(self):
        """Clear the internal persona cache."""
        self._cache.clear()
        print("  🧹 Persona cache cleared")


# globalinstance
persona_loader = PersonaLoader()


def load_echo_agent_personas(count: int = 5) -> List[Dict[str, Any]]:
    """Load positive personas specifically for echo agents."""
    return persona_loader.sample_personas("positive", count)


def load_regular_user_personas(count: int = 3) -> List[Dict[str, Any]]:
    """Load mixed personas for regular users at a 1:1:1 ratio."""
    # Calculate how many personas per class type
    per_type = max(1, count // 3)
    remainder = count % 3
    
    positive_count = per_type + (1 if remainder > 0 else 0)
    neutral_count = per_type + (1 if remainder > 1 else 0)
    negative_count = per_type
    
    return persona_loader.sample_mixed_personas(positive_count, neutral_count, negative_count)


def load_malicious_agent_personas(count: int = 2) -> List[Dict[str, Any]]:
    """Load negative personas for malicious agents."""
    return persona_loader.sample_personas("negative", count)


if __name__ == "__main__":
    # Testing utilities
    print("🧪 Persona loader test")
    print("=" * 50)
    
    # Display database statistics
    stats = persona_loader.get_persona_stats()
    for persona_type, stat in stats.items():
        print(f"\n📊 {persona_type.upper()} database statistics:")
        if "error" in stat:
            print(f"   ❌ Error: {stat['error']}")
        else:
            print(f"   Total count: {stat['total_count']}")
            print(f"   Top professions: {stat['top_professions'][:3]}")
    
    # Test loading functions
    print(f"\n🧪 Test loading personas:")
    echo_personas = load_echo_agent_personas(3)
    print(f"   Echo agents: {len(echo_personas)} personas")
    
    user_personas = load_regular_user_personas(6)
    print(f"   Regular users: {len(user_personas)} personas")
    
    malicious_personas = load_malicious_agent_personas(2)
    print(f"   Malicious agents: {len(malicious_personas)} personas")
