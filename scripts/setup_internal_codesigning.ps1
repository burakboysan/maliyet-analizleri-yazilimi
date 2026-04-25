param(
    [string]$Subject = "Bomaksan Internal Code Signing - bomaksan.com",
    [int]$ValidYears = 3,
    [string]$ExportDirectory,
    [switch]$ExportPfx,
    [string]$PfxPassword
)

$ErrorActionPreference = "Stop"

function Read-RequiredValue {
    param(
        [string]$CurrentValue,
        [string]$PromptText,
        [switch]$AsSecureString
    )

    if ($CurrentValue) {
        return $CurrentValue
    }

    if ($AsSecureString) {
        $secure = Read-Host -Prompt $PromptText -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }

    return (Read-Host -Prompt $PromptText).Trim()
}

function Set-UserEnvironmentVariable {
    param(
        [string]$Name,
        [string]$Value
    )

    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    if ($null -eq $Value) {
        Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
    }
    else {
        Set-Item "Env:$Name" $Value
    }
}

if (-not $ExportDirectory) {
    $ExportDirectory = Join-Path $env:USERPROFILE "BomaksanCodeSigning"
}

New-Item -ItemType Directory -Path $ExportDirectory -Force | Out-Null

$cert = New-SelfSignedCertificate `
    -Subject "CN=$Subject" `
    -Type CodeSigningCert `
    -KeyAlgorithm RSA `
    -KeyLength 3072 `
    -HashAlgorithm SHA256 `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears($ValidYears) `
    -FriendlyName "Bomaksan Internal Code Signing"

if (-not $cert) {
    throw "Self-signed code signing sertifikasi olusturulamadi."
}

$cerPath = Join-Path $ExportDirectory "bomaksan-internal-code-signing.cer"
Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null

[Environment]::SetEnvironmentVariable("BOMAKSAN_SIGN_CERT_SHA1", $cert.Thumbprint, "User")
[Environment]::SetEnvironmentVariable("BOMAKSAN_SIGN_CERT_SUBJECT", $cert.Subject, "User")
Set-Item "Env:BOMAKSAN_SIGN_CERT_SHA1" $cert.Thumbprint
Set-Item "Env:BOMAKSAN_SIGN_CERT_SUBJECT" $cert.Subject

if ($ExportPfx) {
    $PfxPassword = Read-RequiredValue -CurrentValue $PfxPassword -PromptText "PFX sifresi" -AsSecureString
    $securePassword = ConvertTo-SecureString -String $PfxPassword -AsPlainText -Force
    $pfxPath = Join-Path $ExportDirectory "bomaksan-internal-code-signing.pfx"
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $securePassword | Out-Null
    Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_PFX_PATH" -Value $pfxPath
    Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_PFX_PASSWORD" -Value $PfxPassword
}

Write-Host ""
Write-Host "[OK] Sirket ici code signing sertifikasi hazirlandi." -ForegroundColor Green
Write-Host "Konu      : $($cert.Subject)" -ForegroundColor Yellow
Write-Host "Thumbprint: $($cert.Thumbprint)" -ForegroundColor Yellow
Write-Host "CER       : $cerPath" -ForegroundColor Yellow
if ($ExportPfx) {
    Write-Host "PFX       : $pfxPath" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Bu makinede imzali build almak icin:" -ForegroundColor Cyan
Write-Host "py build_exe.py --release --require-sign" -ForegroundColor Yellow
Write-Host ""
Write-Host "Istemci makinelere guven dagitimi icin:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File .\scripts\trust_internal_signer.ps1 -CertificatePath `"$cerPath`"" -ForegroundColor Yellow
