# Gemini removal and local-model migration — 20 November 2026

Applied to the actual project. Extension **1.3.50** is built; restart the installed
unpacked extension and refresh Facebook to use it. This report records migration
verification, not survey, defense or public-deployment approval.

## Why the implementation changed

Gemini was explored for primary classification, evidence reading and audio
transcription during development. The current runtime retires the three provider
modules and uses the actual DistilBERT-LR classifier, a local multilingual NLI
fallback and local faster-whisper. This makes inference reproducible from pinned
local model files without remote inference credentials or API quotas. Old
commits and dated development records remain intact. No Git history was
rewritten, and no force-push is part of the migration.

Public source retrieval still needs Serper and readable publisher websites when
requested. A one-time public model download is an explicit setup operation;
model inference during a user request does not download weights or call Gemini.

## Preserved behavior

- Primary profile `suriph-finetune-6a35c6d4a2a0`, saved threshold **0.85**;
  architecture and seven features unchanged. Classifier, encoder, archived
  dataset, partitions and original training-notebook SHA-256 checks are unchanged.
- Two successful labels, with the actual original model prediction retained
  when evidence is missing, insufficient, conflicting or unavailable. No
  invented third label or technical-error substitute prediction was added.
- One evidence path: literal/material assertions, then local NLI fallback.
  Only actual readable article passages can be cited. Material person, amount,
  quantity, date and location checks constrain decisions. Explicit untitled
  multiword names also receive a preservation check. Existing publisher,
  independence, primary-authority and local-trial policy rules remain in effect.
- Both direct-download and browser-captured video bytes use the same local
  transcription function. The caption-only/caption-and-video choice and complete
  normal-speed playback fallback are preserved. Unclear speech can use a
  complete informative caption with explicit provenance; infrastructure failures
  do not silently substitute captions. Speech/frame disagreement requires review.

## Final checks

| Check | Result |
|---|---|
| Full installed backend suite | **291 passed, 0 failed** |
| Full extension tests | **45 passed, 0 failed** |
| Extension product contract / build | Passed / passed |
| Admin dashboard lint / build | Passed / passed |
| Local API / MariaDB startup | `/ready: true`, MariaDB available |
| Speech provider | Local faster-whisper turbo, CPU INT8; engine loaded |
| NLI loading | Explicit prepared local snapshot; lazy request-time load, no remote inference |

The final backend suite was rerun after the reader-state metadata correction.
Earlier migration failures were corrected in the working copy: obsolete runtime
references, retired score fixtures and a missing untitled-name anchor guard.
The suite counts differ from older reports because remote-provider tests were
retired/adapted and local contracts were added; these are not added accuracy samples.

Two controlled synthetic integration fixtures exercised the **actual** local NLI
model and evidence-decision code with outbound HTTP blocked: a supporting Taglish
clinic passage and a contradictory English smoking-policy passage. They produced
the expected two evidence-assisted labels with actual supplied passages. The URLs
were fixture identifiers, not real retrieved reports. This is integration
evidence, not a two-example accuracy claim.

## NLI calibration is conservative and limited

There are 108 authored synthetic semantic pairs, fixed before scoring: 72 for
calibration, 36 in scenario-disjoint audit. The selected acceptance thresholds
are **0.998 entailment / 0.999 contradiction**, replacing arbitrary 0.80 cutoffs.
The audit accepted six correct support/contradiction relations and no incorrect
ones, but left **18 of 24** real support/contradiction relationships unaccepted.
All 12 unrelated pairs stayed related; three-way audit accuracy is **50%**.
Low coverage is an unresolved limitation. See [the calibration report](LOCAL-NLI-CALIBRATION-20261120.md)
and its per-pair JSON for the full sweep. Taglish/Tagalog inference is not
guaranteed by the multilingual model name or a high individual score.

## Real local video rehearsal

Two existing complete files were decoded and transcribed by the shared local
pipeline with outbound HTTP blocked. MP4 extraction took **75.308 s**; captured
WebM extraction took **100.779 s**. Both returned local transcript segments and
sampled OCR, and both still required speech/frame review. These times exclude
Facebook acquisition/playback, final classification, evidence lookup and human
review. They are not a controlled before/after speed comparison or a transcript
accuracy benchmark. Earlier cloud latency gains do not apply to this local path.

The module's ordinary VAD/language hints, quality gates and transcription retry
rules are preserved. Existing local transcript material-word issues have not
been declared fixed; manual matching against original speech remains necessary.

## The primary classifier bias remains

The requested existing `probe_short_statement_bias.py` was run against the
unchanged active profile after migration. On its 40 authored examples, relative
to the probe's intended labels: **TN 4, FP 16, FN 1, TP 19**; agreement **57.5%**;
16/20 intended neutral examples were flagged (**80%**).

Those rates are diagnostic, not measured real-world Facebook accuracy. The
existing probe includes time-specific notices and personal anecdotes whose
real-world truth was not independently established. Its source comments describing
all labels as genuine ground truth should not be used as external validation.
Nevertheless, the result makes clear that removing Gemini did **not** repair
the base classifier's short/neutral-text behavior. No training, threshold tuning
or replacement model was performed. The historical 96.32% inherited-label test
result remains a separate record.

The [short-text plan](SHORT-TEXT-RETRAIN-PLAN-20261120.md) records the actual original
`topic,text,label` schema and why the archived fixed-4,000 notebook must not be
silently appended/re-split. The proposed 120-row balanced supplement has not yet
been supplied. Future training requires explicit authorization and a separate
representative source-checked audit.

## Remaining work and recovery

Actual installed Chrome/Facebook observations, representative classifier/evidence
evaluation, transcript-word checks and local CPU latency remain open. They are
not marked passed by regression tests. The private rollback copy is under
`.run/local-model-migration-20261120T010809Z/`; it includes old private settings
and must never be published. Gemini credentials/settings were removed from active
local env files, not printed or committed. Model weights and databases remain
ignored. The existing admin-password exposure in old public history is a separate
previously reported credential issue.

## Complete file inventory

### Modified

- `README.md`
- `START_HERE.md`
- `admin-dashboard/src/components/ActivePipeline.jsx`
- `backend-api/.env.example`
- `backend-api/config.py`
- `backend-api/requirements.txt`
- `backend-api/src/app.py`
- `backend-api/src/evidence_decision.py`
- `backend-api/src/media_processing.py`
- `backend-api/tests/conftest.py`
- `backend-api/tests/test_api.py`
- `backend-api/tests/test_media_processing.py`
- `backend-api/tests/test_verified_final_policy.py`
- `chrome-extension/manifest.json`
- `chrome-extension/src/Popup.jsx`
- `chrome-extension/src/content.js`
- `chrome-extension/src/result_binding.js`
- `docs/ASEAN-EVIDENCE-FIX-20261116.md`
- `docs/CURRENT-SOURCE-20261120.md`
- `docs/DECISION-COMPARISON-20261116.md`
- `docs/EVIDENCE-ANCHOR-AUDIT-20261116.md`
- `docs/FASTER-VIDEO-LOCAL-TRIAL-1.3.45.md`
- `docs/FINE-TUNED-LOCAL-TRIAL-20261120.md`
- `docs/GEMINI-EVIDENCE-SETUP-20261116.md`
- `docs/LOCAL-SURVEY-BUILD-1.3.44.md`
- `docs/PRIMARY-GEMINI-LOCAL-TRIAL-20261116.md`
- `docs/README.md`
- `docs/SEMANTIC-LOCAL-TRIAL-20261116.md`
- `docs/SURVEY-PREPARATION-20261116.md`
- `docs/TRACKING-ARTICLE-IDENTITY-FIX-20261116.md`
- `docs/VIDEO-PROCESSING-20261120.md`
- `docs/VIDEO-SPEED-20261116.md`
- `scripts/start-finetuned-trial.ps1`
- `scripts/start-survey-local.ps1`
- `scripts/verify_admin_browser.mjs`

### Added

- `backend-api/scripts/calibrate_local_nli.py`
- `backend-api/scripts/prepare_local_nli.py`
- `backend-api/src/local_nli.py`
- `backend-api/src/local_nli_thresholds.json`
- `backend-api/tests/fixtures/local_nli_pairs.jsonl`
- `backend-api/tests/test_local_audio.py`
- `backend-api/tests/test_local_nli.py`
- `chrome-extension/tests/local-result.test.mjs`
- `docs/GEMINI-REMOVAL-20261120.json`
- `docs/GEMINI-REMOVAL-20261120.md`
- `docs/LOCAL-NLI-CALIBRATION-20261120.json`
- `docs/LOCAL-NLI-CALIBRATION-20261120.md`
- `docs/SHORT-TEXT-RETRAIN-PLAN-20261120.md`

### Deleted

- `backend-api/src/gemini_audio.py`
- `backend-api/src/gemini_classifier_trial.py`
- `backend-api/src/gemini_evidence.py`
- `backend-api/tests/test_gemini_audio.py`
- `backend-api/tests/test_gemini_evidence.py`
- `chrome-extension/tests/gemini-result.test.mjs`
- `scripts/start-gemini-trial.ps1`

Private local settings were updated separately: `backend-api/.env.local` and `backend-api/.env` when present. Their contents and backups stay outside Git. The machine additionally received `sentencepiece==0.2.1` and the pinned local NLI snapshot; existing torch/transformers versions were not upgraded.
