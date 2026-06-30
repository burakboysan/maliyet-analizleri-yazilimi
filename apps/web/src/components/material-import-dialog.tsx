import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp, Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import { importMamulMaterials, type MaterialImportResponse } from "../lib/api";
import { Button } from "./ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  inserted: { label: "Eklendi", className: "text-emerald-400" },
  existing: { label: "Mevcut", className: "text-amber-400" },
  failed: { label: "Hata", className: "text-destructive" },
};

function downloadTemplate() {
  const content = "malzeme_kodu;ad;birim_fiyat\nMML-0001;Örnek Mamül;100,00\n";
  const blob = new Blob(["\uFEFF" + content], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "mamul_ice_aktar_sablonu.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export function MaterialImportDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<MaterialImportResponse | null>(null);

  const importMutation = useMutation({
    mutationFn: (f: File) => importMamulMaterials(token!, f),
    onSuccess: (res) => {
      setResult(res);
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      queryClient.invalidateQueries({ queryKey: ["materials-cost-version"] });
      toast.success(
        `İçe aktarma tamamlandı: ${res.inserted_count} eklendi, ${res.existing_count} mevcut, ${res.failed_count} hata.`,
      );
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "İçe aktarma başarısız.");
    },
  });

  const handleClose = (o: boolean) => {
    if (!o) {
      setFile(null);
      setResult(null);
    }
    onOpenChange(o);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="border-border bg-surface sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-display">Mamül İçe Aktar</DialogTitle>
          <DialogDescription>
            Excel dosyasından toplu mamül malzeme aktarın.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
              }}
            />
            <Button variant="outline" onClick={() => inputRef.current?.click()}>
              <FileUp className="size-4" />
              Dosya Seç
            </Button>
            <Button variant="outline" onClick={downloadTemplate}>
              <Download className="size-4" />
              Şablon İndir
            </Button>
            <span className="truncate text-sm text-muted-foreground">
              {file ? file.name : "Dosya seçilmedi"}
            </span>
          </div>

          {result && (
            <div className="overflow-hidden rounded-md border border-border">
              <div className="grid grid-cols-4 gap-2 border-b border-border bg-background px-4 py-2 text-center font-mono text-[11px] uppercase text-muted-foreground">
                <span>Toplam {result.total_count}</span>
                <span className="text-emerald-400">Eklendi {result.inserted_count}</span>
                <span className="text-amber-400">Mevcut {result.existing_count}</span>
                <span className="text-destructive">Hata {result.failed_count}</span>
              </div>
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-surface font-mono text-[11px] uppercase text-muted-foreground">
                    <tr className="border-b border-border">
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-medium">Kod</th>
                      <th className="px-3 py-2 font-medium">Ad</th>
                      <th className="px-3 py-2 font-medium">Durum</th>
                      <th className="px-3 py-2 font-medium">Mesaj</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {result.items.map((item, i) => {
                      const status = STATUS_LABELS[item.status] ?? {
                        label: item.status,
                        className: "text-muted-foreground",
                      };
                      return (
                        <tr key={i}>
                          <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                            {item.row_number}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">
                            {item.malzeme_kodu ?? "—"}
                          </td>
                          <td className="px-3 py-2">{item.ad ?? "—"}</td>
                          <td className={`px-3 py-2 font-medium ${status.className}`}>
                            {status.label}
                          </td>
                          <td className="px-3 py-2 text-xs text-muted-foreground">
                            {item.message}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            Kapat
          </Button>
          <Button
            onClick={() => file && importMutation.mutate(file)}
            disabled={!file || importMutation.isPending}
          >
            {importMutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Upload className="size-4" />
            )}
            İçe Aktar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
