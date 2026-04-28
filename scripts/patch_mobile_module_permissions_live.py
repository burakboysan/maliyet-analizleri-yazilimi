from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal


BASE = Path("/opt/mobile_api/app")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + f".bak_mobile_module_permissions_{STAMP}"))


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if old not in content:
        raise RuntimeError(f"{label} bulunamadi")
    return content.replace(old, new, 1)


def patch_tables() -> None:
    path = BASE / "db" / "tables.py"
    content = path.read_text(encoding="utf-8")
    original = content
    if "mobile_module_permissions = Column" not in content:
        if "module_permissions = Column" in content:
            content = replace_once(
                content,
                "    module_permissions = Column(JSON, nullable=True)\n",
                "    module_permissions = Column(JSON, nullable=True)\n"
                "    mobile_module_permissions = Column(JSON, nullable=True)\n",
                "tables mobile permissions",
            )
        else:
            content = replace_once(
                content,
                "    leave_notification_email = Column(Boolean, nullable=False, default=True)\n",
                "    leave_notification_email = Column(Boolean, nullable=False, default=True)\n"
                "    mobile_module_permissions = Column(JSON, nullable=True)\n",
                "tables mobile permissions",
            )
    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_models_admin() -> None:
    path = BASE / "models" / "admin.py"
    content = path.read_text(encoding="utf-8-sig")
    original = content
    content = content.replace("from typing import List, Optional", "from typing import Dict, List, Optional")

    if "mobile_module_permissions: Optional[Dict[str, bool]] = None" not in content:
        if "module_permissions: Optional[Dict[str, bool]] = None" in content:
            content = replace_once(
                content,
                "    module_permissions: Optional[Dict[str, bool]] = None\n",
                "    module_permissions: Optional[Dict[str, bool]] = None\n"
                "    mobile_module_permissions: Optional[Dict[str, bool]] = None\n",
                "models mobile field",
            )
        else:
            content = replace_once(
                content,
                "    is_active: bool = False\n",
                "    is_active: bool = False\n"
                "    mobile_module_permissions: Optional[Dict[str, bool]] = None\n",
                "models mobile field",
            )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_auth_schema() -> None:
    path = BASE / "auth.py"
    content = path.read_text(encoding="utf-8")
    original = content
    if "mobile_module_permissions" not in content:
        if "module_permissions" in content:
            content = replace_once(
                content,
                "    if not _column_exists(\"module_permissions\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN module_permissions JSON NULL\"))\n",
                "    if not _column_exists(\"module_permissions\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN module_permissions JSON NULL\"))\n"
                "    if not _column_exists(\"mobile_module_permissions\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN mobile_module_permissions JSON NULL\"))\n",
                "auth schema mobile permissions",
            )
        else:
            content = replace_once(
                content,
                "    if not _column_exists(\"locked_until\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN locked_until DATETIME NULL\"))\n",
                "    if not _column_exists(\"locked_until\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN locked_until DATETIME NULL\"))\n"
                "    if not _column_exists(\"mobile_module_permissions\"):\n"
                "        db.execute(text(\"ALTER TABLE kullanicilar ADD COLUMN mobile_module_permissions JSON NULL\"))\n",
                "auth schema mobile permissions",
            )
    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_routes_admin() -> None:
    path = BASE / "routes" / "admin.py"
    content = path.read_text(encoding="utf-8")
    original = content

    if "def _get_user_mobile_module_permissions_from_db" not in content:
        content = replace_once(
            content,
            "def _get_user_module_permissions_from_db(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n",
            "def _get_user_module_permissions_from_db(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n"
            "def _get_user_mobile_module_permissions_from_db(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT mobile_module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"mobile_module_permissions\") if row else None)\n\n\n",
            "admin mobile helper",
        )

    if "mobile_module_permissions=mobile_module_permissions" not in content:
        content = replace_once(
            content,
            "    module_permissions = _get_user_module_permissions_from_db(db, user.id) if db else {}\n"
            "    return UserSummary(\n",
            "    module_permissions = _get_user_module_permissions_from_db(db, user.id) if db else {}\n"
            "    mobile_module_permissions = _get_user_mobile_module_permissions_from_db(db, user.id) if db else {}\n"
            "    return UserSummary(\n",
            "summary mobile db session",
        )
        content = replace_once(
            content,
            "        module_permissions=module_permissions,\n"
            "    )\n",
            "        module_permissions=module_permissions,\n"
            "        mobile_module_permissions=mobile_module_permissions,\n"
            "    )\n",
            "summary mobile permissions",
        )

    if "@router.get(\"/users/{user_id}/mobile-module-permissions\"" not in content:
        insert_before = "@router.post(\"/users\", response_model=UserSummary, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_owner)])\n"
        content = replace_once(
            content,
            insert_before,
            "@router.get(\"/users/{user_id}/mobile-module-permissions\", dependencies=[Depends(require_owner)])\n"
            "async def get_user_mobile_module_permissions(user_id: int, db: Session = Depends(get_db)):\n"
            "    user = db.query(UserTable).filter(UserTable.id == user_id).first()\n"
            "    if not user:\n"
            "        raise HTTPException(status_code=404, detail=\"Kullanici bulunamadi.\")\n"
            "    return {\n"
            "        \"user_id\": user_id,\n"
            "        \"mobile_module_permissions\": _get_user_mobile_module_permissions_from_db(db, user_id),\n"
            "    }\n\n\n"
            "@router.put(\"/users/{user_id}/mobile-module-permissions\", dependencies=[Depends(require_owner)])\n"
            "async def update_user_mobile_module_permissions(user_id: int, req: dict, db: Session = Depends(get_db)):\n"
            "    user = db.query(UserTable).filter(UserTable.id == user_id).first()\n"
            "    if not user:\n"
            "        raise HTTPException(status_code=404, detail=\"Kullanici bulunamadi.\")\n"
            "    raw_permissions = (req or {}).get(\"mobile_module_permissions\") or {}\n"
            "    mobile_module_permissions = {str(key): bool(value) for key, value in raw_permissions.items()}\n"
            "    db.execute(\n"
            "        text(\"UPDATE kullanicilar SET mobile_module_permissions = :mobile_module_permissions WHERE id = :user_id\"),\n"
            "        {\"mobile_module_permissions\": json.dumps(mobile_module_permissions), \"user_id\": user_id},\n"
            "    )\n"
            "    db.commit()\n"
            "    return {\"user_id\": user_id, \"mobile_module_permissions\": mobile_module_permissions}\n\n\n"
            + insert_before,
            "admin mobile endpoints",
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_routes_app_auth() -> None:
    path = BASE / "routes" / "app_auth.py"
    content = path.read_text(encoding="utf-8")
    original = content

    if "def _get_user_mobile_module_permissions" not in content:
        content = replace_once(
            content,
            "def _get_user_module_permissions(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n",
            "def _get_user_module_permissions(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"module_permissions\") if row else None)\n\n\n"
            "def _get_user_mobile_module_permissions(db: Session, user_id: int) -> dict[str, bool]:\n"
            "    row = db.execute(\n"
            "        text(\"SELECT mobile_module_permissions FROM kullanicilar WHERE id = :user_id\"),\n"
            "        {\"user_id\": int(user_id)},\n"
            "    ).mappings().first()\n"
            "    return _parse_module_permissions(row.get(\"mobile_module_permissions\") if row else None)\n\n\n",
            "app auth mobile helper",
        )

    if "@router.get(\"/me/mobile-module-permissions\")" not in content:
        content += (
            "\n\n@router.get(\"/me/mobile-module-permissions\")\n"
            "async def app_me_mobile_module_permissions(\n"
            "    current_user: UserTable = Depends(require_authenticated_user),\n"
            "    db: Session = Depends(get_db),\n"
            "):\n"
            "    return {\n"
            "        \"user_id\": current_user.id,\n"
            "        \"mobile_module_permissions\": _get_user_mobile_module_permissions(db, current_user.id),\n"
            "    }\n"
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def ensure_db_column() -> None:
    db = SessionLocal()
    try:
        exists = db.execute(text("SHOW COLUMNS FROM kullanicilar LIKE 'mobile_module_permissions'")).first()
        if exists is None:
            db.execute(text("ALTER TABLE kullanicilar ADD COLUMN mobile_module_permissions JSON NULL"))
            db.commit()
    finally:
        db.close()


def main() -> None:
    patch_tables()
    patch_models_admin()
    patch_auth_schema()
    patch_routes_admin()
    patch_routes_app_auth()
    ensure_db_column()
    print("MOBILE_MODULE_PERMISSIONS_PATCH_OK")


if __name__ == "__main__":
    main()
