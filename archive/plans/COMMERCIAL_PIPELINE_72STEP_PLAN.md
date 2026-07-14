# 72ステップ実装計画書：商用化作品輸出パイプライン（提案A/B/C具現化）

**作成日**: 2026-07-09
**対象プロジェクト**: cR15（覇権小説自動生成エンジン）
**前提ドキュメント**: [`COMMERCIALIZATION_FEASIBILITY.md`](COMMERCIALIZATION_FEASIBILITY.md:1) の提案A/B/Cを具現化
**目的**: 低性能LLM（推論能力・コンテキスト制限が小さい環境）でも、1ステップ＝1関数／1ファイル編集レベルで確実に実装できるよう、72個の小ステップに分割する。

---

## 設計原則（低性能LLM対応）

1. **1ステップ＝1PR／1コミット相当**：1ファイル・1関数・1プロンプト追加のみ。複数ファイル同時編集禁止。
2. **依存方向は常にPhase内→次Phase**：後続ステップは前ステップの完了を前提とし、戻り参照しない。
3. **各ステップは検証可能**：pytest1件／`python -c`1行／目視確認のいずれかで必ず確認できる。
4. **巨大生成禁止**：本ドキュメントはロードマップ。各ステップの実装指示は短文（5-20行の関数）に留め、長大なコードを一度に書かせない。
5. **ドラフト→監査→修正の3段固定**: 提案Aの本質である"生成→足切り→仕上げ"をステップ粒度でも再現する。

---

## Phase 1: 提案A基盤 — ざまぁ周回プロファイル（ステップ1-12）

### ステップ1: ざまぁ4章型Bible雛型の作成
- **対象ファイル**: `prompts/templates/narrative/bible_zamaa_template.j2`（新規）
- **アクション**: 4章型（屈辱蓄積→触反→無双開始→完全制圧）の穴埋め雛型を作成。1ファイル40行以内。
- **検証**: `python -c "from jinja2 import Environment, FileSystemLoader; Environment(loader=FileSystemLoader('prompts/templates/narrative')).get_template('bible_zamaa_template.j2')"` が例外なく通ること。

### ステップ2: ざまぁ曲線 `zamaa_heavy` 流入の単体確認
- **対象ファイル**: `src/backend/tension_curve_config.py`（既存 `zamaa_heavy` を確認のみ）
- **アクション**: 既存曲線を参照する関数 `assert_zamaa_curve_exists()` を `tests/unit/test_zamaa_curve.py` に1関数追加。
- **検証**: `pytest tests/unit/test_zamaa_curve.py -q` が PASS。

### ステップ3: ざまぁ用 `engine_key` 定数追加
- **対象ファイル**: `src/models/planning_config.py`
- **アクション**: `engine_key` の選択肢として `"zamaa"` を許容するだけのdocstring/Literal追記。ロジック変更なし。
- **検証**: `python -c "from src.models.planning_config import PlanningConfig; PlanningConfig(engine_key='zamaa').engine_key == 'zamaa'"`。

### ステップ4: `select_tension_curve` の分岐追加
- **対象ファイル**: `src/backend/tension_utils.py`
- **アクション**: `genre` 又は `story_type` が `"zamaa"` のとき曲線名 `"zamaa_heavy"` を返す1分岐追加。
- **検証**: `pytest tests/test_tension_utils.py -q`（既存テスト）が全部PASSのまま、新規1件追加で通る。

### ステップ5: ざまぁ向け `tension_threshold` 初期値
- **対象ファイル**: `src/models/planning_config.py`
- **アクション**: `tension_threshold` のデフォルトを `85` のまま据え置き、`engine_key == "zamaa"` のとき `80` に補正するpost_initを1件追加。
- **検証**: `PlanningConfig(engine_key='zamaa').tension_threshold == 80`。

### ステップ6: ざまぁ用プロンプト切替ヘルパ
- **対象ファイル**: `prompts/manager.py`
- **アクション**: `build_bible_prompt(genre, ..., engine_key)` が `engine_key=='zamaa'` のとき `bible_zamaa_template.j2` を選ぶ分岐1件追加。
- **検証**: 単体テスト1件追加し、戻り値に `屈辱` 文字列が含まれることを assert。

### ステップ7: 1日3話並列用 配列入力スキーマ
- **対象ファイル**: `src/models/api_schemas.py`
- **アクション**: `BatchEpisodeRequest`（`series_id, ep_nums: List[int]` のみ）を1モデル追加。
- **検証**: `from src.models.api_schemas import BatchEpisodeRequest; BatchEpisodeRequest(series_id=1, ep_nums=[1,2,3])`。

### ステップ8: 監査スコア足切りヘルパ
- **対象ファイル**: `src/services/writing_services.py` 直下に `select_best_episode(chapters: List[dict], key='audit_score')` 関数追加。10行以内。
- **検証**: テストデータ3件で最高スコアを返すpytest1件。

### ステップ9: 人間仕上げ用 差分出力フォーマッタ
- **対象ファイル**: `streamlit_app/utils/diff_export.py`（新規）
- **アクション**: 生成稿＋監査メモ＋改善案をMarkdown1ファイルに出力する関数 `export_for_human_polish(chapter)` を追加。30行以内。
- **検証**: サンプル1章でMarkdown文字列が返るpytest1件。

### ステップ10: マーケティング出力（タイトル/あらすじ/タグ）呼出ヘルパ
- **対象ファイル**: `src/services/marketing_service.py`（既存確認後、未なら新規ファイル）。`build_pack(series_title, episode_summary)` の1関数。
- **検証**: モックLLMでMarkdown文字列が返るpytest1件。

### ステップ11: ざまぁ周回エンドツーエンド スモーク
- **対象ファイル**: `tests/integration/test_zamaa_loop_smoke.py`（新規）
- **アクション**: モックLLMで「企画→プロット→執筆→監査→スコア足切り→マーケ出力」が例外なく完走することを検証。
- **検証**: `pytest tests/integration/test_zamaa_loop_smoke.py -q` PASS。

### ステップ12: Phase1完了チェックリスト
- **対象ファイル**: `docs/phase1_done.md`（新規）
- **アクション**: ステップ1-11の完了検証コマンド一覧をMarkdownで記録。コード変更なし。
- **検証**: 各コマンドが `awk` で抽出してすべて0（成功）終了することを人間が確認。

---

## Phase 2: 提案C基盤 — マルチプラットフォーム規約守護（ステップ13-24）

### ステップ13: `platform_rules.yaml` 雛型作成
- **対象ファイル**: `config/platform_rules.yaml`（新規）
- **アクション**: `kakuyomu` `narou` `novelba` `kdp` の4キーに `forbidden_words: []`, `max_chars_per_episode: null`, `ai_label_required: false` の3フィールドのみ定義。
- **検証**: `python -c "import yaml; yaml.safe_load(open('config/platform_rules.yaml'))"`。

### ステップ14: 規約ローダ関数
- **対象ファイル**: `config/data_loader.py`（既存）に `load_platform_rules(platform: str)` を追加。15行。
- **検証**: `load_platform_rules('kakuyomu')['forbidden_words']` がlist型のpytest1件。

### ステップ15: 禁止表現スキャナ（既存censor拡張）
- **対象ファイル**: `formatters/erotic_censor.py`（既存確認）
- **アクション**: `scan_forbidden(text, forbidden_words)` 関数を追加。15行。正規表現はコンパイル済みのキャッシュを返す。マッチした語と位置をリストで返す。
- **検証**: テスト1件でキーワード検出されること。

### ステップ16: 禁止表現マスキング関数
- **対象ファイル**: `formatters/erotic_censor.py`
- **アクション**: `mask_forbidden(text, forbidden_words)` 追加。ヒット語を伏せ字（`*`）化。10行。
- **検証**: pytest1件で「××」が伏字になること。

### ステップ17: カクヨムAdapter 既存の棚卸
- **対象ファイル**: `formatters/kakuyomu.py`（既存）
- **アクション**: 現状の公開関数一覧を `docs/formatters_kakuyomu.md` に記録。**コード編集なし**。
- **検証**: ファイルが存在し、3関数以上が記載されていることを目視。

### ステップ18: なろうAdapter 新規
- **対象ファイル**: `formatters/narou.py`（新規）
- **アクション**: `format_narou(chapter_text)` の1関数。改行正規化＋3行空行抑制のみ。20行。
- **検証**: pytest1件で改行が正規化されること。

### ステップ19: ノベルバAdapter 新規
- **対象ファイル**: `formatters/novelba.py`（新規）
- **アクション**: `format_novelba(chapter_text)` の1関数。改行→`<br>`置換のみ。12行。
- **検証**: pytest1件で `<br>` が挿入されること。

### ステップ20: KDP（EPUB）最小Adapter
- **対象ファイル**: `formatters/kdp.py`（新規）
- **アクション**: `chapter_to_epub_html(chapter_text)` の1関数。`<p>` タグ化のみ。15行。
- **検証**: pytest1件で `<p>` が付与されること。本格EPUBパッキングはPhase外。

### ステップ21: Adapter レジストリ
- **対象ファイル**: `formatters/__init__.py`
- **アクション**: `FORMATTERS = {'kakuyomu': ..., 'narou': ..., 'novelba': ..., 'kdp': ...}` のdictを公開。
- **検証**: `from formatters import FORMATTERS; len(FORMATTERS) == 4`。

### ステップ22: プラットフォーム別 官能Lv自動引き下げヘルパ
- **対象ファイル**: `config/erotic_platform_presets.py`（既存確認）
- **アクション**: `max_level_for(platform)` を追加し、`narou` → `2`、`kakuyomu` → `3`、`novelba` → `3`、`kdp` → `2` を返す。10行。
- **検証**: pytest4件（1プラットフォーム1件）。

### ステップ23: 生成直後フォーマット→規約スキャン パイプ関数
- **対象ファイル**: `src/services/export_pipeline.py`（新規）
- **アクション**: `export(chapter_text, platform)` の1関数。`FORMATTERS[platform]`→`scan_forbidden`→`mask_forbidden`→`max_level_for`に基づき警告を付与してdictを返す。25行。
- **検証**: モックテキストで `forbidden_hits` フィールドが空になることのpytest1件。

### ステップ24: Phase2 E2E スモーク
- **対象ファイル**: `tests/integration/test_export_pipeline_smoke.py`
- **アクション**: 4プラットフォームに対し `export(sample_text, p)` が例外なく通ることを1テストで検証。
- **検証**: `pytest tests/integration/test_export_pipeline_smoke.py -q` PASS。

---

## Phase 3: 提案C拡張 — 規約CI化・A/B出力（ステップ25-33）

### ステップ25: 規約YAML バリデータ
- **対象ファイル**: `config/validator.py` に `validate_platform_rules(path)` 追加。必須キー3種の存在確認。15行。
- **検証**: 不正YAMLで例外、正規YAMLでTrueを返すpytest2件。

### ステップ26: 規約デグレ検知 pytest1件
- **対象ファイル**: `tests/test_platform_rules_drift.py`
- **アクション**: `validate_platform_rules('config/platform_rules.yaml')` をCI smokeとして常時実行するテストを1件。
- **検証**: `pytest tests/test_platform_rules_drift.py -q` PASS。

### ステップ27: GitHub Actions workflow 追加
- **対象ファイル**: `.github/workflows/platform_rules.yml`（新規）
- **アクション**: `pytest tests/test_platform_rules_drift.py` を走らせる最小workflow。20行。
- **検証**: YAML構文チェックのみ（`python -c "import yaml; yaml.safe_load(...)"`）。

### ステップ28: A/Bマーケティング出力 プロンプト調整確認
- **対象ファイル**: `prompts/templates/utility/marketing_ab_test_prompt.j2`（既存確認）
- **アクション**: 既存テンプレの変数名をREADME形式で1件コメント追記。**コード編集なし**。
- **検証**: ファイル上部コメント行が追加されていることを目視。

### ステップ29: A/Bタイトル生成ヘルパ
- **対象ファイル**: `src/services/marketing_service.py`
- **アクション**: `generate_ab_titles(seeds: List[str], n=2)` を追加。#!/ モックLLMで2案返す。10行。
- **検証**: 戻り値`len == 2`のpytest1件。

### ステップ30: 投稿予約CSV出力ヘルパ
- **対象ファイル**: `streamlit_app/utils/schedule_csv.py`（新規）
- **アクション**: `(platform, ep_num, scheduled_at, title, body_path)` をCSV出力する `write_schedule(rows, path)` 。15行。
- **検証**: 一時ファイルに3行書き込まれるpytest1件。

### ステップ31: 1企画→3プラットフォーム同時出力
- **対象ファイル**: `src/services/export_pipeline.py`
- **アクション**: `export_multi(chapter_text, platforms: List[str])` 追加。`{platform: export(...)}` を返す。10行。
- **検証**: 3プラットフォームでdict長3のpytest1件。

### ステップ32: フォーマッタ差分ログ
- **対象ファイル**: `streamlit_app/utils/diff_export.py`（既存）に `format_diff_log(before, after)` 追加。15行。Unified diff生成。
- **検証**: pytest1件で `@@` 文字列を含むことを確認。

### ステップ33: Phase3完了チェックリスト
- **対象ファイル**: `docs/phase3_done.md`
- **アクション**: コード変更なし、検証コマンド一覧記録。
- **検証**: 人目視。

---

## Phase 4: 提案B基盤 — Style DNA 抽出（ステップ34-48）

### ステップ34: `StyleDNA` モデル新規
- **対象ファイル**: `src/models/style_dna.py`（新規）
- **アクション**: `StyleDNA` Pydanticモデル。フィールドは `avg_sentence_length: float`, `vocab_richness: float`, `ending_particles: Dict[str,int]`, `metaphor_density: float`, `source_works: List[str]`, `confidence: float` の6個のみ。
- **検証**: `StyleDNA(avg_sentence_length=15.0, vocab_richness=0.5, ending_particles={'ね':1}, metaphor_density=0.1, source_works=[], confidence=0.0)` が例外なく構築できること。

### ステップ35: 文長平均 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`（新規）
- **アクション**: `avg_sentence_length(text: str) -> float` 追加。`。` で分割。10行。
- **検証**: 既知文字列で既知長を返すpytest1件。

### ステップ36: 語彙多様性 (TTR) 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `vocabulary_richness(text) -> float` （type/token ratio）。15行。MeCab不使用、簡易空白/文字ベース。
- **検証**: GD谐笑话5件の中で0<値<=1。

### ステップ37: 終助詞分布 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `ending_particles(text) -> Dict[str,int]`。`。` 直前1-2文字を素朴にカウント。15行。
- **検証**: `{"ね": N, "よ": M, ...}` 形式のdictを返すpytest1件。

### ステップ38: 比喩密度 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `metaphor_density(text) -> float`。`のように|まるで| ごとく` の出現率。10行。
- **検証**: pytest1件。

### ステップ39: 3-5話からのDNA統合ハイパー関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `extract_dna(samples: List[str]) -> StyleDNA`。ステップ35-38を呼び出して平均化。15行。
- **検証**: 3サンプルで `confidence == 1/(1+len(samples))` になるpytest1件。

### ステップ40: DNA→プロンプトノート 変換関数
- **対象ファイル**: `prompts/utils.py` に `dna_to_notes(dna: StyleDNA) -> str`。12行。
- **検証**: pytest1件で文字列に `avg_sentence_length` が含まれる。

### ステップ41: `style_inheritance_notes.j2` への注入
- **対象ファイル**: `prompts/templates/utility/style_inheritance_notes.j2`（既存）
- **アクション**: `{{ style_notes }}` 変数1個を末尾に追加。5行編集。
- **検証**: `Environment().from_string(...).render(style_notes='X')` が文字列Xを含む。

### ステップ42: 文体ブレ検知 Auditor 雛型
- **対象ファイル**: `prompts/templates/audit/style_drift_audit_prompt.j2`（新規）
- **アクション**: DNA参照稿と新生成稿の乖離を指摘させるプロンプト。20行以内。
- **検証**: Jinja構文エラーがないことの `python -c`。

### ステップ43: StyleDriftAuditor クラス
- **対象ファイル**: `src/agents/style_drift.py`（新規）
- **アクション**: `StyleDriftAuditor.score(reference_dna: StyleDNA, new_text: str) -> float`。参照DNAと新テキストDNAの差を0-100で返す。20行。
- **検証**: pytest1件で完全一致0、極端に違えば高得点。

### ステップ44: 乖離スコア閾値定数
- **対象ファイル**: `src/models/planning_config.py`
- **アクション**: `style_drift_threshold: float = 25.0` を1行追加。
- **検証**: `PlanningConfig().style_drift_threshold == 25.0`。

### ステップ45: 自動リライト依頼キュー
- **対象ファイル**: `src/services/writing_services.py`
- **アクション**: `request_rewrite_if_drift(chapter, dna, threshold)` 関数。乖離超時に `{"rewrite": True, "reason": ...}` 返す。15行。
- **検証**: 閾値超で `True`、未超で `False` のpytest2件。

### ステップ46: ヒューマンPDF出力（学習戻しログ）
- **対象ファイル**: `streamlit_app/utils/diff_export.py` に `export_style_log(dna, drift_score, chapter)`。20行。
- **検証**: サンプル1件でMarkdownが返るpytest1件。

### ステップ47: Phase4 E2E スモーク
- **対象ファイル**: `tests/integration/test_style_dna_loop_smoke.py`
- **アクション**: 3サンプル→DNA抽出→新稿生成→乖離スコア→リライト要求が例外なく通ること。
- **検証**: pytest PASS。

### ステップ48: Phase4完了チェックリスト
- **対象ファイル**: `docs/phase4_done.md`
- **アクション**: ステップ34-47の検証コマンド一覧を記録。**コード変更なし**。

---

## Phase 5: 提案A+C+B 統合 — 統合ワークフロー（ステップ49-60）

### ステップ49: 統合パイプライン定義
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`（新規）
- **アクション**: `CommercialPipeline.run(series_config, samples, platforms)` のシグネチャのみ定義。中身は後続ステップで埋める。10行スタブ。
- **検証**: import できること。

### ステップ50: ざまぁ企画ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `run()` 内 `_step_plan(series_config)` を呼んでBible返す。10行。
- **検証**: モックLLMで `bible` キーが入るpytest1件。

### ステップ51: 3話並列執筆ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_batch_write(bible, [1,2,3])` を call。3章返す。15行。
- **検証**: 長さ3のリストが返るpytest1件。

### ステップ52: 監査足切りステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_audit_and_select(chapters)` で `select_best_episode`（ステップ8）を呼ぶ。10行。
- **検証**: 単一dictを返すpytest1件。

### ステップ53: 仕上げ用差分出力ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_export_for_human(chapter)` で `export_for_human_polish`（ステップ9）を呼ぶ。8行。
- **検証**: Markdown文字列のpytest1件。

### ステップ54: マーケ+A/B ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_marketing(chapter)` で `generate_ab_titles`（ステップ29）と `build_pack`（ステップ10）を呼ぶ。10行。
- **検証**: `{"titles": [...], "pack": "..."}` 形式のdictが返るpytest1件。

### ステップ55: Style DNA 学習ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_learn_style(samples)` で `extract_dna`（ステップ39）を呼ぶ。8行。
- **検証**: StyleDNAが返るpytest1件。

### ステップ56: 文体ブレ検知＋リライト要求ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_style_audit(chapter, dna)` で `StyleDriftAuditor.score` と `request_rewrite_if_drift`（ステップ45）を呼ぶ。10行。
- **検証**: `drift_score` と `rewrite_required` キーを含むpytest1件。

### ステップ57: マルチプラットフォーム出力ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_export_multi(chapter, platforms)` で `export_multi`（ステップ31）を呼ぶ。8行。
- **検証**: dict長が platform数と一致するpytest1件。

### ステップ58: 投稿予約CSVステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_schedule_csv(exports)` で `write_schedule`（ステップ30）を呼ぶ。8行。
- **検証**: CSVファイルが作成されるpytest1件。

### ステップ59: 統合パイプラインrun()結合
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `run()` 内で ステップ50-58 を順に呼ぶ。**新規関数10個のみ**、それ以上書かない。
- **検証**: `run()` をモックLLMで呼んで例外が起きないpytest1件。

### ステップ60: Phase5 E2E スモーク
- **対象ファイル**: `tests/integration/test_commercial_pipeline_smoke.py`
- **アクション**: run()を3プラットフォームで実行、戻り値が `{'bible':..., 'selected':..., 'exports': dict, 'schedule_csv': path}` を満たすことを確認。
- **検証**: pytest PASS。

---

## Phase 6: UI・運用・観察（ステップ61-66）

### ステップ61: Streamlit「ざまぁ周回」実行ボタン
- **対象ファイル**: `streamlit_app/pages/easy_mode.py`（既存又は新規）
- **アクション**: ボタン1つ→`CommercialPipeline.run(...)` を呼ぶ `st.button`。20行。
- **検証**: `streamlit run` でボタンが表示されることを人目視（ユニットテスト不要）。

### ステップ62: 仕上げ用DLリンク
- **対象ファイル**: `streamlit_app/pages/easy_mode.py`
- **アクション**: ステップ9の出力Markdownを `st.download_button` で出す。10行。
- **検証**: 人目視。

### ステップ63: 文体ブレ可視化
- **対象ファイル**: `streamlit_app/pages/easy_mode.py`
- **アクション**: `st.metric("文体乖離", value=drift_score)` 1行追加。
- **検証**: 人目視。

### ステップ64: APIエンドポイント `/commercial/run`
- **対象ファイル**: `src/backend/server.py`
- **アクション**: `POST /commercial/run` を1ルート追加。`CommercialPipeline.run` 呼び出し。15行。
- **検証**: `pytest` や curl で 200。 既存 `tests/integration/test_ui_backend_communication.py` に1件追加。

### ステップ65: ログ構造化フィールド追加
- **対象ファイル**: `config/logging_config.py`
- **アクション**: `extra_fields` に `series_id`, `platform`, `drift_score` を標準で埋め込む1行追加。
- **検証**: 既存 `tests/test_structured_logging.py` がPASSのまま。

### ステップ66: メトリクス出力（Counter）
- **対象ファイル**: `src/services/metrics.py`（新規又は既存）
- **アクション**: `increment_episode_generated()`, `increment_platform_export(platform)` の2関数。
- **検証**: pytest1件でカウントが増えること。

---

## Phase 7: テスト・品質ゲート・リリース（ステップ67-72）

### ステップ67: 品質ゲート閾値定義
- **対象ファイル**: `pytest.ini` に `--strict-markers` 等の既存設定確認のみ。**編集なし**。
- **検証**: `pytest --co -q` が error しない。

### ステップ68: カバレッジ最小target設定
- **対象ファイル**: `.coveragerc`（既存確認）又は `pyproject.toml`
- **アクション**: 新規ファイル `src/services/style_dna_extractor.py` と `commercial_pipeline.py` をカバレッジ対象に指定。2行。
- **検証**: `coverage report --include=...` が error しない。

### ステップ69: CI workflow 全体実行
- **対象ファイル**: `.github/workflows/test.yml`（既存又は新規）
- **アクション**: pytest 実行＋platform_rules drift チェック＋lint の3job構成。30行。
- **検証**: YAML構文チェック。

### ステップ70: 運用マニュアル（ざまぁ周回）
- **対象ファイル**: `docs/manual_zamaa_farm.md`（新規）
- **アクション**: 1シリーズ立ち上げ手順を5ステップで記述。**コード変更なし**。
- **検証**: 人目視。

### ステップ71: 運用マニュアル（フォーマッタ・Style DNA）
- **対象ファイル**: `docs/manual_export_style.md`（新規）
- **アクション**: 3プラットフォーム同時投稿手順と文体学習戻し手順。**コード変更なし**。
- **検証**: 人目視。

### ステップ72: 完了宣言・リリースノート
- **対象ファイル**: `RELEASE_NOTES_COMMERCIAL_PIPELINE.md`（新規）
- **アクション**: Phase1-6完了成果物一覧、検証コマンド一覧、既知制約（Gemini依存、長編一気書き不可、官能Lv.3上限）を簡潔に記述。**コード編集なし**。
- **検証**: 全Phase完了チェックリストが埋まっていることを最終確認。

---

## 依存関係サマリ

```
Phase1(A基盤:1-12) ──┐
                     ├─→ Phase5(統合:49-60) ─→ Phase6(UI:61-66) ─→ Phase7(品質:67-72)
Phase2(C基盤:13-24) ──┤
                     │
Phase3(C拡張:25-33) ─┘
Phase4(B基盤:34-48) ──┘
```

- Phase1, 2, 4 は互いに独立並列可能。
- Phase3はPhase2完了後のみ着手。
- Phase5はPhase1/2/3/4すべて完了後着手。
- Phase6, 7はPhase5完了後に着手。

各ステップは**1ファイル編集・1関数追加**に抑制済みのため、低性能LLMでも「該当ステップ番号→ファイル→関数の指示文」を1件渡すだけで確実に実装できる。
