"""Step 26 検証テスト: プロセス内メトリクス（/metrics）のメモリリーク防止.

長時間稼働時にメトリクスカウンタが肥大化しないよう、固定キー集計に限定し、
動的ラベル生成を抑制していることを検証する。
"""

from __future__ import annotations

from src.backend.observability.health import _ALLOWED_COUNTER_KEYS, metrics


class TestFixedKeyAggregation:
    def test_allowed_keys_are_fixed_set(self):
        """許容キーが frozenset（固定集合）であること。"""
        assert isinstance(_ALLOWED_COUNTER_KEYS, frozenset)

    def test_known_keys_increment(self):
        """既知キーは正常に加算されること。"""
        metrics.reset_for_testing()
        metrics.increment("tasks_enqueued", 5)
        assert metrics.get("tasks_enqueued") == 5

    def test_unknown_keys_ignored(self):
        """未知の動的キーは無視されること（メモリリーク防止）。"""
        metrics.reset_for_testing()
        for i in range(1000):
            metrics.increment(f"dynamic_label_{i}")
        snapshot = metrics.snapshot()
        # 動的キーが 1 つも追加されていないこと
        assert len(snapshot) == len(_ALLOWED_COUNTER_KEYS)
        assert all(not k.startswith("dynamic_label_") for k in snapshot)

    def test_long_keys_ignored(self):
        """64 文字超のキーは無視されること。"""
        metrics.reset_for_testing()
        long_key = "x" * 100
        metrics.increment(long_key)
        snapshot = metrics.snapshot()
        assert long_key not in snapshot

    def test_no_growth_after_many_increments(self):
        """大量の increment 後もカウンタキー数が増えないこと。"""
        metrics.reset_for_testing()
        initial_size = len(metrics.snapshot())
        for i in range(10_000):
            metrics.increment(f"request:{i % 7}:user:{i}")  # 動的ラベル風キー
        assert len(metrics.snapshot()) == initial_size

    def test_snapshot_returns_copy(self):
        """snapshot() がコピーを返すこと（外部変更の影響を受けない）。"""
        metrics.reset_for_testing()
        snapshot = metrics.snapshot()
        snapshot["tasks_enqueued"] = 999
        assert metrics.get("tasks_enqueued") == 0

    def test_reset_for_testing(self):
        metrics.increment("health_checks", 10)
        metrics.reset_for_testing()
        assert metrics.get("health_checks") == 0

    def test_counter_values_are_int(self):
        metrics.reset_for_testing()
        metrics.increment("tasks_completed", 3)
        snapshot = metrics.snapshot()
        assert all(isinstance(v, int) for v in snapshot.values())
