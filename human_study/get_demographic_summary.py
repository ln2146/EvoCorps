import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import os

def analyze_demographics(csv_path, output_file):
    """
    Analyze demographic data from CSV file and write summary to a text file
    
    Args:
        csv_path (str): Path to the demographic CSV data
        output_file (str): Path to save the summary text file
    """
    # Load the demographic data
    df = pd.read_csv(csv_path)
    
    # Create a directory for plots if it doesn't exist
    plots_dir = 'demographic_plots'
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
    
    with open(output_file, 'w') as f:
        # Write header
        f.write("# Demographic Summary of Study Participants\n\n")
        
        # Total number of participants
        f.write(f"## Overview\n\n")
        f.write(f"Total number of participants: {len(df)}\n\n")
        
        # Analyze each demographic category
        demographic_categories = {
            'age': 'Age Distribution',
            'gender': 'Gender Distribution',
            'religion': 'Religious Affiliation',
            'ethnic_group': 'Ethnic Group Distribution',
            'education': 'Education Level',
            'primary_language': 'Primary Language',
            'type_of_residence': 'Type of Residence',
            'income': 'Income Distribution',
            'political_stance': 'Political Stance'
        }
        
        for category, title in demographic_categories.items():
            f.write(f"## {title}\n\n")
            
            # Count occurrences of each value
            value_counts = df[category].value_counts().sort_values(ascending=False)
            total = len(df)
            
            # Create table of counts and percentages
            f.write("| Value | Count | Percentage |\n")
            f.write("|-------|-------|------------|\n")
            
            for value, count in value_counts.items():
                percentage = (count / total) * 100
                f.write(f"| {value} | {count} | {percentage:.2f}% |\n")
            
            f.write("\n")
            
            # Create and save plot for this category
            plt.figure(figsize=(12, 6))
            bars = plt.bar(value_counts.index, value_counts.values)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                         f'{height} ({(height/total)*100:.1f}%)',
                         ha='center', va='bottom', rotation=0)
            
            plt.title(f'{title}')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save plot
            plot_path = f"{plots_dir}/{category}_distribution.png"
            plt.savefig(plot_path)
            plt.close()
            
            f.write(f"![{title}]({plot_path})\n\n")
        
        # Additional cross-tabulation analyses
        f.write("## Demographic Cross-Tabulations\n\n")
        
        # Create a custom function to format DataFrames as markdown tables
        def dataframe_to_markdown(df):
            markdown = "| |" + "|".join(str(col) for col in df.columns) + "|\n"
            markdown += "|---|" + "|".join(["---"] * len(df.columns)) + "|\n"
            
            for idx, row in df.iterrows():
                markdown += f"| {idx} |" + "|".join(f"{val:.1f}" for val in row) + "|\n"
            
            return markdown

        # Gender vs Education
        f.write("### Gender vs Education\n\n")
        gender_edu = pd.crosstab(df['gender'], df['education'], normalize='index').round(2) * 100
        f.write(dataframe_to_markdown(gender_edu))
        f.write("\n\n")
        
        # Age vs Income
        f.write("### Age vs Income\n\n")
        age_income = pd.crosstab(df['age'], df['income'], normalize='index').round(2) * 100
        f.write(dataframe_to_markdown(age_income))
        f.write("\n\n")
        
        # Political Stance vs Education
        f.write("### Political Stance vs Education\n\n")
        political_edu = pd.crosstab(df['political_stance'], df['education'], normalize='index').round(2) * 100
        f.write(dataframe_to_markdown(political_edu))
        f.write("\n\n")
        
        # Ethnic Group vs Income
        f.write("### Ethnic Group vs Income\n\n")
        ethnic_income = pd.crosstab(df['ethnic_group'], df['income'], normalize='index').round(2) * 100
        f.write(dataframe_to_markdown(ethnic_income))
        f.write("\n\n")

        f.write("## Summary Insights\n\n")
        f.write("Based on the demographic data analysis:\n\n")
        
        # Age distribution insight
        most_common_age = df['age'].value_counts().idxmax()
        age_percentage = (df['age'].value_counts()[most_common_age] / len(df)) * 100
        f.write(f"- The most common age group is {most_common_age} ({age_percentage:.1f}% of participants)\n")
        
        # Gender distribution insight
        most_common_gender = df['gender'].value_counts().idxmax()
        gender_percentage = (df['gender'].value_counts()[most_common_gender] / len(df)) * 100
        f.write(f"- {most_common_gender}s make up {gender_percentage:.1f}% of the participant pool\n")
        
        # Education insight
        most_common_edu = df['education'].value_counts().idxmax()
        edu_percentage = (df['education'].value_counts()[most_common_edu] / len(df)) * 100
        f.write(f"- The most common education level is {most_common_edu} ({edu_percentage:.1f}%)\n")
        
        # Residence insight
        most_common_residence = df['type_of_residence'].value_counts().idxmax()
        residence_percentage = (df['type_of_residence'].value_counts()[most_common_residence] / len(df)) * 100
        f.write(f"- {most_common_residence} areas are where {residence_percentage:.1f}% of participants reside\n")
        
        # Political stance insight
        most_common_political = df['political_stance'].value_counts().idxmax()
        political_percentage = (df['political_stance'].value_counts()[most_common_political] / len(df)) * 100
        f.write(f"- The most common political stance is {most_common_political} ({political_percentage:.1f}%)\n")
        
        # Calculate diversity index for ethnic groups (Simpson's diversity index)
        ethnic_counts = df['ethnic_group'].value_counts()
        ethnic_proportions = ethnic_counts / ethnic_counts.sum()
        ethnic_diversity = 1 - sum(ethnic_proportions ** 2)
        f.write(f"- The ethnic diversity index of the sample is {ethnic_diversity:.2f} (0=homogeneous, 1=diverse)\n")

def plot_demographic_grid(csv_path, output_dir='demographic_plots'):
    """
    Create a grid of plots showing distributions for all demographic attributes
    
    Args:
        csv_path (str): Path to the demographic CSV data
        output_dir (str): Directory to save the output visualization
    
    Returns:
        str: Path to the saved visualization
    """
    # Load the demographic data
    df = pd.read_csv(csv_path)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Define demographic categories and their display titles
    demographic_categories = {
        'age': 'Age Distribution',
        'gender': 'Gender Distribution',
        'religion': 'Religious Affiliation',
        'ethnic_group': 'Ethnic Group Distribution',
        'education': 'Education Level',
        'primary_language': 'Primary Language',
        'type_of_residence': 'Type of Residence',
        'income': 'Income Distribution',
        'political_stance': 'Political Stance'
    }
    
    # Determine grid size based on number of categories
    n_categories = len(demographic_categories)
    n_cols = 3  # You can adjust this for different layouts
    n_rows = (n_categories + n_cols - 1) // n_cols
    
    # Create the figure and subplots
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 4*n_rows))
    axes = axes.flatten()  # Flatten the 2D array of axes for easy indexing
    
    # Add a main title to the figure
    fig.suptitle('Demographic Distributions of Study Participants', fontsize=16, y=0.98)
    
    # Plot each demographic category
    for i, (category, title) in enumerate(demographic_categories.items()):
        ax = axes[i]
        
        # Skip if the category doesn't exist in the dataframe
        if category not in df.columns:
            ax.text(0.5, 0.5, f"Category '{category}' not found", 
                   ha='center', va='center', fontsize=12)
            ax.axis('off')
            continue
        
        # Count occurrences of each value
        value_counts = df[category].value_counts().sort_values(ascending=False)
        total = len(df)
        
        # Plot the distribution
        bars = ax.bar(value_counts.index, value_counts.values)
        
        # Add value and percentage labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height}\n({(height/total)*100:.1f}%)',
                   ha='center', va='bottom', rotation=0, fontsize=8)
        
        ax.set_title(title)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        
        # Set y-limit slightly higher to accommodate labels
        ax.set_ylim(0, max(value_counts.values) * 1.15)
    
    # Hide any unused subplots
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.95)  # Adjust for the main title
    
    # Save the visualization
    output_path = os.path.join(output_dir, 'all_demographics_grid.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Demographic grid visualization saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    csv_path = "demographic_data.csv"
    output_file = "demographic_summary.txt"
    # analyze_demographics(csv_path, output_file)
    # print(f"Demographic summary has been written to {output_file}")
    plot_demographic_grid(csv_path)
