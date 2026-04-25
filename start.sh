#!/bin/bash

# FastAPIをバックグラウンドで起動（ポート8081で内部用）
uvicorn app.main:app --host 0.0.0.0 --port 8081 &

# Streamlitが内部APIを参照できるように環境変数をセット
export API_BASE_URL="http://localhost:8081/api/v1"
export PYTHONPATH=$PYTHONPATH:.

# Streamlitをフォアグラウンドで起動（メインプロセス、外部公開用）
# Cloud Runは環境変数 PORT でアクセスしてくるのでそれを使用
streamlit run streamlit_app/app.py \
    --server.port ${PORT:-8080} \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
