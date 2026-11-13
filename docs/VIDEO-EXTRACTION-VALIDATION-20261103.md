# SuriPH video extraction validation — 2026-11-03

## Decision and scope

Video screening now has two stages: `/extract/video` returns the exact ASR transcript and filtered frame OCR **without a prediction**; `/analyze/confirmed-video` runs the unchanged hybrid classifier only after the user confirms those exact strings. An extraction failure, a rejected preview, an expired or altered review token, or the old direct `/analyze/video` route produces no prediction. The extension shows speech and on-screen text separately in English or Tagalog before confirmation. The final prediction labels remain **No Misleading Information Detected** and **Potentially Misleading**.

The active classification artifact remains `model_4_full_dataset_CANDIDATE.joblib`, 775 feature dimensions, and decision threshold 0.40. The ASR engine is now CPU CTranslate2 `faster-whisper` with multilingual `turbo`, INT8 inference, `task="transcribe"`, and Filipino (`tl`) speech hint. The hint preserved both Filipino and English portions in the checked Taglish and mostly English examples. It is not an instruction to translate. It can be overridden through `SURI_WHISPER_ENGINE`, `SURI_WHISPER_MODEL`, and `SURI_WHISPER_LANGUAGE_HINT` for controlled evaluation.

## Verified root causes and safeguards

1. The former running ASR was multilingual Whisper `tiny`; its original-reel transcript included “live bill” and corrupted names. Default temperature fallback made repeated transcripts vary. Deterministic decoding and a stronger ASR model reduce this failure, but do not guarantee exact names or allegations.
2. OCR originally treated ticker, logos, clocks, and isolated numbers as story text. Frame OCR now uses time-stamped bounding boxes and excludes top logos, bottom ticker/clock regions, end cards, and low-confidence fragments. A headline must substantially agree with speech before the two become one classification input.
3. The old segment diagnostic accepted a different accident report with misheard location and malformed phrases. The live API returned HTTP 200 and a prediction, demonstrating that acoustic confidence and OCR agreement alone cannot certify material wording. The required user review now prevents **automatic** classification of such transcripts. A user who incorrectly confirms bad text can still obtain a bad result; this is a remaining human-review limitation.
4. The same downloaded Facebook reel was replayed through isolated browser capture. Original/captured audio duration was 69.100/69.120 s; aligned overlap 69.100 s; waveform correlation 0.9995. A replay starting mid-video and rewinding also correlated 0.9995. This verifies that isolated capture path, not the missing historical in-Facebook capture. The extension now starts recording before playback, rewinds, and requires an audio track.

## Separate Filipino/Taglish ASR benchmark

The [FilSwitch dataset](https://huggingface.co/datasets/qwerttyuiiop/FilSwitch) provides manually validated, speaker-disjoint Filipino-English read-news test utterances. Before inference, we selected every 53rd row of its 804-row test metadata in UUID order, starting at row 0: 16 distinct clips and 309 reference words. Files, manifest, raw hypotheses, and the dataset evaluator are private under `tmp/media-regression/`. WER below uses the dataset's own number-aware normalization; the timings exclude model load, FFmpeg decode, OCR, and classification. This is an ASR sample, not an independently reviewed SuriPH misinformation evaluation.

| ASR setting | Normalized WER | Total ASR time for 16 clips | Observation |
| --- | ---: | ---: | --- |
| OpenAI Whisper `tiny`, auto language | 51.48% | 20.76 s | Detected Japanese, Hebrew, or Swahili on three Filipino/Taglish clips. |
| OpenAI Whisper `small`, Filipino hint | 22.30% | 210.63 s | Faster, but a separate accident report remained substantially garbled. |
| OpenAI Whisper `turbo`, Filipino hint | 13.44% | 705.87 s | Better words but impractical CPU latency on the original reel. |
| CTranslate2 `turbo` INT8, Filipino hint | 13.44% | 375.37 s | Same normalized WER on this sample with lower CPU time. |

Numbers written as words versus digits were scored with FilSwitch's `eval_script.py`; ordinary punctuation and acronym formatting can still affect individual WERs. The optimized model still misheard some proper names in the independent clips. No model was retrained and no classifier metric was changed.

## Actual news-video checks

- Original GMA reel: <https://www.facebook.com/reel/2202426650624013>, 69.10 s, SHA-256 `F0FC902A97F4BC71A378ADB87F40745DACFD18EC2A375E44B5E8F5CFFA7E133A`. The exact old `tiny` transcript is in `tmp/media-regression/asr-deterministic-final.json`; it begins “Nagha inag reklamun live bill at cyber libel...” and truncates the later GMA response. The exact optimized-turbo transcript and segment diagnostics are in `tmp/media-regression/asr-faster-turbo-original.json`; it begins “Nag-high ng reklamong libel at cyber libel si Davao City 1st District Representative Paolo Pulong Duterte...” and includes the later GMA response. The user confirmed the key phrase **cyber libel**. The new transcript still distorts the opening verb, allegation about money, and some response wording. No full listening-checked reference exists, so exact-reel WER and material-error totals cannot be honestly calculated. With optimized ASR and the OCR gate, the pre-review API returned **HTTP 422 in 112.79 s**. The final `/extract/video` route independently returned **HTTP 422 in 111.74 s**, with no prediction.
- Original-reel OCR: 1/23/46/65 s frames had 11/9/10/7 raw detections. The 23 and 46 s story lower-third was retained; GMA marks, the 24 Oras logo, clock, unrelated weather/entertainment ticker, and end-card text were excluded. The retained OCR still has `AI CYBERLIBEL` where the frame appears to read `AT CYBERLIBEL`; this is an unresolved OCR word error. It was not silently rewritten.
- Separate ICC report, 70.72 s: tested with both original and optimized ASR as a different-topic clip. Its retained headline and speech disagreed; no claim of a correct transcript is made without a listening reference.
- Separate motorcycle/dump-truck report, 61.51 s: the old direct optimized-ASR API returned **HTTP 200 in 105.90 s** despite “Tanhai,” malformed phrases, and “Outro,” then produced a Non-Misleading prediction. This is the observed reason for mandatory review. After the review change, `/extract/video` returned **HTTP 200 in 113.48 s**, with 910 speech characters, 84 OCR characters, a review token, and **no final label**. Altering the text during confirmation and using the old direct endpoint both returned **HTTP 409**. The bad transcript was not confirmed or classified in the revised flow.

The 16 FilSwitch utterances have dataset-provided human-validated references; the three GMA videos do **not** have full listening-checked references in this workspace. Their outputs are coverage and failure-case checks, not measured news-video WER. The original user-supplied “cyber libel” phrase is one confirmed material phrase, not a complete reference.

## Verification and remaining limits

- Backend API and media tests: **56 passed**, including failed extraction, review-before-classification, exact-text binding, one-time token, and direct-route rejection.
- Extension binding/product/video-review contract tests: **7 passed**; production extension build passed.
- Isolated Edge Facebook fixture passed for chooser, post binding, stale-response handling, bilingual output, and other existing modal behavior. It is **not** a real-account Facebook verification of the newly installed extension.
- The local `/health` reported `faster-whisper`/`turbo`/`tl`; `/ready` reported MariaDB available and the unchanged hybrid classifier ready. The API is bound to `127.0.0.1:8000`.
- The review token lasts 15 minutes and is consumed once. An API restart invalidates it. The user must re-extract if the preview expires, the selected post changes, or text does not match.
- Automated quality gates remain imperfect; proper nouns and allegations may be wrong with apparently good ASR scores. The review step makes that limitation visible and blocks automatic classification, but correctness depends on a careful comparison with the original video.
- Speech and OCR remain separate on screen. A sampled frame budget cannot cover every on-screen claim. A video containing unsupported language or inaccessible audio should fail with an extraction error. A 178.05-second timing-only test used concatenated Filipino news audio and a blank frame. `/extract/video` finished in **211.13 s** and returned HTTP 422 for an incomplete middle speech section; this is a latency check, not an ASR accuracy result or a claim that all 3-minute videos finish within that time. The earlier stream-copy montage had 184.66 s of decoded audio despite a 179 s container duration and was correctly rejected as over-limit; it was not used for timing.

## Manuscript updates required

Describe video classification as **human-confirmed extraction followed by the existing hybrid text classifier**. Document the ASR engine/model/hint and OCR filters independently of the 775-dimensional classification model. Report the FilSwitch WER and latency as a small, speaker-disjoint **read-speech ASR** benchmark; do not combine it with the classifier's 598-sample held-out accuracy or claim improved misinformation accuracy. State that failed or rejected video extractions receive no label, while completed screenings retain only the two established prediction labels. Report actual news-video examples and the absence of full listening references as limitations, including the risk that a user could confirm a wrong transcript.
