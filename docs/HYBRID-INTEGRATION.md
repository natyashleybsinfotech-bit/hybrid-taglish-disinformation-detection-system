# SuriPH hybrid model integration

> Archived research and reproducibility reference. The active product no longer loads this classifier; see [EVIDENCE-ONLY-MODE.md](EVIDENCE-ONLY-MODE.md).

Verified locally, with cleanup checks completed October 20, 2026. The actual frozen hybrid pipeline loads and
produces verified predictions on CPU. This does not establish that its predictions
are always factually correct, nor does it complete production hosting or Chrome UI QA.

## Active model and verification evidence

- Only classifier: `models/model_4.joblib`.
- Training run: `20261011T235112Z`.
- Classifier SHA-256: `72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`.
- Saved threshold: **0.65**, confirmed in the classifier bundle, its embedded
  selection, and `records/selected_configurations.csv`. The selection file's hash
  matches `run_manifest.json`.
- Mapping: Non-Misleading = 0; Misleading = 1. `classes_` determines the probability
  column; `predict()` is never used on the saved classifier.

The complete raw-text pipeline processed all **598** rows in `records/test.csv`,
joined to `records/test_predictions.csv` by SHA-256 of the original UTF-8 text.
All input/reference IDs matched exactly. No cached contextual embeddings were read.

| Integration comparison | Result |
| --- | --- |
| Label mismatches at threshold 0.65 | **0 / 598** |
| Probability mismatches | **0 / 598** |
| Maximum absolute probability difference | **3.1492805406818647e-6** |
| Mean absolute probability difference | **2.5496172914611914e-7** |
| Texts requiring multiple chunks | **291** |
| Actual inference device | **CPU** |
| Full comparison duration on this workstation | **700.8 seconds** |

Tolerance was declared before the comparison:
`abs(actual - reference) <= 1e-5 + 1e-5 * abs(reference)`.
Small numeric differences are expected between the saved CUDA run and CPU execution
and between padded batch groupings. No thresholds, parameters or preprocessing were
adjusted using these records. Detailed aggregate evidence, versions and reference-file
hashes are in [HYBRID-VERIFICATION.json](HYBRID-VERIFICATION.json).

## Exact inference contract

1. Collapse whitespace with `re.sub(r'\s+', ' ', text).strip()`. Preserve case,
   punctuation, language and all remaining text.
2. Load the supplied multilingual DistilBERT tokenizer/encoder entirely from local
   `models/contextual_encoder/`. Freeze parameters and use eval/inference mode.
3. Tokenize without special tokens and without truncation. Split every text into
   non-overlapping chunks of at most **510 content tokens**, then add CLS and SEP.
4. Exclude padding and only the added CLS/SEP positions from pooling. Content UNK
   tokens remain included. Sum float32 hidden states for each chunk, accumulate in
   float64 across all chunks, divide by total content-token count, and cast to
   float32. The saved chunk batch size is **8**.
5. Restore the exact serialized Tagalog tokenizer into `spacy.blank('tl')` with
   `exclude=['vocab']`. Use only this tokenizer, not POS/NER or another NLP model.
6. Compute the seven float32 linguistic features below with the saved lexicons.
   Lingua uses only TAGALOG and ENGLISH with minimum relative distance **0.2**;
   ambiguous words contribute to neither language count.
7. Apply the saved 768-dimensional `context_scaler` and seven-dimensional
   `ling_scaler`. Concatenate **scaled contextual then scaled linguistic** features,
   yielding 775 columns. Neither scaler is fitted or updated.
8. Apply the saved Logistic Regression's `predict_proba`. Read the class-1 column
   using `classes_` and select Misleading when its score is **>= 0.65**.

Feature order and denominators:

| Feature | Exact definition |
| --- | --- |
| code_switching_ratio | min(Tagalog count, English count) / (Tagalog + English count) |
| filipino_particle_frequency | matching alphabetic, casefolded particle tokens / all non-space tokens |
| punctuation_intensity | count of `!` and `?` / total characters |
| capitalization_ratio | uppercase alphabetic characters / all alphabetic characters |
| repeated_character_ratio | characters in case-sensitive `(.)\1{2,}` runs / total characters |
| emotional_language_frequency | matching alphabetic, casefolded emotion tokens / all non-space tokens |
| urgency_cue_frequency | matching alphabetic, casefolded urgency tokens / all non-space tokens |

Zero denominators produce zero features. The three lexicons are loaded from the
saved feature configuration and checked against the hash-verified classifier bundle.
The old heuristic feature extractor and old CLS/truncation embedding module remain
historical files, but the serving app does not import or call them.

## Artifact structure and failure behavior

The default artifact root is `backend-api/models/TRAINING RESULTS/`:

```text
run_manifest.json
models/
  model_4.joblib
  feature_config.json
  tagalog_tokenizer
  contextual_encoder/
    config.json
    model.safetensors
    special_tokens_map.json
    tokenizer.json
    tokenizer_config.json
    vocab.txt
```

The notebook and `records/` are needed only for reference inspection/verification,
not serving. Compose mounts only the above inference components, read-only. It does
not mount alternative classifiers or raw records into the API container.

`SURI_MODEL_ARTIFACT_DIR` can relocate this complete artifact root. It does not
select a classifier. The old `SURI_MODEL_BUNDLE` variable is retired and ignored.
`hybrid_model.pkl`, legacy schema-1 bundles and model_1/2/3 cannot be substituted.
Database model registry entries no longer select the running model. Model registration,
activation and training queue routes return HTTP 410; the worker and historical
training CLI are disabled. No retraining was performed.

Startup verifies required files, the classifier's manifest hash and fixed run/hash,
the Tagalog tokenizer hash, embedded configuration, classifier/scaler dimensions,
class mapping, dependency versions and encoder settings. The supplied encoder files
are additionally pinned in `src/hybrid_artifacts.json`. These encoder hashes are a
local inventory of the supplied files, not hashes claimed to exist in the original
training manifest. Incomplete or mismatched encoder weight loading is rejected.

Resources load once at startup. Health checks do not reload resources or download
weights. Failed startup leaves the API available for diagnostics, `/ready` returns
503 and predictions return 503 without a label/score. An inference exception also
clears readiness and requires resolving the issue and restarting the process.
An invalid production database/configuration may still prevent server startup.

## Start the backend

Use Python 3.11–3.13; this workstation was verified using Python 3.13. Install the
model's pinned versions with the rest of the API requirements. Preserve existing
private database settings rather than replacing them with example credentials.

From the project root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend-api\requirements.txt
.\scripts\start-mariadb.ps1
Set-Location backend-api
..\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1
```

For a fresh checkout, create `.venv` first and configure `backend-api/.env` using
`.env.example`. An empty `SURI_DB_HOST` uses SQLite locally; MariaDB is required by
production configuration. `SURI_LOAD_ENV_FILES=false` disables local dotenv files for
isolated tests. Real process environment values take precedence.

Optional settings: `SURI_MODEL_DEVICE=auto` (CUDA if available, otherwise CPU),
`cpu`, or `cuda` (explicitly unavailable CUDA fails); `SURI_MODEL_CPU_THREADS=4`.
`requirements-model.txt` pins the recorded major inference package versions. CUDA
and CPU torch builds may have different build suffixes; their base version must match.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/analyze -Method Post -ContentType application/json -Body '{"text":"Basahin muna natin ang buong balita."}'
```

`/health` and `/ready` expose the active classifier, run ID, SHA-256, actual device,
threshold, readiness, package versions and load/inference error when present.

## Response and extension behavior

`internal_label` retains the canonical `Misleading` and `Non-Misleading` strings;
`public_label` uses the cautious labels `Potentially Misleading` and
`No Misleading Information Detected`. `model_score` and `misleading_probability` are the
unrounded class-1/Misleading score, with `predicted_class`, `decision_threshold`,
`training_run_id`, `artifact_sha256`, `device`, chunk/token counts and the actual
seven measured features. The legacy `confidence` field is retained for old clients
as the selected class's probability. `displayed_class_score` explicitly returns the
score for the displayed class; the UI uses that field and keeps P(Misleading) in an
expandable technical section. Neither is described as calibrated certainty. A
Misleading score below 0.65 predicts Non-Misleading, even when the selected-class
score is below 0.5.

The post-context panel contains only metadata and acquisition details obtained from the
selected Facebook post, or identifies manual input as manually entered. It does not
invent claim-by-claim explanations. Public lookup uses Serper only and returns related
reading from approved publishers. Google Fact Check is available only through the
administrator evidence-review endpoint. Neither provider generates or changes classifier
labels or scores, and a provider failure does not change the prediction. `POST
/related-sources` supports a later source lookup and never invokes classification.
Approved-domain results are additionally filtered and ranked by overlap between informative
terms in the supplied post and each result's title and snippet. Normal post-sized queries
also require at least two informative headline matches, so generic snippet overlap is not
enough. A credible domain by itself
does not qualify a link; the endpoint returns `no_results` when no candidate passes this
relevance gate. If the first result set has no qualifying candidate, one focused retry uses
concise event terms and approved Philippine publisher domains; the same relevance gate is
applied to the retry.
Extension version 1.3.1 enables its visible Serper setting once on install/update because
public Facebook screening is expected to return related sources. The user can turn it off
before analysis; the API itself still defaults to no external lookup when omitted.

Empty/whitespace inputs return 422. Text has an explicit **1,000,000-character API
limit**; oversize input is rejected rather than silently clipped. The extension no
longer clips post text to 20,000 characters or reuses a cached post prediction on a
new screening action. It no longer silently substitutes caption-only screening
when selected media fails. The popup no longer saves input/results or research
receipts locally; only page-tools, lookup and interface-language preferences persist.
The active manifest and media allowlist are Facebook-only. Recognized Facebook caption
containers or exact user selections are used; the content script fails closed instead
of classifying a whole feed/article container. Fixed English/Tagalog supporting text can
be switched without another request, while both classification labels remain English.
Survey and
participant collection are separate from the extension and admin dashboard. The same
lookup preference controls the in-page S button. Clicking Analyze performs a new request.
An optional candidate submission requires an explicit consent checkbox and stores only
the analyzed text/page metadata in the private review queue; ordinary screening is not stored.

From the project root in another terminal:

```powershell
Set-Location chrome-extension
npm.cmd ci
npm.cmd run build
```

Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and
select `chrome-extension/dist`. Reload an already installed extension and refresh
the target page after rebuilding. The development API defaults to port 8000.
For deployment set `VITE_API_BASE_URL=https://YOUR_API_DOMAIN` in the ignored
`chrome-extension/.env.production` before building; Vite adds that origin to the
manifest host permissions. No model files, datasets or secrets belong in `public/`,
`dist/` or `VITE_` settings.

## Repeat the checks

From `backend-api/`:

```powershell
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
..\.venv\Scripts\python.exe -B scripts/verify_hybrid.py
..\.venv\Scripts\python.exe -B scripts/verify_http.py
```

The first command covers failure paths, threshold boundary, class-column order,
weighted full-text chunking, artifact rejection, retrieval independence and API
compatibility using isolated test fixtures. The second runs actual inference on all
598 saved raw test inputs and writes `tmp/hybrid-verification.json`. The third starts
a temporary real API with an isolated SQLite database and uses Node.js to exercise
the extension's actual client and background handler against it. It also tests
empty input, fresh text, persistence and a 1,611-content-token input across four chunks.
No live development/production records are created by this HTTP harness.

Recorded results: **72 backend tests passed**, the live HTTP and extension transport
checks passed, both frontend builds passed, and dashboard lint and dependency checks
passed. The HTTP aggregate report is
[HYBRID-HTTP-VERIFICATION.json](HYBRID-HTTP-VERIFICATION.json).

Raw datasets and retired model binaries previously tracked by Git have been removed
from the index, preserving local data files. Ignore rules exclude the supplied export,
datasets and secrets from future commits. This does not erase any historical copies
already present in Git history.

## Limits and remaining release checks

- Actual English and Tagalog component rendering was checked in headless Chrome,
  including a 320-pixel result viewport. Installed-extension host permissions, real Facebook extraction and
  browser video capture still require hands-on QA. See UI-VERIFICATION.json.
- Actual CUDA inference was not exercised on this CPU workstation. Run the same
  comparison on the intended deployment hardware and retain its report.
- Real OCR and Whisper passed synthetic image/video smoke checks; these do not
  establish accuracy across participant media. See MEDIA-VERIFICATION.json.
- Docker image build, TLS, production traffic/load and the Docker backup wrapper still
  need validation on the chosen server. Native isolated logical restoration passed. Keep one API worker/replica for this setup.
- Test agreement reproduces the saved classifier, including its possible errors; it
  is not independent evidence of factual accuracy or probability calibration.

## Files changed for this integration

- Backend: `src/hybrid_pipeline.py`, `src/hybrid_artifacts.json`, `src/model_runtime.py`,
  `src/app.py`, `src/fact_check.py`, `src/deployment_check.py`,
  `config.py`, `scripts/log_current_model.py`, `requirements.txt`,
  `requirements-model.txt`, `Dockerfile`, `.dockerignore`, `.env.example`.
- Checks: `scripts/verify_hybrid.py`, `scripts/verify_http.py`, `tests/test_hybrid_contract.py`,
  `tests/test_api.py`, `tests/test_services.py`, `chrome-extension/tests/connection.mjs`.
- UI: `chrome-extension/src/Popup.jsx`, `src/content.js`, `src/background.js`, rebuilt
  extension `dist/`, and `admin-dashboard/src/pages/Governance.jsx`.
- Deployment/docs: `.gitignore`, `.env.production.example`, `docker-compose.yml`,
  `README.md`, `backend-api/models/README.md`, `docs/DEPLOYMENT.md`, this guide and the
  aggregate verification reports. Existing unrelated working-tree edits were retained.
- Historical training/worker and approximate extraction modules are preserved in
  `archive/legacy-backend/`, outside the runtime and Docker context. See the
  [project structure](PROJECT-STRUCTURE.md) and [documentation index](README.md).
