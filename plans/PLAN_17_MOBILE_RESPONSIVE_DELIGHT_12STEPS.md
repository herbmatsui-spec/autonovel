# PLAN 17: モバイル最適化＆リアルタイム思考可視化（Progress Delight） 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 フロントエンドUI/UX、リアルタイム進捗通知（SSE/WebSocket）、モバイル対応  
**目的**: PCワイド画面前提（1500px以上）のレイアウトを脱却し、スマートフォンやiPadでもプロット確認・執筆・推敲が快適に行えるレスポンシブWebデザインを実現する。併せて、長時間のAI生成待ち時間（30〜60秒）を作家がワクワクして見守れる「AIの思考プロセス可視化（Progress Delight）」へと刷新する。  
**前提**: 画面幅768px以下（SP）と1024px以下（Tablet）のブレークポイントにおいて、崩れや横スクロールのないUIを保証。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | デザイン定義 | `frontend/src/index.css` (修正) | モバイルブレークポイント、Safe Area Insets、タッチ最適化CSSユーティリティ追加 |
| **2** | 下部ナビ | `frontend/src/components/mobile/MobileBottomNav.tsx` (新規) | スマホ用ボトムナビゲーション（作品一覧、プロット、執筆、設定）コンポーネント |
| **3** | SPドロワー | `frontend/src/components/mobile/MobileChapterDrawer.tsx` (新規) | スマホ上で親指1本でエピソードやプロットを切り替えられるボトムシートドロワー |
| **4** | モバイル推敲バー | `frontend/src/components/mobile/MobileQuickActionBar.tsx` (新規) | キーボード上に固定されるAI推敲、字下げ、カギ括弧入力ショートカットバー |
| **5** | 進捗スキーマ | `src/models/generation_progress.py` (新規) | リアルタイム思考ステップ（フェーズ、思考要約、進捗率）のPydanticモデル定義 |
| **6** | SSEイベント拡張 | `src/backend/sse.py` (修正) | 各エージェント（プロット、執筆、伏線検索、推敲）の思考プロセスをSSEでリアルタイム配信 |
| **7** | 進捗フック | `frontend/src/hooks/useGenerationProgress.ts` (新規) | SSEストリームを受信し、滑らかなアニメーション用進捗ステートを管理するフック |
| **8** | 思考可視化UI | `frontend/src/components/common/ProgressDelightModal.tsx` (新規) | AIが現在「何を考え、どのシーンを書いているか」を流麗に表示するモーダル |
| **9** | マイクロ演出 | `frontend/src/components/common/TypingStoryPreview.tsx` (新規) | 生成中の本文がリアルタイムにタイピング風アニメーションで流れるプレビュー演出 |
| **10** | バックグラウンド通知 | `frontend/src/services/browserNotification.ts` (新規) | スマホで別タブを開いていても生成完了を伝えるWeb Push / Browser Notification |
| **11** | レスポンシブ統合 | `frontend/src/App.tsx` (修正) | PC・タブレット・スマートフォンに応じた動的レイアウト切替の統合 |
| **12** | 統合検証 | `tests/frontend/mobile_responsive.test.tsx` (新規) | モバイルビューポート（375px/768px）での表示崩れゼロとタッチ操作を検証するテスト |

---

## 各ステップの詳細仕様

### Step 1: モバイルCSSユーティリティ定義 (`frontend/src/index.css`)
* **目標**: スマートフォンのノッチ（Safe Area）やタッチ操作に最適化したスタイルの整備。
* **実装内容**:
  ```css
  /* Mobile Responsive Breakpoints */
  :root {
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --mobile-nav-height: 60px;
  }
  @media (max-width: 768px) {
    .hide-on-mobile { display: none !important; }
    .mobile-full-width { width: 100% !important; padding: 12px !important; }
    .touch-target { min-height: 44px; min-width: 44px; }
  }
  ```
* **受け入れ基準**: スマホ画面で水平スクロール（横揺れ）が発生しないこと。

---

### Step 2: モバイルボトムナビゲーション (`frontend/src/components/mobile/MobileBottomNav.tsx`)
* **目標**: 片手操作で主要画面を切り替えられるネイティブアプリ風ナビ。
* **実装内容**:
  - アイコン群: `[📚 作品] [🗺️ プロット] [✍️ 執筆] [⚙️ 設定]`
  - 現在アクティブな画面のハイライトと、親指が届く高さ設計。
* **受け入れ基準**: 画面最下部に固定表示され、画面遷移がスムーズに行えること。

---

### Step 3: スマホ用ボトムシートドロワー (`frontend/src/components/mobile/MobileChapterDrawer.tsx`)
* **目標**: 画面の狭いスマホで章一覧を快適に選択。
* **実装内容**:
  - 画面下部からスワイプアップで開くボトムシート。
  - 第1話〜第N話のタイトル、執筆ステータス（下書き/完成）の一覧。
* **受け入れ基準**: タップで章が即座に切り替わり、ドロワーが閉じること。

---

### Step 4: モバイルクイックアクションバー (`frontend/src/components/mobile/MobileQuickActionBar.tsx`)
* **目標**: スマホでの日本語小説入力のストレスを解消。
* **実装内容**:
  - ソフトウェアキーボードの上に `[「」] [……] [――] [全角空白] [🤖 AI続き] [✨ 校正]` のショートカットボタンを常時配置。
* **受け入れ基準**: ワンタップでカギ括弧が挿入され、カーソルがカッコ内に自動移動すること。

---

### Step 5: 思考プロセスデータモデル (`src/models/generation_progress.py`)
* **目標**: AIエージェントの内部思考状態をフロントエンドに伝える構造。
* **実装内容**:
  ```python
  from __future__ import annotations
  from pydantic import BaseModel

  class AgentThoughtStep(BaseModel):
      phase: str        # "planning", "rag_retrieval", "writing", "refining"
      step_name: str    # "伏線の照合中"
      detail_thought: str  # "第1話で提示した『銀の鍵』の回収フラグを検証しています..."
      progress_percent: int
      timestamp: float
  ```
* **受け入れ基準**: `mypy src/models/generation_progress.py` でエラーゼロ。

---

### Step 6: SSEリアルタイム配信拡張 (`src/backend/sse.py`)
* **目標**: 各エージェントの処理開始・完了時に思考メタデータをイベント送信。
* **実装内容**:
  - `event: progress` として `AgentThoughtStep` のJSONを随時ストリーミング。
* **受け入れ基準**: 生成処理の各ステップでフロントエンドへ即座にイベントが届くこと。

---

### Step 7: 進捗管理Reactフック (`frontend/src/hooks/useGenerationProgress.ts`)
* **目標**: SSEメッセージを受信し、ゲージのイージング計算とテキスト切り替えを管理。
* **実装内容**:
  - 実際の進捗が急に進んでもゲージがカクつかず滑らかに動く補間ロジック。
* **受け入れ基準**: 進捗率が0%から100%までスムーズにアニメーションすること。

---

### Step 8: 思考プロセス可視化モーダル (`frontend/src/components/common/ProgressDelightModal.tsx`)
* **目標**: 待ち時間をエンタメ化する美しいモーダル画面。
* **実装内容**:
  - 発光するサークルプログレスバー。
  - 「今考えていること」のタイピングアニメーション表示。
  - ステップ履歴のタイムライン表示（✔ プロット完了 → ⚡ 伏線検索完了 → ✍️ 執筆中）。
* **受け入れ基準**: ユーザーが生成の進行状況をワクワクしながら直感把握できること。

---

### Step 9: リアルタイム執筆プレビュー (`frontend/src/components/common/TypingStoryPreview.tsx`)
* **目標**: 生成中の本文がまるでAI作家がリアルタイムでタイプしているように見える演出。
* **実装内容**:
  - 生成されたトークンが逐次フェードインで追加される軽量プレビュー画面。
* **受け入れ基準**: ブラウザの負荷を上げることなくスムーズに文字が表示されること。

---

### Step 10: ブラウザ通知サービス (`frontend/src/services/browserNotification.ts`)
* **目標**: 生成中に別タブで調べ物をしていても完了に気づける仕組み。
* **実装内容**:
  - `Notification.requestPermission()` によるWeb通知許可取得。
  - 生成完了時に「✨ 第3話の執筆が完了しました！」をデスクトップ/スマホに通知。
* **受け入れ基準**: タブが非アクティブな状態でも通知が正常に届くこと。

---

### Step 11: レスポンシブレイアウト統合 (`frontend/src/App.tsx`)
* **目標**: デバイス幅に応じた最適なコンポーネントツリーの自動切り替え。
* **実装内容**:
  - 幅768px未満の場合は自動的にモバイルレイアウト（ボトムナビ＋単一ビュー）へ切り替え。
  - タブレット（768〜1024px）ではスプリットビューを採用。
* **受け入れ基準**: ウィンドウ幅をリサイズしてもレイアウト破綻が生じないこと。

---

### Step 12: モバイルE2Eテスト (`tests/frontend/mobile_responsive.test.tsx`)
* **目標**: モバイル環境での画面描画とボタンタップをテスト。
* **実装内容**:
  - Viewport 375x667（iPhone SE想定）でボトムナビが表示され、執筆画面が開くことを検証。
* **受け入れ基準**: Vitestテストが PASS すること。
