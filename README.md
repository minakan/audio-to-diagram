# audio-to-diagram

プログラミング演習向けの、講師発話リアルタイム可視化システムです。

## アーキテクチャ

- フロントエンド: Next.js (TypeScript)
- バックエンド: FastAPI (Python)
- リアルタイム通信: WebSocket (`/ws/audio`)
- 中間表現: `diagram_plan`
- SVG 出力: サニタイズ済み SVG のみ
- データベース: PostgreSQL（Docker サービス）

## クイックスタート（Docker）

1コマンドで起動する場合:

```bash
./start.sh
```

内部で `.env` がなければ自動作成し、`docker compose up --build` を実行します。
`8000` / `3000` が使用中の場合は空きポートへ自動フォールバックします。

手動で起動する場合:

```bash
cp .env.example .env
docker compose up --build
```

- フロントエンド: `http://localhost:3000`
- バックエンドヘルスチェック: `http://localhost:8000/health`
- WebSocket: `ws://localhost:8000/ws/audio`

## ローカルでバックエンド起動（uv）

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## ローカルテスト

```bash
cd backend
uv sync --extra dev
uv run pytest
```
