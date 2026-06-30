// Teknik Hesaplamalar — masaüstü/Python modüllerinden birebir taşınan
// hesaplama sabitleri ve yardımcı fonksiyonları. Formüller değiştirilmemiştir;
// yalnızca arayüz katmanı projenin tasarım sistemine uyarlanmıştır.

export type TechnicalToolKey =
  | "fan"
  | "pressure-loss"
  | "capacity"
  | "compressed-air"
  | "explosion-vent";

export type CapacityToolKey =
  | "thermal-cutting"
  | "cnc-lathe"
  | "hood"
  | "welding-hall";

export const STANDARD_AIR_DENSITY = 1.2;
export const KELVIN_OFFSET = 273.15;
export const GAS_CONSTANT_DRY_AIR = 287.05;
export const DEFAULT_ENERGY_PER_NM3 = 0.11;

export const STANDARD_MOTOR_POWERS_KW = [
  0.18, 0.25, 0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22,
  30, 37, 45, 55, 75, 90, 110, 132, 160, 200, 250, 315,
];

export const DRIVE_TYPES = { "Direkt akuple": 1, "Kayış kasnak": 0.95 } as const;
export const VFD_OPTIONS = { Var: true, Yok: false } as const;

export const THERMAL_CUTTING_POWER_OPTIONS = {
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
} as const;

export const VALVE_TIGHTNESS_OPTIONS = {
  Kötü: 70,
  Orta: 60,
  İyi: 50,
  "Çok İyi": 40,
} as const;

export const HOOD_TYPE_FACTORS = {
  "Düz Davlumbaz": 1,
  "Flanşlı Davlumbaz": 0.75,
} as const;

export const HOOD_CAPTURE_OPTIONS = {
  "Hafif yayılım (0,3 - 0,5 m/s)": 0.4,
  "Düşük hızlı yayılım (0,5 - 1,0 m/s)": 0.75,
  "Aktif oluşum (1,0 - 2,5 m/s)": 1.75,
  "Yüksek hızlı yayılım (2,5 - 10 m/s)": 4,
} as const;

export const PRESSURE_CONSTANTS: Record<number, Record<number, number>> = {
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

export const CNC_DEFAULT_VISCOSITY = {
  Synthetic: "0,8",
  "Water Soluble": "0,8",
  "Semi-Synthetic": "1",
  "Straight Oil": "10",
} as const;

export const CNC_DOOR_ADJUSTMENT = {
  "Sliding Door, Vertical": -100,
  "Sliding Door, Horizontal": 0,
  "Sliding Door, Open on Top": 250,
} as const;

export const CNC_STANDARD_PRODUCTS: Array<[string, number]> = [
  ["YBFpro MINI", 600],
  ["YBFpro MIDI", 1000],
  ["DT.YBF.1.100.170.7,5.3.50.380.DS.LCD", 1000],
  ["DT.YBF.1.150.170.11.2.50.380.DS.LCD", 1500],
  ["DT.YBF.1.200.170.15.2.50.380.DS.LCD", 2000],
  ["DT.YBF.2.300.170.22.2.50.380.DS.LCD", 3000],
  ["DT.YBF.2.350.170.30.2.50.380.DS.LCD", 3500],
  ["DT.YBF.2.400.170.30.2.50.380.DS.LCD", 4000],
];

export const CNC_HEPA_PRODUCTS: Array<[string, number]> = [
  ["H.YBFpro MINI", 500],
  ["H.YBFpro MIDI", 900],
  ["DT.HYBF.1.100.200.11.2.50.380.DS.LCD", 1000],
  ["DT.HYBF.1.150.200.15.2.50.380.DS.LCD", 1500],
  ["DT.HYBF.1.200.200.22.2.50.380.DS.LCD", 2000],
  ["DT.HYBF.2.300.200.30.2.50.380.DS.LCD", 3000],
  ["DT.HYBF.2.350.200.40.2.50.380.DS.LCD", 3500],
  ["DT.HYBF.2.400.200.40.2.50.380.DS.LCD", 4000],
];

export const WELDING_FUME_FACTORS: Record<string, number> = {
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

export const EXPLOSION_ST_CLASSES = {
  St1: { pmax: 8, kst: 200 },
  St2: { pmax: 9, kst: 300 },
  St3: { pmax: 10, kst: 301 },
} as const;

export const EXPLOSION_PANEL_AREAS = {
  "586 x 920 mm (0,539 m²)": 0.539,
  "320 x 640 mm (0,205 m²)": 0.205,
  "1.020 x 1.020 mm (1,040 m²)": 1.04,
} as const;

export function parseNumber(value: string | number) {
  const raw = String(value ?? "")
    .trim()
    .replace(/\s/g, "");
  if (!raw) return 0;
  const normalized =
    raw.includes(",") && !raw.includes(".")
      ? raw.replace(",", ".")
      : raw.replace(/,/g, "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatNumber(value: number, digits = 2) {
  return new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function selectMotor(requiredKw: number) {
  return (
    STANDARD_MOTOR_POWERS_KW.find((power) => power >= requiredKw) ??
    STANDARD_MOTOR_POWERS_KW[STANDARD_MOTOR_POWERS_KW.length - 1]
  );
}

export function airDensity(temperatureC: number, altitudeM: number) {
  const temperatureK = temperatureC + KELVIN_OFFSET;
  const pressurePa = 101325 * Math.exp(-altitudeM / 8434);
  return {
    pressurePa,
    density: pressurePa / (GAS_CONSTANT_DRY_AIR * temperatureK),
  };
}

export function downloadCsv(
  filename: string,
  header: string[],
  rows: Array<Array<string | number>>,
) {
  const csv = [header, ...rows]
    .map((row) =>
      row
        .map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`)
        .join(";"),
    )
    .join("\n");
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportRowsToPdf(
  title: string,
  rows: Array<{ label: string; value: string; strong?: boolean }>,
) {
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
