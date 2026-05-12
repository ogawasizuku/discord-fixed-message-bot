#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/discord-fixed-message-bot"
SERVICE_NAME="discord-fixed-message-bot.service"

sudo mkdir -p "$APP_DIR/data"
sudo cp -r . "$APP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR"

cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "先に $APP_DIR/.env に DISCORD_TOKEN を設定してください。"
  exit 1
fi

sudo cp deploy/$SERVICE_NAME /etc/systemd/system/$SERVICE_NAME
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME
sudo systemctl status $SERVICE_NAME --no-pager
