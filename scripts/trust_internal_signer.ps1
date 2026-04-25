param(
    [Parameter(Mandatory = $true)]
    [string]$CertificatePath,
    [ValidateSet("CurrentUser", "LocalMachine")]
    [string]$StoreLocation = "CurrentUser"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CertificatePath)) {
    throw "Sertifika dosyasi bulunamadi: $CertificatePath"
}

$rootStore = "Cert:\$StoreLocation\Root"
$publisherStore = "Cert:\$StoreLocation\TrustedPublisher"

Import-Certificate -FilePath $CertificatePath -CertStoreLocation $rootStore | Out-Null
Import-Certificate -FilePath $CertificatePath -CertStoreLocation $publisherStore | Out-Null

Write-Host ""
Write-Host "[OK] Sertifika guvenilen depolara eklendi." -ForegroundColor Green
Write-Host "Root            : $rootStore" -ForegroundColor Yellow
Write-Host "TrustedPublisher: $publisherStore" -ForegroundColor Yellow
