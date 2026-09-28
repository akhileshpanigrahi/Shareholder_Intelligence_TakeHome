# Data Quality Fault List

**Purpose:** Document all data quality issues found in the synthetic shareholder data, categorized by severity and resolution.

---

## UNEXPECTED FAULTS (Data Errors - Fixed)

1. **Duplicate event_id E1040 in register_events.csv** - Identical transaction recorded twice with same event_id, transfer_id, and all fields | **FIXED:** Deduplication in `src/clean_data.py` removes duplicate keeping first occurrence

2. **Duplicate accession_no 0002233445-26-000077 in beneficial_filings.csv** - Bluewater Pension Trust SC 13G/A filing appears twice with identical data | **FIXED:** Deduplication in `src/clean_data.py` removes duplicate keeping first occurrence

---

## EXPECTED FAULTS (Real-World Features - Documented)

### Name Variations

3. **Filer name variations for CIK 1234567** - Same filer appears as "Ridgeline Capital Partners, L.P." (with comma) and "Ridgeline Capital Partners LP" (without comma) across filings | **HANDLED:** Fuzzy string matching in `src/create_holder_mapping.py` using thefuzz library

4. **Filer name variations for CIK 3344556** - Same filer appears as "Sable Point Advisors LLC" and "Sable Point Advisors, LLC" (comma variation) | **HANDLED:** Fuzzy string matching in `src/create_holder_mapping.py`

### Holder Changes

5. **H007 name change from "Halvard Family Holdings LLC" to "Halvard Family Office LLC"** - Entity renamed effective 2026-08-03, tracked via version 2 | **EXPECTED:** Legitimate business name change handled by versioned holders table with valid_from dates

6. **H010 type change from "individual" to "insider"** - Owen Castellanos reclassified effective 2026-07-15, tracked via version 2 | **EXPECTED:** Legitimate status change (became company insider), handled by versioned holders table

### Temporal Features

7. **Late-recorded reversal E1189** - Reversal for transfer T5189 occurred on 2026-08-27 but not recorded until 2026-09-02, creating 5-day lag between effective_date and recorded_at | **EXPECTED:** Real-world scenario where errors discovered days later, demonstrates dual-timestamp tracking (effective_date vs recorded_at)

8. **Partial reversal E1187** - Reverses only 400,000 shares of original 1,650,000 share transfer T5182, with note "partial reversal; broker over-delivered" | **EXPECTED:** Real-world correction scenario where only portion of original transfer was erroneous

9. **SEC filing lags range 7-45 days** - beneficial_filings shows filing_date averaging 15 days after event_date, with maximum 45-day lag | **EXPECTED:** Normal regulatory filing delays, demonstrates difference between when ownership change occurred vs when publicly disclosed

### Data Sparsity

10. **H011 (Sable Point Advisors LLC) opening position = 0 shares** - Holder exists in holders.csv and opening_positions.csv but started with zero shares on 2026-05-31 | **EXPECTED:** New investor who entered position during June-August 2026 period (first acquisition visible in register_events)

11. **NULL holder_id in register_events** - Some transactions have NULL from_holder_id (equity issuance) or NULL to_holder_id (share buybacks) | **EXPECTED:** Corporate actions that change total shares outstanding, not shareholder-to-shareholder transfers

### SEC Filing Inconsistencies

12. **Inconsistent outstanding_basis in beneficial_filings** - Filers use different shares_outstanding denominators (40,482,500 vs 40,782,500 vs 39,882,500) for calculating percent_reported, even for same-day filings | **EXPECTED:** Filers reference different historical 10-Q/8-K reports as basis, causing percentage calculation discrepancies across filings

13. **Vantage Quant Strategies (CIK 6677889) has no holder_id mapping** - SEC filer appears in beneficial_filings but not in holders.csv and has no entry in holder_filer_mapping.csv | **EXPECTED:** Beneficial owner behind CEDE & CO nominee with no direct register presence, only visible via 5%+ SEC filings

### Reversal Patterns

14. **Reversal note field used for explanations** - Events E1187 and E1189 include explanatory notes ("partial reversal; broker over-delivered", "duplicate instruction") | **EXPECTED:** Audit trail feature documenting why corrections were necessary

---

## DATA QUALITY VALIDATION RESULTS (No Issues Found)

15. **Date format consistency** - All date fields parseable as YYYY-MM-DD or YYYY-MM-DD HH:MM:SS, no format violations across 5 CSV files | **VALIDATED:** No cleaning needed

16. **Temporal ordering in register_events** - Zero violations of recorded_at >= effective_date rule (cannot record before event happens) | **VALIDATED:** No impossible timestamp sequences

17. **Temporal ordering in beneficial_filings** - Zero violations of filing_date >= event_date rule (SEC receives filing after ownership change) | **VALIDATED:** All filing lags are positive

18. **Referential integrity for holder_id** - All holder_id values in opening_positions.csv and register_events.csv exist in holders.csv | **VALIDATED:** No orphan references

19. **Referential integrity for transfer reversals** - All reverses_transfer_id values in register_events point to existing transfer_id | **VALIDATED:** No broken reversal chains

20. **Referential integrity for SEC amendments** - All amends_accession_no values in beneficial_filings point to existing accession_no | **VALIDATED:** No broken amendment chains

21. **Share count positivity** - All shares, shares_reported values are > 0 across all files | **VALIDATED:** No negative or zero share counts

22. **Percentage validity** - All percent_reported values are between 0-100% in beneficial_filings | **VALIDATED:** No invalid ownership percentages

23. **Percentage calculation accuracy** - All reported percentages match (shares_reported / outstanding_basis * 100) within 0.01% rounding tolerance | **VALIDATED:** No calculation errors

24. **Date range coverage** - register_events spans full expected period (2026-06-01 to 2026-08-31) with no missing start/end dates | **VALIDATED:** Complete date coverage

25. **Holder version chronology** - For multi-version holders (H007, H010), version 2 valid_from dates are after version 1 valid_from dates | **VALIDATED:** Correct version ordering

---

## SUMMARY

**Total faults identified:** 25

**Breakdown:**
- **Data errors fixed:** 2 (duplicates)
- **Expected real-world features:** 12 (name variations, holder changes, temporal lags, partial reversals, filing inconsistencies)
- **Validation checks passed:** 11 (no issues found)

**Data cleaning approach:**
- **Automated cleaning:** Deduplication script in `src/clean_data.py` handles duplicate event_id and accession_no
- **Fuzzy matching:** `src/create_holder_mapping.py` handles name variations across systems
- **Schema design:** Versioned holders table, dual timestamps (effective_date/recorded_at), reversal pattern support real-world complexities
- **Query logic:** Queries account for partial reversals, late recordings, name variations, and NULL corporate actions

**Conclusion:** The synthetic data intentionally contains realistic faults to simulate production shareholder intelligence systems. All data errors have been resolved, and expected real-world features are handled by appropriate schema design and query logic.
