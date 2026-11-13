# SuriPH revised questionnaire acceptance record

This checklist follows the 45 numbered statements in **SuriPH System Evaluation Questionnaire Revised.docx**, supplied by the study team on 10 November 2026. Both AFP and BSIT forms use the same 45 rating statements through separate survey links. The response choices are **5 Strongly agree, 4 Agree, 3 Moderately Agree, 2 Disagree, 1 Strongly disagree**, plus a separate **N/A: not tested or observed**. Survey collection and participant ratings remain outside SuriPH. No rating has been prefilled.

The status here describes the **system rehearsal**, not a participant's answer. **Passed** means the stated behavior was observed on the current local build in the named environment. A controlled Edge fixture or direct API call is identified as such; it does not establish that the installed extension works on live Facebook in Google Chrome. **Failed** means an observed sample did not meet the statement. **Not demonstrated** means a required action or observation is still missing. The exact build is recorded in [the build manifest](../REHEARSAL-BUILD-20261110.json).

Evidence keys: [API and Windows rehearsal](../DEFENSE-REHEARSAL-20261110.md) (`R`); [Facebook fixture](../FACEBOOK-MODAL-VERIFICATION.json) (`F`); [administrator browser](../ADMIN-BROWSER-VERIFICATION.json) (`A`); [isolated database restore](../MARIADB-VERIFICATION.json) (`D`); [original GMA reel retest](ITEM-1.4-GMA-RETEST-20261110.md) (`G`); [prior video validation](../VIDEO-EXTRACTION-VALIDATION-20261103.md) (`V`); [12 November extraction repair](../EXTRACTION-REPAIR-20261112.md) (`X`); [13 November mismatch review and current software checks](../VIDEO-MISMATCH-REVIEW-20261113.md) (`M`). The 12 November backend suite passed 155 tests; extension result/capture contracts passed 14. The 13 November backend suite passed 186 tests; 20 extension behavior tests and the product/video contracts passed. These software checks do not replace the evaluator's experience.

**14 November follow-up:** [Current local readiness](../STATUS-20261114.md) records 200 backend tests, 21 extension behavior tests, an isolated Edge modal close/date regression, and a live two-source BOC article check. These do not change item 1.4 from **Failed** or turn pending signed-in Facebook observations into passes.

## 1 Functional Suitability

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 1.1 | Submit a Taglish Facebook post and see one of the two English labels. | Two-label output passed a controlled fixture; no current installed Chrome/Facebook result supplied. | Not demonstrated | F, R |
| 1.2 | Compare displayed analyzed text with the exact selected post text. | Exact binding passed the controlled fixture and extension contracts; live selected-post comparison is pending. | Not demonstrated | F, R |
| 1.3 | Read a sample image and compare its visible words with OCR. | A real local image OCR and a two-image HTTP request passed; the installed Chrome/Facebook image comparison is pending. | Not demonstrated | R, X |
| 1.4 | Listen to the sample news video and compare all material words with the transcript. | The same GMA reel replayed offline and through the running API (HTTP 200, review preview in 96.011 s). Speech and frame text were separated, but speech still says “Nag-high” and contains an unclear money allegation. A 13 November fix now stops classification when speech and frame text disagree, but does not repair the transcript; matched-but-wrong text remains possible. No complete listening-checked reference exists. | Failed | G, V, X, M |
| 1.5 | Open a source and check the specific people, event, date, location and quantities. | A 14 November direct API test of the BOC destruction claim returned two readable articles with matching amount and box count. The evaluator has not yet checked source cards against the same post in the installed Chrome extension. | Not demonstrated | R, [14 November status](../STATUS-20261114.md) |

## 2 Performance Efficiency

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 2.1 | Time a complete text check and judge whether the wait is acceptable. | Two local API checks returned the same result; participant-facing Chrome timing and acceptance target were not measured. | Not demonstrated | R |
| 2.2 | Time an image check and judge the wait. | No current installed Chrome image timing. | Not demonstrated | R |
| 2.3 | Time a video check and judge the wait. | Offline GMA extraction took 81.042 s alone and 110.325 s while API work also ran; the English clip took 112.480 s after language selection; a separate 62-second eGov extraction took 165.848 s in the latest retest. Participant-facing Chrome timing and acceptability remain unmeasured. | Not demonstrated | G, V, X, M |
| 2.4 | Time source lookup during a real check. | No current complete Chrome lookup timing and participant acceptance observation. | Not demonstrated | R |
| 2.5 | Observe simultaneous requests against a stated target. | Three short-text requests returned HTTP 200 in 203 ms total; a separate longer-payload run returned three HTTP 200 responses in 4.90 s. These workloads are not directly comparable and do not measure saturation or target-server capacity; see the 13 November update below. | Not demonstrated | R |

## 3 Compatibility

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 3.1 | Use the installed extension in the supported laptop Google Chrome setup. | Current fixture ran in isolated Edge; live Google Chrome installation remains to be observed. | Not demonstrated | F |
| 3.2 | Open SuriPH from an assigned Facebook post. | Chooser opened in a controlled Facebook-origin fixture; actual post view is pending. | Not demonstrated | F |
| 3.3 | Confirm the backend result belongs to the submitted Facebook post. | Post-switch and stale-response fixture checks passed; actual Facebook result binding is pending. | Not demonstrated | F |
| 3.4 | See caption, image OCR, speech and frame text under the correct input type. | Video review and binding contracts passed; separate speech/frame OCR and one multi-image request were verified in software. Installed Chrome media output remains pending. | Not demonstrated | F, R, X |
| 3.5 | Open a returned source link in a usable browser tab. | Links were rendered in the fixture; no current live source opening was observed. | Not demonstrated | F |

## 4 Interaction Capability

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 4.1 | Start analysis from the selected post. | Controlled chooser passed; participant ease on actual Facebook is unobserved. | Not demonstrated | F |
| 4.2 | Read instructions at each step. | Copy exists in the current build; no evaluator comprehension observation. | Not demonstrated | F |
| 4.3 | Find the prediction label quickly. | Banner exists in the fixture; no evaluator observation. | Not demonstrated | F |
| 4.4 | Explain what the model score represents. | UI says it is the Misleading class score, not probability the claim is false; evaluator comprehension is unobserved. | Not demonstrated | F |
| 4.5 | Expand linguistic features and explain them. | Expandable features are present; evaluator comprehension is unobserved. | Not demonstrated | F |

## 5 Reliability

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 5.1 | Repeat exactly the same input with unchanged settings. | Two live API calls returned Potentially Misleading and the identical model score 0.41724348392335725. This is API reproducibility, not factual correctness. | Passed | R |
| 5.2 | Submit empty input and read the error. | Direct request to the running API returned HTTP 422 with a nonempty-text validation detail; the evaluator-facing Chrome error has not been observed. | Not demonstrated | G, R |
| 5.3 | Observe source-provider failure message. | Failure branch passed backend tests; no current UI interruption demonstration. | Not demonstrated | R |
| 5.4 | Recover from a deliberate service interruption and check again. | The running API was kept available for the user's live test, so no current interruption was performed. | Not demonstrated | R |
| 5.5 | Inspect restored test records after a database restore. | An isolated MariaDB 11.4.13 instance completed migration 1–6, restart, logical gzip restore and record comparison. The working database was untouched. | Passed | D |

## 6 Security

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 6.1 | Open protected dashboard page before and after sign-in. | Isolated Edge connected to the real dashboard/API: admin login, cookie reload, logout and expired session passed. | Passed | A |
| 6.2 | Use a restricted viewer account on an admin-only operation. | Real viewer login succeeded; protected candidate endpoint returned HTTP 403. | Passed | R |
| 6.3 | Request a protected record without authorization. | The same endpoint returned HTTP 401 without a session. | Passed | R |
| 6.4 | Review exactly what content will be sent before checking. | Text/video review UI and exact-input contracts passed; actual Chrome user observation is pending. | Not demonstrated | F, R |
| 6.5 | See a secure browser connection to the deployed service. | No deployed HTTPS origin or second-laptop browser session is available. | Not demonstrated | R |

## 7 Maintainability

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 7.1 | Follow the setup guide on the demonstrated machine. | Existing portable MariaDB started, migration had no pending versions, and the pinned API reached `/ready: true`. | Passed | R |
| 7.2 | Use the troubleshooting guide for a demonstrated error. | Windows DLL error is documented in R; no evaluator walkthrough of a recovery guide occurred. | Not demonstrated | R |
| 7.3 | Locate the component in a diagnostic failure record. | Code Integrity events 3033/3077 identify SQLAlchemy `_util_cy.cp313-win_amd64.pyd`; the subsequent full suite passed without a policy change. | Passed | R |
| 7.4 | Identify the exact release version used in the demo. | Build manifest records extension 1.3.15, local bundle hashes, model run/hash and dirty working-tree state. | Passed | [Build manifest](../REHEARSAL-BUILD-20261110.json) |
| 7.5 | Follow a demonstrated rollback to an earlier version. | Rollback instructions exist; no current rollback operation was demonstrated. | Not demonstrated | R |

## 8 Flexibility

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 8.1 | Check more than one supported Facebook post type in one extension. | Text/image/video contracts passed; live Chrome multi-type flow is pending. | Not demonstrated | F, R |
| 8.2 | Toggle English and Tagalog explanations, keeping labels in English. | Controlled fixture passed switch stability; current installed Chrome observation is pending. | Not demonstrated | F |
| 8.3 | Use the result panel at different Chrome window sizes. | Isolated fixture and earlier narrow views passed; current installed Chrome resizing is pending. | Not demonstrated | F |
| 8.4 | Repeat on a second supported Chrome setup. | No second laptop or second Chrome setup was used. | Not demonstrated | R |
| 8.5 | Change the server address using documented configuration. | Local API origin remains loopback; no configured-origin change was demonstrated. | Not demonstrated | R |

## 9 Safety

| Item | Evaluator action or view | Current build observation | Status | Evidence |
| --- | --- | --- | --- | --- |
| 9.1 | Read the screening reminder in the result. | Controlled fixture displays the academic disclaimer; participant interpretation is pending. | Not demonstrated | F |
| 9.2 | Identify a model prediction without verified evidence. | Current API returned `verification_status: not_verified`; fixture and product contract show the bilingual unverified notice. | Passed | F, R |
| 9.3 | See the reminder to check the original before sharing. | Current controlled modal includes the reminder and original-post link. | Passed | F |
| 9.4 | Distinguish related reading from direct support or contradiction. | The UI has relationship text, but the known vape case remains only related; no live source comparison was demonstrated. | Not demonstrated | F, R |
| 9.5 | Identify the exact parts of a post that were analyzed. | Separate speech/frame OCR and explicit exclusion of unmatched frame text passed the software checks; actual Chrome media observation remains pending. | Not demonstrated | F, R, X |

**Current count: 10 passed, 1 failed, 34 not demonstrated.** These statuses must be updated from the user's actual Chrome/Facebook observations and the evaluator session records before either survey link is released. The original questionnaire ratings and participant judgments must remain blank until each person completes the test independently.

### Pending manual Facebook incident, 10 November

The tester reported multiple new errors, especially for video. No new screenshot or post URL has yet been supplied in the workspace, and the currently open Facebook tab shows no SuriPH result. The running API log contains one `/extract/video` HTTP 422 request lasting **83.95 seconds** (request ID `9d9f82b116be44458bb37e97fdc24b6a`), but the log does not retain its post URL, uploaded media, or response detail. It cannot be assigned to a questionnaire item or labeled as the GMA reel without the matching browser observation. Keep the existing statuses unchanged; append the original post URL, exact error/result and retest evidence when supplied. Do not interpret HTTP 422 alone as a wrong prediction: an extraction failure is expected to produce no label.

### Current rehearsal update, 13 November

- The local API and dashboard returned HTTP 200; `/ready` returned ready. The backend suite passed **185 tests**, extension behavior tests and product contract passed, the extension built, and dashboard lint/build passed. These checks do not replace evaluator observation.
- The selected video for the recording is the synthetic English clip, for a functional pipeline demonstration only. It does not resolve the GMA Tagalog transcript errors or establish Taglish/news-video accuracy; item 1.4 remains failed for the GMA sample.
- The three-request smoke run is a latency observation only. The production limiter's configured capacity is two in-flight screening requests; its backend test verifies that excess screening requests receive a bounded 503 response and that service capacity recovers. Neither the unit test nor the light local smoke establishes a target-server load result or that overload behavior meets the evaluator's exact criterion. Keep item 2.5 not demonstrated until that criterion is confirmed and the target environment is tested.
- A separate longer-input local run recorded three concurrent HTTP 200 responses in 4.90 seconds total ([measured report](../LIVE-STACK-PERFORMANCE.json)); the 203 ms run used short inputs. Do not compare the two as if they were the same workload or use either as a latency promise.
- The installed Google Chrome/Facebook flow was not observed, so the Chrome- and live-post-dependent items remain unchanged. The local-only setup also does not meet the HTTPS and second-Chrome requirements for items 6.5 and 8.4.
- No participant ratings were collected or inferred. Keep survey answers blank until actual participants complete the approved tasks.
