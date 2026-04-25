from datetime import datetime, timedelta


LOGIN_RATE_LIMIT = (5, 10)
VERIFICATION_SEND_RATE_LIMIT = (3, 10)
VERIFICATION_VERIFY_RATE_LIMIT = (5, 10)
PASSWORD_RESET_SEND_RATE_LIMIT = (3, 10)
PASSWORD_RESET_VERIFY_RATE_LIMIT = (5, 10)
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


class AuthSecurityError(ValueError):
    """Authentication security rule violation."""


def _normalize_key(value):
    return str(value or "").strip().lower()


def _require_column(cursor, table_name, column_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    if not cursor.fetchone():
        raise AuthSecurityError(
            f"Gerekli veritabani kolonu eksik: {table_name}.{column_name}. Lutfen sistem yoneticisine basvurun."
        )


def _require_table(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    if not cursor.fetchone():
        raise AuthSecurityError(
            f"Gerekli veritabani tablosu eksik: {table_name}. Lutfen sistem yoneticisine basvurun."
        )


def ensure_auth_security_schema(cursor):
    _require_column(cursor, "kullanicilar", "failed_login_attempts")
    _require_column(cursor, "kullanicilar", "locked_until")
    _require_table(cursor, "auth_rate_limits")


def consume_rate_limit(cursor, action_type, target_key, limit_count, window_minutes, message):
    normalized_key = _normalize_key(target_key)
    if not normalized_key:
        return

    now = datetime.now()
    cursor.execute(
        """
        SELECT id, attempt_count, window_started_at
        FROM auth_rate_limits
        WHERE action_type = %s AND target_key = %s
        LIMIT 1
        """,
        (action_type, normalized_key),
    )
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            """
            INSERT INTO auth_rate_limits (action_type, target_key, window_started_at, attempt_count)
            VALUES (%s, %s, %s, %s)
            """,
            (action_type, normalized_key, now, 1),
        )
        return

    if isinstance(row, dict):
        row_id = row.get("id")
        attempt_count = row.get("attempt_count")
        window_started_at = row.get("window_started_at")
    else:
        row_id, attempt_count, window_started_at = row
    elapsed_seconds = max(0, int((now - window_started_at).total_seconds()))
    window_seconds = window_minutes * 60

    if elapsed_seconds >= window_seconds:
        cursor.execute(
            """
            UPDATE auth_rate_limits
            SET window_started_at = %s, attempt_count = %s
            WHERE id = %s
            """,
            (now, 1, row_id),
        )
        return

    if int(attempt_count) >= limit_count:
        retry_after_seconds = max(1, window_seconds - elapsed_seconds)
        retry_after_minutes = max(1, (retry_after_seconds + 59) // 60)
        raise AuthSecurityError(f"{message} Lutfen {retry_after_minutes} dakika sonra tekrar deneyin.")

    cursor.execute(
        "UPDATE auth_rate_limits SET attempt_count = attempt_count + 1 WHERE id = %s",
        (row_id,),
    )


def ensure_account_not_locked(user_row):
    locked_until = None
    if isinstance(user_row, dict):
        locked_until = user_row.get("locked_until")
    if locked_until and locked_until > datetime.now():
        remaining_seconds = max(1, int((locked_until - datetime.now()).total_seconds()))
        remaining_minutes = max(1, (remaining_seconds + 59) // 60)
        raise AuthSecurityError(
            f"Hesabiniz gecici olarak kilitlendi. Lutfen {remaining_minutes} dakika sonra tekrar deneyin."
        )


def register_failed_login(cursor, user_row):
    user_id = user_row.get("id") if isinstance(user_row, dict) else None
    if not user_id:
        return

    failed_attempts = int(user_row.get("failed_login_attempts") or 0) + 1
    if failed_attempts >= LOCKOUT_THRESHOLD:
        locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        cursor.execute(
            """
            UPDATE kullanicilar
            SET failed_login_attempts = 0,
                locked_until = %s
            WHERE id = %s
            """,
            (locked_until, user_id),
        )
        raise AuthSecurityError(
            f"Cok sayida hatali giris denemesi algilandi. Hesap {LOCKOUT_MINUTES} dakika kilitlendi."
        )

    cursor.execute(
        """
        UPDATE kullanicilar
        SET failed_login_attempts = %s
        WHERE id = %s
        """,
        (failed_attempts, user_id),
    )


def clear_login_failures(cursor, user_id):
    if not user_id:
        return

    cursor.execute(
        """
        UPDATE kullanicilar
        SET failed_login_attempts = 0,
            locked_until = NULL
        WHERE id = %s
        """,
        (user_id,),
    )
