#!/usr/bin/env python3
"""
Persona adapter
Integrates the new persona database system into the existing opinion simulation system.
"""

import json
import random
import logging
from typing import List, Dict, Optional
try:
    from .persona_manager import PersonaManager
except ImportError:
    from persona_manager import PersonaManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaAdapter:
    """Persona adapter used to integrate into the current system."""
    
    def __init__(self):
        self.persona_manager = PersonaManager()
        
    def generate_agent_configs_for_simulation(self, 
                                            num_users: int,
                                            balance_agents: int = 0,
                                            malicious_agents: int = 0) -> List[Dict]:
        """
        Generate agent configurations for the opinion simulation.
        
        Args:
            num_users: number of regular users
            balance_agents: number of opinion balance agents
            malicious_agents: number of malicious agents
        
        Returns:
            A list of agent configurations
        """
        all_configs = []
        
        # Generate regular user configurations (1:1:1 ratio)
        if num_users > 0:
            logger.info(f"🎭 Generating {num_users} regular personas...")
            user_configs = self.persona_manager.get_agent_configs(num_users, 'regular')
            all_configs.extend(user_configs)
        
        # Generate opinion balance agent configurations
        if balance_agents > 0:
            logger.info(f"⚖️ Generating {balance_agents} opinion balance personas...")
            balance_configs = self.persona_manager.get_agent_configs(balance_agents, 'balance')
            all_configs.extend(balance_configs)
        
        # Generate malicious agent configurations
        if malicious_agents > 0:
            logger.info(f"😈 Generating {malicious_agents} malicious personas...")
            malicious_configs = self.persona_manager.get_agent_configs(malicious_agents, 'malicious')
            all_configs.extend(malicious_configs)
        
        # Randomly shuffle the sequence
        random.shuffle(all_configs)
        
        logger.info(f"✅ Generated {len(all_configs)} agent configurations total")
        return all_configs
    
    def convert_to_legacy_format(self, agent_config: Dict) -> Dict:
        """
        Convert to the legacy format for compatibility with the existing system.
        """
        # Extract key information
        background_text = agent_config['background']
        background_labels = agent_config['background_labels']
        
        # Build the legacy format
        legacy_config = {
            'name': agent_config['name'],
            'background': background_text,
            'background_labels': background_labels,
            'persona_type': agent_config['type'],
            'profession': agent_config['demographic']['profession'],
            'age_range': agent_config['demographic']['age_range'],
            'education': agent_config['demographic']['education'],
            'region': agent_config['demographic']['region'],
            'personality_traits': agent_config['personality']['traits'],
            'social_media_behavior': agent_config['social_media_behavior'],
            'communication_style': agent_config['personality']['communication_style']
        }
        
        return legacy_config
    
    def generate_legacy_configs(self, 
                               num_users: int,
                               balance_agents: int = 0,
                               malicious_agents: int = 0) -> List[Dict]:
        """Generate configurations compatible with the legacy system."""
        new_configs = self.generate_agent_configs_for_simulation(
            num_users, balance_agents, malicious_agents
        )
        
        legacy_configs = []
        for config in new_configs:
            legacy_config = self.convert_to_legacy_format(config)
            legacy_configs.append(legacy_config)
        
        return legacy_configs
    
    def save_configs_to_jsonl(self, configs: List[Dict], filename: str):
        """Save configurations to a JSONL file."""
        import jsonlines
        import os
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with jsonlines.open(filename, mode='w') as writer:
            for config in configs:
                writer.write(config)
        
        logger.info(f"✅ Saved {len(configs)} configurations to {filename}")
    
    def create_persona_files_for_system(self, 
                                      num_positive: int = 50,
                                      num_neutral: int = 50,
                                      num_negative: int = 50):
        """
        Create persona files for the existing system.
        """
        # Generate positive persona file
        positive_configs = self.persona_manager.get_agent_configs(num_positive, 'balance')
        positive_legacy = [self.convert_to_legacy_format(config) for config in positive_configs]
        self.save_configs_to_jsonl(positive_legacy, "personas/positive_personas.jsonl")
        
        # Generate neutral persona file (filter neutral personas from regular users)
        neutral_personas = []
        attempts = 0
        while len(neutral_personas) < num_neutral and attempts < num_neutral * 3:
            config = self.persona_manager.select_persona_for_regular_user()
            if config and config['type'] == 'neutral':
                agent_config = self.persona_manager.convert_to_agent_config(config)
                legacy_config = self.convert_to_legacy_format(agent_config)
                neutral_personas.append(legacy_config)
            attempts += 1
        
        self.save_configs_to_jsonl(neutral_personas, "personas/neutral_personas.jsonl")
        
        # Generate negative persona file
        negative_configs = self.persona_manager.get_agent_configs(num_negative, 'malicious')
        negative_legacy = [self.convert_to_legacy_format(config) for config in negative_configs]
        self.save_configs_to_jsonl(negative_legacy, "personas/extreme_personas.jsonl")
        
        logger.info("🎉 Persona files creation complete!")
        logger.info(f"   Positive personas: {len(positive_legacy)} -> personas/positive_personas.jsonl")
        logger.info(f"   Neutral personas: {len(neutral_personas)} -> personas/neutral_personas.jsonl")
        logger.info(f"   Negative personas: {len(negative_legacy)} -> personas/extreme_personas.jsonl")
    
    def get_statistics_report(self) -> Dict:
        """Get a detailed statistics report."""
        stats = self.persona_manager.get_persona_statistics()
        
        # Add additional analysis
        report = {
            'database_stats': stats,
            'distribution_analysis': {
                'total_available': stats['available_personas'],
                'balance_ratio': {
                    'positive': stats['by_type']['positive']['available'] / stats['available_personas'] * 100,
                    'neutral': stats['by_type']['neutral']['available'] / stats['available_personas'] * 100,
                    'negative': stats['by_type']['negative']['available'] / stats['available_personas'] * 100
                },
                'recommended_usage': {
                    'max_regular_users': stats['available_personas'] // 3,  # 1:1:1 ratio
                    'max_balance_agents': stats['by_type']['positive']['available'],
                    'max_malicious_agents': stats['by_type']['negative']['available']
                }
            },
            'quality_metrics': {
                'persona_diversity': len(set(p['profession'] for p in 
                    self.persona_manager.positive_personas + 
                    self.persona_manager.neutral_personas + 
                    self.persona_manager.negative_personas)),
                'age_diversity': len(set(p['age_range'] for p in 
                    self.persona_manager.positive_personas + 
                    self.persona_manager.neutral_personas + 
                    self.persona_manager.negative_personas)),
                'region_diversity': len(set(p['region'] for p in 
                    self.persona_manager.positive_personas + 
                    self.persona_manager.neutral_personas + 
                    self.persona_manager.negative_personas))
            }
        }
        
        return report
    
    def print_detailed_report(self):
        """Print the detailed report."""
        report = self.get_statistics_report()
        
        print("📊 Persona database detailed report")
        print("=" * 50)
        
        # basicstatistics
        stats = report['database_stats']
        print(f"📈 Basic statistics:")
        print(f"   Total personas: {stats['total_personas']}")
        print(f"   Used: {stats['used_personas']} ({stats['usage_percentage']:.1f}%)")
        print(f"   Available: {stats['available_personas']}")
        
        # breakdown by persona type statistics
        print(f"\n📋 Breakdown by persona type:")
        for persona_type, type_stats in stats['by_type'].items():
            type_name = {'positive': 'Positive', 'neutral': 'Neutral', 'negative': 'Negative'}[persona_type]
            print(f"   {type_name}: {type_stats['used']}/{type_stats['total']} (available {type_stats['available']})")
        
        # distribution analysis
        dist = report['distribution_analysis']
        print(f"\n🎯 Distribution analysis:")
        print(f"   Positive persona ratio: {dist['balance_ratio']['positive']:.1f}%")
        print(f"   Neutral persona ratio: {dist['balance_ratio']['neutral']:.1f}%")
        print(f"   Negative persona ratio: {dist['balance_ratio']['negative']:.1f}%")
        
        # Recommended usage
        rec = dist['recommended_usage']
        print(f"\n💡 Recommended usage:")
        print(f"   Max regular users: {rec['max_regular_users']} (1:1:1 ratio)")
        print(f"   Max balance agents: {rec['max_balance_agents']}")
        print(f"   Max malicious agents: {rec['max_malicious_agents']}")
        
        # Quality metrics
        quality = report['quality_metrics']
        print(f"\n🏆 Quality metrics:")
        print(f"   Occupational diversity: {quality['persona_diversity']} different professions")
        print(f"   Age diversity: {quality['age_diversity']} age brackets")
        print(f"   Regional diversity: {quality['region_diversity']} regions")


def main():
    """Test the persona adapter."""
    adapter = PersonaAdapter()
    
    print("🧪 Testing persona adapter...")
    print()
    
    # Testing agent configuration generation
    print("1. Test agent configuration generation:")
    configs = adapter.generate_agent_configs_for_simulation(
        num_users=6,
        balance_agents=2,
        malicious_agents=2
    )
    
    print(f"   Generated configurations: {len(configs)}")
    print("   Configuration distribution:")
    type_counts = {}
    for config in configs:
        config_type = config['type']
        type_counts[config_type] = type_counts.get(config_type, 0) + 1
    
    for config_type, count in type_counts.items():
        type_name = {'positive': 'Positive', 'neutral': 'Neutral', 'negative': 'Negative'}[config_type]
        print(f"     {type_name}: {count}")
    
    print()
    
    # Testing legacy format conversion
    print("2. Test legacy format conversion:")
    legacy_config = adapter.convert_to_legacy_format(configs[0])
    print(f"   Original field count: {len(configs[0])}")
    print(f"   Converted field count: {len(legacy_config)}")
    print(f"   Persona type: {legacy_config['persona_type']}")
    print(f"   Profession: {legacy_config['profession']}")
    
    print()
    
    # Create system persona files
    print("3. Generate persona files for the system:")
    adapter.create_persona_files_for_system(
        num_positive=20,
        num_neutral=20,
        num_negative=20
    )
    
    print()
    
    # Print the detailed report
    print("4. Detailed statistics report:")
    adapter.print_detailed_report()


if __name__ == "__main__":
    main()
