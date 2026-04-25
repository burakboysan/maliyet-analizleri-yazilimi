def normalize_role(role):
    return str(role or "").strip().lower()


def is_owner(role):
    return normalize_role(role) == "owner"


def has_master_admin_capabilities(role):
    return normalize_role(role) in {"master admin", "owner"}


def can_access_user_management(role):
    return is_owner(role)
