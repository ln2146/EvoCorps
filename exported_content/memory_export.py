#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory Export - Export and analyze agent_memories table data
Query user memory data from agent_memories table with multiple export formats and analysis features
"""

import sqlite3
import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

class AgentMemoryExporter:
    """Agent Memory Data Exporter"""
    
    def __init__(self, db_path: str = "./database/simulation.db"):
        """
        Initialize exporter
        
        Args:
            db_path: Database file path
        """
        self.db_path = db_path
        self.output_dir = "agent_memory_exports"
        
        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def connect_database(self) -> sqlite3.Connection:
        """Connect to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Make query results accessible by column name
            return conn
        except sqlite3.Error as e:
            print(f"Database connection failed: {e}")
            raise
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory data statistics"""
        conn = self.connect_database()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Basic statistics
            cursor.execute("SELECT COUNT(*) FROM agent_memories")
            stats["total_memories"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM agent_memories")
            stats["unique_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT memory_type) FROM agent_memories")
            stats["memory_types"] = cursor.fetchone()[0]
            
            # Group by memory type
            cursor.execute("""
                SELECT memory_type, COUNT(*) as count, AVG(importance_score) as avg_importance
                FROM agent_memories 
                GROUP BY memory_type
                ORDER BY count DESC
            """)
            stats["by_memory_type"] = [dict(row) for row in cursor.fetchall()]
            
            # Group by user
            cursor.execute("""
                SELECT user_id, COUNT(*) as memory_count, 
                       AVG(importance_score) as avg_importance,
                       AVG(decay_factor) as avg_decay
                FROM agent_memories 
                GROUP BY user_id
                ORDER BY memory_count DESC
                LIMIT 10
            """)
            stats["top_users_by_memory_count"] = [dict(row) for row in cursor.fetchall()]
            
            # Importance statistics
            cursor.execute("""
                SELECT 
                    MIN(importance_score) as min_importance,
                    MAX(importance_score) as max_importance,
                    AVG(importance_score) as avg_importance
                FROM agent_memories
                WHERE importance_score IS NOT NULL
            """)
            importance_stats = cursor.fetchone()
            if importance_stats:
                stats["importance_statistics"] = dict(importance_stats)
            
            # Time statistics
            cursor.execute("""
                SELECT 
                    MIN(created_at) as earliest_memory,
                    MAX(created_at) as latest_memory,
                    COUNT(*) as total_count
                FROM agent_memories
            """)
            time_stats = cursor.fetchone()
            if time_stats:
                stats["time_statistics"] = dict(time_stats)
            
            return stats
            
        finally:
            conn.close()
    
    def export_all_memories(self, format: str = "json", limit: Optional[int] = None) -> str:
        """
        Export all memory data
        
        Args:
            format: Export format ('json', 'csv', 'excel')
            limit: Limit export count, None means export all
            
        Returns:
            Export file path
        """
        conn = self.connect_database()
        cursor = conn.cursor()
        
        try:
            # Build query
            query = """
                SELECT 
                    memory_id, user_id, memory_type, content, 
                    importance_score, created_at, last_accessed, decay_factor
                FROM agent_memories
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            memories = [dict(row) for row in cursor.fetchall()]
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"agent_memories_{timestamp}"
            
            if format.lower() == "json":
                filename = f"{base_filename}.json"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False, default=str)
                    
            elif format.lower() == "csv":
                filename = f"{base_filename}.csv"
                filepath = os.path.join(self.output_dir, filename)
                
                if memories:
                    fieldnames = memories[0].keys()
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(memories)
                        
            elif format.lower() == "excel":
                filename = f"{base_filename}.xlsx"
                filepath = os.path.join(self.output_dir, filename)
                
                df = pd.DataFrame(memories)
                df.to_excel(filepath, index=False)
                
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            print(f"Exported {len(memories)} memory records to: {filepath}")
            return filepath
            
        finally:
            conn.close()
    
    def export_memories_by_user(self, user_id: str, format: str = "json") -> str:
        """
        Export memory data by user
        
        Args:
            user_id: User ID
            format: Export format
            
        Returns:
            Export file path
        """
        conn = self.connect_database()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    memory_id, user_id, memory_type, content, 
                    importance_score, created_at, last_accessed, decay_factor
                FROM agent_memories
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            memories = [dict(row) for row in cursor.fetchall()]
            
            if not memories:
                print(f"No memory data found for user {user_id}")
                return None
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_user_id = user_id.replace("-", "_")
            filename = f"memories_{safe_user_id}_{timestamp}.{format}"
            filepath = os.path.join(self.output_dir, filename)
            
            if format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == "csv":
                if memories:
                    fieldnames = memories[0].keys()
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(memories)
            
            print(f"Exported {len(memories)} memory records for user {user_id} to: {filepath}")
            return filepath
            
        finally:
            conn.close()
    
    def export_memories_by_type(self, memory_type: str, format: str = "json") -> str:
        """
        Export data by memory type
        
        Args:
            memory_type: Memory type
            format: Export format
            
        Returns:
            Export file path
        """
        conn = self.connect_database()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    memory_id, user_id, memory_type, content, 
                    importance_score, created_at, last_accessed, decay_factor
                FROM agent_memories
                WHERE memory_type = ?
                ORDER BY importance_score DESC, created_at DESC
            """, (memory_type,))
            
            memories = [dict(row) for row in cursor.fetchall()]
            
            if not memories:
                print(f"No data found for memory type {memory_type}")
                return None
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_type = memory_type.replace(" ", "_").replace("-", "_")
            filename = f"memories_type_{safe_type}_{timestamp}.{format}"
            filepath = os.path.join(self.output_dir, filename)
            
            if format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == "csv":
                if memories:
                    fieldnames = memories[0].keys()
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(memories)
            
            print(f"Exported {len(memories)} records for memory type {memory_type} to: {filepath}")
            return filepath
            
        finally:
            conn.close()
    
    def export_high_importance_memories(self, min_importance: float = 0.8, format: str = "json") -> str:
        """
        Export high importance memories
        
        Args:
            min_importance: Minimum importance threshold
            format: Export format
            
        Returns:
            Export file path
        """
        conn = self.connect_database()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    memory_id, user_id, memory_type, content, 
                    importance_score, created_at, last_accessed, decay_factor
                FROM agent_memories
                WHERE importance_score >= ?
                ORDER BY importance_score DESC, created_at DESC
            """, (min_importance,))
            
            memories = [dict(row) for row in cursor.fetchall()]
            
            if not memories:
                print(f"No memories found with importance >= {min_importance}")
                return None
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"high_importance_memories_{min_importance}_{timestamp}.{format}"
            filepath = os.path.join(self.output_dir, filename)
            
            if format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == "csv":
                if memories:
                    fieldnames = memories[0].keys()
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(memories)
            
            print(f"Exported {len(memories)} high importance memory records to: {filepath}")
            return filepath
            
        finally:
            conn.close()
    
    def generate_memory_report(self) -> str:
        """Generate memory analysis report"""
        stats = self.get_memory_statistics()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"memory_analysis_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Agent Memory Analysis Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Basic statistics
            f.write("Basic Statistics:\n")
            f.write(f"   Total memories: {stats['total_memories']}\n")
            f.write(f"   Unique users: {stats['unique_users']}\n")
            f.write(f"   Memory types: {stats['memory_types']}\n\n")
            
            # By type statistics
            f.write("Memory Type Distribution:\n")
            for item in stats['by_memory_type']:
                avg_imp = item['avg_importance'] if item['avg_importance'] else 0
                f.write(f"   {item['memory_type']}: {item['count']} records (avg importance: {avg_imp:.2f})\n")
            f.write("\n")
            
            # Top users
            f.write("Top Users by Memory Count:\n")
            for item in stats['top_users_by_memory_count']:
                avg_imp = item['avg_importance'] if item['avg_importance'] else 0
                avg_decay = item['avg_decay'] if item['avg_decay'] else 0
                f.write(f"   {item['user_id']}: {item['memory_count']} memories ")
                f.write(f"(avg importance: {avg_imp:.2f}, avg decay: {avg_decay:.2f})\n")
            f.write("\n")
            
            # Importance statistics
            if 'importance_statistics' in stats:
                imp_stats = stats['importance_statistics']
                f.write("Importance Statistics:\n")
                f.write(f"   Min importance: {imp_stats['min_importance']:.3f}\n")
                f.write(f"   Max importance: {imp_stats['max_importance']:.3f}\n")
                f.write(f"   Avg importance: {imp_stats['avg_importance']:.3f}\n\n")
            
            # Time statistics
            if 'time_statistics' in stats:
                time_stats = stats['time_statistics']
                f.write("Time Statistics:\n")
                f.write(f"   Earliest memory: {time_stats['earliest_memory']}\n")
                f.write(f"   Latest memory: {time_stats['latest_memory']}\n\n")
        
        print(f"Generated memory analysis report: {report_file}")
        return report_file

def main():
    """Main function - demonstrate various export features"""
    print("Agent Memory Export Tool")
    print("=" * 50)
    
    try:
        exporter = AgentMemoryExporter()
        
        # Check if table exists first
        conn = exporter.connect_database()
        cursor = conn.cursor()
        query = '''
            SELECT memory_id, content, memory_type, importance_score, created_at, decay_factor
            FROM agent_memories
            WHERE user_id = ? 
            AND importance_score * decay_factor >= ?
            AND memory_type = ?
            ORDER BY importance_score * decay_factor DESC 
            LIMIT ?
        '''
        
        cursor.execute(query, (
            "user-d5b2a6",
            0.7,
            "interaction",
            10
        ))

        rows = cursor.fetchall()
        for row in rows:
            print(tuple(row))   # Print as tuple

        # cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_memories'")
        # table_exists = cursor.fetchone() is not None
        # conn.close()
        
        # if not table_exists:
        #     print("agent_memories table not found in database")
        #     print("The table might not have been created yet or the database path is incorrect")
        #     return
        
        # # Generate statistics report
        print("\n1. Generating memory analysis report...")
        exporter.generate_memory_report()
        
        # Export all memory data (JSON format)
        print("\n2. Exporting all memory data...")
        exporter.export_all_memories(format="json", limit=1000)
        
        # Export CSV format
        print("\n3. Exporting CSV format...")
        exporter.export_all_memories(format="csv", limit=500)
        
        # Export high importance memories
        print("\n4. Exporting high importance memories...")
        exporter.export_high_importance_memories(min_importance=0.7)
        
        # Get and display statistics
        print("\n5. Displaying statistics...")
        stats = exporter.get_memory_statistics()
        print(f"   Total memories: {stats['total_memories']}")
        print(f"   Unique users: {stats['unique_users']}")
        print(f"   Memory types: {stats['memory_types']}")
        
        if stats['by_memory_type']:
            print("   Main memory types:")
            for item in stats['by_memory_type'][:5]:
                print(f"      {item['memory_type']}: {item['count']} records")
        
        print(f"\nAll export tasks completed!")
        print(f"Files saved in: {exporter.output_dir}/")
        
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
