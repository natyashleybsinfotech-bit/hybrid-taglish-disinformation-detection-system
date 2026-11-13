# Existing-system fixes — 12 November 2026

No classifier training, model replacement, threshold change, dataset edit or ASR model replacement was performed. A separate unexecuted experiment package was prepared earlier, then stopped at the user's direction; it is not part of the running application.

## Fixed

- **Late source responses:** clearing a popup result invalidates its pending lookup. A delayed reply cannot recreate a cleared result, attach the previous post's links to a newer result, or unlock a newer request. Source-only refresh preserves the decision and any already assessed supporting/contradicting article.
- **Actual checked material:** the popup derives its material description from the returned extraction. Speech-only, frame-only and image-only inputs no longer claim that a caption was included.
- **Incomplete video OCR:** frame-reader failures are reported separately from frames with no readable text. Speech remains available for explicit review; incomplete frame extraction is returned as partial, with a visible English/Tagalog notice before confirmation and in the popup's extracted-text display. No missing text is invented.

## Verification

- 143 backend tests passed. Private log: `tmp/system-software-fixes-20261112.log`.
- 11 extension result-binding, delayed-response, actual-material, incomplete-frame and video-review checks passed.
- Product contract passed; extension **1.3.18** built successfully in `chrome-extension/dist`.
- Rebuilt unpacked extension passed the isolated Microsoft Edge Facebook fixture: selected-post boundaries, stale requests, exact eight-part order, source-only lookup, language switching and one bottom reminder. This fixture is not a test of a logged-in Facebook account.

These software checks do not establish zero false positives or word-for-word speech accuracy. Existing classifier and speech-recognition limitations remain; the software does not mask them by substituting captions, fabricated words, unrelated links or forced labels. No public deployment or new factual accuracy claim was made.
