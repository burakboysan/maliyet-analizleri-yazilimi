# MySQL Backup ve Restore Runbook

Bu dokuman, `maliyet-server` uzerindeki MySQL yedekleme ve geri yukleme akisini operasyonel olarak yonetmek icin hazirlandi.

## Sistem Ozeti

- Sunucu: `maliyet-server`
- Proje: `maliyet-analizi-yazilimi`
- Veritabani: `urun_maliyet_db`
- Backup bucket: `gs://maliyet-analizi-yazilimi-mysql-backups-416688102123`
- Gunluk backup saati: her gun `03:30 Europe/Istanbul`
- Haftalik restore testi: her pazar `04:30 Europe/Istanbul`
- Retention: `31 gun`
- Alarm e-postalari:
  - `burakboysan@gmail.com`
  - `burakboysan@bomaksan.com`

## Sunucudaki Kritik Dosyalar

- Backup script: `/usr/local/sbin/mysql_gcs_backup.sh`
- Restore verify script: `/usr/local/sbin/mysql_restore_verify.sh`
- Hata wrapper script: `/usr/local/sbin/mysql_job_runner.sh`
- Backup timer: `/etc/systemd/system/mysql-gcs-backup.timer`
- Backup service: `/etc/systemd/system/mysql-gcs-backup.service`
- Restore timer: `/etc/systemd/system/mysql-restore-verify.timer`
- Restore service: `/etc/systemd/system/mysql-restore-verify.service`
- Backup MySQL kimligi: `/root/.mysql-backup.cnf`

## Normal Davranis

- Her gun bir `.sql.gz` dump dosyasi ve yaninda `.sha256` checksum dosyasi bucket'a yuklenir.
- Haftalik restore testi en son dump'i indirir, checksum kontrolu yapar, gecici bir veritabanina restore eder, temel tablo kontrolunu yapar ve test veritabanini siler.
- Backup veya restore verify hata alirsa Cloud Logging'e `mysql-backup-alert` logu yazilir.
- Bu log, Google Cloud Monitoring tarafinda e-posta alarmi tetikler.

## Hizli Kontrol Komutlari

### Timer durumlari

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="systemctl list-timers --all | grep mysql"
```

### Son backup dosyalari

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' storage ls 'gs://maliyet-analizi-yazilimi-mysql-backups-416688102123/urun_maliyet_db/'
```

### Backup service loglari

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo journalctl -u mysql-gcs-backup.service -n 80 --no-pager"
```

### Restore verify loglari

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo journalctl -u mysql-restore-verify.service -n 80 --no-pager"
```

### Alarm loglari

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' logging read 'logName="projects/maliyet-analizi-yazilimi/logs/mysql-backup-alert"' --project='maliyet-analizi-yazilimi' --limit=20 --format='table(timestamp,severity,textPayload)'
```

## Manuel Backup Calistirma

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo systemctl start mysql-gcs-backup.service && sudo systemctl status mysql-gcs-backup.service --no-pager"
```

Ardindan bucket kontrol edilir:

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' storage ls 'gs://maliyet-analizi-yazilimi-mysql-backups-416688102123/urun_maliyet_db/'
```

## Manuel Restore Testi Calistirma

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo systemctl start mysql-restore-verify.service && sudo systemctl status mysql-restore-verify.service --no-pager"
```

Basarili durumda logta buna benzer bir satir gorulur:

```text
Restore verified successfully from ... with ... tables and estimated ... rows
```

## Gercek Restore Adimlari

Asagidaki adimlar uretim veritabanina geri donus gerektiginde kullanilir.

### 1. Uygulamayi durdur

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo systemctl stop fastapi.service"
```

### 2. Geri donulecek backup dosyasini sec

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' storage ls 'gs://maliyet-analizi-yazilimi-mysql-backups-416688102123/urun_maliyet_db/'
```

### 3. Sunucuda gecici klasore indir

`BACKUP_FILE` yerine secilen dosyayi yazin.

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="mkdir -p /tmp/mysql-restore && gcloud storage cp 'gs://maliyet-analizi-yazilimi-mysql-backups-416688102123/urun_maliyet_db/BACKUP_FILE' /tmp/mysql-restore/"
```

### 4. Mevcut veritabanini yeniden adlandir veya dump al

Canli olayda bunu duruma gore karar verin. Guvenli varsayim once son bir dump almaktir.

### 5. Restore islemi

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="bash -lc 'gzip -dc /tmp/mysql-restore/BACKUP_FILE | mysql --protocol=TCP -h 127.0.0.1 -u root -p\"\"\"BoBo1991\"\"\" urun_maliyet_db'"
```

Not: Buyuk veri kaybini onlemek icin gercek restore oncesi mevcut veritabani yedegi alinmadan overwrite yapilmaz.

### 6. Uygulamayi tekrar kaldir

```powershell
& 'C:\Users\burak\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' compute ssh maliyet-server --project='maliyet-analizi-yazilimi' --zone='europe-west9-b' --command="sudo systemctl start fastapi.service && sudo systemctl status fastapi.service --no-pager"
```

## Alarm Geldiginde Kontrol Listesi

1. Alarm metninde `mysql-gcs-backup` mi `mysql-restore-verify` mi hata vermis bakin.
2. Ilgili service logunu inceleyin.
3. Bucket'ta o gunun yedegi olusmus mu kontrol edin.
4. Gerekirse backup service'i manuel yeniden calistirin.
5. Restore verify hatasinda:
   gecici bir format sorunu mu, yoksa backup dosyasi bozuk mu kontrol edin.
6. Son saglam backup dosyasini not alin.
7. Uygulama etkileniyorsa servis sagligini ayri kontrol edin.

## Beklenen Basarili Sonuclar

- Bucket'ta duzenli yeni `.sql.gz` dosyalari gorunmeli.
- Her pazar restore verify loglarinda basari satiri olusmali.
- `mysql-backup-alert` logu yalnizca gercek hata veya kontrollu testlerde gorunmeli.

## Dikkat Edilecek Noktalar

- Bu yapi su anda `urun_maliyet_db` icin kuruludur.
- Yedekleme MySQL dump tabanlidir; fiziksel disk snapshot'i degildir.
- Sunucudaki root sifresi ve backup kimlik dosyalari degistirilirse scriptler tekrar gozden gecirilmelidir.
- Alarm policy Cloud Logging uzerinden calisir; bu nedenle `logging.googleapis.com` ve `monitoring.googleapis.com` etkin kalmalidir.
