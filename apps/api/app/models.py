from typing import Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    kullanici_adi: str
    sifre: str


class UserResponse(BaseModel):
    id: int
    kullanici_adi: str
    rol_id: int | None = None
    rol_adi: str | None = None
    module_permissions: dict[str, bool] = {}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MaterialResponse(BaseModel):
    id: int
    malzeme_kodu: str | None = None
    malzeme_tipi: str | None = None
    ad: str | None = None
    fiyat: float | None = None
    guncelleme_tarihi: str | None = None


class ProductResponse(BaseModel):
    id: int
    urun_kodu: str | None = None
    urun_adi: str | None = None
    urun_kategorisi: str | None = None
    urun_tipi: str | None = None
    urun_modeli: str | None = None
    maliyet: float | None = None
    filtre_medyasi: str | None = None
    filtre_medyasi_kodu: str | None = None
    patlac_kumanda_tipi: str | None = None
    toplam_filtre_alani: float | str | None = None
    debi: float | str | None = None
    fan_basinc: float | str | None = None
    fan_basinc_birimi: str | None = None
    motor: str | None = None
    fan_kumanda_tipi: str | None = None
    patlama_kapagi: str | None = None
    filtre_elemani_sayisi: float | str | None = None
    maliyet_hesaplama_tarihi: str | None = None


class ProductTreeItemResponse(BaseModel):
    id: int
    kod: str | None = None
    ad: str | None = None
    miktar: float | None = None


class ProductLaborResponse(BaseModel):
    iscilik_tipi: str | None = None
    usta_saat: float | None = None
    yardimci_saat: float | None = None


class ProductLaborUpdateRequest(BaseModel):
    iscilik_tipi: str
    usta_saat: float | int | str | None = 0
    yardimci_saat: float | int | str | None = 0


class ProductDetailFieldResponse(BaseModel):
    key: str
    label: str
    value: str | float | int | None = None


class ProductCostBreakdownResponse(BaseModel):
    malzeme_maliyeti: float | str | None = None
    iscilik_maliyeti: float | str | None = None
    uretim_gideri: float | str | None = None
    yonetim_gideri: float | str | None = None
    alt_urun_maliyeti: float | str | None = None
    toplam_maliyet: float | str | None = None


class ProductDetailResponse(BaseModel):
    product: dict[str, Any]
    display_fields: list[ProductDetailFieldResponse]
    cost_breakdown: ProductCostBreakdownResponse
    labor_rows: list[ProductLaborResponse]
    channel_fields: list[ProductDetailFieldResponse] = []
    flange_fields: list[ProductDetailFieldResponse] = []


class ProductEditOptionsResponse(BaseModel):
    category_options: list[str]
    type_options_by_category: dict[str, list[str]]
    field_options: dict[str, list[str]]
    filter_media_code_map: dict[str, str]


class ProductUpdateRequest(BaseModel):
    fields: dict[str, str | float | int | None] = {}
    labor_rows: list[ProductLaborUpdateRequest] = []
    recalculate_cost: bool = False


class ProductUpdateResponse(BaseModel):
    product_id: int
    updated_fields: list[str]
    labor_updated: bool = False
    cost_recalculated: bool = False
    recalculation_error: str | None = None
    detail: ProductDetailResponse


class ProductDeleteResponse(BaseModel):
    product_id: int
    deleted_count: int
    blocked_count: int = 0
    message: str


class ProductCopyRequest(BaseModel):
    new_product_code: str


class ProductCopyResponse(BaseModel):
    source_product_id: int
    new_product_id: int
    new_product_code: str
    cost_recalculated: bool = False
    recalculation_error: str | None = None
    detail: ProductDetailResponse


class ProductCostRevisionRequest(BaseModel):
    product_ids: list[int]


class ProductCostRevisionResponse(BaseModel):
    requested_count: int
    updated_count: int
    failed_count: int
    message: str


class ProductTreeResponse(BaseModel):
    product_id: int
    stats: dict[str, float | int]
    yari_mamuller: list[ProductTreeItemResponse]
    mamuller: list[ProductTreeItemResponse]
    alt_urunler: list[ProductTreeItemResponse]
    iscilikler: list[ProductLaborResponse]
