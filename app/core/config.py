from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "RISEN Rush API"
    secret_key: str = "change-this-in-production-super-secret-risen-rush-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./risen_rush.db"


settings = Settings()