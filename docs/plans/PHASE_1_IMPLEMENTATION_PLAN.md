# フェーズ１詳細実装計画書：低性能LLM対応最適化版
## 目標：伏線・フック・挿絵の3機能を36ステップで実装
### 前提条件
- LLM性能に依存しない実装（プロンプトエンジニアリング・テンプレート・ルールベース中心）
- 既存パイプライン基盤（AutoWorkflowPipeline・WorkflowContext）を変更しない
- 各ステップは1-2時間で完了可能な粒度
- ロールバック容易（各ステップ独立コミット可能）

---

## ステップ群1：伏線データベース基盤（ステップ1-12）

### フェーズ1-1：データモデル拡張
1. **目的**：`Foreshadowing` データクラス作成
   - `src/models/foreshadowing.py` 新規作成
   - フィールド: `id (str)`, `content (str)`, `hang_volume (int)`, `hang_episode (int)`, `hang_chapter (int)`, `hang_type (Literal["explicit", "implicit", "reader_task", "unresolved"])`, `importance (Literal["★", "★★", "★★★"])`, `resolution_volume (Optional[int])`, `resolution_episode (Optional[int])`
   - コンストラクタ、バリデーション、to_dict/from_dict 実装
   - テスト: `tests/models/test_foreshadowing.py`

2. **目的**：`WorkflowContext` に伏線リストフィールド追加
   - `src/services/pipeline_base.py` の `WorkflowContext` に `foreshadowings: list[Foreshadowing] = []` 追加
   - 必要に応じて `pipeline_param_mapper.py` も更新（マッピングは後で）
   - テスト: Context作成時にリストが空で初期化されること確認

3. **目的**：伏線ID生成ユーティリティ作成
   - `src/services/foreshadowing_id_generator.py` 新規作成
   - 関数: `generate_foreshadowing_id(genre: str, volume: int, episode: int) -> str`
   - 形式例: `F-{genre_code}-{volume:03d}-{episode:03d}-{seq:03d}`（ジャンルコード辞書参照）
   - テスト: 同一巻話で連番生成、異なる巻話で衝突しないこと

### フェーズ1-2：伏線管理サービス
4. **目的**：伏線リポジトリインターフェース作成
   - `src/domain/interfaces/foreshadowing_repository.py` 新規作成
   - メソッド: `add(foreshadowing: Foreshadowing) -> None`, `get_by_book_id(book_id: int) -> list[Foreshadowing]`, `get_unresolved(book_id: int) -> list[Foreshadowing]`, `resolve(foreshadowing_id: str, volume: int, episode: int) -> None`, `get_balance(volume: int) -> dict`（新規張り数-回収数）
   - インメモリ実装のスケルトン（後で実装置換）

5. **目的**：インメモリ伏線リポジトリ実装
   - `src/infrastructure/repositories/foreshadowing_repository.py` 新規作成
   - `ForeshadowingRepository` クラスでインターフェース実装
   - 内部辞書: `_store: Dict[int, list[Foreshadowing]]` (book_id -> list)
   - 全メソッドをスレッドセーフに実装（ロック使用）
   - テスト: 追加・取得・解決・バランス計算の正常動作確認

6. **目的**：エンジンに伏線リポジトリ注入
   - `src/backend/engine.py` の `UltimateHegemonyEngine` に `foreshadowing_repository: ForeshadowingRepository` フィールド追加
   - コンストラクタで受け取り、内部プロパティとして保持
   - テスト: エンジン作成時にリポジトリが正しく設定されること

### フェーズ1-3：伏線登録・解決ロジック
7. **目的**：伏線登録ステップ骨格作成
   - `src/services/pipeline_steps.py` に `ForeshadowingRegistrationStep` クラス新規作成
   - `execute` メソッド: 暫定的に `return True` （後に実装）
   - ドキュメンテーション文字列: 「伏線をPlanStepのアウトプットから抽出・登録」
   - テスト: ステップインスタンス生成可能こと確認

8. **目的**：伏線登録ロジック実装（PlanStep連携）
   - `ForeshadowingRegistrationStep.execute` に実装
   - 手順: 
     a. `ctx.book_id` が None ならスキップ
     b. `engine.planner` から直近生成されたプロット・バブルを取得（実装は後で簡易版）
     c. プロット要素から伏線候補を抽出（仮: 特定キーワード含む文を伏線とする）
     d. `Foreshadowing` オブジェクト作成・リポジトリに登録
   - テスト: モックエンジンで正常動作確認

9. **目的**：伏線解決ステップ骨格作成
   - `src/services/pipeline_steps.py` に `ForeshadowingResolutionStep` クラス新規作成
   - `execute` メソッド: 暫定的に `return True`
   - ドキュメンテーション文字列: 「指定巻話での伏線解決登録」
   - テスト: ステップ生成可能こと確認

10. **目的**：伏線解決ロジック実装（WriteStep連携想定）
    - `ForeshadowingResolutionStep.execute` に実装
    - 手順:
      a. `ctx.book_id` が None ならスキップ
      b. エピソード生成完了後のタイミングで呼び出される想定（実際の連携は後で）
      c. 現在の巻話（`ctx.current_volume`, `ctx.current_episode` が必要→後で追加）で解決すべき伏線をリポジトリから取得
      d. 取得した伏線に解決巻話を設定・リポジトリ更新
    - テスト: モックで解決フロー正常動作確認

11. **目的**：伏線バランスチェックユーティリティ作成
    - `src/services/foreshadowing_balance_checker.py` 新規作成
    - 関数: `check_volume_balance(repository: ForeshadowingRepository, book_id: int, target_volume: int) -> dict`
    - 返却値: `{"hang_count": int, "resolve_count": int, "balance": int, "status": Literal["OK", "TOO_MANY_HANGS", "TOO_MANY_RESOLVES"]}`
    - 基準: 新規張り数 ≒ 回収数（±5以内をOKとする）
    - テスト: 各パターンで正常判定されること

12. **目的**：伏線バランスチェックステップ作成
    - `src/services/pipeline_steps.py` に `ForeshadowingBalanceCheckStep` クラス新規作成
    - `execute` メソッドで `ForeshadowingBalanceChecker.check_volume_balance` 呼び出し
    - バランスNGなら `reporter.report` で警告（失敗扱いにせず継続）
    - テスト: 各バランスパターンで適切な警告ログ出力確認

---

## ステップ群2：フック生成機能（ステップ13-24）

### フェーズ2-1：フックデータモデル・テンプレート
13. **目的**：`Hook` データクラス作成
    - `src/models/hook.py` 新規作成
    - フィールド: `id (str)`, `type (Literal["mystery", "threat", "emotion"])`, `content (str)`, `target_position (Literal["episode_end", "volume_end", "series_end"])`, `volume (int)`, `episode (int)`, `chapter (int)`
    - コンストラクタ、バリデーション、to_dict/from_dict 実装
    - テスト: `tests/models/test_hook.py`

14. **目的**：フックテンプレート辞書作成
    - `src/services/hook_templates.py` 新規作成
    - 定数: `HOOK_TEMPLATES = { "mystery": [ "...", "...", "..." ], "threat": [ "...", "...", "..." ], "emotion": [ "...", "...", "..." ] }`
    - 各タイプ3パターン以上（ガイドライン準拠）
    - テンプレートには `{character_name}`, `{genre}` 等のプレースホルダーを含む
    - テスト: すべてのテンプレートが取得可能・プレースホルダー含有こと確認

15. **目的**：フックプレースホルダー置換ユーティリティ作成
    - `src/services/hook_formatter.py` 新規作成
    - 関数: `format_hook(template: str, context: dict[str, Any]) -> str`
    - 実装: `str.format` または `jinja2.Template` 軽量版（依存追加なしで `replace` 連結）
    - プレースホルダー例: `{character_name}`, `{genre}`, `{protagonist_type}`, `{current_volume}`, `{current_episode}`
    - テスト: 正常置換・欠損プレースホルダー時の挙動確認（元のまま返すか空文字か）

### フェーズ2-2：フック生成サービス
16. **目的**：フックリポジトリインターフェース作成
    - `src/domain/interfaces/hook_repository.py` 新規作成
    - メソッド: `add(hook: Hook) -> None`, `get_by_book_id(book_id: int) -> list[Hook]`, `get_pending_hooks(book_id: int) -> list[Hook]`（未使用のフック取得）
    - インメモリ実装のスケルトン

17. **目的**：インメモリフックリポジトリ実装
    - `src/infrastructure/repositories/hook_repository.py` 新規作成
    - `HookRepository` クラスでインターフェース実装
    - 内部辞書: `_store: Dict[int, list[Hook]]`
    - 全メソッドスレッドセーフ実装
    - テスト: 基本CRUD動作確認

18. **目的**：エンジンにフックリポジトリ注入
    - `src/backend/engine.py` の `UltimateHegemonyEngine` に `hook_repository: HookRepository` フィールド追加
    - コンストラクタで受け取り・保持
    - テスト: エンジン作成時にリポジトリ正常設定確認

19. **目的**：フック生成ステップ骨格作成
    - `src/services/pipeline_steps.py` に `HookGenerationStep` クラス新規作成
    - `execute` メソッド: 暫定的に `return True`
    - ドキュメンテーション文字列: 「エピソード・巻終わりにフック生成・登録」
    - テスト: ステップインスタンス生成可能こと確認

20. **目的**：フック生成ロジック実装（エピソード終わり用）
    - `HookGenerationStep.execute` に実装
    - 手順:
      a. `ctx.book_id` が None ならスキップ
      b. エピソード終わりかどうか判定（後で `ctx.current_episode == ctx.target_eps` 等で実装→今は仮に常に実行）
      c. フックタイプをランダム選択またはローテーション（簡易: インデックスカウントで循環）
      d. テンプレート辞書から対応タイプのランダム1つ選択
      e. `HookFormatter.format_hook` で現在コンテキスト適用
      f. `Hook` オブジェクト作成・リポジトリに登録
      g. `reporter.report` で生成フック内容通知
    - テスト: モックでフック生成・登録フロー正常確認

21. **目的**：巻終わりフック生成ロジック追加
    - `HookGenerationStep.execute` に巻終わり判定ロジック追加
    - 手順:
      a. エピソード終わりフック生成に加えて
      b. `ctx.current_episode == ctx.target_eps` かつ `ctx.current_volume` が終了巻のとき
      c. 巻終わり用フックタイプ（「未解決の重大クエスチョン」＋「次巻タイトル暗示」）を生成
      d. テンプレート: `「第{next_volume}巻『{next_volume_title_hint}』──その{objective}が、{subject}を{action}まで」`
      e. プレースホルダーに次巻ヒント等を設定（簡易: デフォルト値使用）
    - テスト: 巻終わり条件で異なるフック生成確認

22. **目的**：フック生成頻度制御ユーティリティ作成
    - `src/services/hook_frequency_controller.py` 新規作成
    - 関数: `should_generate_hook(current_episode: int, target_eps: int, pattern: Literal["every", "every_other", "third"]) -> bool`
    - デフォルト: `every_other`（2話に1回）等設定可能
    - テスト: 各パターンで正常判定されること

### フェーズ2-3：フック表示・メタデータ
23. **目的**：`WorkflowContext` にフック関連フィールド追加
    - `src/services/pipeline_base.py` の `WorkflowContext` に 
      `hooks: list[Hook] = []`
      `hook_generation_index: int = 0`（ローテーション用）
      `current_volume: int = 1`
      `current_episode: int = 0`
    - 追加フィールドを初期化
    - テスト: Context作成時にデフォルト値確認

24. **目的**：パラメータマッパーにフックフィールド追加
    - `src/services/pipeline_param_mapper.py` の 
      `map_fullauto_kwargs_to_context` と `map_easymode_kwargs_to_context` に
      `current_volume`, `current_episode` を追加（デフォルト: 1, 0）
    - テスト: マッピング後にフィールドが設定されること確認

---

## ステップ群3：挿絵ポイント詳細化（ステップ25-36）

### フェーズ3-1：挿絵設定モデル拡張
25. **目的**：挿絵ポイントデータクラス作成
    - `src/models/illustration_point.py` 新規作成
    - フィールド: `id (str)`, `page (str)`（例: "口絵1", "15"）、`scene_description (str)`, `composition (str)`, `props (str)`, `expressions (dict[str, str])`, `background (str)`, `notes (Optional[str])`
    - コンストラクタ、バリデーション、to_dict/from_dict 実装
    - テスト: `tests/models/test_illustration_point.py`

26. **目的**：`WorkflowContext` に挿絵ポイントリスト追加
    - `src/services/pipeline_base.py` の `WorkflowContext` に `illustration_points: list[IllustrationPoint] = []` 追加
    - テスト: Context作成時に空リスト初期化確認

27. **目的**：挿絵ポイントテンプレート辞書作成
    - `src/services/illustration_point_templates.py` 新規作成
    - 定数: `ILLUSTRATION_POINT_TEMPLATES = { "口絵": [ {...}, {...} ], "モノクロ挿絵1": [ {...} ], ... }`
    - 各テンプレートは `IllustrationPoint` オブジェクトのdict表現
    - ジャンル別・シーン別テンプレートを用意（簡易版: ファンタジー共通テンプレート）
    - テスト: テンプレート取得・オブジェクト変換正常こと確認

### フェーズ3-2：挿絵ポイント生成ロジック
28. **目的**：挿絵ポイント抽出ユーティリティ作成
    - `src/services/illustration_point_extractor.py` 新規作成
    - 関数: `extract_illustration_points_from_bible(bible: dict, genre: str) -> list[IllustrationPoint]`
    - 実装:
      a. バブルからキャラクター・シーン情報抽出
      b. ジャンルテンプレートとマッチング
      c. プレースホルダー置換（キャラクター名等）
      d. `IllustrationPoint` オブジェクトリスト生成
    - 初期実装はハードコーディング（後でデータ駆動化）
    - テスト: サンプルバブルでポイント抽出確認

29. **目的**：挿絵ポイント登録ステップ骨格作成
    - `src/services/pipeline_steps.py` に `IllustrationPointRegistrationStep` クラス新規作成
    - `execute` メソッド: 暫定的に `return True`
    - ドキュメンテーション文字列: 「PlanStep後のバブルから挿絵ポイント抽出・登録」
    - テスト: ステップ生成可能こと確認

30. **目的**：挿絵ポイント登録ロジック実装
    - `IllustrationPointRegistrationStep.execute` に実装
    - 手順:
      a. `ctx.book_id` が None ならスキップ
      b. `engine.repo.bible.get_by_book_id(ctx.book_id)` でバブル取得
      c. `IllustrationPointExtractor.extract_illustration_points_from_bible` 呼び出し
      d. 生成されたポイントを `ctx.illustration_points` に設定
      e. `reporter.report` でポイント数通知
    - テスト: モックバブルでポイント抽出・設定フロー正常確認

31. **目的**：挿絵プロンプトビルダー拡張
    - `src/services/illustration/prompts.py` を修正
    - 既存のプロンプト生成関数に `illustration_points: list[IllustrationPoint]` パラメータ追加
    - ポイント情報からより詳細なプロンプト構築:
      - 「構図: {composition}」
      - 「シーン: {scene_description}」
      - 「小道具: {props}」
      - 「表情: {expressions の文字列化}」
      - 「背景: {background}」
    - 既存プロンプトをポイント情報で上書き・拡張する形
    - テスト: ポイントありなしでプロンプト内容が変化すること確認

### フェーズ3-3：挿絵ステップ連携・表示
32. **目的**：`IllustrationStep` にポイント情報渡し実装
    - `src/services/pipeline_steps.py` の `IllustrationStep.execute` を修正
    - 実装:
      a. `if not ctx.illustration_points:` でポイントなし時のスキップロジック改善
      b. `illustration_workflow.execute` 呼び出し時に `illustration_points=ctx.illustration_points` を追加
      c. （仕様変更が必要なら`illustration_workflow.py`も合わせて修正、ただし最小変更に留める）
    - テスト: ポイントありでプロンプトに詳細情報含まれること確認

33. **目的**：挿絵ポイント生成フローをパイプラインに組み込み
    - `src/services/auto_workflow_pipeline.py` の 
      `create_full_auto_pipeline` と `create_easy_mode_pipeline` に
      `IllustrationPointRegistrationStep()` を `PlanStep` 後に `WriteStep` 前に挿入
    - テスト: パイプラインステップ順序が正しいこと確認

34. **目的**：挿絵ポイント情報を結果に含める
    - `src/services/pipeline_param_mapper.py` の 
      `map_context_to_fullauto_result` と `map_context_to_easymode_result` に
      `illustration_points` フィールド追加（`ctx.illustration_points` から変換）
    - テスト: 結果にイラストポイント情報が含まれること確認

35. **目的**：挿絵ポイントテンプレート・バリエーション拡張
    - `src/services/illustration_point_templates.py` にジャンル別テンプレート追加
    - ファンタジー・学園ラブコメ・異世界転生・SF 各3-5テンプレート
    - 各テンプレートにジャンル特有の要素を含める
    - テスト: 各ジャンルで適切なテンプレートが選択・使用されること確認

36. **目的**：全機能統合テスト・ドキュメント更新
    - **テスト**: 
      a. `pytest tests/test_foreshadowing_registration_step.py -v`
      b. `pytest tests/test_hook_generation_step.py -v`
      c. `pytest tests/test_illustration_point_registration_step.py -v`
      d. `pytest tests/test_unified_pipeline_with_new_steps.py -v`（新ステップ含むパイプラインテスト）
    - **ドキュメント**: 
      a. `API.md` に新ステップ・フィールド追加
      b. `ARCHITECTURE.md` に最適化フロー図更新
      c. `README.md` の「機能追加」節にこれらの実装内容を追記
    - **確認**: 既存テスト全通過・新機能で期待動作確認

---

## 実装ガイドライン（低性能LLM対応）

### 原則
1. **LLM呼び出し最小化**: 
   - フック・挿絵ポイントはテンプレート・ルールベース
   - LLMは既存のプロット生成・本文執筆にのみ使用
2. **状態管理の単純化**: 
   - 複雑なアルゴリズムではなくインデックス・カウンターで代替
   - 外部依存なし（ファイルI/O・ネットワークなし）
3. **エラートレラント設計**: 
   - 1ステップ失敗してもパイプライン継続（警告レベル）
   - デフォルト動作で安全にフォールバック
4. **観測可能性確保**: 
   - 各ステップで詳細なログ出力（レポーター経由）
   - メトリクスポイントは後で追加可能なフックを残す

### テスト戦略
- 各ステップはモックエンジン・リポジトリで単体テスト
- 統合テストはインメモリ実装で動作確認
- 性能テストは別途（目安: 1エピソードあたり+100ms以内増加）
- ロールバックテスト: 各ステップを飛ばしても既存機能動作確認

### 完了判定基準
- 全36ステップのコード実装・単体テスト通過
- 統合テストで伏線・フック・挿絵ポイントが正常に生成・連携
- 既存のFullAuto/EasyModeワークフローが後方互換性維持
- 性能劣化が許容範囲内（1エピソードあたり+200ms以内）