# Frozen candidate evaluation: human review instructions

The 24 text cases are frozen in the ignored private file
`research-data/evaluation-20261029/review_batch.csv`; see the hashes-only
`EVALUATION-BATCH-MANIFEST.json`. Do not share raw case text or private review
notes in Git, the extension bundle, or public reports. The batch has four cases
per inherited-label/word-length stratum. Inherited labels and saved model scores
are sampling/replay metadata, **not** human judgments. This selected sample is
not a prevalence estimate.

Two reviewers should independently read each **complete** claim, identify the
people/entities, event, date, place, quantities, negation, and material qualifiers,
and inspect the full source or original primary record. Record a stable evidence
URL, source publisher, claim date/location, and why the source does or does not
establish the exact claim. A shared wire report copied by multiple outlets counts
as one original line of evidence. When sources conflict, investigate provenance
and retain the conflict in notes. Reviewers should first work without seeing
`saved_model_score_for_replay_only` or the inherited label.

Use `human_label=Misleading` or `Non-Misleading` only after both reviewers agree
and evidence is sufficient. Otherwise leave `human_label` blank and set
`review_status=unresolved` or `insufficient_context`; retain those cases in the
denominator of cases attempted. Never force uncertain claims into a binary label.
After adjudication set `review_status=adjudicated`, enter both reviewer codes,
evidence URL, and concise notes. Do not overwrite initial disagreements; preserve
them in a separate private adjudication log. Obtain the institution's approval
for record storage, retention, and reviewer process before human evaluation.

The private `media_review_batch.csv` lists two PNGs and two silent MP4s frozen as
synthetic renderings of four text-batch claims. Inspect extraction and displayed
context through the image/video routes; record outcomes separately and do not
count them as four independent classification cases. For natural image/video
coverage, collect a **separate** frozen set of public or researcher-created media
after checking rights and provenance.
Record media SHA-256, source URL/creator, capture date, mode, exact OCR/transcript,
extraction failures, and reviewer judgments. These are currently outstanding;
do not count the existing synthetic image/video smoke fixtures as factual claims.
Do not combine duplicate text and media renderings of one claim as independent
accuracy cases.

After adjudication, start the exact candidate API and run
`..\.venv-candidate-20261023-isolated\Scripts\python.exe -B scripts/evaluate_frozen_batch.py`
from `backend-api`. This replays every frozen text case through `/analyze` with
related-source lookup and writes a private per-case report. It counts HTTP
failures and unresolved cases, and reports TN/FP/FN/TP, accuracy, class precision,
recall, F1 and macro-F1 on adjudicated cases only. Do not publish a performance
claim until the completion count and unresolved/failure count are disclosed.
Before adjudication, run the same command with `--audit` to confirm the frozen
case count without network requests. The full replay refuses to run while no
human adjudication is recorded.
