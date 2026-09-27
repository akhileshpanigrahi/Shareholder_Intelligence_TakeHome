-- Query 3: Percent of Company Reconciliation
-- Compares our computed ownership percentages vs SEC filer reported percentages
-- Analyzes ALL filings (including amendments) to show reconciliation over time

-- All beneficial filings (including original and amendments)
WITH all_filings AS (
  SELECT
    accession_no,
    filer_cik,
    filer_name,
    event_date,
    form_type,
    filing_date,
    shares_reported,
    percent_reported,
    outstanding_basis,
    amends_accession_no
  FROM beneficial_filings
),

-- Calculate register position for each filer as of their event_date
filer_positions AS (
  SELECT
    af.accession_no,
    af.filer_cik,
    af.event_date,
    COALESCE(op.shares, 0)
    + COALESCE(SUM(CASE WHEN re.to_holder_id = m.holder_id THEN re.shares ELSE 0 END), 0)
    - COALESCE(SUM(CASE WHEN re.from_holder_id = m.holder_id THEN re.shares ELSE 0 END), 0)
    AS our_shares
  FROM all_filings af
  LEFT JOIN holder_filer_mapping m ON af.filer_cik = m.filer_cik
  LEFT JOIN opening_positions op ON m.holder_id = op.holder_id AND op.as_of_date = '2026-05-31'
  LEFT JOIN register_events re ON (
    (re.to_holder_id = m.holder_id OR re.from_holder_id = m.holder_id)
    AND re.effective_date <= af.event_date
    AND re.transfer_id NOT IN (
      SELECT reverses_transfer_id
      FROM register_events
      WHERE reverses_transfer_id IS NOT NULL
    )
  )
  GROUP BY af.accession_no, af.filer_cik, af.event_date, m.holder_id, op.shares
),

-- Get actual shares outstanding as of each event_date
-- If event_date is before first shares_outstanding record, use earliest available
actual_outstanding AS (
  SELECT
    af.accession_no,
    COALESCE(
      -- Try to get most recent shares_outstanding <= event_date
      (
        SELECT so.shares_outstanding
        FROM shares_outstanding so
        WHERE so.as_of_date <= af.event_date
        ORDER BY so.as_of_date DESC
        LIMIT 1
      ),
      -- If none found (event_date before our data), use earliest available
      (
        SELECT so.shares_outstanding
        FROM shares_outstanding so
        ORDER BY so.as_of_date ASC
        LIMIT 1
      )
    ) AS actual_outstanding
  FROM all_filings af
),

-- Combine and calculate differences
combined AS (
  SELECT
    af.accession_no,
    af.filer_cik,
    af.filer_name,
    af.event_date,
    af.filing_date,
    af.form_type,
    af.amends_accession_no,

    -- Reported values
    af.shares_reported,
    af.percent_reported,
    af.outstanding_basis,

    -- Our computed values (using MAX logic like Query 1)
    COALESCE(fp.our_shares, 0) as register_shares,
    CASE
      WHEN COALESCE(fp.our_shares, 0) > af.shares_reported THEN COALESCE(fp.our_shares, 0)
      ELSE af.shares_reported
    END as our_shares,
    ao.actual_outstanding,

    -- Differences
    COALESCE(fp.our_shares, 0) - af.shares_reported as register_diff,
    ao.actual_outstanding - af.outstanding_basis as outstanding_diff

  FROM all_filings af
  LEFT JOIN filer_positions fp ON af.accession_no = fp.accession_no
  LEFT JOIN actual_outstanding ao ON af.accession_no = ao.accession_no
)

-- Final output with explanation
SELECT
  filer_cik,
  filer_name,
  event_date,
  filing_date,
  accession_no,
  form_type,
  amends_accession_no,

  -- Reported values
  CAST(shares_reported AS INTEGER) as shares_reported,
  ROUND(percent_reported, 2) as percent_reported,
  CAST(outstanding_basis AS INTEGER) as outstanding_basis,

  -- Our computed values (using MAX of register and reported)
  CAST(our_shares AS INTEGER) as our_shares,
  CAST(actual_outstanding AS INTEGER) as actual_outstanding,
  ROUND(our_shares * 100.0 / NULLIF(actual_outstanding, 0), 2) as our_percent,

  -- Differences
  ROUND((our_shares * 100.0 / NULLIF(actual_outstanding, 0)) - percent_reported, 2) as percent_diff,

  -- Simplified explanation
  CASE
    -- Perfect match
    WHEN ABS(register_diff) = 0
         AND ABS(outstanding_diff) = 0
         AND ABS((our_shares * 100.0 / NULLIF(actual_outstanding, 0)) - percent_reported) <= 0.01
    THEN 'Match'

    -- Position mismatch - register exceeds filing (ERROR)
    WHEN register_diff > 0
    THEN 'Mismatch: Register position exceeds SEC filing by ' || CAST(register_diff AS INTEGER) || ' shares'

    -- Stale outstanding basis only
    WHEN ABS(register_diff) = 0
         AND ABS(outstanding_diff) != 0
    THEN 'Mismatch: Stale outstanding basis (filer used ' || CAST(outstanding_basis AS INTEGER) ||
         ', actual ' || CAST(actual_outstanding AS INTEGER) || ')'

    -- Indirect holdings via CEDE (normal case where SEC > register)
    WHEN register_diff < 0 AND ABS(outstanding_diff) = 0
    THEN 'Match: Indirect holdings via CEDE & CO (' || CAST(ABS(register_diff) AS INTEGER) || ' shares)'

    -- Both issues
    WHEN register_diff < 0 AND ABS(outstanding_diff) != 0
    THEN 'Match: Indirect holdings via CEDE, but stale basis (' || CAST(outstanding_diff AS INTEGER) || ' shares off)'

    -- Rounding only
    WHEN ABS(register_diff) = 0
         AND ABS(outstanding_diff) = 0
         AND ABS((our_shares * 100.0 / NULLIF(actual_outstanding, 0)) - percent_reported) > 0.01
    THEN 'Match: Minor rounding difference'

    ELSE 'Review needed'
  END as explanation

FROM combined
ORDER BY filer_cik, event_date;
