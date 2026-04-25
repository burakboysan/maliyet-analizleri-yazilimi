# Bomaksan Sirket Ici Kod Imzalama Operasyon Notu

Bu not, `www.bomaksan.com` markasi altinda yalnizca Bomaksan icinde kullanilacak Windows masaustu yaziliminin guvenli sekilde imzalanmasi ve istemci bilgisayarlara guven dagitiminin yapilmasi icindir.

## Hedef

- Build makinesinde uygulama ve installer dosyalarini imzalamak
- Sirket ici istemci bilgisayarlarda `Unknown Publisher` ve guven uyarilarini azaltmak
- Disaridan public CA satin almadan, ic dagitim icin kontrollu bir guven zinciri kurmak

## Net karar

Bomaksan icin ilk asamada onerilen model:

- Build makinesinde self-signed `Code Signing` sertifikasi uretin
- Yazilimi bu sertifika ile imzalayin
- Sertifikanin `.cer` dosyasini sirket bilgisayarlarina guvenilir olarak dagitin

Bu model yalnizca sirket ici dagitim icin uygundur. Dis musterilere dagitimda public-trust code signing gerekir.

## Domain notu

- `www.bomaksan.com` web domaininizdir
- Eger Windows Active Directory domaininiz `bomaksan.com` ise GPO dagitimi dogrudan bu domain uzerinden yapilir
- Eger AD domaininiz farkliysa, sertifika yine ayni kalir; sadece dagitim o AD domain uzerinden yapilir
- Code signing guveni domain adindan degil, istemci makinelerin sertifikaya guvenmesinden gelir

## Kullanim senaryolari

### Senaryo 1: On-prem AD ve Group Policy varsa

En temiz ve en az operasyonel maliyetli yol budur.

- Build makinesinde sertifikayi uretin
- `.cer` dosyasini paylasima koyun
- GPO ile istemcilere dagitin

### Senaryo 2: Cihazlar Microsoft Entra ID / Intune ile yonetiliyorsa

Office 365 kullaniyor olmaniz Intune kullandiginiz anlamina gelmez, ama Microsoft 365/Business Premium/EMS lisanslariniz varsa Intune kullaniliyor olabilir.

- Root guveni Intune `Trusted certificate` profili ile dagitabilirsiniz
- `Trusted Publisher` magazasi icin Windows CSP OMA-URI profili kullanmak gerekir

### Senaryo 3: Ne AD ne Intune varsa

Kucuk bir ortamda manuel dagitim yapabilirsiniz.

- `.cer` dosyasini istemciye kopyalayin
- `scripts\trust_internal_signer.ps1` ile import edin
- veya kullaniciya cift tikla calisan paket verin

## Build makinesi adimlari

### 1. Ic imza sertifikasini olustur

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_internal_codesigning.ps1 -Subject "Bomaksan Internal Code Signing - bomaksan.com"
```

Bu komut:

- `CurrentUser\My` altinda self-signed code signing sertifikasi olusturur
- Build scriptinin kullanacagi ortam degiskenlerini ayarlar
- Paylasim icin `.cer` dosyasi uretir

### 2. Imzali release al

```powershell
py build_exe.py --release --require-sign
```

## Dagitim secenegi A: Group Policy

Bu bolum, bilgisayarlar domain'e bagliysa kullanilmalidir.

### Hazirlik

- `bomaksan-internal-code-signing.cer` dosyasini herkesin okuyabilecegi bir paylasima koyun
- Ornek: `\\fileserver\software\certs\bomaksan-internal-code-signing.cer`

### GPO adimlari

1. `Group Policy Management` acin
2. Ilgili OU veya domain icin yeni bir GPO olusturun
3. `Computer Configuration > Policies > Windows Settings > Security Settings > Public Key Policies` yoluna gidin
4. `Trusted Root Certification Authorities` icine `.cer` dosyasini import edin
5. `Trusted Publishers` icine ayni `.cer` dosyasini import edin
6. GPO'yu istemci bilgisayarlarin bulundugu OU'ya link edin
7. Istemcilerde `gpupdate /force` calistirin veya yeniden baslatin

### Istemci dogrulama

Istemci bilgisayarda kontrol:

- `certmgr.msc` veya `certlm.msc` acin
- Sertifikanin su depolarda oldugunu dogrulayin:
- `Trusted Root Certification Authorities`
- `Trusted Publishers`

## Dagitim secenegi B: Intune

Bu bolum, cihazlariniz Entra/Intune ile yonetiliyorsa uygundur.

### Onemli not

Microsoft dokumanina gore Intune `Trusted certificate profile`, root veya intermediate sertifikalari dagitmak icindir. `Trusted Publishers` icin Windows `RootCATrustedCertificates CSP` altinda `TrustedPublisher` dugumune custom OMA-URI ile yazmak gerekir.

### B1. Root guveni dagit

Intune Admin Center:

1. `Devices > Manage devices > Configuration > Create`
2. Platform: `Windows 10 and later`
3. Profile: `Templates > Trusted certificate`
4. `.cer` dosyasini yukleyin
5. Destination Store: `Computer certificate store - Root`
6. Cihaz grubuna assign edin

### B2. Trusted Publisher dagit

Custom profile ile asagidaki OMA-URI kullanilir:

- OMA-URI:
  `./Device/Vendor/MSFT/RootCATrustedCertificates/TrustedPublisher/{SHA1_THUMBPRINT}/EncodedCertificate`
- Data type:
  `Base64 (file)` veya Intune ekranina gore `String/Base64`
- Value:
  `.cer` dosyasinin Base64 icerigi, satir kirmadan

`{SHA1_THUMBPRINT}` yerine sertifikanin SHA1 thumbprint degeri kullanilir.

### Thumbprint alma

```powershell
Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*Bomaksan Internal Code Signing*" } | Select-Object Subject, Thumbprint
```

### Base64 alma

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\Users\$env:USERNAME\BomaksanCodeSigning\bomaksan-internal-code-signing.cer"))
```

### Intune atama notu

- Profilleri `device group` olarak atayin
- Pilot grup ile baslayin
- Birkac test cihazinda dogrulamadan tum sirkete acmayin

## Dagitim secenegi C: Manuel import

Kucuk ofislerde veya test cihazlarinda hizli cozum:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\trust_internal_signer.ps1 -CertificatePath "C:\yol\bomaksan-internal-code-signing.cer"
```

## Tek tik paket

Kullaniciya paylasilabilir klasor hazirlamak icin:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_internal_signer_package.ps1
```

Bu komut su klasoru uretir:

- [internal_signer_package](C:\Users\burak\Desktop\Bomaksan Yazılımlar\Maliyet Analizleri Yazılımı\internal_signer_package)

Klasor icerigi:

- `install_internal_signer.bat`
- `install_internal_signer.ps1`
- `bomaksan-internal-code-signing.cer`
- `README.txt`

Kullanici tarafinda yapilacak tek islem:

- `install_internal_signer.bat` dosyasina cift tiklamak

## Kontrol listesi

- Build makinesinde sertifika olustu
- `.cer` dosyasi export edildi
- Build `--require-sign` ile basarili tamamladi
- Istemci bilgisayarda sertifika `Trusted Root` altina geldi
- Istemci bilgisayarda sertifika `Trusted Publishers` altina geldi
- Kurulum ve uygulama acilisi test edildi

## Bomaksan icin onerilen uygulama plani

Eger domain'e bagli Windows bilgisayarlariniz varsa:

- Ana yol: `GPO`
- Yedek yol: manuel import

Eger cihazlar Intune ile yonetiliyorsa:

- Ana yol: `Intune Trusted certificate + custom OMA-URI TrustedPublisher`

Eger henuz merkezi yonetim net degilse:

1. Once 2-3 test makinesinde manuel import ile dogrulayin
2. Sonra merkezi dagitima gecin

## Kaynaklar

- [Microsoft Intune trusted certificate profiles](https://learn.microsoft.com/en-us/mem/intune/protect/certificates-trusted-root)
- [Microsoft Intune certificate profile overview](https://learn.microsoft.com/en-us/intune/fundamentals/certificates/overview)
- [Microsoft RootCATrustedCertificates CSP](https://learn.microsoft.com/en-us/windows/client-management/mdm/rootcacertificates-csp)
