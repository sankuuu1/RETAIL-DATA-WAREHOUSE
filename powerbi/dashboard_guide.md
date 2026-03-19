# Power BI Dashboard Guide

> Connect Power BI to `db/retail.db` using the **SQLite ODBC driver**.
> Go to **Get Data → ODBC** and point it to your `retail.db` file.
> Import all 4 star-schema tables: `fact_sales`, `dim_date`, `dim_product`, `dim_customer`.

---

## Relationships (set up in Model View)

| From | To | Key |
|------|----|-----|
| `fact_sales.date_key` | `dim_date.date_key` | Many-to-One |
| `fact_sales.product_key` | `dim_product.product_key` | Many-to-One |
| `fact_sales.customer_key` | `dim_customer.customer_key` | Many-to-One |

---

## Slicer (1)

| Element | Field | Purpose |
|---------|-------|---------|
| **Year Slicer** | `dim_date.year` | Let the user filter the entire dashboard by year (2009, 2010, 2011) |

Place this at the top of the dashboard page.

---

## Visual 1 — Monthly Revenue Trend (Line Chart)

| Setting | Value |
|---------|-------|
| **Chart type** | Line Chart |
| **X-axis** | `dim_date.month_name` (sort by `dim_date.month_number`) |
| **Y-axis** | `fact_sales.revenue` (Sum) |
| **Legend** | `dim_date.year` |
| **Business question** | _"What does the seasonal revenue pattern look like? When should we stock up?"_ |

> **Tip:** Right-click the month_name axis → Sort by → month_number, so months appear Jan–Dec.

---

## Visual 2 — Top 10 Products by Revenue (Bar Chart)

| Setting | Value |
|---------|-------|
| **Chart type** | Horizontal Bar Chart |
| **Y-axis** | `dim_product.Description` |
| **X-axis** | `fact_sales.revenue` (Sum) |
| **Filter** | Top N = 10, by Sum of revenue |
| **Business question** | _"Which products are our biggest revenue drivers? (Pareto / 80/20)"_ |

> This directly mirrors the 80/20 SKU analysis from the SQL queries.

---

## Visual 3 — Revenue by Country (Filled Map or Bar Chart)

| Setting | Value |
|---------|-------|
| **Chart type** | Horizontal Bar Chart (or Filled Map if you prefer) |
| **Y-axis** | `dim_customer.Country` |
| **X-axis** | `fact_sales.revenue` (Sum) |
| **Filter** | Top N = 10, by Sum of revenue |
| **Business question** | _"How concentrated is our revenue geographically? Are we over-dependent on the UK?"_ |

---

## Visual 4 — Revenue by Product Category (Donut Chart)

| Setting | Value |
|---------|-------|
| **Chart type** | Donut Chart |
| **Legend** | `dim_product.category_bucket` |
| **Values** | `fact_sales.revenue` (Sum) |
| **Business question** | _"What product categories drive the most revenue? Where should we focus inventory?"_ |

---

## Visual 5 — Customer Segment Split (Card + Stacked Bar)

| Setting | Value |
|---------|-------|
| **Chart type** | Stacked Bar Chart |
| **Y-axis** | `dim_customer.customer_segment` |
| **X-axis** | `fact_sales.revenue` (Sum) |
| **Business question** | _"How much revenue comes from High / Mid / Low value customers?"_ |

Additionally, add a **Card visual** showing:
- **Total Revenue**: `Sum of fact_sales.revenue`
- **Total Orders**: `Distinct count of fact_sales.Invoice`
- **Total Customers**: `Distinct count of dim_customer.CustomerID`

---

## Dashboard Layout Suggestion

```
┌─────────────────────────────────────────────┐
│  [Year Slicer]   [Card: Revenue] [Card: Orders] [Card: Customers]  │
├──────────────────────────┬──────────────────┤
│                          │                  │
│  Visual 1: Monthly       │  Visual 4:       │
│  Revenue Trend           │  Category Donut  │
│  (Line Chart)            │                  │
│                          │                  │
├──────────────────────────┼──────────────────┤
│                          │                  │
│  Visual 2: Top 10        │  Visual 5:       │
│  Products (Bar)          │  Customer        │
│                          │  Segments (Bar)  │
│                          │                  │
├──────────────────────────┴──────────────────┤
│  Visual 3: Revenue by Country (Bar/Map)     │
└─────────────────────────────────────────────┘
```

---

## No DAX Required

All visuals use simple **drag-and-drop** with built-in aggregations (Sum, Count, Distinct Count). No custom DAX measures needed.
