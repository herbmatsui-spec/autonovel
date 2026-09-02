from src.easy_mode.phase3.if_routes import (
    BranchCondition,
    ConditionOperator,
    IFRouteGenerator,
    RouteChoice,
    create_if_route_system,
)
from src.easy_mode.pipeline import EpisodeResult, SeriesResult
from src.easy_mode.spice_guard import SpiceElement


def test_branch_condition_equals():
    """等価条件の評価検証。"""
    cond = BranchCondition(
        variable="route",
        operator=ConditionOperator.EQUALS,
        value="heroine_a",
    )
    assert cond.evaluate({"route": "heroine_a"}) is True
    assert cond.evaluate({"route": "heroine_b"}) is False


def test_branch_condition_numeric_comparison():
    """数値比較条件の評価検証。"""
    cond_gt = BranchCondition(
        variable="player.affection",
        operator=ConditionOperator.GREATER_THAN,
        value=50,
    )
    assert cond_gt.evaluate({"player": {"affection": 60}}) is True
    assert cond_gt.evaluate({"player": {"affection": 40}}) is False
    assert cond_gt.evaluate({"player": {"affection": 50}}) is False


def test_branch_condition_contains():
    """含有・非含有条件の評価検証。"""
    cond_contains = BranchCondition(
        variable="inventory",
        operator=ConditionOperator.CONTAINS,
        value="legendary_sword",
    )
    assert cond_contains.evaluate({"inventory": ["potion", "legendary_sword"]}) is True
    assert cond_contains.evaluate({"inventory": ["potion"]}) is False


def test_route_choice_apply_effects_nested():
    """`apply_effects` がネストした dict キーに副作用を反映できることを確認。"""
    choice = RouteChoice(
        id="c1", text="選択", effects={"player.affection": 10, "flags.hero": True}
    )
    new_ctx = choice.apply_effects({"player": {"affection": 5}, "flags": {}})
    assert new_ctx["player"]["affection"] == 10
    assert new_ctx["flags"]["hero"] is True


def _make_series(eps: int = 1) -> SeriesResult:
    return SeriesResult(
        genre="ハイファンタジー (R15)",
        title="テスト",
        concept="テスト",
        total_episodes=eps,
        episodes=[
            EpisodeResult(
                episode_num=i + 1,
                title=f"第{i + 1}話",
                content="本文",
                word_count=10,
                audit_score=80.0,
                audit_passed=True,
                rewrite_count=0,
                spice_elements=[SpiceElement(type="unique_metaphor", text="", position=0, priority="low")],
                metadata={},
            )
            for i in range(eps)
        ],
        bible={},
        plot_outline=[],
        metadata={"prologue": "始"},
    )


def test_if_route_generator_minimum_nodes():
    """1 話のシリーズから最低 1 ノードが生成される。"""
    gen = IFRouteGenerator(
        "ハイファンタジー (R15)", {"characters": {"archetypes": {}}, "erotic": {}}
    )
    series = _make_series(eps=1)
    graph = gen.generate_from_series(series)
    assert len(graph.nodes) >= 1
    assert graph.entry_node_id


def test_if_route_graph_validate():
    graph = create_if_route_system(
        "ハイファンタジー (R15)",
        _make_series(eps=2),
        {"characters": {"archetypes": {}}, "erotic": {}},
    )
    errors = graph.validate()
    assert isinstance(errors, list)

