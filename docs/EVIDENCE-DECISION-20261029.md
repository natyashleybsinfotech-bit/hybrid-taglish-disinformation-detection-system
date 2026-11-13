# SuriPH final decision and evidence review (29 October 2026)

## Current runtime contract

The local API keeps the pinned `full-cleaned-20261023T022416Z` hybrid model, SHA-256
`c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376`,
the saved 775-feature order and scalers, class mapping (`Non-Misleading` = 0,
internal `Misleading` = 1), and threshold `0.4000000000000001`. The public final
labels are only **No Misleading Information Detected** and **Potentially Misleading**. The original
`model_public_label`, `model_score` for the internal Misleading class, threshold,
run ID and artifact hash remain in the API trace. The model score is not the
certainty of an evidence-derived final decision.

Search results discover candidate links. The server fetches each trusted HTTPS
publisher URL without cross-site redirects, limits the response size, and reads
the first main article with its own heading. It displays that article's heading
and a paragraph from the same body. Navigation, ads, other article cards, and
search snippets are excluded. An inaccessible page is shown as a URL without a
purported article title or excerpt and cannot change the verdict.

The current automatic override gate requires at least two independent,
approved publishers with readable full-text articles directly supporting the
complete claim and its material details. A publisher-authored headline can
contribute only when its readable article body corroborates the claim's
informative terms and material details. A headline alone, publisher reputation,
keyword overlap, search snippet, or post link without a readable article is not
proof. Two independent approved publishers must also directly contradict a
claim before evidence can reverse a clear model result. One credible
contradiction blocks a supporting override; any readable trusted support blocks
a contradiction override. Multiple URLs from one publisher and near-identical
syndicated article bodies count only once. Untrusted sources do not count
toward either threshold. If evidence is insufficient, conflicting, or
inaccessible, the system retains one of its two model labels and explicitly
describes the output as unverified. This gate can miss valid evidence and is
not a substitute for human review.

The 14 November 2026 follow-up adds normalized claim matching for price
rollbacks (including “pump prices” and future-week wording) so a readable
publisher article can be recognized as direct support. Negated expectations
remain excluded. This improves the evidence relationship shown to users; it
does not lower the two-independent-publisher override threshold.

The same follow-up moves the Facebook result panel to a viewport-level,
fixed overlay with important host positioning, preventing Facebook feed
containers and page styles from clipping the result. The expanded card also
sets its responsive width and scroll bounds inline with `!important`, then
clears those overrides when closed so the in-post S control returns to compact
size.

The API returns `model_public_label`, `model_score`, `evidence_assessments`,
`evidence_urls`, `final_label`, `final_reason`, and `evidence_adjusted`. An
additive schema-6 `ScreeningDecisions` table records these separately in MariaDB
without saving submitted text or page identity (only a SHA-256 text hash). The
admin Activity page reads `/admin-api/screening-decisions`. Source-only lookup
after a result does not retroactively change that result; rerun the analysis to
apply the evidence policy. A failed database write is reported as
`decision_record_status: unavailable` while a model result remains available.

## Reviewed examples and actual local API results

The tested texts below are reconstructed from the full articles, **not copies of
the user's original Facebook captions**. They therefore cannot reproduce or
prove resolution of the reported Facebook false positives.

| Case | Available source content reviewed | Local API after change |
| --- | --- | --- |
| TV Patrol, Occidental Mindoro, 4 July 2023 | The ABS-CBN video description says a man was invited for clarification, was not yet a suspect, and the rape allegation was qualified as `umano`. The video transcript was unavailable. A full later report says a suspect was arrested on 21 July; that later stage must not be merged into the 4 July claim. | Reconstructed qualified claim: model `No Misleading Information Detected`, score 0.0002222; final `No Misleading Information Detected`; fetched article inaccessible to the local article reader, evidence `unverified`, no override. |
| BOC vape products, 1 October 2026 | Philstar reports destruction of 3,174 boxes valued at ₱1.4 billion in Navotas. A March 2026 Navotas seizure and an October 2023 Valenzuela seizure are different events despite similar amounts. | Reconstructed destruction claim: model `No Misleading Information Detected`, score 0.0075018; final `No Misleading Information Detected`; fetched article inaccessible to the local reader, evidence `unverified`, no override. |

Both local requests recorded a decision trace in MariaDB. Readable full pages were
reviewed separately with the research browser; that review was **not** supplied
to the automatic API during these requests. Where the publisher blocks the
local fetch, the two-label policy retains the model verdict even if a person can
read the article in another tool.

## Software verification and limits

The 94 backend regression tests passed, covering direct support and debunk
fixtures, source conflicts, changed dates/amounts, inaccessible content,
source-only lookup, retrieval failures, and incomplete captions. Extension 1.3.11
contract test, dashboard build, extension build, and isolated HTTPS Facebook
fixture passed; the fixture includes switching to another post while a request
is pending. `/ready` returned model and database available after the additive
MariaDB migration. No logged-in Facebook page, original reported caption, or
independently reviewed end-to-end accuracy sample was tested in this run. The
source parser's strict article layout can mark valid pages inaccessible.
The isolated Chrome popup harness did not register the unpacked service worker;
an Edge retry reached a worker context without the `chrome` API. Popup browser
verification therefore remains open even though the popup builds and its
static product contract passes.

## Manuscript changes required

- Describe the two-label final decision as a hybrid prediction with a narrowly
  gated, full-article evidence override. State that inaccessible, conflicting,
  and merely related sources leave the model prediction unchanged.
- Report the original model score as the internal Misleading-class score, not
  factual certainty or confidence in a source-derived verdict.
- Show model verdict, evidence assessment, final verdict, and changed flag as
  separate fields in diagrams, screenshots, and methodology.
- Report inherited-label model metrics separately from human-reviewed final
  decision accuracy. The latter has not been established.
- Keep the work described as a supervised screening prototype until the frozen
  human evaluation and live Facebook rehearsal are complete. Do not claim this
  document revised a submitted manuscript or produced new evaluation findings.
