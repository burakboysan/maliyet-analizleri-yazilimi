param(
    [string]$HostName,
    [int]$Port = 3306,
    [string]$DatabaseName,
    [string]$UserName,
    [string]$Password
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

$HostName = Read-RequiredValue -CurrentValue $HostName -PromptText "Veritabani host"
$DatabaseName = Read-RequiredValue -CurrentValue $DatabaseName -PromptText "Veritabani adi"
$UserName = Read-RequiredValue -CurrentValue $UserName -PromptText "Veritabani kullanici adi"
$Password = Read-RequiredValue -CurrentValue $Password -PromptText "Veritabani sifresi" -AsSecureString

$configDir = Join-Path $HOME ".bomaksan_config"
$configPath = Join-Path $configDir "db_config.json"

New-Item -ItemType Directory -Path $configDir -Force | Out-Null

$config = [ordered]@{
    host = $HostName
    port = $Port
    user = $UserName
    password = $Password
    database = $DatabaseName
    connection_timeout = 30
    pool_timeout = 5
    pool_size = 1
    use_pure = $true
    charset = "utf8mb4"
    collation = "utf8mb4_unicode_ci"
}

$json = $config | ConvertTo-Json -Depth 3
Set-Content -Path $configPath -Value $json -Encoding UTF8

Write-Host ""
Write-Host "Yapilandirma dosyasi olusturuldu:" -ForegroundColor Green
Write-Host $configPath -ForegroundColor Yellow
Write-Host ""
Write-Host "Uygulamayi simdi guvenli sekilde calistirabilirsiniz." -ForegroundColor Green
Write-Host ""
Read-Host "Devam etmek icin Enter tusuna basin"
