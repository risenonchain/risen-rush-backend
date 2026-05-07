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

        # Create news table if not exists
        try:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    summary VARCHAR(300) NOT NULL,
                    details TEXT NOT NULL,
                    url VARCHAR(300),
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            '''))
        except Exception:
            pass

        # Create league_events table if not exists
        try:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS league_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    is_live_visible BOOLEAN DEFAULT 0,
                    live_fee_usd INTEGER DEFAULT 30,
                    created_at DATETIME
                )
            '''))
        except Exception:
            pass

        conn.commit()