"""
tests/test_commercial_end_to_end.py — Commercial Pipeline エンドツーエンドテスト
"""
import asyncio
import json
import time
from typing import Dict, Any

import httpx
import pytest

# ----------------------------------------------------------------------
# ユーティリティ: ステータスポーリング
# ----------------------------------------------------------------------
async def wait_for_task_completion(task_id: str, client: httpx.AsyncClient, timeout: int = 30) -> Dict[str, Any]:
    """
    タスクのステータスをポーリングし、完了または失敗になるまで待機する。
    Returns the final status payload from the API.
    """
    elapsed = 0
    interval = 1
    while elapsed < timeout:
        try:
            resp = await client.get(f"http://localhost:8000/api/tasks/{task_id}/status")
            if resp.status_code != 200:
                pytest.fail(f"Failed to get status for task {task_id}: HTTP {resp.status_code}")
            payload = resp.json()
            status = payload.get("status")
            if status == "completed":
                return payload
            if status == "failed":
                pytest.fail(f"Task {task_id} failed: {payload.get('message')}")
            # まだ進行中
            await asyncio.sleep(interval)
            elapsed += interval
            interval = min(interval * 2, 5)  # 指数バックオフ
        except Exception as e:
            pytest.fail(f"Error while polling task status: {e}")
    pytest.fail(f"Timed out waiting for task {task_id} to complete")


# ----------------------------------------------------------------------
# テスト本体
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_commercial_pipeline_end_to_end():
    """
    エンドツーエンドテストシナリオ：
    1. /api/commercial/run でパイプラインを起動
    2. /api/tasks/{id}/status で完了を待機
    3. /api/novel/1/report でレポートを取得
    4. レポートに必要な 필드が存在することを検証
    """
    # ---------- 1. 商用化API呼出 ----------
    commercial_config = {
        "series_config": {
            "title": "終端チェストテスト作品",
            "genre": "fantasy",
            "concept": "テスト用のファンタジー作品",
            "keywords": ["テスト", "ファンタジー", "世界観"],
            "target_eps": 2,
            "target_word_count_per_episode": 1500
        },
        "samples": [],
        "platforms": ["kakuyomu"]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # POSTでパイプライン実行リクエスト
        resp = await client.post(
            "http://localhost:8000/api/commercial/run",
            json=commercial_config,
            timeout=60.0
        )
        assert resp.status_code == 200, f"商用化APIが失敗: {resp.status_code} {resp.text}"
        result = resp.json()
        trace_id = result.get("trace_id") or result.get("task_id")
        assert trace_id, "trace_idまたはtask_idが応答に含まれていません"

        # ---------- 2. ステータスポーリング ----------
        status_payload = await wait_for_task_completion(trace_id, client, timeout=30)
        assert status_payload.get("status") == "completed", "タスクが完了しなかった"

        # ---------- 3. レポート取得 ----------
        report_resp = await client.get("http://localhost:8000/api/novel/1/report")
        assert report_resp.status_code == 200, f"レポート取得失敗: {report_resp.status_code}"
        report_data = report_resp.json()

        # ---------- 4. レポート構造検証 ----------
        # 必須 fields（簡易チェック）
        required_keys = [
            "title", "genre", "target_word_count", "token_usage",
            "episode_summaries", "quality_metrics", "total_generation_time"
        ]
        for key in required_keys:
            assert key in report_data, f"レポートに必須キー '{key}' が欠如しています"

        # トークン使用量に関するサブキー
        token_usage = report_data["token_usage"]
        assert "total_tokens" in token_usage
        assert "input_tokens" in token_usage
        assert "output_tokens" in token_usage
        assert "episode_count" in token_usage

        # エピソードサマリーにエピソード数が期待値と一致するか
        episodes = report_data["episode_summaries"]
        assert len(episodes) == 2, f"期待されたエピソード数が不一致 (期待:2, 実際:{len(episodes)})"

        # 各エピソードに必須フィールドが存在するか
        for ep in episodes:
            ep_required = ["ep_num", "title", "word_count", "summary", "quality_score"]
            for req in ep_required:
                assert req in ep, f"エピソード {ep['ep_num']} に必須フィールド '{req}' が欠如"

        # 品質メトリクスのスコアは 0.0〜1.0 の範囲にあるか
        qm = report_data["quality_metrics"]
        for score_field in qm.dict():
            if not str(score_field).startswith("_"):  # 読み取り可能なスコープのみ
                score = getattr(qm, score_field)
                assert isinstance(score, (int, float)), f"{score_field} は数値であるべき"
                assert 0.0 <= score <= 1.0, f"{score_field} のスコアが 0.0-1.0 の範囲外: {score}"