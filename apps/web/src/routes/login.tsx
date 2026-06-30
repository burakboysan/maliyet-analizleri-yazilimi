import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ArrowLeft, Loader2 } from "lucide-react";

import { useAuth } from "../lib/auth";
import {
  resetPasswordWithCode,
  sendEmailVerification,
  sendPasswordResetCode,
  signup,
  verifyEmailCode,
} from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import logo from "../assets/logo.png";

const loginHero = "/assets/lovable/login-hero.webp";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [{ title: "Giriş — Bomaksan Maliyet Analizleri" }],
  }),
  component: LoginPage,
});

type Mode = "login" | "signup" | "forgot" | "reset" | "verify";

function LoginPage() {
  const { token, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [busy, setBusy] = useState(false);

  // shared fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (!loading && token) navigate({ to: "/dashboard", replace: true });
  }, [loading, token, navigate]);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await signIn(username.trim(), password);
      toast.success("Giriş başarılı");
      navigate({ to: "/dashboard", replace: true });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Giriş başarısız");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignup(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await signup(username.trim(), email.trim(), password);
      toast.success("Kayıt oluşturuldu. E-posta adresinizi doğrulayın.");
      setIdentifier(email.trim());
      setMode("verify");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Kayıt başarısız");
    } finally {
      setBusy(false);
    }
  }

  async function handleSendVerify() {
    setBusy(true);
    try {
      await sendEmailVerification(identifier.trim() || email.trim());
      toast.success("Doğrulama kodu gönderildi");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Kod gönderilemedi");
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await verifyEmailCode(identifier.trim() || email.trim(), code.trim());
      toast.success("E-posta doğrulandı. Giriş yapabilirsiniz.");
      setMode("login");
      setCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Doğrulama başarısız");
    } finally {
      setBusy(false);
    }
  }

  async function handleForgot(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await sendPasswordResetCode(identifier.trim());
      toast.success("Sıfırlama kodu gönderildi");
      setMode("reset");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Kod gönderilemedi");
    } finally {
      setBusy(false);
    }
  }

  async function handleReset(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await resetPasswordWithCode(identifier.trim(), code.trim(), newPassword);
      toast.success("Parola güncellendi. Giriş yapabilirsiniz.");
      setMode("login");
      setCode("");
      setNewPassword("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sıfırlama başarısız");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-dark relative grid min-h-screen overflow-hidden bg-background text-foreground lg:grid-cols-[1fr_1.05fr]">
      <img
        src={loginHero}
        alt="Bomaksan endüstriyel filtrasyon sistemleri"
        className="pointer-events-none absolute inset-0 size-full object-cover"
      />
      {/* layered background overlays span the whole screen */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_120%_at_85%_0%,rgba(26,6,8,0.78)_0%,rgba(10,10,11,0.9)_60%)]" />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)",
          backgroundSize: "38px 38px",
          maskImage:
            "radial-gradient(120% 100% at 80% 10%, black 0%, transparent 70%)",
        }}
      />
      <div className="pointer-events-none absolute -right-32 top-1/3 size-96 rounded-full bg-primary/20 blur-[120px]" />

      {/* Brand panel */}
      <div className="relative order-2 hidden flex-col justify-between overflow-hidden p-14 lg:flex">



        <div className="relative space-y-6">
          <p className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-primary">
            <span className="size-1.5 rounded-full bg-primary" />
            Maliyet Analizleri
          </p>
          <h1 className="font-display text-[2.75rem] font-bold leading-[1.05] tracking-tight">
            Endüstriyel filtrasyon için
            <br />
            <span className="bg-gradient-to-r from-primary to-rose-300 bg-clip-text text-transparent">
              hassas maliyet yönetimi.
            </span>
          </h1>
          <p className="max-w-md text-[15px] leading-relaxed text-muted-foreground">
            Ürün reçeteleri, malzeme maliyetleri, seçim sihirbazı ve teknik
            hesaplamalar — tek bir mühendislik platformunda.
          </p>
          <div className="flex gap-8 pt-2">
            {[
              ["Reçete", "Ürün maliyeti"],
              ["Sihirbaz", "Akıllı seçim"],
              ["Teknik", "Hesaplama"],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="font-display text-lg font-bold text-foreground">
                  {k}
                </div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {v}
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          © {new Date().getFullYear()} Bomaksan
        </p>
      </div>

      {/* Form panel */}
      <div className="relative order-1 flex items-center justify-center p-6">

        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(100%_60%_at_50%_0%,rgba(239,68,68,0.07)_0%,transparent_60%)]" />
        <div className="relative w-full max-w-sm">
          <img
            src={logo}
            alt="Bomaksan"
            className="mb-5 h-9 w-auto"
          />
          <div className="rounded-2xl border border-white/10 bg-card/40 p-8 shadow-[0_24px_70px_-20px_rgba(0,0,0,0.85)] backdrop-blur-xl">





          {mode === "login" && (
            <form onSubmit={handleLogin} className="space-y-5">
              <Header title="Oturum Aç" subtitle="Hesabınıza giriş yapın." />
              <Field label="Kullanıcı Adı">
                <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
              </Field>
              <Field label="Parola">
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              </Field>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="size-4 animate-spin" />} Giriş Yap
              </Button>
              <div className="flex items-center justify-between text-xs">
                <button type="button" className="text-muted-foreground hover:text-foreground" onClick={() => setMode("forgot")}>
                  Parolamı unuttum
                </button>
                <button type="button" className="text-primary hover:underline" onClick={() => setMode("signup")}>
                  Yeni hesap oluştur
                </button>
              </div>
            </form>
          )}

          {mode === "signup" && (
            <form onSubmit={handleSignup} className="space-y-5">
              <Header title="Hesap Oluştur" subtitle="Yeni bir kullanıcı kaydı açın." />
              <Field label="Kullanıcı Adı">
                <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
              </Field>
              <Field label="E-posta">
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
              <Field label="Parola">
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="size-4 animate-spin" />} Kayıt Ol
              </Button>
              <BackLink onClick={() => setMode("login")} />
            </form>
          )}

          {mode === "verify" && (
            <form onSubmit={handleVerify} className="space-y-5">
              <Header title="E-posta Doğrulama" subtitle="E-postanıza gelen kodu girin." />
              <Field label="E-posta">
                <Input type="email" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
              </Field>
              <Field label="Doğrulama Kodu">
                <Input value={code} onChange={(e) => setCode(e.target.value)} required />
              </Field>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="size-4 animate-spin" />} Doğrula
              </Button>
              <button type="button" className="w-full text-center text-xs text-muted-foreground hover:text-foreground" onClick={handleSendVerify} disabled={busy}>
                Kodu tekrar gönder
              </button>
              <BackLink onClick={() => setMode("login")} />
            </form>
          )}

          {mode === "forgot" && (
            <form onSubmit={handleForgot} className="space-y-5">
              <Header title="Parola Sıfırla" subtitle="Kullanıcı adı veya e-postanızı girin." />
              <Field label="Kullanıcı Adı / E-posta">
                <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
              </Field>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="size-4 animate-spin" />} Kod Gönder
              </Button>
              <BackLink onClick={() => setMode("login")} />
            </form>
          )}

          {mode === "reset" && (
            <form onSubmit={handleReset} className="space-y-5">
              <Header title="Yeni Parola" subtitle="Kod ve yeni parolanızı girin." />
              <Field label="Kullanıcı Adı / E-posta">
                <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
              </Field>
              <Field label="Sıfırlama Kodu">
                <Input value={code} onChange={(e) => setCode(e.target.value)} required />
              </Field>
              <Field label="Yeni Parola">
                <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
              </Field>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy && <Loader2 className="size-4 animate-spin" />} Parolayı Güncelle
              </Button>
              <BackLink onClick={() => setMode("login")} />
            </form>
          )}
          </div>
        </div>
      </div>

    </div>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="space-y-1">
      <h2 className="font-display text-2xl font-bold tracking-tight">{title}</h2>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}

function BackLink({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="size-3.5" /> Girişe dön
    </button>
  );
}
