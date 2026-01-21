#!/usr/bin/env python3
"""
Config manager - manage MOSAIC system configuration options
"""

import json
import os
from typing import Dict, Any, List, Optional


class ConfigManager:
    """Config manager"""
    
    def __init__(self, config_file: str = "config/mosaic_config.json"):
        # Ensure config file path is correct
        if not os.path.isabs(config_file):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Public-opinion-balance directory
            self.config_file = os.path.join(project_root, config_file)
        else:
            self.config_file = config_file
        self.config = self._load_config()
        
        # Supported monitoring interval options
        self.supported_monitoring_intervals = [1, 5, 10, 30, 60]
        
        # Monitoring interval descriptions
        self.monitoring_interval_descriptions = {
            1: "🔥 Ultra-high frequency monitoring (1 min) - real-time response, high resource usage",
            5: "🚀 High-frequency monitoring (5 min) - fast response, suitable for emergencies",
            10: "⚡ Mid-high frequency monitoring (10 min) - balance speed and resources",
            30: "📊 Standard monitoring (30 min) - recommended setting, balance effect and cost",
            60: "🕐 Low-frequency monitoring (60 min) - resource-saving, suitable for long-term monitoring"
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config file"""
        
        # Default config
        default_config = {
            "opinion_balance_system": {
                "enabled": True,
                "monitoring_enabled": True,
                "intervention_threshold": 2,
                "response_delay_minutes": [2, 4, 6, 8, 10],
                "max_responses_per_post": 5,
                "effectiveness_tracking": True,
                "monitoring_interval_minutes": 30,
                "auto_adjustment_enabled": True,
                "adjustment_sensitivity": "medium"
            },
            "echo_agents": {
                "count": 5,
                "persona_source": "positive_personas_database.json",
                "diversity_mode": "random",
                "response_authenticity_threshold": 0.7
            },
            "monitoring_system": {
                "baseline_collection_minutes": 10,
                "sentiment_analysis_enabled": True,
                "engagement_tracking_enabled": True,
                "report_generation_enabled": True
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "console_enabled": True
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Merge default config and loaded config
                config = self._merge_configs(default_config, loaded_config)
                print(f"✅ Config file loaded successfully: {self.config_file}")
                return config
            else:
                print(f"📝 Config file not found, using default config: {self.config_file}")
                self._save_config(default_config)
                return default_config
                
        except Exception as e:
            print(f"❌ Failed to load config file, using default config: {e}")
            return default_config
    
    def _merge_configs(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Merge config and preserve default values"""
        
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _save_config(self, config: Dict[str, Any]):
        """Save config to file"""
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Config saved: {self.config_file}")
            
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
    
    def get_monitoring_interval(self) -> int:
        """Get current monitoring interval"""
        return self.config.get('opinion_balance_system', {}).get('monitoring_interval_minutes', 30)
    
    def set_monitoring_interval(self, interval: int) -> bool:
        """Set monitoring interval"""
        
        if interval not in self.supported_monitoring_intervals:
            print(f"❌ Unsupported monitoring interval: {interval} minutes")
            print(f"📋 Supported intervals: {self.supported_monitoring_intervals}")
            return False
        
        # Save both key names for compatibility
        self.config['opinion_balance_system']['monitoring_interval_minutes'] = interval
        self.config['opinion_balance_system']['monitoring_interval'] = interval
        self._save_config(self.config)
        
        print(f"✅ Monitoring interval set to: {interval} minutes")
        print(f"📋 {self.monitoring_interval_descriptions[interval]}")
        
        return True
    
    def get_monitoring_interval_options(self) -> List[Dict[str, Any]]:
        """Get monitoring interval options"""
        
        current_interval = self.get_monitoring_interval()
        
        options = []
        for interval in self.supported_monitoring_intervals:
            options.append({
                "value": interval,
                "label": f"{interval} minutes",
                "description": self.monitoring_interval_descriptions[interval],
                "is_current": interval == current_interval,
                "recommended": interval == 30
            })
        
        return options
    
    def display_monitoring_options(self):
        """Display monitoring interval options"""
        
        print("📊 Monitoring interval options:")
        print("=" * 60)
        
        options = self.get_monitoring_interval_options()
        
        for i, option in enumerate(options, 1):
            current_mark = " ✅ [current]" if option["is_current"] else ""
            recommended_mark = " 🌟 [recommended]" if option["recommended"] else ""
            
            print(f"{i}. {option['description']}{current_mark}{recommended_mark}")
        
        print("=" * 60)
    
    def interactive_set_monitoring_interval(self):
        """Interactively set monitoring interval"""
        
        self.display_monitoring_options()
        
        try:
            choice = input("\nSelect monitoring interval (enter number 1-5): ").strip()
            
            if not choice.isdigit():
                print("❌ Please enter a valid number")
                return False
            
            choice_idx = int(choice) - 1
            
            if choice_idx < 0 or choice_idx >= len(self.supported_monitoring_intervals):
                print("❌ Selection out of range")
                return False
            
            selected_interval = self.supported_monitoring_intervals[choice_idx]
            return self.set_monitoring_interval(selected_interval)
            
        except KeyboardInterrupt:
            print("\n❌ Operation canceled")
            return False
        except Exception as e:
            print(f"❌ Failed to set interval: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get full config"""
        return self.config.copy()
    
    def update_config(self, updates: Dict[str, Any]):
        """Update config"""
        
        self.config = self._merge_configs(self.config, updates)
        self._save_config(self.config)
    
    def reset_to_defaults(self):
        """Reset to default config"""
        
        print("⚠️  Resetting config to defaults...")
        
        # Reload default config
        self.config = self._load_config()
        
        # Delete existing config file
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        
        # Save default config
        self._save_config(self.config)
        
        print("✅ Config reset to defaults")


# Global config manager instance
config_manager = ConfigManager()


if __name__ == "__main__":
    # Testing config manager
    print("🧪 Testing config manager")
    print("=" * 50)
    
    # Show current config
    current_interval = config_manager.get_monitoring_interval()
    print(f"Current monitoring interval: {current_interval} minutes")
    
    # Show options
    config_manager.display_monitoring_options()
    
    # Interactive setting (if running in terminal)
    if os.isatty(0):  # Check if in interactive terminal
        print("\n🔧 Interactive config:")
        config_manager.interactive_set_monitoring_interval()
    
    # Show full config
    print(f"\n📋 Full config:")
    config = config_manager.get_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))
