-- Query 4: Watch List - Threshold Crossings and Form Changes
-- Detects holders who crossed 5% or 10% thresholds (either direction)
-- and filers who changed from 13G to 13D (passive to activist)
-- Date range: June 1 - August 31, 2026

-- Get each filing with details from the previous filing by same filer
WITH filings_with_previous AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    form_type,
    percent_reported,
    -- Get previous filing details using window functions
    LAG(percent_reported) OVER (PARTITION BY filer_cik ORDER BY event_date, filing_date) as prev_percent,
    LAG(form_type) OVER (PARTITION BY filer_cik ORDER BY event_date, filing_date) as prev_form,
    LAG(event_date) OVER (PARTITION BY filer_cik ORDER BY event_date, filing_date) as prev_event_date
  FROM beneficial_filings
),

-- Detect crossings above 5% threshold
cross_above_5 AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    'Crossed above 5%' as alert_type,
    COALESCE(prev_percent, 0.0) as previous_percent,
    percent_reported as current_percent,
    NULL as previous_form,
    NULL as current_form
  FROM filings_with_previous
  WHERE event_date BETWEEN '2026-06-01' AND '2026-08-31'
    AND (prev_percent IS NULL OR prev_percent < 5.0)
    AND percent_reported >= 5.0
),

-- Detect crossings below 5% threshold
cross_below_5 AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    'Crossed below 5%' as alert_type,
    prev_percent as previous_percent,
    percent_reported as current_percent,
    NULL as previous_form,
    NULL as current_form
  FROM filings_with_previous
  WHERE event_date BETWEEN '2026-06-01' AND '2026-08-31'
    AND prev_percent >= 5.0
    AND percent_reported < 5.0
),

-- Detect crossings above 10% threshold
cross_above_10 AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    'Crossed above 10%' as alert_type,
    COALESCE(prev_percent, 0.0) as previous_percent,
    percent_reported as current_percent,
    NULL as previous_form,
    NULL as current_form
  FROM filings_with_previous
  WHERE event_date BETWEEN '2026-06-01' AND '2026-08-31'
    AND (prev_percent IS NULL OR prev_percent < 10.0)
    AND percent_reported >= 10.0
),

-- Detect crossings below 10% threshold
cross_below_10 AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    'Crossed below 10%' as alert_type,
    prev_percent as previous_percent,
    percent_reported as current_percent,
    NULL as previous_form,
    NULL as current_form
  FROM filings_with_previous
  WHERE event_date BETWEEN '2026-06-01' AND '2026-08-31'
    AND prev_percent >= 10.0
    AND percent_reported < 10.0
),

-- Detect form type changes from 13G to 13D (passive to activist)
form_changes AS (
  SELECT
    filer_cik,
    filer_name,
    event_date,
    filing_date,
    'Changed from 13G to 13D' as alert_type,
    NULL as previous_percent,
    NULL as current_percent,
    prev_form as previous_form,
    form_type as current_form
  FROM filings_with_previous
  WHERE event_date BETWEEN '2026-06-01' AND '2026-08-31'
    AND prev_form LIKE '%13G%'
    AND form_type LIKE '%13D%'
)

-- Combine all alerts
SELECT
  filer_cik,
  filer_name,
  event_date as date_happened,
  filing_date as date_learned,
  alert_type,

  -- Additional context for threshold crossings
  CASE
    WHEN previous_percent IS NOT NULL
    THEN ROUND(previous_percent, 2)
    ELSE NULL
  END as previous_percent,

  CASE
    WHEN current_percent IS NOT NULL
    THEN ROUND(current_percent, 2)
    ELSE NULL
  END as current_percent,

  -- Additional context for form changes
  previous_form,
  current_form

FROM (
  SELECT * FROM cross_above_5
  UNION ALL
  SELECT * FROM cross_below_5
  UNION ALL
  SELECT * FROM cross_above_10
  UNION ALL
  SELECT * FROM cross_below_10
  UNION ALL
  SELECT * FROM form_changes
)
ORDER BY event_date, filing_date, filer_cik, alert_type;
