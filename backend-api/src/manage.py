"""Explicit operator commands. No classifier loading or training."""
import argparse
import json
import os
import re
import pymysql
import config
from . import database, research_store

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["migrate", "purge-research", "provision"])
    args = parser.parse_args()
    if args.action == "purge-research":
        print(json.dumps({"expired_records_deleted": research_store.purge_expired()}))
        return
    if args.action == "provision":
        # Isolated maintenance service only; these credentials are cleared in API.
        name, user, password = config.DB_NAME, os.environ["SURI_DB_USER"], os.environ["SURI_DB_PASSWORD"]
        if not all(re.fullmatch(r"[A-Za-z0-9_]+", value) for value in (name, user)) or len(password) < 16:
            raise RuntimeError("Invalid database name/account or weak application password")
        connection = pymysql.connect(host=config.DB_HOST, port=config.DB_PORT, user="root", password=os.environ["MARIADB_ROOT_PASSWORD"])
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE USER IF NOT EXISTS '{user}'@'%%' IDENTIFIED BY %s", (password,))
                cursor.execute(f"ALTER USER '{user}'@'%%' IDENTIFIED BY %s", (password,))
                cursor.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{user}'@'%'")
                cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{name}`.* TO '{user}'@'%'")
        # Schema-scoped maintenance identity, separate from the running API.
        from sqlalchemy.engine import URL
        config.DATABASE_URL = URL.create("mysql+pymysql", username=os.environ["MARIADB_USER"], password=os.environ["MARIADB_PASSWORD"], host=config.DB_HOST, port=config.DB_PORT, database=name)
    state = database.migrate()
    if state["status"] != "available":
        raise RuntimeError("Migration failed; inspect database availability and maintenance permissions")
    database.ensure_bootstrap_admin()
    database.ensure_bootstrap_viewer()
    print(json.dumps(state))

if __name__ == "__main__":
    main()
