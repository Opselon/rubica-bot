#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Opselon/rubica-bot.git}"
INSTALL_DIR="${INSTALL_DIR:-/opt/rubica-bot}"
SERVICE_NAME="${SERVICE_NAME:-rubica-bot}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
USER_NAME="${USER_NAME:-$(whoami)}"

echo "🚀 Installing Rubika Bot from ${REPO_URL}"

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "🔄 Updating existing repository..."
  git -C "${INSTALL_DIR}" fetch --all
  git -C "${INSTALL_DIR}" reset --hard origin/main
else
  echo "📥 Cloning repository..."
  sudo mkdir -p "${INSTALL_DIR}"
  sudo chown "${USER_NAME}":"${USER_NAME}" "${INSTALL_DIR}"
  git clone "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

echo "🐍 Creating virtual environment..."
${PYTHON_BIN} -m venv .venv
source .venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🛠️ Running setup wizard..."
python -m app.cli.botctl setup --db-url sqlite:///data/bot.db

echo "🧾 Creating systemd service..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Rubika Bot
After=network.target

[Service]
User=${USER_NAME}
WorkingDirectory=${INSTALL_DIR}
Environment=RUBIKA_DB_URL=sqlite:///data/bot.db
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "✅ Done! Service ${SERVICE_NAME} is running."
