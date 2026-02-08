from pathlib import Path

from install import render_env, render_systemd_service


def test_render_env_includes_required_values() -> None:
    output = render_env(
        token="token-123",
        api_base_url="https://api.example",
        webhook_base_url="https://webhook.example",
        webhook_secret="secret",
        owner_id="42",
    )
    assert "RUBIKA_BOT_TOKEN=token-123" in output
    assert "RUBIKA_API_BASE_URL=https://api.example" in output
    assert "RUBIKA_OWNER_ID=42" in output
    assert "RUBIKA_WEBHOOK_BASE_URL=https://webhook.example" in output
    assert "RUBIKA_WEBHOOK_SECRET=secret" in output


def test_render_env_skips_optional_values() -> None:
    output = render_env(
        token="token-123",
        api_base_url="https://api.example",
        webhook_base_url="",
        webhook_secret="",
    )
    assert "RUBIKA_WEBHOOK_BASE_URL" not in output
    assert "RUBIKA_WEBHOOK_SECRET" not in output


def test_render_systemd_service_contains_paths(tmp_path: Path) -> None:
    working_dir = tmp_path / "app"
    venv_path = tmp_path / ".venv"
    output = render_systemd_service(
        working_dir=working_dir,
        venv_path=venv_path,
        service_name="rubika-bot",
        host="0.0.0.0",
        port=8080,
    )
    assert f"WorkingDirectory={working_dir}" in output
    assert f"EnvironmentFile={working_dir / '.env'}" in output
    assert f"{venv_path / 'bin' / 'python'} -m uvicorn app.main:app --host 0.0.0.0 --port 8080" in output
