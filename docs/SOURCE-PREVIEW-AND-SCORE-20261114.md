# Source preview and model-score clarification — 14 November 2026

## Reproduced case

The Facebook post text supplied for this regression was:

> Nvidia CEO Jensen Huang has called it quits after revelations about two
> extramarital affairs, including one with an alleged Chinese spy. Link to the
> full story in the comments section. | via ANC 24/7

The linked Al Jazeera liveblog URL returned HTTP 200 to the backend reader, but
the page contained a headline, a date line, a video title, and the message
“This live page has now been closed.” It had no bounded article body or
publisher-provided `articleBody`. The article reader therefore correctly
returned `content_status: inaccessible`. Its search title/snippet were
discovery previews only and were not eligible for evidence assessment.

As a result, evidence did not override the classifier. The displayed `100%`
was the model's score for its Misleading class, not a 100% probability that the
claim was false. This example does **not** establish that the claim is false or
that the preview proves every detail; it reproduces an unverified model warning
caused by unavailable full-text evidence.

The later CNN Business liveblog was initially also excluded: the page was about
6.7 MB, while its readable structured liveblog content was inside the first
1 MB. The article reader now extracts that bounded structured content and
recognizes CNN's canonical `www.cnn.com` URL as the same publisher as the
requested `edition.cnn.com` URL. The direct full retrieval path now returns the
CNN article as readable and its full text supports the claim's material details.
That is one publisher, however, so it cannot override the model under the
two-independent-publisher rule.

A separate Facebook image-post check showed an irrelevant DOJ search preview:
the post discussed easing the abortion ban for rape victims, while the result
described a Thai national's drug-import conviction. Retrieval had counted
“Department,” “Justice,” and “DOJ” as three separate overlapping terms even
though they identify the same agency. The relevance filter now canonicalizes
the acronym and full name to one anchor; a specific, claim-matching title is
still required. A regression uses the post caption, image text, and unrelated
preview together and confirms the drug-case link is excluded.

## Changes

- Both result surfaces now call the section **Sources found**, rather than
  implying every returned link is a reliable source.
- The result explanation explicitly says a link or search preview does not
  verify the full claim; only readable article content is assessed.
- The numeric classifier score was removed from the prominent explanation and
  retained inside expandable text-analysis details, with a clear note that it
  is not the probability the claim is false. The two public labels are
  unchanged.
- Regression tests cover the exact Jensen Huang claim: an inaccessible source
  and matching search snippet cannot override the model; one readable article
  that supports the claim is insufficient to override. Additional tests require
  two independent trusted publishers, reject same-publisher aliases and
  near-identical article bodies, and ensure trusted contradictions block a
  support override. Another reader test verifies that a closed liveblog
  headline/video title is not promoted to an article body.

## Limit

This fixes a CNN liveblog extraction and canonical-host mismatch and makes
evidence overrides stricter; it does not fix a model false positive or prove
the claim true or false. Even with one readable supporting publisher, the
result remains a model screening output until a second independent trusted
publisher is available and no trusted contradiction is found. No model
artifact, training data, or classifier threshold was changed.

## Verification

- Backend regression suite: **198 passed**.
- Extension checks: **20 behavior tests**, product contract, and video-review
  contract passed; production build completed with manifest version **1.3.30**.
- Direct CNN fetch through `inspect_related_sources`: one readable source;
  its body was assessed as supporting the full qualified claim, but one source
  did not meet the two-publisher threshold. The final result therefore stayed
  `Potentially Misleading` from the screening model.
- The supplied abortion-ban post and DOJ drug-case preview now produce no
  related-source candidate, while a relevant abortion-ban headline remains
  eligible for retrieval.
- The local API `/ready` endpoint returned ready, but its running Uvicorn
  process was not configured for auto-reload and was left running. Restart the
  API before validating the updated backend through the existing port.
