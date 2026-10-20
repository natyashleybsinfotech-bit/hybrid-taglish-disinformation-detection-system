# Project structure and cleanup

| Location | Purpose |
| --- | --- |
| `backend-api/src/` | Active API, fixed model pipeline, database/migrations, retrieval and media |
| `backend-api/config.py`, `requirements*.txt`, `Dockerfile` | Backend tool entry points and dependencies |
| `backend-api/scripts/` | Model verification, HTTP verification, benchmark and maintenance utilities |
| `backend-api/tests/` | Backend regression tests, including explicitly imported legacy feature tests |
| `chrome-extension/` | Extension sources, Vite configuration and transport test |
| `admin-dashboard/` | Dashboard sources, Vite/ESLint configuration and image build |
| `scripts/` | Cross-project setup, backup, survey validation and verification tools |
| `deploy/`, root `docker-compose.yml` | Proxy, maintenance timer and container service configuration |
| `docs/references/` | Preserved paper, requirements, prototype and agent-instruction documents |
| `docs/research/` | Draft participant and evaluation materials |
| `docs/tools/` | Historical SDD generator and sections; npm configuration stays in `docs/` |
| `archive/legacy-backend/` | Historical code removed from active runtime and Docker context |

The backend script paths are based on their own file locations, so commands work
from either the repository root or `backend-api/`. The API entry point remains
`src.app:app` from `backend-api/`. Model mounts, Docker contexts, environment paths,
database paths and migration entry points have not moved.

Moves were checked with SHA-256 before and after each move. The inventory records
the bytes **at move time**; script path fixes made afterward are visible in Git.
Reference documents and archived code retain those recorded bytes. No recursive
deletion was used. Empty former directories can remain harmlessly on this workstation.

The existing virtual environments, model export, local credentials, database files,
backups, temporary investigations, tools and participant data are preserved.
VS Code now hides generated dependencies, runtime caches, `tmp/` and `tools/` from
Explorer and excludes large/private data from searches. **Hidden is not deleted.**
Disable the relevant `.vscode/settings.json` exclusions to browse those folders.
No cleanup inference was made from a folder being named `tmp` or `old`.

Generated extension `dist/` is no longer tracked, matching the dashboard. Run
`npm ci` and `npm run build` in the extension for local installation; use
`npm run build:release` with the real HTTPS API setting for a release. Existing
local build files remain. Earlier tracked datasets/model binaries are untracked;
historical Git copies have not been rewritten or purged.

The previously tracked `chrome-extension/node_modules/` and `docs/node_modules/`
dependencies are also removed from the Git index only. Their installed files
remain locally, and both npm lockfiles remain tracked for reproducible `npm ci`.

Maintenance utilities that create users or sample candidates should be run only
intentionally against the appropriate database. The sample utility contains
development examples, not participant data or classifier-generated predictions.
It is not invoked by the API, startup scripts or deployment.
