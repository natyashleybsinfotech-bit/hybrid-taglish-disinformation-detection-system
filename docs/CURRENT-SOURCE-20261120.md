# Current source snapshot — 20 November 2026

Start here when reviewing the latest code. Earlier dated records describe earlier configurations and are not proof of current readiness.

## Current local pipeline

- Chrome extension version: **1.3.49**; backend: FastAPI; persistence: MariaDB; administrator dashboard: React.
- The selected local trial uses partially fine-tuned multilingual DistilBERT, seven linguistic features, saved scalers, and Logistic Regression. Profile: `suriph-finetune-6a35c6d4a2a0`; saved threshold: 0.85. Model weights and private runtime configuration are intentionally excluded from Git.
- `scripts/start-finetuned-trial.ps1` starts model mode with optional evidence assistance. `-RawModelOnly` explicitly disables evidence adjustment. No retraining occurs at startup.
- There are two successful screening labels: **Potentially Misleading** and **No Misleading Information Detected**. Missing, unrelated or unreadable evidence retains the real model prediction. Classifier/extraction failures remain technical errors; the API does not fabricate a prediction.
- Requested source lookup retrieves article bodies. Gemini is used as a separately validated evidence reader and may also provide audio transcription according to private configuration. It is not the active primary text classifier. Validated supporting/contradicting passages may adjust the displayed label under the configured evidence policy. Original model score and seven features remain separate from the final evidence-assisted result.
- `/ready` reports actual model identity plus `screening_policy.model_authoritative` and `screening_policy.evidence_assistance_enabled`.

## Video behavior

Direct video extraction is attempted first. Where a usable video URL is unavailable, the interface offers caption-only or caption-and-video processing. Playback capture records the selected video at normal speed for actual speech transcription. Unclear speech may fall back to a complete informative caption, identified in the checked-text details. Provider or infrastructure failures are not silently substituted with captions. See [video choices](VIDEO-CAPTION-CHOICE-20261120.md) and [processing changes](VIDEO-PROCESSING-20261120.md).

## Verification and remaining issues

- Latest selected backend regression run: **248 tests passed**, including API/media contracts, evidence decisions/validation, deployment configuration and model contracts. External provider responses were mocked in this regression run.
- Extension regression run: **47 tests passed**; product contract and normal extension build passed.
- Separate live checks returned both successful HTTP responses and all seven features, but the true Manila-capital statement and prior ASEAN caption still received the raw misleading label. Retrieved evidence was absent, unreadable or insufficient for a validated correction. These are unresolved false-positive examples, not successful accuracy demonstrations.
- Historical candidate accuracy (96.32% on 598 inherited-label records) is not measured real-world Facebook accuracy. Short-text training coverage is strongly imbalanced. See [the fine-tuned trial record](FINE-TUNED-LOCAL-TRIAL-20261120.md).
- Installed-extension tests on current Facebook posts and representative accuracy evaluation remain necessary. This snapshot is not a claim of survey, defense or deployment approval.

## Review entry points

- Primary routes and output assembly: `backend-api/src/app.py`
- Model identity and inference: `backend-api/src/model_runtime.py`, `backend-api/src/model_profiles.json`
- Retrieval and body extraction: `backend-api/src/retrieval.py`, `backend-api/src/article_reader.py`
- Evidence reading and decisions: `backend-api/src/gemini_evidence.py`, `backend-api/src/evidence_decision.py`
- Media/audio extraction: `backend-api/src/media_processing.py`, `backend-api/src/gemini_audio.py`
- Public result binding and UI: `chrome-extension/src/result_binding.js`, `chrome-extension/src/Popup.jsx`, `chrome-extension/src/content.js`
- Binary fallback policy regression tests: `backend-api/tests/test_verified_final_policy.py`

## Public checkout boundaries

API keys, passwords, `.env.local`, runtime databases, respondent records, datasets, model weights, backups, virtual environments, generated builds and dependencies are not included. Use the example configuration and obtain compatible model artifacts separately. A checkout cannot serve the selected model until its verified artifacts are installed.
