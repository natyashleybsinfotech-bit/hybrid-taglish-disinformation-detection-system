# SuriPH final defense rehearsal record

**Date:** 10 November 2026, local Windows laptop. **Decision:** the local service is available for supervised testing, but the final defense, participant survey and public deployment are not yet signed off. This record is the current handoff; older dated release pages remain historical. The 45-item [revised questionnaire checklist](research/QUESTIONNAIRE-ACCEPTANCE-20261110.md) has 10 passed, 1 failed and 34 not demonstrated. Participant ratings are blank.

## Exact build in this rehearsal

The [build manifest](REHEARSAL-BUILD-20261110.json) records Git HEAD, dirty working-tree status and SHA-256 hashes of the actual local extension/dashboard bundles and backend source files. The working tree was **not clean**; retain it and do not represent this as a tagged public release. The built local extension is **1.3.15** in `chrome-extension/dist`. The active API loads **only** `model_4_full_dataset_CANDIDATE.joblib`, run `full-cleaned-20261023T022416Z`, artifact SHA-256 `c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376`, 775 dimensions and threshold `0.4000000000000001`. The API and MariaDB were left available on loopback. This is a **local trial candidate**, not an approved hosted release.

The admin dashboard is available at `http://127.0.0.1:5173`; API at `http://127.0.0.1:8000`. The current Chrome installation has **not** been confirmed to be the rebuilt extension. Reload `chrome-extension/dist` in `chrome://extensions` and refresh Facebook before the user's manual test. The current local extension uses the loopback API. A public release build requires an approved real HTTPS API origin and has not been produced.

## Verification on the actual current local build

| Check | Observation | Boundary |
| --- | --- | --- |
| API and database | `/health` available; `/ready` true; MariaDB available; pinned candidate hash and threshold matched the build manifest. Running migration reported `applied_versions: []`. | Local Windows only. |
| Backend suite | **119 tests passed** in the active isolated candidate virtualenv. Full log is private at `tmp/backend-full-20261110.log`. | Software tests, not factual accuracy. |
| Extension | **7 binding/video review tests passed**; extension production build passed. | Built bundle has not been checked in the user's installed Google Chrome. |
| Facebook modal | Current content script passed isolated Edge Facebook-origin fixture: selected post, neighboring post exclusion, post switch, stale response, bilingual label stability, source-only lookup and output order. | Synthetic page fixture, no real Facebook account or post. [Report](FACEBOOK-MODAL-VERIFICATION.json). |
| Administrator workflow | Real dashboard/API in isolated Edge: admin sign-in, cookie reload, logout, expired session, viewer sign-in, desktop/narrow layout and retired research export. A stale browser-test expectation for post-login `/` was corrected to `/performance`, matching the requested dashboard landing page. | Test accounts; no participant records. [Report](ADMIN-BROWSER-VERIFICATION.json). |
| Access control | Viewer login worked; `GET /admin-api/candidates` returned **403** for viewer and **401** without a session. | Local HTTP; deployed HTTPS is pending. |
| MariaDB recovery | Separate disposable MariaDB 11.4.13 instance applied migrations 1–6, rejected DDL from runtime account, retained records after restart and restored a logical gzip backup into a second isolated database. The live database was untouched. | Native Windows; Linux/Compose recovery is pending. [Report](MARIADB-VERIFICATION.json). |
| Repeatability and disclosure | Twice submitted the same synthetic sentence with lookup off. Both responses were **Potentially Misleading**, score `0.41724348392335725`, exact analyzed text, and `verification_status: not_verified`. | Repeatability and disclosure only; this is not a reviewed truth label. |
| Independent factual evaluation | Frozen 24-case audit: **0 adjudicated with evidence, 24 pending**; zero network requests. | Raw-model and final-system FP/FN counts and denominators are **not measurable yet**. No threshold tuning was done. [Instructions](research/HUMAN-EVALUATION-INSTRUCTIONS.md). |

### Windows Application Control incident, separate from test results

The **first** full backend run reported `Ran 84 tests ... FAILED (errors=1)` because `test_api` could not import `app` through SQLAlchemy. Python raised `ImportError: DLL load failed while importing _util_cy: An Application Control policy has blocked this file.` The exact file was:

`C:\Users\Lenovo\Desktop\capstone-wtf\hybrid taglish-detector system\.venv-candidate-20261023-isolated\Lib\site-packages\sqlalchemy\engine\_util_cy.cp313-win_amd64.pyd`

Its SHA-256 was `051AB7F3EE13FB4FE5017C9A3C57992FA3B18528536B9E334F6BF53788A8508C`. Windows Code Integrity Operational events **3033** and **3077** named that file, the Python 3.13 process and Enterprise signing policy ID `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`. The file had no digital signature or Zone.Identifier alternate stream. An immediate standalone import and focused `test_api` rerun then succeeded; the **complete 119-test suite passed** in the same pinned virtualenv and unchanged Windows policy. This is an intermittent Windows load/policy issue, not a failing application assertion. No security control, execution policy, signature requirement or antivirus setting was weakened. If it recurs, preserve the event/log and have the machine administrator investigate the policy and approved Python wheel path; do not bypass the policy.

### Known factual and media limitations

The earlier reported Bureau of Customs vape-caption replay used text reconstructed from a screenshot, not the exact installed-extension request. Its model score was **0.9864678225697466** and the final label remained **Potentially Misleading**. The official article became readable after the reader fix, but the strict assertion gate classified it as **related**; this is **unresolved** as a factual false-positive complaint. No threshold, model or source override was changed to force that case.

The original 69-second GMA reel had material speech errors under the old ASR. The current `/extract/video` returned **HTTP 422 after 111.74 seconds with no prediction** because speech and story text did not agree sufficiently. A separate accident report had an apparently acceptable but garbled transcript; the revised video flow returned a review preview without automatically classifying it. The reviewer may reject incorrect text. Full listening-checked transcripts for these news videos are absent; [video validation](VIDEO-EXTRACTION-VALIDATION-20261103.md) does not claim news-video WER or factual accuracy.

The current evidence gate distinguishes article support, contradiction and related coverage only under strict complete-assertion rules. Search snippets, publisher status, inaccessible pages and empty results do not establish a verdict. Generic paraphrase matching and independent review of real Facebook false positives remain open. The two English public labels are **No Misleading Information Detected** and **Potentially Misleading**; `not_verified` is a disclosure, not a third label.

### Item 1.4 continuation on the original GMA reel

The [same-file retest record](research/ITEM-1.4-GMA-RETEST-20261110.md) documents the preserved 69.10-second original and captured audio (0.9995 waveform correlation), exact pre/post ASR, model comparisons, OCR exclusions, root cause and timings. The last offline extraction retest sampled the full clip at 11.52, 34.55 and 57.58 seconds; it returned the speech/frame mismatch error after **110.563 seconds**, with **no prediction**. The 57.58-second English GMA statement is relevant, but simple overlap with its Tagalog spoken paraphrase is only 11/24 salient words. ASR also still has material suspect phrases. Thus **questionnaire 1.4 remains Failed** and no word error rate is asserted.

The current source edit replaces inferred FFmpeg frame timestamps with explicit uniformly spread seeks and handles a split/compound `cyber libel` topic term. Its latest **21 media tests and complete 120-test backend suite passed** in the pinned virtualenv; no Windows security control was altered. The already-running port-8000 API was deliberately left available for the user's installed-extension test and is still the **earlier code snapshot** in the original build manifest. These new source edits have been tested offline only. Current edited `media_processing.py` SHA-256: `AE87923F9A5CE89F9D99BF5322E1D70A40F2A32EFE582AF7E21B0297996A96F0`. A direct empty-input request to the running API returned HTTP 422; the installed Chrome error screen remains unobserved.

## Manual Facebook observation to add without disturbing the current service

For each text, image and video post, record: post URL and author; selected check type; screenshot of the chooser/review screen; **exact analyzed text** shown by SuriPH; raw model label/score, evidence relationship, final label and verification notice; source URL and the specific article passage if one is shown; and elapsed time. For media, compare image words or spoken names, places, numbers, negation and allegations with the original. Record the English and Tagalog displays. For failures, retain the screenshot and post URL so the same input can be replayed through the API. Do not treat a displayed source or a green banner as proof that a claim is true. Save private test captures under ignored `tmp/` or approved study storage.

The user's manual observations will determine which of the 34 un-demonstrated questionnaire items can change status and whether a new prediction, source or transcript defect must be fixed and retested. Preserve the initial observation and append the retest result. Do not replace a failed sample with an easier one without disclosure.

## Short defense runbook

1. Use this [build manifest](REHEARSAL-BUILD-20261110.json) to identify the local extension bundle and model. Preserve `backend-api/.env.local` privately. From the repository root, start MariaDB with `.\scripts\start-mariadb.ps1` only if it is stopped. Run `cd backend-api; ..\.venv-candidate-20261023-isolated\Scripts\python.exe -m src.manage migrate` and then `..\.venv-candidate-20261023-isolated\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log`. The service is already running during this rehearsal; do not start a duplicate API on port 8000.
2. Open the dashboard at `http://127.0.0.1:5173`. Admin sign-in opens Model performance; show System status, protected candidate access with the approved test account, and logout. Do not show passwords or private records to the panel.
3. Reload the unpacked `chrome-extension/dist` in `chrome://extensions`, refresh the Facebook tab, and show the exact selected-post text before checking. Use only posts that have passed the actual Chrome rehearsal and have stable, documented source context. Show label, score explanation, `not verified` notice where applicable, article relationship, analyzed text and both language options. Do not present the 598-sample historical metrics as the current candidate's independent factual evaluation.
4. For a failed lookup, explain that the model prediction remains unverified. For backend outage, use `/ready` and restart the existing local API; no result should be fabricated. For incorrect OCR/ASR, reject the extraction and show no prediction. For a post switch or stale result, close/reselect and check the exact text again.
5. If the local database is stopped, run `.\scripts\start-mariadb.ps1`; verify `/ready` again. `./scripts/stop-mariadb.ps1` is the local stop command **after** the user's rehearsal, not during it. Preserve the data directory and existing backups.

## Three readiness decisions

| Area | Decision on 10 November | Gates passed | Still required before GO |
| --- | --- | --- | --- |
| Defense Demo | **NO-GO for final scripted demo** | Local API/DB ready; active build's prior backend 119/119; edited candidate code 120/120 offline; extension build/contracts; controlled Facebook fixture; admin workflow; isolated restore. | User's installed Google Chrome/Facebook text, image and video observations; fix/retest any wrong output; select only source-checked demonstration posts; rehearse full sequence and recovery. The original GMA video sample still fails transcript matching. |
| Participant Survey | **NO-GO** | Revised 45-item checklist created and updated with same-clip retest; separate AFP/BSIT links and 5-to-1 plus N/A scale specified; no SuriPH survey storage. | Live Chrome coverage, listening-checked correction and passing retest of item 1.4, resolution of visible source/prediction defects, expert/adviser instrument review, pilot, approved consent/contacts/retention and independent participant ratings. |
| Deployment | **NO-GO** | Native local schema-6 migration, role restrictions, isolated backup/restore, builds and loopback health. | Apply and verify edited media code on a controlled active build after the user's test, obtain listening-checked media accuracy evidence, authorized host and release approval, HTTPS domain/certificates, production settings and release extension build, Linux/Compose migration/backup/restore and service restart, restricted admin access, second-laptop Facebook and dashboard check. No public service was started. |

The local MariaDB, API and dashboard remain running for the user's manual checks. This record makes no claim that the participant questionnaire is validated, that the live Facebook extension passed, or that the current candidate has independently measured misinformation accuracy.

### New manual test report pending reproduction

The tester subsequently reported multiple errors, especially on video. The running API logged one `/extract/video` HTTP 422 after 83.95 seconds, but its log does not retain the post URL or response detail. No matching new screenshot or exact submitted media has been supplied yet, and the currently open Chrome Facebook page has no SuriPH result. This observation does not identify the failed post or establish a prediction error. The [45-item checklist](research/QUESTIONNAIRE-ACCEPTANCE-20261110.md) retains its existing statuses until the specific URL, exact error/result and same-build replay can be attached.

An extension source fix now gives distinct Tagalog messages for speech/OCR mismatch, an untranscribed middle section and missing audio; it was syntax-checked and passed the product, video-review and result-binding contracts. The installed extension was **not rebuilt or reloaded** while the tester was using Chrome. Defense Demo, Participant Survey and Deployment therefore each remain **NO-GO** for the separate reasons above; no browser item was promoted by this source-only fix.
