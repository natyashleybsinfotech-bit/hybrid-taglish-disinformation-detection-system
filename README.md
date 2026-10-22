# SuriPH

Start with [START_HERE.md](START_HERE.md) and the [release evidence](docs/RELEASE-READINESS.md).
Use the [documentation index](docs/README.md) to find the paper, training references,
setup, research materials and [project layout](docs/PROJECT-STRUCTURE.md).

SuriPH is a deployable Taglish content-screening system composed of a FastAPI service, a Facebook-only Google Chrome extension, and an administrator dashboard. It screens manual or user-selected Facebook text and text extracted from images or videos, reports model predictions and scores, and can attach related reporting from approved publishers. Public screening uses Serper for related sources, then requires multiple informative terms from the supplied post to match each result title or snippet. Google Fact Check Tools remains an administrator evidence-review tool.

The classifier is loaded from a versioned model bundle. The API never falls back to random, hash-based, or mock verdicts. If the bundle is missing or incompatible, screening returns an error and the readiness endpoint fails.

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

The only active classifier is `backend-api/models/TRAINING RESULTS/models/model_4.joblib`
from training run `20261011T235112Z`, using frozen multilingual DistilBERT, the seven
saved linguistic features and Logistic Regression with threshold **0.65**.
The exact raw-text pipeline reproduced all **598** reference test labels and all
probabilities within the declared tolerance (maximum difference **3.15e-6**).
This is serving parity with the saved Colab output, not 100% classification accuracy.
Against the saved ground truth, model_4 was correct on **560/598 (93.65%)** with
Macro-F1 **0.9364**.

Read [the integration guide](docs/HYBRID-INTEGRATION.md) for the artifact layout,
exact preprocessing, dependencies, API fields, verification evidence and limitations.
The old `hybrid_model.pkl`/schema-1 loader is retired. Renaming another model does
not make it compatible. Dataset/model review records remain in the restricted dashboard;
the incompatible historical retraining worker, model registration and runtime switching
remain disabled so they cannot replace model_4.

`/health` and `/ready` report the classifier identity, SHA-256, actual CPU/CUDA device,
threshold and readiness. A load/inference failure returns 503 for prediction and
false readiness. No alternative classifier or fabricated prediction is used.

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

Start the API from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend-api\requirements.txt
Set-Location .\backend-api
..\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location .\admin-dashboard
npm.cmd ci
npm.cmd run dev
```

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
open Facebook tab so the version 1.3.1 content script replaces the old one. Version 1.3.1
enables related-source lookup once on upgrade; the visible checkbox can turn it off before
analysis. Up to 500 characters are sent to Serper only when this setting is enabled.

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
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v

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
- Model scores are predictions, not calibrated certainty or factual verification. Retrieved links require independent review.
