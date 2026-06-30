import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Copy,
  ListTree,
  Pencil,
  RefreshCw,
  SlidersHorizontal,
  TrendingUp,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import {
  copyProduct,
  fetchProductDetail,
  recalculateProductTreeCost,
  reviseProductCosts,
  type ProductDetailField,
} from "../lib/api";
import { formatCurrency, formatDate } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { BomEditorDialog } from "./bom-editor-dialog";

function formatFieldValue(field: ProductDetailField): string {
  const { key, value } = field;
  if (value === null || value === undefined || value === "") return "—";
  if (key === "maliyet_hesaplama_tarihi") return formatDate(String(value));
  return String(value);
}

export function ProductDetailDialog({
  productId,
  open,
  onOpenChange,
}: {
  productId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [bomOpen, setBomOpen] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: () => fetchProductDetail(token!, productId),
    enabled: !!token && open,
  });

  const detail = detailQuery.data;
  const cost = detail?.cost_breakdown;

  const productName =
    (detail?.product?.urun_adi as string | undefined) ?? "Ürün Detayı";
  const productCode = detail?.product?.urun_kodu as string | undefined;

  const invalidateProduct = () => {
    queryClient.invalidateQueries({ queryKey: ["product-detail", productId] });
    queryClient.invalidateQueries({ queryKey: ["product-tree", productId] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
    queryClient.invalidateQueries({ queryKey: ["products-cost-version"] });
  };

  const recalcMutation = useMutation({
    mutationFn: () => recalculateProductTreeCost(token!, productId),
    onSuccess: () => {
      toast.success("Maliyet yeniden hesaplandı");
      invalidateProduct();
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Hesaplama başarısız"),
  });

  const reviseMutation = useMutation({
    mutationFn: () => reviseProductCosts(token!, [productId]),
    onSuccess: () => {
      toast.success("Fiyatlar revize edildi");
      invalidateProduct();
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Revizyon başarısız"),
  });

  const copyMutation = useMutation({
    mutationFn: (newCode: string) => copyProduct(token!, productId, newCode),
    onSuccess: () => {
      toast.success("Ürün kopyalandı");
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Kopyalama başarısız"),
  });

  const handleCopy = () => {
    const newCode = window.prompt("Yeni ürün kodu girin:");
    if (newCode && newCode.trim()) copyMutation.mutate(newCode.trim());
  };

  const busy =
    recalcMutation.isPending ||
    reviseMutation.isPending ||
    copyMutation.isPending;

  // Properties to show in the "Özellikler" tab. The backend curates
  // display_fields per category (filter / channel / flange) with labels.
  const specFields = (detail?.display_fields ?? []).filter(
    (f) => f.key !== "id" && f.key !== "aciklama",
  );
  const description = detail?.display_fields?.find((f) => f.key === "aciklama");

  const laborRows = (detail?.labor_rows ?? []).filter(
    (r) => Number(r.usta_saat) > 0 || Number(r.yardimci_saat) > 0,
  );

  const costRows: { label: string; value: number | string | null | undefined }[] =
    cost
      ? [
          { label: "Malzeme Maliyeti", value: cost.malzeme_maliyeti },
          { label: "İşçilik Maliyeti", value: cost.iscilik_maliyeti },
          { label: "Üretim Gideri", value: cost.uretim_gideri },
          { label: "Yönetim Gideri", value: cost.yonetim_gideri },
          { label: "Alt Ürün Maliyeti", value: cost.alt_urun_maliyeti },
        ]
      : [];

  const calcDate = detail?.product?.maliyet_hesaplama_tarihi as
    | string
    | undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-3xl flex-col gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">{productName} detayları</DialogTitle>
        {/* Deep-red header */}
        <div className="shrink-0 border-b border-white/15 bg-panel-red px-6 py-5 text-panel-red-foreground">
          {productCode && (
            <span className="font-mono text-[11px] uppercase tracking-widest text-panel-red-foreground/70">
              {productCode}
            </span>
          )}
          <h2 className="truncate font-display text-xl font-bold tracking-tight text-panel-red-foreground">
            {productName}
          </h2>
          {calcDate && (
            <p className="mt-1 font-mono text-[11px] text-panel-red-foreground/60">
              Son hesaplama: {formatDate(calcDate)}
            </p>
          )}
        </div>

        {/* Action toolbar */}
        <div className="flex shrink-0 flex-wrap gap-2 border-b border-border bg-muted/40 px-6 py-3">
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 px-2.5 text-xs"
            disabled={busy}
            onClick={() => recalcMutation.mutate()}
          >
            <RefreshCw
              className={cn("size-3.5", recalcMutation.isPending && "animate-spin")}
            />
            Yeniden Hesapla
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 px-2.5 text-xs"
            disabled={busy}
            onClick={() => reviseMutation.mutate()}
          >
            <TrendingUp className="size-3.5" />
            Fiyatları Revize Et
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 px-2.5 text-xs"
            onClick={() => setBomOpen(true)}
          >
            <Pencil className="size-3.5" />
            Reçete Düzenle
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 px-2.5 text-xs"
            disabled={busy}
            onClick={handleCopy}
          >
            <Copy className="size-3.5" />
            Kopyala
          </Button>
        </div>

        {detailQuery.isLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </div>
        ) : detailQuery.isError ? (
          <div className="p-10 text-center text-sm text-destructive">
            Ürün detayı yüklenemedi.
          </div>
        ) : (
          <Tabs defaultValue="specs" className="flex min-h-0 flex-1 flex-col">
            <TabsList className="mx-6 mt-4 w-fit">
              <TabsTrigger value="specs" className="gap-1.5 text-xs">
                <SlidersHorizontal className="size-3.5" />
                Özellikler
              </TabsTrigger>
              <TabsTrigger value="labor" className="gap-1.5 text-xs">
                <Wrench className="size-3.5" />
                İşçilik
              </TabsTrigger>
              <TabsTrigger value="cost" className="gap-1.5 text-xs">
                <ListTree className="size-3.5" />
                Maliyet
              </TabsTrigger>
            </TabsList>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-6">
              {/* Özellikler */}
              <TabsContent value="specs" className="mt-4">
                {description?.value && (
                  <div className="mb-4 rounded-lg border border-border bg-muted/30 p-3">
                    <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                      Açıklama
                    </p>
                    <p className="mt-1 text-sm">{String(description.value)}</p>
                  </div>
                )}
                <dl className="grid grid-cols-1 gap-x-8 gap-y-0 sm:grid-cols-2">
                  {specFields.map((field) => (
                    <div
                      key={field.key}
                      className="flex items-center justify-between gap-4 border-b border-border/60 py-2.5"
                    >
                      <dt className="text-sm text-muted-foreground">
                        {field.label}
                      </dt>
                      <dd className="text-right font-mono text-sm font-medium">
                        {formatFieldValue(field)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </TabsContent>

              {/* İşçilik */}
              <TabsContent value="labor" className="mt-4">
                {laborRows.length === 0 ? (
                  <p className="py-10 text-center text-sm text-muted-foreground">
                    Bu ürün için tanımlı işçilik saati yok.
                  </p>
                ) : (
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                        <th className="py-2.5 font-medium">İşçilik Tipi</th>
                        <th className="py-2.5 text-right font-medium">
                          Usta (saat)
                        </th>
                        <th className="py-2.5 text-right font-medium">
                          Yardımcı (saat)
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/60">
                      {laborRows.map((row) => (
                        <tr key={row.iscilik_tipi}>
                          <td className="py-2.5">{row.iscilik_tipi}</td>
                          <td className="py-2.5 text-right font-mono">
                            {Number(row.usta_saat) || 0}
                          </td>
                          <td className="py-2.5 text-right font-mono">
                            {Number(row.yardimci_saat) || 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </TabsContent>

              {/* Maliyet */}
              <TabsContent value="cost" className="mt-4">
                <div className="space-y-2">
                  {costRows.map((row) => (
                    <div
                      key={row.label}
                      className="flex justify-between border-b border-border/60 py-2.5 text-sm"
                    >
                      <span className="text-muted-foreground">{row.label}</span>
                      <span className="font-mono font-medium">
                        {formatCurrency(row.value)}
                      </span>
                    </div>
                  ))}
                  <div className="mt-2 flex justify-between rounded-lg bg-panel-red px-4 py-3 font-bold text-panel-red-foreground">
                    <span>TOPLAM</span>
                    <span className="font-mono">
                      {formatCurrency(cost?.toplam_maliyet)}
                    </span>
                  </div>
                </div>
              </TabsContent>
            </div>
          </Tabs>
        )}

        <BomEditorDialog
          productId={productId}
          productName={productName}
          productCode={productCode}
          open={bomOpen}
          onOpenChange={setBomOpen}
        />
      </DialogContent>
    </Dialog>
  );
}
