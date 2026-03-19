-- ============================================================
-- analysis.sql
-- ============================================================
-- 5 SQL queries that mirror real supply chain analysis.
--
-- These are the same types of analyses done during the
-- IIM Mumbai supply chain internship — now formalized in SQL
-- and powered by a proper data warehouse structure.
--
-- How to run:
--   python scripts/run_sql.py sql/analysis.sql
-- ============================================================


-- ────────────────────────────────────────────
-- QUERY 1: 80/20 SKU Analysis (Pareto Principle)
-- ────────────────────────────────────────────
-- Business question: Which top 20% of SKUs generate 80% of revenue?
--
-- This is the classic Pareto analysis used in inventory management.
-- The idea: a small number of products drive most of the revenue,
-- so those are the SKUs you should focus on for stock management.
--
-- Logic:
--   1. Sum revenue by StockCode
--   2. Rank SKUs by revenue (highest first)
--   3. Calculate cumulative percentage of total revenue
--   4. Flag SKUs that fall within the top 80% of revenue

SELECT
    StockCode,
    Description,
    total_revenue,
    -- Show what % of total revenue this single SKU contributes
    ROUND(total_revenue * 100.0 / grand_total, 2)       AS pct_of_total,
    -- Cumulative % — running total as we go down the list
    ROUND(cumulative_revenue * 100.0 / grand_total, 2)   AS cumulative_pct,
    -- Classification: 'A' = top 80%, 'B' = next 15%, 'C' = bottom 5%
    -- (ABC analysis is the formal supply chain term for this)
    CASE
        WHEN ROUND(cumulative_revenue * 100.0 / grand_total, 2) <= 80 THEN 'A - Top 80%'
        WHEN ROUND(cumulative_revenue * 100.0 / grand_total, 2) <= 95 THEN 'B - Next 15%'
        ELSE 'C - Bottom 5%'
    END AS abc_class
FROM (
    SELECT
        p.StockCode,
        p.Description,
        SUM(f.revenue) AS total_revenue,
        -- Window function: running total of revenue, ordered by revenue descending
        SUM(SUM(f.revenue)) OVER (ORDER BY SUM(f.revenue) DESC) AS cumulative_revenue,
        -- Grand total of all revenue (same for every row)
        SUM(SUM(f.revenue)) OVER () AS grand_total
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.StockCode, p.Description
)
ORDER BY total_revenue DESC
LIMIT 50;


-- ────────────────────────────────────────────
-- QUERY 2: Slow-Moving Products (Last 6 Months)
-- ────────────────────────────────────────────
-- Business question: Which SKUs had the lowest sales volume
-- in the last 6 months of data?
--
-- Why this matters: Slow-moving inventory ties up capital and
-- warehouse space. In the IIM internship, this directly related
-- to identifying near-expiry cosmetics that weren't selling.
--
-- Logic:
--   1. Find the maximum date in the dataset
--   2. Filter to last 6 months
--   3. Sum quantity by SKU
--   4. Show the bottom 30 (slowest sellers)

SELECT
    p.StockCode,
    p.Description,
    p.category_bucket,
    SUM(f.Quantity)                AS total_qty_sold,
    COUNT(DISTINCT f.Invoice)     AS num_orders,
    ROUND(SUM(f.revenue), 2)      AS total_revenue
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
WHERE
    -- Filter to last 6 months of data
    -- We calculate this dynamically using the max date
    f.date_key >= DATE(
        (SELECT MAX(date_key) FROM dim_date),
        '-6 months'
    )
GROUP BY p.StockCode, p.Description, p.category_bucket
-- Only include products with at least 1 sale (exclude zero-sellers)
HAVING SUM(f.Quantity) > 0
ORDER BY total_qty_sold ASC
LIMIT 30;


-- ────────────────────────────────────────────
-- QUERY 3: Revenue by Month (Seasonality Analysis)
-- ────────────────────────────────────────────
-- Business question: What does the monthly revenue trend look like?
-- Are there seasonal spikes we can plan inventory around?
--
-- Why this matters: Seasonal demand planning is critical in retail.
-- If November/December spike (which they typically do for UK retail),
-- the warehouse needs to stock up in October.

SELECT
    d.year,
    d.month_number,
    d.month_name,
    COUNT(DISTINCT f.Invoice)     AS num_orders,
    SUM(f.Quantity)               AS total_qty,
    ROUND(SUM(f.revenue), 2)     AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month_number, d.month_name
ORDER BY d.year, d.month_number;


-- ────────────────────────────────────────────
-- QUERY 4: Country-Wise Revenue Concentration
-- ────────────────────────────────────────────
-- Business question: How concentrated is revenue across countries?
-- Is this business heavily UK-dependent?
--
-- Why this matters: Revenue concentration risk — if 90% of revenue
-- comes from one country, that's a supply chain risk.
-- Diversification is important for resilience.

SELECT
    c.Country,
    COUNT(DISTINCT c.CustomerID)   AS num_customers,
    COUNT(DISTINCT f.Invoice)      AS num_orders,
    ROUND(SUM(f.revenue), 2)       AS total_revenue,
    -- What percentage of total revenue comes from this country?
    ROUND(
        SUM(f.revenue) * 100.0 / SUM(SUM(f.revenue)) OVER (),
        2
    ) AS pct_of_total_revenue
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.Country
ORDER BY total_revenue DESC
LIMIT 20;


-- ────────────────────────────────────────────
-- QUERY 5: Cancellation Rate by Product
-- ────────────────────────────────────────────
-- Business question: Which SKUs get cancelled most often?
-- High cancellation rates signal quality issues, wrong descriptions,
-- or customer dissatisfaction — all critical for supply chain ops.
--
-- NOTE: We query from stg_retail (the RAW table), not ods_retail,
-- because ods_retail already has cancellations removed.
-- We need both cancelled and completed orders to calculate the rate.

SELECT
    StockCode,
    Description,
    -- Total number of order lines for this product
    COUNT(*)                                               AS total_lines,
    -- Count of cancelled lines (Invoice starts with 'C')
    SUM(CASE WHEN Invoice LIKE 'C%' THEN 1 ELSE 0 END)    AS cancelled_lines,
    -- Count of completed (non-cancelled) lines
    SUM(CASE WHEN Invoice NOT LIKE 'C%' THEN 1 ELSE 0 END) AS completed_lines,
    -- Cancellation rate as a percentage
    ROUND(
        SUM(CASE WHEN Invoice LIKE 'C%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS cancellation_rate_pct
FROM stg_retail
WHERE
    -- Only consider products that have at least 10 order lines
    -- (to avoid noise from rarely-ordered items)
    StockCode IS NOT NULL
GROUP BY StockCode, Description
HAVING COUNT(*) >= 10
ORDER BY cancellation_rate_pct DESC
LIMIT 30;
