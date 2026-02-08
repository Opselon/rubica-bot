from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any
import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from install import render_env
from app.cli.doctor_utils import mask_secret, parse_sqlite_path

app = typer.Typer(help="Rubika Bot control CLI")
console = Console()


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True)


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def prompt_value(label: str, default: str | None = None, required: bool = False) -> str:
    while True:
        value = Prompt.ask(label, default=default or "").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        console.print("❌ مقدار الزامی است.", style="red")


def update_webhook_endpoints(token: str, api_base_url: str, webhook_base_url: str) -> dict[str, Any]:
    webhook_base = webhook_base_url.rstrip("/")
    urls = [f"{webhook_base}/receiveUpdate", f"{webhook_base}/receiveInlineMessage"]
    url = f"{api_base_url.rstrip('/')}/{token}/updateBotEndpoints"
    response = httpx.post(url, json={"urls": urls}, timeout=10)
    response.raise_for_status()
    return response.json()


def _check_result(ok: bool, label: str, detail: str, fix: str | None = None) -> Table:
    status = "✅" if ok else "❌"
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left")
    table.add_column(justify="left")
    table.add_row(status, Text(label, style="bold"))
    table.add_row("", detail)
    if fix:
        table.add_row("", Text(f"Fix: {fix}", style="yellow"))
    return table


def _warning_result(label: str, detail: str, fix: str | None = None) -> Table:
    status = "⚠️"
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left")
    table.add_column(justify="left")
    table.add_row(status, Text(label, style="bold"))
    table.add_row("", detail)
    if fix:
        table.add_row("", Text(f"Fix: {fix}", style="yellow"))
    return table


@app.command()
def install(
    project_path: Path = typer.Option(Path("."), "--project-path"),
    token: str = typer.Option("", "--token"),
    owner_id: str = typer.Option("", "--owner-id"),
    webhook_base_url: str = typer.Option("", "--webhook-base-url"),
    api_base_url: str = typer.Option("https://botapi.rubika.ir/v3", "--api-base-url"),
    service_name: str = typer.Option("rubika-bot", "--service-name"),
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8080, "--port"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
    install_deps: bool = typer.Option(False, "--install-deps"),
    with_nginx: bool = typer.Option(False, "--with-nginx"),
    with_ssl: bool = typer.Option(False, "--with-ssl"),
    systemd_install: bool = typer.Option(False, "--systemd-install"),
    run_tests: bool = typer.Option(True, "--run-tests"),
    register_webhook: bool = typer.Option(True, "--register-webhook"),
) -> None:
    install_script = project_path / "install.py"
    if not install_script.exists():
        raise typer.BadParameter("install.py یافت نشد.")
    cmd = ["python3", str(install_script)]
    if non_interactive:
        cmd.append("--non-interactive")
    if token:
        cmd += ["--token", token]
    if owner_id:
        cmd += ["--owner-id", owner_id]
    if webhook_base_url:
        cmd += ["--webhook-base-url", webhook_base_url]
    if api_base_url:
        cmd += ["--api-base-url", api_base_url]
    if service_name:
        cmd += ["--service-name", service_name]
    if host:
        cmd += ["--host", host]
    if port:
        cmd += ["--port", str(port)]
    if install_deps:
        cmd.append("--install-deps")
    if with_nginx:
        cmd.append("--with-nginx")
    if with_ssl:
        cmd.append("--with-ssl")
    if systemd_install:
        cmd.append("--systemd-install")
    if not run_tests:
        cmd.append("--no-tests")
    if not register_webhook:
        cmd.append("--no-webhook")
    run(cmd)


@app.command()
def configure(
    path: Path = typer.Option(Path("."), "--path"),
    token: str = typer.Option("", "--token"),
    owner_id: str = typer.Option("", "--owner-id"),
    webhook_base_url: str = typer.Option("", "--webhook-base-url"),
    api_base_url: str = typer.Option("https://botapi.rubika.ir/v3", "--api-base-url"),
    webhook_secret: str = typer.Option("", "--webhook-secret"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    env_path = path / ".env"
    existing = read_env(env_path)
    token = token or prompt_value("TOKEN", existing.get("RUBIKA_BOT_TOKEN"), required=True)
    owner_id = owner_id or prompt_value("OWNER_ID", existing.get("RUBIKA_OWNER_ID"), required=True)
    api_base_url = api_base_url or existing.get("RUBIKA_API_BASE_URL", api_base_url)
    webhook_base_url = webhook_base_url or prompt_value(
        "WEBHOOK_BASE_URL", existing.get("RUBIKA_WEBHOOK_BASE_URL", "")
    )
    webhook_secret = webhook_secret or existing.get("RUBIKA_WEBHOOK_SECRET", "")
    env_text = render_env(
        token=token,
        api_base_url=api_base_url,
        webhook_base_url=webhook_base_url,
        webhook_secret=webhook_secret,
        owner_id=owner_id,
    )
    if env_path.exists() and not force:
        raise typer.BadParameter(".env وجود دارد. برای بازنویسی از --force استفاده کنید.")
    env_path.write_text(env_text, encoding="utf-8")
    console.print("✅ .env ذخیره شد.", style="green")


@app.command("webhook-set")
def webhook_set(
    path: Path = typer.Option(Path("."), "--path"),
    token: str = typer.Option("", "--token"),
    api_base_url: str = typer.Option("", "--api-base-url"),
    webhook_base_url: str = typer.Option("", "--webhook-base-url"),
) -> None:
    env_data = read_env(path / ".env")
    token = token or env_data.get("RUBIKA_BOT_TOKEN") or prompt_value("TOKEN", required=True)
    api_base_url = api_base_url or env_data.get("RUBIKA_API_BASE_URL", "https://botapi.rubika.ir/v3")
    webhook_base_url = webhook_base_url or env_data.get("RUBIKA_WEBHOOK_BASE_URL") or prompt_value(
        "WEBHOOK_BASE_URL", required=True
    )
    result = update_webhook_endpoints(token, api_base_url, webhook_base_url)
    console.print(f"✅ وبهوک ثبت شد: {result}", style="green")


@app.command()
def status(service: str = typer.Option("rubika-bot", "--service")) -> None:
    run(["systemctl", "status", service])


@app.command()
def logs(
    service: str = typer.Option("rubika-bot", "--service"),
    follow: bool = typer.Option(False, "--follow", "-f"),
) -> None:
    cmd = ["journalctl", "-u", service, "-n", "200", "--no-pager"]
    if follow:
        cmd = ["journalctl", "-u", service, "-f"]
    run(cmd)


@app.command()
def update(
    path: Path = typer.Option(Path("/opt/rubika-bot"), "--path"),
    service: str = typer.Option("rubika-bot", "--service"),
    backup: bool = typer.Option(True, "--backup"),
    venv_path: Path = typer.Option(Path(".venv"), "--venv-path"),
    run_tests: bool = typer.Option(False, "--run-tests"),
) -> None:
    if backup:
        backup_path = path.with_suffix(".bak")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(path, backup_path)
    run(["git", "-C", str(path), "pull", "--rebase"])
    python_root = venv_path if venv_path.is_absolute() else path / venv_path
    python = python_root / "bin" / "python"
    if python.exists():
        run([str(python), "-m", "pip", "install", "-r", str(path / "requirements.txt")])
        if run_tests:
            run([str(python), "-m", "pytest", str(path / "tests")])
    run(["systemctl", "restart", service])
    console.print("✅ بروزرسانی انجام شد.", style="green")


@app.command()
def rollback(
    path: Path = typer.Option(Path("/opt/rubika-bot"), "--path"),
    service: str = typer.Option("rubika-bot", "--service"),
) -> None:
    backup_path = path.with_suffix(".bak")
    if not backup_path.exists():
        raise typer.BadParameter("بکاپی برای بازگشت وجود ندارد.")
    if path.exists():
        shutil.rmtree(path)
    shutil.move(backup_path, path)
    run(["systemctl", "restart", service])
    console.print("✅ بازگشت انجام شد.", style="green")


@app.command()
def doctor(
    path: Path = typer.Option(Path("/opt/rubika-bot"), "--path"),
    service: str = typer.Option("rubika-bot", "--service"),
    port: int = typer.Option(8080, "--port"),
    api_base_url: str = typer.Option("", "--api-base-url"),
    send_owner: bool = typer.Option(False, "--send-owner"),
    test_webhook: bool = typer.Option(False, "--test-webhook"),
    apply_webhook: bool = typer.Option(False, "--apply-webhook"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    console.print(Panel.fit("Rubika Bot Doctor", style="bold cyan"))
    env_path = path / ".env"
    env_data = read_env(env_path)
    token = env_data.get("RUBIKA_BOT_TOKEN", "")
    owner_id = env_data.get("RUBIKA_OWNER_ID", "")
    webhook_url = env_data.get("RUBIKA_WEBHOOK_BASE_URL", "")
    api_base = api_base_url or env_data.get("RUBIKA_API_BASE_URL", "https://botapi.rubika.ir/v3")
    db_url = env_data.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("A) System & Prerequisites", style="bold magenta"))
    console.print(section)

    python_ok = sys.version_info >= (3, 10)
    console.print(
        _check_result(
            python_ok,
            "Python Version",
            f"{sys.version.split()[0]}",
            "Upgrade to Python 3.10+",
        )
    )
    venv_active = bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix
    console.print(
        _check_result(
            venv_active,
            "Virtualenv",
            os.environ.get("VIRTUAL_ENV", "not active"),
            "Activate venv: source .venv/bin/activate",
        )
    )
    console.print(
        _check_result(
            path.exists(),
            "Install Path",
            str(path),
            "Ensure /opt/rubika-bot exists or pass --path",
        )
    )
    try:
        disk = shutil.disk_usage(path if path.exists() else Path("/"))
        disk_gb = disk.free / (1024**3)
        console.print(
            _check_result(
                disk_gb > 1.0,
                "Disk Free",
                f"{disk_gb:.2f} GB free",
                "Free up disk space",
            )
        )
    except OSError as exc:
        console.print(_warning_result("Disk Free", f"Unable to read disk: {exc}"))
    try:
        mem_total_kb = 0
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    mem_total_kb = int(line.split()[1])
                    break
        mem_gb = mem_total_kb / (1024**2)
        console.print(
            _check_result(
                mem_gb > 0.5,
                "RAM Available",
                f"{mem_gb:.2f} GB available",
                "Close heavy processes or increase RAM",
            )
        )
    except OSError as exc:
        console.print(_warning_result("RAM Available", f"Unable to read /proc/meminfo: {exc}"))
    try:
        socket.gethostbyname("botapi.rubika.ir")
        console.print(_check_result(True, "DNS", "botapi.rubika.ir resolved"))
    except OSError as exc:
        console.print(_check_result(False, "DNS", str(exc), "Fix DNS or network connectivity"))

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("B) Service & Runtime", style="bold magenta"))
    console.print(section)

    try:
        status = run(["systemctl", "show", service, "-p", "ActiveState", "-p", "NRestarts", "-p", "ExecMainStatus"])
        status_data = dict(line.split("=", 1) for line in status.stdout.splitlines() if "=" in line)
        active = status_data.get("ActiveState") == "active"
        console.print(
            _check_result(
                active,
                "systemd",
                json.dumps(status_data, ensure_ascii=False),
                f"systemctl restart {service}",
            )
        )
    except subprocess.CalledProcessError as exc:
        console.print(_warning_result("systemd", f"systemctl failed: {exc}", "Check service name and permissions"))
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            console.print(_check_result(True, "App Port", f"127.0.0.1:{port} open"))
    except OSError as exc:
        console.print(_check_result(False, "App Port", str(exc), "Check app service and --port"))

    try:
        nginx_status = run(["systemctl", "is-active", "nginx"], check=False)
        nginx_active = nginx_status.returncode == 0
        console.print(
            _check_result(
                nginx_active,
                "Nginx",
                nginx_status.stdout.strip() or nginx_status.stderr.strip(),
                "systemctl restart nginx",
            )
        )
        if nginx_active:
            nginx_test = run(["nginx", "-t"], check=False)
            ok = nginx_test.returncode == 0
            console.print(
                _check_result(
                    ok,
                    "Nginx Config",
                    (nginx_test.stdout or nginx_test.stderr).strip(),
                    "Fix nginx config syntax",
                )
            )
    except FileNotFoundError:
        console.print(_warning_result("Nginx", "nginx not installed"))

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("C) Configuration", style="bold magenta"))
    console.print(section)

    console.print(
        _check_result(
            env_path.exists(),
            ".env file",
            str(env_path),
            "Run rubikactl configure",
        )
    )
    console.print(
        _check_result(
            bool(token),
            "TOKEN",
            mask_secret(token),
            "Set RUBIKA_BOT_TOKEN in .env",
        )
    )
    console.print(
        _check_result(
            bool(owner_id),
            "OWNER_ID",
            owner_id or "missing",
            "Set RUBIKA_OWNER_ID in .env",
        )
    )
    console.print(
        _check_result(
            bool(webhook_url),
            "WEBHOOK_BASE_URL",
            webhook_url or "missing",
            "Set RUBIKA_WEBHOOK_BASE_URL in .env",
        )
    )

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("D) Rubika API", style="bold magenta"))
    console.print(section)

    if token:
        try:
            response = httpx.post(f"{api_base.rstrip('/')}/{token}/getMe", json={}, timeout=10)
            ok = response.status_code == 200
            console.print(
                _check_result(
                    ok,
                    "getMe",
                    response.text[:200],
                    "Check token and network connectivity",
                )
            )
        except httpx.RequestError as exc:
            console.print(_check_result(False, "getMe", str(exc), "Check network connectivity"))
    else:
        console.print(_warning_result("getMe", "Skipped: token missing"))

    if send_owner and token and owner_id:
        if yes or Prompt.ask("Send test message to owner? (y/n)", default="n").lower() == "y":
            try:
                payload = {"chat_id": owner_id, "text": "Rubika doctor test message."}
                response = httpx.post(f"{api_base.rstrip('/')}/{token}/sendMessage", json=payload, timeout=10)
                console.print(
                    _check_result(
                        response.status_code == 200,
                        "sendMessage",
                        response.text[:200],
                        "Check owner ID permissions",
                    )
                )
            except httpx.RequestError as exc:
                console.print(_check_result(False, "sendMessage", str(exc), "Check network connectivity"))

    if test_webhook and token and webhook_url:
        urls = [f"{webhook_url.rstrip('/')}/receiveUpdate", f"{webhook_url.rstrip('/')}/receiveInlineMessage"]
        if apply_webhook:
            try:
                response = httpx.post(
                    f"{api_base.rstrip('/')}/{token}/updateBotEndpoints",
                    json={"urls": urls},
                    timeout=10,
                )
                console.print(
                    _check_result(
                        response.status_code == 200,
                        "updateBotEndpoints",
                        response.text[:200],
                        "Check webhook URL reachability",
                    )
                )
            except httpx.RequestError as exc:
                console.print(_check_result(False, "updateBotEndpoints", str(exc), "Check network connectivity"))
        else:
            console.print(_warning_result("updateBotEndpoints", f"Dry-run: {urls}", "Add --apply-webhook"))

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("E) Queue & Worker", style="bold magenta"))
    console.print(section)

    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health/queue", timeout=5)
        if response.status_code == 200:
            data = response.json()
            console.print(
                _check_result(
                    True,
                    "Queue Status",
                    json.dumps(data.get("queue", {}), ensure_ascii=False),
                )
            )
            workers = data.get("workers", [])
            console.print(
                _check_result(
                    True,
                    "Workers",
                    json.dumps(workers, ensure_ascii=False),
                )
            )
            console.print(
                _check_result(
                    True,
                    "Processing Stats",
                    json.dumps(data.get("stats", {}), ensure_ascii=False),
                )
            )
        else:
            console.print(_check_result(False, "Queue Status", response.text, "Check app service health"))
    except httpx.RequestError as exc:
        console.print(_warning_result("Queue Status", str(exc), "Ensure app is running"))

    section = Table.grid(padding=(1, 1))
    section.add_row(Text("F) SQLite Database", style="bold magenta"))
    console.print(section)

    db_path = parse_sqlite_path(db_url)
    try:
        if not Path(db_path).exists():
            console.print(_check_result(False, "Database File", db_path, "Check RUBIKA_DB_URL or migrations"))
        else:
            size_mb = Path(db_path).stat().st_size / (1024**2)
            console.print(_check_result(True, "Database File", f"{db_path} ({size_mb:.2f} MB)"))
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                quick_check = conn.execute("PRAGMA quick_check;").fetchone()
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                console.print(
                    _check_result(
                        quick_check and quick_check[0] == "ok",
                        "SQLite quick_check",
                        str(quick_check[0] if quick_check else "unknown"),
                        "Restore from backup or recreate DB",
                    )
                )
                console.print(
                    _check_result(
                        True,
                        "Tables",
                        ", ".join(row[0] for row in tables),
                    )
                )
                last_message = conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1;").fetchone()
                detail = dict(last_message) if last_message else {}
                console.print(_check_result(True, "Last Message", json.dumps(detail, ensure_ascii=False)))
    except Exception as exc:  # noqa: BLE001
        console.print(_check_result(False, "SQLite", str(exc), "Check DB permissions or corruption"))


if __name__ == "__main__":
    app()
