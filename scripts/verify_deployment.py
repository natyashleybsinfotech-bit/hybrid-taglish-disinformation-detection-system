"""Static deployment checks. Does not substitute for a Docker build or stack test."""
import ast
import hashlib
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert set(services) == {"database", "api", "admin", "migrate", "proxy"}
    assert "ports" not in services["database"], "Database must not be exposed"
    assert "suriph-database:/var/lib/mysql" in services["database"]["volumes"]
    assert "suriph-database" in compose["volumes"]
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"]
    assert services["admin"]["ports"] == ["127.0.0.1:8080:80"]
    assert services["migrate"]["profiles"] == ["maintenance"]
    assert services["migrate"]["command"] == ["python", "-m", "src.manage", "provision"]
    for name in ("api", "migrate", "admin"):
        build = services[name]["build"]
        context = ROOT / (build if isinstance(build, str) else build["context"])
        assert (context / "Dockerfile").is_file()
        assert (context / ".dockerignore").is_file()
    environment = services["api"]["environment"]
    assert environment["SURI_AUTO_MIGRATE"] == "false"
    for name in ("MARIADB_ROOT_PASSWORD", "MARIADB_PASSWORD", "MARIADB_USER"):
        assert environment[name] == "", f"Runtime must not receive {name}"
    mounts = services["api"]["volumes"]
    artifact_mounts = [entry for entry in mounts if ":/app/artifacts/" in entry]
    assert len(artifact_mounts) == 5
    for entry in artifact_mounts:
        source, target, mode = entry.split(":")
        assert (ROOT / source).exists(), f"Required local artifact missing: {source}"
        assert target.startswith("/app/artifacts/") and mode == "ro"
        assert not any(name in source for name in ("model_1", "model_2", "model_3", "records"))
    artifact = ROOT / "backend-api/models/TRAINING RESULTS/models/model_4.joblib"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = json.loads((artifact.parents[1] / "run_manifest.json").read_text())
    assert manifest["run_id"] == "20261011T235112Z"
    assert digest == "72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c"
    dockerfile = (ROOT / "backend-api/Dockerfile").read_text()
    assert '"--workers", "1"' in dockerfile
    assert "COPY src ./src" in dockerfile and "archive" not in dockerfile
    retired = {"train_model", "training_worker", "embedding_extractor",
               "feature_extractor", "preprocessing", "data_loader", "taglish_filter", "mock_classifier"}
    for path in (ROOT / "backend-api/src").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [alias.name for alias in node.names]
            assert not any(name.split(".")[0] in retired for name in names), path.name
    maintenance_service = (ROOT / "deploy/suriph-maintenance.service").read_text()
    maintenance_timer = (ROOT / "deploy/suriph-maintenance.timer").read_text()
    assert "python -m src.manage purge-research" in maintenance_service
    assert "database_backup.py --retention-days 7" in maintenance_service
    assert "OnCalendar=*-*-* 02:00:00" in maintenance_timer and "Persistent=true" in maintenance_timer
    docker_available = shutil.which("docker") is not None
    result = {"static_checks_passed": True, "artifact_sha256": digest,
              "artifact_mounts": 5, "api_workers": 1, "retired_runtime_imports": 0,
              "database_exposed": False, "docker_build_tested": False,
              "compose_stack_tested": False, "tls_tested": False,
              "maintenance_timer_checked": True, "backup_retention_days": 7,
              "docker_available": docker_available,
              "limitation": "YAML, paths, maintenance schedule and invariants checked locally; Docker is not installed." if not docker_available else "Static checks passed; run the documented Docker build and stack checks separately."}
    (ROOT / "docs/DEPLOYMENT-VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
