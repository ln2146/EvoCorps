#!/usr/bin/env python3
"""
Persona management system
Select suitable personas from the database for different agent types
"""

import json
import random
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaManager:
    def __init__(self):
        self.positive_personas_file = "personas/positive_personas_database.json"
        self.neutral_personas_file = "personas/neutral_personas_database.json"
        self.negative_personas_file = "personas/negative_personas_database.json"
        
        # Load persona database
        self.positive_personas = self.load_personas(self.positive_personas_file)
        self.neutral_personas = self.load_personas(self.neutral_personas_file)
        self.negative_personas = self.load_personas(self.negative_personas_file)
        
        # Used persona IDs to avoid duplicates
        self.used_persona_ids = set()
        
        logger.info("✅ Persona database load complete:")
        logger.info(f"   Positive personas: {len(self.positive_personas)} items")
        logger.info(f"   Neutral personas: {len(self.neutral_personas)} items")
        logger.info(f"   Negative personas: {len(self.negative_personas)} items")
    
    def load_personas(self, filename: str) -> List[Dict]:
        """Load persona data"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                personas = json.load(f)
            logger.info(f"✅ Successfully loaded {len(personas)} personas from {filename}")
            return personas
        except Exception as e:
            logger.error(f"❌ Failed to load personas {filename}: {e}")
            return []
    
    def get_available_personas(self, persona_list: List[Dict]) -> List[Dict]:
        """Get unused personas"""
        return [p for p in persona_list if p['id'] not in self.used_persona_ids]
    
    def mark_persona_used(self, persona_id: str):
        """Mark persona as used"""
        self.used_persona_ids.add(persona_id)
    
    def reset_used_personas(self):
        """Reset used persona list"""
        self.used_persona_ids.clear()
        logger.info("🔄 Reset persona usage record")
    
    def select_persona_for_balance_agent(self) -> Optional[Dict]:
        """Select positive persona for opinion_balance agent"""
        available_positive = self.get_available_personas(self.positive_personas)
        
        if not available_positive:
            logger.warning("⚠️ No available positive personas, resetting usage record")
            self.reset_used_personas()
            available_positive = self.positive_personas
        
        # Prefer positive personas with specific traits
        preferred_traits = ["Rational", "Inclusive", "Moderate", "Upright", "Compassionate"]
        preferred_professions = ["Teacher", "Doctor", "Counselor", "Social Worker", "Scientist"]
        
        # Filter priority personas
        priority_personas = []
        for persona in available_positive:
            if (any(trait in persona['personality_traits'] for trait in preferred_traits) or
                persona['profession'] in preferred_professions):
                priority_personas.append(persona)
        
        # Select persona
        if priority_personas:
            selected = random.choice(priority_personas)
        else:
            selected = random.choice(available_positive)
        
        self.mark_persona_used(selected['id'])
        logger.info(f"🎭 Selected persona for opinion_balance agent: {selected['name']} ({selected['demographics']['profession']})")
        return selected
    
    def select_persona_for_regular_user(self) -> Optional[Dict]:
        """Select persona for regular user (1:1:1 ratio)"""
        # Randomly select persona type
        persona_type = random.choice(['positive', 'neutral', 'negative'])
        
        if persona_type == 'positive':
            available = self.get_available_personas(self.positive_personas)
            source_name = "positive"
        elif persona_type == 'neutral':
            available = self.get_available_personas(self.neutral_personas)
            source_name = "neutral"
        else:  # negative
            available = self.get_available_personas(self.negative_personas)
            source_name = "negative"
        
        if not available:
            logger.warning(f"⚠️ No available {source_name} personas, resetting usage record")
            self.reset_used_personas()
            if persona_type == 'positive':
                available = self.positive_personas
            elif persona_type == 'neutral':
                available = self.neutral_personas
            else:
                available = self.negative_personas
        
        selected = random.choice(available)
        self.mark_persona_used(selected['id'])
        logger.info(f"👤 Selected {source_name} persona for regular user: {selected['name']} ({selected['demographics']['profession']})")
        return selected
    
    def select_persona_for_malicious_agent(self) -> Optional[Dict]:
        """Select negative persona for malicious agent"""
        available_negative = self.get_available_personas(self.negative_personas)
        
        if not available_negative:
            logger.warning("⚠️ No available negative personas, resetting usage record")
            self.reset_used_personas()
            available_negative = self.negative_personas
        
        # Prefer negative personas with specific traits
        preferred_traits = ["Aggressive", "Extreme", "Inciting", "Paranoid", "Angry"]
        preferred_professions = ["Internet Troll", "Keyboard Warrior", "Conspiracy Theorist", "Extremist", "Hate Spreader"]
        
        # Filter priority personas
        priority_personas = []
        for persona in available_negative:
            if (any(trait in persona['personality_traits'] for trait in preferred_traits) or
                persona['demographics']['profession'] in preferred_professions):
                priority_personas.append(persona)
        
        # Select persona
        if priority_personas:
            selected = random.choice(priority_personas)
        else:
            selected = random.choice(available_negative)
        
        self.mark_persona_used(selected['id'])
        logger.info(f"😈 Selected persona for malicious agent: {selected['name']} ({selected['demographics']['profession']})")
        return selected
    
    def select_personas_batch(self, count: int, agent_type: str = 'regular') -> List[Dict]:
        """Select personas in batch"""
        selected_personas = []
        
        for i in range(count):
            if agent_type == 'balance':
                persona = self.select_persona_for_balance_agent()
            elif agent_type == 'malicious':
                persona = self.select_persona_for_malicious_agent()
            else:  # regular
                persona = self.select_persona_for_regular_user()
            
            if persona:
                selected_personas.append(persona)
        
        logger.info(f"📋 Batch selection complete: {len(selected_personas)} {agent_type} personas")
        return selected_personas
    
    def get_persona_statistics(self) -> Dict:
        """Get persona usage statistics"""
        total_personas = len(self.positive_personas) + len(self.neutral_personas) + len(self.negative_personas)
        used_count = len(self.used_persona_ids)
        
        # Stats by persona type
        used_positive = sum(1 for pid in self.used_persona_ids if pid.startswith('positive_'))
        used_neutral = sum(1 for pid in self.used_persona_ids if pid.startswith('neutral_'))
        used_negative = sum(1 for pid in self.used_persona_ids if pid.startswith('negative_'))
        
        stats = {
            'total_personas': total_personas,
            'used_personas': used_count,
            'available_personas': total_personas - used_count,
            'usage_percentage': (used_count / total_personas) * 100 if total_personas > 0 else 0,
            'by_type': {
                'positive': {
                    'total': len(self.positive_personas),
                    'used': used_positive,
                    'available': len(self.positive_personas) - used_positive
                },
                'neutral': {
                    'total': len(self.neutral_personas),
                    'used': used_neutral,
                    'available': len(self.neutral_personas) - used_neutral
                },
                'negative': {
                    'total': len(self.negative_personas),
                    'used': used_negative,
                    'available': len(self.negative_personas) - used_negative
                }
            }
        }
        
        return stats
    
    def print_statistics(self):
        """Print persona usage statistics"""
        stats = self.get_persona_statistics()
        
        print("📊 Persona usage stats:")
        print(f"   Total personas: {stats['total_personas']}")
        print(f"   Used: {stats['used_personas']} ({stats['usage_percentage']:.1f}%)")
        print(f"   Available: {stats['available_personas']}")
        print()
        print("📋 By type:")
        for persona_type, type_stats in stats['by_type'].items():
            type_name = {'positive': 'Positive', 'neutral': 'Neutral', 'negative': 'Negative'}[persona_type]
            print(f"   {type_name} personas: {type_stats['used']}/{type_stats['total']} (remaining {type_stats['available']})")
    
    def convert_to_agent_config(self, persona: Dict) -> Dict:
        """Convert persona to agent config format"""
        # Build background labels
        background_labels = []
        background_labels.extend(persona['personality_traits'])
        # New format has no interests field; use background instead
        profession = persona.get('demographics', {}).get('profession', 
                  persona.get('profession', 'Unknown'))
        background_labels.append(profession)
        background_labels.append(f"Age {persona['demographics']['age']}")
        background_labels.append(f"From {persona['demographics']['region']}")
        
        # Build agent config
        agent_config = {
            'persona_id': persona['id'],
            'name': persona['name'],
            'background': persona.get('background', ''),
            'background_labels': background_labels,
            'personality': {
                'traits': persona['personality_traits'],
                'communication_style': persona.get('communication_style', {}),
                'values': persona.get('values_and_beliefs', {}).get('core_values', [])
            },
            'social_media_behavior': persona.get('social_media_behavior', {}),
            'demographic': {
                'profession': profession,
                'age_range': persona['demographics']['age'],
                'education': persona['demographics'].get('education', 'Unknown'),
                'region': persona['demographics']['region']
            },
            'type': persona['type']
        }
        
        return agent_config
    
    def get_agent_configs(self, count: int, agent_type: str = 'regular') -> List[Dict]:
        """Get agent config list"""
        personas = self.select_personas_batch(count, agent_type)
        return [self.convert_to_agent_config(persona) for persona in personas]


def main():
    """Testing persona management system"""
    manager = PersonaManager()
    
    print("🧪 Testing persona selection system...")
    print()
    
    # testing opinion_balance agent persona select
    print("1. Test opinion balance agent persona selection:")
    balance_persona = manager.select_persona_for_balance_agent()
    if balance_persona:
        print(f"   Selected persona: {balance_persona['name']}")
        print(f"   Profession: {balance_persona['demographics']['profession']}")
        print(f"   Personality: {', '.join(balance_persona['personality_traits'])}")
    print()
    
    # testing regular user persona select
    print("2. Test regular user persona selection (1:1:1 ratio):")
    for i in range(6):
        user_persona = manager.select_persona_for_regular_user()
        if user_persona:
 ": {user_persona['name']} ({user_persona['type']}) - {user_persona['demographics']['profession']}")
    print()
    
    # testing malicious agent persona select
    print("3. Test malicious agent persona selection:")
    malicious_persona = manager.select_persona_for_malicious_agent()
    if malicious_persona:
        print(f"   Selected persona: {malicious_persona['name']}")
        print(f"   Profession: {malicious_persona['demographics']['profession']}")
        print(f"   Personality: {', '.join(malicious_persona['personality_traits'])}")
    print()
    
    # Print statistics info
    manager.print_statistics()
    
    # testing agent config conversion
    print("\n4. Test agent config conversion:")
    agent_config = manager.convert_to_agent_config(balance_persona)
    print(f"   Agent ID: {agent_config['persona_id']}")
    print(f"   Background label count: {len(agent_config['background_labels'])}")
    print(f"   Type: {agent_config['type']}")


if __name__ == "__main__":
    main()
