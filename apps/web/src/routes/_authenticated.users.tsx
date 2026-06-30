import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Check,
  KeyRound,
  Loader2,
  MailCheck,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Trash2,
  UserPlus,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import { isOwner } from "../lib/roles";
import {
  adminResetPassword,
  adminSendEmailVerification,
  adminSendPasswordResetCode,
  adminVerifyEmail,
  createAdminUser,
  deleteAdminUser,
  fetchAdminRoles,
  fetchAdminUsers,
  fetchUserMobileModulePermissions,
  fetchUserModulePermissions,
  updateAdminLeaveUser,
  updateAdminUserEmail,
  updateAdminUserPassword,
  updateUserMobileModulePermissions,
  updateUserModulePermissions,
  type AdminUser,
} from "../lib/api";
import { formatNumber } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

import { Switch } from "../components/ui/switch";
import { Skeleton } from "../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";

export const Route = createFileRoute("/_authenticated/users")({
  head: () => ({ meta: [{ title: "Kullanıcı Yönetimi — Bomaksan" }] }),
  component: UsersGuard,
});

function UsersGuard() {
  const { user } = useAuth();
  if (!isOwner(user)) {
    return (
      <div className="flex h-full items-center justify-center p-16">
        <div className="flex max-w-md flex-col items-center gap-4 text-center">
          <ShieldAlert className="size-10 text-amber-400" />
          <div>
            <p className="text-sm font-medium text-foreground">
              Bu sayfaya yalnızca yönetici erişebilir
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Kullanıcı Yönetim Paneli yönetici (Owner, Master Admin, Admin)
              rolündeki hesaplara açıktır.
            </p>
          </div>
        </div>
      </div>
    );
  }
  return <UsersPage />;
}

const ROL_ALL = "__all__";

function UsersPage() {
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState(ROL_ALL);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => fetchAdminUsers(token!),
    enabled: !!token,
  });

  const rolesQuery = useQuery({
    queryKey: ["admin-roles"],
    queryFn: () => fetchAdminRoles(token!),
    enabled: !!token,
  });

  const users = usersQuery.data ?? [];
  const roles = rolesQuery.data ?? [];

  const roleNames = useMemo(
    () => Array.from(new Set(roles.map((r) => r.rol_adi))),
    [roles],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase("tr");
    return users.filter((u) => {
      if (roleFilter !== ROL_ALL && u.rol_adi !== roleFilter) return false;
      if (!q) return true;
      return (
        u.kullanici_adi.toLocaleLowerCase("tr").includes(q) ||
        u.email.toLocaleLowerCase("tr").includes(q)
      );
    });
  }, [users, search, roleFilter]);

  const selected = users.find((u) => u.id === selectedId) ?? null;

  return (
    <div className="flex h-full overflow-hidden">
      {/* LEFT: list + create */}
      <div className="flex min-w-0 flex-1 flex-col border-r border-border">
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-6 py-4">
          <div className="relative max-w-sm flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Kullanıcı adı veya e-posta ara..."
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            <Label className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              Rol
            </Label>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="h-9 w-44">
                <SelectValue placeholder="Tüm Roller" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ROL_ALL}>Tüm Roller</SelectItem>
                {roleNames.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <span className="ml-auto font-mono text-xs text-muted-foreground">
            {filtered.length} kullanıcı
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => usersQuery.refetch()}
            disabled={usersQuery.isFetching}
          >
            {usersQuery.isFetching ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Yenile
          </Button>
        </div>

        <NewUserForm roleNames={roleNames} />

        <div className="flex-1 overflow-auto">
          {usersQuery.isLoading ? (
            <div className="space-y-2 p-6">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : usersQuery.isError ? (
            <div className="p-16 text-center text-sm text-muted-foreground">
              Kullanıcı listesi yüklenemedi.{" "}
              {(usersQuery.error as Error)?.message}
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-16 text-center text-sm text-muted-foreground">
              Kullanıcı bulunamadı.
            </div>
          ) : (
            <table className="w-full min-w-[680px] text-left">
              <thead className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
                <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                  <th className="px-6 py-3 font-medium">ID</th>
                  <th className="px-3 py-3 font-medium">Kullanıcı Adı</th>
                  <th className="px-3 py-3 font-medium">E-posta</th>
                  <th className="px-3 py-3 font-medium">Rol</th>
                  <th className="px-3 py-3 text-center font-medium">E-posta</th>
                  <th className="px-3 py-3 text-center font-medium">Aktif</th>
                  <th className="px-6 py-3 text-right font-medium">Kalan İzin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-sm">
                {filtered.map((u) => (
                  <tr
                    key={u.id}
                    onClick={() => setSelectedId(u.id)}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent",
                      selectedId === u.id &&
                        "border-l-2 border-l-primary bg-accent",
                    )}
                  >
                    <td className="px-6 py-3 font-mono text-xs text-muted-foreground">
                      {u.id}
                    </td>
                    <td className="px-3 py-3 font-medium">{u.kullanici_adi}</td>
                    <td className="px-3 py-3 text-muted-foreground">{u.email}</td>
                    <td className="px-3 py-3 text-muted-foreground">
                      {u.rol_adi ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-center">
                      <BoolPill ok={!!u.email_verified} />
                    </td>
                    <td className="px-3 py-3 text-center">
                      <BoolPill ok={!!u.is_active} />
                    </td>
                    <td className="px-6 py-3 text-right font-mono">
                      {formatNumber(u.available_days ?? 0, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* RIGHT: fixed detail panel */}
      <div className="flex w-[480px] shrink-0 flex-col overflow-hidden bg-sidebar">
        {selected ? (
          <UserDetailPanel
            user={selected}
            allUsers={users}
            roleNames={roleNames}
            onDeleted={() => setSelectedId(null)}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center p-10 text-center text-sm text-muted-foreground">
            Detayları görmek için soldan bir kullanıcı seçin.
          </div>
        )}
      </div>
    </div>
  );
}

function BoolPill({ ok }: { ok: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex size-5 items-center justify-center rounded-full",
        ok ? "bg-emerald-500/15 text-emerald-600" : "bg-muted text-muted-foreground",
      )}
    >
      {ok ? <Check className="size-3" /> : <X className="size-3" />}
    </span>
  );
}

function NewUserForm({ roleNames }: { roleNames: string[] }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [kullaniciAdi, setKullaniciAdi] = useState("");
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [sifre2, setSifre2] = useState("");
  const [rol, setRol] = useState("");

  const reset = () => {
    setKullaniciAdi("");
    setEmail("");
    setSifre("");
    setSifre2("");
    setRol("");
  };

  const create = useMutation({
    mutationFn: () =>
      createAdminUser(token!, {
        kullanici_adi: kullaniciAdi.trim(),
        email: email.trim(),
        sifre,
        rol_adi: rol,
      }),
    onSuccess: () => {
      toast.success("Kullanıcı oluşturuldu.");
      reset();
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const submit = () => {
    if (!kullaniciAdi.trim()) return toast.error("Kullanıcı adı zorunludur.");
    if (!email.trim()) return toast.error("E-posta zorunludur.");
    if (sifre.length < 4) return toast.error("Şifre çok kısa.");
    if (sifre !== sifre2) return toast.error("Şifreler eşleşmiyor.");
    if (!rol) return toast.error("Rol seçin.");
    create.mutate();
  };

  return (
    <div className="border-b border-border px-6 py-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <UserPlus className="size-4" />
        Yeni Kullanıcı Oluştur
      </button>
      {open && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Kullanıcı Adı">
            <Input
              value={kullaniciAdi}
              onChange={(e) => setKullaniciAdi(e.target.value)}
              placeholder="kullanıcı adı"
            />
          </Field>
          <Field label="E-posta">
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ornek@bomaksan.com"
            />
          </Field>
          <Field label="Şifre Belirleme">
            <Input
              type="password"
              value={sifre}
              onChange={(e) => setSifre(e.target.value)}
              placeholder="••••••"
            />
          </Field>
          <Field label="Şifre Doğrulama">
            <Input
              type="password"
              value={sifre2}
              onChange={(e) => setSifre2(e.target.value)}
              placeholder="••••••"
            />
          </Field>
          <Field label="Rol Seçme">
            <Select value={rol} onValueChange={setRol}>
              <SelectTrigger>
                <SelectValue placeholder="Rol seçin" />
              </SelectTrigger>
              <SelectContent>
                {roleNames.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <div className="col-span-2 flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={submit}
              disabled={create.isPending}
            >
              {create.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <UserPlus className="size-4" />
              )}
              Kullanıcı Ekle
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function UserDetailPanel({
  user,
  allUsers,
  roleNames,
  onDeleted,
}: {
  user: AdminUser;
  allUsers: AdminUser[];
  roleNames: string[];
  onDeleted: () => void;
}) {
  const initials = user.kullanici_adi.slice(0, 2).toLocaleUpperCase("tr");

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-5">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-secondary font-mono text-sm">
          {initials}
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate font-display font-bold">
              {user.kullanici_adi}
            </span>
            <span className="font-mono text-[10px] text-muted-foreground">
              #{user.id}
            </span>
          </div>
          <div className="truncate text-xs text-muted-foreground">
            {user.email}
          </div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-wide text-primary">
            {user.rol_adi ?? "—"}
          </div>
        </div>
      </div>

      <Tabs defaultValue="profile" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="mx-4 mt-3 grid w-auto grid-cols-5 gap-1">
          <TabsTrigger value="profile" className="text-[11px]">
            Profil
          </TabsTrigger>
          <TabsTrigger value="security" className="text-[11px]">
            Güvenlik
          </TabsTrigger>
          <TabsTrigger value="modules" className="text-[11px]">
            Modül
          </TabsTrigger>
          <TabsTrigger value="mobile" className="text-[11px]">
            Mobil
          </TabsTrigger>
          <TabsTrigger value="leave" className="text-[11px]">
            İzin
          </TabsTrigger>
        </TabsList>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <TabsContent value="profile" className="mt-0">
            <ProfileTab
              key={`profile-${user.id}`}
              user={user}
              onDeleted={onDeleted}
            />
          </TabsContent>
          <TabsContent value="security" className="mt-0">
            <SecurityTab key={`sec-${user.id}`} user={user} />
          </TabsContent>
          <TabsContent value="modules" className="mt-0">
            <ModulesTab
              key={`mod-${user.id}`}
              userId={user.id}
              kind="web"
              title="Modül Yetkileri"
              description="Seçili kullanıcının web/masaüstü ana menüde görebileceği modüller."
              modules={WEB_MODULES}
              initial={user.module_permissions ?? {}}
            />
          </TabsContent>
          <TabsContent value="mobile" className="mt-0">
            <ModulesTab
              key={`mob-${user.id}`}
              userId={user.id}
              kind="mobile"
              title="Mobil Modül Görünürlükleri"
              description="Seçili kullanıcının mobil uygulama ana ekranında görebileceği modülleri belirleyin."
              modules={MOBILE_MODULES}
              initial={user.mobile_module_permissions ?? {}}
            />
          </TabsContent>

          <TabsContent value="leave" className="mt-0">
            <LeaveTab key={`leave-${user.id}`} user={user} allUsers={allUsers} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function ProfileTab({
  user,
  onDeleted,
}: {
  user: AdminUser;
  onDeleted: () => void;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(user.email);

  const saveEmail = useMutation({
    mutationFn: () => updateAdminUserEmail(token!, user.id, email.trim()),
    onSuccess: (r) => {
      toast.success(r.message || "E-posta güncellendi.");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const removeUser = useMutation({
    mutationFn: () => deleteAdminUser(token!, user.id),
    onSuccess: (r) => {
      toast.success(r.message || "Kullanıcı silindi.");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      onDeleted();
    },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-5">
      <SectionTitle>Profil Bilgileri</SectionTitle>
      <Field label="E-posta Güncelle">
        <Input value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label="Rol">
        <Input disabled value={user.rol_adi ?? ""} />
      </Field>
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            if (!email.trim()) return toast.error("E-posta boş olamaz.");
            saveEmail.mutate();
          }}
          disabled={saveEmail.isPending}
        >
          {saveEmail.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Save className="size-4" />
          )}
          E-postayı Güncelle
        </Button>
      </div>
      <div className="border-t border-border pt-5">
        <Button
          variant="destructive"
          size="sm"
          onClick={() => {
            if (
              window.confirm(
                `"${user.kullanici_adi}" kullanıcısı kalıcı olarak silinecek. Onaylıyor musunuz?`,
              )
            ) {
              removeUser.mutate();
            }
          }}
          disabled={removeUser.isPending}
        >
          {removeUser.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Trash2 className="size-4" />
          )}
          Seçili Kullanıcıyı Sil
        </Button>
      </div>
    </div>
  );
}

function SecurityTab({ user }: { user: AdminUser }) {
  const { token } = useAuth();
  const [directPassword, setDirectPassword] = useState("");
  const [directPassword2, setDirectPassword2] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verifyCode, setVerifyCode] = useState("");

  const setDirect = useMutation({
    mutationFn: () => updateAdminUserPassword(token!, user.id, directPassword),
    onSuccess: (r) => {
      toast.success(r.message || "Şifre belirlendi.");
      setDirectPassword("");
      setDirectPassword2("");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const sendResetCode = useMutation({
    mutationFn: () => adminSendPasswordResetCode(token!, user.email),
    onSuccess: (r) => toast.success(r.message || "Sıfırlama kodu gönderildi."),
    onError: (e) => toast.error((e as Error).message),
  });

  const resetPassword = useMutation({
    mutationFn: () =>
      adminResetPassword(token!, user.email, resetCode, newPassword),
    onSuccess: (r) => {
      toast.success(r.message || "Şifre güncellendi.");
      setResetCode("");
      setNewPassword("");
      setConfirmPassword("");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const sendVerification = useMutation({
    mutationFn: () => adminSendEmailVerification(token!, user.email),
    onSuccess: (r) => toast.success(r.message || "Doğrulama maili gönderildi."),
    onError: (e) => toast.error((e as Error).message),
  });

  const verifyEmail = useMutation({
    mutationFn: () => adminVerifyEmail(token!, user.email, verifyCode),
    onSuccess: (r) => {
      toast.success(r.message || "E-posta doğrulandı.");
      setVerifyCode("");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const submitReset = () => {
    if (!resetCode.trim()) return toast.error("Sıfırlama kodunu girin.");
    if (newPassword.length < 4) return toast.error("Şifre çok kısa.");
    if (newPassword !== confirmPassword)
      return toast.error("Şifreler eşleşmiyor.");
    resetPassword.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <SectionTitle>Şifre Belirle (Doğrudan)</SectionTitle>
        <Field label="Yeni Şifre">
          <Input
            type="password"
            value={directPassword}
            onChange={(e) => setDirectPassword(e.target.value)}
          />
        </Field>
        <Field label="Yeni Şifre Tekrar">
          <Input
            type="password"
            value={directPassword2}
            onChange={(e) => setDirectPassword2(e.target.value)}
          />
        </Field>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            if (directPassword.length < 4) return toast.error("Şifre çok kısa.");
            if (directPassword !== directPassword2)
              return toast.error("Şifreler eşleşmiyor.");
            setDirect.mutate();
          }}
          disabled={setDirect.isPending}
        >
          {setDirect.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <KeyRound className="size-4" />
          )}
          Şifreyi Belirle
        </Button>
      </div>

      <div className="space-y-4 border-t border-border pt-5">
        <SectionTitle>Kod ile Şifre Sıfırlama</SectionTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => sendResetCode.mutate()}
          disabled={sendResetCode.isPending}
        >
          {sendResetCode.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <KeyRound className="size-4" />
          )}
          Sıfırlama Kodu Gönder
        </Button>
        <Field label="Sıfırlama Kodu">
          <Input
            value={resetCode}
            onChange={(e) => setResetCode(e.target.value)}
            placeholder="E-posta ile gelen kod"
          />
        </Field>
        <Field label="Yeni Şifre">
          <Input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </Field>
        <Field label="Yeni Şifre Tekrar">
          <Input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </Field>
        <Button
          variant="secondary"
          size="sm"
          onClick={submitReset}
          disabled={resetPassword.isPending}
        >
          {resetPassword.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Save className="size-4" />
          )}
          Şifreyi Güncelle
        </Button>
      </div>

      <div className="space-y-4 border-t border-border pt-5">
        <SectionTitle>E-posta Doğrulama</SectionTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={() => sendVerification.mutate()}
          disabled={sendVerification.isPending}
        >
          {sendVerification.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <MailCheck className="size-4" />
          )}
          Doğrulama Maili Gönder
        </Button>
        <Field label="Doğrulama Kodu">
          <Input
            value={verifyCode}
            onChange={(e) => setVerifyCode(e.target.value)}
            placeholder="Doğrulama kodu"
          />
        </Field>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            if (!verifyCode.trim()) return toast.error("Doğrulama kodunu girin.");
            verifyEmail.mutate();
          }}
          disabled={verifyEmail.isPending}
        >
          {verifyEmail.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <MailCheck className="size-4" />
          )}
          Kodu Doğrula
        </Button>
      </div>
    </div>
  );
}

type ModuleDef = { key: string; title: string; description: string };

const WEB_MODULES: ModuleDef[] = [
  { key: "products", title: "Ürünler", description: "Ürün maliyetleri ve reçete işlemleri." },
  { key: "materials", title: "Malzemeler", description: "Malzeme kartları ve birim fiyatlar." },
  { key: "channel_management", title: "Emiş Kanalı Yönetimi", description: "Emiş kanalı tanımları ve hesapları." },
  { key: "price_list", title: "Fiyat Listesi", description: "Fiyat listesi görüntüleme ve yönetimi." },
  { key: "leave_management", title: "İzin Yönetim Modülü", description: "İzin talepleri ve bakiye işlemleri." },
  { key: "selection_wizard", title: "Seçim Sihirbazı", description: "Ürün seçim ve konfigürasyon akışları." },
  { key: "project_offers", title: "Proje Teklif Yönetimi", description: "Proje tekliflerinin hazırlanması." },
  { key: "project_management", title: "Proje Yönetim Modülü", description: "Proje takibi ve yönetimi." },
  { key: "technical_calculations", title: "Teknik Hesaplamalar", description: "Mühendislik hesap araçları." },
  { key: "documents", title: "Dokümanlar", description: "Doküman erişimi ve yönetimi." },
];

const MOBILE_MODULES: ModuleDef[] = [
  { key: "selection_wizard", title: "Seçim Sihirbazı", description: "Ürün seçim ve konfigürasyon akışları." },
  { key: "field_service", title: "Saha Servis", description: "Saha ekipleri için servis işlemleri." },
  { key: "ai_assistant", title: "AI Asistan", description: "Mobil destek/asistan özellikleri." },
  { key: "leave_management", title: "İzin Yönetimi Modülü", description: "İzin talebi ve bakiye işlemleri." },
  { key: "technical_calculations", title: "Teknik Hesaplamalar", description: "Mobil mühendislik hesap araçları." },
  { key: "price_list", title: "Fiyat Listesi", description: "Mobil fiyat listesi görüntüleme." },
  { key: "documents", title: "Dokümanlar", description: "Mobil doküman erişimi." },
];

function ModulesTab({
  userId,
  kind,
  title,
  description,
  modules,
  initial,
}: {
  userId: number;
  kind: "web" | "mobile";
  title: string;
  description: string;
  modules: ModuleDef[];
  initial: Record<string, boolean>;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [state, setState] = useState<Record<string, boolean>>(initial);
  const [dirty, setDirty] = useState(false);

  const setAll = (v: boolean) => {
    setState(Object.fromEntries(modules.map((m) => [m.key, v])));
    setDirty(true);
  };

  const load = useMutation({
    mutationFn: () =>
      kind === "web"
        ? fetchUserModulePermissions(token!, userId)
        : fetchUserMobileModulePermissions(token!, userId),
    onSuccess: (perms) => {
      setState(perms);
      setDirty(false);
      toast.success("Yetkiler API'den yüklendi.");
    },
    onError: (e) => toast.error((e as Error).message),
  });

  const save = useMutation({
    mutationFn: () => {
      const payload = Object.fromEntries(
        modules.map((m) => [m.key, !!state[m.key]]),
      );
      return kind === "web"
        ? updateUserModulePermissions(token!, userId, payload)
        : updateUserMobileModulePermissions(token!, userId, payload);
    },
    onSuccess: (r) => {
      toast.success(r.message || "Yetkiler kaydedildi.");
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-4">
      <SectionTitle>{title}</SectionTitle>
      <p className="text-xs text-muted-foreground">{description}</p>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => setAll(true)}>
          Tümünü Aç
        </Button>
        <Button variant="outline" size="sm" onClick={() => setAll(false)}>
          Tümünü Kapat
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => load.mutate()}
          disabled={load.isPending}
        >
          {load.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <RefreshCw className="size-4" />
          )}
          API'den Yükle
        </Button>
      </div>

      <div className="divide-y divide-border/50 rounded-md border border-border">
        {modules.map((m) => (
          <label
            key={m.key}
            className="flex cursor-pointer items-start justify-between gap-3 px-3 py-2.5 text-sm transition-colors hover:bg-accent"
          >
            <span className="min-w-0">
              <span className="block font-medium">{m.title}</span>
              <span className="block text-xs text-muted-foreground">
                {m.description}
              </span>
              <span className="mt-0.5 block font-mono text-[10px] text-muted-foreground/70">
                {m.key}
              </span>
            </span>
            <Switch
              className="mt-0.5"
              checked={!!state[m.key]}
              onCheckedChange={(v) => {
                setState((s) => ({ ...s, [m.key]: v }));
                setDirty(true);
              }}
            />
          </label>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Save className="size-4" />
          )}
          Yetkileri Kaydet
        </Button>
        {dirty && (
          <span className="font-mono text-[10px] uppercase tracking-wide text-amber-500">
            Kaydedilmemiş değişiklik
          </span>
        )}
      </div>
    </div>
  );
}

function LeaveTab({
  user,
  allUsers,
}: {
  user: AdminUser;
  allUsers: AdminUser[];
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [annual, setAnnual] = useState(String(user.annual_allowance_days ?? 0));
  const [managerId, setManagerId] = useState<string>(
    user.manager_user_id != null ? String(user.manager_user_id) : "none",
  );
  const [notify, setNotify] = useState(!!user.leave_notification_email);

  const save = useMutation({
    mutationFn: () =>
      updateAdminLeaveUser(token!, user.id, {
        manager_user_id: managerId === "none" ? null : Number(managerId),
        annual_allowance_days: Number(annual),
        leave_notification_email: notify,
      }),
    onSuccess: (r) => {
      toast.success(r.message || "İzin bilgileri kaydedildi.");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-5">
      <SectionTitle>İzin Yönetimi</SectionTitle>

      <div className="grid grid-cols-2 gap-3">
        <ReadStat label="Kullanılan" value={user.used_days ?? 0} />
        <ReadStat label="Kalan Bakiye" value={user.available_days ?? 0} />
        <ReadStat label="Rezerve" value={user.reserved_days ?? 0} />
        <ReadStat label="Devreden" value={user.carried_over_days ?? 0} />
      </div>

      <Field label="Yıllık Hak (gün)">
        <Input
          type="number"
          step="0.5"
          value={annual}
          onChange={(e) => setAnnual(e.target.value)}
        />
      </Field>

      <Field label="Yönetici Ataması">
        <Select value={managerId} onValueChange={setManagerId}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Yönetici Yok</SelectItem>
            {allUsers
              .filter((u) => u.id !== user.id)
              .map((u) => (
                <SelectItem key={u.id} value={String(u.id)}>
                  {u.kullanici_adi}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </Field>

      <label className="flex items-center justify-between gap-3 text-sm">
        <span>İzin Bildirim E-postası</span>
        <Switch checked={notify} onCheckedChange={setNotify} />
      </label>

      <Button
        variant="secondary"
        size="sm"
        onClick={() => save.mutate()}
        disabled={save.isPending}
      >
        {save.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Save className="size-4" />
        )}
        İzin Bilgilerini Kaydet
      </Button>
    </div>
  );
}

function ReadStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-background/40 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-sm">{formatNumber(value, 1)}</div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function Field({
  label,
  children,
}: {
  label: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}
