export type ModuleInfo = {
  key: string;
  title: string;
  phase: number;
};

export type WizardProduct = {
  key: string;
  title: string;
  description: string;
  status: "active" | "planned" | string;
};

export type WizardOption = {
  label: string;
  value: string;
  description?: string;
  cartridge_count?: number | string | null;
  section_area?: number | string | null;
  filter_area?: number | string | null;
  rise_velocity?: number | string | null;
  filtration_velocity?: number | string | null;
};

export type WizardSection = {
  title: string;
  field: string;
  options?: WizardOption[];
  inputs?: Array<{ field: string; label: string; placeholder?: string }>;
};

export type WizardStep = {
  key: string;
  title: string;
};

export type WizardSchema = {
  key: string;
  title: string;
  description: string;
  initial_state: Record<string, string>;
  steps: WizardStep[];
  sections: Record<string, WizardSection[]>;
};

export type WizardCostSummary = {
  total_cost?: number | null;
  error?: string | null;
  found_codes: string[];
  missing_codes: string[];
  zero_cost_codes: string[];
  costs: Record<string, number | null>;
  is_partial?: boolean;
};

export type WizardPreview = {
  state: Record<string, string>;
  sections: Record<string, WizardSection[]>;
  summary?: Record<string, string | number | null> | null;
  cost: WizardCostSummary;
};

function normalizeWizardPreview(payload: unknown): WizardPreview {
  const obj = (payload && typeof payload === "object" ? payload : {}) as Record<string, unknown>;
  const rawCost =
    obj.cost && typeof obj.cost === "object"
      ? (obj.cost as Record<string, unknown>)
      : {};

  const totalCandidate =
    rawCost.total_cost ?? rawCost.totalCost ?? rawCost.total ?? rawCost.grand_total;

  return {
    state: (obj.state && typeof obj.state === "object" ? obj.state : {}) as Record<string, string>,
    sections:
      (obj.sections && typeof obj.sections === "object" ? obj.sections : {}) as Record<
        string,
        WizardSection[]
      >,
    summary:
      obj.summary && typeof obj.summary === "object"
        ? (obj.summary as Record<string, string | number | null>)
        : null,
    cost: {
      total_cost:
        typeof totalCandidate === "number"
          ? totalCandidate
          : totalCandidate == null || totalCandidate === ""
            ? null
            : Number(totalCandidate),
      error: typeof rawCost.error === "string" ? rawCost.error : null,
      found_codes: asArray<string>(rawCost.found_codes ?? rawCost.found),
      missing_codes: asArray<string>(rawCost.missing_codes ?? rawCost.missing),
      zero_cost_codes: asArray<string>(rawCost.zero_cost_codes ?? rawCost.zero),
      costs:
        rawCost.costs && typeof rawCost.costs === "object"
          ? (rawCost.costs as Record<string, number | null>)
          : {},
    },
  };
}

const FAN_POWER_SUFFIX: Record<string, string> = {
  "2.2 kW": "22.3000",
  "3.0 kW": "30.3000",
  "4.0 kW": "40.3000",
  "5.5 kW": "55.3000",
  "7.5 kW": "75.3000",
  "11.0 kW": "110.3000",
  "15.0 kW": "150.1500",
  "18.5 kW": "185.1500",
  "22.0 kW": "220.1500",
  "30.0 kW": "300.3000",
};

const FILTER_MEDIA_SEGMENTS: Record<string, string> = {
  "nanoBLEND FR": "B135FR",
  "polyMIGHT 55": "255P",
  "polyMIGHT PTFE 65": "265PTFE",
  "polyMIGHT ALU": "260ALU",
  "polyMIGHT ALU PTFE 65": "265ALUPTFE",
  "polyMIGHT HO": "255HO",
  "polyMIGHT HO 55": "255HO",
};

const VERTY_CASE_CODES: Record<string, string> = {
  V66: "VERTY.V66",
  "V66 - Ortam Emisli": "VERTY.V66.BCKDRFT",
  V100: "VERTY.V100",
  "V100 - Ortam Emisli": "VERTY.V100.BCKDRFT",
  V132: "VERTY.V132",
  "V132 - Ortam Emisli": "VERTY.V132.BCKDRFT",
};

const HEXAFIL_FILTER_CODES: Record<string, string> = {
  "nanoBLEND FR|660 mm": "HTM/410/660/B135FR/20 X 6",
  "polyMIGHT 55|660 mm": "HTM/410/660/255P/10 X 6",
  "polyMIGHT PTFE 65|660 mm": "HTM/410/660/265PTFE/10 X 6",
  "polyMIGHT ALU|660 mm": "HTM/410/660/260ALU/10 X 6",
  "polyMIGHT HO 55|660 mm": "HTM/410/660/255HO/10 X 6",
  "polyMIGHT HO|660 mm": "HTM/410/660/255HO/10 X 6",
  "polyMIGHT ALU PTFE 65|660 mm": "HTM/410/660/265ALUPTFE/10 X 6",
  "nanoBLEND FR|1.000 mm": "HTM/410/1000/B135FR/30 X 6",
  "polyMIGHT 55|1.000 mm": "HTM/410/1000/255P/15 X 6",
  "polyMIGHT PTFE 65|1.000 mm": "HTM/410/1000/265PTFE/15 X 6",
  "polyMIGHT ALU|1.000 mm": "HTM/410/1000/260ALU/15 X 6",
  "polyMIGHT HO 55|1.000 mm": "HTM/410/1000/255HO/15 X 6",
  "polyMIGHT HO|1.000 mm": "HTM/410/1000/255HO/15 X 6",
  "polyMIGHT ALU PTFE 65|1.000 mm": "HTM/410/1000/265ALUPTFE/15 X 6",
  "polyMIGHT 55|1.200 mm": "HTM/410/1200/255P/25 X 6",
  "polyMIGHT PTFE 65|1.200 mm": "HTM/410/1200/265PTFE/25 X 6",
  "polyMIGHT ALU|1.200 mm": "HTM/410/1200/260ALU/25 X 6",
  "polyMIGHT HO 55|1.200 mm": "HTM/410/1200/255HO/25 X 6",
  "polyMIGHT HO|1.200 mm": "HTM/410/1200/255HO/25 X 6",
  "polyMIGHT ALU PTFE 65|1.200 mm": "HTM/410/1200/265ALUPTFE/25 X 6",
  "nanoBLEND FR|1.320 mm": "HTM/410/1320/B135FR/40 X 6",
};

const LINE_CARTRIDGE_COUNTS: Record<string, number> = {
  "LINE.8": 8,
  "LINE.12": 12,
  "LINE.18": 18,
  "LINE.24": 24,
  "LINE.32": 32,
  "LINE.36": 36,
};

const PKFC_CARTRIDGE_COUNTS: Record<string, number> = {
  "PKFC.S4": 4,
  "PKFC.S6": 6,
  "PKFC.S8": 8,
  "PKFC.L6": 6,
  "PKFC.L8": 8,
  "PKFC.L10": 10,
};

function normalizeWizardText(value: unknown): string {
  return String(value ?? "").trim();
}

function parseApiNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const parsed = Number(String(value).replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function addCode(codes: string[], code: string | null | undefined) {
  const normalized = normalizeWizardText(code).toUpperCase();
  if (normalized && !codes.includes(normalized)) codes.push(normalized);
}

function fanCode(fanType: string, fanPower: string): string | null {
  const prefix = { "Plug Fan": "BRPF.DA.", "Salyangoz Fan": "BRF.DA." }[fanType];
  const suffix = FAN_POWER_SUFFIX[fanPower];
  return prefix && suffix ? `${prefix}${suffix}` : null;
}

function ecogFilterCode(filterMedia: string, filterLength: string, filterVariant: string) {
  const cartridgeCount = Number(filterVariant.split(".")[1]);
  const shortLength = { "660 mm": "660", "1.000 mm": "1000" }[filterLength];
  const mediaCode = FILTER_MEDIA_SEGMENTS[filterMedia];
  if (!cartridgeCount || !shortLength || !mediaCode) return null;
  const pieceLabel = filterMedia === "nanoBLEND FR" ? (filterLength === "660 mm" ? "20" : "30") : filterLength === "660 mm" ? "10" : "15";
  return `HTM/327G/${shortLength}/${mediaCode}/${pieceLabel} x ${cartridgeCount}`;
}

function ecogPanelCode(panel: string, fanPower: string): string | null {
  if (panel === "Motor Koruma Salteri") {
    return { "2.2 kW": "ECOG.MPS.380.50.22", "3.0 kW": "ECOG.MPS.380.50.30", "4.0 kW": "ECOG.MPS.380.50.40" }[fanPower] ?? null;
  }
  if (panel === "Yildiz Ucgen") {
    return {
      "5.5 kW": "ECOG.DS.380.50.55",
      "7.5 kW": "ECOG.DS.380.50.75",
      "11.0 kW": "ECOG.DS.380.50.110",
      "15.0 kW": "ECOG.DS.380.50.150",
      "18.5 kW": "ECOG.DS.380.50.185",
      "22.0 kW": "ECOG.DS.380.50.220",
      "30.0 kW": "ECOG.DS.380.50.300",
    }[fanPower] ?? null;
  }
  if (panel === "Frekans Invertoru") {
    return {
      "2.2 kW": "KMPKT.VFD.380.50.22",
      "3.0 kW": "KMPKT.VFD.380.50.30",
      "4.0 kW": "KMPKT.VFD.380.50.40",
      "5.5 kW": "KMPKT.VFD.380.50.55",
      "7.5 kW": "KMPKT.VFD.380.50.75",
      "11.0 kW": "KMPKT.VFD.380.50.110",
      "15.0 kW": "KMPKT.VFD.380.50.150",
      "18.5 kW": "KMPKT.VFD.380.50.185",
      "22.0 kW": "KMPKT.VFD.380.50.220",
      "30.0 kW": "KMPKT.VFD.380.50.300",
    }[fanPower] ?? null;
  }
  return null;
}

function cartridgeFilterCode(wizardKey: string, filterMedia: string, filterLength: string, filterVariant: string) {
  const countMap = wizardKey === "line" ? LINE_CARTRIDGE_COUNTS : PKFC_CARTRIDGE_COUNTS;
  const cartridgeCount = countMap[filterVariant];
  const mediaCode = FILTER_MEDIA_SEGMENTS[filterMedia];
  if (!cartridgeCount || !mediaCode) return null;
  if (wizardKey === "line") return `HTM/500/480/1000/${mediaCode}/5 x ${cartridgeCount}`;
  const lengthCode = { "660 mm": "660", "1.000 mm": "1000", "1.200 mm": "1200", "1.320 mm": "1320" }[filterLength];
  const pieceArea = filterLength === "660 mm" ? (filterMedia === "nanoBLEND FR" ? 20 : 10) : filterLength === "1.000 mm" ? (filterMedia === "nanoBLEND FR" ? 30 : 15) : filterLength === "1.200 mm" ? 25 : filterLength === "1.320 mm" ? 40 : null;
  return lengthCode && pieceArea ? `HTM/327G/${lengthCode}/${mediaCode}/${pieceArea} x ${cartridgeCount}` : null;
}

function cartridgePanelCode(wizardKey: string, panel: string, fanPower: string): string | null {
  const prefix = wizardKey === "line" ? "LINE" : "PKFC";
  if (panel === "Motor Koruma Salteri") {
    return { "2.2 kW": `${prefix}.MPS.380.50.22`, "3.0 kW": `${prefix}.MPS.380.50.30`, "4.0 kW": `${prefix}.MPS.380.50.40` }[fanPower] ?? null;
  }
  if (panel === "Yildiz Ucgen") {
    return {
      "5.5 kW": `${prefix}.DS.380.50.55`,
      "7.5 kW": `${prefix}.DS.380.50.75`,
      "11.0 kW": `${prefix}.DS.380.50.110`,
      "15.0 kW": `${prefix}.DS.380.50.150`,
      "18.5 kW": `${prefix}.DS.380.50.185`,
      "22.0 kW": `${prefix}.DS.380.50.220`,
      "30.0 kW": `${prefix}.DS.380.50.300`,
    }[fanPower] ?? null;
  }
  return panel === "Frekans Invertoru" ? ecogPanelCode(panel, fanPower) : null;
}

function vertyPanelCode(panel: string, fanPower: string): string | null {
  if (panel === "HARIC") return null;
  const prefix = { "Motor Koruma Salteri": "VERTY.MPS.380.50.", "Yildiz Ucgen": "VERTY.DS.380.50.", "Frekans Invertoru": "KMPKT.VFD.380.50." }[panel];
  const suffix = { "2.2 kW": "22", "3.0 kW": "30", "4.0 kW": "40", "5.5 kW": "55", "7.5 kW": "75", "11.0 kW": "110" }[fanPower];
  return prefix && suffix ? `${prefix}${suffix}` : null;
}

function buildWizardProductCodes(wizardKey: string, state: Record<string, unknown>, summary?: Record<string, string | number | null> | null) {
  const fromSummary = ["kasaKodu", "filtreSetKodu", "temizlikKodu", "fanKodu", "fanKabiniKodu", "fanModulKodu", "sesIzolasyonKodu", "panoKodu", "tozBosaltmaKodu", "susturucuKodu"]
    .map((key) => normalizeWizardText(summary?.[key]))
    .filter(Boolean);
  if (fromSummary.length > 0) return Array.from(new Set(fromSummary.map((code) => code.toUpperCase())));

  const key = wizardKey.toLowerCase();
  const codes: string[] = [];
  const fanType = normalizeWizardText(state.fan_type);
  const fanPower = normalizeWizardText(state.fan_power);
  const filterMedia = normalizeWizardText(state.filter_media);
  const filterLength = normalizeWizardText(state.filter_length);
  const filterVariant = normalizeWizardText(state.filter_variant);
  const cleaning = normalizeWizardText(state.cleaning);
  const panel = normalizeWizardText(state.panel);

  if (key === "ecog") {
    addCode(codes, filterVariant && filterLength ? `${filterVariant}.${filterLength === "660 mm" ? "66" : "100"}` : null);
    addCode(codes, filterMedia && filterLength && filterVariant ? ecogFilterCode(filterMedia, filterLength, filterVariant) : null);
    addCode(codes, cleaning === "B-CONTROL" ? "SCHDL.CLEAN" : cleaning === "ECON" && ["ECOG.3", "ECOG.4"].includes(filterVariant) ? "ECOG.ECON.4" : cleaning === "ECON" && ["ECOG.6", "ECOG.8"].includes(filterVariant) ? "ECOG.ECON.8" : null);
    addCode(codes, fanCode(fanType, fanPower));
    addCode(codes, ecogPanelCode(panel, fanPower));
  } else if (key === "line" || key === "pkfc") {
    addCode(codes, filterVariant);
    addCode(codes, filterMedia && filterLength && filterVariant ? cartridgeFilterCode(key, filterMedia, filterLength, filterVariant) : null);
    if (key === "line") {
      const lineEconomizer: Record<string, string> = { "LINE.8": "LINE.ECON.4", "LINE.12": "LINE.ECON.8", "LINE.18": "LINE.ECON.12", "LINE.24": "LINE.ECON.12", "LINE.32": "LINE.ECON.16", "LINE.36": "LINE.ECON.20" };
      const lineBControl: Record<string, string> = { "LINE.8": "LINE.LCD.9", "LINE.12": "LINE.LCD.9", "LINE.18": "LINE.LCD.9", "LINE.24": "LINE.LCD.18", "LINE.32": "LINE.LCD.18", "LINE.36": "LINE.LCD.18" };
      addCode(codes, cleaning === "ECON" ? lineEconomizer[filterVariant] : cleaning === "B-CONTROL" ? lineBControl[filterVariant] : null);
    } else {
      const pkfcEconomizer: Record<string, string> = { "PKFC.S4": "PKFC.ECON.4", "PKFC.S6": "PKFC.ECON.8", "PKFC.S8": "PKFC.ECON.8", "PKFC.L6": "PKFC.ECON.8", "PKFC.L8": "PKFC.ECON.8", "PKFC.L10": "PKFC.ECON.12" };
      addCode(codes, cleaning === "B-CONTROL" ? "SCHDL.CLEAN" : cleaning === "ECON" ? pkfcEconomizer[filterVariant] : null);
    }
    addCode(codes, fanCode(fanType, fanPower));
    addCode(codes, cartridgePanelCode(key, panel, fanPower));
  } else if (key === "hexafil") {
    const caseValue = normalizeWizardText(state.case);
    const typeValue = normalizeWizardText(state.type);
    const isFanExcluded = normalizeWizardText(state.is_fan_excluded).toLowerCase() === "true";
    addCode(codes, caseValue && typeValue ? `HEXA.${typeValue.replace(/\s/g, "")}.${caseValue.replace(" Kasa", "").replace(/\s/g, "")}` : null);
    addCode(codes, HEXAFIL_FILTER_CODES[`${filterMedia}|${filterLength}`]);
    addCode(codes, cleaning === "ECON" ? "HEXAFIL.ECON.8" : cleaning === "B-CONTROL" ? "SCHDL.CLEAN" : null);
    if (!isFanExcluded) {
      const fanKw = Number(fanPower.replace(" kW", ""));
      addCode(codes, fanType === "Plug Fan" && fanKw > 11 ? null : fanType === "Salyangoz Fan" && fanKw > 22 ? null : fanCode(fanType, fanPower));
      addCode(codes, normalizeWizardText(state.fan_cabin) === "Fan Kabini" && typeValue ? `HEXAFIL.FANCABIN.${typeValue.replace(/\s/g, "").toUpperCase()}` : null);
      addCode(codes, normalizeWizardText(state.sound) === "EKLE" && typeValue ? `HEXAFIL.SOUNDINS.${typeValue.replace(/\s/g, "").toUpperCase()}` : null);
      addCode(codes, vertyPanelCode(panel, fanPower) ?? ecogPanelCode(panel, fanPower));
      addCode(codes, { "Kanal Tipi": "SILENCER.DUCT.500", "Dirsek Tipi": "SILENCER.ELBOW" }[normalizeWizardText(state.silencer)]);
    }
  } else if (key === "verty") {
    const caseValue = normalizeWizardText(state.case);
    const fanModule = normalizeWizardText(state.fan_module);
    addCode(codes, VERTY_CASE_CODES[caseValue]);
    addCode(codes, filterMedia && filterLength ? (HEXAFIL_FILTER_CODES[`${filterMedia}|${filterLength}`]?.replace(" X 6", " x 4") ?? null) : null);
    addCode(codes, cleaning === "B-CONTROL" ? "SCHDL.CLEAN" : null);
    addCode(codes, fanCode(fanType, fanPower));
    addCode(codes, fanModule && fanModule !== "HARIC" ? fanModule : null);
    addCode(codes, normalizeWizardText(state.sound) === "EKLE" && ["VERTY.FAN.700", "VERTY.FAN.900"].includes(fanModule) ? `${fanModule}.SOUNDINS` : null);
    addCode(codes, vertyPanelCode(panel, fanPower));
    addCode(codes, normalizeWizardText(state.dust) === "Toz Kovasi" ? "VERTY.BIN" : null);
    addCode(codes, { "Kanal Tipi": "SILENCER.DUCT.500", "Dirsek Tipi": "SILENCER.ELBOW" }[normalizeWizardText(state.silencer)]);
  }

  return codes;
}

async function fetchProductCostsByCodes(token: string, codes: string[]) {
  const uniqueCodes = Array.from(new Set(codes.map((code) => code.toUpperCase()).filter(Boolean)));
  if (uniqueCodes.length === 0) return null;

  const entries = await Promise.all(
    uniqueCodes.map(async (code) => {
      const params = new URLSearchParams({ search: code, limit: "10" });
      const response = await apiFetch(`${API_BASE_URL}/products?${params.toString()}`, {
        headers: authHeaders(token),
      });
      if (!response.ok) throw new Error(await parseError(response));
      const rows = asArray<ProductInfo>(await response.json());
      const exact = rows.find((row) => normalizeWizardText(row.urun_kodu).toUpperCase() === code);
      return [code, parseApiNumber(exact?.maliyet)] as const;
    }),
  );

  const costs = Object.fromEntries(entries);
  const found_codes = entries.filter(([, value]) => value !== null).map(([code]) => code);
  const missing_codes = entries.filter(([, value]) => value === null).map(([code]) => code);
  const zero_cost_codes = entries.filter(([, value]) => value === 0).map(([code]) => code);
  return {
    total_cost: found_codes.length ? found_codes.reduce((sum, code) => sum + (costs[code] ?? 0), 0) : null,
    found_codes,
    missing_codes,
    zero_cost_codes,
    costs,
    is_partial: true,
  } satisfies WizardCostSummary;
}

async function enrichWizardPreviewCost(token: string, wizardKey: string, preview: WizardPreview): Promise<WizardPreview> {
  if (preview.cost.total_cost != null || Object.keys(preview.cost.costs).length > 0) return preview;
  const codes = buildWizardProductCodes(wizardKey, preview.state, preview.summary);
  try {
    const liveCost = await fetchProductCostsByCodes(token, codes);
    return liveCost ? { ...preview, cost: liveCost } : preview;
  } catch {
    return preview;
  }
}

export type UserInfo = {
  id: number;
  kullanici_adi: string;
  rol_id?: number | null;
  rol_adi?: string | null;
  module_permissions: Record<string, boolean>;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserInfo;
};

export type MessageResponse = {
  status: string;
  message: string;
};

export type MaterialInfo = {
  id: number;
  malzeme_kodu?: string | null;
  malzeme_tipi?: string | null;
  ad?: string | null;
  fiyat?: number | null;
  guncelleme_tarihi?: string | null;
};

export type MaterialFixedCostItem = {
  kalem_adi: string;
  birim_fiyat?: number | null;
};

export type MaterialAddOptions = {
  next_yari_mamul_code: string;
  fixed_cost_items: MaterialFixedCostItem[];
};

export type MaterialCreatePayload = {
  malzeme_kodu: string;
  malzeme_tipi: string;
  ad: string;
  birim_fiyat: string | number;
};

export type MaterialUsageProduct = {
  urun_kodu?: string | null;
  urun_adi?: string | null;
};

export type MaterialDetail = {
  material: MaterialInfo;
  used_products: MaterialUsageProduct[];
};

export type MaterialDeleteResponse = {
  material_id: number;
  message: string;
};

export type MaterialImportResultItem = {
  row_number: number;
  malzeme_kodu?: string | null;
  ad?: string | null;
  status: "inserted" | "existing" | "failed" | string;
  message: string;
};

export type MaterialImportResponse = {
  total_count: number;
  inserted_count: number;
  existing_count: number;
  failed_count: number;
  items: MaterialImportResultItem[];
};

export type ProductInfo = {
  id: number;
  urun_kodu?: string | null;
  urun_adi?: string | null;
  urun_kategorisi?: string | null;
  urun_tipi?: string | null;
  urun_modeli?: string | null;
  maliyet?: number | null;
  filtre_medyasi?: string | null;
  filtre_medyasi_kodu?: string | null;
  patlac_kumanda_tipi?: string | null;
  toplam_filtre_alani?: number | string | null;
  debi?: number | string | null;
  fan_basinc?: number | string | null;
  fan_basinc_birimi?: string | null;
  motor?: string | null;
  fan_kumanda_tipi?: string | null;
  patlama_kapagi?: string | null;
  filtre_elemani_sayisi?: number | string | null;
  maliyet_hesaplama_tarihi?: string | null;
};

export type ProductTreeItem = {
  id: number;
  kod?: string | null;
  ad?: string | null;
  miktar?: number | null;
};

export type ProductLabor = {
  iscilik_tipi?: string | null;
  usta_saat?: number | string | null;
  yardimci_saat?: number | string | null;
};

export type ProductDetailField = {
  key: string;
  label: string;
  value?: string | number | null;
};

export type ProductCostBreakdown = {
  malzeme_maliyeti?: number | string | null;
  iscilik_maliyeti?: number | string | null;
  uretim_gideri?: number | string | null;
  yonetim_gideri?: number | string | null;
  alt_urun_maliyeti?: number | string | null;
  toplam_maliyet?: number | string | null;
};

export type ProductDetail = {
  product: Record<string, string | number | null>;
  display_fields: ProductDetailField[];
  cost_breakdown: ProductCostBreakdown;
  labor_rows: ProductLabor[];
  channel_fields: ProductDetailField[];
  flange_fields: ProductDetailField[];
};

export type ProductEditOptions = {
  category_options: string[];
  type_options_by_category: Record<string, string[]>;
  field_options: Record<string, string[]>;
  filter_media_code_map: Record<string, string>;
};

export type ProductUpdatePayload = {
  fields: Record<string, string | number | null>;
  labor_rows: ProductLabor[];
  recalculate_cost: boolean;
};

export type ProductUpdateResponse = {
  product_id: number;
  updated_fields: string[];
  labor_updated: boolean;
  cost_recalculated: boolean;
  recalculation_error?: string | null;
  detail: ProductDetail;
};

export type ProductDeleteResponse = {
  product_id: number;
  deleted_count: number;
  blocked_count: number;
  message: string;
};

export type ProductCopyResponse = {
  source_product_id: number;
  new_product_id: number;
  new_product_code: string;
  cost_recalculated: boolean;
  recalculation_error?: string | null;
  detail: ProductDetail;
};

export type ProductCostRevisionResponse = {
  requested_count: number;
  updated_count: number;
  failed_count: number;
  message: string;
};

export type ProductTreeDeleteResponse = {
  deleted_count: number;
  message: string;
};

export type ProductTreeMaterial = {
  kod: string;
  ad: string;
  malzeme_tipi: string;
};

export type ProductTreeMaterialAddItem = ProductTreeMaterial & {
  miktar: number;
};

export type ProductTreeMaterialAddResponse = {
  inserted_count: number;
  message: string;
};

export type ProductTreeMaterialResolveItem = {
  kod: string;
  ad: string;
  found: boolean;
};

export type ProductTreeRecalculateResponse = {
  product_id: number;
  cost_recalculated: boolean;
  recalculation_error?: string | null;
  detail: ProductDetail;
};

export type ProductTree = {
  product_id: number;
  stats: Record<string, number>;
  yari_mamuller: ProductTreeItem[];
  mamuller: ProductTreeItem[];
  alt_urunler: ProductTreeItem[];
  iscilikler: ProductLabor[];
};

export type LeaveBalance = {
  annual_allowance_days?: number | null;
  carried_over_days?: number | null;
  reserved_days?: number | null;
  used_days?: number | null;
  pending_approval_days?: number | null;
  available_days?: number | null;
  updated_at?: string | null;
};

export type LeaveRequestInfo = {
  id: number;
  user_id?: number | null;
  user_name?: string | null;
  manager_user_id?: number | null;
  leave_type?: string | null;
  approval_mode?: string | null;
  status?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  requested_days?: number | null;
  reserved_days?: number | null;
  approved_days?: number | null;
  actual_used_days?: number | null;
  remaining_days_after?: number | null;
  reason?: string | null;
  employee_note?: string | null;
  manager_note?: string | null;
  usage_confirmation_requested_at?: string | null;
  finalized_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type LeaveDashboard = {
  balance: LeaveBalance;
  my_requests: LeaveRequestInfo[];
  manager_requests: LeaveRequestInfo[];
  pending_manager_requests: LeaveRequestInfo[];
};

export type LeaveWorkdaySummary = {
  start_date: string;
  end_date: string;
  work_days: number;
};

export type LeaveCreatePayload = {
  leave_type: string;
  start_date: string;
  end_date: string;
  requested_days: number;
  reason?: string | null;
  employee_note?: string | null;
};

export type LeaveApprovePayload = {
  approval_mode: "BAKIYEDEN_DUSECEK" | "YONETICI_IZNI";
  approved_days?: number | null;
  manager_note?: string | null;
};

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  (import.meta.env.DEV ? "http://127.0.0.1:8100" : "");

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
const REQUEST_TIMEOUT_MS = 15000;
const LOGIN_TIMEOUT_MS = 60000;

async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  if (!API_BASE_URL) {
    throw new Error("API adresi yapılandırılmamış (VITE_API_BASE_URL). Lütfen yöneticinizle iletişime geçin.");
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("API yanıt vermedi. Lütfen backend servisinin çalıştığını kontrol edin.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}


async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || "İşlem tamamlanamadı.";
  } catch {
    return "İşlem tamamlanamadı.";
  }
}

// The list endpoints normally return a bare JSON array, but some deployments
// wrap the rows in an object ({ items: [...] } / { data: [...] }). Normalize so
// the UI always receives an array and never crashes on `.reduce`/`.map`.
function asArray<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    for (const key of ["items", "data", "results", "rows"]) {
      if (Array.isArray(obj[key])) return obj[key] as T[];
    }
  }
  return [];
}

function authHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function login(kullaniciAdi: string, sifre: string): Promise<LoginResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      kullanici_adi: kullaniciAdi,
      sifre,
    }),
  }, LOGIN_TIMEOUT_MS);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LoginResponse;
}

export async function signup(kullaniciAdi: string, email: string, sifre: string): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      kullanici_adi: kullaniciAdi,
      email,
      sifre,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function sendEmailVerification(email: string): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/email/send-verification`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function verifyEmailCode(email: string, code: string): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/email/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, code }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function sendPasswordResetCode(identifier: string): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/password/send-reset-code`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ identifier }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function resetPasswordWithCode(identifier: string, code: string, newPassword: string): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/password/reset`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      identifier,
      code,
      new_password: newPassword,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function fetchMe(token: string): Promise<UserInfo> {
  const response = await apiFetch(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as UserInfo;
}

export async function fetchModules(token: string): Promise<ModuleInfo[]> {
  const response = await apiFetch(`${API_BASE_URL}/modules`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as { modules?: ModuleInfo[] };
  return payload.modules ?? [];
}

export async function fetchWizardProducts(token: string): Promise<WizardProduct[]> {
  const response = await apiFetch(`${API_BASE_URL}/selection-wizard/products`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as { products?: WizardProduct[] };
  return payload.products ?? [];
}

export async function fetchWizardSchema(token: string, wizardKey: string): Promise<WizardSchema> {
  const response = await apiFetch(`${API_BASE_URL}/selection-wizard/${wizardKey}/schema`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as WizardSchema;
}

export async function previewWizard(token: string, wizardKey: string, state: Record<string, string>): Promise<WizardPreview> {
  const response = await apiFetch(`${API_BASE_URL}/selection-wizard/${wizardKey}/preview`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ state }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const preview = normalizeWizardPreview(await response.json());
  return enrichWizardPreviewCost(token, wizardKey, preview);
}

export async function fetchLeaveDashboard(token: string): Promise<LeaveDashboard> {
  const response = await apiFetch(`${API_BASE_URL}/leave/dashboard`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveDashboard;
}

export async function fetchLeaveWorkdaySummary(token: string, startDate: string, endDate: string): Promise<LeaveWorkdaySummary> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  const response = await apiFetch(`${API_BASE_URL}/leave/workday-summary?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveWorkdaySummary;
}

export async function createLeaveRequest(token: string, payload: LeaveCreatePayload): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function cancelLeaveRequest(token: string, requestId: number): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests/${requestId}/cancel`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function approveLeaveRequest(token: string, requestId: number, payload: LeaveApprovePayload): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests/${requestId}/approve`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function rejectLeaveRequest(token: string, requestId: number, managerNote?: string): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests/${requestId}/reject`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ manager_note: managerNote?.trim() || null }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function markLeaveUsageConfirmation(token: string, requestId: number): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests/${requestId}/mark-usage-confirmation`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function finalizeLeaveRequest(token: string, requestId: number, actualUsedDays: number, managerNote?: string): Promise<LeaveRequestInfo> {
  const response = await apiFetch(`${API_BASE_URL}/leave/requests/${requestId}/finalize`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ actual_used_days: actualUsedDays, manager_note: managerNote?.trim() || null }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LeaveRequestInfo;
}

export async function fetchMaterials(token: string, search = ""): Promise<MaterialInfo[]> {
  const params = new URLSearchParams({ limit: "10000" });
  if (search.trim()) {
    params.set("search", search.trim());
  }
  const response = await apiFetch(`${API_BASE_URL}/materials?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return asArray<MaterialInfo>(await response.json());
}

export async function fetchMaterialAddOptions(token: string): Promise<MaterialAddOptions> {
  const response = await apiFetch(`${API_BASE_URL}/materials/add-options`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialAddOptions;
}

export async function createMaterial(token: string, payload: MaterialCreatePayload): Promise<MaterialInfo> {
  const response = await apiFetch(`${API_BASE_URL}/materials`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialInfo;
}

export async function fetchMaterialDetail(token: string, materialId: number): Promise<MaterialDetail> {
  const response = await apiFetch(`${API_BASE_URL}/materials/${materialId}/detail`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialDetail;
}

export async function updateMaterial(token: string, materialId: number, payload: MaterialCreatePayload): Promise<MaterialDetail> {
  const response = await apiFetch(`${API_BASE_URL}/materials/${materialId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialDetail;
}

export async function deleteMaterial(token: string, materialId: number): Promise<MaterialDeleteResponse> {
  const response = await apiFetch(`${API_BASE_URL}/materials/${materialId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialDeleteResponse;
}

export async function importMamulMaterials(token: string, file: File): Promise<MaterialImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiFetch(`${API_BASE_URL}/materials/import`, {
    method: "POST",
    headers: authHeaders(token),
    body: formData,
  }, 60000);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MaterialImportResponse;
}

// Categories the backend's product-list query excludes. Mirrored client-side so
// the "listable" count matches the data layer even if the deployed endpoint
// returns the raw set.
const EXCLUDED_PRODUCT_CATEGORIES = new Set([
  "ÖZEL TASARIM ÜRÜNLER",
  "KANAL",
  "KANAL_LISTESI",
  "FLANŞ",
]);

async function fetchProductsPage(
  token: string,
  page: number,
  search: string,
): Promise<{ items: ProductInfo[]; total?: number; pageSize?: number; isArray: boolean }> {
  // Send both `limit` (flat-list backend, up to 10000) and `page`
  // (paginated backend whose page_size is fixed at 200).
  const params = new URLSearchParams({ limit: "10000", page: String(page) });
  if (search.trim()) {
    params.set("search", search.trim());
  }
  const response = await apiFetch(`${API_BASE_URL}/products?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as unknown;
  if (Array.isArray(payload)) {
    return { items: payload as ProductInfo[], isArray: true };
  }
  const obj = payload as { items?: unknown; total?: number; page_size?: number };
  return {
    items: asArray<ProductInfo>(Array.isArray(obj.items) ? obj.items : payload),
    total: typeof obj.total === "number" ? obj.total : undefined,
    pageSize: typeof obj.page_size === "number" ? obj.page_size : undefined,
    isArray: false,
  };
}

export async function fetchProducts(token: string, search = ""): Promise<ProductInfo[]> {
  const byId = new Map<number, ProductInfo>();
  const ordered: ProductInfo[] = [];

  const addItems = (items: ProductInfo[]) => {
    for (const item of items) {
      if (typeof item?.id === "number") {
        if (byId.has(item.id)) continue;
        byId.set(item.id, item);
      }
      ordered.push(item);
    }
  };

  // Fetch the first page to learn the pagination shape.
  const first = await fetchProductsPage(token, 1, search);
  addItems(first.items);

  // Flat array (everything in one response) → done.
  if (!first.isArray && first.total !== undefined) {
    const pageSize = first.pageSize && first.pageSize > 0 ? first.pageSize : first.items.length || 200;
    const totalPages = Math.min(50, Math.ceil(first.total / pageSize));

    if (totalPages > 1) {
      // Fetch remaining pages in parallel, in capped batches to avoid hammering.
      const pages = Array.from({ length: totalPages - 1 }, (_, i) => i + 2);
      const BATCH = 6;
      for (let i = 0; i < pages.length; i += BATCH) {
        const batch = pages.slice(i, i + BATCH);
        const results = await Promise.all(
          batch.map((p) => fetchProductsPage(token, p, search)),
        );
        for (const r of results) addItems(r.items);
      }
    }
  }

  // Mirror the backend's category exclusion so the listable count is correct.
  return ordered.filter(
    (p) => !EXCLUDED_PRODUCT_CATEGORIES.has((p.urun_kategorisi ?? "").toUpperCase()),
  );
}

// Lightweight version stamp that changes whenever any product cost is
// recalculated/revised on the backend. We fold it into the products query
// key so the heavy list refetches automatically when costs change, while
// staying instant (served from the persisted cache) when nothing changed.
export async function fetchCostVersion(token: string): Promise<string> {
  const response = await apiFetch(`${API_BASE_URL}/products/cost-version`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as unknown;
  if (typeof payload === "string") return payload;
  if (typeof payload === "number") return String(payload);
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    const candidate =
      obj.version ??
      obj.cost_version ??
      obj.hash ??
      obj.etag ??
      obj.value ??
      obj.updated_at ??
      obj.last_updated ??
      obj.timestamp;
    if (candidate != null) return String(candidate);
  }
  return JSON.stringify(payload);
}

export async function fetchProductTree(token: string, productId: number): Promise<ProductTree> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}/tree`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTree;
}

export async function fetchProductDetail(token: string, productId: number): Promise<ProductDetail> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}/detail`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductDetail;
}

export async function fetchProductEditOptions(token: string): Promise<ProductEditOptions> {
  const response = await apiFetch(`${API_BASE_URL}/products/edit-options`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductEditOptions;
}

export async function updateProduct(token: string, productId: number, payload: ProductUpdatePayload): Promise<ProductUpdateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductUpdateResponse;
}

export async function deleteProduct(token: string, productId: number): Promise<ProductDeleteResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductDeleteResponse;
}

export async function copyProduct(token: string, productId: number, newProductCode: string): Promise<ProductCopyResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}/copy`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ new_product_code: newProductCode }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductCopyResponse;
}

export async function reviseProductCosts(token: string, productIds: number[]): Promise<ProductCostRevisionResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/revise-costs`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_ids: productIds }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductCostRevisionResponse;
}

export async function updateProductTreeItemQuantity(token: string, itemId: number, miktar: number): Promise<ProductTreeItem> {
  const response = await apiFetch(`${API_BASE_URL}/products/tree-items/${itemId}`, {
    method: "PATCH",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ miktar }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeItem;
}

export async function deleteProductTreeItems(token: string, itemIds: number[]): Promise<ProductTreeDeleteResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/tree-items/delete`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ item_ids: itemIds }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeDeleteResponse;
}

export async function searchProductTreeMaterials(token: string, materialType: string, search = ""): Promise<ProductTreeMaterial[]> {
  const params = new URLSearchParams({ material_type: materialType });
  if (search.trim()) {
    params.set("q", search.trim());
  }
  const response = await apiFetch(`${API_BASE_URL}/products/tree-materials/search?${params.toString()}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeMaterial[];
}

export async function addProductTreeMaterials(token: string, productId: number, items: ProductTreeMaterialAddItem[]): Promise<ProductTreeMaterialAddResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/tree-materials`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_id: productId, items }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeMaterialAddResponse;
}

export async function resolveProductTreeMaterialCodes(token: string, codes: string[]): Promise<ProductTreeMaterialResolveItem[]> {
  const response = await apiFetch(`${API_BASE_URL}/products/tree-materials/resolve`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ codes }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as { items?: ProductTreeMaterialResolveItem[] };
  return payload.items ?? [];
}

export async function saveProductTreeLabor(token: string, productId: number, laborRows: ProductLabor[]): Promise<ProductTreeRecalculateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}/tree/labor`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ labor_rows: laborRows, recalculate_cost: true }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeRecalculateResponse;
}

export async function recalculateProductTreeCost(token: string, productId: number): Promise<ProductTreeRecalculateResponse> {
  const response = await apiFetch(`${API_BASE_URL}/products/${productId}/tree/recalculate`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ProductTreeRecalculateResponse;
}

// ============================================================
// Doküman Yönetimi
// ============================================================

// GET /documents response shape is not strictly typed by the backend, so we
// keep this flexible and normalize at read time.
export type DocumentInfo = {
  id?: number | string;
  series_key?: string | null;
  series?: string | null;
  title?: string | null;
  document_type?: string | null;
  type?: string | null;
  language?: string | null;
  description?: string | null;
  updated_at?: string | null;
  guncelleme_tarihi?: string | null;
  url?: string | null;
  file_url?: string | null;
  download_url?: string | null;
  [key: string]: unknown;
};

export type DocumentFilters = {
  seriesKey?: string;
  type?: string;
  language?: string;
};

export type DocumentUploadPayload = {
  series_key?: string;
  title: string;
  document_type: string;
  language?: string;
  description?: string;
  sort_order?: number;
};

export async function fetchDocuments(
  token: string,
  filters: DocumentFilters = {},
): Promise<DocumentInfo[]> {
  const params = new URLSearchParams();
  if (filters.seriesKey) params.set("series_key", filters.seriesKey);
  if (filters.type) params.set("type", filters.type);
  if (filters.language) params.set("language", filters.language);
  const query = params.toString();
  const response = await apiFetch(
    `${API_BASE_URL}/documents${query ? `?${query}` : ""}`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = await response.json();
  return asArray<DocumentInfo>(
    (payload as { documents?: unknown })?.documents ?? payload,
  );
}

export async function uploadDocument(
  token: string,
  payload: DocumentUploadPayload,
  file: File,
): Promise<MessageResponse> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("document_type", payload.document_type);
  form.append("series_key", payload.series_key ?? "");
  form.append("language", payload.language ?? "tr");
  form.append("description", payload.description ?? "");
  form.append("sort_order", String(payload.sort_order ?? 0));
  form.append("file", file);
  const response = await apiFetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function deleteDocument(
  token: string,
  documentId: number | string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

// ============================================================
// Sabit Maliyet Yönetimi (/fixed-costs)
// ============================================================

export type FixedCostItem = {
  id?: number | string;
  kalem_adi?: string | null;
  kategori?: string | null;
  birim?: string | null;
  birim_fiyat?: number | string | null;
  para_birimi?: string | null;
  aktif?: boolean | number | null;
  aciklama?: string | null;
  guncelleme_tarihi?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
};

export type FixedCostFilters = {
  search?: string;
  category?: string;
  currency?: string;
  active?: string;
};

export type FixedCostPayload = {
  kalem_adi: string;
  kategori?: string | null;
  birim?: string | null;
  birim_fiyat: number | string;
  para_birimi?: string | null;
  aktif?: boolean;
  aciklama?: string | null;
};

export async function fetchFixedCosts(
  token: string,
  filters: FixedCostFilters = {},
): Promise<FixedCostItem[]> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.category) params.set("category", filters.category);
  if (filters.currency) params.set("currency", filters.currency);
  if (filters.active) params.set("active", filters.active);
  const query = params.toString();
  const response = await apiFetch(
    `${API_BASE_URL}/fixed-costs${query ? `?${query}` : ""}`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = await response.json();
  return asArray<FixedCostItem>(
    (payload as { items?: unknown; fixed_costs?: unknown })?.items ??
      (payload as { fixed_costs?: unknown })?.fixed_costs ??
      payload,
  );
}

export async function createFixedCost(
  token: string,
  payload: FixedCostPayload,
): Promise<FixedCostItem> {
  const response = await apiFetch(`${API_BASE_URL}/fixed-costs`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as FixedCostItem;
}

export async function updateFixedCost(
  token: string,
  itemId: number | string,
  payload: FixedCostPayload,
): Promise<FixedCostItem> {
  const response = await apiFetch(`${API_BASE_URL}/fixed-costs/${itemId}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as FixedCostItem;
}

export async function deleteFixedCost(
  token: string,
  itemId: number | string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/fixed-costs/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

// ============================================================
// Kullanıcı Yönetimi (Owner) — yalnızca gerçek uçlar
// ============================================================

export type AdminLeaveUser = {
  id: number;
  kullanici_adi: string;
  email: string;
  manager_user_id: number | null;
  leave_notification_email: number | boolean;
  annual_allowance_days: number;
  carried_over_days: number;
  reserved_days: number;
  used_days: number;
  pending_approval_days: number;
  available_days: number;
};

export type AdminLeaveUserUpdatePayload = {
  manager_user_id?: number | null;
  annual_allowance_days: number;
  leave_notification_email?: boolean;
};

export async function fetchAdminLeaveUsers(token: string): Promise<AdminLeaveUser[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/leave/users`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return asArray<AdminLeaveUser>(await response.json());
}

export async function updateAdminLeaveUser(
  token: string,
  userId: number,
  payload: AdminLeaveUserUpdatePayload,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/leave/users/${userId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function adminSendEmailVerification(
  token: string,
  email: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/auth/email/send-verification`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function adminVerifyEmail(
  token: string,
  email: string,
  code: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/auth/email/verify`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function adminSendPasswordResetCode(
  token: string,
  identifier: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/auth/password/send-reset-code`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function adminResetPassword(
  token: string,
  identifier: string,
  code: string,
  newPassword: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/auth/password/reset`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, code, new_password: newPassword }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

// ============================================================
// Admin Kullanıcı Yönetimi (/admin/users, /admin/roles)
// ============================================================

export type AdminUser = {
  id: number;
  kullanici_adi: string;
  email: string;
  rol_id?: number | null;
  rol_adi?: string | null;
  email_verified?: boolean | null;
  is_active?: boolean | null;
  manager_user_id?: number | null;
  manager_kullanici_adi?: string | null;
  leave_notification_email?: boolean | number | null;
  module_permissions?: Record<string, boolean>;
  mobile_module_permissions?: Record<string, boolean>;
  annual_allowance_days?: number;
  carried_over_days?: number;
  reserved_days?: number;
  used_days?: number;
  pending_approval_days?: number;
  available_days?: number;
};

export type AdminRole = {
  id: number;
  rol_adi: string;
};

export type AdminUserCreatePayload = {
  kullanici_adi: string;
  email: string;
  sifre: string;
  rol_adi: string;
};

export async function fetchAdminUsers(token: string): Promise<AdminUser[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return asArray<AdminUser>(await response.json());
}

export async function fetchAdminRoles(token: string): Promise<AdminRole[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/roles`, {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return asArray<AdminRole>(await response.json());
}

export async function createAdminUser(
  token: string,
  payload: AdminUserCreatePayload,
): Promise<AdminUser> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as AdminUser;
}

export async function deleteAdminUser(
  token: string,
  userId: number,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users/${userId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function updateAdminUserEmail(
  token: string,
  userId: number,
  email: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users/${userId}/email`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function updateAdminUserPassword(
  token: string,
  userId: number,
  newPassword: string,
): Promise<MessageResponse> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users/${userId}/password`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function fetchUserModulePermissions(
  token: string,
  userId: number,
): Promise<Record<string, boolean>> {
  const response = await apiFetch(
    `${API_BASE_URL}/admin/users/${userId}/module-permissions`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = await response.json();
  return (
    (payload as { module_permissions?: Record<string, boolean> })
      ?.module_permissions ?? (payload as Record<string, boolean>) ?? {}
  );
}

export async function updateUserModulePermissions(
  token: string,
  userId: number,
  modulePermissions: Record<string, boolean>,
): Promise<MessageResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/admin/users/${userId}/module-permissions`,
    {
      method: "PUT",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ module_permissions: modulePermissions }),
    },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

export async function fetchUserMobileModulePermissions(
  token: string,
  userId: number,
): Promise<Record<string, boolean>> {
  const response = await apiFetch(
    `${API_BASE_URL}/admin/users/${userId}/mobile-module-permissions`,
    { headers: authHeaders(token) },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = await response.json();
  return (
    (payload as { mobile_module_permissions?: Record<string, boolean> })
      ?.mobile_module_permissions ?? (payload as Record<string, boolean>) ?? {}
  );
}

export async function updateUserMobileModulePermissions(
  token: string,
  userId: number,
  mobileModulePermissions: Record<string, boolean>,
): Promise<MessageResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/admin/users/${userId}/mobile-module-permissions`,
    {
      method: "PUT",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ mobile_module_permissions: mobileModulePermissions }),
    },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as MessageResponse;
}

