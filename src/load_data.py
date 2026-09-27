import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "northwind.db"
DATA_DIR = Path("clean_data")

def load_data():
    conn = sqlite3.connect(DB_PATH)

    # Load schema
    with open("src/schema.sql") as f:
        conn.executescript(f.read())

    # Load CSV files
    tables = {
        "holders": "holders.csv",
        "opening_positions": "opening_positions.csv",
        "register_events": "register_events.csv",
        "shares_outstanding": "shares_outstanding.csv",
        "beneficial_filings": "beneficial_filings.csv"
    }

    for table, csv_file in tables.items():
        df = pd.read_csv(DATA_DIR / csv_file)
        df.to_sql(table, conn, if_exists="append", index=False)
        print(f"Loaded {len(df)} rows into {table}")

    conn.commit()
    conn.close()
    print(f"\nDatabase created: {DB_PATH}")

if __name__ == "__main__":
    load_data()
