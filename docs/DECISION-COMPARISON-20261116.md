# SuriPH decision-flow comparison — 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

This is a nine-case diagnostic smoke comparison, not independent human-adjudicated real-world accuracy. Reference labels were fixed from public CDC, GMA and Manila Times pages. Three deliberately negated controls are constructed test claims, not claimed real Facebook posts. Only the ASEAN input is the exact caption supplied by the user. The Mariah inputs are source-backed paraphrases; the original failed caption is still unavailable.

The existing 24-case human evaluation batch was audited: 0/24 cases had adjudicated evidence-backed labels. It was not represented as completed evaluation.

All three completed runs used the same frozen case manifest: `8bb47588df12f60eed6edaa066884e47c3397de7fab0251901cdd2ab01967cb9`. The runner sends an explicit reference URL through `context.visible_links`, and actual publisher content is fetched by the API. Both policies receive the identical response for each case. This is more favorable than discovery from an unlinked Facebook post and must not be described as unassisted Facebook performance.

## Policies

- Original: the pinned original classifier alone.
- Current: original classifier plus the existing scoped-primary, original-photo-report or two-independent-publisher gate.
- Candidate: use one eligible full-claim, server-validated supporting or contradicting trusted article if there is no eligible contradiction/conflict. Otherwise retain the original model as unverified. The candidate is computed offline and was not enabled in production. It does not introduce a third public label.

## All completed runs

| Run | Original correct | Current correct | Candidate correct | Current FP / FN | Candidate FP / FN |
|---|---:|---:|---:|---:|---:|
| decision_comparison_source_linked_20261116 | 3/9 | 6/9 | 7/9 | 2 / 1 | 2 / 0 |
| decision_comparison_source_linked_20261116_after_fix | 3/9 | 6/9 | 6/9 | 3 / 0 | 3 / 0 |
| decision_comparison_source_linked_20261116_passage_ids | 3/9 | 6/9 | 8/9 | 2 / 1 | 0 / 1 |

Repeated runs are debugging retests on the same known cases, not independent replication or a held-out estimate. Failed provider or extraction stages are retained, not discarded. Software fixes and network variability both affect the retests.

## Final run details

| Case | Reference | Current | Candidate | Reader status |
|---|---|---|---|---|
| water_en | Non-Misleading | Non-Misleading | Non-Misleading | assessed |
| water_tl | Non-Misleading | Non-Misleading | Non-Misleading | assessed |
| water_negated | Misleading | Misleading | Misleading | assessed |
| antibiotics_supported | Non-Misleading | Non-Misleading | Non-Misleading | no_readable_sources |
| antibiotics_negated | Misleading | Non-Misleading | Non-Misleading | unavailable |
| music_supported | Non-Misleading | Misleading | Non-Misleading | assessed |
| music_tl | Non-Misleading | Misleading | Non-Misleading | assessed |
| music_negated | Misleading | Misleading | Misleading | assessed |
| asean_original | Non-Misleading | Non-Misleading | Non-Misleading | assessed |

Reader status counts: `{"assessed": 7, "no_readable_sources": 1, "unavailable": 1}`.

## Concrete fixes applied

1. Merge slash/no-slash URL aliases only when they have the same fetched body. Differing article bodies remain visible so corrections or contradictions are not discarded.
2. CDC public-health scope now includes antibiotic/virus/bacteria guidance. It remains ineligible to verify unrelated entertainment claims.
3. Gemini now selects server-owned passage IDs instead of writing quotations. Unknown, duplicated or cross-source IDs and generated quote fields are rejected. The server supplies the original article passage for display. This fixes the observed `quote_not_in_body` failure without accepting fabricated quotations.
4. Invalid-reader responses return fixed validation categories, never raw provider errors or secrets.

254 backend tests passed, including source-ID and passage checks, invented quote rejection, URL-alias/conflicting-body regression, material-detail validation, and the existing API and media contracts. No training or classifier artifact changes were made.

## Boundaries

No claim of survey/deployment readiness follows from nine selected cases. Current source sufficiency can still retain an incorrect model result even when one article supports a claim. The candidate cannot fix unavailable providers, unreadable articles, missing retrieval, or wrongly extracted media. Video speech accuracy and installed Chrome/Facebook end-to-end behavior were not verified by this diagnostic.

At comparison time the candidate was computed offline. It was subsequently enabled as a reversible local-only trial after 257 tests; see LOCAL_TRIAL_ACTIVATION.md and ACTIVATED_LOCAL_STATUS.json. It remains blocked for production and has not passed independent real-post evaluation. The prior discovery-only partial run was stopped when a harness field mismatch was found; it remains separately stored and is excluded from this source-linked comparison.

## Source references

- https://www.cdc.gov/antibiotic-use/communication-resources/virus-or-bacteria.html
- https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/index.html
- https://www.gmanetwork.com/entertainment/showbiznews/mariah-deborah-releases-official-music-video-for-viral-hit-na-para-bang/141183/
- https://www.manilatimes.net/2026/11/14/photos/express-lanes/2470121/amp
