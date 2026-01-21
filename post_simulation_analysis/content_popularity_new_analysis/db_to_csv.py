import sqlite3
import pandas as pd

def load_db_tables(db_path):
    """
    Load specified tables from a SQLite database into pandas DataFrames
    """
    conn = sqlite3.connect(db_path)
    
    # Define tables to read
    tables = {
        'posts': 'SELECT * FROM posts',
        'users': 'SELECT * FROM users',
        'user_actions': 'SELECT * FROM user_actions',
        'comments': 'SELECT * FROM comments'
    }
    
    # Read each table into a DataFrame
    dataframes = {}
    for table_name, query in tables.items():
        try:
            df = pd.read_sql_query(query, conn)
            dataframes[table_name] = df
        except Exception as e:
            print(f"Error reading table {table_name}: {e}")
    
    conn.close()
    return dataframes

def load_and_compare_dbs():
    """
    Load data from both databases and return as dictionaries of DataFrames
    """
    # Paths to your databases
    db1_path = '20250122_215428.db'
    db2_path = '20250124_235727.db'
    
    # Load data from both DBs
    print("Loading data from first database...")
    db1_data = load_db_tables(db1_path)
    
    print("Loading data from second database...")
    db2_data = load_db_tables(db2_path)
    
    return db1_data, db2_data

def merge_tables(db1_data, db2_data):
    """
    Merge tables from both databases while maintaining unique primary keys
    """
    merged_data = {}
    
    # Define primary keys for each table
    primary_keys = {
        'users': 'user_id',
        'posts': 'post_id',
        'user_actions': 'id',
        'comments': 'comment_id'
    }
    
    # Merge each table
    for table_name, pk in primary_keys.items():
        if table_name in db1_data and table_name in db2_data:
            # Concatenate the DataFrames
            merged_df = pd.concat([db1_data[table_name], db2_data[table_name]], axis=0)
            
            # Drop duplicates based on primary key
            merged_df = merged_df.drop_duplicates(subset=[pk], keep='last')
            
            # Reset index
            merged_df = merged_df.reset_index(drop=True)
            
            merged_data[table_name] = merged_df
            
    return merged_data

def export_to_csv(merged_data):
    """
    Export each merged DataFrame to a CSV file
    """
    for table_name, df in merged_data.items():
        output_path = f'merged_{table_name}.csv'
        df.to_csv(output_path, index=False)
        print(f"Exported {table_name} to {output_path}")

if __name__ == "__main__":
    # Load data from both databases
    db1_data, db2_data = load_and_compare_dbs()
    
    # Print basic information about the original data
    print("\nOriginal Data Summary:")
    for db_name, data in [("DB1", db1_data), ("DB2", db2_data)]:
        print(f"\n{db_name} Summary:")
        for table_name, df in data.items():
            print(f"{table_name}: {len(df)} rows")
    
    # Merge tables
    print("\nMerging tables...")
    merged_data = merge_tables(db1_data, db2_data)
    
    # Print information about merged data
    print("\nMerged Data Summary:")
    for table_name, df in merged_data.items():
        print(f"{table_name}: {len(df)} rows")
        print(f"Columns: {', '.join(df.columns)}")
        print(f"Memory usage: {df.memory_usage().sum() / 1024**2:.2f} MB\n")
    
    # Export merged tables to CSV
    print("\nExporting merged tables to CSV...")
    export_to_csv(merged_data)
