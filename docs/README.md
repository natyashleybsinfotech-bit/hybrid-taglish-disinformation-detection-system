# Documentation index

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

**Latest implementation:** [20 November local NLI/Whisper migration](CURRENT-SOURCE-20261120.md), [removal and verification record](GEMINI-REMOVAL-20261120.md), [NLI calibration](LOCAL-NLI-CALIBRATION-20261120.md), and [short-text repair plan](SHORT-TEXT-RETRAIN-PLAN-20261120.md).

**Historical local status:** [14 November source-preview and score clarification](SOURCE-PREVIEW-AND-SCORE-20261114.md), [13 November video mismatch review](VIDEO-MISMATCH-REVIEW-20261113.md), [12 November extraction repair](EXTRACTION-REPAIR-20261112.md), [10 November defense rehearsal](DEFENSE-REHEARSAL-20261110.md), [revised 45-item questionnaire acceptance record](research/QUESTIONNAIRE-ACCEPTANCE-20261110.md), and [rehearsal build manifest](REHEARSAL-BUILD-20261110.json). Earlier dated readiness and survey drafts are historical where they differ.

| Need | Start here |
| --- | --- |
| Current status, local startup and manuscript corrections | [October 29 readiness](CURRENT-READINESS-20261029.md), [START_HERE](../START_HERE.md) |
| Historical release checks and remaining public-release gates | [October 22 release readiness](RELEASE-READINESS.md) |
| Frozen human review batch and instructions | [Batch manifest](research/EVALUATION-BATCH-MANIFEST.json), [review instructions](research/HUMAN-EVALUATION-INSTRUCTIONS.md), [media rehearsal](research/MEDIA-SUPPLEMENT-REHEARSAL.json) |
| Model contract, artifacts, threshold, parity and observed scope bias | [Local candidate trial and rollback](LOCAL-CANDIDATE-TRIAL.md), [component hash comparison](CANDIDATE-COMPONENT-COMPARISON.json), [candidate supplied-case result](CANDIDATE-REGRESSION-VERIFICATION.json), [candidate 3,470-record result](CANDIDATE-HYBRID-VERIFICATION.json), [stable hybrid integration](HYBRID-INTEGRATION.md), [stable 598-record result](HYBRID-VERIFICATION.json), [prediction-path diagnostic](PREDICTION-PATH-DIAGNOSTIC.json), [Facebook-only regression investigation](FACEBOOK-CLASSIFICATION-REGRESSION.json), [news-style path check](NEWS-STYLE-DIAGNOSTIC.json), [short-input diagnostic](MODEL-SANITY-DIAGNOSTIC.json) |
| VPS, Compose, database, HTTPS, backups and restore | [Deployment guide](DEPLOYMENT.md) |
| Separate survey plan and participant tasks | [Participant guide](research/PARTICIPANT-GUIDE.md) |
| Draft questionnaires and expert review | [Questionnaires](research/QUESTIONNAIRES.md), [pilot and traceability](research/PILOT-AND-TRACEABILITY.md) |
| Research paper | [Revised paper, chapters 1–3](references/REVISED-PAPER-1-3.pdf) |
| Earlier requirements and agent instructions | [Prototype instructions](references/SuriPH_Codex_Prototype_Instructions.docx), [initial prototype](references/SuriPH_Sprint1_Working_Prototype.docx), [prototype v2](references/SuriPH_Sprint1_Working_Prototype_v2.docx), [final document](references/final.docx) |
| Historical system design | [SDD](sdd.docx); its preserved generator is in `tools/`, with npm configuration here |
| UI and browser inspection | [UI report](UI-VERIFICATION.json), [current popup regression](EXTENSION-POPUP-VERIFICATION.json), [synthetic Facebook modal](FACEBOOK-MODAL-VERIFICATION.json), [Google Chrome/Facebook status](CHROME-FACEBOOK-VERIFICATION.json), [earlier isolated Edge extension](INSTALLED-EXTENSION-VERIFICATION.json), [extension failure states](EXTENSION-FAILURE-VERIFICATION.json), [administrator browser flow](ADMIN-BROWSER-VERIFICATION.json), [screenshots](verification/ui/) |
| Database, providers, media and resources | [MariaDB](MARIADB-VERIFICATION.json), [provider availability](PROVIDER-VERIFICATION.json), [retrieval relevance regression](RETRIEVAL-RELEVANCE-VERIFICATION.json), [current multi-video extraction validation](VIDEO-EXTRACTION-VALIDATION-20261103.md), [historical exact-reel audit](VIDEO-TRANSCRIPTION-AUDIT-20261102.md), [media](MEDIA-VERIFICATION.json), [API resources](RESOURCE-MEASUREMENTS.json), [live stack](LIVE-STACK-PERFORMANCE.json) |
| Repository layout and preservation decisions | [Project structure](PROJECT-STRUCTURE.md), [move inventory](CLEANUP-MOVES.json) |

The supplied training notebook, manifest, feature configuration, encoder, tokenizers,
all model artifacts, evidence figures and reference predictions remain **local and
unchanged** under `backend-api/models/TRAINING RESULTS/`. They are deliberately
excluded from Git, not deleted. See that directory's `SuriPH_Repaired_Training_Run.ipynb`,
`run_manifest.json`, `models/feature_config.json` and `records/`.

The full-cleaned candidate run is stored separately under the ignored
`backend-api/models/local-trials/full-cleaned-20261023T022416Z/` directory. Its
classifier and raw records are also local-only and unchanged.

Historical documents describe earlier designs. The latest dated current-source record
takes precedence for current local operation. Existing research
papers and prototype instructions have not been rewritten.

The extension and administrator dashboard do not collect, display or export participant
survey data. Files under `docs/research/` are preserved planning materials for a separate,
institutionally approved survey workflow.
