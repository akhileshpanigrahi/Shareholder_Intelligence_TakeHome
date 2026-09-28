-- Query 1: Top 10 holders as of August 31, 2026
-- Run date: September 1, 2026 00:00
-- Register/SEC columns: System view (what we knew on Aug 31)
-- Best estimate: Actual position (true ownership on Aug 31)

-- Calculate register position - SYSTEM VIEW (recorded_at)
WITH register_system_view AS (
  SELECT
    op.holder_id,
    op.shares
    + COALESCE(SUM(CASE WHEN re.to_holder_id = op.holder_id THEN re.shares ELSE 0 END), 0)
    - COALESCE(SUM(CASE WHEN re.from_holder_id = op.holder_id THEN re.shares ELSE 0 END), 0)
    AS register_shares
  FROM opening_positions op
  LEFT JOIN register_events re ON (
    (re.to_holder_id = op.holder_id OR re.from_holder_id = op.holder_id)
    AND re.recorded_at <= '2026-08-31 23:59:59'
    AND re.transfer_id NOT IN (
      SELECT reverses_transfer_id FROM register_events WHERE reverses_transfer_id IS NOT NULL
    )
  )
  WHERE op.holder_id != 'H001'
  GROUP BY op.holder_id, op.shares
),

-- Calculate register position - ACTUAL (effective_date)
register_actual AS (
  SELECT
    op.holder_id,
    op.shares
    + COALESCE(SUM(CASE WHEN re.to_holder_id = op.holder_id THEN re.shares ELSE 0 END), 0)
    - COALESCE(SUM(CASE WHEN re.from_holder_id = op.holder_id THEN re.shares ELSE 0 END), 0)
    AS actual_shares
  FROM opening_positions op
  LEFT JOIN register_events re ON (
    (re.to_holder_id = op.holder_id OR re.from_holder_id = op.holder_id)
    AND re.effective_date <= '2026-08-31'
    AND re.transfer_id NOT IN (
      SELECT reverses_transfer_id FROM register_events WHERE reverses_transfer_id IS NOT NULL
    )
  )
  WHERE op.holder_id != 'H001'
  GROUP BY op.holder_id, op.shares
),

-- Latest SEC filing - SYSTEM VIEW (filing_date)
latest_sec_system AS (
  SELECT
    bf1.filer_cik,
    bf1.shares_reported AS sec_shares
  FROM beneficial_filings bf1
  WHERE bf1.filing_date <= '2026-08-31'
    AND NOT EXISTS (
      SELECT 1 FROM beneficial_filings bf2
      WHERE bf2.amends_accession_no = bf1.accession_no
        AND bf2.filing_date <= '2026-08-31'
    )
),

-- Latest SEC filing - ACTUAL (event_date)
latest_sec_actual AS (
  SELECT
    bf1.filer_cik,
    bf1.shares_reported AS sec_actual_shares
  FROM beneficial_filings bf1
  WHERE bf1.event_date <= '2026-08-31'
    AND NOT EXISTS (
      SELECT 1 FROM beneficial_filings bf2
      WHERE bf2.amends_accession_no = bf1.accession_no
        AND bf2.event_date <= '2026-08-31'
    )
),

-- Map to holder_id
sec_system_by_holder AS (
  SELECT m.holder_id, s.sec_shares
  FROM latest_sec_system s
  JOIN holder_filer_mapping m ON s.filer_cik = m.filer_cik
),

sec_actual_by_holder AS (
  SELECT m.holder_id, s.sec_actual_shares
  FROM latest_sec_actual s
  JOIN holder_filer_mapping m ON s.filer_cik = m.filer_cik
),

-- Holder names
holder_names AS (
  SELECT h1.holder_id, h1.holder_name, h1.holder_type
  FROM holders h1
  WHERE h1.version = (SELECT MAX(h2.version) FROM holders h2 WHERE h2.holder_id = h1.holder_id)
),

-- Get all unique holder_ids (including unmapped SEC filers)
all_holders AS (
  SELECT holder_id FROM register_system_view
  UNION
  SELECT holder_id FROM sec_system_by_holder
  UNION
  SELECT holder_id FROM register_actual
  UNION
  SELECT holder_id FROM sec_actual_by_holder
  UNION
  -- Include unmapped SEC filers (beneficial owners with no direct register presence)
  SELECT 'UNMAPPED_' || filer_cik AS holder_id
  FROM latest_sec_system
  WHERE filer_cik NOT IN (SELECT filer_cik FROM holder_filer_mapping)
  UNION
  SELECT 'UNMAPPED_' || filer_cik AS holder_id
  FROM latest_sec_actual
  WHERE filer_cik NOT IN (SELECT filer_cik FROM holder_filer_mapping)
),

-- Combine all sources
combined AS (
  SELECT
    ah.holder_id,
    -- Handle unmapped SEC filers (get name from beneficial_filings)
    CASE
      WHEN ah.holder_id LIKE 'UNMAPPED_%' THEN
        (SELECT filer_name
         FROM beneficial_filings
         WHERE filer_cik = REPLACE(ah.holder_id, 'UNMAPPED_', '')
         LIMIT 1)
      ELSE hn.holder_name
    END AS holder_name,
    -- Unmapped filers are typically institutions
    CASE
      WHEN ah.holder_id LIKE 'UNMAPPED_%' THEN 'institution'
      ELSE hn.holder_type
    END AS holder_type,
    COALESCE(rsv.register_shares, 0) AS register_shares,
    -- For unmapped filers, get SEC shares from latest_sec_system directly
    CASE
      WHEN ah.holder_id LIKE 'UNMAPPED_%' THEN
        COALESCE((SELECT sec_shares FROM latest_sec_system
                  WHERE filer_cik = REPLACE(ah.holder_id, 'UNMAPPED_', '')), 0)
      ELSE COALESCE(ss.sec_shares, 0)
    END AS sec_shares,
    -- Best estimate calculation
    CASE
      WHEN ah.holder_id LIKE 'UNMAPPED_%' THEN
        -- Unmapped filers: only have SEC data, no register presence
        COALESCE((SELECT sec_actual_shares FROM latest_sec_actual
                  WHERE filer_cik = REPLACE(ah.holder_id, 'UNMAPPED_', '')), 0)
      WHEN ra.actual_shares IS NOT NULL AND sa.sec_actual_shares IS NOT NULL THEN
        CASE WHEN ra.actual_shares > sa.sec_actual_shares THEN ra.actual_shares ELSE sa.sec_actual_shares END
      ELSE COALESCE(ra.actual_shares, sa.sec_actual_shares, 0)
    END AS best_estimate
  FROM all_holders ah
  LEFT JOIN holder_names hn ON ah.holder_id = hn.holder_id
  LEFT JOIN register_system_view rsv ON ah.holder_id = rsv.holder_id
  LEFT JOIN sec_system_by_holder ss ON ah.holder_id = ss.holder_id
  LEFT JOIN register_actual ra ON ah.holder_id = ra.holder_id
  LEFT JOIN sec_actual_by_holder sa ON ah.holder_id = sa.holder_id
)

SELECT
  holder_id,
  holder_name,
  holder_type,
  CAST(register_shares AS INTEGER) AS register_shares,
  CAST(sec_shares AS INTEGER) AS sec_shares,
  CAST(best_estimate AS INTEGER) AS best_estimate
FROM combined
ORDER BY best_estimate DESC
LIMIT 10;
