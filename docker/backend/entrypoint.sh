#!/usr/bin/env bash
# AutoNovel backend container entrypoint.
#  - Run alembic upgrade head against the configured database (unless skipped).
#  - Hand off to the original command (uvicorn / huey_consumer).

set -euo pipefail

: "${ALEMBIC_DATABASE_URL:=${DATABASE_URL:-}}"
if [ -z "${ALEMBIC_DATABASE_URL}" ]; then
    echo "[entrypoint] WARN: ALEMBIC_DATABASE_URL/DATABASE_URL が未設定です" >&2
fi
export ALEMBIC_DATABASE_URL

skip_migrations=0
if [ "${1:-}" = "--skip-migrations" ] || [ "${SKIP_ALEMBIC:-0}" = "1" ]; then
    skip_migrations=1
    shift || true
fi

if [ "$skip_migrations" = "0" ]; then
    echo "[entrypoint] alembic upgrade head"
    alembic upgrade head
fi

echo "[entrypoint] starting: $*"
exec "$@"
