# AutoNovel v5.0 実装計画書 T2: 伏線ステートマシン ＆ 3層ローリング記憶 (全12ステップ)

**対象領域**: コア設計 2 (Foreshadowing State Machine & 3-Layer Memory)  
**目的**: Apache AGE (GraphRAG) を完全撤廃し、RDBMS `foreshadowing` テーブルと3層ローリング記憶（バイブル・100字要約・直前生文）により、20〜50話の長編執筆を破綻なく完走させる。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。  
**リグレッション防止**: 各コード変更ステップでは既存機能のリグレッションテストを作成し、CIパイプラインで自動検証を行う。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Schema | `src/domain/schemas/foreshadowing.py` | [MODIFY] グラフ可視化互換スキーマ（ノード/エッジ出力型）追加 |
| **Step 2** | Service | `src/services/foreshadowing_service.py` | [MODIFY] `get_foreshadowing_graph(book_id)` メソッド実装（AGE不要でグラフ生成） |
| **Step 3** | Router | `src/backend/routers/graph.py` | [MODIFY] `GET /api/graph` に `book_id` クエリ引数を追加し、RDBMS伏線・キャラから動的グラフ返却 |
| **Step 4** | Test | `tests/unit/api/test_graph_relational.py` | [NEW] RDBMSベース相関図APIの単体テスト（固定ダミー脱却検証） |
| **Step 5** | Service | `src/services/episode_context.py` | [MODIFY] 3層ローリング記憶ビルダー（Layer 1: バイブル, Layer 2: 100字要約, Layer 3: 直前生文）実装 |
| **Step 6** | Test | `tests/unit/services/test_episode_context_3layer.py` | [NEW] 3層コンテキストビルダーの単体テスト（トークン数抑制検証） |
| **Step 7** | Pipeline | `src/backend/writing_service.py` | [MODIFY] `EpisodeContextBuilder` を本文執筆パイプラインのプロンプト構築へ接続 |
| **Step 8** | Pipeline | `src/backend/writing_service.py` | [MODIFY] 執筆後に `ForeshadowingService.check_and_resolve` を呼び出して伏線を自動回収 |
| **Step 9** | Client | `frontend/src/api/graph.ts` | [MODIFY] `fetchGraphData(bookId)` に `book_id` を送信し `apiFetch` へ切り替え |
| **Step 10** | UI | `frontend/src/components/GraphVisualization.tsx` | [MODIFY] 選択中の `selectedBookId` を渡して実データ相関図を描画 |
| **Step 11** | Deprecate| `src/services/age_client.py` | [MODIFY] Apache AGE コードを安全にスタブ化し非推奨化警告を追加 |
| **Step 12** | E2E | `tests/integration/test_relational_memory_e2e.py` | [NEW] 1話〜5話での伏線自動回収と3層記憶維持の結合テスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: グラフ可視化スキーマ追加 (`src/domain/schemas/foreshadowing.py`)
- **目的**: RDBMSデータから直接 Force-Graph 向けのノード・エッジ JSON を生成するための型定義。
- **実装内容**:
```python
class GraphNodeSchema(AutoNovelBaseSchema):
    id: str
    label: str  # "Character", "Foreshadowing", "Location"
    properties: dict = {}

class GraphEdgeSchema(AutoNovelBaseSchema):
    source: str
    target: str
    type: str  # "PLANTED_IN", "RESOLVED_BY", "RELATED_TO"
    properties: dict = {}

class ForeshadowingGraphResponse(AutoNovelBaseSchema):
    graph_name: str
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
```
- **リグレッション防止**: 
  - 既存のスキーマ定義が変更されないことを確認するため、関連するユニットテストを作成または更新
  - スキーマの互換性を維持するためのテストケースを追加（他のサービスがこのスキーマに依存している場合）
- **検証コマンド**: 
  - `python -c "from src.domain.schemas.foreshadowing import ForeshadowingGraphResponse; print(ForeshadowingGraphResponse)"`
  - `python -m pytest tests/unit/schemas/test_foreshadowing.py -v` (スキーマテスト実行)

---

### Step 2: グラフ生成メソッド追加 (`src/services/foreshadowing_service.py`)
- **目的**: 作品IDに紐づく伏線（未回収・回収済み）および登場人物をクエリし、ノード・エッジ配列へ変換する。
- **検証コマンド**: `python -c "from src.services.foreshadowing_service import ForeshadowingService; print(hasattr(ForeshadowingService, 'get_foreshadowing_graph'))"`
- **リグレッション防止**: 
  - 既存のforeshadowingサービスのインターフェースが変更されないことを確認するため、ユニットテストを作成
  - メソッドの戻り値の型が期待通りであることを検証するテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/services/test_foreshadowing_service.py -v`

---

### Step 3: 相関図ルーターの RDBMS 連動 (`src/backend/routers/graph.py`)
- **目的**: `GET /api/graph` で `book_id` を必須/任意で受け取り、PostgreSQL/AGE がない環境でも実際の作品伏線グラフを返却する（固定ダミーを廃止）。
- **検証コマンド**: `python -c "from src.backend.routers.graph import router; print(router)"`
- **リグレッション防止**: 
  - 既存のエンドポイントのインターフェースが変更されないことを確認するため、API契約テストを作成
  - レスポンスフォーマットとステータスコードの互換性を維持するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/routers/test_graph.py -v`

---

### Step 4: ルーター単体テスト (`tests/unit/api/test_graph_relational.py`)
- **目的**: 指定した `book_id` の伏線データがノード・エッジとして正しく返却されることを検証。さらに、既存のグラフAPI機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（有効なbook_id）
  - 異常系テスト（無効なbook_id、存在しないbook_idなど）
  - リグレッションテスト（既存のグラフ生成ロジックが変更されないことを確認）
  - エッジケーステスト（空の伏線データ、大量のデータなど）
- **検証コマンド**: `pytest tests/unit/api/test_graph_relational.py`
- **リグレッション防止強化**: 
  - テストカバレッジを80%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 5: 3層ローリング記憶ビルダー (`src/services/episode_context.py`)
- **目的**:
  1. Layer 1（バイブル）: キャラクター・世界観設定（約1,000トークン）
  2. Layer 2（全話要約）: 過去全話の100文字事実要約＋未回収伏線一覧（累積しても数千トークン）
  3. Layer 3（直前文脈）: 直前1エピソードの生テキスト
  上記を合体させたプロンプトコンテキストを構築する。
- **検証コマンド**: `python -c "from src.services.episode_context import EpisodeContextBuilder; print(EpisodeContextBuilder)"`
- **リグレッション防止**: 
  - 既存のepisode_contextサービスのインターフェースが変更されないことを確認するため、ユニットテストを作成
  - 各層の機能が独立して動作することを検証するテストケースを追加
  - トークン数計算の正確性を維持するためのテストを追加
- **検証コマンド追加**: `python -m pytest tests/unit/services/test_episode_context.py -v`

---

### Step 6: 3層記憶ビルダー単体テスト (`tests/unit/services/test_episode_context_3layer.py`)
- **目的**: 1話目、10話目、30話目でのプロンプト構築とトークン長が想定内に収まっているかをテスト。さらに、既存の3層記憶ビルダー機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（各話数でのプロンプト構築）
  - 境界値テスト（第1話、第50話など）
  - リグレッションテスト（既存のトークン計算ロジックが変更されないことを確認）
  - エッジケーステスト（空のバイブル、極端に長いテキストなど）
- **検証コマンド**: `pytest tests/unit/services/test_episode_context_3layer.py`
- **リグレッション防止強化**: 
  - テストカバレッジを90%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 7: 執筆パイプラインへの3層記憶接続 (`src/backend/writing_service.py`)
- **目的**: 本文生成のシステムプロンプト構築時に `EpisodeContextBuilder.build_context` の出力を注入。
- **検証コマンド**: `python -c "from src.backend.writing_service import WritingService; print(WritingService)"`
- **リグレッション防止**: 
  - 既存のwriting_serviceのインターフェースが変更されないことを確認するため、ユニットテストを作成
  - プロンプト構築プロセスが変更されないことを検証するためのテストケースを追加
  - エピソードコンテキストの注入が正しく行われることをテスト
- **検証コマンド追加**: `pytest tests/unit/test_writing_services.py -v`

---

### Step 8: 本文生成後の伏線自動回収トリガー (`src/backend/writing_service.py`)
- **目的**: 本文生成が完了した直後に `ForeshadowingService.check_and_resolve` を呼び出し、回収された伏線を DB 上で `resolved` に更新。
- **検証コマンド**: `pytest tests/unit/test_writing_services.py`
- **リグレッション防止**: 
  - 既存のwriting_serviceの機能が変更されないことを確認するため、包括的なテストスイートを実行
  - 伏線自動回収のトリガー条件が変更されないことを検証するためのテストケースを追加
  - DB更新の原子性と整合性を維持するためのテストを追加
- **検証コマンド追加**: 
  - `pytest tests/unit/test_writing_service.py -v` (詳細な書き込みサービステスト実行)
  - `pytest tests/integration/test_writing_workflow.py -v` (ライティングワークフロー統合テスト実行)

---

### Step 9: フロントエンドAPIクライアント改修 (`frontend/src/api/graph.ts`)
- **目的**: `fetchGraphData(bookId)` で `book_id` パラメータを送信し、生 `fetch` を `apiFetch` へ切り替える。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 既存のAPIクライアント関数の変更が他のサービス呼び出しに影響しないことを確認するため、モックを使ったユニットテストを作成
  - エラーハンドリングとタイムアウト処理のリグレッションテストを追加
- **検証コマンド追加**: `cd frontend && npm test src/api/graph.test.ts`

---

### Step 10: 相関図UIの選択作品連動 (`frontend/src/components/GraphVisualization.tsx`)
- **目的**: コンテキストの `selectedBookId` を受け取り、現在選択中の作品の相関図を描画。
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/ExportConfirmModal.test.tsx`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/GraphVisualization.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 11: `age_client.py` 非推奨化 (`src/services/age_client.py`)
- **目的**: 過去のAGEクライアント呼び出し箇所に DeprecationWarning を付与し、RDBMSへの移行を明示。
- **検証コマンド**: `python -c "from src.services.age_client import age_client; print(age_client)"`
- **リグレッション防止**: 
  - 既存のAGEクライアントのインターフェースが変更されないことを確認するため、後方互換性テストを作成
  - DeprecationWarningが正しく出力されることを検証するためのテストケースを追加
  - AGEクライアントを使用している既存のコードが引き続き機能することを確認するためのテストを追加
- **検証コマンド追加**: `python -m pytest tests/unit/services/test_age_client.py -v`

---

### Step 12: 長編整合性E2E結合テスト (`tests/integration/test_relational_memory_e2e.py`)
- **目的**: 第1話で伏線を設置し、第3話で回収される一連のライフサイクルが自動実行されることを検証。さらに、システム全体のリグレッション防止のためのベースラインテストとして機能させる。
- **実装内容**: 
  - 正常系E2Eテスト（第1話で伏線設置→第3話で自動回収）
  - エラーケースE2Eテスト（不正な入力、システムエラー時の挙動）
  - パフォーマンスリグレッションテスト（応答時間が一定の閾値を超えないことを確認）
  - データ整合性リグレッションテスト（伏線状態がデータベースに正しく保存されることを確認）
  - クロスブラウザ互換性テスト（フロントエンド描画のリグレッションを検出）
- **検証コマンド**: `pytest tests/integration/test_relational_memory_e2e.py`
- **リグレッション防止強化**: 
  - E2EテストをCIパイプラインの必須チェック項目に追加
  - テスト結果のトレンドを監視し、パフォーマンスの劣化を早期検出
  - 本番環境と同等のデータ量でテストを実行し、スケーラビリティのリグレッションを防止
  - テストカバレッジレポートを生成し、重要なパスの見落としがないことを確認

---
### 🛡️ リグレッション防止戦略（全ステップ共通）

本実装計画では、以下のリグレッション防止策を全ステップにわたって実施します：

1. **段階的テスト追加**：各実装ステップにおいて、変更箇所に関するユニットテスト・統合テストを必ず追加または更新
2. **自動検証パイプライン**： 
   - プルリクエスト時に自動的にテストスイートを実行
   - テストカバレッジが基準値（80%）を下回る場合はマージをブロック
   - ビルド失敗時はデプロイを防止
3. **テスト種類の多様化**：
   - ユニットテスト：個別関数・クラスの動作検証
   - 統合テスト：モジュール間の連携検証
   - E2Eテスト：ユーザー視点での完全なワークフロー検証
   - ビジュアル回帰テスト：UIの意図しない変更検出（フロントエンド）
   - アクセシビリティテスト：a11y準拠のリグレッション防止
4. **継続的監視**：
   - テスト実行時間のトレンド監視（パフォーマンスリグレッション検出）
   - テスト失敗パターンの分析と予防的保守
   - 本番環境でのエラーレート監視とテストギャップの特定

この戦略により、伏線ステートマシン＆3層ローリング記憶機能の追加による既存機能への影響を最小限に抑え、高品質なリリースを継続的に実現します。
