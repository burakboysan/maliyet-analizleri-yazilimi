import {
  AlertCircle,
  Boxes,
  CircleDollarSign,
  ClipboardList,
  Copy,
  Database,
  Download,
  Edit,
  FileText,
  Gauge,
  GitBranch,
  Eye,
  Info,
  LockKeyhole,
  LogOut,
  Menu,
  PackagePlus,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  Upload,
  User,
  Wrench,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  addProductTreeMaterials,
  copyProduct,
  deleteProduct,
  deleteProductTreeItems,
  fetchMaterials,
  fetchMe,
  fetchModules,
  fetchProductDetail,
  fetchProductEditOptions,
  fetchProducts,
  fetchProductTree,
  login,
  recalculateProductTreeCost,
  reviseProductCosts,
  resolveProductTreeMaterialCodes,
  searchProductTreeMaterials,
  saveProductTreeLabor,
  updateProduct,
  updateProductTreeItemQuantity,
  type MaterialInfo,
  type ModuleInfo,
  type ProductDetail,
  type ProductEditOptions,
  type ProductLabor,
  type ProductInfo,
  type ProductTree,
  type ProductTreeItem,
  type ProductTreeMaterial,
  type ProductTreeMaterialAddItem,
  type ProductTreeMaterialResolveItem,
  type UserInfo,
} from "./api";
import bomaksanLogo from "./assets/logo.png";

type AppView = "dashboard" | "products" | "materials";
type MaterialFilterKey = "malzeme_kodu" | "malzeme_tipi" | "ad" | "fiyat" | "guncelleme_tarihi";
type ProductFilterKey =
  | "urun_kodu"
  | "urun_adi"
  | "urun_kategorisi"
  | "urun_tipi"
  | "urun_modeli"
  | "filtre_medyasi"
  | "filtre_medyasi_kodu"
  | "patlac_kumanda_tipi"
  | "toplam_filtre_alani"
  | "debi"
  | "fan_basinc"
  | "fan_basinc_birimi"
  | "motor"
  | "fan_kumanda_tipi"
  | "patlama_kapagi"
  | "filtre_elemani_sayisi";

const phaseLabels: Record<number, string> = {
  1: "İlk faz",
  2: "İkinci faz",
  3: "Üçüncü faz",
  4: "Yönetici fazı",
};

const productColumns: Array<{ key: ProductFilterKey | "maliyet"; label: string; filterType?: "text" | "select" }> = [
  { key: "urun_kodu", label: "Ürün Kodu", filterType: "text" },
  { key: "urun_adi", label: "Ürün Adı", filterType: "text" },
  { key: "urun_kategorisi", label: "Kategori", filterType: "select" },
  { key: "urun_tipi", label: "Ürün Tipi", filterType: "select" },
  { key: "urun_modeli", label: "Model", filterType: "text" },
  { key: "maliyet", label: "Genel Toplam Maliyet" },
  { key: "filtre_medyasi", label: "Filtre Medyası", filterType: "select" },
  { key: "filtre_medyasi_kodu", label: "Filtre Medyası Kodu", filterType: "text" },
  { key: "patlac_kumanda_tipi", label: "Patlaç Kontrol", filterType: "select" },
  { key: "toplam_filtre_alani", label: "Toplam Filtre Alanı", filterType: "text" },
  { key: "debi", label: "Debi", filterType: "text" },
  { key: "fan_basinc", label: "Basınç", filterType: "text" },
  { key: "fan_basinc_birimi", label: "Basınç Birimi", filterType: "select" },
  { key: "motor", label: "Motor", filterType: "text" },
  { key: "fan_kumanda_tipi", label: "Fan Pano Tipi", filterType: "select" },
  { key: "patlama_kapagi", label: "Patlama Kapağı", filterType: "text" },
  { key: "filtre_elemani_sayisi", label: "Filtre Sayısı", filterType: "text" },
];

const materialColumns: Array<{ key: MaterialFilterKey; label: string; filterType?: "text" | "select" }> = [
  { key: "malzeme_kodu", label: "Malzeme Kodu", filterType: "text" },
  { key: "malzeme_tipi", label: "Tipi", filterType: "select" },
  { key: "ad", label: "Adı", filterType: "text" },
  { key: "fiyat", label: "Fiyat (EUR)", filterType: "text" },
  { key: "guncelleme_tarihi", label: "Güncelleme", filterType: "text" },
];

const materialFilterGroups: Array<{
  title: string;
  description: string;
  keys: MaterialFilterKey[];
}> = [
  {
    title: "Ana filtreler",
    description: "Malzemeyi kod, tip veya ad üzerinden daraltın.",
    keys: ["malzeme_kodu", "malzeme_tipi", "ad"],
  },
  {
    title: "Fiyat ve tarih",
    description: "Birim fiyat veya güncelleme tarihine göre süzün.",
    keys: ["fiyat", "guncelleme_tarihi"],
  },
];

const productFilterGroups: Array<{
  title: string;
  description: string;
  keys: ProductFilterKey[];
}> = [
  {
    title: "Ana filtreler",
    description: "Ürünü kod, ad, kategori ve model üzerinden daraltın.",
    keys: ["urun_kodu", "urun_adi", "urun_kategorisi", "urun_tipi", "urun_modeli"],
  },
  {
    title: "Filtre ve pano",
    description: "Filtre medyası, patlaç kontrol ve fan pano bilgilerine göre süzün.",
    keys: ["filtre_medyasi", "filtre_medyasi_kodu", "patlac_kumanda_tipi", "fan_kumanda_tipi"],
  },
  {
    title: "Teknik değerler",
    description: "Debi, basınç, motor ve filtre sayısı gibi teknik alanları kullanın.",
    keys: ["toplam_filtre_alani", "debi", "fan_basinc", "fan_basinc_birimi", "motor", "patlama_kapagi", "filtre_elemani_sayisi"],
  },
];

const moduleIcons = [Boxes, Database, Gauge, FileText, ShieldCheck];
const readonlyDetailFields = new Set([
  "id",
  "urun_kodu",
  "maliyet",
  "malzeme_maliyeti",
  "iscilik_maliyeti",
  "uretim_gideri",
  "yonetim_gideri",
  "alt_urun_maliyeti",
  "kanal_agirligi",
  "flans_agirligi",
  "flans_durumu",
  "maliyet_hesaplama_tarihi",
]);
const dropdownDetailFields = new Set([
  "urun_kategorisi",
  "urun_tipi",
  "filtre_medyasi",
  "filtre_medyasi_kodu",
  "patlac_kumanda_tipi",
  "fan_basinc_birimi",
  "fan_kumanda_tipi",
]);
const laborTypes = [
  "Plazma/Lazer",
  "Makas",
  "Testere",
  "Abkant",
  "Silindir",
  "Delik Delme",
  "Kaynak",
  "Argon",
  "Montaj",
  "Boya",
  "Elektrik",
  "Ambalaj/Yükleme",
];

function formatValue(value?: string | number | null) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "number") {
    return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
  }
  return value;
}

function formatMoney(value?: number | string | null) {
  return formatValue(value);
}

function formatCurrency(value?: number | string | null, currency = "EUR") {
  return `${formatValue(value)} ${currency}`;
}

function canSeeModule(modules: ModuleInfo[], key: string) {
  return modules.some((module) => module.key === key);
}

function isMasterUser(user: UserInfo | null) {
  const role = String(user?.rol_adi ?? "").trim().toLowerCase();
  return role === "owner" || role === "master admin" || role === "admin";
}

function parseBulkMaterialRows(text: string) {
  const quantityByCode = new Map<string, number | null>();
  const codes: string[] = [];
  for (const line of text.split("\n")) {
    const normalizedLine = line.trim().replace(/\s+/g, " ");
    if (!normalizedLine) {
      continue;
    }
    const [code, quantityText] = normalizedLine.split(" ");
    if (!code || !quantityText) {
      continue;
    }
    const quantity = Number(quantityText.replace(",", "."));
    if (!codes.includes(code)) {
      codes.push(code);
    }
    if (!Number.isFinite(quantity)) {
      quantityByCode.set(code, null);
      continue;
    }
    if (quantityByCode.get(code) !== null) {
      quantityByCode.set(code, (quantityByCode.get(code) ?? 0) + quantity);
    }
  }
  return codes.map((kod) => {
    const miktar = quantityByCode.get(kod) ?? null;
    return {
      kod,
      miktar,
      validQuantity: typeof miktar === "number" && Number.isFinite(miktar) && miktar > 0,
    };
  });
}

export function App() {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [token, setToken] = useState<string>(() => window.localStorage.getItem("maliyet_web_token") ?? "");
  const [user, setUser] = useState<UserInfo | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materials, setMaterials] = useState<MaterialInfo[]>([]);
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [materialSearch, setMaterialSearch] = useState("");
  const [materialFilters, setMaterialFilters] = useState<Partial<Record<MaterialFilterKey, string>>>({});
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialInfo | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [productFilters, setProductFilters] = useState<Partial<Record<ProductFilterKey, string>>>({});
  const [selectedProduct, setSelectedProduct] = useState<ProductInfo | null>(null);
  const [productDetail, setProductDetail] = useState<ProductDetail | null>(null);
  const [productEditOptions, setProductEditOptions] = useState<ProductEditOptions | null>(null);
  const [productTree, setProductTree] = useState<ProductTree | null>(null);
  const [isTreeOpen, setIsTreeOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [detailMode, setDetailMode] = useState<"view" | "edit">("view");
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [isSavingDetail, setIsSavingDetail] = useState(false);
  const [isSavingTree, setIsSavingTree] = useState(false);
  const [isProductActionRunning, setIsProductActionRunning] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [view, setView] = useState<AppView>("dashboard");
  const [dataError, setDataError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  useEffect(() => {
    if (!token) {
      setModules([]);
      setUser(null);
      return;
    }
    Promise.all([fetchMe(token), fetchModules(token)])
      .then(([currentUser, moduleRows]) => {
        setUser(currentUser);
        setModules(moduleRows);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message);
        setToken("");
        setUser(null);
        setModules([]);
        window.localStorage.removeItem("maliyet_web_token");
      });
  }, [token]);

  useEffect(() => {
    if (!token || !user || modules.length === 0) {
      return;
    }
    const loadData = async () => {
      setIsLoadingData(true);
      setDataError(null);
      try {
        const [productRows, materialRows] = await Promise.all([
          canSeeModule(modules, "products") ? fetchProducts(token, productSearch) : Promise.resolve([]),
          canSeeModule(modules, "materials") ? fetchMaterials(token, materialSearch) : Promise.resolve([]),
        ]);
        setProducts(productRows);
        setMaterials(materialRows);
        setSelectedMaterial((current) => (current && !materialRows.some((material) => material.id === current.id) ? null : current));
        if (selectedProduct && !productRows.some((product) => product.id === selectedProduct.id)) {
          setSelectedProduct(null);
          setProductTree(null);
        }
      } catch (err) {
        setDataError(err instanceof Error ? err.message : "Veriler yüklenemedi.");
      } finally {
        setIsLoadingData(false);
      }
    };
    const timeout = window.setTimeout(loadData, 250);
    return () => window.clearTimeout(timeout);
  }, [materialSearch, modules, productSearch, selectedProduct, token, user]);

  const firstPhaseModules = useMemo(() => modules.filter((module) => module.phase === 1), [modules]);
  const activeFilterEntries = useMemo(() => {
    const entries = productColumns
      .filter((column) => column.filterType)
      .map((column) => {
        const key = column.key as ProductFilterKey;
        const value = String(productFilters[key] ?? "").trim();
        return value ? { key, label: column.label, value } : null;
      })
      .filter((entry): entry is { key: ProductFilterKey; label: string; value: string } => entry !== null);
    return productSearch.trim() ? [{ key: "urun_adi" as ProductFilterKey, label: "Genel arama", value: productSearch.trim() }, ...entries] : entries;
  }, [productFilters, productSearch]);
  const activeFilterCount = useMemo(
    () => Object.values(productFilters).filter((value) => String(value ?? "").trim()).length + (productSearch.trim() ? 1 : 0),
    [productFilters, productSearch],
  );
  const activeMaterialFilterEntries = useMemo(() => {
    const entries = materialColumns
      .filter((column) => column.filterType)
      .map((column) => {
        const value = String(materialFilters[column.key] ?? "").trim();
        return value ? { key: column.key, label: column.label, value } : null;
      })
      .filter((entry): entry is { key: MaterialFilterKey; label: string; value: string } => entry !== null);
    return materialSearch.trim()
      ? [{ key: "ad" as MaterialFilterKey, label: "Genel arama", value: materialSearch.trim() }, ...entries]
      : entries;
  }, [materialFilters, materialSearch]);
  const activeMaterialFilterCount = useMemo(
    () => Object.values(materialFilters).filter((value) => String(value ?? "").trim()).length + (materialSearch.trim() ? 1 : 0),
    [materialFilters, materialSearch],
  );
  const materialFilterOptions = useMemo(() => {
    const options: Partial<Record<MaterialFilterKey, string[]>> = {};
    for (const column of materialColumns) {
      if (column.filterType !== "select") {
        continue;
      }
      const values = new Set<string>();
      for (const material of materials) {
        const value = material[column.key];
        if (value !== null && value !== undefined && String(value).trim()) {
          values.add(String(value));
        }
      }
      options[column.key] = Array.from(values).sort((a, b) => a.localeCompare(b, "tr"));
    }
    return options;
  }, [materials]);
  const filteredMaterials = useMemo(() => {
    return materials.filter((material) => {
      return materialColumns.every((column) => {
        if (!column.filterType) {
          return true;
        }
        const filterValue = String(materialFilters[column.key] ?? "").trim().toLocaleLowerCase("tr-TR");
        if (!filterValue) {
          return true;
        }
        const rawValue = column.key === "fiyat" ? formatMoney(material.fiyat) : material[column.key];
        const cellValue = String(rawValue ?? "").toLocaleLowerCase("tr-TR");
        return cellValue.includes(filterValue);
      });
    });
  }, [materialFilters, materials]);
  const productFilterOptions = useMemo(() => {
    const options: Partial<Record<ProductFilterKey, string[]>> = {};
    for (const column of productColumns) {
      if (column.filterType !== "select") {
        continue;
      }
      const key = column.key as ProductFilterKey;
      const values = new Set<string>();
      for (const product of products) {
        const value = product[key];
        if (value !== null && value !== undefined && String(value).trim()) {
          values.add(String(value));
        }
      }
      options[key] = Array.from(values).sort((a, b) => a.localeCompare(b, "tr"));
    }
    return options;
  }, [products]);
  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      return productColumns.every((column) => {
        if (!column.filterType) {
          return true;
        }
        const filterValue = String(productFilters[column.key as ProductFilterKey] ?? "").trim().toLocaleLowerCase("tr-TR");
        if (!filterValue) {
          return true;
        }
        const cellValue = String(product[column.key as keyof ProductInfo] ?? "").toLocaleLowerCase("tr-TR");
        return cellValue.includes(filterValue);
      });
    });
  }, [productFilters, products]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await login(username, password);
      window.localStorage.setItem("maliyet_web_token", response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      if (!rememberMe) {
        setUsername("");
      }
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş yapılamadı.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleProductSelect(product: ProductInfo) {
    setSelectedProduct(product);
    setProductTree(null);
    setDataError(null);
    try {
      setProductTree(await fetchProductTree(token, product.id));
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün ağacı yüklenemedi.");
    }
  }

  async function handleOpenProductTree(product?: ProductInfo) {
    const targetProduct = product ?? selectedProduct;
    if (!targetProduct) {
      setNotice("Ürün ağacını açmak için önce tablodan bir ürün seçin.");
      return;
    }
    setSelectedProduct(targetProduct);
    setIsTreeOpen(true);
    setIsLoadingTree(true);
    setDataError(null);
    try {
      setProductTree(await fetchProductTree(token, targetProduct.id));
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün ağacı yüklenemedi.");
      setIsTreeOpen(false);
    } finally {
      setIsLoadingTree(false);
    }
  }

  async function refreshProductTree(productId = selectedProduct?.id) {
    if (!productId) {
      return null;
    }
    const nextTree = await fetchProductTree(token, productId);
    setProductTree(nextTree);
    return nextTree;
  }

  async function handleOpenProductDetail(product?: ProductInfo, mode: "view" | "edit" = "view") {
    const targetProduct = product ?? selectedProduct;
    if (!targetProduct) {
      setNotice(mode === "edit" ? "Ürünü düzenlemek için önce tablodan bir ürün seçin." : "Ürün detayını açmak için önce tablodan bir ürün seçin.");
      return;
    }

    setSelectedProduct(targetProduct);
    setDetailMode(mode);
    setIsDetailOpen(true);
    setIsLoadingDetail(true);
    setProductDetail(null);
    setDataError(null);
    try {
      const [detailResponse, optionsResponse] = await Promise.all([
        fetchProductDetail(token, targetProduct.id),
        mode === "edit" ? fetchProductEditOptions(token) : Promise.resolve(productEditOptions),
      ]);
      setProductDetail(detailResponse);
      if (optionsResponse) {
        setProductEditOptions(optionsResponse);
      }
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün detayı yüklenemedi.");
      setIsDetailOpen(false);
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function handleSaveProductDetail(fields: Record<string, string | number | null>, laborRows: ProductLabor[]) {
    if (!productDetail || !token) {
      return;
    }
    const recalculateCost = window.confirm("Ürün bilgileri kaydedildikten sonra maliyeti yeniden hesaplamak ister misiniz?");
    setIsSavingDetail(true);
    setDataError(null);
    try {
      const response = await updateProduct(token, Number(productDetail.product.id), {
        fields,
        labor_rows: laborRows,
        recalculate_cost: recalculateCost,
      });
      setProductDetail(response.detail);
      const productRows = await fetchProducts(token, productSearch);
      setProducts(productRows);
      setSelectedProduct(productRows.find((product) => product.id === response.product_id) ?? null);
      setProductTree(null);
      setIsDetailOpen(false);
      setNotice(
        response.recalculation_error
          ? `Ürün kaydedildi, ancak maliyet yeniden hesaplanamadı: ${response.recalculation_error}`
          : response.cost_recalculated
            ? "Ürün kaydedildi ve maliyet yeniden hesaplandı."
            : "Ürün kaydedildi.",
      );
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün kaydedilemedi.");
    } finally {
      setIsSavingDetail(false);
    }
  }

  async function refreshProductRows(nextSelectedProductId?: number | null) {
    const productRows = await fetchProducts(token, productSearch);
    setProducts(productRows);
    if (nextSelectedProductId) {
      setSelectedProduct(productRows.find((product) => product.id === nextSelectedProductId) ?? null);
    } else {
      setSelectedProduct(null);
    }
    setProductTree(null);
    return productRows;
  }

  async function handleDeleteProduct() {
    if (!selectedProduct) {
      setNotice("Silmek için önce tablodan bir ürün seçin.");
      return;
    }
    const confirmed = window.confirm(
      `'${selectedProduct.urun_kodu}' kodlu ürünü ve bağlı tüm verilerini (ürün ağacı, işçilik) kalıcı olarak silmek istediğinize emin misiniz?`,
    );
    if (!confirmed) {
      return;
    }
    setIsProductActionRunning(true);
    setDataError(null);
    try {
      const response = await deleteProduct(token, selectedProduct.id);
      await refreshProductRows(null);
      setNotice(response.message);
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün silinemedi.");
    } finally {
      setIsProductActionRunning(false);
    }
  }

  async function handleCopyProduct() {
    if (!selectedProduct) {
      setNotice("Kopyalamak için önce tablodan bir ürün seçin.");
      return;
    }
    const newProductCode = window.prompt(`${selectedProduct.urun_kodu} için yeni ürün kodunu girin:`, "");
    if (newProductCode === null) {
      return;
    }
    const trimmedCode = newProductCode.trim();
    if (!trimmedCode) {
      setNotice("Ürün kodu boş olamaz.");
      return;
    }
    setIsProductActionRunning(true);
    setDataError(null);
    try {
      const response = await copyProduct(token, selectedProduct.id, trimmedCode);
      await refreshProductRows(response.new_product_id);
      setNotice(
        response.recalculation_error
          ? `${selectedProduct.urun_kodu} -> ${response.new_product_code} kopyalandı, ancak maliyet hesaplanamadı: ${response.recalculation_error}`
          : `${selectedProduct.urun_kodu} -> ${response.new_product_code} kopyalandı.`,
      );
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün kopyalanamadı.");
    } finally {
      setIsProductActionRunning(false);
    }
  }

  async function handleReviseProductCosts() {
    const productIds = filteredProducts.map((product) => product.id);
    if (!productIds.length) {
      setNotice("Güncellenecek ürün bulunamadı.");
      return;
    }
    const confirmed = window.confirm(
      "Listelenen tüm ürünlerin maliyetleri güncel malzeme fiyatlarına göre yeniden hesaplanacaktır. Devam edilsin mi?",
    );
    if (!confirmed) {
      return;
    }
    setIsProductActionRunning(true);
    setDataError(null);
    try {
      const response = await reviseProductCosts(token, productIds);
      const nextSelectedId = selectedProduct?.id && productIds.includes(selectedProduct.id) ? selectedProduct.id : null;
      await refreshProductRows(nextSelectedId);
      setNotice(response.message);
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Fiyat revizyonu başlatılamadı.");
    } finally {
      setIsProductActionRunning(false);
    }
  }

  async function handleUpdateTreeQuantity(item: ProductTreeItem) {
    if (!item.id || !selectedProduct) {
      return;
    }
    const value = window.prompt("Yeni miktarı girin:", String(item.miktar ?? 0).replace(".", ","));
    if (value === null) {
      return;
    }
    const parsedValue = Number(value.replace(",", "."));
    if (!Number.isFinite(parsedValue)) {
      setNotice("Lütfen geçerli bir miktar girin.");
      return;
    }
    setIsSavingTree(true);
    setDataError(null);
    try {
      await updateProductTreeItemQuantity(token, item.id, parsedValue);
      await refreshProductTree(selectedProduct.id);
      setNotice("Miktar güncellendi.");
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Miktar güncellenemedi.");
    } finally {
      setIsSavingTree(false);
    }
  }

  async function handleDeleteTreeItems(itemIds: number[]) {
    if (!selectedProduct || !itemIds.length) {
      return;
    }
    const confirmed = window.confirm(`Seçili ${itemIds.length} kaydı ürün ağacından silmek istediğinize emin misiniz?`);
    if (!confirmed) {
      return;
    }
    setIsSavingTree(true);
    setDataError(null);
    try {
      const response = await deleteProductTreeItems(token, itemIds);
      await refreshProductTree(selectedProduct.id);
      setNotice(response.message);
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün ağacı kaydı silinemedi.");
    } finally {
      setIsSavingTree(false);
    }
  }

  async function handleSearchTreeMaterials(materialType: string, search: string) {
    return searchProductTreeMaterials(token, materialType, search);
  }

  async function handleResolveTreeMaterialCodes(codes: string[]) {
    return resolveProductTreeMaterialCodes(token, codes);
  }

  async function handleAddTreeMaterials(items: ProductTreeMaterialAddItem[]) {
    if (!selectedProduct || !items.length) {
      return;
    }
    setIsSavingTree(true);
    setDataError(null);
    try {
      const response = await addProductTreeMaterials(token, selectedProduct.id, items);
      await refreshProductTree(selectedProduct.id);
      setNotice(response.message);
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Malzeme ürün ağacına eklenemedi.");
    } finally {
      setIsSavingTree(false);
    }
  }

  async function handleSaveTreeLabor(laborRows: ProductLabor[]) {
    if (!selectedProduct) {
      return;
    }
    setIsSavingTree(true);
    setDataError(null);
    try {
      const response = await saveProductTreeLabor(token, selectedProduct.id, laborRows);
      await refreshProductTree(selectedProduct.id);
      const productRows = await fetchProducts(token, productSearch);
      setProducts(productRows);
      setSelectedProduct(productRows.find((product) => product.id === selectedProduct.id) ?? selectedProduct);
      setNotice(
        response.recalculation_error
          ? `İşçilik kaydedildi, ancak maliyet hesaplanamadı: ${response.recalculation_error}`
          : "İşçilik saatleri kaydedildi ve maliyet yeniden hesaplandı.",
      );
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "İşçilik saatleri kaydedilemedi.");
    } finally {
      setIsSavingTree(false);
    }
  }

  async function handleSaveProductTree() {
    if (!selectedProduct) {
      return;
    }
    setIsSavingTree(true);
    setDataError(null);
    try {
      const response = await recalculateProductTreeCost(token, selectedProduct.id);
      const productRows = await fetchProducts(token, productSearch);
      setProducts(productRows);
      setSelectedProduct(productRows.find((product) => product.id === selectedProduct.id) ?? selectedProduct);
      setIsTreeOpen(false);
      setNotice(
        response.recalculation_error
          ? `Ürün ağacı kaydedildi, ancak maliyet hesaplanamadı: ${response.recalculation_error}`
          : "Ürün ağacı kaydedildi ve maliyet yeniden hesaplandı.",
      );
    } catch (err) {
      setDataError(err instanceof Error ? err.message : "Ürün ağacı kaydedilemedi.");
    } finally {
      setIsSavingTree(false);
    }
  }

  function handleProductAction(action: string) {
    if (action === "detail") {
      handleOpenProductDetail();
      return;
    }
    if (action === "edit") {
      handleOpenProductDetail(undefined, "edit");
      return;
    }
    if (action === "delete") {
      handleDeleteProduct();
      return;
    }
    if (action === "copy") {
      handleCopyProduct();
      return;
    }
    if (action === "revise") {
      handleReviseProductCosts();
      return;
    }
    if (action === "tree") {
      handleOpenProductTree();
      return;
    }
    if (action === "export") {
      exportProducts(filteredProducts);
      setNotice("Görünen ürün listesi CSV olarak hazırlandı.");
      return;
    }
    setNotice("Bu masaüstü aksiyonu web API'ye taşınacağı sıradaki adım için ekranda hazır tutuluyor.");
  }

  function updateProductFilter(key: ProductFilterKey, value: string) {
    setProductFilters((current) => ({ ...current, [key]: value }));
  }

  function clearProductFilters() {
    setProductSearch("");
    setProductFilters({});
  }

  function updateMaterialFilter(key: MaterialFilterKey, value: string) {
    setMaterialFilters((current) => ({ ...current, [key]: value }));
  }

  function clearMaterialFilters() {
    setMaterialSearch("");
    setMaterialFilters({});
  }

  function handleMaterialAction(action: string) {
    if (action === "export") {
      exportMaterials(filteredMaterials);
      setNotice("Görünen malzeme listesi CSV olarak hazırlandı.");
      return;
    }
    if (!selectedMaterial && ["edit", "delete"].includes(action)) {
      setNotice("İşlem yapmak için önce tablodan bir malzeme seçin.");
      return;
    }
    const actionMessages: Record<string, string> = {
      add: "Malzeme ekleme API akışı hazırlandığında bu buton aktif edilecek.",
      edit: "Malzeme düzenleme API akışı hazırlandığında bu buton seçili malzemeyi açacak.",
      delete: "Malzeme silme API akışı hazırlandığında bu buton onayla silme yapacak.",
      import: "Mamül içe aktarma masaüstündeki import akışı web API'ye taşındığında aktif edilecek.",
    };
    setNotice(actionMessages[action] ?? "Bu malzeme aksiyonu henüz web API'ye bağlanmadı.");
  }

  function handleLogout() {
    window.localStorage.removeItem("maliyet_web_token");
    setToken("");
    setUser(null);
    setModules([]);
    setMaterials([]);
    setProducts([]);
    setSelectedProduct(null);
    setProductDetail(null);
    setProductTree(null);
    setIsDetailOpen(false);
  }

  if (!token || !user) {
    return (
      <main className="login-shell">
        <section className="login-panel" aria-label="Bomaksan Maliyet Analizleri giriş ekranı">
          <div className="login-header">
            <img className="login-logo" src={bomaksanLogo} alt="Bomaksan" />
            <h1>Maliyet Analizleri Yazılımı</h1>
            <p>Web arayüzü</p>
            <span className="login-version">Sürüm Web</span>
          </div>
          <form className="login-form" onSubmit={handleLogin}>
            <label className="login-field">
              <span>Kullanıcı Adı</span>
              <div className="login-input-wrap">
                <User size={17} aria-hidden="true" />
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </div>
            </label>
            <label className="login-field">
              <span>Şifre</span>
              <div className="login-input-wrap">
                <LockKeyhole size={17} aria-hidden="true" />
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type={isPasswordVisible ? "text" : "password"}
                  autoComplete="current-password"
                />
                <button
                  className="password-toggle"
                  type="button"
                  onClick={() => setIsPasswordVisible((current) => !current)}
                  aria-label={isPasswordVisible ? "Şifreyi gizle" : "Şifreyi göster"}
                  title={isPasswordVisible ? "Şifreyi gizle" : "Şifreyi göster"}
                >
                  <Eye size={16} />
                </button>
              </div>
            </label>
            <div className="login-options">
              <label className="remember-option">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                />
                <span>Beni Hatırla</span>
              </label>
              <div className="login-links" aria-label="Hesap işlemleri">
                <button type="button" onClick={() => setError("E-posta doğrulama akışı web arayüzüne henüz bağlanmadı.")}>
                  E-posta Doğrula
                </button>
                <button type="button" onClick={() => setError("Şifre sıfırlama akışı web arayüzüne henüz bağlanmadı.")}>
                  Şifremi Unuttum
                </button>
              </div>
            </div>
            {error ? (
              <div className="error-state">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            ) : null}
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Giriş yapılıyor..." : "Giriş Yap"}
            </button>
            <div className="login-footer">
              <span>Henüz hesabınız yok mu?</span>
              <button type="button" onClick={() => setError("Hesap oluşturma akışı web arayüzüne henüz bağlanmadı.")}>
                Hesap Oluştur
              </button>
            </div>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className={isSidebarOpen ? "app-shell sidebar-open" : "app-shell"}>
      <aside className="sidebar" id="main-navigation">
        <div className="brand">
          <div className="brand-mark">B</div>
          <div>
            <strong>Bomaksan</strong>
            <span>Maliyet Web</span>
          </div>
          <button
            className="sidebar-close"
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Menüyü kapat"
            title="Menüyü kapat"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="nav-list" aria-label="Modül navigasyonu">
          <button className={view === "dashboard" ? "active" : ""} type="button" onClick={() => setView("dashboard")}>
            Genel Bakış
          </button>
          {canSeeModule(modules, "products") ? (
            <button className={view === "products" ? "active" : ""} type="button" onClick={() => setView("products")}>
              Ürünler
            </button>
          ) : null}
          {canSeeModule(modules, "materials") ? (
            <button className={view === "materials" ? "active" : ""} type="button" onClick={() => setView("materials")}>
              Malzemeler
            </button>
          ) : null}
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className={isSidebarOpen ? "menu-toggle active" : "menu-toggle"}
              type="button"
              onClick={() => setIsSidebarOpen((current) => !current)}
              aria-controls="main-navigation"
              aria-expanded={isSidebarOpen}
              title={isSidebarOpen ? "Menüyü gizle" : "Menüyü aç"}
            >
              <Menu size={20} />
              <span>Menü</span>
            </button>
            <div>
              <h1>{view === "products" ? "Ürünler" : view === "materials" ? "Malzemeler" : "Maliyet Analizleri Web App"}</h1>
              <p>
                {view === "products"
                  ? "Masaüstü Ürünler ekranındaki tablo, filtreler ve aksiyonlar web modül ekranına taşındı."
                  : "Ürün ve malzeme modülleri aynı veritabanı üzerinden çalışıyor."}
              </p>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="user-chip">
              <strong>{user.kullanici_adi}</strong>
              <span>{user.rol_adi || "Rol yok"}</span>
            </div>
            <div className="db-badge">
              <Database size={18} />
              <span>urun_maliyet_db</span>
            </div>
            <button className="ghost-button icon-button" type="button" onClick={handleLogout} title="Çıkış">
              <LogOut size={18} />
              <span>Çıkış</span>
            </button>
          </div>
        </header>

        {dataError ? (
          <div className="error-state inline-error">
            <AlertCircle size={20} />
            <span>{dataError}</span>
          </div>
        ) : null}

        {notice ? (
          <div className="notice-state">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice(null)} title="Kapat">
              <X size={16} />
            </button>
          </div>
        ) : null}

        {view === "products" ? (
          <ProductModuleScreen
            activeFilterCount={activeFilterCount}
            activeFilterEntries={activeFilterEntries}
            filterOptions={productFilterOptions}
            filters={productFilters}
            isLoading={isLoadingData}
            isActionRunning={isProductActionRunning}
            isMaster={isMasterUser(user)}
            onAction={handleProductAction}
            onClearFilters={clearProductFilters}
            onFilterChange={updateProductFilter}
            onOpenDetail={handleOpenProductDetail}
            onSearchChange={setProductSearch}
            onSelectProduct={handleProductSelect}
            productSearch={productSearch}
            products={filteredProducts}
            selectedProduct={selectedProduct}
            totalProductCount={products.length}
          />
        ) : view === "materials" ? (
          <MaterialsScreen
            activeFilterCount={activeMaterialFilterCount}
            activeFilterEntries={activeMaterialFilterEntries}
            filterOptions={materialFilterOptions}
            filters={materialFilters}
            isLoading={isLoadingData}
            isMaster={isMasterUser(user)}
            materialSearch={materialSearch}
            materials={filteredMaterials}
            onAction={handleMaterialAction}
            onClearFilters={clearMaterialFilters}
            onFilterChange={updateMaterialFilter}
            onMaterialSearchChange={setMaterialSearch}
            onSelectMaterial={setSelectedMaterial}
            selectedMaterial={selectedMaterial}
            totalMaterialCount={materials.length}
          />
        ) : (
          <DashboardScreen firstPhaseModules={firstPhaseModules} materials={materials} modules={modules} products={products} setView={setView} />
        )}
      </section>
      {isDetailOpen ? (
        <ProductDetailModal
          detail={productDetail}
          editOptions={productEditOptions}
          mode={detailMode}
          isLoading={isLoadingDetail}
          isSaving={isSavingDetail}
          onClose={() => {
            setIsDetailOpen(false);
            setProductDetail(null);
          }}
          onSave={handleSaveProductDetail}
        />
      ) : null}
      {isTreeOpen ? (
        <ProductTreeModal
          isLoading={isLoadingTree}
          isSaving={isSavingTree}
          isMaster={isMasterUser(user)}
          onAddMaterials={handleAddTreeMaterials}
          onClose={() => setIsTreeOpen(false)}
          onDeleteItems={handleDeleteTreeItems}
          onSave={handleSaveProductTree}
          onSaveLabor={handleSaveTreeLabor}
          onResolveMaterialCodes={handleResolveTreeMaterialCodes}
          onSearchMaterials={handleSearchTreeMaterials}
          onUpdateQuantity={handleUpdateTreeQuantity}
          product={selectedProduct}
          tree={productTree}
        />
      ) : null}
    </main>
  );
}

function ProductModuleScreen({
  activeFilterCount,
  activeFilterEntries,
  filterOptions,
  filters,
  isActionRunning,
  isLoading,
  isMaster,
  onAction,
  onClearFilters,
  onFilterChange,
  onOpenDetail,
  onSearchChange,
  onSelectProduct,
  productSearch,
  products,
  selectedProduct,
  totalProductCount,
}: {
  activeFilterCount: number;
  activeFilterEntries: Array<{ key: ProductFilterKey; label: string; value: string }>;
  filterOptions: Partial<Record<ProductFilterKey, string[]>>;
  filters: Partial<Record<ProductFilterKey, string>>;
  isActionRunning: boolean;
  isLoading: boolean;
  isMaster: boolean;
  onAction: (action: string) => void;
  onClearFilters: () => void;
  onFilterChange: (key: ProductFilterKey, value: string) => void;
  onOpenDetail: (product?: ProductInfo) => void;
  onSearchChange: (value: string) => void;
  onSelectProduct: (product: ProductInfo) => void;
  productSearch: string;
  products: ProductInfo[];
  selectedProduct: ProductInfo | null;
  totalProductCount: number;
}) {
  return (
    <section className="product-module-shell">
      <aside className="product-filter-panel">
        <div className="filter-panel-header">
          <div className="filter-title">
            <SlidersHorizontal size={20} />
            <strong>Filtreleme</strong>
          </div>
          <span>{activeFilterCount ? `${activeFilterCount} aktif` : "Temiz"}</span>
        </div>

        <label className="search-box full-search">
          <Search size={18} />
          <input value={productSearch} onChange={(event) => onSearchChange(event.target.value)} placeholder="Kod, ad, kategori veya model ara" />
        </label>

        <div className="filter-summary-card">
          <strong>{products.length}</strong>
          <span>{totalProductCount === products.length ? "ürün gösteriliyor" : `${totalProductCount} ürün içinden gösteriliyor`}</span>
        </div>

        {activeFilterEntries.length ? (
          <div className="active-filter-list" aria-label="Aktif filtreler">
            {activeFilterEntries.map((entry, index) => (
              <button
                className="active-filter-chip"
                key={`${entry.key}-${index}`}
                type="button"
                onClick={() => (entry.label === "Genel arama" ? onSearchChange("") : onFilterChange(entry.key, ""))}
              >
                <span>{entry.label}</span>
                <strong>{entry.value}</strong>
                <X size={14} />
              </button>
            ))}
          </div>
        ) : null}

        <button className="filter-clear-button" type="button" onClick={onClearFilters} disabled={!activeFilterCount}>
          Filtreleri Temizle
        </button>

        <div className="filter-groups">
          {productFilterGroups.map((group, index) => (
            <FilterGroup
              defaultOpen={index === 0}
              filterOptions={filterOptions}
              filters={filters}
              group={group}
              key={group.title}
              onFilterChange={onFilterChange}
            />
          ))}
        </div>
      </aside>

      <section className="product-workspace">
        <div className="product-commandbar">
          <div className="commandbar-copy">
            <strong>Ürün Tablosu</strong>
            <span>Masaüstündeki kolon yapısı korunur, filtreler soldan yönetilir.</span>
          </div>
          <div className="product-toolbar primary-toolbar">
            <ProductActionButton disabled={isActionRunning} emphasis icon={<PackagePlus size={18} />} label="Ürün Ekle" onClick={() => onAction("add")} />
            <ProductActionButton disabled={isActionRunning} icon={<FileText size={18} />} label="Detay" onClick={() => onAction("detail")} />
            <ProductActionButton disabled={isActionRunning} icon={<GitBranch size={18} />} label="Ürün Ağacı" onClick={() => onAction("tree")} />
            <ProductActionButton disabled={isActionRunning} icon={<Download size={18} />} label="Dışa Aktar" onClick={() => onAction("export")} />
          </div>
          <div className="product-toolbar secondary-toolbar">
            {isMaster ? (
              <>
                <ProductActionButton danger disabled={isActionRunning} icon={<Trash2 size={18} />} label="Ürün Sil" onClick={() => onAction("delete")} />
                <ProductActionButton disabled={isActionRunning} icon={<Edit size={18} />} label="Düzenle" onClick={() => onAction("edit")} />
              </>
            ) : null}
            <ProductActionButton danger disabled={isActionRunning} icon={<RefreshCw size={18} />} label={isActionRunning ? "Revize Ediliyor" : "Fiyatları Revize Et"} onClick={() => onAction("revise")} />
            <ProductActionButton disabled={isActionRunning} icon={<Copy size={18} />} label={isActionRunning ? "İşleniyor" : "Kopyala"} onClick={() => onAction("copy")} />
          </div>
        </div>

        {selectedProduct ? (
          <section className="selected-product-summary">
            <div>
              <span>Seçili Ürün</span>
              <strong>{selectedProduct.urun_kodu}</strong>
              <p>{selectedProduct.urun_adi || "Ürün adı yok"}</p>
            </div>
            <dl>
              <div>
                <dt>Kategori</dt>
                <dd>{selectedProduct.urun_kategorisi || "-"}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{selectedProduct.urun_modeli || "-"}</dd>
              </div>
              <div>
                <dt>Maliyet</dt>
                <dd>{formatMoney(selectedProduct.maliyet)}</dd>
              </div>
            </dl>
          </section>
        ) : null}

        <div className="product-table-shell">
          <div className="product-table-header">
            <div>
              <strong>{products.length} ürün</strong>
              <span>{totalProductCount !== products.length ? `${totalProductCount} toplam kayıttan filtrelendi` : "Veritabanından gelen güncel liste"}</span>
            </div>
            <div className={selectedProduct ? "selected-product-pill" : "selected-product-pill muted-pill"}>
              {isLoading ? "Veriler yükleniyor..." : selectedProduct ? `${selectedProduct.urun_kodu} seçili` : "Tablodan ürün seçin"}
            </div>
          </div>
          <div className="data-table desktop-product-table" role="table" aria-label="Ürünler">
            <div className="data-row header" role="row">
              {productColumns.map((column) => (
                <span key={column.key}>{column.label}</span>
              ))}
            </div>
            {products.map((product) => (
              <button
                className={selectedProduct?.id === product.id ? "data-row selected" : "data-row"}
                key={product.id}
                type="button"
                onClick={() => onSelectProduct(product)}
                onDoubleClick={() => onOpenDetail(product)}
              >
                {productColumns.map((column) => (
                  <span key={column.key}>{column.key === "maliyet" ? formatMoney(product.maliyet) : formatValue(product[column.key as keyof ProductInfo])}</span>
                ))}
              </button>
            ))}
            {!products.length ? <div className="table-empty-state">Bu filtrelerle eşleşen ürün bulunamadı.</div> : null}
          </div>
        </div>
      </section>
    </section>
  );
}

function ProductTreeModal({
  isLoading,
  isSaving,
  isMaster,
  onAddMaterials,
  onClose,
  onDeleteItems,
  onSave,
  onSaveLabor,
  onResolveMaterialCodes,
  onSearchMaterials,
  onUpdateQuantity,
  product,
  tree,
}: {
  isLoading: boolean;
  isSaving: boolean;
  isMaster: boolean;
  onAddMaterials: (items: ProductTreeMaterialAddItem[]) => Promise<void>;
  onClose: () => void;
  onDeleteItems: (itemIds: number[]) => void;
  onSave: () => void;
  onSaveLabor: (laborRows: ProductLabor[]) => void;
  onResolveMaterialCodes: (codes: string[]) => Promise<ProductTreeMaterialResolveItem[]>;
  onSearchMaterials: (materialType: string, search: string) => Promise<ProductTreeMaterial[]>;
  onUpdateQuantity: (item: ProductTreeItem) => void;
  product: ProductInfo | null;
  tree: ProductTree | null;
}) {
  const [activeTab, setActiveTab] = useState<"yari" | "mamul" | "alt" | "labor">("yari");
  const [selectedItems, setSelectedItems] = useState<Record<string, number[]>>({});
  const [laborRows, setLaborRows] = useState<ProductLabor[]>([]);
  const [isAddPanelOpen, setIsAddPanelOpen] = useState(false);
  const [materialSearch, setMaterialSearch] = useState("");
  const [materialQuantity, setMaterialQuantity] = useState("1");
  const [materialResults, setMaterialResults] = useState<ProductTreeMaterial[]>([]);
  const [selectedMaterialCodes, setSelectedMaterialCodes] = useState<string[]>([]);
  const [isSearchingMaterials, setIsSearchingMaterials] = useState(false);
  const [addPanelError, setAddPanelError] = useState<string | null>(null);
  const [isInfoOpen, setIsInfoOpen] = useState(false);
  const [isBulkPanelOpen, setIsBulkPanelOpen] = useState(false);
  const [bulkText, setBulkText] = useState("");
  const [bulkRows, setBulkRows] = useState<Array<{ kod: string; ad: string; miktar: number | null; found: boolean; validQuantity: boolean }>>([]);
  const [isResolvingBulk, setIsResolvingBulk] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const tabItems = [
    { key: "yari" as const, label: "Yarı Mamüller", items: tree?.yari_mamuller ?? [] },
    { key: "mamul" as const, label: "Mamüller", items: tree?.mamuller ?? [] },
    { key: "alt" as const, label: "Alt Ürünler", items: tree?.alt_urunler ?? [] },
  ];
  const activeItems = tabItems.find((tab) => tab.key === activeTab)?.items ?? [];
  const activeSelection = selectedItems[activeTab] ?? [];
  const activeMaterialType = activeTab === "yari" ? "Yarı Mamül" : activeTab === "mamul" ? "Mamül" : "";
  const canAddMaterial = isMaster && Boolean(activeMaterialType);
  const canBulkAddMaterial = isMaster && activeTab === "mamul";

  useEffect(() => {
    const laborByType = new Map((tree?.iscilikler ?? []).map((row) => [row.iscilik_tipi ?? "", row]));
    setLaborRows(
      laborTypes.map((laborType) => {
        const row = laborByType.get(laborType);
        return {
          iscilik_tipi: laborType,
          usta_saat: row?.usta_saat ?? 0,
          yardimci_saat: row?.yardimci_saat ?? 0,
        };
      }),
    );
    setSelectedItems({});
  }, [tree]);

  useEffect(() => {
    setIsAddPanelOpen(false);
    setMaterialSearch("");
    setMaterialResults([]);
    setSelectedMaterialCodes([]);
    setAddPanelError(null);
    setIsBulkPanelOpen(false);
    setBulkText("");
    setBulkRows([]);
    setBulkError(null);
  }, [activeTab]);

  useEffect(() => {
    if (!isAddPanelOpen || !activeMaterialType || materialSearch.trim().length < 2) {
      setMaterialResults([]);
      setSelectedMaterialCodes([]);
      setIsSearchingMaterials(false);
      return;
    }

    let isCurrent = true;
    setIsSearchingMaterials(true);
    setAddPanelError(null);
    const timeoutId = window.setTimeout(() => {
      onSearchMaterials(activeMaterialType, materialSearch)
        .then((rows) => {
          if (!isCurrent) {
            return;
          }
          setMaterialResults(rows);
          setSelectedMaterialCodes((codes) => codes.filter((code) => rows.some((row) => row.kod === code)));
        })
        .catch((err) => {
          if (!isCurrent) {
            return;
          }
          setAddPanelError(err instanceof Error ? err.message : "Malzeme aranamadı.");
          setMaterialResults([]);
        })
        .finally(() => {
          if (isCurrent) {
            setIsSearchingMaterials(false);
          }
        });
    }, 300);

    return () => {
      isCurrent = false;
      window.clearTimeout(timeoutId);
    };
  }, [activeMaterialType, isAddPanelOpen, materialSearch, onSearchMaterials]);

  useEffect(() => {
    if (!isBulkPanelOpen || bulkText.trim().length === 0) {
      setBulkRows([]);
      setBulkError(null);
      setIsResolvingBulk(false);
      return;
    }

    const parsed = parseBulkMaterialRows(bulkText);
    if (!parsed.length) {
      setBulkRows([]);
      setBulkError("Her satırı KOD MİKTAR formatında girin.");
      setIsResolvingBulk(false);
      return;
    }

    let isCurrent = true;
    setIsResolvingBulk(true);
    setBulkError(null);
    const timeoutId = window.setTimeout(() => {
      onResolveMaterialCodes(parsed.map((row) => row.kod))
        .then((resolvedRows) => {
          if (!isCurrent) {
            return;
          }
          const resolvedMap = new Map(resolvedRows.map((row) => [row.kod, row]));
          setBulkRows(
            parsed.map((row) => {
              const resolved = resolvedMap.get(row.kod);
              return {
                kod: row.kod,
                ad: resolved?.ad ?? "",
                miktar: row.miktar,
                found: Boolean(resolved?.found),
                validQuantity: row.validQuantity,
              };
            }),
          );
        })
        .catch((err) => {
          if (!isCurrent) {
            return;
          }
          setBulkError(err instanceof Error ? err.message : "Toplu mamül kodları kontrol edilemedi.");
          setBulkRows([]);
        })
        .finally(() => {
          if (isCurrent) {
            setIsResolvingBulk(false);
          }
        });
    }, 300);

    return () => {
      isCurrent = false;
      window.clearTimeout(timeoutId);
    };
  }, [bulkText, isBulkPanelOpen, onResolveMaterialCodes]);

  function toggleItem(tabKey: string, itemId: number) {
    setSelectedItems((current) => {
      const existing = current[tabKey] ?? [];
      const next = existing.includes(itemId) ? existing.filter((id) => id !== itemId) : [...existing, itemId];
      return { ...current, [tabKey]: next };
    });
  }

  function updateLabor(index: number, key: "usta_saat" | "yardimci_saat", value: string) {
    setLaborRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value === "" ? 0 : value } : row)));
  }

  function toggleMaterial(code: string) {
    setSelectedMaterialCodes((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  async function handleAddSelectedMaterials() {
    const quantity = Number(materialQuantity.replace(",", "."));
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setAddPanelError("Lütfen geçerli bir miktar girin.");
      return;
    }
    const rows = materialResults.filter((row) => selectedMaterialCodes.includes(row.kod));
    if (!rows.length) {
      setAddPanelError("Lütfen listeden en az bir malzeme seçin.");
      return;
    }
    await onAddMaterials(rows.map((row) => ({ ...row, miktar: quantity })));
    setSelectedMaterialCodes([]);
    setMaterialSearch("");
    setMaterialResults([]);
    setMaterialQuantity("1");
    setAddPanelError(null);
  }

  async function handleAddBulkMaterials() {
    const validRows = bulkRows.filter((row) => row.found && row.validQuantity && row.miktar && row.miktar > 0);
    if (!validRows.length) {
      setBulkError("Kaydedilecek geçerli bir mamül bulunamadı.");
      return;
    }
    await onAddMaterials(validRows.map((row) => ({ kod: row.kod, ad: row.ad, miktar: Number(row.miktar), malzeme_tipi: "Mamül" })));
    setBulkText("");
    setBulkRows([]);
    setBulkError(null);
    setIsBulkPanelOpen(false);
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="product-tree-modal" role="dialog" aria-modal="true" aria-labelledby="product-tree-title">
        <header className="product-detail-header">
          <div>
            <span>Ürün Ağacı Yönetimi</span>
            <h2 id="product-tree-title">{formatValue(product?.urun_kodu)}</h2>
          </div>
          <div className="tree-modal-actions">
            {isMaster ? (
              <button className="product-action emphasis save-action" type="button" onClick={onSave} disabled={isSaving || isLoading || !tree}>
                <Save size={18} />
                <span>{isSaving ? "Kaydediliyor" : "Kaydet"}</span>
              </button>
            ) : null}
            <div className="tree-info-menu">
              <button className="modal-icon-button" type="button" onClick={() => setIsInfoOpen((value) => !value)} title="Özet bilgiler">
                <Info size={18} />
              </button>
              {isInfoOpen && tree ? (
                <div className="tree-info-popover">
                  <strong>Özet Bilgiler</strong>
                  <span>Yarı Mamül: {tree.stats.yari_mamul_count ?? 0}</span>
                  <span>Mamül: {tree.stats.mamul_count ?? 0}</span>
                  <span>Alt Ürün: {tree.stats.alt_urun_count ?? 0}</span>
                  <span>İşçilik: {formatValue(tree.stats.iscilik_toplam)} saat</span>
                  <span>Yarı Mamül: {formatValue(tree.stats.yari_mamul_kg)} kg</span>
                </div>
              ) : null}
            </div>
            <button className="modal-close-button" type="button" onClick={onClose} title="Kapat">
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="product-tree-modal-body">
          {isLoading ? (
            <div className="detail-loading">Ürün ağacı yükleniyor...</div>
          ) : tree ? (
            <>
              <div className="tree-tabs" role="tablist" aria-label="Ürün ağacı sekmeleri">
                {tabItems.map((tab) => (
                  <button className={activeTab === tab.key ? "active" : ""} type="button" key={tab.key} onClick={() => setActiveTab(tab.key)}>
                    {tab.label}
                  </button>
                ))}
                <button className={activeTab === "labor" ? "active" : ""} type="button" onClick={() => setActiveTab("labor")}>
                  İşçilik
                </button>
              </div>

              {activeTab === "labor" ? (
                <section className="tree-panel-table">
                  <div className="tree-table-row labor-tree-row header">
                    <span></span>
                    <span>İşçilik Tipi</span>
                    <span>Usta Saat</span>
                    <span>Yardımcı Saat</span>
                    <span></span>
                  </div>
                  {laborRows.map((row, index) => (
                    <div className="tree-table-row labor-tree-row" key={row.iscilik_tipi ?? "empty"}>
                      <span></span>
                      <span>{row.iscilik_tipi}</span>
                      <input
                        className="labor-input"
                        disabled={!isMaster || isSaving}
                        min="0"
                        step="0.01"
                        type="number"
                        value={row.usta_saat ?? 0}
                        onChange={(event) => updateLabor(index, "usta_saat", event.target.value)}
                      />
                      <input
                        className="labor-input"
                        disabled={!isMaster || isSaving}
                        min="0"
                        step="0.01"
                        type="number"
                        value={row.yardimci_saat ?? 0}
                        onChange={(event) => updateLabor(index, "yardimci_saat", event.target.value)}
                      />
                      <span></span>
                    </div>
                  ))}
                  {isMaster ? (
                    <div className="tree-panel-actions">
                      <button className="product-action emphasis" type="button" onClick={() => onSaveLabor(laborRows)} disabled={isSaving}>
                        İşçilik Saatlerini Kaydet
                      </button>
                    </div>
                  ) : null}
                </section>
              ) : (
                <section className="tree-panel-table">
                  {canAddMaterial && isAddPanelOpen ? (
                    <div className="tree-add-panel">
                      <label>
                        Arama
                        <input value={materialSearch} onChange={(event) => setMaterialSearch(event.target.value)} placeholder="En az 2 karakter yazın" />
                      </label>
                      <label>
                        Miktar
                        <input value={materialQuantity} onChange={(event) => setMaterialQuantity(event.target.value)} inputMode="decimal" />
                      </label>
                      <div className="tree-material-results">
                        {materialSearch.trim().length < 2 ? <div className="table-empty-state">Arama için en az 2 karakter yazın.</div> : null}
                        {isSearchingMaterials ? <div className="table-empty-state">Malzemeler aranıyor...</div> : null}
                        {!isSearchingMaterials && materialSearch.trim().length >= 2 && !materialResults.length ? <div className="table-empty-state">Sonuç bulunamadı.</div> : null}
                        {materialResults.map((row) => (
                          <label className="tree-material-result" key={row.kod}>
                            <input checked={selectedMaterialCodes.includes(row.kod)} type="checkbox" onChange={() => toggleMaterial(row.kod)} />
                            <span>{row.kod}</span>
                            <strong>{row.ad}</strong>
                            <em>{row.malzeme_tipi}</em>
                          </label>
                        ))}
                      </div>
                      {addPanelError ? <div className="inline-error">{addPanelError}</div> : null}
                    </div>
                  ) : null}
                  {canBulkAddMaterial && isBulkPanelOpen ? (
                    <div className="tree-bulk-panel">
                      <label>
                        Toplu Mamül Listesi
                        <textarea
                          value={bulkText}
                          onChange={(event) => setBulkText(event.target.value)}
                          placeholder={"Excel'den KOD MİKTAR formatında yapıştırın\nYMM-001 12,5\nYMM-002 8"}
                        />
                      </label>
                      <div className="tree-bulk-preview">
                        <div className="tree-table-row bulk-tree-row header">
                          <span>Kod</span>
                          <span>Ad</span>
                          <span>Miktar</span>
                          <span>Durum</span>
                        </div>
                        {isResolvingBulk ? <div className="table-empty-state">Mamül kodları kontrol ediliyor...</div> : null}
                        {!isResolvingBulk && !bulkRows.length ? <div className="table-empty-state">Önizleme için satır yapıştırın.</div> : null}
                        {bulkRows.map((row) => (
                          <div className={row.found && row.validQuantity ? "tree-table-row bulk-tree-row" : "tree-table-row bulk-tree-row invalid"} key={row.kod}>
                            <span>{row.kod}</span>
                            <span>{row.ad || "Kod bulunamadı veya Mamül değil"}</span>
                            <span>{row.validQuantity ? formatValue(row.miktar) : "Hatalı"}</span>
                            <span>{row.found && row.validQuantity ? "Hazır" : "Kontrol gerekli"}</span>
                          </div>
                        ))}
                      </div>
                      {bulkError ? <div className="inline-error">{bulkError}</div> : null}
                    </div>
                  ) : null}
                  <div className="tree-table-row header">
                    <span></span>
                    <span>Kod</span>
                    <span>Ad</span>
                    <span>Miktar</span>
                    <span></span>
                  </div>
                  {activeItems.map((item) => (
                    <div className="tree-table-row" key={item.id}>
                      <input
                        aria-label={`${item.kod ?? "Kayıt"} seç`}
                        checked={activeSelection.includes(item.id)}
                        disabled={!isMaster || isSaving}
                        type="checkbox"
                        onChange={() => toggleItem(activeTab, item.id)}
                      />
                      <span>{item.kod || "-"}</span>
                      <span>{item.ad || "-"}</span>
                      <span>{formatValue(item.miktar)}</span>
                      {isMaster ? (
                        <button className="product-action compact-action" type="button" onClick={() => onUpdateQuantity(item)} disabled={isSaving}>
                          Miktar
                        </button>
                      ) : (
                        <span></span>
                      )}
                    </div>
                  ))}
                  {!activeItems.length ? <div className="table-empty-state">Bu sekmede kayıt yok.</div> : null}
                  {isMaster ? (
                    <div className="tree-panel-actions">
                      {canAddMaterial ? (
                        <>
                          <button className="product-action" type="button" onClick={() => setIsAddPanelOpen((value) => !value)} disabled={isSaving}>
                            {isAddPanelOpen ? "Ekleme Alanını Kapat" : `${activeMaterialType} Ekle`}
                          </button>
                          {canBulkAddMaterial ? (
                            <button className="product-action" type="button" onClick={() => setIsBulkPanelOpen((value) => !value)} disabled={isSaving}>
                              {isBulkPanelOpen ? "Toplu Ekleme Alanını Kapat" : "Toplu Ekle"}
                            </button>
                          ) : null}
                          {isAddPanelOpen ? (
                            <button className="product-action emphasis" type="button" onClick={handleAddSelectedMaterials} disabled={isSaving || !selectedMaterialCodes.length}>
                              Seçili Malzemeleri Ekle
                            </button>
                          ) : null}
                          {isBulkPanelOpen ? (
                            <button className="product-action emphasis" type="button" onClick={handleAddBulkMaterials} disabled={isSaving || isResolvingBulk || !bulkRows.some((row) => row.found && row.validQuantity)}>
                              Toplu Listeyi Ekle
                            </button>
                          ) : null}
                        </>
                      ) : null}
                      <button className="product-action danger" type="button" onClick={() => onDeleteItems(activeSelection)} disabled={isSaving || !activeSelection.length}>
                        Seçili Öğeyi Sil
                      </button>
                    </div>
                  ) : null}
                </section>
              )}
            </>
          ) : (
            <div className="detail-loading">Ürün ağacı verisi bulunamadı.</div>
          )}
        </div>
      </section>
    </div>
  );
}

function ProductDetailModal({
  detail,
  editOptions,
  mode,
  isLoading,
  isSaving,
  onClose,
  onSave,
}: {
  detail: ProductDetail | null;
  editOptions: ProductEditOptions | null;
  mode: "view" | "edit";
  isLoading: boolean;
  isSaving: boolean;
  onClose: () => void;
  onSave: (fields: Record<string, string | number | null>, laborRows: ProductLabor[]) => void;
}) {
  const isEditMode = mode === "edit";
  const product = detail?.product ?? {};
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [laborValues, setLaborValues] = useState<ProductLabor[]>([]);
  const costRows = detail
    ? [
        { label: "Malzeme Maliyeti", value: detail.cost_breakdown.malzeme_maliyeti },
        { label: "İşçilik Maliyeti", value: detail.cost_breakdown.iscilik_maliyeti },
        { label: "Üretim Gideri", value: detail.cost_breakdown.uretim_gideri },
        { label: "Yönetim Gideri", value: detail.cost_breakdown.yonetim_gideri },
        { label: "Alt Ürün Maliyeti", value: detail.cost_breakdown.alt_urun_maliyeti },
        { label: "Genel Toplam Maliyet", value: detail.cost_breakdown.toplam_maliyet, total: true },
      ]
    : [];

  useEffect(() => {
    if (!detail) {
      setFieldValues({});
      setLaborValues([]);
      return;
    }
    setFieldValues(
      Object.fromEntries(
        detail.display_fields.map((field) => [field.key, field.value === null || field.value === undefined || field.value === "-" ? "" : String(field.value)]),
      ),
    );
    setLaborValues(detail.labor_rows.map((row) => ({ ...row, usta_saat: row.usta_saat ?? 0, yardimci_saat: row.yardimci_saat ?? 0 })));
  }, [detail]);

  function getFieldOptions(key: string) {
    const currentValue = fieldValues[key] ?? "";
    let options: string[] = [];
    if (key === "urun_kategorisi") {
      options = editOptions?.category_options ?? [];
    } else if (key === "urun_tipi") {
      options = editOptions?.type_options_by_category[fieldValues.urun_kategorisi ?? ""] ?? [];
    } else {
      options = editOptions?.field_options[key] ?? [];
    }
    return currentValue && !options.includes(currentValue) ? [currentValue, ...options] : options;
  }

  function updateFieldValue(key: string, value: string) {
    setFieldValues((current) => {
      const next = { ...current, [key]: value };
      if (key === "urun_kategorisi") {
        const typeOptions = editOptions?.type_options_by_category[value] ?? [];
        next.urun_tipi = typeOptions.includes(current.urun_tipi ?? "") ? (current.urun_tipi ?? "") : (typeOptions[0] ?? "");
      }
      if (key === "filtre_medyasi") {
        next.filtre_medyasi_kodu = editOptions?.filter_media_code_map[value] ?? "YOK - [NULL]";
      }
      return next;
    });
  }

  function updateLaborValue(index: number, key: "usta_saat" | "yardimci_saat", value: string) {
    setLaborValues((current) =>
      current.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value === "" ? 0 : value } : row)),
    );
  }

  function handleSubmit() {
    if (!detail) {
      return;
    }
    const editableFields = Object.fromEntries(
      detail.display_fields
        .filter((field) => !readonlyDetailFields.has(field.key))
        .map((field) => [field.key, fieldValues[field.key] === undefined || fieldValues[field.key] === "" ? null : fieldValues[field.key]]),
    );
    onSave(editableFields, laborValues);
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="product-detail-modal" role="dialog" aria-modal="true" aria-labelledby="product-detail-title">
        <header className="product-detail-header">
          <div>
            <span>{isEditMode ? "Ürün Düzenleme Kartı" : "Ürün Detay Kartı"}</span>
            <h2 id="product-detail-title">
              {formatValue(product.urun_kodu)} · {formatValue(product.urun_adi)}
            </h2>
            <p>
              {formatValue(product.urun_kategorisi)} / {formatValue(product.urun_tipi)} / {formatValue(product.urun_modeli)}
            </p>
          </div>
          <div className="detail-header-cost">
            <span>Toplam Maliyet</span>
            <strong>{formatCurrency(detail?.cost_breakdown.toplam_maliyet)}</strong>
          </div>
          <button className="modal-close-button" type="button" onClick={onClose} title="Kapat">
            <X size={20} />
          </button>
        </header>

        <div className="product-detail-body">
          {isLoading ? (
            <div className="detail-loading">Ürün detayları yükleniyor...</div>
          ) : detail ? (
            <>
              <section className="detail-card product-info-card">
                <div className="detail-card-heading">
                  <strong>
                    <ClipboardList size={18} />
                    Ürün Bilgileri
                  </strong>
                  <span>{isEditMode ? "Masaüstünde düzenlenebilir olan alanlar aktif" : "Masaüstü detay kartındaki alanlar"}</span>
                </div>
                <div className="detail-field-grid">
                  {detail.display_fields.map((field) => (
                    <div className="detail-field" key={field.key}>
                      <span>{field.label}</span>
                      {isEditMode && !readonlyDetailFields.has(field.key) ? (
                        field.key === "aciklama" ? (
                          <textarea
                            className="detail-textarea"
                            value={fieldValues[field.key] ?? ""}
                            onChange={(event) => updateFieldValue(field.key, event.target.value)}
                          />
                        ) : dropdownDetailFields.has(field.key) ? (
                          <select
                            className="detail-input"
                            disabled={field.key === "filtre_medyasi_kodu"}
                            value={fieldValues[field.key] ?? ""}
                            onChange={(event) => updateFieldValue(field.key, event.target.value)}
                          >
                            <option value="">Seçiniz</option>
                            {getFieldOptions(field.key).map((option) => (
                              <option value={option} key={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            className="detail-input"
                            value={fieldValues[field.key] ?? ""}
                            onChange={(event) => updateFieldValue(field.key, event.target.value)}
                          />
                        )
                      ) : (
                        <strong>{formatValue(field.value)}</strong>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              <section className="detail-card cost-card">
                <div className="detail-card-heading">
                  <strong>
                    <CircleDollarSign size={18} />
                    Maliyet Kırılımları
                  </strong>
                  <span>Son hesaplama: {formatValue(product.maliyet_hesaplama_tarihi)}</span>
                </div>
                <div className="cost-breakdown-list">
                  {costRows.map((row) => (
                    <div className={row.total ? "cost-row total" : "cost-row"} key={row.label}>
                      <span>{row.label}</span>
                      <strong>{formatCurrency(row.value)}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="detail-card labor-card">
                <div className="detail-card-heading">
                  <strong>
                    <Wrench size={18} />
                    İşçilik Bilgileri
                  </strong>
                  <span>{isEditMode ? "Usta ve yardımcı saatleri düzenlenebilir" : "Masaüstündeki işçilik türleriyle aynı sırada"}</span>
                </div>
                <div className="labor-table">
                  <div className="labor-row header">
                    <span>İşçilik Tipi</span>
                    <span>Usta Saat</span>
                    <span>Yardımcı Saat</span>
                  </div>
                  {(isEditMode ? laborValues : detail.labor_rows).map((row, index) => (
                    <div className="labor-row" key={row.iscilik_tipi ?? "empty"}>
                      <span>{row.iscilik_tipi || "-"}</span>
                      {isEditMode ? (
                        <>
                          <input
                            className="labor-input"
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.usta_saat ?? 0}
                            onChange={(event) => updateLaborValue(index, "usta_saat", event.target.value)}
                          />
                          <input
                            className="labor-input"
                            min="0"
                            step="0.01"
                            type="number"
                            value={row.yardimci_saat ?? 0}
                            onChange={(event) => updateLaborValue(index, "yardimci_saat", event.target.value)}
                          />
                        </>
                      ) : (
                        <>
                          <span>{formatValue(row.usta_saat)}</span>
                          <span>{formatValue(row.yardimci_saat)}</span>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <div className="detail-loading">Detay verisi bulunamadı.</div>
          )}
        </div>

        <footer className="product-detail-footer">
          {isEditMode ? (
            <button className="product-action emphasis" type="button" onClick={handleSubmit} disabled={isSaving || isLoading || !detail}>
              {isSaving ? "Kaydediliyor..." : "Değişiklikleri Kaydet"}
            </button>
          ) : null}
          <button className="product-action" type="button" onClick={onClose}>
            Geri Dön
          </button>
        </footer>
      </section>
    </div>
  );
}

function ProductActionButton({
  danger = false,
  disabled = false,
  emphasis = false,
  icon,
  label,
  onClick,
}: {
  danger?: boolean;
  disabled?: boolean;
  emphasis?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={danger ? "product-action danger" : emphasis ? "product-action emphasis" : "product-action"} type="button" onClick={onClick} disabled={disabled}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

function FilterGroup({
  defaultOpen,
  filterOptions,
  filters,
  group,
  onFilterChange,
}: {
  defaultOpen: boolean;
  filterOptions: Partial<Record<ProductFilterKey, string[]>>;
  filters: Partial<Record<ProductFilterKey, string>>;
  group: (typeof productFilterGroups)[number];
  onFilterChange: (key: ProductFilterKey, value: string) => void;
}) {
  return (
    <details className="filter-group" open={defaultOpen}>
      <summary>
        <span>
          <strong>{group.title}</strong>
          <small>{group.description}</small>
        </span>
      </summary>
      <div className="filter-grid">
        {group.keys.map((key) => {
          const column = productColumns.find((item) => item.key === key);
          if (!column) {
            return null;
          }
          return (
            <label className="filter-control" key={key}>
              <span>{column.label}</span>
              {column.filterType === "select" ? (
                <select value={filters[key] ?? ""} onChange={(event) => onFilterChange(key, event.target.value)}>
                  <option value="">Tümü</option>
                  {(filterOptions[key] ?? []).map((value) => (
                    <option value={value} key={value}>
                      {value}
                    </option>
                  ))}
                </select>
              ) : (
                <input value={filters[key] ?? ""} onChange={(event) => onFilterChange(key, event.target.value)} placeholder={`${column.label} ara`} />
              )}
            </label>
          );
        })}
      </div>
    </details>
  );
}

function MaterialFilterGroup({
  defaultOpen,
  filterOptions,
  filters,
  group,
  onFilterChange,
}: {
  defaultOpen: boolean;
  filterOptions: Partial<Record<MaterialFilterKey, string[]>>;
  filters: Partial<Record<MaterialFilterKey, string>>;
  group: (typeof materialFilterGroups)[number];
  onFilterChange: (key: MaterialFilterKey, value: string) => void;
}) {
  return (
    <details className="filter-group" open={defaultOpen}>
      <summary>
        <span>
          <strong>{group.title}</strong>
          <small>{group.description}</small>
        </span>
      </summary>
      <div className="filter-grid">
        {group.keys.map((key) => {
          const column = materialColumns.find((item) => item.key === key);
          if (!column) {
            return null;
          }
          return (
            <label className="filter-control" key={key}>
              <span>{column.label}</span>
              {column.filterType === "select" ? (
                <select value={filters[key] ?? ""} onChange={(event) => onFilterChange(key, event.target.value)}>
                  <option value="">Tümü</option>
                  {(filterOptions[key] ?? []).map((value) => (
                    <option value={value} key={value}>
                      {value}
                    </option>
                  ))}
                </select>
              ) : (
                <input value={filters[key] ?? ""} onChange={(event) => onFilterChange(key, event.target.value)} placeholder={`${column.label} ara`} />
              )}
            </label>
          );
        })}
      </div>
    </details>
  );
}

function MaterialsScreen({
  activeFilterCount,
  activeFilterEntries,
  filterOptions,
  filters,
  isLoading,
  isMaster,
  materials,
  materialSearch,
  onAction,
  onClearFilters,
  onFilterChange,
  onMaterialSearchChange,
  onSelectMaterial,
  selectedMaterial,
  totalMaterialCount,
}: {
  activeFilterCount: number;
  activeFilterEntries: Array<{ key: MaterialFilterKey; label: string; value: string }>;
  filterOptions: Partial<Record<MaterialFilterKey, string[]>>;
  filters: Partial<Record<MaterialFilterKey, string>>;
  isLoading: boolean;
  isMaster: boolean;
  materials: MaterialInfo[];
  materialSearch: string;
  onAction: (action: string) => void;
  onClearFilters: () => void;
  onFilterChange: (key: MaterialFilterKey, value: string) => void;
  onMaterialSearchChange: (value: string) => void;
  onSelectMaterial: (material: MaterialInfo) => void;
  selectedMaterial: MaterialInfo | null;
  totalMaterialCount: number;
}) {
  const typeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const material of materials) {
      const type = String(material.malzeme_tipi || "Tipsiz");
      counts.set(type, (counts.get(type) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);
  }, [materials]);

  return (
    <section className="product-module-shell material-module-shell" id="materials">
      <aside className="product-filter-panel material-filter-panel">
        <div className="filter-panel-header">
          <div className="filter-title">
            <SlidersHorizontal size={20} />
            <strong>Filtreleme</strong>
          </div>
          <span>{activeFilterCount ? `${activeFilterCount} aktif` : "Temiz"}</span>
        </div>

        <label className="search-box full-search">
          <Search size={18} />
          <input value={materialSearch} onChange={(event) => onMaterialSearchChange(event.target.value)} placeholder="Kod, tip veya ad ara" />
        </label>

        <div className="filter-summary-card">
          <strong>{materials.length}</strong>
          <span>{totalMaterialCount === materials.length ? "malzeme gösteriliyor" : `${totalMaterialCount} malzeme içinden gösteriliyor`}</span>
        </div>

        {activeFilterEntries.length ? (
          <div className="active-filter-list" aria-label="Aktif filtreler">
            {activeFilterEntries.map((entry, index) => (
              <button
                className="active-filter-chip"
                key={`${entry.key}-${index}`}
                type="button"
                onClick={() => (entry.label === "Genel arama" ? onMaterialSearchChange("") : onFilterChange(entry.key, ""))}
              >
                <span>{entry.label}</span>
                <strong>{entry.value}</strong>
                <X size={14} />
              </button>
            ))}
          </div>
        ) : null}

        <button className="filter-clear-button" type="button" onClick={onClearFilters} disabled={!activeFilterCount}>
          Filtreleri Temizle
        </button>

        <div className="filter-groups">
          {materialFilterGroups.map((group, index) => (
            <MaterialFilterGroup
              defaultOpen={index === 0}
              filterOptions={filterOptions}
              filters={filters}
              group={group}
              key={group.title}
              onFilterChange={onFilterChange}
            />
          ))}
        </div>
      </aside>

      <section className="product-workspace material-workspace">
        <div className="product-commandbar material-commandbar">
          <div className="commandbar-copy">
            <strong>Malzeme Tablosu</strong>
            <span>Masaüstündeki kolonlar korunur; arama, filtre ve seçim işlemleri web ekranına taşındı.</span>
          </div>
          <div className="product-toolbar primary-toolbar">
            <ProductActionButton emphasis icon={<PackagePlus size={18} />} label="Malzeme Ekle" onClick={() => onAction("add")} />
            <ProductActionButton icon={<Download size={18} />} label="Dışa Aktar" onClick={() => onAction("export")} />
            <ProductActionButton icon={<Upload size={18} />} label="Mamül İçe Aktar" onClick={() => onAction("import")} />
          </div>
          <div className="product-toolbar secondary-toolbar">
            <ProductActionButton disabled={!selectedMaterial} icon={<Edit size={18} />} label="Malzeme Düzenle" onClick={() => onAction("edit")} />
            {isMaster ? (
              <ProductActionButton danger disabled={!selectedMaterial} icon={<Trash2 size={18} />} label="Malzeme Çıkart" onClick={() => onAction("delete")} />
            ) : null}
          </div>
        </div>

        {selectedMaterial ? (
          <section className="selected-product-summary selected-material-summary">
            <div>
              <span>Seçili Malzeme</span>
              <strong>{selectedMaterial.malzeme_kodu || "-"}</strong>
              <p>{selectedMaterial.ad || "Malzeme adı yok"}</p>
            </div>
            <dl>
              <div>
                <dt>Tipi</dt>
                <dd>{selectedMaterial.malzeme_tipi || "-"}</dd>
              </div>
              <div>
                <dt>Fiyat</dt>
                <dd>{formatCurrency(selectedMaterial.fiyat)}</dd>
              </div>
              <div>
                <dt>Güncelleme</dt>
                <dd>{selectedMaterial.guncelleme_tarihi || "-"}</dd>
              </div>
            </dl>
          </section>
        ) : null}

        <div className="material-type-strip" aria-label="Malzeme tipi dağılımı">
          {typeCounts.length ? (
            typeCounts.map(([type, count]) => (
              <div key={type}>
                <span>{type}</span>
                <strong>{count}</strong>
              </div>
            ))
          ) : (
            <span className="muted">Malzeme tipi özeti için kayıt bekleniyor.</span>
          )}
        </div>

        <div className="product-table-shell material-table-shell">
          <div className="product-table-header">
            <div>
              <strong>{materials.length} malzeme</strong>
              <span>{totalMaterialCount !== materials.length ? `${totalMaterialCount} toplam kayıttan filtrelendi` : "Veritabanından gelen güncel liste"}</span>
            </div>
            <div className={selectedMaterial ? "selected-product-pill" : "selected-product-pill muted-pill"}>
              {isLoading ? "Veriler yükleniyor..." : selectedMaterial ? `${selectedMaterial.malzeme_kodu || selectedMaterial.ad} seçili` : "Tablodan malzeme seçin"}
            </div>
          </div>
          <div className="data-table desktop-material-table" role="table" aria-label="Malzeme listesi">
            <div className="data-row header" role="row">
              {materialColumns.map((column) => (
                <span key={column.key}>{column.label}</span>
              ))}
            </div>
            {materials.map((material) => (
              <button
                className={selectedMaterial?.id === material.id ? "data-row selected" : "data-row"}
                role="row"
                key={material.id}
                type="button"
                onClick={() => onSelectMaterial(material)}
                onDoubleClick={() => onAction("edit")}
              >
                <span>{material.malzeme_kodu || "-"}</span>
                <span>{material.malzeme_tipi || "-"}</span>
                <span>{material.ad || "-"}</span>
                <span>{formatMoney(material.fiyat)}</span>
                <span>{material.guncelleme_tarihi || "-"}</span>
              </button>
            ))}
            {!materials.length ? <div className="table-empty-state">Bu filtrelerle eşleşen malzeme bulunamadı.</div> : null}
          </div>
        </div>
      </section>
    </section>
  );
}

function DashboardScreen({
  firstPhaseModules,
  materials,
  modules,
  products,
  setView,
}: {
  firstPhaseModules: ModuleInfo[];
  materials: MaterialInfo[];
  modules: ModuleInfo[];
  products: ProductInfo[];
  setView: (view: AppView) => void;
}) {
  return (
    <section className="workbench-grid">
      <section className="status-grid wide-panel" id="dashboard">
        <button className="status-panel status-button" type="button" onClick={() => setView("products")}>
          <span>Ürünler</span>
          <strong>{products.length} kayıt</strong>
          <p>Ürün modülü ekranını açar.</p>
        </button>
        <button className="status-panel status-button" type="button" onClick={() => setView("materials")}>
          <span>Malzemeler</span>
          <strong>{materials.length} kayıt</strong>
          <p>Malzeme modülü ekranını açar.</p>
        </button>
        <div className="status-panel">
          <span>Modül Yetkisi</span>
          <strong>{modules.length} modül</strong>
          <p>Liste kullanıcının web yetkilerine göre süzülür.</p>
        </div>
      </section>

      <section className="module-section wide-panel" id="modules">
        <div className="section-heading">
          <div>
            <h2>Taşınacak Modüller</h2>
            <p>İlk fazdaki ana akışlar ürün, malzeme, fiyat listesi ve maliyet hesaplama üzerine kuruluyor.</p>
          </div>
        </div>
        <div className="module-table" role="table" aria-label="Web app modül taşıma listesi">
          <div className="module-row header" role="row">
            <span>Modül</span>
            <span>Faz</span>
            <span>Durum</span>
          </div>
          {modules.map((module, index) => {
            const Icon = moduleIcons[index % moduleIcons.length];
            return (
              <div className="module-row" role="row" key={module.key}>
                <span className="module-title">
                  <Icon size={18} />
                  {module.title}
                </span>
                <span>{phaseLabels[module.phase] ?? `${module.phase}. faz`}</span>
                <span className={module.phase === 1 ? "tag active-tag" : "tag"}>{module.phase === 1 ? "Öncelikli" : "Planlandı"}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="migration-panel wide-panel" id="migration">
        <div>
          <h2>İlk Faz Odağı</h2>
          <p>Ürün modülü masaüstü davranışına yaklaştırıldı; sırada buton aksiyonlarının gerçek web API karşılıkları var.</p>
        </div>
        <ul>
          {firstPhaseModules.map((module) => (
            <li key={module.key}>{module.title}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function TreeList({ title, items }: { title: string; items: ProductTree["yari_mamuller"] }) {
  return (
    <div className="tree-list">
      <strong>{title}</strong>
      {items.length === 0 ? (
        <span className="muted">Kayıt yok</span>
      ) : (
        items.slice(0, 6).map((item) => (
          <span key={item.id}>
            {item.kod || "-"} · {item.ad || "-"} · {formatMoney(item.miktar)}
          </span>
        ))
      )}
    </div>
  );
}

function exportProducts(products: ProductInfo[]) {
  const header = productColumns.map((column) => column.label);
  const rows = products.map((product) =>
    productColumns.map((column) => {
      const value = column.key === "maliyet" ? product.maliyet : product[column.key as keyof ProductInfo];
      return `"${String(value ?? "").replace(/"/g, '""')}"`;
    }),
  );
  const csv = [header, ...rows].map((row) => row.join(";")).join("\n");
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "urunler.csv";
  link.click();
  URL.revokeObjectURL(url);
}


function exportMaterials(materials: MaterialInfo[]) {
  const header = materialColumns.map((column) => column.label);
  const rows = materials.map((material) =>
    materialColumns.map((column) => {
      const value = column.key === "fiyat" ? material.fiyat : material[column.key];
      return `"${String(value ?? "").replace(/"/g, '""')}"`;
    }),
  );
  const csv = [header, ...rows].map((row) => row.join(";")).join("\n");
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "malzemeler.csv";
  link.click();
  URL.revokeObjectURL(url);
}
