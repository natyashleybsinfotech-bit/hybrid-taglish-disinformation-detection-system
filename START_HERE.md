# Start here — SuriPH research prototype

**Current extension build: 1.3.29.** On 14 November, the backend suite passed **188 tests**, the extension passed **20 behavior tests** and its product contract, and the extension build passed. `/ready` returned true with MariaDB and the pinned model. A local text/image/video smoke check passed using a synthetic English speech clip: repeated text returned the same label and score, image OCR matched its known text, and the confirmed video transcript matched its known audio (21.46 seconds). Three simultaneous short-text requests returned HTTP 200 in 203 ms total on this workstation. A separate [live-stack report](docs/LIVE-STACK-PERFORMANCE.json) used longer synthetic text payloads and measured three concurrent HTTP 200 responses in 4.90 seconds. Those workloads are not directly comparable; neither is an SLA or a target-server capacity result. These are local functional/latency checks, not natural Taglish/news-video or factual-classification accuracy results.

**Still unresolved:** material speech-recognition errors in the GMA news clip; known classifier false positives and no independent real-world accuracy result; the user's installed Google Chrome/Facebook rehearsal and accessibility checks; Linux/Docker deployment; and institutional review before participant research. A known true health claim was classified as Potentially Misleading when lookup was off; with lookup on, a readable CDC article directly supporting it corrected the final label. This is one checked case, not a general accuracy guarantee. Keep related-source lookup enabled for the demo and compare each result with the full source. Do not claim every transcript or prediction is accurate, survey approval, or public readiness. Videos whose speech and sampled on-screen text disagree now stop for human text review before classification; that safeguard does not correct a misheard transcript when the screen text cannot reveal it.

On the first API start during this rehearsal, Windows Application Control blocked a native Python module and `/ready` returned 503. A fresh process start succeeded without changing the security policy. If this recurs, retain the error and ask the machine administrator; do not disable or bypass Application Control.

For item 2.5, the current acceptance checklist describes simultaneous requests against capacity, not a numeric response-time target. The production traffic guard admits two concurrent screening requests and returns HTTP 503 with a retry hint for excess requests; a backend test verifies rejection and recovery. A separate local smoke run returned HTTP 200 for three short-text requests in 203 ms total, but that does not measure saturation, establish target-server capacity, or set an SLA. Confirm the evaluator's pass criterion and demonstrate the target server before marking the item passed. Items 6.5 and 8.4 also require a deployed HTTPS service and a second supported Chrome setup, respectively. The current loopback HTTP rehearsal cannot be reported as passing those items.

**Current change records:** [14 November source-preview and score clarification](docs/SOURCE-PREVIEW-AND-SCORE-20261114.md), [video mismatch review, evidence wording, tests and remaining limits](docs/VIDEO-MISMATCH-REVIEW-20261113.md). **Historical records:** [consolidated software status](docs/FINAL-SOFTWARE-STATUS-20261112.md), [readable-source and Windows dependency repair](docs/FINISHING-REPAIR-20261112.md), [model/source/admin refinement](docs/SYSTEM-REFINEMENT-20261112.md), [speech comparison](docs/SPEECH-IMPROVEMENT-20261112.md), and [defense rehearsal](docs/DEFENSE-REHEARSAL-20261110.md). Their test counts and extension versions refer to the earlier snapshots they describe. The [questionnaire checklist](docs/research/QUESTIONNAIRE-ACCEPTANCE-20261110.md), [November 2 findings](docs/FINISHING-STATUS-20261102.md), and [October 29 readiness checklist](docs/CURRENT-READINESS-20261029.md) remain historical research context.

**Implemented and locally tested; deployment prepared; not publicly deployed.**
See [the release evidence and GO/NO-GO gate](docs/RELEASE-READINESS.md) before inviting participants.
The [documentation index](docs/README.md) maps research references, setup and deployment.
The active hybrid's saved-output parity is verified, but factual accuracy is not.
The prepared workstation selects the local-trial candidate described in
[LOCAL-CANDIDATE-TRIAL.md](docs/LOCAL-CANDIDATE-TRIAL.md); it is not approved for production.
An earlier isolated Edge Chromium extension rehearsal
passed; Linux containers, production HTTPS and a manual Google Chrome/Facebook study
session still need completion.

## This prepared Windows workstation

Run from `hybrid taglish-detector system`, not its parent folder. Preserve the existing
private `.env.local`; do not overwrite it with examples. Python 3.13 was tested here.

```powershell
.\.venv-candidate-20261023-isolated\Scripts\python.exe -m pip install -r backend-api\requirements-test-candidate.txt
.\scripts\start-mariadb.ps1
cd backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m src.manage migrate
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

For a fresh candidate trial, first create `.venv-candidate-20261023-isolated` with
`python -m venv .venv-candidate-20261023-isolated` and install
`backend-api/requirements-candidate.txt`. The portable
database scripts are specific to this prepared workstation; use Compose below for
a reproducible fresh database. Never reuse its development login in production.

In a second terminal, from the project root:

```powershell
cd admin-dashboard
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173` (use the same host spelling as the API for local cookies).
Read the private local administrator/viewer credentials from `backend-api/.env.local`.
The dashboard uses an HttpOnly session cookie; no token is kept in localStorage.

In a third terminal:

```powershell
cd chrome-extension
npm.cmd ci
npm.cmd run build
```

Open `chrome://extensions`, enable Developer mode, **Load unpacked**, select
`chrome-extension/dist`. Reload existing installs and supported pages after a build.
Manual text works from the popup; selection/caption extraction is supported only on
Facebook. Media extraction remains experimental; [three natural news-video checks](docs/VIDEO-EXTRACTION-VALIDATION-20261103.md) exposed transcription errors. A speech/frame mismatch now triggers review before classification; matched-but-wrong transcripts remain possible. The installed Google Chrome/Facebook media flow still needs the user's live observation.
No Chrome Web Store publication has occurred.

Check the API:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/analyze -Method Post -ContentType application/json -Body '{"text":"Basahin muna ang buong balita bago mag-share."}'
```

The default request saves nothing and does not query an external evidence provider.
Version 1.3.27 retains the visible related-source choice enabled after install/update. Public
Facebook screening requests related reports from approved publishers by default.
The final output has exactly two labels. Only sufficient claim-specific evidence from readable articles can change the model prediction; merely related links cannot.
When evidence is insufficient, the model prediction remains visible and is
explicitly identified as unverified. Media results separate caption, speech,
and sampled frame text; uncertain speech quality can stop the request without
producing a prediction. See the current handoff for the measured checks and limits.
Users can turn evidence lookup off before analysis. A separate explicit-consent
action can submit the analyzed text to the private human-review queue; it does not add the
text to a dataset. Participant surveys and responses are handled separately from the
extension and administrator dashboard; the screening API does not save them.

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
service provisions it and applies schema v6. Root/maintenance credentials are cleared
from the running API environment. Do not start two local APIs on port 8000.

Stop without deleting data:

```powershell
docker compose --env-file .env.local-stack stop
```

## Repeat the verification

From the project root (local model artifacts and test records required):

```powershell
.\.venv-candidate-20261023-isolated\Scripts\python.exe -B -m pytest backend-api/tests -q
.\.venv-candidate-20261023-isolated\Scripts\python.exe -B backend-api/scripts/verify_candidate_regressions.py
.\.venv-candidate-20261023-isolated\Scripts\python.exe -B backend-api/scripts/verify_hybrid.py
.\.venv\Scripts\python.exe -B backend-api/scripts/diagnose_prediction_path.py
.\.venv\Scripts\python.exe -B backend-api/scripts/verify_http.py
.\.venv\Scripts\python.exe scripts/verify_mariadb_local.py
.\.venv\Scripts\python.exe scripts/verify_providers.py
.\.venv\Scripts\python.exe scripts/verify_media_local.py
.\.venv\Scripts\python.exe scripts/verify_deployment.py
node scripts/verify_ui.mjs
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_live_stack.ps1
$env:SURI_TEST_BROWSER='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
node scripts/verify_extension_popup.mjs
node scripts/verify_facebook_modal.mjs
node scripts/verify_installed_extension.mjs
node scripts/verify_admin_browser.mjs
```

The MariaDB/media scripts use this workstation's portable MariaDB and Windows speech/font
tools. Provider checks use configured keys and public synthetic queries; no secrets are
printed. UI checks use installed headless Chrome, real React components and the live API
test result. The installed-extension script uses an isolated Edge Chromium profile and a
synthetic supported-origin fixture; it does not test current third-party DOMs or accounts.
All isolated test data are synthetic and ignored by Git. Do not use participant records
as test fixtures. Run `npm.cmd run lint` and `npm.cmd run build` in the dashboard, and `npm.cmd run build`
in the extension after UI edits.

## Research and launch materials

- [Participant instructions and draft consent](docs/research/PARTICIPANT-GUIDE.md)
- [Separate questionnaires and response format](docs/research/QUESTIONNAIRES.md)
- [Pilot checklist, expert test form and traceability](docs/research/PILOT-AND-TRACEABILITY.md)
- [VPS, HTTPS, backup/restore and operations](docs/DEPLOYMENT.md)
- [Measured results and exact external release steps](docs/RELEASE-READINESS.md)
