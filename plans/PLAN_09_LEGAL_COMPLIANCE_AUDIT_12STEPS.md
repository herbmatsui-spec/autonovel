# PLAN 09: 規約遵守＆出版法務コンプライアンス 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 法務コンプライアンス・創作証跡・納品基盤  
**目的**: カクヨムのAI生成ガイドラインや大型商業コンテスト（カクコン等）の応募規約、および出版社の法務・契約審査を突破するため、人間の関与比率（Human-in-the-Loop）を証明するGit風編集証跡と、確率的平滑化を破壊するヒューマナイズ・ポストプロセッサを実装する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/compliance.py` (新規) | 創作監査ログ、加筆修正Diff、規約診断結果のPydanticモデル定義 |
| **2** | テスト | `tests/unit/compliance/test_audit_trail.py` (新規) | 人間加筆Diffの記録と人間関与比率計算の単体テスト作成（TDD先行） |
| **3** | ロジック | `src/services/compliance/audit_trail_tracker.py` (新規) | プロット、AI下書き、人間による編集履歴をタイムスタンプ付きで記録するサービス |
| **4** | テスト | `tests/unit/compliance/test_humanize_postprocessor.py` (新規) | 統計的平滑化を崩すヒューマナイズ処理の単体テスト作成 |
| **5** | 後処理 | `src/services/anti_ai/humanize_postprocessor.py` (新規) | 均等な文長・読点リズムを意図的に崩し人間の手書き特有の呼吸を再現する処理 |
| **6** | テスト | `tests/unit/compliance/test_kakuyomu_policy_checker.py` (新規) | カクヨム規約・コンテスト応募要件の自動照合テスト |
| **7** | 診断器 | `src/services/compliance/kakuyomu_policy_checker.py` (新規) | カクヨムAIタグ付け義務判定＆コンテスト適格性スコアリング機 |
| **8** | レポート | `src/services/compliance/report_generator.py` (新規) | 出版社法務提出用の「創作プロセス証明書（Markdown/PDF）」生成サービス |
| **9** | エクスポート | `src/agents/marketing.py` (修正) | ワンクリック納品ZIPに `06_創作プロセス証明書.md` を自動格納する改修 |
| **10** | ルーター | `src/backend/routers/compliance.py` (新規) | 規約診断結果取得・編集証跡ログ出力のFastAPIエンドポイント |
| **11** | フロント | `frontend/src/components/compliance/ComplianceDashboard.tsx` (新規) | 人間関与比率メーター（%）＆コンテスト応募適格性チェックパネルUI |
| **12** | 統合検証 | `tests/e2e/test_compliance_audit_pipeline.py` (新規) | 執筆 → 加筆 → 証跡記録 → 証明書ZIP同封までのE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/compliance.py`)
* **目標**: 創作の正当性を証明するメタデータ型を定義。
* **実装内容**:
  ```python
  from datetime import datetime
  from pydantic import BaseModel, Field

  class EditDiffLog(BaseModel):
      timestamp: datetime
      editor_type: str = Field(..., description="human または ai_assistant")
      action: str = Field(..., description="initial_draft, manual_rewrite, prompt_direction 等")
      diff_chars_added: int
      diff_chars_deleted: int

  class CreationAuditTrail(BaseModel):
      book_id: int
      total_word_count: int
      human_contribution_ratio: float = Field(..., ge=0.0, le=1.0, description="人間の加筆・ディレクション関与比率")
      history: list[EditDiffLog]

  class PolicyComplianceResult(BaseModel):
      kakuyomu_ai_tag_required: bool
      kakukon_eligible: bool = Field(..., description="カクヨムWeb小説コンテスト応募適格性")
      legal_risk_level: str = Field(..., description="LOW, MEDIUM, HIGH")
      compliance_notes: list[str]
  ```
* **受け入れ基準**: `mypy src/models/compliance.py` がエラーなく通ること。

---

### Step 2: 監査ログ記録テスト作成 (`tests/unit/compliance/test_audit_trail.py`)
* **目標**: AI下書きに対して人間が加筆した際、関与比率が正しく計算されるか検証。
* **実装内容**:
  - 3,000文字の下書きに対し、人間が600文字修正・追記した場合に関与比率（約20%）が記録されることをテスト。
* **受け入れ基準**: テストファイルが正しく実行できること。

---

### Step 3: 創作証跡トラッカー (`src/services/compliance/audit_trail_tracker.py`)
* **目標**: 作品の変更履歴をGitのコミットログのように追跡・集計する。
* **実装内容**:
  - `record_edit_event(book_id, editor_type, before_text, after_text)`
  - 文字数差分（Levenshtein距離またはdifflib）から人間関与率を自動算出。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 4: ヒューマナイズ処理テスト作成 (`tests/unit/compliance/test_humanize_postprocessor.py`)
* **目標**: 均一すぎる文末や読点リズムが、人間らしい不規則なリズムに変換されるか検証。
* **実装内容**:
  - 5文連続で同じ長さ（約40字）の文章が、短文・体言止め・感情的倒置により揺らぎを持つようになることを検証。
* **受け入れ基準**: テストがモジュール未定義で正しく失敗すること。

---

### Step 5: ヒューマナイズ・ポストプロセッサ (`src/services/anti_ai/humanize_postprocessor.py`)
* **目標**: 確率的平滑化（AI特有の平均化構文）を破壊し、手書きの熱量を付与する。
* **実装内容**:
  - `humanize_prose(text: str) -> str`
  - 3行以上の均等文長を検知した場合、1文を極端に短い1語の行（「ありえない。」「死んだ。」等）に分割。
  - 規則正しすぎる接続詞「しかし」「そのため」の半数を省略または口語の息継ぎに置換。
* **受け入れ基準**: Step 4 のテストが通過すること。

---

### Step 6: 規約照合テスト作成 (`tests/unit/compliance/test_kakuyomu_policy_checker.py`)
* **目標**: 人間関与比率に応じたカクヨム規約・コンテスト適格性診断をテスト。
* **実装内容**:
  - 人間関与率が30%以上で、ヒューマナイズ済みの場合に `kakukon_eligible=True`（コンテスト応募推奨）となることを検証。
* **受け入れ基準**: テストが正しく実行できること。

---

### Step 7: カクヨム規約診断器 (`src/services/compliance/kakuyomu_policy_checker.py`)
* **目標**: 現在の原稿がカクヨムのAIポリシー・コンテスト規定を満たしているか判定。
* **実装内容**:
  - カクヨム最新ガイドライン（人間が創作的主体であるか否か）に照らし合わせ、タグ付けの要否とコンテスト応募時の注意点をアドバイス。
* **受け入れ基準**: Step 6 のテストが通過すること。

---

### Step 8: 創作プロセス証明レポート生成 (`src/services/compliance/report_generator.py`)
* **目標**: 出版社編集部・法務部へ提示できる公的体裁の証明ドキュメントを作成。
* **実装内容**:
  - 作品名、著者名、各話の人間加筆履歴、AIアシスタント使用範囲、著作権帰属の主張ステートメントをMarkdown形式で整形。
* **受け入れ基準**: レポート文字列が抜け漏れなく生成されること。

---

### Step 9: 納品ZIPパッケージへの統合 (`src/agents/marketing.py`)
* **目標**: `MarketingAgent.create_export_package` のZIP内に証明書を同封。
* **実装内容**:
  - `06_創作プロセス証明書.md` をZIPアーカイブに自動追加。
* **受け入れ基準**: エクスポートされたZIPを解凍して証明書が存在すること。

---

### Step 10: FastAPIルーター (`src/backend/routers/compliance.py`)
* **目標**: コンプライアンス診断用APIエンドポイントを新設。
* **実装内容**:
  - `GET /api/compliance/status/{book_id}`: 規約診断結果と人間関与比率の取得
  - `GET /api/compliance/report/{book_id}`: 創作プロセス証明書のプレビュー取得
* **受け入れ基準**: `TestClient` で 200 OK が返ること。

---

### Step 11: コンプライアンスダッシュボードUI (`frontend/src/components/compliance/ComplianceDashboard.tsx`)
* **目標**: 作家が「自分の関与比率」と「コンテスト応募可否」を一目で確認できるUI。
* **実装内容**:
  - 「人間関与比率：38%（安全圏）」円グラフ表示。
  - 「カクヨムWeb小説コンテスト適格性：合格（人間が主導する創作物）」グリーンシールド表示。
  - 「創作プロセス証明書をダウンロード」ボタン。
* **受け入れ基準**: UIがエラーなくレンダリングされること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_compliance_audit_pipeline.py`)
* **目標**: 執筆から加筆ログ記録、ポストプロセッサ適用、ZIP同封までの一連の流れを検証。
* **実装内容**:
  - 執筆実行 → 手動加筆イベント送信 → 納品ZIP生成 → ZIP内に `06_創作プロセス証明書.md` が含まれることを検証。
* **受け入れ基準**: `pytest tests/e2e/test_compliance_audit_pipeline.py` が ALL GREEN。
