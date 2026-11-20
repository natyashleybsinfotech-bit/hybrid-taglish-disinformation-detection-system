# Current source snapshot — 20 November 2026

This record supersedes earlier runtime-policy and cloud-provider descriptions. See [the removal and verification record](GEMINI-REMOVAL-20261120.md) for the change and remaining limits.

## Active local models

- The primary classifier remains **partially fine-tuned multilingual DistilBERT + seven linguistic features + Logistic Regression**, profile `suriph-finetune-6a35c6d4a2a0`, saved threshold **0.85**. Its architecture, training code, model artifacts and decision threshold were not changed or retrained by this migration.
- Evidence reading follows one local path: literal assertion checks, material-detail checks, then a bounded multilingual NLI fallback using `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, revision `8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c`. NLI compares article passage (premise) with claim (hypothesis); it does not establish facts independently.
- The NLI snapshot is prepared explicitly with `backend-api/scripts/prepare_local_nli.py`. Runtime loading uses local files only; there are no Gemini API imports, calls or config entries in the active backend. Old exploratory commits and dated reports remain in Git history.
- Both direct-download bytes and playback-capture uploads use the same `process_video` -> `_transcribe_local` -> local faster-whisper path: **turbo, CPU INT8, Filipino hint, actual transcription**. OCR and speech decoding run sequentially on CPU. Missing model files do not trigger request-time downloads.
- The UI has exactly two successful screening labels: **Potentially Misleading** and **No Misleading Information Detected**. No readable or sufficient evidence retains the real primary classifier prediction; technical failures do not generate a substitute prediction. Original model score and all seven linguistic measurements remain visible in analysis details.
- Public source search still sends its query to Serper and reads public publisher websites when requested. Local model inference does not make the entire retrieval system offline.

## Evidence safeguards and calibration

The reader only uses actual readable article passages. Search snippets and headlines alone are not proof. Person/name, quantity, amount, place, date and timing checks still constrain evidence; syndicated copies do not count as independent publishers. The configured source-count/authority policy is preserved, including its explicit local-trial status. Conflicting or insufficient evidence leaves the original binary prediction unverified.

The 0.80 NLI placeholders were not adopted. A fixed set of **108 authored synthetic semantic pairs** covers English, Tagalog and Taglish: 72 calibration pairs and 36 scenario-disjoint audit pairs. The selected acceptance thresholds are entailment **0.998** and contradiction **0.999**. They are model relation-score cutoffs, not factual-accuracy or user confidence scores. The audit accepted 6 correct support/contradiction relations out of 24 such relations, rejected the other 18 to related, and correctly left 12 unrelated pairs as related. There were no wrong accepted relations in this small audit, but coverage was low. These results do not establish performance on real Facebook posts. See [calibration details](LOCAL-NLI-CALIBRATION-20261120.md).

## Video acquisition and limitations

Direct access to Facebook streams is not always available. Keep the extension's existing direct-download attempt, then caption-only / caption-and-video choice and normal-speed complete playback capture. Unclear speech may use a complete informative caption with explicit provenance in Text checked. Missing engines, decoding failures and service failures are not silently replaced by captions. Transcript/frame mismatch still requires review; matching caption and video does not make a claim true.

Local CPU transcription can be slower than the removed cloud path. Earlier cloud latency measurements are historical and do not describe this version. [Video choice](VIDEO-CAPTION-CHOICE-20261120.md) and [processing history](VIDEO-PROCESSING-20261120.md) remain available with superseding notes.

## Verification and known classifier weakness

The closing removal record lists the final backend/extension test counts, real local media rehearsals, startup check and the unchanged-classifier bias probe. Passing regression tests is not proof of factual accuracy or installed-Facebook compatibility. Historical 96.32% candidate accuracy on 598 inherited-label records is not measured real-world Facebook accuracy. Neutral/short text false positives remain a separate problem.

The next training step is documented in [the short-text repair plan](SHORT-TEXT-RETRAIN-PLAN-20261120.md); no retraining is authorized or performed here. This snapshot does not certify survey, defense or public-deployment readiness.

## Review entry points

- API and readiness policy: `backend-api/src/app.py`
- Primary model identity/inference: `backend-api/src/model_runtime.py`, `backend-api/src/model_profiles.json`
- Retrieval: `backend-api/src/retrieval.py`, `backend-api/src/article_reader.py`
- Local evidence path: `backend-api/src/evidence_decision.py`, `backend-api/src/local_nli.py`, `backend-api/src/local_nli_thresholds.json`
- Shared speech/OCR pipeline: `backend-api/src/media_processing.py`
- Reader calibration: `backend-api/scripts/calibrate_local_nli.py`, `backend-api/tests/fixtures/local_nli_pairs.jsonl`
- User result binding/UI: `chrome-extension/src/result_binding.js`, `chrome-extension/src/content.js`, `chrome-extension/src/Popup.jsx`
- Startup: `scripts/start-finetuned-trial.ps1`; `-RawModelOnly` retains the pure-model diagnostic path.

Private API keys, passwords, databases, respondent records, datasets, model weights, backups and generated builds stay outside Git. A fresh checkout needs the verified classifier artifacts and prepared local NLI/Whisper/OCR models before it can run these paths.
