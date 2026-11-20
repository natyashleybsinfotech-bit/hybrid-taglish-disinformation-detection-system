# SuriPH

**Latest source snapshot (20 November 2026):** Read [the current implementation, test scope and unresolved issues](docs/CURRENT-SOURCE-20261120.md) first. It supersedes older runtime-selection descriptions below. The code is available for review; private configuration, data and model weights are excluded.

Start with the [local setup and demo guide](START_HERE.md). The
[October 29 readiness report](docs/CURRENT-READINESS-20261029.md) and older
[release evidence](docs/RELEASE-READINESS.md) are historical records; check their
dates and superseding notes before relying on their versions or test counts.
Use the [documentation index](docs/README.md) to find the paper, training references,
setup, research materials and [project layout](docs/PROJECT-STRUCTURE.md).

SuriPH is a Taglish screening prototype composed of a FastAPI service, a Facebook-only Google Chrome extension, and an administrator dashboard. It returns exactly two public labels: **Potentially Misleading** or **No Misleading Information Detected**. The selected classifier screens text and extracted caption/image/video content; when requested, readable publisher evidence can adjust a prediction only under the documented corroboration rules. A direct speech/frame mismatch now requires a person to review the extracted video text before classification. Neither a model score nor a source link proves a claim, and results can be wrong. Search previews and inaccessible pages are not evidence; the model score is shown only in expandable analysis details and is not the probability that a claim is false. Insufficient evidence must be treated as unverified, not as a factual verdict. See [the evidence decision process](docs/EVIDENCE-DECISION-20261029.md).

Local development defaults to `SURI_SCREENING_MODE=model`; set `SURI_SCREENING_MODE=evidence_only` only to explicitly disable classifier inference. Production requires model mode. OCR and speech recognition remain active in either mode. A local-trial model profile is not deployment-approved: its held-out scores measure agreement with inherited dataset labels, not independently verified real-world Facebook accuracy.

## Repository layout

- `backend-api`: inference API, MariaDB persistence, OCR/video processing, maintenance scripts and tests.
- `chrome-extension`: user-triggered page, text, image, and video screening.
- `admin-dashboard`: role-controlled system health/performance views and researcher-only dataset governance.
- `docker-compose.yml`: production-shaped API and dashboard deployment.

Screening stores no input or prediction by default. A separate checkbox and button let a
user explicitly consent to store the analyzed text and page metadata in the private candidate
review queue; it never enters a dataset automatically. Survey collection is separate from
the extension and administrator dashboard. Existing curated candidate workflows remain available. The system suggests one of the paper's eight topic
domains and retains the model result as a proposed label. A researcher must confirm a
matching evidence URL before approval. Candidate Samples reports counts per topic and
exports the filtered review queue as UTF-8 CSV or Excel. Datasets and Models shows
approved dataset versions, historical training records and the pinned runtime model.

Uploaded image/video bytes, extracted frames, and temporary media paths are never
written to the dataset or MariaDB; video working files are removed when processing
finishes. Historical survey materials and any existing private records remain preserved
outside the product UI for the research team to manage under its approved process.

## Active hybrid model

The prepared workstation selects the local-trial profile `suriph-finetune-6a35c6d4a2a0`: partially fine-tuned multilingual DistilBERT, seven linguistic measurements, saved scalers and Logistic Regression. The saved decision threshold is 0.85. The primary classifier and training artifacts were not changed by the local evidence/audio migration.

The current evidence reader is a separate local multilingual NLI fallback; speech recognition uses local faster-whisper. See [current source](docs/CURRENT-SOURCE-20261120.md) and [migration verification](docs/GEMINI-REMOVAL-20261120.md). Historical 96.32% held-out accuracy concerns 598 inherited-label records, not real-world Facebook performance. Known short/neutral-text false positives remain unresolved; the profile is not approved for production.

Model artifacts are local-only. A checkout needs the compatible, hash-verified classifier/encoder/tokenizer files plus prepared local evidence and media models. Runtime never silently substitutes another primary classifier when the selected profile cannot load.

## Related-source context

The Facebook extension enables related-source search by default. Direct API callers must explicitly set `retrieve_sources`; API requests do not send text to a search provider unless requested. Serper provides up to 20 candidates, then the service fetches and checks up to 5–10 readable article bodies (configured maximum is clamped to 5–10) against the claim's material details. When source lookup is enabled, HTTPS links found in the Facebook post are prioritized within the same bounded article-fetch limit, but only on curated trusted-publisher domains. Their readable article body must corroborate a publisher headline that directly states the complete claim before that headline can contribute to evidence. Queries use plain claim terms; social domains are filtered locally instead of with search operators that may be rejected by some Serper account tiers. Results are restricted to a curated set of 60 local and international news, wire-service, and fact-checking publisher domains (including GMA, ABS-CBN, Inquirer, Rappler, VERA Files, Philstar, Manila Bulletin, Manila Standard, BusinessMirror, BusinessWorld, SunStar, Reuters, AP, BBC, CNN, NPR, The Guardian, Al Jazeera, &ASIAN, and others). Matching Philippine news and fact-checking publishers are preferred; international approved publishers are used if no Philippine match is found. Results are kept diverse by publisher; unsupported, social, and unrelated pages are excluded. In retrieval, “Department of Justice” and “DOJ” count as one relevance anchor, so a generic DOJ page cannot qualify merely because its name is repeated in a title and preview. If an approved publisher blocks article reading, its link and search preview may still be shown, clearly labeled as unverified and never used as evidence. This is a vetted publisher list, not a claim that every website is reliable or that every news domain is covered; not every Facebook post is necessarily reported by these publishers. Search cleanup ignores common photo/news bylines and post-date labels while retaining and matching years stated in the claim; English/Filipino forms such as `isapribado` and `maisapribado` are normalized for retrieval. An evidence override now requires two independent curated publishers with readable full articles directly supporting the complete claim and its material details, and no readable trusted article directly contradicting it. Contradictions can override a model warning only when two independent trusted publishers directly support the contradiction and no trusted source supports the claim. Multiple URLs from the same publisher, near-identical syndicated article bodies, untrusted domains, headlines alone, search snippets, and merely related articles do not count as corroboration. When sources are insufficient, conflicting, or inaccessible, the final label stays one of the two model screening labels and is explicitly unverified, not a factual verdict. Google Fact Check remains an administrator review tool.

## Local development

For a fresh checkout configure private local settings from the example. On this prepared workstation, preserve the existing `.env.local`.

On the prepared Windows workstation, the portable MariaDB instance is bound only to
`127.0.0.1:3306`. Its local, ignored configuration is in
`backend-api/.env.local`; values there override `backend-api/.env` for local use.
Start or stop it from the repository root with:

```powershell
.\scripts\start-mariadb.ps1
.\scripts\stop-mariadb.ps1
```

Read development credentials privately from `.env.local`. Production setup generates
new random credentials; never reuse a development password.

Start the candidate API from the repository root:

```powershell
python -m venv .venv-candidate-20261023-isolated
.\.venv-candidate-20261023-isolated\Scripts\python.exe -m pip install -r .\backend-api\requirements-candidate.txt
Set-Location .\backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Local development loads the selected classifier at startup and fails readiness if it cannot load. The Facebook caption remains included alongside image OCR or analyzed video transcript/frame text when the caption is complete. If a Facebook caption is collapsed, a media check analyzes only the extracted media and says the caption was omitted. Videos with a detected speech/frame mismatch are sent to a review step and are not classified until confirmed. Source search is enabled by the extension when selected by the user; direct API callers must explicitly set `retrieve_sources`. A local-trial profile must not be presented as deployment-approved or guaranteed accurate.

In a second terminal:

```powershell
Set-Location .\admin-dashboard
npm.cmd ci
npm.cmd run dev
```

Open the admin console at `http://127.0.0.1:5173/` and sign in with your configured local administrator account.

The dataset review workflows remain available, but this deployment cannot queue
training or switch its active classifier. Historical registry records do not control
inference. Do not start the old training worker.

Build and load the extension:

```powershell
Set-Location .\chrome-extension
npm.cmd ci
npm.cmd run build
```

Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select `chrome-extension/dist`.
After every rebuild, click **Reload** on SuriPH in `chrome://extensions` and refresh every
open Facebook tab so the version 1.3.14 content script replaces the old one. Version 1.3.14
enables related-source lookup once on upgrade; the visible checkbox can turn it off before
analysis. Up to 500 characters are sent to Serper only when this setting is enabled.
Video audio processing accepts clips up to 3 minutes and 50 MiB.

## Production deployment

Follow the full [deployment runbook](docs/DEPLOYMENT.md) for the VPS setup,
model acceptance, commands, extension release, backup/restore and rollback steps.

1. Preserve the verified model_4 export and complete inference component directory.
2. Choose a Docker-capable Linux VPS and API/dashboard domains.
3. Run `scripts/prepare_deployment.py` with those domains to generate private settings and random credentials.
4. Build the containers and run `python -m src.deployment_check --media` inside the API container.
5. Start Compose with `--profile https` to enable Caddy HTTPS, and verify `/ready` and real text/image/video screening.
6. Build the extension with the public HTTPS API URL; test admin/viewer permissions and database recovery before release.

Production rejects placeholder secrets, incompatible or changed model components, localhost CORS origins,
and wildcard trusted hosts. It runs real hybrid inference during startup. Model
failures remain visible through health/readiness; production database/bootstrap
errors prevent startup. Training and model switching are disabled.

## Release verification

```powershell
Set-Location .\backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v

Set-Location ..\admin-dashboard
npm.cmd ci
npm.cmd run lint
npm.cmd run build

Set-Location ..\chrome-extension
npm.cmd ci
npm.cmd run build

Set-Location ..
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production build
```

After the approved model is installed and the stack is live, record the response-time evidence required by the paper:

```powershell
python .\backend-api\scripts\benchmark.py --url https://api.example.com/analyze --requests 30
```

The paper-to-code review is recorded in [`docs/IMPLEMENTATION-TRACEABILITY.md`](docs/IMPLEMENTATION-TRACEABILITY.md).

Before release, also run representative Filipino, English, and Taglish samples through text, image, and video flows; confirm model version/hash in the dashboard; test expired administrator and viewer sessions; and back up the `suriph-database` MariaDB volume.

## Operational notes

- Production Compose uses MariaDB 11.4.13. Local development and tests may leave `SURI_DB_HOST` empty to use SQLite.
- The classifier loads its supplied encoder/tokenizers locally and never downloads replacement weights. OCR and Whisper may download/cache weights unless pre-populated in `backend-api/data/runtime-models`.
- Facebook in-page video analysis shows a result after speech and on-screen-text extraction when the two agree; a detected mismatch opens a review step before classification. All extraction remains fallible, and a matching topic does not prove a word-perfect transcript. See [video extraction validation](docs/VIDEO-EXTRACTION-VALIDATION-20261103.md) for ASR benchmarks and remaining limitations.
- Model scores are predictions, not calibrated certainty or factual verification. Retrieved links require independent review.
