# PLAN 04: 作家ハイブリッド執筆コクピット 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 フロントエンドUI・協調執筆API  
**目的**: 「完全自動生成」の幻想を捨て、人間の偏愛・フェチズム・エッジの効いた狂気（Emotional Spine）を10%注入し、AIが90%を超高速かつ高密度に具現化する作家コクピットを構築する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/cockpit.py` (新規) | 作家の魂（Emotional Spine）およびインライン修正指示のPydanticモデル定義 |
| **2** | テスト | `tests/unit/cockpit/test_partial_rewriter.py` (新規) | 段落単位の部分リライトエンジンの単体テスト作成（TDD先行） |
| **3** | プロンプト | `prompts/templates/cockpit/inline_direction.j2` (新規) | 前後文脈を維持しつつ作家の一行指示をピンポイント反映するJinja2プロンプト |
| **4** | ロジック | `src/services/hybrid_cockpit/partial_rewriter.py` (新規) | 選択段落のみを文体一貫性を保ったまま再生成するサービス |
| **5** | ストレージ | `src/services/hybrid_cockpit/spine_manager.py` (新規) | 作品全体の通底する欲望・フェチ設定のDB保存・取得サービス |
| **6** | ルーター | `src/backend/routers/cockpit.py` (新規) | 部分リライト＆Emotional Spine用のFastAPIエンドポイント |
| **7** | 型定義 | `frontend/src/types/cockpit.ts` (新規) | フロントエンド用TypeScriptインターフェース定義 |
| **8** | UI部品 | `frontend/src/components/cockpit/EmotionalSpineCard.tsx` (新規) | 作家が作品の「狂気・性癖」を入力・ピン留めする常設カードUI |
| **9** | UIエディタ | `frontend/src/components/cockpit/InlineDirectionEditor.tsx` (新規) | 本文を選択して「煽りを強化」「もっと冷たく」と一行指示できるポップオーバーUI |
| **10** | 差分表示 | `frontend/src/components/cockpit/RewriteDiffModal.tsx` (新規) | AI提案と元テキストのインライン差分プレビュー＆ワンクリック反映UI |
| **11** | 統合 | `frontend/src/components/Editor.tsx` (修正) | メインエディタ画面へのコクピット機能（Spineカード＋インライン指示）組み込み |
| **12** | 統合検証 | `tests/e2e/test_cockpit_flow.py` (新規) | 作家ディレクション入力から部分リライト反映までのE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/cockpit.py`)
* **目標**: 作家とAIが対話的に執筆するためのデータ構造を定義。
* **実装内容**:
  ```python
  from pydantic import BaseModel, Field

  class EmotionalSpine(BaseModel):
      core_fetish: str = Field(..., description="作者の絶対的な性癖・こだわり")
      unforgivable_sin: str = Field(..., description="この作品で最も許されない悪行")
      catharsis_peak: str = Field(..., description="読者に見せつけたい究極のカタルシス")

  class InlineRewriteRequest(BaseModel):
      book_id: int
      ep_num: int
      selected_text: str = Field(..., min_length=5, description="修正対象の選択テキスト")
      preceding_context: str = Field("", description="直前の文脈 (最大500字)")
      following_context: str = Field("", description="直後の文脈 (最大500字)")
      direction: str = Field(..., description="作家の一行指示 (例: もっとネチネチした煽りを入れて)")

  class InlineRewriteResponse(BaseModel):
      rewritten_text: str
      diff_summary: str
  ```
* **受け入れ基準**: `mypy src/models/cockpit.py` がエラーなく通ること。

---

### Step 2: 部分リライト単体テスト作成 (`tests/unit/cockpit/test_partial_rewriter.py`)
* **目標**: 前後文脈を壊さずに選択範囲だけをディレクション通りに書き換えるテストを用意。
* **実装内容**:
  ```python
  import pytest
  from src.services.hybrid_cockpit.partial_rewriter import PartialRewriter

  @pytest.mark.asyncio
  async def test_rewrite_selected_paragraph():
      rewriter = PartialRewriter(mock_llm)
      result = await rewriter.rewrite_selection(
          selected_text="「やめてくれ」と彼は言った。",
          direction="もっと無様に泣き叫ばせて",
          preceding="剣を突きつけられた。",
          following="容赦なく刃が振り下ろされた。"
      )
      assert "やめてくれ" in result.rewritten_text or "泣" in result.rewritten_text
  ```
* **受け入れ基準**: テストが正しく実行できること。

---

### Step 3: インラインリライトプロンプト (`prompts/templates/cockpit/inline_direction.j2`)
* **目標**: 前後の文章のトーン（文体）を崩さずに、選択範囲だけに作家の指示を適用するJinja2テンプレート。
* **実装内容**:
  - 指示: 「前後の文脈（{{ preceding_context }} と {{ following_context }}）に完全に接続するように執筆せよ」
  - 指示: 「作家のディレクション『{{ direction }}』を極端な解像度で反映せよ」
  - 指示: 「選択範囲以外の内容を勝手に付け足すな」
* **受け入れ基準**: テンプレートレンダリングが正常に動作すること。

---

### Step 4: 部分リライトサービス (`src/services/hybrid_cockpit/partial_rewriter.py`)
* **目標**: `InlineRewriteRequest` を受け取り、LLMに指示を出して差し替え文を返すサービス。
* **実装内容**:
  - `rewrite_selection(req: InlineRewriteRequest) -> InlineRewriteResponse`
  - 前後500文字を文脈として注入。
  - 生成後のテキストが前後の接続詞と矛盾しないか簡易チェック。
* **受け入れ基準**: Step 2 の単体テストが通過すること。

---

### Step 5: Emotional Spine管理サービス (`src/services/hybrid_cockpit/spine_manager.py`)
* **目標**: 作品ごとの「作家の魂（Spine）」をDBに永続化し、毎回のプロット・執筆時に注入可能にする。
* **実装内容**:
  - `save_spine(book_id: int, spine: EmotionalSpine)`
  - `get_spine(book_id: int) -> EmotionalSpine | None`
  - Bible または Book モデルのメタデータ列に格納。
* **受け入れ基準**: 保存と取り出しが正しく動作すること。

---

### Step 6: FastAPIルーター実装 (`src/backend/routers/cockpit.py`)
* **目標**: フロントエンドから呼び出すエンドポイントを公開。
* **実装内容**:
  - `POST /api/cockpit/inline-rewrite`: 部分リライト実行
  - `POST /api/cockpit/spine/{book_id}`: Spine保存
  - `GET /api/cockpit/spine/{book_id}`: Spine取得
* **受け入れ基準**: `TestClient` で 200 OK が返ること。

---

### Step 7: フロントエンド型定義 (`frontend/src/types/cockpit.ts`)
* **目標**: TypeScriptの型定義を作成。
* **実装内容**:
  ```typescript
  export interface EmotionalSpine {
    core_fetish: string;
    unforgivable_sin: string;
    catharsis_peak: string;
  }

  export interface InlineRewriteRequest {
    book_id: number;
    ep_num: number;
    selected_text: string;
    preceding_context: string;
    following_context: string;
    direction: string;
  }

  export interface InlineRewriteResponse {
    rewritten_text: string;
    diff_summary: string;
  }
  ```
* **受け入れ基準**: `npm run typecheck` が通過すること。

---

### Step 8: Emotional Spine設定カード (`frontend/src/components/cockpit/EmotionalSpineCard.tsx`)
* **目標**: エディタのサイドバーに常駐する「作家のこだわり・狂気」入力UI。
* **実装内容**:
  - 「コアな性癖」「絶対に許せない悪行」「目指すカタルシス」の3行フォーム。
  - 保存ボタンを押すと即座に作品設定へ反映。
* **受け入れ基準**: コンポーネントが単体でレンダリングできること。

---

### Step 9: インライン・ディレクション・ポップオーバー (`frontend/src/components/cockpit/InlineDirectionEditor.tsx`)
* **目標**: 本文のテキストを選択した際に浮遊表示されるミニプロンプト入力バー。
* **実装内容**:
  - 選択範囲の文字列を取得。
  - 「例: もっと冷酷に」「ざまぁ感を強く」などのクイックサジェストボタン付き。
  - 「AIに書き直させる」ボタンでAPI呼び出し。
* **受け入れ基準**: テキスト選択時に座標追従してポップオーバーが表示されること。

---

### Step 10: 差分プレビューモーダル (`frontend/src/components/cockpit/RewriteDiffModal.tsx`)
* **目標**: AIが提案したリライト結果を元テキストと左右比較し、ワンクリックで本文置換できるモーダル。
* **実装内容**:
  - 赤（削除）・緑（追加）のシンプルなテキスト差分表示。
  - 「採用する」「破棄する」ボタン。
* **受け入れ基準**: 採用ボタンクリックで親コンポーネントの本文ステートが更新されること。

---

### Step 11: メインエディタ統合 (`frontend/src/components/Editor.tsx`)
* **目標**: `Editor.tsx` に `EmotionalSpineCard` と `InlineDirectionEditor` を組み込む。
* **実装内容**:
  - エディタ右ペインに Spine 設定タブを追加。
  - テキストエリアのマウスアップイベントでインラインポップオーバーを起動。
* **受け入れ基準**: ブラウザでエディタを開いて正常に操作できること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_cockpit_flow.py`)
* **目標**: Spine保存 → 本文生成 → 一部選択 → インライン修正指示 → 差し替え完了のフローをテスト。
* **実装内容**:
  - APIレベルで一連のリクエストをシミュレーションし、意図通りの修正が本文に反映されることを検証。
* **受け入れ基準**: `pytest tests/e2e/test_cockpit_flow.py` が ALL GREEN。
