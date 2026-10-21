# Start here — SuriPH research prototype

**Implemented and locally tested; deployment prepared; not publicly deployed.**
See [the release evidence and GO/NO-GO gate](docs/RELEASE-READINESS.md) before inviting participants.
The [documentation index](docs/README.md) maps research references, setup and deployment.
The selected hybrid model is verified. An isolated Edge Chromium extension rehearsal
passed; Linux containers, production HTTPS and a manual Chrome/assistive-tech study
session still need completion.

## This prepared Windows workstation

Run from `hybrid taglish-detector system`, not its parent folder. Preserve the existing
private `.env.local`; do not overwrite it with examples. Python 3.13 was tested here.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend-api\requirements-test.txt
.\scripts\start-mariadb.ps1
cd backend-api
..\.venv\Scripts\python.exe -m src.manage migrate
..\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

For a fresh checkout, first create `.venv` with `python -m venv .venv`. The portable
database scripts are specific to this prepared workstation; use Compose below for
a reproducible fresh database. Never reuse its development login in production.

In a second terminal, from the project root:

```powershell
cd admin-dashboard
npm ci
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173` (use the same host spelling as the API for local cookies).
Read the private local administrator/viewer credentials from `backend-api/.env.local`.
The dashboard uses an HttpOnly session cookie; no token is kept in localStorage.

In a third terminal:

```powershell
cd chrome-extension
npm ci
npm run build
```

Open `chrome://extensions`, enable Developer mode, **Load unpacked**, select
`chrome-extension/dist`. Reload existing installs and supported pages after a build.
Manual text works from the popup; selection/caption extraction requires a supported
social page. Media extraction is experimental and has only synthetic smoke evidence.
No Chrome Web Store publication has occurred.

Check the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/analyze -Method Post -ContentType application/json -Body '{"text":"Basahin muna ang buong balita bago mag-share."}'
```

The default request saves nothing and does not query an external evidence provider.
The popup has one unchecked choice for external source lookup. Participant surveys and
responses are handled separately from the extension and administrator dashboard; the
screening API does not save them.

## Reproducible local Compose rehearsal (Docker required)

This machine has no Docker, so these commands are prepared, **not claimed executed**.
Install Docker with Compose on the test host. Preserve the artifact directory described
in [the integration guide](docs/HYBRID-INTEGRATION.md). No domain or hosting purchase is needed.

```powershell
python scripts/prepare_local.py
docker compose --env-file .env.local-stack config --quiet
docker compose --env-file .env.local-stack build
docker compose --env-file .env.local-stack up -d database
docker compose --env-file .env.local-stack --profile maintenance run --rm migrate
docker compose --env-file .env.local-stack up -d --wait --wait-timeout 600 api admin
docker compose --env-file .env.local-stack ps
```

API: `http://127.0.0.1:8000`; dashboard: `http://127.0.0.1:8080`.
The named database volume belongs to project `suriph-local`; no database port is exposed.
The API account has SELECT/INSERT/UPDATE/DELETE only. The separate one-shot migration
service provisions it and applies schema v5. Root/maintenance credentials are cleared
from the running API environment. Do not start two local APIs on port 8000.

Stop without deleting data:

```powershell
docker compose --env-file .env.local-stack stop
```

## Repeat the verification

From the project root (local model artifacts and test records required):

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s backend-api/tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -B backend-api/scripts/verify_hybrid.py
.\.venv\Scripts\python.exe -B backend-api/scripts/verify_http.py
.\.venv\Scripts\python.exe scripts/verify_mariadb_local.py
.\.venv\Scripts\python.exe scripts/verify_providers.py
.\.venv\Scripts\python.exe scripts/verify_media_local.py
.\.venv\Scripts\python.exe scripts/verify_deployment.py
node scripts/verify_ui.mjs
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_live_stack.ps1
$env:SURI_TEST_BROWSER='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
node scripts/verify_installed_extension.mjs
node scripts/verify_admin_browser.mjs
```

The MariaDB/media scripts use this workstation's portable MariaDB and Windows speech/font
tools. Provider checks use configured keys and public synthetic queries; no secrets are
printed. UI checks use installed headless Chrome, real React components and the live API
test result. The installed-extension script uses an isolated Edge Chromium profile and a
synthetic supported-origin fixture; it does not test current third-party DOMs or accounts.
All isolated test data are synthetic and ignored by Git. Do not use participant records
as test fixtures. Run `npm run lint` and `npm run build` in the dashboard, and `npm run build`
in the extension after UI edits.

## Research and launch materials

- [Participant instructions and draft consent](docs/research/PARTICIPANT-GUIDE.md)
- [Separate questionnaires and response format](docs/research/QUESTIONNAIRES.md)
- [Pilot checklist, expert test form and traceability](docs/research/PILOT-AND-TRACEABILITY.md)
- [VPS, HTTPS, backup/restore and operations](docs/DEPLOYMENT.md)
- [Measured results and exact external release steps](docs/RELEASE-READINESS.md)
