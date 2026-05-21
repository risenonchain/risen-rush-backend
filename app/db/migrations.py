from datetime import datetime
from sqlalchemy import text
from app.db.database import engine


def run_migrations():
    with engine.connect() as conn:
        is_postgres = "postgresql" in str(engine.url)

        # Postgres uses TIMESTAMP, SQLite uses DATETIME
        ts_type = "TIMESTAMP" if is_postgres else "DATETIME"
        id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_true = "TRUE" if is_postgres else "1"
        bool_false = "FALSE" if is_postgres else "0"

        # Helper to run commands one by one and handle transaction state
        def execute_step(sql, params=None):
            try:
                conn.execute(text(sql), params or {})
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        # Add columns to users table
        columns = [
            ("reset_token", "VARCHAR"),
            ("reset_token_expires_at", ts_type),
            ("referral_code", "VARCHAR"),
            ("referred_by_user_id", "INTEGER"),
            ("wallet_address", "VARCHAR"),
            ("avatar_url", "VARCHAR"),
            ("generated_avatar_url", "VARCHAR"),
            ("vault_trials", "INTEGER DEFAULT 0"),
            ("is_premium", f"BOOLEAN DEFAULT {bool_false}"),
            ("premium_expires_at", ts_type),
            ("best_score", "INTEGER DEFAULT 0"),
            ("best_level", "INTEGER DEFAULT 1"),
            ("ads_watched_today", "INTEGER DEFAULT 0"),
            ("last_ad_date", ts_type),
            ("is_admin", f"BOOLEAN DEFAULT {bool_false}"),
            ("agreed_to_terms", f"BOOLEAN DEFAULT {bool_false}"),
            ("marketing_consent", f"BOOLEAN DEFAULT {bool_false}")
        ]

        for col_name, col_type in columns:
            if is_postgres:
                execute_step(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            else:
                execute_step(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

        # Mark existing users as agreed
        execute_step(f"UPDATE users SET agreed_to_terms = {bool_true}, marketing_consent = {bool_true} WHERE agreed_to_terms = {bool_false}")

        # Create announcements table
        execute_step(f'''
            CREATE TABLE IF NOT EXISTS announcements (
                id {id_type},
                message TEXT NOT NULL,
                is_active BOOLEAN DEFAULT {bool_true},
                created_at {ts_type} DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create news table
        execute_step(f'''
            CREATE TABLE IF NOT EXISTS news (
                id {id_type},
                title VARCHAR(200) NOT NULL,
                summary VARCHAR(300) NOT NULL,
                details TEXT NOT NULL,
                url VARCHAR(300),
                is_active BOOLEAN DEFAULT {bool_true},
                created_at {ts_type} DEFAULT CURRENT_TIMESTAMP,
                updated_at {ts_type}
            )
        ''')

        # Create seasons table
        execute_step(f'''
            CREATE TABLE IF NOT EXISTS seasons (
                id {id_type},
                name VARCHAR(100) NOT NULL,
                start_at {ts_type} DEFAULT CURRENT_TIMESTAMP,
                end_at {ts_type},
                is_active BOOLEAN DEFAULT {bool_true}
            )
        ''')

        # Create league_events table
        execute_step(f'''
            CREATE TABLE IF NOT EXISTS league_events (
                id {id_type},
                name VARCHAR(100) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT {bool_false},
                is_live_visible BOOLEAN DEFAULT {bool_false},
                live_fee_usd INTEGER DEFAULT 30,
                current_stage VARCHAR(50) DEFAULT 'registration',
                created_at {ts_type} DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Check if there is an active season, if not create one
        try:
            res = conn.execute(text("SELECT COUNT(*) FROM seasons WHERE is_active = :val"), {"val": True if is_postgres else 1}).fetchone()
            if res and res[0] == 0:
                execute_step("INSERT INTO seasons (name, is_active, start_at) VALUES ('Genesis Season', :is_active, :now)",
                            {"is_active": True if is_postgres else 1, "now": datetime.utcnow()})
        except Exception:
            pass

        # Update other tables for league support if needed
        if is_postgres:
            execute_step(f"ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS is_league_game BOOLEAN DEFAULT {bool_false}")
            execute_step("ALTER TABLE game_sessions ADD COLUMN IF NOT EXISTS league_match_id INTEGER")
            execute_step("ALTER TABLE league_fixtures ADD COLUMN IF NOT EXISTS stage VARCHAR DEFAULT 'group'")
            execute_step("ALTER TABLE league_fixtures ADD COLUMN IF NOT EXISTS group_name VARCHAR")
            execute_step("ALTER TABLE league_participants ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'")
        else:
            execute_step("ALTER TABLE game_sessions ADD COLUMN is_league_game BOOLEAN DEFAULT 0")
            execute_step("ALTER TABLE game_sessions ADD COLUMN league_match_id INTEGER")
            execute_step("ALTER TABLE league_fixtures ADD COLUMN stage VARCHAR DEFAULT 'group'")
            execute_step("ALTER TABLE league_fixtures ADD COLUMN group_name VARCHAR")
            execute_step("ALTER TABLE league_participants ADD COLUMN status VARCHAR DEFAULT 'active'")

        try:
            conn.commit()
        except Exception:
            pass
