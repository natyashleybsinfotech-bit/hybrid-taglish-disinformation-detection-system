# SuriPH

SuriPH is a Facebook-focused evidence lookup prototype with a FastAPI backend, Chrome extension, and administrator dashboard. The active runtime is **evidence-only**: it does not load or call a trained classifier and does not return a model score, probability, or automatic Misleading/Non-Misleading label.

The result is one of:

- **Published fact-check: _rating_** when Google Fact Check returns a closely matching ClaimReview record. The rating is explicitly attributed to its publisher.
- **Related coverage found** when approved-publisher articles are relevant. These links are context and do not prove or disprove every detail.
- **Unresolved** when there is no close fact-check or related coverage.
- **Evidence providers unavailable** when configured providers fail.

Inputs are not stored by default. Public candidate submission and participant/survey controls are absent from the extension and active admin navigation. Historical research papers, datasets, model artifacts, notebooks, manifests, and verification records remain preserved for provenance but are outside the active decision path.

See [START_HERE.md](START_HERE.md) to run the system, [evidence-only behavior](docs/EVIDENCE-ONLY-MODE.md), and the [documentation index](docs/README.md).

## Project layout

- `backend-api`: evidence API, provider clients, MariaDB persistence, media extraction, and tests.
- `chrome-extension`: popup and Facebook page controls.
- `admin-dashboard`: evidence-provider health and research archive views.
- `deploy` and `docker-compose.yml`: deployment configuration.
- `docs`: setup, deployment, research references, historical diagnostics, and verification evidence.

## Safety contract

The API abstains instead of inventing a label when evidence is absent, weak, or unavailable. Related sources never override or become a verdict. Provider failures remain separate from the assessment. `/health` and `/ready` expose `decision_engine.mode=evidence_only`, `classifier_loaded=false`, configured providers, and readiness.
