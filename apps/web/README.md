# Maliyet Web

React + TypeScript + Vite tabanli web frontend baslangicidir. Masaustu uygulamayi degistirmez; API uzerinden maliyet verisine ulasir.

Yerel gelistirme komutu:

```powershell
cd apps/web
npm install
npm run dev
```

Yerel varsayilan API adresi:

```text
http://127.0.0.1:8100
```

Production build icin `VITE_API_BASE_URL` zorunludur. Cloudflare Pages ayarlari:

- Root directory: `apps/web`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://<cloud-run-api-url>`

Local API URL ile sadece build kontrolu yapmak gerekirse:

```powershell
npm run build:local
```
