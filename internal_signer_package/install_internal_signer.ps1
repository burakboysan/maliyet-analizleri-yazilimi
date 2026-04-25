param(
    [string]$CertificatePath
)

$ErrorActionPreference = "Stop"

if (-not $CertificatePath) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $CertificatePath = Join-Path $scriptDir "bomaksan-internal-code-signing.cer"
}

$resolvedCertificatePath = Resolve-Path $CertificatePath -ErrorAction Stop
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($resolvedCertificatePath)

Import-Certificate -FilePath $resolvedCertificatePath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
Import-Certificate -FilePath $resolvedCertificatePath -CertStoreLocation "Cert:\CurrentUser\TrustedPublisher" | Out-Null

$rootMatch = Get-ChildItem "Cert:\CurrentUser\Root" | Where-Object { $_.Thumbprint -eq $cert.Thumbprint } | Select-Object -First 1
$publisherMatch = Get-ChildItem "Cert:\CurrentUser\TrustedPublisher" | Where-Object { $_.Thumbprint -eq $cert.Thumbprint } | Select-Object -First 1

if (-not $rootMatch -or -not $publisherMatch) {
    throw "Sertifika depolara eklendi ancak dogrulama basarisiz."
}

Write-Host ""
Write-Host "[OK] Bomaksan ic imza sertifikasi kuruldu." -ForegroundColor Green
Write-Host "Konu      : $($cert.Subject)" -ForegroundColor Yellow
Write-Host "Thumbprint: $($cert.Thumbprint)" -ForegroundColor Yellow
Write-Host "Root      : CurrentUser\\Root" -ForegroundColor Yellow
Write-Host "Publisher : CurrentUser\\TrustedPublisher" -ForegroundColor Yellow
Write-Host ""
Read-Host "Pencereyi kapatmak icin Enter tusuna basin"
