#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bomaksan Maliyet Analizleri - Virtual Environment Setup Script
"""

import os
import sys
import subprocess
import shutil
import zipfile

def create_venv_package():
    """Virtual environment ile kurulum paketi oluştur"""
    print("📦 Virtual Environment kurulum paketi hazırlanıyor...")
    
    # Paket dizini oluştur
    package_dir = "Bomaksan_Maliyet_VENV_Setup"
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)
    
    # Proje dosyalarını kopyala
    project_files = [
        "main.py",
        "requirements.txt",
        "core/",
        "flans_yonetimi/",
        "kanal_yonetimi/",
        "kullanici_yonetimi/",
        "maliyet/",
        "malzeme_yonetimi/",
        "proje_yonetimi/",
        "teklif_yonetimi/",
        "urun_detay/",
        "urun_yonetimi/",
        "tkcalendar/",
        "bcrypt/",
        "assets/"
    ]
    
    for item in project_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(package_dir, item))
            else:
                shutil.copy2(item, package_dir)
    
    # Windows kurulum script'i oluştur
    install_script = """@echo off
echo Bomaksan Maliyet Analizleri - Kurulum Başlatılıyor
echo ================================================

REM Python kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadı!
    echo Lütfen Python 3.13.5'i https://www.python.org/downloads/ adresinden indirin ve kurun.
    pause
    exit /b 1
)

echo Python bulundu, versiyon kontrol ediliyor...
python --version

REM Virtual environment oluştur
echo Virtual environment oluşturuluyor...
python -m venv venv

REM Virtual environment'ı aktifleştir
echo Virtual environment aktifleştiriliyor...
call venv\\Scripts\\activate.bat

REM Gerekli paketleri yükle
echo Gerekli paketler yükleniyor...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ================================================
echo Kurulum tamamlandı!
echo.
echo Yazılımı başlatmak için:
echo 1. Bu klasörde "baslat.bat" dosyasını çalıştırın
echo 2. Veya komut satırında: venv\\Scripts\\activate.bat && python main.py
echo.
pause
"""
    
    with open(os.path.join(package_dir, "install.bat"), "w", encoding="utf-8") as f:
        f.write(install_script)
    
    # Başlatma script'i oluştur
    start_script = """@echo off
echo Bomaksan Maliyet Analizleri Başlatılıyor...
echo ================================================

REM Virtual environment'ı aktifleştir
call venv\\Scripts\\activate.bat

REM Uygulamayı başlat
python main.py

pause
"""
    
    with open(os.path.join(package_dir, "baslat.bat"), "w", encoding="utf-8") as f:
        f.write(start_script)
    
    # README dosyası oluştur
    readme_content = """# Bomaksan Maliyet Analizleri - Virtual Environment Kurulumu

## Kurulum Talimatları

### Ön Gereksinimler
1. Python 3.13.5 kurulu olmalı (https://www.python.org/downloads/)
2. İnternet bağlantısı

### Kurulum Adımları
1. Bu klasörde `install.bat` dosyasını çalıştırın
2. Kurulum otomatik olarak tamamlanacaktır
3. Kurulum tamamlandıktan sonra `baslat.bat` ile yazılımı başlatın

### Manuel Kurulum (Alternatif)
Eğer otomatik kurulum çalışmazsa:

1. Komut satırını açın (cmd)
2. Bu klasöre gidin: `cd "klasör_yolu"`
3. Virtual environment oluşturun: `python -m venv venv`
4. Aktifleştirin: `venv\\Scripts\\activate.bat`
5. Paketleri yükleyin: `pip install -r requirements.txt`
6. Uygulamayı başlatın: `python main.py`

## Sistem Gereksinimleri

- Windows 10/11 (64-bit)
- Python 3.13.5
- İnternet bağlantısı (veritabanı erişimi için)
- Minimum 4GB RAM
- 500MB boş disk alanı

## Sorun Giderme

### Python bulunamadı hatası:
- Python'u PATH'e eklediğinizden emin olun
- Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin

### Paket yükleme hataları:
- İnternet bağlantınızı kontrol edin
- Antivirüs yazılımınızı geçici olarak devre dışı bırakın

### Veritabanı bağlantı hatası:
- İnternet bağlantınızı kontrol edin
- Firewall ayarlarınızı kontrol edin

## Destek

Herhangi bir sorun yaşarsanız Bomaksan IT departmanı ile iletişime geçin.

© 2025 Bomaksan A.Ş
"""
    
    with open(os.path.join(package_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # ZIP dosyası oluştur
    zip_filename = "Bomaksan_Maliyet_VENV_Setup.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)
    
    print(f"✅ Virtual Environment kurulum paketi hazırlandı:")
    print(f"   📁 Klasör: {package_dir}")
    print(f"   📦 ZIP: {zip_filename}")

def main():
    """Ana fonksiyon"""
    print("🚀 Bomaksan Maliyet Analizleri - Virtual Environment Setup")
    print("=" * 60)
    
    try:
        create_venv_package()
        print("\n🎉 Virtual Environment paketi oluşturuldu!")
        
    except Exception as e:
        print(f"❌ Hata oluştu: {e}")

if __name__ == "__main__":
    main()
