from sqlalchemy import text
from app.db.database import engine


def run_migrations():
    with engine.connect() as conn:
        # Add reset_token column if not exists
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR"))
        except Exception:
            pass

        # Add reset_token_expires_at column if not exists
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires_at DATETIME"))
        except Exception:
            pass

        conn.commit()