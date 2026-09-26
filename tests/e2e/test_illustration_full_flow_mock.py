"""統合イラスト生成の E2E（mock モード・ネットワーク遮断）。

1話分のフルフロー（挿絵ポイント生成 → 5種別の画像生成 → 永続化）を
外部ネットワークなしで通しで検証する。
"""

from __future__ import annotations

import asyncio

import pytest

from src.models.illustration import (
    IllustrationRequest,
    IllustrationType,
)
from src.services.illustration.wiring import (
    build_illustration_agent,
    build_unified_illustration_generator,
    resolve_illustration_generator_step,
)

ALL_TYPES = list(IllustrationType)


class _StatusReporter:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def update_progress(self, current, total, message=""):
        self.messages.append(message)

    def report(self, message, level="info"):
        self.messages.append(f"[{level}] {message}")

    def report_progress(self, **kwargs):
        pass


class _MemoryRepo:
    """極小のメモリ repo（create_illustration 記録のみ）。"""

    def __init__(self) -> None:
        self.saved: list[dict] = []

    async def create_illustration(self, **kwargs):
        self.saved.append(kwargs)
        return len(self.saved)

    async def get_book(self, book_id):
        return type("Book", (), {"title": "天空の城", "genre": "ファンタジー"})()

    async def get_chapters(self, book_id):
        return [
            type("Ch", (), {"number": i, "content": f"第{i}話の本文。" * 30})()
            for i in range(1, 4)
        ]

    async def get_chapter(self, book_id, ep_num):
        return type("Ch", (), {"content": f"第{ep_num}話の本文。" * 30})()


def _context(book_id: int = 1, **kwargs):
    from src.services.pipeline_base import WorkflowContext

    params = {
        "genre": "ファンタジー",
        "keywords": "魔法,剣",
        "archetype_key": "チート主人公",
        "target_eps": 3,
        "initial_limit": 3,
        "word_count": 2000,
        "book_id": book_id,
    }
    params.update(kwargs)
    return WorkflowContext(**params)


def _engine():
    class _Bible:
        characters = [type("C", (), {"name": "アルト"})()]

    class _Engine:
        class repo:  # noqa: N801
            class bible:  # noqa: N801
                @staticmethod
                async def get_by_book_id(book_id):
                    return _Bible()

            class plot:  # noqa: N801
                @staticmethod
                async def get_all_plots(book_id):
                    return [type("P", (), {})() for _ in range(3)]

            class episode:  # noqa: N801
                @staticmethod
                async def get_all_by_book_id(book_id):
                    return [type("E", (), {})() for _ in range(3)]

    return _Engine()


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """APIキー無し・疑似生成・外部ネットワーク遮断で実行する。"""
    for key in ("GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY", "NANOBANANA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AUTONOVEL_IMAGE_MOCK", "1")


def test_e2e_all_five_types_generate_offline(tmp_path):
    """【E2E】APIキー無しでも5種別すべてが画像になる。"""
    generator = build_unified_illustration_generator(output_root=tmp_path / "out")
    results = asyncio.run(
        generator.generate_batch(
            [
                IllustrationRequest(
                    book_id=1,
                    illustration_type=t,
                    episode_number=1,
                    scene_text="夜空の下、主人公が剣を抜いた。" * 3,
                    book_context={"title": "天空の城", "genre": "ファンタジー"},
                    panels=24 if t == IllustrationType.MANGA_24PANEL else 6,
                )
                for t in ALL_TYPES
            ]
        )
    )
    assert all(r is not None for r in results)
    assert len({r.request.illustration_type for r in results}) == 5
    for result in results:
        assert result.image_path.exists()
        assert result.model_used == "gemini-3.1-flash-lite-image"
    # 出力は book_id 配下に揃う
    assert {p.parent.name for p in (tmp_path / "out").rglob("*.png")} == {"1"}


def test_e2e_points_to_images_pipeline(tmp_path):
    """【E2E】挿絵ポイント生成 → 画像生成まで一気通貫する。"""
    generator = build_unified_illustration_generator(output_root=tmp_path / "out")
    step = resolve_illustration_generator_step(generator)
    ctx = _context(enable_illustration=True, enable_illustration_generation=True)
    reporter = _StatusReporter()

    assert asyncio.run(step.execute(ctx, _engine(), reporter)) is True
    assert ctx.illustration_points, "挿絵ポイントが生成されていない"
    assert ctx.illustrations, "画像が生成されていない"
    assert all(row["image_path"] for row in ctx.illustrations)


def test_e2e_points_to_images_disabled_by_default(tmp_path):
    """【E2E】既定では画像生成しない（既存パイプライン挙動の維持）。"""
    generator = build_unified_illustration_generator(output_root=tmp_path / "out")
    step = resolve_illustration_generator_step(generator)
    ctx = _context(enable_illustration=True)
    assert asyncio.run(step.execute(ctx, _engine(), _StatusReporter())) is True
    assert ctx.illustrations == []


def test_e2e_agent_persists_all_types(tmp_path):
    """【E2E】Agent 経由で5種別を生成し、DB 永続化される。"""
    repo = _MemoryRepo()
    agent = build_illustration_agent(
        repo=repo, output_root=tmp_path / "out", image_service=None
    )

    async def _run():
        out = []
        for illo_type in ALL_TYPES:
            result = await agent.run(
                request=IllustrationRequest(
                    book_id=5,
                    illustration_type=illo_type,
                    episode_number=2,
                    scene_text="Castle on the hill at night." * 2,
                    book_context={"title": "天空の城", "genre": "ファンタジー"},
                    panels=24 if illo_type == IllustrationType.MANGA_24PANEL else 6,
                )
            )
            out.append(result)
        return out

    results = asyncio.run(_run())
    assert all(r["status"] == "success" for r in results)
    assert all(r["result"].illustration_id for r in results)
    assert len(repo.saved) == 5
    assert {row["illustration_type"] for row in repo.saved} == {
        t.value for t in ALL_TYPES
    }
    assert all(row["book_id"] == 5 for row in repo.saved)


def test_e2e_workflow_full_flow(tmp_path):
    """【E2E】Workflow で表紙＋挿絵＋6コマ＋24コマがまとめて生成される。"""
    from src.backend.workflows.illustration_workflow import IllustrationWorkflow

    repo = _MemoryRepo()
    agent = build_illustration_agent(
        repo=repo, output_root=tmp_path / "out", image_service=None
    )
    workflow = IllustrationWorkflow(illustration_agent=agent, repo=repo)
    reporter = _StatusReporter()

    result = asyncio.run(
        workflow.execute(
            reporter,
            book_id=3,
            settings={
                "enableIllustration": True,
                "generateCover": True,
                "generateEpisodeIllustrations": True,
                "episodeInterval": 2,
                "generateYonkoma": True,
                "generateManga24": True,
            },
        )
    )
    assert result["status"] == "success"
    produced = result["illustrations"]
    types = {r.request.illustration_type for r in produced}
    assert IllustrationType.COVER in types
    assert IllustrationType.EPISODE in types
    assert IllustrationType.YONKOMA in types
    assert IllustrationType.MANGA_24PANEL in types


def test_e2e_cost_budget_per_episode(tmp_path):
    """【E2E】1話分のコストが上限内に収まる（予算崩壊の防止）。"""
    generator = build_unified_illustration_generator(output_root=tmp_path / "out")
    requests = [
        IllustrationRequest(
            book_id=1,
            illustration_type=t,
            episode_number=1,
            scene_text="x" * 200,
            book_context={"title": "T", "genre": "ファンタジー"},
            panels=24 if t == IllustrationType.MANGA_24PANEL else 6,
        )
        for t in ALL_TYPES
    ]
    total = generator.estimate_cost_batch(requests)
    # 5種別（うち24コマ1枚）= 5 * $0.034 = $0.17
    assert total == pytest.approx(0.17, abs=0.001)
    assert total <= 0.25, "1話あたりのイラストコストが上限を超過"


def test_e2e_idempotent_regeneration(tmp_path):
    """【E2E】同じ設定で2回実行してもファイルが衝突しない。"""
    generator = build_unified_illustration_generator(output_root=tmp_path / "out")
    request = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.MANGA_24PANEL,
        episode_number=1,
        scene_text="Story text. " * 50,
        book_context={"title": "T", "genre": "ファンタジー"},
    )
    first = asyncio.run(generator.generate(request))
    second = asyncio.run(generator.generate(request))
    assert first.image_path != second.image_path
    assert len(list((tmp_path / "out" / "1").glob("*.png"))) == 2


def test_e2e_rollout_env_var_switch(tmp_path, monkeypatch):
    """【E2E】環境変数1つでモデルが切り替わり、出力は同じ形になる。"""
    seen = []
    for model_key, expected in (
        ("nanobanana2lite", "gemini-3.1-flash-lite-image"),
        ("imagen_ultra", "imagen-4.0-ultra-generate-001"),
    ):
        monkeypatch.setenv("AUTONOVEL_IMAGE_MODEL", model_key)
        generator = build_unified_illustration_generator(output_root=tmp_path / model_key)
        result = asyncio.run(
            generator.generate(
                IllustrationRequest(
                    book_id=1,
                    illustration_type=IllustrationType.COVER,
                    scene_text="cover",
                    book_context={"title": "T", "genre": "ファンタジー"},
                )
            )
        )
        assert result.model_used == expected
        assert result.image_path.exists()
        seen.append(result.prompt)
    assert seen[0] == seen[1], "プロンプトはモデルに依存しない"
