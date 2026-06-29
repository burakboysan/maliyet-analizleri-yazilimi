from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.db import get_connection
from app.core.security import require_current_user, require_module_access


router = APIRouter(prefix="/leave", tags=["leave"])


class LeaveCreateRequest(BaseModel):
    leave_type: str = "YILLIK_IZIN"
    start_date: str
    end_date: str
    requested_days: float | int | str | None = None
    reason: str | None = None
    employee_note: str | None = None


class LeaveApproveRequest(BaseModel):
    approval_mode: str = "BAKIYEDEN_DUSECEK"
    approved_days: float | int | str | None = None
    manager_note: str | None = None


class LeaveRejectRequest(BaseModel):
    manager_note: str | None = None


class LeaveFinalizeRequest(BaseModel):
    actual_used_days: float | int | str
    manager_note: str | None = None


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _datetime_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")
    return str(value)


def _parse_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} YYYY-MM-DD formatinda olmalidir.") from exc


def _is_owner(user: dict[str, Any]) -> bool:
    return str(user.get("rol_adi") or "").strip().lower() == "owner"


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_name} sayisal olmalidir.") from exc


def _clean_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _work_days(connection: Any, start_date: date, end_date: date) -> float:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bitis tarihi baslangic tarihinden once olamaz.")

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT DATE(holiday_date) AS holiday_date
        FROM resmi_tatiller
        WHERE is_public = 1
          AND DATE(holiday_date) BETWEEN %s AND %s
        """,
        (start_date, end_date),
    )
    holidays = {row["holiday_date"] for row in cursor.fetchall()}
    current = start_date
    total = 0
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            total += 1
        current += timedelta(days=1)
    return float(total)


def _get_or_create_balance(cursor, user_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT *
        FROM izin_bakiyeleri
        WHERE user_id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (user_id,),
    )
    balance = cursor.fetchone()
    if balance:
        return balance

    cursor.execute(
        """
        INSERT INTO izin_bakiyeleri
          (user_id, annual_allowance_days, carried_over_days, reserved_days, used_days, pending_approval_days)
        VALUES (%s, 14, 0, 0, 0, 0)
        """,
        (user_id,),
    )
    cursor.execute(
        """
        SELECT *
        FROM izin_bakiyeleri
        WHERE user_id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (user_id,),
    )
    return cursor.fetchone() or {}


def _add_movement(cursor, user_id: int, leave_request_id: int, movement_type: str, day_amount: float, description: str, created_by_user_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO izin_hareketleri
          (leave_request_id, user_id, movement_type, day_amount, description, created_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (leave_request_id, user_id, movement_type, day_amount, description, created_by_user_id),
    )


def _fetch_request(cursor, leave_request_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT it.*, k.kullanici_adi AS user_name
        FROM izin_talepleri it
        LEFT JOIN kullanicilar k ON k.id = it.user_id
        WHERE it.id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (leave_request_id,),
    )
    leave_request = cursor.fetchone()
    if not leave_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Izin talebi bulunamadi.")
    return leave_request


def _ensure_manager(current_user: dict[str, Any], leave_request: dict[str, Any]) -> None:
    current_user_id = int(current_user["id"])
    if _is_owner(current_user) or int(leave_request.get("manager_user_id") or 0) == current_user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu izin talebi icin yonetici yetkiniz yok.")


def _remaining_days(balance: dict[str, Any]) -> float:
    return (
        float(balance.get("annual_allowance_days") or 0)
        + float(balance.get("carried_over_days") or 0)
        - float(balance.get("reserved_days") or 0)
        - float(balance.get("used_days") or 0)
        - float(balance.get("pending_approval_days") or 0)
    )


def _get_manager_user_id(cursor, user_id: int) -> int | None:
    cursor.execute("SELECT manager_user_id FROM kullanicilar WHERE id = %s LIMIT 1", (user_id,))
    row = cursor.fetchone() or {}
    manager_user_id = row.get("manager_user_id")
    if manager_user_id:
        return int(manager_user_id)

    cursor.execute(
        """
        SELECT k.id
        FROM kullanicilar k
        LEFT JOIN roller r ON r.id = k.rol_id
        WHERE LOWER(COALESCE(r.rol_adi, '')) = 'owner'
          AND k.id <> %s
        ORDER BY k.id
        LIMIT 1
        """,
        (user_id,),
    )
    owner = cursor.fetchone()
    return int(owner["id"]) if owner else None


def _request_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "user_name": row.get("user_name"),
        "manager_user_id": row.get("manager_user_id"),
        "leave_type": row.get("leave_type"),
        "approval_mode": row.get("approval_mode"),
        "status": row.get("status"),
        "start_date": _date_text(row.get("start_date")),
        "end_date": _date_text(row.get("end_date")),
        "requested_days": row.get("requested_days"),
        "reserved_days": row.get("reserved_days"),
        "approved_days": row.get("approved_days"),
        "actual_used_days": row.get("actual_used_days"),
        "remaining_days_after": row.get("remaining_days_after"),
        "reason": row.get("reason"),
        "employee_note": row.get("employee_note"),
        "manager_note": row.get("manager_note"),
        "usage_confirmation_requested_at": _datetime_text(row.get("usage_confirmation_requested_at")),
        "finalized_at": _datetime_text(row.get("finalized_at")),
        "created_at": _datetime_text(row.get("created_at")),
        "updated_at": _datetime_text(row.get("updated_at")),
    }


def _request_rows(cursor, where_sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cursor.execute(
        f"""
        SELECT
          it.*,
          k.kullanici_adi AS user_name
        FROM izin_talepleri it
        LEFT JOIN kullanicilar k ON k.id = it.user_id
        {where_sql}
        ORDER BY it.created_at DESC, it.id DESC
        LIMIT 100
        """,
        params,
    )
    return [_request_row(row) for row in cursor.fetchall()]


@router.get("/workday-summary")
def get_workday_summary(
    start_date: str = Query(...),
    end_date: str = Query(...),
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "work_days": _work_days(connection, start, end),
    }


@router.get("/dashboard")
def get_leave_dashboard(
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    user_id = int(current_user["id"])
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
          annual_allowance_days,
          carried_over_days,
          reserved_days,
          used_days,
          pending_approval_days,
          updated_at
        FROM izin_bakiyeleri
        WHERE user_id = %s
        LIMIT 1
        """,
        (user_id,),
    )
    balance = cursor.fetchone() or {
        "annual_allowance_days": 0,
        "carried_over_days": 0,
        "reserved_days": 0,
        "used_days": 0,
        "pending_approval_days": 0,
        "updated_at": None,
    }
    available_days = (
        float(balance.get("annual_allowance_days") or 0)
        + float(balance.get("carried_over_days") or 0)
        - float(balance.get("reserved_days") or 0)
        - float(balance.get("used_days") or 0)
        - float(balance.get("pending_approval_days") or 0)
    )
    balance["available_days"] = available_days
    balance["updated_at"] = _datetime_text(balance.get("updated_at"))

    my_requests = _request_rows(cursor, "WHERE it.user_id = %s", (user_id,))
    manager_where = "WHERE it.manager_user_id = %s"
    manager_params: tuple[Any, ...] = (user_id,)
    if _is_owner(current_user):
        manager_where = "WHERE it.user_id <> %s"
        manager_params = (user_id,)
    manager_requests = _request_rows(cursor, manager_where, manager_params)
    pending_manager_requests = [
        item
        for item in manager_requests
        if item.get("status") in {"BEKLEMEDE", "KULLANIM_ONAYI_BEKLIYOR", "ONAYLANDI"}
    ]

    return {
        "balance": balance,
        "my_requests": my_requests,
        "manager_requests": manager_requests,
        "pending_manager_requests": pending_manager_requests,
    }


@router.post("/requests")
def create_leave_request(
    payload: LeaveCreateRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    user_id = int(current_user["id"])
    start = _parse_date(payload.start_date, "start_date")
    end = _parse_date(payload.end_date, "end_date")
    requested_days = _work_days(connection, start, end)
    if payload.requested_days is not None:
        requested_days = _to_float(payload.requested_days, "requested_days")
    if requested_days <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Secilen tarih araliginda izin dusulecek is gunu bulunamadi.")

    cursor = connection.cursor(dictionary=True)
    try:
        manager_user_id = _get_manager_user_id(cursor, user_id)
        if not manager_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Izin yoneticisi tanimli degil.")

        balance = _get_or_create_balance(cursor, user_id)
        cursor.execute(
            """
            UPDATE izin_bakiyeleri
            SET reserved_days = COALESCE(reserved_days, 0) + %s,
                pending_approval_days = COALESCE(pending_approval_days, 0) + %s,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (requested_days, requested_days, user_id),
        )
        cursor.execute(
            """
            INSERT INTO izin_talepleri
              (user_id, manager_user_id, leave_type, approval_mode, status, start_date, end_date,
               requested_days, reserved_days, approved_days, reason, employee_note)
            VALUES (%s, %s, %s, 'BAKIYEDEN_DUSECEK', 'BEKLEMEDE', %s, %s, %s, %s, 0, %s, %s)
            """,
            (
                user_id,
                manager_user_id,
                _clean_text(payload.leave_type) or "YILLIK_IZIN",
                start,
                end,
                requested_days,
                requested_days,
                _clean_text(payload.reason),
                _clean_text(payload.employee_note),
            ),
        )
        leave_request_id = int(cursor.lastrowid)
        _add_movement(
            cursor,
            user_id,
            leave_request_id,
            "TALEP_REZERV",
            requested_days,
            "Izin talebi icin gun rezerve edildi.",
            user_id,
        )
        connection.commit()
        request_row = _fetch_request(cursor, leave_request_id)
        request_row["remaining_days_after"] = _remaining_days(balance) - requested_days
        return _request_row(request_row)
    except Exception:
        connection.rollback()
        raise


@router.post("/requests/{leave_request_id}/cancel")
def cancel_leave_request(
    leave_request_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    user_id = int(current_user["id"])
    cursor = connection.cursor(dictionary=True)
    try:
        leave_request = _fetch_request(cursor, leave_request_id)
        if int(leave_request.get("user_id") or 0) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu izin talebi size ait degil.")
        if leave_request.get("status") in {"REDDEDILDI", "TAMAMLANDI", "IPTAL_EDILDI"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu durumdaki izin talebi iptal edilemez.")

        reserved = float(leave_request.get("reserved_days") or 0)
        _get_or_create_balance(cursor, user_id)
        if reserved > 0:
            cursor.execute(
                """
                UPDATE izin_bakiyeleri
                SET reserved_days = GREATEST(0, COALESCE(reserved_days, 0) - %s),
                    pending_approval_days = GREATEST(0, COALESCE(pending_approval_days, 0) - %s),
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (reserved, reserved, user_id),
            )
            _add_movement(cursor, user_id, leave_request_id, "IPTAL_IADE", reserved, "Iptal edilen izin talebi icin rezerve gunler iade edildi.", user_id)

        cursor.execute(
            """
            UPDATE izin_talepleri
            SET status = 'IPTAL_EDILDI',
                reserved_days = 0,
                manager_note = COALESCE(manager_note, 'Talep kullanici tarafindan iptal edildi.'),
                updated_at = NOW()
            WHERE id = %s
            """,
            (leave_request_id,),
        )
        connection.commit()
        return _request_row(_fetch_request(cursor, leave_request_id))
    except Exception:
        connection.rollback()
        raise


@router.post("/requests/{leave_request_id}/approve")
def approve_leave_request(
    leave_request_id: int,
    payload: LeaveApproveRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    manager_user_id = int(current_user["id"])
    approval_mode = (_clean_text(payload.approval_mode) or "BAKIYEDEN_DUSECEK").upper()
    if approval_mode not in {"BAKIYEDEN_DUSECEK", "YONETICI_IZNI"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Gecersiz onay modu.")

    cursor = connection.cursor(dictionary=True)
    try:
        leave_request = _fetch_request(cursor, leave_request_id)
        _ensure_manager(current_user, leave_request)
        if leave_request.get("status") not in {"BEKLEMEDE"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sadece bekleyen izin talepleri onaylanabilir.")

        user_id = int(leave_request["user_id"])
        reserved = float(leave_request.get("reserved_days") or 0)
        approved_days = _to_float(payload.approved_days, "approved_days") if payload.approved_days is not None else float(leave_request.get("requested_days") or 0)
        if approved_days <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Onaylanan gun sayisi sifirdan buyuk olmalidir.")

        _get_or_create_balance(cursor, user_id)
        pending_release = reserved
        reserved_release = reserved if approval_mode == "YONETICI_IZNI" else max(0.0, reserved - approved_days)
        if pending_release > 0 or reserved_release > 0:
            cursor.execute(
                """
                UPDATE izin_bakiyeleri
                SET pending_approval_days = GREATEST(0, COALESCE(pending_approval_days, 0) - %s),
                    reserved_days = GREATEST(0, COALESCE(reserved_days, 0) - %s),
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (pending_release, reserved_release, user_id),
            )
        cursor.execute(
            """
            UPDATE izin_talepleri
            SET status = 'ONAYLANDI',
                approval_mode = %s,
                approved_days = %s,
                reserved_days = %s,
                manager_note = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (approval_mode, approved_days, 0 if approval_mode == "YONETICI_IZNI" else approved_days, _clean_text(payload.manager_note), leave_request_id),
        )
        _add_movement(cursor, user_id, leave_request_id, "ONAY", approved_days, "Izin talebi onaylandi.", manager_user_id)
        connection.commit()
        return _request_row(_fetch_request(cursor, leave_request_id))
    except Exception:
        connection.rollback()
        raise


@router.post("/requests/{leave_request_id}/reject")
def reject_leave_request(
    leave_request_id: int,
    payload: LeaveRejectRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    manager_user_id = int(current_user["id"])
    cursor = connection.cursor(dictionary=True)
    try:
        leave_request = _fetch_request(cursor, leave_request_id)
        _ensure_manager(current_user, leave_request)
        if leave_request.get("status") in {"REDDEDILDI", "TAMAMLANDI", "IPTAL_EDILDI"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu durumdaki izin talebi reddedilemez.")

        user_id = int(leave_request["user_id"])
        reserved = float(leave_request.get("reserved_days") or 0)
        _get_or_create_balance(cursor, user_id)
        if reserved > 0:
            cursor.execute(
                """
                UPDATE izin_bakiyeleri
                SET reserved_days = GREATEST(0, COALESCE(reserved_days, 0) - %s),
                    pending_approval_days = GREATEST(0, COALESCE(pending_approval_days, 0) - %s),
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (reserved, reserved, user_id),
            )
        cursor.execute(
            """
            UPDATE izin_talepleri
            SET status = 'REDDEDILDI',
                reserved_days = 0,
                manager_note = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (_clean_text(payload.manager_note), leave_request_id),
        )
        _add_movement(cursor, user_id, leave_request_id, "RED", reserved, "Izin talebi reddedildi.", manager_user_id)
        connection.commit()
        return _request_row(_fetch_request(cursor, leave_request_id))
    except Exception:
        connection.rollback()
        raise


@router.post("/requests/{leave_request_id}/mark-usage-confirmation")
def mark_leave_usage_confirmation(
    leave_request_id: int,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    cursor = connection.cursor(dictionary=True)
    try:
        leave_request = _fetch_request(cursor, leave_request_id)
        _ensure_manager(current_user, leave_request)
        if leave_request.get("status") != "ONAYLANDI":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sadece onaylanmis izinler kullanim onayina alinabilir.")
        cursor.execute(
            """
            UPDATE izin_talepleri
            SET status = 'KULLANIM_ONAYI_BEKLIYOR',
                usage_confirmation_requested_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (leave_request_id,),
        )
        connection.commit()
        return _request_row(_fetch_request(cursor, leave_request_id))
    except Exception:
        connection.rollback()
        raise


@router.post("/requests/{leave_request_id}/finalize")
def finalize_leave_request(
    leave_request_id: int,
    payload: LeaveFinalizeRequest,
    connection: Any = Depends(get_connection),
    current_user: dict = Depends(require_current_user),
):
    require_module_access(current_user, "leave_management")
    manager_user_id = int(current_user["id"])
    actual_used_days = _to_float(payload.actual_used_days, "actual_used_days")
    if actual_used_days < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fiili gun negatif olamaz.")

    cursor = connection.cursor(dictionary=True)
    try:
        leave_request = _fetch_request(cursor, leave_request_id)
        _ensure_manager(current_user, leave_request)
        if leave_request.get("status") not in {"ONAYLANDI", "KULLANIM_ONAYI_BEKLIYOR"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sadece onaylanmis izinler kesinlestirilebilir.")

        user_id = int(leave_request["user_id"])
        reserved = float(leave_request.get("reserved_days") or 0)
        approval_mode = str(leave_request.get("approval_mode") or "BAKIYEDEN_DUSECEK")
        balance = _get_or_create_balance(cursor, user_id)
        used_increment = actual_used_days if approval_mode == "BAKIYEDEN_DUSECEK" else 0
        cursor.execute(
            """
            UPDATE izin_bakiyeleri
            SET reserved_days = GREATEST(0, COALESCE(reserved_days, 0) - %s),
                pending_approval_days = GREATEST(0, COALESCE(pending_approval_days, 0) - %s),
                used_days = COALESCE(used_days, 0) + %s,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (reserved, reserved, used_increment, user_id),
        )
        updated_balance = {
            **balance,
            "reserved_days": max(0.0, float(balance.get("reserved_days") or 0) - reserved),
            "pending_approval_days": max(0.0, float(balance.get("pending_approval_days") or 0) - reserved),
            "used_days": float(balance.get("used_days") or 0) + used_increment,
        }
        remaining = _remaining_days(updated_balance)
        cursor.execute(
            """
            UPDATE izin_talepleri
            SET status = 'TAMAMLANDI',
                actual_used_days = %s,
                remaining_days_after = %s,
                manager_note = COALESCE(%s, manager_note),
                finalized_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (actual_used_days, remaining, _clean_text(payload.manager_note), leave_request_id),
        )
        _add_movement(cursor, user_id, leave_request_id, "KULLANIM", actual_used_days, "Izin kullanimi kesinlestirildi.", manager_user_id)
        connection.commit()
        return _request_row(_fetch_request(cursor, leave_request_id))
    except Exception:
        connection.rollback()
        raise
