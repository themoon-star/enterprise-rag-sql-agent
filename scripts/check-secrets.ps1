$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    docker run --rm -v "${PWD}:/repo:ro" zricethezav/gitleaks:v8.28.0 detect --source=/repo --redact --no-banner
    if ($LASTEXITCODE -ne 0) {
        throw "Git 历史敏感信息扫描未通过"
    }

    docker run --rm -v "${PWD}:/repo:ro" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-git --redact --no-banner
    if ($LASTEXITCODE -ne 0) {
        throw "当前工作树敏感信息扫描未通过"
    }
}
finally {
    Pop-Location
}
