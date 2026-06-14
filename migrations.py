from sqlalchemy import text
from database import engine


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def run():
    """Add missing columns to existing tables without dropping data."""
    with engine.connect() as conn:
        # contacts table
        existing = _columns(conn, "contacts")
        pending = {
            "email":          "VARCHAR",
            "phone_prefix":   "VARCHAR",
            "phone_number":   "VARCHAR",
            "cv_version_id":  "INTEGER",
            "location":       "VARCHAR",
        }
        for col, col_type in pending.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE contacts ADD COLUMN {col} {col_type}"))
        conn.commit()
