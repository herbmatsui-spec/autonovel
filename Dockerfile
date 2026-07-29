# AutoNovel Backend Dockerfile (マルチステージ builder→runtime slim)
# Step 61: 依存インストールを builder ステージに分離し、runtime は最小構成。

ARG PYTHON_VERSION=3.12-slim

# ---- builder: 依存インストール ----
FROM python:${PYTHON_VERSION} AS builder
WORKDIR /app

# ビルドに必要な最小ツール
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ---- runtime: 実行環境 ----
FROM python:${PYTHON_VERSION} AS runtime
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# builder から --user インストール成果物を複製
COPY --from=builder /root/.local /root/.local

# アプリケーションソースをコピー
COPY src/ ./src/
COPY pyproject.toml ./

EXPOSE 8200

# ヘルスチェック用 curl を runtime に残さないため、Python でチェック
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').status == 200 else 1)"

CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]
