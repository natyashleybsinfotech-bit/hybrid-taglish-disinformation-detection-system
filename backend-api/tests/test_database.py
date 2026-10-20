import os
import sys
import tempfile
import unittest
from pathlib import Path
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
        with patch.object(database.config, "DATABASE_URL", ""), patch.object(
            database.config, "DB_PATH", None
        ):
            self.assertEqual(database.database_health()["status"], "not_configured")
            self.assertEqual(database.migrate()["status"], "not_configured")

    def test_sqlite_migration_and_persistence_flow(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database.config, "DATABASE_URL", ""
        ), patch.object(
            database.config, "DB_PATH", Path(directory) / "test.db"
        ), patch.object(database.config, "ADMIN_BOOTSTRAP_USERNAME", "admin"), patch.object(
            database.config, "ADMIN_BOOTSTRAP_PASSWORD", "temporary-test-password"
        ), patch.object(database.config, "VIEWER_BOOTSTRAP_USERNAME", "afp-viewer"
        ), patch.object(database.config, "VIEWER_BOOTSTRAP_PASSWORD", "temporary-viewer-password"
        ):
            migration = database.migrate()
            self.assertEqual(migration["status"], "available")
            self.assertEqual(database.database_health(), {"status": "available", "engine": "sqlite"})
            self.assertTrue(database.ensure_bootstrap_admin())
            self.assertFalse(database.ensure_bootstrap_admin())
            self.assertTrue(database.ensure_bootstrap_viewer())
            self.assertEqual(
                database.verify_admin("afp-viewer", "temporary-viewer-password")["role"],
                "viewer",
            )
            self.assertIsNotNone(database.verify_admin("admin", "temporary-test-password"))
            self.assertIsNone(database.verify_admin("admin", "wrong"))

            with self.assertRaisesRegex(ValueError, "Misleading or Non-Misleading"):
                database.create_candidate(
                    text="Invalid label", page_url=None, page_title=None,
                    proposed_label="Unlabeled",
                )

            candidate_id = database.create_candidate(
                text="Sample candidate", page_url="https://example.com", page_title="Example",
                source_type="image", proposed_label="Misleading",
                topic="Health and Medicine", topic_confidence=0.8,
            )
            evidence_missing_id = database.create_candidate(
                text="Needs evidence", page_url=None, page_title=None,
                proposed_label="Non-Misleading",
                topic="Other and General", topic_confidence=0.35,
            )
            with self.assertRaisesRegex(ValueError, "matching evidence URL"):
                database.review_candidate(
                    evidence_missing_id, decision="approve", proposed_label="Misleading",
                    notes=None, reviewer="admin", language="Taglish",
                    topic="Other and General", claim_group_id="claim-missing",
                )
            database.add_evidence(
                candidate_id,
                source_url="https://example.com/evidence",
                publisher="Example",
                rating="False",
                claim_match_status="matched",
                notes="Same underlying claim.",
                reviewer="admin",
            )
            database.review_candidate(
                candidate_id,
                decision="approve",
                proposed_label="Misleading",
                notes="Evidence confirmed.",
                reviewer="admin",
                language="Taglish",
                claim_group_id="claim-1",
            )
            database.add_independent_annotation(
                candidate_id, reviewer="reviewer-1", proposed_label="Misleading",
                annotation_round="pilot", evidence_sufficient=True, notes=None,
            )
            database.add_independent_annotation(
                candidate_id, reviewer="reviewer-2", proposed_label="Misleading",
                annotation_round="pilot", evidence_sufficient=True, notes=None,
            )
            database.add_independent_annotation(
                candidate_id, reviewer="reviewer-3", proposed_label="Misleading",
                annotation_round="pilot", evidence_sufficient=True, notes=None,
            )
            database.add_independent_annotation(
                candidate_id, reviewer="reviewer-4", proposed_label="Misleading",
                annotation_round="pilot", evidence_sufficient=True, notes=None,
            )
            self.assertEqual(len(database.list_annotations(candidate_id)), 5)
            dataset_id = database.create_dataset_version("dataset-v1", None, "admin")
            database.add_dataset_item(
                dataset_id,
                candidate_id=candidate_id,
                final_label="Misleading",
                partition_name="train",
                claim_group_id="claim-1",
            )
            bulk_dataset_id = database.create_dataset_version("dataset-bulk-v1", None, "admin")
            bulk_result = database.bulk_add_approved_candidates(bulk_dataset_id)
            self.assertEqual(bulk_result["added"], 1)
            self.assertEqual(sum(bulk_result["partitions"].values()), 1)
            with patch.object(database.config, "MIN_TAGLISH_SAMPLES", 1), patch.object(
                database.config, "ENFORCE_PAPER_DATASET", False
            ):
                database.approve_dataset_version(dataset_id)
            training_run_id = database.queue_training_run(dataset_id, "model-v1", "admin")
            self.assertEqual(database.list_training_runs()[0]["training_run_id"], training_run_id)
            model_id = database.register_model_version(
                dataset_version_id=dataset_id,
                model_name="Test model",
                version_name="model-v1",
                feature_mode="hybrid_distilbert",
                metrics={"f1_macro": 0.8},
                artifact_path="models/test.pkl",
                created_by="admin",
            )
            database.review_model_version(model_id, "approved", "admin")
            database.activate_model_version(model_id, "admin")
            claimed = database.claim_training_run()
            self.assertEqual(claimed["training_run_id"], training_run_id)
            database.update_training_progress(training_run_id, 60, "Testing progress")
            self.assertEqual(database.list_training_runs()[0]["progress_percent"], 60)
            database.finish_training_run(training_run_id, status="completed", model_version_id=model_id)
            self.assertEqual(database.list_training_runs()[0]["progress_stage"], "Completed")
            database.log_audit("TEST_EVENT", "SQLite persistence test.")
            reviewed = database.list_candidates(topic="Health and Medicine")[0]
            self.assertEqual(reviewed["candidate_sample_id"], candidate_id)
            self.assertEqual(reviewed["evidence_status"], "verified")
            summary = database.candidate_topic_summary()["totals"]
            self.assertEqual(summary["candidates"], 2)
            self.assertEqual(summary["misleading"], 1)
            self.assertEqual(summary["non_misleading"], 1)
            self.assertEqual(database.export_candidates()[0]["topic"], "Health and Medicine")
            self.assertEqual(database.list_audits()[0]["action"], "TEST_EVENT")
            self.assertEqual(database.list_evidence(candidate_id)[0]["claim_match_status"], "matched")
            self.assertEqual(database.get_active_model()["model_version_id"], model_id)
            self.assertEqual(database.sprint_stats()["candidate_samples"], 2)

            imported = database.import_validated_dataset(
                "import-v1",
                [{
                    "text": "Validated imported claim",
                    "label": "Non-Misleading",
                    "topic": "Other and General",
                    "claim_group_id": "claim-imported",
                    "evidence_url": "https://example.com/imported-evidence",
                    "partition_name": None,
                    "language": "Taglish",
                }],
                created_by="admin",
            )
            self.assertEqual(imported["imported"], 1)
            self.assertEqual(sum(imported["partitions"].values()), 1)

    def test_core_schema_is_versioned(self):
        schema = " ".join(table.name for table in database.metadata.sorted_tables)
        for table in ("AdminUsers", "CandidateSamples", "AuditLogs"):
            self.assertIn(table, schema)
        self.assertIn("training_status", database.candidate_samples.c)
        self.assertIn("topic_confidence", database.candidate_samples.c)
        self.assertIn("progress_percent", database.training_runs.c)
        self.assertIn("progress_stage", database.training_runs.c)
        self.assertEqual(
            database.candidate_samples.c.training_status.server_default.arg,
            "not_training_data",
        )


if __name__ == "__main__":
    unittest.main()
