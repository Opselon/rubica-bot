from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any
import httpx
import typer
from rich.console import Console
from rich.prompt import Prompt

from install import render_env

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


if __name__ == "__main__":
    app()
