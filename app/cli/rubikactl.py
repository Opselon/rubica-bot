import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import httpx
import sqlite3
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from install import render_env
from app.cli.doctor_utils import mask_secret, parse_sqlite_path

app = typer.Typer(help="Rubika Bot control CLI", rich_markup_mode=None)
console = Console()
db_app = typer.Typer(help="SQLite maintenance commands", rich_markup_mode=None)
fix_app = typer.Typer(help="Fix common issues", rich_markup_mode=None)
queue_app = typer.Typer(help="Queue utilities", rich_markup_mode=None)

app.add_typer(db_app, name="db")
app.add_typer(fix_app, name="fix")
app.add_typer(queue_app, name="queue")


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


def _open_db(db_url: str) -> tuple[str, sqlite3.Connection]:
    db_path = parse_sqlite_path(db_url)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return db_path, conn


def _db_record_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in ["incoming_updates", "messages", "admins", "filters"]:
        try:
            row = conn.execute(f"SELECT COUNT(1) AS total FROM {table};").fetchone()
            counts[table] = int(row["total"] if row else 0)
        except sqlite3.Error:
            counts[table] = 0
    return counts


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


@dataclass
class DoctorCheck:
    section: str
    status: str
    label: str
    detail: str
    fix: str | None = None


def _add_check(
    checks: list[DoctorCheck],
    section: str,
    ok: bool,
    label: str,
    detail: str,
    fix: str | None = None,
) -> None:
    status = "ok" if ok else "fail"
    checks.append(DoctorCheck(section=section, status=status, label=label, detail=detail, fix=fix))


def _add_warning(
    checks: list[DoctorCheck],
    section: str,
    label: str,
    detail: str,
    fix: str | None = None,
) -> None:
    checks.append(DoctorCheck(section=section, status="warn", label=label, detail=detail, fix=fix))


def _render_doctor_tables(checks: list[DoctorCheck]) -> tuple[int, int]:
    status_icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    status_style = {"ok": "green", "warn": "yellow", "fail": "red"}
    failures = 0
    warnings = 0
    for section in dict.fromkeys(check.section for check in checks):
        console.print(Panel.fit(section, style="bold cyan"))
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", width=6)
        table.add_column("Check", style="bold")
        table.add_column("Detail")
        table.add_column("Fix")
        for check in [item for item in checks if item.section == section]:
            if check.status == "fail":
                failures += 1
            if check.status == "warn":
                warnings += 1
            fix_text = f"Fix: {check.fix}" if check.fix else "-"
            table.add_row(
                Text(status_icon[check.status], style=status_style[check.status]),
                check.label,
                check.detail,
                fix_text,
            )
        console.print(table)
    return failures, warnings


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
    skip_systemd: bool = typer.Option(False, "--skip-systemd"),
    skip_nginx: bool = typer.Option(False, "--skip-nginx"),
    skip_queue: bool = typer.Option(False, "--skip-queue"),
    skip_rubika: bool = typer.Option(False, "--skip-rubika"),
    skip_dns: bool = typer.Option(False, "--skip-dns"),
    skip_db: bool = typer.Option(False, "--skip-db"),
) -> None:
    console.print(Panel.fit("Rubika Bot Doctor", style="bold cyan"))
    checks: list[DoctorCheck] = []
    env_path = path / ".env"
    env_data = read_env(env_path)
    token = env_data.get("RUBIKA_BOT_TOKEN", "")
    owner_id = env_data.get("RUBIKA_OWNER_ID", "")
    webhook_url = env_data.get("RUBIKA_WEBHOOK_BASE_URL", "")
    api_base = api_base_url or env_data.get("RUBIKA_API_BASE_URL", "https://botapi.rubika.ir/v3")
    db_url = env_data.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")

    section = "A) System & Prerequisites"

    python_ok = sys.version_info >= (3, 10)
    _add_check(
        checks,
        section,
        python_ok,
        "Python Version",
        f"{sys.version.split()[0]}",
        "Upgrade to Python 3.10+",
    )
    venv_active = bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix
    _add_check(
        checks,
        section,
        venv_active,
        "Virtualenv",
        os.environ.get("VIRTUAL_ENV", "not active"),
        "Activate venv: source .venv/bin/activate",
    )
    _add_check(
        checks,
        section,
        path.exists(),
        "Install Path",
        str(path),
        "Ensure /opt/rubika-bot exists or pass --path",
    )
    try:
        disk = shutil.disk_usage(path if path.exists() else Path("/"))
        disk_gb = disk.free / (1024**3)
        _add_check(
            checks,
            section,
            disk_gb > 1.0,
            "Disk Free",
            f"{disk_gb:.2f} GB free",
            "Free up disk space",
        )
    except OSError as exc:
        _add_warning(checks, section, "Disk Free", f"Unable to read disk: {exc}")
    try:
        mem_total_kb = 0
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    mem_total_kb = int(line.split()[1])
                    break
        mem_gb = mem_total_kb / (1024**2)
        _add_check(
            checks,
            section,
            mem_gb > 0.5,
            "RAM Available",
            f"{mem_gb:.2f} GB available",
            "Close heavy processes or increase RAM",
        )
    except OSError as exc:
        _add_warning(checks, section, "RAM Available", f"Unable to read /proc/meminfo: {exc}")
    if skip_dns:
        _add_warning(checks, section, "DNS", "Skipped", "Remove --skip-dns to validate DNS")
    else:
        try:
            socket.gethostbyname("botapi.rubika.ir")
            _add_check(checks, section, True, "DNS", "botapi.rubika.ir resolved")
        except OSError as exc:
            _add_check(checks, section, False, "DNS", str(exc), "Fix DNS or network connectivity")

    section = "B) Service & Runtime"

    if skip_systemd:
        _add_warning(checks, section, "systemd", "Skipped", "Remove --skip-systemd to check service")
    else:
        try:
            status = subprocess.run(
                ["systemctl", "show", service, "-p", "ActiveState", "-p", "NRestarts", "-p", "ExecMainStatus"],
                check=True,
                text=True,
                capture_output=True,
            )
            status_data = dict(line.split("=", 1) for line in status.stdout.splitlines() if "=" in line)
            active = status_data.get("ActiveState") == "active"
            _add_check(
                checks,
                section,
                active,
                "systemd",
                json.dumps(status_data, ensure_ascii=False),
                f"systemctl restart {service}",
            )
        except subprocess.CalledProcessError as exc:
            _add_warning(checks, section, "systemd", f"systemctl failed: {exc}", "Check service name and permissions")
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            _add_check(checks, section, True, "App Port", f"127.0.0.1:{port} open")
    except OSError as exc:
        _add_check(checks, section, False, "App Port", str(exc), "Check app service and --port")

    if skip_nginx:
        _add_warning(checks, section, "Nginx", "Skipped", "Remove --skip-nginx to check Nginx")
    else:
        try:
            nginx_status = subprocess.run(
                ["systemctl", "is-active", "nginx"],
                check=False,
                text=True,
                capture_output=True,
            )
            nginx_active = nginx_status.returncode == 0
            _add_check(
                checks,
                section,
                nginx_active,
                "Nginx",
                nginx_status.stdout.strip() or nginx_status.stderr.strip(),
                "systemctl restart nginx",
            )
            if nginx_active:
                nginx_test = subprocess.run(["nginx", "-t"], check=False, text=True, capture_output=True)
                ok = nginx_test.returncode == 0
                _add_check(
                    checks,
                    section,
                    ok,
                    "Nginx Config",
                    (nginx_test.stdout or nginx_test.stderr).strip(),
                    "Fix nginx config syntax",
                )
        except FileNotFoundError:
            _add_warning(checks, section, "Nginx", "nginx not installed")

    section = "C) Configuration"

    _add_check(
        checks,
        section,
        env_path.exists(),
        ".env file",
        str(env_path),
        "Run rubikactl configure",
    )
    _add_check(
        checks,
        section,
        bool(token),
        "TOKEN",
        mask_secret(token),
        "Set RUBIKA_BOT_TOKEN in .env",
    )
    _add_check(
        checks,
        section,
        bool(owner_id),
        "OWNER_ID",
        owner_id or "missing",
        "Set RUBIKA_OWNER_ID in .env",
    )
    _add_check(
        checks,
        section,
        bool(webhook_url),
        "WEBHOOK_BASE_URL",
        webhook_url or "missing",
        "Set RUBIKA_WEBHOOK_BASE_URL in .env",
    )

    section = "D) Rubika API"

    if skip_rubika:
        _add_warning(checks, section, "getMe", "Skipped", "Remove --skip-rubika to validate API")
    elif token:
        try:
            response = httpx.post(f"{api_base.rstrip('/')}/{token}/getMe", json={}, timeout=10)
            ok = response.status_code == 200
            _add_check(
                checks,
                section,
                ok,
                "getMe",
                response.text[:200],
                "Check token and network connectivity",
            )
        except httpx.RequestError as exc:
            _add_check(checks, section, False, "getMe", str(exc), "Check network connectivity")
    else:
        _add_warning(checks, section, "getMe", "Skipped: token missing")

    if send_owner and token and owner_id:
        if yes or Prompt.ask("Send test message to owner? (y/n)", default="n").lower() == "y":
            try:
                payload = {"chat_id": owner_id, "text": "Rubika doctor test message."}
                response = httpx.post(f"{api_base.rstrip('/')}/{token}/sendMessage", json=payload, timeout=10)
                _add_check(
                    checks,
                    section,
                    response.status_code == 200,
                    "sendMessage",
                    response.text[:200],
                    "Check owner ID permissions",
                )
            except httpx.RequestError as exc:
                _add_check(checks, section, False, "sendMessage", str(exc), "Check network connectivity")

    if test_webhook and token and webhook_url:
        urls = [f"{webhook_url.rstrip('/')}/receiveUpdate", f"{webhook_url.rstrip('/')}/receiveInlineMessage"]
        if apply_webhook:
            try:
                response = httpx.post(
                    f"{api_base.rstrip('/')}/{token}/updateBotEndpoints",
                    json={"urls": urls},
                    timeout=10,
                )
                _add_check(
                    checks,
                    section,
                    response.status_code == 200,
                    "updateBotEndpoints",
                    response.text[:200],
                    "Check webhook URL reachability",
                )
            except httpx.RequestError as exc:
                _add_check(checks, section, False, "updateBotEndpoints", str(exc), "Check network connectivity")
        else:
            _add_warning(checks, section, "updateBotEndpoints", f"Dry-run: {urls}", "Add --apply-webhook")

    section = "E) Queue & Worker"

    if skip_queue:
        _add_warning(checks, section, "Queue Status", "Skipped", "Remove --skip-queue to validate worker health")
    else:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/health/queue", timeout=5)
            if response.status_code == 200:
                data = response.json()
                _add_check(
                    checks,
                    section,
                    True,
                    "Queue Status",
                    json.dumps(data.get("queue", {}), ensure_ascii=False),
                )
                queue_data = data.get("queue", {})
                if queue_data.get("size", 0) > 500:
                    _add_warning(
                        checks,
                        section,
                        "Queue Backlog",
                        json.dumps(queue_data, ensure_ascii=False),
                        "Consider increasing workers or enabling priority queues",
                    )
                workers = data.get("workers", [])
                _add_check(
                    checks,
                    section,
                    True,
                    "Workers",
                    json.dumps(workers, ensure_ascii=False),
                )
                _add_check(
                    checks,
                    section,
                    True,
                    "Processing Stats",
                    json.dumps(data.get("stats", {}), ensure_ascii=False),
                )
            else:
                _add_check(checks, section, False, "Queue Status", response.text, "Check app service health")
        except httpx.RequestError as exc:
            _add_warning(checks, section, "Queue Status", str(exc), "Ensure app is running")

    section = "F) SQLite Database"

    if skip_db:
        _add_warning(checks, section, "SQLite", "Skipped", "Remove --skip-db to inspect DB health")
    else:
        db_path = parse_sqlite_path(db_url)
        try:
            if not Path(db_path).exists():
                _add_check(checks, section, False, "Database File", db_path, "Check RUBIKA_DB_URL or migrations")
            else:
                size_mb = Path(db_path).stat().st_size / (1024**2)
                _add_check(checks, section, True, "Database File", f"{db_path} ({size_mb:.2f} MB)")
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    quick_check = conn.execute("PRAGMA quick_check;").fetchone()
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                    journal = conn.execute("PRAGMA journal_mode;").fetchone()
                    counts = _db_record_counts(conn)
                    _add_check(
                        checks,
                        section,
                        quick_check and quick_check[0] == "ok",
                        "SQLite quick_check",
                        str(quick_check[0] if quick_check else "unknown"),
                        "Restore from backup or recreate DB",
                    )
                    wal_ok = journal and journal[0].lower() == "wal"
                    if wal_ok:
                        _add_check(
                            checks,
                            section,
                            True,
                            "WAL mode",
                            str(journal[0] if journal else "unknown"),
                        )
                    else:
                        _add_warning(
                            checks,
                            section,
                            "WAL mode",
                            str(journal[0] if journal else "unknown"),
                            "Run: rubikactl fix db",
                        )
                    _add_check(
                        checks,
                        section,
                        True,
                        "Tables",
                        ", ".join(row[0] for row in tables),
                    )
                    _add_check(
                        checks,
                        section,
                        True,
                        "Record counts",
                        json.dumps(counts, ensure_ascii=False),
                    )
                    last_message = conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1;").fetchone()
                    detail = dict(last_message) if last_message else {}
                    _add_check(checks, section, True, "Last Message", json.dumps(detail, ensure_ascii=False))
                retention_hours = int(env_data.get("RUBIKA_INCOMING_UPDATES_RETENTION_HOURS", "48") or 48)
                retention_enabled = env_data.get("RUBIKA_INCOMING_UPDATES_ENABLED", "true").lower() != "false"
                _add_check(
                    checks,
                    section,
                    retention_enabled,
                    "Retention",
                    f"incoming_updates {retention_hours}h",
                    "Set RUBIKA_INCOMING_UPDATES_RETENTION_HOURS and enable janitor",
                )
                if size_mb > 500:
                    _add_warning(
                        checks,
                        section,
                        "Database Size",
                        f"{size_mb:.2f} MB",
                        "Run: rubikactl db cleanup --days 2 --keep-per-chat 10000",
                    )
        except Exception as exc:  # noqa: BLE001
            _add_check(checks, section, False, "SQLite", str(exc), "Check DB permissions or corruption")

    failures, warnings = _render_doctor_tables(checks)
    if failures == 0 and warnings == 0:
        console.print(Panel.fit("Overall: OK", style="bold green"))
    elif failures == 0:
        console.print(Panel.fit("Overall: OK (with warnings)", style="bold yellow"))
    else:
        console.print(Panel.fit("Overall: Issues detected", style="bold red"))


@db_app.command("stats")
def db_stats(path: Path = typer.Option(Path("."), "--path")) -> None:
    env = read_env(path / ".env")
    db_url = env.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")
    db_path, conn = _open_db(db_url)
    try:
        size_mb = Path(db_path).stat().st_size / (1024**2) if Path(db_path).exists() else 0.0
        counts = _db_record_counts(conn)
        console.print(_check_result(True, "DB Size", f"{db_path} ({size_mb:.2f} MB)"))
        console.print(_check_result(True, "Record counts", json.dumps(counts, ensure_ascii=False)))
    finally:
        conn.close()


@db_app.command("cleanup")
def db_cleanup(
    path: Path = typer.Option(Path("."), "--path"),
    days: int = typer.Option(2, "--days"),
    keep_per_chat: int = typer.Option(10000, "--keep-per-chat"),
) -> None:
    env = read_env(path / ".env")
    db_url = env.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")
    _, conn = _open_db(db_url)
    try:
        cutoff = time.time() - days * 86400
        cur_updates = conn.execute("DELETE FROM incoming_updates WHERE received_at < ?;", (cutoff,))
        total_deleted = 0
        chat_rows = conn.execute("SELECT DISTINCT chat_id FROM messages;").fetchall()
        for row in chat_rows:
            chat_id = row["chat_id"]
            cursor = conn.execute(
                """
                DELETE FROM messages
                WHERE chat_id = ?
                AND id NOT IN (
                    SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?
                );
                """,
                (chat_id, chat_id, keep_per_chat),
            )
            total_deleted += cursor.rowcount
        conn.commit()
        console.print(
            _check_result(
                True,
                "Cleanup",
                f"incoming_updates deleted: {cur_updates.rowcount}, messages trimmed: {total_deleted}",
            )
        )
    finally:
        conn.close()


@db_app.command("vacuum")
def db_vacuum(path: Path = typer.Option(Path("."), "--path")) -> None:
    env = read_env(path / ".env")
    db_url = env.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")
    _, conn = _open_db(db_url)
    try:
        console.print(_warning_result("Vacuum", "Running VACUUM may lock the DB."))
        conn.execute("VACUUM;")
        console.print(_check_result(True, "Vacuum", "Completed"))
    finally:
        conn.close()


@db_app.command("optimize")
def db_optimize(path: Path = typer.Option(Path("."), "--path")) -> None:
    env = read_env(path / ".env")
    db_url = env.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")
    _, conn = _open_db(db_url)
    try:
        conn.execute("PRAGMA optimize;")
        console.print(_check_result(True, "Optimize", "Completed"))
    finally:
        conn.close()


@fix_app.command("db")
def fix_db(path: Path = typer.Option(Path("."), "--path")) -> None:
    env = read_env(path / ".env")
    db_url = env.get("RUBIKA_DB_URL", "sqlite:///data/bot.db")
    _, conn = _open_db(db_url)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-20000;")
        conn.execute("PRAGMA busy_timeout=3000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_incoming_updates_received ON incoming_updates (received_at);"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages (chat_id, id DESC);")
        conn.commit()
        console.print(_check_result(True, "Fix DB", "Pragmas and indexes applied"))
    finally:
        conn.close()


@fix_app.command("nginx")
def fix_nginx() -> None:
    nginx_test = run(["nginx", "-t"], check=False)
    if nginx_test.returncode != 0:
        console.print(_check_result(False, "Nginx Config", nginx_test.stderr.strip(), "Fix nginx config syntax"))
        return
    run(["systemctl", "reload", "nginx"])
    console.print(_check_result(True, "Nginx", "Reloaded"))


@fix_app.command("service")
def fix_service(service: str = typer.Option("rubika-bot", "--service")) -> None:
    run(["systemctl", "restart", service])
    console.print(_check_result(True, "Service", f"Restarted {service}"))


@queue_app.command("status")
def queue_status(port: int = typer.Option(8080, "--port")) -> None:
    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health/queue", timeout=5)
        if response.status_code == 200:
            console.print(_check_result(True, "Queue Status", response.text))
            return
        console.print(_check_result(False, "Queue Status", response.text, "Check app service health"))
    except httpx.RequestError as exc:
        console.print(_warning_result("Queue Status", str(exc), "Ensure app is running"))


@queue_app.command("top")
def queue_top(port: int = typer.Option(8080, "--port")) -> None:
    try:
        response = httpx.get(f"http://127.0.0.1:{port}/health/queue", timeout=5)
        if response.status_code == 200:
            data = response.json()
            console.print(_check_result(True, "Queue Snapshot", json.dumps(data, ensure_ascii=False)))
            return
        console.print(_check_result(False, "Queue Snapshot", response.text, "Check app service health"))
    except httpx.RequestError as exc:
        console.print(_warning_result("Queue Snapshot", str(exc), "Ensure app is running"))


@queue_app.command("drain")
def queue_drain(port: int = typer.Option(8080, "--port")) -> None:
    try:
        response = httpx.post(f"http://127.0.0.1:{port}/health/queue/drain", timeout=10)
        if response.status_code == 200:
            console.print(_check_result(True, "Queue Drain", response.text))
            return
        console.print(_check_result(False, "Queue Drain", response.text, "Check app service health"))
    except httpx.RequestError as exc:
        console.print(_warning_result("Queue Drain", str(exc), "Ensure app is running"))


if __name__ == "__main__":
    app()
