# キャラクター商品価値設計：48ステップ実装プラン

## 概要
[`config/archetypes.py`](config/archetypes.py:1) に9つの「商用キャラクター役割（Commercial Roles）」を追加し、物語生成時に各キャラクターに商業的な「感情報酬供給装置」としての機能を 자동으로 부여する。

---

## フェーズ1：基盤データ構造の拡張（ステップ1-12）

### 1. 商用役割の型定義追加
- [`config/archetypes.py`](config/archetypes.py:1) に `CommercialRole` 型（列挙型）を定義
- 9つの役割を定数として列挙：
  - `AVATAR_OF_DESIRE` = 自己投影・願望充足キャラクター
  - `HATE_MAGNET` = 憎悪集積型悪役
  - `UNCONDITIONAL_SUPPORTER` = 絶対的肯定シェルター
  - `CONTRAST_ENGINE` = ギャップ萌え駆動
  - `UNIQUE_VALUE_PROPOSITION` = 希少能力・承認欲求充足
  - `GROWTH_INVESTMENT` = 成長可視化・投資心理喚起
  - `DESTINED_RESONANCE` = 運命的結びつき
  - `INFORMATION_HEGEMONY` = 情報の非対称性
  - `STATUS_FLIP_TRIGGER` = 社会的地位逆転

### 2. 商用役割デフォルト値の Dict 作成
- `DEFAULT_COMMERCIAL_ROLES: Dict[str, List[str]]` を追加
- 例：`{"protagonist": ["AVATAR_OF_DESIRE", "GROWTH_INVESTMENT"], "villain": ["HATE_MAGNET", "STATUS_FLIP_TRIGGER"]}`

### 3. 商用役割별 必須属性マッピングの追加
- 各役割が必要とするキャラクター属性を定義
- 例：`ROLE_REQUIRED_ATTRIBUTES = {"AVATAR_OF_DESIRE": ["hidden_potential", "social_disadvantage"], "HATE_MAGNET": ["unjust_authority", "public Humiliation_trigger"]}`

### 4.快感トリガーキーワード辞書の拡張
- [`config/data/hegemony_patterns.json`](config/data/hegemony_patterns.json:1) に各役割別の快感情关键词を追加
- 例：`"HATE_MAGNET_keywords": ["許せない", "ふざけるな", "死んでほしい"]`

### 5. 商品価値メタデータ型の定義
- `CharacterCommercialMeta` dataclass を [`config/models.py`](config/models.py:1) に追加
- フィールド：`role`, `pleasure_score`, `gap_attributes`, `resonance_targets`, `flip_timing`

### 6. archetypes.py に role_assigner 関数のスケルトン作成
- `def assign_commercial_role(character_profile: Dict) -> List[str]:` を追加
- 現在のキャラクター設定から適切な役割リストを返すロジックの中身を stub で作成

### 7. ギャップ萌え属性ペア辞書の作成
- `GAP_ATTRIBUTE_PAIRS: List[Tuple[str, str]]` を追加
- 例：`[("cold_aristocrat", "secret_sweet_tooth"), ("fearless_warrior", "animal_lover")]`

### 8. 運命的結びつきパターンの定義
- `DESTINED_RESONANCE_PATTERNS: Dict[str, str]` を追加
- 例：`{"soul_complement": "欠落部分を互いに補完する魂の相性", "destined_rival": "必然的な競争と成長を促す存在"}`

### 9. 地位逆転タイミング定義の追加
- `STATUS_FLIP_TIMING: Dict[str, int]` を追加
- 例：`{"early_flip": 20, "mid_flip": 50, "late_flip": 80}` （全体の何%で逆転するか）

### 10. 情報非対称性パターン辞書の追加
- `INFORMATION_HEGEMONY_PATTERNS: Dict[str, str]` を追加
- 例：`{"future_knowledge": "未来の知識", "system_bug": "システムのバグ知り", "true_identity": "真の正体・立場"}`

### 11. 承認欲求充足スコア計算式の定義
- `def calculate_recognition_value(base_power: int, rarity: int) -> float:` を追加
- 能力の希少性に基づく承認得快感のスコア計算ロジック

### 12. 成長投資曲線タイマー定義の追加
- `GROWTH_INVESTMENT_PHASES: List[Dict[str, Any]]` を追加
- 例：`[{"phase": 1, "status": "軽蔑", "threshold": 0}, {"phase": 2, "status": "認識", "threshold": 30}, {"phase": 3, "status": "賞賛", "threshold": 70}]`

---

## フェーズ2：カーネルとの統合（ステップ13-24）

### 13. [`kernels/hegemony.py`](kernels/hegemony.py:1) に role_based_power_shift 関数追加
- 商用役割に応じて登場人物の発言権・支配力を動的に変動させるロジック
- 例：`HATE_MAGNET` は初期に強い支配力を持つが、後半で崩壊する

### 14. [`kernels/comfort.py`](kernels/comfort.py:1) に unconditional_supporter_trigger 追加
- `UNCONDITIONAL_SUPPORTER` 役割のキャラクターが「全肯定台词」を吐出するトリガー条件の定義

### 15. [`kernels/resonance.py`](kernels/resonance.py:1) に destined_connection_builder 追加
- `DESTINED_RESONANCE` 役割のキャラクター同士の「運命的な出会い」を演出するプロンプト生成

### 16. [`kernels/graph.py`](kernels/graph.py:1) に pleasure_graph 型の追加
- カタルシス・グラフを表現するデータ構造（ノード：快不快イベント、エッジ：因果関係）

### 17. graph.py に status_flip_validator 関数追加
- 社会的地位逆転イベントが適切に配置されているかを検証

### 18. [`kernels/conflict.py`](kernels/conflict.py:1) に hate_amplification_loop 追加
- `HATE_MAGNET` 役の悪役が「憎悪を蓄積させる行動」を繰り返し演じるループ構造

### 19. [`kernels/enigma.py`](kernels/enigma.py:1) に information_monopoly_builder 追加
- `INFORMATION_HEGEMONY` 役割に基づき、「主人公だけが知る情報」のiscovery シーンを生成

### 20. [`kernels/body_language.py`](kernels/body_language.py:1) に gap_expression_patterns 追加
- `CONTRAST_ENGINE` 役割のキャラクターの外見と内面のギャップを身体言語で表現するパターン

### 21. [`kernels/dialogue.py`](kernels/dialogue.py:1) に avatar_desire_dialogue_generator 追加
- `AVATAR_OF_DESIRE` 役割のキャラクターが「読者の願望を代弁する台词」を生成

### 22. [`kernels/pov.py`](kernels/pov.py:1) に growth_investment_pov_switcher 追加
- `GROWTH_INVESTMENT` に基づいて主人公視点の「成長を実感できる瞬間」を優先的に描写

### 23. [`kernels/memory.py`](kernels/memory.py:1) に pleasure_memory_tagger 追加
- 生成されたシーンに「快感情の種類」と「強度」をタグ付けして記憶

### 24. [`kernels/preset_triggers.py`](kernels/preset_triggers.py:1) に commercial_role_triggers 追加
- 商用役割別の自動トリガー条件定義（例：物語の10%地点でSTATUS_FLIP潜伏を開始など）

---

## フェーズ3：プロンプト・レジストリ拡張（ステップ25-36）

### 25. [`prompts/registry.py`](prompts/registry.py:1) に commercial_role_templates 辞書を追加
- 各商用役割用のテンプレート文字列をレジストリに追加

### 26. prompts/registry.py に role_specific_system_prompts 追加
- 例：`HATE_MAGNET` 系の悪役を描写するためのシステムプロンプト追加

### 27. [`prompts/creation.py`](prompts/creation.py:1) に assign_commercial_role_to_character プロンプト追加
- キャラクター生成時に「商品価値役割」を指定するプロンプトテンプレート

### 28. prompts/creation.py に generate_gap_moe_scene プロンプト追加
- 「ギャップ萌え」場面を自動生成するプロンプト

### 29. [`prompts/hegemony_persona.py`](prompts/hegemony_persona.py:1) に role_based_hegemony_rules 追加
- 商用役割に応じた支配・服従の力学を描写するルール

### 30. prompts/conflict_persona.py に hate_accumulation_protocol 追加
- 読者の憎悪を計画的に蓄積・爆発させるプロセス

### 31. prompts/comfort_persona.py に unconditional_support_template 追加
- 「全肯定台词」の自動生成用テンプレート

### 32. prompts/enigma_persona.py に information_reveal_script 追加
- 「だけが知る真実」の開示シーン用スクリプト

### 33. prompts/connection_persona.py に destined_bond_builder 追加
- 運命的な結びつきを演出する台詞・行動パターン

### 34. prompts/serenity_persona.py に comfort_shelter_metrics 追加
- 「精神的シェルター」の強度を維持するための指標とプロンプト

### 35. prompts/plotting.py に pleasure_graph_builder_prompt 追加
- カタルシス・グラフを物語プロットに組み込むプロンプト

### 36. prompts/utils.py に role_validator ユーティリティ関数追加
- 生成されたキャラクター設定が商品価値役割の要件を満たしているか検証

---

## フェーズ4：データローダー・設定連携（ステップ37-42）

### 37. [`config/data_loader.py`](config/data_loader.py:1) に load_commercial_role_data 関数追加
- 商品価値役割用のJSON/YAMLデータを読み込むローダー

### 38. config/data_loader.py に load_pleasure_patterns 関数追加
- [`config/data/hegemony_patterns.json`](config/data/hegemony_patterns.json:1) 等の快感情パターンデータを読み込む

### 39. [`config/settings.py`](config/settings.py:1) に ENABLE_COMMERCIAL_ROLES フラグ追加
- 商用役割システムを有効/無効にする設定スイッチ

### 40. config/settings.toml に commercial_roles セクション追加
- 各役割のデフォルト強度、スコアリングパラメータ等の設定

### 41. [`config/domain_profile_manager.py`](config/domain_profile_manager.py:1) に apply_commercial_roles_to_profile 追加
- ドメインプロファイルに商用役割情報を 자동으로 병합

### 42. config/models.py に CommercialRoleConfig dataclass 追加
- 商用役割用の設定オブジェクト（役割名、有効/無効、カスタムパラメータ）

---

## フェーズ5：テスト・統合（ステップ43-48）

### 43. tests/ ディレクトリに character_commercial_value_test.py 作成
- 各商用役割のキャラクター生成テストケース

### 44. [`prompts/ai_producer_audit`](prompts/ai_producer_audit) に commercial_value_audit 追加
- 生成作品が商品価値役割を適切に果たしているかを監査するプロンプト

### 45. [`kernels/pipeline.py`](kernels/pipeline.py:1) に commercial_role_injection_point 追加
- 物語生成パイプラインのどの段階で商用役割を注入するかの制御ポイント

### 46. [`formatters/kakuyomu.py`](formatters/kakuyomu.py:1) に role_based_tag_generator 追加
- 商用役割に基づいたカクヨム向け自動タグ生成

### 47. demo.py または [`demo_hegemony.db-shm`](demo_hegemony.db-shm) に関連テストケース追加
- 商用役割システムを実際に動作させるデモスクリプト

### 48. [`docs/`](docs/:1) に commercial_role_implementation_guide.md 作成
- 実装ガイド兼、利用者向けAPI仕様書ドキュメント

---

## 実装優先順位マトリクス

| ステップ | 役割 | 重要度 | 依存関係 |
|---------|------|--------|---------|
| 1-12 | 基盤データ構造 | ★★★ | なし |
| 13-24 | カーネル統合 | ★★★ | 1-12完了後 |
| 25-36 | プロンプト拡張 | ★★☆ | 1-12完了後 |
| 37-42 | 設定連携 | ★★☆ | 1-12, 25-36後 |
| 43-48 | テスト・統合 | ★☆☆ | 全フェーズ完了後 |

---

## 成功指標

- 全9つの商用役割が[`config/archetypes.py`](config/archetypes.py:1)에서 정의되고
- 物語生成時に役割に応じた快感情upplyが自動化され
- [`prompts/ai_producer_audit`](prompts/ai_producer_audit) で商業品質が検証される