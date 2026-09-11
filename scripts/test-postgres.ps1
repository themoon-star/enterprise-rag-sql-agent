$ErrorActionPreference = "Stop"

$projectName = "trustquery-integration"
$env:ANALYTICS_ADMIN_PASSWORD = "admin-" + [guid]::NewGuid().ToString("N")
$env:ANALYTICS_READONLY_PASSWORD = "reader-" + [guid]::NewGuid().ToString("N")
$env:ANALYTICS_PORT = "55439"
$env:TEST_POSTGRES_URL = "postgresql://trustquery_reader:$($env:ANALYTICS_READONLY_PASSWORD)@127.0.0.1:$($env:ANALYTICS_PORT)/analytics"

try {
    docker compose -f compose.integration.yml -p $projectName up -d --wait
    uv run pytest backend/tests/integration/test_postgres_executor.py -q
}
finally {
    docker compose -f compose.integration.yml -p $projectName down -v
    Remove-Item Env:TEST_POSTGRES_URL -ErrorAction SilentlyContinue
    Remove-Item Env:ANALYTICS_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:ANALYTICS_READONLY_PASSWORD -ErrorAction SilentlyContinue
}
