from datetime import datetime
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

        # User profile and gaming columns
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN referral_code VARCHAR"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN wallet_address VARCHAR"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN generated_avatar_url VARCHAR"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN vault_trials INTEGER DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN premium_expires_at DATETIME"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN best_score INTEGER DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN best_level INTEGER DEFAULT 1"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN ads_watched_today INTEGER DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_ad_date DATETIME"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
        except Exception: pass

        # Privacy and Marketing Consent
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN agreed_to_terms BOOLEAN DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN marketing_consent BOOLEAN DEFAULT 0"))
        except Exception: pass

        # Mark all existing users as agreed
        try:
            conn.execute(text("UPDATE users SET agreed_to_terms = 1, marketing_consent = 1"))
        except Exception: pass

        # Create announcements table
        try:
            # Check if using postgres
            is_postgres = "postgresql" in str(engine.url)

            id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_true = "TRUE" if is_postgres else "1"

            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS announcements (
                    id {id_type},
                    message TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT {bool_true},
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''))
        except Exception:
            pass

        # Create news table if not exists
        try:
            is_postgres = "postgresql" in str(engine.url)
            id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_true = "TRUE" if is_postgres else "1"

            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS news (
                    id {id_type},
                    title VARCHAR(200) NOT NULL,
                    summary VARCHAR(300) NOT NULL,
                    details TEXT NOT NULL,
                    url VARCHAR(300),
                    is_active BOOLEAN DEFAULT {bool_true},
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            '''))
        except Exception:
            pass

        # Create league_events table if not exists
        try:
            is_postgres = "postgresql" in str(engine.url)
            id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_false = "FALSE" if is_postgres else "0"

            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS league_events (
                    id {id_type},
                    name VARCHAR(100) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT {bool_false},
                    is_live_visible BOOLEAN DEFAULT {bool_false},
                    live_fee_usd INTEGER DEFAULT 30,
                    current_stage VARCHAR DEFAULT 'registration',
                    created_at DATETIME
                )
            '''))
        except Exception:
            pass

        # Update league_events if columns missing
        try:
            conn.execute(text("ALTER TABLE league_events ADD COLUMN is_live_visible BOOLEAN DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE league_events ADD COLUMN live_fee_usd INTEGER DEFAULT 30"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE league_events ADD COLUMN current_stage VARCHAR DEFAULT 'registration'"))
        except Exception: pass

        # Update game_sessions for league support
        try:
            conn.execute(text("ALTER TABLE game_sessions ADD COLUMN is_league_game BOOLEAN DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE game_sessions ADD COLUMN league_match_id INTEGER"))
        except Exception: pass

        # Update league_fixtures for stages
        try:
            conn.execute(text("ALTER TABLE league_fixtures ADD COLUMN stage VARCHAR DEFAULT 'group'"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE league_fixtures ADD COLUMN group_name VARCHAR"))
        except Exception: pass

        # Update league_participants for status
        try:
            conn.execute(text("ALTER TABLE league_participants ADD COLUMN status VARCHAR DEFAULT 'active'"))
        except Exception: pass

        # Create seasons table
        try:
            # Check if table exists
            conn.execute(text("SELECT 1 FROM seasons LIMIT 1"))
        except Exception:
            # Table doesn't exist, create it
            is_postgres = "postgresql" in str(engine.url)
            id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_true = "TRUE" if is_postgres else "1"

            conn.execute(text(f'''
                CREATE TABLE IF NOT EXISTS seasons (
                    id {id_type},
                    name VARCHAR(100) NOT NULL,
                    start_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_at DATETIME,
                    is_active BOOLEAN DEFAULT {bool_true}
                )
            '''))

        try:
            # Check if there is an active season, if not create one
            res = conn.execute(text("SELECT COUNT(*) FROM seasons WHERE is_active = :val"), {"val": True if "postgresql" in str(engine.url) else 1}).fetchone()
            if res[0] == 0:
                # Force the Genesis season to start NOW to hide old data
                bool_val = True if "postgresql" in str(engine.url) else 1
                conn.execute(text("INSERT INTO seasons (name, is_active, start_at) VALUES ('Genesis Season', :is_active, :now)"), {"is_active": bool_val, "now": datetime.utcnow()})
        except Exception:
            pass

        conn.commit()
