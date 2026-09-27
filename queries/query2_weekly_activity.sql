-- Query 2: Weekly Activity by Holder Type (Aug 24-28, 2026)
-- Run date: August 31, 2026 16:00 (Monday after market close)
-- Shows who bought and sold during the week, grouped by holder type

-- Get latest holder version as of Aug 31
WITH latest_holders AS (
  SELECT
    h1.holder_id,
    h1.holder_type
  FROM holders h1
  WHERE h1.version = (
    SELECT MAX(h2.version)
    FROM holders h2
    WHERE h2.holder_id = h1.holder_id
      AND h2.valid_from <= '2026-08-31'
  )
),

-- Filter relevant events (Aug 24-28, recorded by Aug 31 4pm, not reversed)
relevant_events AS (
  SELECT
    event_id,
    transfer_id,
    from_holder_id,
    to_holder_id,
    shares,
    effective_date
  FROM register_events
  WHERE effective_date BETWEEN '2026-08-24' AND '2026-08-28'
    AND recorded_at <= '2026-08-31 16:00:00'
    AND transfer_id NOT IN (
      SELECT reverses_transfer_id
      FROM register_events
      WHERE reverses_transfer_id IS NOT NULL
    )
),

-- Calculate buys per holder type
buys AS (
  SELECT
    lh.holder_type,
    SUM(re.shares) as shares_bought
  FROM relevant_events re
  JOIN latest_holders lh ON re.to_holder_id = lh.holder_id
  WHERE re.to_holder_id IS NOT NULL
  GROUP BY lh.holder_type
),

-- Calculate sells per holder type
sells AS (
  SELECT
    lh.holder_type,
    SUM(re.shares) as shares_sold
  FROM relevant_events re
  JOIN latest_holders lh ON re.from_holder_id = lh.holder_id
  WHERE re.from_holder_id IS NOT NULL
  GROUP BY lh.holder_type
),

-- Get all active holder types (who bought OR sold)
all_active_types AS (
  SELECT holder_type FROM buys
  UNION
  SELECT holder_type FROM sells
)

-- Final result: combine buys and sells
SELECT
  at.holder_type,
  CAST(COALESCE(b.shares_bought, 0) AS INTEGER) as shares_bought,
  CAST(COALESCE(s.shares_sold, 0) AS INTEGER) as shares_sold,
  CAST(COALESCE(b.shares_bought, 0) - COALESCE(s.shares_sold, 0) AS INTEGER) as net_change
FROM all_active_types at
LEFT JOIN buys b ON at.holder_type = b.holder_type
LEFT JOIN sells s ON at.holder_type = s.holder_type
ORDER BY at.holder_type;
