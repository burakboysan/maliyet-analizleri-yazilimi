# Maliyet Web

React + TypeScript + Vite tabanli web frontend uygulamasidir. Frontend source of truth bu klasordur; UI gelistirme ve deploy akisi ana repo uzerinden yurutulur.

## Yerel gelistirme

```powershell
cd apps/web
npm install
npm run dev
```

Yerel varsayilan API adresi:

```text
http://127.0.0.1:8100
```

## Build

Production build icin `VITE_API_BASE_URL` zorunludur:

```powershell
$env:VITE_API_BASE_URL = "https://<cloud-run-api-url>"
npm run build
```

Local API URL ile sadece build kontrolu yapmak gerekirse:

```powershell
npm run build:local
```

## Cloudflare Pages

- Root directory: `apps/web`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<cloud-run-api-url>`

SPA deep-link fallback kuralinin source of truth dosyasi `public/_redirects` dosyasidir:

```text
/* /index.html 200
```
