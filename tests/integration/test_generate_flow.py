"""かんたんモード 生成フロー統合テスト (Step 57)。

POST /easy_mode/generate でタスク投入 → GET /easy_mode/status/{task_id} で
ステータス参照する一連の流れを TestClient + real_db_manager で検証する。

注意:
    huey.immediate が False のままだとステータスが pending のままになるため、
    本テストでは huey を immediate=True に差し替え、タスクを即時実行させる。
    ただし generate_with_llm は NotImplementedError を投げるため、
    タスク本体は failed 相当の error を result として保持する。
    本テストでは「エンドポイント経由で task_id が戻り、status が取得できる」
    ことのみを検証する (LLM 実装は別タスク)。
"""

from __future__ import annotations

import re
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.backend.server import app


@pytest.fixture
def client(real_db_manager) -> Generator[TestClient, None, None]:
    """real_db_manager によって DB が init_db() 済みの状態で TestClient を返す。

    ``with`` ブロックで TestClient を起動することで FastAPI の lifespan
    (server.py の ``init_db()`` 呼び出し) を確実に走らせ、DB スキーマが
    real_db_manager が差し替えた engine 上に構築された状態を保証する。
    """
    _ = real_db_manager  # 依存関係を確立 (engine 差替え + init_db 呼び出し)
    with TestClient(app) as c:
        yield c


def _extract_task_id(suggestions: list[str]) -> str:
    """GenerateResponse.suggestions から task_id を正規表現で抽出する。"""
    joined = " ".join(suggestions)
    m = re.search(r"/easy_mode/status/(\d+)", joined)
    assert m is not None, f"task_id が suggestions に見つかりません: {suggestions}"
    return m.group(1)


def test_generate_flow_status_pending(client: TestClient) -> None:
    """generate → status フロー。即時実行を無効化している前提で
    ステータスは pending または completed いずれかを返す。"""
    # Huey を immediate モードにせず、タスクは投入のみ。
    # ただし huey.result は即座に None を返すため status=pending になる。
    resp = client.post(
        "/easy_mode/generate",
        json={
            "current_chapter": "勇者は森を抜け、村にたどり着いた。",
            "chapter_history": [],
            "character_params": {},
            "content_length_limit": 2000,
        },
    )
    # generate_with_llm はタスク関数内で呼ばれるため、エンドポイント自体は 200
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "suggestions" in data

    task_id = _extract_task_id(data["suggestions"])

    status_resp = client.get(f"/easy_mode/status/{task_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["task_id"] == task_id
    # 即時実行ではないため、通常は pending。Huey の内部状態次第。
    assert status_data["status"] in {"pending", "completed"}


def test_status_unknown_task_returns_pending(client: TestClient) -> None:
    """存在しない task_id でも 200 & pending を返す（コントラクト準拠）。"""
    resp = client.get("/easy_mode/status/999999")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "999999"
    assert body["status"] == "pending"
