# 実装状況サマリ（MVP棚卸し）

- 作成日: 2026-03-17
- 対象ブランチ: `feat/mvp-e2e-docker`
- 目的: 現在の実装済み/未実装を明確化し、次の実装プロンプト作成に使える材料を整理する。

## 1. 全体結論

- **MVPとしての最短E2Eは実装済み**。
- 具体的には、`/ws/audio` に対して `session.start -> audio.chunk -> utterance.flush` を送ると、`transcript.final -> analysis.result -> diagram.plan -> svg.result`（条件により `skipped`）まで到達する。
- ただし、仕様書で示した初期版全体要件に対しては、**未実装/簡易実装が多く残る**（特に並列化、REST補助API、ログ閲覧API/画面、Claude対応、高度VAD/意味区切り、評価機能）。

## 2. 実装済み（完了）

| 区分 | ステータス | 実装内容 | 根拠ファイル |
|---|---|---|---|
| Docker実行基盤 | 実装済み | `frontend` / `backend` / `postgres` の3サービス構成。`.env` 読み込みで起動 | `docker-compose.yml`, `.env.example` |
| ワンコマンド起動 | 実装済み | `.env` 自動生成 + `docker compose up --build` | `start.sh` |
| FastAPI起動/DI | 実装済み | lifespanでDB初期化、Provider/STT/Pipeline/Loggerを組み立て | `backend/app/main.py` |
| WebSocketエンドポイント | 実装済み | `WS /ws/audio` 実装、イベント受信/検証/応答 | `backend/app/api/websocket/audio_ws.py` |
| WebSocketイベントスキーマ | 実装済み | `session.start`, `audio.chunk`, `utterance.flush`, `session.stop` とサーバー返却イベントをPydanticで型定義 | `backend/app/schemas/websocket.py` |
| パイプライン段階処理 | 実装済み | `STT -> normalize -> domain -> visualization -> diagram_plan -> SVG sanitize/validate -> logging` | `backend/app/services/orchestration/realtime_pipeline.py` |
| ドメイン判定/可視化判定 | 実装済み | Provider経由で判定、ドメイン非該当時は可視化を抑止 | `backend/app/services/analysis/domain_filter_service.py`, `backend/app/services/analysis/visualization_decision_service.py` |
| `diagram_plan` スキーマ | 実装済み | `topic/diagram_type/nodes/edges/annotations/layout/source` を型定義 | `backend/app/schemas/diagram_plan.py` |
| `diagram_plan` 生成 | 実装済み | 二分探索向けテンプレと汎用フロー生成を実装 | `backend/app/services/analysis/diagram_planner_service.py` |
| SVG生成 | 実装済み | `diagram_plan` からSVG文字列生成 | `backend/app/services/generation/svg_generator_service.py` |
| SVGサニタイズ/検証 | 実装済み | `script`除去、`on*`属性除去、`viewBox`保証、SVG妥当性検査 | `backend/app/services/generation/svg_sanitizer.py`, `backend/app/services/analysis/quality_check_service.py` |
| OpenAI Provider抽象化 | 実装済み | Provider Protocol + OpenAI実装（正規化/判定） | `backend/app/services/llm/provider_base.py`, `backend/app/services/llm/openai_provider.py` |
| STTサービス | 実装済み | OpenAI STT呼び出し経路 + デバッグ文字列/フォールバック文 | `backend/app/services/stt/stt_service.py` |
| ログ保存 | 実装済み | sessions/chunks/transcripts/analysis/diagram_artifacts テーブルに保存 | `backend/app/models/records.py`, `backend/app/services/storage/pipeline_logger.py` |
| フロントUI（単画面） | 実装済み | 録音開始/停止、flush、partial/final表示、analysis/diagram_plan/SVG表示、イベントログ表示 | `frontend/app/page.tsx` |
| フロント型 | 実装済み | WS受信イベント型をTypeScriptで定義 | `frontend/src/types/ws.ts` |
| CI | 実装済み | backend: ruff/mypy/pytest、frontend: lint/typecheck/build | `.github/workflows/ci.yml` |
| テスト（backend） | 実装済み | unit: diagram planner / sanitizer、integration: websocket E2E(可視化/skip) | `backend/app/tests/*` |

## 3. 部分実装（要強化）

| 区分 | 現状 | 制約/不足 |
|---|---|---|
| 音声区切り/VAD | サーバ側は「最大長到達」で強制flush。クライアントは `utterance.flush` 手動送信可能 | 無音検出ロジック本体は未実装。`vad_state` は受信するが実運用判定に使っていない |
| STT partial | `transcript.partial` は実装される | 実際の逐次STTではなく、`debug_text` または固定文字列中心 |
| STT final | OpenAI API経路あり | `debug_text` があるとAPIを使わずそれを最優先で返す（実験向け挙動） |
| Provider抽象化 | Protocolあり | 実装プロバイダはOpenAIのみ。Claude実装は未追加 |
| プロンプト管理 | `prompts/` ディレクトリは存在 | 実行時に `prompts/*.txt` を読み込む設計には未接続（コード内文字列中心） |
| 並列処理 | サービス分離は済 | 実行はほぼ直列。sub-agent並列実行や待ち合わせ制御は未実装 |
| フォールバック | `diagram_plan` は保持し、SVG失敗時は `error + skipped` を返す | 「直前SVG維持」「再試行回数制御」「段階別フォールバック戦略」は未実装 |
| DB | PostgreSQL利用可能、SQLiteデフォルトも可 | マイグレーション未導入（`create_all`のみ） |

## 4. 未実装（仕様書との差分）

### 4.1 API / プロトコル関連

- 未実装: `POST /api/transcribe`
- 未実装: `POST /api/analyze-utterance`
- 未実装: `POST /api/generate-svg`
- 未実装: `POST /api/session/start`, `POST /api/session/stop`
- 未実装: `GET /api/logs`
- 現状はWebSocket中心で最小構成

### 4.2 バックエンド機能

- 未実装: Claude provider (`claude_provider.py`) 実装
- 未実装: タスクルータ/フォールバック管理の本実装（現状はプレースホルダ）
- 未実装: 無音ベースVAD + 意味境界補正（文末・接続詞・STT確定タイミング活用）
- 未実装: 重複図抑制（直前diagramとの差分判定）
- 未実装: テーマ同一時の差分更新戦略（再描画or差分更新選択）
- 未実装: prompt version の段階別管理（domain/viz/planner/svg）
- 未実装: stage別レイテンシの詳細記録（現状は主にdiagram artifact側）
- 未実装: 永続化のRepository層分離（service内で直接書き込み）

### 4.3 フロントエンド機能

- 未実装: 履歴画面（一覧/詳細/再表示）
- 未実装: ログ閲覧画面
- 未実装: プロンプト設定画面
- 未実装: 実験評価画面
- 未実装: 図の再生成・破棄UI
- 未実装: マイク状態の詳細表示（待機/録音/処理中はあるが、VAD由来の内訳や遅延メトリクス表示は未整備）

### 4.4 テスト/品質

- 未実装: frontendの単体/統合テスト
- 未実装: e2eテスト（ブラウザ操作含む）
- 未実装: provider失敗時の詳細な回復テスト
- 未実装: 負荷/遅延検証（リアルタイム要件向け）

## 5. 要件別チェック（仕様書の主項目に対応）

| 仕様観点 | 判定 | コメント |
|---|---|---|
| 6.1 音声入力 | 一部達成 | 録音開始/停止と200msチャンク送信はある。自動無音区切りは未実装 |
| 6.2 文字起こし | 一部達成 | partial/finalイベントはあるが、partial品質は簡易 |
| 6.3 前処理 | 一部達成 | normalizeあり。高度整形・意味単位再構成は未実装 |
| 6.4 ドメイン判定 | 達成（MVP） | 明示判定と棄却フローあり |
| 6.5 可視化要否判定 | 達成（MVP） | 明示判定とskipあり |
| 6.6 説明内容構造化 | 達成（MVP） | `diagram_plan` 生成とスキーマ検証あり |
| 6.7 SVG生成 | 達成（MVP） | 生成 + sanitize + validate |
| 6.8 図表示 | 一部達成 | 最新表示は可。履歴操作・再生成/破棄は未実装 |
| 6.9 並列処理 | 未達 | 実行は直列中心 |
| 6.10 ログ | 一部達成 | DB保存あり。取得API/UI・詳細メトリクスは不足 |
| 7.x 非機能要件 | 一部達成 | 型・責務分離・CIはある。性能/可観測性は未整備 |
| 8.x アーキテクチャ方針 | 概ね達成 | Next.js + FastAPI + uv + WS + diagram_planを維持 |
| 10 並列サブエージェント案 | 未達 | 分離のみで並列実行なし |
| 12 REST API案 | 未達 | `/health` 以外のRESTは未実装 |
| 21 WSイベント設計 | 達成（MVP） | 主要イベント一式を実装 |
| 22 diagram_planスキーマ | 達成（MVP） | 必須構造を型化 |

## 6. 次プロンプト作成用の優先バックログ

### 優先度A（次に着手推奨）

1. **VAD + 自動発話確定の本実装**
- 目標: `audio.chunk` を無音継続時間と最大発話長で自動flush
- 完了条件: 手動flushなしでも `transcript.final` が安定して返る

2. **REST補助APIの実装（ログ取得含む）**
- 目標: `/api/logs` と必要最小限の `session/transcribe/analyze/generate-svg` を追加
- 完了条件: UI/検証スクリプトからHTTP経由でデータ参照可能

3. **Claude provider追加**
- 目標: `provider_base` に準拠した `claude_provider.py` を追加
- 完了条件: 設定でOpenAI/Claude切替できる

### 優先度B（品質向上）

4. **並列実行オーケストレータ**
- 目標: normalize/domain/viz/plannerの一部を並列化し、合流制御を導入
- 完了条件: 同等品質で処理時間短縮が確認できる

5. **図の重複抑制/差分更新戦略**
- 目標: 直近 `diagram_plan` 比較で再生成抑制
- 完了条件: 同内容連続発話で `svg.result` が無駄発行されない

6. **可観測性強化**
- 目標: ステージ別 latency と判定理由・prompt version を統一ログ化
- 完了条件: 1 utterance 単位で全ステージを追跡可能

## 7. 次プロンプトのテンプレート（そのまま利用可能）

```text
現状の IMPLEMENTATION_STATUS.md を前提に、優先度Aの1つ目「VAD + 自動発話確定の本実装」を行ってください。

制約:
- 既存アーキテクチャ（Next.js + FastAPI + WebSocket + diagram_plan）を維持
- WebSocketイベント名は変更しない
- backend中心に実装し、必要最小限のfrontend変更のみ
- 追加するしきい値は設定化する（silence_timeout_ms, max_utterance_ms など）

完了条件:
- manual flushなしで無音検出により utterance が確定される
- transcript.final / analysis.result / diagram.plan / svg.result(条件付き) が従来どおり流れる
- backendテストを追加・更新する
- 変更点と残課題を報告する
```

## 8. 補足（作業ツリー状態）

- `README.md` はローカル変更あり
- `start.sh` は未追跡ファイル
- 評価時点では上記を含むワークツリー前提で棚卸し

