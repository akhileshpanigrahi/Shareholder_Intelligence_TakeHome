-- Query 5: Sable Point Temporal Comparison
-- Shows Sable Point Advisors register position on July 31, 2026
-- from two perspectives: "as we knew it then" vs "as we know it now"

-- Position as we knew it on July 31, 2026
-- Include all transfers recorded by July 31, excluding reversal events
WITH position_then AS (
  SELECT
    'H011' as holder_id,
    COALESCE(op.shares, 0)
    + COALESCE(SUM(CASE WHEN re.to_holder_id = 'H011' THEN re.shares ELSE 0 END), 0)
    - COALESCE(SUM(CASE WHEN re.from_holder_id = 'H011' THEN re.shares ELSE 0 END), 0)
    AS shares
  FROM opening_positions op
  LEFT JOIN register_events re ON (
    (re.to_holder_id = 'H011' OR re.from_holder_id = 'H011')
    AND re.effective_date <= '2026-07-31'
    AND re.recorded_at <= '2026-07-31 23:59:59'
    AND re.event_type != 'reversal'  -- Exclude reversal events (we didn't know about them yet)
  )
  WHERE op.holder_id = 'H011'
    AND op.as_of_date = '2026-05-31'
),

-- Position as we know it today (Sept 1, 2026)
-- Include all transfers recorded by Sept 1, including reversals
position_now AS (
  SELECT
    'H011' as holder_id,
    COALESCE(op.shares, 0)
    + COALESCE(SUM(CASE WHEN re.to_holder_id = 'H011' THEN re.shares ELSE 0 END), 0)
    - COALESCE(SUM(CASE WHEN re.from_holder_id = 'H011' THEN re.shares ELSE 0 END), 0)
    AS shares
  FROM opening_positions op
  LEFT JOIN register_events re ON (
    (re.to_holder_id = 'H011' OR re.from_holder_id = 'H011')
    AND re.effective_date <= '2026-07-31'
    AND re.recorded_at <= '2026-09-01 23:59:59'
    -- Include ALL events (transfers and reversals) - natural netting occurs
  )
  WHERE op.holder_id = 'H011'
    AND op.as_of_date = '2026-05-31'
),

-- Get holder details
holder_info AS (
  SELECT
    holder_id,
    holder_name
  FROM holders
  WHERE holder_id = 'H011'
    AND version = (
      SELECT MAX(version)
      FROM holders
      WHERE holder_id = 'H011'
    )
),

-- Find the late-recorded events that caused the difference
late_events AS (
  SELECT
    re.event_id,
    re.transfer_id,
    re.event_type,
    re.shares,
    re.effective_date,
    re.recorded_at,
    re.reverses_transfer_id,
    re.note
  FROM register_events re
  WHERE (re.to_holder_id = 'H011' OR re.from_holder_id = 'H011')
    AND re.effective_date <= '2026-07-31'
    AND re.recorded_at > '2026-07-31 23:59:59'
    AND re.recorded_at <= '2026-09-01 23:59:59'

  UNION ALL

  -- Also include original transfers that were reversed after July 31
  SELECT
    re.event_id,
    re.transfer_id,
    re.event_type,
    re.shares,
    re.effective_date,
    re.recorded_at,
    re.reverses_transfer_id,
    re.note
  FROM register_events re
  WHERE (re.to_holder_id = 'H011' OR re.from_holder_id = 'H011')
    AND re.effective_date <= '2026-07-31'
    AND re.recorded_at <= '2026-07-31 23:59:59'
    AND re.transfer_id IN (
      SELECT reverses_transfer_id
      FROM register_events
      WHERE reverses_transfer_id IS NOT NULL
        AND recorded_at > '2026-07-31 23:59:59'
        AND recorded_at <= '2026-09-01 23:59:59'
    )
)

-- Final output
SELECT
  hi.holder_id,
  hi.holder_name,
  '2026-07-31' as as_of_date,
  CAST(pt.shares AS INTEGER) as position_then,
  CAST(pn.shares AS INTEGER) as position_now,
  CAST(pn.shares - pt.shares AS INTEGER) as difference,

  -- Explanation of the difference
  CASE
    WHEN ABS(pn.shares - pt.shares) < 0.01 THEN 'No change - positions match'
    WHEN pn.shares - pt.shares < 0 THEN
      'Position decreased by ' || CAST(ABS(pn.shares - pt.shares) AS INTEGER) ||
      ' shares due to late-recorded reversal(s) after July 31'
    ELSE
      'Position increased by ' || CAST(pn.shares - pt.shares AS INTEGER) ||
      ' shares due to late-recorded event(s) after July 31'
  END as explanation,

  -- Show details of late events
  (
    SELECT GROUP_CONCAT(
      'Event ' || event_id || ' (' || event_type || '): ' ||
      CAST(shares AS INTEGER) || ' shares on ' || effective_date ||
      ', recorded ' || recorded_at ||
      CASE WHEN note IS NOT NULL THEN ' - ' || note ELSE '' END,
      '; '
    )
    FROM late_events
  ) as late_events_detail

FROM holder_info hi
CROSS JOIN position_then pt
CROSS JOIN position_now pn;
