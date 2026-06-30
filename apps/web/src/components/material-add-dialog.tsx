import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../lib/auth";
import {
  createMaterial,
  fetchMaterialAddOptions,
  type MaterialCreatePayload,
} from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

const MATERIAL_TYPES = ["Yarı Mamül", "Mamül", "Proje Mamül"] as const;

export function MaterialAddDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [type, setType] = useState<string>("Mamül");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [fixedItem, setFixedItem] = useState("");

  const optionsQuery = useQuery({
    queryKey: ["material-add-options"],
    queryFn: () => fetchMaterialAddOptions(token!),
    enabled: !!token && open,
  });

  const isYariMamul = type === "Yarı Mamül";
  const fixedCostItems = optionsQuery.data?.fixed_cost_items ?? [];

  // Reset fields when dialog opens
  useEffect(() => {
    if (open) {
      setType("Mamül");
      setCode("");
      setName("");
      setPrice("");
      setFixedItem("");
    }
  }, [open]);

  // For Yarı Mamül, code comes from next_yari_mamul_code
  useEffect(() => {
    if (isYariMamul && optionsQuery.data) {
      setCode(optionsQuery.data.next_yari_mamul_code ?? "");
    } else if (!isYariMamul) {
      setCode((prev) => (prev === optionsQuery.data?.next_yari_mamul_code ? "" : prev));
    }
  }, [isYariMamul, optionsQuery.data]);

  // For Yarı Mamül, name/price come from selected fixed cost item
  useEffect(() => {
    if (!isYariMamul || !fixedItem) return;
    const found = fixedCostItems.find((i) => i.kalem_adi === fixedItem);
    if (found) {
      setName(found.kalem_adi);
      setPrice(found.birim_fiyat != null ? String(found.birim_fiyat) : "");
    }
  }, [fixedItem, isYariMamul, fixedCostItems]);

  const createMutation = useMutation({
    mutationFn: (payload: MaterialCreatePayload) => createMaterial(token!, payload),
    onSuccess: () => {
      toast.success("Malzeme eklendi.");
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      queryClient.invalidateQueries({ queryKey: ["materials-cost-version"] });
      queryClient.invalidateQueries({ queryKey: ["material-add-options"] });
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Malzeme eklenemedi.");
    },
  });

  const canSubmit = useMemo(() => {
    if (!code.trim() || !name.trim()) return false;
    if (isYariMamul && !fixedItem) return false;
    return true;
  }, [code, name, isYariMamul, fixedItem]);

  const handleSubmit = () => {
    createMutation.mutate({
      malzeme_kodu: code.trim(),
      malzeme_tipi: type,
      ad: name.trim(),
      birim_fiyat: price === "" ? 0 : price,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-surface sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display">Malzeme Ekle</DialogTitle>
          <DialogDescription>
            Yeni bir malzeme kaydı oluşturun.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Tip</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger>
                <SelectValue placeholder="Tip seçin" />
              </SelectTrigger>
              <SelectContent>
                {MATERIAL_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {isYariMamul && (
            <>
              <div className="flex items-start gap-2 rounded-md border border-primary/30 bg-primary/10 p-3 text-xs text-foreground">
                <Info className="mt-0.5 size-4 shrink-0 text-primary" />
                <span>
                  Yarı Mamül için kod otomatik atanır; ad ve fiyat seçilen sabit
                  maliyet kaleminden gelir.
                </span>
              </div>
              <div className="space-y-2">
                <Label>Sabit Maliyet Kalemi</Label>
                <Select value={fixedItem} onValueChange={setFixedItem}>
                  <SelectTrigger>
                    <SelectValue placeholder="Kalem seçin" />
                  </SelectTrigger>
                  <SelectContent>
                    {fixedCostItems.map((i) => (
                      <SelectItem key={i.kalem_adi} value={i.kalem_adi}>
                        {i.kalem_adi}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label>Malzeme Kodu</Label>
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={isYariMamul}
              placeholder="Örn. MML-0001"
              className="font-mono"
            />
          </div>

          <div className="space-y-2">
            <Label>Ad</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isYariMamul}
              placeholder="Malzeme adı"
            />
          </div>

          <div className="space-y-2">
            <Label>Birim Fiyat (EUR)</Label>
            <Input
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={isYariMamul}
              inputMode="decimal"
              placeholder="0,00"
              className="font-mono"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            İptal
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || createMutation.isPending}>
            {createMutation.isPending && (
              <Loader2 className="size-4 animate-spin" />
            )}
            Kaydet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
