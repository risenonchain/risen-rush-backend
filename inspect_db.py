import os
import sys
from sqlalchemy import create_url, text
from sqlalchemy import create_engine

# Try to get the database URL from settings or environment
try:
    from app.core.config import settings
    db_url = settings.database_url
except Exception:
    db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("ERROR: DATABASE_URL not found in environment or settings.")
    sys.exit(1)

# Mask sensitive info for display
url_obj = create_url(db_url)
print(f"Connecting to: {url_obj.host} / {url_obj.database}")

engine = create_engine(db_url)

def inspect_table(table_name):
    print(f"\n--- Inspecting Table: {table_name} ---")
    try:
        with engine.connect() as conn:
            # PostgreSQL specific column inspection
            query = text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            result = conn.execute(query)
            columns = result.fetchall()
            if not columns:
                print(f"Table '{table_name}' not found or has no columns.")
                return

            for col in columns:
                print(f"Column: {col[0]:<25} Type: {col[1]:<15} Nullable: {col[2]:<10} Default: {col[3]}")

            # Show a sample row if possible to check values
            sample = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1")).fetchone()
            if sample:
                print(f"\nSample Row Keys: {sample._mapping.keys()}")
            else:
                print("\nNo rows found in table.")
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

if __name__ == "__main__":
    inspect_table("users")
    inspect_table("game_sessions")
    inspect_table("league_challenges")
    inspect_table("league_events")
