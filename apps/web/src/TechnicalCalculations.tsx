import { Calculator, Flame, Gauge, PanelTop, Scissors, Wind, Zap } from "lucide-react";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";

export type TechnicalToolKey = "fan" | "pressure-loss" | "capacity" | "compressed-air" | "explosion-vent";
type CapacityToolKey = "thermal-cutting" | "cnc-lathe" | "hood" | "welding-hall";

const STANDARD_AIR_DENSITY = 1.2;
const KELVIN_OFFSET = 273.15;
const GAS_CONSTANT_DRY_AIR = 287.05;
const DEFAULT_ENERGY_PER_NM3 = 0.11;
const STANDARD_MOTOR_POWERS_KW = [
  0.18, 0.25, 0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315,
];
const DRIVE_TYPES = { "Direkt akuple": 1, "Kayış kasnak": 0.95 };
const VFD_OPTIONS = { Var: true, Yok: false };
const THERMAL_CUTTING_POWER_OPTIONS = {
  "2 kW (Laser)": 3500,
  "4 kW (Laser)": 4000,
  "6 kW (Laser)": 4700,
  "8 kW (Laser)": 5000,
  "10 kW (Laser)": 5500,
  "12 kW (Laser)": 6000,
  "Up to 150 A (Plasma)": 3600,
  "Up to 300 A (Plasma)": 4100,
  "Up to 450 A (Plasma)": 4700,
  "Above 450 A (Plasma)": 5000,
};
const VALVE_TIGHTNESS_OPTIONS = { Kötü: 70, Orta: 60, İyi: 50, "Çok İyi": 40 };
const HOOD_TYPE_FACTORS = { "Düz Davlumbaz": 1, "Flanşlı Davlumbaz": 0.75 };
const HOOD_CAPTURE_OPTIONS = {
  "Hafif yayılım (0,3 - 0,5 m/s)": 0.4,
  "Düşük hızlı yayılım (0,5 - 1,0 m/s)": 0.75,
  "Aktif oluşum (1,0 - 2,5 m/s)": 1.75,
  "Yüksek hızlı yayılım (2,5 - 10 m/s)": 4,
};
const PRESSURE_CONSTANTS: Record<number, Record<number, number>> = {
  20: { 0.75: 0.1674, 1: 0.1302, 1.5: 0.1054, 2: 0.1023 },
  30: { 0.75: 0.243, 1: 0.189, 1.5: 0.153, 2: 0.1485 },
  45: { 0.75: 0.324, 1: 0.252, 1.5: 0.204, 2: 0.198 },
  60: { 0.75: 0.4212, 1: 0.3276, 1.5: 0.2652, 2: 0.2574 },
  75: { 0.75: 0.486, 1: 0.378, 1.5: 0.306, 2: 0.297 },
  90: { 0.75: 0.54, 1: 0.42, 1.5: 0.34, 2: 0.33 },
  110: { 0.75: 0.6102, 1: 0.4746, 1.5: 0.3842, 2: 0.3729 },
  130: { 0.75: 0.648, 1: 0.504, 1.5: 0.408, 2: 0.396 },
  150: { 0.75: 0.6912, 1: 0.5376, 1.5: 0.4352, 2: 0.4224 },
  180: { 0.75: 0.756, 1: 0.588, 1.5: 0.476, 2: 0.462 },
};
const CNC_DEFAULT_VISCOSITY = { Synthetic: "0,8", "Water Soluble": "0,8", "Semi-Synthetic": "1", "Straight Oil": "10" };
const CNC_DOOR_ADJUSTMENT = { "Sliding Door, Vertical": -100, "Sliding Door, Horizontal": 0, "Sliding Door, Open on Top": 250 };
const CNC_STANDARD_PRODUCTS: Array<[string, number]> = [
  ["YBFpro MINI", 600],
  ["YBFpro MIDI", 1000],
  ["DT.YBF.1.100.170.7,5.3.50.380.DS.LCD", 1000],
  ["DT.YBF.1.150.170.11.2.50.380.DS.LCD", 1500],
  ["DT.YBF.1.200.170.15.2.50.380.DS.LCD", 2000],
  ["DT.YBF.2.300.170.22.2.50.380.DS.LCD", 3000],
  ["DT.YBF.2.350.170.30.2.50.380.DS.LCD", 3500],
  ["DT.YBF.2.400.170.30.2.50.380.DS.LCD", 4000],
];
const CNC_HEPA_PRODUCTS: Array<[string, number]> = [
  ["H.YBFpro MINI", 500],
  ["H.YBFpro MIDI", 900],
  ["DT.HYBF.1.100.200.11.2.50.380.DS.LCD", 1000],
  ["DT.HYBF.1.150.200.15.2.50.380.DS.LCD", 1500],
  ["DT.HYBF.1.200.200.22.2.50.380.DS.LCD", 2000],
  ["DT.HYBF.2.300.200.30.2.50.380.DS.LCD", 3000],
  ["DT.HYBF.2.350.200.40.2.50.380.DS.LCD", 3500],
  ["DT.HYBF.2.400.200.40.2.50.380.DS.LCD", 4000],
];
const WELDING_FUME_FACTORS: Record<string, number> = {
  "SC Ar/CO2": 5,
  "SC CO2": 8,
  "STT Ar/CO2": 4,
  "RMD Ar/CO2": 4,
  "CMT Ar/CO2": 3,
  "GT Ar/CO2": 10,
  "GT CO2": 13,
  "AXS Ar/CO2": 12,
  "AX-P Ar/CO2": 9,
  "FCAW Ar/CO2": 18,
};
const EXPLOSION_ST_CLASSES = {
  St1: { pmax: 8, kst: 200 },
  St2: { pmax: 9, kst: 300 },
  St3: { pmax: 10, kst: 301 },
};
const EXPLOSION_PANEL_AREAS = {
  "586 x 920 mm (0,539 m²)": 0.539,
  "320 x 640 mm (0,205 m²)": 0.205,
  "1.020 x 1.020 mm (1,040 m²)": 1.04,
};

function parseNumber(value: string | number) {
  const raw = String(value ?? "").trim().replace(/\s/g, "");
  if (!raw) return 0;
  const normalized = raw.includes(",") && !raw.includes(".") ? raw.replace(",", ".") : raw.replace(/,/g, "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatNumber(value: number, digits = 2) {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
}

function selectMotor(requiredKw: number) {
  return STANDARD_MOTOR_POWERS_KW.find((power) => power >= requiredKw) ?? STANDARD_MOTOR_POWERS_KW[STANDARD_MOTOR_POWERS_KW.length - 1];
}

function airDensity(temperatureC: number, altitudeM: number) {
  const temperatureK = temperatureC + KELVIN_OFFSET;
  const pressurePa = 101325 * Math.exp(-altitudeM / 8434);
  return { pressurePa, density: pressurePa / (GAS_CONSTANT_DRY_AIR * temperatureK) };
}

function downloadCsv(filename: string, header: string[], rows: Array<Array<string | number>>) {
  const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(";")).join("\n");
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportRowsToPdf(title: string, rows: Array<{ label: string; value: string; strong?: boolean }>) {
  const reportWindow = window.open("", "_blank", "width=900,height=720");
  if (!reportWindow) {
    window.print();
    return;
  }
  const rowHtml = rows
    .map(
      (row, index) => `
        <tr class="${row.strong ? "strong" : ""}">
          <td>${index + 1}. ${row.label}</td>
          <td>${row.value}</td>
        </tr>
      `,
    )
    .join("");
  reportWindow.document.write(`
    <!doctype html>
    <html lang="tr">
      <head>
        <meta charset="utf-8" />
        <title>${title}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 32px; color: #162033; }
          h1 { margin: 0 0 24px; font-size: 22px; }
          table { width: 100%; border-collapse: collapse; }
          td { border-bottom: 1px solid #e5e7eb; padding: 13px 0; font-size: 13px; }
          td:last-child { text-align: right; font-weight: 700; color: #000; }
          tr.strong td { font-size: 16px; font-weight: 800; }
          tr.strong td:last-child { color: #d32f2f; font-size: 20px; }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        <table>${rowHtml}</table>
        <script>window.onload = () => { window.print(); };</script>
      </body>
    </html>
  `);
  reportWindow.document.close();
}

const toolTitles: Record<TechnicalToolKey, { title: string; description: string; icon: typeof Gauge }> = {
  fan: { title: "Fan Motor Modülü", description: "Debi, basınç, yoğunluk, mil gücü ve nominal motor seçimi.", icon: Zap },
  "pressure-loss": { title: "Basınç Kaybı Modülü", description: "Dirsek, düz kanal, Jet-Cap ve ekipman kayıplarını listeleyerek toplam basınç kaybı.", icon: Wind },
  capacity: { title: "Kapasite Hesap Modülü", description: "Isıl kesim, CNC torna, davlumbaz ve kaynak hol kapasite hesapları bu ekran içinden seçilir.", icon: Calculator },
  "compressed-air": { title: "Basınçlı Hava Tüketim Modülü", description: "Patlaç tipi, darbe aralığı ve çalışma basıncıyla enerji tüketimi.", icon: Flame },
  "explosion-vent": { title: "Patlama Kapağı Modülü", description: "ST sınıfı, net hacim ve panel alanına göre kapak alanı ve adet hesabı.", icon: PanelTop },
};

export function TechnicalCalculationsScreen({ tool }: { tool: TechnicalToolKey }) {
  const current = toolTitles[tool];
  const Icon = current.icon;

  return (
    <section className="technical-shell">
      <div className="technical-hero">
        <div>
          <h2>{current.title}</h2>
          <p>{current.description}</p>
        </div>
        <div className="technical-hero-mark">
          <Icon size={30} />
        </div>
      </div>

      {tool === "fan" ? <FanPowerCalculator /> : null}
      {tool === "pressure-loss" ? <PressureLossCalculator /> : null}
      {tool === "capacity" ? <CapacityCalculatorScreen /> : null}
      {tool === "compressed-air" ? <CompressedAirCalculator /> : null}
      {tool === "explosion-vent" ? <ExplosionVentCalculator /> : null}
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="technical-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function ResultRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={strong ? "technical-result-row strong" : "technical-result-row"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FanPowerCalculator() {
  const [flow, setFlow] = useState("10000");
  const [pressure, setPressure] = useState("2500");
  const [efficiency, setEfficiency] = useState("65");
  const [temperature, setTemperature] = useState("20");
  const [altitude, setAltitude] = useState("1000");
  const [driveType, setDriveType] = useState<keyof typeof DRIVE_TYPES>("Direkt akuple");
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
    const shaftPower = fanEfficiency > 0 ? (flowM3s * pressurePa) / 1000 / fanEfficiency : 0;
    const driveEfficiency = DRIVE_TYPES[driveType];
    const motorInput = driveEfficiency > 0 ? shaftPower / driveEfficiency : 0;
    const densityRatio = densityInfo.density > 0 ? STANDARD_AIR_DENSITY / densityInfo.density : 0;
    const recommendedMotor = selectMotor(motorInput * (1 + serviceMargin / 100));
    return { flowM3h, flowM3s, pressurePa, fanEfficiency, temperatureC, serviceMargin, densityInfo, shaftPower, stdPressure: pressurePa * densityRatio, stdShaftPower: shaftPower * densityRatio, recommendedMotor, hasVfd: VFD_OPTIONS[vfd] };
  }, [altitude, driveType, efficiency, flow, margin, pressure, temperature, vfd]);
  const resultRows = [
    { label: "Hava Debisi", value: `${formatNumber(result.flowM3h)} m³/h` },
    { label: "Hava Yoğunluğu (Deniz Seviyesi, 0 °C)", value: `${formatNumber(1.293, 3)} kg/m³` },
    { label: "Hava Debisi", value: `${formatNumber(result.flowM3s, 3)} m³/s` },
    { label: "Giriş/Atmosfer Basıncı", value: `${formatNumber(result.densityInfo.pressurePa, 0)} Pa` },
    { label: "Emilen Hava Sıcaklığı", value: `${formatNumber(result.temperatureC, 1)} °C` },
    { label: "Toplam Gerçek Basınç Farkı", value: `${formatNumber(result.pressurePa)} Pa` },
    { label: "Toplam Basınç Farkı (@ 1,2 kg/m³ yoğunlukta)", value: `${formatNumber(result.stdPressure)} Pa` },
    { label: "Fan Verimi", value: `%${formatNumber(result.fanEfficiency * 100)}` },
    { label: "Mil Gücü (Actual)", value: `${formatNumber(result.shaftPower)} kW` },
    { label: "Mil Gücü (@ 1,2 kg/m³ yoğunlukta)", value: `${formatNumber(result.stdShaftPower)} kW` },
    { label: "Servis Payı", value: `%${formatNumber(result.serviceMargin)}` },
    { label: "Önerilen Nominal Motor Gücü", value: `${formatNumber(result.recommendedMotor)} kW`, strong: true },
  ];

  return (
    <CalculatorPanel title="Fan Motor Hesabı" description="Masaüstündeki fan güç ekranındaki yoğunluk, mil gücü ve motor seçimi akışı korunur.">
      <div className="fan-calculation-layout">
        <section className="fan-input-panel">
          <div className="technical-panel-subheading">
            <strong>Girdiler</strong>
            <span>Fan çalışma şartları ve seçim parametreleri</span>
          </div>
          <div className="technical-form-grid compact">
            <Field label="Hava debisi (m³/h)"><input value={flow} onChange={(event) => setFlow(event.target.value)} /></Field>
            <Field label="Toplam gerçek basınç farkı (Pa)"><input value={pressure} onChange={(event) => setPressure(event.target.value)} /></Field>
            <Field label="Fan verimi (%)"><input value={efficiency} onChange={(event) => setEfficiency(event.target.value)} /></Field>
            <Field label="Servis payı (%)"><input value={margin} onChange={(event) => setMargin(event.target.value)} /></Field>
            <Field label="Emilen hava sıcaklığı (°C)"><input value={temperature} onChange={(event) => setTemperature(event.target.value)} /></Field>
            <Field label="Rakım (m)"><input value={altitude} onChange={(event) => setAltitude(event.target.value)} /></Field>
            <Field label="Tahrik tipi"><select value={driveType} onChange={(event) => setDriveType(event.target.value as keyof typeof DRIVE_TYPES)}>{Object.keys(DRIVE_TYPES).map((item) => <option key={item}>{item}</option>)}</select></Field>
            <Field label="VFD"><select value={vfd} onChange={(event) => setVfd(event.target.value as keyof typeof VFD_OPTIONS)}>{Object.keys(VFD_OPTIONS).map((item) => <option key={item}>{item}</option>)}</select></Field>
          </div>
        </section>
        <section className="fan-result-panel">
          <div className="technical-panel-subheading fan-result-heading">
            <strong>Sonuçlar</strong>
          </div>
          <div className="fan-result-table">
            {resultRows.map((row, index) => (
              <div className={row.strong ? "fan-result-row strong" : "fan-result-row"} key={`${row.label}-${index}`}>
                <span>{index + 1}. {row.label}</span>
                <strong>{row.value}</strong>
              </div>
            ))}
          </div>
          <div className="fan-export-footer">
            <button type="button" onClick={() => exportRowsToPdf("Fan Motor Gücü Hesaplama Sonuçları", resultRows)}>PDF Export</button>
          </div>
        </section>
      </div>
    </CalculatorPanel>
  );
}

function PressureLossCalculator() {
  type PressureRow = { id: number; tip: string; cap: number; debi: number; hiz: number; miktar: number; kayip: number };
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
    const area = diameterM > 0 ? Math.PI * diameterM ** 2 / 4 : 0;
    const flowM3h = parseNumber(flow);
    const velocity = area > 0 ? flowM3h / area / 3600 : 0;
    const density = airDensity(parseNumber(temperature), parseNumber(altitude)).density;
    const vp = density * velocity ** 2 / 2;
    const constant = PRESSURE_CONSTANTS[Math.round(parseNumber(angle))]?.[parseNumber(rd)] ?? 0;
    const elbowSingle = vp * constant;
    const term = diameterMm > 0 && velocity > 0 ? 0.03 / diameterMm + 68 / (66.4 * diameterMm * velocity) : 0;
    const fpp = term > 0 ? 0.11 * term ** 0.25 : 0;
    const straightPerM = diameterMm > 0 ? ((1000 * (0.85 * fpp + 0.0028)) / diameterMm) * vp * 1.15 * 1.18 : 0;
    const jetCapLoss = 2.5 * ((STANDARD_AIR_DENSITY * velocity ** 2) / 2);
    return { diameterMm, flowM3h, density, area, velocity, elbowSingle, straightPerM, jetCapLoss };
  }, [altitude, angle, diameter, flow, rd, temperature]);
  const totalLoss = rows.reduce((sum, row) => sum + row.kayip, 0);

  function addRow(tip: string, miktar: number, kayip: number) {
    const row = { id: Date.now(), tip, cap: metrics.diameterMm, debi: metrics.flowM3h, hiz: metrics.velocity, miktar, kayip };
    setRows((current) => [...current, row]);
    setSelectedId(row.id);
  }

  return (
    <CalculatorPanel title="Basınç Kaybı Hesaplama" description="Masaüstündeki dirsek, düz kanal, Jet-Cap, ekipman ve toplam liste mantığı web ekranına taşındı.">
      <div className="pressure-loss-layout">
        <section className="pressure-input-panel">
          <div className="technical-panel-subheading">
            <strong>Girdiler</strong>
            <span>Kanal şartları ve eklenecek kayıp tipi</span>
          </div>
          <div className="technical-form-grid compact">
            <Field label="Hava sıcaklığı (°C)"><input value={temperature} onChange={(event) => setTemperature(event.target.value)} /></Field>
            <Field label="Rakım (m)"><input value={altitude} onChange={(event) => setAltitude(event.target.value)} /></Field>
            <Field label="Açı"><select value={angle} onChange={(event) => setAngle(event.target.value)}>{Object.keys(PRESSURE_CONSTANTS).map((item) => <option key={item}>{item}</option>)}</select></Field>
            <Field label="r/D"><select value={rd} onChange={(event) => setRd(event.target.value)}><option>0,75</option><option>1</option><option>1,5</option><option>2</option></select></Field>
            <Field label="Boru çapı (mm)"><input value={diameter} onChange={(event) => setDiameter(event.target.value)} /></Field>
            <Field label="Debi (m³/h)"><input value={flow} onChange={(event) => setFlow(event.target.value)} /></Field>
            <Field label="Dirsek adedi"><input value={elbowCount} onChange={(event) => setElbowCount(event.target.value)} /></Field>
            <Field label="Düz kanal uzunluğu (m)"><input value={length} onChange={(event) => setLength(event.target.value)} /></Field>
            <Field label="Ekipman tipi"><select value={equipmentType} onChange={(event) => setEquipmentType(event.target.value)}><option>Filtre</option><option>Akrobat Kol</option><option>Davlumbaz</option><option>Menfez</option><option>Diğer</option></select></Field>
            <Field label="Ekipman basınç kaybı (Pa)"><input value={equipmentLoss} onChange={(event) => setEquipmentLoss(event.target.value)} /></Field>
          </div>
        </section>

        <section className="pressure-calc-panel">
          <div className="technical-panel-subheading">
            <strong>Hesaplar</strong>
            <span>Anlık hesaplanan değerleri tabloya ekleyin</span>
          </div>
          <div className="pressure-result-list">
            <ResultRow label="Hava yoğunluğu" value={`${formatNumber(metrics.density, 3)} kg/m³`} />
            <ResultRow label="Boru kesit alanı" value={`${formatNumber(metrics.area, 4)} m²`} />
            <ResultRow label="Taşıma hızı" value={`${formatNumber(metrics.velocity)} m/sn`} />
            <ResultRow label="Dirsek kaybı" value={`${formatNumber(metrics.elbowSingle)} Pa/adet`} />
            <ResultRow label="Düz kanal kaybı" value={`${formatNumber(metrics.straightPerM)} Pa/m`} />
            <ResultRow label="Jet-Cap kaybı" value={`${formatNumber(metrics.jetCapLoss)} Pa`} />
          </div>
          <div className="technical-actions vertical">
            <button type="button" onClick={() => addRow("Dirsek", parseNumber(elbowCount), metrics.elbowSingle * parseNumber(elbowCount))}>Dirsek Ekle</button>
            <button type="button" onClick={() => addRow("Düz Kanal", parseNumber(length), metrics.straightPerM * parseNumber(length))}>Düz Kanal Ekle</button>
            <button type="button" onClick={() => addRow("Jet-Cap", 1, metrics.jetCapLoss)}>Jet-Cap Ekle</button>
            <button type="button" onClick={() => addRow(equipmentType, 1, parseNumber(equipmentLoss))}>Ekipman Ekle</button>
          </div>
        </section>

        <section className="pressure-table-panel">
          <div className="technical-panel-subheading pressure-table-heading">
            <div>
              <strong>Basınç Kaybı Tablosu</strong>
              <span>{rows.length ? `${rows.length} öge listede` : "Henüz öge eklenmedi"}</span>
            </div>
            <strong className="pressure-total">{formatNumber(totalLoss)} Pa</strong>
          </div>
          <div className="technical-table pressure-table" role="table" aria-label="Basınç kaybı listesi">
            <div className="technical-table-row header" role="row"><span>ID</span><span>Tip</span><span>Kanal Çapı</span><span>Debi</span><span>Hız</span><span>Miktar</span><span>Basınç Kaybı</span></div>
            {rows.map((row) => (
              <button className={selectedId === row.id ? "technical-table-row selected" : "technical-table-row"} type="button" key={row.id} onClick={() => setSelectedId(row.id)}>
                <span>{row.id}</span><span>{row.tip}</span><span>{formatNumber(row.cap, 0)} mm</span><span>{formatNumber(row.debi, 0)} m³/h</span><span>{formatNumber(row.hiz)} m/sn</span><span>{formatNumber(row.miktar)}</span><span>{formatNumber(row.kayip)} Pa</span>
              </button>
            ))}
            {!rows.length ? <div className="technical-table-empty">Henüz öge eklenmedi.</div> : null}
          </div>
          <div className="technical-actions pressure-table-actions">
            <button type="button" disabled={!selectedId} onClick={() => setRows((current) => current.filter((row) => row.id !== selectedId))}>Seçili Ögeyi Sil</button>
            <button type="button" onClick={() => downloadCsv("basinc-kaybi.csv", ["ID", "Tip", "Kanal Çapı (mm)", "Debi (m³/h)", "Kanal İçi Hız (m/sn)", "Miktar", "Basınç Kaybı (Pa)"], rows.map((row) => [row.id, row.tip, row.cap, row.debi, formatNumber(row.hiz), row.miktar, formatNumber(row.kayip)]))}>CSV'ye Aktar</button>
          </div>
        </section>
      </div>
    </CalculatorPanel>
  );
}

function CapacityCalculatorScreen() {
  const [active, setActive] = useState<CapacityToolKey>("thermal-cutting");
  const modules: Array<{ key: CapacityToolKey; label: string; icon: typeof Gauge }> = [
    { key: "thermal-cutting", label: "Isıl Kesim", icon: Scissors },
    { key: "cnc-lathe", label: "CNC Torna", icon: Gauge },
    { key: "hood", label: "Davlumbaz", icon: Wind },
    { key: "welding-hall", label: "Kaynak Holü", icon: Flame },
  ];
  return (
    <section className="technical-capacity-shell">
      <div className="technical-submodule-bar" aria-label="Kapasite hesap alt modülleri">
        {modules.map((module) => {
          const Icon = module.icon;
          return <button className={active === module.key ? "active" : ""} type="button" key={module.key} onClick={() => setActive(module.key)}><Icon size={18} />{module.label}</button>;
        })}
      </div>
      {active === "thermal-cutting" ? <ThermalCuttingCalculator /> : null}
      {active === "cnc-lathe" ? <CncLatheCapacityCalculator /> : null}
      {active === "hood" ? <HoodCapacityCalculator /> : null}
      {active === "welding-hall" ? <WeldingHallCapacityCalculator /> : null}
    </section>
  );
}

function ThermalCuttingCalculator() {
  const [power, setPower] = useState<keyof typeof THERMAL_CUTTING_POWER_OPTIONS>("12 kW (Laser)");
  const [tightness, setTightness] = useState<keyof typeof VALVE_TIGHTNESS_OPTIONS>("Kötü");
  const [valveCount, setValveCount] = useState("16");
  const [widthMm, setWidthMm] = useState("1500");
  const [lengthMm, setLengthMm] = useState("2000");
  const [reserve, setReserve] = useState("15");
  const result = useMemo(() => {
    const area = (parseNumber(widthMm) * parseNumber(lengthMm)) / 1_000_000;
    const processFlow = THERMAL_CUTTING_POWER_OPTIONS[power] * area;
    const leakageFlow = parseNumber(valveCount) * VALVE_TIGHTNESS_OPTIONS[tightness];
    const required = processFlow + leakageFlow;
    return { area, processFlow, leakageFlow, required, reserved: required * (1 + parseNumber(reserve) / 100) };
  }, [lengthMm, power, reserve, tightness, valveCount, widthMm]);
  return (
    <CalculatorPanel title="Isıl Kesim Kapasite Hesaplama" description="Modül alanı, kesim gücü ve klape sızıntısına göre gerekli emiş kapasitesi.">
      <div className="technical-form-grid">
        <Field label="Kesim gücü"><select value={power} onChange={(event) => setPower(event.target.value as keyof typeof THERMAL_CUTTING_POWER_OPTIONS)}>{Object.keys(THERMAL_CUTTING_POWER_OPTIONS).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Klape sızdırmazlığı"><select value={tightness} onChange={(event) => setTightness(event.target.value as keyof typeof VALVE_TIGHTNESS_OPTIONS)}>{Object.keys(VALVE_TIGHTNESS_OPTIONS).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Valf adedi"><input value={valveCount} onChange={(event) => setValveCount(event.target.value)} /></Field>
        <Field label="Modül genişliği (mm)"><input value={widthMm} onChange={(event) => setWidthMm(event.target.value)} /></Field>
        <Field label="Modül uzunluğu (mm)"><input value={lengthMm} onChange={(event) => setLengthMm(event.target.value)} /></Field>
        <Field label="Emniyet / rezerv payı (%)"><input value={reserve} onChange={(event) => setReserve(event.target.value)} /></Field>
      </div>
      <ResultGrid>
        <ResultRow label="Modül alanı" value={`${formatNumber(result.area, 3)} m²`} />
        <ResultRow label="Proses debisi" value={`${formatNumber(result.processFlow)} m³/h`} />
        <ResultRow label="Klape sızıntı debisi" value={`${formatNumber(result.leakageFlow)} m³/h`} />
        <ResultRow label="Gerekli kapasite" value={`${formatNumber(result.required)} m³/h`} />
        <ResultRow label="Rezerve edilmiş kapasite" value={`${formatNumber(result.reserved)} m³/h`} strong />
      </ResultGrid>
    </CalculatorPanel>
  );
}

function CncLatheCapacityCalculator() {
  const [coolant, setCoolant] = useState<keyof typeof CNC_DEFAULT_VISCOSITY>("Water Soluble");
  const [spindle, setSpindle] = useState("8000");
  const [pressure, setPressure] = useState("100");
  const [space, setSpace] = useState("6");
  const [door, setDoor] = useState<keyof typeof CNC_DOOR_ADJUSTMENT>("Sliding Door, Open on Top");
  const [doorArea, setDoorArea] = useState("1");
  const [cycleTime, setCycleTime] = useState("300");
  const [viscosity, setViscosity] = useState("0,8");
  const result = useMemo(() => {
    const spindlePressureFactor = (0.22 * Math.log(parseNumber(spindle) * parseNumber(pressure)) - 2.4) * 2;
    const processingSpaceMultiplier = 1 + (parseNumber(space) - 1) * 0.5;
    const doorOpeningMultiplier = ((parseNumber(doorArea) - 0.5) * 0.08) * 2;
    const cycleFactor = Math.max(0, -0.0653 * Math.log(parseNumber(cycleTime)) + 0.1419);
    const viscosityValue = parseNumber(viscosity);
    const viscosityFactor = Math.max(1, -0.00002 * viscosityValue ** 2 + 0.0313 * viscosityValue + 0.7349);
    const beforeSafety = (processingSpaceMultiplier * 3600 * 0.2 * (1 + spindlePressureFactor) * (1 + cycleFactor) * (1 + doorOpeningMultiplier) + CNC_DOOR_ADJUSTMENT[door]) / viscosityFactor;
    const requiredAirflow = Math.max(150, beforeSafety) / 1.3;
    const products = coolant === "Straight Oil" ? CNC_HEPA_PRODUCTS : CNC_STANDARD_PRODUCTS;
    const selectedProduct = products.find(([, threshold]) => requiredAirflow <= threshold / viscosityFactor)?.[0] ?? products[products.length - 1][0];
    return { requiredAirflow, selectedProduct, viscosityFactor };
  }, [coolant, cycleTime, door, doorArea, pressure, space, spindle, viscosity]);

  function handleCoolantChange(next: keyof typeof CNC_DEFAULT_VISCOSITY) {
    setCoolant(next);
    setViscosity(CNC_DEFAULT_VISCOSITY[next]);
  }

  return (
    <CalculatorPanel title="CNC Torna Tezgah Kapasite Hesaplama" description="Oil mist filtre seçim aracındaki gerekli hava debisi ve ürün önerisi hesabı.">
      <div className="technical-form-grid">
        <Field label="Soğutma sıvısı tipi"><select value={coolant} onChange={(event) => handleCoolantChange(event.target.value as keyof typeof CNC_DEFAULT_VISCOSITY)}>{Object.keys(CNC_DEFAULT_VISCOSITY).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Maks. iş mili devri (rpm)"><input value={spindle} onChange={(event) => setSpindle(event.target.value)} /></Field>
        <Field label="Soğutma pompası basıncı (bar)"><input value={pressure} onChange={(event) => setPressure(event.target.value)} /></Field>
        <Field label="İşleme hacmi (m³)"><input value={space} onChange={(event) => setSpace(event.target.value)} /></Field>
        <Field label="Kapı tipi"><select value={door} onChange={(event) => setDoor(event.target.value as keyof typeof CNC_DOOR_ADJUSTMENT)}>{Object.keys(CNC_DOOR_ADJUSTMENT).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Kapı açıklık alanı (m²)"><input value={doorArea} onChange={(event) => setDoorArea(event.target.value)} /></Field>
        <Field label="Çevrim süresi (dk)"><input value={cycleTime} onChange={(event) => setCycleTime(event.target.value)} /></Field>
        <Field label="Viskozite (cSt)"><input value={viscosity} onChange={(event) => setViscosity(event.target.value)} /></Field>
      </div>
      <ResultGrid>
        <ResultRow label="Viskozite faktörü" value={formatNumber(result.viscosityFactor, 3)} />
        <ResultRow label="Gerekli hava debisi" value={`${formatNumber(result.requiredAirflow)} m³/h`} strong />
        <ResultRow label="Önerilen ürün" value={result.selectedProduct} />
      </ResultGrid>
    </CalculatorPanel>
  );
}

function HoodCapacityCalculator() {
  const [hoodType, setHoodType] = useState<keyof typeof HOOD_TYPE_FACTORS>("Flanşlı Davlumbaz");
  const [profile, setProfile] = useState<keyof typeof HOOD_CAPTURE_OPTIONS>("Düşük hızlı yayılım (0,5 - 1,0 m/s)");
  const [velocity, setVelocity] = useState("0,75");
  const [distance, setDistance] = useState("0,5");
  const [width, setWidth] = useState("1,2");
  const [length, setLength] = useState("0,8");
  const [reserve, setReserve] = useState("15");
  const result = useMemo(() => {
    const area = parseNumber(width) * parseNumber(length);
    const airflowM3s = HOOD_TYPE_FACTORS[hoodType] * parseNumber(velocity) * (10 * parseNumber(distance) ** 2 + area);
    const airflowM3h = airflowM3s * 3600;
    return { area, airflowM3s, airflowM3h, reserved: airflowM3h * (1 + parseNumber(reserve) / 100) };
  }, [distance, hoodType, length, reserve, velocity, width]);
  return (
    <CalculatorPanel title="Davlumbaz Kapasite Hesaplama" description="Yakalama profili, davlumbaz katsayısı, mesafe ve kesit alanı ile hava debisi.">
      <div className="technical-form-grid">
        <Field label="Davlumbaz tipi"><select value={hoodType} onChange={(event) => setHoodType(event.target.value as keyof typeof HOOD_TYPE_FACTORS)}>{Object.keys(HOOD_TYPE_FACTORS).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Yakalama profili"><select value={profile} onChange={(event) => { const next = event.target.value as keyof typeof HOOD_CAPTURE_OPTIONS; setProfile(next); setVelocity(String(HOOD_CAPTURE_OPTIONS[next]).replace(".", ",")); }}>{Object.keys(HOOD_CAPTURE_OPTIONS).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Yakalama hızı (m/s)"><input value={velocity} onChange={(event) => setVelocity(event.target.value)} /></Field>
        <Field label="Mesafe x (m)"><input value={distance} onChange={(event) => setDistance(event.target.value)} /></Field>
        <Field label="Genişlik (m)"><input value={width} onChange={(event) => setWidth(event.target.value)} /></Field>
        <Field label="Uzunluk (m)"><input value={length} onChange={(event) => setLength(event.target.value)} /></Field>
        <Field label="Güvenlik payı (%)"><input value={reserve} onChange={(event) => setReserve(event.target.value)} /></Field>
      </div>
      <ResultGrid>
        <ResultRow label="Kesit alanı" value={`${formatNumber(result.area, 3)} m²`} />
        <ResultRow label="Hava debisi" value={`${formatNumber(result.airflowM3s, 3)} m³/s`} />
        <ResultRow label="Hava debisi" value={`${formatNumber(result.airflowM3h)} m³/h`} />
        <ResultRow label="Güvenlik paylı debi" value={`${formatNumber(result.reserved)} m³/h`} strong />
      </ResultGrid>
    </CalculatorPanel>
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
    const totalWire = parseNumber(manualCount) * parseNumber(manualWire) + parseNumber(robotCount) * parseNumber(robotWire);
    const fumeFactor = WELDING_FUME_FACTORS[weldingType] ?? 5;
    const totalParticle = totalWire * 1000 * fumeFactor;
    const hallVolume = parseNumber(depth) * parseNumber(width) * parseNumber(height);
    const particleRatio = hallVolume > 0 ? totalParticle / hallVolume : 0;
    const minimumAch = parseNumber(limit) > 0 ? particleRatio / parseNumber(limit) : 0;
    const ach = parseNumber(requestedAch);
    const requiredCapacity = ach >= minimumAch ? hallVolume * ach : 0;
    return { fumeFactor, totalWire, totalParticle, hallVolume, particleRatio, minimumAch, requiredCapacity, validAch: ach >= minimumAch };
  }, [depth, height, limit, manualCount, manualWire, requestedAch, robotCount, robotWire, weldingType, width]);
  return (
    <CalculatorPanel title="Kaynak Hol Havalandırması Kapasite Hesaplama" description="Kaynak prosesi kaynaklı duman yüküne göre minimum ACH ve gerekli kapasite.">
      <div className="technical-form-grid">
        <Field label="Kaynak tipi"><select value={weldingType} onChange={(event) => setWeldingType(event.target.value)}>{Object.keys(WELDING_FUME_FACTORS).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Manuel kaynakçı sayısı"><input value={manualCount} onChange={(event) => setManualCount(event.target.value)} /></Field>
        <Field label="Manuel tel tüketimi (kg/h)"><input value={manualWire} onChange={(event) => setManualWire(event.target.value)} /></Field>
        <Field label="Robot sayısı"><input value={robotCount} onChange={(event) => setRobotCount(event.target.value)} /></Field>
        <Field label="Robot tel tüketimi (kg/h)"><input value={robotWire} onChange={(event) => setRobotWire(event.target.value)} /></Field>
        <Field label="Hol derinliği (m)"><input value={depth} onChange={(event) => setDepth(event.target.value)} /></Field>
        <Field label="Hol genişliği (m)"><input value={width} onChange={(event) => setWidth(event.target.value)} /></Field>
        <Field label="Hol yüksekliği (m)"><input value={height} onChange={(event) => setHeight(event.target.value)} /></Field>
        <Field label="Partikül limit değeri (mg/Nm³)"><input value={limit} onChange={(event) => setLimit(event.target.value)} /></Field>
        <Field label="Gerekli ACH (1/h)"><input value={requestedAch} onChange={(event) => setRequestedAch(event.target.value)} /></Field>
      </div>
      <ResultGrid>
        <ResultRow label="Referans duman katsayısı" value={`${formatNumber(result.fumeFactor, 1)} mg/g`} />
        <ResultRow label="Toplam tel tüketimi" value={`${formatNumber(result.totalWire)} kg/h`} />
        <ResultRow label="Toplam partikül" value={`${formatNumber(result.totalParticle, 0)} mg/h`} />
        <ResultRow label="Hol hacmi" value={`${formatNumber(result.hallVolume)} m³`} />
        <ResultRow label="Minimum ACH" value={`${formatNumber(result.minimumAch)} 1/h`} />
        <ResultRow label="Gerekli kapasite" value={result.validAch ? `${formatNumber(result.requiredCapacity, 0)} m³/h` : "ACH minimumdan düşük"} strong />
      </ResultGrid>
    </CalculatorPanel>
  );
}

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
    const simultaneous = interval > 0 ? Math.ceil((parseNumber(valveCount) * interval) / 60 / 5) : 0;
    const hourlyFreeAir = interval > 0 ? (freeAirNl * simultaneous * (60 / interval) * 60) / 1000 : 0;
    const hourlyCompressedAir = hourlyFreeAir / (parseNumber(pressureBar) + 1);
    const hourlyEnergy = hourlyCompressedAir * DEFAULT_ENERGY_PER_NM3;
    const annualEnergy = parseNumber(annualHours) * hourlyEnergy;
    return { freeAirNl, simultaneous, hourlyFreeAir, hourlyCompressedAir, hourlyEnergy, annualEnergy, annualCost: annualEnergy * parseNumber(kwhPrice) };
  }, [annualHours, kwhPrice, pressureBar, pulseInterval, valveCount, valveType]);
  return (
    <CalculatorPanel title="Basınçlı Hava Tüketimi Hesabı" description="Masaüstündeki patlaç tipi, darbe aralığı, basınç ve enerji maliyeti hesapları korunur.">
      <div className="technical-form-grid">
        <Field label="Patlaç tipi"><select value={valveType} onChange={(event) => setValveType(event.target.value as '1"' | '1 1/2"')}><option>1"</option><option>1 1/2"</option></select></Field>
        <Field label="Patlaç sayısı"><input value={valveCount} onChange={(event) => setValveCount(event.target.value)} /></Field>
        <Field label="2 darbe arası süre (sn)"><input value={pulseInterval} onChange={(event) => setPulseInterval(event.target.value)} /></Field>
        <Field label="Çalışma basıncı (bar)"><input value={pressureBar} onChange={(event) => setPressureBar(event.target.value)} /></Field>
        <Field label="Yıllık çalışma saati"><input value={annualHours} onChange={(event) => setAnnualHours(event.target.value)} /></Field>
        <Field label="kWh birim fiyatı"><input value={kwhPrice} onChange={(event) => setKwhPrice(event.target.value)} /></Field>
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
    </CalculatorPanel>
  );
}

function ExplosionVentCalculator() {
  const [stClass, setStClass] = useState<keyof typeof EXPLOSION_ST_CLASSES>("St1");
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
  const [panel, setPanel] = useState<keyof typeof EXPLOSION_PANEL_AREAS>("586 x 920 mm (0,539 m²)");

  function handleStClass(next: keyof typeof EXPLOSION_ST_CLASSES) {
    setStClass(next);
    setPmax(String(EXPLOSION_ST_CLASSES[next].pmax));
    setKst(String(EXPLOSION_ST_CLASSES[next].kst));
  }

  const result = useMemo(() => {
    const filterVolumeSingle = parseNumber(filterLength) * Math.PI * parseNumber(filterDiameter) ** 2 / 4;
    const filterVolume = parseNumber(filterCount) * filterVolumeSingle;
    const veff = parseNumber(a) * parseNumber(c) * parseNumber(b);
    const leff = parseNumber(b);
    const de = leff > 0 ? 2 * Math.sqrt((veff / leff) / Math.PI) : 0;
    const lOverDe = de > 0 ? Math.max(1, leff / de) : 0;
    const netVolume = veff + parseNumber(c) * parseNumber(d) * (parseNumber(a) + parseNumber(e)) / 2 - filterVolume;
    const predValue = parseNumber(pred);
    const volumeFactor = netVolume > 0 ? netVolume ** 0.753 : 0;
    const term1 = predValue > 0 ? 3.264e-5 * parseNumber(pmax) * parseNumber(kst) * predValue ** -0.569 : 0;
    const term2 = predValue > 0 ? 0.27 * (parseNumber(pstat) - 0.1) * predValue ** -0.5 : 0;
    const bValue = (term1 + term2) * volumeFactor;
    const cValue = predValue > 0 ? -4.305 * Math.log10(predValue) + 0.758 : 0;
    const ventArea = lOverDe > 0 ? bValue * (1 + cValue * Math.log10(lOverDe)) : 0;
    const panelArea = EXPLOSION_PANEL_AREAS[panel];
    const panelCount = panelArea > 0 ? Math.ceil(Math.max(ventArea, 0) / panelArea) : 0;
    const areaOverVolume = volumeFactor > 0 ? ventArea / volumeFactor : 0;
    return { filterVolume, veff, leff, de, lOverDe, netVolume, bValue, cValue, ventArea, panelCount, areaOverVolume };
  }, [a, b, c, d, e, filterCount, filterDiameter, filterLength, kst, panel, pmax, pred, pstat]);

  return (
    <CalculatorPanel title="Patlama Kapağı Hesaplama" description="ST sınıfı, Pred/Pstat, filtre hacmi ve kirli oda ölçülerine göre patlama kapağı alanı ve adedi.">
      <div className="technical-form-grid">
        <Field label="ST sınıfı"><select value={stClass} onChange={(event) => handleStClass(event.target.value as keyof typeof EXPLOSION_ST_CLASSES)}>{Object.keys(EXPLOSION_ST_CLASSES).map((item) => <option key={item}>{item}</option>)}</select></Field>
        <Field label="Pred (bar)"><input value={pred} onChange={(event) => setPred(event.target.value)} /></Field>
        <Field label="Pmax (bar)"><input value={pmax} onChange={(event) => setPmax(event.target.value)} /></Field>
        <Field label="Kst (bar.m/sn)"><input value={kst} onChange={(event) => setKst(event.target.value)} /></Field>
        <Field label="Pstat (bar)"><input value={pstat} onChange={(event) => setPstat(event.target.value)} /></Field>
        <Field label="Filtre sayısı"><input value={filterCount} onChange={(event) => setFilterCount(event.target.value)} /></Field>
        <Field label="Filtre uzunluğu (m)"><input value={filterLength} onChange={(event) => setFilterLength(event.target.value)} /></Field>
        <Field label="Filtre çapı (m)"><input value={filterDiameter} onChange={(event) => setFilterDiameter(event.target.value)} /></Field>
        <Field label="Kirli oda eni a (m)"><input value={a} onChange={(event) => setA(event.target.value)} /></Field>
        <Field label="Kirli oda boyu c (m)"><input value={c} onChange={(event) => setC(event.target.value)} /></Field>
        <Field label="Kirli oda yüksekliği b (m)"><input value={b} onChange={(event) => setB(event.target.value)} /></Field>
        <Field label="Bunker yüksekliği d (m)"><input value={d} onChange={(event) => setD(event.target.value)} /></Field>
        <Field label="Toz döküm açıklığı e (m)"><input value={e} onChange={(event) => setE(event.target.value)} /></Field>
        <Field label="Patlama kapağı seçimi"><select value={panel} onChange={(event) => setPanel(event.target.value as keyof typeof EXPLOSION_PANEL_AREAS)}>{Object.keys(EXPLOSION_PANEL_AREAS).map((item) => <option key={item}>{item}</option>)}</select></Field>
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
      {parseNumber(pred) !== 0.1 || parseNumber(pstat) !== 0.1 ? (
        <p className="technical-note">Masaüstü modüldeki uyarı: Pred ve Pstat için varsayılan değer 0,1 bar. Değiştirilen değerler hesap sonucunu doğrudan etkiler.</p>
      ) : null}
    </CalculatorPanel>
  );
}

function CalculatorPanel({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="technical-calculator-panel">
      <div className="technical-panel-heading">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function ResultGrid({ children }: { children: ReactNode }) {
  return <div className="technical-result-grid">{children}</div>;
}
