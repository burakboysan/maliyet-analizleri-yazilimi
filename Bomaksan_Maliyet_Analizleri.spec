# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('tkcalendar', 'tkcalendar'), ('bcrypt', 'bcrypt'), ('..\\Ürün Konfig App\\mobile_api\\reports', 'App/mobile_api/reports')],
    hiddenimports=['customtkinter', 'PIL', 'mysql.connector', 'tkcalendar', 'openpyxl', 'bcrypt', 'reportlab', 'reportlab.lib.pagesizes', 'reportlab.pdfbase', 'reportlab.pdfbase.pdfmetrics', 'reportlab.pdfbase.ttfonts', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas', 'proje_yonetimi.add_project', 'proje_yonetimi.edit_project', 'proje_yonetimi.project_management', 'teklif_yonetimi.add_quote', 'teklif_yonetimi.edit_quote'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bomaksan_Maliyet_Analizleri',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Bomaksan_Maliyet_Analizleri',
)
