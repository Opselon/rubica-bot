from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _SilentHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _start_static_server(directory: Path) -> tuple[ThreadingHTTPServer, int]:
    port = _find_free_port()

    class Handler(_SilentHandler):
        def do_GET(self) -> None:  # noqa: N802
            file_path = directory / self.path.lstrip("/")
            if not file_path.exists():
                self.send_response(404)
                self.end_headers()
                return
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _start_api_server() -> tuple[ThreadingHTTPServer, str]:
    port = _find_free_port()

    class Handler(_SilentHandler):
        def do_POST(self) -> None:  # noqa: N802
            response = {"ok": True, "result": {"id": 1, "first_name": "TestBot"}}
            payload = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def _wait_for_health(url: str, timeout: float = 20) -> None:
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("health endpoint did not become ready")


@pytest.mark.install
def test_one_line_install(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    install_path = tmp_path / "rubica-install"
    source_repo = tmp_path / "source-repo"
    shutil.copytree(
        repo_root,
        source_repo,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
    )
    subprocess.run(["git", "-C", str(source_repo), "init"], check=True)
    subprocess.run(["git", "-C", str(source_repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(source_repo), "commit", "-m", "test snapshot"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    static_server, static_port = _start_static_server(repo_root)
    api_server, api_base_url = _start_api_server()

    try:
        cmd = (
            f"curl -fsSL http://127.0.0.1:{static_port}/install.sh | "
            "bash -s -- "
            "--non-interactive "
            "--test-mode "
            f"--install-path {install_path} "
            "--token TEST_TOKEN "
            "--owner-id 123456 "
            f"--base-url {api_base_url} "
            "--webhook-base-url https://example.test "
            "--with-nginx "
            "--systemd-install "
            "--no-tests "
            "--no-webhook"
        )
        env = os.environ.copy()
        env["RUBIKA_INSTALL_REPO"] = str(source_repo)
        subprocess.run(["bash", "-c", cmd], check=True, env=env)
    finally:
        static_server.shutdown()

    env_file = install_path / ".env"
    assert env_file.exists()
    env_text = env_file.read_text(encoding="utf-8")
    assert "RUBIKA_BOT_TOKEN=TEST_TOKEN" in env_text
    assert "RUBIKA_OWNER_ID=123456" in env_text
    assert "RUBIKA_WEBHOOK_BASE_URL=https://example.test" in env_text
    assert (install_path / "rubika-bot.service").exists()
    assert (install_path / ".mock" / "systemd" / "rubika-bot.service").exists()
    assert (install_path / ".mock" / "nginx" / "sites-available" / "rubika-bot.conf").exists()

    venv_python = install_path / ".venv" / "bin" / "python"
    app_port = _find_free_port()
    env = os.environ.copy()
    env["RUBIKA_BOT_TOKEN"] = "TEST_TOKEN"
    env["RUBIKA_OWNER_ID"] = "123456"
    env["RUBIKA_REGISTER_WEBHOOK"] = "false"
    env["RUBIKA_API_BASE_URL"] = api_base_url
    process = subprocess.Popen(
        [
            str(venv_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(app_port),
        ],
        cwd=install_path,
        env=env,
    )
    try:
        _wait_for_health(f"http://127.0.0.1:{app_port}/health")
        doctor_script = (
            "from pathlib import Path; "
            "from app.cli import rubikactl; "
            f"rubikactl.doctor(path=Path('{install_path}'), "
            "service='rubika-bot', "
            f"port={app_port}, "
            f"api_base_url='{api_base_url}', "
            "skip_systemd=True, "
            "skip_nginx=True, "
            "skip_queue=False, "
            "skip_rubika=False, "
            "skip_dns=True, "
            "skip_db=True)"
        )
        doctor = subprocess.run(
            [str(venv_python), "-c", doctor_script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=install_path,
        )
        assert "Overall: OK" in doctor.stdout
    finally:
        process.terminate()
        process.wait(timeout=10)
        api_server.shutdown()
