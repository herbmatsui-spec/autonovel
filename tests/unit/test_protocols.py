"""protocols.py のユニットテスト。

- 全 Protocol がインポート可能であること
- __all__ に全て含まれていること
- 実際のサービス実装 (WorldBibleGenerator, WritingAgent 等) が
  Protocol の構造的サブタイプになっていること（メソッド存在確認）
"""
from src.backend import protocols


def test_all_protocols_importable():
    for name in protocols.__all__:
        assert hasattr(protocols, name), f"missing {name}"
        cls = getattr(protocols, name)
        assert isinstance(cls, object)


def test_planning_port_methods():
    assert hasattr(protocols.PlanningPort, "create_hegemony_plan")
    assert hasattr(protocols.PlanningPort, "expand_plots")
    assert hasattr(protocols.PlanningPort, "rebuild_hegemony_plot")
    assert hasattr(protocols.PlanningPort, "audit_bible_completeness")


def test_writing_port_methods():
    assert hasattr(protocols.WritingPort, "generate_episodes_pipeline")
    assert hasattr(protocols.WritingPort, "generate_episodes")
    assert hasattr(protocols.WritingPort, "analyze_and_import_chapter")


def test_critique_port_methods():
    assert hasattr(protocols.CritiquePort, "run_iterative_gap_analysis")
    assert hasattr(protocols.CritiquePort, "audit_plot_as_issues")


def test_bible_port_methods():
    assert hasattr(protocols.BiblePort, "sync_bible_lifecycle")
    assert hasattr(protocols.BiblePort, "resolve_pending_setting")
    assert hasattr(protocols.BiblePort, "get_latest_bible")


def test_tension_port_methods():
    assert hasattr(protocols.TensionPort, "determine_target_tension")
    assert hasattr(protocols.TensionPort, "validate_tension_deviation")


def test_repo_port_methods():
    assert hasattr(protocols.DataRepositoryPort, "get_book")
    assert hasattr(protocols.DataRepositoryPort, "get_total_episodes")
    assert hasattr(protocols.DataRepositoryPort, "get_latest_bible")


def test_real_implementations_satisfy_protocols():
    """実サービス実装が Protocol の必須メソッドを備えているか（構造的確認）。"""
    from src.services.bible_service import WorldBibleGenerator
    from src.agents.writing import WritingAgent

    # WorldBibleGenerator は create_hegemony_plan を実装 (PlanningPort の核心)
    assert hasattr(WorldBibleGenerator, "create_hegemony_plan")
    # WritingAgent は generate_episodes_pipeline を実装 (WritingPort の核心)
    assert hasattr(WritingAgent, "generate_episodes_pipeline")
    assert hasattr(WritingAgent, "generate_episodes")
