$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    docker compose -p trustquery-demo --env-file .env.runtime -f compose.yml down -v
}
finally {
    Pop-Location
}

Write-Host "TrustQuery 演示服务与本地数据卷已停止并清理。"
