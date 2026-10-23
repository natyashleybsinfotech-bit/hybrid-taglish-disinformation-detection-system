# Start here — SuriPH evidence-only prototype

Run commands from `hybrid taglish-detector system`. Preserve `backend-api/.env.local`; it contains local settings and must not be committed.

## Start the backend

```powershell
.\scripts\start-mariadb.ps1
cd backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m src.manage migrate
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

At least one evidence provider must be configured for readiness. Set `SERPER_API_KEY` and/or `GOOGLE_FACT_CHECK_API_KEY` in the private `backend-api/.env.local` and keep the corresponding provider enabled.

Verify the active mode:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/analyze -Method Post -ContentType application/json -Body '{"text":"Basahin ang buong balita at source nito.","retrieve_sources":true}'
```

Health must report `decision_engine.mode` as `evidence_only`, `classifier_loaded` as `false`, and model status as `disabled`.

## Build and load the Chrome extension

```powershell
cd chrome-extension
npm.cmd ci
npm.cmd run build
```

Open `chrome://extensions`, enable Developer mode, reload the existing SuriPH extension or choose **Load unpacked**, and select `chrome-extension/dist`. Reload the Facebook tab after every extension rebuild. Version 1.4.0 displays evidence assessment, published fact-checks, related context, the exact assessed text, and no model label or score.

## Run the admin dashboard

```powershell
cd admin-dashboard
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. The dashboard shows evidence-provider health and clearly reports that the classifier is disabled. Historical research assets remain archived and do not control runtime decisions.

## Run checks

```powershell
.\.venv-candidate-20261023-isolated\Scripts\python.exe -m unittest discover -s backend-api\tests -p "test_*.py"
node chrome-extension\tests\product-contract.mjs
npm.cmd --prefix chrome-extension run build
npm.cmd --prefix admin-dashboard run build
```

See [docs/EVIDENCE-ONLY-MODE.md](docs/EVIDENCE-ONLY-MODE.md) for decision rules and limitations, and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment steps.
