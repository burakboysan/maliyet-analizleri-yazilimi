import { createFileRoute } from "@tanstack/react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Gauge,
  Loader2,
  Sparkles,
  WandSparkles,
} from "lucide-react";

import { useAuth } from "../lib/auth";
import {
  fetchWizardProducts,
  fetchWizardSchema,
  previewWizard,
  type WizardSchema,
} from "../lib/api";
import { formatCurrency, formatNumber } from "../lib/format";
import { cn } from "../lib/utils";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Skeleton } from "../components/ui/skeleton";

const productImages: Record<string, string> = {};

// Friendly Turkish labels for configuration summary keys returned by the API.
const FIELD_LABELS: Record<string, string> = {
  kapasite: "Kapasite",
  kirlilikTipi: "Kirlilik Tipi",
  filtreMedyasi: "Filtre Medyası",
  filtreBoyu: "Filtre Boyu",
  filtreAdedi: "Filtre Adedi",
  kasa: "Kasa",
  kasaKodu: "Kasa Kodu",
  temizlik: "Temizlik",
  temizlikKodu: "Temizlik Kodu",
  fanTipi: "Fan Tipi",
  fanGucu: "Fan Gücü",
  fanKodu: "Fan Kodu",
  pano: "Pano",
  panoKodu: "Pano Kodu",
  filtreSetKodu: "Filtre Set Kodu",
  motorBilgisi: "Motor Bilgisi",
  articleNo: "Ürün No",
};

// Keys shown separately as engineering info, or that are internal — hidden from the plain summary.
const HIDDEN_SUMMARY_KEYS = new Set([
  "combinationKey",
  "articleKey",
  "panoValue",
  "kesitAlani",
  "toplamFiltreAlani",
  "yukselmeHizi",
  "filtrasyonHizi",
  "milGucu",
  "onerilenMotor",
]);

const humanizeKey = (key: string) =>
  FIELD_LABELS[key] ??
  key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/^./, (c) => c.toUpperCase());

type TechInfoItem = { label: string; display: string };

const ECOG_SECTION_AREAS: Record<string, Record<string, number>> = {
  "660 mm": { "ECOG.3": 0.67, "ECOG.4": 0.67, "ECOG.6": 0.99, "ECOG.8": 1.31 },
  "1.000 mm": { "ECOG.3": 0.998, "ECOG.4": 0.998, "ECOG.6": 1.484, "ECOG.8": 1.969 },
};

const CARTRIDGE_SECTION_AREAS: Record<string, Record<string, number>> = {
  line: {
    "LINE.8": 0.954,
    "LINE.12": 1.334,
    "LINE.18": 1.757,
    "LINE.24": 2.542,
    "LINE.32": 3.493,
    "LINE.36": 4.183,
  },
  pkfc: {
    "PKFC.S4": 0.804,
    "PKFC.S6": 1.336,
    "PKFC.S8": 1.543,
    "PKFC.L6": 1.336,
    "PKFC.L8": 1.543,
    "PKFC.L10": 1.914,
  },
};

const HEXAFIL_TYPE_AREAS: Record<string, number> = {
  "Tip 1": 1.23,
  "Tip 2": 1.69,
  "Tip 2R": 1.6,
  "Tip 2+": 2.15,
  "Tip 3": 2.2,
  "Tip 3+": 2.79,
};

function parseDecimal(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const raw = String(value).trim().replace(/\s/g, "");
  if (!raw) return null;
  let normalized = raw;
  if (raw.includes(",") && raw.includes(".")) {
    normalized =
      raw.lastIndexOf(",") > raw.lastIndexOf(".")
        ? raw.replace(/\./g, "").replace(",", ".")
        : raw.replace(/,/g, "");
  } else if (raw.includes(",")) {
    const right = raw.split(",", 2)[1] ?? "";
    normalized = right.length <= 2 ? raw.replace(",", ".") : raw.replace(/,/g, "");
  } else if (raw.includes(".")) {
    const right = raw.split(".", 2)[1] ?? "";
    normalized = right.length === 3 && /^\d+$/.test(right) ? raw.replace(/\./g, "") : raw;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function cartridgePieceArea(filterMedia: unknown, filterLength: unknown) {
  const media = String(filterMedia ?? "").trim();
  const length = String(filterLength ?? "").trim();
  if (length === "660 mm") return media === "nanoBLEND FR" ? 20 : 10;
  if (length === "1.000 mm") return media === "nanoBLEND FR" ? 30 : 15;
  if (length === "1.200 mm") return 25;
  if (length === "1.320 mm") return 40;
  return null;
}

function selectedOption(
  sections: Record<string, WizardSchema["sections"][string]>,
  field: string,
  value: unknown,
) {
  const selected = String(value ?? "");
  if (!selected) return null;
  for (const sectionList of Object.values(sections)) {
    for (const section of sectionList) {
      if (section.field !== field) continue;
      const option = section.options?.find((opt) => opt.value === selected);
      if (option) return option;
    }
  }
  return null;
}

function deriveLiveMetrics(
  wizardKey: string,
  pstate: Record<string, unknown>,
  sections: Record<string, WizardSchema["sections"][string]>,
) {
  const airflow = parseDecimal(pstate.airflow_text ?? pstate.airflow_value);
  const key = wizardKey.toLowerCase();
  let sectionArea: number | null = null;
  let filterArea: number | null = null;

  const selectedVariant = selectedOption(sections, "filter_variant", pstate.filter_variant);
  if (selectedVariant) {
    sectionArea = parseDecimal(selectedVariant.section_area);
    filterArea = parseDecimal(selectedVariant.filter_area);
    const riseVelocity = parseDecimal(selectedVariant.rise_velocity);
    const filtrationVelocity = parseDecimal(selectedVariant.filtration_velocity);
    if (riseVelocity !== null || filtrationVelocity !== null || sectionArea !== null || filterArea !== null) {
      return { sectionArea, filterArea, riseVelocity, filtrationVelocity };
    }
  }

  const filterLength = String(pstate.filter_length ?? "").trim();
  const filterMedia = String(pstate.filter_media ?? "").trim();

  if (key === "ecog") {
    const variant = String(pstate.filter_variant ?? "").trim();
    const cartridgeCount = parseDecimal(variant.split(".").pop());
    const pieceArea = cartridgePieceArea(filterMedia, filterLength);
    sectionArea = ECOG_SECTION_AREAS[filterLength]?.[variant] ?? null;
    filterArea = pieceArea !== null && cartridgeCount !== null ? pieceArea * cartridgeCount : null;
  } else if (key === "line" || key === "pkfc") {
    const variant = String(pstate.filter_variant ?? "").trim();
    const cartridgeCount = parseDecimal(selectedVariant?.cartridge_count ?? variant.replace(/^.*?(\d+)$/, "$1"));
    const pieceArea = key === "line" ? 5 : cartridgePieceArea(filterMedia, filterLength);
    sectionArea = CARTRIDGE_SECTION_AREAS[key]?.[variant] ?? null;
    filterArea = pieceArea !== null && cartridgeCount !== null ? pieceArea * cartridgeCount : null;
  } else if (key === "hexafil") {
    const caseValue = String(pstate.case ?? "").trim();
    const typeValue = String(pstate.type ?? "").trim();
    const pieceArea = cartridgePieceArea(filterMedia, filterLength);
    sectionArea = caseValue && typeValue ? (HEXAFIL_TYPE_AREAS[typeValue] ?? null) : null;
    filterArea = pieceArea !== null ? pieceArea * 6 : null;
  } else if (key === "verty") {
    const caseValue = String(pstate.case ?? "").trim();
    const pieceArea = cartridgePieceArea(filterMedia, filterLength);
    sectionArea = caseValue ? 0.865 : null;
    filterArea = pieceArea !== null ? pieceArea * 4 : null;
  }

  return {
    sectionArea,
    filterArea,
    riseVelocity: airflow && sectionArea ? airflow / sectionArea / 3600 : null,
    filtrationVelocity: airflow && filterArea ? airflow / filterArea / 60 : null,
  };
}

// Builds the engineering guidance (fan kW recommendation, filtration/rise velocity, etc.)
// from the live preview state and summary, formatting numbers with units.
function buildTechInfo(
  wizardKey: string,
  pstate: Record<string, unknown>,
  summary: Record<string, unknown> | null,
  sections: Record<string, WizardSchema["sections"][string]>,
): TechInfoItem[] {
  const num = (v: unknown): number | null => {
    if (v == null || v === "") return null;
    const n = typeof v === "number" ? v : Number(v);
    return Number.isFinite(n) ? n : null;
  };

  const items: Array<TechInfoItem | null> = [];
  const push = (
    label: string,
    value: unknown,
    opts?: { unit?: string; digits?: number; text?: boolean },
  ) => {
    if (opts?.text) {
      if (value == null || value === "") return;
      items.push({ label, display: String(value) });
      return;
    }
    const n = num(value);
    if (n === null) return;
    const unit = opts?.unit ? ` ${opts.unit}` : "";
    items.push({ label, display: `${formatNumber(n, opts?.digits ?? 2)}${unit}` });
  };

  const liveMetrics = deriveLiveMetrics(wizardKey, pstate, sections);

  push("Önerilen Fan Gücü", pstate.recommended_fan_power, { text: true });
  push("Mil Gücü", summary?.milGucu ?? pstate.shaft_power, { unit: "kW", digits: 2 });
  push("Önerilen Motor", summary?.onerilenMotor ?? pstate.recommended_motor_kw, {
    unit: "kW",
    digits: 1,
  });
  push("Filtrasyon Hızı", liveMetrics.filtrationVelocity ?? summary?.filtrasyonHizi, {
    unit: "m/dk",
    digits: 2,
  });
  push("Yükselme Hızı", liveMetrics.riseVelocity ?? summary?.yukselmeHizi, {
    unit: "m/s",
    digits: 2,
  });
  push("Kesit Alanı", liveMetrics.sectionArea ?? summary?.kesitAlani, { unit: "m²", digits: 3 });
  push("Toplam Filtre Alanı", liveMetrics.filterArea ?? summary?.toplamFiltreAlani, {
    unit: "m²",
    digits: 1,
  });

  return items.filter((i): i is TechInfoItem => i !== null);
}



export const Route = createFileRoute("/_authenticated/selection-wizard")({
  head: () => ({ meta: [{ title: "Seçim Sihirbazı — Bomaksan" }] }),
  component: WizardPage,
});

function WizardPage() {
  const { token } = useAuth();
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const productsQuery = useQuery({
    queryKey: ["wizard-products"],
    queryFn: () => fetchWizardProducts(token!),
    enabled: !!token,
  });

  if (activeKey) {
    return <WizardRunner wizardKey={activeKey} onBack={() => setActiveKey(null)} />;
  }

  const products = productsQuery.data ?? [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="font-display text-lg font-bold tracking-tight">
          Bir konfigürasyon seçin
        </h2>
        <p className="text-sm text-muted-foreground">
          Ürün konfigüratörünü başlatmak için bir kalem seçin.
        </p>
      </div>

      {productsQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <EmptyState
          icon={<WandSparkles className="size-6" />}
          title="Konfigürasyon bulunamadı"
          description="Şu anda kullanılabilir bir ürün sihirbazı yok."
        />
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {products.map((p) => {
            const active = p.status === "active";
            const image = productImages[p.key.toLowerCase()];
            return (
              <button
                key={p.key}
                disabled={!active}
                onClick={() => active && setActiveKey(p.key)}
                className={cn(
                  "group relative flex flex-col overflow-hidden rounded-xl border border-border bg-surface text-left shadow-sm transition-all duration-300",
                  active
                    ? "hover:-translate-y-1 hover:border-primary/40 hover:shadow-xl hover:shadow-primary/5"
                    : "cursor-not-allowed opacity-50",
                )}
              >
                {/* Prominent image stage */}
                <div className="relative flex h-56 w-full items-center justify-center overflow-hidden bg-gradient-to-b from-muted/60 via-background to-background">
                  <div className="pointer-events-none absolute inset-x-8 bottom-6 h-8 rounded-[50%] bg-foreground/10 blur-xl" />
                  {image ? (
                    <img
                      src={image}
                      alt={p.title}
                      className="relative z-10 h-full w-full object-contain p-6 drop-shadow-md transition-transform duration-500 ease-out group-hover:scale-105"
                    />
                  ) : (
                    <WandSparkles className="relative z-10 size-12 text-primary/70" />
                  )}
                  <span
                    className={cn(
                      "absolute right-3 top-3 z-20 rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide backdrop-blur",
                      active
                        ? "bg-primary/15 text-primary"
                        : "bg-secondary/80 text-muted-foreground",
                    )}
                  >
                    {active ? "Aktif" : "Planlanıyor"}
                  </span>
                </div>

                {/* Info footer */}
                <div className="flex flex-1 flex-col border-t border-border px-5 py-4">
                  <h3 className="font-display text-base font-bold tracking-tight">{p.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{p.description}</p>
                  {active && (
                    <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                      Konfigüratörü başlat
                      <ArrowRight className="size-3.5" />
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

      )}
    </div>
  );
}

function WizardRunner({
  wizardKey,
  onBack,
}: {
  wizardKey: string;
  onBack: () => void;
}) {
  const { token } = useAuth();
  const [state, setState] = useState<Record<string, string>>({});
  const [stepIndex, setStepIndex] = useState(0);

  const schemaQuery = useQuery({
    queryKey: ["wizard-schema", wizardKey],
    queryFn: () => fetchWizardSchema(token!, wizardKey),
    enabled: !!token,
  });

  useEffect(() => {
    if (!schemaQuery.data) return;
    const data = schemaQuery.data;
    const init: Record<string, string> = { ...(data.initial_state ?? {}) };
    // Pre-fill empty numeric criteria inputs (debi, basınç, vb.) with their
    // placeholder defaults so the engineering calculation — mil gücü, önerilen
    // motor ve önerilen fan gücü — ile canlı maliyet hemen çalışsın. Aksi halde
    // alanlar boş başlar (placeholder yalnızca görseldir) ve hiçbir öneri/maliyet
    // hesaplanmaz.
    for (const sectionList of Object.values(data.sections ?? {})) {
      for (const section of sectionList) {
        for (const input of section.inputs ?? []) {
          if ((init[input.field] ?? "") === "" && input.placeholder) {
            init[input.field] = input.placeholder;
          }
        }
      }
    }
    setState(init);
  }, [schemaQuery.data]);

  const previewKey = useMemo(() => JSON.stringify(state), [state]);

  const previewQuery = useQuery({
    queryKey: ["wizard-preview", wizardKey, previewKey],
    queryFn: () => previewWizard(token!, wizardKey, state),
    enabled: !!token && Object.keys(state).length > 0,
    // Keep the last successful preview (sections, options, cost) on screen while
    // the next selection is being fetched. Without this, `preview` is undefined
    // during each refetch and the UI falls back to the static schema — whose
    // dynamic option lists (fan/case/cleaning/panel) are empty — so options and
    // costs blink out for 1-2s after every click on the slow live API.
    placeholderData: keepPreviousData,
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
  });

  const schema = schemaQuery.data;
  const preview = previewQuery.data;
  const cost = preview?.cost;
  const sections = preview?.sections ?? schema?.sections ?? {};
  const summary = preview?.summary ?? null;

  // Sync backend-corrected selections (e.g. auto-filled recommended fan power,
  // cleared invalid choices) back into local state so the UI stays in step.
  const previewState = preview?.state as Record<string, unknown> | undefined;
  const liveState = { ...(previewState ?? {}), ...state } as Record<string, unknown>;
  useEffect(() => {
    if (!previewState || !schema) return;
    const keys = Object.keys(schema.initial_state ?? {});
    setState((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const k of keys) {
        const raw = previewState[k];
        const sv = raw == null ? "" : String(raw);
        if ((prev[k] ?? "") !== sv) {
          next[k] = sv;
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [previewState, schema]);

  const techInfo = buildTechInfo(wizardKey, liveState, summary, sections);

  // Backend-derived engineering recommendations, surfaced inline in the steps.
  const recommendedFanPower =
    (liveState.recommended_fan_power as string | null | undefined) ?? null;
  const recommendedMotorKw =
    (liveState.recommended_motor_kw as number | null | undefined) ?? null;
  const shaftPower =
    (liveState.shaft_power as number | null | undefined) ?? null;


  const steps = schema?.steps ?? [];
  const safeIndex = Math.min(stepIndex, Math.max(steps.length - 1, 0));
  const activeStep = steps[safeIndex];
  const activeSections = activeStep ? (sections[activeStep.key] ?? []) : [];
  const isLastStep = safeIndex >= steps.length - 1;
  const isSummaryStep = activeSections.length === 0;

  const setField = (field: string, value: string) =>
    setState((s) => ({ ...s, [field]: value }));

  const goNext = () =>
    setStepIndex((i) => Math.min(i + 1, Math.max(steps.length - 1, 0)));
  const goPrev = () => {
    if (safeIndex === 0) onBack();
    else setStepIndex((i) => Math.max(i - 1, 0));
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ============ Left: focused configuration flow ============ */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-border px-8 py-4">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" /> Ürünler
          </button>
          <h2 className="font-display font-bold tracking-tight">
            {schema?.title ?? "Sihirbaz"}
          </h2>
        </div>

        {/* Progress spine */}
        {steps.length > 0 && (
          <div className="border-b border-border px-8 pb-4 pt-5">
            <div className="flex items-center gap-1.5">
              {steps.map((step, i) => (
                <div
                  key={step.key}
                  className={cn(
                    "h-1.5 flex-1 rounded-full transition-colors duration-300",
                    i < safeIndex
                      ? "bg-primary/50"
                      : i === safeIndex
                        ? "bg-primary"
                        : "bg-muted",
                  )}
                />
              ))}
            </div>
            <div className="mt-2.5 flex justify-between gap-2">
              {steps.map((step, i) => (
                <span
                  key={step.key}
                  className={cn(
                    "truncate font-mono text-[10px] uppercase tracking-wider transition-colors",
                    i === safeIndex
                      ? "font-semibold text-primary"
                      : i < safeIndex
                        ? "text-foreground"
                        : "text-muted-foreground",
                  )}
                >
                  {step.title}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Active step */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {schemaQuery.isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : (
            <div key={safeIndex} className="animate-fade-in mx-auto max-w-2xl">
              <div className="mb-8">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-full bg-primary font-mono text-[11px] font-bold text-primary-foreground">
                    {safeIndex + 1}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Adım {safeIndex + 1} / {steps.length}
                  </span>
                </div>
                <h3 className="font-display text-2xl font-bold tracking-tight">
                  {activeStep?.title ?? "Özet"}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {isSummaryStep
                    ? "Yapılandırmanızı gözden geçirin ve tamamlayın."
                    : "Bu adım için seçimlerinizi yapın."}
                </p>
              </div>

              {isSummaryStep ? (
                <SummaryReview summary={summary} cost={cost} techInfo={techInfo} />
              ) : (
                <WizardStepBlock
                  sections={activeSections}
                  state={state}
                  onChange={setField}
                  recommendedFanPower={recommendedFanPower}
                  recommendedMotorKw={recommendedMotorKw}
                  shaftPower={shaftPower}
                  isFetching={previewQuery.isFetching}
                />
              )}
            </div>
          )}
        </div>

        {/* Footer nav */}
        <div className="flex items-center justify-between gap-3 border-t border-border bg-surface px-8 py-4">
          <button
            onClick={goPrev}
            className="flex items-center gap-1.5 rounded-lg border border-border px-5 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            {safeIndex === 0 ? "Vazgeç" : "Geri"}
          </button>
          {isLastStep ? (
            <button
              onClick={onBack}
              className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              <CheckCircle2 className="size-4" />
              Konfigürasyonu Tamamla
            </button>
          ) : (
            <button
              onClick={goNext}
              className="flex items-center gap-2 rounded-lg bg-foreground px-6 py-2.5 text-sm font-semibold text-background transition-colors hover:bg-foreground/90"
            >
              Sonraki Adım
              <ArrowRight className="size-4" />
            </button>
          )}
        </div>
      </div>

      {/* ============ Right: live cost console ============ */}
      <div className="flex w-96 shrink-0 flex-col overflow-y-auto bg-console p-8 text-console-foreground">
        <h3 className="mb-5 font-mono text-[10px] font-bold uppercase tracking-widest text-console-muted">
          Canlı Maliyet
        </h3>

        <div className="mb-1 flex items-center gap-2 text-sm text-console-muted">
          <span>Toplam Tahmini Maliyet</span>
          {!previewQuery.isPending && previewQuery.isFetching && (
            <span className="inline-flex items-center gap-1 rounded-full bg-console-surface px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-console-muted">
              <Loader2 className="size-3 animate-spin" />
              Maliyet hesaplanıyor
            </span>
          )}
        </div>
        {previewQuery.isPending ? (
          <Skeleton className="h-10 w-40 bg-console-surface" />
        ) : (
          <div
            className={cn(
              "font-display text-4xl font-bold tracking-tight text-console-foreground transition-opacity",
              previewQuery.isFetching && "opacity-50",
            )}
          >
            {formatCurrency(cost?.total_cost)}
          </div>
        )}
        {cost?.is_partial && (
          <div className="mt-2 rounded-full border border-console-border bg-console-surface px-3 py-1 text-center font-mono text-[10px] uppercase tracking-wide text-console-muted">
            Seçili maliyet kalemleri toplamı
          </div>
        )}
        <div className="mt-5 h-1 w-full overflow-hidden rounded-full bg-console-surface">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{
              width: `${steps.length > 1 ? ((safeIndex + 1) / steps.length) * 100 : 100}%`,
            }}
          />
        </div>

        <div className="mt-8 flex-1 space-y-8">
          {/* Engineering guidance: fan kW recommendation, velocities, motor */}
          {techInfo.length > 0 && (
            <div className="rounded-2xl border border-primary/30 bg-primary/10 p-4">
              <h4 className="mb-3 font-mono text-[10px] font-bold uppercase tracking-widest text-primary">
                Teknik Bilgiler
              </h4>
              <dl className="space-y-2.5">
                {techInfo.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between gap-3 text-sm"
                  >
                    <dt className="truncate text-console-muted">{item.label}</dt>
                    <dd className="shrink-0 text-right font-mono font-semibold text-console-foreground">
                      {item.display}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {/* Configuration summary */}
          {summary &&
            Object.keys(summary).some((k) => !HIDDEN_SUMMARY_KEYS.has(k)) && (
              <div>
                <h4 className="mb-4 font-mono text-[10px] font-bold uppercase tracking-widest text-console-muted">
                  Yapılandırma Özeti
                </h4>
                <dl className="space-y-2.5">
                  {Object.entries(summary)
                    .filter(([key]) => !HIDDEN_SUMMARY_KEYS.has(key))
                    .map(([key, value]) => {
                      const empty = value == null || value === "";
                      return (
                        <div
                          key={key}
                          className="flex items-center justify-between gap-3 text-sm"
                        >
                          <dt className="truncate text-console-muted">
                            {humanizeKey(key)}
                          </dt>
                          <dd
                            className={cn(
                              "shrink-0 text-right font-medium",
                              empty
                                ? "italic text-console-muted/60"
                                : "text-console-foreground",
                            )}
                          >
                            {empty ? "Seçilmedi" : String(value)}
                          </dd>
                        </div>
                      );
                    })}
                </dl>
              </div>
            )}


          {/* Status counters */}
          {cost && (
            <div className="grid grid-cols-3 gap-2">
              <ConsoleCounter
                count={cost.found_codes.length}
                label="Bulundu"
                tone="ok"
              />
              <ConsoleCounter
                count={cost.zero_cost_codes.length}
                label="Sıfır"
                tone="warn"
              />
              <ConsoleCounter
                count={cost.missing_codes.length}
                label="Eksik"
                tone="error"
              />
            </div>
          )}

          {cost && cost.missing_codes.length > 0 && (
            <div className="rounded-xl border border-destructive/40 bg-destructive/15 p-3 text-xs text-red-300">
              <div className="mb-1 font-medium">Eksik maliyet kodları</div>
              <div className="font-mono leading-relaxed">
                {cost.missing_codes.join(", ")}
              </div>
            </div>
          )}

          {/* Cost breakdown */}
          {cost && Object.keys(cost.costs).length > 0 ? (
            <div className="rounded-2xl bg-console-surface/60 p-4">
              <h4 className="mb-3 text-center font-mono text-[10px] font-bold uppercase tracking-widest text-console-muted">
                {cost.is_partial ? "Canlı Maliyet Kalemleri" : "Maliyet Kalemleri"}
              </h4>
              <div className="space-y-2.5">
                {Object.entries(cost.costs).map(([code, value]) => {
                  const isZero = cost.zero_cost_codes.includes(code);
                  const isMissing = cost.missing_codes.includes(code);
                  return (
                    <div
                      key={code}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <span
                          className={cn(
                            "size-1.5 shrink-0 rounded-full",
                            isMissing
                              ? "bg-destructive"
                              : isZero
                                ? "bg-amber-400"
                                : "bg-emerald-400",
                          )}
                        />
                        <span className="truncate font-mono text-console-muted">
                          {code}
                        </span>
                      </span>
                      <span className="shrink-0 font-mono font-bold text-console-foreground">
                        {formatCurrency(value)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            !previewQuery.isFetching && (
              <p className="rounded-xl border border-dashed border-console-border p-3 text-center text-xs text-console-muted">
                Maliyet kalemlerini görmek için seçim yapın.
              </p>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryReview({
  summary,
  cost,
  techInfo,
}: {
  summary: Record<string, unknown> | null;
  cost: { total_cost?: number | null } | undefined;
  techInfo: TechInfoItem[];
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-6">
        <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Toplam Maliyet
        </div>
        <div className="mt-1 font-display text-3xl font-bold text-primary">
          {formatCurrency(cost?.total_cost)}
        </div>
      </div>

      {techInfo.length > 0 && (
        <div>
          <h4 className="mb-3 font-mono text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Teknik Bilgiler
          </h4>
          <dl className="grid grid-cols-2 gap-3">
            {techInfo.map((item) => (
              <div
                key={item.label}
                className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3"
              >
                <dt className="text-xs text-muted-foreground">{item.label}</dt>
                <dd className="mt-0.5 font-mono text-sm font-semibold text-foreground">
                  {item.display}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {summary &&
        Object.keys(summary).some((k) => !HIDDEN_SUMMARY_KEYS.has(k)) && (
          <dl className="divide-y divide-border rounded-2xl border border-border bg-surface">
            {Object.entries(summary)
              .filter(([key]) => !HIDDEN_SUMMARY_KEYS.has(key))
              .map(([key, value]) => {
                const empty = value == null || value === "";
                return (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-3 px-5 py-3 text-sm"
                  >
                    <dt className="truncate text-muted-foreground">
                      {humanizeKey(key)}
                    </dt>
                    <dd className="shrink-0 text-right font-medium">
                      {empty ? "—" : String(value)}
                    </dd>
                  </div>
                );
              })}
          </dl>
        )}
    </div>
  );
}


function ConsoleCounter({
  count,
  label,
  tone,
}: {
  count: number;
  label: string;
  tone: "ok" | "warn" | "error";
}) {
  const toneClass =
    tone === "ok"
      ? "text-emerald-400"
      : tone === "warn"
        ? "text-amber-400"
        : "text-red-400";
  return (
    <div className="flex flex-col items-center gap-0.5 rounded-xl border border-console-border bg-console-surface p-3 text-center">
      <span className={cn("font-mono text-lg font-bold", toneClass)}>{count}</span>
      <span className="font-mono text-[9px] uppercase tracking-wide text-console-muted">
        {label}
      </span>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface px-6 py-16 text-center">
      <div className="mb-3 flex size-12 items-center justify-center rounded-full border border-border bg-background text-muted-foreground">
        {icon}
      </div>
      <h3 className="font-display font-bold">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function WizardStepBlock({
  sections,
  state,
  onChange,
  recommendedFanPower,
  recommendedMotorKw,
  shaftPower,
  isFetching,
}: {
  sections: WizardSchema["sections"][string];
  state: Record<string, string>;
  onChange: (field: string, value: string) => void;
  recommendedFanPower?: string | null;
  recommendedMotorKw?: number | null;
  shaftPower?: number | null;
  isFetching?: boolean;
}) {
  if (sections.length === 0) return null;
  return (
    <div className="space-y-8">
      {sections.map((section, i) => {
        const isCriteriaInputs = !!section.inputs && section.inputs.length > 0;
        return (
          <div key={`${section.field}-${i}`}>
            <Label className="mb-3 block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {section.title}
            </Label>
            {section.field === "fan_power" && recommendedFanPower && (
              <p className="-mt-1.5 mb-3 flex items-center gap-1.5 text-xs text-primary">
                <Sparkles className="size-3.5 shrink-0" />
                Debi ve basınca göre hesaplanan önerilen fan gücü{" "}
                <strong className="font-semibold">{recommendedFanPower}</strong>{" "}
                olarak işaretlendi.
              </p>
            )}
            {section.options && section.options.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {section.options.map((opt, optIndex) => {
                  const selected = state[section.field] === opt.value;
                  const isRecommended =
                    section.field === "fan_power" &&
                    !!recommendedFanPower &&
                    opt.label === recommendedFanPower;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => onChange(section.field, opt.value)}
                      style={{ animationDelay: `${Math.min(optIndex * 25, 200)}ms` }}
                      className={cn(
                        "group relative flex animate-fade-in flex-col rounded-2xl border-2 p-5 text-left transition-all",
                        selected
                          ? "border-primary bg-primary/5 shadow-sm"
                          : isRecommended
                            ? "border-primary/40 bg-primary/[0.03] hover:border-primary/60 hover:shadow-sm"
                            : "border-border bg-surface hover:border-muted-foreground/30 hover:shadow-sm",
                      )}
                    >
                      {selected && (
                        <span className="absolute right-4 top-4 flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                          <Check className="size-4" />
                        </span>
                      )}
                      <span className="flex items-center gap-2 pr-8">
                        <span className="font-display text-lg font-bold tracking-tight text-foreground">
                          {opt.label}
                        </span>
                        {isRecommended && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wide text-primary-foreground">
                            <Sparkles className="size-2.5" />
                            Önerilen
                          </span>
                        )}
                      </span>
                      {opt.description && (
                        <span className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                          {opt.description}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ) : section.inputs && section.inputs.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {section.inputs.map((input) => (
                  <div key={input.field}>
                    <Label className="mb-1.5 block text-xs text-muted-foreground">
                      {input.label}
                    </Label>
                    <Input
                      value={state[input.field] ?? ""}
                      placeholder={input.placeholder}
                      onChange={(e) => onChange(input.field, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            ) : null}

            {/* Motor recommendation: appears once criteria (debi, basınç, fan
                verimi, servis payı) yield a backend kW suggestion. */}
            {isCriteriaInputs && (recommendedMotorKw != null || shaftPower != null) && (
              <div
                className={cn(
                  "mt-5 rounded-2xl border-2 border-primary/30 bg-primary/5 p-5 transition-opacity",
                  isFetching && "opacity-60",
                )}
              >
                <div className="flex items-center gap-2">
                  <Gauge className="size-4 text-primary" />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-primary">
                    Fan Gücü Hesabı
                  </span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                  Girilen debi, basınç, fan verimi ve servis payına göre
                  hesaplanan değerlerdir. Önerilen motor gücü bir sonraki adımda
                  fan seçiminde işaretlenir.
                </p>
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-primary/20 bg-background/60 px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                      Mil Gücü
                    </div>
                    <div className="mt-0.5 font-mono text-lg font-semibold text-foreground">
                      {shaftPower != null ? `${formatNumber(shaftPower, 2)} kW` : "—"}
                    </div>
                  </div>
                  <div className="rounded-xl border border-primary/20 bg-background/60 px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                      Önerilen Motor
                    </div>
                    <div className="mt-0.5 font-display text-lg font-bold tracking-tight text-foreground">
                      {recommendedMotorKw != null
                        ? `${formatNumber(recommendedMotorKw, 1)} kW`
                        : "—"}
                    </div>
                  </div>
                  <div className="rounded-xl border-2 border-primary/40 bg-primary/10 px-4 py-3">
                    <div className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-widest text-primary">
                      <Sparkles className="size-2.5" />
                      Önerilen Fan
                    </div>
                    <div className="mt-0.5 font-display text-lg font-bold tracking-tight text-primary">
                      {recommendedFanPower ?? "—"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
