import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import database


class DatabaseTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        encoded = database.hash_password("a-secure-test-password", iterations=1_000)
        self.assertTrue(database.verify_password("a-secure-test-password", encoded))
        self.assertFalse(database.verify_password("wrong", encoded))
        self.assertNotIn("a-secure-test-password", encoded)

    def test_unconfigured_database_has_honest_health(self):
        with patch.object(database.config, "DB_USER", ""):
            self.assertEqual(database.database_health()["status"], "not_configured")
            self.assertEqual(database.migrate()["status"], "not_configured")

    def test_core_schema_is_versioned(self):
        schema = " ".join(statement for _, group in database.MIGRATIONS for statement in group)
        for table in ("AdminUsers", "CandidateSamples", "AuditLogs"):
            self.assertIn(table, schema)
        self.assertIn("training_status", schema)
        self.assertIn("not_training_data", schema)


if __name__ == "__main__":
    unittest.main()
