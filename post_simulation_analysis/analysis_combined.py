import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import os
from matplotlib.colors import LinearSegmentedColormap
# from pySankey import sankey

# Configuration
EXPERIMENT_NAMES = ['hybrid', 'community_based', 'third_party', 'no_fact_check']

EXPERIMENT_COLORS = {
    'hybrid': '#1f77b4',        # A soft blue
    'community_based': '#2ca02c', # A vibrant green
    'third_party': '#ff7f0e',   # A warm orange
    'no_fact_check': '#d62728'   # A bold red
}

# create output directory if it doesn't exist
OUTPUT_DIR = Path('plots/comparison')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    
def load_data(experiment_name):
    """Load data from SQLite database for a specific experiment."""
    db_path = f'{experiment_name}.db'
    conn = sqlite3.connect(db_path)
    spread_metrics = pd.read_sql_query('SELECT * FROM spread_metrics', conn)
    posts = pd.read_sql_query('SELECT * FROM posts', conn)
    conn.close()
    
    # Calculate total interactions
    spread_metrics['total_interactions'] = (
        # spread_metrics['views'] + 
        spread_metrics['num_likes'] + 
        spread_metrics['num_comments'] + 
        spread_metrics['num_shares']
    )
    
    # Add experiment name column
    spread_metrics['experiment'] = experiment_name
    posts['experiment'] = experiment_name
    
    # Convert news_type values: "real" to "factual" and "fake" to "misinfo"
    posts['news_type'] = posts['news_type'].replace({'real': 'factual', 'fake': 'misinfo'})
    
    return spread_metrics, posts

def plot_metrics_over_time_comparison(all_data):
    """Create subplot grid showing different metrics over time for all experiments."""
    # Filter for first 40 time steps
    all_data = all_data[all_data['time_step'] <= 40]
    
    # Create a 4 x 1 grid of subplots, one for each experiment
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharex=True, sharey=True)
    axes = axes.flatten()
    
    # Define blue and yellow colors
    colors = {
        'factual': '#1f77b4',  # Blue
        'misinfo': '#ff7f0e'   # Orange
    }
    
    metric = 'total_interactions'
    
    # Define experiment titles (more readable versions of the experiment names)
    experiment_titles = {
        'hybrid': 'Hybrid Approach',
        'community_based': 'Community-Based',
        'third_party': 'Third-Party',
        'no_fact_check': 'No Fact-Checking'
    }
    
    FONT_SIZE = 22
    
    for i, experiment in enumerate(EXPERIMENT_NAMES):
        # Filter data for this experiment
        exp_data = all_data[all_data['experiment'] == experiment]
        
        # Plot each news type
        for news_type in ['factual', 'misinfo']:
            news_data = exp_data[exp_data['news_type'] == news_type]
            avg_data = news_data.groupby('time_step')[metric].mean().reset_index()
            
            if not avg_data.empty:
                linestyle = '-'
                axes[i].plot(avg_data['time_step'], avg_data[metric], 
                         marker='o', markersize=4, linewidth=2.5, 
                         color=colors[news_type], linestyle=linestyle,
                         label=f"{news_type.title()}")
                
                # Add light shaded area under the curve
                axes[i].fill_between(avg_data['time_step'], 0, avg_data[metric], 
                                 alpha=0.1, color=colors[news_type])
        
        # Add title to each subplot
        axes[i].set_title(experiment_titles[experiment], fontsize=FONT_SIZE, pad=10)
        
        # x-axis fontsize
        axes[i].xaxis.set_tick_params(labelsize=FONT_SIZE-7)
        # y-axis fontsize
        axes[i].yaxis.set_tick_params(labelsize=FONT_SIZE-7)
        
        # Style the subplot
        axes[i].set_xlabel('Time Step', fontsize=FONT_SIZE)
        axes[0].set_ylabel('Average Total Interactions', fontsize=FONT_SIZE-3)
        axes[i].grid(True, alpha=0.3, linestyle='--')
        axes[i].legend(fontsize=FONT_SIZE, framealpha=0.7)
        axes[i].set_xlim(-1, 41)
        
        # Add a light background color
        axes[i].set_facecolor('#f8f9fa')
    
    # Add a common legend at the bottom
    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=FONT_SIZE, 
               frameon=True, framealpha=0.8, bbox_to_anchor=(0.5, -0.08))
    
    # Remove individual legends
    for ax in axes:
        ax.get_legend().remove()
    
    # Remove the figure border
    fig.patch.set_edgecolor('none')
    
    plt.tight_layout(rect=[0, 0.07, 1, 0.95])
    
    plt.savefig(OUTPUT_DIR / 'metrics_over_time_comparison.pdf', dpi=300, bbox_inches='tight')
    plt.close()

def plot_cumulative_growth_comparison(all_data):
    """Plot cumulative growth of average interactions for all experiments."""
    # Filter for first 40 time steps
    all_data = all_data[all_data['time_step'] <= 40]
    
    # Create a figure with two subplots stacked vertically
    fig, axes = plt.subplots(2, 1, figsize=(10, 12), sharey=False)  
    
    # Add a main title for the entire figure
    fig.suptitle('Cumulative Growth of Interactions by Content Type', fontsize=18, y=0.98)
    
    # Dictionary to store max y-values for each news type to determine common y-scale
    max_y_values = {}
    
    # First pass: calculate all cumulative data to find the maximum y-value
    for news_type in ['factual', 'misinfo']:
        max_y_values[news_type] = 0
        for experiment in EXPERIMENT_NAMES:
            # Filter data for this experiment and news type
            filtered_data = all_data[(all_data['experiment'] == experiment) & 
                                    (all_data['news_type'] == news_type)]
            
            if not filtered_data.empty:
                # Calculate cumulative data
                cumulative_data = filtered_data.groupby('time_step')['total_interactions'].mean().reset_index()
                cumulative_data = cumulative_data.sort_values('time_step')
                
                # Update max y-value
                max_y = cumulative_data['total_interactions'].cumsum().max()
                max_y_values[news_type] = max(max_y_values[news_type], max_y)
    
    # Improved titles for each news type
    news_type_titles = {
        'factual': 'Factual Content (Legitimate News)',
        'misinfo': 'Misinformation Content (Fake News)'
    }
    
    # Improved experiment labels
    experiment_labels = {
        'hybrid': 'Hybrid Approach',
        'community_based': 'Community Based',
        'third_party': 'Third Party',
        'no_fact_check': 'No Fact Check'
    }
    
    # Second pass: create the actual plots
    for i, news_type in enumerate(['factual', 'misinfo']):
        ax = axes[i]
        
        # Plot each experiment for this news type
        for experiment in EXPERIMENT_NAMES:
            # Filter data for this experiment and news type
            filtered_data = all_data[(all_data['experiment'] == experiment) & 
                                    (all_data['news_type'] == news_type)]
            
            if not filtered_data.empty:
                # Calculate cumulative data
                cumulative_data = filtered_data.groupby('time_step')['total_interactions'].mean().reset_index()
                cumulative_data = cumulative_data.sort_values('time_step')
                
                # Plot the line
                ax.plot(
                    cumulative_data['time_step'], 
                    cumulative_data['total_interactions'].cumsum(),
                    marker='o', 
                    markersize=4, 
                    linewidth=2,
                    color=EXPERIMENT_COLORS[experiment],
                    label=experiment_labels[experiment]
                )
                
                # Add a light background color
                ax.set_facecolor('#f8f9fa')
        
        # Add clear subplot title
        ax.set_title(f"{news_type_titles[news_type]}", fontsize=16, pad=10)
        
        # Add labels and grid
        ax.set_xlabel('Time Step', fontsize=14)
        ax.set_ylabel('Cumulative Average Total Interactions\n(Likes + Comments + Shares)', fontsize=14)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Set axis limits
        ax.set_xlim(-1, 41)
        ax.set_ylim(0, max_y_values[news_type] * 1.05)  # Add 5% padding to the top
        
        # Add legend with improved formatting
        legend = ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
        legend.get_frame().set_facecolor('#f8f9fa')
        legend.get_frame().set_edgecolor('#cccccc')
        
        # Add tick parameters
        ax.tick_params(axis='both', which='major', labelsize=12)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust rect to make space for the main title

    plt.savefig(OUTPUT_DIR / 'cumulative_growth_comparison.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'cumulative_growth_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

def plot_combined_interactions_heatmap(all_spread_metrics, all_posts):
    """Create combined heatmap of total interactions for all experiments."""
    # Filter for first 40 time steps
    all_spread_metrics = [metrics[metrics['time_step'] <= 40] for metrics in all_spread_metrics]
    
    fig, axes = plt.subplots(1, len(EXPERIMENT_NAMES), figsize=(18, 5), sharey=True)
    
    # Create a consistent order for y-axis labels
    consistent_labels = [f"factual-{i+1}" for i in range(10)] + [f"misinfo-{i+1}" for i in range(10)]
    
    # Find global min and max values across all experiments
    all_values = []
    for idx, experiment in enumerate(EXPERIMENT_NAMES):
        spread_metrics = all_spread_metrics[idx]
        posts = all_posts[idx]
        
        post_to_news_type = posts[['post_id', 'news_type']].set_index('post_id')['news_type'].to_dict()

        # Group time steps into bins of 5
        spread_metrics['time_bin'] = (spread_metrics['time_step'] // 5) * 5
        
        # Aggregate interactions within each time bin
        binned_metrics = spread_metrics.groupby(['post_id', 'time_bin'])['total_interactions'].mean().reset_index()
        all_values.extend(binned_metrics['total_interactions'].values)
    
    vmin, vmax = min(all_values), max(all_values)
    
    # Create a custom colormap with fewer, more distinct colors
    colors = ['#000044', '#0066CC', '#66CCFF', '#FFFF00', '#FF6600', '#FF0000']
    n_bins = 256
    custom_cmap = LinearSegmentedColormap.from_list("custom", colors, N=n_bins)
    
    for idx, experiment in enumerate(EXPERIMENT_NAMES):
        spread_metrics = all_spread_metrics[idx]
        posts = all_posts[idx]
        
        post_to_news_type = posts[['post_id', 'news_type']].set_index('post_id')['news_type'].to_dict()

        # Group time steps into bins of 5
        spread_metrics['time_bin'] = (spread_metrics['time_step'] // 5) * 5
        
        # Aggregate interactions within each time bin
        binned_metrics = spread_metrics.groupby(['post_id', 'time_bin'])['total_interactions'].mean().reset_index()
        
        heatmap_data = binned_metrics.pivot_table(
            index='post_id', 
            columns='time_bin', 
            values='total_interactions',
            fill_value=0
        )

        post_totals = pd.DataFrame({
            'post_id': heatmap_data.sum(axis=1).index,
            'total_interactions': heatmap_data.sum(axis=1).values
        })
        post_totals['news_type'] = post_totals['post_id'].map(post_to_news_type)
        post_totals = post_totals.dropna(subset=['news_type'])

        sample_size = 10
        # Get top posts for each type
        factual_posts = post_totals[post_totals['news_type'] == 'factual'].nlargest(sample_size, 'total_interactions')['post_id'].tolist()
        misinfo_posts = post_totals[post_totals['news_type'] == 'misinfo'].nlargest(sample_size, 'total_interactions')['post_id'].tolist()
        
        selected_posts = factual_posts + misinfo_posts
        heatmap_data = heatmap_data.loc[selected_posts]
        
        # Create index mapping with consistent order
        index_mapping = {}
        for i, post_id in enumerate(factual_posts):
            index_mapping[post_id] = f"factual-{i+1}"
        for i, post_id in enumerate(misinfo_posts):
            index_mapping[post_id] = f"misinfo-{i+1}"
        
        # Rename the index
        heatmap_data.index = [index_mapping[idx] for idx in heatmap_data.index]
        
        # Reorder the index to match consistent_labels
        heatmap_data = heatmap_data.reindex(consistent_labels)

        # Update the heatmap to use custom colormap
        sns.heatmap(heatmap_data, 
                   cmap=custom_cmap,
                   annot=False, 
                   fmt='.0f', 
                   linewidths=0.5, 
                   ax=axes[idx],
                   vmin=vmin,
                   vmax=vmax)
        
        if idx == 0:
            axes[idx].set_ylabel('Post Type', fontsize=16)
        else:
            axes[idx].set_ylabel('')
            
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])

    plt.savefig(OUTPUT_DIR / 'combined_interactions_heatmap.pdf')
    plt.close()

def plot_moderation_effectiveness_gap(all_data):
    """
    Plot the cumulative gap between factual and misinformation engagement 
    for different content moderation approaches.
    A positive gap means factual content received more engagement than misinformation.
    """
    # Filter for first 40 time steps
    all_data = all_data[all_data['time_step'] <= 40]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(9, 6))
    
    FONT_SIZE = 17
    
    # Dictionary to store calculated gaps for each experiment
    gaps_by_experiment = {}
    
    # Calculate gap for each experiment
    for experiment in EXPERIMENT_NAMES:
        # Get data for this experiment
        exp_data = all_data[all_data['experiment'] == experiment]
        
        # Calculate average interactions by time step and news type
        factual_data = exp_data[exp_data['news_type'] == 'factual'].groupby('time_step')['total_interactions'].mean().reset_index()
        misinfo_data = exp_data[exp_data['news_type'] == 'misinfo'].groupby('time_step')['total_interactions'].mean().reset_index()
        
        # Ensure we have data for all time steps (fill with zeros if needed)
        all_time_steps = pd.DataFrame({'time_step': range(41)})
        factual_data = all_time_steps.merge(factual_data, on='time_step', how='left').fillna(0)
        misinfo_data = all_time_steps.merge(misinfo_data, on='time_step', how='left').fillna(0)
        
        # Calculate cumulative sums
        factual_cumulative = factual_data['total_interactions'].cumsum()
        misinfo_cumulative = misinfo_data['total_interactions'].cumsum()
        
        # Calculate the gap (positive means factual content gets more engagement)
        engagement_gap = factual_cumulative - misinfo_cumulative
        
        # Store for plotting
        gaps_by_experiment[experiment] = engagement_gap
        
        # Plot the gap
        ax.plot(
            range(41),  # time steps 0-40
            engagement_gap,
            marker='o',
            markersize=4,
            linewidth=2.5,
            color=EXPERIMENT_COLORS[experiment],
            label=experiment.replace('_', ' ').title()
        )
    
    # Add horizontal line at y=0 (where factual and misinfo have equal engagement)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Equal Engagement')
    
    # Add labels and title
    ax.set_xlabel('Time Step', fontsize=FONT_SIZE)
    ax.set_ylabel('Cumulative Engagement Gap\n(Factual - Misinformation)', fontsize=FONT_SIZE)
    # ax.set_title('Effectiveness of Content Moderation Approaches\nin Promoting Factual Content', fontsize=FONT_SIZE)
    
    # Add explanatory text
    # ax.text(
    #     0.02, 0.02, 
    #     "Positive values: Factual content receives more engagement\nNegative values: Misinformation receives more engagement", 
    #     transform=ax.transAxes, 
    #     fontsize=12,
    #     bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray')
    # )
    
    # Style the plot
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(-1, 41)
    
    # tick fontsize
    ax.tick_params(axis='both', which='major', labelsize=FONT_SIZE, fontweight='bold')
    
    
    # Add legend
    legend = ax.legend(fontsize=FONT_SIZE, loc='best', framealpha=0.9)
    legend.get_frame().set_facecolor('#f8f9fa')
    legend.get_frame().set_edgecolor('#cccccc')
    
    # Set background
    ax.set_facecolor('#f8f9fa')
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig(OUTPUT_DIR / 'moderation_effectiveness_gap.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'moderation_effectiveness_gap.png', dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Set the style for all plots
    plt.style.use('ggplot')
    
    # Load data from all experiments
    all_spread_metrics = []
    all_posts = []
    
    for experiment in EXPERIMENT_NAMES:
        try:
            spread_metrics, posts = load_data(experiment)
            all_spread_metrics.append(spread_metrics)
            all_posts.append(posts)
            print(f"Loaded data for {experiment}")
        except Exception as e:
            print(f"Error loading data for {experiment}: {e}")
    
    # Combine all data
    combined_spread_metrics = pd.concat(all_spread_metrics, ignore_index=True)
    combined_posts = pd.concat(all_posts, ignore_index=True)
    
    # Merge data
    merged_data = combined_spread_metrics.merge(
        combined_posts[['post_id', 'is_news', 'news_type', 'status', 'experiment']], 
        on=['post_id', 'experiment'], 
        how='left'
    )
    
    # Generate comparison plots
    plot_metrics_over_time_comparison(merged_data)
    plot_cumulative_growth_comparison(merged_data)
    # plot_combined_interactions_heatmap(all_spread_metrics, all_posts)
    plot_moderation_effectiveness_gap(merged_data)

if __name__ == "__main__":
    main()