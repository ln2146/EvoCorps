#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Negative News Heat Analysis System

Features:
1. Load real-time heat data (realtime_negative_news_heat.json)
2. Display heat trend charts (comments count)
3. Export CSV data
"""

import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class NegativeNewsHeatAnalyzer:
    """Analyzer for negative news heat data"""
    
    def __init__(self, data_file='realtime_negative_news_heat.json'):
        """Initialize the analyzer"""
        self.data_file = Path(__file__).parent / data_file
        self.data = None
        self.output_dir = Path(__file__).parent / 'analysis_results'
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create the output directory
        self.output_dir.mkdir(exist_ok=True)
    
    def load_data(self):
        """Load heat data"""
        try:
            if not self.data_file.exists():
                print(f"❌ Data file missing: {self.data_file}")
                print(f"💡 Tip: Please run the simulation system to generate data first")
                return False
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            print(f"✅ Successfully loaded data file: {self.data_file}")
            print(f"📊 Data overview:")
            print(f"   - Negative news post count: {len(self.data.get('posts', {}))}")
            print(f"   - Tracked timesteps: {self.data.get('total_timesteps', 0)}")
            print(f"   - Last update: {self.data.get('last_update', 'N/A')}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON format error: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            return False
    
    def show_heatmap(self):
        """Display the heat curve chart (comments count)"""
        if not self.data or not self.data.get('posts'):
            print("⚠️ No data available, skipping heat curve generation")
            return
        
        print("\n📈 Generating heat curve chart...")
        
        posts = self.data['posts']
        
        # Create a single chart showing only comment counts
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.suptitle('Negative News Comments Trend', 
                     fontsize=16, fontweight='bold')
        
        # Plot comment count trend for each negative news post
        for post_id, post_data in posts.items():
            timesteps = [record['timestep'] for record in post_data['history']]
            comments = [record['comments'] for record in post_data['history']]
            
            # Retrieve extremism label
            extremism = post_data['info'].get('extremism_level', 'N/A')
            label = f"{post_id} (Extremism: {extremism})"
            
            ax.plot(timesteps, comments, marker='o', label=label, 
                   linewidth=2.5, markersize=6)
        
        ax.set_xlabel('Time Step', fontsize=13)
        ax.set_ylabel('Comments', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        # Display the chart
        print("✅ Displaying heat curve chart...")
        print("💡 Close the chart window to continue")
        plt.show()
    
    def show_growth_per_timestep(self):
        """Generate and display the comment increment chart per timestep."""
        if not self.data or not self.data.get('posts'):
            print("⚠️ No data available, cannot generate increment chart")
            return

        print("\n📈 Generating comment increment chart per timestep...")

        posts = self.data['posts']

        fig, ax = plt.subplots(figsize=(12, 8))
        fig.suptitle('Increment of Comments per Timestep',
                     fontsize=16, fontweight='bold')

        for post_id, post_data in posts.items():
            history = post_data.get('history', [])
            if not history:
                continue

            timesteps = [rec['timestep'] for rec in history]
            comments = [rec['comments'] for rec in history]
            # Include the initial injection step as growth from a zero baseline
            increments = [comments[0]] + [comments[i] - comments[i - 1] for i in range(1, len(comments))]
            inc_steps = timesteps

            extremism = post_data['info'].get('extremism_level', 'N/A')
            label = f"{post_id} (Extremism: {extremism})"
            ax.plot(inc_steps, increments, marker='o', label=label, linewidth=2.0, markersize=6)

        ax.set_xlabel('Time Step', fontsize=13)
        ax.set_ylabel('ΔComments', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        print("✅ Displaying increment chart... Close the window to continue")
        plt.show()

    def print_statistics(self):
        """Print statistics to the terminal (comments only)"""
        if not self.data or not self.data.get('posts'):
            print("⚠️ No data available")
            return
        
        print("\n📊 Negative news heat statistics (comments)")
        print("="*70)
        
        posts = self.data['posts']
        
        for post_id, post_data in posts.items():
            history = post_data['history']
            if not history:
                continue
            
            comments_list = [r['comments'] for r in history]
            
            print(f"\n🔖 {post_id}:")
            print(f"   Extremism level: {post_data['info'].get('extremism_level', 'N/A')}")
            print(f"   Injection timestep: {post_data['info'].get('injection_timestep', 'N/A')}")
            print(f"   Tracked timesteps: {len(history)}")
            print(f"   Comments: {comments_list[0]} → {comments_list[-1]} (increase +{comments_list[-1] - comments_list[0]})")
            print(f"   Max comments: {max(comments_list)}")
            print(f"   Average comments: {sum(comments_list)/len(comments_list):.1f}")
        
        print("="*70)
    
    def export_csv(self):
        """Export CSV data (comments only)"""
        if not self.data or not self.data.get('posts'):
            print("⚠️ No data available, skipping CSV export")
            return

        print("\n📁 Exporting CSV data...")
        
        posts = self.data['posts']
        
        # Export detailed data (one CSV per post)
        for post_id, post_data in posts.items():
            csv_path = self.output_dir / f'comments_{post_id}_{self.timestamp}.csv'
            
            with open(csv_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write('TimeStep,Comments\n')
                f.write('TimeStep,Comments\n')
                
                # Write data
                for record in post_data['history']:
                    f.write(f"{record['timestep']},{record['comments']}\n")
            
            print(f"  ✅ {post_id} → {csv_path}")
        
        # Export summary data (all posts in one CSV)
        summary_csv_path = self.output_dir / f'comments_summary_{self.timestamp}.csv'
        
        with open(summary_csv_path, 'w', encoding='utf-8') as f:
            # Build the header
            header = ['TimeStep']
            for post_id in posts.keys():
                header.append(f'{post_id}_comments')
            f.write(','.join(header) + '\n')
            
            # Determine maximum timestep count
            max_timesteps = max(
                len(post_data['history']) 
                for post_data in posts.values()
            )
            
            # Write data
            for step in range(max_timesteps):
                row = [str(step + 1)]
                
                for post_id, post_data in posts.items():
                    if step < len(post_data['history']):
                        record = post_data['history'][step]
                        row.append(str(record['comments']))
                    else:
                        row.append('')
                
                f.write(','.join(row) + '\n')
        
        print(f"✅ Summary CSV saved: {summary_csv_path}")
    
    def run_analysis(self):
        """Execute the full analysis workflow"""
        print("\n" + "="*70)
        print("🚀 Negative News Heat Analysis System")
        print("="*70)
        
        # Load data
        if not self.load_data():
            print("\n❌ Analysis terminated: failed to load data")
            return
        
        # Print statistics
        self.print_statistics()
        
        # Export CSV data
        self.export_csv()
        
        # Display heat curve chart (last because it blocks)
        self.show_heatmap()
        
        # Display comment increment chart per timestep
        self.show_growth_per_timestep()
        
        print("\n" + "="*70)
        print("✅ Analysis complete! CSV files saved to:")
        print(f"   📁 {self.output_dir}")
        print("="*70 + "\n")


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════════════════╗
║     Negative News Heat Analysis System                ║
╚════════════════════════════════════════════════════════╝
    """)
    
    analyzer = NegativeNewsHeatAnalyzer()
    analyzer.run_analysis()


if __name__ == '__main__':
    main()
