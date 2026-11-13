# SuriPH system fixes on 11 November 2026

## Applied changes

- Image and video endpoints ignore caption fields from older clients. Image classification uses extracted image text. Video classification uses the extracted media text after the existing explicit review. The multi-image extension path also excludes captions.
- Video acquisition returns the original speech and original frame text for review when word overlap is low. Tagalog speech and an English on-screen quotation can therefore reach the review screen. This change does not establish transcription accuracy or cause automatic classification. The preview carries a specific discrepancy warning in English and Tagalog.
- Source inspection reapplies the existing relevance checks to fetched article content. A matching search snippet cannot retain an unrelated fetched article. When every readable candidate is rejected, the response reports no results.
- Philippine currency amounts are compared across equivalent forms such as P1.4B and 1,400 million pesos. A candidate mentioning a different amount alone is rejected as a relevance mismatch. This comparison is a retrieval filter, not a factual verdict.
- The extension was rebuilt as version 1.3.16. The local API was restarted after testing. The pinned hybrid classifier and its threshold remain the active model configuration.

## Verification

- 125 backend tests passed in the existing pinned environment. Log is private at `tmp/backend-final-20261111.log`.
- Six extension result-binding and video-review tests passed. The extension build and product-contract checks passed.
- The restarted live API processed the existing synthetic image and excluded an explicitly supplied unrelated caption from its analyzed text.
- The same original GMA video, SHA-256 `f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a`, returned HTTP 200 with an extraction-review preview in 82.72 seconds. Its discrepancy status was `review_required`. No video classification was requested.
- A live source request initially returned an inaccessible article URL describing a P1-billion seizure for a claim about P1.4 billion. After the final currency filter and API restart, the same query returned `no_results` and excluded that URL. No directly supporting replacement article was established by this check.
- Final `/ready` returned true with MariaDB and the pinned model available. Private live responses are in `tmp/live-fix-20261111.json`.

## Remaining failures and verification boundaries

The GMA transcript still contains material wording errors including “Nag-high” and a distorted allegation phrase. Item 1.4 remains failed for transcription accuracy. Returning a review preview fixes the cross-language rejection but does not repair these words. No human-verified WER is claimed.

The known classifier generalization and factual false-positive complaints remain unresolved. The current fixes address media input selection and source relevance. Empty source results leave the model prediction unverified, following the user's selected behavior.

Actual installed Chrome interaction was attempted. Computer Use stopped because it could not verify the current browser URL sufficiently for its access checks. No installed-extension Facebook pass is claimed. Reload SuriPH from `chrome://extensions`, confirm 1.3.16, and refresh Facebook to load the rebuilt content script.

Defense, participant-survey and deployment sign-off remain pending. Existing participant ratings and the failed original-video accuracy status have not been replaced with fabricated passes. No public deployment was performed. The existing working tree includes earlier unrelated changes and has not been committed by this work.
