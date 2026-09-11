$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$runtimeFile = Join-Path $root ".env.runtime"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path -LiteralPath $runtimeFile)) {
    $secretKey = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)).ToLower()
    $fernetKey = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $fernetKey = $fernetKey.Replace("+", "-").Replace("/", "_")
    $metadataPassword = "meta-" + [guid]::NewGuid().ToString("N")
    $analyticsAdminPassword = "admin-" + [guid]::NewGuid().ToString("N")
    $analyticsReadonlyPassword = "reader-" + [guid]::NewGuid().ToString("N")

    $environment = @(
        "APP_SECRET_KEY=$secretKey",
        "APP_CREDENTIAL_ENCRYPTION_KEY=$fernetKey",
        "METADATA_PASSWORD=$metadataPassword",
        "ANALYTICS_ADMIN_PASSWORD=$analyticsAdminPassword",
        "ANALYTICS_READONLY_PASSWORD=$analyticsReadonlyPassword",
        "API_PORT=8100",
        "WEB_PORT=3100"
    )
    [System.IO.File]::WriteAllLines($runtimeFile, $environment, $utf8NoBom)
}

Push-Location $root
try {
    docker compose -p trustquery-demo --env-file .env.runtime -f compose.yml up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "TrustQuery Docker Compose 启动失败"
    }
}
finally {
    Pop-Location
}

Write-Host "TrustQuery 已启动：http://localhost:3100"
Write-Host "API 文档：http://localhost:8100/docs"
