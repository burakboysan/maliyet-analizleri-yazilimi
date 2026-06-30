import { useMemo } from "react";
import { Check, Filter, X } from "lucide-react";

import type { ProductInfo } from "../lib/api";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./ui/command";

// ---- Field configuration --------------------------------------------------

type CategoricalKey =
  | "urun_kategorisi"
  | "urun_tipi"
  | "urun_modeli"
  | "filtre_medyasi"
  | "motor"
  | "patlac_kumanda_tipi"
  | "fan_kumanda_tipi"
  | "patlama_kapagi";

type NumericKey =
  | "maliyet"
  | "debi"
  | "fan_basinc"
  | "toplam_filtre_alani"
  | "filtre_elemani_sayisi";

const CATEGORICAL_FIELDS: { key: CategoricalKey; label: string }[] = [
  { key: "urun_kategorisi", label: "Kategori" },
  { key: "urun_tipi", label: "Tip" },
  { key: "urun_modeli", label: "Model" },
  { key: "filtre_medyasi", label: "Filtre Medyası" },
  { key: "motor", label: "Motor" },
  { key: "patlac_kumanda_tipi", label: "Patlaç Kumanda" },
  { key: "fan_kumanda_tipi", label: "Fan Kumanda" },
  { key: "patlama_kapagi", label: "Patlama Kapağı" },
];

const NUMERIC_FIELDS: { key: NumericKey; label: string }[] = [
  { key: "maliyet", label: "Maliyet (€)" },
  { key: "debi", label: "Debi" },
  { key: "fan_basinc", label: "Fan Basınç" },
  { key: "toplam_filtre_alani", label: "Filtre Alanı" },
  { key: "filtre_elemani_sayisi", label: "Eleman Sayısı" },
];

// ---- Filter state ---------------------------------------------------------

export type ProductFilterState = {
  categorical: Partial<Record<CategoricalKey, string[]>>;
  numeric: Partial<Record<NumericKey, { min?: number; max?: number }>>;
};

export const EMPTY_FILTERS: ProductFilterState = {
  categorical: {},
  numeric: {},
};

function toNumber(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const cleaned = String(value).replace(/[^0-9.,-]/g, "").replace(",", ".");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function countActiveFilters(state: ProductFilterState): number {
  let count = 0;
  for (const key of Object.keys(state.categorical) as CategoricalKey[]) {
    if ((state.categorical[key]?.length ?? 0) > 0) count += 1;
  }
  for (const key of Object.keys(state.numeric) as NumericKey[]) {
    const r = state.numeric[key];
    if (r && (r.min != null || r.max != null)) count += 1;
  }
  return count;
}

export function applyProductFilters(
  products: ProductInfo[],
  state: ProductFilterState,
): ProductInfo[] {
  const catEntries = (Object.keys(state.categorical) as CategoricalKey[])
    .map((key) => [key, state.categorical[key]] as const)
    .filter(([, values]) => (values?.length ?? 0) > 0);
  const numEntries = (Object.keys(state.numeric) as NumericKey[])
    .map((key) => [key, state.numeric[key]] as const)
    .filter(([, r]) => r && (r.min != null || r.max != null));

  if (catEntries.length === 0 && numEntries.length === 0) return products;

  return products.filter((p) => {
    for (const [key, values] of catEntries) {
      const raw = (p[key] ?? "").toString();
      if (!values!.includes(raw)) return false;
    }
    for (const [key, r] of numEntries) {
      const n = toNumber(p[key]);
      if (n == null) return false;
      if (r!.min != null && n < r!.min) return false;
      if (r!.max != null && n > r!.max) return false;
    }
    return true;
  });
}

// ---- UI -------------------------------------------------------------------

function CategoricalFacet({
  field,
  options,
  selected,
  onChange,
}: {
  field: { key: CategoricalKey; label: string };
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
}) {
  const toggle = (value: string) => {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value],
    );
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "h-8 gap-1.5",
            selected.length > 0 && "border-primary/50 text-primary",
          )}
        >
          {field.label}
          {selected.length > 0 && (
            <Badge
              variant="secondary"
              className="ml-0.5 h-4 rounded px-1 font-mono text-[10px]"
            >
              {selected.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-60 p-0" align="start">
        <Command>
          <CommandInput placeholder={`${field.label} ara...`} className="h-9" />
          <CommandList>
            <CommandEmpty>Sonuç yok.</CommandEmpty>
            <CommandGroup>
              {options.map((opt) => {
                const isSel = selected.includes(opt);
                return (
                  <CommandItem
                    key={opt}
                    value={opt}
                    onSelect={() => toggle(opt)}
                    className="gap-2"
                  >
                    <div
                      className={cn(
                        "flex size-4 items-center justify-center rounded border border-primary/40",
                        isSel
                          ? "bg-primary text-primary-foreground"
                          : "opacity-60",
                      )}
                    >
                      {isSel && <Check className="size-3" />}
                    </div>
                    <span className="truncate">{opt}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function NumericFacet({
  field,
  range,
  onChange,
}: {
  field: { key: NumericKey; label: string };
  range: { min?: number; max?: number };
  onChange: (range: { min?: number; max?: number }) => void;
}) {
  const active = range.min != null || range.max != null;
  const parse = (v: string) => {
    const n = Number(v);
    return v.trim() === "" || !Number.isFinite(n) ? undefined : n;
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "h-8 gap-1.5",
            active && "border-primary/50 text-primary",
          )}
        >
          {field.label}
          {active && (
            <Badge
              variant="secondary"
              className="ml-0.5 h-4 rounded px-1 font-mono text-[10px]"
            >
              {range.min ?? "–"}…{range.max ?? "–"}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 space-y-3 p-3" align="start">
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">En az</Label>
          <Input
            type="number"
            inputMode="decimal"
            value={range.min ?? ""}
            onChange={(e) =>
              onChange({ ...range, min: parse(e.target.value) })
            }
            placeholder="min"
            className="h-8"
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">En çok</Label>
          <Input
            type="number"
            inputMode="decimal"
            value={range.max ?? ""}
            onChange={(e) =>
              onChange({ ...range, max: parse(e.target.value) })
            }
            placeholder="max"
            className="h-8"
          />
        </div>
        {active && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-full text-xs"
            onClick={() => onChange({})}
          >
            Temizle
          </Button>
        )}
      </PopoverContent>
    </Popover>
  );
}

export function ProductFilterBar({
  products,
  value,
  onChange,
}: {
  products: ProductInfo[];
  value: ProductFilterState;
  onChange: (next: ProductFilterState) => void;
}) {
  // Derive distinct, sorted option lists for each categorical field from the
  // actual data so facets always reflect what's in the catalog.
  const facetOptions = useMemo(() => {
    const sets: Record<string, Set<string>> = {};
    for (const f of CATEGORICAL_FIELDS) sets[f.key] = new Set();
    for (const p of products) {
      for (const f of CATEGORICAL_FIELDS) {
        const v = (p[f.key] ?? "").toString().trim();
        if (v) sets[f.key].add(v);
      }
    }
    const out: Record<string, string[]> = {};
    for (const f of CATEGORICAL_FIELDS) {
      out[f.key] = Array.from(sets[f.key]).sort((a, b) =>
        a.localeCompare(b, "tr"),
      );
    }
    return out;
  }, [products]);

  const activeCount = countActiveFilters(value);

  const setCategorical = (key: CategoricalKey, values: string[]) => {
    onChange({
      ...value,
      categorical: { ...value.categorical, [key]: values },
    });
  };
  const setNumeric = (key: NumericKey, range: { min?: number; max?: number }) => {
    onChange({ ...value, numeric: { ...value.numeric, [key]: range } });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Filter className="size-3.5" />
        Filtrele
      </span>
      {CATEGORICAL_FIELDS.filter((f) => facetOptions[f.key]?.length > 0).map(
        (f) => (
          <CategoricalFacet
            key={f.key}
            field={f}
            options={facetOptions[f.key]}
            selected={value.categorical[f.key] ?? []}
            onChange={(values) => setCategorical(f.key, values)}
          />
        ),
      )}
      {NUMERIC_FIELDS.map((f) => (
        <NumericFacet
          key={f.key}
          field={f}
          range={value.numeric[f.key] ?? {}}
          onChange={(range) => setNumeric(f.key, range)}
        />
      ))}
      {activeCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1 text-xs text-muted-foreground"
          onClick={() => onChange(EMPTY_FILTERS)}
        >
          <X className="size-3.5" />
          Temizle ({activeCount})
        </Button>
      )}
    </div>
  );
}
