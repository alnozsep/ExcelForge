#!/bin/bash

# 単一プロセス構成: Streamlitのみ起動（処理エンジンは同一プロセス内で直接呼び出す）
# 従来のFastAPIバックグラウンドプロセスは不要になった
export PYTHONPATH=$PYTHONPATH:.

# Streamlitをフォアグラウンドで起動
# Cloud Runは環境変数 PORT でアクセスしてくるのでそれを使用
streamlit run streamlit_app/app.py \
    --server.port ${PORT:-8080} \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
