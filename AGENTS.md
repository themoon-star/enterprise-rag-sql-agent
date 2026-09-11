# Repository Guidelines

## Clean-room rule

- Do not copy source code, README text, screenshots, assets, or Git history from Yuxi or SQLBot.
- Implement behavior from this repository's specifications and tests.
- Third-party libraries may be used through their public APIs and must remain declared in `pyproject.toml` or `frontend/package.json`.

## Engineering rule

- Prefer the smallest implementation that satisfies a written acceptance criterion.
- Every security boundary needs a focused test before it is considered complete.
- Tenant identity must come from a verified token, never from a request-body tenant id.
- Repaired SQL must traverse the same validator as first-pass SQL.
- Keep credentials out of responses, logs, fixtures, reports, and commits.
- Update `docs/PROGRESS.md` after every completed milestone.

## Verification order

1. Focused tests.
2. Full backend/frontend tests.
3. Ruff/ESLint and production build.
4. Docker Compose acceptance and fixed evaluation sets.
5. Secret and license scan before publishing.

