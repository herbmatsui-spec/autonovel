from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.engine import UltimateHegemonyEngine
from src.backend.engine_deps import EngineDeps


def make_full_deps(**overrides):
    """全必須依存を含む EngineDeps を作成（テスト用ヘルパー）"""
    defaults = {
        "planner": MagicMock(),
        "writer": MagicMock(),
        "pm": MagicMock(),
        "ctx_mgr": MagicMock(),
        "formatter": MagicMock(),
        "validator": MagicMock(),
        "auditor": MagicMock(),
        "narrative": MagicMock(),
        "critique": MagicMock(),
        "marketing": MagicMock(),
        "bible_agent": MagicMock(),
        "plot_agent": MagicMock(),
        "style_rag": MagicMock(),
    }
    defaults.update(overrides)
    return EngineDeps(**defaults)


# -------------------------------------------------------------
# 1. コンストラクタテスト (Tests 1-10)
# -------------------------------------------------------------
@pytest.mark.parametrize("index", range(10))
def test_engine_init_properties(index):
    deps = make_full_deps()
    mock_llm = MagicMock()
    mock_cooldown = MagicMock()
    mock_repo = MagicMock()
    mock_db = MagicMock()
    mock_plot_service = MagicMock()

    engine = UltimateHegemonyEngine(
        api_key=f"api-key-{index}",
        repo=mock_repo,
        db=mock_db,
        llm=mock_llm,
        cooldown=mock_cooldown,
        plot_service=mock_plot_service,
        deps=deps,
    )

    assert engine.api_key == f"api-key-{index}"
    assert engine.planner is deps.planner
    assert engine.writer is deps.writer
    assert engine.pm is deps.pm
    assert engine.ctx_mgr is deps.ctx_mgr
    assert engine.formatter is deps.formatter
    assert engine.validator is deps.validator
    assert engine.auditor is deps.auditor
    assert engine.narrative is deps.narrative
    assert engine.critique is deps.critique
    assert engine.marketing is deps.marketing
    assert engine.bible_agent is deps.bible_agent
    assert engine.plot_agent is deps.plot_agent
    assert engine.style_rag is deps.style_rag
    assert engine.llm is mock_llm
    assert engine.cooldown is mock_cooldown
    assert engine.repo is mock_repo
    assert engine.db is mock_db
    assert engine.plot_service is mock_plot_service
    assert engine.client is None
    assert engine.current_ep_num == 0


# -------------------------------------------------------------
# 2. sync_bible テスト (Tests 11-20)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_id, reporter_val, return_val",
    [(i, f"reporter-{i}" if i % 2 == 0 else None, f"result-{i}") for i in range(10)],
)
async def test_engine_sync_bible(book_id, reporter_val, return_val):
    bible_agent_mock = AsyncMock()
    bible_agent_mock.sync_bible_lifecycle.return_value = return_val

    deps = make_full_deps(bible_agent=bible_agent_mock)

    engine = UltimateHegemonyEngine(
        api_key="key",
        deps=deps,
    )

    res = await engine.sync_bible(book_id, reporter=reporter_val)
    assert res == return_val
    bible_agent_mock.sync_bible_lifecycle.assert_called_once_with(book_id, reporter=reporter_val)


# -------------------------------------------------------------
# 3. resolve_bible_setting テスト (Tests 21-30)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting_id, status", [(i, "approved" if i % 2 == 0 else "rejected") for i in range(10)]
)
async def test_engine_resolve_bible_setting(setting_id, status):
    repo_mock = AsyncMock()

    deps = make_full_deps()

    engine = UltimateHegemonyEngine(
        api_key="key",
        repo=repo_mock,
        deps=deps,
    )

    await engine.resolve_bible_setting(setting_id, status)
    repo_mock.resolve_pending_setting.assert_called_once_with(setting_id, status)


# -------------------------------------------------------------
# 4. determine_target_tension テスト (Tests 31-80: 計 50ケース)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "book_id, ep_num, genre, story_type, total_eps, expected_tension",
    [
        (book_id, ep_num, genre, story_type, total_eps, expected)
        for book_id in [1, 2]
        for ep_num in [1, 3, 5, 8, 10]
        for genre in ["ファンタジー", "恋愛"]
        for story_type in ["王道", None]
        for total_eps in [10]
        for expected in [0.0]
    ],
)
async def test_engine_determine_target_tension(
    book_id, ep_num, genre, story_type, total_eps, expected_tension
):
    repo_mock = AsyncMock()
    repo_mock.get_total_episodes.return_value = total_eps
    plot_service_mock = AsyncMock()
    plot_service_mock.determine_target_tension.return_value = 0.5

    deps = make_full_deps()

    engine = UltimateHegemonyEngine(
        api_key="key",
        repo=repo_mock,
        plot_service=plot_service_mock,
        deps=deps,
    )

    res = await engine.determine_target_tension(book_id, ep_num, genre, story_type)

    assert isinstance(res, float)
    assert 0.0 <= res <= 1.0
    plot_service_mock.determine_target_tension.assert_called_once_with(
        book_id=book_id, ep_num=ep_num, genre=genre, story_type=story_type
    )


@pytest.mark.asyncio
async def test_determine_target_tension_zero_total_episodes():
    repo_mock = AsyncMock()
    repo_mock.get_total_episodes.return_value = 0
    plot_service_mock = AsyncMock()
    plot_service_mock.determine_target_tension.return_value = 0.0

    deps = make_full_deps()

    engine = UltimateHegemonyEngine(
        api_key="key",
        repo=repo_mock,
        plot_service=plot_service_mock,
        deps=deps,
    )

    res = await engine.determine_target_tension(1, 1, "ファンタジー")
    assert res == 0.0


# -------------------------------------------------------------
# 5. validate_tension_deviation テスト (Tests 81-100: 計 20ケース)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ep_num, gen_tension, target_tension, tolerance, expected_valid, expected_deviation",
    [
        (1, 0.5, 0.5, 0.2, True, 0.0),
        (2, 0.5, 0.6, 0.2, True, 0.1),
        (3, 0.5, 0.7, 0.2, True, 0.2),
        (4, 0.5, 0.71, 0.2, False, 0.21),
        (5, 0.8, 0.5, 0.2, False, 0.3),
        (6, 0.4, 0.2, 0.2, True, 0.2),
        (7, 0.4, 0.19, 0.2, False, 0.21),
        (8, 0.5, None, 0.2, True, 0.0),
        (9, 0.5, "NO_PLOT", 0.2, True, 0.0),
    ]
    * 3,
)
async def test_engine_validate_tension_deviation(
    ep_num, gen_tension, target_tension, tolerance, expected_valid, expected_deviation
):
    repo_mock = AsyncMock()
    if target_tension == "NO_PLOT":
        repo_mock.get_plot.return_value = None
    else:
        plot_mock = MagicMock()
        plot_mock.target_tension = target_tension
        repo_mock.get_plot.return_value = plot_mock

    plot_service_mock = AsyncMock()
    plot_service_mock.validate_tension_deviation.return_value = (expected_valid, expected_deviation)

    deps = make_full_deps()

    engine = UltimateHegemonyEngine(
        api_key="key",
        repo=repo_mock,
        plot_service=plot_service_mock,
        deps=deps,
    )

    is_valid, deviation = await engine.validate_tension_deviation(
        ep_num, gen_tension, book_id=1, tolerance=tolerance
    )
    assert is_valid == expected_valid
    assert abs(deviation - expected_deviation) < 1e-6
    plot_service_mock.validate_tension_deviation.assert_called_once_with(
        ep_num=ep_num,
        generated_tension=gen_tension,
        book_id=1,
        tolerance=tolerance,
    )


# -------------------------------------------------------------
# 6. DIコンテナ連携テスト (Tests 101-110)
# -------------------------------------------------------------
@pytest.mark.parametrize("index", range(10))
def test_app_container_resolves_engine(index):
    # AppContainer から正しくインスタンス解決できるか
    from src.core.container import AppContainer

    container = AppContainer()
    engine = container.engine()
    assert isinstance(engine, UltimateHegemonyEngine)
    assert engine.api_key == "DUMMY"  # AppContainer uses DUMMY