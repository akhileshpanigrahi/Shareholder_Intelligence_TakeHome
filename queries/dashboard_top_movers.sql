-- Dashboard Query: Top Weekly Movers
-- Identifies top 5 individual holders by absolute net share change
-- Date range: August 24-28, 2026 (week ending Monday, August 31)

-- Get latest holder version for names and types
WITH latest_holders AS (
  SELECT
    h1.holder_id,
    h1.holder_name,
    h1.holder_type
  FROM holders h1
  WHERE h1.version = (
    SELECT MAX(h2.version)
    FROM holders h2
    WHERE h2.holder_id = h1.holder_id
      AND h2.valid_from <= '2026-08-31'
  )
),

-- Filter to relevant week's events, excluding reversals
relevant_events AS (
  SELECT
    event_id,
    from_holder_id,
    to_holder_id,
    shares,
    effective_date
  FROM register_events
  WHERE effective_date BETWEEN '2026-08-24' AND '2026-08-28'
    AND recorded_at <= '2026-08-31 16:00:00'  -- Knowledge cutoff
    AND transfer_id NOT IN (
      SELECT reverses_transfer_id
      FROM register_events
      WHERE reverses_transfer_id IS NOT NULL
    )
    AND from_holder_id IS NOT NULL  -- Exclude equity issuance
    AND to_holder_id IS NOT NULL     -- Exclude buybacks
),

-- Calculate activity per holder
holder_activity AS (
  SELECT
    holder_id,
    SUM(shares_bought) as shares_bought,
    SUM(shares_sold) as shares_sold,
    SUM(shares_bought) - SUM(shares_sold) as net_change
  FROM (
    -- Buys (holder received shares)
    SELECT
      re.to_holder_id as holder_id,
      re.shares as shares_bought,
      0 as shares_sold
    FROM relevant_events re

    UNION ALL

    -- Sells (holder transferred away shares)
    SELECT
      re.from_holder_id as holder_id,
      0 as shares_bought,
      re.shares as shares_sold
    FROM relevant_events re
  )
  GROUP BY holder_id
)

-- Final output: Top 5 by absolute net change
SELECT
  ha.holder_id,
  lh.holder_name,
  lh.holder_type,
  CAST(ha.shares_bought AS INTEGER) as shares_bought,
  CAST(ha.shares_sold AS INTEGER) as shares_sold,
  CAST(ha.net_change AS INTEGER) as net_change,
  CASE
    WHEN ha.net_change > 0 THEN 'buyer'
    WHEN ha.net_change < 0 THEN 'seller'
    ELSE 'neutral'
  END as activity_type
FROM holder_activity ha
JOIN latest_holders lh ON ha.holder_id = lh.holder_id
WHERE ha.holder_id != 'H001'  -- Exclude CEDE & CO (not a beneficial owner)
  AND (ha.shares_bought > 0 OR ha.shares_sold > 0)  -- Must have activity
ORDER BY ABS(ha.net_change) DESC
LIMIT 5;
