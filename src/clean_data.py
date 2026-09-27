"""
Data Cleaning Script for Shareholder Intelligence System

This script cleans raw data files and outputs them to the clean_data/ folder.
It handles known data quality issues discovered during EDA.

Usage:
    python src/clean_data.py

The script is idempotent - running it multiple times produces the same result.
"""

import pandas as pd
import os
from pathlib import Path


def setup_directories():
    """Ensure clean_data directory exists."""
    clean_data_dir = Path('clean_data')
    clean_data_dir.mkdir(exist_ok=True)
    return clean_data_dir


def clean_register_events(input_path: str, output_path: str) -> dict:
    """
    Clean register_events.csv

    Data Quality Issues Fixed:
    1. Duplicate event_id: Event E1040 appears twice with identical data
       - Remove duplicates keeping first occurrence

    Args:
        input_path: Path to raw register_events.csv
        output_path: Path to save cleaned file

    Returns:
        dict with cleaning statistics
    """
    df = pd.read_csv(input_path)

    initial_rows = len(df)
    duplicates_found = df.duplicated(subset=['event_id']).sum()

    # Remove duplicate event_ids (keep first occurrence)
    df.drop_duplicates(subset=['event_id'], inplace=True)

    final_rows = len(df)
    rows_removed = initial_rows - final_rows

    # Save cleaned data
    df.to_csv(output_path, index=False)

    return {
        'file': 'register_events.csv',
        'initial_rows': initial_rows,
        'duplicates_found': duplicates_found,
        'rows_removed': rows_removed,
        'final_rows': final_rows
    }


def clean_beneficial_filings(input_path: str, output_path: str) -> dict:
    """
    Clean beneficial_filings.csv

    Data Quality Issues Fixed:
    1. Duplicate accession_no: Accession 0002233445-26-000077 appears twice
       - Remove duplicates keeping first occurrence

    Args:
        input_path: Path to raw beneficial_filings.csv
        output_path: Path to save cleaned file

    Returns:
        dict with cleaning statistics
    """
    df = pd.read_csv(input_path)

    initial_rows = len(df)
    duplicates_found = df.duplicated(subset=['accession_no']).sum()

    # Remove duplicate accession_nos (keep first occurrence)
    df.drop_duplicates(subset=['accession_no'], inplace=True)

    final_rows = len(df)
    rows_removed = initial_rows - final_rows

    # Save cleaned data
    df.to_csv(output_path, index=False)

    return {
        'file': 'beneficial_filings.csv',
        'initial_rows': initial_rows,
        'duplicates_found': duplicates_found,
        'rows_removed': rows_removed,
        'final_rows': final_rows
    }


def copy_unchanged_file(input_path: str, output_path: str, filename: str) -> dict:
    """
    Copy files that don't require cleaning.

    Args:
        input_path: Path to raw file
        output_path: Path to save copy
        filename: Name of the file

    Returns:
        dict with file statistics
    """
    df = pd.read_csv(input_path)
    df.to_csv(output_path, index=False)

    return {
        'file': filename,
        'rows': len(df),
        'action': 'copied (no cleaning needed)'
    }


def main():
    """Run all data cleaning operations."""
    print("=" * 70)
    print("Data Cleaning Pipeline")
    print("=" * 70)

    # Setup directories
    clean_data_dir = setup_directories()
    data_dir = Path('data')

    if not data_dir.exists():
        print(f"Error: {data_dir} directory not found")
        return

    # Track all cleaning operations
    results = []

    # 1. Clean register_events.csv
    print("\n[1/5] Cleaning register_events.csv...")
    result = clean_register_events(
        input_path=data_dir / 'register_events.csv',
        output_path=clean_data_dir / 'register_events.csv'
    )
    results.append(result)
    if result['rows_removed'] > 0:
        print(f"  ✓ Removed {result['rows_removed']} duplicate event_id(s)")
    else:
        print(f"  ✓ No duplicates found")

    # 2. Clean beneficial_filings.csv
    print("\n[2/5] Cleaning beneficial_filings.csv...")
    result = clean_beneficial_filings(
        input_path=data_dir / 'beneficial_filings.csv',
        output_path=clean_data_dir / 'beneficial_filings.csv'
    )
    results.append(result)
    if result['rows_removed'] > 0:
        print(f"  ✓ Removed {result['rows_removed']} duplicate accession_no(s)")
    else:
        print(f"  ✓ No duplicates found")

    # 3-5. Copy files that don't need cleaning
    unchanged_files = [
        'holders.csv',
        'opening_positions.csv',
        'shares_outstanding.csv'
    ]

    for idx, filename in enumerate(unchanged_files, start=3):
        print(f"\n[{idx}/5] Copying {filename}...")
        result = copy_unchanged_file(
            input_path=data_dir / filename,
            output_path=clean_data_dir / filename,
            filename=filename
        )
        results.append(result)
        print(f"  ✓ Copied {result['rows']} rows")

    # Print summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    for result in results:
        if 'rows_removed' in result:
            status = f"Cleaned: {result['initial_rows']} → {result['final_rows']} rows"
            if result['rows_removed'] > 0:
                status += f" (-{result['rows_removed']} duplicates)"
        else:
            status = f"{result['action']}: {result['rows']} rows"

        print(f"  {result['file']:30s} {status}")

    print("\n✓ All files cleaned and saved to clean_data/")
    print("\nNote: As new data quality issues are discovered in EDA,")
    print("      add new cleaning functions to this script.")


if __name__ == '__main__':
    main()
