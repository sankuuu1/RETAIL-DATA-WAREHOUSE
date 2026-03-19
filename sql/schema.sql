-- ============================================================
-- schema.sql
-- ============================================================
-- Purpose: Build a STAR SCHEMA from the cleaned ods_retail table.
--
-- Star schema has:
--   1 fact table   → fact_sales (one row per transaction line)
--   3 dim tables   → dim_date, dim_product, dim_customer
--
-- Why a star schema?
--   It's the standard structure for analytics / BI dashboards.
--   Fact table holds the numbers (quantity, price, revenue).
--   Dimension tables hold the descriptive attributes (who, what, when).
--
-- How to run:
--   python scripts/run_sql.py sql/schema.sql
-- ============================================================


-- ────────────────────────────────────────────
-- DIMENSION 1: dim_date
-- ────────────────────────────────────────────
-- One row per unique date in the dataset.
-- Power BI can use this for time-based slicing.

DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date AS
SELECT
    -- Use the date string itself as the key (YYYY-MM-DD format)
    InvoiceDate                                        AS date_key,

    -- Full date for display purposes
    InvoiceDate                                        AS full_date,

    -- Week number (1–53) — useful for weekly sales reports
    CAST(STRFTIME('%W', InvoiceDate) AS INTEGER)       AS week_number,

    -- Month name — e.g., "January", "February"
    -- SQLite doesn't have a built-in month name function,
    -- so we use CASE on the month number
    CASE CAST(STRFTIME('%m', InvoiceDate) AS INTEGER)
        WHEN 1  THEN 'January'
        WHEN 2  THEN 'February'
        WHEN 3  THEN 'March'
        WHEN 4  THEN 'April'
        WHEN 5  THEN 'May'
        WHEN 6  THEN 'June'
        WHEN 7  THEN 'July'
        WHEN 8  THEN 'August'
        WHEN 9  THEN 'September'
        WHEN 10 THEN 'October'
        WHEN 11 THEN 'November'
        WHEN 12 THEN 'December'
    END                                                AS month_name,

    -- Month number (1–12) — handy for sorting months in order
    CAST(STRFTIME('%m', InvoiceDate) AS INTEGER)       AS month_number,

    -- Quarter (1–4) — common in business reporting
    -- Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec
    CASE
        WHEN CAST(STRFTIME('%m', InvoiceDate) AS INTEGER) <= 3  THEN 1
        WHEN CAST(STRFTIME('%m', InvoiceDate) AS INTEGER) <= 6  THEN 2
        WHEN CAST(STRFTIME('%m', InvoiceDate) AS INTEGER) <= 9  THEN 3
        ELSE 4
    END                                                AS quarter,

    -- Year (e.g., 2009, 2010, 2011)
    CAST(STRFTIME('%Y', InvoiceDate) AS INTEGER)       AS year,

    -- Is it a weekend? (Saturday = 6, Sunday = 0 in SQLite's %w)
    -- %w returns 0 for Sunday, 6 for Saturday
    CASE
        WHEN CAST(STRFTIME('%w', InvoiceDate) AS INTEGER) IN (0, 6)
        THEN 1
        ELSE 0
    END                                                AS is_weekend

FROM (
    -- Get unique dates only — we want one row per date
    SELECT DISTINCT InvoiceDate
    FROM ods_retail
    WHERE InvoiceDate IS NOT NULL
)
ORDER BY date_key;


-- ────────────────────────────────────────────
-- DIMENSION 2: dim_product
-- ────────────────────────────────────────────
-- One row per unique StockCode.
-- Includes a 'category_bucket' column that groups products
-- into broad categories based on keywords in the description.

DROP TABLE IF EXISTS dim_product;

CREATE TABLE dim_product AS
SELECT
    -- Auto-incrementing key for this dimension
    ROW_NUMBER() OVER (ORDER BY StockCode)            AS product_key,

    -- The original StockCode from the retailer
    StockCode,

    -- Product description (we take the most common description
    -- for each StockCode, since some codes have slight variations)
    Description,

    -- Category bucket — we look for keywords in the description
    -- and assign a broad category. This is the same approach
    -- you'd use for 80/20 SKU analysis in supply chain.
    CASE
        -- Seasonal items: Christmas, Easter, Halloween themed
        WHEN UPPER(Description) LIKE '%CHRISTMAS%'
          OR UPPER(Description) LIKE '%XMAS%'
          OR UPPER(Description) LIKE '%EASTER%'
          OR UPPER(Description) LIKE '%HALLOWEEN%'
          OR UPPER(Description) LIKE '%VALENTINE%'
            THEN 'Seasonal'

        -- Kitchen items
        WHEN UPPER(Description) LIKE '%KITCHEN%'
          OR UPPER(Description) LIKE '%COOK%'
          OR UPPER(Description) LIKE '%MUG%'
          OR UPPER(Description) LIKE '%CUP%'
          OR UPPER(Description) LIKE '%PLATE%'
          OR UPPER(Description) LIKE '%BOWL%'
          OR UPPER(Description) LIKE '%TEA%'
          OR UPPER(Description) LIKE '%COFFEE%'
          OR UPPER(Description) LIKE '%SPOON%'
          OR UPPER(Description) LIKE '%FORK%'
            THEN 'Kitchen'

        -- Home & Garden
        WHEN UPPER(Description) LIKE '%GARDEN%'
          OR UPPER(Description) LIKE '%CANDLE%'
          OR UPPER(Description) LIKE '%LIGHT%'
          OR UPPER(Description) LIKE '%LANTERN%'
          OR UPPER(Description) LIKE '%FRAME%'
          OR UPPER(Description) LIKE '%CLOCK%'
          OR UPPER(Description) LIKE '%DOOR%'
          OR UPPER(Description) LIKE '%WALL%'
          OR UPPER(Description) LIKE '%CUSHION%'
          OR UPPER(Description) LIKE '%CURTAIN%'
            THEN 'Home & Garden'

        -- Gifts & wrapping
        WHEN UPPER(Description) LIKE '%GIFT%'
          OR UPPER(Description) LIKE '%WRAP%'
          OR UPPER(Description) LIKE '%RIBBON%'
          OR UPPER(Description) LIKE '%BOX%'
          OR UPPER(Description) LIKE '%CARD%'
            THEN 'Gifts'

        -- Bags & accessories
        WHEN UPPER(Description) LIKE '%BAG%'
          OR UPPER(Description) LIKE '%PURSE%'
          OR UPPER(Description) LIKE '%WALLET%'
          OR UPPER(Description) LIKE '%CASE%'
            THEN 'Bags & Accessories'

        -- Stationery
        WHEN UPPER(Description) LIKE '%PEN%'
          OR UPPER(Description) LIKE '%PENCIL%'
          OR UPPER(Description) LIKE '%NOTEBOOK%'
          OR UPPER(Description) LIKE '%PAPER%'
          OR UPPER(Description) LIKE '%STAMP%'
            THEN 'Stationery'

        -- Novelty / fun items
        WHEN UPPER(Description) LIKE '%TOY%'
          OR UPPER(Description) LIKE '%GAME%'
          OR UPPER(Description) LIKE '%MAGNET%'
          OR UPPER(Description) LIKE '%NOVELTY%'
          OR UPPER(Description) LIKE '%PARTY%'
            THEN 'Novelty'

        -- Everything else
        ELSE 'Other'
    END AS category_bucket

FROM (
    -- For each StockCode, pick the most frequently used Description
    -- (some codes have slight spelling variations across rows)
    SELECT
        StockCode,
        Description,
        ROW_NUMBER() OVER (
            PARTITION BY StockCode
            ORDER BY COUNT(*) DESC
        ) AS rn
    FROM ods_retail
    GROUP BY StockCode, Description
)
WHERE rn = 1
ORDER BY StockCode;


-- ────────────────────────────────────────────
-- DIMENSION 3: dim_customer
-- ────────────────────────────────────────────
-- One row per unique CustomerID.
-- Includes a 'customer_segment' based on total spend:
--   High Value   = top 20% spenders
--   Mid Value    = middle 30% spenders
--   Low Value    = bottom 50% spenders

DROP TABLE IF EXISTS dim_customer;

CREATE TABLE dim_customer AS
SELECT
    ROW_NUMBER() OVER (ORDER BY CustomerID)  AS customer_key,
    CustomerID,
    Country,

    -- Segment customers by their total lifetime spend
    -- We use NTILE(10) to split into deciles, then bucket into 3 segments
    CASE
        WHEN spend_decile >= 9 THEN 'High Value'   -- top 20%  (deciles 9-10)
        WHEN spend_decile >= 6 THEN 'Mid Value'    -- middle 30% (deciles 6-8)
        ELSE 'Low Value'                            -- bottom 50% (deciles 1-5)
    END AS customer_segment

FROM (
    SELECT
        CustomerID,
        Country,
        -- NTILE(10) divides all customers into 10 equal groups
        -- ordered by total spend. Group 10 = highest spenders.
        NTILE(10) OVER (ORDER BY total_spend) AS spend_decile
    FROM (
        -- First, calculate each customer's total revenue
        SELECT
            CustomerID,
            -- Take the most common country for this customer
            Country,
            SUM(revenue) AS total_spend
        FROM ods_retail
        GROUP BY CustomerID
    )
)
ORDER BY CustomerID;


-- ────────────────────────────────────────────
-- FACT TABLE: fact_sales
-- ────────────────────────────────────────────
-- One row per transaction line (same grain as ods_retail).
-- Contains foreign keys to each dimension table
-- and the numeric measures (quantity, price, revenue).

DROP TABLE IF EXISTS fact_sales;

CREATE TABLE fact_sales AS
SELECT
    -- Foreign key to dim_date
    o.InvoiceDate                   AS date_key,

    -- Foreign key to dim_product
    p.product_key                   AS product_key,

    -- Foreign key to dim_customer
    c.customer_key                  AS customer_key,

    -- The original invoice number (for drill-down)
    o.Invoice,

    -- ── Measures (the numbers we analyze) ──
    o.Quantity,
    o.Price,
    o.revenue

FROM ods_retail o

-- Join to dim_product on StockCode
LEFT JOIN dim_product p
    ON o.StockCode = p.StockCode

-- Join to dim_customer on CustomerID
LEFT JOIN dim_customer c
    ON o.CustomerID = c.CustomerID;


-- ────────────────────────────────────────────
-- Verification: print row counts for all tables
-- ────────────────────────────────────────────

SELECT 'dim_date rows' AS table_name, COUNT(*) AS row_count FROM dim_date;

SELECT 'dim_product rows' AS table_name, COUNT(*) AS row_count FROM dim_product;

SELECT 'dim_customer rows' AS table_name, COUNT(*) AS row_count FROM dim_customer;

SELECT 'fact_sales rows' AS table_name, COUNT(*) AS row_count FROM fact_sales;
