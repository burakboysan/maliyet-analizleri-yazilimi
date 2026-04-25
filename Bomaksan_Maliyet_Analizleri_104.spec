# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('tkcalendar', 'tkcalendar'), ('bcrypt', 'bcrypt')],
    hiddenimports=['customtkinter', 'PIL', 'mysql.connector', 'tkcalendar', 'openpyxl', 'bcrypt', 'proje_yonetimi.add_project', 'proje_yonetimi.edit_project', 'proje_yonetimi.project_management', 'teklif_yonetimi.add_quote', 'teklif_yonetimi.edit_quote'],
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
    a.binaries,
    a.datas,
    [],
    name='Bomaksan_Maliyet_Analizleri_104',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo_icon.ico'],
)
