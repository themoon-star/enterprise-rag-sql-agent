# Quality and publication audit

Audit date: 2026-09-11.

## Verification results

| Check | Result |
|---|---|
| Ruff over `backend` and `scripts` | PASS |
| Pytest without external database | 39 passed, 2 PostgreSQL-only tests skipped |
| Real PostgreSQL executor suite | 2 passed |
| Fixed acceptance evaluation | 100 RAG PASS; 50 Text-to-SQL PASS |
| Vue ESLint / TypeScript / production build | PASS / PASS / PASS |
| Browser acceptance | Desktop RAG and SQL flows PASS; 390 px layout has no horizontal overflow; console issues 0 |
| Gitleaks v8.28.0 | Full Git history PASS; publication worktree PASS |
| pip-audit | No known third-party Python vulnerabilities; local package correctly skipped as non-PyPI |
| npm audit | 0 vulnerabilities across 198 dependency entries |
| License review | Permissive direct/runtime licenses; no missing npm license metadata |
| GitHub Actions workflow | actionlint 1.7.7 PASS |

## Reproduction commands

```powershell
uv sync --frozen
uv run ruff check backend scripts
uv run pytest -q
.\scripts\test-postgres.ps1
.\scripts\run-evaluations.ps1
.\scripts\check-secrets.ps1

Set-Location frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run typecheck
npm run build
```

Python vulnerability audit:

```powershell
uv export --frozen --no-hashes --format requirements-txt --output-file reports/raw/requirements.txt
uvx --from pip-audit pip-audit -r reports/raw/requirements.txt
```

`reports/raw/` is ignored because scanner intermediates can contain machine-specific paths. Committed
evidence is limited to the fixed evaluation report and this redacted audit summary.

## Known evidence boundary

The two tests skipped by the ordinary `pytest` command require `TEST_POSTGRES_URL`; the dedicated
PowerShell runner starts an isolated PostgreSQL container and executes both. The fixed metrics remain
synthetic/offline evidence and do not claim production traffic or live-model quality.
