# AutoNovel v5.0 実装計画書 T3: 構成共創 3ステップ・ファネル (全12ステップ)

**対象領域**: コア設計 3 (Creation Co-pilot 3-Step Funnel)  
**目的**: ChatGPT等の単なるチャット生成と決定的に差別化するため、「Step 1 企画ブレスト → Step 2 商業ビートシート確定 → Step 3 本文執筆＆縦書きEPUB 3納品」の3ステップ共創UIを実動化し、メイン画面へ統合する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。  
**リグレッション防止**: 各コード変更ステップでは既存機能のリグレッションテストを作成し、CIパイプラインで自動検証を行う。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Router | `src/backend/routers/plots.py` | [MODIFY] `POST /api/plots/expand-beats` 商業12ステップビート生成エンドポイント新設 |
| **Step 2** | Router | `src/backend/routers/stream_writing.py` | [MODIFY] 実パイプライン進行状況と連動したSSEストリーミングAPI実装 |
| **Step 3** | Test | `tests/unit/api/test_plots_expand_beats.py` | [NEW] 商業ビート生成APIの単体テスト |
| **Step 4** | Client | `frontend/src/api/wizard.ts` | [NEW] ウィザード用APIクライアント（企画保存、ビート生成、SSE接続） |
| **Step 5** | Component | `frontend/src/components/wizard/Step1PlotInput.tsx` | [MODIFY] 入力バリデーション強化とローディング・ジャンル連動 |
| **Step 6** | Component | `frontend/src/components/wizard/Step2StructureReview.tsx` | [MODIFY] ビート編集（追加・削除・並び替え）機能の有効化 |
| **Step 7** | Component | `frontend/src/components/common/StreamingProgressBar.tsx` | [MODIFY] SSEイベントリスナーとの結合プロップス追加 |
| **Step 8** | Component | `frontend/src/components/wizard/Step3InteractiveWriting.tsx` | [MODIFY] SSE進捗バー組み込みとリアルタイム本文反映 |
| **Step 9** | Page | `frontend/src/pages/WizardWorkflowPage.tsx` | [MODIFY] モック配列を廃止し、Step 1〜3をバックエンドAPIと完全結合 |
| **Step 10** | Nav | `frontend/src/App.tsx` | [MODIFY] 「共創ウィザード」起動導線（モード切替または新規作成モーダル）を追加 |
| **Step 11** | Test | `frontend/tests/components/WizardWorkflowPage.test.tsx` | [NEW] ウィザードの3ステップ進行テスト |
| **Step 12** | E2E | `tests/integration/test_wizard_creation_funnel.py` | [NEW] 企画→ビート確定→執筆のE2Eテスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: 商業ビート生成エンドポイント新設 (`src/backend/routers/plots.py`)
- **目的**: 企画パラメータ（チート度・成長曲線・代償過酷度）を受け取り、12ステップの商業ビートシート（五感フォーカス・クリフハンガー種別付き）を即時生成する。
- **実装内容**:
```python
class ExpandBeatsRequest(BaseModel):
    title: str
    genre: str
    synopsis: str
    target_chapters: int = 20
    cheat_scale: int = 4
    growth_curve: str = "最初からカンスト(無双)"
    system_assist: int = 70
    cost_severity: int = 2

class BeatItemSchema(BaseModel):
    episode: int
    title: str
    outline: str
    cliffhanger_type: str
    sensory_focus: list[str]
    foreshadowing_notes: str = ""

@router.post("/expand-beats", response_model=list[BeatItemSchema])
async def expand_commercial_beats(req: ExpandBeatsRequest):
    ...
```
- **リグレッション防止**: 
  - 既存のplotsルーターのエンドポイントが変更されないことを確認するため、API契約テストを作成
  - 新しいエンドポイントの追加が既存のエンドポイントに影響しないことを確認するためのテストケースを追加
- **検証コマンド**: 
  - `python -c "from src.backend.routers.plots import router; print(router)"`
  - `python -m pytest tests/unit/routers/test_plots.py -v` (既存のplotsルーターテスト実行)

---

### Step 2: SSEストリーミングの実動化 (`src/backend/routers/stream_writing.py`)
- **目的**: 固定スリープではなく、実際のコンテキスト構築・執筆・監査の各フェーズの完了に応じてイベントを yield する。
- **検証コマンド**: `python -c "from src.backend.routers.stream_writing import router; print(router)"`
- **リグレッション防止**: 
  - 既存のstream_writingルーターのインターフェースが変更されないことを確認するため、ユニットテストを作成
  - SSEストリーミング機能の変更が他のストリーミングエンドポイントに影響しないことを確認するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/routers/test_stream_writing.py -v`

---

### Step 3: ビート生成単体テスト (`tests/unit/api/test_plots_expand_beats.py`)
- **目的**: 企画パラメータに応じた12ステップのビートシートが正しく生成されることを検証。さらに、既存のビート生成ロジックに対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（各ジャンルでのビート生成）
  - 異常系テスト（不正な入力パラメータ）
  - リグレッションテスト（既存のビート生成ロジックが変更されないことを確認）
  - エッジケーステスト（極端な値、空の入力など）
- **検証コマンド**: `pytest tests/unit/api/test_plots_expand_beats.py`
- **リグレッション防止強化**: 
  - テストカバレッジを80%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 4: ウィザード用APIクライアント (`frontend/src/api/wizard.ts`)
- **目的**: `expandBeats()`, `saveWizardBook()`, `subscribeWritingStream()` の型安全クライアントを新規作成。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 既存のAPIクライアントが変更されないことを確認するため、モックを使ったユニットテストを作成
  - 新しいクライアント関数の追加が既存のAPIクライアントに影響しないことを確認するためのテストケースを追加
- **検証コマンド追加**: `cd frontend && npm test src/api/wizard.test.ts`

---

### Step 5: Step 1 企画入力UI強化 (`frontend/src/components/wizard/Step1PlotInput.tsx`)
- **目的**: 入力必須チェックと、「AIアイデア生成中...」のスピナー表示を追加。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/wizard/Step1PlotInput.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 6: Step 2 構成レビューUI強化 (`frontend/src/components/wizard/Step2StructureReview.tsx`)
- **目的**: 生成されたビートシートのドラッグ並び替え、クリフハンガー種別の選択変更を可能にする。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確保するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/wizard/Step2StructureReview.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 7: プログレスバー改修 (`frontend/src/components/common/StreamingProgressBar.tsx`)
- **目的**: SSE接続ステータス（接続中、受信中、完了、エラー）と経過秒数の自動カウント機能を追加。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/common/StreamingProgressBar.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 8: Step 3 対話型執筆UI接続 (`frontend/src/components/wizard/Step3InteractiveWriting.tsx`)
- **目的**: `StreamingProgressBar` を組み込み、ストリーミング本文生成とリテイクボタンを実動化。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/wizard/Step3InteractiveWriting.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 9: ウィザード統合ページ実動化 (`frontend/src/pages/WizardWorkflowPage.tsx`)
- **目的**: ハードコードされたダミー配列を全廃。Step 1完了時に `POST /api/plots/expand-beats` を呼び出し、Step 2確認時にプロジェクトと章データをDB保存してStep 3へ遷移。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - ページコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のページインターフェースが変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/pages/WizardWorkflowPage.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 10: メイン画面導線統合 (`frontend/src/App.tsx`)
- **目的**: ヘッダーまたは初期画面に「✨ 3ステップ共創ウィザードを開始」ボタンを配置し、`WizardWorkflowPage` へ切り替え可能にする。
- **検証コマンド**: `cd frontend && npm run build`
- **リグレッション防止**: 
  - メインアプリケーションコンポーネントの変更が既存のナビゲーションやレイアウトに影響しないことを確認するため、包括的なUIテストを実行
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のルーティング機能が変更されないことを確認するためのテストケースを追加
- **検証コマンド追加**: 
  - `cd frontend && npm test src/App.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 11: ウィザード単体テスト (`frontend/tests/components/WizardWorkflowPage.test.tsx`)
- **目的**: Step 1 入力 → Step 2 ビート確認 → Step 3 執筆開始の画面遷移をテスト。さらに、既存のウィザード機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 画面遷移テスト（各ステップ間の正常な遷移）
  - フォームバリデーションテスト（入力チェックとエラーメッセージ）
  - リグレッションテスト（既存のウィザードロジックが変更されないことを確認）
  - エッジケーステスト（ネットワークエラー、タイムアウトなど）
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/WizardWorkflowPage.test.tsx`
- **リグレッション防止強化**: 
  - コンポーネントのテストカバレッジを90%以上維持することを確認
  - ビジュアル回帰テストツール（例: Chromatic, Percy）の導入を検討
  - テスト失敗時に詳細なレポートを生成する設定を追加

---

### Step 12: 創作ファネルE2Eテスト (`tests/integration/test_wizard_creation_funnel.py`)
- **目的**: APIとフロントエンドを通じた企画〜執筆の完走テスト。さらに、システム全体のリグレッション防止のためのベースラインテストとして機能させる。
- **実装内容**: 
  - 正常系E2Eテスト（企画→ビート確定→執筆の完全フロー）
  - エラーケースE2Eテスト（ネットワークエラー、バックエンドエラー時の挙動）
  - パフォーマンスリグレッションテスト（応答時間が一定の閾値を超えないことを確認）
  - データ整合性リグレッションテスト（ウィザードデータがデータベースに正しく保存されることを確認）
  - クロスブラウザ互換性テスト（フロントエンド描画のリグレッションを検出）
- **検証コマンド**: `pytest tests/integration/test_wizard_creation_funnel.py`
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

この戦略により、構成共創3ステップ・ファネル機能の追加による既存機能への影響を最小限に抑え、高品質なリリースを継続的に実現します。
