import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def plot_demographic_grid(csv_path, output_dir='demographic_plots'):
    """
    Create a grid of plots showing distributions for top 5 values of each demographic attribute,
    with remaining values grouped as "Other"
    
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
        'age': 'Age',
        'gender': 'Gender',
        'religion': 'Religion',
        'ethnic_group': 'Ethnicity',
        'education': 'Education',
        'primary_language': 'Language',
        'type_of_residence': 'Residence',
        'income': 'Income',
        'political_stance': 'Political Stance'
    }
    
    # Label shortening dictionary - define shortened versions for long labels
    label_shortener = {
        # Income brackets
        'Less than $10,000': '<$10K',
        '$10,000 - $19,999': '$10K-20K',
        '$20,000 - $29,999': '$20K-30K',
        '$30,000 - $39,999': '$30K-40K',
        '$40,000 - $49,999': '$40K-50K',
        '$50,000 - $59,999': '$50K-60K',
        '$60,000 - $69,999': '$60K-70K',
        '$70,000 - $79,999': '$70K-80K',
        '$80,000 - $89,999': '$80K-90K',
        '$90,000 - $99,999': '$90K-100K',
        '$100,000 - $149,999': '$100K-150K',
        'More than $150,000': '>$150K',
        'Rather not say': 'Undisclosed',
        
        # Education levels
        'Undergraduate degree (BA/BSc/other)': 'Bachelor\'s',
        'High school diploma/A-levels': 'High School',
        'Graduate degree (MA/MSc/MPhil/other)': 'Master\'s',
        'Secondary education (e.g. GED/GCSE)': 'Secondary',
        'Doctorate degree (PhD/other)': 'Doctorate',
        'Technical/community college': 'Technical',
        
        # Ethnicities
        'White or Caucasian': 'White',
        'Black or African American': 'Black',
        'Hispanic or Latino': 'Hispanic',
        'American Indian or Alaska Native': 'Native American',
        'Native Hawaiian or Pacific Islander': 'Pacific Islander',
        'Middle Eastern / North African': 'MENA',
        
        # Religion
        'Christianity': 'Christian',
        'No Religion': 'None',
        'Spiritual but not religious': 'Spiritual',
        'Other Christianity': 'Other Christ.',
        
        # Political stance
        # 'Very liberal': 'V. Liberal',
        # 'Liberal': 'Liberal',
        # 'Moderate': 'Moderate',
        # 'Conservative': 'Conservative',
        # 'Very conservative': 'V. Conservative',
        # 'Libertarian': 'Libertarian',
        # 'Prefer not to say': 'No answer',
        # 'I do not vote because it makes no difference': 'Non-voter',
        
        # Language
        'English': 'English',
        'Spanish': 'Spanish',
        'French': 'French',
        'German': 'German',
        'Italian': 'Italian',
        'Portuguese': 'Portuguese',
        'Mandarin Chinese': 'Chinese',
    }
    
    # Determine grid size
    n_categories = len(demographic_categories)
    n_cols = 3
    n_rows = (n_categories + n_cols - 1) // n_cols
    
    # Create the figure with adjusted size for more compact layout
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 12))
    axes = axes.flatten()
    
    # Use a higher quality style
    # plt.style.use('seaborn-v0_8-pastel')
    
    # Add a main title to the figure
    # fig.suptitle('Demographic Distributions of Study Participants', fontsize=18, y=0.98)
    
    # Set up color palette (slightly more vibrant)
    colors = plt.cm.tab10(np.linspace(0, 1, 6))  # 5 categories + "Other"
    
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
        value_counts = df[category].value_counts()
        total = len(df)
        
        # Get the top 5 categories
        top_categories = value_counts.head(5)
        
        # Calculate the sum of the rest as "Other"
        other_count = value_counts.iloc[5:].sum() if len(value_counts) > 5 else 0
        
        # Add "Other" category if there are more than 5 categories
        if other_count > 0:
            top_categories_with_other = pd.Series({
                **top_categories.to_dict(),
                'Other': other_count
            })
        else:
            top_categories_with_other = top_categories
            
        # Prepare shortened labels
        labels = []
        for idx in top_categories_with_other.index:
            if idx == 'Other':
                labels.append('Other')
            # Special handling for language category
            elif category == 'primary_language':
                if idx == 'English':
                    labels.append('English')
                elif idx == 'Mandarin Chinese':
                    labels.append('Chinese')
                elif idx.startswith('English,'):
                    # Remove "English, " prefix and keep only the second language
                    second_lang = idx.replace('English, ', '')
                    labels.append(second_lang)
                else:
                    labels.append(idx)
            elif idx in label_shortener:
                labels.append(label_shortener[idx])
            else:
                # If very long, truncate with ellipsis
                shortened_idx = str(idx)
                if len(str(idx)) > 30:
                    shortened_idx = str(idx)[:20] + '...'
                labels.append(shortened_idx)
        
        # Plot the distribution with shortened labels
        bars = ax.bar(range(len(top_categories_with_other)), 
                      top_categories_with_other.values,
                      color=colors)
        
        # Use a different color for "Other" if it exists
        if other_count > 0:
            bars[-1].set_color('#CCCCCC')  # Gray color for "Other"
        
        # Set the shortened x-tick labels
        ax.set_xticks(range(len(top_categories_with_other)))
        ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=10)
        
        # Add value and percentage labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}\n({(height/total)*100:.1f}%)',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_title(title, fontsize=14, pad=10, fontweight='bold')
        ax.tick_params(axis='y', labelsize=10)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Set y-limit slightly higher to accommodate labels
        ax.set_ylim(0, max(top_categories_with_other.values) * 1.15)
        
        # Remove x-axis label
        ax.set_xlabel('')
        
        # Set y-axis label
        ax.set_ylabel('Count', fontsize=10)
    
    # Hide any unused subplots
    for j in range(i+1, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.95, hspace=0.4, wspace=0.3)
    
    # Save the visualization
    output_path = os.path.join(output_dir, 'demographic_top5_grid.pdf')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Demographic top 5 grid visualization saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    csv_path = "demographic_data.csv"  # Update this path to your actual CSV file
    plot_demographic_grid(csv_path)