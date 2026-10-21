# Release evidence and GO/NO-GO — October 21, 2026

**Implemented:** the fixed hybrid runtime, feature display, separate optional evidence
lookup, MariaDB schema v5, administration and deployment scripts. Participant survey
collection is outside the extension and administrator dashboard.
**Tested:** the native local checks below. **Deployment prepared:** single-VPS Compose,
private model mounts, explicit migrations, HTTPS proxy, retention and backups.
**Actually deployed:** no public deployment, hosting purchase, domain purchase or store submission.

## Completed evidence

| Check | Actual result | Evidence |
| --- | --- | --- |
| Raw-text hybrid parity | 598/598 labels; no probability mismatches at atol=rtol=1e-5 | [HYBRID-VERIFICATION.json](HYBRID-VERIFICATION.json) |
| Model identity | Only model_4; run 20261011T235112Z; pinned SHA-256; threshold 0.65; CPU | [Integration contract](HYBRID-INTEGRATION.md) |
| Backend regression suite | 69 active-runtime tests passed; no unresolved failures in the final run | `python -m unittest discover -s backend-api/tests -p 'test_*.py'` |
| Model scope sanity probe | Saved examples produced both classes as recorded, but 10/10 short general statements were predicted Misleading with scores from 0.902293 to 1.0 | [Diagnostic report](MODEL-SANITY-DIAGNOSTIC.json) |
| Live API and extension transport | Actual fresh inference, empty/long input and real fetch through extension client/background | [HTTP report](HYBRID-HTTP-VERIFICATION.json) |
| MariaDB | Empty/idempotent v1–v5 migration, actual provision command, DML-only writes, denied DDL, rollback, restart, outage, isolated SQL restore and withdrawal | [MariaDB report](MARIADB-VERIFICATION.json) |
| Existing local database | Private logical backup made; schema v5 applied; existing candidate count preserved | Local operator execution; ignored backup under `backups/pre-schema5-*.sql.gz` |
| Evidence providers | Current live provider check: Serper returned 3 links and Google Fact Check returned 3 reviews; an installed-extension run displayed 2 related links and 3 fact-check links | [Provider report](PROVIDER-VERIFICATION.json), [installed-extension report](INSTALLED-EXTENSION-VERIFICATION.json) |
| Provider edge cases | Mocked success/empty/timeout, malformed or oversized response rejection, redirect rejection, missing-key behavior | `test_services.py`, `test_participant.py`; these fixtures are not live evidence |
| Media | Actual EasyOCR image smoke passed in 13.4 s; video OCR + Whisper smoke passed in 21.4 s | [Media report](MEDIA-VERIFICATION.json); synthetic fixtures, not an accuracy study |
| UI | Actual React component screenshots in headless Chrome; API feature values match rendered data attributes; narrow viewport overflow checked | [UI report](UI-VERIFICATION.json), [screenshots](verification/ui/) |
| Installed extension | Actual unpacked build in isolated Microsoft Edge Chromium: action popup, focused caption extraction, reload toggle, persisted opt-in lookup, long/stale/duplicate behavior, live Serper/Google evidence, and absence of survey controls passed | [Installed-extension report](INSTALLED-EXTENSION-VERIFICATION.json) |
| Extension failure states | A stopped backend produced a clear unavailable message and no prediction; controlled popup checks covered timeout, no-results and provider-unavailable display without changing the classifier result | [Failure-state report](EXTENSION-FAILURE-VERIFICATION.json) |
| Administrator browser flow | Actual isolated Chromium login, HttpOnly-cookie reload, absent participant view/export, logout, expired 401, first keyboard focus and narrow layout passed | [Admin browser report](ADMIN-BROWSER-VERIFICATION.json) |
| Frontends | Dashboard lint/build and extension build passed; release extension build intentionally rejects missing HTTPS configuration | `npm run lint`, `npm run build`, `npm run build:release` |
| Dependencies | Runtime/model primary versions pinned; pip check passed; npm lockfiles retained | requirements files and package-lock files |
| Cleanup and deployment paths | SHA-256-preserving moves; retired runtime imports absent; five read-only artifact mounts; database not exposed; single worker | [Structure](PROJECT-STRUCTURE.md), [static deployment checks](DEPLOYMENT-VERIFICATION.json) |
| Privacy and access | No screening/survey storage; external search remains opt-in; participant routes/export removed; login JSON exposes no bearer token; origin/role tests | `test_participant.py`, installed extension and admin browser reports |
| Backup expiry | Completed expired dumps are removed; recent dumps, partial files and unrelated files are preserved | `test_backup_retention_only_removes_expired_completed_dumps` |

The full raw-text pipeline—not saved embeddings or cached answers—produces the parity
report. The original maximum absolute difference was 3.1492805406818647e-6. Reference
records were used only for integration checks. No model was trained or tuned.

Parity proves that serving reproduces the saved artifact; it does not prove that the
artifact generalizes. A targeted live probe of ten brief ordinary English/Filipino/
Taglish statements produced ten Misleading predictions, including several saturated
scores. This is a material model-quality limitation, not a loader or fallback-model
defect. The UI now warns about brief/out-of-distribution inputs and the extension extracts
focused post caption text, but those changes do not correct the classifier itself.

## Resource measurements and their limits

[RESOURCE-MEASUREMENTS.json](RESOURCE-MEASUREMENTS.json) records one native Windows API
worker, CPU execution, four inference threads and two admitted simultaneous screenings.
Five short requests had a median HTTP latency of **46.96 ms**; measured inference ranged
from approximately **24–26 ms** after startup. A **1,611-content-token/four-chunk** input
took **1,367 ms** for inference. Peak sampled process-tree RSS was **816.3 MiB**. Three
simultaneous long requests returned **200, 503, 200**: overload was rejected, not fabricated.

Retrieval was disabled for the model timing and measured separately with live provider
calls above. These are single-run observations and a very small short-input sample,
not a throughput SLA, percentile estimate, participant-capacity promise or Linux/VPS
benchmark. Memory excludes separate MariaDB/dashboard processes and separately warmed
OCR/Whisper. Model initialization occurs before readiness. Repeat the benchmark and
measure the complete container stack on the intended host before choosing capacity.

[LIVE-STACK-PERFORMANCE.json](LIVE-STACK-PERFORMANCE.json) adds one current native run
covering the live API, Vite dashboard and MariaDB listener processes. Ten short requests
had a 25.04 ms median and 76.58 ms p95; the complete long input took 2,781.37 ms; three
concurrent requests all returned 200 in 4,285.87 ms; one live retrieval returned two
links in 1,829.43 ms. Peak sampled stack RSS was 1,032.64 MiB. This is still a single
Windows workstation observation, not a Docker/Linux capacity result or SLA.

## What visual checks do and do not establish

Screenshots cover popup input/result, 320-pixel popup layout and desktop/narrow admin login.
Headless Chrome rendering uses the actual
React components and an actual synthetic API result. It checks exact viewport width,
horizontal overflow and seven unscaled feature values. The misleading prediction in a
synthetic screenshot is the model's actual output, not an approved factual judgement.

The installed-extension harness loaded the unpacked build in an isolated Microsoft Edge
Chromium profile and exercised a synthetic article on a manifest-supported facebook.com
origin. It did not use an account or participant content. Google Chrome 156 ignored the
command-line unpacked-extension flag on this machine, so manual Chrome installation,
current third-party DOM behavior and screen-reader testing remain hands-on checks. The
earlier narrow screenshot harness was repaired to use explicit device emulation. The
timeout/no-results/provider-failure popup states used controlled transport responses;
the corresponding backend provider branches are separately covered by automated tests.

## Research delivery

[Participant guide](research/PARTICIPANT-GUIDE.md), [separate BSIT/AFP questionnaires](research/QUESTIONNAIRES.md),
expert-review form, pilot checklist and [traceability](research/PILOT-AND-TRACEABILITY.md)
are drafts ready for institutional review. No questionnaire validation, participant
responses, scores, reliability coefficients or certification is claimed. The historical
agreement statistic was removed from the active backend. The saved comparison still
shows TF-IDF outperforming the hybrid on the reported test metrics.

The product does not collect usefulness feedback or participant responses. Use the
documented blank long-format response schema and validation tool for the separate survey;
store actual responses only under private, ignored `research-data/` or approved storage.

## GO / NO-GO gate

**GO:** internal local rehearsal with synthetic inputs and review of the prepared materials.
**NO-GO:** public deployment or formal participant evaluation until all applicable gates below pass.

- [x] Required artifact hashes, exact preprocessing/features, threshold and parity verified.
- [x] Failure paths return errors; no reachable alternate classifier or random label.
- [ ] Model owner resolves the observed short-input Misleading bias through a new reviewed training run, or formally restricts and validates the supported input scope.
- [x] No screening or survey storage path is exposed; participant UI/routes/export are removed.
- [x] Native MariaDB migration, least-privilege provisioning, restart and logical restore passed.
- [x] Live providers and synthetic media processing checked; model and retrieval timings separated.
- [x] Frontend builds and inspected headless component layouts passed.
- [x] Isolated Chromium unpacked-extension and authenticated administrator flows passed with synthetic data.
- [x] Backup expiry selection and the daily maintenance configuration were checked locally.
- [ ] Docker/Compose installed on a test host; exact images build and stack reaches healthy state.
- [ ] Linux container migration/backup-wrapper/restore and full-stack memory/load checks passed.
- [ ] Manual Google Chrome install, current social-page DOM, full keyboard and assistive-tech rehearsal passed.
- [ ] Final supported social-page/media matrix and participant task scope signed off.
- [ ] Institutional/adviser approvals, study contact, consent language and questionnaire review completed.
- [ ] Linux retention timer execution, off-server backup access and withdrawal-after-restore process verified.
- [ ] For public service: chosen server/domain, DNS, HTTPS, production cookies/CORS, generated credentials and monitoring verified.

## Consolidated external/operator actions

1. Use a Docker-capable local/Linux test host. Follow `START_HERE.md` local Compose steps;
   no purchase or public endpoint is required for this gate. Docker is absent here.
2. Complete one manual Google Chrome supervised rehearsal and record results using the
   pilot form. Test supported pages against their current DOM and permissions, then run
   keyboard-only and screen-reader checks. The isolated Edge Chromium rehearsal passed.
3. Have the study team finish contact/approval fields, review the draft instruments and
   decide participant scope/retention before recruitment. This cannot be fabricated by code.
4. If public deployment is later authorized, choose the VPS and sibling API/admin domains,
   provide DNS and TLS contact details, generate private settings, securely transfer the
   supplied model directory, configure approved evidence keys and run the documented gates.
   Working provider credentials exist locally; their production transfer must remain private.
5. Configure private off-server backup storage and monitoring; test retention/restore on
   Linux. Retain model artifacts/settings securely; never publish raw records or secrets.

No additional classifier artifact is missing. CUDA was not tested; CPU is the verified
deployment path. Do not label these remaining external checks “passed” based on native tests.

## Changed areas

- Backend: `config.py`, `app.py`, `database.py`, `research_store.py`, `feature_display.py`,
  `hybrid_pipeline.py`, `model_runtime.py`, `provider_http.py`, `retrieval.py`, `fact_check.py`,
  `media_processing.py`, `traffic_limits.py`, `manage.py`, deployment checks and requirements.
- Extension: `Popup.jsx`, `api.js`, `background.js`, `content.js`, styles, build configuration,
  release command and locally rebuilt distribution (ignored by Git). Previous-result disk storage removed.
- Dashboard: session handling, responsive styles, login, model status and Research export page.
- Verification: expanded backend tests, live HTTP/resource harness, MariaDB/provider/media/UI,
  installed-extension and administrator browser scripts with aggregate JSON reports. Failures
  found during work were corrected and retested; Docker/Linux and manual Chrome/assistive-tech
  gates remain explicitly unverified.
- Operations/research: Compose migration service, secret generators, backup retention/timer,
  START_HERE, deployment runbook, survey validation and participant/research materials.

Existing unrelated working-tree edits and existing participant/candidate data were preserved.
Model binaries/raw datasets previously staged for untracking remain excluded from new commits;
historical Git copies were not erased. No public service deployment or paid purchase was made. See the handoff for the source-control commit and push result.
