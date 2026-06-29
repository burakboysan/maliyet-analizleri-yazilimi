#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veritabanı Bağlantı Test Script'i
"""

import sys
import os

# Proje dizinini Python path'ine ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Veritabanı bağlantısını test et"""
    print("🔍 Veritabanı bağlantısı test ediliyor...")
    
    try:
        from core.database import veritabani_baglanti, close_connection
        
        # Bağlantıyı test et
        connection = veritabani_baglanti()
        
        if connection and connection.is_connected():
            print("✅ Veritabanı bağlantısı başarılı!")
            
            # Basit bir sorgu test et
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result:
                print("✅ Sorgu testi başarılı!")
            else:
                print("❌ Sorgu testi başarısız!")
            
            cursor.close()
            close_connection(connection)
            return True
        else:
            print("❌ Veritabanı bağlantısı başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        return False

def test_auth():
    """Kimlik doğrulama test et"""
    print("\n🔍 Kimlik doğrulama test ediliyor...")
    
    try:
        from core.auth import kullanici_giris_yap
        
        # Test kullanıcısı ile giriş dene
        kullanici_adi, rol = kullanici_giris_yap("admin", "admin123")
        
        if kullanici_adi and rol:
            print(f"✅ Kimlik doğrulama başarılı! Kullanıcı: {kullanici_adi}, Rol: {rol}")
            return True
        else:
            print("❌ Kimlik doğrulama başarısız!")
            return False
            
    except Exception as e:
        print(f"❌ Kimlik doğrulama hatası: {e}")
        return False

def test_imports():
    """Gerekli modüllerin import edilip edilemediğini test et"""
    print("🔍 Modül import testleri...")
    
    modules = [
        ("customtkinter", "GUI kütüphanesi"),
        ("PIL", "Resim işleme"),
        ("psycopg", "PostgreSQL bağlantısı"),
        ("tkcalendar", "Takvim widget'ı"),
        ("openpyxl", "Excel işleme"),
        ("bcrypt", "Şifreleme")
    ]
    
    all_ok = True
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name} ({description}) - OK")
        except ImportError as e:
            print(f"❌ {module_name} ({description}) - HATA: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Ana test fonksiyonu"""
    print("🚀 Bomaksan Maliyet Analizleri - Bağlantı Testi")
    print("=" * 60)
    
    # 1. Modül import testleri
    imports_ok = test_imports()
    
    # 2. Veritabanı bağlantı testi
    db_ok = test_database_connection()
    
    # 3. Kimlik doğrulama testi
    auth_ok = test_auth()
    
    print("\n" + "=" * 60)
    print("📊 TEST SONUÇLARI:")
    print(f"   Modül Importları: {'✅ BAŞARILI' if imports_ok else '❌ BAŞARISIZ'}")
    print(f"   Veritabanı Bağlantısı: {'✅ BAŞARILI' if db_ok else '❌ BAŞARISIZ'}")
    print(f"   Kimlik Doğrulama: {'✅ BAŞARILI' if auth_ok else '❌ BAŞARISIZ'}")
    
    if imports_ok and db_ok and auth_ok:
        print("\n🎉 Tüm testler başarılı! Yazılım çalışmaya hazır.")
    else:
        print("\n⚠️ Bazı testler başarısız. Sorunları kontrol edin.")
    
    input("\nDevam etmek için Enter'a basın...")

if __name__ == "__main__":
    main()
