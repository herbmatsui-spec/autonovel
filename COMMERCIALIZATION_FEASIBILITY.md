# 覇権小説エンジン v3.0 — 作品輸出としての商用化可能性検証と3提案

本ドキュメントは「app.pyを含むツール一式」を精査し、**このツールを使って商業出版作品／Web小説ランキング上位作品を実際に生み出せるか**（＝SaaS化ではなく"作品成果物としての商用化"）の現実的可能性を検証した結果をまとめる。既存の [`COMMERCIALIZATION_PROPOSALS.md`](COMMERCIALIZATION_PROPOSALS.md:1) は「ツール自体のSaaS事業化」中心であるため、ここでは補完的に「出力作品の商業化」に焦点を当てる。

---

## 1. 精査による現状把握（コア能力の棚卸し）

### 1.1 アーキテクチャの成熟度
- [`streamlit_app/app.py`](streamlit_app/app.py:1) は Streamlit フロント＋FastAPI バックエンドの二層構成で、プラグインローダ、UIStateStore、ヘルスチェック、 エンジンシングルトン（[`src/engine_service.py`](src/engine_service.py:1)）を備える。
- [`src/services/writing_services.py`](src/services/writing_services.py:1)、[`src/backend/engine.py`](src/backend/engine.py:1)、[`src/backend/engine_narrative.py`](src/backend/engine_narrative.py:1) に LangGraph/ワークフロー群と監査エージェントが実装されている。[`prompts/`](prompts/__init__.py:1) 配下は persona・audit・narrative・polish・utility の5カテゴリに整理済み。

### 1.2 商用／ランキング上位を想定した既存の機構（差別化資産）
| 機構 | 実装場所 | 役割 |
|---|---|---|
| **商用執筆プロトコル** | [`prompts/templates/utility/commercial_protocol.j2`](prompts/templates/utility/commercial_protocol.j2:1) | 「文字数の水増し禁止」「描写の解像度で達成」「各シーン末尾にフック」 |
| **ダイナミック・フック戦略** | [`prompts/templates/utility/hook_strategy_section.j2`](prompts/templates/utility/hook_strategy_section.j2:1) | 冒頭3行で欠落を刺激、末尾5行で次話クリフハンガー |
| **ストレス/カタルシス曲線** | [`src/backend/engine_narrative.py`](src/backend/engine_narrative.py:95) [`src/models/world.py`](src/models/world.py:41) | 累積ストレスが閾値を超えると**強制カタルシス**（ざまぁ発動）を自動挿入 |
| **ジャンル別テンション曲線** | [`src/backend/tension_utils.py`](src/backend/tension_utils.py:6) [`src/backend/tension_curve_config.py`](src/backend/tension_curve_config.py:1) | 進捗位置に応じた目標テンションを動的計算し、逸脱を検証 |
| **波パターン分析** | [`src/backend/engine_narrative.py`](src/backend/engine_narrative.py:172) [`src/models/audit.py`](src/models/audit.py:248) | 連載全体のストレス波を可視化し単調化を検知 |
| **監査エージェント群** | [`prompts/templates/audit/`](prompts/templates/audit/hegemony_audit_prompt.j2:1) | hegemony/conflict/enigma/comfort/serenity/logical/producer 等の多次元監査 |
| **官能強度基準 Lv.1-5** | [`erotic_intensity_standards.md`](erotic_intensity_standards.md:1) [`prompts/erotic/`](prompts/erotic/__init__.py:1) | Lv.3をセーフティ上限とし、プラットフォーム規約抵触を自動回避 |
| **95点超え改善指示** | [`src/models/audit.py`](src/models/audit.py:160) | 監査結果から「95点越えへの具体的改善案」「未来の熱狂的読者レビュー」を生成 |
| **モデルティアルーティング** | [`src/services/model_router.py`](src/services/model_router.py:23) | 難易度・緊張値に応じて上位モデルを自動選択（コスト最適化） |
| **Style DNA / 文体継承** | [`prompts/templates/utility/style_dna_analysis_prompt.j2`](prompts/templates/utility/style_dna_analysis_prompt.j2:1) [`prompts/templates/utility/style_inheritance_notes.j2`](prompts/templates/utility/style_inheritance_notes.j2:1) | 系列内の文体ブレを抑制 |
| **描写密度制御** | [`prompts/templates/narrative/final_writing_prompt.j2`](prompts/templates/narrative/final_writing_prompt.j2:27) | Extreme/High/Low/標準の4段階でペーシングを制御 |
| **POV漏れ排除** | [`prompts/templates/narrative/final_writing_prompt.j2`](prompts/templates/narrative/final_writing_prompt.j2:21) | 視点人物が知り得ない情報の地の文記述を禁止 |

### 1.3 制約・懸念点（現実可能性を下げる要素）
1. **Gemini API依存**：[`src/llm/gemini_client.py`](src/llm/gemini_client.py:1) と [`src/llm/model_router.py`](src/llm/model_router.py:1) で抽象化済みだが、実質Gemini前提。コスト・レート・規約変動リスク。
2. **[`src/engine_service.py`](src/engine_service.py:30) の書籍管理はインメモリスタブ**（"後でDBに置き換える"コメント）。[`src/backend/`](src/backend/server.py:1) 側に本番DB実装があるため二重構造で一貫性に注意。
3. **長編一気書きはリスク**：メモリ・整合性・トークン上限（[`src/core/context_window_manager.py`](src/core/context_window_manager.py:121) 95%警告）の壁。エピソード粒度運用が前提。
4. **「完成原稿の仕上げ」は人間必須**：監査は強力だが、Web小説上位常連レベルの「一癖ある文体」「作者の熱量」はAI単独では再現困難。
5. **著作権/プラットフォーム規約**：AI生成物の掲載可否は各プラットフォームで流動的。カクヨム/なろうのAI表記の要否確認が必須。

---

## 2. 現実可能性の検証結論

**「半自動＋人間仕上げ」のハイブリッド運用で、週1話×3シリーズを同時並行で生産する体制を組めば、**Web小説の**ランキング上位（ジャンル別上位／累計上位を含む）を狙える現実力は中〜高**と評価する。根拠：

1. 本エンジンは「お話作り」ではなく「読者をクリックさせる構造の工学的再現」に最適化されている（フック・カタルシス・テンション曲線・官能セーフティ）。这正是 Web小説ランキング上位が要求する最もノイズの多い非創造的工程を自動化する対象。
2. 既存の監査エージェント＋95点改善指示は、人間編集者のレビューループの代替ではなく**前工程の足切り/補強**として機能し、人間の仕上げ時間を大幅短縮できる。
3. 単一モデル依存とコスト、長編一気書きの整合性リスクは運用設計で緩和可能（エピソード粒度・マルチプロバイダ・キャッシュ）。

逆に「AI単独ゼロ人間で商業出版掲載レベルの単行本原稿」を即 Getter することは現実的ではない。よって提案は「出力作品をいかに商業に近づけるか」を運用・プロンプト・出力の3レイヤで構成する。

---

## 3. 3提案

### 提案A：ランキング上位量産パイプライン「ざまぁ周回ファーム」運用 --- P0
**目的**：最も確率の高いWeb小説上位ジャンル（ざまぁ／なろう系／復讐譚）を、本エンジンの核心機構である**ストレス→強制カタルシス**曲線に最適化して量産する。

**構成**
1. **企画テンプレ固定化**：[`prompts/templates/narrative/`](prompts/templates/narrative/bible_creation_prompt.j2:1) に「ざまぁ4章型（屈辱蓄積→触発→無双開始→完全制圧）」のBible雛形を常時注入。
2. **テンション曲線の最適化**：[`src/backend/tension_curve_config.py`](src/backend/tension_curve_config.py:1) の `EMOTIONAL_CURVES` に「ざまぁ特化スパイク曲線」を追加し、[`src/models/planning_config.py`](src/models/planning_config.py:17) の `tension_threshold` を80前後に下げてカタルシス頻度を上げる。
3. **1日3話並列生成→1話採用**：監査エージェント（[`prompts/templates/audit/`](prompts/templates/audit/hegemony_audit_prompt.j2:1)）でスコア順に並べ、上位1話を人間が30分仕上げ。ダイジェスト/あらすじも [`prompts/templates/utility/title_generation_prompt.j2`](prompts/templates/utility/title_generation_prompt.j2:1)＋[`marketing_pack_prompt.j2`](prompts/templates/utility/marketing_pack_prompt.j2:1) で自動生成。
4. **熱量スケール**：週1シリーズ×8話、3週で1クール完結型を3シリーズ並行（月産24話）。

**現実可能性評価**：**高**。エンジンがその用途そのままに最適化されており、追加実装はテンション曲線1プロファイル・Bibleテンプレ1点で完結する最小工数。最大リスクは「同ジャンル飽和」で、変曲点はSaaS提案3（納品フォーマッター）ではなく作品側の'image差別化'。

**成功指標**：30日以内にカクヨムで「ジャンル別日間上位50圏内」を1作以上達成、3ヶ月でシリーズ完結型1作を累計10万文字超で完結。

---

### 提案B：人気既存作品の「文体リスペル」＋連載ブレ防止でプロ作家の分身化 --- P1
**目的**：既に実績のあるWeb小説家のシリーズ継続、又はゴースト的補助として、**Style DNA〔[`prompts/templates/utility/style_dna_analysis_prompt.j2`](prompts/templates/utility/style_dna_analysis_prompt.j2:1)〕実装を最後まで活性化**し、読者が作風の違いを違和感を覚えないレベルの文体継承を実現する。

**構成**
1. **少サンプル学習ワークフロー**：既存3-5話分から StyleDNA（文長/語彙多様性/終助詞分布/視点距離/比喩頻度〔[`src/agents/erotic_integrity.py`](src/agents/erotic_integrity.py:69) の汎用化〕）を抽出し、[`prompts/templates/utility/style_inheritance_notes.j2`](prompts/templates/utility/style_inheritance_notes.j2:1) で各話に注入。
2. **文体ブレリアルタイム検知**：監査エージェントに"Style Drift Auditor"を追加し、乖離スコアが閾値超で自動リライト依頼。
3. **メタ人間レビューループ**：提出稿は必ず1人プロ作家が読み、Style DNA特徴量差分ログを元に修正→学習データ戻し。

**現実可能性評価**：**中**。Style DNA の土台は既存するが、文体指紋の抽出精度とリライト品質が連載ブレ完全防止には不足。**プロ作家1名と1ヶ月共同で"個人文体DNA"を学習させる PoC**が前提。出版契約ノウハウ/報酬合意も必要。リスク高いが単価大きい。

**成功指標**：依頼作家3名と半年で「総合不可分」連載を各12話納入、作家満足度	Close-Outで4/5+ ハンドリング時間50%削減。

---

### 提案C：マルチプラットフォーム同時展開「同一プロット多出力」のためのフォーマッタ＋規約守護レイヤ --- P1
**目的**：1企画からカクヨム/なろう/KDP/ノベルバ/Kindleを同時に入市するため、 [`COMMERCIALIZATION_PROPOSALS.md`](COMMERCIALIZATION_PROPOSALS.md:63) 提案3を**作品輸出側で実装**する。各プラットフォームの入稿仕様・規約抵触を自動で回避する「規約守護レイヤ」を上書きする。

**構成**
1. **プラットフォーム規約DB**：[`config/`](config/README.md:1) に `platform_rules.yaml` を置き、カクヨム/なろう等の「禁止表現」「AI表記要否」「ルビ書式」「1話文字数上限」をメンテ。
2. **フォーマッタプラグイン**：[`formatters/`](formatters/__init__.py:1) 配下に各プラットフォーム向け Adapter を実装。生成直後にテキストを変換＋規約スキャン。
3. **官能Lv自動調整**：[`erotic_intensity_standards.md`](erotic_intensity_standards.md:1) の Lv.3上限を、各プラットフォームの規約（なろうはより厳、ノベルバは緩、等）で動的に下げる。[`prompts/erotic/safety_manifest.py`](prompts/erotic/safety_manifest.py:1) と連動。
4. **メタデータ・あらすじ一括生成**： [`prompts/templates/utility/marketing_pack_prompt.j2`](prompts/templates/utility/marketing_pack_prompt.j2:1) でキャッチ/あらすじ/タグを一括出力。

**現実可能性評価**：**高**。最も純増実装量が少なく、既存の監査/官能マニフェスト基盤に乗るだけ。提案Aと**併用すると作品到達と投稿手間の両面が解消し、相乗効果が最大**になる。リスクはプラットフォーム規約の頻繁な変更なので、YAML一元管理＋CIで規約のデグレを検知する仕組みを継続稼働させること。

**成功指標**：1企画・3プラットフォーム同時連載が5分以内に投稿可能。3ヶ月で5作品×3プラットフォーム=15配信化、うち1作が各プラットフォームで規約抵触ストライク0を維持。

---

## 4. 推奨ロードマップ（90日）

| 週 | 提案A（ざまぁ周回） | 提案B（Style DNA PoC） | 提案C（フォーマッタ） |
|---|---|---|---|
| W1-2 | テンション曲線プロファイル追加＋Bible雛型 | プロ作家1名と提携・既存話収集 | platform_rules.yaml定義 |
| W3-4 | 1シリーズ×8話のパイロット | Style DNA 抽出 PoC | カクヨム Adapter 実装 |
| W5-8 | 3シリーズ並行＋監査スコア土砂降見化 | 文体ブレ検知 Auditor 追加 | なろう/KDP Adapter 追加 |
| W9-12 | ランキング実績データ蓄積 | 修正→学習戻しループ | 規約CI追加＋15配信化 |

**三提案の優先度**: A（即時収益接近）→ C（アンチクリフト・コスト削減）→ B（長期単価向上）。

---

## 5. 結論

本プロジェクトは**「Web小説ランキング上位の構造を工学的に再現する」という明確な意図で設計されており、その核心機構（ストレス/カタルシス曲線・フック戦略・官能セーフティ・多次元監査）はすでに商用実用域にある**。ただし「AIがゼロ人間で商業出版レベルを一手に書く」運用では、文体の熱量・一貫性・規約リスクで必ず足をすくう。

採るべき戦略は:
```text
[ざまぁ周回]生成量×監査スコア足切り → 人間30分仕上げ → [フォーマッタ]自動納品 → [Style DNA]作家スケール化
```
提案AとCの併用で月産24話のラインを3ヶ月以内に立ち上げ、提案Bでプロ作家向けB2B化に段階移行する。これが「このツールを使って商用化作品・Web小説ランキング上位作品を生み出す」ための最も現実的な3段構えである。
