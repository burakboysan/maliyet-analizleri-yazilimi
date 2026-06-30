import { createFileRoute } from "@tanstack/react-router";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import { useDebouncedValue } from "../hooks/use-debounced-value";
import {
  Copy,
  Pencil,
  RefreshCw,
  Search,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import {
  copyProduct,
  fetchCostVersion,
  fetchProducts,
  recalculateProductTreeCost,
  reviseProductCosts,
  type ProductInfo,
} from "../lib/api";
import { formatCurrency } from "../lib/format";
import { cn } from "../lib/utils";
import { Input } from "../components/ui/input";
import { TableErrorState, TableLoadingState } from "../components/table-state";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "../components/ui/context-menu";
import { BomEditorDialog } from "../components/bom-editor-dialog";
import { ProductDetailDialog } from "../components/product-detail-dialog";
import {
  applyProductFilters,
  EMPTY_FILTERS,
  ProductFilterBar,
  type ProductFilterState,
} from "../components/product-filters";

export const Route = createFileRoute("/_authenticated/products")({
  head: () => ({ meta: [{ title: "Ürünler — Bomaksan" }] }),
  component: ProductsPage,
});

function ProductsPage() {
  const { token } = useAuth();
  const [search, setSearch] = useState("");

  // Cheap version stamp from the backend. It changes whenever any product
  // cost is recalculated/revised, so we use it as part of the products query
  // key — the heavy list refetches automatically when costs change but stays
  // instant (cached) when nothing changed. A short staleTime keeps tab
  // switches instant (no network wait on every mount) while still
  // revalidating periodically; mutations invalidate it explicitly.
  const costVersionQuery = useQuery({
    queryKey: ["products-cost-version"],
    queryFn: () => fetchCostVersion(token!),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
  // While loading → undefined (wait). On error → fall back so the list still
  // loads instead of being blocked by a missing/failing version endpoint.
  const costVersion = costVersionQuery.isError
    ? "no-version"
    : costVersionQuery.data;

  // Fetch the full list ONCE per cost version (cached + persisted). Search is
  // applied in memory so typing never triggers a new multi-page fetch.
  // keepPreviousData keeps the current rows on screen if the version stamp
  // changes, so the table never flashes an empty/loading state.
  const productsQuery = useQuery({
    queryKey: ["products", costVersion ?? "pending"],
    queryFn: () => fetchProducts(token!),
    enabled: !!token && costVersion !== undefined,
    placeholderData: keepPreviousData,
  });

  const allProducts = productsQuery.data ?? [];
  const [filters, setFilters] = useState<ProductFilterState>(EMPTY_FILTERS);
  // Debounce the filter so typing doesn't re-scan/re-render the whole list on
  // every keystroke, and memoize the result so it only recomputes when the
  // data or the (debounced) query actually changes.
  const debouncedSearch = useDebouncedValue(search, 200);
  const products = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    const byText = !q
      ? allProducts
      : allProducts.filter((p) =>
          [p.urun_kodu, p.urun_adi, p.urun_kategorisi, p.urun_tipi, p.urun_modeli].some(
            (f) => (f ?? "").toLowerCase().includes(q),
          ),
        );
    return applyProductFilters(byText, filters);
  }, [allProducts, debouncedSearch, filters]);


  const [selectedId, setSelectedId] = useState<number | null>(null);


  const queryClient = useQueryClient();
  const [bomTarget, setBomTarget] = useState<ProductInfo | null>(null);

  const invalidateProducts = (id: number) => {
    queryClient.invalidateQueries({ queryKey: ["product-detail", id] });
    queryClient.invalidateQueries({ queryKey: ["product-tree", id] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
    // The cost version on the backend changed too — pick up the new stamp.
    queryClient.invalidateQueries({ queryKey: ["products-cost-version"] });
  };

  const rowRecalc = useMutation({
    mutationFn: (id: number) => recalculateProductTreeCost(token!, id),
    onSuccess: (_d, id) => {
      toast.success("Maliyet yeniden hesaplandı");
      invalidateProducts(id);
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Hesaplama başarısız"),
  });

  const rowRevise = useMutation({
    mutationFn: (id: number) => reviseProductCosts(token!, [id]),
    onSuccess: (_d, id) => {
      toast.success("Fiyatlar revize edildi");
      invalidateProducts(id);
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Revizyon başarısız"),
  });

  const rowCopy = useMutation({
    mutationFn: ({ id, newCode }: { id: number; newCode: string }) =>
      copyProduct(token!, id, newCode),
    onSuccess: () => {
      toast.success("Ürün kopyalandı");
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : "Kopyalama başarısız"),
  });

  const handleRowCopy = (id: number) => {
    const newCode = window.prompt("Yeni ürün kodu girin:");
    if (newCode && newCode.trim()) rowCopy.mutate({ id, newCode: newCode.trim() });
  };

  // Virtualize the row list: only the visible rows (plus a small overscan) are
  // mounted, so 500+ products render instantly instead of building hundreds of
  // ContextMenu nodes up front.
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: products.length,
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
      {/* Table */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="relative max-w-md flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Ürün kodu veya adı ara..."
                className="pl-9"
              />
            </div>
            <span className="font-mono text-xs text-muted-foreground">
              {products.length} kayıt
            </span>
          </div>
          <ProductFilterBar
            products={allProducts}
            value={filters}
            onChange={setFilters}
          />
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">

          {productsQuery.isError ? (
            <TableErrorState
              error={productsQuery.error}
              retrying={productsQuery.isFetching}
              onRetry={() => {
                costVersionQuery.refetch();
                productsQuery.refetch();
              }}
            />
          ) : productsQuery.isLoading || costVersion === undefined ? (
            <TableLoadingState message="Ürünler yükleniyor…" rows={8} />
          ) : products.length === 0 ? (
            <div className="p-16 text-center text-sm text-muted-foreground">
              Ürün bulunamadı.
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
                <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                  <th className="px-8 py-4 font-medium">Ürün Kodu</th>
                  <th className="px-4 py-4 font-medium">Ürün Adı</th>
                  <th className="px-4 py-4 font-medium">Kategori</th>
                  <th className="hidden px-4 py-4 font-medium lg:table-cell">
                    Tip
                  </th>
                  <th className="hidden px-4 py-4 font-medium xl:table-cell">
                    Model
                  </th>
                  <th className="px-8 py-4 text-right font-medium">Maliyet</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-sm">
                {paddingTop > 0 && (
                  <tr aria-hidden>
                    <td colSpan={6} style={{ height: paddingTop }} />
                  </tr>
                )}
                {virtualRows.map((vr) => {
                  const p = products[vr.index];
                  return (
                  <ContextMenu key={p.id}>
                    <ContextMenuTrigger asChild>
                      <tr
                        onClick={() => setSelectedId(p.id)}
                        className={cn(
                          "cursor-pointer transition-colors hover:bg-accent",
                          selectedId === p.id &&
                            "border-l-2 border-l-primary bg-accent",
                        )}
                      >
                        <td className="px-8 py-4 font-mono text-sm">
                          {p.urun_kodu ?? "—"}
                        </td>
                        <td className="px-4 py-4 font-medium">{p.urun_adi ?? "—"}</td>
                        <td className="px-4 py-4 text-muted-foreground">
                          {p.urun_kategorisi ?? "—"}
                        </td>
                        <td className="hidden px-4 py-4 text-muted-foreground lg:table-cell">
                          {p.urun_tipi ?? "—"}
                        </td>
                        <td className="hidden px-4 py-4 text-muted-foreground xl:table-cell">
                          {p.urun_modeli ?? "—"}
                        </td>
                        <td
                          className={cn(
                            "px-8 py-4 text-right font-mono text-sm",
                            selectedId === p.id && "text-primary",
                          )}
                        >
                          {formatCurrency(p.maliyet)}
                        </td>
                      </tr>
                    </ContextMenuTrigger>
                    <ContextMenuContent className="w-52">
                      <ContextMenuItem
                        disabled={rowRecalc.isPending}
                        onSelect={() => rowRecalc.mutate(p.id)}
                      >
                        <RefreshCw className="size-3.5" />
                        Yeniden Hesapla
                      </ContextMenuItem>
                      <ContextMenuItem
                        disabled={rowRevise.isPending}
                        onSelect={() => rowRevise.mutate(p.id)}
                      >
                        <TrendingUp className="size-3.5" />
                        Fiyatları Revize Et
                      </ContextMenuItem>
                      <ContextMenuItem onSelect={() => setBomTarget(p)}>
                        <Pencil className="size-3.5" />
                        Reçete Düzenle
                      </ContextMenuItem>
                      <ContextMenuItem
                        disabled={rowCopy.isPending}
                        onSelect={() => handleRowCopy(p.id)}
                      >
                        <Copy className="size-3.5" />
                        Kopyala
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                  );
                })}
                {paddingBottom > 0 && (
                  <tr aria-hidden>
                    <td colSpan={6} style={{ height: paddingBottom }} />
                  </tr>
                )}


              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detail modal */}
      {selectedId !== null && (
        <ProductDetailDialog
          key={selectedId}
          productId={selectedId}
          open={selectedId !== null}
          onOpenChange={(open) => !open && setSelectedId(null)}
        />
      )}

      {bomTarget && (
        <BomEditorDialog
          productId={bomTarget.id}
          productName={bomTarget.urun_adi ?? "Ürün"}
          productCode={bomTarget.urun_kodu ?? undefined}
          open={!!bomTarget}
          onOpenChange={(open) => !open && setBomTarget(null)}
        />
      )}
    </div>

  );
}
