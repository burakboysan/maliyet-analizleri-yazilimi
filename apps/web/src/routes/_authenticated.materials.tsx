import { createFileRoute } from "@tanstack/react-router";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Download, FileUp, Loader2, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import { useDebouncedValue } from "../hooks/use-debounced-value";
import {
  deleteMaterial,
  fetchCostVersion,
  fetchMaterialDetail,
  fetchMaterials,
  updateMaterial,
  type MaterialInfo,
} from "../lib/api";
import { formatCurrency, formatDate } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Skeleton } from "../components/ui/skeleton";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "../components/ui/context-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { MaterialAddDialog } from "../components/material-add-dialog";
import { MaterialImportDialog } from "../components/material-import-dialog";
import { TableErrorState, TableLoadingState } from "../components/table-state";

export const Route = createFileRoute("/_authenticated/materials")({
  head: () => ({ meta: [{ title: "Malzemeler — Bomaksan" }] }),
  component: MaterialsPage,
});

function exportMaterialsCsv(materials: MaterialInfo[]) {
  const header = "malzeme_kodu;malzeme_tipi;ad;fiyat;guncelleme_tarihi";
  const rows = materials.map((m) =>
    [
      m.malzeme_kodu ?? "",
      m.malzeme_tipi ?? "",
      (m.ad ?? "").replace(/;/g, ","),
      m.fiyat ?? "",
      m.guncelleme_tarihi ?? "",
    ].join(";"),
  );
  const content = [header, ...rows].join("\n");
  const blob = new Blob(["\uFEFF" + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `malzemeler_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function MaterialsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<MaterialInfo | null>(null);
  const [editRequest, setEditRequest] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<MaterialInfo | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // Cheap shared version stamp. The backend now folds material and fixed-cost
  // (EUR/kg semi-finished) update timestamps into this value, so we use it as
  // part of the materials query key: the list refetches automatically when any
  // of those change, but stays instant (cached) when nothing changed. A short
  // staleTime keeps tab switches instant (no network wait on every mount)
  // while still revalidating periodically; mutations invalidate it explicitly.
  const costVersionQuery = useQuery({
    queryKey: ["materials-cost-version"],
    queryFn: () => fetchCostVersion(token!),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
  const costVersion = costVersionQuery.isError
    ? "no-version"
    : costVersionQuery.data;

  // Fetch all materials ONCE per version (cached + persisted); filter in memory
  // so search is instant and never re-hits the API. keepPreviousData keeps the
  // current rows visible if the version stamp changes, avoiding a loading flash.
  const materialsQuery = useQuery({
    queryKey: ["materials", costVersion ?? "pending"],
    queryFn: () => fetchMaterials(token!),
    enabled: !!token && costVersion !== undefined,
    placeholderData: keepPreviousData,
  });

  const allMaterials = materialsQuery.data ?? [];
  // Debounce + memoize so typing doesn't re-scan/re-render the whole list.
  const debouncedSearch = useDebouncedValue(search, 200);
  const materials = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    if (!q) return allMaterials;
    return allMaterials.filter((m) =>
      [m.malzeme_kodu, m.malzeme_tipi, m.ad].some((f) =>
        (f ?? "").toLowerCase().includes(q),
      ),
    );
  }, [allMaterials, debouncedSearch]);

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteMaterial(token!, id),
    onSuccess: (res, id) => {
      toast.success(res.message ?? "Malzeme silindi.");
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      queryClient.invalidateQueries({ queryKey: ["materials-cost-version"] });
      setDeleteTarget(null);
      if (selected?.id === id) setSelected(null);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Silme başarısız.");
      setDeleteTarget(null);
    },
  });


  const openMaterial = (m: MaterialInfo, edit = false) => {
    setSelected(m);
    setEditRequest(edit);
  };

  // Virtualize the rows so 800+ materials mount only the visible window.
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: materials.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 57,
    overscan: 12,
  });
  const virtualRows = rowVirtualizer.getVirtualItems();
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0;
  const paddingBottom =
    virtualRows.length > 0
      ? rowVirtualizer.getTotalSize() - virtualRows[virtualRows.length - 1].end
      : 0;


  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-4 sm:px-8">
          <div className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Malzeme kodu, tip veya ad ara..."
              className="pl-9"
            />
          </div>
          <span className="font-mono text-xs text-muted-foreground">
            {materials.length} kayıt
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportMaterialsCsv(materials)}
              disabled={materials.length === 0}
            >
              <Download className="size-4" />
              Dışa Aktar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
              <FileUp className="size-4" />
              Mamül İçe Aktar
            </Button>
            <Button size="sm" onClick={() => setAddOpen(true)}>
              <Plus className="size-4" />
              Malzeme Ekle
            </Button>
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {materialsQuery.isError ? (
            <TableErrorState
              error={materialsQuery.error}
              retrying={materialsQuery.isFetching}
              onRetry={() => {
                costVersionQuery.refetch();
                materialsQuery.refetch();
              }}
            />
          ) : materialsQuery.isLoading || costVersion === undefined ? (
            <TableLoadingState message="Malzemeler yükleniyor…" rows={10} />
          ) : materials.length === 0 ? (
            <div className="p-16 text-center text-sm text-muted-foreground">
              Malzeme bulunamadı.
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
                <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                  <th className="px-8 py-4 font-medium">Malzeme Kodu</th>
                  <th className="px-4 py-4 font-medium">Tip</th>
                  <th className="px-4 py-4 font-medium">Ad</th>
                  <th className="px-4 py-4 font-medium">Güncelleme</th>
                  <th className="px-8 py-4 text-right font-medium">Fiyat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-sm">
                {paddingTop > 0 && (
                  <tr aria-hidden>
                    <td colSpan={5} style={{ height: paddingTop }} />
                  </tr>
                )}
                {virtualRows.map((vr) => {
                  const m = materials[vr.index];
                  return (
                  <ContextMenu key={m.id}>
                    <ContextMenuTrigger asChild>
                      <tr
                        onClick={() => openMaterial(m)}
                        className={cn(
                          "cursor-pointer transition-colors hover:bg-accent",
                          selected?.id === m.id &&
                            "border-l-2 border-l-primary bg-accent",
                        )}
                      >
                        <td className="px-8 py-4 font-mono text-sm">
                          {m.malzeme_kodu ?? "—"}
                        </td>
                        <td className="px-4 py-4 text-muted-foreground">
                          {m.malzeme_tipi ?? "—"}
                        </td>
                        <td className="px-4 py-4 font-medium">{m.ad ?? "—"}</td>
                        <td className="px-4 py-4 font-mono text-xs text-muted-foreground">
                          {formatDate(m.guncelleme_tarihi)}
                        </td>
                        <td className="px-8 py-4 text-right font-mono">
                          {formatCurrency(m.fiyat)}
                        </td>
                      </tr>
                    </ContextMenuTrigger>
                    <ContextMenuContent className="w-48">
                      <ContextMenuItem onSelect={() => openMaterial(m, true)}>
                        <Pencil className="size-3.5" />
                        Düzenle
                      </ContextMenuItem>
                      <ContextMenuItem
                        className="text-destructive focus:text-destructive"
                        onSelect={() => setDeleteTarget(m)}
                      >
                        <Trash2 className="size-3.5" />
                        Sil
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                  );
                })}
                {paddingBottom > 0 && (
                  <tr aria-hidden>
                    <td colSpan={5} style={{ height: paddingBottom }} />
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

      </div>

      {selected && (
        <MaterialDetailPanel
          key={`${selected.id}-${editRequest}`}
          materialId={selected.id}
          fallback={selected}
          initialEditing={editRequest}
          onClose={() => setSelected(null)}
          onRequestDelete={(m) => setDeleteTarget(m)}
        />
      )}

      <MaterialAddDialog open={addOpen} onOpenChange={setAddOpen} />
      <MaterialImportDialog open={importOpen} onOpenChange={setImportOpen} />

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <AlertDialogContent className="border-border bg-surface">
          <AlertDialogHeader>
            <AlertDialogTitle>Malzemeyi sil?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget?.ad} ({deleteTarget?.malzeme_kodu}) kalıcı olarak
              silinecek. Bu işlem geri alınamaz.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
              }}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending && <Loader2 className="size-4 animate-spin" />}
              Sil
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function MaterialDetailPanel({
  materialId,
  fallback,
  initialEditing,
  onClose,
  onRequestDelete,
}: {
  materialId: number;
  fallback: MaterialInfo;
  initialEditing: boolean;
  onClose: () => void;
  onRequestDelete: (m: MaterialInfo) => void;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(initialEditing);
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");

  const detailQuery = useQuery({
    queryKey: ["material-detail", materialId],
    queryFn: () => fetchMaterialDetail(token!, materialId),
    enabled: !!token,
  });

  const material = detailQuery.data?.material ?? fallback;
  const usedProducts = detailQuery.data?.used_products ?? [];
  const isYariMamul = (material.malzeme_tipi ?? "").toLowerCase().includes("yarı");

  useEffect(() => {
    setName(material.ad ?? "");
    setPrice(material.fiyat != null ? String(material.fiyat) : "");
  }, [material.ad, material.fiyat, editing]);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateMaterial(token!, materialId, {
        malzeme_kodu: material.malzeme_kodu ?? "",
        malzeme_tipi: material.malzeme_tipi ?? "",
        ad: name.trim(),
        birim_fiyat: price === "" ? 0 : price,
      }),
    onSuccess: () => {
      toast.success("Malzeme güncellendi.");
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      queryClient.invalidateQueries({ queryKey: ["materials-cost-version"] });
      queryClient.invalidateQueries({ queryKey: ["material-detail", materialId] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Güncelleme başarısız.");
    },
  });

  return (
    <div className="animate-panel-in fixed inset-0 z-40 flex w-full flex-col overflow-hidden border-panel-red bg-panel-red text-panel-red-foreground md:static md:z-auto md:w-96 md:shrink-0 md:border-l">
      <div className="flex shrink-0 items-start justify-between border-b border-white/15 p-6">
        <div className="min-w-0">
          {material.malzeme_kodu && (
            <span className="font-mono text-[11px] uppercase tracking-widest text-panel-red-foreground/70">
              {material.malzeme_kodu}
            </span>
          )}
          <h2 className="truncate font-display text-lg font-bold tracking-tight text-panel-red-foreground">
            {material.ad ?? "Malzeme"}
          </h2>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-panel-red-foreground/70 hover:bg-white/10 hover:text-panel-red-foreground"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* Action toolbar */}
      <div className="flex shrink-0 gap-2 border-b border-white/15 bg-black/15 p-4">
        {editing ? (
          <>
            <Button
              size="sm"
              variant="outline"
              className="h-8 flex-1 gap-1.5 border-white/25 bg-transparent px-2 text-xs text-panel-red-foreground hover:bg-white/10 hover:text-panel-red-foreground"
              onClick={() => setEditing(false)}
            >
              <X className="size-3.5" />
              İptal
            </Button>
            <Button
              size="sm"
              className="h-8 flex-1 gap-1.5 px-2 text-xs"
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending && <Loader2 className="size-3.5 animate-spin" />}
              Kaydet
            </Button>
          </>
        ) : (
          <>
            <Button
              size="sm"
              variant="outline"
              className="h-8 flex-1 gap-1.5 border-white/25 bg-transparent px-2 text-xs text-panel-red-foreground hover:bg-white/10 hover:text-panel-red-foreground"
              onClick={() => setEditing(true)}
            >
              <Pencil className="size-3.5" />
              Düzenle
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 flex-1 gap-1.5 border-white/25 bg-transparent px-2 text-xs text-panel-red-foreground hover:bg-white/10 hover:text-panel-red-foreground"
              onClick={() => onRequestDelete(material)}
            >
              <Trash2 className="size-3.5" />
              Sil
            </Button>
          </>
        )}
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        <div className="grid grid-cols-2 gap-4">
          <PanelInfoBox label="Tip" value={material.malzeme_tipi ?? "—"} />
          {editing ? (
            <div className="rounded-md border border-white/20 bg-white/10 p-3">
              <Label className="mb-1 block font-mono text-[10px] uppercase tracking-wide text-panel-red-foreground/70">
                Birim Fiyat
              </Label>
              <Input
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                disabled={isYariMamul}
                inputMode="decimal"
                className="h-8 border-white/25 bg-white/10 font-mono text-panel-red-foreground placeholder:text-panel-red-foreground/50"
              />
            </div>
          ) : (
            <PanelInfoBox label="Birim Fiyat" value={formatCurrency(material.fiyat)} mono />
          )}
        </div>

        {editing && (
          <div className="space-y-2">
            <Label className="font-mono text-[10px] uppercase tracking-wide text-panel-red-foreground/70">
              Ad
            </Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isYariMamul}
              className="border-white/25 bg-white/10 text-panel-red-foreground placeholder:text-panel-red-foreground/50"
            />
          </div>
        )}

        {editing && isYariMamul && (
          <p className="rounded-md border border-white/25 bg-white/10 p-3 text-xs text-panel-red-foreground">
            Yarı Mamül kayıtlarının ad ve fiyatı doğrudan düzenlenemez; bağlı sabit
            maliyet kaleminden hesaplanır.
          </p>
        )}

        <div>
          <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-panel-red-foreground/70">
            Kullanıldığı Ürünler
          </h3>
          {detailQuery.isLoading ? (
            <Skeleton className="h-20 w-full bg-white/10" />
          ) : usedProducts.length === 0 ? (
            <p className="text-xs text-panel-red-foreground/70">
              Bu malzeme henüz bir üründe kullanılmıyor.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {usedProducts.map((u, i) => (
                <li
                  key={i}
                  className="flex justify-between rounded border border-white/20 bg-white/10 px-3 py-2 text-sm"
                >
                  <span className="truncate text-panel-red-foreground">{u.urun_adi ?? "—"}</span>
                  <span className="shrink-0 font-mono text-xs text-panel-red-foreground/70">
                    {u.urun_kodu}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function PanelInfoBox({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-white/20 bg-white/10 p-3">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wide text-panel-red-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          "text-sm font-medium text-panel-red-foreground",
          mono && "font-mono",
        )}
      >
        {value}
      </div>
    </div>
  );
}
