# mypy strict モード完全クリア 実装計画書（48ステップ）

## 目的
mypy strict モードをクリアし、型安全性を確保するための48ステップ計画
低性能LLMでも実装可能な小さなステップに分解

## 原則
1. 各ステップは15-30分で完了可能
2. エラータイプ別にグループ化して効率化
3. テストを必ず実行し、後退を防ぐ
4. 一貫したコードスタイルを維持

## 前提条件
- Python 3.12+
- mypy 1.0.1+
- すでに`pyproject.toml`にmypy設定あり
- Gitで変更管理可能

## フェーズ別計画

### フェーズ1: 基本的な型注釈追加（ステップ1-16）
**目標**: no-untyped-def, no-untyped-def (パラメータ), var-annotated エラーを解消

### フェーズ2: 戻り値とコール修正（ステップ17-32）
**目標**: no-any-return, no-untyped-call, return-value, arg-type エラーを解消

### フェーズ3: 属性とジェネリクス修正（ステップ33-40）
**目標**: attr-defined, type-arg, assignment エラーを解消

### フェーズ4: 雑項目と最終調整（ステップ41-48）
**目標**: 残りのmisc, name-defined, call-arg, method-assign 等を解消

---

## フェーズ1: 基本的な型注釈追加（ステップ1-16）

### ステップ1: streamlit_app/state.py 基本関数
- **ファイル**: streamlit_app/state.py
- **タスク**: 関数定義に型注釈を追加（最初の10関数）
- **具体例**: `def get_runtime(): → def get_runtime() -> UIStateStore:`
- **検証**: `mypy streamlit_app/state.py --no-error-summary | head -20`

### ステップ2: streamlit_app/state.py 残りの関数
- **ファイル**: streamlit_app/state.py
- **タスク**: 関数定義に型注釈を追加（残りの関数）
- **具体例**: パラメータにも型注釈を追加
- **検証**: `mypy streamlit_app/state.py --no-error-summary | head -20`

### ステップ3: streamlit_app/api_client.py 基本関数
- **ファイル**: streamlit_app/api_client.py
- **タスク**: 関数定義に型注釈を追加（最初の15関数）
- **具体例**: `def _async_req(): → def _async_req() -> Awaitable[Response]:`
- **検証**: `mypy streamlit_app/api_client.py --no-error-summary | head -20`

### ステップ4: streamlit_app/api_client.py 残りの関数
- **ファイル**: streamlit_app/api_client.py
- **タスク**: 関数定義に型注釈を追加（残りの関数）
- **具体例**: パラメータにも型注釈を追加
- **検証**: `mypy streamlit_app/api_client.py --no-error-summary | head -20`

### ステップ5: streamlit_app/stores.py
- **ファイル**: streamlit_app/stores.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: 変数にも型注釈を追加（var-annotated対策）
- **検証**: `mypy streamlit_app/stores.py --no-error-summary`

### ステップ6: streamlit_app/ui_store.py
- **ファイル**: streamlit_app/ui_store.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: コールバック関数のCallable型を正確に指定
- **検証**: `mypy streamlit_app/ui_store.py --no-error-summary`

### ステップ7: streamlit_app/state_manager.py
- **ファイル**: streamlit_app/state_manager.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: 戻り値型をAppStateModelに統一
- **検証**: `mypy streamlit_app/state_manager.py --no-error-summary`

### ステップ8: streamlit_app/sidebar.py
- **ファイル**: streamlit_app/sidebar.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: Streamlitの戻り値型を正確に把握
- **検証**: `mypy streamlit_app/sidebar.py --no-error-summary`

### ステップ9: streamlit_app/pages_config.py
- **ファイル**: streamlit_app/pages_config.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: ページ設定関数の戻り値型をDict[str, List[Page]]
- **検証**: `mypy streamlit_app/pages_config.py --no-error-summary`

### ステップ10: streamlit_app/health_check.py
- **ファイル**: streamlit_app/health_check.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: ヘルスチェックの戻り値型をDict[str, str]
- **検証**: `mypy streamlit_app/health_check.py --no-error-summary`

### ステップ11: streamlit_app/event_bus.py
- **ファイル**: streamlit_app/event_bus.py
- **タスク**: 全関数に型注釈を追加
- **具体例: イベントバスの型を正確に定義
- **検証**: `mypy streamlit_app/event_bus.py --no-error-summary`

### ステップ12: streamlit_app/controllers/manager.py
- **ファイル**: streamlit_app/controllers/manager.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: コントローラーマネージャーのインターフェース型
- **検証**: `mypy streamlit_app/controllers/manager.py --no-error-summary`

### ステップ13: streamlit_app/backend_launcher.py
- **ファイル**: streamlit_app/backend_launcher.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: subprocess.Popenの型引数を追加
- **検証**: `mypy streamlit_app/backend_launcher.py --no-error-summary`

### ステップ14: streamlit_app/app.py
- **ファイル**: streamlit_app/app.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: Streamlitのコールバック関数型に注意
- **検証**: `mypy streamlit_app/app.py --no-error-summary`

### ステップ15: streamlit_app/utils.py
- **ファイル**: streamlit_app/utils.py
- **タスク**: 全関数に型注釈を追加
- **具体例**: ユーティリティ関数の汎用型を活用
- **検証**: `mypy streamlit_app/utils.py --no-error-summary`

### ステップ16: streamlit_app/ui_tabs_* ファイル群
- **ファイル**: streamlit_app/ui_tabs_*.py (複数ファイル)
- **タスク**: 各ファイルの関数に型注釈を追加
- **具体例**: UIコンポーネント関数のStreamlit要素型
- **検証**: `mypy streamlit_app/ui_tabs_*.py --no-error-summary`

---

## フェーズ2: 戻り値とコール修正（ステップ17-32）

### ステップ17: src/agents/writing.py 基本修正
- **ファイル**: src/agents/writing.py
- **タスク**: no-any-returnとno-untyped-defを修正
- **具体例**: 戻り値Anyを具体型をstr/List/Dictに統一、Coroutineのawait漏れ修正
- **検証**: `mypy src/agents/writing.py --no-error-summary | head -20`

### ステップ18: src/agents/writing.py 継続修正
- **ファイル**: src/agents/writing.py
- **タスク**: 残りの型注釈とコール修正
- **具体例**: EroticParameters等のジェネリクス型引数追加
- **検証**: `mypy src/agents/writing.py --no-error-summary | tail -20`

### ステップ19: src/agents/plot.py 基本修正
- **ファイル**: src/agents/plot.py
- **タスク**: no-any-returnとno-untyped-defを修正
- **具体例**: PlotAgentのメソッド戻り値型を統一
- **検証**: `mypy src/agents/plot.py --no-error-summary | head -20`

### ステップ20: src/agents/plot.py 継続修正
- **ファイル**: src/agents/plot.py
- **タスク**: 残りの型注釈とコール修正
- **具体例**: IPromptManagerのメソッドコール修正
- **検証**: `mypy src/agents/plot.py --no-error-summary | tail -20`

### ステップ21: src/agents/base.py
- **ファイル**: src/agents/base.py
- **タスク**: BaseAgentの型注釈を追加
- **具体例**: ジェネリクスBaseAgent[T]の実装開始
- **検証**: `mypy src/agents/base.py --no-error-summary`

### ステップ22: src/agents/audit.py
- **ファイル**: src/agents/audit.py
- **タスク**: 監査エージェントの型注釈を追加
- **具体例**: CriticFeedback等の戻り値型統一
- **検証**: `mypy src/agents/audit.py --no-error-summary`

### ステップ23: src/agents/erotic_integrity.py 基本修正
- **ファイル**: src/agents/erotic_integrity.py
- **タスク**: 長いファイルの前半部分を修正
- **具体例**: 変数型注釈と関数署名修正
- **検証**: `mypy src/agents/erotic_integrity.py --no-error-summary | head -30`

### ステップ24: src/agents/erotic_integrity.py 継続修正
- **ファイル**: src/agents/erotic_integrity.py
- **タスク**: 中盤部分を修正
- **具体例**: 辞書・リストのジェネリクス型引数追加
- **検証**: `mypy src/agents/erotic_integrity.py --no-error-summary | sed -n '30,60p'`

### ステップ25: src/agents/erotic_integrity.py 継続修正
- **ファイル**: src/agents/erotic_integrity.py
- **タスク**: 後半部分を修正
- **具体例**: 残りの型注釈とメソッドコール修正
- **検証**: `mypy src/agents/erotic_integrity.py --no-error-summary | tail -30`

### ステップ26: src/services/llm_service.py
- **ファイル**: src/services/llm_service.py
- **タスク**: LLMサービスの型注釈を追加
- **具体例**: ジェネリックレスポンス型とコルーチン型
- **検証**: `mypy src/services/llm_service.py --no-error-summary`

### ステップ27: src/services/novel_service.py
- **ファイル**: src/services/novel_service.py
- **タスク**: ノベルサービスの型注釈を追加
- **具体例**: IRepositoryインターフェースの適切な型付け
- **検証**: `mypy src/services/novel_service.py --no-error-summary`

### ステップ28: src/services/retry_decorator.py
- **ファイル**: src/services/retry_decorator.py
- **タスク**: リトライデコレータの型注釈を追加
- **具体例**: 汎用Callable型とParamSpecの使用検討
- **検証**: `mypy src/services/retry_decorator.py --no-error-summary`

### ステップ29: src/services/llm_service.pyの依存修正
- **ファイル**: src/services/llm_service.py
- **タスク**: _ensure_factory()と関連メソッドの型修正
- **具体例**: LLMProviderFactoryの戻り値型を明示
- **検証**: `mypy src/services/llm_service.py --no-error-summary`

### ステップ30: src/engine_service.py
- **ファイル**: src/engine_service.py
- **タスク**: エンジンサービスの型注釈を追加
- **具体例**: 辞書型のキー・バリュー型を明示
- **検証**: `mypy src/engine_service.py --no-error-summary`

### ステップ31: src/shared/ ファイル群
- **ファイル**: src/shared/（resilient_http.py, retry_policy.py等）
- **タffix**: 共有モジュールの型注釈を追加
- **具体例**: CircuitBreakerとResilientHttpClientの型安全化
- **検証**: `mypy src/shared/ --no-error-summary`

### ステップ32: src/models/ ファイル群
- **ファイル**: src/models/（db.py, writing.py, plot.py等）
- **タスク**: Pydanticモデルの型注釈を強化
- **具体例**: Union型とOptional型の適切な使用
- **検証**: `mypy src/models/ --no-error-summary`

---

## フェーズ3: 属性とジェネリクス修正（ステップ33-40）

### ステップ33: src/backend/database/ リポジトリ群 基本修正
- **ファイル**: src/backend/database/repositories/*.py
- **タffix**: _get_session属性エラーとUntyped decoratorを修正
- **具体例**: BaseRepositoryのジェネリクス型引数追加とメソッド実装
- **検証**: `mypy src/backend/database/repositories/ --no-error-summary | head -30`

### ステップ34: src/backend/database/ リポジトリ群 継続修正
- **ファイル**: src/backend/database/repositories/*.py
- **タffix**: 残りの型注釈と戻り値型修正
- **具体例**: Column[int] → int の変換と sesssion型注釈
- **検証**: `mypy src/backend/database/repositories/ --no-error-summary | tail -30`

### ステップ35: src/backend/database/core.py
- **ファイル**: src/backend/database/core.py
- **タffix**: DatabaseConnectionWrapperの属性エラーを修正
- **具体例**: 欠落している属性を追加か、適切な型注釈で代替
- **検証**: `mypy src/backend/database/core.py --no-error-summary`

### ステップ36: src/backend/database/connection_protocol.py
- **ファイル**: src/backend/database/connection_protocol.py
- **タffix**: Tuple型引数のmissingを修正
- **具体例**: Tuple[...] に適切な型引数を追加
- **検証**: `mypy src/backend/database/connection_protocol.py --no-error-summary`

### スteps37: src/backend/tasks.py
- **ファイル**: src/backend/tasks.py
- **タスク**: Hueyタスクの型注釈を追加
- **具体例**: 関数デコレータと戻り値型を明示
- **検証**: `mypy src/backend/tasks.py --no-error-summary`

### ステップ38: src/backend/workflows/ ファイル群
- **ファイル**: src/backend/workflows/*.py
- **タスク**: Langgraphワークフローの型注釈を追加
- **具体例**: Stateグラフとノード関数の型を精密化
- **検証**: `mypy src/backend/workflows/ --no-error-summary`

### ステップ39: src/backend/routers/ ファイル群
- **ファイル**: src/backend/routers/*.py
- **タスク**: FastAPIルーターの型注釈を追加
- **具体例**: リクエスト/レスポンスモデルと依存関係の型付け
- **検証**: `mypy src/backend/routers/ --no-error-summary`

### ステップ40: src/backend/server.py
- **ファイル**: src/backend/server.py
- **タスク**: FastAPIサーバーの型注釈を追加
- **具体例**: エンドポイント関数と依存注入の型付け
- **検証**: `mypy src/backend/server.py --no-error-summary`

---

## フェーズ4: 雑項目と最終調整（ステップ41-48）

### ステップ41: src/core/ ファイル群 基本修正
- **ファイル**: src/core/（llm_gateway.py, plugin_loader.py等）
- **タスク**: コアモジュールの基本型注釈を追加
- **具体例**: LLMゲートウェイとプラグインローダーのインターフェース
- **検証**: `mypy src/core/ --no-error-summary | head -30`

### ステップ42: src/core/ ファイル群 継続修正
- **ファイル**: src/core/（llm_gateway.py, plugin_loader.py等）
- **タスク**: 残りの型注釈と属性エラーを修正
- **具体例**: モデルルーティングとコンテナの型安全化
- **検証**: `mypy src/core/ --no-error-summary | tail -30`

### ステップ43: src/api/ ファイル群
- **ファイル**: src/api/（client.py等）
- **タスク**: APIクライアントの型注釈を追加
- **具体例**: HTTPクライアントとレスポンスハンドラーの型付け
- **検証**: `mypy src/api/ --no-error-summary`

### ステップ44: src/agents/writing_scheduler.py
- **ファイル**: src/agents/writing_scheduler.py
- **タスク**: ライティングスケジューラーの型注釈を追加
- **具体例**: Futureとタスクディクショナリの型引数追加
- **検証**: `mypy src/agents/writing_scheduler.py --no-error-summary`

### ステップ45: src/agents/state_validator.py et al.
- **ファイル**: 残りのagent/*.pyファイル
- **タスク**: state_validator, marketing, illustration_agent等の型注釈
- **具体例**: 小規模ファイルを集中して処理
- **検証**: `mypy src/agents/state_validator.py src/agents/marketing.py src/agents/illustration_agent.py --no-error-summary`

### ステップ46: 残りのno-any-returnとno-untyped-call修正
- **ファイル**: 全プロジェクト
- **タスク**: 残っているno-any-returnとno-untyped-callを集中修正
- **具体例**: 戻り値Anyを具体的型に変換、未型付き関数へのコールをラップ
- **検証**: `mypy . --ignore-missing-imports --no-error-summary -e "no-any-return\|no-untyped-call" | wc -l`

### ステップ47: 残っているattr-definedとtype-arg修正
- **ファイル**: 全プロジェクト
- **タスク**: 属性エラーとジェネリクス型引数を修正
- **具体例**: モックオブジェクトの型付けとラッパークラスのジェネリクス化
- **検証**: `mypy . --ignore-missing-imports --no-error-summary -e "attr-defined\|type-arg" | wc -l`

### ステップ48: 最終検証とクリーンアップ
- **ファイル**: 全プロジェクト
- **タスク**: mypy strictモード完全通過確認と不要な# type: comment削除
- **具体例**: 
  1. `mypy . --strict` が0エラーになることを確認
  2. テストスイートを実行して後退がないことを確認
  3. 不要なtype: ignoreコメントを削除
- **検証**: 
  ```bash
  mypy . --strict
  pytest tests/unit/ -q
  ```

## 進捗追跡方法

### 毎日の目標
- 3-4ステップ完了を目安（1-2時間作業）

### 品質ゲート
- 各ステップ完了後: `mypy <対象ファイル> --no-error-summary` でエラー減少を確認
- 週末: `pytest tests/unit/ -q` で後退検知

### モジュール別完了基準
- ファイル単位: 対象ファイルのmypyエラーが0になる
- ディレクトリ単位: ディレクトリ内の*.pyファイルのmypyエラーが0になる

## リスク低減策

1. **段階的変更**: 大規模リファクタリングではなく、型注釈追加に焦点
2. **テスト駆動**: 各変更後に最低限の関連テストを実行
3. **ロールバック準備**: 頻繁にgit commitし、問題があれば即時戻せるようにする
4. **型の仮置き**: 複雑な型については最初はAnyを置いて後で改良（ただしstrictモードクリアが目標なので最終的には除去）

## 成功の定義
- `mypy . --strict` が終了コード0で実行される
- 型エラーが0件になる
- 既存の機能テストが後退しないこと
- IDEの自動補完が改善されていること

この計画により、低性能LLMでも15-30分の小さなタスクに集中して着実に型安全性を向上させることができます。