# SuriPH current readiness — 29 October 2026

This page supersedes older release and browser reports where they describe automatic
source corroboration, model_4 threshold 0.65 as the active local model, or an earlier
extension version. Keep those reports as historical evidence, not current sign-off.

## What the system now decides

The local API runs one pinned classifier: `model_4_full_dataset_CANDIDATE.joblib`, run
`full-cleaned-20261023T022416Z`, SHA-256
`c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376`,
threshold `0.4000000000000001`, CPU. The candidate is `local_trial: true` and
`deployment_approved: false`. Production configuration rejects this profile. The
previous model_4 is an explicit rollback profile, not a runtime fallback.

The final output uses only **No Misleading Information Detected** and **Potentially Misleading**. The internal class remains `Non-Misleading`.
An additive, conservative full-article gate can change the original model verdict
only when direct claim-specific support or contradiction is established. Search
snippets, official domains, multiple related publishers, and lexical fact-check
overlap do not establish this. Inaccessible, conflicting and merely related
coverage leaves the model prediction intact. Public screening does not query
Google Fact Check. `model_score` remains the score for the model's internal
**Misleading** class and is not confidence in an evidence-derived verdict.
See `EVIDENCE-DECISION-20261029.md` for the exact process and new verification.

The Facebook extension refuses a caption with a collapsed See more control or a
terminal ellipsis, and asks the user to expand or select the complete content.
The API also refuses explicit `caption_complete: false` metadata with HTTP 422 before
inference. Short complete claims are still screened. This heuristic cannot detect
every missing context or OCR/transcription omission; users must inspect the exact
analyzed text and the selected media.

## Evidence actually observed on this workstation

On 29 October, the documented portable MariaDB instance started and schema migration
reported no pending versions. The local API `/ready` returned `ready: true`, MariaDB
available, the candidate identity/hash/threshold above, and CPU. A complete short
claim returned HTTP 200; the incomplete-caption case returned HTTP 422. The image
and video API routes each returned HTTP 200 on existing synthetic fixtures, extracted
the expected word, and reported `evidence_adjusted: false`. In the frozen media
supplement, both images passed. Two initial videos failed because the generated
fixtures lacked audio streams; their hashes and HTTP 422 failures are retained in
`research/MEDIA-SUPPLEMENT-REHEARSAL.json`. Amended videos with silent audio tracks
both returned HTTP 200, with one sampled frame each. Backend regression suite:
94 tests passed in the latest run. Dashboard lint/build and extension 1.3.11 build passed. The actual
content script in an isolated Microsoft Edge Chromium profile passed its synthetic
HTTPS Facebook fixture, including caption boundaries, excluded controls/comments,
source-only lookup, bilingual result stability, and no prediction for an incomplete
caption. The fixture report is `FACEBOOK-MODAL-VERIFICATION.json`.

This does not establish operation on a current logged-in Facebook account. Google
Chrome access through computer use timed out; extension 1.3.11 installation/reload
and post-refresh observation remain unverified. The dashboard's local API default
is `http://127.0.0.1:8000/admin-api`, and the local extension build uses the same
origin. No Linux/Compose or public HTTPS deployment was performed.

The candidate's inherited-label test set has 3,470 records: 93.60% accuracy,
macro-F1 90.03%, 108 false positives, and 114 false negatives. Those are agreement
with inherited labels, which retain annotation conflicts. The 3,470/3,470 saved
prediction replay establishes integration parity. Neither figure is independent
fact verification or an observed Facebook false-positive rate.

## Supervised evaluation and public release

The frozen private 24-text-case batch and four paired synthetic media
renderings (two images and two silent videos) are described in
`research/EVALUATION-BATCH-MANIFEST.json` and the review instructions below. It is
balanced by inherited label and word length, excludes earlier diagnostic texts,
and has no claim-group overlap with train/validation partitions. The original
labels are only sampling strata. Human verdicts, full-source evidence links,
unresolved decisions, and final end-to-end accuracy are still pending. The
paired media test acquisition only; they are not four independent claims.
Media processing has synthetic functional smoke evidence, not a natural-media
accuracy study.

**Supervised usability/system testing:** suitable for a controlled pilot on public
or researcher-written content once the facilitator completes the current Chrome
installation/reload rehearsal and the study team approves contact, consent, tasks,
and ISO-based questionnaires. Describe it as a screening prototype and allow
participants to flag incorrect or unclear results. Do not use participant surveys
as substitutes for independent claim labels.

**Verified classification performance:** not established until human reviewers
adjudicate the frozen batch with evidence and the final API output is scored,
including false positives, false negatives, failures, and unresolved cases.

**Public deployment:** no-go. Candidate is not approved for production; Linux
Compose, HTTPS, backup/restore, current Chrome/Facebook, institutional and
operational gates remain. No store publication is part of this work.

## Current local startup

From the repository root, preserve `backend-api/.env.local` and ensure it selects
`SURI_MODEL_PROFILE=full-cleaned-20261023T022416Z`. Run:

```powershell
.\scripts\start-mariadb.ps1
cd backend-api
..\.venv-candidate-20261023-isolated\Scripts\python.exe -B -m src.manage migrate
..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In a second terminal, inspect `http://127.0.0.1:8000/ready`. Build the extension
with `cd chrome-extension; npm.cmd run build`, then reload version 1.3.14 in
`chrome://extensions` and refresh each Facebook tab. Build/start the dashboard
as described in `START_HERE.md`. Do not run two APIs on port 8000.

## Manuscript correction checklist

- Replace any statement that the deployed/local candidate is the old model_4
  run with the candidate run ID, threshold, 23,128 dataset records, and 3,470
  inherited-label test records. Keep the older experiment as a separate baseline.
- Remove claims that one official article, two publishers, or a lexical fact-check
  automatically verifies or changes a claim. Describe links as unverified context.
- State that the saved score is P(Misleading) from the classifier, not probability
  of factual falsehood or certainty in a source-derived verdict.
- Separate inherited-label metrics and parity from any human-verified Facebook
  evaluation. Report the pending human batch and later include all TP/TN/FP/FN,
  unresolved cases, input-mode failures, and the sampling design.
- Keep the reported TF-IDF comparison: the previous hybrid did not outperform
  TF-IDF on the cited saved test metrics. Do not invent fine-tuning or new training.
- Update extension diagrams/screenshots to version 1.3.11 and show the incomplete
  caption prompt and source-relationship disclaimer.
- Keep the ISO-based BSIT and AFP survey as a separate usability/system-quality
  evaluation. Do not insert participant registration, fabricated survey findings,
  or the removed agreement statistic.

This checklist identifies edits for the study team; it does not claim that the
submitted manuscript or research findings have already been revised.
