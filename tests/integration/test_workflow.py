import pytest

from src.backend.background import ProgressState, StatusReporter
from src.backend.engine import UltimateHegemonyEngine
from src.backend.workflows.full_auto_workflow import FullAutoWorkflow
from src.core.container import AppContainer, make_container
from tests.mocks.mock_llm import LLMGenerateResultMockProxy


class DummyReporter(StatusReporter):
    def __init__(self):
        super().__init__()
        self.state = ProgressState(is_running=True)
        self.messages = []

    def report(self, message: str, status: str = "info"):
        self.messages.append((status, message))
        print(f"[{status}] {message}")

    def update_progress(self, current: int, total: int, step_name: str = "", *args, **kwargs):
        self.state.update(step_name, step=current, total=total)
        print(f"[Progress] {current}/{total} - {step_name}")

    def update_streaming_text(self, text: str):
        pass

@pytest.mark.asyncio
async def test_full_auto_workflow_easy_mode(real_db_manager, mock_llm):
    # Setup mock LLM responses for planning
    mock_llm.add_json_response("gemini-3.1-flash-lite", {
        "bible_core": {
            "title": "テスト用の異世界",
            "concept": "剣と魔法が支配する世界",
            "genre": "ファンタジー",
            "style_key": "style_serious_fantasy",
            "keywords": "剣, 魔法",
            "engine_key": "novel",
            "world_settings": {"tension_threshold": 50, "tension_gain": 30},
            "mc_profile": {"name": "主人公", "surface_persona": "一見平凡な冒険者", "inner_conflict": "野望", "iron_constraint": "ルール遵守"},
            "arcs": [{"title": "追放", "summary": "主人公が追放される"}]
        },
        "full_story_roadmap": [{
            "ep_num": 1,
            "one_line_summary": "ギルドから理不尽に追放されるアレン",
            "resolution_style": "Cheat",
            "antagonist_status": "現状維持",
            "title": "理不尽な追放",
            "synopsis": "アレンはギルドから追放される"
        }]
    })

    mock_llm.add_json_response("gemma-4-31b-it", {
        "plots": [
            {
                "ep_num": 1,
                "thought_process": "展開思考",
                "title": "プロット第1話",
                "one_line_summary": "ギルドから理不尽に追放されるアレン。",
                "detailed_blueprint": "詳細設計図...",
                "tension": 60,
                "tension_delta": 10,
                "catharsis": 0,
                "is_catharsis": False,
                "love_meter": 0,
                "catharsis_type": "なし",
                "next_hook": {"type": "New Crisis", "description": "次の危機"},
                "misunderstanding_gap": "なし",
                "current_chain_phase": "Friction",
                "emotional_payoff": "なし",
                "resolution_style": "Cheat",
                "burned_cost_or_loot": "なし",
                "thematic_milestone": "なし",
                "antagonist_status": "現状維持",
                "scenes": [
                    {
                        "scene_number": 1,
                        "action": "アレンがギルドを去るシーン。",
                        "dialogue_point": "ギルドマスターとアレンの会話。",
                        "dramatic_function": "導入",
                        "emotional_payoff": "なし",
                        "beats": [
                            {"beat_type": "導入", "action_description": "ギルドのドアが閉まる。", "sensory_keywords": [], "psychology_keywords": []}
                        ],
                        "bridge_instruction": "",
                        "impact_score": 70,
                        "psychological_layer": "アレンは悲しんでいる。"
                    }
                ]
            }
        ]
    })

    mock_llm.add_json_response("文脈の整理", {
        "alignment_summary": "Test Summary",
        "active_subplots": [],
        "locked_foreshadowings": []
    })

    # Detailed plot expansion mock response
    mock_llm.add_json_response("plot_expansion_prompt", {
        "plots": [
            {
                "ep_num": 1,
                "thought_process": "展開思考",
                "title": "プロット第1話",
                "one_line_summary": "ギルドから理不尽に追放されるアレン。",
                "detailed_blueprint": "詳細設計図...",
                "tension": 60,
                "tension_delta": 10,
                "catharsis": 0,
                "is_catharsis": False,
                "love_meter": 0,
                "catharsis_type": "なし",
                "next_hook": {"type": "New Crisis", "description": "次の危機"},
                "misunderstanding_gap": "なし",
                "current_chain_phase": "Friction",
                "emotional_payoff": "なし",
                "resolution_style": "Cheat",
                "burned_cost_or_loot": "なし",
                "thematic_milestone": "なし",
                "antagonist_status": "現状維持",
                "scenes": [
                    {
                        "scene_number": 1,
                        "action": "アレンがギルドを去るシーン。",
                        "dialogue_point": "ギルドマスターとアレンの会話。",
                        "dramatic_function": "導入",
                        "emotional_payoff": "なし",
                        "beats": [
                            {"beat_type": "導入", "action_description": "ギルドのドアが閉まる。", "sensory_keywords": [], "psychology_keywords": []}
                        ],
                        "bridge_instruction": "",
                        "impact_score": 70,
                        "psychological_layer": "アレンは悲しんでいる。"
                    }
                ]
            }
        ]
    })

    # Writing/Drafting and Polishing mock responses
    mock_llm.add_text_response("drafting_user", "アレンは静かに剣を置いた。ギルドマスターの声が響く。「お前はクビだ」。アレンはただ黙って部屋を後にした。新たな伝説の始まりだった。")
    mock_llm.add_text_response("polishing", "アレンは静かに剣を置いた。ギルドマスターの冷酷な声が響く。「お前はクビだ」。アレンはただ黙って部屋を後にした。新たな伝説の始まりだった。")
    mock_llm.add_text_response("amplify", "アレンは静かに剣を置いた。ギルドマスターの冷酷な声が響く。「お前はクビだ」。アレンはただ黙って部屋を後にした。新たな伝説の始まりだった。")

    AppContainer.llm.override(LLMGenerateResultMockProxy(mock_llm))
    AppContainer.repo.reset_override()
    AppContainer.uow.reset_override()

    container = make_container("test-api-key", db=real_db_manager)
    db_from_container = container.db
    engine = container.engine()
    if hasattr(real_db_manager, "db"):
        mgr = real_db_manager.db
        if hasattr(mgr, "engine"):
            import sqlite3
            conn = sqlite3.connect(mgr.engine.url.database)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(books)")
            cols = [row[1] for row in cursor.fetchall()]
            conn.close()

    workflow = FullAutoWorkflow(engine=engine)
    reporter = DummyReporter()

    try:
        # Run the workflow in easy mode
        result = await workflow.execute(
            reporter=reporter,
            genre="ファンタジー",
            keywords="追放, チート",
            archetype_key="王道ざまぁ（爽快感最大）",
            target_eps=1,
            initial_limit=1,
            word_count=500,
            concept="追放された最強の剣士"
        )

        assert result is not None
        assert result["book_id"] is not None
        assert len(result.get("failed_episodes", [])) == 0
        assert result["chars_count"] > 0
    finally:
        AppContainer.llm.reset_override()


@pytest.mark.asyncio
async def test_full_auto_workflow_normal_mode(real_db_manager, mock_llm):
    # Setup mock LLM responses for planning and normal mode validations
    mock_llm.add_json_response("gemini-3.1-flash-lite", {
        "bible_core": {
            "title": "テスト用の異世界",
            "concept": "剣と魔法が支配する世界",
            "genre": "ファンタジー",
            "style_key": "style_serious_fantasy",
            "keywords": "剣, 魔法",
            "engine_key": "novel",
            "world_settings": {"tension_threshold": 50, "tension_gain": 30},
            "mc_profile": {"name": "主人公", "surface_persona": "一見平凡な冒険者", "inner_conflict": "野望", "iron_constraint": "ルール遵守"},
            "arcs": [{"title": "追放", "summary": "主人公が追放される"}]
        },
        "full_story_roadmap": [{
            "ep_num": 1,
            "one_line_summary": "ギルドから理不尽に追放されるアレン",
            "resolution_style": "Cheat",
            "antagonist_status": "現状維持",
            "title": "理不尽な追放",
            "synopsis": "アレンはギルドから追放される"
        }]
    })

    mock_llm.add_json_response("gemma-4-31b-it", {
        "plots": [
            {
                "ep_num": 1,
                "thought_process": "通常モード展開思考",
                "title": "プロット第1話",
                "one_line_summary": "ギルドから理不尽に追放されるアレン。",
                "detailed_blueprint": "詳細設計図...",
                "tension": 60,
                "tension_delta": 10,
                "catharsis": 0,
                "is_catharsis": False,
                "love_meter": 0,
                "catharsis_type": "なし",
                "next_hook": {"type": "New Crisis", "description": "次の危機"},
                "misunderstanding_gap": "なし",
                "current_chain_phase": "Friction",
                "emotional_payoff": "なし",
                "resolution_style": "Cheat",
                "burned_cost_or_loot": "なし",
                "thematic_milestone": "なし",
                "antagonist_status": "現状維持",
                "scenes": [
                    {
                        "scene_number": 1,
                        "action": "アレンがギルドを去るシーン。",
                        "dialogue_point": "会話。",
                        "dramatic_function": "導入",
                        "emotional_payoff": "なし",
                        "beats": [
                            {"beat_type": "導入", "action_description": "ドアが閉まる。", "sensory_keywords": [], "psychology_keywords": []}
                        ],
                        "bridge_instruction": "",
                        "impact_score": 70,
                        "psychological_layer": "悲しみ。"
                    }
                ]
            }
        ]
    })

    mock_llm.add_json_response("文脈の整理", {
        "alignment_summary": "Test Summary",
        "active_subplots": [],
        "locked_foreshadowings": []
    })

    mock_llm.add_json_response("plot_expansion_prompt", {
        "plots": [
            {
                "ep_num": 1,
                "thought_process": "通常モード展開思考",
                "title": "プロット第1話",
                "one_line_summary": "ギルドから理不尽に追放されるアレン。",
                "detailed_blueprint": "詳細設計図...",
                "tension": 60,
                "tension_delta": 10,
                "catharsis": 0,
                "is_catharsis": False,
                "love_meter": 0,
                "catharsis_type": "なし",
                "next_hook": {"type": "New Crisis", "description": "次の危機"},
                "misunderstanding_gap": "なし",
                "current_chain_phase": "Friction",
                "emotional_payoff": "なし",
                "resolution_style": "Cheat",
                "burned_cost_or_loot": "なし",
                "thematic_milestone": "なし",
                "antagonist_status": "現状維持",
                "scenes": [
                    {
                        "scene_number": 1,
                        "action": "アレンがギルドを去るシーン。",
                        "dialogue_point": "会話。",
                        "dramatic_function": "導入",
                        "emotional_payoff": "なし",
                        "beats": [
                            {"beat_type": "導入", "action_description": "ドアが閉まる。", "sensory_keywords": [], "psychology_keywords": []}
                        ],
                        "bridge_instruction": "",
                        "impact_score": 70,
                        "psychological_layer": "悲しみ。"
                    }
                ]
            }
        ]
    })

    # Normal mode specific mock responses
    mock_llm.add_json_response("小説本文とシーン設計図", {
        "is_consistent": True,
        "conflict_report": "不整合なし",
        "failures": []
    })

    mock_llm.add_json_response("原稿を評価してください", {
        "score": 90,
        "reason": "テスト用自己評価：合格",
        "recommended_patch": ""
    })

    AppContainer.llm.override(LLMGenerateResultMockProxy(mock_llm))
    AppContainer.repo.reset_override()
    AppContainer.uow.reset_override()

    container = make_container("test-api-key", db=real_db_manager)
    db_from_container = container.db
    engine = container.engine()
    if hasattr(real_db_manager, "db"):
        mgr = real_db_manager.db
        if hasattr(mgr, "engine"):
            import sqlite3
            conn = sqlite3.connect(mgr.engine.url.database)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(books)")
            cols = [row[1] for row in cursor.fetchall()]
            conn.close()

    workflow = FullAutoWorkflow(engine=engine)
    reporter = DummyReporter()

    try:
        result = await workflow.execute(
            reporter=reporter,
            genre="ファンタジー",
            keywords="追放, チート",
            archetype_key="王道ざまぁ（爽快感最大）",
            target_eps=1,
            initial_limit=1,
            word_count=500,
            concept="通常モード検証"
        )

        assert result is not None
        assert result["book_id"] is not None
        assert len(result.get("failed_episodes", [])) == 0
        assert result["chars_count"] > 0
    finally:
        AppContainer.llm.reset_override()

@pytest.mark.asyncio
async def test_full_auto_workflow_api_failure(real_db_manager, mock_llm):
    """APIエラー時の挙動を確認するテスト"""
    # 企画生成でわざとエラーを出す
    mock_llm.add_exception("gemini-3.1-flash-lite", Exception("API Connection Error"))

    AppContainer.llm.override(LLMGenerateResultMockProxy(mock_llm))
    AppContainer.repo.reset_override()
    AppContainer.uow.reset_override()

    container = make_container("test-api-key", db=real_db_manager)
    db_from_container = container.db
    engine = container.engine()
    if hasattr(real_db_manager, "db"):
        mgr = real_db_manager.db
        if hasattr(mgr, "engine"):
            import sqlite3
            conn = sqlite3.connect(mgr.engine.url.database)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(books)")
            cols = [row[1] for row in cursor.fetchall()]
            conn.close()
    workflow = FullAutoWorkflow(engine=engine)
    reporter = DummyReporter()

    try:
        with pytest.raises(Exception) as excinfo:
            await workflow.execute(
                reporter=reporter,
                genre="ファンタジー",
                keywords="追放",
                archetype_key="王道ざまぁ（爽快感最大）",
                target_eps=1,
                initial_limit=1,
                word_count=500
            )
        assert "API Connection Error" in str(excinfo.value)
        assert any(status == "error" for status, msg in reporter.messages)
    finally:
        AppContainer.llm.reset_override()
