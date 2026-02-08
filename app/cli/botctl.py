from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from app.db import Repository, ensure_schema

DEFAULT_DB_URL = "sqlite:///data/bot.db"

console = Console()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def deploy(args: argparse.Namespace) -> None:
    target_path = Path(args.path).expanduser().resolve()
    source_path = Path(args.source).expanduser().resolve()
    if target_path.exists():
        backup = target_path.with_suffix(".bak")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(target_path, backup)
    shutil.copytree(source_path, target_path)
    run([args.python, "-m", "pip", "install", "-r", str(target_path / "requirements.txt")])
    run([args.python, "-m", "pytest", str(target_path / "tests")])
    run(["systemctl", "restart", args.service])


def rollback(args: argparse.Namespace) -> None:
    target_path = Path(args.path).expanduser().resolve()
    backup = target_path.with_suffix(".bak")
    if backup.exists():
        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.move(backup, target_path)
        run(["systemctl", "restart", args.service])


def status(args: argparse.Namespace) -> None:
    run(["systemctl", "status", args.service])


def logs(args: argparse.Namespace) -> None:
    run(["journalctl", "-u", args.service, "-n", "200", "--no-pager"])


def _resolve_db_path(db_url: str) -> str:
    return db_url.replace("sqlite:///", "", 1) if db_url.startswith("sqlite:///") else db_url


def _prompt_value(label: str, default: Optional[str] = None, secret: bool = False) -> str:
    if secret:
        return Prompt.ask(label, default=default, password=True)
    return Prompt.ask(label, default=default)


def setup(args: argparse.Namespace) -> None:
    console.print(Panel.fit("⚙️ راه‌اندازی سریع روبیکا بات", style="cyan"))
    db_url = args.db_url or DEFAULT_DB_URL
    db_path = _resolve_db_path(db_url)
    ensure_schema(db_path)
    repo = Repository(db_path)

    bot_token = _prompt_value("توکن بات", repo.get_setting("bot_token") or None, secret=True)
    api_base_url = _prompt_value(
        "آدرس API",
        repo.get_setting("api_base_url") or "https://botapi.rubika.ir/v3",
    )
    webhook_base_url = _prompt_value(
        "دامنه وبهوک (مثال: https://your-domain.example)",
        repo.get_setting("webhook_base_url") or "",
    )
    webhook_secret = _prompt_value(
        "Secret وبهوک (اختیاری)",
        repo.get_setting("webhook_secret") or "",
        secret=True,
    )

    repo.set_setting("bot_token", bot_token)
    repo.set_setting("api_base_url", api_base_url)
    if webhook_base_url:
        repo.set_setting("webhook_base_url", webhook_base_url)
    if webhook_secret:
        repo.set_setting("webhook_secret", webhook_secret)

    console.print("[green]✅ تنظیمات ذخیره شد.[/green]")
    if Confirm.ask("آیا می‌خواهید سرویس را همین حالا اجرا کنید؟", default=False):
        run_server(args, db_url=db_url)


def run_server(args: argparse.Namespace, db_url: Optional[str] = None) -> None:
    db_url = db_url or args.db_url or DEFAULT_DB_URL
    os.environ.setdefault("RUBIKA_DB_URL", db_url)
    os.environ.setdefault("RUBIKA_REGISTER_WEBHOOK", "true")
    uvicorn_cmd = [
        args.python,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    run(uvicorn_cmd)


def quickstart(args: argparse.Namespace) -> None:
    setup(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="botctl")
    parser.add_argument("--service", default="rubika-bot")
    parser.add_argument("--db-url", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    deploy_parser = sub.add_parser("deploy")
    deploy_parser.add_argument("--path", required=True)
    deploy_parser.add_argument("--source", default=".")
    deploy_parser.add_argument("--python", default="python3")
    deploy_parser.set_defaults(func=deploy)

    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--path", required=True)
    rollback_parser.set_defaults(func=rollback)

    status_parser = sub.add_parser("status")
    status_parser.set_defaults(func=status)

    logs_parser = sub.add_parser("logs")
    logs_parser.set_defaults(func=logs)

    setup_parser = sub.add_parser("setup")
    setup_parser.set_defaults(func=setup)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--host", default="0.0.0.0")
    run_parser.add_argument("--port", default=8080, type=int)
    run_parser.add_argument("--python", default="python3")
    run_parser.set_defaults(func=run_server)

    quickstart_parser = sub.add_parser("quickstart")
    quickstart_parser.add_argument("--host", default="0.0.0.0")
    quickstart_parser.add_argument("--port", default=8080, type=int)
    quickstart_parser.add_argument("--python", default="python3")
    quickstart_parser.set_defaults(func=quickstart)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
