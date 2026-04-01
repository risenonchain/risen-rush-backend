from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=72)
    referral_code: str | None = Field(default=None, max_length=64)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=8)
    new_password: str = Field(min_length=6, max_length=72)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    wallet_address: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)
    generated_avatar_url: str | None = Field(default=None, max_length=500)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None
    expires_at: str | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool
    email_verified: bool
    referral_code: str | None = None
    wallet_address: str | None = None
    avatar_url: str | None = None
    generated_avatar_url: str | None = None
    vault_trials: int = 0
    is_admin: bool = False

    class Config:
        from_attributes = True