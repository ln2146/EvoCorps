import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import os
# Configuration
EXPERIMENT_NAME = 'third_party' # 'hybrid', 'community_based', 'third_party', 'no_fact_check'

DATABASE_PATH = f'{EXPERIMENT_NAME}.db'

# create output directory if it doesn't exist
OUTPUT_DIR = Path(f'plots/{EXPERIMENT_NAME}')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    

def load_data(db_path):
    """Load data from SQLite database."""
    conn = sqlite3.connect(db_path)
    spread_metrics = pd.read_sql_query('SELECT * FROM spread_metrics', conn)
    posts = pd.read_sql_query('SELECT * FROM posts', conn)
    conn.close()
    
    # Calculate total interactions
    spread_metrics['total_interactions'] = (
        spread_metrics['views'] + 
        spread_metrics['num_likes'] + 
        spread_metrics['num_comments'] + 
        spread_metrics['num_shares']
    )
    
    return spread_metrics, posts

def plot_metrics_over_time(merged_data):
    """Create subplot grid showing different metrics over time."""
    # Filter for first 40 time steps
    merged_data = merged_data[merged_data['time_step'] <= 40]
    
    fig, axes = plt.subplots(3, 2, figsize=(20, 15))
    axes = axes.flatten()

    metrics = ['total_interactions', 'views', 'num_likes', 'num_comments', 'num_shares', 'num_flags']
    titles = ['Total Interactions', 'Views', 'Likes', 'Comments', 'Shares', 'Flags']

    for i, (metric, title) in enumerate(zip(metrics, titles)):
        avg_data = merged_data.groupby(['time_step', 'news_type'])[metric].mean().reset_index()
        
        for news_type in avg_data['news_type'].unique():
            if pd.notna(news_type):
                type_data = avg_data[avg_data['news_type'] == news_type]
                axes[i].plot(type_data['time_step'], type_data[metric], 
                         marker='o', linewidth=2, label=f'{news_type}')
        
        axes[i].set_title(f'Average {title} Over Time - {EXPERIMENT_NAME.replace("_", " ").title()}', fontsize=16)
        axes[i].set_xlabel('Time Step', fontsize=14)
        axes[i].set_ylabel(f'Average {title}', fontsize=14)
        axes[i].grid(True, alpha=0.3)
        axes[i].legend(fontsize=12)
        # Set x-axis limits with some padding
        axes[i].set_xlim(-1, 41)

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.suptitle(f'Average Spread Metrics for Fake vs Real News Over Time\n{EXPERIMENT_NAME.replace("_", " ").title()} Experiment', fontsize=20)
    plt.savefig(OUTPUT_DIR / 'metrics_over_time.pdf')
    plt.close()

def plot_interactions_heatmap(spread_metrics, posts):
    """Create heatmap of total interactions."""
    # Filter for first 40 time steps
    spread_metrics = spread_metrics[spread_metrics['time_step'] <= 40]
    
    plt.figure(figsize=(15, 10))
    post_to_news_type = posts[['post_id', 'news_type']].set_index('post_id')['news_type'].to_dict()

    heatmap_data = spread_metrics.pivot_table(
        index='post_id', 
        columns='time_step', 
        values='total_interactions',
        fill_value=0
    )

    post_totals = pd.DataFrame({
        'post_id': heatmap_data.sum(axis=1).index,
        'total_interactions': heatmap_data.sum(axis=1).values
    })
    post_totals['news_type'] = post_totals['post_id'].map(post_to_news_type)
    post_totals = post_totals.dropna(subset=['news_type'])

    sample_size = 15
    real_posts = post_totals[post_totals['news_type'] == 'real'].nlargest(sample_size, 'total_interactions')['post_id'].tolist()
    fake_posts = post_totals[post_totals['news_type'] == 'fake'].nlargest(sample_size, 'total_interactions')['post_id'].tolist()
    
    selected_posts = real_posts + fake_posts
    heatmap_data = heatmap_data.loc[selected_posts]

    sns.heatmap(heatmap_data, cmap='viridis', annot=False, fmt='.0f', linewidths=0.5)
    plt.title(f'Total Interactions Heatmap - {EXPERIMENT_NAME.replace("_", " ").title()} Experiment\n(Equal Sample of Real and Fake News)', fontsize=16)
    plt.xlabel('Time Step', fontsize=14)
    plt.ylabel('Post ID', fontsize=14)

    plt.xticks(np.arange(0.5, len(heatmap_data.columns), 1), range(len(heatmap_data.columns)))
    
    y_labels = [f"{post_id} ({post_to_news_type.get(post_id, 'Unknown')})" for post_id in heatmap_data.index]
    plt.yticks(np.arange(0.5, len(heatmap_data.index), 1), y_labels)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'interactions_heatmap.pdf')
    plt.close()

def plot_cumulative_growth(merged_data):
    """Plot cumulative growth of average interactions."""
    # Filter for first 40 time steps
    merged_data = merged_data[merged_data['time_step'] <= 40]
    
    plt.figure(figsize=(15, 8))
    cumulative_data = merged_data.groupby(['time_step', 'news_type'])['total_interactions'].mean().reset_index()

    for news_type in cumulative_data['news_type'].unique():
        if pd.notna(news_type):
            type_data = cumulative_data[cumulative_data['news_type'] == news_type].sort_values('time_step')
            plt.plot(type_data['time_step'], type_data['total_interactions'].cumsum(), 
                     marker='o', linewidth=2, label=f'{news_type}')

    plt.title(f'Cumulative Growth of Average Total Interactions by News Type\n{EXPERIMENT_NAME.replace("_", " ").title()} Experiment', fontsize=16)
    plt.xlabel('Time Step', fontsize=14)
    plt.ylabel('Cumulative Average Total Interactions', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    # Set x-axis limits with some padding
    plt.xlim(-1, 41)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'cumulative_growth.pdf')
    plt.close()

def plot_final_metrics_comparison(merged_data, metrics):
    """Create bar chart comparing final metrics."""
    # Use time step 40 as the final step
    final_data = merged_data[merged_data['time_step'] == 40]

    plt.figure(figsize=(15, 8))
    final_avg = final_data.groupby('news_type')[metrics].mean().reset_index()
    final_avg_melted = pd.melt(final_avg, id_vars=['news_type'], value_vars=metrics, 
                              var_name='Metric', value_name='Average Value')

    sns.barplot(x='news_type', y='Average Value', hue='Metric', data=final_avg_melted)
    plt.title(f'Final Average Metrics by News Type\n{EXPERIMENT_NAME.replace("_", " ").title()} Experiment', fontsize=16)
    plt.xlabel('News Type', fontsize=14)
    plt.ylabel('Average Value', fontsize=14)
    plt.xticks(rotation=45)
    plt.legend(title='Metric', fontsize=12)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'final_metrics_comparison.pdf')
    plt.close()

def main():
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Set the style for all plots
    plt.style.use('ggplot')
    
    # Load data
    spread_metrics, posts = load_data(DATABASE_PATH)
    
    # Merge data
    merged_data = spread_metrics.merge(
        posts[['post_id', 'is_news', 'news_type', 'status']], 
        on='post_id', 
        how='left'
    )
    
    # Define metrics
    metrics = ['total_interactions', 'views', 'num_likes', 'num_comments', 'num_shares', 'num_flags']
    
    # Generate all plots
    plot_metrics_over_time(merged_data)
    plot_interactions_heatmap(spread_metrics, posts)
    plot_cumulative_growth(merged_data)
    plot_final_metrics_comparison(merged_data, metrics)

if __name__ == "__main__":
    main()