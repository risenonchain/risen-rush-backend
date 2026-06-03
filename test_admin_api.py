import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.point_wallet import PointWallet
from datetime import datetime

# Use your Render DB URL here for local testing if needed
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not set")
    exit(1)

engine = create_engine(DATABASE_URL)

def test_user_fetch():
    print("--- Testing Admin User Query Logic ---")
    try:
        with Session(engine) as db:
            # Replicating the logic in routes_admin.py: get_detailed_users
            query = db.query(User, PointWallet).join(PointWallet, User.id == PointWallet.user_id)
            results = query.limit(5).all()

            print(f"Found {len(results)} users with wallets.")

            for u, w in results:
                print(f"User: {u.username} (ID: {u.id})")
                # Try to access all fields used in the response
                data = {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "is_premium": u.is_premium,
                    "premium_expires_at": u.premium_expires_at, # Check if this crashes
                    "best_score": u.best_score,
                    "best_level": u.best_level,
                    "available_points": w.available_points,
                    "total_points_earned": w.total_points_earned,
                }
                print(f"  Data OK: {data['username']} | Expires: {data['premium_expires_at']}")

    except Exception as e:
        print(f"CRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_fetch()
