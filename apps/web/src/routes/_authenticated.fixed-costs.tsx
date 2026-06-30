import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Coins,
  Download,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import { isOwner } from "../lib/roles";
import {
  createFixedCost,
  deleteFixedCost,
  fetchFixedCosts,
  updateFixedCost,
  type FixedCostItem,
  type FixedCostPayload,
} from "../lib/api";
import { formatDate } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Skeleton } from "../components/ui/skeleton";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

export const Route = createFileRoute("/_authenticated/fixed-costs")({
  head: () => ({ meta: [{ title: "Sabit Maliyet Yönetimi - Bomaksan" }] }),
  component: FixedCostsGuard,
});

const TUMU = "__all__";

const COLUMNS = [
  "ID",
  "Kalem Adı",
  "Kategori",
  "Birim",
  "Birim Fiyat",
  "Para Birimi",
  "Aktif",
  "Güncelleme Tarihi",
  "Açıklama",
];

const EMPTY_DRAFT: FixedCostPayload = {
  kalem_adi: "",
  kategori: "",
  birim: "",
  birim_fiyat: "",
  para_birimi: "EUR",
  aktif: true,
  aciklama: "",
};

const fcId = (item: FixedCostItem) => item.id;
const fcName = (item: FixedCostItem) => (item.kalem_adi ?? "") as string;
const fcCategory = (item: FixedCostItem) => (item.kategori ?? "") as string;
const fcUnit = (item: FixedCostItem) => (item.birim ?? "") as string;
const fcPrice = (item: FixedCostItem) => item.birim_fiyat ?? null;
const fcCurrency = (item: FixedCostItem) =>
  (item.para_birimi ?? "EUR") as string;
const fcActive = (item: FixedCostItem) =>
  item.aktif === true || item.aktif === 1;
const fcDesc = (item: FixedCostItem) => (item.aciklama ?? "") as string;
const fcUpdated = (item: FixedCostItem) =>
  (item.guncelleme_tarihi ?? item.updated_at ?? "") as string;

function formatMoney(
  value: number | string | null | undefined,
  currency: string | null | undefined,
): string {
  if (value === null || value === undefined || value === "") return "-";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: currency || "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

function exportFixedCostsCsv(items: FixedCostItem[]) {
  const header =
    "id;kalem_adi;kategori;birim;birim_fiyat;para_birimi;aktif;guncelleme_tarihi;aciklama";
  const rows = items.map((item) =>
    [
      fcId(item) ?? "",
      fcName(item),
      fcCategory(item),
      fcUnit(item),
      fcPrice(item) ?? "",
      fcCurrency(item),
      fcActive(item) ? "Aktif" : "Pasif",
      fcUpdated(item),
      fcDesc(item).replace(/;/g, ","),
    ].join(";"),
  );
  const blob = new Blob(["\uFEFF" + [header, ...rows].join("\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sabit_maliyetler_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function FixedCostsGuard() {
  const { user } = useAuth();
  const allowed = isOwner(user);

  if (!allowed) {
    return (
      <div className="flex h-full items-center justify-center p-16">
        <div className="flex max-w-md flex-col items-center gap-4 text-center">
          <ShieldAlert className="size-10 text-amber-400" />
          <div>
            <p className="text-sm font-medium text-foreground">
              Bu ekran için yetkiniz yok.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Sabit Maliyet Yönetimi yalnızca yönetici (Owner, Master Admin,
              Admin) rolündeki hesaplara açıktır.
            </p>
          </div>
        </div>
      </div>
    );
  }
  return <FixedCostsPage />;
}

function FixedCostsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState(TUMU);
  const [currency, setCurrency] = useState(TUMU);
  const [active, setActive] = useState(TUMU);
  const [selectedId, setSelectedId] = useState<number | string | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [draft, setDraft] = useState<FixedCostPayload>(EMPTY_DRAFT);

  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timeout);
  }, [search]);

  const queryCategory = category === TUMU ? "" : category;
  const queryCurrency = currency === TUMU ? "" : currency;
  const queryActive = active === TUMU ? "" : active;

  const query = useQuery({
    queryKey: [
      "fixed-costs",
      debounced,
      queryCategory,
      queryCurrency,
      queryActive,
    ],
    queryFn: () =>
      fetchFixedCosts(token!, {
        search: debounced,
        category: queryCategory,
        currency: queryCurrency,
        active: queryActive,
      }),
    enabled: !!token,
    retry: false,
  });

  const items = query.data ?? [];

  const categoryOptions = useMemo(
    () =>
      Array.from(new Set(items.map(fcCategory).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b, "tr"),
      ),
    [items],
  );
  const currencyOptions = useMemo(
    () =>
      Array.from(new Set(items.map(fcCurrency).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b, "tr"),
      ),
    [items],
  );

  const selected = useMemo(
    () => items.find((item) => fcId(item) === selectedId) ?? null,
    [items, selectedId],
  );

  useEffect(() => {
    if (selectedId != null && !items.some((item) => fcId(item) === selectedId)) {
      setSelectedId(null);
      setIsNew(false);
    }
  }, [items, selectedId]);

  const openNew = () => {
    setIsNew(true);
    setSelectedId(null);
    setDraft(EMPTY_DRAFT);
  };

  const openItem = (item: FixedCostItem) => {
    setIsNew(false);
    setSelectedId(fcId(item) ?? null);
    setDraft({
      kalem_adi: fcName(item),
      kategori: fcCategory(item),
      birim: fcUnit(item),
      birim_fiyat: fcPrice(item) ?? "",
      para_birimi: fcCurrency(item),
      aktif: fcActive(item),
      aciklama: fcDesc(item),
    });
  };

  const closePanel = () => {
    setIsNew(false);
    setSelectedId(null);
    setDraft(EMPTY_DRAFT);
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: FixedCostPayload = {
        ...draft,
        birim_fiyat:
          typeof draft.birim_fiyat === "string"
            ? draft.birim_fiyat.replace(",", ".")
            : draft.birim_fiyat,
      };
      if (isNew || selectedId == null) {
        return createFixedCost(token!, payload);
      }
      return updateFixedCost(token!, selectedId, payload);
    },
    onSuccess: () => {
      toast.success(isNew ? "Kalem oluşturuldu." : "Kalem güncellendi.");
      queryClient.invalidateQueries({ queryKey: ["fixed-costs"] });
      closePanel();
    },
    onError: (error) => toast.error((error as Error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number | string) => deleteFixedCost(token!, id),
    onSuccess: (response) => {
      toast.success(response.message || "Kalem silindi.");
      queryClient.invalidateQueries({ queryKey: ["fixed-costs"] });
      closePanel();
    },
    onError: (error) => toast.error((error as Error).message),
  });

  const handleSave = () => {
    if (!draft.kalem_adi.trim()) {
      toast.error("Kalem adı zorunludur.");
      return;
    }
    saveMutation.mutate();
  };

  const handleDelete = () => {
    if (selectedId == null) return;
    if (
      !window.confirm("Bu sabit maliyet kalemi silinecek. Onaylıyor musunuz?")
    ) {
      return;
    }
    deleteMutation.mutate(selectedId);
  };

  const panelOpen = isNew || selected != null;

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col border-r border-border">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-8 py-5">
          <div>
            <h2 className="font-display text-lg font-bold tracking-tight">
              Sabit Maliyet Yönetimi
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Sabit maliyet kalemlerini görüntüleyin, fiyatlarını güncelleyin ve
              ürün/malzeme hesaplarında kullanılan temel maliyetleri yönetin.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              {query.isFetching ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              Yenile
            </Button>
            <Button variant="secondary" size="sm" onClick={openNew}>
              <Plus className="size-4" />
              Yeni Kalem Ekle
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportFixedCostsCsv(items)}
              disabled={items.length === 0}
            >
              <Download className="size-4" />
              Dışa Aktar
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-3 border-b border-border px-8 py-4">
          <div className="flex min-w-[220px] flex-1 flex-col gap-1">
            <Label className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              Ara
            </Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Kalem adı, kategori veya açıklama ara..."
                className="h-9 pl-9"
              />
            </div>
          </div>
          <FilterSelect
            label="Kategori"
            value={category}
            onChange={setCategory}
            allLabel="Tüm Kategoriler"
            options={categoryOptions}
          />
          <FilterSelect
            label="Para Birimi"
            value={currency}
            onChange={setCurrency}
            allLabel="Tüm Para Birimleri"
            options={currencyOptions}
          />
          <div className="flex flex-col gap-1">
            <Label className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              Durum
            </Label>
            <Select value={active} onValueChange={setActive}>
              <SelectTrigger className="h-9 w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TUMU}>Tümü</SelectItem>
                <SelectItem value="active">Aktif</SelectItem>
                <SelectItem value="passive">Pasif</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <span className="pb-2 font-mono text-xs text-muted-foreground">
            {items.length} kayıt
          </span>
        </div>

        <div className="flex-1 overflow-auto">
          {query.isLoading ? (
            <div className="space-y-2 p-8">
              {Array.from({ length: 10 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : query.isError ? (
            <div className="flex flex-col items-center justify-center gap-3 p-16 text-center text-muted-foreground">
              <Coins className="size-10 opacity-40" />
              <p className="text-sm font-medium text-foreground">
                Sabit maliyet listesi yüklenemedi.
              </p>
              <p className="max-w-xl text-xs">
                {(query.error as Error)?.message || "Backend yanıtı alınamadı."}
              </p>
              <Button variant="outline" size="sm" onClick={() => query.refetch()}>
                <RefreshCw className="size-4" />
                Tekrar Dene
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 p-16 text-center text-muted-foreground">
              <Coins className="size-10 opacity-40" />
              <p className="text-sm">Sabit maliyet kalemi bulunamadı.</p>
            </div>
          ) : (
            <table className="w-full min-w-[920px] text-left">
              <thead className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
                <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                  {COLUMNS.map((column) => (
                    <th
                      key={column}
                      className={cn(
                        "px-4 py-3 font-medium first:pl-8 last:pr-8",
                        column === "Birim Fiyat" && "text-right",
                      )}
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-sm">
                {items.map((item, index) => {
                  const id = fcId(item);
                  const isSelected = id != null && id === selectedId;
                  return (
                    <tr
                      key={id ?? index}
                      onClick={() => openItem(item)}
                      className={cn(
                        "cursor-pointer transition-colors hover:bg-accent",
                        isSelected && "border-l-2 border-l-primary bg-accent",
                      )}
                    >
                      <td className="px-4 py-3 pl-8 font-mono text-xs text-muted-foreground">
                        {id ?? "-"}
                      </td>
                      <td className="px-4 py-3 font-medium">
                        {fcName(item) || "-"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {fcCategory(item) || "-"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {fcUnit(item) || "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {formatMoney(fcPrice(item), fcCurrency(item))}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs uppercase text-muted-foreground">
                        {fcCurrency(item)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10px] uppercase",
                            fcActive(item)
                              ? "bg-emerald-500/15 text-emerald-600"
                              : "bg-muted text-muted-foreground",
                          )}
                        >
                          {fcActive(item) ? "Aktif" : "Pasif"}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {formatDate(fcUpdated(item))}
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 pr-8 text-muted-foreground">
                        {fcDesc(item) || "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="flex w-[440px] shrink-0 flex-col overflow-hidden bg-sidebar">
        {panelOpen ? (
          <FixedCostDetailForm
            isNew={isNew}
            draft={draft}
            setDraft={setDraft}
            onSave={handleSave}
            onCancel={closePanel}
            onDelete={handleDelete}
            saving={saveMutation.isPending}
            deleting={deleteMutation.isPending}
            canDelete={!isNew && selectedId != null}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center p-10 text-center text-sm text-muted-foreground">
            Düzenlemek için bir kalem seçin veya "Yeni Kalem Ekle" ile
            başlayın.
          </div>
        )}
      </div>
    </div>
  );
}

function FixedCostDetailForm({
  isNew,
  draft,
  setDraft,
  onSave,
  onCancel,
  onDelete,
  saving,
  deleting,
  canDelete,
}: {
  isNew: boolean;
  draft: FixedCostPayload;
  setDraft: React.Dispatch<React.SetStateAction<FixedCostPayload>>;
  onSave: () => void;
  onCancel: () => void;
  onDelete: () => void;
  saving: boolean;
  deleting: boolean;
  canDelete: boolean;
}) {
  const set = <K extends keyof FixedCostPayload>(
    key: K,
    value: FixedCostPayload[K],
  ) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border px-6 py-5">
        <div>
          <h3 className="font-display font-bold tracking-tight">
            {isNew ? "Yeni Kalem" : "Kalem Detayı"}
          </h3>
          <p className="text-xs text-muted-foreground">
            {isNew
              ? "Yeni bir sabit maliyet kalemi oluşturun."
              : "Seçili kalemi görüntüleyin veya düzenleyin."}
          </p>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        <Field label="Kalem Adı *">
          <Input
            value={draft.kalem_adi}
            onChange={(event) => set("kalem_adi", event.target.value)}
            placeholder="Örn. Elektrik tüketimi"
          />
        </Field>
        <Field label="Kategori">
          <Input
            value={draft.kategori ?? ""}
            onChange={(event) => set("kategori", event.target.value)}
            placeholder="Örn. Genel Gider"
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Birim">
            <Input
              value={draft.birim ?? ""}
              onChange={(event) => set("birim", event.target.value)}
              placeholder="adet / saat / kg"
            />
          </Field>
          <Field label="Birim Fiyat">
            <Input
              inputMode="decimal"
              value={String(draft.birim_fiyat ?? "")}
              onChange={(event) => set("birim_fiyat", event.target.value)}
              placeholder="0,00"
            />
          </Field>
        </div>
        <Field label="Para Birimi">
          <Select
            value={draft.para_birimi ?? "EUR"}
            onValueChange={(value) => set("para_birimi", value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Para birimi seçin" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EUR">EUR (€)</SelectItem>
              <SelectItem value="USD">USD ($)</SelectItem>
              <SelectItem value="TRY">TRY (₺)</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="Açıklama">
          <Textarea
            value={draft.aciklama ?? ""}
            onChange={(event) => set("aciklama", event.target.value)}
            rows={3}
            placeholder="Kısa açıklama"
          />
        </Field>
        <label className="flex items-center justify-between gap-3 text-sm">
          <span>Aktif</span>
          <Switch
            checked={!!draft.aktif}
            onCheckedChange={(value) => set("aktif", value)}
          />
        </label>
      </div>

      <div className="space-y-3 border-t border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onSave}
            disabled={saving}
          >
            {saving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Save className="size-4" />
            )}
            Kaydet
          </Button>
          <Button variant="outline" size="sm" onClick={onCancel}>
            <X className="size-4" />
            İptal
          </Button>
        </div>
        {canDelete && (
          <div className="border-t border-border pt-3">
            <Button
              variant="destructive"
              size="sm"
              onClick={onDelete}
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Sil
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  allLabel,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  allLabel: string;
  options: string[];
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-9 w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TUMU}>{allLabel}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function Field({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}
