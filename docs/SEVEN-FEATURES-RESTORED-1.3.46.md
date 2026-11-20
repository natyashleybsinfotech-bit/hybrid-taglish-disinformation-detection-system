# Seven linguistic features restored — SuriPH 1.3.46

Restored all seven real measurements in the expandable analysis details in both the popup and the Facebook in-page result. Values are computed locally from the exact normalized analyzed_text: code-switching ratio, Filipino-particle frequency, punctuation intensity, capitalization ratio, repeated-character ratio, emotional-word frequency and urgency cues. Original bilingual names and definitions are retained.

The standalone measurer reuses the original measurement formula and saved tokenizer/lexicons. It verifies the tokenizer checksum and uses the same Tagalog/English language detector settings, without constructing the contextual encoder or Logistic Regression classifier. Token-language lookup is bounded in RAM; complete submitted texts are not cached by this component. No training or new remote request is needed for these values.

Measurements describe writing style; they are not feature importance, factual evidence, or the AI-reported confidence score. Current classifier, evidence decisions, audio trial and score behavior are unchanged. If measurement resources are unavailable, the API explicitly reports unavailable and the UI shows that state instead of fabricating zeros.

Verification:
- 283 backend tests passed, including real saved-tokenizer measurements, hand-counted punctuation/capitalization/repetition ratios, particle denominators, whitespace normalization, and the live-mode contract returning seven features without old classifier inference.
- 40 extension behavior tests passed and extension production build succeeded.
- Live API returned seven values; independently measured values matched the exact analyzed_text. The old model score remained null and current AI-reported score remained separate. Raw proof: workspace outputs/seven_features_20261116/live-result.json.
- Twelve component renders passed in English/narrow Tagalog. Renderer asserts each returned feature name/value/definition appears in the result markup. Screenshot inspected: docs/verification/ui/popup-result-en.png.
- Final isolated Facebook modal rehearsal passed on 1.3.46, including opening the details, seven unique feature names and finite ratios. An initial harness assertion attempted to read an extension-isolated JS property from the page context; it was corrected to inspect public DOM values. No application failure was involved in that harness issue. This is an isolated Edge fixture, not a current signed-in Chrome/Facebook test.

Use: reload SuriPH 1.3.46 in chrome://extensions, refresh Facebook, make a new check and expand How the text was analyzed. Old saved results are not retroactively supplied with measurements. The updated local API remains running.

No database changes or model artifact changes. Secret-free pre-change UI/API backup: runtime/linguistic-display-backup-20261116. Existing video accuracy and full survey validation boundaries remain as previously documented.
