import asyncio
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from src.traffic_limits import TrafficLimits


class ProductionConfigTests(unittest.TestCase):
    def production(self, **overrides):
        values = dict(
            APP_ENV="production", SESSION_SECRET="a" * 48,
            ADMIN_BOOTSTRAP_USERNAME="researcher", ADMIN_BOOTSTRAP_PASSWORD="b" * 32,
            VIEWER_BOOTSTRAP_USERNAME="viewer", VIEWER_BOOTSTRAP_PASSWORD="c" * 32,
            CORS_ORIGINS=("https://admin.suriph.ph",), TRUSTED_HOSTS=("api.suriph.ph",),
            DB_ENGINE="mariadb", DATABASE_URL="mysql+pymysql://suriph:abcdefghijklmnop12345@database/suriph",
            MODEL_REQUIRED=True, MODEL_WARMUP=True, MODEL_PROFILE="20261011T235112Z",
        )
        return patch.multiple(config, **(values | overrides))

    def test_real_settings_pass(self):
        with self.production():
            config.validate_runtime_config()

    def test_placeholder_secrets_and_origins_fail(self):
        for values in (
            {"SESSION_SECRET": "generate-at-least-32-random-characters"},
            {"ADMIN_BOOTSTRAP_PASSWORD": "generate-a-strong-password"},
            {"VIEWER_BOOTSTRAP_PASSWORD": "generate-a-different-strong-password"},
            {"CORS_ORIGINS": ("https://admin.example.com",)},
            {"CORS_ORIGINS": ("http://admin.suriph.ph",)},
            {"ADMIN_BOOTSTRAP_USERNAME": "viewer"},
            {"DATABASE_URL": "mysql+pymysql://suriph:generate-a-password@database/suriph"},
            {"MODEL_WARMUP": False},
        ):
            with self.subTest(values=values), self.production(**values), self.assertRaises(RuntimeError):
                config.validate_runtime_config()

    def test_local_candidate_profile_is_rejected_in_production(self):
        with self.production(MODEL_PROFILE="full-cleaned-20261023T022416Z"), self.assertRaisesRegex(
            RuntimeError, "local trial only"
        ):
            config.validate_runtime_config()


class DeploymentGeneratorTests(unittest.TestCase):
    def test_generation_is_private_unique_and_non_overwriting(self):
        source = Path(__file__).resolve().parents[2] / "scripts" / "prepare_deployment.py"
        spec = importlib.util.spec_from_file_location("prepare_deployment", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chrome-extension").mkdir()
            (root / ".env.production.example").write_text((source.parents[1] / ".env.production.example").read_text(), encoding="utf-8")
            args = [str(source), "--api-domain", "api.suriph.ph", "--admin-domain", "admin.suriph.ph", "--email", "ops@suriph.ph"]
            output = io.StringIO()
            with patch.object(module, "ROOT", root), patch.object(sys, "argv", args), contextlib.redirect_stdout(output):
                module.main()
                saved = (root / ".env.production").read_text()
                values = dict(line.split("=", 1) for line in saved.splitlines() if "=" in line)
                keys = ("MARIADB_PASSWORD", "MARIADB_ROOT_PASSWORD", "SURI_ADMIN_PASSWORD", "SURI_VIEWER_PASSWORD", "SURI_SESSION_SECRET")
                self.assertEqual(len({values[key] for key in keys}), len(keys))
                for key in keys:
                    self.assertEqual(len(values[key]), 64)
                    self.assertNotIn(values[key], output.getvalue())
                self.assertIn("https://api.suriph.ph", (root / "chrome-extension" / ".env.production").read_text())
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    module.main()
                self.assertEqual((root / ".env.production").read_text(), saved)


class TrafficLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_is_limited_but_health_is_not(self):
        async def downstream(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
        limiter = TrafficLimits(downstream)
        async def request(path, method="POST"):
            messages = []
            async def send(message):
                messages.append(message)
            await limiter({"type": "http", "method": method, "path": path, "client": ("127.0.0.1", 123)}, None, send)
            return messages[0]["status"]
        for _ in range(5):
            self.assertEqual(await request("/admin-api/login"), 200)
        self.assertEqual(await request("/admin-api/login"), 429)
        self.assertEqual(await request("/ready", "GET"), 200)

    async def test_busy_screening_is_rejected_and_capacity_recovers(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def downstream(scope, receive, send):
            entered.set()
            await release.wait()
        limiter = TrafficLimits(downstream, concurrency=1)
        scope = {"type": "http", "method": "POST", "path": "/analyze", "client": ("client", 0)}
        messages = []
        async def send(message):
            messages.append(message)
        task = asyncio.create_task(limiter(scope, None, send))
        await entered.wait()
        await limiter(scope, None, send)
        self.assertEqual(messages[0]["status"], 503)
        release.set()
        await task
        self.assertEqual(limiter.active, 0)


if __name__ == "__main__":
    unittest.main()
