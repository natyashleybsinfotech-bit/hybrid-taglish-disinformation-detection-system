# Extraction repair record — 12 November 2026

## What changed

- Facebook caption collection now keeps text owned by the selected post and excludes captions inside independently authored comments. This is a post-binding change, not a change to the hybrid classifier.
- A post with two to four images now sends one `/analyze/images` request. Each image is OCR-read, the per-image text is retained for tracing, identical complete OCR text is deduplicated before one classification, and an unreadable image fails the whole request without a partial prediction. The result stays `input_type=image` for exact post binding.
- Video speech and sampled-frame OCR remain separate. A frame overlay is included in the classifier input only when its words can be tied conservatively to the speech; otherwise it remains visible for review with an explicit exclusion notice. Bottom-center subtitles can be retained when their words match speech. Isolated broadcast logos, clocks, ticker bands and generic end cards are excluded from frame OCR.
- The active speech recognizer remains faster-whisper turbo on CPU INT8. For long clips, three separated audio windows must all strongly identify English before language auto detection is used for the full transcript; mixed or uncertain clips retain the Filipino hint. If a Filipino-hinted transcript fails the existing quality gate, one auto-detection retry is accepted only when it produces clean detected-English speech. No caption, model-generated rewrite or translation is substituted. Failed quality checks produce no prediction.

## Real media observations

| Media | Before | After | Limit |
| --- | --- | --- | --- |
| Original 69.1 s GMA Filipino reel, SHA-256 `f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a` | Existing transcript included “Nag-high” and an unclear money allegation. An earlier extraction either failed the speech/frame lexical gate or required review. | The same clip was replayed offline in 81.042 s. The final replay, while API work also ran, took 110.325 s. Speech remained the same 822 characters; OCR fell from 211 to 199 characters after removing an isolated `GMA NETWORK` logo. The English quotation and imperfect frame text remain visible for review, while only speech is eligible for classification. No classification was submitted. | Material spoken words remain wrong; questionnaire 1.4 remains **Failed**. No listening-checked complete reference exists, so no WER is claimed. |
| Publicly accessible 62.3 s eGov reel, SHA-256 `c31a3f67d82695f71e7c23522de2477974d4a60f935ff954244c71834d8c2cb2` | Filipino hint produced a repeated “Powered by” hallucination at the end, and the quality gate correctly blocked classification. The measured full ASR passes were 124.437 s under the Filipino hint and 72.368 s under auto detection. | A clean detected-English transcript was recovered by a quality-gated retry in 203.787 s. With three-window language detection, the same 619-character transcript and 387-character OCR were produced in **112.480 s**; unmatched screen OCR was excluded from the classifier input. | 112.480 s is still slow and this clip is English, so it does not validate Filipino speech accuracy. This accessible reel is a separate sample; it is not asserted to be the user's unrecorded recent Facebook failure. |
| Real local image OCR sample | One image returned `READ THE COMPLETE REPORT BEFORE SHARING.` | Two copies posted to the live API returned HTTP 200 in 12.002 s with two separately traced OCR entries and one image classification. After deduplication and API restart, the same request returned HTTP 200 in **8.880 s** with two trace entries and only one copy of the text analyzed. | The returned model label was not independently reviewed as factual truth. This sample does not establish OCR accuracy on arbitrary Facebook images. |

Private replay details are in `tmp/media-regression/gma-extraction-20261112.json`, `tmp/media-regression/gma-extraction-final-20261112.json`, `tmp/media-regression/egov-extraction-20261112.json`, `tmp/media-regression/egov-extraction-optimized-20261112.json`, `tmp/multi-image-live-20261112.json`, and `tmp/multi-image-live-final-20261112.json`. The exact GMA transcript is unchanged between the two final replays; its material word errors were not corrected by these pipeline safeguards.

The **running API** also accepted the original GMA video at `/extract/video`: HTTP 200 in **96.011 s**. The response required review, contained the same 822-character Filipino speech and 199-character frame OCR, identified `tl` as the speech language, marked frame OCR excluded, and contained **no prediction field**. The live response is private at `tmp/gma-api-preview-final-20261112.json`.

### Original GMA speech hypothesis, before and after

The **before and after text is identical**; this is the recognizer output, not a checked transcript of what was actually said:

> Nag-high ng reklamong libel at cyber libel si Davao City First District Representative Paolo Pulong Duterte, kaugnay ng mga pahayag ng dating polis na si Rodolfo Gracioso ng paghati naman nun ng pera. Bukod kay Gracioso, inereklamo rin ni Duterte sa Office of the City Prosecutor sa Davao City Hall, si National Bureau of Investigation Director Melvin Matibag. Isinama rin sa reklamo ang ilang executives at personalidad ng GMA Network. Ayon kay Duterte, walang katotohanan ng mga pahayag. Sa isang pahayag, sinabi ni Matibag na hindi pa niya nakukuha ang kopya ng reklamo pero karapatan na niya ito ni Duterte at mainam ng idulog niya ito sa korte. Sa isang pahayag, sinabi ng GMA Network na hindi pa nito natatanggap ang kopya ng reklamo. Pag-aaralan daw nila ito at magbibigay ng komento kapag natanggap na ang reklamo.

## Software checks and readiness boundary

The backend suite passed **155 tests** in the isolated Windows environment; extension result/capture contracts passed **14 tests**. The extension build passed. The first isolated Edge fixture attempt hit a Windows Application Control block on Node's child PowerShell process (`spawnSync ... powershell.exe EPERM`). A local HTTPS fixture certificate was then created directly in the approved PowerShell shell and supplied to the script; no security setting was weakened. The rebuilt extension passed the fresh isolated Edge Facebook fixture, including selected-post caption ownership, nested-comment exclusion, post switching and result order. The saved fixture result is `docs/FACEBOOK-MODAL-VERIFICATION.json`. This is still not a signed-in Facebook test.

The local API was restarted from the updated source and `/ready` returned `true` with MariaDB available and the active hybrid model ready. The extension bundle is **1.3.21**. The installed extension still needs to be reloaded from `chrome-extension/dist` and its Facebook tab refreshed before a manual Chrome result can be attributed to this build. Neither the model artifact nor its threshold changed.

### Separate readiness decisions

- **Defense Demo — not signed off for news video.** Text and image paths have software evidence, and the video preview fails safely, but the GMA speech still has material errors. The installed Chrome/Facebook flow is unobserved on this build.
- **Participant Survey — hold video-fidelity claim.** Questionnaire 1.4 stays Failed. Participant ratings and real Facebook observations must be collected independently; no rating is prefilled.
- **Deployment — local only.** The loopback API and MariaDB are ready. Public HTTPS, hosting and a second machine have not been verified.
