#!/usr/bin/env python3
"""
English persona adapter
Integrate the English persona database system into the existing opinion simulation system
Supports 600 personas (200 positive + 200 neutral + 200 negative)
"""

import json
import random
import logging
from typing import List, Dict, Optional

try:
    from .english_persona_manager import EnglishPersonaManager
except ImportError:
    from english_persona_manager import EnglishPersonaManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnglishPersonaAdapter:
    """English persona adapter for integration with existing system"""
    
    def __init__(self):
        self.persona_manager = EnglishPersonaManager()
        
    def generate_agent_configs_for_simulation(self, 
                                            num_users: int,
                                            balance_agents: int = 0,
                                            malicious_agents: int = 0) -> List[Dict]:
        """
        Generate agent configs for opinion simulation
        
        Args:
            num_users: Regular user count
            balance_agents: Opinion balance agent count
            malicious_agents: Malicious agent count
        
        Returns:
            List of agent configs
        """
        all_configs = []
        
        # Generate regular user configs (1:1:1 ratio)
        if num_users > 0:
            logger.info(f"🎭 Generating {num_users} regular user personas...")
            user_configs = self.persona_manager.get_agent_configs(num_users, 'regular')
            all_configs.extend(user_configs)
        
        # generateopinion_balanceAgentconfigure
        if balance_agents > 0:
            logger.info(f"⚖️ Generating {balance_agents} balance agent personas...")
            balance_configs = self.persona_manager.get_agent_configs(balance_agents, 'balance')
            all_configs.extend(balance_configs)
        
        # Generate malicious agent configs
        if malicious_agents > 0:
            logger.info(f"😈 Generating {malicious_agents} malicious agent personas...")
            malicious_configs = self.persona_manager.get_agent_configs(malicious_agents, 'malicious')
            all_configs.extend(malicious_configs)
        
        # Randomize order
        random.shuffle(all_configs)
        
        logger.info(f"✅ Total generated {len(all_configs)} agent configs")
        return all_configs
    
    def convert_to_legacy_format(self, agent_config: Dict) -> Dict:
        """
        Convert to legacy format for compatibility
        """
        # Extract key info
        background_text = agent_config['background']
        background_labels = agent_config['background_labels']
        
        # Build legacy format
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
        """Generate configs compatible with legacy system"""
        new_configs = self.generate_agent_configs_for_simulation(
            num_users, balance_agents, malicious_agents
        )
        
        legacy_configs = []
        for config in new_configs:
            legacy_config = self.convert_to_legacy_format(config)
            legacy_configs.append(legacy_config)
        
        return legacy_configs
    
    def save_configs_to_jsonl(self, configs: List[Dict], filename: str):
        """Save configs to JSONL file"""
        import jsonlines
        import os
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with jsonlines.open(filename, mode='w') as writer:
            for config in configs:
                writer.write(config)
        
        logger.info(f"✅ Saved {len(configs)} configs to {filename}")
    
    def create_persona_files_for_system(self, 
                                      num_positive: int = 100,
                                      num_neutral: int = 100,
                                      num_negative: int = 100):
        """
        Create English persona files for the existing system
        """
        # Generate positive persona file
        positive_configs = self.persona_manager.get_agent_configs(num_positive, 'balance')
        positive_legacy = [self.convert_to_legacy_format(config) for config in positive_configs]
        self.save_configs_to_jsonl(positive_legacy, "personas/positive_personas_en.jsonl")
        
        # Generate neutral persona file (filter neutral from regular users)
        neutral_personas = []
        attempts = 0
        while len(neutral_personas) < num_neutral and attempts < num_neutral * 3:
            config = self.persona_manager.select_persona_for_regular_user()
            if config and config['type'] == 'neutral':
                agent_config = self.persona_manager.convert_to_agent_config(config)
                legacy_config = self.convert_to_legacy_format(agent_config)
                neutral_personas.append(legacy_config)
            attempts += 1
        
        self.save_configs_to_jsonl(neutral_personas, "personas/neutral_personas_en.jsonl")
        
        # Generate negative persona file
        negative_configs = self.persona_manager.get_agent_configs(num_negative, 'malicious')
        negative_legacy = [self.convert_to_legacy_format(config) for config in negative_configs]
        self.save_configs_to_jsonl(negative_legacy, "personas/extreme_personas_en.jsonl")
        
        logger.info("🎉 English persona files created!")
        logger.info(f"   Positive personas: {len(positive_legacy)} -> personas/positive_personas_en.jsonl")
        logger.info(f"   Neutral personas: {len(neutral_personas)} -> personas/neutral_personas_en.jsonl")
        logger.info(f"   Negative personas: {len(negative_legacy)} -> personas/extreme_personas_en.jsonl")
    
    def get_statistics_report(self) -> Dict:
        """Get detailed statistics report"""
        stats = self.persona_manager.get_persona_statistics()
        
        # Add extra analysis
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
        """Print detailed report"""
        report = self.get_statistics_report()
        
        print("📊 English Persona Database Detailed Report")
        print("=" * 50)
        
        # Basic statistics
        stats = report['database_stats']
        print(f"📈 Basic Statistics:")
        print(f"   Total personas: {stats['total_personas']}")
        print(f"   Used: {stats['used_personas']} ({stats['usage_percentage']:.1f}%)")
        print(f"   Available: {stats['available_personas']}")
        
        # By type statistics
        print(f"\n📋 By Type:")
        for persona_type, type_stats in stats['by_type'].items():
            type_name = {'positive': 'Positive', 'neutral': 'Neutral', 'negative': 'Negative'}[persona_type]
            print(f"   {type_name}: {type_stats['used']}/{type_stats['total']} (available {type_stats['available']})")
        
        # Distribution analysis
        dist = report['distribution_analysis']
        print(f"\n🎯 Distribution Analysis:")
        print(f"   Positive ratio: {dist['balance_ratio']['positive']:.1f}%")
        print(f"   Neutral ratio: {dist['balance_ratio']['neutral']:.1f}%")
        print(f"   Negative ratio: {dist['balance_ratio']['negative']:.1f}%")
        
        # Recommended usage
        rec = dist['recommended_usage']
        print(f"\n💡 Recommended Usage:")
        print(f"   Max regular users: {rec['max_regular_users']} (1:1:1 ratio)")
        print(f"   Max balance agents: {rec['max_balance_agents']}")
        print(f"   Max malicious agents: {rec['max_malicious_agents']}")
        
        # Quality metrics
        quality = report['quality_metrics']
        print(f"\n🏆 Quality Metrics:")
        print(f"   Profession diversity: {quality['persona_diversity']} different professions")
        print(f"   Age diversity: {quality['age_diversity']} age groups")
        print(f"   Region diversity: {quality['region_diversity']} regions")


def main():
    """Testing English persona adapter"""
    adapter = EnglishPersonaAdapter()
    
    print("🧪 Testing English Persona Adapter...")
    print()
    
    # Test agent config generation
    print("1. Testing agent config generation:")
    configs = adapter.generate_agent_configs_for_simulation(
        num_users=10,
        balance_agents=3,
        malicious_agents=2
    )
    
    print(f"   Generated configs: {len(configs)}")
    print("   Config type distribution:")
    type_counts = {}
    for config in configs:
        config_type = config['type']
        type_counts[config_type] = type_counts.get(config_type, 0) + 1
    
    for config_type, count in type_counts.items():
        type_name = {'positive': 'Positive', 'neutral': 'Neutral', 'negative': 'Negative'}[config_type]
        print(f"     {type_name}: {count}")
    
    print()
    
    # Test legacy format conversion
    print("2. Testing legacy format conversion:")
    legacy_config = adapter.convert_to_legacy_format(configs[0])
    print(f"   Original fields: {len(configs[0])}")
    print(f"   Converted fields: {len(legacy_config)}")
    print(f"   Persona type: {legacy_config['persona_type']}")
    print(f"   Profession: {legacy_config['profession']}")
    
    print()
    
    # Create system persona files
    print("3. Creating system persona files:")
    adapter.create_persona_files_for_system(
        num_positive=50,
        num_neutral=50,
        num_negative=50
    )
    
    print()
    
    # Print detailed report
    print("4. Detailed statistics report:")
    adapter.print_detailed_report()


if __name__ == "__main__":
    main()
