"""
build_dashboard.py
==================
Purpose: Query the SQLite data warehouse and generate a beautiful,
         self-contained interactive HTML dashboard with Chart.js.

         This creates all 5 visuals from the Power BI guide:
         1. Monthly Revenue Trend (Line Chart)
         2. Top 10 Products by Revenue (Bar Chart)
         3. Revenue by Country (Bar Chart)
         4. Revenue by Product Category (Donut Chart)
         5. Customer Segment Split (Bar Chart)
         + KPI Cards (Total Revenue, Orders, Customers)
         + Year Slicer

How to run:
    py scripts/build_dashboard.py
    → Opens dashboard/index.html in your browser
"""

import sqlite3
import os
import json
import webbrowser

# ──────────────────────────────────────────────
# 1. Connect to the database
# ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "db", "retail.db")
conn = sqlite3.connect(DB_PATH)

print("Connected to database. Extracting data...")

# ──────────────────────────────────────────────
# 2. Extract data for each visual
# ──────────────────────────────────────────────

# KPI Cards
kpi = conn.execute("""
    SELECT
        ROUND(SUM(revenue), 2) AS total_revenue,
        COUNT(DISTINCT Invoice) AS total_orders,
        COUNT(DISTINCT customer_key) AS total_customers
    FROM fact_sales
""").fetchone()

# Monthly Revenue Trend (by year + month)
monthly_data = conn.execute("""
    SELECT d.year, d.month_number, d.month_name, ROUND(SUM(f.revenue), 2) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month_number, d.month_name
    ORDER BY d.year, d.month_number
""").fetchall()

# Top 10 Products by Revenue
top_products = conn.execute("""
    SELECT p.Description, ROUND(SUM(f.revenue), 2) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.Description
    ORDER BY revenue DESC
    LIMIT 10
""").fetchall()

# Revenue by Country (Top 10)
country_data = conn.execute("""
    SELECT c.Country, ROUND(SUM(f.revenue), 2) AS revenue
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    GROUP BY c.Country
    ORDER BY revenue DESC
    LIMIT 10
""").fetchall()

# Revenue by Category
category_data = conn.execute("""
    SELECT p.category_bucket, ROUND(SUM(f.revenue), 2) AS revenue
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    GROUP BY p.category_bucket
    ORDER BY revenue DESC
""").fetchall()

# Customer Segment Revenue
segment_data = conn.execute("""
    SELECT c.customer_segment, ROUND(SUM(f.revenue), 2) AS revenue,
           COUNT(DISTINCT c.CustomerID) AS num_customers
    FROM fact_sales f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    GROUP BY c.customer_segment
    ORDER BY revenue DESC
""").fetchall()

# 80/20 ABC Analysis summary
abc_data = conn.execute("""
    SELECT abc_class, COUNT(*) AS sku_count, ROUND(SUM(total_revenue), 2) AS revenue
    FROM (
        SELECT p.StockCode,
            CASE
                WHEN ROUND(SUM(SUM(f.revenue)) OVER (ORDER BY SUM(f.revenue) DESC) * 100.0
                     / SUM(SUM(f.revenue)) OVER (), 2) <= 80 THEN 'A - Top 80%'
                WHEN ROUND(SUM(SUM(f.revenue)) OVER (ORDER BY SUM(f.revenue) DESC) * 100.0
                     / SUM(SUM(f.revenue)) OVER (), 2) <= 95 THEN 'B - Next 15%'
                ELSE 'C - Bottom 5%'
            END AS abc_class,
            SUM(f.revenue) AS total_revenue
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.StockCode
    )
    GROUP BY abc_class
    ORDER BY abc_class
""").fetchall()

# Cancellation stats
cancel_summary = conn.execute("""
    SELECT
        COUNT(*) AS total_lines,
        SUM(CASE WHEN Invoice LIKE 'C%' THEN 1 ELSE 0 END) AS cancelled,
        ROUND(SUM(CASE WHEN Invoice LIKE 'C%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS cancel_rate
    FROM stg_retail
""").fetchone()

# Per-year data for the slicer
yearly_kpis = conn.execute("""
    SELECT d.year,
           ROUND(SUM(f.revenue), 2) AS revenue,
           COUNT(DISTINCT f.Invoice) AS orders,
           COUNT(DISTINCT f.customer_key) AS customers
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year
    ORDER BY d.year
""").fetchall()

# Monthly data per year (for filtered line chart)
monthly_by_year = {}
for year_row in yearly_kpis:
    yr = year_row[0]
    rows = conn.execute("""
        SELECT d.month_number, d.month_name, ROUND(SUM(f.revenue), 2) AS revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = ?
        GROUP BY d.month_number, d.month_name
        ORDER BY d.month_number
    """, (yr,)).fetchall()
    monthly_by_year[str(yr)] = [[r[0], r[1], r[2]] for r in rows]

# Top products per year
top_products_by_year = {}
for year_row in yearly_kpis:
    yr = year_row[0]
    rows = conn.execute("""
        SELECT p.Description, ROUND(SUM(f.revenue), 2) AS revenue
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = ?
        GROUP BY p.Description
        ORDER BY revenue DESC
        LIMIT 10
    """, (yr,)).fetchall()
    top_products_by_year[str(yr)] = [[r[0], r[1]] for r in rows]

# Country per year
country_by_year = {}
for year_row in yearly_kpis:
    yr = year_row[0]
    rows = conn.execute("""
        SELECT c.Country, ROUND(SUM(f.revenue), 2) AS revenue
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = ?
        GROUP BY c.Country
        ORDER BY revenue DESC
        LIMIT 10
    """, (yr,)).fetchall()
    country_by_year[str(yr)] = [[r[0], r[1]] for r in rows]

# Category per year
category_by_year = {}
for year_row in yearly_kpis:
    yr = year_row[0]
    rows = conn.execute("""
        SELECT p.category_bucket, ROUND(SUM(f.revenue), 2) AS revenue
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = ?
        GROUP BY p.category_bucket
        ORDER BY revenue DESC
    """, (yr,)).fetchall()
    category_by_year[str(yr)] = [[r[0], r[1]] for r in rows]

# Segment per year
segment_by_year = {}
for year_row in yearly_kpis:
    yr = year_row[0]
    rows = conn.execute("""
        SELECT c.customer_segment, ROUND(SUM(f.revenue), 2) AS revenue,
               COUNT(DISTINCT c.CustomerID) AS num_customers
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.year = ?
        GROUP BY c.customer_segment
        ORDER BY revenue DESC
    """, (yr,)).fetchall()
    segment_by_year[str(yr)] = [[r[0], r[1], r[2]] for r in rows]

conn.close()
print("Data extracted. Generating dashboard...")

# ──────────────────────────────────────────────
# 3. Build the data object for JavaScript
# ──────────────────────────────────────────────
dashboard_data = {
    "kpi": {"revenue": kpi[0], "orders": kpi[1], "customers": kpi[2]},
    "monthly": [[r[0], r[1], r[2], r[3]] for r in monthly_data],
    "topProducts": [[r[0], r[1]] for r in top_products],
    "countries": [[r[0], r[1]] for r in country_data],
    "categories": [[r[0], r[1]] for r in category_data],
    "segments": [[r[0], r[1], r[2]] for r in segment_data],
    "abc": [[r[0], r[1], r[2]] for r in abc_data],
    "cancelSummary": {"total": cancel_summary[0], "cancelled": cancel_summary[1], "rate": cancel_summary[2]},
    "yearlyKpis": [[r[0], r[1], r[2], r[3]] for r in yearly_kpis],
    "monthlyByYear": monthly_by_year,
    "topProductsByYear": top_products_by_year,
    "countryByYear": country_by_year,
    "categoryByYear": category_by_year,
    "segmentByYear": segment_by_year,
}

data_json = json.dumps(dashboard_data)

# ──────────────────────────────────────────────
# 4. Generate the HTML dashboard
# ──────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Retail Data Warehouse — Supply Chain Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-primary: #0f1117;
    --bg-card: #1a1d27;
    --bg-card-hover: #22263a;
    --border: #2a2e3f;
    --text-primary: #f0f0f5;
    --text-secondary: #8b8fa3;
    --text-muted: #5f6377;
    --accent-blue: #4f8cff;
    --accent-purple: #a855f7;
    --accent-green: #22c55e;
    --accent-orange: #f97316;
    --accent-pink: #ec4899;
    --accent-cyan: #06b6d4;
    --accent-yellow: #eab308;
    --accent-red: #ef4444;
    --gradient-blue: linear-gradient(135deg, #4f8cff 0%, #3b5fdb 100%);
    --gradient-purple: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
    --gradient-green: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    --gradient-orange: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
    --shadow: 0 4px 24px rgba(0,0,0,0.3);
    --radius: 16px;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    line-height: 1.6;
  }}

  .dashboard-header {{
    background: linear-gradient(135deg, #151823 0%, #1e2235 50%, #1a1630 100%);
    border-bottom: 1px solid var(--border);
    padding: 28px 40px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
  }}

  .header-inner {{
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }}

  .header-left h1 {{
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #4f8cff, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}

  .header-left p {{
    color: var(--text-secondary);
    font-size: 13px;
    margin-top: 2px;
  }}

  .year-slicer {{
    display: flex;
    gap: 6px;
    align-items: center;
  }}

  .year-slicer label {{
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
    margin-right: 4px;
  }}

  .year-btn {{
    padding: 7px 18px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text-secondary);
    border-radius: 8px;
    cursor: pointer;
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.25s ease;
  }}

  .year-btn:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent-blue);
    color: var(--text-primary);
  }}

  .year-btn.active {{
    background: var(--gradient-blue);
    border-color: var(--accent-blue);
    color: #fff;
    font-weight: 600;
    box-shadow: 0 0 20px rgba(79, 140, 255, 0.3);
  }}

  .container {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px 40px 60px;
  }}

  /* KPI Cards */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-bottom: 28px;
  }}

  .kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }}

  .kpi-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
  }}

  .kpi-card:nth-child(1)::before {{ background: var(--gradient-blue); }}
  .kpi-card:nth-child(2)::before {{ background: var(--gradient-green); }}
  .kpi-card:nth-child(3)::before {{ background: var(--gradient-purple); }}
  .kpi-card:nth-child(4)::before {{ background: var(--gradient-orange); }}

  .kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: var(--shadow);
    border-color: var(--accent-blue);
  }}

  .kpi-label {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }}

  .kpi-value {{
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
  }}

  .kpi-card:nth-child(1) .kpi-value {{ color: var(--accent-blue); }}
  .kpi-card:nth-child(2) .kpi-value {{ color: var(--accent-green); }}
  .kpi-card:nth-child(3) .kpi-value {{ color: var(--accent-purple); }}
  .kpi-card:nth-child(4) .kpi-value {{ color: var(--accent-orange); }}

  .kpi-sub {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* Chart Grid */
  .chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 28px;
  }}

  .chart-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    transition: all 0.3s ease;
  }}

  .chart-card:hover {{
    border-color: rgba(79, 140, 255, 0.3);
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
  }}

  .chart-card.full-width {{
    grid-column: 1 / -1;
  }}

  .chart-title {{
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text-primary);
  }}

  .chart-subtitle {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 20px;
  }}

  .chart-container {{
    position: relative;
    width: 100%;
    height: 320px;
  }}

  .chart-container.tall {{
    height: 380px;
  }}

  /* ABC Table */
  .abc-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
  }}

  .abc-table th, .abc-table td {{
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    border-bottom: 1px solid var(--border);
  }}

  .abc-table th {{
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.8px;
  }}

  .abc-table td {{
    color: var(--text-primary);
  }}

  .abc-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }}

  .abc-a {{ background: rgba(34,197,94,0.15); color: var(--accent-green); }}
  .abc-b {{ background: rgba(234,179,8,0.15); color: var(--accent-yellow); }}
  .abc-c {{ background: rgba(239,68,68,0.15); color: var(--accent-red); }}

  .insight-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(79,140,255,0.1);
    color: var(--accent-blue);
    border: 1px solid rgba(79,140,255,0.2);
    margin-top: 12px;
  }}

  .footer {{
    text-align: center;
    padding: 24px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
  }}

  @media (max-width: 900px) {{
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-grid {{ grid-template-columns: 1fr; }}
    .container {{ padding: 16px; }}
    .dashboard-header {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<div class="dashboard-header">
 <div class="header-inner">
  <div class="header-left">
    <h1>📦 Supply Chain Analytics Dashboard</h1>
    <p>Online Retail II · 1.06M transactions · 2009–2011 · Star Schema Data Warehouse</p>
  </div>
  <div class="year-slicer">
    <label>Filter by Year:</label>
    <button class="year-btn active" onclick="setYear('all')">All Years</button>
    <button class="year-btn" onclick="setYear('2009')">2009</button>
    <button class="year-btn" onclick="setYear('2010')">2010</button>
    <button class="year-btn" onclick="setYear('2011')">2011</button>
  </div>
 </div>
</div>

<div class="container">

  <!-- KPI Cards -->
  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Total Revenue</div>
      <div class="kpi-value" id="kpi-revenue">—</div>
      <div class="kpi-sub">Gross revenue (GBP)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Orders</div>
      <div class="kpi-value" id="kpi-orders">—</div>
      <div class="kpi-sub">Unique invoices</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Customers</div>
      <div class="kpi-value" id="kpi-customers">—</div>
      <div class="kpi-sub">Distinct customer IDs</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Cancellation Rate</div>
      <div class="kpi-value" id="kpi-cancel">—</div>
      <div class="kpi-sub">Overall order cancellations</div>
    </div>
  </div>

  <!-- Chart Row 1: Monthly Trend + Top Products -->
  <div class="chart-grid">
    <div class="chart-card full-width">
      <div class="chart-title">📈 Monthly Revenue Trend</div>
      <div class="chart-subtitle">When should we stock up? Identify seasonal spikes for demand planning.</div>
      <div class="chart-container tall">
        <canvas id="monthlyChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Chart Row 2: Top Products + Country -->
  <div class="chart-grid">
    <div class="chart-card">
      <div class="chart-title">🏆 Top 10 Products by Revenue</div>
      <div class="chart-subtitle">Which products are our biggest revenue drivers? (Pareto / 80-20)</div>
      <div class="chart-container tall">
        <canvas id="productsChart"></canvas>
      </div>
    </div>
    <div class="chart-card">
      <div class="chart-title">🌍 Revenue by Country (Top 10)</div>
      <div class="chart-subtitle">How concentrated is revenue geographically?</div>
      <div class="chart-container tall">
        <canvas id="countryChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Chart Row 3: Category Donut + Customer Segments -->
  <div class="chart-grid">
    <div class="chart-card">
      <div class="chart-title">🏷️ Revenue by Product Category</div>
      <div class="chart-subtitle">What product categories drive the most revenue?</div>
      <div class="chart-container">
        <canvas id="categoryChart"></canvas>
      </div>
    </div>
    <div class="chart-card">
      <div class="chart-title">👥 Customer Segment Split</div>
      <div class="chart-subtitle">Revenue contribution from High / Mid / Low value customers</div>
      <div class="chart-container">
        <canvas id="segmentChart"></canvas>
      </div>
    </div>
  </div>

  <!-- ABC Analysis Table -->
  <div class="chart-grid">
    <div class="chart-card full-width">
      <div class="chart-title">📊 ABC / 80-20 Inventory Classification</div>
      <div class="chart-subtitle">Pareto analysis — A small number of SKUs drive most of the revenue. Focus inventory management on Class A.</div>
      <table class="abc-table">
        <thead>
          <tr><th>Class</th><th>SKU Count</th><th>Total Revenue (£)</th><th>% of SKUs</th><th>Insight</th></tr>
        </thead>
        <tbody id="abc-body"></tbody>
      </table>
      <div class="insight-badge" id="abc-insight"></div>
    </div>
  </div>

</div>

<div class="footer">
  Built with Python + SQLite + Chart.js · Star Schema Data Warehouse · Online Retail II UCI Dataset
</div>

<script>
const DATA = {data_json};

// ── Color palette ──
const COLORS = {{
  blue: '#4f8cff', purple: '#a855f7', green: '#22c55e', orange: '#f97316',
  pink: '#ec4899', cyan: '#06b6d4', yellow: '#eab308', red: '#ef4444',
  indigo: '#6366f1', lime: '#84cc16'
}};
const PALETTE = Object.values(COLORS);

// ── Utility ──
function fmt(n) {{ return '£' + Number(n).toLocaleString('en-GB', {{minimumFractionDigits: 0, maximumFractionDigits: 0}}); }}
function fmtK(n) {{ return n >= 1e6 ? '£' + (n/1e6).toFixed(1) + 'M' : n >= 1e3 ? '£' + (n/1e3).toFixed(0) + 'K' : '£' + n; }}
function fmtNum(n) {{ return Number(n).toLocaleString('en-GB'); }}

// ── Chart defaults ──
Chart.defaults.color = '#8b8fa3';
Chart.defaults.borderColor = 'rgba(42,46,63,0.6)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'circle';

let charts = {{}};
let currentYear = 'all';

function setYear(year) {{
  currentYear = year;
  document.querySelectorAll('.year-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  updateDashboard();
}}

function updateDashboard() {{
  const yr = currentYear;

  // KPIs
  if (yr === 'all') {{
    document.getElementById('kpi-revenue').textContent = fmtK(DATA.kpi.revenue);
    document.getElementById('kpi-orders').textContent = fmtNum(DATA.kpi.orders);
    document.getElementById('kpi-customers').textContent = fmtNum(DATA.kpi.customers);
    document.getElementById('kpi-cancel').textContent = DATA.cancelSummary.rate + '%';
  }} else {{
    const yk = DATA.yearlyKpis.find(r => String(r[0]) === yr);
    if (yk) {{
      document.getElementById('kpi-revenue').textContent = fmtK(yk[1]);
      document.getElementById('kpi-orders').textContent = fmtNum(yk[2]);
      document.getElementById('kpi-customers').textContent = fmtNum(yk[3]);
    }}
    document.getElementById('kpi-cancel').textContent = DATA.cancelSummary.rate + '%';
  }}

  // Monthly Chart
  if (charts.monthly) charts.monthly.destroy();
  const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');

  if (yr === 'all') {{
    // Group by year for multi-line
    const years = [...new Set(DATA.monthly.map(r => r[0]))];
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const datasets = years.map((y, i) => ({{
      label: String(y),
      data: months.map((_, mi) => {{
        const row = DATA.monthly.find(r => r[0] === y && r[1] === mi + 1);
        return row ? row[3] : null;
      }}),
      borderColor: PALETTE[i % PALETTE.length],
      backgroundColor: PALETTE[i % PALETTE.length] + '20',
      borderWidth: 2.5,
      tension: 0.4,
      fill: true,
      pointRadius: 4,
      pointHoverRadius: 7,
    }}));
    charts.monthly = new Chart(monthlyCtx, {{
      type: 'line',
      data: {{ labels: months, datasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) }} }} }},
        scales: {{ y: {{ ticks: {{ callback: v => fmtK(v) }} }} }}
      }}
    }});
  }} else {{
    const mdata = DATA.monthlyByYear[yr] || [];
    charts.monthly = new Chart(monthlyCtx, {{
      type: 'line',
      data: {{
        labels: mdata.map(r => r[1]),
        datasets: [{{
          label: yr,
          data: mdata.map(r => r[2]),
          borderColor: COLORS.blue,
          backgroundColor: COLORS.blue + '20',
          borderWidth: 2.5, tension: 0.4, fill: true, pointRadius: 4, pointHoverRadius: 7,
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ tooltip: {{ callbacks: {{ label: ctx => fmt(ctx.raw) }} }} }},
        scales: {{ y: {{ ticks: {{ callback: v => fmtK(v) }} }} }}
      }}
    }});
  }}

  // Top Products
  if (charts.products) charts.products.destroy();
  const pData = yr === 'all' ? DATA.topProducts : (DATA.topProductsByYear[yr] || []);
  charts.products = new Chart(document.getElementById('productsChart').getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: pData.map(r => r[0].length > 28 ? r[0].substring(0,28) + '…' : r[0]),
      datasets: [{{
        data: pData.map(r => r[1]),
        backgroundColor: PALETTE.slice(0, pData.length).map(c => c + 'cc'),
        borderColor: PALETTE.slice(0, pData.length),
        borderWidth: 1.5, borderRadius: 6,
      }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => fmt(ctx.raw) }} }} }},
      scales: {{ x: {{ ticks: {{ callback: v => fmtK(v) }} }} }}
    }}
  }});

  // Country
  if (charts.country) charts.country.destroy();
  const cData = yr === 'all' ? DATA.countries : (DATA.countryByYear[yr] || []);
  charts.country = new Chart(document.getElementById('countryChart').getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: cData.map(r => r[0]),
      datasets: [{{
        data: cData.map(r => r[1]),
        backgroundColor: PALETTE.slice(0, cData.length).map(c => c + 'cc'),
        borderColor: PALETTE.slice(0, cData.length),
        borderWidth: 1.5, borderRadius: 6,
      }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => fmt(ctx.raw) }} }} }},
      scales: {{ x: {{ ticks: {{ callback: v => fmtK(v) }} }} }}
    }}
  }});

  // Category Donut
  if (charts.category) charts.category.destroy();
  const catData = yr === 'all' ? DATA.categories : (DATA.categoryByYear[yr] || []);
  charts.category = new Chart(document.getElementById('categoryChart').getContext('2d'), {{
    type: 'doughnut',
    data: {{
      labels: catData.map(r => r[0]),
      datasets: [{{
        data: catData.map(r => r[1]),
        backgroundColor: PALETTE.slice(0, catData.length).map(c => c + 'dd'),
        borderColor: '#1a1d27', borderWidth: 3,
        hoverOffset: 8,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'right', labels: {{ padding: 14, font: {{ size: 12 }} }} }},
        tooltip: {{ callbacks: {{ label: ctx => ctx.label + ': ' + fmt(ctx.raw) }} }}
      }},
      cutout: '60%',
    }}
  }});

  // Customer Segments
  if (charts.segment) charts.segment.destroy();
  const segData = yr === 'all' ? DATA.segments : (DATA.segmentByYear[yr] || []);
  const segColors = {{ 'High Value': COLORS.green, 'Mid Value': COLORS.yellow, 'Low Value': COLORS.red }};
  charts.segment = new Chart(document.getElementById('segmentChart').getContext('2d'), {{
    type: 'bar',
    data: {{
      labels: segData.map(r => r[0]),
      datasets: [{{
        label: 'Revenue',
        data: segData.map(r => r[1]),
        backgroundColor: segData.map(r => (segColors[r[0]] || COLORS.blue) + 'cc'),
        borderColor: segData.map(r => segColors[r[0]] || COLORS.blue),
        borderWidth: 1.5, borderRadius: 6,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => fmt(ctx.raw) + ' (' + segData[ctx.dataIndex][2] + ' customers)' }} }} }},
      scales: {{ y: {{ ticks: {{ callback: v => fmtK(v) }} }} }}
    }}
  }});

  // ABC Table
  const abcBody = document.getElementById('abc-body');
  const totalSkus = DATA.abc.reduce((s, r) => s + r[1], 0);
  abcBody.innerHTML = DATA.abc.map(r => {{
    const cls = r[0].startsWith('A') ? 'abc-a' : r[0].startsWith('B') ? 'abc-b' : 'abc-c';
    const insight = r[0].startsWith('A') ? 'Focus here — stock management priority'
                  : r[0].startsWith('B') ? 'Monitor — moderate importance'
                  : 'Evaluate — consider discontinuing slow sellers';
    return `<tr>
      <td><span class="abc-badge ${{cls}}">${{r[0]}}</span></td>
      <td>${{fmtNum(r[1])}}</td>
      <td>${{fmt(r[2])}}</td>
      <td>${{(r[1] * 100 / totalSkus).toFixed(1)}}%</td>
      <td style="color: var(--text-secondary); font-size: 12px;">${{insight}}</td>
    </tr>`;
  }}).join('');

  const aRow = DATA.abc.find(r => r[0].startsWith('A'));
  if (aRow) {{
    const aPct = (aRow[1] * 100 / totalSkus).toFixed(0);
    document.getElementById('abc-insight').textContent = '💡 Pareto confirmed: ' + aPct + '% of SKUs generate 80% of revenue — classic 80/20 rule in action.';
  }}
}}

// Init
updateDashboard();
</script>
</body>
</html>"""

# ──────────────────────────────────────────────
# 5. Write the HTML file
# ──────────────────────────────────────────────
out_dir = os.path.join(PROJECT_ROOT, "dashboard")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "index.html")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dashboard generated: {out_path}")

# Open in browser
webbrowser.open(f"file:///{out_path.replace(os.sep, '/')}")
print("Opened in browser!")
