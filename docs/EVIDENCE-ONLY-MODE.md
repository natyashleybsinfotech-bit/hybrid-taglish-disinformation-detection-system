# Evidence-only mode

The active SuriPH runtime does not load a classifier. Historical model artifacts are retained for reproducibility, but they are not mounted by Compose and no active API or extension path imports the model runtime.

For each request, SuriPH normalizes whitespace while preserving the full supplied text, then queries enabled evidence providers concurrently. Approved-publisher search and Google Fact Check remain independent:

1. A Google ClaimReview record is surfaced as a published rating only when its text-match score is at least `0.70`, at least three informative terms match, and the record supplies both a rating and a safe URL.
2. Approved-publisher search results are shown as related context. Their presence never creates a true/false or misleading/non-misleading verdict.
3. When neither condition is met, SuriPH returns `Unresolved`.
4. Provider failure returns `Evidence providers unavailable` when neither configured provider completes. It does not create a fallback result.

The API returns `classification_performed: false` and `classifier_loaded: false`. It does not return model probability, confidence, class, threshold, linguistic feature vector, or a fabricated citation. A published rating is the named publisher’s finding, not SuriPH’s independent factual conclusion.

This approach cannot determine truth for posts that have not been fact-checked or sufficiently covered by approved publishers. Retrieval relevance can also be imperfect, so users must inspect the linked sources and original post context.
