# ===== ビルドステージ =====
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== 実行ステージ =====
FROM python:3.11-slim AS runtime

# セキュリティ: 非rootユーザーで実行
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# 依存ライブラリをコピー
COPY --from=builder /install /usr/local

# アプリケーションコードをコピー
COPY app/ ./app/
COPY streamlit_app/ ./streamlit_app/
COPY .streamlit/ ./.streamlit/

# 所有権を非rootユーザーに変更
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# ポート公開 (Cloud Runは環境変数 PORT で指定されたポートを使うため)
EXPOSE 8080
ENV PORT=8080

# 起動コマンド（FastAPI + Streamlitを同時起動）
COPY --chown=appuser:appuser start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
