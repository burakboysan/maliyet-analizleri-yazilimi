from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal


BASE = Path("/opt/mobile_api/app")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + f".bak_document_language_{STAMP}"))


def replace_once(content: str, old: str, new: str, label: str) -> str:
    if old not in content:
        raise RuntimeError(f"{label} bulunamadi")
    return content.replace(old, new, 1)


def patch_tables() -> None:
    path = BASE / "db" / "tables.py"
    content = path.read_text(encoding="utf-8-sig")
    original = content

    if "    language = Column(String(5), nullable=False, default=\"tr\", index=True)\n" not in content:
        content = replace_once(
            content,
            "    document_type = Column(String(50), nullable=False, index=True)\n"
            "    file_url = Column(String(500), nullable=False)\n",
            "    document_type = Column(String(50), nullable=False, index=True)\n"
            "    language = Column(String(5), nullable=False, default=\"tr\", index=True)\n"
            "    file_url = Column(String(500), nullable=False)\n",
            "DocumentTable.language",
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def patch_documents_route() -> None:
    path = BASE / "routes" / "documents.py"
    content = path.read_text(encoding="utf-8")
    original = content

    if "ALLOWED_DOCUMENT_LANGUAGES" not in content:
        content = replace_once(
            content,
            "ALLOWED_DOCUMENT_TYPES = {\"brosur\", \"teknik_foy\", \"kullanim_kilavuzu\"}\n",
            "ALLOWED_DOCUMENT_TYPES = {\"brosur\", \"teknik_foy\", \"kullanim_kilavuzu\"}\n"
            "ALLOWED_DOCUMENT_LANGUAGES = {\"tr\", \"en\"}\n",
            "allowed document languages",
        )

    if "    language: str = Field(default=\"tr\", min_length=2, max_length=5)\n" not in content:
        content = replace_once(
            content,
            "    document_type: str = Field(..., min_length=1, max_length=50)\n"
            "    file_url: str = Field(..., min_length=1, max_length=500)\n",
            "    document_type: str = Field(..., min_length=1, max_length=50)\n"
            "    language: str = Field(default=\"tr\", min_length=2, max_length=5)\n"
            "    file_url: str = Field(..., min_length=1, max_length=500)\n",
            "DocumentCreateRequest.language",
        )

    if "def _normalize_document_language(language: str | None) -> str:" not in content:
        content = replace_once(
            content,
            "def _normalize_document_type(document_type: str) -> str:\n"
            "    normalized = document_type.strip().lower()\n"
            "    if normalized not in ALLOWED_DOCUMENT_TYPES:\n"
            "        raise HTTPException(status_code=400, detail=\"Invalid document_type\")\n"
            "    return normalized\n\n\n",
            "def _normalize_document_type(document_type: str) -> str:\n"
            "    normalized = document_type.strip().lower()\n"
            "    if normalized not in ALLOWED_DOCUMENT_TYPES:\n"
            "        raise HTTPException(status_code=400, detail=\"Invalid document_type\")\n"
            "    return normalized\n\n\n"
            "def _normalize_document_language(language: str | None) -> str:\n"
            "    normalized = (language or \"tr\").strip().lower()\n"
            "    if normalized not in ALLOWED_DOCUMENT_LANGUAGES:\n"
            "        raise HTTPException(status_code=400, detail=\"Invalid document language\")\n"
            "    return normalized\n\n\n",
            "document language normalizer",
        )

    if "        \"language\": row.language or \"tr\",\n" not in content:
        content = replace_once(
            content,
            "        \"document_type\": row.document_type,\n"
            "        \"file_url\": row.file_url,\n",
            "        \"document_type\": row.document_type,\n"
            "        \"language\": row.language or \"tr\",\n"
            "        \"file_url\": row.file_url,\n",
            "serialized document language",
        )

    if "    language: Optional[str] = Query(default=None),\n" not in content:
        content = replace_once(
            content,
            "    document_type: Optional[str] = Query(default=None, alias=\"type\"),\n"
            "    active_only: bool = True,\n",
            "    document_type: Optional[str] = Query(default=None, alias=\"type\"),\n"
            "    language: Optional[str] = Query(default=None),\n"
            "    active_only: bool = True,\n",
            "list_documents language query",
        )

    if "    if language:\n        query = query.filter(DocumentTable.language == _normalize_document_language(language))\n\n" not in content:
        content = replace_once(
            content,
            "    if document_type:\n"
            "        query = query.filter(DocumentTable.document_type == _normalize_document_type(document_type))\n\n"
            "    rows = (\n",
            "    if document_type:\n"
            "        query = query.filter(DocumentTable.document_type == _normalize_document_type(document_type))\n\n"
            "    if language:\n"
            "        query = query.filter(DocumentTable.language == _normalize_document_language(language))\n\n"
            "    rows = (\n",
            "list_documents language filter",
        )

    if "        language=_normalize_document_language(payload.language),\n" not in content:
        content = replace_once(
            content,
            "        document_type=_normalize_document_type(payload.document_type),\n"
            "        file_url=payload.file_url.strip(),\n",
            "        document_type=_normalize_document_type(payload.document_type),\n"
            "        language=_normalize_document_language(payload.language),\n"
            "        file_url=payload.file_url.strip(),\n",
            "create_document language",
        )

    if "    language: str = Form(default=\"tr\"),\n" not in content:
        content = replace_once(
            content,
            "    document_type: str = Form(...),\n"
            "    description: Optional[str] = Form(default=None),\n",
            "    document_type: str = Form(...),\n"
            "    language: str = Form(default=\"tr\"),\n"
            "    description: Optional[str] = Form(default=None),\n",
            "upload_document language form",
        )

    if "    normalized_language = _normalize_document_language(language)\n" not in content:
        content = replace_once(
            content,
            "    normalized_type = _normalize_document_type(document_type)\n"
            "    normalized_series_key = series_key.strip().upper()\n",
            "    normalized_type = _normalize_document_type(document_type)\n"
            "    normalized_language = _normalize_document_language(language)\n"
            "    normalized_series_key = series_key.strip().upper()\n",
            "upload_document normalized language",
        )

    if "        language=normalized_language,\n" not in content:
        content = replace_once(
            content,
            "        document_type=normalized_type,\n"
            "        file_url=public_url,\n",
            "        document_type=normalized_type,\n"
            "        language=normalized_language,\n"
            "        file_url=public_url,\n",
            "upload_document table language",
        )

    if content != original:
        backup(path)
        path.write_text(content, encoding="utf-8")


def ensure_db_column() -> None:
    db = SessionLocal()
    try:
        exists = db.execute(text("SHOW COLUMNS FROM documents LIKE 'language'")).first()
        if exists is None:
            db.execute(text("ALTER TABLE documents ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'tr'"))
            db.execute(text("CREATE INDEX idx_documents_language ON documents (language)"))
            db.commit()
    finally:
        db.close()


def main() -> None:
    patch_tables()
    patch_documents_route()
    ensure_db_column()
    print("DOCUMENT_LANGUAGE_PATCH_OK")


if __name__ == "__main__":
    main()
