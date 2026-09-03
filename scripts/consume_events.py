#!/usr/bin/env python3
"""
scripts/consume_events.py

Agent イベントを Redis Streams から購読し、ログ出力 / メトリクス送信するコンシューマー例。
将来的に独立サービス化するための雛形。

Usage:
    USE_REDIS_EVENTS=true python scripts/consume_events.py
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import sys

import redis.asyncio as redis


STREAM_KEY_PREFIX = "agent_events:"
CONSUMER_GROUP = "event_consumers"
CONSUMER_NAME = "consumer_1"


async def consume_events(redis_url: str = "redis://localhost:6379/0") -> None:
    """イベントを継続購読して処理する。"""
    client = redis.from_url(redis_url, decode_responses=True)

    # コンシューマーグループ作成（存在しない場合）
    try:
        await client.xgroup_create(STREAM_KEY_PREFIX + "*", CONSUMER_GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    print(f"Started consuming events from {STREAM_KEY_PREFIX}* with group {CONSUMER_GROUP}")

    try:
        while True:
            # 新しいイベントをブロッキング読み取り（5秒タイムアウト）
            streams = await client.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                {STREAM_KEY_PREFIX + "*": ">"},
                count=10,
                block=5000,
            )

            for stream_name, messages in streams:
                for msg_id, data in messages:
                    try:
                        event = {
                            "agent": data.get("agent", ""),
                            "payload": json.loads(data.get("payload", "{}")),
                            "correlation_id": data.get("correlation_id", ""),
                        }
                        # イベント処理（ログ出力 / メトリクス送信 / など）
                        print(f"[EVENT] {event['agent']} | {event['correlation_id']} | {event['payload']}")

                        # TODO: ここでメトリクス送信、アラート判定、外部システム通知など

                        # 確認応答（ACK）
                        await client.xack(stream_name, CONSUMER_GROUP, msg_id)

                    except Exception as e:
                        print(f"Error processing event {msg_id}: {e}", file=sys.stderr)
                        # 再試行のために NACK しない（再配信される）

    except asyncio.CancelledError:
        print("Consumer cancelled")
    finally:
        await client.close()


def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler():
        print("Shutdown signal received")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows などでは未対応
            pass

    try:
        loop.run_until_complete(consume_events(redis_url))
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()