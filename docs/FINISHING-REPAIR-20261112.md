# Finishing repair — 12 November 2026

## Completed and active

1. **Readable source articles.** The previously inaccessible Philstar vape report and CDC water article were accessible over HTTPS; the reader did not recognize their publisher layouts. The reader now supports bounded WHO, Philstar and CDC body containers, requiring a matching page heading and document/OG title. It continues to exclude related-story blocks, navigation, ads and footer prose. Duplicate bodies or mismatched headings are rejected. Structured metadata and same-publisher redirect safeguards remain in place.
2. **Alternate-source recovery.** If discovered pages cannot be read or fail fetched-body relevance, the API makes at most one focused retry, excludes the failed URLs and inspects at most two replacement candidates. The same logic serves initial screening and source-only lookup. A failed retry preserves explicit unverified status and never triggers another classifier call. Focused domains include Philippine government and named international public-health sources.
3. **Specific short-query matching.** Short source queries must match all informative query terms, rather than only two generic overlaps. Auxiliary terms such as “helps” and “enough” do not substitute for the specific subject. A general drinking-water page cannot pass for a dehydration claim when that subject is absent.
4. **Windows database dependency.** The initial test attempt hit a Windows Application Control block on SQLAlchemy's optional `_collections_cy` extension. SQLAlchemy **2.1.2** was rebuilt using the upstream-supported `DISABLE_SQLALCHEMY_CEXT=1` option and installed as a pure-Python wheel in the project environment. No security policy was changed. The installed module now loads from `_collections_cy.py`. The version and all other dependencies were preserved. The build method is documented by [SQLAlchemy](https://docs.sqlalchemy.org/en/21/intro.html#building-the-cython-extensions). Stop the API before using the reproducible `scripts/install-sqlalchemy-pure.ps1` repair command in a recreated environment.

## Actual verification

- **142 backend tests passed** in the repaired environment, including retry failure/recovery, same-page article selection, observed publisher containers and short-query precision. Log: private `tmp/finishing-backend-20261112.log`.
- `pip check`: no broken requirements.
- Pure-Python wheel contains no `.pyd`, `.dll` or `.so` files. Built wheel SHA-256: `55ef14dadc00c956c84756590cb5cac1b04775cf3ab794c03c35631ed31d8fe1`.
- Saved real HTML from WHO, Philstar and CDC now yields readable article bodies of 7,777, 1,625 and 2,119 characters respectively. Private bounded-layout verification: `tmp/publisher-layouts-20261112.json`.
- After API restart, the live vape source-only request returned the readable Philstar article **“BOC destroys P1.4 billion smuggled vape products”** in **4.51 seconds**.
- The live dehydration source-only request returned a readable CDC article **“About Water and Healthier Drinks”** in **2.02 seconds**.
- Both requests returned HTTP 200 and `classification_performed: false`. A readable source is not automatically assigned a supporting verdict. Live responses: private `tmp/FINISHING-LIVE-20261112.json`.
- MariaDB was started and `/ready` returned true. The same pinned hybrid classifier is active. The extension remains **1.3.17**; these changes are server-side.

## Classifier finding: not corrected by these repairs

A source-supported paired-language diagnostic used six formulations of the same hydration claim. They are engineering probes of wording sensitivity, not six independent facts or a population accuracy estimate. Reference: [CDC water information](https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/).

| Formulation | P(Misleading) | Model label |
| --- | ---: | --- |
| English, short | 0.869707 | Potentially Misleading |
| Filipino | 0.000053 | No Misleading Information Detected |
| Mixed English/Filipino | 0.000805 | No Misleading Information Detected |
| Short mixed wording with CDC attribution | 0.294353 | No Misleading Information Detected |
| English with CDC attribution | 0.221800 | No Misleading Information Detected |
| Longer mixed wording with CDC attribution | 0.000259 | No Misleading Information Detected |

This demonstrates sensitivity to language/wording/context in this case. It does not establish the training cause or an overall language-subgroup error rate. The API has not been changed to translate, pad or attribute user input to force a different prediction. No model, threshold or source-specific exception was introduced. Private exact inputs/results: `tmp/paired-language-diagnostic-20261112.json`.

Correcting generalization requires a validated model/data evaluation and, where justified by those results, retraining. Repeating integration tests or overriding labels based on a credible domain does not establish that repair. The existing inherited-label test metrics and the separate human evaluation remain distinct.

## Speech finding: current limitation remains

Two neutral initial prompts were tested on the first 15.1 seconds of the original GMA audio. Neither fixed “Nag-high” or the unclear allegation phrase; they also degraded a name. Neither prompt was adopted. No caption or desired transcript was supplied to the decoder. Private comparison: `tmp/media-regression/prompt-probe-20261112.json`.

The prior measured turbo/VAD configuration remains active. Full original-video word accuracy has not been established; review is still required. No word-for-word transcript pass or zero-false-positive claim is made.

The source reader and Windows dependency failures are repaired. Classifier generalization and original-video transcription fidelity remain substantive blockers to declaring all requested outputs accurate. This report is not a defense, survey or public-deployment sign-off.
