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

        # Update league_events if columns missing
        try:
            conn.execute(text("ALTER TABLE league_events ADD COLUMN is_live_visible BOOLEAN DEFAULT 0"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE league_events ADD COLUMN live_fee_usd INTEGER DEFAULT 30"))
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

        conn.commit()
