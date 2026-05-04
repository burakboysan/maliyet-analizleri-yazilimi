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
  LogOut,
  PackagePlus,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  Wrench,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  fetchMaterials,
  fetchMe,
  fetchModules,
  fetchProductDetail,
  fetchProducts,
  fetchProductTree,
  login,
  updateProduct,
  type MaterialInfo,
  type ModuleInfo,
  type ProductDetail,
  type ProductLabor,
  type ProductInfo,
  type ProductTree,
  type UserInfo,
} from "./api";

type AppView = "dashboard" | "products" | "materials";
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

export function App() {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [token, setToken] = useState<string>(() => window.localStorage.getItem("maliyet_web_token") ?? "");
  const [user, setUser] = useState<UserInfo | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [materials, setMaterials] = useState<MaterialInfo[]>([]);
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [materialSearch, setMaterialSearch] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [productFilters, setProductFilters] = useState<Partial<Record<ProductFilterKey, string>>>({});
  const [selectedProduct, setSelectedProduct] = useState<ProductInfo | null>(null);
  const [productDetail, setProductDetail] = useState<ProductDetail | null>(null);
  const [productTree, setProductTree] = useState<ProductTree | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [detailMode, setDetailMode] = useState<"view" | "edit">("view");
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSavingDetail, setIsSavingDetail] = useState(false);
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
      setProductDetail(await fetchProductDetail(token, targetProduct.id));
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

  function handleProductAction(action: string) {
    if (action === "detail") {
      handleOpenProductDetail();
      return;
    }
    if (action === "edit") {
      handleOpenProductDetail(undefined, "edit");
      return;
    }
    if (action === "tree") {
      if (selectedProduct) {
        handleProductSelect(selectedProduct);
      } else {
        setNotice("Ürün ağacını açmak için önce tablodan bir ürün seçin.");
      }
      return;
    }
    if (action === "export") {
      exportProducts(filteredProducts);
      setNotice("Görünen ürün listesi CSV olarak hazırlandı.");
      return;
    }
    if (action === "close") {
      setView("dashboard");
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
        <section className="login-panel">
          <div className="login-copy">
            <div className="brand-mark">B</div>
            <h1>Bomaksan Maliyet Web</h1>
            <p>Masaüstü yazılımla aynı veritabanını kullanan web arayüzüne giriş yapın.</p>
          </div>
          <form className="login-form" onSubmit={handleLogin}>
            <label>
              Kullanıcı adı
              <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
            </label>
            <label>
              Şifre
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </label>
            {error ? (
              <div className="error-state">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            ) : null}
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Giriş yapılıyor..." : "Giriş Yap"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">B</div>
          <div>
            <strong>Bomaksan</strong>
            <span>Maliyet Web</span>
          </div>
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
          <div>
            <h1>{view === "products" ? "Ürünler" : view === "materials" ? "Malzemeler" : "Maliyet Analizleri Web App"}</h1>
            <p>
              {view === "products"
                ? "Masaüstü Ürünler ekranındaki tablo, filtreler ve aksiyonlar web modül ekranına taşındı."
                : "Ürün ve malzeme modülleri aynı veritabanı üzerinden çalışıyor."}
            </p>
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
            isMaster={isMasterUser(user)}
            onAction={handleProductAction}
            onClearFilters={clearProductFilters}
            onFilterChange={updateProductFilter}
            onOpenDetail={handleOpenProductDetail}
            onSearchChange={setProductSearch}
            onSelectProduct={handleProductSelect}
            productSearch={productSearch}
            productTree={productTree}
            products={filteredProducts}
            selectedProduct={selectedProduct}
            totalProductCount={products.length}
          />
        ) : view === "materials" ? (
          <MaterialsScreen materials={materials} materialSearch={materialSearch} onMaterialSearchChange={setMaterialSearch} />
        ) : (
          <DashboardScreen firstPhaseModules={firstPhaseModules} materials={materials} modules={modules} products={products} setView={setView} />
        )}
      </section>
      {isDetailOpen ? (
        <ProductDetailModal
          detail={productDetail}
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
    </main>
  );
}

function ProductModuleScreen({
  activeFilterCount,
  activeFilterEntries,
  filterOptions,
  filters,
  isLoading,
  isMaster,
  onAction,
  onClearFilters,
  onFilterChange,
  onOpenDetail,
  onSearchChange,
  onSelectProduct,
  productSearch,
  productTree,
  products,
  selectedProduct,
  totalProductCount,
}: {
  activeFilterCount: number;
  activeFilterEntries: Array<{ key: ProductFilterKey; label: string; value: string }>;
  filterOptions: Partial<Record<ProductFilterKey, string[]>>;
  filters: Partial<Record<ProductFilterKey, string>>;
  isLoading: boolean;
  isMaster: boolean;
  onAction: (action: string) => void;
  onClearFilters: () => void;
  onFilterChange: (key: ProductFilterKey, value: string) => void;
  onOpenDetail: (product?: ProductInfo) => void;
  onSearchChange: (value: string) => void;
  onSelectProduct: (product: ProductInfo) => void;
  productSearch: string;
  productTree: ProductTree | null;
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
            <ProductActionButton emphasis icon={<PackagePlus size={18} />} label="Ürün Ekle" onClick={() => onAction("add")} />
            <ProductActionButton icon={<FileText size={18} />} label="Detay" onClick={() => onAction("detail")} />
            <ProductActionButton icon={<GitBranch size={18} />} label="Ürün Ağacı" onClick={() => onAction("tree")} />
            <ProductActionButton icon={<Download size={18} />} label="Dışa Aktar" onClick={() => onAction("export")} />
          </div>
          <div className="product-toolbar secondary-toolbar">
            {isMaster ? (
              <>
                <ProductActionButton danger icon={<Trash2 size={18} />} label="Ürün Sil" onClick={() => onAction("delete")} />
                <ProductActionButton icon={<Edit size={18} />} label="Düzenle" onClick={() => onAction("edit")} />
              </>
            ) : null}
            <ProductActionButton danger icon={<RefreshCw size={18} />} label="Fiyatları Revize Et" onClick={() => onAction("revise")} />
            <ProductActionButton icon={<Copy size={18} />} label="Kopyala" onClick={() => onAction("copy")} />
            <ProductActionButton icon={<X size={18} />} label="Kapat" onClick={() => onAction("close")} />
          </div>
        </div>

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

        {productTree ? (
          <section className="product-tree-detail">
            <div className="tree-stats">
              <span>Yarı Mamül: {productTree.stats.yari_mamul_count ?? 0}</span>
              <span>Mamül: {productTree.stats.mamul_count ?? 0}</span>
              <span>Alt Ürün: {productTree.stats.alt_urun_count ?? 0}</span>
              <span>İşçilik: {formatMoney(productTree.stats.iscilik_toplam)} saat</span>
            </div>
            <div className="tree-lists">
              <TreeList title="Yarı Mamüller" items={productTree.yari_mamuller} />
              <TreeList title="Mamüller" items={productTree.mamuller} />
              <TreeList title="Alt Ürünler" items={productTree.alt_urunler} />
            </div>
          </section>
        ) : null}
      </section>
    </section>
  );
}

function ProductDetailModal({
  detail,
  mode,
  isLoading,
  isSaving,
  onClose,
  onSave,
}: {
  detail: ProductDetail | null;
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

  function updateFieldValue(key: string, value: string) {
    setFieldValues((current) => ({ ...current, [key]: value }));
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
  emphasis = false,
  icon,
  label,
  onClick,
}: {
  danger?: boolean;
  emphasis?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={danger ? "product-action danger" : emphasis ? "product-action emphasis" : "product-action"} type="button" onClick={onClick}>
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

function MaterialsScreen({
  materials,
  materialSearch,
  onMaterialSearchChange,
}: {
  materials: MaterialInfo[];
  materialSearch: string;
  onMaterialSearchChange: (value: string) => void;
}) {
  return (
    <section className="data-panel wide-panel" id="materials">
      <div className="panel-heading">
        <div>
          <h2>Malzemeler</h2>
          <p>Masaüstüyle aynı malzeme fiyat kaynağı kullanılır.</p>
        </div>
        <label className="search-box">
          <Search size={18} />
          <input value={materialSearch} onChange={(event) => onMaterialSearchChange(event.target.value)} placeholder="Malzeme ara" />
        </label>
      </div>
      <div className="data-table material-table" role="table" aria-label="Malzeme listesi">
        <div className="data-row header" role="row">
          <span>Kod</span>
          <span>Tip</span>
          <span>Ad</span>
          <span>Fiyat EUR</span>
          <span>Güncelleme</span>
        </div>
        {materials.map((material) => (
          <div className="data-row" role="row" key={material.id}>
            <span>{material.malzeme_kodu || "-"}</span>
            <span>{material.malzeme_tipi || "-"}</span>
            <span>{material.ad || "-"}</span>
            <span>{formatMoney(material.fiyat)}</span>
            <span>{material.guncelleme_tarihi || "-"}</span>
          </div>
        ))}
      </div>
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
