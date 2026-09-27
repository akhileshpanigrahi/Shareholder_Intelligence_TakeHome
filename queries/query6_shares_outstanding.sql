-- Query 6: Shares Outstanding Reconciliation
-- Prove whether register total agrees with company's shares outstanding
-- Check dates: June 30, 2026 and August 3, 2026 (closest to August 31)

-- Calculate register total for each date
WITH register_totals AS (
  SELECT
    as_of_date,
    opening_total,
    COALESCE(equity_issued, 0) as equity_issued,
    COALESCE(shares_repurchased, 0) as shares_repurchased,
    opening_total + COALESCE(equity_issued, 0) - COALESCE(shares_repurchased, 0) as register_total
  FROM (
    -- June 30, 2026
    SELECT
      '2026-06-30' as as_of_date,
      (SELECT SUM(shares) FROM opening_positions WHERE as_of_date = '2026-05-31') as opening_total,
      (
        SELECT SUM(re.shares)
        FROM register_events re
        WHERE re.from_holder_id IS NULL  -- Equity issuance
          AND re.effective_date <= '2026-06-30'
          AND re.transfer_id NOT IN (
            SELECT reverses_transfer_id
            FROM register_events
            WHERE reverses_transfer_id IS NOT NULL
          )
      ) as equity_issued,
      (
        SELECT SUM(re.shares)
        FROM register_events re
        WHERE re.to_holder_id IS NULL  -- Share buyback/retirement
          AND re.effective_date <= '2026-06-30'
          AND re.transfer_id NOT IN (
            SELECT reverses_transfer_id
            FROM register_events
            WHERE reverses_transfer_id IS NOT NULL
          )
      ) as shares_repurchased

    UNION ALL

    -- August 3, 2026 (closest to August 31)
    SELECT
      '2026-08-03' as as_of_date,
      (SELECT SUM(shares) FROM opening_positions WHERE as_of_date = '2026-05-31') as opening_total,
      (
        SELECT SUM(re.shares)
        FROM register_events re
        WHERE re.from_holder_id IS NULL  -- Equity issuance
          AND re.effective_date <= '2026-08-03'
          AND re.transfer_id NOT IN (
            SELECT reverses_transfer_id
            FROM register_events
            WHERE reverses_transfer_id IS NOT NULL
          )
      ) as equity_issued,
      (
        SELECT SUM(re.shares)
        FROM register_events re
        WHERE re.to_holder_id IS NULL  -- Share buyback/retirement
          AND re.effective_date <= '2026-08-03'
          AND re.transfer_id NOT IN (
            SELECT reverses_transfer_id
            FROM register_events
            WHERE reverses_transfer_id IS NOT NULL
          )
      ) as shares_repurchased
  )
),

-- Get company-reported shares outstanding for these dates
reported_outstanding AS (
  SELECT
    as_of_date,
    shares_outstanding as reported_shares,
    source_form,
    published_date
  FROM shares_outstanding
  WHERE as_of_date IN ('2026-06-30', '2026-08-03')
)

-- Final comparison
SELECT
  rt.as_of_date,
  CAST(rt.opening_total AS INTEGER) as opening_total_may_31,
  CAST(rt.equity_issued AS INTEGER) as equity_issued,
  CAST(rt.shares_repurchased AS INTEGER) as shares_repurchased,
  CAST(rt.register_total AS INTEGER) as register_total,
  CAST(ro.reported_shares AS INTEGER) as reported_outstanding,
  CAST(rt.register_total - ro.reported_shares AS INTEGER) as difference,

  -- Explanation
  CASE
    WHEN ABS(rt.register_total - ro.reported_shares) < 0.01 THEN 'Perfect reconciliation'
    WHEN rt.register_total > ro.reported_shares THEN
      'Register exceeds reported by ' || CAST(ABS(rt.register_total - ro.reported_shares) AS INTEGER) || ' shares'
    ELSE
      'Register below reported by ' || CAST(ABS(rt.register_total - ro.reported_shares) AS INTEGER) || ' shares'
  END as explanation,

  ro.source_form as filing_source,
  ro.published_date as date_published

FROM register_totals rt
INNER JOIN reported_outstanding ro ON rt.as_of_date = ro.as_of_date
ORDER BY rt.as_of_date;
