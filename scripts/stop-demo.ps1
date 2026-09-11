$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$runtimeFile = Join-Path $root ".env.runtime"
if (-not (Test-Path -LiteralPath $runtimeFile)) {
    Write-Host "未发现 TrustQuery 演示运行文件，无需清理。"
    exit 0
}

Push-Location $root
try {
    docker compose -p trustquery-demo --env-file .env.runtime -f compose.yml down -v
    if ($LASTEXITCODE -ne 0) {
        throw "TrustQuery Docker Compose 清理失败"
    }
}
finally {
    Pop-Location
}

Remove-Item -LiteralPath $runtimeFile

Write-Host "TrustQuery 演示服务与本地数据卷已停止并清理。"
