# ASEAN caption replay and regression fixes — 16 November 2026

The exact caption supplied by the user was replayed against the local API. Before the fixes, the final result was Potentially Misleading. After the fixes, live retrieval plus Gemini returned **No Misleading Information Detected** with the matching Manila Times photo-caption passage. This is one verified integration case, not a measured real-world accuracy result.

## Causes and changes

1. The article reader could download the Manila Times AMP photo story but could not read its displayed photo caption. Added a publisher-layout parser bounded to the article body, matching displayed/metadata title and excluding outside captions. Also enabled captions inside the generic primary-article parser so the extraction improvement is not limited to one layout.
2. Gemini treated the terminal reporter credit `| via Jonas Sulit, Abante` as an event actor. The prompt now distinguishes newsroom attribution from event assertions. The deterministic person guard strips only a narrowly delimited capitalized terminal credit; actual event actors, dates, quantities and locations remain checked. The cache prompt version was incremented.
3. A single matching original photo report was blocked by the ordinary two-publisher rule. Added a narrow `direct_publisher_photo_report` rule: the server must retrieve the article, match its same-page NewsArticle photo metadata and displayed headline, find a visible named photo credit and publication date, obtain a full-claim supporting Gemini assessment with literal quotation and matching event date/anchors, and find no credible contradiction. Page provenance means same-page consistency, not forensic authentication of the photo. Other single-publisher articles retain the existing sufficiency rules. This is an explicit evidence-policy change, not a model threshold adjustment or post-specific label override.
4. Source-specific English/Tagalog explanations are now visible. Provider failures and rate limits are distinguished from successfully assessed unrelated sources. An unreadable source does not claim that the entire final decision retained the model when another source supplied the decision.

## Evidence and checks

- `ASEAN_REPLAY.json`: actual live response, Gemini assessed, `direct_publisher_photo_report`, source used for decision and literal matching passage.
- `ASEAN_BEFORE_PHOTO_RULE.json`: intermediate response where extraction worked but the ordinary two-publisher rule still blocked it.
- Real source: https://www.manilatimes.net/2026/11/14/photos/express-lanes/2470121/amp
- Backend: **249 tests passed**, including photo boundary exclusions, title mismatch, duplicate article bodies, missing provenance, wrong date, conflicting evidence, reporter attribution, and original safeguards.
- Extension: **37 behavior tests passed**, product contract passed, production build passed. Version **1.3.41**.
- Three live-provider controlled fixtures passed again using the revised prompt: supporting paraphrase, explicit contradiction, incomplete support. These are declared synthetic fixtures, not real-news accuracy measurements.
- Twelve isolated-browser UI layouts passed. The actual ASEAN API response was supplied to the render check. These are not installed-extension Facebook end-to-end observations.

## Use and limits

Reload SuriPH 1.3.41 in `chrome://extensions`, refresh Facebook, keep source checking selected and perform a fresh check. The original classifier, its threshold, MariaDB records and model artifacts were not changed. No retraining was performed.

The fixes reduce repeat failures for the covered patterns. They do not guarantee correct decisions for every post, every publisher layout, inaccessible articles, OCR or speech transcription. Image/video extraction was not changed by this particular fix. Original unverified model fallback behavior remains when evidence is insufficient.

Secret-free pre-fix files are in project `runtime/asean-reader-backup-20261116T013052/`. Restore individual files deliberately, preserving unrelated edits, and rebuild/restart if rollback is needed. The original private key was not included in this backup.
