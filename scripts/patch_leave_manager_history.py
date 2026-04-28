from pathlib import Path


MODEL_PATH = Path("/opt/mobile_api/app/models/leave.py")
SERVICE_PATH = Path("/opt/mobile_api/app/services/leave_service.py")


def patch_models() -> None:
    text = MODEL_PATH.read_text(encoding="utf-8")
    if "\n    manager_requests: list[LeaveRequestSummary]" not in text:
        text = text.replace(
            "    notifications: list[LeaveNotificationItem]\n",
            "    manager_requests: list[LeaveRequestSummary] = []\n"
            "    notifications: list[LeaveNotificationItem]\n",
        )
    MODEL_PATH.write_text(text, encoding="utf-8")


def patch_service() -> None:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    if "\n        manager_requests = (\n" not in text:
        text = text.replace(
            "        notifications = (\n",
            "        manager_requests = (\n"
            "            self.db.query(LeaveRequestTable)\n"
            "            .filter(LeaveRequestTable.manager_user_id == current_user.id)\n"
            "            .order_by(LeaveRequestTable.created_at.desc())\n"
            "            .limit(100)\n"
            "            .all()\n"
            "        )\n"
            "        notifications = (\n",
        )
    if "manager_requests=[self._to_leave_summary(item) for item in manager_requests]" not in text:
        text = text.replace(
            "            pending_manager_requests=[self._to_leave_summary(item) for item in pending_manager_requests],\n"
            "            notifications=[self._to_notification(item) for item in notifications],\n",
            "            pending_manager_requests=[self._to_leave_summary(item) for item in pending_manager_requests],\n"
            "            manager_requests=[self._to_leave_summary(item) for item in manager_requests],\n"
            "            notifications=[self._to_notification(item) for item in notifications],\n",
        )
    SERVICE_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_models()
    patch_service()
    print("leave manager history patched")
