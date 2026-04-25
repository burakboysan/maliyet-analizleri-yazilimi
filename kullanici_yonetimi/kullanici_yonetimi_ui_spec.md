# Kullanıcı Yönetimi UI/UX Spec

Bu doküman kullanıcı yönetimi ekranının Lovable benzeri bir UI aracında veya sonraki masaüstü uygulama tasarım adımında yeniden tasarlanması için hazırlanmıştır. Amaç, mevcut çalışan işlevleri koruyup modern, stabil ve profesyonel bir arayüz üretmektir.

## Temel Hedef

Owner rolündeki kullanıcı, masaüstü uygulamada kullanıcı hesaplarını, e-posta doğrulama işlemlerini, şifre işlemlerini ve izin/yönetici atamalarını tek ekrandan yönetebilmelidir.

Ekran görsel olarak modern olmalı ama operasyonel araç gibi davranmalıdır: sakin, yoğun bilgiyi okunur sunan, sabit ölçülü, arama ve sekme geçişlerinde oynamayan bir panel düzeni.

## Kritik UX Kuralları

1. Arama kutusuna yazı girildiğinde yalnızca tablo satırları filtrelenmeli. Header, form, butonlar, sağ panel, tablo genişliği ve pencere yerleşimi hareket etmemeli.
2. Sağ panelde sekmeler arasında geçiş yapılırken panel genişliği, sekme bar genişliği, içerik başlangıç noktası ve ana sayfa kolonları değişmemeli.
3. Butonlar, inputlar ve comboboxlar sabit yükseklik ve min/max genişliğe sahip olmalı.
4. Tablo kolonları pencere yeniden boyutlandırıldığında responsive olmalı; arama sırasında yeniden layout hesaplanmamalı.
5. Aktif sekme kırmızı tehlike/aksiyon butonu gibi görünmemeli. Hafif vurgu kullanılmalı.
6. Silme işlemi hariç kırmızı buton kullanılmamalı.
7. Kart içinde kart kullanılmamalı. Ana bölümler panel, satır içi tekrarlar tablo veya form bandı olmalı.
8. Türkçe karakterler doğru görünmeli: Kullanıcı, Şifre, Doğrulama, İzin, Yönetici, E-posta.

## Önerilen Layout

Sayfa iki ana bölüme ayrılır:

- Sol ana alan: kullanıcı listesi ve yeni kullanıcı oluşturma.
- Sağ sabit detay paneli: seçili kullanıcının profil, güvenlik ve izin işlemleri.

Önerilen oran:

- Sol alan: kalan tüm genişliği alır.
- Sağ panel: sabit 440-480 px genişlik.
- Minimum pencere: 1220 x 760.

## Sol Alan

### Üst Araç Çubuğu

İçerikler:

- Başlık: Kullanıcılar
- Alt küçük metin: “8 kullanıcı gösteriliyor”
- Arama inputu: sabit genişlik, örn. 320-360 px
- Rol filtresi: sabit genişlik, örn. 150-170 px
- Listeyi yenile butonu tercihen header sağında veya toolbar sağında

Arama davranışı:

- Debounce opsiyonel ama layout değişmemeli.
- Filtre sonucu tablo satırlarını değiştirir.
- Seçili kullanıcı filtre dışında kalırsa sağ panel aynı kalabilir veya “seçili kullanıcı filtre dışında” bilgisi gösterilebilir; panel ölçüsü değişmemelidir.

### Yeni Kullanıcı Oluşturma

Tek satırlı form bandı veya kompakt iki satırlı form.

Alanlar:

- Kullanıcı Adı
- Email Adresi
- Şifre Belirleme
- Şifre Doğrulama
- Rol Seçme
- Kullanıcı Ekle butonu

Kurallar:

- Tüm inputlar aynı yükseklikte olmalı.
- Buton yüksekliği inputlarla aynı olmalı.
- Form arama yaparken veya tablo yenilenirken hareket etmemeli.
- Şifre göster/gizle gerekiyorsa checkbox yerine küçük ikonlu sabit buton tercih edilmeli.

### Kullanıcı Tablosu

Kolonlar:

- ID
- Kullanıcı Adı
- E-posta
- Rol
- E-posta Durumu
- Aktif
- Kalan İzin

Kolon oran önerisi:

- ID: %5
- Kullanıcı Adı: %22
- E-posta: %34
- Rol: %14
- E-posta Durumu: %11
- Aktif: %6
- Kalan İzin: %8

Satır davranışı:

- Satır yüksekliği 42-48 px.
- Zebra striping kullanılabilir.
- Seçili satır açık ve sakin bir vurgu almalı.
- Doğrulanmamış/pasif durumlar metin rozetleriyle gösterilmeli; tüm satırı kırmızı yapmak yok.

## Sağ Panel

Sağ panel sabit genişlikte olmalı. İçerik değişse bile panel genişliği ve tab bar ölçüsü asla değişmemeli.

### Seçili Kullanıcı Başlığı

Kompakt yapı:

- Sol: avatar/initials rozeti
- Sağ üst: ID + rol küçük metin
- Sağ alt: kullanıcı adı

Örnek:

```text
[BG]  ID 22 · Master Admin
      Beyzanur Güç
```

### Sekmeler

Sekmeler:

- Profil
- Güvenlik
- İzin Yönetimi

Kurallar:

- Segment bar sabit yükseklik: 40-44 px.
- Her sekme eşit genişlikte.
- Aktif sekme açık kırmızı/rose arka plan + koyu kırmızı metin veya nötr primary vurgu.
- Pasif sekmeler açık gri zemin.
- Sekme geçişinde içerik alanı aynı x/y konumunda kalmalı.

### Profil Sekmesi

İçerikler:

- E-posta Güncelle inputu
- Rol alanı. Rol düzenleme API hazır değilse disabled gösterilebilir.
- E-postayı Güncelle butonu
- Seçili Kullanıcıyı Sil butonu

### Güvenlik Sekmesi

İçerikler:

- Yeni Şifre
- Yeni Şifre Tekrar
- Şifreyi Güncelle
- E-posta doğrulama durumu rozeti
- Doğrulama Maili Gönder
- Kod Doğrula

### İzin Yönetimi Sekmesi

İçerikler:

- Yıllık Hak
- Kullanılan
- Kalan Bakiye
- Yönetici Ataması
- İzin Bakiyesi
- Düzeltme Notu
- İzin Bilgilerini Kaydet

Backend hazır değilse:

- Alanlar tasarımda görünmeli.
- Kaydetme butonu API bağlanana kadar disabled veya “API bekliyor” bilgisiyle gösterilmeli.

## Görsel Dil

Renkler:

- Arka plan: `#eef2f6`
- Panel: `#ffffff`
- Form yüzeyi: `#f8fafc`
- Border: `#d8e0ea`
- Metin: `#1f2937`
- İkincil metin: `#64748b`
- Bomaksan kırmızı vurgu: `#c62828`
- Tehlike/silme: `#dc2626`
- Bilgi: `#2563eb`
- Başarılı: `#15803d`
- Uyarı: `#b45309`

Köşe yuvarlaklığı:

- Paneller: 8-10 px
- Input/button: 8 px
- Tab segment: 8 px

Tipografi:

- Başlık: 24-28 px bold
- Panel başlıkları: 16-18 px bold
- Form label: 11-12 px semibold
- Tablo: 10-11 px

## Kabul Kriterleri

1. Arama yazarken pencere içindeki header, form, sağ panel ve tablo container boyutu değişmez.
2. Sekme değiştirirken sağ panel genişliği sabit kalır.
3. Silme butonu dışında kırmızı dolu buton kullanılmaz.
4. Aktif sekme hata/tehlike butonu gibi görünmez.
5. Full screen ve minimum pencere boyutunda metin taşması olmaz.
6. Kullanıcı seçimi tablo satırı ve sağ panelde tutarlı görünür.
7. İlk API hatasında ekran boş kalmaz; panel içinde anlaşılır hata gösterilir.
8. Türkçe karakterler bozulmaz.

## Lovable Prompt Taslağı

```text
Design a modern desktop admin screen for “Kullanıcı Yönetim Paneli” in Turkish.

This is an operational user-management tool, not a marketing page. Use a calm, dense, professional layout. The app uses a light background, white panels, subtle borders, Bomaksan red only as a restrained accent, and red danger styling only for deletion.

Create a two-column layout:
- Left column fills available space and contains a toolbar, a new-user form, and a responsive user table.
- Right column is a fixed-width 460px details panel that never changes width when switching tabs.

Important UX constraints:
- Typing into search must only filter table rows; no other element may resize, move, or reflow.
- Switching tabs must not change the right panel width or layout origin.
- Segment tabs must be calm and professional, not red danger buttons.
- Use Turkish labels with correct characters.

Left toolbar:
- Title “Kullanıcılar”
- Small status text like “8 kullanıcı gösteriliyor”
- Search input
- Role filter
- Refresh button

New user form:
- Kullanıcı Adı
- Email Adresi
- Şifre Belirleme
- Şifre Doğrulama
- Rol Seçme
- Kullanıcı Ekle

Table columns:
ID, Kullanıcı Adı, E-posta, Rol, E-posta Durumu, Aktif, Kalan İzin.

Right panel:
- Selected user header with initials avatar, ID + role, full name.
- Tabs: Profil, Güvenlik, İzin Yönetimi.
- Profil includes email update, disabled/current role field, update email, delete user.
- Güvenlik includes password update and email verification actions.
- İzin Yönetimi includes annual leave, used leave, remaining balance, manager assignment, balance edit, note, save.

Make all inputs and buttons stable in size. Avoid layout shift. Use subtle borders and consistent spacing.
```
