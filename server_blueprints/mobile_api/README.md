# Mobile API AI Lead Automation Blueprint

Bu klasör, repoda kalıcı mobile API kaynak klasörü bulunmadığı için AI Lead Automation backend iskeletini commitlenebilir bir blueprint olarak tutar.

Canlı FastAPI paketine uygulanacak dosya:

```text
server_blueprints/mobile_api/routes_ai_leads.py
```

Hedef paket içinde önerilen konum:

```text
/opt/mobile_api/app/routes/ai_leads.py
```

`app/main.py` veya mevcut `app_main.py` içine eklenecek kayıt:

```python
from .routes.ai_leads import router as ai_leads_router

app.include_router(ai_leads_router)
```

Blueprint şu endpointleri sağlar:

- `GET /desktop/ai-leads`
- `POST /desktop/ai-leads`
- `POST /desktop/ai-leads/import`
- `POST /desktop/ai-leads/apollo/search`
- `POST /desktop/ai-leads/{lead_id}/apollo-enrich`
- `GET /desktop/ai-leads/segments`
- `GET /desktop/ai-leads/sequences`
- `GET /desktop/ai-leads/{lead_id}`
- `POST /desktop/ai-leads/{lead_id}/analyze`
- `PUT /desktop/ai-leads/{lead_id}/segment`
- `POST /desktop/ai-leads/{lead_id}/exclude`
- `POST /desktop/ai-leads/{lead_id}/email-drafts`
- `POST /desktop/ai-leads/email-drafts/{draft_id}/approve`

Email verisi `ai_lead_contacts.email` alanında tutulur. Apollo People Search net-new kişi/şirket datasını lead ve contact iskeleti olarak ekler; email bulunması veya doğrulanması için People Enrichment akışı `ai_lead_contacts.email`, `ai_lead_contacts.email_status` ve Apollo raw JSON alanlarını günceller.

İlk sürüm gerçek AI çağrısı yapmaz; deterministic MVP segmentasyon kurallarıyla sonuç üretir. Böylece masaüstü modül canlı API'ye bağlanabilir, veri kalıcılığı ve onay akışı test edilebilir. Gerçek AI entegrasyonu daha sonra `analyze_ai_lead` ve `generate_ai_email_draft` akışlarına eklenmelidir.
