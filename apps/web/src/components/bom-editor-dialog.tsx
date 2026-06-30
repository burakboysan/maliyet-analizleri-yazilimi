import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Boxes,
  Calculator,
  Layers,
  Loader2,
  Package,
  Plus,
  Search,
  Trash2,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import {
  addProductTreeMaterials,
  deleteProductTreeItems,
  fetchMaterials,
  fetchProductDetail,
  fetchProductTree,
  recalculateProductTreeCost,
  saveProductTreeLabor,
  searchProductTreeMaterials,
  updateProductTreeItemQuantity,
  type ProductLabor,
  type ProductTreeItem,
} from "../lib/api";
import { formatCurrency } from "../lib/format";
import { cn } from "../lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

function toNum(v: number | string | null | undefined): number {
  if (v === null || v === undefined || v === "") return 0;
  const n = typeof v === "string" ? Number(v) : v;
  return Number.isNaN(n) ? 0 : n;
}

export function BomEditorDialog({
  productId,
  productName,
  productCode,
  open,
  onOpenChange,
}: {
  productId: number;
  productName: string;
  productCode?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { token } = useAuth();
  const qc = useQueryClient();

  const treeQuery = useQuery({
    queryKey: ["product-tree", productId],
    queryFn: () => fetchProductTree(token!, productId),
    enabled: !!token && open,
  });
  const detailQuery = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: () => fetchProductDetail(token!, productId),
    enabled: !!token && open,
  });

  const tree = treeQuery.data;
  const cost = detailQuery.data?.cost_breakdown;

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["product-tree", productId] });
    qc.invalidateQueries({ queryKey: ["product-detail", productId] });
    qc.invalidateQueries({ queryKey: ["products"] });
  };

  const recalcMutation = useMutation({
    mutationFn: () => recalculateProductTreeCost(token!, productId),
    onSuccess: () => {
      toast.success("Maliyet yeniden hesaplandı.");
      invalidate();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Hesaplama başarısız."),
  });

  const hasAlt = (tree?.alt_urunler?.length ?? 0) > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] w-[min(900px,95vw)] max-w-none flex-col overflow-hidden p-0 sm:max-w-none">
        <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
          <DialogTitle className="flex items-center gap-2 font-display">
            Reçete Düzenle
            {productCode && (
              <span className="font-mono text-xs font-normal text-primary">
                {productCode}
              </span>
            )}
          </DialogTitle>
          <DialogDescription className="truncate">{productName}</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {treeQuery.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : treeQuery.isError ? (
            <p className="text-sm text-destructive">
              Reçete yüklenemedi. Lütfen tekrar deneyin.
            </p>
          ) : (
            <Tabs defaultValue="yari" className="w-full">
              <TabsList className="mb-5 flex w-full flex-wrap justify-start">
                <TabsTrigger value="yari" className="gap-1.5">
                  <Layers className="size-4" />
                  Yarı Mamuller ({tree?.yari_mamuller?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="mamul" className="gap-1.5">
                  <Package className="size-4" />
                  Mamuller ({tree?.mamuller?.length ?? 0})
                </TabsTrigger>
                {hasAlt && (
                  <TabsTrigger value="alt" className="gap-1.5">
                    <Boxes className="size-4" />
                    Alt Ürünler ({tree?.alt_urunler?.length ?? 0})
                  </TabsTrigger>
                )}
                <TabsTrigger value="iscilik" className="gap-1.5">
                  <Wrench className="size-4" />
                  İşçilikler ({tree?.iscilikler?.length ?? 0})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="yari" className="mt-0">
                <BomMaterialTab
                  title="Yarı Mamuller"
                  items={tree?.yari_mamuller}
                  productId={productId}
                  onChanged={invalidate}
                />
              </TabsContent>

              <TabsContent value="mamul" className="mt-0">
                <BomMaterialTab
                  title="Mamuller"
                  items={tree?.mamuller}
                  productId={productId}
                  onChanged={invalidate}
                />
              </TabsContent>

              {hasAlt && (
                <TabsContent value="alt" className="mt-0">
                  <BomSection
                    title="Alt Ürünler"
                    items={tree?.alt_urunler}
                    productId={productId}
                    onChanged={invalidate}
                  />
                </TabsContent>
              )}

              <TabsContent value="iscilik" className="mt-0">
                <LaborSection
                  productId={productId}
                  labor={tree?.iscilikler}
                  onSaved={invalidate}
                />
              </TabsContent>
            </Tabs>
          )}
        </div>

        <div className="flex shrink-0 items-center justify-between gap-4 border-t border-border bg-surface px-6 py-4">
          <div className="text-sm">
            <span className="text-muted-foreground">Toplam Maliyet: </span>
            <span className="font-mono font-bold text-primary">
              {formatCurrency(cost?.toplam_maliyet)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => recalcMutation.mutate()}
              disabled={recalcMutation.isPending}
            >
              {recalcMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Calculator className="size-4" />
              )}
              Maliyeti Yeniden Hesapla
            </Button>
            <Button onClick={() => onOpenChange(false)}>Kapat</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function BomMaterialTab({
  title,
  items,
  productId,
  onChanged,
}: {
  title: string;
  items?: ProductTreeItem[];
  productId: number;
  onChanged: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const hasItems = !!items && items.length > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {title}
          <span className="text-foreground/60">({items?.length ?? 0})</span>
        </h3>
        <Button
          variant={adding ? "outline" : "default"}
          size="sm"
          onClick={() => setAdding((v) => !v)}
        >
          <Plus className="size-4" />
          {adding ? "Kapat" : "Malzeme Ekle"}
        </Button>
      </div>

      {adding && (
        <AddMaterialPanel
          productId={productId}
          onAdded={() => {
            onChanged();
          }}
        />
      )}

      {hasItems ? (
        <BomSection
          items={items}
          productId={productId}
          onChanged={onChanged}
        />
      ) : (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Bu bölümde henüz kalem yok. "Malzeme Ekle" ile ekleyin.
        </p>
      )}
    </div>
  );
}

function BomSection({
  title,
  items,
  productId,
  onChanged,
}: {
  title?: string;
  items?: ProductTreeItem[];
  productId: number;
  onChanged: () => void;
}) {
  if (!items || items.length === 0) return null;
  return (
    <section>
      {title && (
        <h3 className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {title}
          <span className="text-foreground/60">({items.length})</span>
        </h3>
      )}
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 font-mono text-[11px] uppercase text-muted-foreground">
              <th className="px-3 py-2 text-left font-medium">Kod</th>
              <th className="px-3 py-2 text-left font-medium">Ad</th>
              <th className="w-32 px-3 py-2 text-right font-medium">Miktar</th>
              <th className="w-12 px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {items.map((item) => (
              <BomRow
                key={item.id}
                item={item}
                productId={productId}
                onChanged={onChanged}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function BomRow({
  item,
  onChanged,
}: {
  item: ProductTreeItem;
  productId: number;
  onChanged: () => void;
}) {
  const { token } = useAuth();
  const [value, setValue] = useState(String(toNum(item.miktar)));
  const [confirmDelete, setConfirmDelete] = useState(false);

  const qtyMutation = useMutation({
    mutationFn: (miktar: number) =>
      updateProductTreeItemQuantity(token!, item.id, miktar),
    onSuccess: () => {
      toast.success("Miktar güncellendi.");
      onChanged();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Güncelleme başarısız."),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProductTreeItems(token!, [item.id]),
    onSuccess: () => {
      toast.success("Kalem silindi.");
      onChanged();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Silme başarısız."),
  });

  const dirty = toNum(value) !== toNum(item.miktar);

  const commit = () => {
    if (!dirty) return;
    const n = toNum(value);
    if (n <= 0) {
      toast.error("Miktar 0'dan büyük olmalı.");
      setValue(String(toNum(item.miktar)));
      return;
    }
    qtyMutation.mutate(n);
  };

  return (
    <tr className="text-foreground">
      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
        {item.kod ?? "—"}
      </td>
      <td className="px-3 py-2">{item.ad ?? "—"}</td>
      <td className="px-3 py-2 text-right">
        <div className="flex items-center justify-end gap-1.5">
          <Input
            type="number"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
            className={cn(
              "h-8 w-24 text-right font-mono",
              dirty && "border-primary",
            )}
          />
          {qtyMutation.isPending && (
            <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
          )}
        </div>
      </td>
      <td className="px-3 py-2 text-right">
        <button
          onClick={() => setConfirmDelete(true)}
          disabled={deleteMutation.isPending}
          className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          aria-label="Sil"
        >
          {deleteMutation.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Trash2 className="size-4" />
          )}
        </button>
      </td>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Kalem silinsin mi?</AlertDialogTitle>
            <AlertDialogDescription>
              "{item.ad ?? item.kod}" reçeteden kaldırılacak. Bu işlem geri
              alınamaz.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Vazgeç</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Sil
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </tr>
  );
}

function AddMaterialPanel({
  productId,
  onAdded,
}: {
  productId: number;
  onAdded: () => void;
}) {
  const { token } = useAuth();
  const [materialType, setMaterialType] = useState<string>("");
  const [search, setSearch] = useState("");

  const typesQuery = useQuery({
    queryKey: ["material-types"],
    queryFn: async () => {
      const list = await fetchMaterials(token!, "");
      const types = new Set<string>();
      for (const m of list) {
        if (m.malzeme_tipi) types.add(m.malzeme_tipi);
      }
      return Array.from(types).sort((a, b) => a.localeCompare(b, "tr"));
    },
    enabled: !!token,
  });

  const resultsQuery = useQuery({
    queryKey: ["tree-material-search", materialType, search],
    queryFn: () => searchProductTreeMaterials(token!, materialType, search),
    enabled: !!token && !!materialType,
  });

  const results = resultsQuery.data ?? [];

  return (
    <section className="rounded-lg border border-dashed border-border p-4">
      <h3 className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <Plus className="size-3.5 text-primary" />
        Malzeme Ekle
      </h3>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Select value={materialType} onValueChange={setMaterialType}>
          <SelectTrigger className="w-full sm:w-56">
            <SelectValue placeholder="Malzeme tipi seçin" />
          </SelectTrigger>
          <SelectContent>
            {typesQuery.isLoading ? (
              <div className="p-2 text-xs text-muted-foreground">
                Yükleniyor...
              </div>
            ) : (
              (typesQuery.data ?? []).map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={
              materialType ? "Kod veya ad ara..." : "Önce tip seçin"
            }
            disabled={!materialType}
            className="pl-9"
          />
        </div>
      </div>

      {materialType && (
        <div className="mt-3 max-h-60 overflow-y-auto rounded-md border border-border">
          {resultsQuery.isLoading ? (
            <div className="space-y-2 p-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : results.length === 0 ? (
            <p className="p-4 text-center text-xs text-muted-foreground">
              Sonuç bulunamadı.
            </p>
          ) : (
            <ul className="divide-y divide-border/50">
              {results.slice(0, 50).map((m) => (
                <AddMaterialRow
                  key={m.kod}
                  kod={m.kod}
                  ad={m.ad}
                  malzemeTipi={m.malzeme_tipi}
                  productId={productId}
                  onAdded={onAdded}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function AddMaterialRow({
  kod,
  ad,
  malzemeTipi,
  productId,
  onAdded,
}: {
  kod: string;
  ad: string;
  malzemeTipi: string;
  productId: number;
  onAdded: () => void;
}) {
  const { token } = useAuth();
  const [qty, setQty] = useState("1");

  const addMutation = useMutation({
    mutationFn: () =>
      addProductTreeMaterials(token!, productId, [
        { kod, ad, malzeme_tipi: malzemeTipi, miktar: toNum(qty) },
      ]),
    onSuccess: () => {
      toast.success(`${kod} eklendi.`);
      setQty("1");
      onAdded();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Ekleme başarısız."),
  });

  return (
    <li className="flex items-center gap-3 px-3 py-2 text-sm">
      <span className="font-mono text-xs text-muted-foreground">{kod}</span>
      <span className="min-w-0 flex-1 truncate">{ad}</span>
      <Input
        type="number"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        className="h-8 w-20 text-right font-mono"
      />
      <Button
        size="sm"
        onClick={() => {
          if (toNum(qty) <= 0) {
            toast.error("Miktar 0'dan büyük olmalı.");
            return;
          }
          addMutation.mutate();
        }}
        disabled={addMutation.isPending}
      >
        {addMutation.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <Plus className="size-4" />
        )}
        Ekle
      </Button>
    </li>
  );
}

function LaborSection({
  productId,
  labor,
  onSaved,
}: {
  productId: number;
  labor?: ProductLabor[];
  onSaved: () => void;
}) {
  const { token } = useAuth();
  const initial = useMemo<ProductLabor[]>(
    () =>
      (labor ?? []).map((l) => ({
        iscilik_tipi: l.iscilik_tipi ?? "",
        usta_saat: toNum(l.usta_saat),
        yardimci_saat: toNum(l.yardimci_saat),
      })),
    [labor],
  );
  const [rows, setRows] = useState<ProductLabor[]>(initial);
  const [editing, setEditing] = useState(false);

  // Re-sync when server data changes and we are not editing.
  const initialKey = JSON.stringify(initial);
  const [syncedKey, setSyncedKey] = useState(initialKey);
  if (!editing && initialKey !== syncedKey) {
    setRows(initial);
    setSyncedKey(initialKey);
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      saveProductTreeLabor(
        token!,
        productId,
        rows.map((r) => ({
          iscilik_tipi: r.iscilik_tipi ?? "",
          usta_saat: toNum(r.usta_saat),
          yardimci_saat: toNum(r.yardimci_saat),
        })),
      ),
    onSuccess: () => {
      toast.success("İşçilik kaydedildi.");
      setEditing(false);
      onSaved();
    },
    onError: (e: unknown) =>
      toast.error(e instanceof Error ? e.message : "Kayıt başarısız."),
  });

  const update = (i: number, patch: Partial<ProductLabor>) => {
    setEditing(true);
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  };

  if (!labor || labor.length === 0)
    return (
      <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Bu ürün için tanımlı işçilik kalemi yok.
      </p>
    );

  return (
    <section>
      <h3 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        İşçilikler
      </h3>
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 font-mono text-[11px] uppercase text-muted-foreground">
              <th className="px-3 py-2 text-left font-medium">İşçilik Tipi</th>
              <th className="w-32 px-3 py-2 text-right font-medium">
                Usta (saat)
              </th>
              <th className="w-32 px-3 py-2 text-right font-medium">
                Yardımcı (saat)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.iscilik_tipi || "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  <Input
                    type="number"
                    value={String(toNum(r.usta_saat))}
                    onChange={(e) =>
                      update(i, { usta_saat: e.target.value })
                    }
                    className="h-8 w-24 text-right font-mono"
                  />
                </td>
                <td className="px-3 py-2 text-right">
                  <Input
                    type="number"
                    value={String(toNum(r.yardimci_saat))}
                    onChange={(e) =>
                      update(i, { yardimci_saat: e.target.value })
                    }
                    className="h-8 w-24 text-right font-mono"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <div className="mt-3 flex justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setRows(initial);
              setEditing(false);
            }}
          >
            Vazgeç
          </Button>
          <Button
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending && (
              <Loader2 className="size-4 animate-spin" />
            )}
            İşçiliği Kaydet
          </Button>
        </div>
      )}
    </section>
  );
}
