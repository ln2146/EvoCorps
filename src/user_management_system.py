#!/usr/bin/env python3
"""
User management system that handles different user classes (regular users, malicious agents, etc.)
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from utils.persona_loader import persona_loader


class UserManagementSystem:
    """User management system"""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
        self.cursor = db_connection.cursor()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure the required tables exist"""
        
        # users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS managed_users (
                user_id TEXT PRIMARY KEY,
                user_type TEXT NOT NULL,
                persona_id TEXT,
                name TEXT,
                persona_type TEXT,
                profession TEXT,
                age_range TEXT,
                education TEXT,
                region TEXT,
                personality_traits TEXT,
                interests TEXT,
                creation_time TIMESTAMP,
                activity_level TEXT,
                posting_frequency TEXT,
                engagement_style TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_activity TIMESTAMP,
                total_posts INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0
            )
        ''')
        
        # Table for malicious agent specific attributes
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS malicious_agent_attributes (
                user_id TEXT PRIMARY KEY,
                agent_capabilities TEXT,
                target_topics TEXT,
                attack_strategies TEXT,
                success_rate REAL DEFAULT 0.0,
                total_attacks INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES managed_users (user_id)
            )
        ''')
        
        self.db.commit()
    
    def generate_regular_users(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate regular users (1:1:1 ratio from the three persona pools)"""
        
        print(f"👥 Generating {count} regular users (1:1:1 ratio)")
        
        # Calculate how many users per persona class
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
        
        # Shuffle the sequential list randomly
        random.shuffle(users)
        
        # Persist to the database
        self._save_users_to_db(users)
        
        print(f"   ✅ Successfully generated and saved {len(users)} regular users")
        return users
    
    def generate_malicious_agents(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate malicious agents (sampled from the negative persona database)"""
        
        print(f"🦹 Generating {count} malicious agents")
        
        negative_personas = persona_loader.sample_personas("negative", count)
        
        agents = []
        for persona in negative_personas:
            agent = self._create_user_from_persona(persona, "malicious_agent")
            
            # Special attributes for malicious agents
            agent_capabilities = ["content_generation", "coordinated_posting", "harassment"]
            target_topics = persona.get("interests", [])
            attack_strategies = self._determine_attack_strategies(persona)
            
            agent.update({
                "agent_capabilities": agent_capabilities,
                "target_topics": target_topics,
                "attack_strategies": attack_strategies
            })
            
            agents.append(agent)
        
        # Persist to the database
        self._save_users_to_db(agents)
        self._save_malicious_attributes(agents)
        
        print(f"   ✅ Successfully generated and saved {len(agents)} malicious agents")
        return agents
    
    def _create_user_from_persona(self, persona_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Create a user record from persona data"""
        
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
            "engagement_style": self._determine_engagement_style(persona_data),
            "is_active": True,
            "last_activity": datetime.now(),
            "total_posts": 0,
            "total_comments": 0
        }
        
        return user
    
    def _generate_user_id(self, prefix: str = "user") -> str:
        """Generate a unique user ID"""
        import string
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        timestamp = datetime.now().strftime("%m%d%H%M")
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def _determine_activity_level(self, persona_data: Dict[str, Any]) -> str:
        """Determine activity level from persona data"""
        persona_type = persona_data.get("type", "neutral")
        personality_traits = persona_data.get("personality_traits", [])
        
        if persona_type == "positive":
            if any(trait in personality_traits for trait in ["Active", "Enthusiastic", "Energetic"]):
                return "high"
            else:
                return "medium"
        elif persona_type == "negative":
            if any(trait in personality_traits for trait in ["Aggressive", "Radical", "Destructive"]):
                return "very_high"
            else:
                return "high"
        else:  # neutral
            return "low"
    
    def _determine_posting_frequency(self, persona_data: Dict[str, Any]) -> str:
        """Determine posting frequency from persona data"""
        activity_level = self._determine_activity_level(persona_data)
        
        frequency_map = {
            "very_high": "multiple_daily",
            "high": "daily", 
            "medium": "weekly",
            "low": "monthly"
        }
        
        return frequency_map.get(activity_level, "weekly")
    
    def _determine_engagement_style(self, persona_data: Dict[str, Any]) -> str:
        """Determine engagement style from persona data"""
        persona_type = persona_data.get("type", "neutral")
        personality_traits = persona_data.get("personality_traits", [])
        
        if persona_type == "positive":
            if any(trait in personality_traits for trait in ["Supportive", "Helpful", "Kind"]):
                return "supportive"
            elif any(trait in personality_traits for trait in ["Rational", "Logical", "Analytical"]):
                return "analytical"
            else:
                return "encouraging"
        elif persona_type == "negative":
            if any(trait in personality_traits for trait in ["Aggressive", "Hostile"]):
                return "confrontational"
            elif any(trait in personality_traits for trait in ["Skeptical", "Critical"]):
                return "critical"
            else:
                return "disruptive"
        else:  # neutral
            return "observational"
    
    def _determine_attack_strategies(self, persona_data: Dict[str, Any]) -> List[str]:
        """Determine attack strategies based on persona traits"""
        personality_traits = persona_data.get("personality_traits", [])
        interests = persona_data.get("interests", [])
        
        strategies = []
        
        if any(trait in personality_traits for trait in ["Aggressive", "Hostile"]):
            strategies.append("direct_confrontation")
        if any(trait in personality_traits for trait in ["Manipulative", "Deceptive"]):
            strategies.append("misinformation_spreading")
        if any(trait in personality_traits for trait in ["Radical", "Extreme"]):
            strategies.append("extremist_content")
        if "Online Harassment" in interests:
            strategies.append("targeted_harassment")
        if "Extreme Politics" in interests:
            strategies.append("political_polarization")
        
        # Default strategy
        if not strategies:
            strategies = ["general_disruption"]
        
        return strategies
    
    def _save_users_to_db(self, users: List[Dict[str, Any]]):
        """Save user records to the database"""
        
        for user in users:
            self.cursor.execute('''
                INSERT OR REPLACE INTO managed_users (
                    user_id, user_type, persona_id, name, persona_type, profession,
                    age_range, education, region, personality_traits, interests,
                    creation_time, activity_level, posting_frequency, engagement_style,
                    is_active, last_activity, total_posts, total_comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user["user_id"], user["user_type"], user["persona_id"], user["name"],
                user["persona_type"], user["profession"], user["age_range"], user["education"],
                user["region"], json.dumps(user["personality_traits"]), json.dumps(user["interests"]),
                user["creation_time"], user["activity_level"], user["posting_frequency"],
                user["engagement_style"], user["is_active"], user["last_activity"],
                user["total_posts"], user["total_comments"]
            ))
        
        self.db.commit()
    
    def _save_malicious_attributes(self, agents: List[Dict[str, Any]]):
        """Save malicious agent-specific attributes"""
        
        for agent in agents:
            if agent["user_type"] == "malicious_agent":
                self.cursor.execute('''
                    INSERT OR REPLACE INTO malicious_agent_attributes (
                        user_id, agent_capabilities, target_topics, attack_strategies,
                        success_rate, total_attacks
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    agent["user_id"],
                    json.dumps(agent.get("agent_capabilities", [])),
                    json.dumps(agent.get("target_topics", [])),
                    json.dumps(agent.get("attack_strategies", [])),
                    0.0,  # Initial success rate
                    0     # Initial attack count
                ))
        
        self.db.commit()
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Return aggregated user statistics"""
        
        # Basic statistics
        self.cursor.execute('SELECT COUNT(*) FROM managed_users')
        total_users = self.cursor.fetchone()[0]
        
        # Statistics by user class
        self.cursor.execute('SELECT user_type, COUNT(*) FROM managed_users GROUP BY user_type')
        by_type = dict(self.cursor.fetchall())
        
        # Statistics by persona class
        self.cursor.execute('SELECT persona_type, COUNT(*) FROM managed_users GROUP BY persona_type')
        by_persona_type = dict(self.cursor.fetchall())
        
        # Statistics by activity level
        self.cursor.execute('SELECT activity_level, COUNT(*) FROM managed_users GROUP BY activity_level')
        by_activity_level = dict(self.cursor.fetchall())
        
        # Top 10 professions statistics
        self.cursor.execute('SELECT profession, COUNT(*) FROM managed_users GROUP BY profession ORDER BY COUNT(*) DESC LIMIT 10')
        top_professions = self.cursor.fetchall()
        
        return {
            "total_users": total_users,
            "by_type": by_type,
            "by_persona_type": by_persona_type,
            "by_activity_level": by_activity_level,
            "top_professions": top_professions
        }
    
    def get_users_by_type(self, user_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get users filtered by class type"""
        
        self.cursor.execute('''
            SELECT * FROM managed_users 
            WHERE user_type = ? AND is_active = TRUE 
            ORDER BY creation_time DESC 
            LIMIT ?
        ''', (user_type, limit))
        
        columns = [description[0] for description in self.cursor.description]
        users = []
        
        for row in self.cursor.fetchall():
            user = dict(zip(columns, row))
            # Parse JSON fields
            user["personality_traits"] = json.loads(user["personality_traits"])
            user["interests"] = json.loads(user["interests"])
            users.append(user)
        
        return users
    
    def clear_all_users(self):
        """Clear all user data"""
        self.cursor.execute('DELETE FROM malicious_agent_attributes')
        self.cursor.execute('DELETE FROM managed_users')
        self.db.commit()
        print("🧹 All user data has been cleared")


if __name__ == "__main__":
    # Testing code
    import tempfile
    import os
    
    print("🧪 Testing the user management system")
    print("=" * 50)
    
    # createtemporarydatabase
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        conn = sqlite3.connect(temp_db.name)
        user_mgmt = UserManagementSystem(conn)
        
        # Generate regular users
        regular_users = user_mgmt.generate_regular_users(12)
        
        # Generate malicious agents
        malicious_agents = user_mgmt.generate_malicious_agents(4)
        
        # Display statistics
        stats = user_mgmt.get_user_stats()
        print(f"\n📊 User statistics:")
        print(f"   Total users: {stats['total_users']}")
        print(f"   By user type: {stats['by_type']}")
        print(f"   By persona type: {stats['by_persona_type']}")
        print(f"   By activity level: {stats['by_activity_level']}")
        print(f"   Top professions: {stats['top_professions'][:5]}")
        
        # Show sample users
        print(f"\n👥 Sample regular users:")
        sample_users = user_mgmt.get_users_by_type("regular_user", 3)
        for i, user in enumerate(sample_users, 1):
            print(f"   {i}. {user['name']} ({user['persona_type']}) - {user['profession']}")
        
        print(f"\n🦹 Sample malicious agents:")
        sample_agents = user_mgmt.get_users_by_type("malicious_agent", 2)
        for i, agent in enumerate(sample_agents, 1):
            print(f"   {i}. {agent['name']} - {agent['profession']}")
        
        conn.close()
        
    finally:
        os.unlink(temp_db.name)
