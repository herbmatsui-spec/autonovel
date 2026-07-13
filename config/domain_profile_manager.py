"""
config/domain_profile_manager.py — ドメインプロファイルの重み・設定へのアクセサ

DomainProfileManager:  スコアリング重み係数を管理する
DomainProfileService:  ドメイン固有のテキスト生成補助メソッドを提供する
"""
from __future__ import annotations

from typing import Any, Dict, List

# ランタイム上書き用レジストリ
_domain_values: Dict[str, Any] = {}

# デフォルト重み係数
_DEFAULT_WEIGHTS: Dict[str, float] = {
    "WEIGHT_EMOTIONAL_RESONANCE": 1.0,
    "WEIGHT_THEMATIC_DEPTH":      1.0,
    "WEIGHT_LITERARY_BEAUTY":     1.0,
    "WEIGHT_BASE_ENGAGEMENT":     1.0,
}


class DomainProfileManager:
    """
    ジャンル・ドメインに応じたスコアリング重み係数を管理する。
    将来的にはジャンル別プロファイルファイルから読み込む実装に置き換える。
    """

    @staticmethod
    def get_value(key: str, default: Any = None) -> Any:
        """
        指定されたキーの値を返す。

        Parameters
        ----------
        key : str
            重み係数名 (例: "WEIGHT_EMOTIONAL_RESONANCE")
        default : Any
            キーが未定義の場合のデフォルト値

        Returns
        -------
        Any
        """
        # ランタイム上書きを優先
        if key in _domain_values:
            return _domain_values[key]
        # デフォルト重みテーブルを参照
        if key in _DEFAULT_WEIGHTS:
            return _DEFAULT_WEIGHTS[key]
        return default

    @staticmethod
    def set_value(key: str, value: Any) -> None:
        """ランタイム上書きで値を変更する（プロファイル切り替え用）。"""
        _domain_values[key] = value

    @staticmethod
    def reset() -> None:
        """ランタイム上書きをリセットする。"""
        _domain_values.clear()


class DomainProfileService:
    """
    ジャンルおよびエンジンキーに応じた生成補助テキストを提供する。
    将来的には config/data/ 配下の JSON プロファイルから読み込む実装に置き換える。
    """

    _PLATFORM_PROFILES: Dict[str, Dict[str, Any]] = {
        "カクヨム/なろう": {
            "name": "カクヨム/小説家になろう",
            "description": "テンプレ設定、追放ざまぁ、WEB小説特有の超速ペーシング、読者の即時カタルシスと承認欲求充足が極めて重要。",
            "preferred_tropes": ["追放・ざまぁ", "チート・ユニークスキル", "無自覚・勘違い", "パーティー追放からのソロ無双"],
            "tone": "コミカルかつスカッとする、テンポ重視、説明的すぎず分かりやすい地の文"
        },
        "アルファポリス": {
            "name": "アルファポリス",
            "description": "スローライフ、もふもふ動物、お仕事もの、女性向け異世界恋愛。まったりした日常描写や、明確な悪意のない穏やかなストーリーが好まれる。",
            "preferred_tropes": ["もふもふ・精霊契約", "スローライフ・開拓", "料理・生産職", "悪役令嬢の領地経営"],
            "tone": "穏やかで丁寧、アットホーム、過度な暴力描写は避ける"
        },
        "ノベルアップ＋": {
            "name": "ノベルアップ＋",
            "description": "読者と作者の距離が近く、メタフィクション要素、ゲーム風ステータス、ちょっと尖ったニッチな設定やギャグが許容されやすい。",
            "preferred_tropes": ["ステータス・システム画面", "メタ要素・パロディ", "ダークヒーロー", "独自のニッチ職業"],
            "tone": "賑やか、ポップ、ライトノベルらしい軽快なセリフ回し"
        },
        "ライト文芸": {
            "name": "ライト文芸",
            "description": "キャラクター文芸、現代のファンタジー、怪異・あやかし、謎解き、心理描写やエモーショナルな人間関係を重視。イラスト映えするキャラクター描写。",
            "preferred_tropes": ["怪異・あやかしとの共生", "日常の謎・ライトミステリ", "契約結婚・すれ違いの愛", "京都・和風レトロな舞台"],
            "tone": "情緒的、情感豊かな描写、キャラクターの繊細な心理変化に焦点を当てる"
        },
        "一般エンタメ": {
            "name": "一般エンタメ",
            "description": "普遍的なテーマ性、論理的整合性の高さ、深い人間ドラマ、しっかりした世界観構築。ご都合主義を排したリアルな葛藤と展開。",
            "preferred_tropes": ["成長ドラマ", "謎解き・サスペンス", "職業・業界のリアルな内幕", "宿命の対決"],
            "tone": "重厚、叙情的、リアリズムを重視し、安易なステータスやご都合チートは避ける"
        }
    }

    @classmethod
    def get_platform_profile(cls, platform: str) -> Dict[str, Any]:
        """指定されたプラットフォームのプロファイルを返す。"""
        return cls._PLATFORM_PROFILES.get(platform, cls._PLATFORM_PROFILES["カクヨム/なろう"])

    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """サポートされているプラットフォームの一覧を返す。"""
        return list(cls._PLATFORM_PROFILES.keys())

    # ジャンル別のあらすじ構成要素（テーマ・結末）
    _THEME_MAP: Dict[str, str] = {
        "追放":       "不当な追放から這い上がり、圧倒的な力で旧勢力に報復する物語。",
        "ざまぁ":      "積み重なった屈辱を一気に晴らす爽快なカタルシスを描く物語。",
        "悪役令嬢":    "断罪イベントを回避しつつ、真の幸福をつかみ取る逆転劇。",
        "スローライフ": "競争から離れ、自らのペースで充実した日常を築く癒やしの物語。",
        "飯テロ":      "絶品料理と人との交流を軸に、穏やかな日常を彩る物語。",
        "転生":        "異世界での新しい人生を切り開く、成長と冒険の物語。",
    }

    _ENDING_MAP: Dict[str, str] = {
        "追放":       "最終的に旧勢力が崩壊し、主人公が真の評価を得て悲願を果たす。",
        "ざまぁ":      "かつての迫害者が完全に断罪され、主人公は揺るぎない地位を確立する。",
        "悪役令嬢":    "主人公は断罪の運命を覆し、真の幸福とパートナーを手に入れる。",
        "スローライフ": "理想の生活拠点が完成し、かけがえのない仲間と静かな幸福を享受する。",
        "飯テロ":      "料理を通じた絆が広がり、主人公はなくてはならない存在として認められる。",
        "転生":        "前世の知識と経験を活かし、新しい世界で唯一無二の居場所を確立する。",
    }

    @classmethod
    def get_fallback_synopsis_details(
        cls,
        genre: str,
        keywords: str,
        engine_key: str,
    ) -> Dict[str, str]:
        """
        フォールバックあらすじ生成用の補助テキストを返す。

        Parameters
        ----------
        genre : str
            ジャンル文字列 (例: "追放・ざまぁ・ファンタジー")
        keywords : str
            企画キーワード
        engine_key : str
            エンジンキー (例: "zama", "slow_life")

        Returns
        -------
        Dict[str, str]
            {"theme_desc": str, "ending_desc": str}
        """
        theme_desc = "様々な試練を乗り越えながら成長し、真の自分の姿を確立する。"
        ending_desc = "主人公は全ての困難を克服し、望んでいた未来をつかみ取る。"

        for genre_key, desc in cls._THEME_MAP.items():
            if genre_key in genre or genre_key in keywords:
                theme_desc = desc
                break

        for genre_key, desc in cls._ENDING_MAP.items():
            if genre_key in genre or genre_key in keywords:
                ending_desc = f"【結末の方向性】{desc}"
                break

        return {"theme_desc": theme_desc, "ending_desc": ending_desc}

    # ジャンル・エンジンキー別 causality_map デフォルトテーブル
    _CAUSALITY_MAP_DEFAULTS: Dict[str, List[str]] = {
        "追放": [
            "不当な追放 → 主人公の孤立と実力の秘輟 → 圧倒的成長 → 旧勢力との逆転",
            "追放した側の慢心 → 主人公の暗躍を見落とす → 断罪フラグの積み上がり",
            "追放理由の隠蔽 → 真実が明るみに出た時の社会的崩壊",
        ],
        "ざまぁ": [
            "屈辱の蓄積 → 主人公の内的変化 → 一点突破の逆転劇",
            "追迫者の油断 → 主人公の爆発的成長を見逃す → 断罪不可避",
        ],
        "悪役令嬢": [
            "断罪フラグの認識 → 主人公の戦略的行動 → 運命の書き換え",
            "前世知識 → 世界の仕組みの逆用 → 周囲の認識とのギャップによるコメディ/緊張",
        ],
        "スローライフ": [
            "過労・競争社会からの離脱 → 田舎での再出発 → 本物の豊かさの再定義",
            "主人公の特殊スキル × 辺境の環境 → 地域コミュニティの変革",
        ],
        "飯テロ": [
            "料理の命 → 人との繋がり → 心理的安全基地の形成",
            "食材の希少性 → 主人公の独自展開 → 地域に欠かせない存在への承認",
        ],
        "転生": [
            "前世の記憶・知識 → 異世界のコモンセンスへの逐用 → 周囲との圧倒的ギャップの拡大",
            "転生直後の弱さ → 成長とスキル習得 → 新世界での居場所の確立",
        ],
        "enigma": [
            "情報の非対称性 → 主人公が相手の思考を先読みする → 知略の優位確立",
            "伏線の埋め込み → 中盤での複線交差 → 終盤の論理的カタルシス",
            "真実の隠蔽 → 段階的な暴露 → 読者の推理欲求の充足",
        ],
        "default": [
            "行動には必ず対価・代償が伴う",
            "強者は弱者を撗取する構造が存在し、主人公はその外側に立つ",
            "秘密は必ず明るみに出る—タイミングが物語の緊張を生む",
        ],
    }

    @classmethod
    def get_default_causality_map(cls, genre: str, engine_key: str) -> List[str]:
        """
        ジャンル・エンジンキーに基づいてデフォルトの causality_map を返す。

        Parameters
        ----------
        genre : str
            ジャンル文字列 (例: "追放・ざまぁ・ファンタジー")
        engine_key : str
            エンジンキー (例: "enigma", "zama", "slow_life")

        Returns
        -------
        List[str]
            causality_map のデフォルトエントリリスト
        """
        # engine_key を優先チェック（enigma 等エンジン固有の因果律を優先）
        if engine_key in cls._CAUSALITY_MAP_DEFAULTS:
            return cls._CAUSALITY_MAP_DEFAULTS[engine_key]
        # genre 文字列に含まれるキーをチェック
        for key in cls._CAUSALITY_MAP_DEFAULTS:
            if key not in ("default", "enigma") and key in genre:
                return cls._CAUSALITY_MAP_DEFAULTS[key]
        return cls._CAUSALITY_MAP_DEFAULTS["default"]


# =============================================================================
# フェーズ4（ステップ37-42）：商業データローダー・設定連携
# =============================================================================



class CommercialDataLoader:
    """
    商用化作品生成のためのデータローダー。
    DomainProfileServiceを拡張し、商业的な重み・プロファイルを提供する。
    """

    # 商業的役割とプラットフォームの相性マトリクス
    _ROLE_PLATFORM_COMPATIBILITY: Dict[str, Dict[str, float]] = {
        "avatar_of_desire": {
            "カクヨム/なろう": 1.0,
            "アルファポリス": 0.6,
            "ノベルアップ＋": 0.9,
            "ライト文芸": 0.7,
            "一般エンタメ": 0.8,
        },
        "hate_magnet": {
            "カクヨム/なろう": 1.0,
            "アルファポリス": 0.3,
            "ノベルアップ＋": 0.8,
            "ライト文芸": 0.5,
            "一般エンタメ": 0.9,
        },
        "unconditional_supporter": {
            "カクヨム/なろう": 0.7,
            "アルファポリス": 1.0,
            "ノベルアップ＋": 0.6,
            "ライト文芸": 0.9,
            "一般エンタメ": 0.7,
        },
        "contrast_engine": {
            "カクヨム/なろう": 0.8,
            "アルファポリス": 0.7,
            "ノベルアップ＋": 0.9,
            "ライト文芸": 1.0,
            "一般エンタメ": 0.8,
        },
        "unique_value": {
            "カクヨム/なろう": 0.9,
            "アルファポリス": 0.6,
            "ノベルアップ＋": 0.8,
            "ライト文芸": 0.9,
            "一般エンタメ": 1.0,
        },
        "growth_investment": {
            "カクヨム/なろう": 1.0,
            "アルファポリス": 0.5,
            "ノベルアップ＋": 0.9,
            "ライト文芸": 0.7,
            "一般エンタメ": 0.8,
        },
        "destined_resonance": {
            "カクヨム/なろう": 0.8,
            "アルファポリス": 0.9,
            "ノベルアップ＋": 0.7,
            "ライト文芸": 1.0,
            "一般エンタメ": 0.8,
        },
        "information_hegemony": {
            "カクヨム/なろう": 0.7,
            "アルファポリス": 0.4,
            "ノベルアップ＋": 1.0,
            "ライト文芸": 0.9,
            "一般エンタメ": 0.9,
        },
        "status_flip_trigger": {
            "カクヨム/なろう": 1.0,
            "アルファポリス": 0.4,
            "ノベルアップ＋": 0.8,
            "ライト文芸": 0.6,
            "一般エンタメ": 0.9,
        },
    }

    # 商業的スコアリング重み
    COMMERCIAL_WEIGHTS: Dict[str, float] = {
        "WEIGHT_CHARACTER_COMMERCIAL_VALUE": 1.2,  # キャラクターの商業的価値
        "WEIGHT_PLEASURE_CATHARSIS": 1.5,         # カタルシス設計
        "WEIGHT_READER_INVESTMENT": 1.3,           # 読者投資度
        "WEIGHT_PLATFORM_FIT": 1.1,                # プラットフォーム適合性
        "WEIGHT_HOOK_EFFECTIVENESS": 1.0,          # フックの効果
        "WEIGHT_SERIES_POTENTIAL": 0.9,            # シリーズ化ポテンシャル
    }

    # 市場トレンドデータ（簡易版）
    MARKET_TREND_DATA: Dict[str, Dict[str, Any]] = {
        "trending_tropes": {
            "2024_h2": [
                "スラム・辺境からのはい上がり",
                "Intelligence不是・IQだけの强者",
                "ハーレムなし·一対一の-Romance",
                "生産技.net 向上系",
                "悪役女主角",
            ],
            "2025_h1": [
                "スキル transferencias・能力コピー",
                "tsundereから捂着への移行",
                "後悔系·前世トラウマ",
                "Villainの可視化·立体化",
                "日常系·空气嫁の重要性",
            ],
        },
        "declining_tropes": [
            "単純な最強無敵",
            "ハーレム展開",
            "読者への侮蔑を呼ぶ主人公",
            "ご都合主義的なチート",
        ],
    }

    @classmethod
    def get_role_platform_score(cls, role: str, platform: str) -> float:
        """
        商業的役割とプラットフォームの相性スコアを返す。
        
        Args:
            role: 商業的役割名
            platform: プラットフォーム名
        
        Returns:
            相性スコア (0.0-1.0)
        """
        role_compat = cls._ROLE_PLATFORM_COMPATIBILITY.get(role, {})
        return role_compat.get(platform, 0.5)

    @classmethod
    def get_optimal_roles_for_platform(cls, platform: str) -> List[Tuple[str, float]]:
        """
        プラットフォームに最も効果的な商業的役割ランキングを返す。
        
        Returns:
            役割名とスコアのタプルのリスト
        """
        scores = []
        for role in cls._ROLE_PLATFORM_COMPATIBILITY:
            score = cls.get_role_platform_score(role, platform)
            scores.append((role, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    @classmethod
    def get_commercial_weight(cls, weight_key: str) -> float:
        """商業的スコアリング重みを返す。"""
        return cls.COMMERCIAL_WEIGHTS.get(
            weight_key,
            cls.COMMERCIAL_WEIGHTS.get("WEIGHT_CHARACTER_COMMERCIAL_VALUE", 1.0)
        )

    @classmethod
    def get_default_roles_for_genre(cls, genre: str) -> List[str]:
        """
        ジャンルに応じたデフォルト商業的役割リストを返す。
        
        Args:
            genre: ジャンル文字列
        
        Returns:
            推奨商業的役割リスト
        """
        role_mapping = {
            "追放": ["avatar_of_desire", "hate_magnet", "status_flip_trigger"],
            "ざまぁ": ["hate_magnet", "schadenfreude", "status_flip_trigger"],
            "悪役令嬢": ["contrast_engine", "growth_investment", "destined_resonance"],
            "スローライフ": ["unconditional_supporter", "growth_investment", "contrast_engine"],
            "飯テロ": ["unconditional_supporter", "destined_resonance"],
            "転生": ["avatar_of_desire", "growth_investment", "unique_value"],
            "Intelligence不是": ["unique_value", "information_hegemony", "contrast_engine"],
        }

        for key, roles in role_mapping.items():
            if key in genre:
                return roles

        return ["avatar_of_desire", "growth_investment"]

    @classmethod
    def get_market_trend_recommendations(cls) -> Dict[str, Any]:
        """現在の市場トレンド推奨情報を返す。"""
        return {
            "trending": cls.MARKET_TREND_DATA["trending_tropes"]["2025_h1"],
            "declining": cls.MARKET_TREND_DATA["declining_tropes"],
            "advice": (
                "現在の市場では、平面的な最強主人公より、「成長過程が見える主人公」と"
                "「立体的な悪役）に注目が集まっています。HATE_MAGNET的な悪役は倒了時に"
                "大きなカタルシスを生みますが、同時に「なぜそうなったのか」の背景も重要です。"
            ),
        }

    @classmethod
    def calculate_commercial_score(
        cls,
        character_profile: Dict[str, Any],
        platform: str,
        genre: str,
    ) -> float:
        """
        キャラクターのプロファイルから商業スコアを算出。
        
        Args:
            character_profile: キャラクターパロファイル
            platform: プラットフォーム名
            genre: ジャンル
        
        Returns:
            商業スコア (0.0-2.0)
        """
        base_score = 1.0

        # 役割のプラットフォーム適合性を加成
        roles = character_profile.get("commercial_roles", [])
        if roles:
            role_avg = sum(cls.get_role_platform_score(r, platform) for r in roles) / len(roles)
            base_score *= (0.5 + role_avg)

        # ジャンルとの一致度を加成
        default_roles = cls.get_default_roles_for_genre(genre)
        genre_bonus = len(set(roles) & set(default_roles)) / max(len(default_roles), 1)
        base_score *= (1.0 + genre_bonus * 0.3)

        return min(base_score, 2.0)  # 上限2.0


class ABTestConfig:
    """
    A/Bテスト用の設定を管理するクラス。
    """

    # テストパターン定義
    TEST_PATTERNS: Dict[str, Dict[str, Any]] = {
        "opening_hook": {
            "A": {"type": "question_hook", "description": "疑問形で 시작"},
            "B": {"type": "action_hook", "description": "アクション開始で開始"},
            "C": {"type": "mystery_hook", "description": "謎かけで開始"},
        },
        "villain_defeat_pattern": {
            "A": {"type": "direct_confrontation", "description": "直接対決で撃破"},
            "B": {"type": "strategic_defeat", "description": "智略で翻弄して撃破"},
            "C": {"type": "humiliation_reversal", "description": " Former victimsによる逆襲"},
        },
        "romance_progression": {
            "A": {"type": "slow_burn", "description": "缓慢な感情浸透"},
            "B": {"type": "quick_bond", "description": "危機共有で急接近"},
            "C": {"type": "rivalry_love", "description": "恋のライバルの存在"},
        },
    }

    @classmethod
    def get_test_variants(cls, test_name: str) -> List[Dict[str, Any]]:
        """テスト名のバライエーションリストを返す。"""
        variants = cls.TEST_PATTERNS.get(test_name, {})
        return [
            {"key": key, **value}
            for key, value in variants.items()
        ]

    @classmethod
    def get_default_test_suite(cls) -> Dict[str, List[str]]:
        """デフォルトのテストスイートを返す。"""
        return {
            "character_introduction": ["opening_hook"],
            "conflict_resolution": ["villain_defeat_pattern"],
            "relationship_development": ["romance_progression"],
        }


def load_commercial_settings() -> Dict[str, Any]:
    """
    商用化設定を全て読み込んで返す。
    
    Returns:
        設定辞書を包括的に返す
    """
    return {
        "commercial_weights": CommercialDataLoader.COMMERCIAL_WEIGHTS,
        "role_platform_matrix": CommercialDataLoader._ROLE_PLATFORM_COMPATIBILITY,
        "market_trends": CommercialDataLoader.get_market_trend_recommendations(),
        "ab_test_suite": ABTestConfig.get_default_test_suite(),
        "platform_profiles": DomainProfileService._PLATFORM_PROFILES,
    }
