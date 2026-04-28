"""FastAPI ile haberlesen ortak istemci yardimcilari."""

import json
import os
from urllib import error, parse, request


DEFAULT_API_BASE_URL = "http://34.163.45.18/"
DEFAULT_TIMEOUT_SECONDS = 30


class ApiClientError(Exception):
    """API istemci hatalari icin ozel exception."""


def _api_base_url():
    configured_url = str(os.getenv("BOMAKSAN_API_BASE_URL", DEFAULT_API_BASE_URL)).strip()
    if not configured_url:
        configured_url = DEFAULT_API_BASE_URL
    if not configured_url.endswith("/"):
        configured_url += "/"
    return configured_url


def _build_url(path):
    return parse.urljoin(_api_base_url(), path.lstrip("/"))


def _decode_response(response):
    body = response.read().decode("utf-8")
    if not body.strip():
        return None
    return json.loads(body)


def _build_http_error_message(exc):
    detail = None
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        detail = payload.get("detail")
    except Exception:
        detail = None

    if isinstance(detail, list):
        detail = " | ".join(str(item) for item in detail if item)

    if exc.code == 400:
        return detail or "Gonderilen bilgiler gecersiz."
    if exc.code == 401:
        return detail or "Yetkilendirme gerekli."
    if exc.code == 403:
        return detail or "Bu islem icin yetkiniz yok."
    if exc.code == 404:
        return detail or "Istenen kaynak bulunamadi."
    if exc.code == 422:
        return detail or "Gonderilen alanlar dogrulamadan gecemedi."
    return detail or f"HTTP {exc.code} hatasi olustu."


def request_json(method, path, payload=None, headers=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    data = None
    final_headers = {"Accept": "application/json"}
    if headers:
        final_headers.update(headers)

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        final_headers["Content-Type"] = "application/json"

    req = request.Request(_build_url(path), data=data, headers=final_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return _decode_response(response)
    except error.HTTPError as exc:
        raise ApiClientError(_build_http_error_message(exc)) from exc
    except error.URLError as exc:
        raise ApiClientError(f"Sunucuya baglanilamadi: {exc.reason}") from exc
    except Exception as exc:
        raise ApiClientError(str(exc)) from exc


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def app_login(kullanici_adi, sifre):
    return request_json(
        "POST",
        "/auth/login",
        payload={
            "kullanici_adi": str(kullanici_adi or "").strip(),
            "sifre": str(sifre or ""),
        },
    )


def app_signup(kullanici_adi, email, sifre):
    return request_json(
        "POST",
        "/auth/signup",
        payload={
            "kullanici_adi": str(kullanici_adi or "").strip(),
            "email": str(email or "").strip(),
            "sifre": str(sifre or ""),
        },
    )


def send_password_reset_code(identifier):
    return request_json(
        "POST",
        "/admin/auth/password/send-reset-code",
        payload={"identifier": str(identifier or "").strip()},
    )


def reset_password_with_code(identifier, code, new_password):
    return request_json(
        "POST",
        "/admin/auth/password/reset",
        payload={
            "identifier": str(identifier or "").strip(),
            "code": str(code or "").strip(),
            "new_password": str(new_password or ""),
        },
    )


def send_verification_email(email):
    return request_json(
        "POST",
        "/admin/auth/email/send-verification",
        payload={"email": str(email or "").strip()},
    )


def verify_email_code(email, code):
    return request_json(
        "POST",
        "/admin/auth/email/verify",
        payload={"email": str(email or "").strip(), "code": str(code or "").strip()},
    )


def list_roles(token):
    response = request_json("GET", "/admin/roles", headers=auth_headers(token))
    return response or []


def list_users(token):
    response = request_json("GET", "/admin/users", headers=auth_headers(token))
    return response or []


def get_my_module_permissions(token):
    response = request_json("GET", "/auth/me/module-permissions", headers=auth_headers(token))
    return (response or {}).get("module_permissions")


def get_my_mobile_module_permissions(token):
    response = request_json("GET", "/auth/me/mobile-module-permissions", headers=auth_headers(token))
    return (response or {}).get("mobile_module_permissions")


def get_user_module_permissions(token, user_id):
    response = request_json("GET", f"/admin/users/{int(user_id)}/module-permissions", headers=auth_headers(token))
    return (response or {}).get("module_permissions")


def get_user_mobile_module_permissions(token, user_id):
    response = request_json("GET", f"/admin/users/{int(user_id)}/mobile-module-permissions", headers=auth_headers(token))
    return (response or {}).get("mobile_module_permissions")


def update_user_module_permissions(token, user_id, module_permissions):
    return request_json(
        "PUT",
        f"/admin/users/{int(user_id)}/module-permissions",
        payload={"module_permissions": module_permissions or {}},
        headers=auth_headers(token),
    )


def update_user_mobile_module_permissions(token, user_id, mobile_module_permissions):
    return request_json(
        "PUT",
        f"/admin/users/{int(user_id)}/mobile-module-permissions",
        payload={"mobile_module_permissions": mobile_module_permissions or {}},
        headers=auth_headers(token),
    )


def create_user(token, payload):
    return request_json("POST", "/admin/users", payload=payload, headers=auth_headers(token))


def delete_user(token, user_id):
    return request_json("DELETE", f"/admin/users/{int(user_id)}", headers=auth_headers(token))


def update_user_password(token, user_id, new_password):
    return request_json(
        "POST",
        f"/admin/users/{int(user_id)}/password",
        payload={"new_password": str(new_password or "")},
        headers=auth_headers(token),
    )


def update_user_email(token, user_id, email):
    return request_json(
        "PUT",
        f"/admin/users/{int(user_id)}/email",
        payload={"email": str(email or "").strip()},
        headers=auth_headers(token),
    )


def resend_user_verification(token, user_id):
    return request_json(
        "POST",
        f"/admin/users/{int(user_id)}/send-verification",
        headers=auth_headers(token),
    )


def list_leave_admin_users(token):
    response = request_json("GET", "/admin/leave/users", headers=auth_headers(token))
    return response or []


def get_user_leave_management(token, user_id):
    users = list_leave_admin_users(token)
    for row in users:
        if int(row.get("user_id") or 0) == int(user_id):
            return {
                "kullanici_id": row.get("user_id"),
                "yonetici_id": row.get("manager_user_id"),
                "yonetici_adi": row.get("manager_kullanici_adi"),
                "annual_allowance_days": row.get("annual_allowance_days"),
                "carried_over_days": row.get("carried_over_days"),
                "rezerv_izin_gunleri": row.get("reserved_days"),
                "used_days": row.get("used_days"),
                "kalan_izin_bakiyesi": row.get("available_days"),
            }
    return {}


def update_user_leave_management(token, user_id, payload):
    current = get_user_leave_management(token, user_id)
    annual_allowance = float(current.get("annual_allowance_days") or 0)
    used_days = float(current.get("used_days") or 0)
    reserved_days = float(current.get("rezerv_izin_gunleri") or 0)
    desired_available = float(payload.get("kalan_izin_bakiyesi") or 0)
    carried_over_days = desired_available + used_days + reserved_days - annual_allowance
    if carried_over_days < 0:
        annual_allowance = desired_available + used_days + reserved_days
        carried_over_days = 0

    return request_json(
        "PUT",
        f"/admin/leave/users/{int(user_id)}",
        payload={
            "manager_user_id": payload.get("yonetici_id"),
            "annual_allowance_days": annual_allowance,
            "carried_over_days": carried_over_days,
            "leave_notification_email": True,
        },
        headers=auth_headers(token),
    )


def list_user_leave_requests(token, user_id):
    response = request_json("GET", f"/admin/leave/users/{int(user_id)}/requests", headers=auth_headers(token))
    return response or []


def get_leave_dashboard(token):
    return request_json("GET", "/leave/dashboard", headers=auth_headers(token)) or {}


def get_leave_workday_summary(token, start_date, end_date):
    query = parse.urlencode({"start_date": str(start_date), "end_date": str(end_date)})
    return request_json("GET", f"/leave/workday-summary?{query}", headers=auth_headers(token)) or {}


def create_leave_request(token, payload):
    return request_json("POST", "/leave/requests", payload=payload, headers=auth_headers(token))


def cancel_leave_request(token, request_id):
    return request_json("POST", f"/leave/requests/{int(request_id)}/cancel", headers=auth_headers(token))


def approve_leave_request(token, request_id, payload):
    return request_json("POST", f"/leave/requests/{int(request_id)}/approve", payload=payload, headers=auth_headers(token))


def reject_leave_request(token, request_id, manager_note=None):
    return request_json(
        "POST",
        f"/leave/requests/{int(request_id)}/reject",
        payload={"manager_note": str(manager_note or "").strip() or None},
        headers=auth_headers(token),
    )


def mark_leave_usage_confirmation(token, request_id):
    return request_json("POST", f"/leave/requests/{int(request_id)}/mark-usage-confirmation", headers=auth_headers(token))


def finalize_leave_request(token, request_id, actual_used_days, manager_note=None):
    return request_json(
        "POST",
        f"/leave/requests/{int(request_id)}/finalize",
        payload={
            "actual_used_days": float(actual_used_days),
            "manager_note": str(manager_note or "").strip() or None,
        },
        headers=auth_headers(token),
    )


def get_dashboard_stats(token):
    return request_json("GET", "/desktop/dashboard/stats", headers=auth_headers(token))


def get_mobile_price_list(token):
    response = request_json("GET", "/desktop/mobile-price-list", headers=auth_headers(token))
    return response or []


def save_mobile_price_list(token, rows):
    return request_json(
        "PUT",
        "/desktop/mobile-price-list",
        payload={"rows": rows},
        headers=auth_headers(token),
    )


def get_mobile_price_list_product_options(token, search=None, limit=500):
    query = {"limit": int(limit)}
    if search:
        query["search"] = str(search).strip()
    path = "/desktop/mobile-price-list/product-options"
    if query:
        path += "?" + parse.urlencode(query)
    response = request_json("GET", path, headers=auth_headers(token))
    return response or []


def get_mobile_price_list_form_options(token):
    response = request_json("GET", "/desktop/mobile-price-list/form-options", headers=auth_headers(token))
    return response or {}


def mobile_price_list_code_exists(token, urun_kodu):
    path = "/desktop/mobile-price-list/code-exists?" + parse.urlencode({"urun_kodu": str(urun_kodu or "").strip()})
    response = request_json("GET", path, headers=auth_headers(token))
    return bool((response or {}).get("exists"))


def get_mobile_price_list_costs(token, codes):
    codes = [str(code or "").strip() for code in codes if str(code or "").strip()]
    if not codes:
        return []
    path = "/desktop/mobile-price-list/costs?" + parse.urlencode([("codes", code) for code in codes])
    response = request_json("GET", path, headers=auth_headers(token))
    return response or []


def create_mobile_price_list_entry(token, payload):
    return request_json(
        "POST",
        "/desktop/mobile-price-list/create",
        payload=payload,
        headers=auth_headers(token),
    )


def list_ai_leads(token, filters=None):
    query = {}
    for key, value in (filters or {}).items():
        if value not in (None, ""):
            query[str(key)] = str(value)
    path = "/desktop/ai-leads"
    if query:
        path += "?" + parse.urlencode(query)
    response = request_json("GET", path, headers=auth_headers(token))
    return response or []


def search_apollo_ai_leads(token, payload):
    return request_json("POST", "/desktop/ai-leads/apollo/search", payload=payload, headers=auth_headers(token)) or {}


def search_apollo_segment_leads(token, payload):
    return request_json("POST", "/desktop/ai-leads/apollo/segment-search", payload=payload, headers=auth_headers(token)) or {}


def search_serpapi_domains(token, payload):
    return request_json("POST", "/desktop/ai-leads/serpapi/search", payload=payload, headers=auth_headers(token)) or {}


def list_ai_search_recipes(token):
    response = request_json("GET", "/desktop/ai-leads/search-recipes", headers=auth_headers(token))
    return response or []


def create_ai_search_recipe(token, payload):
    return request_json(
        "POST",
        "/desktop/ai-leads/search-recipes",
        payload=payload,
        headers=auth_headers(token),
    ) or {}


def update_ai_search_recipe(token, recipe_id, payload):
    return request_json(
        "PUT",
        f"/desktop/ai-leads/search-recipes/{int(recipe_id)}",
        payload=payload,
        headers=auth_headers(token),
    ) or {}


def import_apollo_seed_domains(token, domains, per_domain_people=5, enrich=True):
    return request_json(
        "POST",
        "/desktop/ai-leads/apollo/domain-import",
        payload={
            "domains": domains,
            "per_domain_people": int(per_domain_people or 5),
            "enrich": bool(enrich),
        },
        headers=auth_headers(token),
    ) or {}


def enrich_ai_lead_from_apollo(token, lead_id):
    return request_json("POST", f"/desktop/ai-leads/{int(lead_id)}/apollo-enrich", headers=auth_headers(token)) or {}


def enrich_ai_lead_from_hunter(token, lead_id):
    return request_json("POST", f"/desktop/ai-leads/{int(lead_id)}/hunter-domain-search", headers=auth_headers(token)) or {}


def search_hunter_companies(token, payload):
    return request_json("POST", "/desktop/ai-leads/hunter/company-search", payload=payload or {}, headers=auth_headers(token), timeout=90) or {}


def get_ai_lead_detail(token, lead_id):
    return request_json("GET", f"/desktop/ai-leads/{int(lead_id)}", headers=auth_headers(token)) or {}


def create_ai_lead(token, payload):
    return request_json("POST", "/desktop/ai-leads", payload=payload, headers=auth_headers(token))


def import_ai_leads_csv(token, rows):
    return request_json("POST", "/desktop/ai-leads/import", payload={"rows": rows}, headers=auth_headers(token))


def analyze_ai_lead(token, lead_id):
    return request_json("POST", f"/desktop/ai-leads/{int(lead_id)}/analyze", headers=auth_headers(token))


def deep_research_ai_lead(token, lead_id):
    return request_json("POST", f"/desktop/ai-leads/{int(lead_id)}/deep-research", headers=auth_headers(token), timeout=120) or {}


def update_ai_lead_segment(token, lead_id, payload):
    return request_json("PUT", f"/desktop/ai-leads/{int(lead_id)}/segment", payload=payload, headers=auth_headers(token))


def update_ai_lead_status(token, lead_id, status, note=None):
    return request_json(
        "PUT",
        f"/desktop/ai-leads/{int(lead_id)}/status",
        payload={"status": str(status or "").strip(), "note": str(note or "").strip() or None},
        headers=auth_headers(token),
    ) or {}


def exclude_ai_lead(token, lead_id, reason):
    return request_json(
        "POST",
        f"/desktop/ai-leads/{int(lead_id)}/exclude",
        payload={"reason": str(reason or "").strip()},
        headers=auth_headers(token),
    )


def delete_ai_lead(token, lead_id):
    return request_json("DELETE", f"/desktop/ai-leads/{int(lead_id)}", headers=auth_headers(token)) or {}


def generate_ai_email_draft(token, lead_id, step_number=1):
    return request_json(
        "POST",
        f"/desktop/ai-leads/{int(lead_id)}/email-drafts",
        payload={"step_number": int(step_number or 1)},
        headers=auth_headers(token),
    )


def generate_ai_email_sequence(token, lead_id):
    return request_json(
        "POST",
        f"/desktop/ai-leads/{int(lead_id)}/sequence-drafts",
        headers=auth_headers(token),
    ) or {}


def approve_ai_email_draft(token, draft_id):
    return request_json("POST", f"/desktop/ai-leads/email-drafts/{int(draft_id)}/approve", headers=auth_headers(token))


def list_ai_segments(token):
    response = request_json("GET", "/desktop/ai-leads/segments", headers=auth_headers(token))
    return response or []


def list_ai_sequences(token):
    response = request_json("GET", "/desktop/ai-leads/sequences", headers=auth_headers(token))
    return response or []


def get_projects(token):
    response = request_json("GET", "/desktop/projects", headers=auth_headers(token))
    return response or []


def project_code_exists(token, proje_kodu):
    path = "/desktop/projects/code-exists?" + parse.urlencode({"proje_kodu": str(proje_kodu or "").strip()})
    response = request_json("GET", path, headers=auth_headers(token))
    return bool((response or {}).get("exists"))


def get_next_project_reference(token):
    response = request_json("GET", "/desktop/projects/next-reference", headers=auth_headers(token))
    return (response or {}).get("proje_referans_no") or ""


def get_customer_options(token):
    response = request_json("GET", "/desktop/customers", headers=auth_headers(token))
    return (response or {}).get("musteriler") or []


def create_customer(token, payload):
    return request_json("POST", "/desktop/customers", payload=payload, headers=auth_headers(token))


def create_project(token, payload):
    return request_json("POST", "/desktop/projects", payload=payload, headers=auth_headers(token))


def delete_projects(token, proje_referans_nolari):
    refs = [str(item or "").strip() for item in proje_referans_nolari if str(item or "").strip()]
    path = "/desktop/projects"
    if refs:
        path += "?" + parse.urlencode([("proje_referans_nolari", ref) for ref in refs])
    return request_json("DELETE", path, headers=auth_headers(token))


def get_project_detail(token, proje_referans_no):
    return request_json(
        "GET",
        f"/desktop/projects/{parse.quote(str(proje_referans_no or '').strip(), safe='')}",
        headers=auth_headers(token),
    )


def get_product_detail(token, product_id):
    return request_json(
        "GET",
        f"/products/{int(product_id)}",
        headers=auth_headers(token),
    ) or {}


def list_products(token, search=None, page=1, page_size=200):
    query = {
        "page": int(page),
        "page_size": int(page_size),
    }
    if search:
        query["search"] = str(search).strip()
    return request_json(
        "GET",
        f"/products?{parse.urlencode(query)}",
        headers=auth_headers(token),
    ) or {}


def get_product_tree_read_data(token, product_id):
    return request_json(
        "GET",
        f"/desktop/products/{int(product_id)}/tree-read",
        headers=auth_headers(token),
    ) or {}


def update_product_tree_item_quantity(token, item_id, miktar):
    return request_json(
        "PUT",
        f"/desktop/product-tree/items/{int(item_id)}/quantity",
        payload={"miktar": float(miktar)},
        headers=auth_headers(token),
    ) or {}


def delete_product_tree_items(token, item_ids):
    normalized_ids = [int(item_id) for item_id in list(item_ids or [])]
    return request_json(
        "POST",
        "/desktop/product-tree/items/delete",
        payload={"item_ids": normalized_ids},
        headers=auth_headers(token),
    ) or {}


def save_product_labor(token, product_id, labor_rows):
    return request_json(
        "PUT",
        f"/desktop/products/{int(product_id)}/labor",
        payload={"labor_rows": list(labor_rows or [])},
        headers=auth_headers(token),
    ) or {}


def search_product_tree_materials(token, material_type, q=None):
    query = {"material_type": str(material_type or "").strip()}
    if q:
        query["q"] = str(q).strip()
    return request_json(
        "GET",
        f"/desktop/product-tree/material-search?{parse.urlencode(query)}",
        headers=auth_headers(token),
    ) or []


def resolve_product_tree_material_codes(token, codes):
    return request_json(
        "POST",
        "/desktop/product-tree/material-codes/resolve",
        payload={"codes": list(codes or [])},
        headers=auth_headers(token),
    ) or {}


def add_product_tree_material_items(token, product_id, items):
    return request_json(
        "POST",
        "/desktop/product-tree/material-items",
        payload={"product_id": int(product_id), "items": list(items or [])},
        headers=auth_headers(token),
    ) or {}


def list_product_tree_sub_product_types(token):
    return request_json(
        "GET",
        "/desktop/product-tree/sub-product-types",
        headers=auth_headers(token),
    ) or {}


def search_product_tree_sub_products(token, exclude_product_id, tip=None, q=None):
    query = {"exclude_product_id": int(exclude_product_id)}
    if tip:
        query["tip"] = str(tip).strip()
    if q:
        query["q"] = str(q).strip()
    return request_json(
        "GET",
        f"/desktop/product-tree/sub-product-search?{parse.urlencode(query)}",
        headers=auth_headers(token),
    ) or []


def add_product_tree_sub_products(token, main_product_id, sub_product_ids, miktar):
    return request_json(
        "POST",
        "/desktop/product-tree/sub-products",
        payload={
            "main_product_id": int(main_product_id),
            "sub_product_ids": [int(item_id) for item_id in list(sub_product_ids or [])],
            "miktar": float(miktar),
        },
        headers=auth_headers(token),
    ) or {}


def create_configurator_product(token, payload):
    return request_json(
        "POST",
        "/desktop/products/configurator-create",
        payload=payload,
        headers=auth_headers(token),
    ) or {}


def delete_products(token, product_codes):
    return request_json(
        "POST",
        "/desktop/products/delete",
        payload={"product_codes": list(product_codes or [])},
        headers=auth_headers(token),
    ) or {}


def get_project_assignees(token):
    response = request_json("GET", "/desktop/projects/assignees", headers=auth_headers(token))
    return (response or {}).get("kullanicilar") or []


def get_project_quotes(token, proje_referans_no):
    response = request_json(
        "GET",
        f"/desktop/projects/{parse.quote(str(proje_referans_no or '').strip(), safe='')}/quotes",
        headers=auth_headers(token),
    )
    return response or []


def get_quote_detail(token, teklif_kodu):
    return request_json(
        "GET",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}",
        headers=auth_headers(token),
    )


def quote_exists(token, teklif_kodu):
    response = request_json(
        "GET",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}/exists",
        headers=auth_headers(token),
    )
    return bool((response or {}).get("exists"))


def upsert_quote(token, payload):
    return request_json(
        "POST",
        "/desktop/quotes",
        payload=payload,
        headers=auth_headers(token),
    )


def get_quote_cost_summary(token, teklif_kodu):
    return request_json(
        "GET",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}/cost-summary",
        headers=auth_headers(token),
    ) or {}


def get_quote_items(token, teklif_kodu):
    return request_json(
        "GET",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}/items",
        headers=auth_headers(token),
    ) or {}


def get_quote_item_detail(token, item_id):
    return request_json(
        "GET",
        f"/desktop/quote-items/{int(item_id)}/detail",
        headers=auth_headers(token),
    ) or {}


def get_quote_row_options(token):
    return request_json(
        "GET",
        "/desktop/quote-row-options",
        headers=auth_headers(token),
    ) or {}


def create_quote_item(token, payload):
    return request_json(
        "POST",
        "/desktop/quote-items",
        payload=payload,
        headers=auth_headers(token),
    )


def update_quote_item(token, item_id, payload):
    return request_json(
        "PUT",
        f"/desktop/quote-items/{int(item_id)}",
        payload=payload,
        headers=auth_headers(token),
    )


def delete_quote_item(token, item_id):
    return request_json(
        "DELETE",
        f"/desktop/quote-items/{int(item_id)}",
        headers=auth_headers(token),
    )


def delete_project_quote(token, teklif_kodu):
    return request_json(
        "DELETE",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}",
        headers=auth_headers(token),
    )


def update_quote(token, teklif_kodu, payload):
    return request_json(
        "PUT",
        f"/desktop/quotes/{parse.quote(str(teklif_kodu or '').strip(), safe='')}",
        payload=payload,
        headers=auth_headers(token),
    )


def update_project(token, proje_referans_no, payload):
    return request_json(
        "PUT",
        f"/desktop/projects/{parse.quote(str(proje_referans_no or '').strip(), safe='')}",
        payload=payload,
        headers=auth_headers(token),
    )
