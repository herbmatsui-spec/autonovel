# PLAN 13: 外部投稿サイト規約遵守・投稿アシスタント化＆コンプライアンス基盤 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 外部パブリッシング基盤、規約準拠投稿アシスタント、法務ドキュメント  
**目的**: 「小説家になろう」「カクヨム」等の利用規約に抵触する非公式自動スクレイピング投稿を廃止し、アカウントBANリスクゼロの「半自動投稿アシスタント（クリップボード自動整形・予約投稿チェックリスト）」へ安全に移行する。併せて文化庁ガイドラインおよび各投稿サイトのAI開示義務に対応する。  
**前提**: ユーザー自身が各プラットフォーム上で最終投稿を行うフローとし、プラットフォーム側の仕様変更に強く、法的安全性の高い設計。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/publishing_assistant.py` (新規) | 投稿先別フォーマット（前書き・本文・後書き）、AI開示メタデータのPydanticモデル定義 |
| **2** | 規約定義 | `src/config/platform_compliance_rules.py` (新規) | カクヨム・なろう・KDPの最新利用規約（文字数制限、禁止文字、AI開示文言）辞書 |
| **3** | 整形エンジン | `src/services/publishing/content_splitter.py` (新規) | 小説本文から「あらすじ」「前書き」「本文」「後書き」「次回予告」を自動抽出・構造化 |
| **4** | AI開示生成 | `src/services/publishing/ai_disclosure_generator.py` (新規) | プラットフォームごとの推奨AI利用明記文（キャプション・後書き用）の自動生成 |
| **5** | 規約チェッカー | `src/services/publishing/compliance_validator.py` (新規) | プラットフォーム規約（R15/R18表現、タイトル文字数、ガイドライン違反）の事前検査 |
| **6** | 旧ロジック廃止 | `src/backend/routers/commercial.py` (修正) | セレニウム/自動ログインによる危険な自動投稿エンドポイントの安全な非推奨化・削除 |
| **7** | 新規API | `src/backend/routers/publishing_assistant.py` (新規) | プラットフォーム別クリップボード整形データおよびチェックリスト提供API |
| **8** | 法務文書 | `docs/legal/TERMS_OF_SERVICE.md` (新規) | AI生成物の著作権帰属、免責事項、商用利用規約ドラフト |
| **9** | プライバシー | `docs/legal/PRIVACY_POLICY.md` (新規) | 作家データの非学習保証（Zero Data Retention）および個人情報保護方針ドラフト |
| **10** | フロントUI | `frontend/src/components/publishing/PublishAssistantModal.tsx` (新規) | カクヨム/なろう別タブ、ワンクリックコピー、AI開示チェックボックスUI |
| **11** | ガイドUI | `frontend/src/components/publishing/SubmissionChecklist.tsx` (新規) | 「AIタグ付与」「文字数確認」等の投稿前チェックリスト＆ダイレクトリンク |
| **12** | 統合検証 | `tests/unit/test_publishing_assistant.py` (新規) | プラットフォーム別分割精度、AI開示テキスト生成、規約バリデーションの単体テスト |

---

## 各ステップの詳細仕様

### Step 1: 投稿アシスタント用Pydanticモデル定義 (`src/models/publishing_assistant.py`)
* **目標**: プラットフォーム別の投稿フォーマットとAI利用申告の型定義。
* **実装内容**:
  ```python
  from __future__ import annotations
  from enum import Enum
  from pydantic import BaseModel, Field

  class TargetPlatform(str, Enum):
      KAKUYOMU = "kakuyomu"
      NAROU = "narou"
      ALPHAPOLIS = "alphapolis"
      KINDLE = "kindle"

  class FormattedChapterPayload(BaseModel):
      platform: TargetPlatform
      chapter_title: str
      foreword: str = Field("", description="前書き（前話のおさらい等）")
      main_content: str = Field(..., description="プラットフォーム記法適用済み本文")
      afterword: str = Field("", description="後書き（AI利用明記、次回予告）")
      char_count: int
      ai_disclosure_statement: str
      validation_warnings: list[str] = Field(default_factory=list)
  ```
* **受け入れ基準**: `mypy src/models/publishing_assistant.py` でエラーゼロ。

---

### Step 2: プラットフォーム規約ルール辞書 (`src/config/platform_compliance_rules.py`)
* **目標**: 各投稿サイトの制限事項（タイトル長、話数ごとの上限、AI規定）を定義。
* **実装内容**:
  - `KAKUYOMU`: 1話10万文字以内、タイトル100文字以内、AI利用作品タグ必須（自主企画・タグ対応）。
  - `NAROU`: 1話10万文字以内、タイトル100文字以内、AI生成作品フラグの付与要件、18禁表現のR18（ノクターン/ムーンライト）分離ルール。
* **受け入れ基準**: 各プラットフォームの定数が正しく取得できること。

---

### Step 3: 前書き・本文・後書き自動分割エンジン (`src/services/publishing/content_splitter.py`)
* **目標**: 1つの生成テキストから投稿枠（前書き・本文・後書き）へ自動マッピング。
* **実装内容**:
  - `【前書き】` や `【後書き】`、`――次回予告――` などのマーカーを検出し、プラットフォームの入力欄に合わせて文字列を分離。
  - ルビ記法の自動相互変換（カクヨム記法 `|漢字《ルビ》` ⇔ なろう記法 `漢字(るび)`）。
* **受け入れ基準**: マーカーの有無に関わらず、本文が欠落することなく正しく分割されること。

---

### Step 4: AI開示文言ジェネレーター (`src/services/publishing/ai_disclosure_generator.py`)
* **目標**: 文化庁ガイドラインおよび投稿サイト規約に適合した適切なAI利用表示を生成。
* **実装内容**:
  ```python
  def generate_disclosure(platform: TargetPlatform, ai_role: str = "assisted") -> str:
      if platform == TargetPlatform.KAKUYOMU:
          return "※本作はAIツール（AutoNovel）による構成・執筆支援を活用して制作しています。"
      elif platform == TargetPlatform.NAROU:
          return "【AI生成・支援に関する表記】本作はAI支援ツールを用いてプロット構築および推敲を行っています。"
      return "Generated / Assisted with AI (AutoNovel)"
  ```
* **受け入れ基準**: プラットフォームごとに推奨される文面が出力されること。

---

### Step 5: 規約違反事前バリデーター (`src/services/publishing/compliance_validator.py`)
* **目標**: 投稿前に規約違反（禁止表現、文字数オーバー）を検知して警告。
* **実装内容**:
  - 文字数上限オーバーの検出。
  - 一般向けサイトにおける過度な性的・残虐描写（R18相当）の検出と警告（Seriousness / Eroticフィルター連動）。
* **受け入れ基準**: 規約違反リスクのあるテキストに対して適切なWarningメッセージが返ること。

---

### Step 6: 危険な自動投稿ロジックの廃止 (`src/backend/routers/commercial.py`)
* **目標**: アカウントBANリスクのある非公式API・スクレイピングコードを安全に除去。
* **実装内容**:
  - Selenium / Playwright / Requests による非公式ログイン・自動投稿関数を削除または非推奨化。
  - スケジュール自動投稿のエンドポイントを「投稿準備完了通知（Remind）」へリファクタリング。
* **受け入れ基準**: バックエンドに非公式な外部ログインクレデンシャルを保持しない構成になること。

---

### Step 7: 投稿アシスタントAPIエンドポイント (`src/backend/routers/publishing_assistant.py`)
* **目標**: フロントエンドへ最適化された整形済みテキストとチェックリストを提供。
* **実装内容**:
  - `POST /api/publish-assistant/format`: 指定された作品・章をプラットフォーム向けに整形し、前書き・本文・後書き・警告リストを返却。
* **受け入れ基準**: リクエストに対して整形済みJSONが即時返却されること。

---

### Step 8: 利用規約ドラフト作成 (`docs/legal/TERMS_OF_SERVICE.md`)
* **目標**: 商用SaaS公開における法的リスクヘッジ（著作権・免責・禁止事項）。
* **実装内容**:
  - 生成された小説の知的財産権はユーザーに帰属することの明記。
  - プラットフォームへの投稿規約違反やアカウント凍結に対する免責。
  - 他者の著作権・名誉を侵害するプロンプト入力の禁止。
* **受け入れ基準**: 弁護士チェックに回せるレベルの標準SaaS利用規約草案が完成すること。

---

### Step 9: プライバシーポリシー作成 (`docs/legal/PRIVACY_POLICY.md`)
* **目標**: 作家のプロット・アイデアの非学習保証（データプライバシー）。
* **実装内容**:
  - LLMプロバイダのAPI規約（商用API利用時のZero Data Retention）の明記。
  - ユーザーの創作データが第三者LLMの追加学習に用いられないことの保証。
* **受け入れ基準**: 作家が安心して作品データを預けられるプライバシー条項が整備されること。

---

### Step 10: 投稿アシスタントモーダルUI (`frontend/src/components/publishing/PublishAssistantModal.tsx`)
* **目標**: ワンクリックで各投稿サイトの入力欄へ貼り付けられるUI。
* **実装内容**:
  - カクヨム / なろう / Kindle の切替タブ。
  - 「タイトル」「前書き」「本文」「後書き」の各ブロック横に「📋 コピー」ボタンを設置。
  - コピー成功時のトーストフィードバック（「カクヨム用本文をコピーしました」）。
* **受け入れ基準**: ワンクリックでクリップボードへ整形済みテキストが格納されること。

---

### Step 11: 投稿前セーフティチェックリストUI (`frontend/src/components/publishing/SubmissionChecklist.tsx`)
* **目標**: ユーザー自身による最終確認を促す安心のガイドライン表示。
* **実装内容**:
  - チェックボックス群:
    - [ ] 「AI生成・支援」設定にチェックを入れたか？
    - [ ] 過度な性的・暴力的表現が一般向け規定に収まっているか？
    - [ ] 各サイトの投稿管理画面を開く（外部リンクボタン）。
* **受け入れ基準**: チェックリストが直感的に操作でき、外部リンクが別タブで開くこと。

---

### Step 12: 投稿アシスタント単体テスト (`tests/unit/test_publishing_assistant.py`)
* **目標**: 分割処理、ルビ記法変換、AI開示文生成の正確性をテスト。
* **実装内容**:
  - ルビ記法の相互変換（カクヨム ⇔ なろう）の網羅テスト。
  - 前書き・後書き分離の境界値テスト。
* **受け入れ基準**: `pytest tests/unit/test_publishing_assistant.py` が PASS すること。
