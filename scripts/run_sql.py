"""
run_sql.py
==========
Purpose: A simple helper that reads a .sql file and executes it
         against our SQLite database (db/retail.db).

         This lets us keep all SQL in .sql files (clean separation)
         while still running everything from Python.

How to run:
    python scripts/run_sql.py sql/transform.sql
    python scripts/run_sql.py sql/schema.sql
    python scripts/run_sql.py sql/analysis.sql
"""

import sqlite3
import sys
import os

# Fix for Windows: the default console encoding (cp1252) can't handle
# some characters in product descriptions. Force UTF-8 output.
sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────
# 1. Get the SQL file path from command-line argument
# ──────────────────────────────────────────────

# sys.argv[0] is the script name itself
# sys.argv[1] is the first argument the user passes (the .sql file path)
if len(sys.argv) < 2:
    print("Usage: python scripts/run_sql.py <path-to-sql-file>")
    print("Example: python scripts/run_sql.py sql/transform.sql")
    sys.exit(1)

SQL_FILE = sys.argv[1]

# ──────────────────────────────────────────────
# 2. Build the database path
# ──────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "db", "retail.db")

# ──────────────────────────────────────────────
# 3. Read the SQL file contents
# ──────────────────────────────────────────────

# Build the full path — if the user gave a relative path, resolve it
# from the project root
if not os.path.isabs(SQL_FILE):
    SQL_FILE = os.path.join(PROJECT_ROOT, SQL_FILE)

print(f"Reading SQL from: {SQL_FILE}")

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql_script = f.read()

# ──────────────────────────────────────────────
# 4. Connect to SQLite and execute the SQL
# ──────────────────────────────────────────────

conn = sqlite3.connect(DB_PATH)

# We use executescript() because our .sql files contain multiple
# statements separated by semicolons.
# executescript() automatically commits after running all statements.

# However, for analysis.sql we want to print SELECT results.
# So we split by semicolons and handle SELECTs separately.

# Split the script into individual statements
statements = [s.strip() for s in sql_script.split(";") if s.strip()]

for statement in statements:
    # Skip pure comment blocks (lines that start with --)
    non_comment_lines = [
        line for line in statement.split("\n")
        if line.strip() and not line.strip().startswith("--")
    ]

    if not non_comment_lines:
        continue  # skip blocks that are only comments

    # Check if this statement is a SELECT (i.e., it returns data)
    # We look at the first non-comment line to decide
    first_keyword = non_comment_lines[0].strip().split()[0].upper()

    if first_keyword == "SELECT":
        # For SELECT statements, fetch and print results nicely
        # Extract a title from the comment block above the SELECT
        comment_lines = [
            line.strip().lstrip("- ").strip()
            for line in statement.split("\n")
            if line.strip().startswith("--")
        ]
        title = comment_lines[0] if comment_lines else "Query Result"
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

        cursor = conn.execute(statement)
        # Get column names from the cursor description
        col_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        # Print column headers
        print(" | ".join(col_names))
        print("-" * 60)

        # Print each row (limit to 25 for readability)
        for row in rows[:25]:
            print(" | ".join(str(val) for val in row))

        if len(rows) > 25:
            print(f"... ({len(rows) - 25} more rows not shown)")

        print(f"Total rows: {len(rows)}\n")
    else:
        # For non-SELECT statements (CREATE, INSERT, DROP, etc.)
        # just execute them
        conn.execute(statement)
        conn.commit()
        # Print a summary of what was executed
        print(f"Executed: {first_keyword} ...")

print("\nAll statements executed successfully.")
conn.close()
