# SuriPH Sprint 1 Working Prototype

This build implements user-triggered screening for manual or page-extracted text, uploaded images, and uploaded videos. Results come from a deterministic mock classifier and must not be presented as trained-model or fact-checking verdicts.

## Components

- `backend-api`: FastAPI screening API, EasyOCR, packaged FFmpeg, Whisper, optional Serper retrieval, and MySQL/MariaDB persistence.
- `chrome-extension`: popup workflow for manual text, selected text, supported post text (including accessible open shadow roots), image uploads, and video uploads.
- `admin-dashboard`: authenticated real system status, candidate-sample records, and audit records. Retraining and model-performance pages are intentionally outside Sprint 1.

## Configuration

Set server secrets and service configuration as environment variables. Use `backend-api/.env.example` as the variable checklist; it contains placeholders only. At minimum, configure `SURI_DB_USER`, `SURI_ADMIN_USERNAME`, `SURI_ADMIN_PASSWORD`, and a long random `SURI_SESSION_SECRET`. `SERPER_API_KEY` is optional; retrieval reports `unavailable_not_configured` without it.

The API applies versioned MySQL/MariaDB migrations on startup. The configured database itself must already exist. Media model weights are downloaded on first use into `backend-api/data/runtime-models` by default and are ignored by Git.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\backend-api\requirements.txt
Set-Location .\backend-api
..\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location .\admin-dashboard
npm run dev
```

Build and load the browser extension:

```powershell
Set-Location .\chrome-extension
npm run build
```

Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select `chrome-extension/dist`. The extension never collects or classifies page content until the user clicks an extraction or analysis control.

## Verification

```powershell
Set-Location .\backend-api
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v

Set-Location ..\chrome-extension
npm run build

Set-Location ..\admin-dashboard
npm run lint
npm run build
```
