# AutoNovel Backend Dockerfile (単一ステージ構成)
ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION}
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 依存パッケージインストール（C拡張ビルドに必要な最小ツールを含む）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc libpq-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /root/.cache

# アプリケーションソースをコピー
COPY src/ ./src/
COPY config/ ./config/
COPY database/ ./database/
COPY docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY formatters/ ./formatters/
COPY plugins/ ./plugins/
COPY prompts/ ./prompts/
COPY schemas/ ./schemas/
COPY alembic.ini ./
COPY pyproject.toml ./
COPY requirements.txt ./

RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8200

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]
