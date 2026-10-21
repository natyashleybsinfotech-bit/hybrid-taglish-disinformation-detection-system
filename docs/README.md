# Documentation index

| Need | Start here |
| --- | --- |
| Install and run locally | [START_HERE](../START_HERE.md) |
| Completed checks and remaining release gates | [Release readiness](RELEASE-READINESS.md) |
| Model contract, artifacts, threshold, parity and observed scope bias | [Hybrid integration](HYBRID-INTEGRATION.md), [598-record result](HYBRID-VERIFICATION.json), [short-input diagnostic](MODEL-SANITY-DIAGNOSTIC.json) |
| VPS, Compose, database, HTTPS, backups and restore | [Deployment guide](DEPLOYMENT.md) |
| Participant consent and tasks | [Participant guide](research/PARTICIPANT-GUIDE.md) |
| Draft questionnaires and expert review | [Questionnaires](research/QUESTIONNAIRES.md), [pilot and traceability](research/PILOT-AND-TRACEABILITY.md) |
| Research paper | [Revised paper, chapters 1–3](references/REVISED-PAPER-1-3.pdf) |
| Earlier requirements and agent instructions | [Prototype instructions](references/SuriPH_Codex_Prototype_Instructions.docx), [initial prototype](references/SuriPH_Sprint1_Working_Prototype.docx), [prototype v2](references/SuriPH_Sprint1_Working_Prototype_v2.docx), [final document](references/final.docx) |
| Historical system design | [SDD](sdd.docx); its preserved generator is in `tools/`, with npm configuration here |
| UI and browser inspection | [UI report](UI-VERIFICATION.json), [installed extension](INSTALLED-EXTENSION-VERIFICATION.json), [extension failure states](EXTENSION-FAILURE-VERIFICATION.json), [administrator browser flow](ADMIN-BROWSER-VERIFICATION.json), [screenshots](verification/ui/) |
| Database, providers, media and resources | [MariaDB](MARIADB-VERIFICATION.json), [providers](PROVIDER-VERIFICATION.json), [media](MEDIA-VERIFICATION.json), [API resources](RESOURCE-MEASUREMENTS.json), [live stack](LIVE-STACK-PERFORMANCE.json) |
| Repository layout and preservation decisions | [Project structure](PROJECT-STRUCTURE.md), [move inventory](CLEANUP-MOVES.json) |

The supplied training notebook, manifest, feature configuration, encoder, tokenizers,
all model artifacts, evidence figures and reference predictions remain **local and
unchanged** under `backend-api/models/TRAINING RESULTS/`. They are deliberately
excluded from Git, not deleted. See that directory's `SuriPH_Repaired_Training_Run.ipynb`,
`run_manifest.json`, `models/feature_config.json` and `records/`.

Historical documents describe earlier designs. The current integration contract and
release evidence take precedence for operating this deployment. Existing research
papers and prototype instructions have not been rewritten.
