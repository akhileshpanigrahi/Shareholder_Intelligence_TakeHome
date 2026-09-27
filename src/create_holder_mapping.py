import pandas as pd
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def create_mapping():
    # Read from clean_data
    holders = pd.read_csv("clean_data/holders.csv")
    filings = pd.read_csv("clean_data/beneficial_filings.csv")

    # Get latest version per holder
    holders = holders.sort_values(['holder_id', 'version']).groupby('holder_id').tail(1)
    unique_holders = holders[['holder_id', 'holder_name']].drop_duplicates()
    unique_filers = filings[['filer_cik', 'filer_name']].drop_duplicates()

    print("=== HOLDER to FILER MAPPING ===\n")

    mappings = []

    for _, holder in unique_holders.iterrows():
        best_match = None
        best_score = 0

        for _, filer in unique_filers.iterrows():
            score = similarity(holder['holder_name'], filer['filer_name'])
            if score > best_score and score > 0.6:
                best_score = score
                best_match = filer

        if best_match is not None:
            print(f"{holder['holder_id']} → {best_match['filer_cik']}")
            print(f"  {holder['holder_name']} ≈ {best_match['filer_name']} ({best_score:.2f})\n")

            mappings.append({
                'holder_id': holder['holder_id'],
                'filer_cik': best_match['filer_cik'],
                'holder_name': holder['holder_name'],
                'filer_name': best_match['filer_name']
            })

    mapping_df = pd.DataFrame(mappings)

    # Save to CSV
    csv_path = Path("clean_data/holder_filer_mapping.csv")
    csv_path.parent.mkdir(exist_ok=True)
    mapping_df.to_csv(csv_path, index=False)
    print(f"Saved to: {csv_path}\n")

    # Load to database
    conn = sqlite3.connect("northwind.db")
    conn.execute("DROP TABLE IF EXISTS holder_filer_mapping")
    conn.execute("""
        CREATE TABLE holder_filer_mapping (
            holder_id TEXT PRIMARY KEY,
            filer_cik TEXT NOT NULL,
            holder_name TEXT,
            filer_name TEXT
        )
    """)
    mapping_df.to_sql('holder_filer_mapping', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

    print(f"Loaded {len(mapping_df)} mappings to database")
    print("\nReview the CSV and edit if needed, then re-run to update DB")

if __name__ == "__main__":
    create_mapping()
