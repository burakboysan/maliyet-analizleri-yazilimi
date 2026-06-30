// Frontend yetki modeli — backend ile tek kaynak.
//
// Canlı FastAPI backend'inde (mobile_compat._is_owner) yönetici sayılan roller:
//   owner, master admin, admin
// Karşılaştırma backend'de normalize edilerek (trim + lowercase) yapıldığı için
// burada da aynı normalizasyonu uyguluyoruz. Bu kapılar yalnızca UI gizleme
// amaçlıdır; gerçek koruma backend guard'larındadır (require_module_access,
// require_owner, _is_owner).

export type RoleHolder = { rol_adi?: string | null } | null | undefined;

// Backend _is_owner ile birebir aynı küme.
const OWNER_ROLES = new Set(["owner", "master admin", "admin"]);

export function normalizeRole(role?: string | null): string {
  return (role ?? "").trim().toLowerCase();
}

/**
 * Backend `_is_owner` ile uyumlu yönetici kontrolü.
 * owner / master admin / admin rolleri yönetici sayılır.
 */
export function isOwner(user: RoleHolder): boolean {
  return OWNER_ROLES.has(normalizeRole(user?.rol_adi));
}
