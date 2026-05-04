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
  toplam_filtre_alani?: number | string | null;
  debi?: number | string | null;
  fan_basinc?: number | string | null;
  fan_basinc_birimi?: string | null;
  motor?: string | null;
  fan_kumanda_tipi?: string | null;
  patlama_kapagi?: string | null;
  filtre_elemani_sayisi?: number | string | null;
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
  usta_saat?: number | string | null;
  yardimci_saat?: number | string | null;
};

export type ProductDetailField = {
  key: string;
  label: string;
  value?: string | number | null;
};

export type ProductCostBreakdown = {
  malzeme_maliyeti?: number | string | null;
  iscilik_maliyeti?: number | string | null;
  uretim_gideri?: number | string | null;
  yonetim_gideri?: number | string | null;
  alt_urun_maliyeti?: number | string | null;
  toplam_maliyet?: number | string | null;
};

export type ProductDetail = {
  product: Record<string, string | number | null>;
  display_fields: ProductDetailField[];
  cost_breakdown: ProductCostBreakdown;
  labor_rows: ProductLabor[];
  channel_fields: ProductDetailField[];
  flange_fields: ProductDetailField[];
};

export type ProductEditOptions = {
  category_options: string[];
  type_options_by_category: Record<string, string[]>;
  field_options: Record<string, string[]>;
  filter_media_code_map: Record<string, string>;
};

export type ProductUpdatePayload = {
  fields: Record<string, string | number | null>;
  labor_rows: ProductLabor[];
  recalculate_cost: boolean;
};

export type ProductUpdateResponse = {
  product_id: number;
  updated_fields: string[];
  labor_updated: boolean;
  cost_recalculated: boolean;
  recalculation_error?: string | null;
  detail: ProductDetail;
};

export type ProductDeleteResponse = {
  product_id: number;
  deleted_count: number;
  blocked_count: number;
  message: string;
};

export type ProductCopyResponse = {
  source_product_id: number;
  new_product_id: number;
  new_product_code: string;
  cost_recalculated: boolean;
  recalculation_error?: string | null;
  detail: ProductDetail;
};

export type ProductCostRevisionResponse = {
  requested_count: number;
  updated_count: number;
  failed_count: number;
  message: string;
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

export async function fetchProductDetail(token: string, productId: number): Promise<ProductDetail> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}/detail`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductDetail;
}

export async function fetchProductEditOptions(token: string): Promise<ProductEditOptions> {
  const response = await fetch(`${API_BASE_URL}/products/edit-options`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductEditOptions;
}

export async function updateProduct(token: string, productId: number, payload: ProductUpdatePayload): Promise<ProductUpdateResponse> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductUpdateResponse;
}

export async function deleteProduct(token: string, productId: number): Promise<ProductDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductDeleteResponse;
}

export async function copyProduct(token: string, productId: number, newProductCode: string): Promise<ProductCopyResponse> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}/copy`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ new_product_code: newProductCode }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductCopyResponse;
}

export async function reviseProductCosts(token: string, productIds: number[]): Promise<ProductCostRevisionResponse> {
  const response = await fetch(`${API_BASE_URL}/products/revise-costs`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_ids: productIds }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductCostRevisionResponse;
}
