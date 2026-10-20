"""Stream a consistent MariaDB SQL backup through Docker; never print credentials."""

import argparse
import gzip
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--project-name", default="suriph")
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--confirm-restore", action="store_true", help="Acknowledge replacing target database contents")
    parser.add_argument("--retention-days", type=int, default=7)
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error("Retention must be at least one day")
    command = ["docker", "compose", "--project-name", args.project_name, "--env-file", args.env_file, "exec", "-T", "database", "sh", "-c"]
    auth = 'export MYSQL_PWD="$MARIADB_PASSWORD"; '
    if args.restore:
        if not args.confirm_restore:
            parser.error("Restore replaces data. Stop API/worker, back up first, then add --confirm-restore")
        # Verify gzip integrity before sending any SQL to the target database.
        with gzip.open(args.restore, "rb") as stream:
            while stream.read(1024 * 1024):
                pass
        process = subprocess.Popen(command + [auth + 'exec mariadb --user="$MARIADB_USER" "$MARIADB_DATABASE"'], cwd=ROOT, stdin=subprocess.PIPE)
        try:
            with gzip.open(args.restore, "rb") as stream:
                shutil.copyfileobj(stream, process.stdin)
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise SystemExit("Restore failed; leave application stopped and inspect the database")
        print("Database restored. Verify schema and application before reopening traffic.")
        return
    folder = ROOT / "backups"
    folder.mkdir(mode=0o700, exist_ok=True)
    output = folder / (datetime.now(timezone.utc).strftime("suriph-%Y%m%dT%H%M%S%fZ") + ".sql.gz")
    temporary = output.with_suffix(".partial")
    process = subprocess.Popen(command + [auth + 'exec mariadb-dump --user="$MARIADB_USER" --single-transaction --quick --hex-blob --skip-lock-tables "$MARIADB_DATABASE"'], cwd=ROOT, stdout=subprocess.PIPE)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as stream:
            shutil.copyfileobj(process.stdout, stream)
        if process.wait() != 0:
            raise RuntimeError("Database dump failed")
        temporary.rename(output)
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
        temporary.unlink(missing_ok=True)
    print(f"Backup created: {output}")
    cutoff = datetime.now(timezone.utc).timestamp() - args.retention_days * 86400
    # Only this utility's completed dumps in its fixed private directory are rotated.
    for previous in folder.glob("suriph-*.sql.gz"):
        if previous.is_file() and not previous.is_symlink() and previous.stat().st_mtime < cutoff:
            previous.unlink()
    print("Copy it to private off-server storage; also retain approved model bundles and deployment settings.")


if __name__ == "__main__":
    main()
