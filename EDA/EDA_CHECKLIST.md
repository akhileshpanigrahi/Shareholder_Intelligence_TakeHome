# Shareholder Intelligence System - EDA Checklist

This checklist guides you through data quality checks for all 5 data files.
Run each check in your Python notebook. Document findings. Add fixes to `src/clean_data.py` if needed.

---

## ✅ COMPLETED
- [x] Duplicate event_id in register_events.csv (E1040)
- [x] Duplicate accession_no in beneficial_filings.csv (0002233445-26-000077)

---

## 1. DATA TYPE & FORMAT VALIDATION

### 1.1 Date Format Consistency
**Files:** All files with date columns

```python
# Check date format consistency and parseability
date_columns = {
    'holders': ['valid_from'],
    'opening_positions': ['as_of_date'],
    'register_events': ['effective_date', 'recorded_at'],
    'shares_outstanding': ['as_of_date', 'published_date'],
    'beneficial_filings': ['filing_date', 'event_date']
}

# Test parsing each date column
for file_name, cols in date_columns.items():
    df = eval(f'{file_name}_df')
    print(f"\n{file_name}:")
    for col in cols:
        try:
            parsed = pd.to_datetime(df[col])
            print(f"  ✓ {col}: All dates valid ({parsed.min()} to {parsed.max()})")
            # Check for dates outside expected range (2025-2026)
            outside_range = (parsed.dt.year < 2025) | (parsed.dt.year > 2027)
            if outside_range.any():
                print(f"    ⚠️  {outside_range.sum()} dates outside 2025-2027 range")
        except Exception as e:
            print(f"  ❌ {col}: Parse error - {e}")
```

**What to look for:**
- Invalid date formats
- Dates outside the expected range (data is June-August 2026)
- NULL dates where they shouldn't be

---

## 2. TEMPORAL CONSISTENCY

### 2.1 Effective Date vs Recorded At (register_events)
**Critical:** `recorded_at` should be >= `effective_date` (we can't record something before it happens)

```python
# Check temporal ordering
register_events_df['effective_date_dt'] = pd.to_datetime(register_events_df['effective_date'])
register_events_df['recorded_at_dt'] = pd.to_datetime(register_events_df['recorded_at'])

temporal_violations = register_events_df[
    register_events_df['recorded_at_dt'] < register_events_df['effective_date_dt']
]

print(f"Temporal violations (recorded before effective): {len(temporal_violations)}")
if len(temporal_violations) > 0:
    print("\nViolations:")
    print(temporal_violations[['event_id', 'effective_date', 'recorded_at', 'event_type']])
```

**What to look for:**
- Records where `recorded_at < effective_date` (impossible - data error)
- Late recordings (large gap between effective and recorded) - this is EXPECTED for reversals

### 2.2 Filing Date vs Event Date (beneficial_filings)
**Normal:** `filing_date` >= `event_date` (SEC filings arrive after the event)

```python
# Check filing lag
beneficial_filings_df['filing_date_dt'] = pd.to_datetime(beneficial_filings_df['filing_date'])
beneficial_filings_df['event_date_dt'] = pd.to_datetime(beneficial_filings_df['event_date'])
beneficial_filings_df['filing_lag_days'] = (
    beneficial_filings_df['filing_date_dt'] - beneficial_filings_df['event_date_dt']
).dt.days

print("Filing lag statistics (days):")
print(beneficial_filings_df['filing_lag_days'].describe())
print(f"\nFilings where event_date > filing_date: {(beneficial_filings_df['filing_lag_days'] < 0).sum()}")

# Show extreme lags
print("\nExtreme filing lags (>60 days):")
print(beneficial_filings_df[beneficial_filings_df['filing_lag_days'] > 60][
    ['filer_name', 'event_date', 'filing_date', 'filing_lag_days']
])
```

**What to look for:**
- Negative lag (filing before event - data error)
- Extremely long lags (>60 days might indicate backdated events)

### 2.3 Holder Version Validity
**Rule:** For each holder_id, version=2 should have `valid_from` > version=1 `valid_from`

```python
# Check version chronology
holders_multi_version = holders_df.groupby('holder_id').filter(lambda x: len(x) > 1)
version_issues = []

for holder_id in holders_multi_version['holder_id'].unique():
    holder_versions = holders_df[holders_df['holder_id'] == holder_id].sort_values('version')
    holder_versions['valid_from_dt'] = pd.to_datetime(holder_versions['valid_from'])

    for i in range(len(holder_versions) - 1):
        v1_date = holder_versions.iloc[i]['valid_from_dt']
        v2_date = holder_versions.iloc[i + 1]['valid_from_dt']
        if v2_date <= v1_date:
            version_issues.append({
                'holder_id': holder_id,
                'version1': holder_versions.iloc[i]['version'],
                'date1': v1_date,
                'version2': holder_versions.iloc[i + 1]['version'],
                'date2': v2_date
            })

if version_issues:
    print("Version chronology violations:")
    print(pd.DataFrame(version_issues))
else:
    print("✓ All holder versions have correct chronology")
```

---

## 3. REFERENTIAL INTEGRITY

### 3.1 Holder IDs Exist Across Files
**Check:** All holder_ids in other files should exist in holders.csv

```python
# Get all unique holder_ids from holders.csv
valid_holder_ids = set(holders_df['holder_id'].unique())

# Check opening_positions
opening_holders = set(opening_positions_df['holder_id'].unique())
orphan_opening = opening_holders - valid_holder_ids
if orphan_opening:
    print(f"⚠️  Opening positions with unknown holder_id: {orphan_opening}")
else:
    print("✓ All opening_positions holder_ids exist in holders.csv")

# Check register_events (from_holder_id and to_holder_id)
from_holders = set(register_events_df['from_holder_id'].dropna().unique())
to_holders = set(register_events_df['to_holder_id'].dropna().unique())
all_event_holders = from_holders | to_holders

orphan_events = all_event_holders - valid_holder_ids
if orphan_events:
    print(f"⚠️  Register events with unknown holder_id: {orphan_events}")
else:
    print("✓ All register_events holder_ids exist in holders.csv")
```

**What to look for:**
- Holder IDs referenced but not defined in holders.csv
- Note: NULL holder_ids in register_events are OK (corporate actions)

### 3.2 Transfer IDs Referenced in Reversals Exist
**Check:** All `reverses_transfer_id` values should match an existing `transfer_id`

```python
# Check reversal references
reversals = register_events_df[register_events_df['reverses_transfer_id'].notna()]
valid_transfer_ids = set(register_events_df['transfer_id'].unique())

for idx, row in reversals.iterrows():
    reversed_id = row['reverses_transfer_id']
    if reversed_id not in valid_transfer_ids:
        print(f"⚠️  Event {row['event_id']} reverses non-existent transfer {reversed_id}")

# Check that reversed transfers exist
missing_reversals = reversals[~reversals['reverses_transfer_id'].isin(valid_transfer_ids)]
if len(missing_reversals) == 0:
    print("✓ All reversal references are valid")
else:
    print(f"⚠️  {len(missing_reversals)} reversals reference non-existent transfers")
```

### 3.3 Amendment Chains (beneficial_filings)
**Check:** All `amends_accession_no` should reference an existing `accession_no`

```python
# Check amendment references
amendments = beneficial_filings_df[beneficial_filings_df['amends_accession_no'].notna()]
valid_accession_nos = set(beneficial_filings_df['accession_no'].unique())

orphan_amendments = []
for idx, row in amendments.iterrows():
    amends = row['amends_accession_no']
    if amends not in valid_accession_nos:
        orphan_amendments.append({
            'accession_no': row['accession_no'],
            'amends': amends,
            'filer': row['filer_name']
        })

if orphan_amendments:
    print(f"⚠️  {len(orphan_amendments)} amendments reference missing filings:")
    print(pd.DataFrame(orphan_amendments))
else:
    print("✓ All amendment references are valid")
```

---

## 4. BUSINESS LOGIC VALIDATION

### 4.1 Share Counts Are Positive
**Rule:** All share counts should be > 0

```python
# Check opening_positions
neg_opening = opening_positions_df[opening_positions_df['shares'] <= 0]
if len(neg_opening) > 0:
    print(f"⚠️  Opening positions with non-positive shares: {len(neg_opening)}")
    print(neg_opening)
else:
    print("✓ All opening positions have positive shares")

# Check register_events
neg_events = register_events_df[register_events_df['shares'] <= 0]
if len(neg_events) > 0:
    print(f"⚠️  Register events with non-positive shares: {len(neg_events)}")
    print(neg_events[['event_id', 'shares', 'event_type']])
else:
    print("✓ All register events have positive shares")

# Check beneficial_filings
neg_filings = beneficial_filings_df[beneficial_filings_df['shares_reported'] <= 0]
if len(neg_filings) > 0:
    print(f"⚠️  Beneficial filings with non-positive shares: {len(neg_filings)}")
    print(neg_filings)
else:
    print("✓ All beneficial filings have positive shares")
```

### 4.2 Percentage Ownership is Reasonable
**Rule:** SEC-reported percentages should be 0% < x < 100%

```python
# Check reported percentages
invalid_pct = beneficial_filings_df[
    (beneficial_filings_df['percent_reported'] <= 0) |
    (beneficial_filings_df['percent_reported'] >= 100)
]

if len(invalid_pct) > 0:
    print(f"⚠️  {len(invalid_pct)} filings with invalid percentages:")
    print(invalid_pct[['filer_name', 'percent_reported', 'shares_reported']])
else:
    print("✓ All reported percentages are in valid range")

# Check if reported % matches shares/outstanding calculation
beneficial_filings_df['calculated_pct'] = (
    beneficial_filings_df['shares_reported'] /
    beneficial_filings_df['outstanding_basis'] * 100
)
beneficial_filings_df['pct_diff'] = abs(
    beneficial_filings_df['calculated_pct'] - beneficial_filings_df['percent_reported']
)

# Allow 0.01% tolerance for rounding
pct_mismatches = beneficial_filings_df[beneficial_filings_df['pct_diff'] > 0.01]
if len(pct_mismatches) > 0:
    print(f"\n⚠️  {len(pct_mismatches)} filings where reported % doesn't match calculation:")
    print(pct_mismatches[['filer_name', 'shares_reported', 'outstanding_basis',
                          'percent_reported', 'calculated_pct', 'pct_diff']])
else:
    print("✓ All reported percentages match calculations (within 0.01% tolerance)")
```

### 4.3 Opening Positions Total Check
**Sanity check:** Sum of opening positions should be reasonable relative to shares outstanding

```python
# Calculate total opening position
total_opening = opening_positions_df['shares'].sum()
print(f"Total opening positions (May 31): {total_opening:,}")

# Compare to first shares_outstanding record
first_outstanding = shares_outstanding_df.iloc[0]['shares_outstanding']
print(f"Shares outstanding (Mar 31): {first_outstanding:,}")

difference = total_opening - first_outstanding
pct_diff = (difference / first_outstanding) * 100

print(f"\nDifference: {difference:,} shares ({pct_diff:.2f}%)")
if abs(pct_diff) > 5:
    print("⚠️  Opening positions differ from outstanding by >5%")
else:
    print("✓ Opening positions are reasonable")
```

### 4.4 Reversal Logic Check
**Rule:** Reversals should match the original transfer exactly (same from/to/shares)

```python
# Check reversal matching
reversals = register_events_df[register_events_df['event_type'] == 'reversal'].copy()

reversal_mismatches = []
for idx, reversal in reversals.iterrows():
    reversed_id = reversal['reverses_transfer_id']
    original = register_events_df[register_events_df['transfer_id'] == reversed_id]

    if len(original) == 0:
        continue  # Already caught in referential integrity check

    original = original.iloc[0]

    # Check if reversal matches original
    if (reversal['from_holder_id'] != original['from_holder_id'] or
        reversal['to_holder_id'] != original['to_holder_id'] or
        reversal['shares'] != original['shares']):
        reversal_mismatches.append({
            'reversal_event': reversal['event_id'],
            'original_transfer': reversed_id,
            'match': 'NO'
        })

if reversal_mismatches:
    print(f"⚠️  {len(reversal_mismatches)} reversals don't match original transfers")
    print(pd.DataFrame(reversal_mismatches))
else:
    print("✓ All reversals match their original transfers")
```

---

## 5. MISSING DATA ANALYSIS

### 5.1 NULL Value Analysis
**Check:** Understand where NULLs are expected vs unexpected

```python
# Check NULL values in each file
print("NULL value counts:\n")

for name in ['holders_df', 'opening_positions_df', 'register_events_df',
             'shares_outstanding_df', 'beneficial_filings_df']:
    df = eval(name)
    print(f"\n{name}:")
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        print(null_cols)
    else:
        print("  No NULL values")
```

**Expected NULLs:**
- `register_events.reverses_transfer_id` - Only set for reversals
- `register_events.from_holder_id` - NULL for equity issuance
- `register_events.to_holder_id` - NULL for share buybacks
- `register_events.note` - Optional field
- `beneficial_filings.amends_accession_no` - Only set for amendments

**Unexpected NULLs would be:**
- Required identification fields (holder_id, event_id, etc.)
- Share counts
- Dates

### 5.2 Missing Holders in Opening Positions
**Check:** Do all holders have an opening position?

```python
# Get holders that should have opening positions (existed on May 31)
holders_may_31 = holders_df[pd.to_datetime(holders_df['valid_from']) <= '2026-05-31']
expected_holder_ids = set(holders_may_31['holder_id'].unique())

# Get actual opening positions
actual_holder_ids = set(opening_positions_df['holder_id'].unique())

# Find missing
missing_opening = expected_holder_ids - actual_holder_ids

if missing_opening:
    print(f"⚠️  {len(missing_opening)} holders missing opening positions:")
    print(holders_df[holders_df['holder_id'].isin(missing_opening)])
else:
    print("✓ All May 31 holders have opening positions")

# Check for holders in opening that don't exist
extra_opening = actual_holder_ids - expected_holder_ids
if extra_opening:
    print(f"\n⚠️  {len(extra_opening)} opening positions for unknown holders: {extra_opening}")
```

---

## 6. NAME CONSISTENCY & FUZZY MATCHING

### 6.1 Filer Name Variations
**Check:** Same filer_cik with different filer_name (punctuation, abbreviations)

```python
# Group by filer_cik and check name variations
name_variations = beneficial_filings_df.groupby('filer_cik')['filer_name'].unique()

print("Filer name variations by CIK:")
for cik, names in name_variations.items():
    if len(names) > 1:
        print(f"\nCIK {cik}:")
        for name in names:
            print(f"  - {name}")
```

**What to look for:**
- Minor punctuation differences (comma, period, "LLC" vs "L.L.C.")
- These variations make fuzzy matching necessary

### 6.2 Holder Name Changes
**Check:** Same holder_id with different holder_name across versions

```python
# Find holders with multiple versions
multi_version_holders = holders_df.groupby('holder_id').filter(lambda x: len(x) > 1)

print("Holders with name changes:")
for holder_id in multi_version_holders['holder_id'].unique():
    versions = holders_df[holders_df['holder_id'] == holder_id].sort_values('version')
    if versions['holder_name'].nunique() > 1:
        print(f"\n{holder_id}:")
        for _, row in versions.iterrows():
            print(f"  v{row['version']} ({row['valid_from']}): {row['holder_name']}")
```

---

## 7. OUTLIER DETECTION

### 7.1 Unusually Large Transactions
**Check:** Register events with abnormally large share counts

```python
# Get transaction size statistics
stats = register_events_df['shares'].describe()
print("Register event share statistics:")
print(stats)

# Flag transactions > 99th percentile
percentile_99 = register_events_df['shares'].quantile(0.99)
large_transactions = register_events_df[register_events_df['shares'] > percentile_99]

print(f"\nTransactions larger than 99th percentile ({percentile_99:,.0f} shares):")
print(large_transactions[['event_id', 'from_holder_id', 'to_holder_id', 'shares',
                           'effective_date', 'event_type']].sort_values('shares', ascending=False))
```

### 7.2 Unusual Outstanding Shares Changes
**Check:** Are the changes in shares_outstanding reasonable?

```python
# Calculate period-over-period changes
shares_outstanding_df_sorted = shares_outstanding_df.sort_values('as_of_date')
shares_outstanding_df_sorted['change'] = shares_outstanding_df_sorted['shares_outstanding'].diff()
shares_outstanding_df_sorted['pct_change'] = shares_outstanding_df_sorted['shares_outstanding'].pct_change() * 100

print("Shares outstanding changes:")
print(shares_outstanding_df_sorted[['as_of_date', 'shares_outstanding', 'change', 'pct_change']])

# Flag unusual changes (>10%)
unusual = shares_outstanding_df_sorted[abs(shares_outstanding_df_sorted['pct_change']) > 10]
if len(unusual) > 0:
    print("\n⚠️  Large changes in shares outstanding (>10%):")
    print(unusual)
```

---

## 8. DATA COMPLETENESS

### 8.1 Date Range Coverage
**Check:** Are there gaps in the expected date range?

```python
# Expected range: June 1 - August 31, 2026
expected_start = pd.Timestamp('2026-06-01')
expected_end = pd.Timestamp('2026-08-31')

# Check register_events coverage
register_dates = pd.to_datetime(register_events_df['effective_date'])
actual_start = register_dates.min()
actual_end = register_dates.max()

print(f"Register events date range:")
print(f"  Expected: {expected_start.date()} to {expected_end.date()}")
print(f"  Actual: {actual_start.date()} to {actual_end.date()}")

if actual_start > expected_start:
    print(f"  ⚠️  Missing {(actual_start - expected_start).days} days at start")
if actual_end < expected_end:
    print(f"  ⚠️  Missing {(expected_end - actual_end).days} days at end")

# Check for date gaps (days with no activity)
all_dates = pd.date_range(start=actual_start, end=actual_end, freq='D')
active_dates = set(register_dates.dt.date)
missing_dates = [d.date() for d in all_dates if d.date() not in active_dates]

if missing_dates:
    print(f"\n  {len(missing_dates)} days with no register activity")
    # This is normal for weekends/holidays
```

---

## 9. FORM TYPE VALIDATION

### 9.1 Valid Form Types
**Check:** Are all form_type values in expected set?

```python
# Expected form types
expected_forms = ['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A']
actual_forms = beneficial_filings_df['form_type'].unique()

print(f"Found form types: {sorted(actual_forms)}")

unexpected = set(actual_forms) - set(expected_forms)
if unexpected:
    print(f"⚠️  Unexpected form types: {unexpected}")
else:
    print("✓ All form types are valid")
```

### 9.2 Amendment Logic
**Check:** Amendments should have amends_accession_no set

```python
# Check amendment logic
amendments = beneficial_filings_df[beneficial_filings_df['form_type'].str.contains('/A')]
missing_amends_ref = amendments[amendments['amends_accession_no'].isna()]

if len(missing_amends_ref) > 0:
    print(f"⚠️  {len(missing_amends_ref)} amendments missing amends_accession_no:")
    print(missing_amends_ref[['accession_no', 'form_type', 'filer_name']])
else:
    print("✓ All amendments have amends_accession_no")

# Check that non-amendments don't have amends_accession_no
initial_filings = beneficial_filings_df[~beneficial_filings_df['form_type'].str.contains('/A')]
unexpected_amends = initial_filings[initial_filings['amends_accession_no'].notna()]

if len(unexpected_amends) > 0:
    print(f"\n⚠️  {len(unexpected_amends)} initial filings have amends_accession_no (should be NULL)")
else:
    print("✓ Initial filings correctly have NULL amends_accession_no")
```

---

## 10. HOLDER TYPE VALIDATION

### 10.1 Valid Holder Types
**Check:** Are all holder_type values in expected set?

```python
# Expected holder types (from assignment context)
expected_types = ['nominee', 'institution', 'individual', 'trust', 'insider']
actual_types = holders_df['holder_type'].unique()

print(f"Found holder types: {sorted(actual_types)}")

unexpected = set(actual_types) - set(expected_types)
if unexpected:
    print(f"⚠️  Unexpected holder types: {unexpected}")
else:
    print("✓ All holder types are valid")
```

### 10.2 Type Changes Over Time
**Check:** Track holder_type changes across versions

```python
# Find type changes
type_changes = []
multi_version = holders_df.groupby('holder_id').filter(lambda x: len(x) > 1)

for holder_id in multi_version['holder_id'].unique():
    versions = holders_df[holders_df['holder_id'] == holder_id].sort_values('version')
    if versions['holder_type'].nunique() > 1:
        for i in range(len(versions) - 1):
            type_changes.append({
                'holder_id': holder_id,
                'holder_name': versions.iloc[i]['holder_name'],
                'from_type': versions.iloc[i]['holder_type'],
                'to_type': versions.iloc[i + 1]['holder_type'],
                'change_date': versions.iloc[i + 1]['valid_from']
            })

if type_changes:
    print("Holder type changes:")
    print(pd.DataFrame(type_changes))
else:
    print("No holder type changes found")
```

---

## SUMMARY TEMPLATE

After running all checks, create a summary:

```python
print("=" * 70)
print("EDA SUMMARY")
print("=" * 70)

issues_found = [
    # Add each issue found, e.g.:
    # "Duplicate event_id E1040 in register_events.csv [FIXED]",
    # "Holder H011 missing opening position - started at 0 shares [EXPECTED]",
]

print(f"\nTotal issues found: {len(issues_found)}")
for i, issue in enumerate(issues_found, 1):
    print(f"  {i}. {issue}")

print("\n" + "=" * 70)
print("Next steps:")
print("  1. Document all issues in EDA notebook")
print("  2. Add necessary cleaning functions to src/clean_data.py")
print("  3. Update fault list for assignment deliverable #5")
print("=" * 70)
```

---

## Notes

- **Expected anomalies** in synthetic data (per assignment):
  - Duplicates (already found and fixed)
  - Late-recorded reversals (temporal gaps are OK)
  - Name variations across systems
  - Holder type changes
  - Inconsistent outstanding_basis in SEC filings

- **Don't over-clean:** Some "issues" are real-world features, not bugs
  - Late filing lags are normal
  - Name variations require fuzzy matching (handled by create_holder_mapping.py)
  - Type changes are legitimate (individual becomes insider)

- **Focus on:** Data integrity issues that would break queries or produce wrong results
