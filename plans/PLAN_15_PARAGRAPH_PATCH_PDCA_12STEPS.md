# PLAN 15: 差分パッチリライト＆オーディター階層スクリーニング 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 監査・PDCAリライトループ基盤 (`src/services/pdca_cycle.py`, `src/services/audit_aggregator.py`)  
**目的**: 75点未満時にエピソード全文（3,000字）を再生成し、1話あたり最大28回のLLM呼び出しと数分の遅延が発生していた非効率なループを撤廃する。低スコアの特定段落のみを局所リライトする「差分パッチ（Paragraph Patch）」と、1モデルによる高速スクリーニング（Early Exit）を導入し、コストと待ち時間を70%削減する。  
**前提**: 修正対象段落の前後コンテキストを厳密に渡し、文章の接続破綻を防ぐインプレース置換機構。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/patch_pdca.py` (新規) | 段落識別子（Paragraph ID）、局所指摘、パッチ指示のPydanticモデル定義 |
| **2** | スクリーナー | `src/services/audit/fast_screener.py` (新規) | 単一の軽量LLMで8次元の総合合否（合格/要修正）を1秒で判定する階層スクリーナー |
| **3** | 段落マッピング | `src/services/prose/paragraph_indexer.py` (新規) | 小説本文を意味単位（シーン/トピック）の段落ブロックに分割・採番するインデクサー |
| **4** | 指摘特定 | `src/services/audit/targeted_diagnostic.py` (新規) | 8専門オーディターの指摘を「どの段落の何行目か」にピンポイント紐付けるロジック |
| **5** | パッチ生成 | `prompts/templates/audit/paragraph_patch_directive.j2` (新規) | 前後文脈を維持しながら特定段落のみを外科的に書き直させるプロンプト |
| **6** | 局所リライター | `src/agents/writing/paragraph_patch_agent.py` (新規) | 指定段落のみを書き直し、文字数とトーンを合わせて返却するエージェント |
| **7** | マージ結合 | `src/services/prose/patch_merger.py` (新規) | リライトされた段落を元本文に非破壊でマージし、前後の接続詞を調整するエンジン |
| **8** | PDCA刷新 | `src/services/pdca_cycle.py` (修正) | 全文再生成ループから「スクリーニング → 局所パッチ → 再検証」の軽量ループへ全面改修 |
| **9** | 監査集約改修 | `src/services/audit_aggregator.py` (修正) | Early Exit（高スコア時は8オーディター呼び出しを即座にスキップ）の実装 |
| **10** | バックエンドAPI | `src/backend/routers/patches.py` (修正) | 段落パッチ適用APIおよび変更差分ストリーミングの最適化 |
| **11** | フロントUI | `frontend/src/components/studio/PDCADiffViewer.tsx` (修正) | 全文置換ではなく、修正された段落のみが黄色く点灯する局所パッチ可視化UI |
| **12** | 統合検証 | `tests/unit/test_paragraph_patch_pdca.py` (新規) | 局所パッチ適用によるスコア改善、LLM呼び出し回数70%減を立証する単体テスト |

---

## 各ステップの詳細仕様

### Step 1: 差分パッチ用Pydanticモデル定義 (`src/models/patch_pdca.py`)
* **目標**: 段落単位の修正指示・パッチ結果のデータ構造を定義。
* **実装内容**:
  ```python
  from __future__ import annotations
  from pydantic import BaseModel, Field

  class ParagraphTarget(BaseModel):
      index: int = Field(..., description="段落インデックス (0始まり)")
      original_text: str
      issue_category: str  # 例: "emotional_flatness", "foreshadow_miss"
      directive: str       # 修正指示

  class PatchRewriteResult(BaseModel):
      index: int
      patched_text: str
      confidence_score: float
  ```
* **受け入れ基準**: `mypy src/models/patch_pdca.py` でエラーゼロ。

---

### Step 2: 高速スクリーナー実装 (`src/services/audit/fast_screener.py`)
* **目標**: 8人の専門オーディターを毎回全員呼ばず、まず1回の超軽量API呼び出しで合否判定。
* **実装内容**:
  - Gemini 2.0 Flash等を用い、総合スコア（0〜100）と「重大な欠陥の有無」を1秒でスクリーニング。
  - スコアが目標値（例: 80点）以上なら合格（Early Exit）とし、専門監査を全スキップ。
* **受け入れ基準**: 合格ラインの文章に対して専門オーディター呼び出しが0回で終了すること。

---

### Step 3: 段落インデクサー実装 (`src/services/prose/paragraph_indexer.py`)
* **目標**: 本文を安定したインデックス付き段落リストに分割。
* **実装内容**:
  - 改行と空行を考慮し、意味のあるブロック（100〜300字程度）に分割。
  - 各段落にユニークIDと前後の依存関係メタデータを付与。
* **受け入れ基準**: 分割した段落を単純結合すると完全に元の本文と一致すること。

---

### Step 4: 指摘箇所のピンポイント紐付け (`src/services/audit/targeted_diagnostic.py`)
* **目標**: 監査のダメ出し（「戦闘の盛り上がりが足りない」等）を該当段落にマッピング。
* **実装内容**:
  - セマンティック検索（BM25または軽量Embedding）で指摘内容に関連する最もスコアの低い段落を1〜2箇所特定。
* **受け入れ基準**: 指摘内容に最も合致する段落のインデックスが特定されること。

---

### Step 5: 段落パッチJinja2プロンプト (`prompts/templates/audit/paragraph_patch_directive.j2`)
* **目標**: 前後数行をコンテキストとして渡し、該当段落のみを自然にリライト。
* **実装内容**:
  ```
  【直前の段落】: {{ prev_paragraph }}
  【修正対象段落】: {{ target_paragraph }}
  【直後の段落】: {{ next_paragraph }}
  【修正課題】: {{ directive }}
  直前・直後の文章とスムーズに繋がるよう、対象段落のみを修正して出力せよ。
  ```
* **受け入れ基準**: 前後の文脈を壊さない局所プロンプトが生成されること。

---

### Step 6: 局所パッチエージェント (`src/agents/writing/paragraph_patch_agent.py`)
* **目標**: 指定された段落のみを書き直す特化型エージェント。
* **実装内容**:
  - 生成トークン数を最大300〜500トークンに抑制し、超高速（1〜2秒）でリライトを完了。
* **受け入れ基準**: 対象段落の置換文字列のみが正確に返却されること。

---

### Step 7: パッチマージャー (`src/services/prose/patch_merger.py`)
* **目標**: 元テキストの該当段落を安全に差し替え。
* **実装内容**:
  - 指定インデックスの段落を差し替え、文頭・文末の接続詞や改行を自動調整して結合。
* **受け入れ基準**: 置換対象以外の段落が1文字も改変されずに本文が再構築されること。

---

### Step 8: PDCAサイクルの全面改修 (`src/services/pdca_cycle.py`)
* **目標**: 全文再生成コードを排除し、差分パッチループへ統合。
* **実装内容**:
  ```python
  # 従来の全文ループ: draft = await self.writer.write(...)
  # 新しい局所パッチループ:
  target_paras = self.diagnostic.identify_weak_paragraphs(audit_result)
  patched_draft = await self.patch_runner.apply_patches(draft, target_paras)
  ```
* **受け入れ基準**: ループ実行時の消費トークン数が全文再生成と比較して70%以上削減されること。

---

### Step 9: 監査集約層のEarly Exit対応 (`src/services/audit_aggregator.py`)
* **目標**: スクリーナー合格時の短絡評価を正式サポート。
* **実装内容**:
  - `run_hierarchical_audit(draft_text)` メソッドを追加。
* **受け入れ基準**: スクリーナーが高スコアを出した場合、8オーディターの非同期タスクが起動しないこと。

---

### Step 10: パッチ管理APIエンドポイント (`src/backend/routers/patches.py`)
* **目標**: クライアントから手動で特定段落のリライトを指示できるAPI。
* **実装内容**:
  - `POST /api/episodes/{id}/patch-paragraph`: 段落番号と指示を渡して即時差分を取得。
* **受け入れ基準**: 1秒未満で差分プレビューが返却されること。

---

### Step 11: フロントエンド差分ビューア改修 (`frontend/src/components/studio/PDCADiffViewer.tsx`)
* **目標**: どの段落がピンポイントで修正されたかを明快に表示。
* **実装内容**:
  - 修正された段落のみをフォーカス表示し、変更理由（例:「カタルシス強調のため修正」）をタグ表示。
* **受け入れ基準**: 全文をスクロールして探す必要がなく、修正箇所が即座に視認できること。

---

### Step 12: 差分パッチPDCA統合テスト (`tests/unit/test_paragraph_patch_pdca.py`)
* **目標**: 局所パッチによる品質向上とAPI呼び出し削減を自動検証。
* **実装内容**:
  - モックテキストに対し、特定段落のみパッチが適用され、総合スコアが向上することを確認。
  - API呼び出し回数が28回から最大3〜4回へ激減することをアサート。
* **受け入れ基準**: `pytest tests/unit/test_paragraph_patch_pdca.py` が PASS すること。
