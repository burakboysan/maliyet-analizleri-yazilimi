import { AlertCircle, Boxes, Database, FileText, Gauge, LogOut, PackageSearch, Search, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  fetchMaterials,
  fetchMe,
  fetchModules,
  fetchProducts,
  fetchProductTree,
  login,
  type MaterialInfo,
  type ModuleInfo,
  type ProductInfo,
  type ProductTree,
  type UserInfo,
} from "./api";

const phaseLabels: Record<number, string> = {
  1: "İlk faz",
  2: "İkinci faz",
  3: "Üçüncü faz",
  4: "Yönetici fazı",
};

const moduleIcons = [Boxes, Database, Gauge, FileText, ShieldCheck];

function formatMoney(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(value);
}

function canSeeModule(modules: ModuleInfo[], key: string) {
  return modules.some((module) => module.key === key);
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
  const [selectedProduct, setSelectedProduct] = useState<ProductInfo | null>(null);
  const [productTree, setProductTree] = useState<ProductTree | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
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

  function handleLogout() {
    window.localStorage.removeItem("maliyet_web_token");
    setToken("");
    setUser(null);
    setModules([]);
    setMaterials([]);
    setProducts([]);
    setSelectedProduct(null);
    setProductTree(null);
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
          <a className="active" href="#dashboard">Genel Bakış</a>
          <a href="#products">Ürünler</a>
          <a href="#materials">Malzemeler</a>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>Maliyet Analizleri Web App</h1>
            <p>Ürün ve malzeme modüllerinin ilk web okuma ekranı aynı veritabanı üzerinden çalışıyor.</p>
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

        <section className="status-grid" id="dashboard">
          <div className="status-panel">
            <span>Modül Yetkisi</span>
            <strong>{modules.length} modül</strong>
            <p>Liste kullanıcının web yetkilerine göre süzülür.</p>
          </div>
          <div className="status-panel">
            <span>Ürünler</span>
            <strong>{products.length} kayıt</strong>
            <p>Ürün ağacı detayı seçili ürün üzerinden okunur.</p>
          </div>
          <div className="status-panel">
            <span>Malzemeler</span>
            <strong>{materials.length} kayıt</strong>
            <p>Malzeme fiyatı masaüstündeki aynı hesapla gösterilir.</p>
          </div>
        </section>

        {dataError ? (
          <div className="error-state inline-error">
            <AlertCircle size={20} />
            <span>{dataError}</span>
          </div>
        ) : null}

        <section className="workbench-grid">
          <section className="data-panel" id="products">
            <div className="panel-heading">
              <div>
                <h2>Ürünler</h2>
                <p>Ürün seçerek ağaç özetini kontrol edin.</p>
              </div>
              <label className="search-box">
                <Search size={18} />
                <input value={productSearch} onChange={(event) => setProductSearch(event.target.value)} placeholder="Ürün ara" />
              </label>
            </div>
            <div className="data-table product-table" role="table" aria-label="Ürün listesi">
              <div className="data-row header" role="row">
                <span>Kod</span>
                <span>Ad</span>
                <span>Kategori</span>
                <span>Maliyet</span>
              </div>
              {products.map((product) => (
                <button
                  className={selectedProduct?.id === product.id ? "data-row selected" : "data-row"}
                  key={product.id}
                  type="button"
                  onClick={() => handleProductSelect(product)}
                >
                  <span>{product.urun_kodu || "-"}</span>
                  <span>{product.urun_adi || "-"}</span>
                  <span>{product.urun_kategorisi || "-"}</span>
                  <span>{formatMoney(product.maliyet)}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="data-panel tree-panel">
            <div className="panel-heading">
              <div>
                <h2>Ürün Ağacı</h2>
                <p>{selectedProduct ? selectedProduct.urun_kodu : "Bir ürün seçin."}</p>
              </div>
              <PackageSearch size={24} />
            </div>
            {productTree ? (
              <>
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
              </>
            ) : (
              <div className="empty-state">{isLoadingData ? "Veriler yükleniyor..." : "Ürün ağacı burada gösterilecek."}</div>
            )}
          </section>

          <section className="data-panel wide-panel" id="materials">
            <div className="panel-heading">
              <div>
                <h2>Malzemeler</h2>
                <p>Masaüstüyle aynı malzeme fiyat kaynağı kullanılır.</p>
              </div>
              <label className="search-box">
                <Search size={18} />
                <input value={materialSearch} onChange={(event) => setMaterialSearch(event.target.value)} placeholder="Malzeme ara" />
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
              <p>Bu ekrandan sonra ürün ekleme, malzeme ekleme ve maliyet hesaplama aksiyonları sırayla web API'ye alınacak.</p>
            </div>
            <ul>
              {firstPhaseModules.map((module) => (
                <li key={module.key}>{module.title}</li>
              ))}
            </ul>
          </section>
        </section>
      </section>
    </main>
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
