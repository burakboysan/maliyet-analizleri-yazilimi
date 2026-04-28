from __future__ import annotations

from sqlalchemy import text

from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                UPDATE documents
                SET language = 'en'
                WHERE LOWER(COALESCE(title, '')) LIKE '%- en%'
                   OR LOWER(COALESCE(description, '')) LIKE '%english%'
                """
            )
        )
        db.commit()
        print(f"DOCUMENT_LANGUAGE_MIGRATION_OK updated={result.rowcount}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
