# 官能Aサブエージェント拡張実装計画書

## 概要

Fanza等のエロ動画を参考にした「映像パターン→文学技法」変換システムを実装し、UIでオンオフ・程度を調整可能にする。

---

## 1. 現状の課題

| 課題 | 詳細 |
|---|---|
| ボキャブラリが画一的 | 「溶ける」「崩れる」系の比喩が repetición |
| プロンプトが単純 | 感覚の優先順位や強調指示が不足 |
| 映像的な多様性がない | カメラワーク的パターンが考慮されていない |
| パラメータ調整不可 | intensity 只今の0-5では細やかな調整不可 |

---

## 2. 設計方針

### 2.1 コアコンセプト

```
[Fanza等の動画分析] → [映像パターンの抽象化] → [文学技法への翻訳] → [ボキャブラリ登録]
```

### 2.2 ユーザーが調整可能なパラメータ

| パラメータ | 範囲 | デフォルト | 説明 |
|---|---|---|---|
| `enabled` | ON/OFF | OFF | 官能モードの有効/無効 |
| `base_intensity` | 0-5 | 2 | 全体の強度 |
| `sensory_weight_touch` | 0-100 | 80 | 触覚の重み |
| `sensory_weight_scent` | 0-100 | 60 | 嗅覚の重み |
| `sensory_weight_sound` | 0-100 | 70 | 聴覚の重み |
| `sensory_weight_gaze` | 0-100 | 50 | 視線の重み |
| `sensory_weight_breath` | 0-100 | 75 | 呼吸の重み |
| `sensory_weight_taste` | 0-100 | 30 | 味覚の重み |
| `pace_ratio_build` | 1-10 | 3 | ビルドの長さ |
| `pace_ratio_peak` | 1-10 | 2 | ピークの長さ |
| `pace_ratio_afterglow` | 1-10 | 2 | 余韻の長さ |
| `metaphor_density` | 0-100 | 50 | 比喩の密度 |
| `psychology_depth` | 0-100 | 50 | 心理描写の深さ |
| `use_video_patterns` | ON/OFF | ON | 動画パターンの有効/無効 |

---

## 3. 実装計画

### Phase 1: パラメータシステムの構築

#### Step 1: `config/erotic_parameters.py` 新規作成

```python
@dataclass
class EroticParameters:
    enabled: bool = False
    base_intensity: int = 2
    sensory_weights: Dict[str, int] = field(default_factory=lambda: {
        "touch": 80,
        "scent": 60,
        "sound": 70,
        "gaze": 50,
        "breath": 75,
        "taste": 30,
    })
    pace_ratios: Dict[str, int] = field(default_factory=lambda: {
        "build": 3,
        "peak": 2,
        "afterglow": 2,
    })
    metaphor_density: int = 50
    psychology_depth: int = 50
    use_video_patterns: bool = True
```

#### Step 2: `EroticCurve` の動的生成機能拡張

- `EroticCurve.create_from_parameters(params: EroticParameters) -> EroticCurve`
- `pace_ratio` に応じたサブビート数を動的生成
- sensory_weights に応じた sensory_focus の優先度付け

### Phase 2: 映像パターン→文学技法の変換

#### Step 3: `config/erotic_video_patterns.py` 新規作成

```python
VIDEO_PATTERNS = {
    "closeup": {
        "name": "接写",
        "description": "局部や表情のクローズアップ",
        "literary_technique": "部分描写の強調・感覚の細部への焦点",
        "example": "汗ばむ首筋の起伏、鎖骨の影、髪の一筋",
    },
    "pov": {
        "name": "POV視点",
        "description": "主観視点で相手を見る",
        "literary_technique": "「見る」の主体の明確化・視線の流向描写",
        "example": "視線が触れるだけで肌が焼ける",
    },
    "position_change": {
        "name": "体位変化",
        "description": "位置・角度の変化",
        "literary_technique": "空間の三次元描写・重心の移動",
        "example": "浮き上がる腰、変わる重心、崩れる平衡",
    },
    "rhythm": {
        "name": "リズム編集",
        "description": "テンポの変化（速→遅→速）",
        "literary_technique": "文の長さ・テンポの変動",
        "example": "短文と長文の交替、段落の長さ変化",
    },
    "sound_focus": {
        "name": "音強調",
        "description": "喘ぎ声や体音の強調",
        "literary_technique": "擬音・擬態語の増量、呼吸の音声化",
        "example": "荒い息が耳に刺さる、肌が擦れる音",
    },
    "tension_release": {
        "name": "緊張と解放",
        "description": "溜め→一気放出",
        "literary_technique": "クvscale=ド、苦 Periodの強調",
        "example": "抗うことすら忘れてしまう瞬間",
    },
    "multi_angle": {
        "name": "多角撮影",
        "description": "複数の視点からの描写",
        "literary_technique": "三次元空間での位置関係の明確化",
        "example": "二人の影が重なる角度、窓からの光の位置",
    },
    "slow_motion": {
        "name": "スロー再生",
        "description": "瞬間を長く引き伸ばす",
        "literary_technique": "瞬間描写の多重展開・感覚の拡張",
        "example": "触れる指の先が肌に触れる一秒が永遠に広がる",
    },
}
```

### Phase 3: 拡張ボキャブラリ

#### Step 4: `config/erotic_vocabulary_ext.py` の増強

| カテゴリ | 現在 | 目標 | 追加内容 |
|---|---|---|---|
| metaphors | 107 | 200+ | 映像的パターン対応比喩 |
| onomatopoeia | 85 | 150+ | 呼吸音、体音、湿潤音 |
| psychology | 79 | 150+ | 精神崩壊の段階的表現 |

### Phase 4: UI統合

#### Step 5: `streamlit_app/sidebar.py` に拡張コントロール追加

```python
with st.expander("🎬 官能エージェント設定（詳細）", expanded=False):
    # 有効/無効
    enable_erotic = st.checkbox("官能モードを有効にする", value=False)

    if enable_erotic:
        # 基本強度
        base_intensity = st.slider("基本強度", 0, 5, 2)

        # 感覚ウェイト（バー6本）
        st.caption("🎯 感覚ウェイト調整")
        col1, col2, col3 = st.columns(3)
        with col1:
            touch_w = st.slider("触覚", 0, 100, 80)
            scent_w = st.slider("嗅覚", 0, 100, 60)
        with col2:
            sound_w = st.slider("聴覚", 0, 100, 70)
            gaze_w = st.slider("視線", 0, 100, 50)
        with col3:
            breath_w = st.slider("呼吸", 0, 100, 75)
            taste_w = st.slider("味覚", 0, 100, 30)

        # ペーシング
        st.caption("⏱️ ペーシング比率")
        build_r = st.slider("溜め(Build)", 1, 10, 3)
        peak_r = st.slider("頂点(Peak)", 1, 10, 2)
        afterglow_r = st.slider("余韻(Afterglow)", 1, 10, 2)

        # 品質パラメータ
        st.caption("📝 品質パラメータ")
        metaphor_d = st.slider("比喩密度", 0, 100, 50)
        psych_d = st.slider("心理描写深度", 0, 100, 50)

        # 動画パターン
        use_patterns = st.checkbox("映像パターン技術を有効にする", value=True)
```

### Phase 5: Specialist の拡張

#### Step 6: `src/engine/prompts/erotic_specialist.py` 拡張

```python
class EroticSpecialist:
    def build_scene_prompt(
        self,
        curve: EroticCurve,
        context: Dict[str, Any],
        params: Optional[EroticParameters] = None,
    ) -> str:
        # params に応じたプロンプト生成
        # - sensory_weights に応じた感覚優先順位
        # - pace_ratios に応じたビート間比率
        # - video_patterns に応じた文学技法の選択
```

---

## 4. ファイル一覧

| ファイル | 操作 | 内容 |
|---|---|---|
| `config/erotic_parameters.py` | 新規 | パラメータ定義 |
| `config/erotic_video_patterns.py` | 新規 | 映像パターン定義 |
| `config/erotic_vocabulary_ext.py` | 拡張 | ボキャブラリ増強 |
| `config/erotic_pacing.py` | 拡張 | 動的曲線生成 |
| `src/engine/prompts/erotic_specialist.py` | 拡張 | パラメータ対応 |
| `streamlit_app/sidebar.py` | 拡張 | UIコントロール |

---

## 5. テスト計画

| テスト | 内容 |
|---|---|
| `test_erotic_parameters` | パラメータの生成・検証 |
| `test_erotic_curve_from_params` | パラメータからの曲線生成 |
| `test_video_pattern_integration` | 動画パターンのプロンプト挿入 |
| `test_sensory_weight_ordering` | 感覚ウェイトのソート順 |

---

## 6. リスクと対策

| リスク | 対策 |
|---|---|
| パラメータ組み合わせの爆炸 | 初期値は安全に固定、UIで制限 |
| 処理速度の低下 | パラメータ変更時はLazy再生成 |
| ボキャブラリ過多 | tier 別のサイズ上限を設定 |

---

## 7. 実装優先度

1. **Phase 1** (Step 1-2): パラメータシステム ← 優先度: 高
2. **Phase 2** (Step 3): 映像パターンマッピング ← 優先度: 高
3. **Phase 3** (Step 4): ボキャブラリ増強 ← 優先度: 中
4. **Phase 4** (Step 5): UI統合 ← 優先度: 高
5. **Phase 5** (Step 6): Specialist 拡張 ← 優先度: 高