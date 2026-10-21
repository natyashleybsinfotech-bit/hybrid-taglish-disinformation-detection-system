# SuriPH participant session — draft for institutional review

This is a research prototype, not a fact-checking authority. Participation is voluntary.
Researchers must complete the study contact, approval reference, session dates and
retention arrangements below before recruitment. This draft is not an approved consent form.

- Study team/contact: **TO BE COMPLETED BY THE RESEARCH TEAM**
- Institution/adviser and approval reference: **TO BE COMPLETED**
- Session date/location and withdrawal contact: **TO BE COMPLETED**
- Planned duration: approximately 20–30 minutes; verify in the pilot.

## Eligibility and groups

The paper's general-user population is eligible fourth-year BSIT students from the
selected class block, at least 18 years old, able to work with English, Filipino or
Taglish content. Invite the eligible block using the approved total-enumeration procedure;
record eligible, invited and completed counts without claiming public representativeness.
AFP IT evaluators are separately authorized, purposively selected technical personnel.
Do not combine the two groups' response summaries. Do not use protected institutional
systems or records for demonstration without separate authorization.

## Consent information to read before tasks

You may decline, skip a question, or stop without penalty or effect on grades or access.
No account or name is required to use the extension. Use only public or researcher-written
examples. Do not paste private messages, personal identifiers, confidential or sensitive data.

Text and selected media are sent to the study server for processing. Temporary uploaded
media are removed when processing finishes. Ordinary screening does **not** save the
input, page URL/title, prediction or feature values. Request logs contain route, status and
duration, not bodies, raw text or credentials; the server/network may process connection
information. The extension no longer stores previous input or results on disk.

Related-source search is a separate, unchecked choice. When selected, up to 500 cleaned
characters are sent as a search query to Serper and Google Fact Check. The choice persists
on the device and also applies to the in-page S button until switched off. Provider
processing is outside the study's database. Opening a retrieved link contacts that
publisher. Serper links and published fact-check ratings are independent context; neither
establishes that the classifier is correct or changes its prediction. [Serper](https://serper.dev/)
supplies related search results, and the [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search)
supplies matching published reviews when available.

Saving for research is optional and unchecked. If selected, the server saves a random
record ID, consent version, input type, prediction, model identity, seven measurements,
expiry time and optional usefulness rating. A second unchecked choice permits saving
the text and returned links. Without it, those fields are not saved. Records are not
automatically added to training data; retraining is disabled.

The default server retention period is 30 days, enforced by daily scheduled cleanup.
The receipt shows the expiry. Before recruitment, the facilitator must verify the actual
configured period and functioning cleanup. Private backups default to seven days; live
withdrawal does not edit an existing immutable backup. Restrict backup access, expire it
on schedule and reapply withdrawal requests before a restore is opened to users.
Exports and external survey files must follow the same approved deletion schedule.

The extension stores only research receipts locally, without the submitted text. Use
**Research receipts and feedback → Delete this saved record** to withdraw a saved
record. Keep the receipt ID for the study team if the extension is removed or a backup is
restored. Researchers must maintain any necessary withdrawal requests separately with
restricted access. The CSV export excludes text, links, dates and withdrawal tokens but
contains random record IDs: call it **pseudonymous**, not guaranteed anonymous.

Possible inconveniences include slow processing, unavailable sources, extraction mistakes
and incorrect predictions. This is not emergency, medical, legal or financial advice.
Do not make consequential decisions from the model score.

## Installation for a supervised study

1. The facilitator starts the verified local/API service and confirms `/ready` is ready.
2. Open `chrome://extensions`, turn on Developer mode, select **Load unpacked**, and
   choose the prepared `chrome-extension/dist` directory. This is not Web Store publication.
3. Review permissions: active tab, local settings/receipts, configured API origin, supported
   social pages and their media origins. No API key is embedded in the extension.
4. Open the SuriPH popup. Use a new browser study profile without personal accounts where
   possible. Reload the extension and target page after a new build.
5. At session end withdraw test records as appropriate, remove the extension and delete
   research-profile receipts. Removing the extension alone does not delete server records.

## Guided tasks

These are synthetic interaction scenarios, not ground-truth test items. No expected
classification label is supplied. The model may misclassify any scenario.

| ID | Task | Observe/record |
| --- | --- | --- |
| T1 | Paste “Basahin muna ang buong balita bago mag-share. Check the original source.” Leave saving/search unchecked; analyze. | Can you find the predicted label and explain the score without calling it truth? |
| T2 | Change the text to “BREAKING!!! Share agad!!! Totoo ba ito?” | Previous result clears; seven measurements belong to the new input. |
| T3 | Expand all seven measurements. Explain one ratio using its definition. | No invented risk level or feature-importance claim. |
| T4 | On a supported public page, select one public caption, then use selected text. Compare the extracted text before analyzing. | Extraction scope, missing text and unsupported-page behavior. |
| T5 | Select related-source lookup using non-sensitive text. Open one returned source if available. | Publisher/link/date if supplied; no-results/unavailable is not evidence of truth. |
| T6 | Submit spaces only; then let the facilitator demonstrate a disconnected backend. | Clear validation/service error, no fabricated prediction. |
| T7 | Optionally opt in to saving a synthetic result without its text, rate usefulness, then withdraw it. | Separate consent choices, receipt, deletion confirmation; no penalty for skipping. |
| T8 | Optional supervised media demonstration after release checks: use the approved synthetic image and short video, inspect extracted text. | OCR/transcription errors are distinct from classifier errors. No media-accuracy claim. |

AFP-only tasks: inspect readiness/model identity; try viewer access to a protected write;
review migration, rollback, backup/restore and performance evidence; observe two accepted
concurrent requests and a busy response; identify what remains unverified on the target server.

Answer the appropriate draft questionnaire after tasks. Provide comments without names,
private content or classified/institutional details. Do not report invented participant scores.
