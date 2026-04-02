import pandas as pd
import json
import glob
import os

# Configuration
BASE_PATH = r'C:\Users\MartinGrossmann\Downloads\export\output27-02-2026'
MAPPING_FILE = os.path.join(BASE_PATH, '_mapping_serge_ean_sensorid.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'export_pnd_total.csv')

def process():
    print(f"Loading mapping from {MAPPING_FILE}...")
    with open(MAPPING_FILE, 'r') as f:
        mapping = json.load(f)
    
    # Pre-process mapping into a DataFrame for fast merging
    mapping_data = []
    for serge, data in mapping.items():
        mapping_data.append({
            'Serge': serge,
            'sensorID_map': data.get('sensorID'),
            'loraID_map': data.get('ean')
        })
    mapping_df = pd.DataFrame(mapping_data)
    mapping_df['Serge'] = mapping_df['Serge'].astype(str)

    # Find all CSV files
    csv_files = glob.glob(os.path.join(BASE_PATH, 'pnd_*-unified.csv'))
    if not csv_files:
        print("No CSV files found matching pattern pnd_*-unified.csv")
        return

    combined_dfs = []
    for file in csv_files:
        print(f"Processing {os.path.basename(file)}...")
        df = pd.read_csv(file)
        
        # Ensure Serge is string for matching
        df['Serge'] = df['Serge'].astype(str)
        
        # Merge with mapping to fill missing IDs
        df = df.merge(mapping_df, on='Serge', how='left')
        
        # Fill sensorID and loraID from mapping if they are NaN
        df['sensorID'] = df['sensorID'].fillna(df['sensorID_map'])
        df['loraID'] = df['loraID'].fillna(df['loraID_map'])
        
        # Keep original columns, we'll rename later
        df = df[['datetime', 'sensorID', 'loraID', 'Serge', 'Value']]
        combined_dfs.append(df)

    print("Combining all dataframes...")
    full_df = pd.concat(combined_dfs, ignore_index=True)

    # Rename to target specification
    full_df = full_df.rename(columns={
        'datetime': 'DATETIME',
        'sensorID': 'SENSORID',
        'loraID': 'LORAID',
        'Serge': 'SERGE',
        'Value': 'VALUE'
    })

    # Type conversion (NUMBER 38,0 and 38,2)
    # Using Int64 allows the column to store integers while supporting NaNs
    print("Converting data types...")
    full_df['SENSORID'] = pd.to_numeric(full_df['SENSORID'], errors='coerce').astype('Int64')
    full_df['LORAID'] = pd.to_numeric(full_df['LORAID'], errors='coerce').astype('Int64')
    full_df['SERGE'] = pd.to_numeric(full_df['SERGE'], errors='coerce').astype('Int64')
    
    # Value to float rounded to 2
    full_df['VALUE'] = pd.to_numeric(full_df['VALUE'], errors='coerce').round(2)

    # Final column selection
    full_df = full_df[['DATETIME', 'SENSORID', 'LORAID', 'SERGE', 'VALUE']]

    print(f"Saving merged data to {OUTPUT_FILE}...")
    full_df.to_csv(OUTPUT_FILE, index=False)
    print("Done!")

if __name__ == "__main__":
    process()
