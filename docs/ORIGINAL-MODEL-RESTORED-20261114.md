# Original hybrid restored — 14 November 2026

At the user's explicit request, the local API was returned to the original
4,000-row-dataset hybrid, run `20261011T235112Z`. The candidate API process was
stopped before starting the original model on port 8000.

- Active classifier: `models/TRAINING RESULTS/models/model_4.joblib`.
- SHA-256: `72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`.
- Original threshold: `0.65`; CPU; model switching disabled.
- `/ready` confirmed this exact classifier, profile, hash and threshold, with MariaDB available.
- Four raw-text requests to the live `/analyze` endpoint, with source retrieval off,
  matched saved model_4 labels and probabilities within absolute tolerance `1e-5`.
- Evidence record: `tmp/original-model-restored-20261114.json`.
- Start again with `scripts/start-original-model.ps1` after starting MariaDB.

No training, model-weight modification, threshold tuning, evidence-logic change,
extension rebuild, public deployment or Git push was performed for this restoration.
Other candidate files remain on disk but are not selected by this startup script.

This is a restoration and integration check, not a new accuracy evaluation. Known
false positives in this original classifier remain. Source/evidence decisions are
unchanged and can still differ from the raw classifier output when retrieval is enabled.

The existing `verify_hybrid.py --limit 4` could load the original model, but its
legacy CSV reader tried to convert the string `Non-Misleading` directly to an
integer and failed. It was not reported as passing or modified here. The separate
live API check joined references by exact text SHA-256 and compared numeric model
predictions, avoiding any reinterpretation of source truth labels.
