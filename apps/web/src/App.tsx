import { AlertCircle, Boxes, Database, FileText, Gauge, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { fetchMe, fetchModules, login, type ModuleInfo, type UserInfo } from "./api";

const phaseLabels: Record<number, string> = {
  1: "İlk faz",
  2: "İkinci faz",
  3: "Üçüncü faz",
  4: "Yönetici fazı",
};

const moduleIcons = [Boxes, Database, Gauge, FileText, ShieldCheck];

export function App() {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [token, setToken] = useState<string>(() => window.localStorage.getItem("maliyet_web_token") ?? "");
  const [user, setUser] = useState<UserInfo | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  function handleLogout() {
    window.localStorage.removeItem("maliyet_web_token");
    setToken("");
    setUser(null);
    setModules([]);
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
          <a href="#modules">Modüller</a>
          <a href="#migration">Taşıma Durumu</a>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>Maliyet Analizleri Web App</h1>
            <p>Masaüstü yazılım korunarak aynı veritabanı üzerinde web arayüzüne geçiş başlatıldı.</p>
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
            <button className="ghost-button" type="button" onClick={handleLogout}>
              Çıkış
            </button>
          </div>
        </header>

        <section className="status-grid" id="dashboard">
          <div className="status-panel">
            <span>Frontend</span>
            <strong>React + Vite</strong>
            <p>Ayrı web uygulaması olarak hazırlandı.</p>
          </div>
          <div className="status-panel">
            <span>Backend</span>
            <strong>FastAPI</strong>
            <p>Web ve ortak DB arasında güvenli katman.</p>
          </div>
          <div className="status-panel">
            <span>Masaüstü</span>
            <strong>Değişmedi</strong>
            <p>Mevcut uygulama akışı korunuyor.</p>
          </div>
        </section>

        <section className="module-section" id="modules">
          <div className="section-heading">
            <h2>Taşınacak Modüller</h2>
            <p>İlk fazda ana ticari akışı ayağa kaldıracak modüller öne alınır.</p>
          </div>

          {error ? (
            <div className="error-state">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          ) : null}

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

        <section className="migration-panel" id="migration">
          <div>
            <h2>İlk Faz Odağı</h2>
            <p>
              Login, yetki kontrolü, ana menü, ürünler, malzemeler, fiyat listesi ve maliyet hesaplama akışı web'e
              taşınacak ilk parçalardır.
            </p>
          </div>
          <ul>
            {firstPhaseModules.map((module) => (
              <li key={module.key}>{module.title}</li>
            ))}
          </ul>
        </section>
      </section>
    </main>
  );
}
