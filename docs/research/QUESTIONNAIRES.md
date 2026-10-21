# Draft evaluation instruments — not validated

Basis: revised paper PDF printed pages 87–93 (PDF pages 92–98), separate BSIT and AFP
groups, observable quality dimensions and five-point agreement scale. The paper names
six core dimensions; its broader methodology also mentions compatibility and flexibility.
Those two appear only as optional technical modules below. No unobservable dimension is
inserted merely to fill a standard. ISO/IEC 25010:2023 is a quality model, not a validated
questionnaire or certification of this prototype. [Official ISO description](https://www.iso.org/standard/78176.html).

Adviser, methodology expert and statistician review are required before use. Pilot for
wording, task relevance and completion time. Do not claim these items are validated,
invent reliability coefficients, or use the removed inter-rater agreement statistic.

Response scale: **1 Strongly disagree; 2 Disagree; 3 Neutral; 4 Agree; 5 Strongly agree**.
Also offer **N/O — not observed or not applicable** and **Skip**. Neither is zero or neutral.
Record task exposure. Do not ask participants to infer technical properties they did not see.
Keep groups separate in analysis; report item counts and missingness. Interpretation ranges,
aggregation and any reliability analysis require the approved statistical plan.

## BSIT general-user form

Record random session code, instrument version `draft-2026-10-19`, group `BSIT`, consent
confirmation and tasks attempted. Do not request name, student number, address or account.

| ID | ISO dimension | Task | Proposed item |
| --- | --- | --- | --- |
| B01 | Functional suitability | T1 | I could submit the text I intended to analyze. |
| B02 | Functional suitability | T4 | The extension let me inspect the selected text before analysis. |
| B03 | Functional suitability | T5 | I could open a returned source when one was available. |
| B04 | Performance efficiency | T1–T2 | The response time was acceptable for the tasks I performed. |
| B05 | Performance efficiency | T8 or N/O | The media-processing wait was acceptable for the demonstrated sample. |
| B06 | Interaction capability | T1 | I could distinguish the prediction from a verified factual conclusion. |
| B07 | Interaction capability | T1 | The explanation helped me understand what the model score means. |
| B08 | Interaction capability | T3 | The text-signal definitions were understandable. |
| B09 | Interaction capability | T2 | It was clear which input the displayed result belonged to. |
| B10 | Interaction capability | T6 | Error messages told me a useful next action. |
| B11 | Reliability | T6 | The interface made it clear when a result could not be produced. |
| B12 | Reliability | T5 | The interface distinguished missing related sources from a completed prediction. |
| B13 | Security (observable privacy) | T7 | I could tell what would be saved before choosing to save it. |
| B14 | Security (observable privacy) | T7 or N/O | I could tell that survey responses are collected separately and are not displayed in the extension or admin dashboard. |

Do not ask BSIT users to rate server hardening or code maintainability. Comments:
“Which step was confusing?”, “What would you change?”, “Did anything make the result
seem more certain than it was?” Leave answers blank until actual participation.

## AFP IT technical-evaluator form

Record random session code, group `AFP`, tasks/evidence inspected, and only approved
role/experience categories. Do not combine this population with the BSIT block count.

| ID | ISO dimension | Evidence/task | Proposed item |
| --- | --- | --- | --- |
| A01 | Functional suitability | API/extension demonstration | The demonstrated input-to-result flow fulfilled its documented purpose. |
| A02 | Functional suitability | Model parity report | The documented implementation reproduces the selected hybrid pipeline. |
| A03 | Functional suitability | T5 | Source retrieval is clearly separated from classification. |
| A04 | Performance efficiency | Local and target-server measurements | The provided measurements allow assessment of latency under the tested workload. |
| A05 | Performance efficiency | Concurrent-request demonstration | The service clearly handles requests beyond its configured concurrent capacity. |
| A06 | Interaction capability | T1–T3 | The interface distinguishes measurements, predictions and factual evidence. |
| A07 | Interaction capability | T6 | Failure states communicate an appropriate recovery action. |
| A08 | Reliability | Model-failure/readiness tests | The system refuses predictions when the required model is unavailable. |
| A09 | Reliability | MariaDB restart/restore evidence | The demonstrated persistence and restoration procedure recovered the test records. |
| A10 | Reliability | Retrieval outage test | A retrieval outage does not change the classifier output. |
| A11 | Security | Viewer and unauthenticated tests | Protected administrative operations reject unauthorized requests. |
| A12 | Security | Survey-separation demonstration | The extension and admin dashboard expose no participant response, receipt, feedback or export controls. |
| A13 | Security | Deployment review | Runtime database privileges and secret isolation are appropriate for the documented single-server design. |
| A14 | Maintainability | START_HERE and operations guide | The setup and diagnostic instructions are reproducible for the documented environment. |
| A15 | Maintainability | Versioned migration and tests | The migration and test records make changes traceable. |
| A16 | Maintainability | Update/rollback rehearsal | The documented update and rollback process can be followed without overwriting participant data. |
| A17 (optional) | Compatibility | Actual Chrome/OS test matrix | The extension works with the browser and pages that I tested. |
| A18 (optional) | Flexibility | Actual configuration demonstration | The API origin and server configuration can be changed using the documented procedure. |

No safety certification or untested portability claim is implied. Technical comments:
observed defect, reproduction steps, severity, evidence inspected, and suggested correction.

## Expert instrument-review form

For each item record: reviewer code, item ID, relevance (retain/revise/remove), clarity
(clear/revise), whether the task exposes the property, proposed wording, and rationale.
Check double-barrelled wording, leading assumptions, technical terms, missing N/O choices,
translation needs, population fit, privacy and institutional consent language. Record
review date/version and actual review outcome; do not prefill approval.

## Blank response format

Use long-format CSV with these columns:

```text
session_code,group,instrument_version,item_id,rating,response_status,tasks_observed,comment
```

`session_code`: random code, not student/employee ID. `group`: BSIT or AFP.
`rating`: integer 1–5 only when answered; otherwise blank.
`response_status`: answered, not_observed, or skipped.
`tasks_observed`: approved task IDs; `comment`: optional, no personal data.
Keep signed/recorded consent separately from answers and randomize session codes.
No example participant rows are supplied because no responses have been collected.
Use `scripts/validate_survey.py` to validate and produce a sanitized CSV copy; the
separate in-app usefulness export is **not** this questionnaire or a validated scale.
