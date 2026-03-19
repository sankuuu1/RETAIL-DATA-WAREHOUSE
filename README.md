# Online Retail II — Data Warehouse Project

> "I did supply chain analysis manually at IIM Mumbai. This project builds the SQL
> data warehouse that would have powered that same analysis at scale."

## Stack
- **Python + pandas** — reading CSV, loading to database
- **SQLite** — local relational database
- **Plain SQL** — all transformations and analysis
- **Power BI** — final dashboard (connects to SQLite via ODBC)

## Dataset
[Online Retail II UCI](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci)
— 1.06 million real UK retail transactions, 2009–2011.

Download the CSV from Kaggle and place it in `data/online_retail_II.csv`.

## How to Run

```bash
# Step 1 — Load raw CSV into SQLite
python scripts/extract_load.py

# Step 2 — Clean data → ODS layer
python scripts/run_sql.py sql/transform.sql

# Step 3 — Build star schema (dims + fact)
python scripts/run_sql.py sql/schema.sql

# Step 4 — Run analysis queries
python scripts/run_sql.py sql/analysis.sql
```

## Project Structure
```
retail-data-warehouse/
├── data/                  ← Kaggle CSV goes here
├── db/                    ← SQLite database (auto-created)
├── sql/
│   ├── transform.sql      ← ODS layer cleaning
│   ├── schema.sql         ← Star schema DDL + inserts
│   └── analysis.sql       ← 5 supply-chain queries
├── scripts/
│   ├── extract_load.py    ← CSV → stg_retail
│   └── run_sql.py         ← Executes any .sql file
├── powerbi/
│   └── dashboard_guide.md ← Power BI visual specs
└── README.md
```
