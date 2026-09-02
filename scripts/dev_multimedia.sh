#!/usr/bin/env bash
# Multimedia 機能有効化付きで開発サーバを起動する。
set -euo pipefail

export ENABLE_MULTIMEDIA="${ENABLE_MULTIMEDIA:-true}"
export ENABLE_AUDIO_SYNTH="${ENABLE_AUDIO_SYNTH:-true}"
export MULTIMEDIA_OUTPUT_DIR="${MULTIMEDIA_OUTPUT_DIR:-storage/multimedia}"

cd "$(dirname "$0")/.."
exec uvicorn src.backend.server:app --host 0.0.0.0 --port 8200 --reload
