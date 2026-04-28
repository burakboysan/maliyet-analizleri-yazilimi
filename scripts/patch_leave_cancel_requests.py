from pathlib import Path


ROUTE_PATH = Path("/opt/mobile_api/app/routes/leave.py")
SERVICE_PATH = Path("/opt/mobile_api/app/services/leave_service.py")


def patch_routes() -> None:
    text = ROUTE_PATH.read_text(encoding="utf-8")
    endpoint = '''

@router.post("/requests/{leave_request_id}/cancel", response_model=LeaveRequestSummary)
async def cancel_leave_request(
    leave_request_id: int,
    current_user: UserTable = Depends(require_authenticated_user),
    leave_service: LeaveService = Depends(get_leave_service),
):
    try:
        return leave_service.cancel_leave_request(current_user, leave_request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
'''
    if "def cancel_leave_request(" not in text:
        text = text.replace("\n\n@router.post(\"/requests/{leave_request_id}/approve\"", endpoint + "\n\n@router.post(\"/requests/{leave_request_id}/approve\"")
    ROUTE_PATH.write_text(text, encoding="utf-8")


def patch_service() -> None:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    method = '''
    def cancel_leave_request(self, current_user: UserTable, leave_request_id: int) -> LeaveRequestSummary:
        leave_request = (
            self.db.query(LeaveRequestTable)
            .filter(LeaveRequestTable.id == leave_request_id, LeaveRequestTable.user_id == current_user.id)
            .first()
        )
        if not leave_request:
            raise ValueError("Izin talebi bulunamadi veya bu islem icin yetkiniz yok.")
        if leave_request.status in {
            LeaveStatus.REDDEDILDI.value,
            LeaveStatus.TAMAMLANDI.value,
            LeaveStatus.IPTAL_EDILDI.value,
        }:
            raise ValueError("Bu durumdaki izin talebi iptal edilemez.")

        balance = self._get_or_create_balance(leave_request.user_id)
        reserved = float(leave_request.reserved_days or 0)
        if reserved > 0:
            balance.reserved_days = max(0.0, float(balance.reserved_days or 0) - reserved)
            balance.pending_approval_days = max(0.0, float(balance.pending_approval_days or 0) - reserved)
            self._add_movement(
                leave_request.user_id,
                leave_request.id,
                "IPTAL_IADE",
                reserved,
                "Iptal edilen izin talebi icin rezerve gunler iade edildi.",
                current_user.id,
            )

        leave_request.status = LeaveStatus.IPTAL_EDILDI.value
        leave_request.reserved_days = 0
        leave_request.manager_note = leave_request.manager_note or "Talep kullanici tarafindan iptal edildi."
        if leave_request.manager_user_id:
            self._create_notification(
                user_id=leave_request.manager_user_id,
                title="Izin talebi iptal edildi",
                message=f"{current_user.kullanici_adi} izin talebini iptal etti.",
                notification_type="LEAVE_CANCELLED",
                related_entity_id=leave_request.id,
            )
        self.db.commit()
        self.db.refresh(leave_request)
        return self._to_leave_summary(leave_request)

'''
    if "def cancel_leave_request(self, current_user: UserTable" not in text:
        text = text.replace("\n    def approve_leave_request(self, manager_user: UserTable", "\n" + method + "    def approve_leave_request(self, manager_user: UserTable")
    SERVICE_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_routes()
    patch_service()
    print("leave cancel endpoint patched")
