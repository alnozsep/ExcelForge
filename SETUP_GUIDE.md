# ExcelForge 本番環境構築・ユーザー作業 完全マニュアル

本ドキュメントは、ExcelForgeを本番稼働させるために**ユーザー様（管理者）が実施しなければならないすべての作業**を限りなく詳細にまとめたチェックリスト兼手順書です。

上から順に実行することで、セキュアなCI/CDパイプラインと監視体制を備えた本番環境が完成します。

---

## 第1章: Sentry（エラー監視）のセットアップ

Sentryは、システム内で発生したエラー（API通信エラー、ファイルのパース失敗、予期せぬクラッシュなど）を検知し、即座に開発者に通知するクラウド監視サービスです。

### 1-1. Sentryアカウントとプロジェクトの作成
1. [Sentry公式サイト](https://sentry.io/) にアクセスし、アカウントを作成します（無料プランのDeveloperで十分です）。
2. ダッシュボードから `[Create Project]` をクリックします。
3. プラットフォームとして **「FastAPI」** または **「Python」** を選択します。
4. プロジェクト名（例: `excelforge-backend`）を入力し、`[Create Project]` をクリックします。

### 1-2. DSN（データソース名）の取得
1. プロジェクト作成後に表示される設定画面、または `Settings > Projects > (作成したプロジェクト) > Client Keys (DSN)` に移動します。
2. `https://xxxxxx@xxxxxx.ingest.sentry.io/xxxxxx` という形式のURL（**DSN**）をコピーして控えておきます。

### 1-3. Sentry側のセキュリティ設定（PII保護の強化）
※コード側（`masking.py` や `before_send`）でもPII（個人情報）を除外していますが、Sentryのダッシュボード側でも念押しで設定します。
1. `Settings > Security & Privacy` に移動します。
2. **「Data Scrubbing」** をオンにします。
3. **「Scrub IP Addresses」** をオンにします（ユーザーのIPアドレスを保存しないため）。
4. **「Advanced Data Scrubbing」** にて、`[password, secret, token, api_key, authorization]` などの機密文字列が自動でマスクされる設定になっていることを確認します。

---

## 第2章: Google Cloud (GCP) のセットアップ

ExcelForgeのバックエンド、AI処理、およびシークレット管理を行う中核となる設定です。

### 2-1. プロジェクトの作成と課金設定
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセスします。
2. 新しいプロジェクトを作成します（例: `excelforge-production`）。
3. 控えておく値: **プロジェクトID**（例: `excelforge-production-1234`）
4. メニューから「お支払い（Billing）」に移動し、プロジェクトに請求先アカウントが紐付いていることを確認します。

### 2-2. 必要なAPIの有効化
画面上部の検索バーから以下のAPIを検索し、すべて「有効にする（Enable）」をクリックします。
- `Vertex AI API` (AIによるデータ抽出用)
- `Cloud Run API` (アプリケーションのホスティング用)
- `Secret Manager API` (環境変数・機密情報の安全な保管用)
- `IAM Service Account Credentials API` (GitHub Actionsからの認証用)

### 2-3. Secret Manager への機密情報の登録
Cloud Consoleのメニューから `[セキュリティ] > [Secret Manager]` に移動し、以下の2つのシークレットを作成します。

1. **SENTRY_DSN**
   - 名前: `SENTRY_DSN`
   - シークレットの値: 先ほど控えたSentryのDSNを貼り付けます。
2. **VALID_TOKENS**
   - 名前: `VALID_TOKENS`
   - シークレットの値: 認証用トークンのJSON文字列を入力します。
     （例: `{"secret_token_client_a": "株式会社A", "secret_token_client_b": "株式会社B"}`）

### 2-4. Cloud Run実行用サービスアカウントの作成
1. `[IAMと管理] > [サービス アカウント]` に移動し、`[サービスアカウントを作成]` をクリックします。
2. 名前: `excelforge-runtime`
3. 以下のロールを付与します：
   - `Vertex AI ユーザー` (roles/aiplatform.user)
   - `Secret Manager のシークレット アクセサー` (roles/secretmanager.secretAccessor)
   - `Cloud Run 起動元` (roles/run.invoker)

### 2-5. GitHub Actions用デプロイ権限の設定 (Workload Identity Federation)
セキュリティ上、GitHubにサービスアカウントキー（JSON）を持たせないための推奨設定です。

1. [Googleの公式手順 (Auth Action)](https://github.com/google-github-actions/auth) に従い、Workload Identity Pool と Provider を作成します。
2. プロバイダに対して、指定のGitHubリポジトリ（`alnozsep/ExcelForge`）からのアクセスのみを許可するように設定します。
3. デプロイ用の別のサービスアカウント（例: `github-deployer`）を作成し、以下のロールを付与します：
   - `Cloud Run 管理者` (roles/run.admin)
   - `サービスアカウント ユーザー` (roles/iam.serviceAccountUser)
   - `Artifact Registry 管理者` (roles/artifactregistry.admin)
4. 控えておく値:
   - **WIF_PROVIDER**: (例: `projects/123456789/locations/global/workloadIdentityPools/my-pool/providers/my-provider`)
   - **WIF_SERVICE_ACCOUNT**: (例: `github-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com`)

---

## 第3章: GitHub のセットアップ

コードの品質維持と、クラウドへの自動デプロイを構成します。

### 3-1. GitHub Secretsの登録
1. GitHubリポジトリ `alnozsep/ExcelForge` にアクセスします。
2. `Settings > Secrets and variables > Actions` に移動します。
3. `[New repository secret]` をクリックし、以下の3つを登録します。
   - `GCP_PROJECT_ID`: 控えておいたGCPのプロジェクトID
   - `WIF_PROVIDER`: 控えておいたWorkload Identity Providerの文字列
   - `WIF_SERVICE_ACCOUNT`: デプロイ用サービスアカウントのメールアドレス

### 3-2. ブランチ保護ルールの設定
1. リポジトリの `Settings > Branches` に移動します。
2. `[Add branch protection rule]` をクリックし、Branch name pattern に `main` と入力します。
3. 以下の項目にチェックを入れます：
   - **Require a pull request before merging** (直接Pushを禁止しPRを必須にする)
   - **Require status checks to pass before merging** (テストが通らないとマージできないようにする)
     - 検索窓から `lint`, `Test (Python 3.11)`, `Test (Python 3.12)`, `Security Scan` を探し、必須（Required）に設定します。
   - **Do not allow bypassing the above settings** (管理者であってもルールを強制する)
4. `[Save changes]` をクリックします。

---

## 第4章: 手元（ローカル）での確認とデプロイの実行

### 4-1. ローカルテストの確認（任意）
開発PC上で一度以下のコマンドを実行し、環境が整っているか確認します。
```bash
cp .env.example .env
# .env を開き、GCP_PROJECT_ID などを記入

# pre-commit（コミット時の自動チェック）を有効化
.venv/bin/pip install pre-commit
.venv/bin/pre-commit install
```

### 4-2. 初回デプロイの実行
以上の設定が全て終われば、本番デプロイが可能です。

1. 新しい機能や修正をコミットする。
2. GitHub上でPull Requestを作成し、自動テスト（Actions）がグリーン（成功）になるのを待つ。
3. `main` ブランチにマージする。
4. 本番環境に反映させるため、バージョンタグを打ってPushします：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
5. GitHubの `Actions` タブを開くと、「Deploy to Cloud Run」というワークフローが走り出します。
6. 数分後、成功するとCloud RunのURLが発行され、システムが本番稼働を開始します！

---

> **完了チェック**
> - [ ] Sentryのプロジェクト作成とDSN取得が完了した
> - [ ] GCPのプロジェクト作成、API有効化、Secret Managerの登録が完了した
> - [ ] GCPで実行用・デプロイ用のサービスアカウントを作成し、適切な権限を付与した
> - [ ] GitHubリポジトリに3つのSecretを登録した
> - [ ] GitHubの `main` ブランチ保護ルールを設定した
>
> 全てにチェックがつけば、ユーザー様側の作業は完了です！お疲れ様でした。
