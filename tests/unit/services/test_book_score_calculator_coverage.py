"""BookScoreCalculator coverage: 5-dimension scoring, trend analysis, PDCA report."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.book_score_models import BookScore
from src.services.book_score_service import BookScoreCalculator


def make_repo(session=None):
    repo = MagicMock()
    repo.session = session
    repo.save = AsyncMock()
    repo.get_latest = AsyncMock(return_value=None)
    repo.get_all_for_book = AsyncMock(return_value=[])
    return repo


def make_calc(repo=None):
    calc = BookScoreCalculator.__new__(BookScoreCalculator)
    calc.default_weights = {"structure": 25, "coherency": 25,
                            "factual_grounding": 20, "visual_textual_synergy": 15,
                            "reader_experience": 15}
    calc.genre_overrides = {}
    calc.phase_overrides = {}
    calc._repository = repo
    calc.bridge = None
    return calc


def make_session_with(rows_by_model=None):
    """select 結果をテーブル名ごとに返す簡易 session モック。

    rows_by_model: {"plots": rows, "audit_issues": [rows], ...} のように
    実テーブル名をキーに指定する。
    """
    session = MagicMock()
    rows_by_model = rows_by_model or {}

    def execute(stmt, *args, **kwargs):
        # stmt の from 句からテーブル名を抽出
        try:
            from_col = str(stmt.compile()).lower()
        except Exception:
            from_col = ""
        table_key = None
        for key in rows_by_model:
            if key in from_col:
                table_key = key
                break
        result = MagicMock()
        scalars = MagicMock()
        if table_key is None:
            rows = []
        else:
            rows = rows_by_model[table_key]
        if isinstance(rows, list):
            scalars.all.return_value = rows
            scalars.first.return_value = rows[0] if rows else None
        else:
            scalars.first.return_value = rows
            scalars.all.return_value = [rows]
        result.scalars.return_value = scalars
        return result

    session.execute = AsyncMock(side_effect=execute)
    return session


# ============================================================================
# Init & weights
# ============================================================================


def test_init_with_config_file():
    calc = BookScoreCalculator(config_path="config/book_score_weights.yaml")
    assert calc.default_weights
    assert isinstance(calc.genre_overrides, dict)


def test_init_with_missing_config_falls_back(tmp_path):
    calc = BookScoreCalculator(config_path=str(tmp_path / "nope.yaml"))
    assert calc.default_weights["structure"] == 25
    assert calc.genre_overrides == {}


def test_init_with_bridge_override():
    bridge = MagicMock()
    calc = BookScoreCalculator(bridge=bridge)
    assert calc.bridge is bridge


def test_get_weights_with_genre_and_phase():
    calc = make_calc()
    calc.genre_overrides = {"fantasy": {"structure": 30}}
    calc.phase_overrides = {"draft": {"coherency": 30}}
    weights = calc._get_weights("fantasy", "draft")
    assert weights["structure"] == 30
    assert weights["coherency"] == 30
    assert weights["reader_experience"] == 15
    # No overrides -> defaults
    assert calc._get_weights() == calc.default_weights


def test_get_weights_bad_config_values():
    calc = make_calc()
    calc.genre_overrides = {"unknown_genre": {"structure": 99}}
    assert calc._get_weights("unknown_genre")["structure"] == 99
    # Unknown genre key missing -> defaults
    assert calc._get_weights("nonexistent")["structure"] == 25


# ============================================================================
# Specialist mapping / contributions / maturity report
# ============================================================================


def test_calculate_from_specialists_with_bridge():
    calc = make_calc()
    bridge = MagicMock()
    u5d = MagicMock()
    u5d.overall_score = 82.0
    u5d.structure_score = 90.0
    u5d.coherency_score = 80.0
    u5d.factual_grounding_score = 75.0
    u5d.visual_textual_synergy_score = 85.0
    u5d.reader_experience_score = 78.0
    u5d.to_dict.return_value = {"structure": 90}
    bridge.map_to_5d.return_value = u5d
    calc.bridge = bridge

    score = calc.calculate_from_specialists({"logic": 90.0}, genre="fantasy", phase="draft")
    assert score.overall_score == 82.0
    assert score.specialist_breakdown == {"structure": 90}
    bridge.map_to_5d.assert_called_once_with({"logic": 90.0}, genre="fantasy", phase="draft")


def test_calculate_from_specialists_lazy_bridge_init():
    calc = make_calc()
    assert calc.bridge is None
    score = calc.calculate_from_specialists({"logic": 50.0})
    assert calc.bridge is not None


def test_get_score_contributions_and_matrices():
    calc = make_calc()
    bridge = MagicMock()
    u5d = MagicMock()
    u5d.contributions = {"structure": {"logic": 10.0}}
    bridge.map_to_5d.return_value = u5d
    bridge.get_matrix_for_genre.return_value = {
        "structure": {"logic": 0.5}, "coherency": {"speech": 0.4},
    }
    calc.bridge = bridge

    contribs = calc.get_score_contributions({"logic": 90.0})
    assert contribs == {"structure": {"logic": 10.0}}

    fwd = calc.get_dimension_to_specialists_mapping("fantasy")
    assert fwd["structure"] == {"logic": 0.5}

    rev = calc.get_specialist_to_dimensions_mapping("fantasy")
    assert rev == {"logic": {"structure": 0.5}, "speech": {"coherency": 0.4}}


@pytest.mark.parametrize("overall,rank,commercial,webhit", [
    (90.0, "S", True, True),
    (85.0, "S", True, True),
    (80.0, "A", False, True),
    (75.0, "A", False, True),
    (70.0, "B", False, False),
    (65.0, "B", False, False),
    (60.0, "C", False, False),
    (50.0, "C", False, False),
    (30.0, "D", False, False),
])
def test_generate_maturity_report_ranks(overall, rank, commercial, webhit):
    calc = make_calc()
    score = BookScore(overall_score=overall, structure_score=overall,
                      coherency_score=overall, factual_grounding_score=overall,
                      visual_textual_synergy_score=overall,
                      reader_experience_score=overall)
    report = calc.generate_maturity_report(score, genre="fantasy", phase="draft")
    assert report["rank"] == rank
    assert report["is_commercial_ready"] is commercial
    assert report["is_web_hit_ready"] is webhit
    assert report["lowest_dimension"]


# ============================================================================
# 5-dimension scoring with repository
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_full_flow_with_repository():
    session = make_session_with(rows_by_model={
        "audit_issue": [MagicMock(category="logical_consistency", severity="low"),
                        MagicMock(category="causal_integrity", severity="low")],
        "plot": MagicMock(end_ep=5, tension=60),
        "chapter": MagicMock(content="本文です。謎の瞬間。", tension=60),
        "illustration": MagicMock(prompt="1girl, focus, 主役"),
        "bible": MagicMock(settings='{"glossary": {"謎": "なぞ"}}'),
    })
    repo = make_repo(session)
    calc = make_calc(repo)

    score = await calc.calculate(book_id=1, chapter_number=5)
    assert 0 <= score.overall_score <= 100
    assert score.structure_score >= 75
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_calculate_without_repository_defaults_to_50():
    calc = make_calc(None)
    score = await calc.calculate(book_id=1, chapter_number=1)
    assert score.overall_score == 50.0
    assert score.structure_score == 50.0


@pytest.mark.asyncio
async def test_save_score_without_repository_warns():
    calc = make_calc(None)
    score = BookScore(overall_score=80.0, structure_score=80.0, coherency_score=80.0,
                      factual_grounding_score=80.0, visual_textual_synergy_score=80.0,
                      reader_experience_score=80.0)
    # Should not raise
    await calc.save_score(1, 1, score)


@pytest.mark.asyncio
async def test_get_latest_score():
    calc = make_calc(None)
    assert await calc.get_latest_score(1, 1) is None
    repo = make_repo()
    repo.get_latest = AsyncMock(return_value=MagicMock())
    calc._repository = repo
    assert await calc.get_latest_score(1, 1) is not None


@pytest.mark.asyncio
async def test_fetch_helpers_without_session():
    calc = make_calc(MagicMock(spec=["save", "get_latest"]))
    assert await calc._fetch_plot(1, 1) is None
    assert await calc._fetch_chapter(1, 1) is None
    assert await calc._fetch_illustration(1, 1) is None
    assert await calc._fetch_bible(1) is None
    assert await calc._fetch_audit_report(1, 1) is None


@pytest.mark.asyncio
async def test_fetch_helpers_with_session_and_errors():
    session = make_session_with(rows_by_model={"plots": MagicMock(end_ep=1)})
    calc = make_calc(make_repo(session))
    plot = await calc._fetch_plot(1, 1)
    assert plot is not None

    # Errors -> None
    session2 = MagicMock()
    session2.execute = AsyncMock(side_effect=RuntimeError("db"))
    calc2 = make_calc(make_repo(session2))
    assert await calc2._fetch_plot(1, 1) is None
    assert await calc2._fetch_chapter(1, 1) is None
    assert await calc2._fetch_illustration(1, 1) is None
    assert await calc2._fetch_bible(1) is None
    assert await calc2._fetch_audit_report(1, 1) is None


@pytest.mark.asyncio
async def test_score_structure_audit_variations():
    # Both logical & causal passed -> high score
    session = make_session_with(rows_by_model={
        "audit_issues": [MagicMock(category="logical_consistency", severity="low"),
                         MagicMock(category="causal_integrity", severity="low")],
        "plots": MagicMock(end_ep=5),
        "chapters": MagicMock(tension=60),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_structure(1, 5, None)
    assert score >= 90

    # Only one passed -> mid
    session2 = make_session_with(rows_by_model={
        "audit_issues": [MagicMock(category="logical_consistency", severity="low")],
        "plots": MagicMock(end_ep=10),
        "chapters": MagicMock(tension=10),
    })
    calc2 = make_calc(make_repo(session2))
    score2 = await calc2._score_structure(1, 5, None)
    assert 50 <= score2 <= 85

    # Neither passed -> low
    session3 = make_session_with(rows_by_model={
        "audit_issues": [MagicMock(category="other", severity="high")],
        "plots": MagicMock(end_ep=100),
        "chapters": MagicMock(tension=5),
    })
    calc3 = make_calc(make_repo(session3))
    score3 = await calc3._score_structure(1, 1, None)
    assert score3 < 60


@pytest.mark.asyncio
async def test_score_coherency_with_speech_and_naming():
    # No audit issues at all -> default 70 + naming bonus
    session = make_session_with(rows_by_model={
        "audit_issues": [],
        "chapters": MagicMock(content="一貫した本文です。表記も統一されている。"),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_coherency(1, 1, None)
    assert score >= 70  # naming consistency may add up to ~75

    # Multiple speech issues -> low
    session2 = make_session_with(rows_by_model={
        "audit_issues": [MagicMock(category="speech", description=""),
                         MagicMock(category="dialogue", description=""),
                         MagicMock(category="ability", description="")],
        "chapters": MagicMock(content=None),
    })
    calc2 = make_calc(make_repo(session2))
    score2 = await calc2._score_coherency(1, 1, None)
    assert score2 < 75


@pytest.mark.asyncio
async def test_score_factual_with_bible_keywords():
    # Bible keywords found in text -> high coverage
    session = make_session_with(rows_by_model={
        "chapters": MagicMock(content="魔法都市の冒険"),
        "bibles": MagicMock(settings='{"period": "futuristic", "glossary": {"魔法": "まほう"}}'),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_factual(1, 1, None)
    assert score >= 60


@pytest.mark.asyncio
async def test_score_factual_anachronism_detection():
    # medieval period with modern items -> low history score
    session = make_session_with(rows_by_model={
        "chapters": MagicMock(content="電話で話す。コンピュータを使う。"),
        "bibles": MagicMock(settings='{"period": "medieval"}'),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_factual(1, 1, None)
    assert score < 80


def test_get_anachronisms_by_period():
    calc = make_calc()
    assert "電話" in calc._get_anachronisms("medieval")
    assert "馬車" in calc._get_anachronisms("modern")
    assert calc._get_anachronisms("futuristic") == []
    assert calc._get_anachronisms("unknown") == []
    assert calc._get_anachronisms("MEDIEVAL") == calc._get_anachronisms("medieval")


@pytest.mark.asyncio
async def test_score_visual_textual_no_data():
    calc = make_calc(make_repo(make_session_with(rows_by_model={})))
    assert await calc._score_visual_textual(1, 1, None) == 50.0

    # No prompt
    session = make_session_with(rows_by_model={
        "illustrations": MagicMock(prompt=""),
        "chapters": MagicMock(content="本文"),
    })
    calc2 = make_calc(make_repo(session))
    assert await calc2._score_visual_textual(1, 1, None) == 50.0


@pytest.mark.asyncio
async def test_score_visual_textual_full_match():
    session = make_session_with(rows_by_model={
        "illustrations": MagicMock(prompt="魔法都市 focus 主役 bright"),
        "chapters": MagicMock(content="魔法都市の冒険！！「キャラ」… 喜びに満ちる"),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_visual_textual(1, 1, None)
    assert score >= 70


@pytest.mark.asyncio
async def test_score_reader_experience_no_chapter():
    calc = make_calc(make_repo(make_session_with(rows_by_model={})))
    assert await calc._score_reader_experience(1, 1, None) == 50.0


@pytest.mark.asyncio
async def test_score_reader_experience_hook_and_cliffhanger():
    # Dense hooks in prefix, cliffhanger in suffix
    text = "なぜ？謎！違和感…危機！突然のまさか？誰が？" + "本文" * 40 + "続く…次話へ未解決の謎！衝撃！！"
    session = make_session_with(rows_by_model={
        "chapters": MagicMock(content=text, tension=60),
    })
    calc = make_calc(make_repo(session))
    score = await calc._score_reader_experience(1, 1, None)
    assert score >= 80

    # Flat text without hooks -> low
    text2 = "普通" * 60
    session2 = make_session_with(rows_by_model={"chapters": MagicMock(content=text2)})
    calc2 = make_calc(make_repo(session2))
    score2 = await calc2._score_reader_experience(1, 1, None)
    assert score2 < 60


@pytest.mark.asyncio
async def test_score_reader_experience_emotion_from_tension():
    text = "普通" * 30
    session = make_session_with(rows_by_model={"chapters": MagicMock(content=text, tension=60)})
    calc = make_calc(make_repo(session))
    score = await calc._score_reader_experience(1, 1, None)
    assert score > 40

    # No tension -> text-based emotion estimation
    session2 = make_session_with(rows_by_model={"chapters": MagicMock(content=text + "。ちょっと短い。長いのはこういう風に少し長くなっていきますね。")})
    calc2 = make_calc(make_repo(session2))
    score2 = await calc2._score_reader_experience(1, 1, None)
    assert 0 <= score2 <= 100


# ============================================================================
# Trend analysis & PDCA
# ============================================================================


def make_score_row(overall, structure=None, coherency=None, factual=None,
                   visual=None, reader=None):
    row = MagicMock()
    row.overall_score = overall
    row.structure_score = structure if structure is not None else overall
    row.coherency_score = coherency if coherency is not None else overall
    row.factual_grounding_score = factual if factual is not None else overall
    row.visual_textual_synergy_score = visual if visual is not None else overall
    row.reader_experience_score = reader if reader is not None else overall
    return row


@pytest.mark.asyncio
async def test_analyze_trend_no_repository():
    calc = make_calc(None)
    result = await calc.analyze_trend(1)
    assert result == {"error": "Repository not configured"}


@pytest.mark.asyncio
async def test_analyze_trend_insufficient_data():
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=[make_score_row(80.0), make_score_row(85.0)])
    calc = make_calc(repo)
    result = await calc.analyze_trend(1)
    assert "error" in result
    assert result["chapters_evaluated"] == 2


@pytest.mark.asyncio
async def test_analyze_trend_improving_with_changepoints():
    scores = [make_score_row(v) for v in [50.0, 55.0, 65.0, 70.0, 82.0]]
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=scores)
    calc = make_calc(repo)
    result = await calc.analyze_trend(1, window=5)
    assert result["trend_direction"] == "improving"
    assert result["slope"] > 0
    assert len(result["changepoints"]) >= 1
    assert result["next_chapter_prediction"] > 80
    assert len(result["moving_avg_3"]) == 3
    assert 0 <= result["r_squared"] <= 1


@pytest.mark.asyncio
async def test_analyze_trend_declining():
    scores = [make_score_row(v) for v in [90.0, 85.0, 80.0, 70.0, 60.0]]
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=scores)
    calc = make_calc(repo)
    result = await calc.analyze_trend(1)
    assert result["trend_direction"] == "declining"


@pytest.mark.asyncio
async def test_analyze_trend_stable():
    scores = [make_score_row(v) for v in [80.0, 81.0, 80.5, 80.2, 80.8]]
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=scores)
    calc = make_calc(repo)
    result = await calc.analyze_trend(1)
    assert result["trend_direction"] == "stable"


@pytest.mark.asyncio
async def test_generate_pdca_report_error():
    calc = make_calc(None)
    result = await calc.generate_pdca_report(1)
    assert "error" in result


@pytest.mark.asyncio
async def test_generate_pdca_report_full():
    # declining trend + low dimensions -> both actions present
    scores = [make_score_row(72.0, structure=55, coherency=65, factual=50,
                             visual=75, reader=68),
              make_score_row(65.0, structure=58, coherency=66, factual=52,
                             visual=76, reader=70),
              make_score_row(60.0, structure=60, coherency=67, factual=54,
                             visual=77, reader=72)]
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=scores)
    calc = make_calc(repo)
    result = await calc.generate_pdca_report(1)
    assert "error" not in result
    assert result["plan"]["target_score"] == 80.0
    assert result["plan"]["gap"] > 0
    assert result["plan"]["priority_dimensions"]
    assert result["do"]["recent_scores"]
    assert result["check"]["target_achieved"] is False
    assert result["act"]["recommended_actions"]
    actions = [a["action"] for a in result["act"]["recommended_actions"]]
    assert any("improve_" in a for a in actions)
    assert any("investigate_decline" in a for a in actions)
    # score drop of 10+ generates changepoints
    trend = await calc.analyze_trend(1)
    assert trend["trend_direction"] == "declining"


@pytest.mark.asyncio
async def test_generate_pdca_report_target_achieved_no_decline():
    scores = [make_score_row(85.0, structure=90, coherency=88, factual=85,
                             visual=86, reader=87),
              make_score_row(86.0, structure=90, coherency=88, factual=85,
                             visual=86, reader=87),
              make_score_row(87.0, structure=90, coherency=88, factual=85,
                             visual=86, reader=87)]
    repo = make_repo()
    repo.get_all_for_book = AsyncMock(return_value=scores)
    calc = make_calc(repo)
    result = await calc.generate_pdca_report(1)
    assert result["check"]["target_achieved"] is True
    actions = [a["action"] for a in result["act"]["recommended_actions"]]
    assert "investigate_decline" not in actions
    assert "review_changepoints" not in actions
    assert not any("improve_" in a for a in actions)
