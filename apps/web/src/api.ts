export type ModuleInfo = {
  key: string;
  title: string;
  phase: number;
};

export type UserInfo = {
  id: number;
  kullanici_adi: string;
  rol_id?: number | null;
  rol_adi?: string | null;
  module_permissions: Record<string, boolean>;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserInfo;
};

export type MaterialInfo = {
  id: number;
  malzeme_kodu?: string | null;
  malzeme_tipi?: string | null;
  ad?: string | null;
  fiyat?: number | null;
  guncelleme_tarihi?: string | null;
};

export type ProductInfo = {
  id: number;
  urun_kodu?: string | null;
  urun_adi?: string | null;
  urun_kategorisi?: string | null;
  urun_tipi?: string | null;
  urun_modeli?: string | null;
  maliyet?: number | null;
  filtre_medyasi?: string | null;
  filtre_medyasi_kodu?: string | null;
  patlac_kumanda_tipi?: string | null;
  toplam_filtre_alani?: number | null;
  debi?: number | null;
  fan_basinc?: number | null;
  fan_basinc_birimi?: string | null;
  motor?: string | null;
  fan_kumanda_tipi?: string | null;
  patlama_kapagi?: string | null;
  filtre_elemani_sayisi?: number | null;
  maliyet_hesaplama_tarihi?: string | null;
};

export type ProductTreeItem = {
  id: number;
  kod?: string | null;
  ad?: string | null;
  miktar?: number | null;
};

export type ProductLabor = {
  iscilik_tipi?: string | null;
  usta_saat?: number | null;
  yardimci_saat?: number | null;
};

export type ProductTree = {
  product_id: number;
  stats: Record<string, number>;
  yari_mamuller: ProductTreeItem[];
  mamuller: ProductTreeItem[];
  alt_urunler: ProductTreeItem[];
  iscilikler: ProductLabor[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8100";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || "İşlem tamamlanamadı.";
  } catch {
    return "İşlem tamamlanamadı.";
  }
}

function authHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function login(kullaniciAdi: string, sifre: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      kullanici_adi: kullaniciAdi,
      sifre,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LoginResponse;
}

export async function fetchMe(token: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as UserInfo;
}

export async function fetchModules(token: string): Promise<ModuleInfo[]> {
  const response = await fetch(`${API_BASE_URL}/modules`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as { modules?: ModuleInfo[] };
  return payload.modules ?? [];
}

export async function fetchMaterials(token: string, search = ""): Promise<MaterialInfo[]> {
  const params = new URLSearchParams({ limit: "100" });
  if (search.trim()) {
    params.set("search", search.trim());
  }
  const response = await fetch(`${API_BASE_URL}/materials?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialInfo[];
}

export async function fetchProducts(token: string, search = ""): Promise<ProductInfo[]> {
  const params = new URLSearchParams({ limit: "2000" });
  if (search.trim()) {
    params.set("search", search.trim());
  }
  const response = await fetch(`${API_BASE_URL}/products?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductInfo[];
}

export async function fetchProductTree(token: string, productId: number): Promise<ProductTree> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}/tree`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTree;
}
