# Preserved historical material

`legacy-backend/` contains the previous training, approximate preprocessing and
standalone classifier experiment. These are research references, not deployment
entry points. They were moved with byte-for-byte SHA-256 checks; see
[`docs/CLEANUP-MOVES.json`](../docs/CLEANUP-MOVES.json).

Executable trainer/worker/loader examples use `.py.txt` so they cannot accidentally
be launched as Python modules or discovered as tests. Historical imports, absolute
paths and descriptions inside these preserved files are intentionally unchanged.
Do not use them to generate deployed predictions or retrain the selected model.

The historical `feature_extractor.py` remains executable only for its existing
regression tests. No backend runtime module imports it. Actual model features are
computed exclusively by `backend-api/src/hybrid_pipeline.py`.

This directory is outside the backend Docker build context. No model binaries,
datasets, secrets or participant records are archived here. The supplied training
export remains intact in the ignored `backend-api/models/TRAINING RESULTS/`.
