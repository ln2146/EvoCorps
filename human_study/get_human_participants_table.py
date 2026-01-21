import pandas as pd

def extract_demographic_data(input_file='human_study_data.csv', output_file='demographic_data.csv'):
    """
    Extract selected demographic columns from the human study data CSV file.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path for the output CSV file
    """
    try:
        # Read the original CSV file
        df = pd.read_csv(input_file)
        
        # Select only the specified demographic columns
        demographic_columns = [
            'prolific_id', 'age', 'gender', 'religion', 'ethnic_group', 
            'education', 'primary_language', 'type_of_residence', 
            'income', 'political_stance'
        ]
        
        # Create a new dataframe with only these columns
        demographic_df = df[demographic_columns]
        
        # Write to a new CSV file
        demographic_df.to_csv(output_file, index=False)
        
        print(f"Successfully created {output_file} with selected demographic information.")
        return demographic_df
    
    except Exception as e:
        print(f"Error processing the CSV file: {e}")
        return None

if __name__ == "__main__":
    extract_demographic_data()
