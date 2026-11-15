# Media acquisition repairs and classifier diagnosis — 14 November 2026

## Applied changes (extension 1.3.38)

- Direct Facebook downloads accept a complete HTTP 206 range and can assemble contiguous fragments when the remote object has a stable ETag or Last-Modified validator. Every byte range and its size must match; changed, gapped, unknown-length, or unvalidated fragmented objects fall back safely. The existing HTTPS origin allowlist, 50 MiB cap, and 30-second direct-download deadline remain enforced. No cookie export, new extension permission, yt-dlp integration, or third-party downloader was added.
- Download responses are read with a byte limit rather than buffering arbitrarily large bodies first. Download resources are aborted/closed after the acquisition attempt.
- The Facebook loading state distinguishes direct download, backend speech/frame processing, and real-time capture. Capture shows selected-playback elapsed seconds, not an invented recognition percentage. Direct streaming success on actual Facebook is not established by controlled HTTP-range tests.
- Playback capture stops when the request becomes stale, the video is seeked, the selected source changes, or its audio track ends. A skipped-to-the-end clip is not submitted as a complete recording. Playback rate, loop and autoplay settings are restored.
- No classifier weights, threshold, saved linguistic features, lexicons, ASR model, database credentials, or source-decision rules were changed.

## Fresh classifier evidence

Offline diagnostic: `backend-api/scripts/diagnose_feature_blocks.py`. Separate processes used the correct pinned environments for each saved profile. Each profile processed six original synthetic statements and their repeated/padded variants. This is a feature intervention, not a truth-labelled evaluation or an accuracy result.

For the hydration statement:

| Saved profile | P(Misleading), unchanged input | Context logit contribution | Linguistic logit contribution | Diagnostic P with linguistic block at saved training mean |
| --- | ---: | ---: | ---: | ---: |
| 20261011T235112Z | 0.9999736995 | +11.4879679 | −1.7124776 | 0.9999952548 |
| full-cleaned-20261023T022416Z | 0.1295805317 | +3.1174847 | −1.2142001 | 0.3339279498 |

The seven ratios do not explain the legacy hydration false-positive symptom: removing their numeric contribution makes the extreme score higher. The candidate also assigns 0.9984305567 to the synthetic sentence “Read the full article before sharing. Check the original source.” and 0.0064866723 to the synthetic giveaway statement in this diagnostic. Neither model's generalization is repaired by this work. Padding changes both embeddings and ratios and cannot isolate a causal ratio effect.

Counterfactual block replacement is artificial and can itself be out of distribution. It is never used in production. Detailed originals, saved feature values, per-feature contributions, and padding/repetition comparisons are in the ignored local reports:

- `tmp/diagnostic-20261114/default-feature-blocks.json`
- `tmp/diagnostic-20261114/candidate-feature-blocks.json`

The separate pre-existing 40-item short-statement probe is preserved. Its intended labels were not independently source-verified by this investigation; its percentages must not be represented as measured Facebook factual accuracy.

## Real speech replay

The supplied GMA clip (`facebook-2202426650624013.mp4`, SHA-256 `f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a`) was passed through the current local extraction pipeline without classification. Extraction completed in 105.426 seconds on this run, including cold model/OCR setup. It still produced the opening wording “Nag-high” and an unclear allegation phrase. No complete listening-verified reference is available, so neither transcript accuracy nor WER is claimed. The replay is in `tmp/diagnostic-20261114/gma-current-extraction.json`.

Direct download can remove the full-playback wait when the remote media is accessible. It does not correct recognition errors or guarantee a particular transcription time. The ASR and classifier limitations remain material release blockers.

## Verification

- 200 backend tests passed with developer `.env` loading disabled and a test-only SQLite path. One existing missing-provider-key test depended on local `SERPER_ENABLED`; it now explicitly enables retrieval while testing the empty-key path. Production defaults were not changed.
- 35 extension behavior/contract tests passed, including contiguous validated ranges, wrong validators/gaps, over-limit downloads, seek-to-end, stale-request cancellation and lost audio tracks. The product contract also passed.
- Extension production build passed. Existing installed Chrome was observed at 1.3.36 and reloaded to 1.3.38. This version observation alone is not a completed live-media rehearsal.
- In actual logged-in Chrome, opening the original standalone GMA Reel loaded its player but did not expose an in-page SuriPH control. The feed-post selector path must not be claimed as verified support for this standalone Reel layout. No live Reel transcript or result was confirmed through that page.
- Local `/ready` returned true with MariaDB available and the candidate profile already running on CPU. On-disk `.env.local` names the legacy profile; the running process selects the candidate. This investigation did not restart or change the serving model. `START_HERE.md` now explicitly sets the candidate profile and artifact directory in the startup shell so its interpreter does not accidentally try loading the incompatible legacy bundle. Private credentials and persistent settings were not edited.
- Initial API tests stalled before executing requests because restricted local socket creation was unavailable. After granting local-network test access, tests ran normally. No Windows security control was changed.

## Remaining work before readiness can be claimed

1. Correct/replace the saved classifier through the user's separately controlled retraining process, then evaluate source-verified examples independent of fitting/selection. Preserve the two labels; do not disguise model errors using arbitrary overrides or thresholds.
2. Establish acceptable recognition on natural Filipino/Taglish speech with listening-checked references, including names, negation, amounts and allegations. Review remains required while the known GMA failure persists.
3. Complete an installed Chrome/Facebook text/image/video rehearsal on the release build, followed by target-host deployment checks. Software test passes do not satisfy these accuracy and deployment gates.

The system is not certified error-free, survey-ready, or publicly deployment-ready by these changes. No training, public deployment, Git commit or push was performed in this repair pass.
