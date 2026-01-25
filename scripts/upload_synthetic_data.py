import json
import os
from pathlib import Path
from supabase import create_client, Client

# Supabase Configuration
SUPABASE_URL = "https://lvlkgssnfmszujxtrasa.supabase.co"
SUPABASE_KEY = "sb_publishable_l8Cx8bsqkPZ-B_q3ka6MmQ_JspTcv30"

def upload_synthetic_data():
    """
    Uploads synthetic evidence from local JSON to Supabase.
    """
    print(f"Connecting to Supabase at {SUPABASE_URL}...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Load local synthetic data
    data_path = Path("data/synthetic_evidence.json")
    if not data_path.exists():
        print(f"Error: {data_path} not found.")
        return
        
    with open(data_path, "r") as f:
        data = json.load(f)
        
    print(f"Loaded {sum(len(v) for v in data.values())} records from {data_path}")
    
    # Tables to populate
    tables = {
        "permits": "permits",
        "violations": "violations",
        "complaints_311": "complaints_311",
        "sfpd_incidents": "sfpd_incidents"
    }
    
    for json_key, table_name in tables.items():
        records = data.get(json_key, [])
        if not records:
            continue
            
        print(f"Uploading {len(records)} records to table '{table_name}'...")
        
        # Batch upload to avoid timeouts
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            
            # Clean records: remove nested objects if table doesn't support JSONB for them
            # For simplicity, we assume the table schema matches or is flexible (JSONB)
            # But let's flatten 'location' just in case or keep checks simple
            cleaned_batch = []
            for r in batch:
                clean_r = r.copy()
                # Flatten location if needed, or ensure table has jsonb column
                # Here we assume the table structure you might need. 
                # If tables don't exist, this will fail.
                cleaned_batch.append(clean_r)
                
            try:
                supabase.table(table_name).insert(cleaned_batch).execute()
                print(f" - Uploaded batch {i//batch_size + 1}")
            except Exception as e:
                print(f"Error uploading batch to {table_name}: {e}")
                # If error is 'relation does not exist', we need to create tables first
                if "relation" in str(e) and "does not exist" in str(e):
                    print(f"!!! CRITICAL: Table '{table_name}' does not exist in Supabase.")
                    print("You need to run the SQL migration to create these tables first.")
                    return

    print("\nUpload complete!")

if __name__ == "__main__":
    upload_synthetic_data()
