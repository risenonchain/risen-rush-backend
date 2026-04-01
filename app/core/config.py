import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "RISEN Rush API"

    secret_key: str = os.getenv(
        "SECRET_KEY",
        "change-this-in-production-super-secret-risen-rush-key",
    )

    algorithm: str = os.getenv("ALGORITHM", "HS256")

    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )

    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./risen_rush.db_v2",
    )

    turnstile_secret_key: str = os.getenv("TURNSTILE_SECRET_KEY", "")
    turnstile_site_key: str = os.getenv("NEXT_PUBLIC_TURNSTILE_SITE_KEY", "")
    turnstile_enabled: bool = os.getenv("TURNSTILE_ENABLED", "false").lower() == "true"


settings = Settings()