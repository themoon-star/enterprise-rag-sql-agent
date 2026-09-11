# Third-party dependency review

Reviewed on 2026-09-11 from the locked Python and npm dependency metadata. The project license is MIT;
dependency licenses remain with their respective copyright holders.

## Direct Python dependencies

| Package | Locked version | License |
|---|---:|---|
| aiosqlite | 0.22.1 | MIT |
| asyncpg | 0.31.0 | Apache-2.0 |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| FastAPI | 0.141.1 | MIT |
| HTTPX | 0.28.1 | BSD-3-Clause |
| pydantic-settings | 2.15.0 | MIT |
| PyJWT | 2.13.0 | MIT |
| SQLAlchemy | 2.0.52 | MIT |
| SQLGlot | 30.18.0 | MIT |
| Uvicorn | 0.52.4 | BSD-3-Clause |

Python development tools are pytest 9.1.1 (MIT), pytest-asyncio 1.4.0 (Apache-2.0), Ruff 0.16.7
(MIT), and HTTPX2 2.12.0 (BSD-3-Clause).

## Direct frontend dependencies

| Package | Locked version | License |
|---|---:|---|
| Vue | 3.5.42 | MIT |
| @lucide/vue | 1.44.0 | ISC |
| @vitejs/plugin-vue | 6.0.8 | MIT |
| Vite | 7.3.6 | MIT |
| TypeScript | 5.9.3 | Apache-2.0 |
| vue-tsc | 3.3.11 | MIT |
| ESLint | 10.10.0 | MIT |
| typescript-eslint | 8.70.0 | MIT |
| eslint-plugin-vue | 10.11.0 | MIT |

The npm lock contains 198 dependency entries: 165 MIT, 14 Apache-2.0, 8 ISC, 8 BSD-2-Clause,
2 BSD-3-Clause and 1 BlueOak-1.0.0; none have missing license metadata.

## Container images

- Python base image: Python Software Foundation License; uv is MIT OR Apache-2.0.
- Node.js build image: MIT; Nginx runtime image: BSD-2-Clause.
- PostgreSQL image: PostgreSQL License.

This file is a compatibility inventory, not a substitute for the complete license texts distributed
by each package or image.
