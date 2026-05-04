from fastapi import APIRouter


router = APIRouter(prefix="/modules", tags=["modules"])


MODULES = [
    {"key": "products", "title": "Ürünler", "phase": 1},
    {"key": "materials", "title": "Malzemeler", "phase": 1},
    {"key": "channel_management", "title": "Emiş Kanalı Yönetimi", "phase": 2},
    {"key": "price_list", "title": "Fiyat Listesi", "phase": 1},
    {"key": "leave_management", "title": "İzin Yönetim Modülü", "phase": 2},
    {"key": "selection_wizard", "title": "Seçim Sihirbazı", "phase": 3},
    {"key": "project_offers", "title": "Proje Teklif Yönetimi", "phase": 2},
    {"key": "project_management", "title": "Proje Yönetim Modülü", "phase": 2},
    {"key": "technical_calculations", "title": "Teknik Hesaplamalar", "phase": 3},
    {"key": "documents", "title": "Dokümanlar", "phase": 2},
    {"key": "user_management", "title": "Kullanıcı Yönetimi", "phase": 4},
]


@router.get("")
def list_modules():
    return {"modules": MODULES}
