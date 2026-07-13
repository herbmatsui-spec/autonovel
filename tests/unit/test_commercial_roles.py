"""
Commercial Roles Test Suite
商用化作品自動生成システムのテストスイート

フェーズ5（ステップ43-48）：テスト・統合
"""


from config.archetypes import (
    COMMERCIAL_ROLE_DESCRIPTIONS,
    PLEASURE_TRIGGER_KEYWORDS,
    ROLE_REQUIRED_ATTRIBUTES,
    CharacterCommercialMeta,
    CommercialRole,
    assign_commercial_role,
    calculate_recognition_value,
    get_gap_attribute_pair,
    get_role_pleasure_keywords,
    get_status_flip_timing_config,
    validate_character_commercial_value,
)
from config.domain_profile_manager import (
    ABTestConfig,
    CommercialDataLoader,
    load_commercial_settings,
)
from kernels.graph import (
    PleasureGraph,
    PleasureType,
    build_default_pleasure_graph,
)
from prompts.commercial_prompts import (
    ab_test_prompt_registry,
    commercial_role_prompt_registry,
    generate_full_commercial_prompt_pack,
    marketing_prompt_registry,
    pleasure_prompt_registry,
    series_prompt_registry,
    style_prompt_registry,
)

# =============================================================================
# ステップ43: 商業的役割データ構造テスト
# =============================================================================

class TestCommercialRoleEnums:
    """CommercialRole 列挙体のテスト"""

    def test_commercial_role_count(self):
        """9つの商業的役割が定義されている"""
        roles = list(CommercialRole)
        assert len(roles) == 9

    def test_commercial_role_values(self):
        """全ての商業的役割が正しい値を持つ"""
        expected_roles = [
            "avatar_of_desire",
            "hate_magnet",
            "unconditional_supporter",
            "contrast_engine",
            "unique_value",
            "growth_investment",
            "destined_resonance",
            "information_hegemony",
            "status_flip_trigger",
        ]
        actual_roles = [r.value for r in CommercialRole]
        for expected in expected_roles:
            assert expected in actual_roles

    def test_role_descriptions_complete(self):
        """全ての役割に説明が存在する"""
        for role in CommercialRole:
            assert role.value in COMMERCIAL_ROLE_DESCRIPTIONS
            assert len(COMMERCIAL_ROLE_DESCRIPTIONS[role.value]) > 0

    def test_role_required_attributes_complete(self):
        """全ての役割に必要な属性が定義されている"""
        for role in CommercialRole:
            assert role.value in ROLE_REQUIRED_ATTRIBUTES
            assert len(ROLE_REQUIRED_ATTRIBUTES[role.value]) > 0

    def test_pleasure_trigger_keywords_complete(self):
        """全ての役割に快楽トリガーキーワードが定義されている"""
        for role in CommercialRole:
            assert role.value in PLEASURE_TRIGGER_KEYWORDS
            assert len(PLEASURE_TRIGGER_KEYWORDS[role.value]) > 0


class TestCharacterCommercialMeta:
    """CharacterCommercialMeta データクラスのテスト"""

    def test_meta_creation(self):
        """CharacterCommercialMeta が正しく作成できる"""
        meta = CharacterCommercialMeta(
            primary_role=CommercialRole.AVATAR_OF_DESIRE,
            secondary_roles=[CommercialRole.CONTRAST_ENGINE],
            recognition_value=1.5,
            pleasure_keywords=["理想自己", "願望充足"],
            trigger_positions=[0.25, 0.5, 0.85],
        )
        assert meta.primary_role == CommercialRole.AVATAR_OF_DESIRE
        assert len(meta.secondary_roles) == 1
        assert meta.recognition_value == 1.5

    def test_meta_to_dict(self):
        """to_dict() メソッドが正しく動作する"""
        meta = CharacterCommercialMeta(
            primary_role=CommercialRole.HATE_MAGNET,
            secondary_roles=[],
            recognition_value=1.2,
            pleasure_keywords=["憎悪蓄積", "天罰"],
            trigger_positions=[0.3, 0.7],
        )
        result = meta.to_dict()
        assert result["primary_role"] == "hate_magnet"
        assert result["recognition_value"] == 1.2


# =============================================================================
# ステップ44: カーネル統合テスト
# =============================================================================

class TestPleasureGraph:
    """PleasureGraph カーネルのテスト"""

    def test_pleasure_graph_creation(self):
        """PleasureGraph が正しく作成できる"""
        graph = PleasureGraph()
        assert graph.nodes == {}
        assert graph.edges == []
        assert graph.neg_edges == []

    def test_add_pleasure_node(self):
        """快感ノードを追加できる"""
        graph = PleasureGraph()
        node_id = graph.add_pleasure_node(
            pleasure_type=PleasureType.CATHARSIS,
            intensity=0.9,
            description="テストカタルシス",
            story_position=0.8,
        )
        assert node_id in graph.nodes
        assert graph.nodes[node_id].intensity == 0.9

    def test_add_causal_link(self):
        """因果リンクを追加できる"""
        graph = PleasureGraph()
        node_a = graph.add_pleasure_node(PleasureType.TENSION, 0.5, "A", story_position=0.3)
        node_b = graph.add_pleasure_node(PleasureType.CATHARSIS, 0.8, "B", story_position=0.7)
        graph.add_causal_link(node_a, node_b, strength=0.3)

        assert len(graph.edges) == 1
        assert graph.edges[0].source_node == node_a
        assert graph.edges[0].target_node == node_b

    def test_calculate_pleasure_at_position(self):
        """位置に応じた快感値を計算できる"""
        graph = build_default_pleasure_graph()
        value = graph.calculate_pleasure_at_position(0.5)
        assert 0.0 <= value <= 100.0

    def test_build_default_pleasure_graph(self):
        """デフォルト、快楽グラフが正しく構築される"""
        graph = build_default_pleasure_graph()

        node_types = [n.pleasure_type for n in graph.nodes.values()]
        assert PleasureType.CATHARSIS in node_types
        assert PleasureType.TENSION in node_types

        assert len(graph.edges) > 0


class TestHateAmplificationLoop:
    """Hate Amplification Loop のテスト"""

    def test_hate_magnet_state_creation(self):
        """HateMagnetState が正しく作成できる"""
        from kernels.conflict import HateMagnetState

        state = HateMagnetState(character_name="テスト悪役")
        assert state.character_name == "テスト悪役"
        assert state.hate_accumulated == 0.0
        assert len(state.transgressions) == 0

    def test_add_transgression(self):
        """違反を追加できる"""
        from kernels.conflict import HateMagnetState

        state = HateMagnetState(character_name="テスト悪役")
        state.add_transgression("arrogant_abuse", "テスト-context")

        assert state.hate_accumulated > 0.0
        assert len(state.transgressions) == 1

    def test_should_trigger_catharsis(self):
        """カタルシストリガー判定ができる"""
        from kernels.conflict import HateMagnetState

        state = HateMagnetState(character_name="テスト悪役")
        # 十分に蓄積されていない場合
        should_trigger, intensity = state.should_trigger_catharsis()
        assert isinstance(should_trigger, bool)
        assert isinstance(intensity, float)


# =============================================================================
# ステップ45: プロンプトレジストリテスト
# =============================================================================

class TestCommercialPromptRegistry:
    """商用プロンプトレジストリのテスト"""

    def test_commercial_role_prompt_registry(self):
        """商業的役割プロンプトが取得できる"""
        prompt = commercial_role_prompt_registry(
            role="avatar_of_desire",
            character_name="テストキャラ",
            prompt_type="scene_generation"
        )
        assert "テストキャラ" in prompt
        assert len(prompt) > 0

    def test_pleasure_prompt_registry(self):
        """快楽設計プロンプトが取得できる"""
        prompt = pleasure_prompt_registry("catharsis_building")
        assert "カシス" in prompt or "カタルシス" in prompt
        assert len(prompt) > 0

    def test_marketing_prompt_registry(self):
        """マーケティングプロンプトが取得できる"""
        prompt = marketing_prompt_registry("hook_generation")
        assert "フック" in prompt or "hook" in prompt.lower()
        assert len(prompt) > 0

    def test_style_prompt_registry(self):
        """スタイルDNAプロンプトが取得できる"""
        prompt = style_prompt_registry("voice_extraction")
        assert "文体" in prompt or "voice" in prompt.lower()
        assert len(prompt) > 0

    def test_series_prompt_registry(self):
        """シリーズ展開プロンプトが取得できる"""
        prompt = series_prompt_registry("arc_planning")
        assert "シリーズ" in prompt or "arc" in prompt.lower()
        assert len(prompt) > 0

    def test_ab_test_prompt_registry(self):
        """A/Bテストプロンプトが取得できる"""
        prompt = ab_test_prompt_registry("opening_variation")
        assert "A/B" in prompt or "variation" in prompt.lower() or "バライエーション" in prompt
        assert len(prompt) > 0

    def test_generate_full_commercial_prompt_pack(self):
        """完全な商用プロンプトパックが生成できる"""
        pack = generate_full_commercial_prompt_pack(
            character_name="テストキャラ",
            commercial_roles=["avatar_of_desire", "growth_investment"],
            target_market="web novel"
        )

        # 必須キーが存在
        assert "commercial_role_avatar_of_desire" in pack
        assert "pleasure_catharsis" in pack
        assert "marketing_hook" in pack
        assert "style_voice" in pack
        assert "series_arc" in pack
        assert "ab_opening" in pack
        assert "platform_optimization" in pack


# =============================================================================
# ステップ46: データローダー統合テスト
# =============================================================================

class TestCommercialDataLoader:
    """CommercialDataLoader のテスト"""

    def test_role_platform_score(self):
        """役割とプラットフォームの相性スコアが取得できる"""
        score = CommercialDataLoader.get_role_platform_score(
            "avatar_of_desire",
            "カクヨム/なろう"
        )
        assert 0.0 <= score <= 1.0

    def test_get_optimal_roles_for_platform(self):
        """プラットフォームに最適な役割ランキングが取得できる"""
        roles = CommercialDataLoader.get_optimal_roles_for_platform("カクヨム/なろう")
        assert len(roles) == 9  # 全9役
        assert roles[0][1] >= roles[-1][1]  # ソート確認

    def test_get_commercial_weight(self):
        """商業的重みが取得できる"""
        weight = CommercialDataLoader.get_commercial_weight("WEIGHT_PLEASURE_CATHARSIS")
        assert weight > 0

    def test_get_default_roles_for_genre(self):
        """ジャンルに応じたデフォルト役割が取得できる"""
        roles = CommercialDataLoader.get_default_roles_for_genre("追放・ざまぁ")
        assert len(roles) > 0
        assert "avatar_of_desire" in roles or "hate_magnet" in roles

    def test_get_market_trend_recommendations(self):
        """市場トレンド推奨が取得できる"""
        trends = CommercialDataLoader.get_market_trend_recommendations()
        assert "trending" in trends
        assert "declining" in trends
        assert len(trends["trending"]) > 0

    def test_calculate_commercial_score(self):
        """商業スコアが計算できる"""
        profile = {
            "commercial_roles": ["avatar_of_desire", "growth_investment"],
        }
        score = CommercialDataLoader.calculate_commercial_score(
            profile,
            "カクヨム/なろう",
            "追放"
        )
        assert 0.0 <= score <= 2.0


class TestABTestConfig:
    """ABTestConfig のテスト"""

    def test_get_test_variants(self):
        """テストバライエーションが取得できる"""
        variants = ABTestConfig.get_test_variants("opening_hook")
        assert len(variants) == 3  # A, B, C

    def test_get_default_test_suite(self):
        """デフォルトテストスイートが取得できる"""
        suite = ABTestConfig.get_default_test_suite()
        assert "character_introduction" in suite
        assert "conflict_resolution" in suite
        assert "relationship_development" in suite


class TestLoadCommercialSettings:
    """load_commercial_settings のテスト"""

    def test_load_commercial_settings_complete(self):
        """商用設定が完全に読み込める"""
        settings = load_commercial_settings()

        assert "commercial_weights" in settings
        assert "role_platform_matrix" in settings
        assert "market_trends" in settings
        assert "ab_test_suite" in settings
        assert "platform_profiles" in settings


# =============================================================================
# ステップ47-48: ユーティリティ関数テスト
# =============================================================================

class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    def test_calculate_recognition_value(self):
        """認知価値が計算できる"""
        value = calculate_recognition_value(base_power=50, rarity=3)
        assert value > 0

    def test_assign_commercial_role(self):
        """商業的役割が自動割り当てできる"""
        profile = {
            "base_power": 50,
            "personality": ["勇敢", "憐れみ深い"],
        }
        roles = assign_commercial_role(profile)
        assert len(roles) > 0

    def test_get_role_pleasure_keywords(self):
        """役割の快楽キーワードが取得できる"""
        keywords = get_role_pleasure_keywords(["avatar_of_desire", "growth_investment"])
        assert len(keywords) > 0

    def test_validate_character_commercial_value(self):
        """キャラクター商業価値の検証ができる"""
        profile = {
            "name": "テストキャラ",
            "base_power": 50,
            "commercial_roles": ["avatar_of_desire"],
        }
        validation = validate_character_commercial_value(profile)
        assert "is_valid" in validation
        assert "missing_attributes" in validation

    def test_get_gap_attribute_pair(self):
        """ギャップ属性ペアが取得できる"""
        profile = {
            "surface_trait": "冷酷",
            "hidden_trait": "情に脆い",
        }
        pair = get_gap_attribute_pair(profile)
        assert pair is not None

    def test_get_status_flip_timing_config(self):
        """ステータス反転タイミング設定が取得できる"""
        config = get_status_flip_timing_config("mid_flip")
        assert "trigger_position" in config
        assert "impact_modifier" in config


# =============================================================================
# 統合テスト
# =============================================================================

class TestCommercialIntegration:
    """商用化システムの統合テスト"""

    def test_full_commercial_pipeline(self):
        """完全な商用パイプラインが動作する"""
        # 1. キャラクタープロファイル作成
        profile = {
            "name": "テストヒーロー",
            "base_power": 40,
            "personality": ["勇敢", "不安定"],
            "commercial_roles": ["avatar_of_desire", "growth_investment"],
        }

        # 2. 役割の自動割り当て
        roles = assign_commercial_role(profile)
        assert len(roles) > 0

        # 3. 快楽グラフ構築
        graph = build_default_pleasure_graph()
        assert len(graph.nodes) > 0

        # 4. プロンプトパック生成
        pack = generate_full_commercial_prompt_pack(
            character_name=profile["name"],
            commercial_roles=roles,
            target_market="web novel"
        )
        assert len(pack) > 10

        # 5. 商業スコア計算
        score = CommercialDataLoader.calculate_commercial_score(
            profile,
            "カクヨム/なろう",
            "追放"
        )
        assert 0.0 <= score <= 2.0

        # 6. 市場トレンド取得
        trends = CommercialDataLoader.get_market_trend_recommendations()
        assert len(trends["trending"]) > 0
