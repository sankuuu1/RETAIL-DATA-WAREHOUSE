"""
extract_load.py
===============
Purpose: Read the raw CSV from Kaggle and load it INTO SQLite as
         a staging table called 'stg_retail'. No cleaning happens here —
         we just move the data from flat file to database.

How to run:
    python scripts/extract_load.py
"""

# ──────────────────────────────────────────────
# 1. Import the only two libraries we need
# ──────────────────────────────────────────────
import pandas as pd   # for reading the CSV into a DataFrame
import sqlite3         # for creating / connecting to our SQLite database
import os              # for building file paths that work on any OS

# ──────────────────────────────────────────────
# 2. Define file paths
# ──────────────────────────────────────────────

# Get the project root (one level up from the 'scripts' folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the Kaggle CSV file you downloaded
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "online_retail_II.csv")

# Path to the SQLite database (will be auto-created if it doesn't exist)
DB_PATH = os.path.join(PROJECT_ROOT, "db", "retail.db")

# ──────────────────────────────────────────────
# 3. Read the CSV into a pandas DataFrame
# ──────────────────────────────────────────────

print(f"Reading CSV from: {CSV_PATH}")

# The dataset uses ISO-8859-1 encoding (also called Latin-1).
# This is common in European datasets because it supports characters
# like £, é, ñ that UTF-8 sometimes doesn't handle in older files.
df = pd.read_csv(CSV_PATH, encoding="ISO-8859-1")

# Show basic info so we know the load worked
print(f"Rows loaded from CSV: {len(df):,}")
print(f"Columns: {list(df.columns)}")

# ──────────────────────────────────────────────
# 4. Connect to SQLite and write the raw data
# ──────────────────────────────────────────────

# sqlite3.connect() creates the .db file if it doesn't already exist
conn = sqlite3.connect(DB_PATH)

# to_sql() writes the entire DataFrame into a database table.
# - name="stg_retail"    → the table name (stg = staging, meaning raw/untouched)
# - if_exists="replace"  → if the table already exists, drop it and recreate
#                          (so we can re-run this script safely)
# - index=False          → don't write the pandas row index as a column
df.to_sql(name="stg_retail", con=conn, if_exists="replace", index=False)

print(f"Data loaded into SQLite table 'stg_retail' at: {DB_PATH}")

# ──────────────────────────────────────────────
# 5. Quick verification: count rows in the table
# ──────────────────────────────────────────────

# Run a simple SQL query to confirm the row count matches
row_count = conn.execute("SELECT COUNT(*) FROM stg_retail").fetchone()[0]
print(f"Verification — rows in stg_retail: {row_count:,}")

# ──────────────────────────────────────────────
# 6. Close the database connection
# ──────────────────────────────────────────────
conn.close()
print("Done. Connection closed.")
