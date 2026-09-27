-- ============================================================================
-- 1. CLEANUP/IDEMPOTENCY PROTOCOL
-- ============================================================================
DROP TABLE IF EXISTS register_events;
DROP TABLE IF EXISTS opening_positions;
DROP TABLE IF EXISTS beneficial_filings;
DROP TABLE IF EXISTS shares_outstanding;
DROP TABLE IF EXISTS holders;

-- ============================================================================
-- 2. CORE TARGET TABLES DEFINITION
-- ============================================================================

-- Reference: data/holders.csv
-- Contains tracking versions for historical owner type or name changes
CREATE TABLE holders (
    holder_id TEXT NOT NULL,
    version INT NOT NULL,
    valid_from TEXT NOT NULL,  -- Keep text for cross-platform SQLite compatibility (YYYY-MM-DD)
    holder_name TEXT NOT NULL,
    holder_type TEXT NOT NULL,
    country TEXT NOT NULL,
    PRIMARY KEY (holder_id, version)
);

-- Reference: data/opening_positions.csv
-- Base share balance baseline positions at the close of 31 May 2026
CREATE TABLE opening_positions (
    as_of_date TEXT NOT NULL,  -- Date anchor for historical reconstruction
    holder_id TEXT NOT NULL,
    shares REAL NOT NULL,
    PRIMARY KEY (as_of_date, holder_id)
);

-- Reference: data/register_events.csv
-- Immutable ledger tracking movements between share register entities
CREATE TABLE register_events (
    event_id TEXT PRIMARY KEY,
    transfer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_holder_id TEXT NULL,  -- NULL permitted for equity issuance events
    to_holder_id TEXT NULL,    -- NULL permitted for share retirement/buyback events
    shares REAL NOT NULL,
    effective_date TEXT NOT NULL,  -- Legal execution date (When it happened)
    recorded_at TEXT NOT NULL,     -- Administrative entry stamp (When we learned it)
    reverses_transfer_id TEXT NULL, -- Lineage validation flag for transactional offsets
    note TEXT NULL
);

-- Reference: data/shares_outstanding.csv
-- Corporate record tracking published equity parameters
CREATE TABLE shares_outstanding (
    as_of_date TEXT NOT NULL,      -- Target date reporting criteria counts from
    shares_outstanding REAL NOT NULL,
    source_form TEXT NOT NULL,     -- Filing reference vehicle (10-Q, 8-K)
    published_date TEXT NOT NULL,  -- Public release marker
    PRIMARY KEY (as_of_date, source_form)
);

-- Reference: data/beneficial_filings.csv
-- SEC disclosures reflecting external ownership windows (SC 13D/G)
CREATE TABLE beneficial_filings (
    accession_no TEXT PRIMARY KEY,
    form_type TEXT NOT NULL,
    filer_name TEXT NOT NULL,
    filer_cik TEXT NOT NULL,
    filing_date TEXT NOT NULL,          -- Entry date into the SEC database
    event_date TEXT NOT NULL,           -- Direct legal transactional date
    shares_reported REAL NOT NULL,
    percent_reported REAL NOT NULL,
    outstanding_basis REAL NOT NULL,
    amends_accession_no TEXT NULL      -- Points to prior historical version
);
