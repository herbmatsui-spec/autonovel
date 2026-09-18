# AutoNovel v5.0 実装計画書 T1: 二層ハイブリッド監査 (全12ステップ)

**対象領域**: コア設計 1 (Two-Tier Hybrid Audit)  
**目的**: 静的ルール解析（SudachiPy / 0ms / 0円）と定性特化シングルLLM（1回呼出）を執筆パイプラインおよびフロントエンドUI（`ConflictReportPanel`）へ完全結合する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。  
**リグレッション防止**: 各コード変更ステップでは既存機能のリグレッションテストを作成し、CIパイプラインで自動検証を行う。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Model | `src/models/unified_audit.py` | [MODIFY] フロントエンド `ConflictReport` 互換フィールド（`category`, `severity`, `conflicts`）を追加 |
| **Step 2** | Agent | `src/agents/specialists/unified_auditor.py` | [MODIFY] 互換フォーマット出力メソッド `to_conflict_report()` 実装 |
| **Step 3** | Router | `src/backend/routers/editor.py` | [MODIFY] `POST /api/editor/audit` の入力スキーマ（`AuditRequest`）とレスポンス正規化 |
| **Step 4** | Test | `tests/unit/api/test_unified_auditor_endpoint.py` | [NEW] 二層監査エンドポイント単体テスト |
| **Step 5** | Type | `frontend/src/types/editor.ts` | [MODIFY] `UnifiedAuditReport` / `ConflictReport` 型の同期定義 |
| **Step 6** | Client | `frontend/src/api/editor.ts` | [MODIFY] `runHybridAudit(bookId, draftText)` APIクライアント関数実装 (`apiFetch` 使用) |
| **Step 7** | Component | `frontend/src/components/editor/ConflictReportPanel.tsx` | [MODIFY] 監査実行ボタンおよび空状態のUI改善 |
| **Step 8** | Component | `frontend/src/components/studio/StudioWorkspace.tsx` | [MODIFY] `tab === "audit"` に `ConflictReportPanel` を配備しステート結合 |
| **Step 9** | Component | `frontend/src/components/editor/EditorialSidebar.tsx` | [MODIFY] 「二層監査を実行」ボタンをサイドバーに追加し結果連携 |
| **Step 10** | Service | `src/backend/writing_service.py` | [MODIFY] 執筆完了時に `UnifiedAuditor.audit_quantitative` を自動実行しメタデータに記録 |
| **Step 11** | Test | `frontend/tests/components/ConflictReportPanel.test.tsx` | [NEW] パネル表示・承認/却下アクションの単体テスト |
| **Step 12** | E2E | `tests/integration/test_hybrid_audit_e2e.py` | [NEW] テキスト入力→静的解析＋LLM定性評価→フロント描画の結合テスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: スキーマ拡張 (`src/models/unified_audit.py`)
- **目的**: フロントエンド `ConflictReportPanel` でそのまま描画できる差分・警告構造をスキーマに追加。
- **実装内容**:
```python
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class ConflictItemSchema(BaseModel):
    category: str = Field(..., description="カテゴリ (rhythm, dialogue, cliche, hook, character)")
    severity: str = Field(..., description="重要度 (critical, high, medium, low)")
    title: str = Field(..., description="指摘タイトル")
    description: str = Field(..., description="詳細説明")
    field_path: Optional[str] = None
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    evidence_past: str = ""
    evidence_current: str = ""
    constraint_for_next: str = ""
    confidence: float = 0.9

class QualitativeAudit(BaseModel):
    hook_score: float = Field(..., ge=0.0, le=100.0, description="読者引き込み度")
    emotional_score: float = Field(..., ge=0.0, le=100.0, description="感情曲線の自然さ")
    character_consistency: float = Field(..., ge=0.0, le=100.0, description="キャラ言動の一貫性")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="定性総合評価")
    critique: str = Field(default="", description="主要講評")
    actionable_patch: str | None = Field(default=None, description="推奨局所修正パッチ")

class UnifiedAuditReport(BaseModel):
    is_acceptable: bool
    final_score: float
    quantitative_score: float
    qualitative: QualitativeAudit
    detected_cliches: list[str] = Field(default_factory=list)
    dialogue_ratio: float = 0.0
    conflicts: list[ConflictItemSchema] = Field(default_factory=list)
```
- **リグレッション防止**: 既存のスキーマ変更が他のモデルやサービスに影響しないことを確認するため、関連するユニットテストを作成または更新
- **検証コマンド**: 
  - `python -c "from src.models.unified_audit import UnifiedAuditReport; print(UnifiedAuditReport)"`
  - `python -m pytest tests/unit/test_models.py -v` (既存モデルテスト実行)

---

### Step 2: 監査結果の差分アイテム化 (`src/agents/specialists/unified_auditor.py`)
- **目的**: 静的ルール解析結果（文長・台詞率・AI臭い語尾）を `ConflictItemSchema` に自動変換し、フロントで即座に指摘行・修正案を表示できるようにする。
- **検証コマンド**: `python -c "from src.agents.specialists.unified_auditor import UnifiedAuditor; a = UnifiedAuditor(); print(a)"`
- **リグレッション防止**: 
  - 既存の監査ロジックが変更されないことを確認するため、ユニットテストを作成
  - 静的ルール解析結果の変換精度を維持するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/agents/test_unified_auditor.py -v`

---

### Step 3: ルーターリクエストの型付け (`src/backend/routers/editor.py`)
- **目的**: `POST /api/editor/audit` のリクエストボディを Pydantic モデル化（`AuditFastHybridRequest`）し、Swagger/OpenAPI から正しく型出力できるようにする。
- **検証コマンド**: `python -c "from src.backend.routers.editor import router; print(router.prefix)"`
- **リグレッション防止**: 
  - 既存のエンドポイントのインターフェースが変更されないことを確認するため、API契約テストを作成
  - リクエスト/レスポンスの型変換が正しく動作することを確認するテストを追加
- **検証コマンド追加**: `python -m pytest tests/unit/api/test_editor_router.py -v`

---

### Step 4: ルーター単体テスト (`tests/unit/api/test_unified_auditor_endpoint.py`)
- **目的**: `POST /api/editor/audit` の単体テストを作成し、正常応答とスコア計算を確認。さらに、既存の監査機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（通常のテキスト入力）
  - 異常系テスト（不正な入力、空のテキストなど）
  - リグレッションテスト（既存の監査ロジックが変更されないことを確認）
  - エッジケーステスト（極端な値、特殊文字など）
- **検証コマンド**: `pytest tests/unit/api/test_unified_auditor_endpoint.py`
- **リグレッション防止強化**: 
  - テストカバレッジを80%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 5: フロントエンド型定義同期 (`frontend/src/types/editor.ts`)
- **目的**: バックエンドの `UnifiedAuditReport` とフロントエンドの `ConflictReport` の型定義を一致させる。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 型定義の変更が他のコンポーネントやサービスに影響しないことを確認するため、型チェックテストを実行
  - バックエンドとフロントエンドの型定義の不整合を検出する自動テストをCIに組み込む
- **検証コマンド追加**: 
  - `cd frontend && npm run type-check` (型チェックスクリプト実行)
  - `cd frontend && npm run test:types` (型テスト実行、存在する場合)

---

### Step 6: APIクライアント実装 (`frontend/src/api/editor.ts`)
- **目的**: `apiFetch` を使って `POST /api/editor/audit` を呼び出す `runHybridAudit` 関数を実装（認証ヘッダーを自動付与）。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 既存のAPIクライアント関数の変更が他のサービス呼び出しに影響しないことを確認するため、モックを使ったユニットテストを作成
  - エラーハンドリングとタイムアウト処理のリグレッションテストを追加
- **検証コマンド追加**: `cd frontend && npm test src/api/editor.test.ts`

---

### Step 7: 監査パネルUI改善 (`frontend/src/components/editor/ConflictReportPanel.tsx`)
- **目的**: レポートが空の場合に「🧠 AI二層診断を実行する」ボタンを表示し、ワンクリックで診断を起動できるようにする。
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/ExportConfirmModal.test.tsx`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm run test:components` (コンポーネントテストスイート実行)
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 8: StudioWorkspace配備 (`frontend/src/components/studio/StudioWorkspace.tsx`)
- **目的**: `tab === "audit"` のプレースホルダーテキストを撤廃し、`<ConflictReportPanel />` を正式配置。
- **検証コマンド**: ブラウザ上で Studio モード「🧠 矛盾診断レポート」タブを開き、コンポーネントが描画されることを確認。
- **リグレッション防止**: 
  - 他のタブ（執筆、プロットなど）のレイアウトや機能が変更されないことを確認するため、StudioWorkspace全体のスナップショットテストを実行
  - タブ切り替え機能のリグレッションテストを追加
- **検証コマンド追加**: 
  - `cd frontend && npm test frontend/tests/components/studio/StudioWorkspace.test.tsx`
  - ブラウザ上で他のタブが正常に動作することを確認

---

### Step 9: サイドバー連携 (`frontend/src/components/editor/EditorialSidebar.tsx`)
- **目的**: 右ペインのAI編集者サイドバーから「二層ハイブリッド監査」をトリガーし、結果を `ConflictReportPanel` へ受け渡す。
- **検証コマンド**: サイドバーの診断ボタンからタブ切り替えと結果表示が連動することを確認。
- **リグレッション防止**: 
  - サイドバーの他の機能（プロット提案、キャラクター管理など）が変更されないことを確認するため、サイドバーコンポーネントの包括的テストを実行
  - イベントハンドリングと状態遷移のリグレッションテストを追加
- **検証コマンド追加**: 
  - `cd frontend && npm test frontend/tests/components/editor/EditorialSidebar.test.tsx`
  - サイドバーの他のボタンや機能が正常に動作することを確認

---

### Step 10: 執筆パイプライン自動監査接続 (`src/backend/writing_service.py`)
- **目的**: 本文生成直後に `UnifiedAuditor.audit_quantitative` を自動実行し、レスポンスにスコアと警告一覧を付与。
- **検証コマンド**: `pytest tests/unit/test_writing_services.py`
- **リグレッション防止**: 
  - 執筆パイプラインの他のステップ（プロット生成、キャラクター開発など）が変更されないことを確認するため、ライティングサービスの包括的テストを実行
  - 自動監査のトリガー条件と頻度のリグレッションテストを追加
  - 監査結果がメタデータに正しく記録されることを確認するテストを追加
- **検証コマンド追加**: 
  - `pytest tests/unit/test_writing_service.py -v` (詳細な書き込みサービステスト実行)
  - `pytest tests/integration/test_writing_workflow.py -v` (ライティングワークフロー統合テスト実行)

---

### Step 11: パネル単体テスト (`frontend/tests/components/ConflictReportPanel.test.tsx`)
- **目的**: レポートの差分表示、緊急度バッジ（緊急/高/中/低）、承認・却下ボタンの動作をVitestでテスト。さらに、既存のパネル機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 基本的な表示テスト（レポートが空の場合、データがある場合）
  - インタラクションテスト（承認ボタン、却下ボタンのクリックハンドラー）
  - リグレッションテスト（既存のスタイル、レイアウト、アクセシビリティが変更されないことを確認）
  - スナップショットテスト（UIの視覚的リグレッションを検出）
  - 国際化（i18n）リグレッションテスト（存在する場合）
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/ConflictReportPanel.test.tsx`
- **リグレッション防止強化**: 
  - コンポーネントのテストカバレッジを90%以上維持することを確認
  - ビジュアル回帰テストツール（例: Chromatic, Percy）の導入を検討
  - テスト失敗時に詳細なレポートを生成する設定を追加

---

### Step 12: 二層監査E2E結合テスト (`tests/integration/test_hybrid_audit_e2e.py`)
- **目的**: テキスト入力から二層監査実行、指摘項目の生成、修正パッチの適用までの全結合テスト。さらに、システム全体のリグレッション防止のためのベースラインテストとして機能させる。
- **実装内容**: 
  - 正常系E2Eテスト（典型的な小説テキスト入力から監査結果表示まで）
  - エラーケースE2Eテスト（不正な入力、システムエラー時の挙動）
  - パフォーマンスリグレッションテスト（応答時間が一定の閾値を超えないことを確認）
  - データ整合性リグレッションテスト（監査結果がデータベースに正しく保存されることを確認）
  - クロスブラウザ互換性テスト（フロントエンド描画のリグレッションを検出）
- **検証コマンド**: `pytest tests/integration/test_hybrid_audit_e2e.py`
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

この戦略により、二層ハイブリッド監査機能の追加による既存機能への影響を最小限に抑え、高品質なリリースを継続的に実現します。
