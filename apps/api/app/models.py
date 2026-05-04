from pydantic import BaseModel


class LoginRequest(BaseModel):
    kullanici_adi: str
    sifre: str


class UserResponse(BaseModel):
    id: int
    kullanici_adi: str
    rol_id: int | None = None
    rol_adi: str | None = None
    module_permissions: dict[str, bool] = {}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
