# ナラティブ深化機能 実装計画（48ステップ）

## 概要
改善優先度1〜3の以下3機能を、**低性能LLM（推論能力の低いモデル）でも確実に実装できるよう、極めて小さなステップに分割**した詳細実装計画。

- **機能A**: 感情曲線の動的制御（序盤の絶望・中盤の溜めの自動調整）
- **機能B**: 敵役の多層化プロンプト（敵役に「彼らなりの正義」を付与する論理的対立構造）
- **機能C**: 伏線管理システムの強化（長期的な伏線の自動配置・回収管理）

## 設計思想（低性能LLM対応の方針）
1. **1ステップ＝1ファイル変更or1関数追加**を厳守し、 cognitive load を最小化する。
2. 既存のDBモデル（`Plot`, `Foreshadowing`, `Character.registry_data`等）を最大限活用し、新規テーブル追加を最小限に抑える。
3. LLMの推論に頼る部分は「プロンプトで構造化データを要求」し、Python側でバリデーション＆フォールバックする堅牢設計とする。
4. 各ステップは単体テスト可能な粒度とし、TDD（Red-Green-Refactor）を前提とする。

---

# 機能A: 感情曲線の動的制御（ステップ1〜16）

## 目標
プロット生成時に、書籍の進行度（現在のエピソード / 全エピソード）に基づき、 tension （緊張感）と frustration （フラストレーション=溜め）を動的に計算し、LLMのプロンプトに「目標tension値」として注入する。これによりLLMが「早すぎる逆転」を回避し、王道のカタルシス曲線を自動生成する。

### ステップ1: 目標tension曲線の定数定義ファイルの作成
- **ファイル**: `src/backend/tension_curve_config.py`（新規）
- **内容**: `EMOTIONAL_CURVES` dictを定義。"standard", "slow_burn", "rapid_accel"等の曲線テンプレートを、全話に対する割合（0.0〜1.0）をキー、目標tension（0-100）を値とする辞書で定義する。純粋なPython定数のみ。テスト不要。

### ステップ2: 曲線選択ロジックの関数追加
- **ファイル**: `src/backend/tension_curve_config.py`に追記
- **内容**: `select_curve(archetype_key: str) -> str`関数を追加。アーキタイプキーから適用する曲線名を返す単純な分岐。`STORY_ARCHETYPES`が"ざまぁ"なら"rapid_accel"、日常系なら"slow_burn"等。

### ステップ3: 現在進行度の計算関数の追加
- **ファイル**: `src/backend/tension_curve_config.py`に追記
- **内容**: `calc_progress_ratio(current_ep: int, target_eps: int) -> float`関数を追加。`min(1.0, current_ep / max(1, target_eps))`を返す。分母ゼロ回避。

### ステップ4: 目標tension値の取得関数の追加
- **ファイル**: `src/backend/tension_curve_config.py`に追記
- **内容**: `get_target_tension(current_ep: int, target_eps: int, archetype_key: str) -> int`を追加。ステップ2,3を組み合わせ、該当する曲線から現在の目標tensionを補間または四捨五入して返す。曲線にない値は隣接キーで補完。

### ステップ5: ステップ1〜4の単体テスト作成
- **ファイル**: `tests/test_tension_curve_config.py`（新規）
- **内容**: `calc_progress_ratio`のゼロ除算、`get_target_tension`の境界値（1話目、最終話）、未知アーキタイプ時のデフォルト挙動をテスト。

### ステップ6: DBモデルへ動的tension目標値カラムの追加（任意）
- **ファイル**: `alembic/versions/XXXX_add_target_tension.py`（新規マイグレーション）
- **内容**: `Plot`テーブルに`target_tension`（Integer, default=50, nullable=True）を追加。既存データへの影響なし。`alembic revision --autogenerate`で生成。

### ステップ7: PlotモデルのPydantic定義へ項目追加
- **ファイル**: `models/plot.py`の`PlotAnalytics`に`target_tension: int = Field(default=50)`を追記。
- **理由**: LLMが返す構造化データに目標値を含め、整合性をチェックできるようにする。

### ステップ8: プロンプトテンプレートへの注入箇所の特定
- **ファイル**: `src/backend/engine_prompts.py`の調査
- **作業**: プロット生成用システムプロンプト内のtension指定箇所（例: "tensionを50に設定"）を特定し、変数化可能か確認。該当行をメモ。

### ステップ9: プロンプトテンプレートの動的tension化
- **ファイル**: `src/backend/engine_prompts.py`
- **内容**: ステップ8で特定した箇所を `本話の目標tension: {target_tension} / 100 （感情曲線: {curve_name}）` のようなプレースホルダに置換。

### ステップ10: Engineへの目標tension取得処理の組み込み（設計）
- **ファイル**: `src/backend/engine_plot.py`（プロット生成エンジン）の該当メソッドを特定。
- **作業**: `generate_plot`系の非同期メソッドの引数・戻り値を確認し、`target_tension`を受け取れるようシグネチャを検討。

### ステップ11: Engineでの目標tension取得ロジック実装
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: プロット生成開始時に`get_target_tension`（ステップ4）を呼び出し、プロンプト用dictに`target_tension`を詰める処理を追加。

### ステップ12: 生成結果のtension値バリデーション
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: LLM返却後、`PlotAnalytics.tension`と`target_tension`の誤差が±20以内か検証。逸脱時は`lite_model_director_notes`に警告を追記（再生成はしない、低性能LLM向けの緩い検証）。

### ステップ13: 逸脱時の自動リトライ準備
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: ステップ12で大幅逸脱（±30超）の場合、1回だけプロンプトに"tensionが目標値から逸脱しています。調整して再生成"を付与してリトライするラッパーを追加。

### ステップ14: Workflowへの統合（かんたんモード）
- **ファイル**: `src/backend/workflows/plot_expansion_workflow.py`
- **内容**: エピソード生成ループ内で`target_tension`を計算し、エンジン呼び出しに渡す繋ぎ込み。

### ステップ15: 結合テストの作成
- **ファイル**: `tests/integration/test_tension_curve.py`（新規）
- **内容**: モックLLMを使用し、10話生成時にtensionが目標曲線に沿って推移するかを検証。

### ステップ16: ドキュメント更新と設定UI確認
- **ファイル**: `README.md` または `docs/`
- **内容**: 感情曲線の仕様とアーキタイプとの対応表を記載。Streamlit UIに曲線プレビューがあるか確認（任意）。

---

# 機能B: 敵役の多層化プロンプト（ステップ17〜32）

## 目標
キャラクター生成時に、`role="悪役"`のキャラに対し「彼らなりの正義（justification）」「誤解の構造（misunderstanding）」「論理的弱点（logical_flaw）」を強制的に生成させ、プロット生成時にこれを参照させることで、単なる「悪」ではない知的対立構造を作る。

### ステップ17: 敵役メタデータのスキーマ定義
- **ファイル**: `src/agents/base.py` または `models/character.py`
- **内容**: Pydanticモデル`AntagonistDepth`を定義。`justification: str`, `misunderstanding: str`, `logical_flaw: str`を持つシンプルなモデル。

### ステップ18: DB永続化のためのカラム追加
- **ファイル**: `alembic/versions/YYYY_add_antagonist_depth.py`（新規）
- **内容**: `characters`テーブルに`antagonist_depth_json`（Text, nullable=True）を追加。既存レコードはNULL。

### ステップ19: キャラクターレジストリへの組み込み
- **ファイル**: `src/models/character.py` の`CharacterRegistry`相当モデルに`antagonist_depth: Optional[AntagonistDepth]`を追加。`registry_data`JSONへのシリアライズ/デシリアライズを許容。

### ステップ20: 敵役生成専用プロンプトの作成
- **ファイル**: `prompts/antagonist_depth.j2`（新規Jinja2テンプレート）
- **内容**: 「以下の悪役について、彼らの視点での正義、誤解、論理的破綻を3行ずつ出力せよ」という指示と、JSONスキーマ例を記載。

### ステップ21: プロンプトのバリデーション関数
- **ファイル**: `src/agents/base.py` に追記
- **内容**: `parse_antagonist_depth(llm_output: str) -> AntagonistDepth`関数。JSONデコード失敗時は空文字を返すフォールバック付き。

### ステップ22: 敵役生成ロジックの実装（Agent側）
- **ファイル**: `src/agents/marketing.py` または `src/backend/engine.py`のキャラ生成部
- **内容**: `role=="悪役"`のキャラ生成完了時、フックしてステップ20のプロンプトを実行する非同期メソッド`enrich_antagonist_depth`を追加。

### ステップ23: 生成結果のDB保存
- **ファイル**: `src/backend/database/repositories/character.py`
- **内容**: `update_antagonist_depth(character_id, depth_json)`メソッドを追加。ステップ18で追加したカラムへ保存。

### ステップ24: ステップ17〜23の単体テスト
- **ファイル**: `tests/test_antagonist_depth.py`（新規）
- **内容**: プロンプトパースの堅牢性、DB保存の往復、フォールバック挙動をテスト。

### ステップ25: プロット生成プロンプトへの参照追加
- **ファイル**: `src/backend/engine_prompts.py`
- **内容**: プロット生成プロンプトの`active_char_names`表示部で、悪役の場合は`justification`と`logical_flaw`を明示的に表示する分岐を追加。

### ステップ26: ContextManagerでの敵役情報強調
- **ファイル**: `src/backend/engine_context.py`
- **内容**: `filter_active_characters`内で、悪役の`justification`が存在すれば優先的に出力に含める処理を追加。

### ステップ27: 逆転（ざまぁ）時の論理破綻描写指示
- **ファイル**: `prompts/`内のざまぁ用プロンプト
- **内容**: 「主人公が敵役を論破する際、敵役の`logical_flaw`を突く展開にせよ」という指示を追加。低性能LLMでも具体性が出るよう。

### ステップ28: 結合テストの作成
- **ファイル**: `tests/integration/test_antagonist_depth.py`（新規）
- **内容**: キャラ生成→プロット生成のフローで、敵役の論理破綻がプロット内で参照されるかをモックで検証。

### ステップ29: 既存キャラへのバックフィルスクリプト
- **ファイル**: `scripts/backfill_antagonist_depth.py`（新規）
- **内容**: 既存書籍の悪役キャラに対し、一括でステップ22を適用するCLIスクリプト。

### ステップ30〜32: UI表示とドキュメント
- **ステップ30**: Streamlit UI（`streamlit_app/ui_tabs_planning.py`）で敵役の深化情報を表示。
- **ステップ31**: 逆転展開レビューの監査ロジックに「論理破綻の有無」チェックを追加。
- **ステップ32**: ドキュメント更新（敵役設計のベストプラクティス）。

---

# 機能C: 伏線管理システムの強化（ステップ33〜48）

## 目標
既存の`Foreshadowing`テーブルと`engine_context.build_past_context`の`story_threads`を活用し、プロット生成時に「回収すべき伏線」をプロンプトに明示し、LLMが自然に回収・展開するよう制御する。さらに、意図的に「長期伏線」を配置する指示を生成する。

### ステップ33: 伏線の重要度カテゴリの定義
- **ファイル**: `src/backend/foreshadowing_types.py`（新規）
- **内容**: `ForeshadowingCategory`Enum（`short_term`, `mid_term`, `long_term`, `red_herring`）を定義。

### ステップ34: DBモデルへのカテゴリカラム追加
- **ファイル**: `alembic/versions/ZZZZ_add_foreshadowing_category.py`（新規）
- **内容**: `Foreshadowing`テーブルに`category`（String, default="mid_term"）と`priority`（Integer, default=1）を追加。

### ステップ35: Plotモデルへの伏線参照強化
- **ファイル**: `models/plot.py`の`PlotForeshadowing`
- **内容**: `planted_foreshadowings: List[Dict]`と`resolved_foreshadowings: List[str]`フィールドを追加（既存`foreshadowing_refs`を拡張）。

### ステップ36: 伏線リポジトリの拡張
- **ファイル**: `src/backend/database/repositories/misc.py` または専用`foreshadowing_repo.py`
- **内容**: `get_active_foreshadowings(book_id, branch_id, ep_num)`（現時点で未回収の伏線を優先度順で取得）メソッドを追加。

### ステップ37: 回収推奨伏線の選定ロジック
- **ファイル**: `src/backend/engine_context.py`に追記
- **内容**: `select_foreshadowings_to_resolve(active_foreshadowings, current_ep, target_eps) -> List`。現在話数が設定された`payoff_ep`に近い、または長期伏線で進行度が70%超のものを優先。

### ステップ38: 伏線配置プロンプトの作成
- **ファイル**: `prompts/foreshadowing_plant.j2`（新規）
- **内容**: 「このエピソードで、以下の長期伏線を自然に1つ配置せよ: {候補リスト}」という指示テンプレート。

### ステップ39: プロット生成時の伏線注入（配置）
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: ステップ37で選定した「配置候補」をプロンプトdictに詰め、LLPに長期伏線の植え付けを指示。

### ステップ40: プロット生成時の伏線注入（回収）
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: 「回収候補」を選定し、プロンプトに「以下の伏線を本話で回収せよ」と指示。両方存在する場合は両方注入。

### ステップ41: 生成結果からの伏線更新抽出
- **ファイル**: `src/backend/engine_plot.py`
- **内容**: LLM返却後、`PlotForeshadowing.planted_foreshadowings`と`resolved_foreshadowings`を解析し、DB更新用のdictを構築。

### ステップ42: DBへの伏線状態更新
- **ファイル**: `src/backend/database/repositories/misc.py`
- **内容**: `record_foreshadowing_plant`（新規作成）と`mark_foreshadowing_resolved`（fulfilled=Trueに更新）メソッドを追加。

### ステップ43: 未回収伏線の自動警告
- **ファイル**: `src/services/audit_service.py`
- **内容**: 最終話手前で`long_term`かつ未回収の伏線があれば、`AuditIssue`として記録する監査ルールを追加。

### ステップ44: ContextManagerへの統合
- **ファイル**: `src/backend/engine_context.py`
- **内容**: `build_past_context`内の`story_threads`表示を、`category`と`priority`でソートし、重要なものを強調するよう修正。

### ステップ45: ステップ33〜44の単体テスト
- **ファイル**: `tests/test_foreshadowing_manager.py`（新規）
- **内容**: 選定ロジック、DB更新、監査ルールの単体テスト。

### ステップ46: 結合テスト
- **ファイル**: `tests/integration/test_foreshadowing_workflow.py`（新規）
- **内容**: 1話で植えられた伏線が、指定話数で回収されるAIパイプラインをモックで検証。

### ステップ47: UIでの伏線ダッシュボード
- **ファイル**: `streamlit_app/ui_tabs_monitor.py`
- **内容**: 書籍ごとの伏線一覧（配置話・回収話・状態）を表示する表を追加。

### ステップ48: 全体ドキュメント更新とリグレッションテスト
- **ファイル**: `docs/narrative_depth_features.md`（新規）
- **内容**: 機能A〜Cの統合仕様書と、既存テストへの影響確認。`pytest`全通過を確認。

---

## 実装スケジュール目安
- 機能A（ステップ1-16）: 約3日（1日5-6ステップ）
- 機能B（ステップ17-32）: 約3日
- 機能C（ステップ33-48）: 約4日
- **合計**: 約10営業日

各ステップは独立してcommit可能であり、低性能LLM環境下でも「ステップごとの指示」を与えれば確実に実装を進められる構造としている。
