param(
    [string]$PfxPath,
    [string]$Password,
    [ValidateSet("CurrentUser", "LocalMachine")]
    [string]$StoreLocation = "CurrentUser",
    [switch]$UsePfxDirectly,
    [switch]$SkipImport
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

function Find-SignTool {
    $kitsRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
    $candidates = @(
        (Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        "$env:ProgramFiles(x86)\Windows Kits\10\App Certification Kit\signtool.exe",
        "$env:ProgramFiles(x86)\Windows Kits\10\bin\x64\signtool.exe"
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    if (Test-Path $kitsRoot) {
        $latest = Get-ChildItem $kitsRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "x64\signtool.exe" } |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
        if ($latest) {
            return $latest
        }
    }

    return $null
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

function Clear-BomaksanSigningVariables {
    $names = @(
        "BOMAKSAN_SIGN_CERT_SUBJECT",
        "BOMAKSAN_SIGN_CERT_SHA1",
        "BOMAKSAN_SIGN_PFX_PATH",
        "BOMAKSAN_SIGN_PFX_PASSWORD"
    )

    foreach ($name in $names) {
        Set-UserEnvironmentVariable -Name $name -Value $null
    }
}

$signToolPath = Find-SignTool
if ($signToolPath) {
    Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGNTOOL_PATH" -Value $signToolPath
    Write-Host "[OK] Signtool bulundu:" -ForegroundColor Green
    Write-Host $signToolPath -ForegroundColor Yellow
}
else {
    Write-Warning "signtool.exe bulunamadi. Windows 10/11 SDK veya App Certification Kit kurmaniz gerekecek."
}

if (-not $SkipImport) {
    $PfxPath = Read-RequiredValue -CurrentValue $PfxPath -PromptText "PFX dosya yolu"
}

if ($PfxPath -and -not (Test-Path $PfxPath)) {
    throw "PFX dosyasi bulunamadi: $PfxPath"
}

if ($UsePfxDirectly) {
    $Password = Read-RequiredValue -CurrentValue $Password -PromptText "PFX sifresi" -AsSecureString
    Clear-BomaksanSigningVariables
    Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_PFX_PATH" -Value $PfxPath
    Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_PFX_PASSWORD" -Value $Password

    Write-Host ""
    Write-Host "[OK] Kod imzalama PFX modu ile ayarlandi." -ForegroundColor Green
    Write-Host "Sonraki adim:" -ForegroundColor Cyan
    Write-Host "py build_exe.py --release --require-sign" -ForegroundColor Yellow
    exit 0
}

$importedCertificate = $null
if (-not $SkipImport) {
    $Password = Read-RequiredValue -CurrentValue $Password -PromptText "PFX sifresi" -AsSecureString
    $securePassword = ConvertTo-SecureString -String $Password -AsPlainText -Force
    $storePath = "Cert:\$StoreLocation\My"
    $importedCertificate = Import-PfxCertificate -FilePath $PfxPath -CertStoreLocation $storePath -Password $securePassword -Exportable
}
else {
    $storePath = "Cert:\$StoreLocation\My"
    $certificates = Get-ChildItem $storePath | Where-Object {
        $_.EnhancedKeyUsageList.FriendlyName -contains "Code Signing"
    } | Sort-Object NotAfter -Descending

    if (-not $certificates) {
        throw "Code Signing amacli bir sertifika bulunamadi: $storePath"
    }

    $importedCertificate = $certificates | Select-Object -First 1
}

if (-not $importedCertificate) {
    throw "Kod imzalama sertifikasi hazirlanamadi."
}

Clear-BomaksanSigningVariables
Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_CERT_SHA1" -Value $importedCertificate.Thumbprint
Set-UserEnvironmentVariable -Name "BOMAKSAN_SIGN_CERT_SUBJECT" -Value $importedCertificate.Subject

Write-Host ""
Write-Host "[OK] Kod imzalama sertifikasi ayarlandi." -ForegroundColor Green
Write-Host "Konu      : $($importedCertificate.Subject)" -ForegroundColor Yellow
Write-Host "Thumbprint: $($importedCertificate.Thumbprint)" -ForegroundColor Yellow
Write-Host "Depo      : $StoreLocation\My" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test komutu:" -ForegroundColor Cyan
Write-Host "py build_exe.py --release --require-sign" -ForegroundColor Yellow
