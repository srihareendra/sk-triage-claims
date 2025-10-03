
from .sql_tool import run_parameterized

def get_schema_hint():
    rows = run_parameterized(
        "SELECT table_name, column_name, data_type "
        "FROM information_schema.columns "
        "WHERE table_schema='public' "
        "ORDER BY table_name, ordinal_position;"
    )
    by_table = {}
    for r in rows:
        by_table.setdefault(r["table_name"], []).append(f"{r['column_name']}:{r['data_type']}")
    parts = []
    for t, cols in by_table.items():
        parts.append(f"{t}({', '.join(cols)})")
    return "Tables: " + " | ".join(parts)
