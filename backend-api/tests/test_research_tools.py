import csv
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class ResearchToolsTests(unittest.TestCase):
    def test_backup_retention_only_removes_expired_completed_dumps(self):
        tool = module('database_backup')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / 'suriph-20260101T000000000000Z.sql.gz'
            recent = root / 'suriph-20261020T000000000000Z.sql.gz'
            partial = root / 'suriph-20260101T000000000000Z.sql.partial'
            unrelated = root / 'other.sql.gz'
            for path in (old, recent, partial, unrelated):
                path.write_bytes(b'fixture')
            os.utime(old, (100, 100))
            os.utime(partial, (100, 100))
            os.utime(unrelated, (100, 100))

            self.assertEqual(tool.prune_completed_backups(root, 200), 1)
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(partial.exists())
            self.assertTrue(unrelated.exists())

    def test_survey_keeps_missingness_and_neutral_distinct_and_blocks_formula_export(self):
        tool=module('validate_survey')
        with tempfile.TemporaryDirectory() as folder:
            original=Path(folder)/'synthetic.csv';output=Path(folder)/'checked.csv'
            with original.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(tool.FIELDS)
                writer.writerow(['fixture','BSIT','draft','B01','3','answered','T1','=not-a-real-response'])
                writer.writerow(['fixture','BSIT','draft','B02','','not_observed','',''])
            with patch.object(sys,'argv',['validate',str(original),str(output)]),redirect_stdout(io.StringIO()):tool.main()
            with output.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(rows[0]['rating'],'3');self.assertEqual(rows[1]['rating'],'')
            self.assertTrue(rows[0]['comment'].startswith("'="))
            with patch.object(sys,'argv',['validate',str(original),str(output)]),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):tool.main()

    def test_local_compose_settings_are_private_unique_and_non_overwriting(self):
        tool=module('prepare_local')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.env.production.example').write_text((ROOT/'.env.production.example').read_text())
            with patch.object(tool,'ROOT',root),redirect_stdout(io.StringIO()):
                tool.main();saved=(root/'.env.local-stack').read_text()
                self.assertIn('SURI_ENV_FILE=.env.local-stack',saved)
                self.assertIn('SURI_DB_USER=suriph_runtime',saved)
                with self.assertRaises(SystemExit):tool.main()
                self.assertEqual((root/'.env.local-stack').read_text(),saved)
