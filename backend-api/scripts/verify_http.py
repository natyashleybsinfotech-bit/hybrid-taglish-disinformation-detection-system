"""Launch an isolated real API and test endpoints plus extension HTTP transport."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import threading
import statistics
import argparse
from concurrent.futures import ThreadPoolExecutor
import psutil
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]


def request(base, path, body=None, headers=None):
    req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urlopen(req, timeout=180) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=os.environ.get("SURI_MODEL_PROFILE", ""))
    args = parser.parse_args()
    if args.profile:
        profile_id = args.profile
    else:
        from dotenv import dotenv_values
        profile_id = dotenv_values(BASE / ".env.local").get("SURI_MODEL_PROFILE") or "20261011T235112Z"
    profiles = json.loads((BASE / "src/model_profiles.json").read_text(encoding="utf-8"))["profiles"]
    if profile_id not in profiles:
        raise SystemExit(f"Unknown profile: {profile_id}")
    expected_profile = profiles[profile_id]
    with tempfile.TemporaryDirectory(prefix="suriph-http-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = os.environ | {
            "SURI_LOAD_ENV_FILES": "false", "SURI_APP_ENV": "development",
            "SURI_DATABASE_URL": "", "SURI_DB_HOST": "", "SURI_DB_USER": "",
            "SURI_SQLITE_PATH": str(Path(directory) / "test.db"),
            "SURI_TRUSTED_HOSTS": "localhost,127.0.0.1", "SURI_MODEL_DEVICE": "cpu",
            "SERPER_ENABLED": "false", "GOOGLE_FACT_CHECK_ENABLED": "false",
            "SURI_TRAFFIC_LIMITS": "true",
            "SURI_MODEL_PROFILE": profile_id,
        }
        with (Path(directory) / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=BASE, env=env, stdout=log, stderr=log)
            peak = [0]
            sampling = threading.Event()
            def sample_memory():
                while not sampling.wait(.1):
                    try:
                        parent = psutil.Process(process.pid)
                        peak[0] = max(peak[0], sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)]))
                    except psutil.Error:
                        pass
            monitor = threading.Thread(target=sample_memory, daemon=True); monitor.start()
            try:
                deadline = time.monotonic() + 180
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("API exited: " + (Path(directory) / "server.log").read_text(encoding="utf-8")[-5000:])
                    try:
                        status, state = request(base, "/ready")
                        if status == 200:
                            break
                        raise RuntimeError(json.dumps(state))
                    except URLError:
                        if time.monotonic() > deadline:
                            raise RuntimeError("API startup timed out")
                        time.sleep(.5)
                print("Actual API ready on CPU", flush=True)
                assert state["model"]["classifier"] == Path(expected_profile["classifier"]).name
                assert state["model"]["training_run_id"] == profile_id
                assert state["model"]["sha256"] == expected_profile["classifier_sha256"]
                assert state["model"]["device"] == "cpu"
                for text in ("", " \n\t "):
                    status, body = request(base, "/analyze", {"text": text})
                    assert status == 422 and "model_score" not in body
                novel = f"Bagong integration check {time.time_ns()}. Suriin natin ang source ng balita."
                status, first = request(base, "/analyze", {"text": novel})
                assert status == 200 and first["analyzed_text"] == novel
                assert first["predicted_class"] == int(first["model_score"] >= state["model"]["decision_threshold"])
                assert "research_receipt" not in first and "storage_status" not in first
                (BASE.parent / 'tmp' / 'ui-real-result.json').write_text(json.dumps(first), encoding='utf-8')
                long_text = "Basahin natin ang buong artikulo at suriin ang source. " * 100 + "UNIQUE_TAIL_73129"
                status, long_result = request(base, "/analyze", {"text": long_text})
                assert status == 200 and long_result["analyzed_text"] == long_text
                assert long_result["content_token_count"] > 510 and long_result["chunk_count"] > 1
                node = shutil.which("node")
                if not node:
                    raise RuntimeError("Node.js is required for the extension transport check")
                subprocess.run([node, "tests/connection.mjs"], cwd=BASE.parent / "chrome-extension",
                               env=os.environ | {
                                   "SURI_TEST_API_URL": base,
                                   "SURI_TEST_RUN_ID": profile_id,
                                   "SURI_TEST_THRESHOLD": str(expected_profile["expected_threshold"]),
                                   "SURI_TEST_ARTIFACT_SHA256": expected_profile["classifier_sha256"],
                               }, check=True)
                timings=[]; inference=[]
                for index in range(5):
                    began=time.perf_counter()
                    status, measured=request(base,'/analyze',{'text':f'Benchmark {index}: Basahin muna ang buong balita bago magbahagi.'})
                    assert status == 200
                    timings.append((time.perf_counter()-began)*1000); inference.append(measured['timings_ms']['inference'])
                barrier=threading.Barrier(3)
                def concurrent(index):
                    barrier.wait()
                    return request(base,'/analyze',{'text':long_text + str(index)})[0]
                with ThreadPoolExecutor(max_workers=3) as pool:
                    concurrent_statuses=list(pool.map(concurrent,range(3)))
                assert all(status in (200,503) for status in concurrent_statuses) and 200 in concurrent_statuses
                profile={'device':'cpu','api_workers':1,'inference_threads':4,'max_in_flight_requests':2,
                         'platform':sys.platform,'processor':psutil.cpu_count(logical=True),'short_requests':len(timings),
                         'short_http_ms':timings,'short_http_median_ms':statistics.median(timings),
                         'short_inference_ms':inference,'long_inference_ms':long_result['timings_ms']['inference'],
                         'long_content_tokens':long_result['content_token_count'],'peak_process_tree_rss_mib':peak[0]/1024**2,
                         'three_concurrent_statuses':concurrent_statuses,'retrieval':'disabled; live provider measured separately',
                         'scope':'Native Windows; production worker/thread/admission settings; SQLite test DB. Not a Linux Docker capacity guarantee.'}
                (BASE.parent/'docs/RESOURCE-MEASUREMENTS.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
                report = {"passed": True, "live_http": True, "device": state["model"]["device"],
                          "empty_input_status": 422, "long_text_chunks": long_result["chunk_count"],
                          "long_text_content_tokens": long_result["content_token_count"],
                          "novel_input_processed": "passed", "screening_storage_fields_absent": True,
                          "extension_transport": "passed", "browser_ui_tested": False}
                output = BASE.parent / "docs" / "HYBRID-HTTP-VERIFICATION.json"
                output.parent.mkdir(exist_ok=True)
                output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(json.dumps(report, indent=2), flush=True)
            finally:
                sampling.set(); monitor.join(timeout=2)
                if os.name == "nt" and process.poll() is None:
                    # Windows venv python.exe can be a redirector with a child.
                    # Stop the test process tree so neither server nor log survives.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
