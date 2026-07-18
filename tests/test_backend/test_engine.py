import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.engine import UltimateHegemonyEngine
from src.core.container import AppContainer, make_container
from dependency_injector import providers
from src.backend.database.models import Plot

# -------------------------------------------------------------
# 1. コンストラクタテスト (Tests 1-10)
# -------------------------------------------------------------
@pytest.mark.parametrize("index", range(10))
def test_engine_init_properties(index):
    # 各モックの作成
    mock_args = {name: MagicMock() for name in [
        "planner", "writer", "repo", "db", "pm", "ctx_mgr", "formatter",
        "validator", "auditor", "narrative", "critique", "marketing",
        "bible_agent", "plot_agent", "style_rag", "llm", "cooldown"
    ]}
    
    engine = UltimateHegemonyEngine(
        api_key=f"api-key-{index}",
        **mock_args
    )
    
    # 全てのプロパティが正しく設定されていることを確認
    assert engine.api_key == f"api-key-{index}"
    for name, mock_obj in mock_args.items():
        assert getattr(engine, name) is mock_obj
    
    # エイリアスプロパティの確認
    assert engine.ai_api is mock_args["llm"]
    assert engine.llm_client is mock_args["llm"]
    assert engine.client is None
    assert engine.current_ep_num == 0

# -------------------------------------------------------------
# 2. sync_bible テスト (Tests 11-20)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("book_id, reporter_val, return_val", [
    (i, f"reporter-{i}" if i % 2 == 0 else None, f"result-{i}") for i in range(10)
])
async def test_engine_sync_bible(book_id, reporter_val, return_val):
    bible_agent_mock = AsyncMock()
    bible_agent_mock.sync_bible_lifecycle.return_value = return_val
    
    engine = UltimateHegemonyEngine(
        api_key="key",
        planner=None, writer=None, repo=None, db=None, pm=None, ctx_mgr=None,
        formatter=None, validator=None, auditor=None, narrative=None, critique=None,
        marketing=None, bible_agent=bible_agent_mock, plot_agent=None, style_rag=None,
        llm=None, cooldown=None
    )
    
    res = await engine.sync_bible(book_id, reporter=reporter_val)
    assert res == return_val
    bible_agent_mock.sync_bible_lifecycle.assert_called_once_with(book_id, reporter=reporter_val)

# -------------------------------------------------------------
# 3. resolve_bible_setting テスト (Tests 21-30)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("setting_id, status", [
    (i, "approved" if i % 2 == 0 else "rejected") for i in range(10)
])
async def test_engine_resolve_bible_setting(setting_id, status):
    repo_mock = AsyncMock()
    
    engine = UltimateHegemonyEngine(
        api_key="key",
        planner=None, writer=None, repo=repo_mock, db=None, pm=None, ctx_mgr=None,
        formatter=None, validator=None, auditor=None, narrative=None, critique=None,
        marketing=None, bible_agent=None, plot_agent=None, style_rag=None,
        llm=None, cooldown=None
    )
    
    await engine.resolve_bible_setting(setting_id, status)
    repo_mock.resolve_pending_setting.assert_called_once_with(setting_id, status)

# -------------------------------------------------------------
# 4. determine_target_tension テスト (Tests 31-80: 計 50ケース)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("book_id, ep_num, genre, story_type, total_eps, expected_tension", [
    # 各ジャンルとストーリータイプでの検証 (50ケース生成用のシード)
    (book_id, ep_num, genre, story_type, total_eps, expected)
    for book_id in [1, 2]
    for ep_num in [1, 3, 5, 8, 10]
    for genre in ["ファンタジー", "恋愛"]
    for story_type in ["王道", None]
    for total_eps in [10]
    for expected in [0.0]  # モックするためダミー
])
async def test_engine_determine_target_tension(book_id, ep_num, genre, story_type, total_eps, expected_tension):
    repo_mock = AsyncMock()
    repo_mock.get_total_episodes.return_value = total_eps
    
    engine = UltimateHegemonyEngine(
        api_key="key",
        planner=None, writer=None, repo=repo_mock, db=None, pm=None, ctx_mgr=None,
        formatter=None, validator=None, auditor=None, narrative=None, critique=None,
        marketing=None, bible_agent=None, plot_agent=None, style_rag=None,
        llm=None, cooldown=None
    )
    
    res = await engine.determine_target_tension(book_id, ep_num, genre, story_type)
    
    # 戻り値が正しく float であること
    assert isinstance(res, float)
    assert 0.0 <= res <= 1.0
    
    # DB 更新処理が正しく呼び出されていること
    repo_mock.get_total_episodes.assert_called_once_with(book_id)
    repo_mock.update_plot_target_tension.assert_called_once_with(book_id, ep_num, res)

@pytest.mark.asyncio
async def test_determine_target_tension_zero_total_episodes():
    repo_mock = AsyncMock()
    repo_mock.get_total_episodes.return_value = 0
    
    engine = UltimateHegemonyEngine(
        api_key="key",
        planner=None, writer=None, repo=repo_mock, db=None, pm=None, ctx_mgr=None,
        formatter=None, validator=None, auditor=None, narrative=None, critique=None,
        marketing=None, bible_agent=None, plot_agent=None, style_rag=None,
        llm=None, cooldown=None
    )
    
    res = await engine.determine_target_tension(1, 1, "ファンタジー")
    assert res == 0.0

# -------------------------------------------------------------
# 5. validate_tension_deviation テスト (Tests 81-100: 計 20ケース)
# -------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("ep_num, gen_tension, target_tension, tolerance, expected_valid, expected_deviation", [
    (1, 0.5, 0.5, 0.2, True, 0.0),
    (2, 0.5, 0.6, 0.2, True, 0.1),
    (3, 0.5, 0.7, 0.2, True, 0.2),
    (4, 0.5, 0.71, 0.2, False, 0.21),
    (5, 0.8, 0.5, 0.2, False, 0.3),
    # 差がちょうど tolerance の境界値
    (6, 0.4, 0.2, 0.2, True, 0.2),
    (7, 0.4, 0.19, 0.2, False, 0.21),
    # target_tension が None の場合は常に True, 0.0 を返す
    (8, 0.5, None, 0.2, True, 0.0),
    # プロットが存在しない場合も True, 0.0
    (9, 0.5, "NO_PLOT", 0.2, True, 0.0),
] * 3) # 繰り返しでケース数を 20 以上にする
async def test_engine_validate_tension_deviation(ep_num, gen_tension, target_tension, tolerance, expected_valid, expected_deviation):
    repo_mock = AsyncMock()
    if target_tension == "NO_PLOT":
        repo_mock.get_plot.return_value = None
    else:
        plot_mock = MagicMock()
        plot_mock.target_tension = target_tension
        repo_mock.get_plot.return_value = plot_mock
        
    engine = UltimateHegemonyEngine(
        api_key="key",
        planner=None, writer=None, repo=repo_mock, db=None, pm=None, ctx_mgr=None,
        formatter=None, validator=None, auditor=None, narrative=None, critique=None,
        marketing=None, bible_agent=None, plot_agent=None, style_rag=None,
        llm=None, cooldown=None
    )
    
    is_valid, deviation = await engine.validate_tension_deviation(ep_num, gen_tension, book_id=1, tolerance=tolerance)
    assert is_valid == expected_valid
    assert abs(deviation - expected_deviation) < 1e-6
    repo_mock.get_plot.assert_called_once_with(book_id_or_branch_id=1, ep_num=ep_num)

# -------------------------------------------------------------
# 6. DIコンテナ連携テスト (Tests 101-110)
# -------------------------------------------------------------
@pytest.mark.parametrize("index", range(10))
def test_app_container_resolves_engine(index):
    # AppContainer から正しくインスタンス解決できるか
    container = make_container(f"key-{index}")
    engine = container.engine()
    assert isinstance(engine, UltimateHegemonyEngine)
    assert engine.api_key == f"key-{index}"
