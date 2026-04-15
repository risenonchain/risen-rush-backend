# Usage: Run this script with your backend environment activated.
# Example: `python create_admin_user.py`

from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

admin_email = "admin@risenonchain.net"
admin_password = "@Adminrisen"

if __name__ == "__main__":
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            user = User(
                email=admin_email,
                username="admin",
                password_hash=get_password_hash(admin_password),
                is_admin=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")
    finally:
        db.close()
