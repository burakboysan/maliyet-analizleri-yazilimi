from pathlib import Path


ADMIN_PATH = Path("/opt/mobile_api/app/routes/admin.py")
SERVICE_PATH = Path("/opt/mobile_api/app/services/leave_service.py")


def patch_admin() -> None:
    text = ADMIN_PATH.read_text(encoding="utf-8-sig")
    if "LeaveRequestSummary" not in text.split("from app.models.leave import", 1)[1].split(")", 1)[0]:
        text = text.replace(
            "from app.models.leave import LeaveAdminUserItem, LeaveAdminUserUpdateRequest",
            "from app.models.leave import LeaveAdminUserItem, LeaveAdminUserUpdateRequest, LeaveRequestSummary",
        )

    marker = "\n\n@router.put(\"/leave/users/{user_id}\""
    endpoint = '''

@router.get("/leave/users/{user_id}/requests", response_model=List[LeaveRequestSummary], dependencies=[Depends(require_owner)])
async def get_leave_admin_user_requests(
    user_id: int,
    leave_service: LeaveService = Depends(get_leave_service),
):
    try:
        return leave_service.list_admin_user_requests(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
'''
    if "def get_leave_admin_user_requests" not in text:
        text = text.replace(marker, endpoint + marker)

    ADMIN_PATH.write_text(text, encoding="utf-8")


def patch_service() -> None:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    marker = "\n    def update_admin_user(self, user_id: int, payload: LeaveAdminUserUpdateRequest) -> LeaveAdminUserItem:"
    method = '''
    def list_admin_user_requests(self, user_id: int) -> list[LeaveRequestSummary]:
        user = self.db.query(UserTable).filter(UserTable.id == user_id).first()
        if not user:
            raise ValueError("Kullanici bulunamadi.")
        requests = (
            self.db.query(LeaveRequestTable)
            .filter(LeaveRequestTable.user_id == user_id)
            .order_by(LeaveRequestTable.created_at.desc())
            .limit(100)
            .all()
        )
        return [self._to_leave_summary(item) for item in requests]

'''
    if "def list_admin_user_requests" not in text:
        text = text.replace(marker, "\n" + method + marker.lstrip("\n"))

    SERVICE_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_admin()
    patch_service()
    print("leave admin request endpoint patched")
