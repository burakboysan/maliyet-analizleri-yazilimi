param(
    [switch]$RebuildPackage,
    [switch]$RequireSign,
    [switch]$SkipSign
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$issPath = Join-Path $repoRoot "installer\Bomaksan_Maliyet_Analizleri.iss"
$distInstallerDir = Join-Path $repoRoot "dist_installer"

function Find-Iscc {
    $candidates = @(
        (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

if (-not (Test-Path $issPath)) {
    throw "Inno Setup script bulunamadi: $issPath"
}

if ($RebuildPackage) {
    Push-Location $repoRoot
    try {
        $buildArgs = @("build_exe.py")
        if ($RequireSign) {
            $buildArgs += "--require-sign"
        }
        if ($SkipSign) {
            $buildArgs += "--skip-sign"
        }

        & py @buildArgs
        if ($LASTEXITCODE -ne 0) {
            throw "build_exe.py basarisiz oldu."
        }
    }
    finally {
        Pop-Location
    }
}

$isccPath = Find-Iscc
if (-not $isccPath) {
    throw "ISCC.exe bulunamadi. Inno Setup 6 kurulduktan sonra bu scripti yeniden calistirin."
}

New-Item -ItemType Directory -Path $distInstallerDir -Force | Out-Null

Push-Location $repoRoot
try {
    & $isccPath $issPath
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup derlemesi basarisiz oldu."
    }
}
finally {
    Pop-Location
}

$output = Get-ChildItem $distInstallerDir -Filter "*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $output) {
    throw "Derleme tamamlandi ancak dist_installer altinda setup.exe bulunamadi."
}

Write-Host ""
Write-Host "[OK] setup.exe uretildi:" -ForegroundColor Green
Write-Host $output.FullName -ForegroundColor Yellow
