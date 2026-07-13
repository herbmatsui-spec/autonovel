# 1-36ステップ実装計画書：商用化作品輸出パイプライン

**作成日**: 2026-07-09
**目的**: 低性能LLMでも確実に実装可能な粒度で、商用化パイプラインを構築する。

---

## Phase 1: 基盤完成 & 統合テスト（ステップ1-3）

### ステップ1: Phase1完了チェックリスト作成
- **対象ファイル**: `docs/phase1_done.md`（新規）
- **アクション**: ステップ1-11の完了検証コマンド一覧をMarkdownで記録。
- **検証**: 各コマンドがすべて成功することを確認。

### ステップ2: マーケティング出力ヘルパ実装
- **対象ファイル**: `src/services/marketing_service.py`
- **アクション**: `build_pack(series_title, episode_summary)` 関数を実装。タイトル/あらすじ/タグ生成。
- **検証**: モックLLMでMarkdown文字列が返るpytest1件。

### ステップ3: ざまぁ周回エンドツーエンド スモークテスト
- **対象ファイル**: `tests/integration/test_zamaa_loop_smoke.py`（新規）
- **アクション**: 「企画→プロット→執筆→監査→足切り→マーケ出力」の完走を検証。
- **検証**: `pytest tests/integration/test_zamaa_loop_smoke.py -q` PASS。

---

## Phase 2: マルチプラットフォーム規約守護（ステップ4-12）

### ステップ4: `platform_rules.yaml` 雛型作成
- **対象ファイル**: `config/platform_rules.yaml`（新規）
- **アクション**: `kakuyomu`, `narou`, `novelba`, `kdp` の基本設定（禁止語、最大文字数等）を定義。
- **検証**: YAML構文チェック。

### ステップ5: 規約ローダ関数
- **対象ファイル**: `config/data_loader.py`
- **アクション**: `load_platform_rules(platform: str)` を追加。
- **検証**: 正しい設定値が取得できるpytest1件。

### ステップ6: 禁止表現スキャナ
- **対象ファイル**: `formatters/erotic_censor.py`
- **アクション**: `scan_forbidden(text, forbidden_words)` を実装。マッチした語と位置を返す。
- **検証**: キーワード検出のpytest1件。

### ステップ7: 禁止表現マスキング関数
- **対象ファイル**: `formatters/erotic_censor.py`
- **アクション**: `mask_forbidden(text, forbidden_words)` を実装。伏せ字化を行う。
- **検証**: 伏せ字変換のpytest1件。

### ステップ8: なろうAdapter 新規
- **対象ファイル**: `formatters/narou.py`（新規）
- **アクション**: `format_narou(chapter_text)` 実装（改行正規化、空行抑制）。
- **検証**: フォーマット変換のpytest1件。

### ステップ9: ノベルバAdapter 新規
- **対象ファイル**: `formatters/novelba.py`（新規）
- **アクション**: `format_novelba(chapter_text)` 実装（`<br>`置換）。
- **検証**: フォーマット変換のpytest1件。

### ステップ10: KDP（EPUB）最小Adapter
- **対象ファイル**: `formatters/kdp.py`（新規）
- **アクション**: `chapter_to_epub_html(chapter_text)` 実装（`<p>`タグ化）。
- **検証**: HTML変換のpytest1件。

### ステップ11: Adapter レジストリ
- **対象ファイル**: `formatters/__init__.py`
- **アクション**: `FORMATTERS` 辞書を定義し、各Adapterを公開。
- **検証**: `len(FORMATTERS) == 4` の確認。

### ステップ12: プラットフォーム別 官能Lv自動引き下げヘルパ
- **対象ファイル**: `config/erotic_platform_presets.py`
- **アクション**: `max_level_for(platform)` を実装。
- **検証**: プラットフォームごとのレベル値検証。

---

## Phase 3: 規約CI化・A/B出力（ステップ13-18）

### ステップ13: 規約YAML バリデータ
- **対象ファイル**: `config/validator.py`
- **アクション**: `validate_platform_rules(path)` を実装。必須キーチェック。
- **検証**: 正常/異常YAMLのpytest2件。

### ステップ14: 規約デグレ検知テスト
- **対象ファイル**: `tests/test_platform_rules_drift.py`
- **アクション**: CI用スモークテストとしてバリデータを実行。
- **検証**: pytest PASS。

### ステップ15: GitHub Actions workflow 追加
- **対象ファイル**: `.github/workflows/platform_rules.yml`（新規）
- **アクション**: `test_platform_rules_drift.py` を実行するワークフロー定義。
- **検証**: YAML構文チェック。

### ステップ16: A/Bタイトル生成ヘルパ
- **対象ファイル**: `src/services/marketing_service.py`
- **アクション**: `generate_ab_titles(seeds, n=2)` を実装。
- **検証**: 2案返却のpytest1件。

### ステップ17: 投稿予約CSV出力ヘルパ
- **対象ファイル**: `streamlit_app/utils/schedule_csv.py`（新規）
- **アクション**: `write_schedule(rows, path)` を実装。
- **検証**: CSV書き出しのpytest1件。

### ステップ18: 1企画→3プラットフォーム同時出力
- **対象ファイル**: `src/services/export_pipeline.py`（新規）
- **アクション**: `export_multi(chapter_text, platforms)` を実装。
- **検証**: 複数プラットフォーム出力のpytest1件。

---

## Phase 4: Style DNA 抽出（ステップ19-27）

### ステップ19: `StyleDNA` モデル新規
- **対象ファイル**: `src/models/style_dna.py`（新規）
- **アクション**: 文長、語彙多様性、終助詞、比喩密度のフィールドを持つPydanticモデルを定義。
- **検証**: インスタンス化の確認。

### ステップ20: 文長平均 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`（新規）
- **アクション**: `avg_sentence_length(text)` を実装。
- **検証**: 既知文字列での検証pytest。

### ステップ21: 語彙多様性 (TTR) 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `vocabulary_richness(text)` を実装。
- **検証**: 0 < 値 <= 1 の検証pytest。

### ステップ22: 終助詞分布 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `ending_particles(text)` を実装。
- **検証**: 頻度辞書の返却確認pytest。

### ステップ23: 比喩密度 関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `metaphor_density(text)` を実装。
- **検証**: 出現率計算のpytest。

### ステップ24: 3-5話からのDNA統合ハイパー関数
- **対象ファイル**: `src/services/style_dna_extractor.py`
- **アクション**: `extract_dna(samples)` を実装。
- **検証**: 平均化処理のpytest。

### ステップ25: DNA→プロンプトノート 変換関数
- **対象ファイル**: `prompts/utils.py`
- **アクション**: `dna_to_notes(dna)` を実装。
- **検証**: 指示文への変換確認pytest。

### ステップ26: `style_inheritance_notes.j2` への注入
- **対象ファイル**: `prompts/templates/utility/style_inheritance_notes.j2`
- **アクション**: `{{ style_notes }}` 変数を追加。
- **検証**: レンダリング確認。

### ステップ27: 文体ブレ検知 Auditor 雛型
- **対象ファイル**: `prompts/templates/audit/style_drift_audit_prompt.j2`（新規）
- **アクション**: 文体乖離を指摘させるプロンプトを作成。
- **検証**: Jinja構文チェック。

---

## Phase 5: 統合パイプライン構築（ステップ28-33）

### ステップ28: 統合パイプライン定義
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`（新規）
- **アクション**: `CommercialPipeline.run` のシグネチャ定義（スタブ）。
- **検証**: import確認。

### ステップ29: ざまぁ企画ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_plan` の実装（Bible生成）。
- **検証**: 戻り値確認pytest。

### ステップ30: 3話並列執筆ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_batch_write` の実装。
- **検証**: 3章分生成のpytest。

### ステップ31: 監査足切りステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_audit_and_select` の実装（最高スコア選択）。
- **検証**: 1章選択のpytest。

### ステップ32: マルチプラットフォーム出力ステップ
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: `_step_export_multi` の実装。
- **検証**: 複数形式出力のpytest。

### ステップ33: 統合パイプラインrun()結合
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**: 各ステップを `run()` 内で順次呼び出し。
- **検証**: 全工程完走のpytest。

---

## Phase 6: UI・運用・観察（ステップ34-36）

### ステップ34: Streamlit「商用化パイプライン」実行ボタン
- **対象ファイル**: `streamlit_app/pages/easy_mode.py`
- **アクション**: `CommercialPipeline.run` を呼び出すボタンを実装。
- **検証**: 人目視。

### ステップ35: APIエンドポイント `/commercial/run`
- **対象ファイル**: `src/backend/server.py`
- **アクション**: `POST /commercial/run` ルートを追加。
- **検証**: HTTP 200 OKの確認。

### ステップ36: 完了宣言・リリースノート
- **対象ファイル**: `RELEASE_NOTES_COMMERCIAL_PIPELINE.md`（新規）
- **アクション**: 成果物と検証結果を記録。
- **検証**: 人目視。
