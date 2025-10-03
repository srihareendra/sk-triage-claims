import os
import csv
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()  # Load PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

# ✅ Create connection (global, reused)
conn = psycopg.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
    sslmode="require" if os.getenv("PGSSL", "true").lower() == "true" else "disable",
    row_factory=dict_row,
)

def load_table(csv_path, table, cols):
    """Load CSV into table with given column order."""
    count = 0
    with conn.cursor() as cur, open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vals = [row[c] if row[c] != "" else None for c in cols]
            ph = ",".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph})", vals
            )
            count += 1
    conn.commit()
    print(f"✅ Loaded {count} rows into {table}")

if __name__ == "__main__":
    base = "data"   # adjust if your CSVs are in a different folder

    load_table(os.path.join(base,"customers.csv"), "customers", ["customer_id","name","state","age"])
    load_table(os.path.join(base,"policies.csv"), "policies", ["policy_id","customer_id","policy_type","start_date","end_date","premium"])
    load_table(os.path.join(base,"claims.csv"), "claims", ["policy_id","date_of_loss","description","amount_claimed","status"])
    load_table(os.path.join(base,"claim_notes.csv"), "claim_notes", ["note_id","claim_id","note_text"])
    load_table(os.path.join(base,"triage_decisions.csv"), "triage_decisions", ["decision_id","claim_id","severity","fraud_risk","route_to","rationale","created_at"])

    conn.close()
    print("🎉 All CSVs loaded successfully.")
