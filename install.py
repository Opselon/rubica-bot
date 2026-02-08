from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def prompt_text(label: str, default: str | None = None, required: bool = False) -> str:
    hint = f" (پیش‌فرض: {default})" if default else ""
    while True:
        value = input(f"{label}{hint}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("⚠️ مقدار الزامی است. دوباره تلاش کنید.")


def prompt_bool(label: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{label} [{suffix}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "true"}


def render_env(
    token: str,
    api_base_url: str,
    webhook_base_url: str,
    webhook_secret: str,
) -> str:
    lines = [
        f"RUBIKA_BOT_TOKEN={token}",
        f"RUBIKA_API_BASE_URL={api_base_url}",
    ]
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


def ensure_venv(venv_path: Path) -> None:
    if venv_path.exists():
        return
    run([sys.executable, "-m", "venv", str(venv_path)])


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ویزارد نصب بات روبیکا (محیط مجازی، وابستگی‌ها، .env و سرویس systemd)"
    )
    parser.add_argument("--token", help="توکن بات روبیکا")
    parser.add_argument("--api-base-url", default="https://botapi.rubika.ir/v3")
    parser.add_argument("--webhook-base-url", default="")
    parser.add_argument("--webhook-secret", default="")
    parser.add_argument("--venv-path", default=".venv")
    parser.add_argument("--service-name", default="rubika-bot")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--no-tests", action="store_true")
    parser.add_argument("--no-systemd", action="store_true")
    parser.add_argument("--no-env", action="store_true")
    parser.add_argument("--force", action="store_true", help="بازنویسی فایل‌ها در صورت وجود")
    parser.add_argument("--non-interactive", action="store_true")
    return parser


def collect_inputs(args: argparse.Namespace) -> dict[str, str | int | bool | Path]:
    if args.non_interactive:
        if not args.token:
            raise ValueError("در حالت non-interactive باید --token مشخص شود.")
        return {
            "token": args.token,
            "api_base_url": args.api_base_url,
            "webhook_base_url": args.webhook_base_url,
            "webhook_secret": args.webhook_secret,
            "venv_path": Path(args.venv_path),
            "service_name": args.service_name,
            "host": args.host,
            "port": args.port,
            "run_tests": not args.no_tests,
            "write_env": not args.no_env,
            "write_systemd": not args.no_systemd,
            "force": args.force,
        }

    print("✨ ویزارد نصب بات روبیکا")
    token = args.token or prompt_text("توکن بات", required=True)
    api_base_url = prompt_text("آدرس API", default=args.api_base_url)
    webhook_base_url = prompt_text("آدرس وبهوک (اختیاری)", default=args.webhook_base_url)
    webhook_secret = prompt_text("کلید وبهوک (اختیاری)", default=args.webhook_secret)
    venv_path = Path(prompt_text("مسیر محیط مجازی", default=args.venv_path))
    service_name = prompt_text("نام سرویس systemd", default=args.service_name)
    host = prompt_text("Host سرویس", default=args.host)
    port = int(prompt_text("Port سرویس", default=str(args.port)))
    run_tests_choice = prompt_bool("تست‌ها اجرا شوند؟", default=True)
    write_env_choice = prompt_bool("فایل .env ساخته شود؟", default=True)
    write_systemd_choice = prompt_bool("فایل systemd ساخته شود؟", default=True)
    force_choice = prompt_bool("در صورت وجود فایل‌ها بازنویسی شوند؟", default=False)
    return {
        "token": token,
        "api_base_url": api_base_url,
        "webhook_base_url": webhook_base_url,
        "webhook_secret": webhook_secret,
        "venv_path": venv_path,
        "service_name": service_name,
        "host": host,
        "port": port,
        "run_tests": run_tests_choice,
        "write_env": write_env_choice,
        "write_systemd": write_systemd_choice,
        "force": force_choice,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    data = collect_inputs(args)
    venv_path = PROJECT_ROOT / str(data["venv_path"])

    print("🔧 ایجاد محیط مجازی و نصب وابستگی‌ها...")
    ensure_venv(venv_path)
    install_requirements(venv_path)

    if data["write_env"]:
        env_text = render_env(
            token=str(data["token"]),
            api_base_url=str(data["api_base_url"]),
            webhook_base_url=str(data["webhook_base_url"]),
            webhook_secret=str(data["webhook_secret"]),
        )
        write_file(PROJECT_ROOT / ".env", env_text, overwrite=bool(data["force"]))
        print("✅ فایل .env ساخته شد.")

    if data["write_systemd"]:
        service_text = render_systemd_service(
            working_dir=PROJECT_ROOT,
            venv_path=venv_path,
            service_name=str(data["service_name"]),
            host=str(data["host"]),
            port=int(data["port"]),
        )
        service_path = PROJECT_ROOT / f"{data['service_name']}.service"
        write_file(service_path, service_text, overwrite=bool(data["force"]))
        print(f"✅ فایل systemd در {service_path} ساخته شد.")

    if data["run_tests"]:
        print("🧪 اجرای تست‌ها...")
        run_tests(venv_path)

    print("🎉 نصب تکمیل شد.")
    print("برای اجرا:")
    print(f"{venv_path / 'bin' / 'uvicorn'} app.main:app --host {data['host']} --port {data['port']}")


if __name__ == "__main__":
    main()
