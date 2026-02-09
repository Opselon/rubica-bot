from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent
_CONSOLE = None


def get_console():
    global _CONSOLE
    if _CONSOLE is None:
        from rich.console import Console

        _CONSOLE = Console()
    return _CONSOLE


class ValidationError(ValueError):
    pass


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True)


def validate_url(value: str, *, allow_empty: bool = False) -> str:
    if not value:
        if allow_empty:
            return value
        raise ValidationError("URL خالی است.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("URL معتبر نیست.")
    return value.rstrip("/")


def validate_owner_id(value: str) -> str:
    if not value:
        raise ValidationError("OWNER_ID الزامی است.")
    if not value.isdigit():
        raise ValidationError("OWNER_ID باید عددی باشد.")
    return value


def prompt_text(label: str, default: str | None = None, required: bool = False) -> str:
    hint = f" (پیش‌فرض: {default})" if default else ""
    while True:
        from rich.prompt import Prompt

        value = Prompt.ask(f"{label}{hint}", default=default or "")
        value = value.strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        get_console().print("⚠️ مقدار الزامی است. دوباره تلاش کنید.", style="yellow")


def prompt_validated(label: str, validator: Any, default: str | None = None) -> str:
    while True:
        value = prompt_text(label, default=default, required=default is None)
        try:
            return validator(value)
        except ValidationError as exc:
            get_console().print(f"❌ {exc}", style="red")


def prompt_bool(label: str, default: bool = False) -> bool:
    from rich.prompt import Confirm

    return Confirm.ask(label, default=default)


def render_env(
    token: str,
    api_base_url: str,
    webhook_base_url: str,
    webhook_secret: str,
    owner_id: str | None = None,
) -> str:
    lines = [
        f"RUBIKA_BOT_TOKEN={token}",
        f"RUBIKA_API_BASE_URL={api_base_url}",
    ]
    if owner_id:
        lines.append(f"RUBIKA_OWNER_ID={owner_id}")
    if webhook_base_url:
        lines.append(f"RUBIKA_WEBHOOK_BASE_URL={webhook_base_url}")
    if webhook_secret:
        lines.append(f"RUBIKA_WEBHOOK_SECRET={webhook_secret}")
    return "\n".join(lines) + "\n"


def render_systemd_service(
    working_dir: Path,
    venv_path: Path,
    service_name: str,
    host: str,
    port: int,
) -> str:
    python_path = venv_path / "bin" / "python"
    return "\n".join(
        [
            "[Unit]",
            f"Description={service_name}",
            "After=network.target",
            "",
            "[Service]",
            "User=www-data",
            f"WorkingDirectory={working_dir}",
            f"EnvironmentFile={working_dir / '.env'}",
            f"ExecStart={python_path} -m uvicorn app.main:app --host {host} --port {port}",
            "Restart=always",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )


def render_nginx_config(server_name: str, host: str, port: int) -> str:
    backend_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return "\n".join(
        [
            "server {",
            "    listen 80;",
            f"    server_name {server_name};",
            "",
            "    location / {",
            f"        proxy_pass http://{backend_host}:{port};",
            "        proxy_http_version 1.1;",
            "        proxy_set_header Upgrade $http_upgrade;",
            "        proxy_set_header Connection 'upgrade';",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "    }",
            "}",
        ]
    )


def ensure_venv(venv_path: Path) -> None:
    if venv_path.exists():
        return
    cmd = [sys.executable, "-m", "venv"]
    if os.environ.get("RUBIKA_TEST_MODE") == "1":
        cmd.append("--system-site-packages")
    cmd.append(str(venv_path))
    run(cmd)


def install_requirements(venv_path: Path) -> None:
    python = venv_path / "bin" / "python"
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")])


def run_tests(venv_path: Path) -> None:
    python = venv_path / "bin" / "python"
    run([str(python), "-m", "pytest", str(PROJECT_ROOT / "tests")])


def write_file(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"فایل {path} از قبل وجود دارد.")
    path.write_text(content, encoding="utf-8")


def install_dependencies(with_nginx: bool, with_ssl: bool) -> None:
    if os.environ.get("RUBIKA_TEST_MODE") == "1":
        get_console().print("⚠️ Test mode enabled: skipping OS dependency install.", style="yellow")
        return
    if shutil.which("apt-get") is None:
        get_console().print("⚠️ apt-get یافت نشد. نصب پیش‌نیازها رد شد.", style="yellow")
        return
    packages = ["python3", "python3-venv", "python3-pip", "git"]
    if with_nginx:
        packages.append("nginx")
    if with_ssl:
        packages.append("certbot")
        packages.append("python3-certbot-nginx")
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", *packages])


def install_systemd_service(service_path: Path, service_name: str) -> None:
    target_dir = Path(os.environ.get("RUBIKA_SYSTEMD_DIR", "/etc/systemd/system"))
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / service_path.name
    shutil.copy2(service_path, target)
    if os.environ.get("RUBIKA_SKIP_SYSTEMCTL") == "1":
        get_console().print("⚠️ Skipping systemctl calls (RUBIKA_SKIP_SYSTEMCTL=1).", style="yellow")
        return
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", service_name])
    run(["systemctl", "restart", service_name])


def setup_nginx(service_name: str, server_name: str, host: str, port: int, with_ssl: bool) -> None:
    config_text = render_nginx_config(server_name, host, port)
    nginx_root = Path(os.environ.get("RUBIKA_NGINX_DIR", "/etc/nginx"))
    sites_available = nginx_root / "sites-available"
    sites_enabled = nginx_root / "sites-enabled"
    sites_available.mkdir(parents=True, exist_ok=True)
    sites_enabled.mkdir(parents=True, exist_ok=True)
    config_path = sites_available / f"{service_name}.conf"
    config_path.write_text(config_text, encoding="utf-8")
    link_path = sites_enabled / f"{service_name}.conf"
    if not link_path.exists():
        link_path.symlink_to(config_path)
    run(["nginx", "-t"])
    if os.environ.get("RUBIKA_SKIP_SYSTEMCTL") == "1":
        get_console().print("⚠️ Skipping systemctl reload nginx (RUBIKA_SKIP_SYSTEMCTL=1).", style="yellow")
    else:
        run(["systemctl", "reload", "nginx"])
    if with_ssl:
        run(["certbot", "--nginx", "-d", server_name])


def update_webhook_endpoints(token: str, api_base_url: str, webhook_base_url: str) -> dict[str, Any]:
    webhook_base = webhook_base_url.rstrip("/")
    urls = [f"{webhook_base}/receiveUpdate", f"{webhook_base}/receiveInlineMessage"]
    url = f"{api_base_url.rstrip('/')}/{token}/updateBotEndpoints"
    response = httpx.post(url, json={"urls": urls}, timeout=10)
    response.raise_for_status()
    return response.json()


def get_me(token: str, api_base_url: str) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/{token}/getMe"
    response = httpx.post(url, json={}, timeout=10)
    response.raise_for_status()
    return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ویزارد نصب بات روبیکا (محیط مجازی، وابستگی‌ها، .env و سرویس systemd)"
    )
    parser.add_argument("--github-repo", help="آدرس مخزن گیت‌هاب برای دانلود سریع")
    parser.add_argument("--github-ref", help="branch یا tag برای clone")
    parser.add_argument("--install-path", help="مسیر نصب در حالت دانلود از گیت‌هاب")
    parser.add_argument("--install-action", choices=["backup", "remove", "abort"], help="رفتار در صورت وجود مسیر")
    parser.add_argument("--token", help="توکن بات روبیکا")
    parser.add_argument("--owner-id", help="OWNER_ID برای دسترسی ادمین")
    parser.add_argument("--api-base-url", default="https://botapi.rubika.ir/v3")
    parser.add_argument("--webhook-base-url", default="")
    parser.add_argument("--webhook-secret", default="")
    parser.add_argument("--venv-path", default=".venv")
    parser.add_argument("--service-name", default="rubika-bot")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--no-tests", action="store_true")
    parser.add_argument("--skip-pip", action="store_true", help="عدم نصب وابستگی‌ها (برای تست)")
    parser.add_argument("--no-systemd", action="store_true")
    parser.add_argument("--no-env", action="store_true")
    parser.add_argument("--force", action="store_true", help="بازنویسی فایل‌ها در صورت وجود")
    parser.add_argument("--run", action="store_true", help="اجرای سرویس بعد از نصب")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--install-deps", action="store_true", help="نصب پیش‌نیازها")
    parser.add_argument("--with-nginx", action="store_true", help="نصب و تنظیم Nginx")
    parser.add_argument("--with-ssl", action="store_true", help="دریافت SSL با certbot")
    parser.add_argument("--systemd-install", action="store_true", help="نصب و فعال‌سازی سرویس systemd")
    parser.add_argument("--no-webhook", action="store_true", help="ثبت وبهوک انجام نشود")
    return parser


def prepare_install_path(dest: Path, action: str | None, non_interactive: bool) -> None:
    if not dest.exists() or not any(dest.iterdir()):
        return
    if non_interactive:
        chosen = action or "abort"
    else:
        from rich.prompt import Prompt

        get_console().print(f"مسیر {dest} از قبل وجود دارد.", style="yellow")
        chosen = Prompt.ask("انتخاب", choices=["backup", "remove", "abort"], default="backup")
    if chosen == "backup":
        backup = dest.with_suffix(".bak")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(dest, backup)
        return
    if chosen == "remove":
        shutil.rmtree(dest)
        return
    raise FileExistsError(f"مسیر {dest} از قبل وجود دارد.")


def bootstrap_from_github(args: argparse.Namespace) -> None:
    if not args.github_repo:
        return
    dest = Path(args.install_path or "/opt/rubika-bot").expanduser().resolve()
    prepare_install_path(dest, args.install_action, args.non_interactive)
    clone_cmd = ["git", "clone"]
    if args.github_ref:
        clone_cmd += ["--branch", args.github_ref]
    clone_cmd += [args.github_repo, str(dest)]
    run(clone_cmd)
    forward_args: list[str] = []
    passthrough = {
        "token": args.token,
        "owner_id": args.owner_id,
        "api_base_url": args.api_base_url,
        "webhook_base_url": args.webhook_base_url,
        "webhook_secret": args.webhook_secret,
        "venv_path": args.venv_path,
        "service_name": args.service_name,
        "host": args.host,
        "port": args.port,
        "no_tests": args.no_tests,
        "no_systemd": args.no_systemd,
        "no_env": args.no_env,
        "force": args.force,
        "run": args.run,
        "non_interactive": args.non_interactive,
        "install_deps": args.install_deps,
        "with_nginx": args.with_nginx,
        "with_ssl": args.with_ssl,
        "systemd_install": args.systemd_install,
        "no_webhook": args.no_webhook,
    }
    for key, value in passthrough.items():
        flag = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                forward_args.append(flag)
        elif value is not None:
            forward_args.extend([flag, str(value)])
    run([sys.executable, str(dest / "install.py"), *forward_args])
    raise SystemExit(0)


def collect_inputs(args: argparse.Namespace) -> dict[str, Any]:
    if args.non_interactive:
        token = args.token or os.environ.get("RUBIKA_BOT_TOKEN", "")
        owner_id = args.owner_id or os.environ.get("RUBIKA_OWNER_ID", "")
        api_base_url = args.api_base_url or os.environ.get("RUBIKA_API_BASE_URL", args.api_base_url)
        webhook_base_url = args.webhook_base_url or os.environ.get("RUBIKA_WEBHOOK_BASE_URL", "")
        webhook_secret = args.webhook_secret or os.environ.get("RUBIKA_WEBHOOK_SECRET", "")
        if not token or not owner_id:
            raise ValueError("در حالت non-interactive باید --token و --owner-id مشخص شود.")
        webhook_base_url = validate_url(webhook_base_url, allow_empty=True)
        return {
            "token": token,
            "owner_id": owner_id,
            "api_base_url": api_base_url,
            "webhook_base_url": webhook_base_url,
            "webhook_secret": webhook_secret,
            "venv_path": Path(args.venv_path),
            "service_name": args.service_name,
            "host": args.host,
            "port": args.port,
            "run_tests": not args.no_tests,
            "skip_pip": args.skip_pip,
            "write_env": not args.no_env,
            "write_systemd": not args.no_systemd,
            "force": args.force,
            "run_app": args.run,
            "install_deps": args.install_deps,
            "with_nginx": args.with_nginx,
            "with_ssl": args.with_ssl,
            "systemd_install": args.systemd_install,
            "register_webhook": not args.no_webhook,
        }

    from rich import box
    from rich.panel import Panel

    get_console().print(Panel("Rubika Bot API v3 Installer", box=box.DOUBLE, title="Welcome"))
    token = args.token or prompt_text("TOKEN", required=True)
    owner_id = args.owner_id or prompt_validated("OWNER_ID", validate_owner_id)
    api_base_url = prompt_text("آدرس API", default=args.api_base_url)
    webhook_base_url = prompt_validated(
        "WEBHOOK_BASE_URL (مثل https://example.com)",
        lambda val: validate_url(val, allow_empty=True),
        default=args.webhook_base_url,
    )
    webhook_secret = prompt_text("Webhook Secret (اختیاری)", default=args.webhook_secret)
    venv_path = Path(prompt_text("مسیر محیط مجازی", default=args.venv_path))
    service_name = prompt_text("نام سرویس systemd", default=args.service_name)
    host = prompt_text("Host سرویس", default=args.host)
    port = int(prompt_text("Port سرویس", default=str(args.port)))
    install_deps_choice = prompt_bool("نصب پیش‌نیازها؟", default=False)
    with_nginx_choice = prompt_bool("تنظیم Nginx؟", default=False)
    with_ssl_choice = False
    if with_nginx_choice:
        with_ssl_choice = prompt_bool("فعال‌سازی SSL با certbot؟", default=False)
    run_tests_choice = prompt_bool("تست‌ها اجرا شوند؟", default=True)
    write_env_choice = prompt_bool("فایل .env ساخته شود؟", default=True)
    write_systemd_choice = prompt_bool("فایل systemd ساخته شود؟", default=True)
    systemd_install_choice = False
    if write_systemd_choice:
        systemd_install_choice = prompt_bool("سرویس systemd نصب و فعال شود؟", default=True)
    force_choice = prompt_bool("در صورت وجود فایل‌ها بازنویسی شوند؟", default=False)
    run_choice = prompt_bool("سرویس بعد از نصب اجرا شود؟", default=False)
    register_webhook_choice = prompt_bool("ثبت وبهوک انجام شود؟", default=True)
    return {
        "token": token,
        "owner_id": owner_id,
        "api_base_url": api_base_url,
        "webhook_base_url": webhook_base_url,
        "webhook_secret": webhook_secret,
        "venv_path": venv_path,
        "service_name": service_name,
        "host": host,
        "port": port,
        "run_tests": run_tests_choice,
        "skip_pip": False,
        "write_env": write_env_choice,
        "write_systemd": write_systemd_choice,
        "force": force_choice,
        "run_app": run_choice,
        "install_deps": install_deps_choice,
        "with_nginx": with_nginx_choice,
        "with_ssl": with_ssl_choice,
        "systemd_install": systemd_install_choice,
        "register_webhook": register_webhook_choice,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.github_repo:
        bootstrap_from_github(args)
    data = collect_inputs(args)
    venv_path = PROJECT_ROOT / str(data["venv_path"])

    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table

    console = get_console()
    console.print(Panel("شروع نصب", style="bold cyan"))

    summary = Table(title="Installation Plan", show_header=True, header_style="bold magenta")
    summary.add_column("Key")
    summary.add_column("Value")
    summary.add_row("Install Path", str(PROJECT_ROOT))
    summary.add_row("Service Name", str(data["service_name"]))
    summary.add_row("Host:Port", f"{data['host']}:{data['port']}")
    summary.add_row("Venv", str(venv_path))
    summary.add_row("Webhook Base URL", str(data["webhook_base_url"] or "-"))
    summary.add_row("Run Tests", "yes" if data["run_tests"] else "no")
    summary.add_row("Register Webhook", "yes" if data["register_webhook"] else "no")
    console.print(summary)

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        if data["install_deps"]:
            task = progress.add_task("نصب پیش‌نیازها...", total=None)
            install_dependencies(data["with_nginx"], data["with_ssl"])
            progress.update(task, completed=1)

        task = progress.add_task("ایجاد محیط مجازی و نصب وابستگی‌ها...", total=None)
        ensure_venv(venv_path)
        if data.get("skip_pip"):
            console.print("⚠️ نصب وابستگی‌ها رد شد (skip-pip).", style="yellow")
        else:
            install_requirements(venv_path)
        progress.update(task, completed=1)

        if data["write_env"]:
            task = progress.add_task("ساخت فایل .env...", total=None)
            env_text = render_env(
                token=str(data["token"]),
                api_base_url=str(data["api_base_url"]),
                webhook_base_url=str(data["webhook_base_url"]),
                webhook_secret=str(data["webhook_secret"]),
                owner_id=str(data["owner_id"]),
            )
            write_file(PROJECT_ROOT / ".env", env_text, overwrite=bool(data["force"]))
            progress.update(task, completed=1)

        service_path = None
        if data["write_systemd"]:
            task = progress.add_task("تولید فایل systemd...", total=None)
            service_text = render_systemd_service(
                working_dir=PROJECT_ROOT,
                venv_path=venv_path,
                service_name=str(data["service_name"]),
                host=str(data["host"]),
                port=int(data["port"]),
            )
            service_path = PROJECT_ROOT / f"{data['service_name']}.service"
            write_file(service_path, service_text, overwrite=bool(data["force"]))
            progress.update(task, completed=1)

        if data["systemd_install"] and service_path:
            task = progress.add_task("نصب و فعال‌سازی سرویس systemd...", total=None)
            install_systemd_service(service_path, str(data["service_name"]))
            progress.update(task, completed=1)

        if data["with_nginx"] and data["webhook_base_url"]:
            task = progress.add_task("تنظیم Nginx...", total=None)
            server_name = urlparse(str(data["webhook_base_url"])).hostname or "_"
            setup_nginx(str(data["service_name"]), server_name, str(data["host"]), int(data["port"]), data["with_ssl"])
            progress.update(task, completed=1)

        if data["run_tests"]:
            task = progress.add_task("اجرای تست‌ها...", total=None)
            run_tests(venv_path)
            progress.update(task, completed=1)

        if data["register_webhook"] and data["webhook_base_url"]:
            task = progress.add_task("ثبت وبهوک در روبیکا...", total=None)
            result = update_webhook_endpoints(
                str(data["token"]),
                str(data["api_base_url"]),
                str(data["webhook_base_url"]),
            )
            progress.update(task, completed=1)
            console.print(f"✅ وبهوک ثبت شد: {result}", style="green")

        task = progress.add_task("تست getMe...", total=None)
        me = get_me(str(data["token"]), str(data["api_base_url"]))
        progress.update(task, completed=1)
        console.print(f"✅ getMe: {me}", style="green")

    console.print("🎉 نصب تکمیل شد.", style="bold green")
    console.print("برای اجرا:")
    console.print(f"{venv_path / 'bin' / 'uvicorn'} app.main:app --host {data['host']} --port {data['port']}")
    if data.get("run_app"):
        run(
            [
                str(venv_path / "bin" / "uvicorn"),
                "app.main:app",
                "--host",
                str(data["host"]),
                "--port",
                str(data["port"]),
            ]
        )


if __name__ == "__main__":
    main()
