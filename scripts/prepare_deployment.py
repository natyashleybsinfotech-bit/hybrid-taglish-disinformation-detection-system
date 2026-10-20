"""Generate local deployment settings without printing secrets or overwriting files."""

import argparse
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def domain(value):
    value = value.lower().strip()
    if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", value):
        raise argparse.ArgumentTypeError("Use a hostname such as api.yourdomain.ph, without https://")
    if value.endswith("example.com"):
        raise argparse.ArgumentTypeError("Use your actual domain")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-domain", required=True, type=domain)
    parser.add_argument("--admin-domain", required=True, type=domain)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    if args.api_domain == args.admin_domain:
        parser.error("API and admin must use different subdomains")
    if not re.fullmatch(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", args.email):
        parser.error("Supply a valid TLS contact email")
    output = ROOT / ".env.production"
    extension = ROOT / "chrome-extension" / ".env.production"
    if output.exists() or extension.exists():
        parser.error("Production settings already exist; edit them explicitly instead of rotating live credentials")
    values = {
        "PUBLIC_API_URL": f"https://{args.api_domain}",
        "API_DOMAIN": args.api_domain,
        "ADMIN_DOMAIN": args.admin_domain,
        "ACME_EMAIL": args.email,
        "SURI_CORS_ORIGINS": f"https://{args.admin_domain}",
        "SURI_TRUSTED_HOSTS": f"{args.api_domain},localhost,127.0.0.1",
    }
    for key in ("SURI_DB_PASSWORD", "MARIADB_PASSWORD", "MARIADB_ROOT_PASSWORD", "SURI_ADMIN_PASSWORD", "SURI_VIEWER_PASSWORD", "SURI_SESSION_SECRET"):
        values[key] = secrets.token_hex(32)
    lines = []
    for line in (ROOT / ".env.production.example").read_text(encoding="utf-8").splitlines():
        key = line.partition("=")[0]
        lines.append(f"{key}={values[key]}" if key in values else line)
    # Restrictive permissions from creation on Unix; use the user's private folder on Windows.
    for path, contents in ((output, "\n".join(lines) + "\n"), (extension, f"VITE_API_BASE_URL=https://{args.api_domain}\n")):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(contents)
    print("Created .env.production and chrome-extension/.env.production. Secrets were not printed.")
    print("Store the generated admin/viewer credentials in your password manager before deployment.")


if __name__ == "__main__":
    main()
