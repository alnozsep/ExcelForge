# ExcelForge

AIを活用した次世代のExcel帳票自動生成SaaSプラットフォーム。

## 概要

ExcelForgeは、PDFやテキストデータから必要な情報をAI（Gemini 1.5 Pro）で抽出し、既存のExcelテンプレートの指定箇所に自動で書き込むツールです。個人情報の保護を第一に考え、データ永続化を行わない完全ステートレスなアーキテクチャを採用しています。

## 主な機能

- **AIデータ抽出**: Vertex AI (Gemini 1.5 Pro) を使用し、非構造化データから正確に情報を抽出。
- **Excelテンプレート統合**: 既存のExcelファイルの書式（フォント、色、結合セル）を維持したままデータを流し込み。
- **PII（個人情報）保護**: Gemini APIにデータを送信する前に、氏名や電話番号などの個人情報を自動でマスキング。
- **完全ステートレス**: サーバー側に一切のデータを残さない（DB不使用、メモリ完結型）。
- **証跡レシート発行**: 処理のハッシュ値や時間を記録した「処理レシート」を発行し、透明性を確保。

## 技術スタック

- **Backend**: Python 3.11+ / FastAPI
- **Frontend**: Streamlit
- **AI**: Google Cloud Vertex AI (Gemini 1.5 Pro)
- **Excel**: openpyxl
- **Infrastructure**: Docker / Google Cloud Run
- **Monitoring**: Sentry (PIIスクラブ設定済み)
- **CI/CD**: GitHub Actions

## ディレクトリ構成

```
excelforge/
├── app/                # FastAPI バックエンド
│   ├── api/            # エンドポイント・認証
│   ├── core/           # 抽出・書き込み・マスキングの核ロジック
│   ├── models/         # Pydanticスキーマ・列挙型
│   └── utils/          # クリーンアップ・レシート生成
├── streamlit_app/      # Streamlit フロントエンド
├── tests/              # pytestによる自動テスト（60+ ケース）
├── docs/               # 設計書・ドキュメント
├── Dockerfile          # マルチステージビルド用
└── start.sh            # APIとUIの同時起動スクリプト
```

## セットアップ手順

### ローカル実行

1. **環境変数の準備**:
   `.env.example` を `.env` にコピーし、GCPプロジェクトIDを設定します。
   ```bash
   cp .env.example .env
   ```

2. **依存関係のインストール**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **アプリケーションの起動**:
   ```bash
   ./start.sh
   ```
   - API: http://localhost:8080
   - UI: http://localhost:8501

### Docker実行

```bash
docker-compose up --build
```

## 環境変数 (Settings)

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `GCP_PROJECT_ID` | Google Cloud プロジェクトID | (必須) |
| `VALID_TOKENS` | 認証用トークン（JSON形式） | `{"token":"user"}` |
| `SENTRY_DSN` | Sentry 監視用DSN | (任意) |
| `GEMINI_MODEL` | 使用するAIモデル | `gemini-1.5-pro` |

## テストと品質管理

### テストの実行
```bash
pytest tests/
```

### CI/CD
GitHub Actions により、以下のプロセスが自動化されています：
- **Lint/Type Check**: Ruff / mypy
- **Security Scan**: bandit / safety
- **Automatic Deploy**: `v*` タグのPushで Cloud Run へデプロイ

## セキュリティとプライバシー

- **No Persistence**: データベースは一切使用せず、アップロードされたファイルもメモリ上で処理後、直ちに破棄されます。
- **PII Scrubbing**: Sentryに送信されるエラーログからも個人情報が自動的に除外されます。
- **Masking**: AIモデルに送信される前に、機密情報はランダムな文字列に置き換えられます。

---
© 2026 ExcelForge Team. Developed for Advanced Agentic Coding.
