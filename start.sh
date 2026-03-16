#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker が見つかりません。Docker Desktop などをインストールしてください。"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo ".env を .env.example から作成しました。必要に応じて API キーを設定してください。"
fi

docker compose up --build
