# Fine tuned DistilBERT local trial

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

> Superseded runtime policy: the later 20 November update enables optional validated evidence assistance by default. Use `-RawModelOnly` for the model-authoritative diagnostic path. See [current source](CURRENT-SOURCE-20261120.md). The historical results and limitations below remain unchanged.

The selected local classifier is `suriph-finetune-6a35c6d4a2a0`, a partially fine-tuned multilingual DistilBERT encoder plus seven linguistic measurements and Logistic Regression. Only transformer layers 4 and 5 changed from the archived base encoder. Inference freezes the selected encoder. The saved threshold is 0.85; no threshold was selected from the historical test results.

## Verification

- Downloaded model archive CRC passed.
- Candidate predictions match all 598 saved historical test labels when replayed with the local CPU pipeline.
- Maximum observed CPU/GPU probability difference was 0.0008989513 (about 0.09 percentage point). The strict 0.0002 numerical tolerance did not pass. Classification parity and the measured difference support this local trial; probabilities are not represented as bit-identical or calibrated confidence.
- Training used PyTorch 2.14.1 CUDA. Verified local inference uses PyTorch 2.11.0 CPU and the existing pinned inference dependencies. Both versions remain recorded in the candidate verification file.
- API, model-contract and deployment tests passed: 79 tests, including candidate-model authority and no LLM fallback.
- The profile is rejected for production. This record does not certify survey, deployment, or real-world factual accuracy.

## Decision path

`SURI_SCREENING_MODE=model` invokes the pinned local DistilBERT hybrid. `SURI_MODEL_AUTHORITATIVE=true` retains that classifier's label when source retrieval is requested. Retrieved links are references; they are not described as verified evidence for the label. The primary Gemini classifier and semantic evidence override are not invoked in this local screening flow. Existing speech-transcription provider settings were not changed and may still use an external service.

The 96.32% accuracy and 1.33% observed false-positive rate concern the 598 previously inspected inherited-label records. They are not a measured real-world Facebook accuracy rate or a guarantee of correct outputs on new posts.

## Live diagnostic limitation

Actual `/analyze` requests using the candidate still marked the hydration regression sentence and both previous ASEAN-lane and House news captions as Potentially Misleading, with extreme scores. These requests used the genuine candidate and returned all seven linguistic indicators. The short-caption problem is not resolved by the historical improvement. The trial is available for exploratory Facebook testing, not approved for participant survey or defense readiness.

The original 4,000-record collection contains 26 texts under 50 whitespace-delimited words: 17 training, 1 validation, and 8 test records. All 26 have inherited label 1 (Misleading), with zero Non-Misleading examples in that length range. The held-out short-text subset cannot measure false positives. This is a strong distributional warning, not a verified causal explanation or authorization to relabel records.

## Reproducible comparison

The accompanying comparison notebook retrains TF-IDF + LR, frozen DistilBERT + LR, and linguistic + LR using the original training/validation partitions and selection grid. It compares them with the fixed candidate outputs from the preceding trial. Cached original contextual features are indexed by record hashes and reproduce the original baseline scores. No fresh fine-tuning is performed by that notebook.

This is a historical configuration comparison, not a controlled feature ablation: encoder training and selection budgets differ. In the checked run, TF-IDF accuracy is 96.66%, while candidate accuracy is 96.32%. Candidate false positives are 4 versus 7 for TF-IDF. McNemar comparisons include Holm adjustment; the TF-IDF/candidate difference is not statistically significant in this historical sample.

## Start and recover

Start MariaDB using `scripts/start-mariadb.ps1`, then use `scripts/start-finetuned-trial.ps1` or the updated `scripts/start-survey-local.ps1`. Refresh Facebook to discard any result cached in an existing page.

Pre-change source files and the private environment file are backed up under `.run/finetuned-trial-backup-20261120/`. Original model artifacts remain unchanged. The candidate artifact, tensor-change audit, hashes and runtime compatibility record are under `backend-api/models/local-trials/suriph-finetune-6a35c6d4a2a0/`.
