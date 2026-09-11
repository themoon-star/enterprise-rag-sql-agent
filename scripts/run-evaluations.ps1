$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$projectName = "trustquery-evaluation"
$env:ANALYTICS_ADMIN_PASSWORD = "admin-" + [guid]::NewGuid().ToString("N")
$env:ANALYTICS_READONLY_PASSWORD = "reader-" + [guid]::NewGuid().ToString("N")
$env:ANALYTICS_PORT = "55439"
$env:EVAL_POSTGRES_URL = "postgresql://trustquery_reader:$($env:ANALYTICS_READONLY_PASSWORD)@127.0.0.1:$($env:ANALYTICS_PORT)/analytics"

Push-Location $root
try {
    docker compose -f compose.integration.yml -p $projectName up -d --wait
    if ($LASTEXITCODE -ne 0) {
        throw "评测 PostgreSQL 启动失败"
    }
    uv run python scripts/run_evaluations.py
    $evaluationExitCode = $LASTEXITCODE
}
finally {
    docker compose -f compose.integration.yml -p $projectName down -v
    Remove-Item Env:EVAL_POSTGRES_URL -ErrorAction SilentlyContinue
    Remove-Item Env:ANALYTICS_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ANALYTICS_READONLY_PASSWORD -ErrorAction SilentlyContinue
    Pop-Location
}

if ($evaluationExitCode -ne 0) {
    throw "固定评测未通过"
}
