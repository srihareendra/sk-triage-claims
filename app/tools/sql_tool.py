
import os, psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
load_dotenv()
def get_conn():
    return psycopg.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode="require" if os.getenv("PGSSL","true").lower()=="true" else "disable",
        row_factory=dict_row,
    )

def run_parameterized(sql: str, params: tuple = ()):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return cur.fetchall()
        return []
