#!/usr/bin/env python3
"""
User generator - create different user classes (regular users, malicious agents, etc.)
"""

import random
import string
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    from .persona_loader import persona_loader
except ImportError:
    # If relative import fails, try absolute import
    try:
        from persona_loader import persona_loader
    except ImportError:
        # If both imports fail, use a simple fallback
        print("⚠️  persona_loader unavailable, using simplified version")
        class SimplePersonaLoader:
            def sample_personas(self, persona_type, count):
                return []
        persona_loader = SimplePersonaLoader()


class UserGenerator:
        """User generator."""
    
    def __init__(self):
        self.generated_users = []
        self.user_counter = 0
    
    def _generate_user_id(self, prefix: str = "user") -> str:
        """Generate a unique user ID."""
        self.user_counter += 1
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}-{random_suffix}"
    
    def _create_user_from_persona(self, persona_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Create a user record from persona data."""
        
        user_id = self._generate_user_id(user_type)
        
        user = {
            "user_id": user_id,
            "user_type": user_type,
            "persona_id": persona_data.get("id", "unknown"),
            "name": persona_data.get("name", f"User_{user_id}"),
            "persona_type": persona_data.get("type", "unknown"),
            "profession": persona_data.get('demographics', {}).get('profession', 
                      persona_data.get('profession', 'Unknown')),
            "age_range": persona_data.get("demographics", {}).get("age", "Unknown"),
            "education": persona_data.get("demographics", {}).get("education", "Unknown"),
            "region": persona_data.get("demographics", {}).get("region", "Unknown"),
            "personality_traits": persona_data.get("personality_traits", []),
            "interests": persona_data.get("interests", []),
            "creation_time": datetime.now(),
            "activity_level": self._determine_activity_level(persona_data),
            "posting_frequency": self._determine_posting_frequency(persona_data),
            "engagement_style": self._determine_engagement_style(persona_data)
        }
        
        self.generated_users.append(user)
        return user
    
    def _determine_activity_level(self, persona_data: Dict[str, Any]) -> str:
        """Determine activity level based on persona traits."""
        persona_type = persona_data.get("type", "neutral")
        personality_traits = persona_data.get("personality_traits", [])
        
        if persona_type == "positive":
            if "Active" in personality_traits or "Enthusiastic" in personality_traits:
                return "high"
            else:
                return "medium"
        elif persona_type == "negative":
            if "Aggressive" in personality_traits or "Radical" in personality_traits:
                return "very_high"
            else:
                return "high"
        else:  # neutral
            return "low"
    
    def _determine_posting_frequency(self, persona_data: Dict[str, Any]) -> str:
        """Determine posting frequency from activity level."""
        activity_level = self._determine_activity_level(persona_data)
        
        frequency_map = {
            "very_high": "multiple_daily",
            "high": "daily", 
            "medium": "weekly",
            "low": "monthly"
        }
        
        return frequency_map.get(activity_level, "weekly")
    
    def _determine_engagement_style(self, persona_data: Dict[str, Any]) -> str:
        """Determine engagement style from persona traits."""
        persona_type = persona_data.get("type", "neutral")
        personality_traits = persona_data.get("personality_traits", [])
        
        if persona_type == "positive":
            if "Supportive" in personality_traits:
                return "supportive"
            elif "Rational" in personality_traits:
                return "analytical"
            else:
                return "encouraging"
        elif persona_type == "negative":
            if "Aggressive" in personality_traits:
                return "confrontational"
            elif "Skeptical" in personality_traits:
                return "critical"
            else:
                return "disruptive"
        else:  # neutral
            return "observational"
    
    def generate_regular_users(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate regular users by sampling equally from each database."""
        
        print(f"👥 Generating {count} regular users (1:1:1 ratio)")
        
        # Calculate the number of personas per class
        per_type = count // 3
        remainder = count % 3
        
        positive_count = per_type + (1 if remainder > 0 else 0)
        neutral_count = per_type + (1 if remainder > 1 else 0)
        negative_count = per_type
        
        print(f"   📊 Allocation: {positive_count} positive + {neutral_count} neutral + {negative_count} negative")
        
        users = []
        
        # Generate positive users
        if positive_count > 0:
            positive_personas = persona_loader.sample_personas("positive", positive_count)
            for persona in positive_personas:
                user = self._create_user_from_persona(persona, "regular_user")
                users.append(user)
        
        # Generate neutral users
        if neutral_count > 0:
            neutral_personas = persona_loader.sample_personas("neutral", neutral_count)
            for persona in neutral_personas:
                user = self._create_user_from_persona(persona, "regular_user")
                users.append(user)
        
        # Generate negative users
        if negative_count > 0:
            negative_personas = persona_loader.sample_personas("negative", negative_count)
            for persona in negative_personas:
                user = self._create_user_from_persona(persona, "regular_user")
                users.append(user)
        
        # Shuffle the generated users
        random.shuffle(users)
        
        print(f"   ✅ Generated {len(users)} regular users successfully")
        
        return users
    
    def generate_malicious_agents(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate malicious agents sampled from the negative persona database."""
        
        print(f"🦹 Generating {count} malicious agents")
        
        negative_personas = persona_loader.sample_personas("negative", count)
        
        agents = []
        for persona in negative_personas:
            agent = self._create_user_from_persona(persona, "malicious_agent")
            # Add malicious-specific attributes
            agent.update({
                "agent_capabilities": ["content_generation", "coordinated_posting", "harassment"],
                "target_topics": persona.get("interests", []),
                "attack_strategies": self._determine_attack_strategies(persona)
            })
            agents.append(agent)
        
        print(f"   ✅ Generated {len(agents)} malicious agents successfully")
        
        return agents
    
    def _determine_attack_strategies(self, persona_data: Dict[str, Any]) -> List[str]:
        """Determine attack strategies based on persona data."""
        personality_traits = persona_data.get("personality_traits", [])
        interests = persona_data.get("interests", [])
        
        strategies = []
        
        if "Aggressive" in personality_traits:
            strategies.append("direct_confrontation")
        if "Manipulative" in personality_traits:
            strategies.append("misinformation_spreading")
        if "Radical" in personality_traits:
            strategies.append("extremist_content")
        if "Online Harassment" in interests:
            strategies.append("targeted_harassment")
        if "Extreme Politics" in interests:
            strategies.append("political_polarization")
        
        # Default strategy
        if not strategies:
            strategies = ["general_disruption"]
        
        return strategies
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Return statistics about generated users."""
        
        if not self.generated_users:
            return {"total_users": 0}
        
        stats = {
            "total_users": len(self.generated_users),
            "by_type": {},
            "by_persona_type": {},
            "by_activity_level": {},
            "by_profession": {}
        }
        
        for user in self.generated_users:
            # Statistics by user class
            user_type = user["user_type"]
            stats["by_type"][user_type] = stats["by_type"].get(user_type, 0) + 1
            
            # Statistics by persona class
            persona_type = user["persona_type"]
            stats["by_persona_type"][persona_type] = stats["by_persona_type"].get(persona_type, 0) + 1
            
            # Statistics by activity level
            activity_level = user["activity_level"]
            stats["by_activity_level"][activity_level] = stats["by_activity_level"].get(activity_level, 0) + 1
            
            # Statistics by profession
            profession = user["profession"]
            stats["by_profession"][profession] = stats["by_profession"].get(profession, 0) + 1
        
        return stats
    
    def clear_users(self):
        """Clear all generated users."""
        self.generated_users.clear()
        self.user_counter = 0
        print("🧹 Cleared generated user data")


# globalinstance
user_generator = UserGenerator()


if __name__ == "__main__":
    # Test routine
    print("🧪 User generator test")
    print("=" * 50)
    
    # Generate regular users
    regular_users = user_generator.generate_regular_users(9)
    print(f"\n👥 Regular user sample:")
    for i, user in enumerate(regular_users[:3], 1):
        print(f"   {i}. {user['name']} ({user['persona_type']}) - {user['profession']}")
        print(f"      Personality: {', '.join(user['personality_traits'][:3])}")
        print(f"      Activity: {user['activity_level']}, Posting: {user['posting_frequency']}")
    
    # Generate malicious agents
    malicious_agents = user_generator.generate_malicious_agents(3)
    print(f"\n🦹 Malicious agent sample:")
    for i, agent in enumerate(malicious_agents, 1):
        print(f"   {i}. {agent['name']} - {agent['profession']}")
        print(f"      Attack strategies: {', '.join(agent['attack_strategies'])}")
    
    # Show statistics
    stats = user_generator.get_user_stats()
    print(f"\n📊 User statistics:")
    print(f"   Total users: {stats['total_users']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   By persona: {stats['by_persona_type']}")
    print(f"   By activity: {stats['by_activity_level']}")
