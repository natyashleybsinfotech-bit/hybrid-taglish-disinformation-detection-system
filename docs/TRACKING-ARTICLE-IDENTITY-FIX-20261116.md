# Tracking-parameter article identity fix — 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

The screenshot's GMA article was downloaded and inspected directly. Before the fix, both clean and tracked URLs returned HTTP 200 with the same 336,479-byte article HTML. The clean URL was readable, but a URL with `fbclid` was incorrectly marked inaccessible: the structured-article same-page identity check compared the tracking query against the publisher's clean metadata URL.

The reader now removes only known attribution parameters (`fbclid`, `utm_*`, `gclid`, `dclid`, `msclkid`, `igshid`, `mc_cid`, `mc_eid`) before fetching and identity comparison. Meaningful query keys, raw encoded values, article IDs and same-publisher redirect restrictions are preserved. Source URLs passed to Gemini also omit these attribution parameters; public source binding remains attached to the original requested URL. This is a generic URL handling fix, not a rice-post-specific label override.

## Validation

- **259 backend tests passed**. New coverage includes raw/encoded Facebook tracking keys, UTM keys, same-page structured article identity and the rejection of a different meaningful article-ID query.
- Both the clean and tracked real GMA URL now return readable article content.
- Three actual API checks with the tracked link passed: source-backed English claim → Non-Misleading; source-backed Taglish claim → Non-Misleading; deliberately contradicted control → Misleading. All three used server-owned original passages and the active local semantic trial.
- Actual response files and source diagnostics are saved in this folder, including `LIVE_TRACKED_LINK_RESULTS.json`.

Source: https://www.gmanetwork.com/news/topstories/metro/1009579/no-sale-of-p20-kilo-rice-in-metro-manila-on-nov-16-to-18/story/

## Boundaries and rollback

The three texts are reference-backed test inputs, not the exact original Facebook caption; that caption could not be recovered from the current browser state. These checks do not establish real-world accuracy or installed-extension end-to-end success. The full original post may contain additional assertions requiring separate evidence. No model training, classifier threshold change, database reset or new extension build was performed.

The backend has been restarted with this fix. Refresh Facebook and perform a fresh check with reliable-source checking enabled. The local semantic trial remains active and blocked for production.

Secret-free original files are backed up at project `runtime/tracking-url-backup-20261116T022655/`. Restoring changed files requires restarting the API; it does not require replacing the model or resetting MariaDB.
