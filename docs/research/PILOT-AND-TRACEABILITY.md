# Pilot, expert testing and traceability

This supersedes the older traceability file's training/activation and agreement-statistic
claims. The PDF still describes some historical proposals. The user's final scope pins
model_4, removes retraining/activation and the removed inter-rater statistic, and keeps
survey collection outside the product. Record these changes in the final manuscript; do not silently imply the
old proposal was fully implemented.

## Pilot checklist (record actual date, operator and result)

- [ ] Adviser/institutional permissions, recruitment text and consent contact completed.
- [ ] Separate eligible/invited/completed counts planned for BSIT and AFP populations.
- [ ] Questionnaire expert review completed; item revisions and version retained.
- [ ] Exact build, browser/OS, model hash, run ID and server configuration recorded.
- [ ] Readiness true; disposable synthetic records only during rehearsal.
- [ ] Installed extension permission review, manual/selected/caption flows checked.
- [ ] Keyboard-only and screen-reader checks performed, including focus and error announcements.
- [ ] Long text, changed input, duplicate click and timeout behavior checked in real Chrome.
- [ ] Live lookup/no-result/provider failure demonstrated with clear limitations.
- [ ] Optional real media cases checked; unsupported cases excluded from participant tasks.
- [ ] Extension/admin contain no participant survey, receipt, feedback or export controls.
- [ ] Separate approved survey storage and retention process documented and rehearsed.
- [ ] Viewer cannot write; expired sessions and DB outage handled.
- [ ] Workload and acceptable response time reviewed against measured target-server evidence.
- [ ] Pilot comments reviewed, defects fixed/retested, task duration recorded.
- [ ] GO/NO-GO recorded; no fabricated questionnaire responses or evaluation means.

## Blank functional/expert test record

```text
test_id,objective,requirement,build,prerequisites,input_or_action,expected_result,
actual_result,status,evidence_path,defect_id,retest_of,tester_code,date
```

Allowed status: pass/fail/blocked/not_run. A retest gets a new record referencing the
failure. Preserve original failure notes. Do not enter “pass” for a document-only review
when the test requires live behavior.

## Objective-to-evidence map

| Objective / requirement family | Implemented function | Verification evidence | Boundary |
| --- | --- | --- | --- |
| Reproduce selected Taglish hybrid | Pinned encoder/tokenizers/features/scalers/LR, threshold 0.65 | HYBRID-VERIFICATION.json: 598 labels and probabilities within tolerance | Integration parity, not independent truth validation |
| Expose interpretable measurements | Seven original unscaled values and definitions | test_participant; UI-VERIFICATION.json data-value checks | Measurements are not model contributions |
| User-triggered acquisition | Manual, selected text/caption, image/video modules | INSTALLED-EXTENSION-VERIFICATION.json; MEDIA-VERIFICATION.json | Synthetic supported-origin Chromium capture passed; current third-party DOM and manual Chrome still require hands-on testing |
| Independent contextual retrieval | Serper related reading; Google researcher review | PROVIDER-VERIFICATION.json; mocked failure/empty tests | Links do not prove relevance or verdict |
| Candidate governance | Existing curator workflows and protected dataset records | Existing API/database suite | Public auto-capture retired; no participant text enters training automatically |
| Privacy and research evaluation | No screening storage; survey collection kept outside extension/admin | test_participant; installed extension and admin browser reports | Questionnaire consent, approvals and private response storage remain institutional work |
| Persistence and reliability | Schema v5, runtime DML account, migration service | MARIADB-VERIFICATION.json | Native test passed; Docker/Linux wrapper pending |
| Performance efficiency | One worker, four CPU threads, two in-flight screenings | RESOURCE-MEASUREMENTS.json; LIVE-STACK-PERFORMANCE.json | Windows workloads; no Docker/Linux capacity guarantee |
| Security/admin access | HttpOnly cookie session, origin checks, role checks, bounded providers | Automated auth/origin/failure tests; ADMIN-BROWSER-VERIFICATION.json | Production HTTPS and broader browser matrix pending |
| Deployment/maintenance | Compose, read-only artifacts, retention and logical backup | Configuration review, local DB restore | Container build/start/TLS not run: Docker unavailable |

## Preserve the model comparison

The supplied held-out `test_metrics_with_cluster_bootstrap.csv` reports:

| Configuration | Test n | Macro F1 | Accuracy | False-positive rate |
| --- | ---: | ---: | ---: | ---: |
| TF-IDF + LR (reference only) | 598 | 0.966549 | 0.966555 | 0.023333 |
| DistilBERT + LR (reference only) | 598 | 0.939718 | 0.939799 | 0.026667 |
| Linguistic + LR (reference only) | 598 | 0.852181 | 0.852843 | 0.083333 |
| Hybrid / model_4 (only served classifier) | 598 | 0.936352 | 0.936455 | 0.026667 |

These are reported reference experiment values, not new training runs. The hybrid did
**not** outperform TF-IDF on these metrics. Do not convert model agreement with dataset
labels into a claim that every record was independently fact-verified. Participant
usability/quality ratings are a separate evaluation and have not yet been collected.
