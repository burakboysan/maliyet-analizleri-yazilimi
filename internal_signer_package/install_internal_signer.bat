@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_internal_signer.ps1" -CertificatePath "%SCRIPT_DIR%bomaksan-internal-code-signing.cer"

if errorlevel 1 (
    echo.
    echo [HATA] Sertifika kurulumu basarisiz oldu.
    pause
    exit /b 1
)

exit /b 0
