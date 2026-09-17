# ==========================================
# Stage 1: Build dependencies
# ==========================================
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Minimal Runtime
# ==========================================
FROM python:${PYTHON_VERSION} AS runner
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

# ランタイムに必要な共有ライブラリのみインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 非特権ユーザーの作成
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/storage /app/logs && \
    chown -R appuser:appuser /app

# builderステージからインストール済みパッケージをコピー
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# アプリケーションソースのコピー
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser database/ ./database/
COPY --chown=appuser:appuser docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=appuser:appuser formatters/ ./formatters/
COPY --chown=appuser:appuser plugins/ ./plugins/
COPY --chown=appuser:appuser prompts/ ./prompts/
COPY --chown=appuser:appuser schemas/ ./schemas/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./

RUN chmod +x /usr/local/bin/entrypoint.sh

USER appuser
EXPOSE 8200

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200", "--workers", "1"]
