-- ============================================================
-- transform.sql
-- ============================================================
-- Purpose: Create a cleaned "ODS" (Operational Data Store) table
--          from the raw staging table (stg_retail).
--
-- What gets cleaned:
--   1. Cancelled orders removed  (Invoice starts with 'C')
--   2. Rows with no Customer ID removed
--   3. Rows with Price <= 0 or Quantity <= 0 removed
--   4. A new 'revenue' column added (Quantity * Price)
--   5. InvoiceDate parsed into a clean date column
--
-- How to run:
--   python scripts/run_sql.py sql/transform.sql
-- ============================================================

-- Drop the table if it already exists so we can re-run safely
DROP TABLE IF EXISTS ods_retail;

-- Create the clean ODS table from stg_retail
CREATE TABLE ods_retail AS
SELECT
    -- Keep the Invoice number as-is (already filtered out cancellations below)
    Invoice,

    -- Stock code uniquely identifies each product
    StockCode,

    -- Product description (free text from the retailer)
    Description,

    -- Number of units purchased in this transaction line
    Quantity,

    -- Extract just the date part from InvoiceDate
    -- SQLite's DATE() function parses common date formats automatically
    DATE(InvoiceDate) AS InvoiceDate,

    -- Unit price per item in GBP (£)
    Price,

    -- Customer ID — we already filtered out NULLs (see WHERE clause)
    "Customer ID" AS CustomerID,

    -- Country where the customer is based
    Country,

    -- NEW COLUMN: total revenue for this transaction line
    -- This is the core metric for most supply chain analysis
    ROUND(Quantity * Price, 2) AS revenue

FROM stg_retail

WHERE
    -- 1. Remove cancelled orders:
    --    Cancelled invoices start with 'C' (e.g., C489449)
    --    We only want completed sales
    Invoice NOT LIKE 'C%'

    -- 2. Remove rows where Customer ID is missing:
    --    We can't do customer-level analysis without knowing who bought it
    AND "Customer ID" IS NOT NULL

    -- 3. Remove rows where quantity is zero or negative:
    --    These are typically adjustments, not real sales
    AND Quantity > 0

    -- 4. Remove rows where price is zero or negative:
    --    Free items or pricing errors — not useful for revenue analysis
    AND Price > 0;

-- Quick verification: show how many rows survived the cleaning
SELECT
    'ods_retail row count' AS metric,
    COUNT(*) AS value
FROM ods_retail;
