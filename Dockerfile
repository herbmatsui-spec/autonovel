# AutoNovel Backend Dockerfile (マルチステージ builder→runtime slim)
# Step 61: 依存インストールを builder ステージに分離し、runtime は最小構成。

ARG PYTHON_VERSION=3.12-slim

# ---- builder: 依存インストール ----
FROM python:${PYTHON_VERSION} AS builder
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# C拡張ビルドに必要な最小ツール
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --user --upgrade pip && \
    pip install --user -r requirements.txt

# ---- runtime: 実行環境 ----
FROM python:${PYTHON_VERSION} AS runtime
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# ランタイムに必要な最小共有ライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# builder から --user インストール成果物を複製
COPY --from=builder /root/.local /root/.local

# アプリケーションソースをコピー
COPY src/ ./src/
COPY pyproject.toml ./
COPY requirements.txt ./

EXPOSE 8200

# ヘルスチェック用
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').status == 200 else 1)"

CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]
