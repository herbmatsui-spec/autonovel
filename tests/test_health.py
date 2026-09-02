"""FastAPI アプリケーションのヘルスチェック & 入力バリデーションテスト。

Phase 5 (Step 55-58) で ``/health`` を DB 接続・Huey 生存・メトリクスを
含めた総合ステータスに拡充している。本テストは:
  * ``status`` フィールドの互換性 (``ok`` を含む)
  * ``components.database`` / ``components.queue`` の存在と status 形状
  * ``metrics`` カウンタの型
を検証する。

Step 48: /easy_mode/generate の 422 (バリデーションエラー) と
        /easy_mode/export/{book_id} の 422 (book_id < 1) を検証します。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.observability.health import metrics
from src.backend.server import app

client = TestClient(app)


def test_health_ok() -> None:
    """GET /health は 200 & ``status`` を含む拡充ペイロードを返す。

    Phase 5 拡充後でも ``status`` は全コンポーネント正常時に ``ok`` を
    返す設計のため、既存の後方互換アサーションを維持する。
    """
    metrics.reset()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}


def test_health_includes_components() -> None:
    """GET /health は components.database / components.queue を含む。"""
    metrics.reset()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    components = body.get("components", {})
    assert "database" in components
    assert "queue" in components
    assert components["database"]["status"] in {"ok", "error"}
    assert components["queue"]["status"] in {"ok", "error"}


def test_metrics_endpoint() -> None:
    """GET /metrics はカウンタスナップショットを返す。"""
    metrics.reset()
    # /health を叩いて health_checks を increment させる
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert "tasks_enqueued" in body
    assert "exports_succeeded" in body
    assert body["health_checks"] >= 1


def test_generate_returns_422_on_invalid_payload() -> None:
    """Step 48a: content_length_limit が 0 (ge=1 違反) で 422 を返す。"""
    # EasyModeInput.content_length_limit は Field(ge=1, le=10000)。
    # 0 を送ると 422 になることを確認。
    resp = client.post(
        "/easy_mode/generate",
        json={
            "current_chapter": "",
            "chapter_history": [],
            "character_params": "",
            "content_length_limit": 0,
        },
    )
    assert resp.status_code == 422


def test_export_returns_422_on_non_positive_book_id() -> None:
    """Step 48b: Path(ge=1) 違反で 0 は 422 を返す。"""
    resp = client.get("/easy_mode/export/0")
    assert resp.status_code == 422
