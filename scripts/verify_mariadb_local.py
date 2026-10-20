"""Windows isolated MariaDB migration, DML privilege, restart and logical restore test.
Never connects to the existing development database. Keeps its own ignored test dir.
"""
import gzip
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from unittest.mock import patch
import pymysql
from sqlalchemy import insert, select, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'backend-api'), str(ROOT/'backend-api/src')]
os.environ['SURI_LOAD_ENV_FILES']='false'
import config
import database
import research_store

def main():
    binary=ROOT/'tools/mariadb-11.4.13-winx64/bin'
    if not binary.is_dir(): raise RuntimeError('Portable MariaDB tools are required for this Windows-only harness')
    folder=ROOT/'tmp'/('mariadb-check-'+secrets.token_hex(4));folder.mkdir(parents=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    root_password=secrets.token_hex(24); app_password=secrets.token_hex(24)
    subprocess.run([str(binary/'mariadb-install-db.exe'), '--datadir='+str(folder/'data'), '--password='+root_password, '--port='+str(port), '--silent'],capture_output=True,check=True)
    process=None; log=(folder/'server.log').open('w')
    def root_connection(db=None):
        return pymysql.connect(host='127.0.0.1',port=port,user='root',password=root_password,database=db,autocommit=True)
    def start():
        proc=subprocess.Popen([str(binary/'mariadbd.exe'),'--defaults-file='+str(folder/'data/my.ini'),'--bind-address=127.0.0.1','--port='+str(port)],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            try:
                conn=root_connection();conn.close();return proc
            except pymysql.Error: time.sleep(.25)
        proc.terminate();raise RuntimeError('Isolated MariaDB did not start')
    def stop(proc):
        with root_connection() as connection:
            with connection.cursor() as cursor:cursor.execute('SHUTDOWN')
        proc.wait(timeout=30)
    try:
        process=start()
        with root_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute('CREATE DATABASE suriph_check CHARACTER SET utf8mb4')
                cursor.execute('CREATE DATABASE suriph_restore CHARACTER SET utf8mb4')
                cursor.execute("CREATE USER 'suriph_maintenance'@'127.0.0.1' IDENTIFIED BY %s",(root_password,))
                cursor.execute("GRANT ALL ON suriph_check.* TO 'suriph_maintenance'@'127.0.0.1'")
        def use(user,password,db):
            config.DATABASE_URL=URL.create('mysql+pymysql',username=user,password=password,host='127.0.0.1',port=port,database=db)
        use('root',root_password,'suriph_check')
        from src.manage import main as provision
        with patch.dict(os.environ, {'MARIADB_ROOT_PASSWORD':root_password,'MARIADB_USER':'suriph_maintenance','MARIADB_PASSWORD':root_password,'SURI_DB_USER':'suriph_runtime','SURI_DB_PASSWORD':app_password}), patch.object(config,'DB_HOST','127.0.0.1'), patch.object(config,'DB_PORT',port), patch.object(config,'DB_NAME','suriph_check'), patch.object(sys,'argv',['manage','provision']):
            provision()
        assert database.migrate()['applied_versions']==[]
        use('suriph_runtime',app_password,'suriph_check')
        pred={'internal_label':'Non-Misleading','model_score':.2,'training_run_id':'test-fixture','artifact_sha256':'fixture','linguistic_indicators':[]}
        receipt=research_store.save(pred,text='Explicit synthetic consent fixture',input_type='text',sources=[],retain_text=True)
        research_store.change(receipt['record_id'],receipt['withdrawal_token'],usefulness=4)
        try:
            with database._get_engine().begin() as conn: conn.execute(text('CREATE TABLE privilege_probe (id INT)'))
        except Exception: pass
        else: raise AssertionError('Runtime unexpectedly has DDL privileges')
        try:
            with database._get_engine().begin() as conn:
                conn.execute(insert(database.audit_logs).values(action='ROLLBACK_TEST',description='synthetic',performed_by='test'))
                raise ValueError('Rollback fixture')
        except ValueError: pass
        with database._get_engine().connect() as conn:
            assert conn.execute(select(database.audit_logs).where(database.audit_logs.c.action=='ROLLBACK_TEST')).first() is None
        database._get_engine().dispose();stop(process);process=None
        assert database.database_health()['status']=='unavailable'
        process=start()
        assert research_store.export_rows()[0]['usefulness']==4
        auth=os.environ|{'MYSQL_PWD':root_password}
        dump=subprocess.run([str(binary/'mariadb-dump.exe'),'--host=127.0.0.1','--port='+str(port),'--user=root','--single-transaction','--quick','--hex-blob','--skip-lock-tables','suriph_check'],env=auth,capture_output=True,check=True).stdout
        backup=folder/'logical.sql.gz'
        with gzip.open(backup,'wb') as stream:stream.write(dump)
        with gzip.open(backup,'rb') as stream:
            subprocess.run([str(binary/'mariadb.exe'),'--host=127.0.0.1','--port='+str(port),'--user=root','suriph_restore'],env=auth,input=stream.read(),capture_output=True,check=True)
        use('root',root_password,'suriph_restore')
        restored=research_store.export_rows();assert len(restored)==1 and restored[0]['usefulness']==4
        assert database.migrate()['applied_versions']==[]
        research_store.change(receipt['record_id'],receipt['withdrawal_token'],withdraw=True)
        assert not research_store.export_rows()
        report={'passed':True,'engine':'MariaDB 11.4.13 native Windows','schema_version':5,'actual_provision_command':'passed','empty_migration':'passed','idempotent_migration':'passed','runtime_ddl_denied':'passed','transaction_rollback':'passed','restart_persistence':'passed','database_outage':'passed','logical_gzip_restore_to_isolated_database':'passed','withdrawal_after_restore':'passed','production_docker_wrapper_tested':False}
        (ROOT/'docs/MARIADB-VERIFICATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    finally:
        if database._engine:database._engine.dispose()
        if process and process.poll() is None:stop(process)
        log.close()

if __name__=='__main__':main()
