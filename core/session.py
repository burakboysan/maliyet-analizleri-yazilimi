"""Uygulama oturumu boyunca gerekli gecici bilgileri tutar."""

_session_state = {
    "kullanici_adi": None,
    "sifre": None,
    "rol": None,
    "app_token": None,
    "admin_token": None,
    "module_permissions": None,
}


def set_session(kullanici_adi=None, sifre=None, rol=None, app_token=None, admin_token=None, module_permissions=None):
    if kullanici_adi is not None:
        _session_state["kullanici_adi"] = kullanici_adi
    if sifre is not None:
        _session_state["sifre"] = sifre
    if rol is not None:
        _session_state["rol"] = rol
    if app_token is not None:
        _session_state["app_token"] = app_token
    if admin_token is not None:
        _session_state["admin_token"] = admin_token
    if module_permissions is not None:
        _session_state["module_permissions"] = module_permissions


def clear_session():
    _session_state["kullanici_adi"] = None
    _session_state["sifre"] = None
    _session_state["rol"] = None
    _session_state["app_token"] = None
    _session_state["admin_token"] = None
    _session_state["module_permissions"] = None


def get_session():
    return dict(_session_state)


def get_username():
    return _session_state.get("kullanici_adi")


def get_password():
    return _session_state.get("sifre")


def get_role():
    return _session_state.get("rol")


def get_app_token():
    return _session_state.get("app_token")


def get_admin_token():
    return _session_state.get("admin_token")


def get_module_permissions():
    return _session_state.get("module_permissions")
