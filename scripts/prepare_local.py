"""Generate private loopback-only Compose settings. No hosting or domain required."""
import os
from pathlib import Path
import secrets
ROOT=Path(__file__).resolve().parents[1]

def main():
    target=ROOT/'.env.local-stack'
    if target.exists():raise SystemExit('Local stack settings exist; preserve them instead of rotating credentials.')
    values={
        'PUBLIC_API_URL':'http://127.0.0.1:8000', 'SURI_APP_ENV':'development',
        'SURI_CORS_ORIGINS':'http://127.0.0.1:8080,http://localhost:8080',
        'SURI_TRUSTED_HOSTS':'localhost,127.0.0.1', 'SURI_MODEL_DEVICE':'cpu',
    }
    for key in ('SURI_DB_PASSWORD','MARIADB_PASSWORD','MARIADB_ROOT_PASSWORD','SURI_ADMIN_PASSWORD','SURI_VIEWER_PASSWORD','SURI_SESSION_SECRET'):
        values[key]=secrets.token_hex(32)
    lines=[]
    for line in (ROOT/'.env.production.example').read_text().splitlines():
        key=line.partition('=')[0];lines.append(f'{key}={values[key]}' if key in values else line)
    lines+=['SURI_ENV_FILE=.env.local-stack','COMPOSE_PROJECT_NAME=suriph-local','SURI_TRAFFIC_LIMITS=true']
    descriptor=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as stream:stream.write('\n'.join(lines)+'\n')
    print('Created ignored .env.local-stack. Read local login credentials privately from that file. No public service was started.')

if __name__=='__main__':main()
