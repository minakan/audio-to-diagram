#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

read_env_value() {
  local key="$1"
  if [[ ! -f ".env" ]]; then
    return 0
  fi
  grep -E "^${key}=" .env | tail -n 1 | cut -d "=" -f2- || true
}

is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${port} )" 2>/dev/null | tail -n +2 | grep -q .
    return $?
  fi
  return 1
}

find_available_port() {
  local preferred="$1"
  local tries=20
  local port="$preferred"
  local i=0

  while (( i < tries )); do
    if ! is_port_in_use "$port"; then
      echo "$port"
      return 0
    fi
    port=$((port + 1))
    i=$((i + 1))
  done

  return 1
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker が見つかりません。Docker Desktop などをインストールしてください。"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo ".env を .env.example から作成しました。必要に応じて API キーを設定してください。"
fi

requested_backend_port="${HOST_BACKEND_PORT:-$(read_env_value HOST_BACKEND_PORT)}"
requested_frontend_port="${HOST_FRONTEND_PORT:-$(read_env_value HOST_FRONTEND_PORT)}"

if [[ -z "$requested_backend_port" ]]; then
  requested_backend_port=8000
fi
if [[ -z "$requested_frontend_port" ]]; then
  requested_frontend_port=3000
fi

resolved_backend_port="$(find_available_port "$requested_backend_port")"
resolved_frontend_port="$(find_available_port "$requested_frontend_port")"

if [[ "$resolved_backend_port" != "$requested_backend_port" ]]; then
  echo "ポート ${requested_backend_port} は使用中のため、backend を ${resolved_backend_port} で起動します。"
fi
if [[ "$resolved_frontend_port" != "$requested_frontend_port" ]]; then
  echo "ポート ${requested_frontend_port} は使用中のため、frontend を ${resolved_frontend_port} で起動します。"
fi

export HOST_BACKEND_PORT="$resolved_backend_port"
export HOST_FRONTEND_PORT="$resolved_frontend_port"
export NEXT_PUBLIC_WS_URL="ws://localhost:${HOST_BACKEND_PORT}/ws/audio"

echo "frontend: http://localhost:${HOST_FRONTEND_PORT}"
echo "backend:  http://localhost:${HOST_BACKEND_PORT}"

docker compose up --build
