param(
    [string]$CertificatePath = ".\code_signing\bomaksan-internal-code-signing.cer",
    [string]$OutputDirectory = ".\internal_signer_package"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolvedCertificatePath = Resolve-Path (Join-Path $repoRoot $CertificatePath) -ErrorAction Stop
$targetDirectory = Join-Path $repoRoot $OutputDirectory

New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

Copy-Item $resolvedCertificatePath -Destination (Join-Path $targetDirectory "bomaksan-internal-code-signing.cer") -Force
Copy-Item (Join-Path $PSScriptRoot "install_internal_signer.ps1") -Destination (Join-Path $targetDirectory "install_internal_signer.ps1") -Force
Copy-Item (Join-Path $PSScriptRoot "install_internal_signer.bat") -Destination (Join-Path $targetDirectory "install_internal_signer.bat") -Force

$readme = @"
Bomaksan ic imza sertifikasi kurulum paketi

Kullanim:
1. Bu klasoru kullanici bilgisayarina kopyalayin veya paylasimdan acin.
2. install_internal_signer.bat dosyasina cift tiklayin.
3. Kurulum tamamlandiginda pencereyi kapatin.

Bu paket sertifikayi su depolara ekler:
- CurrentUser\Root
- CurrentUser\TrustedPublisher
"@

Set-Content -Path (Join-Path $targetDirectory "README.txt") -Value $readme -Encoding ASCII

Write-Host ""
Write-Host "[OK] Dagitim paketi hazirlandi." -ForegroundColor Green
Write-Host $targetDirectory -ForegroundColor Yellow
