import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Calculator,
  Flame,
  Gauge,
  PanelTop,
  Scissors,
  Wind,
  Zap,
  FileDown,
  Plus,
  Trash2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import {
  airDensity,
  CNC_DEFAULT_VISCOSITY,
  CNC_DOOR_ADJUSTMENT,
  CNC_HEPA_PRODUCTS,
  CNC_STANDARD_PRODUCTS,
  DEFAULT_ENERGY_PER_NM3,
  downloadCsv,
  DRIVE_TYPES,
  EXPLOSION_PANEL_AREAS,
  EXPLOSION_ST_CLASSES,
  exportRowsToPdf,
  formatNumber,
  HOOD_CAPTURE_OPTIONS,
  HOOD_TYPE_FACTORS,
  parseNumber,
  PRESSURE_CONSTANTS,
  selectMotor,
  STANDARD_AIR_DENSITY,
  THERMAL_CUTTING_POWER_OPTIONS,
  VALVE_TIGHTNESS_OPTIONS,
  VFD_OPTIONS,
  WELDING_FUME_FACTORS,
  type CapacityToolKey,
  type TechnicalToolKey,
} from "../../lib/technical-calc";

const inputClass =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-ring";
const selectClass = cn(inputClass, "cursor-pointer appearance-none pr-8");

const TOOLS: Array<{
  key: TechnicalToolKey;
  title: string;
  short: string;
  description: string;
  icon: LucideIcon;
}> = [
  {
    key: "fan",
    title: "Fan Motor Modülü",
    short: "Fan Motor",
    description: "Debi, basınç, yoğunluk, mil gücü ve nominal motor seçimi.",
    icon: Zap,
  },
  {
    key: "pressure-loss",
    title: "Basınç Kaybı Modülü",
    short: "Basınç Kaybı",
    description:
      "Dirsek, düz kanal, Jet-Cap ve ekipman kayıplarını listeleyerek toplam basınç kaybı.",
    icon: Wind,
  },
  {
    key: "capacity",
    title: "Kapasite Hesap Modülü",
    short: "Kapasite",
    description:
      "Isıl kesim, CNC torna, davlumbaz ve kaynak holü kapasite hesapları.",
    icon: Calculator,
  },
  {
    key: "compressed-air",
    title: "Basınçlı Hava Tüketim Modülü",
    short: "Basınçlı Hava",
    description: "Patlaç tipi, darbe aralığı ve çalışma basıncıyla enerji tüketimi.",
    icon: Flame,
  },
  {
    key: "explosion-vent",
    title: "Patlama Kapağı Modülü",
    short: "Patlama Kapağı",
    description:
      "ST sınıfı, net hacim ve panel alanına göre kapak alanı ve adet hesabı.",
    icon: PanelTop,
  },
];

export function TechnicalCalculations() {
  const [tool, setTool] = useState<TechnicalToolKey>("fan");
  const current = TOOLS.find((t) => t.key === tool)!;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Modül seçim çubuğu */}
      <div className="shrink-0 border-b border-border px-4 py-3 sm:px-8">
        <div className="flex flex-wrap gap-2">
          {TOOLS.map((t) => {
            const Icon = t.icon;
            const active = t.key === tool;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTool(t.key)}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium transition-colors sm:text-sm",
                  active
                    ? "border-border bg-sidebar-accent text-foreground"
                    : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
                )}
              >
                <Icon
                  className={cn("size-4 shrink-0", active && "text-primary")}
                />
                <span className="whitespace-nowrap">{t.short}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
          <header className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="font-display text-xl font-bold tracking-tight sm:text-2xl">
                {current.title}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {current.description}
              </p>
            </div>
            <div className="hidden size-12 shrink-0 place-items-center rounded-lg border border-border bg-surface text-primary sm:grid">
              <current.icon className="size-6" />
            </div>
          </header>

          {tool === "fan" && <FanPowerCalculator />}
          {tool === "pressure-loss" && <PressureLossCalculator />}
          {tool === "capacity" && <CapacityCalculatorScreen />}
          {tool === "compressed-air" && <CompressedAirCalculator />}
          {tool === "explosion-vent" && <ExplosionVentCalculator />}
        </div>
      </div>
    </div>
  );
}

/* ----------------------------- Ortak parçalar ----------------------------- */

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function Panel({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-5 py-4">
        <h2 className="font-display font-bold tracking-tight">{title}</h2>
        {description && (
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function SubHeading({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="mb-3">
      <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {title}
      </span>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ResultRow({
  index,
  label,
  value,
  strong = false,
}: {
  index?: number;
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 border-b border-border/60 py-2 text-sm last:border-0",
        strong && "font-bold",
      )}
    >
      <span className={cn("min-w-0", strong ? "text-foreground" : "text-muted-foreground")}>
        {index != null && <span className="mr-1 text-muted-foreground">{index}.</span>}
        {label}
      </span>
      <strong
        className={cn(
          "shrink-0 font-mono",
          strong ? "text-base text-primary" : "font-normal",
        )}
      >
        {value}
      </strong>
    </div>
  );
}

/* ------------------------------ Fan Motor ------------------------------ */

function FanPowerCalculator() {
  const [flow, setFlow] = useState("10000");
  const [pressure, setPressure] = useState("2500");
  const [efficiency, setEfficiency] = useState("65");
  const [temperature, setTemperature] = useState("20");
  const [altitude, setAltitude] = useState("1000");
  const [driveType, setDriveType] =
    useState<keyof typeof DRIVE_TYPES>("Direkt akuple");
  const [vfd, setVfd] = useState<keyof typeof VFD_OPTIONS>("Var");
  const [margin, setMargin] = useState("10");

  const result = useMemo(() => {
    const flowM3h = parseNumber(flow);
    const pressurePa = parseNumber(pressure);
    const fanEfficiency = parseNumber(efficiency) / 100;
    const temperatureC = parseNumber(temperature);
    const serviceMargin = parseNumber(margin);
    const densityInfo = airDensity(parseNumber(temperature), parseNumber(altitude));
    const flowM3s = flowM3h / 3600;
    const shaftPower =
      fanEfficiency > 0 ? (flowM3s * pressurePa) / 1000 / fanEfficiency : 0;
    const driveEfficiency = DRIVE_TYPES[driveType];
    const motorInput = driveEfficiency > 0 ? shaftPower / driveEfficiency : 0;
    const densityRatio =
      densityInfo.density > 0 ? STANDARD_AIR_DENSITY / densityInfo.density : 0;
    const recommendedMotor = selectMotor(motorInput * (1 + serviceMargin / 100));
    return {
      flowM3h,
      flowM3s,
      pressurePa,
      fanEfficiency,
      temperatureC,
      serviceMargin,
      densityInfo,
      shaftPower,
      stdPressure: pressurePa * densityRatio,
      stdShaftPower: shaftPower * densityRatio,
      recommendedMotor,
      hasVfd: VFD_OPTIONS[vfd],
    };
  }, [altitude, driveType, efficiency, flow, margin, pressure, temperature, vfd]);

  const resultRows = [
    { label: "Hava Debisi", value: `${formatNumber(result.flowM3h)} m³/h` },
    {
      label: "Hava Yoğunluğu (Deniz Seviyesi, 0 °C)",
      value: `${formatNumber(1.293, 3)} kg/m³`,
    },
    { label: "Hava Debisi", value: `${formatNumber(result.flowM3s, 3)} m³/s` },
    {
      label: "Giriş/Atmosfer Basıncı",
      value: `${formatNumber(result.densityInfo.pressurePa, 0)} Pa`,
    },
    {
      label: "Emilen Hava Sıcaklığı",
      value: `${formatNumber(result.temperatureC, 1)} °C`,
    },
    {
      label: "Toplam Gerçek Basınç Farkı",
      value: `${formatNumber(result.pressurePa)} Pa`,
    },
    {
      label: "Toplam Basınç Farkı (@ 1,2 kg/m³ yoğunlukta)",
      value: `${formatNumber(result.stdPressure)} Pa`,
    },
    { label: "Fan Verimi", value: `%${formatNumber(result.fanEfficiency * 100)}` },
    { label: "Mil Gücü (Actual)", value: `${formatNumber(result.shaftPower)} kW` },
    {
      label: "Mil Gücü (@ 1,2 kg/m³ yoğunlukta)",
      value: `${formatNumber(result.stdShaftPower)} kW`,
    },
    { label: "Servis Payı", value: `%${formatNumber(result.serviceMargin)}` },
    {
      label: "Önerilen Nominal Motor Gücü",
      value: `${formatNumber(result.recommendedMotor)} kW`,
      strong: true,
    },
  ];

  return (
    <Panel
      title="Fan Motor Hesabı"
      description="Yoğunluk, mil gücü ve nominal motor seçimi akışı korunur."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section>
          <SubHeading title="Girdiler" hint="Fan çalışma şartları ve seçim parametreleri" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Hava debisi (m³/h)">
              <input className={inputClass} value={flow} onChange={(e) => setFlow(e.target.value)} />
            </Field>
            <Field label="Toplam gerçek basınç farkı (Pa)">
              <input className={inputClass} value={pressure} onChange={(e) => setPressure(e.target.value)} />
            </Field>
            <Field label="Fan verimi (%)">
              <input className={inputClass} value={efficiency} onChange={(e) => setEfficiency(e.target.value)} />
            </Field>
            <Field label="Servis payı (%)">
              <input className={inputClass} value={margin} onChange={(e) => setMargin(e.target.value)} />
            </Field>
            <Field label="Emilen hava sıcaklığı (°C)">
              <input className={inputClass} value={temperature} onChange={(e) => setTemperature(e.target.value)} />
            </Field>
            <Field label="Rakım (m)">
              <input className={inputClass} value={altitude} onChange={(e) => setAltitude(e.target.value)} />
            </Field>
            <Field label="Tahrik tipi">
              <select
                className={selectClass}
                value={driveType}
                onChange={(e) => setDriveType(e.target.value as keyof typeof DRIVE_TYPES)}
              >
                {Object.keys(DRIVE_TYPES).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="VFD">
              <select
                className={selectClass}
                value={vfd}
                onChange={(e) => setVfd(e.target.value as keyof typeof VFD_OPTIONS)}
              >
                {Object.keys(VFD_OPTIONS).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
          </div>
        </section>
        <section>
          <SubHeading title="Sonuçlar" />
          <div className="rounded-md border border-border bg-background/40 px-4">
            {resultRows.map((row, index) => (
              <ResultRow
                key={`${row.label}-${index}`}
                index={index + 1}
                label={row.label}
                value={row.value}
                strong={row.strong}
              />
            ))}
          </div>
          <div className="mt-4 flex justify-end">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => exportRowsToPdf("Fan Motor Gücü Hesaplama Sonuçları", resultRows)}
            >
              <FileDown className="size-4" />
              PDF Export
            </Button>
          </div>
        </section>
      </div>
    </Panel>
  );
}

/* ------------------------------ Basınç Kaybı ------------------------------ */

function PressureLossCalculator() {
  type PressureRow = {
    id: number;
    tip: string;
    cap: number;
    debi: number;
    hiz: number;
    miktar: number;
    kayip: number;
  };
  const [rows, setRows] = useState<PressureRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [angle, setAngle] = useState("90");
  const [rd, setRd] = useState("1,5");
  const [diameter, setDiameter] = useState("250");
  const [flow, setFlow] = useState("4500");
  const [elbowCount, setElbowCount] = useState("3");
  const [length, setLength] = useState("5");
  const [temperature, setTemperature] = useState("20");
  const [altitude, setAltitude] = useState("0");
  const [equipmentType, setEquipmentType] = useState("Filtre");
  const [equipmentLoss, setEquipmentLoss] = useState("1200");

  const metrics = useMemo(() => {
    const diameterMm = parseNumber(diameter);
    const diameterM = diameterMm / 1000;
    const area = diameterM > 0 ? (Math.PI * diameterM ** 2) / 4 : 0;
    const flowM3h = parseNumber(flow);
    const velocity = area > 0 ? flowM3h / area / 3600 : 0;
    const density = airDensity(parseNumber(temperature), parseNumber(altitude)).density;
    const vp = (density * velocity ** 2) / 2;
    const constant =
      PRESSURE_CONSTANTS[Math.round(parseNumber(angle))]?.[parseNumber(rd)] ?? 0;
    const elbowSingle = vp * constant;
    const term =
      diameterMm > 0 && velocity > 0
        ? 0.03 / diameterMm + 68 / (66.4 * diameterMm * velocity)
        : 0;
    const fpp = term > 0 ? 0.11 * term ** 0.25 : 0;
    const straightPerM =
      diameterMm > 0
        ? ((1000 * (0.85 * fpp + 0.0028)) / diameterMm) * vp * 1.15 * 1.18
        : 0;
    const jetCapLoss = 2.5 * ((STANDARD_AIR_DENSITY * velocity ** 2) / 2);
    return { diameterMm, flowM3h, density, area, velocity, elbowSingle, straightPerM, jetCapLoss };
  }, [altitude, angle, diameter, flow, rd, temperature]);
  const totalLoss = rows.reduce((sum, row) => sum + row.kayip, 0);

  function addRow(tip: string, miktar: number, kayip: number) {
    const row = {
      id: Date.now(),
      tip,
      cap: metrics.diameterMm,
      debi: metrics.flowM3h,
      hiz: metrics.velocity,
      miktar,
      kayip,
    };
    setRows((current) => [...current, row]);
    setSelectedId(row.id);
  }

  return (
    <Panel
      title="Basınç Kaybı Hesaplama"
      description="Dirsek, düz kanal, Jet-Cap, ekipman ve toplam liste mantığı korunur."
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section>
          <SubHeading title="Girdiler" hint="Kanal şartları ve eklenecek kayıp tipi" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Hava sıcaklığı (°C)">
              <input className={inputClass} value={temperature} onChange={(e) => setTemperature(e.target.value)} />
            </Field>
            <Field label="Rakım (m)">
              <input className={inputClass} value={altitude} onChange={(e) => setAltitude(e.target.value)} />
            </Field>
            <Field label="Açı">
              <select className={selectClass} value={angle} onChange={(e) => setAngle(e.target.value)}>
                {Object.keys(PRESSURE_CONSTANTS).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="r/D">
              <select className={selectClass} value={rd} onChange={(e) => setRd(e.target.value)}>
                <option>0,75</option>
                <option>1</option>
                <option>1,5</option>
                <option>2</option>
              </select>
            </Field>
            <Field label="Boru çapı (mm)">
              <input className={inputClass} value={diameter} onChange={(e) => setDiameter(e.target.value)} />
            </Field>
            <Field label="Debi (m³/h)">
              <input className={inputClass} value={flow} onChange={(e) => setFlow(e.target.value)} />
            </Field>
            <Field label="Dirsek adedi">
              <input className={inputClass} value={elbowCount} onChange={(e) => setElbowCount(e.target.value)} />
            </Field>
            <Field label="Düz kanal uzunluğu (m)">
              <input className={inputClass} value={length} onChange={(e) => setLength(e.target.value)} />
            </Field>
            <Field label="Ekipman tipi">
              <select className={selectClass} value={equipmentType} onChange={(e) => setEquipmentType(e.target.value)}>
                <option>Filtre</option>
                <option>Akrobat Kol</option>
                <option>Davlumbaz</option>
                <option>Menfez</option>
                <option>Diğer</option>
              </select>
            </Field>
            <Field label="Ekipman basınç kaybı (Pa)">
              <input className={inputClass} value={equipmentLoss} onChange={(e) => setEquipmentLoss(e.target.value)} />
            </Field>
          </div>

          <div className="mt-5">
            <SubHeading title="Hesaplar" hint="Anlık hesaplanan değerleri tabloya ekleyin" />
            <div className="rounded-md border border-border bg-background/40 px-4">
              <ResultRow label="Hava yoğunluğu" value={`${formatNumber(metrics.density, 3)} kg/m³`} />
              <ResultRow label="Boru kesit alanı" value={`${formatNumber(metrics.area, 4)} m²`} />
              <ResultRow label="Taşıma hızı" value={`${formatNumber(metrics.velocity)} m/sn`} />
              <ResultRow label="Dirsek kaybı" value={`${formatNumber(metrics.elbowSingle)} Pa/adet`} />
              <ResultRow label="Düz kanal kaybı" value={`${formatNumber(metrics.straightPerM)} Pa/m`} />
              <ResultRow label="Jet-Cap kaybı" value={`${formatNumber(metrics.jetCapLoss)} Pa`} />
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => addRow("Dirsek", parseNumber(elbowCount), metrics.elbowSingle * parseNumber(elbowCount))}>
                <Plus className="size-4" /> Dirsek Ekle
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => addRow("Düz Kanal", parseNumber(length), metrics.straightPerM * parseNumber(length))}>
                <Plus className="size-4" /> Düz Kanal Ekle
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => addRow("Jet-Cap", 1, metrics.jetCapLoss)}>
                <Plus className="size-4" /> Jet-Cap Ekle
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => addRow(equipmentType, 1, parseNumber(equipmentLoss))}>
                <Plus className="size-4" /> Ekipman Ekle
              </Button>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-end justify-between gap-3">
            <SubHeading
              title="Basınç Kaybı Tablosu"
              hint={rows.length ? `${rows.length} öge listede` : "Henüz öge eklenmedi"}
            />
            <span className="font-mono text-lg font-bold text-primary">
              {formatNumber(totalLoss)} Pa
            </span>
          </div>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-background/60 font-mono uppercase text-muted-foreground">
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Tip</th>
                  <th className="px-3 py-2 font-medium">Kanal Çapı</th>
                  <th className="px-3 py-2 font-medium">Debi</th>
                  <th className="px-3 py-2 font-medium">Hız</th>
                  <th className="px-3 py-2 font-medium">Miktar</th>
                  <th className="px-3 py-2 text-right font-medium">Basınç Kaybı</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 font-mono">
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setSelectedId(row.id)}
                    className={cn(
                      "cursor-pointer transition-colors hover:bg-accent",
                      selectedId === row.id && "bg-accent",
                    )}
                  >
                    <td className="px-3 py-2 text-muted-foreground">{row.id}</td>
                    <td className="px-3 py-2 font-sans">{row.tip}</td>
                    <td className="px-3 py-2">{formatNumber(row.cap, 0)} mm</td>
                    <td className="px-3 py-2">{formatNumber(row.debi, 0)}</td>
                    <td className="px-3 py-2">{formatNumber(row.hiz)}</td>
                    <td className="px-3 py-2">{formatNumber(row.miktar)}</td>
                    <td className="px-3 py-2 text-right">{formatNumber(row.kayip)} Pa</td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td colSpan={7} className="px-3 py-8 text-center font-sans text-sm text-muted-foreground">
                      Henüz öge eklenmedi.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={!selectedId}
              onClick={() => setRows((current) => current.filter((row) => row.id !== selectedId))}
            >
              <Trash2 className="size-4" /> Seçili Ögeyi Sil
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={!rows.length}
              onClick={() =>
                downloadCsv(
                  "basinc-kaybi.csv",
                  ["ID", "Tip", "Kanal Çapı (mm)", "Debi (m³/h)", "Kanal İçi Hız (m/sn)", "Miktar", "Basınç Kaybı (Pa)"],
                  rows.map((row) => [row.id, row.tip, row.cap, row.debi, formatNumber(row.hiz), row.miktar, formatNumber(row.kayip)]),
                )
              }
            >
              <FileDown className="size-4" /> CSV'ye Aktar
            </Button>
          </div>
        </section>
      </div>
    </Panel>
  );
}

/* ------------------------------ Kapasite ------------------------------ */

function CapacityCalculatorScreen() {
  const [active, setActive] = useState<CapacityToolKey>("thermal-cutting");
  const modules: Array<{ key: CapacityToolKey; label: string; icon: LucideIcon }> = [
    { key: "thermal-cutting", label: "Isıl Kesim", icon: Scissors },
    { key: "cnc-lathe", label: "CNC Torna", icon: Gauge },
    { key: "hood", label: "Davlumbaz", icon: Wind },
    { key: "welding-hall", label: "Kaynak Holü", icon: Flame },
  ];
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {modules.map((module) => {
          const Icon = module.icon;
          const isActive = active === module.key;
          return (
            <button
              key={module.key}
              type="button"
              onClick={() => setActive(module.key)}
              className={cn(
                "flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                isActive
                  ? "border-primary/50 bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className={cn("size-4", isActive && "text-primary")} />
              {module.label}
            </button>
          );
        })}
      </div>
      {active === "thermal-cutting" && <ThermalCuttingCalculator />}
      {active === "cnc-lathe" && <CncLatheCapacityCalculator />}
      {active === "hood" && <HoodCapacityCalculator />}
      {active === "welding-hall" && <WeldingHallCapacityCalculator />}
    </div>
  );
}

function ResultGrid({ children }: { children: ReactNode }) {
  return (
    <div className="mt-5 rounded-md border border-border bg-background/40 px-4">
      {children}
    </div>
  );
}

function ThermalCuttingCalculator() {
  const [power, setPower] =
    useState<keyof typeof THERMAL_CUTTING_POWER_OPTIONS>("12 kW (Laser)");
  const [tightness, setTightness] =
    useState<keyof typeof VALVE_TIGHTNESS_OPTIONS>("Kötü");
  const [valveCount, setValveCount] = useState("16");
  const [widthMm, setWidthMm] = useState("1500");
  const [lengthMm, setLengthMm] = useState("2000");
  const [reserve, setReserve] = useState("15");
  const result = useMemo(() => {
    const area = (parseNumber(widthMm) * parseNumber(lengthMm)) / 1_000_000;
    const processFlow = THERMAL_CUTTING_POWER_OPTIONS[power] * area;
    const leakageFlow = parseNumber(valveCount) * VALVE_TIGHTNESS_OPTIONS[tightness];
    const required = processFlow + leakageFlow;
    return {
      area,
      processFlow,
      leakageFlow,
      required,
      reserved: required * (1 + parseNumber(reserve) / 100),
    };
  }, [lengthMm, power, reserve, tightness, valveCount, widthMm]);
  return (
    <Panel
      title="Isıl Kesim Kapasite Hesaplama"
      description="Modül alanı, kesim gücü ve klape sızıntısına göre gerekli emiş kapasitesi."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Kesim gücü">
          <select className={selectClass} value={power} onChange={(e) => setPower(e.target.value as keyof typeof THERMAL_CUTTING_POWER_OPTIONS)}>
            {Object.keys(THERMAL_CUTTING_POWER_OPTIONS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Klape sızdırmazlığı">
          <select className={selectClass} value={tightness} onChange={(e) => setTightness(e.target.value as keyof typeof VALVE_TIGHTNESS_OPTIONS)}>
            {Object.keys(VALVE_TIGHTNESS_OPTIONS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Valf adedi">
          <input className={inputClass} value={valveCount} onChange={(e) => setValveCount(e.target.value)} />
        </Field>
        <Field label="Modül genişliği (mm)">
          <input className={inputClass} value={widthMm} onChange={(e) => setWidthMm(e.target.value)} />
        </Field>
        <Field label="Modül uzunluğu (mm)">
          <input className={inputClass} value={lengthMm} onChange={(e) => setLengthMm(e.target.value)} />
        </Field>
        <Field label="Emniyet / rezerv payı (%)">
          <input className={inputClass} value={reserve} onChange={(e) => setReserve(e.target.value)} />
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Modül alanı" value={`${formatNumber(result.area, 3)} m²`} />
        <ResultRow label="Proses debisi" value={`${formatNumber(result.processFlow)} m³/h`} />
        <ResultRow label="Klape sızıntı debisi" value={`${formatNumber(result.leakageFlow)} m³/h`} />
        <ResultRow label="Gerekli kapasite" value={`${formatNumber(result.required)} m³/h`} />
        <ResultRow label="Rezerve edilmiş kapasite" value={`${formatNumber(result.reserved)} m³/h`} strong />
      </ResultGrid>
    </Panel>
  );
}

function CncLatheCapacityCalculator() {
  const [coolant, setCoolant] =
    useState<keyof typeof CNC_DEFAULT_VISCOSITY>("Water Soluble");
  const [spindle, setSpindle] = useState("8000");
  const [pressure, setPressure] = useState("100");
  const [space, setSpace] = useState("6");
  const [door, setDoor] =
    useState<keyof typeof CNC_DOOR_ADJUSTMENT>("Sliding Door, Open on Top");
  const [doorArea, setDoorArea] = useState("1");
  const [cycleTime, setCycleTime] = useState("300");
  const [viscosity, setViscosity] = useState("0,8");
  const result = useMemo(() => {
    const spindlePressureFactor =
      (0.22 * Math.log(parseNumber(spindle) * parseNumber(pressure)) - 2.4) * 2;
    const processingSpaceMultiplier = 1 + (parseNumber(space) - 1) * 0.5;
    const doorOpeningMultiplier = (parseNumber(doorArea) - 0.5) * 0.08 * 2;
    const cycleFactor = Math.max(0, -0.0653 * Math.log(parseNumber(cycleTime)) + 0.1419);
    const viscosityValue = parseNumber(viscosity);
    const viscosityFactor = Math.max(
      1,
      -0.00002 * viscosityValue ** 2 + 0.0313 * viscosityValue + 0.7349,
    );
    const beforeSafety =
      (processingSpaceMultiplier *
        3600 *
        0.2 *
        (1 + spindlePressureFactor) *
        (1 + cycleFactor) *
        (1 + doorOpeningMultiplier) +
        CNC_DOOR_ADJUSTMENT[door]) /
      viscosityFactor;
    const requiredAirflow = Math.max(150, beforeSafety) / 1.3;
    const products = coolant === "Straight Oil" ? CNC_HEPA_PRODUCTS : CNC_STANDARD_PRODUCTS;
    const selectedProduct =
      products.find(([, threshold]) => requiredAirflow <= threshold / viscosityFactor)?.[0] ??
      products[products.length - 1][0];
    return { requiredAirflow, selectedProduct, viscosityFactor };
  }, [coolant, cycleTime, door, doorArea, pressure, space, spindle, viscosity]);

  function handleCoolantChange(next: keyof typeof CNC_DEFAULT_VISCOSITY) {
    setCoolant(next);
    setViscosity(CNC_DEFAULT_VISCOSITY[next]);
  }

  return (
    <Panel
      title="CNC Torna Tezgah Kapasite Hesaplama"
      description="Oil mist filtre seçim aracındaki gerekli hava debisi ve ürün önerisi."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Soğutma sıvısı tipi">
          <select className={selectClass} value={coolant} onChange={(e) => handleCoolantChange(e.target.value as keyof typeof CNC_DEFAULT_VISCOSITY)}>
            {Object.keys(CNC_DEFAULT_VISCOSITY).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Maks. iş mili devri (rpm)">
          <input className={inputClass} value={spindle} onChange={(e) => setSpindle(e.target.value)} />
        </Field>
        <Field label="Soğutma pompası basıncı (bar)">
          <input className={inputClass} value={pressure} onChange={(e) => setPressure(e.target.value)} />
        </Field>
        <Field label="İşleme hacmi (m³)">
          <input className={inputClass} value={space} onChange={(e) => setSpace(e.target.value)} />
        </Field>
        <Field label="Kapı tipi">
          <select className={selectClass} value={door} onChange={(e) => setDoor(e.target.value as keyof typeof CNC_DOOR_ADJUSTMENT)}>
            {Object.keys(CNC_DOOR_ADJUSTMENT).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Kapı açıklık alanı (m²)">
          <input className={inputClass} value={doorArea} onChange={(e) => setDoorArea(e.target.value)} />
        </Field>
        <Field label="Çevrim süresi (dk)">
          <input className={inputClass} value={cycleTime} onChange={(e) => setCycleTime(e.target.value)} />
        </Field>
        <Field label="Viskozite (cSt)">
          <input className={inputClass} value={viscosity} onChange={(e) => setViscosity(e.target.value)} />
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Viskozite faktörü" value={formatNumber(result.viscosityFactor, 3)} />
        <ResultRow label="Gerekli hava debisi" value={`${formatNumber(result.requiredAirflow)} m³/h`} strong />
        <ResultRow label="Önerilen ürün" value={result.selectedProduct} />
      </ResultGrid>
    </Panel>
  );
}

function HoodCapacityCalculator() {
  const [hoodType, setHoodType] =
    useState<keyof typeof HOOD_TYPE_FACTORS>("Flanşlı Davlumbaz");
  const [profile, setProfile] = useState<keyof typeof HOOD_CAPTURE_OPTIONS>(
    "Düşük hızlı yayılım (0,5 - 1,0 m/s)",
  );
  const [velocity, setVelocity] = useState("0,75");
  const [distance, setDistance] = useState("0,5");
  const [width, setWidth] = useState("1,2");
  const [length, setLength] = useState("0,8");
  const [reserve, setReserve] = useState("15");
  const result = useMemo(() => {
    const area = parseNumber(width) * parseNumber(length);
    const airflowM3s =
      HOOD_TYPE_FACTORS[hoodType] *
      parseNumber(velocity) *
      (10 * parseNumber(distance) ** 2 + area);
    const airflowM3h = airflowM3s * 3600;
    return {
      area,
      airflowM3s,
      airflowM3h,
      reserved: airflowM3h * (1 + parseNumber(reserve) / 100),
    };
  }, [distance, hoodType, length, reserve, velocity, width]);
  return (
    <Panel
      title="Davlumbaz Kapasite Hesaplama"
      description="Yakalama profili, davlumbaz katsayısı, mesafe ve kesit alanı ile hava debisi."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Davlumbaz tipi">
          <select className={selectClass} value={hoodType} onChange={(e) => setHoodType(e.target.value as keyof typeof HOOD_TYPE_FACTORS)}>
            {Object.keys(HOOD_TYPE_FACTORS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Yakalama profili">
          <select
            className={selectClass}
            value={profile}
            onChange={(e) => {
              const next = e.target.value as keyof typeof HOOD_CAPTURE_OPTIONS;
              setProfile(next);
              setVelocity(String(HOOD_CAPTURE_OPTIONS[next]).replace(".", ","));
            }}
          >
            {Object.keys(HOOD_CAPTURE_OPTIONS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Yakalama hızı (m/s)">
          <input className={inputClass} value={velocity} onChange={(e) => setVelocity(e.target.value)} />
        </Field>
        <Field label="Mesafe x (m)">
          <input className={inputClass} value={distance} onChange={(e) => setDistance(e.target.value)} />
        </Field>
        <Field label="Genişlik (m)">
          <input className={inputClass} value={width} onChange={(e) => setWidth(e.target.value)} />
        </Field>
        <Field label="Uzunluk (m)">
          <input className={inputClass} value={length} onChange={(e) => setLength(e.target.value)} />
        </Field>
        <Field label="Güvenlik payı (%)">
          <input className={inputClass} value={reserve} onChange={(e) => setReserve(e.target.value)} />
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Kesit alanı" value={`${formatNumber(result.area, 3)} m²`} />
        <ResultRow label="Hava debisi" value={`${formatNumber(result.airflowM3s, 3)} m³/s`} />
        <ResultRow label="Hava debisi" value={`${formatNumber(result.airflowM3h)} m³/h`} />
        <ResultRow label="Güvenlik paylı debi" value={`${formatNumber(result.reserved)} m³/h`} strong />
      </ResultGrid>
    </Panel>
  );
}

function WeldingHallCapacityCalculator() {
  const [weldingType, setWeldingType] = useState("SC Ar/CO2");
  const [manualCount, setManualCount] = useState("10");
  const [manualWire, setManualWire] = useState("1");
  const [robotCount, setRobotCount] = useState("4");
  const [robotWire, setRobotWire] = useState("5");
  const [depth, setDepth] = useState("50");
  const [width, setWidth] = useState("30");
  const [height, setHeight] = useState("8");
  const [limit, setLimit] = useState("5");
  const [requestedAch, setRequestedAch] = useState("6");
  const result = useMemo(() => {
    const totalWire =
      parseNumber(manualCount) * parseNumber(manualWire) +
      parseNumber(robotCount) * parseNumber(robotWire);
    const fumeFactor = WELDING_FUME_FACTORS[weldingType] ?? 5;
    const totalParticle = totalWire * 1000 * fumeFactor;
    const hallVolume = parseNumber(depth) * parseNumber(width) * parseNumber(height);
    const particleRatio = hallVolume > 0 ? totalParticle / hallVolume : 0;
    const minimumAch = parseNumber(limit) > 0 ? particleRatio / parseNumber(limit) : 0;
    const ach = parseNumber(requestedAch);
    const requiredCapacity = ach >= minimumAch ? hallVolume * ach : 0;
    return {
      fumeFactor,
      totalWire,
      totalParticle,
      hallVolume,
      particleRatio,
      minimumAch,
      requiredCapacity,
      validAch: ach >= minimumAch,
    };
  }, [depth, height, limit, manualCount, manualWire, requestedAch, robotCount, robotWire, weldingType, width]);
  return (
    <Panel
      title="Kaynak Holü Havalandırması Kapasite Hesaplama"
      description="Kaynak prosesi kaynaklı duman yüküne göre minimum ACH ve gerekli kapasite."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Kaynak tipi">
          <select className={selectClass} value={weldingType} onChange={(e) => setWeldingType(e.target.value)}>
            {Object.keys(WELDING_FUME_FACTORS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Manuel kaynakçı sayısı">
          <input className={inputClass} value={manualCount} onChange={(e) => setManualCount(e.target.value)} />
        </Field>
        <Field label="Manuel tel tüketimi (kg/h)">
          <input className={inputClass} value={manualWire} onChange={(e) => setManualWire(e.target.value)} />
        </Field>
        <Field label="Robot sayısı">
          <input className={inputClass} value={robotCount} onChange={(e) => setRobotCount(e.target.value)} />
        </Field>
        <Field label="Robot tel tüketimi (kg/h)">
          <input className={inputClass} value={robotWire} onChange={(e) => setRobotWire(e.target.value)} />
        </Field>
        <Field label="Hol derinliği (m)">
          <input className={inputClass} value={depth} onChange={(e) => setDepth(e.target.value)} />
        </Field>
        <Field label="Hol genişliği (m)">
          <input className={inputClass} value={width} onChange={(e) => setWidth(e.target.value)} />
        </Field>
        <Field label="Hol yüksekliği (m)">
          <input className={inputClass} value={height} onChange={(e) => setHeight(e.target.value)} />
        </Field>
        <Field label="Partikül limit değeri (mg/Nm³)">
          <input className={inputClass} value={limit} onChange={(e) => setLimit(e.target.value)} />
        </Field>
        <Field label="Gerekli ACH (1/h)">
          <input className={inputClass} value={requestedAch} onChange={(e) => setRequestedAch(e.target.value)} />
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Referans duman katsayısı" value={`${formatNumber(result.fumeFactor, 1)} mg/g`} />
        <ResultRow label="Toplam tel tüketimi" value={`${formatNumber(result.totalWire)} kg/h`} />
        <ResultRow label="Toplam partikül" value={`${formatNumber(result.totalParticle, 0)} mg/h`} />
        <ResultRow label="Hol hacmi" value={`${formatNumber(result.hallVolume)} m³`} />
        <ResultRow label="Minimum ACH" value={`${formatNumber(result.minimumAch)} 1/h`} />
        <ResultRow
          label="Gerekli kapasite"
          value={result.validAch ? `${formatNumber(result.requiredCapacity, 0)} m³/h` : "ACH minimumdan düşük"}
          strong
        />
      </ResultGrid>
    </Panel>
  );
}

/* ------------------------------ Basınçlı Hava ------------------------------ */

function CompressedAirCalculator() {
  const [valveType, setValveType] = useState<'1"' | '1 1/2"'>('1"');
  const [valveCount, setValveCount] = useState("24");
  const [pulseInterval, setPulseInterval] = useState("10");
  const [pressureBar, setPressureBar] = useState("6");
  const [annualHours, setAnnualHours] = useState("2080");
  const [kwhPrice, setKwhPrice] = useState("0,07");
  const result = useMemo(() => {
    const freeAirNl = valveType === '1"' ? 100 : 240;
    const interval = parseNumber(pulseInterval);
    const simultaneous =
      interval > 0 ? Math.ceil((parseNumber(valveCount) * interval) / 60 / 5) : 0;
    const hourlyFreeAir =
      interval > 0 ? (freeAirNl * simultaneous * (60 / interval) * 60) / 1000 : 0;
    const hourlyCompressedAir = hourlyFreeAir / (parseNumber(pressureBar) + 1);
    const hourlyEnergy = hourlyCompressedAir * DEFAULT_ENERGY_PER_NM3;
    const annualEnergy = parseNumber(annualHours) * hourlyEnergy;
    return {
      freeAirNl,
      simultaneous,
      hourlyFreeAir,
      hourlyCompressedAir,
      hourlyEnergy,
      annualEnergy,
      annualCost: annualEnergy * parseNumber(kwhPrice),
    };
  }, [annualHours, kwhPrice, pressureBar, pulseInterval, valveCount, valveType]);
  return (
    <Panel
      title="Basınçlı Hava Tüketimi Hesabı"
      description="Patlaç tipi, darbe aralığı, basınç ve enerji maliyeti hesapları korunur."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Patlaç tipi">
          <select className={selectClass} value={valveType} onChange={(e) => setValveType(e.target.value as '1"' | '1 1/2"')}>
            <option>1"</option>
            <option>1 1/2"</option>
          </select>
        </Field>
        <Field label="Patlaç sayısı">
          <input className={inputClass} value={valveCount} onChange={(e) => setValveCount(e.target.value)} />
        </Field>
        <Field label="2 darbe arası süre (sn)">
          <input className={inputClass} value={pulseInterval} onChange={(e) => setPulseInterval(e.target.value)} />
        </Field>
        <Field label="Çalışma basıncı (bar)">
          <input className={inputClass} value={pressureBar} onChange={(e) => setPressureBar(e.target.value)} />
        </Field>
        <Field label="Yıllık çalışma saati">
          <input className={inputClass} value={annualHours} onChange={(e) => setAnnualHours(e.target.value)} />
        </Field>
        <Field label="kWh birim fiyatı">
          <input className={inputClass} value={kwhPrice} onChange={(e) => setKwhPrice(e.target.value)} />
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Serbest hava tüketimi" value={`${formatNumber(result.freeAirNl, 0)} Nl`} />
        <ResultRow label="Aynı anda çalışacak patlaç" value={`${result.simultaneous} adet`} />
        <ResultRow label="Saatlik serbest hava" value={`${formatNumber(result.hourlyFreeAir, 3)} Nm³/h`} />
        <ResultRow label="Saatlik sıkışmış hava" value={`${formatNumber(result.hourlyCompressedAir, 3)} Nm³/h`} />
        <ResultRow label="Enerji katsayısı" value={`${formatNumber(DEFAULT_ENERGY_PER_NM3, 2)} kWh/Nm³`} />
        <ResultRow label="Saatlik enerji" value={`${formatNumber(result.hourlyEnergy, 3)} kWh`} />
        <ResultRow label="Yıllık enerji" value={`${formatNumber(result.annualEnergy)} kWh/yıl`} />
        <ResultRow label="Yıllık enerji maliyeti" value={`${formatNumber(result.annualCost)} EUR/yıl`} strong />
      </ResultGrid>
    </Panel>
  );
}

/* ------------------------------ Patlama Kapağı ------------------------------ */

function ExplosionVentCalculator() {
  const [stClass, setStClass] =
    useState<keyof typeof EXPLOSION_ST_CLASSES>("St1");
  const [pred, setPred] = useState("0,1");
  const [pmax, setPmax] = useState("8");
  const [kst, setKst] = useState("200");
  const [pstat, setPstat] = useState("0,1");
  const [filterCount, setFilterCount] = useState("24");
  const [filterLength, setFilterLength] = useState("2");
  const [filterDiameter, setFilterDiameter] = useState("0,16");
  const [a, setA] = useState("2,4");
  const [c, setC] = useState("3");
  const [b, setB] = useState("2,2");
  const [d, setD] = useState("0,8");
  const [e, setE] = useState("0,4");
  const [panel, setPanel] =
    useState<keyof typeof EXPLOSION_PANEL_AREAS>("586 x 920 mm (0,539 m²)");

  function handleStClass(next: keyof typeof EXPLOSION_ST_CLASSES) {
    setStClass(next);
    setPmax(String(EXPLOSION_ST_CLASSES[next].pmax));
    setKst(String(EXPLOSION_ST_CLASSES[next].kst));
  }

  const result = useMemo(() => {
    const filterVolumeSingle =
      (parseNumber(filterLength) * Math.PI * parseNumber(filterDiameter) ** 2) / 4;
    const filterVolume = parseNumber(filterCount) * filterVolumeSingle;
    const veff = parseNumber(a) * parseNumber(c) * parseNumber(b);
    const leff = parseNumber(b);
    const de = leff > 0 ? 2 * Math.sqrt(veff / leff / Math.PI) : 0;
    const lOverDe = de > 0 ? Math.max(1, leff / de) : 0;
    const netVolume =
      veff +
      (parseNumber(c) * parseNumber(d) * (parseNumber(a) + parseNumber(e))) / 2 -
      filterVolume;
    const predValue = parseNumber(pred);
    const volumeFactor = netVolume > 0 ? netVolume ** 0.753 : 0;
    const term1 =
      predValue > 0
        ? 3.264e-5 * parseNumber(pmax) * parseNumber(kst) * predValue ** -0.569
        : 0;
    const term2 = predValue > 0 ? 0.27 * (parseNumber(pstat) - 0.1) * predValue ** -0.5 : 0;
    const bValue = (term1 + term2) * volumeFactor;
    const cValue = predValue > 0 ? -4.305 * Math.log10(predValue) + 0.758 : 0;
    const ventArea = lOverDe > 0 ? bValue * (1 + cValue * Math.log10(lOverDe)) : 0;
    const panelArea = EXPLOSION_PANEL_AREAS[panel];
    const panelCount = panelArea > 0 ? Math.ceil(Math.max(ventArea, 0) / panelArea) : 0;
    const areaOverVolume = volumeFactor > 0 ? ventArea / volumeFactor : 0;
    return { filterVolume, veff, leff, de, lOverDe, netVolume, bValue, cValue, ventArea, panelCount, areaOverVolume };
  }, [a, b, c, d, e, filterCount, filterDiameter, filterLength, kst, panel, pmax, pred, pstat]);

  const showWarning = parseNumber(pred) !== 0.1 || parseNumber(pstat) !== 0.1;

  return (
    <Panel
      title="Patlama Kapağı Hesaplama"
      description="ST sınıfı, Pred/Pstat, filtre hacmi ve kirli oda ölçülerine göre kapak alanı ve adedi."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="ST sınıfı">
          <select className={selectClass} value={stClass} onChange={(e2) => handleStClass(e2.target.value as keyof typeof EXPLOSION_ST_CLASSES)}>
            {Object.keys(EXPLOSION_ST_CLASSES).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Pred (bar)">
          <input className={inputClass} value={pred} onChange={(e2) => setPred(e2.target.value)} />
        </Field>
        <Field label="Pmax (bar)">
          <input className={inputClass} value={pmax} onChange={(e2) => setPmax(e2.target.value)} />
        </Field>
        <Field label="Kst (bar.m/sn)">
          <input className={inputClass} value={kst} onChange={(e2) => setKst(e2.target.value)} />
        </Field>
        <Field label="Pstat (bar)">
          <input className={inputClass} value={pstat} onChange={(e2) => setPstat(e2.target.value)} />
        </Field>
        <Field label="Filtre sayısı">
          <input className={inputClass} value={filterCount} onChange={(e2) => setFilterCount(e2.target.value)} />
        </Field>
        <Field label="Filtre uzunluğu (m)">
          <input className={inputClass} value={filterLength} onChange={(e2) => setFilterLength(e2.target.value)} />
        </Field>
        <Field label="Filtre çapı (m)">
          <input className={inputClass} value={filterDiameter} onChange={(e2) => setFilterDiameter(e2.target.value)} />
        </Field>
        <Field label="Kirli oda eni a (m)">
          <input className={inputClass} value={a} onChange={(e2) => setA(e2.target.value)} />
        </Field>
        <Field label="Kirli oda boyu c (m)">
          <input className={inputClass} value={c} onChange={(e2) => setC(e2.target.value)} />
        </Field>
        <Field label="Kirli oda yüksekliği b (m)">
          <input className={inputClass} value={b} onChange={(e2) => setB(e2.target.value)} />
        </Field>
        <Field label="Bunker yüksekliği d (m)">
          <input className={inputClass} value={d} onChange={(e2) => setD(e2.target.value)} />
        </Field>
        <Field label="Toz döküm açıklığı e (m)">
          <input className={inputClass} value={e} onChange={(e2) => setE(e2.target.value)} />
        </Field>
        <Field label="Patlama kapağı seçimi">
          <select className={selectClass} value={panel} onChange={(e2) => setPanel(e2.target.value as keyof typeof EXPLOSION_PANEL_AREAS)}>
            {Object.keys(EXPLOSION_PANEL_AREAS).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
      </div>
      <ResultGrid>
        <ResultRow label="Filtrelerin toplam hacmi" value={`${formatNumber(result.filterVolume, 3)} m³`} />
        <ResultRow label="Ünite net hacmi" value={`${formatNumber(result.netVolume, 3)} m³`} />
        <ResultRow label="Veff" value={`${formatNumber(result.veff, 3)} m³`} />
        <ResultRow label="Leff" value={`${formatNumber(result.leff, 3)} m`} />
        <ResultRow label="DE" value={`${formatNumber(result.de, 3)} m`} />
        <ResultRow label="L/DE" value={formatNumber(result.lOverDe, 3)} />
        <ResultRow label="B" value={formatNumber(result.bValue, 4)} />
        <ResultRow label="C" value={formatNumber(result.cValue, 4)} />
        <ResultRow label="A / V^0,753" value={formatNumber(result.areaOverVolume, 4)} />
        <ResultRow label="Gerekli kapak alanı A" value={`${formatNumber(result.ventArea, 3)} m²`} strong />
        <ResultRow label="Patlama kapağı sayısı" value={`${result.panelCount} adet`} strong />
      </ResultGrid>
      {showWarning && (
        <p className="mt-4 rounded-md border border-warning/40 bg-warning/10 px-4 py-3 text-xs text-warning">
          Uyarı: Pred ve Pstat için varsayılan değer 0,1 bar. Değiştirilen değerler
          hesap sonucunu doğrudan etkiler.
        </p>
      )}
    </Panel>
  );
}
