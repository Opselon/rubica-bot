#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Rubica Bot One-Line Installer

Usage:
  curl -fsSL https://raw.githubusercontent.com/Opselon/rubica-bot/main/install.sh | bash -s -- [options]

Options:
  --non-interactive         Run without prompts (requires token/owner-id).
  --token VALUE             Bot token (or env RUBIKA_BOT_TOKEN).
  --owner-id VALUE          Owner ID (or env RUBIKA_OWNER_ID).
  --base-url VALUE          Rubika API base URL (or env RUBIKA_API_BASE_URL).
  --webhook-base-url VALUE  Webhook base URL (or env RUBIKA_WEBHOOK_BASE_URL).
  --install-path PATH       Install path (default: /opt/rubica-bot).
  --repo URL|PATH           Git repo URL or local path.
  --ref REF                 Git ref (branch/tag).
  --install-action ACTION   backup|remove|abort (if path exists).
  --with-nginx              Configure nginx.
  --with-ssl                Enable SSL with certbot.
  --systemd-install         Install/enable systemd service.
  --install-deps            Install OS dependencies (apt).
  --no-tests                Skip tests.
  --skip-pip                Skip pip install (test mode).
  --no-webhook              Skip webhook registration.
  --service-name VALUE      systemd service name.
  --host VALUE              Service host.
  --port VALUE              Service port.
  --venv-path PATH          Virtualenv path (default: .venv).
  --force                   Overwrite existing files.
  --test-mode               Enable CI-friendly mocks (no root needed).
  -h, --help                Show this help.
EOF
}

REPO="${RUBIKA_INSTALL_REPO:-https://github.com/Opselon/rubica-bot.git}"
REF="${RUBIKA_INSTALL_REF:-}"
INSTALL_PATH="${RUBIKA_INSTALL_PATH:-/opt/rubica-bot}"
INSTALL_ACTION=""
NON_INTERACTIVE=0
TOKEN="${RUBIKA_BOT_TOKEN:-}"
OWNER_ID="${RUBIKA_OWNER_ID:-}"
API_BASE_URL="${RUBIKA_API_BASE_URL:-https://botapi.rubika.ir/v3}"
WEBHOOK_BASE_URL="${RUBIKA_WEBHOOK_BASE_URL:-}"
WITH_NGINX=0
WITH_SSL=0
SYSTEMD_INSTALL=0
INSTALL_DEPS=0
NO_TESTS=0
SKIP_PIP=0
NO_WEBHOOK=0
SERVICE_NAME="rubika-bot"
HOST="0.0.0.0"
PORT="8080"
VENV_PATH=".venv"
FORCE=0
TEST_MODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive) NON_INTERACTIVE=1; shift ;;
    --token) TOKEN="${2:-}"; shift 2 ;;
    --owner-id) OWNER_ID="${2:-}"; shift 2 ;;
    --base-url|--api-base-url) API_BASE_URL="${2:-}"; shift 2 ;;
    --webhook-base-url) WEBHOOK_BASE_URL="${2:-}"; shift 2 ;;
    --install-path) INSTALL_PATH="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --ref) REF="${2:-}"; shift 2 ;;
    --install-action) INSTALL_ACTION="${2:-}"; shift 2 ;;
    --with-nginx) WITH_NGINX=1; shift ;;
    --with-ssl) WITH_SSL=1; shift ;;
    --systemd-install) SYSTEMD_INSTALL=1; shift ;;
    --install-deps) INSTALL_DEPS=1; shift ;;
    --no-tests) NO_TESTS=1; shift ;;
    --skip-pip) SKIP_PIP=1; shift ;;
    --no-webhook) NO_WEBHOOK=1; shift ;;
    --service-name) SERVICE_NAME="${2:-}"; shift 2 ;;
    --host) HOST="${2:-}"; shift 2 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --venv-path) VENV_PATH="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --test-mode) TEST_MODE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ $TEST_MODE -eq 1 ]]; then
  if [[ "$INSTALL_PATH" == "/opt/rubica-bot" ]]; then
    INSTALL_PATH="./sandbox"
  fi
fi

if [[ $NON_INTERACTIVE -eq 1 ]]; then
  if [[ -z "${TOKEN}" || -z "${OWNER_ID}" ]]; then
    echo "Missing --token/--owner-id or RUBIKA_BOT_TOKEN/RUBIKA_OWNER_ID." >&2
    exit 1
  fi
fi

if [[ ! -w "$(dirname "$INSTALL_PATH")" && $TEST_MODE -eq 0 ]]; then
  echo "Install path not writable. Use --install-path or --test-mode." >&2
  exit 1
fi

if command -v git >/dev/null 2>&1; then
  :
else
  echo "git not found. Please install git first." >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  :
else
  echo "python3 not found. Please install python3 first." >&2
  exit 1
fi

if [[ -d "$INSTALL_PATH" && -n "$(ls -A "$INSTALL_PATH")" ]]; then
  if [[ -z "${INSTALL_ACTION}" ]]; then
    INSTALL_ACTION="backup"
  fi
  case "$INSTALL_ACTION" in
    backup)
      mv "$INSTALL_PATH" "${INSTALL_PATH}.bak"
      ;;
    remove)
      rm -rf "$INSTALL_PATH"
      ;;
    abort)
      echo "Install path exists. Aborting." >&2
      exit 1
      ;;
    *)
      echo "Unknown install action: ${INSTALL_ACTION}" >&2
      exit 1
      ;;
  esac
fi

CLONE_CMD=(git clone)
if [[ -n "${REF}" ]]; then
  CLONE_CMD+=(--branch "${REF}")
fi
CLONE_CMD+=("${REPO}" "${INSTALL_PATH}")

if [[ -d "$INSTALL_PATH/.git" ]]; then
  echo "Repository already exists at ${INSTALL_PATH}" >&2
else
  "${CLONE_CMD[@]}"
fi

pushd "${INSTALL_PATH}" >/dev/null

if [[ $TEST_MODE -eq 1 ]]; then
  MOCK_DIR="${INSTALL_PATH}/.mock"
  MOCK_BIN="${MOCK_DIR}/bin"
  mkdir -p "$MOCK_BIN" "$MOCK_DIR/systemd" "$MOCK_DIR/nginx/sites-available" "$MOCK_DIR/nginx/sites-enabled"
  cat > "${MOCK_BIN}/systemctl" <<'EOS'
#!/usr/bin/env bash
echo "mock systemctl $*" >&2
exit 0
EOS
  cat > "${MOCK_BIN}/nginx" <<'EOS'
#!/usr/bin/env bash
if [[ "$1" == "-t" ]]; then
  echo "mock nginx config ok"
fi
exit 0
EOS
  cat > "${MOCK_BIN}/certbot" <<'EOS'
#!/usr/bin/env bash
echo "mock certbot $*" >&2
exit 0
EOS
  chmod +x "${MOCK_BIN}/systemctl" "${MOCK_BIN}/nginx" "${MOCK_BIN}/certbot"
  export PATH="${MOCK_BIN}:${PATH}"
  export RUBIKA_SYSTEMD_DIR="${MOCK_DIR}/systemd"
  export RUBIKA_NGINX_DIR="${MOCK_DIR}/nginx"
fi

INSTALL_ARGS=()
if [[ $NON_INTERACTIVE -eq 1 ]]; then
  INSTALL_ARGS+=(--non-interactive)
fi
INSTALL_ARGS+=(--token "${TOKEN}")
INSTALL_ARGS+=(--owner-id "${OWNER_ID}")
INSTALL_ARGS+=(--api-base-url "${API_BASE_URL}")
INSTALL_ARGS+=(--webhook-base-url "${WEBHOOK_BASE_URL}")
INSTALL_ARGS+=(--service-name "${SERVICE_NAME}")
INSTALL_ARGS+=(--host "${HOST}")
INSTALL_ARGS+=(--port "${PORT}")
INSTALL_ARGS+=(--venv-path "${VENV_PATH}")
if [[ -n "${INSTALL_ACTION}" ]]; then
  INSTALL_ARGS+=(--install-action "${INSTALL_ACTION}")
fi
if [[ $WITH_NGINX -eq 1 ]]; then
  INSTALL_ARGS+=(--with-nginx)
fi
if [[ $WITH_SSL -eq 1 ]]; then
  INSTALL_ARGS+=(--with-ssl)
fi
if [[ $SYSTEMD_INSTALL -eq 1 ]]; then
  INSTALL_ARGS+=(--systemd-install)
fi
if [[ $INSTALL_DEPS -eq 1 ]]; then
  INSTALL_ARGS+=(--install-deps)
fi
if [[ $NO_TESTS -eq 1 ]]; then
  INSTALL_ARGS+=(--no-tests)
fi
if [[ $SKIP_PIP -eq 1 ]]; then
  INSTALL_ARGS+=(--skip-pip)
fi
if [[ $NO_WEBHOOK -eq 1 ]]; then
  INSTALL_ARGS+=(--no-webhook)
fi
if [[ $FORCE -eq 1 ]]; then
  INSTALL_ARGS+=(--force)
fi

if [[ $TEST_MODE -eq 1 ]]; then
  export RUBIKA_TEST_MODE=1
  export RUBIKA_SKIP_SYSTEMCTL=1
  INSTALL_ARGS+=(--skip-pip)
fi

python3 install.py "${INSTALL_ARGS[@]}"

popd >/dev/null

echo "Install finished at ${INSTALL_PATH}"
