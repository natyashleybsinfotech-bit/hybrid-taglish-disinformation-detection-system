# Retrieval query and source audit — 15 November 2026

The attached `CODEX_PROMPT_retrieval_fix.txt` was treated as an investigation
request. The active hybrid model, its preprocessing, threshold `0.65`, and the
two public labels were not changed. Search discovery still cannot itself
verify or override a claim.

## Measured query order

Live Serper comparisons on this workstation showed that making the old focused
query the universal first attempt would regress coverage:

| Claim | Original full-query accepted publishers | Old focused-query accepted publishers |
| --- | ---: | ---: |
| Drinking enough water helps prevent dehydration | 1 (CDC) | 1 (CDC) |
| BOC destroys P1.4 billion smuggled vape products | 2 (Philstar, Tribune) | **0** |
| Marcos created National AI Council and adopted AI framework | 6 | 6 |
| ACT Teachers calls for education budget and teacher pay | 2 search hits | 1 search hit |

The old focused BOC query was `customs billion 1.4 illicit vape products`:
it lost the action `destroys`, replaced the source wording `smuggled`, and
separated `P1.4 billion`. For a longer post containing the BOC claim followed
by video/share/follow prose, the old full query and old focused query each
yielded one accepted article. The new focused query is `Bureau of Customs
destroyed P1.4 billion smuggled vape products`; it yielded **two** accepted
publisher URLs, Philstar and Tribune, in the live diagnostic. These are search
candidate counts, not evidence-verdict or accuracy measurements.

After restarting the running API, `/related-sources` on that same long input
returned both **readable** publisher URLs in **4.95 s** without performing
classification. They were correctly marked **related**, because the submitted
text also contained separate video/share prose and an additional statement
that those articles did not establish in full. Better search coverage does not
silently erase parts of a submitted post or manufacture a supported verdict.

The chosen strategy is therefore adaptive:

- Short claims start with the cleaned original wording. If fewer than two
  relevant candidate publishers survive, a different focused query is tried.
- Long/noisy text (over 180 cleaned characters or 28 tokens) starts with a
  compact sentence containing a material action and, where available, a
  quantity. If fewer than two candidates survive, the original wording is
  tried as an alternate.
- The focused query preserves the post's surface words, action, `P1.4 billion`
  style quantities, and name suffixes such as `Jr.`. It removes common social
  prompts and can scan up to 4,000 characters for a later material sentence.
  It is a discovery query, not a rewritten factual claim.

The relevance gate still requires multiple informative term matches, title
alignment and matching material entities/dates/amounts before the trusted
domain check. A source must then have a readable, same-article body; only the
separate evidence gate can use it to change the final label. More candidate
URLs can mean more related or inaccessible cards; the app must label those
honestly. Query results and ranking can change with the provider over time.

## Informative-term and domain audit

`_informative_terms()` and `_ordered_informative_terms()` canonicalize common
forms and remove social/date filler. The old focused builder also removed
material action words and took only the first eight terms, losing later
subjects such as teacher pay. The new builder uses the best material sentence
and up to 14 surface tokens. The relevance gate continues to canonicalize
terms so the search query and relevance assessment play different roles.
Negation and allegation words can aid focused discovery; the evidence assessor
still checks their meaning against the full submitted claim.

Current `TRUSTED_DOMAIN_SUFFIXES` contains **60** entries:

`abc.net.au`, `abcnews.go.com`, `abs-cbn.com`, `afp.com`,
`aljazeera.com`, `andasian.com`, `apnews.com`, `bangkokpost.com`,
`bbc.co.uk`, `bbc.com`, `businessmirror.com.ph`, `bworldonline.com`,
`cbc.ca`, `cbsnews.com`, `cdc.gov`, `channelnewsasia.com`, `cnn.com`,
`cnnphilippines.com`, `comelec.gov.ph`, `doh.gov.ph`, `dw.com`,
`edu.ph`, `euronews.com`, `factcheck.afp.com`, `factcheck.org`,
`france24.com`, `fullfact.org`, `gmanetwork.com`, `gov.ph`,
`indianexpress.com`, `inquirer.net`, `jakartapost.com`,
`leadstories.com`, `manilastandard.net`, `manilatimes.net`,
`mb.com.ph`, `nbcnews.com`, `nhs.uk`, `npr.org`, `nytimes.com`,
`officialgazette.gov.ph`, `pbs.org`, `philstar.com`, `pia.gov.ph`,
`pna.gov.ph`, `politifact.com`, `rappler.com`, `reuters.com`,
`scmp.com`, `snopes.com`, `straitstimes.com`, `sunstar.com.ph`,
`theguardian.com`, `thehindu.com`, `tribune.net.ph`, `un.org`,
`verafiles.org`, `vnexpress.net`, `washingtonpost.com`, `who.int`.

Potential additions for a later **publisher and reader** review are
[PortCalls](https://www.portcalls.com/) (specialist cargo/customs coverage),
[DZRH](https://www.dzrh.com.ph/) (radio/news),
[The POST](https://thepost.net.ph/about/) (education coverage), and
[OneNews.PH](https://www.onenews.ph/about/). None was added merely to make
one example pass. The PortCalls and DZRH sample pages returned `inaccessible`
in the current bounded reader, so allowlisting them would not make them
usable evidence. OneNews describes shared Philstar ownership; counting it as
independent of Philstar would require publisher-group deduplication first.
The existing broad `gov.ph` and `edu.ph` suffixes likewise are discovery
allowances, not automatic official proof. A single direct authority override
remains limited to explicit subject scopes in the evidence gate.

## Diagnostic command

From the project root:

```powershell
.\.venv\Scripts\python.exe backend-api\scripts\diagnose_retrieval.py 'sample claim'
.\.venv\Scripts\python.exe backend-api\scripts\diagnose_retrieval.py --live 'sample claim'
```

The first command prints both queries without a network call. The live command
prints the query order, each result URL, keyword and entity alignment checks,
domain/social filtering, and accepted status. It saves the **raw Serper
responses** plus per-result checks only in ignored `tmp/`, with no API key.
For private text, pipe it through stdin and pass `-` as the claim instead of
putting it in shell history. The measured BOC run is recorded in
`tmp/retrieval-diagnostic-run-20261115.log` and its ignored raw JSON file.

The complete backend suite passed **230 tests**. The original GMA speech
regression and independent classification accuracy evaluation remain separate
release blockers. No participant or public-deployment readiness is inferred
from search candidate counts.
