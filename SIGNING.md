# Kod Imzalama

Bu proje release sirasinda uygulama `.exe` dosyasini ve Inno Setup ile uretilen installer `.exe` dosyasini otomatik imzalayabilir.

Kurulumu hizlandirmak icin [scripts\setup_codesigning.ps1](C:\Users\burak\Desktop\Bomaksan Yazılımlar\Maliyet Analizleri Yazılımı\scripts\setup_codesigning.ps1) eklendi.

Sirket ici kullanim icin ek olarak [scripts\setup_internal_codesigning.ps1](C:\Users\burak\Desktop\Bomaksan Yazılımlar\Maliyet Analizleri Yazılımı\scripts\setup_internal_codesigning.ps1) ve [scripts\trust_internal_signer.ps1](C:\Users\burak\Desktop\Bomaksan Yazılımlar\Maliyet Analizleri Yazılımı\scripts\trust_internal_signer.ps1) eklendi.

## Desteklenen yontemler

- Windows sertifika deposundaki sertifika konusu ile: `BOMAKSAN_SIGN_CERT_SUBJECT`
- Windows sertifika deposundaki SHA1 thumbprint ile: `BOMAKSAN_SIGN_CERT_SHA1`
- PFX dosyasi ile: `BOMAKSAN_SIGN_PFX_PATH`

Asagidaki degiskenlerden yalnizca biri zorunludur:

- `BOMAKSAN_SIGN_CERT_SUBJECT`
- `BOMAKSAN_SIGN_CERT_SHA1`
- `BOMAKSAN_SIGN_PFX_PATH`

Istege bagli degiskenler:

- `BOMAKSAN_SIGN_PFX_PASSWORD`
- `BOMAKSAN_SIGNTOOL_PATH`
- `BOMAKSAN_SIGN_TIMESTAMP_URL`
- `BOMAKSAN_SIGN_FILE_DIGEST`
- `BOMAKSAN_SIGN_TIMESTAMP_DIGEST`

Varsayilanlar:

- Timestamp URL: `http://timestamp.digicert.com`
- Digest: `SHA256`

## Ornekler

Sertifika deposundaki sertifika konusu ile:

```powershell
$env:BOMAKSAN_SIGN_CERT_SUBJECT = "Bomaksan A.S."
py build_exe.py --release --require-sign
```

PFX dosyasi ile:

```powershell
$env:BOMAKSAN_SIGN_PFX_PATH = "C:\secure\bomaksan-codesign.pfx"
$env:BOMAKSAN_SIGN_PFX_PASSWORD = "parolaniz"
py build_exe.py --release --require-sign
```

Hazir kurulum scripti ile:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codesigning.ps1
```

PFX'i import etmeden dogrudan kullanmak icin:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codesigning.ps1 -UsePfxDirectly
```

## Parametreler

- `--require-sign`: imzalama yoksa build'i hata ile durdurur
- `--skip-sign`: ortam degiskenleri tanimli olsa bile bu calistirmada imzalamayi kapatir

## Not

`latest.json` hash'i installer imzalandiktan sonra uretildigi icin dagitilan dosya ile uyumlu kalir.

Bu makinede `signtool.exe` yoksa script uyari verir ve `BOMAKSAN_SIGNTOOL_PATH` ayarini ancak arac bulunduysa yazar.

## Sirket ici kullanim

Dis kullanicilara dagitilmayan, yalnizca Bomaksan icindeki bilgisayarlarda calisacak kurulumlar icin public CA almak zorunda degilsiniz.

Bomaksan icin onerilen ic sertifika adi:

- `Bomaksan Internal Code Signing - bomaksan.com`

Not:

- `www.bomaksan.com` web domaininizdir.
- Eger Windows Active Directory domaininiz farkliysa, GPO dagitiminda web domaini degil AD domaini esas alinmalidir.
- Code signing sertifikasinda kritik olan alan domain degil, istemci bilgisayarlarin bu sertifikaya guvenmesidir.

1. Imza atacak makinede self-signed code signing sertifikasi olusturun:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_internal_codesigning.ps1
```

Isterseniz acikca konu vererek de uretebilirsiniz:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_internal_codesigning.ps1 -Subject "Bomaksan Internal Code Signing - bomaksan.com"
```

2. Imzali build alin:

```powershell
py build_exe.py --release --require-sign
```

3. Uygulamanin kurulacagi her istemci makinede `.cer` dosyasini guvenilir depolara ekleyin:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\trust_internal_signer.ps1 -CertificatePath "C:\yol\bomaksan-internal-code-signing.cer"
```

Domain ortaminiz varsa bu `.cer` dosyasini GPO ile `Trusted Root Certification Authorities` ve `Trusted Publishers` depolarina dagitmaniz en temiz yontem olur.

Eger AD domaininiz de `bomaksan.com` ise tipik dagitim yaklasimi sudur:

1. `.cer` dosyasini bir paylasima koyun
2. Group Policy Management uzerinden ilgili OU veya tum domain icin bir GPO olusturun
3. `Computer Configuration > Policies > Windows Settings > Security Settings > Public Key Policies` altinda:
- `Trusted Root Certification Authorities` icine sertifikayi ekleyin
- `Trusted Publishers` icine ayni sertifikayi ekleyin
4. Istemci makinelerde `gpupdate /force` uygulayin veya yeniden baslatin
