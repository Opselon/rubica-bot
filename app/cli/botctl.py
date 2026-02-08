from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


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


def check(args: argparse.Namespace) -> None:
    run([args.python, "-m", "pip", "install", "-r", "requirements.txt"])
    run([args.python, "-m", "pytest", "tests"])
    run([args.python, "-m", "app.utils.speedcheck"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="botctl")
    parser.add_argument("--service", default="rubika-bot")
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

    check_parser = sub.add_parser("check")
    check_parser.add_argument("--python", default="python3")
    check_parser.set_defaults(func=check)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
