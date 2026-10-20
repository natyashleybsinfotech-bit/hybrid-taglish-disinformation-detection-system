# SuriPH deployment runbook

## Current release status

The supplied model_4 hybrid pipeline from run `20261011T235112Z` now loads on CPU.
All 598 saved raw test inputs match reference labels and probabilities within the
declared tolerance. See [HYBRID-INTEGRATION.md](HYBRID-INTEGRATION.md) for verified
details, commands, changed files and remaining limitations.

Local MariaDB schema version 5, administrator/viewer authentication, backend tests,
frontend builds and real API/extension transport have been checked. A connected
installed-extension session was not available. Headless component screenshots were inspected. Docker is not installed
on this workstation: container builds, production TLS and target-server load/backup-wrapper checks
remain release requirements. Native MariaDB restart and isolated logical restore passed. The system is not publicly deployed.

## Hosting choice

Use a **Linux VPS with Docker Compose**, including Hostinger's VPS Docker template.
Start capacity testing around **4 vCPU, 8 GB RAM, 40+ GB free disk**, with training
disabled. This is an engineering starting estimate, not a measured guarantee:
measure simultaneous text/OCR/Whisper memory and response time on the chosen server.
Retraining and model switching are disabled in this deployment.

Hostinger supports Compose deployments on its VPS product. Render can run this
backend as a Docker web service and MariaDB as a private service with a paid disk,
but disks cannot be shared across services. This deployment has one inference API
and no training worker; provision its private artifact directory separately from
the database disk. The Compose recipe below targets a VPS, not a Render Blueprint.

Sources: [Hostinger Docker manager](https://www.hostinger.com/support/12040789-hostinger-docker-manager-for-vps-simplify-your-container-deployments/),
[Render disks](https://render.com/docs/disks),
[Render MySQL deployment](https://render.com/docs/deploy-mysql).

## What to supply before launch

- Transfer the already verified inference artifacts described below to private
  server storage. They are deliberately excluded from Git and container images.
- A server, two subdomains such as `api.yourdomain.ph` and `admin.yourdomain.ph`, and
  an email for certificate expiry/account notices.
- Optional Serper and Google Fact Check keys if related-source lookup is needed.
  Without keys, the API honestly reports these services as unavailable; they are
  not required for classifier inference and do not override its prediction.
- Intended audience/load, approved data retention period, and an off-server private
  backup destination. Screened text is not stored by default; research metadata and optional text require consent;
  uploaded media bytes are temporary. Explain this behavior in the extension's
  privacy notice before distributing it.

## Model acceptance

Preserve `backend-api/models/TRAINING RESULTS/` locally. For serving, only model_4,
the entire contextual_encoder folder, tagalog_tokenizer, feature_config.json and
run_manifest.json are required. `docker-compose.yml` mounts these read-only at
`/app/artifacts`, which is the production `SURI_MODEL_ARTIFACT_DIR`.

The exact threshold is 0.65. The loader verifies hashes, run ID, versions and saved
component settings, then runs actual hybrid inference once at startup. No registry
entry, legacy filename, environment threshold or API call can switch classifiers.
Use `requirements-model.txt`; do not install a different sklearn/transformers stack.
For artifact details and evidence, use [the integration guide](HYBRID-INTEGRATION.md).

## Server setup and first deployment

Use an Ubuntu VPS with Docker Engine and Compose v2. Install Git and Python 3 for
the helper scripts. The server must have outbound access for container images and
initial model downloads. Point both subdomain DNS A records to the server's public
IP; only publish AAAA records when IPv6 is correctly routed. Allow inbound TCP
80/443 and restrict SSH to your administrator IP. The database has no published port;
API 8000 and dashboard 8080 bind to loopback.

Copy this repository and the trusted model files to the server. Do not copy your
local `.env`, virtualenv, `tools/`, development database, or `node_modules`.
Generate settings from the repository root, replacing these example arguments:

```bash
python3 scripts/prepare_deployment.py --api-domain api.yourdomain.ph --admin-domain admin.yourdomain.ph --email you@yourdomain.ph
```

This creates ignored `.env.production` and `chrome-extension/.env.production` with
distinct random database, root, admin, viewer and session secrets. It refuses to
overwrite existing settings. Keep these files private and store the admin/viewer
credentials in a password manager. Edit optional lookup keys directly in the file.
Never put secrets in a `VITE_` variable; frontend values are public.

The API runs as UID 10001. Make the required model files/directories readable by that user. They are mounted read-only.
The model cache uses a persistent Docker volume. On a new volume Docker copies the
image directory ownership; if reusing an old cache, inspect and fix its ownership.

```bash
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d database
docker compose --env-file .env.production --profile maintenance run --rm migrate
docker compose --env-file .env.production run --rm --no-deps api python -m src.deployment_check --media
docker compose --env-file .env.production --profile https up -d --wait --wait-timeout 600
docker compose --env-file .env.production ps
```

Wait for the database health check before running `deployment_check`; if it is
still starting, rerun the check after it becomes healthy. The one-shot migration service creates/upgrades schema and bootstraps accounts.
The API uses a separate DML-only account. The check runs Filipino/English/Taglish inference and
warms OCR/Whisper/FFmpeg. Startup fails on production DB/bootstrap errors. Migration
does not import the old local development data. Use a deliberately reviewed data
export if that is needed; never reuse local development credentials in production.

Caddy provisions and renews HTTPS for the configured domains. DNS and open 80/443
are prerequisites. See [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
and [Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/).

## Release checks

1. `https://api.yourdomain.ph/ready` must return HTTP 200 with `ready: true`, the
   expected model version/hash, and an available MariaDB connection.
2. Log in to the dashboard as both admin and viewer. Confirm viewer writes are
   denied, expired sessions are denied, and the dashboard shows the expected model.
3. Screen real Filipino, English and Taglish examples. Exercise an image with
   readable text and a short spoken video, then check that candidate records persist.
   Model download checks alone do not validate OCR/transcription quality.
4. Test oversized uploads, invalid media, repeated login failures, concurrent
   screening and temporary database failure. Review logs without exposing submitted
   text or passwords. The proxy body limit is 55 MB; the file limit is 50 MiB.
5. Restart the stack and verify data persists. Run a backup and restore drill in a
   separate test Compose project before accepting real data.
6. Benchmark the selected server. Record latency, peak memory, error rate and model
   hash. The public API allows 20 screening requests/minute/IP, 5 login attempts/minute/IP
   and two in-flight screenings. Shared NAT users share a limit. Limits are in-memory
   and reset on restart: this recipe uses **one API process and one replica**.

Do not publish extra API ports or put an untrusted proxy in front of Uvicorn. Its
forwarded headers are trusted because the public ingress is Caddy; adding another
proxy requires a reviewed forwarded-header/trusted-proxy configuration. Multi-replica
deployments need shared limits and coordinated migrations.

## Extension release

Copy only the generated `VITE_API_BASE_URL=https://api.yourdomain.ph` setting to the
development machine's `chrome-extension/.env.production`. Then:

```powershell
Set-Location chrome-extension
npm ci
npm run build:release
```

Load `dist` through `chrome://extensions` for pilot testing. Verify requests go to
the public HTTPS API and the generated manifest includes that origin. For wider
distribution, prepare icons, screenshots, privacy/data-use disclosures and a Chrome
Web Store submission. Store approval is a separate step from deploying the API.

## Backups, recovery and upgrades

```bash
python3 scripts/database_backup.py
```

Install the supplied daily retention/backup timer (see below), keep a retention policy,
and copy `backups/*.sql.gz` to access-controlled off-server storage. Back up approved
models, manifests and settings too. Avoid concurrent schema migrations during dumps.
The script streams a consistent SQL dump, checks exit status, uses restricted file
permissions and never prints credentials. The systemd timer schedules it; off-server upload remains an operator responsibility.

Test restoration against a separate Compose project/database first. The utility's
`--project-name` and `--env-file` options select the target; ensure its credentials
match the test database. No API is needed for a database-only restore drill.
For an actual approved recovery, stop app writers, take a current backup, and run:

```bash
docker compose --env-file .env.production stop api
python3 scripts/database_backup.py --restore backups/CHOSEN_BACKUP.sql.gz --confirm-restore
docker compose --env-file .env.production --profile https up -d --wait
```

Restore replaces target data; keep the app stopped if it fails. Never use
`docker compose down -v` on production: that deletes persistent volumes.
For upgrades, retain the previous source/image versions and model, back up first,
then rebuild, run the one-shot migration service, run the preflight, and repeat smoke checks. A schema change may require
restoring the matching database backup to roll back safely.

Bootstrap passwords create accounts only on the first initialization. Changing the
environment does **not** rotate existing database account passwords. Rotate those
explicitly, and rotate `SURI_SESSION_SECRET` to invalidate existing sessions.
Changing MariaDB initialization variables also does not change users in an existing
database volume. Plan and verify credential rotation before changing these values.

Monitor public `/ready`, disk usage, database backups and container restarts. Docker
health checks report unhealthy services but do not automatically restart a merely
unhealthy process; arrange external alerting. Logs are capped at 3 x 10 MB/service.

## Fixed classifier deployment

Retraining, model registration and activation are disabled in this deployment. Do
not start a training worker or attempt to enable a training Compose profile. The
profile has been removed. Dataset review/export remains available, but cannot alter
the pinned active classifier. This integration did not retrain or tune any model.

## Daily retention and backup scheduling

The migration service needs maintenance/root credentials only while it runs. The API
has DML permissions and cannot create or drop tables. An existing installation must
back up before schema v5; migration is additive and does not remove earlier records.
The Windows native migration/restart/restore check is recorded in
`MARIADB-VERIFICATION.json`. The Docker wrapper still needs execution on Linux.

Set `SURI_RESEARCH_RETENTION_DAYS` before recruitment (default 30). Install the timer,
adjusting `/opt/suriph` in the unit to your actual checkout path:

```bash
sudo install -m 644 deploy/suriph-maintenance.service /etc/systemd/system/
sudo install -m 644 deploy/suriph-maintenance.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now suriph-maintenance.timer
sudo systemctl start suriph-maintenance.service
sudo systemctl status suriph-maintenance.service
sudo systemctl list-timers suriph-maintenance.timer
```

The daily job deletes expired ResearchRecords, then creates a compressed consistent
logical dump. `--retention-days 7` rotates only this utility's completed backups after
a successful new dump. It does not delete arbitrary paths, curate historical datasets,
or upload files. Alert on failed jobs and disk pressure; restrict backup directories
to operators. Off-server backups/exports must follow the same approved retention.
Live withdrawal deletes a research record, not existing backups. Reapply outstanding
withdrawals and purge expired records after restoration and before exposing the API.

## Isolated Docker restore rehearsal

Use a separate Compose project and a private environment file with newly generated
test credentials. Do not reuse the production project name or attach its volume.
Keep `SURI_ENV_FILE=.env.restore-test` inside the ignored environment file. Create it
by adapting the local generator into a separate test checkout, or copying its newly
generated `.env.local-stack` to `.env.restore-test` before any service is started.

```bash
docker compose --project-name suriph-restore-test --env-file .env.restore-test up -d database
# Wait for the database health check, then restore only to the separate project.
python3 scripts/database_backup.py --project-name suriph-restore-test --env-file .env.restore-test --restore backups/CHOSEN_BACKUP.sql.gz --confirm-restore
docker compose --project-name suriph-restore-test --env-file .env.restore-test exec -T database sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE" -e "SELECT MAX(version) FROM SchemaMigrations; SELECT COUNT(*) FROM ResearchRecords;"'
docker compose --project-name suriph-restore-test --env-file .env.restore-test stop
```

Compare schema, row counts and selected synthetic record/feedback values with the
pre-backup observations. Use synthetic data for rehearsal; do not publish backups.
Native Windows verification actually exercised these dump/import options, transaction
rollback, DML-only writes, denial of DDL and restart persistence in isolated databases.
It did not execute these Docker commands, which remain an explicit release gate.

## Configuration and limits

- One Uvicorn worker; one frozen encoder/classifier instance. Four CPU inference
  threads by default; at most two in-flight screenings in the production middleware.
- Twenty screening/research actions per minute per IP; five login attempts per minute.
  Overload returns 503/Retry-After; rate limits return 429. Limits reset on restart and
  are not shared across replicas. Do not increase workers without a capacity design.
- Text maximum: 1,000,000 characters, rejected rather than clipped. Full-text inference
  has a 120-second budget checked at chunk-batch boundaries. A timed-out inference
  produces no partial label and marks readiness false; recover/restart after diagnosis.
  A native compute call is not forcibly preempted mid-kernel.
- Upload maximum: 50 MiB; image processing limit: 20 megapixels; video audio maximum:
  120 seconds. Decoding is bounded and network protocols are disabled in FFmpeg.
  Frames are sampled, not every frame analyzed. Media support is experimental.
- Provider calls target fixed HTTPS APIs, reject redirects, and bound response bodies
  to 2 MB. Result links are not fetched by the server. Default provider timeout: 8 seconds.
- The extension uses a 120-second popup request timeout; selected in-page video processing
  has a five-minute outer timeout. A timeout never generates a substitute prediction.
- Explicit HTTPS CORS origin in production, HttpOnly/Secure/SameSite=Strict admin cookie,
  POST origin checks, role checks, no browser localStorage tokens. Serve API/dashboard
  on sibling subdomains of the same site. Use the same hostname spelling locally.
- Structured request logs record random request ID, method, route template, status and
  duration. Bodies, queries, raw text, receipt tokens and credentials are not logged.
- Git/container ignores exclude models, raw datasets, secrets, backups and research-data.
  Private artifact mounts must contain model_4, full encoder, tokenizer/config and manifest.

## Troubleshooting and rollback

If `/ready` is false, inspect its model and database sections. Hash/version errors require
restoring the exact supplied artifacts and pinned requirements; never substitute another
classifier. Schema errors require the maintenance migration service, not wider runtime
privileges. Provider failure can leave inference usable; inspect the provider status.

For an update, stop API writers, make a logical backup, record current source/image digest
and model hash, build the new version, run migration, preflight and smoke checks, then
reopen access. Retain old image versions privately. Schema v5 is additive; still test the
chosen previous app against the schema before rolling it back. Do not restore a database
backup merely to roll back UI code. A database restore can lose records created after the
backup and needs an explicit recovery decision. Keep the API stopped on restore failure.

`docker compose stop` preserves volumes. Never use `down -v` as an update or rollback.
If a process is unhealthy but still running, Docker does not restart it merely because
the health check failed; investigate the error and restart deliberately after resolving it.
