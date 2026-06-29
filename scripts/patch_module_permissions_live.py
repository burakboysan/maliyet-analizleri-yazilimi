from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal


BASE = Path("/opt/mobile_api/app")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + f".bak_module_permissions_{STAMP}"))


def replace_once(text_value: str, old: str, new: str, label: str) -> str:
    if old not in text_value:
        raise RuntimeError(f"{label} bulunamadi")
    return text_value.replace(old, new, 1)


def patch_models_admin() -> None:
    path = BASE / "models" / "admin.py"
    content = path.read_text(encoding="utf-8-sig")
    original = content

    content = content.replace("from typing import List, Optional", "from typing import Dict, List, Optional")

    if "module_permissions: Optional[Dict[str, bool]] = None" not in content:
        content = replace_once(
            content,
            "class AdminUser(BaseModel):\n"
            "    id: int\n"
            "    kullanici_adi: str\n"
            "    rol_id: Optional[int] = None\n"
            "    rol_adi: Optional[str] = None\n",
            "class AdminUser(BaseModel):\n"
            "    id: int\n"
            "    kullanici_adi: str\n"
            "    rol_id: Optional[int] = None\n"
            "    rol_adi: Optional[str] = None\n"
            "    module_permissions: Optional[Dict[str, bool]] = None\n",
            "AdminUser",
        )

    if "class UserModulePermissionsRequest" not in content:
        content = replace_once(
            content,
            "class UserSummary(BaseModel):\n"
            "    id: int\n"
            "    kullanici_adi: str\n"
            "    email: Optional[str] = None\n"
            "    rol_adi: Optional[str] = None\n"
            "    email_verified: bool = False\n"
            "    is_active: bool = False\n",
            "class UserSummary(BaseModel):\n"
            "    id: int\n"
            "    kullanici_adi: str\n"
            "    email: Optional[str] = None\n"
            "    rol_adi: Optional[str] = None\n"
            "    email_verified: bool = False\n"
            "    is_active: bool = False\n"
            "    module_permissions: Optional[Dict[str, bool]] = None\n\n\n"
            "class UserModulePermissionsRequest(BaseModel):\n"
            "    module_permissions: Dict[str, bool] = Field(default_factory=dict)\n\n\n"
            "class UserModulePermissionsResponse(BaseModel):\n"
            "    user_id: int\n"
            "    module_permissions: Dict[str, bool] = Field(default_factory=dict)\n",
            "UserSummary",
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_routes_admin() -> None:
    path = BASE / "routes" / "admin.py"
    content = path.read_text(encoding="utf-8")
    original = content

    if "import json\n" not in content.splitlines(True)[:5]:
        content = content.replace("# app/routes/admin.py\n", "# app/routes/admin.py\nimport json\n", 1)
    content = content.replace("from sqlalchemy.sql import func", "from sqlalchemy.sql import func, text")

    if "UserModulePermissionsRequest," not in content:
        content = content.replace(
            "    UpdateUserEmailRequest,\n"
            "    UpdateUserPasswordRequest,\n",
            "    UpdateUserEmailRequest,\n"
            "    UserModulePermissionsRequest,\n"
            "    UserModulePermissionsResponse,\n"
            "    UpdateUserPasswordRequest,\n",
            1,
        )

    if "def _parse_module_permissions" not in content:
        content = replace_once(
            content,
            "def get_leave_service(db: Session = Depends(get_db)) -> LeaveService:\n"
            "    return LeaveService(db)\n\n\n",
            "def get_leave_service(db: Session = Depends(get_db)) -> LeaveService:\n"
            "    return LeaveService(db)\n\n\n"
            "def _parse_module_permissions(raw_value) -> dict[str, bool]:\n"
            "    if not raw_value:\n"
            "        return {}\n"
            "    if isinstance(raw_value, dict):\n"
            "        return {str(key): bool(value) for key, value in raw_value.items()}\n"
            "    try:\n"
            "        payload = json.loads(str(raw_value))\n"
            "    except Exception:\n"
            "        return {}\n"
            "    if not isinstance(payload, dict):\n"
            "        return {}\n"
            "    return {str(key): bool(value) for key, value in payload.items()}\n\n\n"
            "def _get_user_module_permissions_from_db(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n",
            "module permission helpers",
        )

    if "module_permissions=module_permissions" not in content:
        content = replace_once(
            content,
            "def _user_to_summary(user: UserTable) -> UserSummary:\n"
            "    return UserSummary(\n",
            "def _user_to_summary(user: UserTable) -> UserSummary:\n"
            "    db = getattr(getattr(user, \"_sa_instance_state\", None), \"session\", None)\n"
            "    module_permissions = _get_user_module_permissions_from_db(db, user.id) if db else {}\n"
            "    return UserSummary(\n",
            "summary db session",
        )
        content = replace_once(
            content,
            "        email_verified=bool(user.email_verified),\n"
            "        is_active=bool(user.is_active),\n"
            "    )\n",
            "        email_verified=bool(user.email_verified),\n"
            "        is_active=bool(user.is_active),\n"
            "        module_permissions=module_permissions,\n"
            "    )\n",
            "summary module permissions",
        )

    if "@router.get(\"/users/{user_id}/module-permissions\"" not in content:
        content = replace_once(
            content,
            "@router.post(\"/users\", response_model=UserSummary, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_owner)])\n",
            "@router.get(\"/users/{user_id}/module-permissions\", response_model=UserModulePermissionsResponse, dependencies=[Depends(require_owner)])\n"
            "async def get_user_module_permissions(user_id: int, db: Session = Depends(get_db)):\n"
            "    user = db.query(UserTable).filter(UserTable.id == user_id).first()\n"
            "    if not user:\n"
            "        raise HTTPException(status_code=404, detail=\"Kullanici bulunamadi.\")\n"
            "    return UserModulePermissionsResponse(\n"
            "        user_id=user_id,\n"
            "        module_permissions=_get_user_module_permissions_from_db(db, user_id),\n"
            "    )\n\n\n"
            "@router.put(\"/users/{user_id}/module-permissions\", response_model=UserModulePermissionsResponse, dependencies=[Depends(require_owner)])\n"
            "async def update_user_module_permissions(user_id: int, req: UserModulePermissionsRequest, db: Session = Depends(get_db)):\n"
            "    user = db.query(UserTable).filter(UserTable.id == user_id).first()\n"
            "    if not user:\n"
            "        raise HTTPException(status_code=404, detail=\"Kullanici bulunamadi.\")\n"
            "    module_permissions = {str(key): bool(value) for key, value in (req.module_permissions or {}).items()}\n"
            "    db.execute(\n"
            "        text(\"UPDATE kullanicilar SET module_permissions = :module_permissions WHERE id = :user_id\"),\n"
            "        {\"module_permissions\": json.dumps(module_permissions), \"user_id\": user_id},\n"
            "    )\n"
            "    db.commit()\n"
            "    return UserModulePermissionsResponse(user_id=user_id, module_permissions=module_permissions)\n\n\n"
            "@router.post(\"/users\", response_model=UserSummary, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_owner)])\n",
            "module permission endpoints",
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_routes_app_auth() -> None:
    path = BASE / "routes" / "app_auth.py"
    content = path.read_text(encoding="utf-8")
    original = content

    if "import json\n" not in content.splitlines(True)[:5]:
        content = "import json\n\n" + content
    if "from sqlalchemy.sql import text" not in content:
        content = content.replace("from sqlalchemy.orm import Session\n", "from sqlalchemy.orm import Session\nfrom sqlalchemy.sql import text\n", 1)

    if "def _parse_module_permissions" not in content:
        content = replace_once(
            content,
            "router = APIRouter(prefix=\"/auth\", tags=[\"auth\"])\n\n\n",
            "router = APIRouter(prefix=\"/auth\", tags=[\"auth\"])\n\n\n"
            "def _parse_module_permissions(raw_value) -> dict[str, bool]:\n"
            "    if not raw_value:\n"
            "        return {}\n"
            "    if isinstance(raw_value, dict):\n"
            "        return {str(key): bool(value) for key, value in raw_value.items()}\n"
            "    try:\n"
            "        payload = json.loads(str(raw_value))\n"
            "    except Exception:\n"
            "        return {}\n"
            "    if not isinstance(payload, dict):\n"
            "        return {}\n"
            "    return {str(key): bool(value) for key, value in payload.items()}\n\n\n"
            "def _get_user_module_permissions(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n",
            "app auth helpers",
        )

    if "module_permissions=_get_user_module_permissions(db, user.id)" not in content:
        content = content.replace(
            "            rol_id=user.rol_id,\n"
            "            rol_adi=user.role.rol_adi if user.role else None,\n"
            "        ),\n",
            "            rol_id=user.rol_id,\n"
            "            rol_adi=user.role.rol_adi if user.role else None,\n"
            "            module_permissions=_get_user_module_permissions(db, user.id),\n"
            "        ),\n",
            1,
        )

    content = content.replace(
        "async def app_me(current_user: UserTable = Depends(require_authenticated_user)):",
        "async def app_me(current_user: UserTable = Depends(require_authenticated_user), db: Session = Depends(get_db)):",
    )

    if "module_permissions=_get_user_module_permissions(db, current_user.id)" not in content:
        content = content.replace(
            "        rol_id=current_user.rol_id,\n"
            "        rol_adi=current_user.role.rol_adi if current_user.role else None,\n"
            "    )\n",
            "        rol_id=current_user.rol_id,\n"
            "        rol_adi=current_user.role.rol_adi if current_user.role else None,\n"
            "        module_permissions=_get_user_module_permissions(db, current_user.id),\n"
            "    )\n",
            1,
        )

    if "@router.get(\"/me/module-permissions\")" not in content:
        content += (
            "\n\n@router.get(\"/me/module-permissions\")\n"
            "async def app_me_module_permissions(\n"
            "    current_user: UserTable = Depends(require_authenticated_user),\n"
            "    db: Session = Depends(get_db),\n"
            "):\n"
            "    return {\n"
            "        \"user_id\": current_user.id,\n"
            "        \"module_permissions\": _get_user_module_permissions(db, current_user.id),\n"
            "    }\n"
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_auth_schema() -> None:
    path = BASE / "auth.py"
    content = path.read_text(encoding="utf-8")
    original = content
    if "module_permissions" not in content:
        content = replace_once(
            content,
            "    if not _column_exists(\"locked_until\"):\n"
            "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN locked_until DATETIME NULL\"))\n",
            "    if not _column_exists(\"locked_until\"):\n"
            "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN locked_until DATETIME NULL\"))\n"
            "    if not _column_exists(\"module_permissions\"):\n"
            "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN module_permissions JSON NULL\"))\n",
            "auth schema module permissions",
        )
    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def ensure_db_column() -> None:
    db = SessionLocal()
    try:
        exists = db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'kullanicilar' AND column_name = 'module_permissions'"
            )
        ).first()
        if exists is None:
            db.execute(text("ALTER TABLE kullanicilar ADD COLUMN module_permissions JSONB NULL"))
            db.commit()
    finally:
        db.close()


def main() -> None:
    patch_models_admin()
    patch_routes_admin()
    patch_routes_app_auth()
    patch_auth_schema()
    ensure_db_column()
    print("MODULE_PERMISSIONS_PATCH_OK")


if __name__ == "__main__":
    main()
