import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  AlertTriangle,
  ExternalLink,
  FileText,
  FileUp,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import { isOwner } from "../lib/roles";
import {
  fetchDocuments,
  uploadDocument,
  deleteDocument,
  type DocumentInfo,
} from "../lib/api";
import { formatDate } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import { Skeleton } from "../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";

export const Route = createFileRoute("/_authenticated/documents")({
  head: () => ({ meta: [{ title: "Doküman Yönetimi — Bomaksan" }] }),
  component: DocumentsPage,
});

// --- normalization helpers (backend shape is not strictly typed) ---
const docId = (d: DocumentInfo, i: number) => String(d.id ?? `${d.title}-${i}`);
const docSeries = (d: DocumentInfo) => (d.series_key ?? d.series ?? "") as string;
const docType = (d: DocumentInfo) => (d.document_type ?? d.type ?? "") as string;
const docLang = (d: DocumentInfo) => (d.language ?? "") as string;
const docTitle = (d: DocumentInfo) => (d.title ?? "") as string;
const docDesc = (d: DocumentInfo) => (d.description ?? "") as string;
const docUpdated = (d: DocumentInfo) =>
  (d.updated_at ?? d.guncelleme_tarihi ?? "") as string;
const docUrl = (d: DocumentInfo) =>
  (d.url ?? d.file_url ?? d.download_url ?? "") as string;

const TUMU = "__all__";

function DocumentsPage() {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();

  const canManage = isOwner(user);

  const [typeFilter, setTypeFilter] = useState(TUMU);
  const [langFilter, setLangFilter] = useState(TUMU);
  const [seriesFilter, setSeriesFilter] = useState(TUMU);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [uploadOpen, setUploadOpen] = useState(false);

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => fetchDocuments(token!),
    enabled: !!token,
    retry: false,
  });

  const allDocs = documentsQuery.data ?? [];

  const typeOptions = useMemo(
    () => Array.from(new Set(allDocs.map(docType).filter(Boolean))).sort(),
    [allDocs],
  );
  const langOptions = useMemo(
    () => Array.from(new Set(allDocs.map(docLang).filter(Boolean))).sort(),
    [allDocs],
  );
  const seriesOptions = useMemo(
    () => Array.from(new Set(allDocs.map(docSeries).filter(Boolean))).sort(),
    [allDocs],
  );

  const docs = useMemo(
    () =>
      allDocs.filter(
        (d) =>
          (typeFilter === TUMU || docType(d) === typeFilter) &&
          (langFilter === TUMU || docLang(d) === langFilter) &&
          (seriesFilter === TUMU || docSeries(d) === seriesFilter),
      ),
    [allDocs, typeFilter, langFilter, seriesFilter],
  );

  const selectedDoc = useMemo(() => {
    if (selectedIds.size !== 1) return null;
    const id = Array.from(selectedIds)[0];
    return allDocs.find((d, i) => docId(d, i) === id) ?? null;
  }, [selectedIds, allDocs]);

  const toggleRow = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openDocument = () => {
    const url = selectedDoc ? docUrl(selectedDoc) : "";
    if (!url) {
      toast.error("Bu doküman için açılabilir bir bağlantı bulunamadı.");
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  };

  // Sadece gerçek (sayısal) id'si olan seçili dokümanlar silinebilir.
  const deletableSelected = useMemo(
    () =>
      allDocs.filter(
        (d, i) => selectedIds.has(docId(d, i)) && d.id != null,
      ),
    [allDocs, selectedIds],
  );

  const deleteMutation = useMutation({
    mutationFn: async () => {
      for (const d of deletableSelected) {
        await deleteDocument(token!, d.id as number | string);
      }
      return deletableSelected.length;
    },
    onSuccess: (count) => {
      toast.success(`${count} doküman silindi.`);
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err) => toast.error((err as Error).message),
  });

  const handleDelete = () => {
    if (deletableSelected.length === 0) {
      toast.error("Silmek için listede gerçek kimliği olan doküman seçin.");
      return;
    }
    if (
      !window.confirm(
        `${deletableSelected.length} doküman kalıcı olarak silinecek. Onaylıyor musunuz?`,
      )
    ) {
      return;
    }
    deleteMutation.mutate();
  };



  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-8 py-5">
        <h2 className="font-display text-lg font-bold tracking-tight">
          Doküman Yönetimi
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Merkezi doküman listesini görüntüleyin ve yetkiniz varsa PDF yükleyin.
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-end gap-3 border-b border-border px-8 py-4">
        <FilterSelect
          label="Doküman Tipi"
          value={typeFilter}
          onChange={setTypeFilter}
          allLabel="Tüm Tipler"
          options={typeOptions}
        />
        <FilterSelect
          label="Dil"
          value={langFilter}
          onChange={setLangFilter}
          allLabel="Tüm Diller"
          options={langOptions}
        />
        <FilterSelect
          label="Seri"
          value={seriesFilter}
          onChange={setSeriesFilter}
          allLabel="Tüm Seriler"
          options={seriesOptions}
        />
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => documentsQuery.refetch()}
            disabled={documentsQuery.isFetching}
          >
            {documentsQuery.isFetching ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Yenile
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={openDocument}
            disabled={!selectedDoc}
          >
            <ExternalLink className="size-4" />
            Dokümanı Aç
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={
              !canManage ||
              deletableSelected.length === 0 ||
              deleteMutation.isPending
            }
            title={
              canManage
                ? undefined
                : "Bu işlem için yönetici yetkisi gerekir."
            }
          >
            {deleteMutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Trash2 className="size-4" />
            )}
            Seçilenleri Sil
            {deletableSelected.length > 0 ? ` (${deletableSelected.length})` : ""}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setUploadOpen(true)}
            disabled={!canManage}
            title={canManage ? undefined : "Bu işlem için yönetici yetkisi gerekir."}
          >
            <FileUp className="size-4" />
            PDF Yükle
          </Button>
        </div>
      </div>

      {!canManage && (
        <div className="border-b border-border bg-muted/30 px-8 py-2 text-xs text-muted-foreground">
          Yükleme ve silme işlemleri yalnızca yönetici (Owner, Master Admin,
          Admin) rolleri için etkindir. Dokümanları görüntüleyebilir ve
          açabilirsiniz.
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {documentsQuery.isLoading ? (
          <div className="space-y-2 p-8">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : documentsQuery.isError ? (
          <div className="flex flex-col items-center justify-center gap-4 p-16 text-center">
            <AlertTriangle className="size-10 text-amber-400" />
            <div>
              <p className="text-sm font-medium text-foreground">
                Doküman servisi şu anda yanıt vermiyor
              </p>
              <p className="mt-1 max-w-md text-xs text-muted-foreground">
                {(documentsQuery.error as Error)?.message ||
                  "Liste yüklenemedi."}{" "}
                Backend ucu hazır olduğunda kayıtlar otomatik görünecek.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => documentsQuery.refetch()}
            >
              <RefreshCw className="size-4" />
              Tekrar Dene
            </Button>
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 p-16 text-center text-muted-foreground">
            <FileText className="size-10 opacity-40" />
            <p className="text-sm">Henüz yayınlanmış doküman yok.</p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead className="sticky top-0 z-10 bg-background/80 backdrop-blur-md">
              <tr className="border-b border-border font-mono text-[11px] uppercase text-muted-foreground">
                <th className="w-10 px-8 py-4" />
                <th className="px-4 py-4 font-medium">Seri</th>
                <th className="px-4 py-4 font-medium">Başlık</th>
                <th className="px-4 py-4 font-medium">Tip</th>
                <th className="px-4 py-4 font-medium">Dil</th>
                <th className="px-4 py-4 font-medium">Açıklama</th>
                <th className="px-8 py-4 font-medium">Güncelleme</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50 text-sm">
              {docs.map((d, i) => {
                const id = docId(d, i);
                const checked = selectedIds.has(id);
                return (
                  <tr
                    key={id}
                    onClick={() => toggleRow(id)}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent",
                      checked && "border-l-2 border-l-primary bg-accent",
                    )}
                  >
                    <td className="px-8 py-4" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => toggleRow(id)}
                      />
                    </td>
                    <td className="px-4 py-4 font-mono text-xs">
                      {docSeries(d) || "—"}
                    </td>
                    <td className="px-4 py-4 font-medium">{docTitle(d) || "—"}</td>
                    <td className="px-4 py-4 text-muted-foreground">
                      {docType(d) || "—"}
                    </td>
                    <td className="px-4 py-4 font-mono text-xs uppercase text-muted-foreground">
                      {docLang(d) || "—"}
                    </td>
                    <td className="max-w-xs truncate px-4 py-4 text-muted-foreground">
                      {docDesc(d) || "—"}
                    </td>
                    <td className="px-8 py-4 font-mono text-xs text-muted-foreground">
                      {formatDate(docUpdated(d))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <UploadSheet
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        typeOptions={typeOptions}
        seriesOptions={seriesOptions}
        onUploaded={() => {
          queryClient.invalidateQueries({ queryKey: ["documents"] });
        }}
      />
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
  onChange: (v: string) => void;
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
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function UploadSheet({
  open,
  onOpenChange,
  typeOptions,
  seriesOptions,
  onUploaded,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  typeOptions: string[];
  seriesOptions: string[];
  onUploaded: () => void;
}) {
  const { token } = useAuth();
  const [seriesKey, setSeriesKey] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [language, setLanguage] = useState("tr");
  const [file, setFile] = useState<File | null>(null);

  const reset = () => {
    setSeriesKey("");
    setTitle("");
    setDescription("");
    setDocumentType("");
    setLanguage("tr");
    setFile(null);
  };

  const mutation = useMutation({
    mutationFn: () =>
      uploadDocument(
        token!,
        {
          series_key: seriesKey,
          title,
          document_type: documentType,
          language,
          description,
        },
        file!,
      ),
    onSuccess: (res) => {
      toast.success(res.message || "Doküman yüklendi.");
      reset();
      onOpenChange(false);
      onUploaded();
    },
    onError: (err) => toast.error((err as Error).message),
  });

  const submit = () => {
    if (!title.trim()) return toast.error("Başlık zorunludur.");
    if (!documentType.trim()) return toast.error("Doküman tipi zorunludur.");
    if (!file) return toast.error("Lütfen bir PDF dosyası seçin.");
    mutation.mutate();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col gap-0 sm:max-w-md">
        <SheetHeader>
          <SheetTitle>PDF Yükle</SheetTitle>
          <SheetDescription>
            Yeni bir doküman yayınlayın. Başlık, tip ve dosya zorunludur.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 overflow-y-auto px-1 py-4">
          <div className="space-y-1.5">
            <Label>Seri</Label>
            <Input
              list="doc-series-options"
              value={seriesKey}
              onChange={(e) => setSeriesKey(e.target.value)}
              placeholder="Örn. ALVERpro"
            />
            <datalist id="doc-series-options">
              {seriesOptions.map((o) => (
                <option key={o} value={o} />
              ))}
            </datalist>
          </div>
          <div className="space-y-1.5">
            <Label>
              Başlık <span className="text-primary">*</span>
            </Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Doküman başlığı"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Açıklama</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Kısa açıklama"
              rows={3}
            />
          </div>
          <div className="space-y-1.5">
            <Label>
              Doküman Tipi <span className="text-primary">*</span>
            </Label>
            <Input
              list="doc-type-options"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              placeholder="Örn. Kullanım Kılavuzu"
            />
            <datalist id="doc-type-options">
              {typeOptions.map((o) => (
                <option key={o} value={o} />
              ))}
            </datalist>
          </div>
          <div className="space-y-1.5">
            <Label>Doküman Dili</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tr">Türkçe (tr)</SelectItem>
                <SelectItem value="en">İngilizce (en)</SelectItem>
                <SelectItem value="de">Almanca (de)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>
              Seçilen Dosya <span className="text-primary">*</span>
            </Label>
            <label className="flex cursor-pointer items-center gap-3 rounded-md border border-dashed border-border px-4 py-3 text-sm transition-colors hover:bg-accent">
              <FileUp className="size-4 text-muted-foreground" />
              <span className="truncate text-muted-foreground">
                {file ? file.name : "PDF Seç..."}
              </span>
              <input
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </div>

        <SheetFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            İptal
          </Button>
          <Button variant="secondary" onClick={submit} disabled={mutation.isPending}>
            {mutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Upload className="size-4" />
            )}
            PDF Yükle
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
