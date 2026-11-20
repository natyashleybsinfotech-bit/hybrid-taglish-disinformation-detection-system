# Local semantic trial activation — 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

The comparison candidate is now enabled **locally** as `SURI_EVIDENCE_POLICY=semantic_single_source_trial`. It is blocked by production configuration validation. The deployment/survey is not certified ready by this trial.

The default policy in code remains `strict`; the local private setting selects the trial. Two public labels remain. A server-validated full-claim supporting or contradicting trusted source can determine the result if there is no eligible credible conflict. Missing, unavailable, invalid or insufficient evidence retains the original model as unverified, as previously requested by the user. A related article alone cannot change the result.

The Gemini reader selects server-owned passage IDs rather than generating quotes. The server supplies original source text and validates the selected IDs against the correct source. Original classifier profile, hash and threshold 0.65 remain unchanged. No training was performed.

257 backend tests passed, including trial conflict and changed-detail checks, and a test proving production configuration rejects this local-only policy.

## Actual local API smoke checks

| Case | Expected | Actual | Verified evidence used | Passed |
|---|---|---|---|---|
| antibiotics_negated | Misleading | Misleading | verified_evidence | True |
| music_supported | Non-Misleading | Non-Misleading | verified_evidence | True |
| music_tl | Non-Misleading | Non-Misleading | verified_evidence | True |
| music_negated | Misleading | Misleading | verified_evidence | True |

These four checks use source-backed paraphrases and deliberately negated controls. They are not a replay of the unavailable original Mariah Facebook caption, not a representative accuracy measurement, and not installed-extension Facebook end-to-end testing. The nine-case comparison recorded 8/9 correct for the alternative in its final run, with a remaining provider failure/model fallback. All earlier failures remain recorded in the comparison folders.

## Rollback

Set `SURI_EVIDENCE_POLICY=strict` in the private backend `.env.local` and restart the original API using `scripts/start-original-model.ps1`. No database reset or model replacement is needed. Backups of changed code are under `runtime/semantic-policy-backup-20261116T021520/` and `runtime/passage-reader-backup-20261116T020959/`. Credentials were not included in those backups.

For the next local check, refresh Facebook and perform a fresh analysis with reliable-source checking enabled. The existing extension 1.3.41 supports the returned evidence fields; no new extension build was required for this backend-only change. Unavailability, source-reading failures, OCR/transcript quality, and independent real-post evaluation remain open readiness concerns.
