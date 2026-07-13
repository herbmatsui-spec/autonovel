# UI/UX 改善 36ステップ実装計画書

> **目的**: `streamlit_app/` を中心とした既存UI/UXの「難解・わかりにくさ」を解消し、魅力的なランディングページと直感的にわかりやすいインターフェースを実現する。
>
> **前提**: 低性能LLMでも確実に1ステップずつ完遂できる粒度に分割。各ステップは「対象ファイル / 変更内容 / 完了条件」を明示。
>
> **精査対象**: `streamlit_app/` 全体 + `frontend/src/` (React版は補完的に参照)

---

## 📋 現状の問題点まとめ（精査結果）

| # | 問題箇所 | 現状 | 難解さの理由 |
|---|---------|------|-------------|
| 1 | `landing.py` | Unsplash外部画像依存のhero-section、3カラム特徴カードのみ | 訴求力弱、画像欠落リスク、導線不明確 |
| 2 | `sidebar.py` | API設定/モード切替/NSFW/禁止表現/読者欲望が1箇所に過密 | 設定項目の階層が不明確、初心者が圧倒される |
| 3 | `app.py` | ガラス効果CSSが `main()` 内にハードコード | CSS散在、メンテ困難 |
| 4 | `ui_tabs_planning.py` | アーキタイプカードが2段構え（カードdiv+選択ボタン別） | クリック体験が難解、どれを押せばいいかわからない |
| 5 | `ui_tabs_planning.py` | `_wizard_step_indicator` のインデント不具合疑惑 | ステップ表示が崩れる |
| 6 | `ui_tabs_monitor.py` L96 | `if st.button` がexpanderインデントから漏れている | 「設定を適用」ボタンが常時表示される |
| 7 | `ui_tabs_audit.py` | 3つの縦並びボタン（Auto-Fix/伏線/無視） | アクション選択が迷う |
| 8 | `ui_tabs_marketing.py` | `st.info` → ボタン → divider → ボタンの流れ | 導線が断片的 |
| 9 | `widgets.py` | 共通UIコンポーネントが存在するが未活用 | 重複実装、見た目不一致 |
| 10 | 全体 | 絵文字多用（⚔️📋✍️📈⚖️📢）だが統一感なし | 視覚的ノイズ |

---

## フェーズ構成

| フェーズ | ステップ | テーマ |
|---------|---------|-------|
| A | 1-6 | 基盤整備（CSS共通化・デザインシステム・共通コンポーネント活用） |
| B | 7-14 | ランディングページ刷新（訴求力・導線・ビジュアル） |
| C | 15-20 | サイドバー整理（階層化・グループ化・初心者保護） |
| D | 21-28 | 企画フロー改善（ウィザード・アーキタイプ・プレビュー） |
| E | 29-34 | 執筆・監査・分析・納品タブ改善 |
| F | 35-36 | 最終検証・ polish |

---

## フェーズA: 基盤整備（Step 1-6）

### Step 1: 共通CSSファイルの作成
- **対象ファイル**: 新規 `streamlit_app/ui/static/styles.css`（または `streamlit_app/styles.py`）
- **変更内容**:
  - `app.py` の `main()` 内にハードコードされているガラス効果CSS（`_glass_css` 等の変数）を外部ファイルに抽出
  - `landing.py` の hero-section や特徴カードCSS も同ファイルに集約
  - `app.py` からは `with open(styles.py) を import` して読み込む形に変更
- **完了条件**: `app.py` にCSS文字列ハードコードがなくなり、1箇所から全CSSを読み込めること

### Step 2: デザイントークン（色・スペーシング・角丸）の定義
- **対象ファイル**: `streamlit_app/styles.py`（Step1で作成）
- **変更内容**:
  - CSS変数として `--primary`, `--accent`, `--bg-surface`, `--text-muted`, `--radius-md`, `--space-md` を定義
  - 全UIファイルで `#1a1a2e` 等のハードコード色を変数参照に置換（`landing.py`, `ui_components.py`, `ui_utils.py`）
- **完了条件**: 各ファイル内に色の16進数ハードコードがなく、`styles.py` 1箇所でテーマ変更可能

### Step 3: 絵文字アイコンマッピングの統一
- **対象ファイル**: 新規 `streamlit_app/ui/icons.py`
- **変更内容**:
  - 各機能の絵文字を一覧定数化: `ICON_PLANNING = "🧙"`, `ICON_WRITING = "✍️"`, `ICON_ANALYTICS = "📈"`, `ICON_AUDIT = "⚖️"`, `ICON_MARKETING = "📢"`, `ICON_MONITOR = "📡"`
  - 全UIファイル (`ui_tabs_*.py`, `sidebar.py`, `landing.py`) の絵文字を `icons.py` 参照に置換
- **完了条件**: 各ファイルに直書き絵文字がなくなり、`icons.py` で一元管理

### Step 4: 共通ボタンコンポーネントの実装
- **対象ファイル**: `streamlit_app/ui/components/widgets.py`
- **変更内容**:
  - `render_primary_action(label, key, help_text=None)` 関数追加: 統一スタイル（type="primary", use_container_width=True）の実行ボタン
  - `render_secondary_action(label, key)` 関数追加: type通常
  - `ui_tabs_marketing.py` のボタンをこの関数で置換
- **完了条件**: marketing/auditタブのボタンがwidgets関数経由で描画される

### Step 5: 共通セクションヘッダーコンポーネント
- **対象ファイル**: `streamlit_app/ui/components/widgets.py`
- **変更内容**:
  - `render_section_header(icon, title, subtitle=None)` 関数追加: 絵文字+タイトル+サブタイトルを統一デザインで描画
  - 全タブファイルの `st.header("⚖️ 監査...")`, `st.header("📈 ...")` をこの関数で置換
- **完了条件**: 各タブのヘッダーが統一フォーマット（アイコン+タイトル+サブタイトル）で表示

### Step 6: ページタイトル・favicon・メタ情報の整備
- **対象ファイル**: `app.py` 先頭部
- **変更内容**:
  - `st.set_page_config(page_title="覇権小説エンジン v3.0", page_icon="⚔️", layout="wide")` を明示
  - ブラウザタブ名とアイコンを全UIで統一
- **完了条件**: ブラウザタブに「覇権小説エンジン」とfavicon表示

---

## フェーズB: ランディングページ刷新（Step 7-14）

### Step 7: hero-section の外部画像依存解消
- **対象ファイル**: `streamlit_app/landing.py`
- **変更内容**:
  - `url('https://images.unsplash.com/...')` をCSSグラデーション+ローカルSVGパターンに置換
  - `assets/` ディレクトリに背景用SVGパターンを配置（またはCSSのみのグラデーション装飾）
  - 画像欠落リスクを排除
- **完了条件**: オフラインでも背景が正しく表示される

### Step 8: ヒーローコピーの刷新
- **対象ファイル**: `streamlit_app/landing.py` の `render_landing()`
- **変更内容**:
  - タイトルを「AIとの共生執筆で、覇権級のWeb小説を生み出す」等の訴求力あるコピーに
  - サブタイトル追加: 「かんたんモードなら3分で起稿。プロデューサーAIが物語設計を完全サポート」
  - CTA（Call To Action）ボタン追加: 「今すぐ始める」→サイドバーのAPIキー入力へ スクロール誘導
- **完了条件**: ヒーロー段に明確なCTAが表示される

### Step 9: 特徴カードのビジュアル強化
- **対象ファイル**: `streamlit_app/landing.py`
- **変更内容**:
  - 3カラムカードを6枚に拡張: ①かんたんモード ②プロデューサー診断 ③物語設計 ④執筆支援 ⑤監査チケット ⑥納品マネージャー
  - 各カードに `styles.py` の `--secondary-surface` 背景とホバーエフェクト付与
  - アイコンは `icons.py` 参照
- **完了条件**: 6つの機能カードがホバー時に浮き上がる効果付きで表示

### Step 10: 導線フローの可視化セクション追加
- **対象ファイル**: `streamlit_app/landing.py`
- **変更内容**:
  - 特徴カード下に「3ステップで完結」セクション追加: ①API連携 → ②企画起稿 → ③執筆・納品
  - `st.columns(3)` + 矢印（→）で横並びフロー図
  - CSSでステップ番号バッジ（① ② ③）を装飾
- **完了条件**: 3ステップフロー図が表示される

### Step 11: 利用実績・信頼性セクション
- **対象ファイル**: `streamlit_app/landing.py`
- **変更内容**:
  - 「🎯 Web小説最適化」「⚡ Gemini API活用」「🔒 ローカル実行で安全」等の信頼性バッジセクション追加
  - `st.columns` で3-4個のバッジを横並び
- **完了条件**: 信頼性バッジがフローセクション下に表示

### Step 12: FAQ・ヘルプへの導線強化
- **対象ファイル**: `streamlit_app/landing.py`, `ui_utils.py`
- **変更内容**:
  - ランディング下部に「よくある質問」expander 3-4問追加（APIキー取得方法、かんたんモードとは、NSFWモードとは）
  - `render_help_tab` へのリンクボタン追加
- **完了条件**: FAQセクションが表示され、ヘルプページへ遷移可能

### Step 13: フッターの追加
- **対象ファイル**: `streamlit_app/landing.py`
- **変更内容**:
  - ランディング最下部にフッター追加: 「© 覇権小説エンジン v3.0 | Gemini API利用」
  - 利用規約・プライバシーへの簡易リンク（ダミーでも可）
- **完了条件**: フッターが表示される

### Step 14: ランディングのレスポンシブ対応
- **対象ファイル**: `streamlit_app/landing.py`, `styles.py`
- **変更内容**:
  - CSSに `@media (max-width: 768px)` を追加し、モバイルでは3カラムを1カラムに
  - フォントサイズを `clamp()` で可変化
- **完了条件**: 狭幅ブラウザでもカードが1カラムで読みやすく表示

---

## フェーズC: サイドバー整理（Step 15-20）

### Step 15: サイドバーセクション分割の明示化
- **対象ファイル**: `streamlit_app/sidebar.py`
- **変更内容**:
  - `render_sidebar` 内を明確に5ブロック分割（可視コメント＋区切り線）:
    1. **接続**: APIキー入力
    2. **基本設定**: モード選択
    3. **作品**: 作品選択
    4. **執筆パラメータ**: 禁止表現・読者欲望
    5. **詳細設定**: NSFW等
  - 各ブロックの冒頭に `st.divider()` と小見出し追加
- **完了条件**: サイドバーが明確な5ブロック構造で表示

### Step 16: APIキー入力セクションのUX改善
- **対象ファイル**: `streamlit_app/sidebar.py` の `render_api_key_section`
- **変更内容**:
  - パスワード入力欄に `help="Google AI Studio発行のAPIキー"` を追加
  - 検証状態を視覚化: 検証前=⚪、検証中=⏳、成功=✅、失敗=❌ のステータスインジケータ追加
  - APIキー未入力時に「APIキー取得方法」expander を常設
- **完了条件**: APIキー状態がアイコンで即時把握可能

### Step 17: モード切替の.prepend.分かりやすさ向上
- **対象ファイル**: `streamlit_app/sidebar.py` の `render_mode_selector`
- **変更内容**:
  - `st.radio` をラベル付きカード形式に変更: 「かんたんモード（初心者向け）」「上級者モード（詳細設定可能）」
  - 各オプションに1行説明文を付与
  - 選択変更時に `st.toast` で「モードを切り替えました」表示
- **完了条件**: 初心者でも2モードの違いが即理解可能

### Step 18: 作品選択セクションの改善
- **対象ファイル**: `streamlit_app/sidebar.py` の `render_book_selector`
- **変更内容**:
  - 選択ボックスを `st.selectbox` から、現作品のサマリ（話数・文字数）を併記するカスタム形式に
  - 「＋ 新規作品」ボタンをサイドバーに常設（現在はEasy Mode内部に隠れている）
- **完了条件**: 作品選択時に現在の進捗サマリが表示される

### Step 19: 執筆パラメータの折りたたみ整理
- **対象ファイル**: `streamlit_app/sidebar.py` の `render_sidebar_settings`
- **変更内容**:
  - 禁止表現（`render_forbidden_patterns`）と読者欲望（`render_reader_desires`）を1つの `st.expander("✏️ 執筆パラメータ")` 内に統合
  - 各サブセクションに「初心者向けプリセット」ボタンを追加（例: 「一般向け初期値を適用」）
- **完了条件**: 禁止表現と読者欲望が1つの折りたたみ内に整理される

### Step 20: 詳細設定（NSFW等）の保護
- **対象ファイル**: `streamlit_app/sidebar.py` の `render_sidebar_settings` 詳細設定部、`ui/components/nsfw_disclaimer.py`
- **変更内容**:
  - 詳細設定expander を `expanded=False` かつ「⚠️ 詳細設定（上級者向け）」ラベルに
  - NSFWトグルON時に `render_nsfw_disclaimer` を必ず呼ぶフローを明示（`sidebar.py` に `if nsfw_enabled and not render_nsfw_disclaimer(): nsfw_enabled = False` のガード追加）
- **完了条件**: NSFW有効化時に必ず同意モーダルが表示される

---

## フェーズD: 企画フロー改善（Step 21-28）

### Step 21: アーキタイプカード選択の1クリック化
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` の Easy Mode アーキタイプ選択部
- **変更内容**:
  - 現状の「カードdiv表示」＋「別途選択ボタン」の2段構えを解消
  - カード全体を `st.button(use_container_width=True)` で1クリック選択可能に
  - 選択中カードに `✓ 選択中` バッジ表示（CSSでborder-color強調）
- **完了条件**: カード1クリックでアーキタイプ選択完了

### Step 22: ウィザードステップインジケータの修正
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` の `_wizard_step_indicator`
- **変更内容**:
  - インデント崩れ（`st.header("📋 企画ウィザード")` が関数内に入り込んでいる可能性）を修正
  - 4ステップ（世界観→主人公→テーマ→骨子）の進捗を `ui_utils.render_visual_roadmap` と統一フォーマットに
- **完了条件**: ウィザード進行中に現在ステップが正確にハイライト表示

### Step 23: ウィザード各ステップの入力ヘルパー強化
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` のステップ1-4
- **変更内容**:
  - 各ステップ入力欄に `help=` で例示テキスト追加（世界観: 例「剣と魔法のファンタジー世界」）
  - 「AIに例を生成してもらう」ボタンを各ステップに追加（1クリックでプレースホルダ記入）
- **完了条件**: 各ステップに例示とAI生成ボタンが表示

### Step 24: プロデューサー診断結果のビジュアル改善
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` 診断結果表示部
- **変更内容**:
  - `audit_result` を `st.container(border=True)` ではなくカード形式に（`widgets.render_section_header` 活用）
  - 評価スコアを `st.metric` の横並びで視覚化
  - 候補プロットを `st.tabs` で比較表示（現在順不同loop）
- **完了条件**: 診断結果がスコア+タブ比較形式で見やすい

### Step 25: コスト見積もり表示の透明化
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` のコスト見積もり部
- **変更内容**:
  - 「実行すると約X円かかります」表示を `st.info` ではなく強調カード化
  - 内訳（入力トークン / 出力トークン / 単価）を `st.caption` で小字付記
- **完了条件**: コストが目立つ位置にかつ内訳付きで表示

### Step 26: 詳細設定モード（Advanced）の整理
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` の `render_planning_tab`
- **変更内容**:
  - `st.form("detail_plan_form")` 内の項目をセクション分割（世界観/キャラ/テーマ/出力）
  - 各セクションに小見出し追加
- **完了条件**: 詳細モードが4セクション分割で表示

### Step 27: 企画完了後の「次へ」導線明示
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py` のプロット保存後
- **変更内容**:
  - 企画保存完了時に「✅ 企画が保存されました」→「次: プロット展開へ進む」ボタン表示
  - ボタン押下で `UIStateStore` のタブ状態を切り替え（`ui_components._set_current_tab` 活用）
- **完了条件**: 企画完了後に明確な次タブへの導線表示

### Step 28: 企画タブのスケルトンローディング
- **対象ファイル**: `streamlit_app/ui_tabs_planning.py`
- **変更内容**:
  - AI診断実行中の `st.spinner` を、スケルトンカード（`st.container(border=True)` + `st.text("◯◯◯◯")` グレー表示）に置換
  - スピナーの「ぐるぐる」より進捗感を演出
- **完了条件**: AI処理中にスケルトンUIが表示

---

## フェーズE: 執筆・監査・分析・納品（Step 29-34）

### Step 29: 執筆タブのレイアウト整理
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py` の `render_writing_tab`
- **変更内容**:
  - ステップ3「本文執筆」の `col1, col2` レイアウトを確認し、入力欄と実行ボタンの位置を明示
  - 「📝 本文執筆エリア」「⚙️ 執筆オプション」「🚀 実行」の3ブロックに `st.divider` で分割
- **完了条件**: 執筆タブが3ブロック構造で整理される

### Step 30: プロット・章リストの状態可視化改善
- **対象ファイル**: `streamlit_app/ui_tabs_writing.py` の `render_plot_tab`, `render_episode_list`
- **変更内容**:
  - `status_icon`（✅📝⬜）に加え、文字数をプログレスバーで表示（`st.progress(len(content)/target)`）
  - インポートタブのファイル選択UIを `st.file_uploader` の accepted_types 明示
- **完了条件**: 各エピソードに文字数進捗バーが表示

### Step 31: 監査タブのIssueカード改善
- **対象ファイル**: `streamlit_app/ui_tabs_audit.py`
- **変更内容**:
  - 3つの解決アクションボタン（Auto-Fix/伏線/無視）を `st.selectbox` + 「実行」ボタン2段併用に
  - 各アクションに `help=` で説明付記（Auto-Fix: AIが自動修正、伏線: 後回収に登録、無視: 妥協）
  - severity（high/medium/low）を色分けバッジで表示
- **完了条件**: Issue解決アクションがプルダウン+ヘルプ付きで整理

### Step 32: モニタータブのインデント不具合修正
- **対象ファイル**: `streamlit_app/ui_tabs_monitor.py` L96
- **変更内容**:
  - `if st.button("設定を適用")` のインデントを96行目から `with st.expander` 内に是正
  - 現状は expander 外に漏れて常時表示されている
- **完了条件**: 「設定を適用」ボタンがexpander内に正しく格納

### Step 33: モニタータブの指標カード美化
- **対象ファイル**: `streamlit_app/ui_tabs_monitor.py`
- **変更内容**:
  - `st.metric` を3カラム表示に整理（完了率/文字数/コスト）
  - 物語状態遷移（6状態）を `render_visual_roadmap` と統一デザインに
- **完了条件**: モニタ指標が3カラムカード + 統一ロードマップで表示

### Step 34: 納品タブの導線フロー化
- **対象ファイル**: `streamlit_app/ui_tabs_marketing.py`
- **変更内容**:
  - `st.info` → `st.button` → `st.divider` → `st.button` の断続フローを、2ステップカード形式に:
    - STEP1「宣伝パックを生成」カード: 宣伝文・あらすじ生成
    - STEP2「一括納品（ZIP）」カード: ダウンロード準備
  - 生成済みデータは `st.success` で「✅ 準備完了」と明示
- **完了条件**: 納品タブが2ステップカード導線で表示

---

## フェーズF: 最終検証・ polish（Step 35-36）

### Step 35: 全体のビジュアル整合性確認
- **対象ファイル**: 全 `streamlit_app/` ファイル
- **変更内容**:
  - 全タブ遷移時の余白・フォントサイズ・ボタンスタイルが `styles.py` トークンで統一されているか目視確認
  - 絵文字が `icons.py` 参照に統一されているか grep 確認
  - レスポンシブ（縦長・横長）での表示崩れ確認
- **完了条件**: 全UIでトークン・アイコンが統一され、表示崩れなし

### Step 36: ユーザーシナリオ別E2E手動検証
- **対象ファイル**: 検証シナリオ実行（コード変更なし）
- **変更内容**:
  - シナリオ1「初心者がかんたんモードで起稿」: ランディング→API設定→Easy Mode→アーキタイプ選択→プロット生成
  - シナリオ2「上級者が詳細設定」: Advanced→詳細企画→執筆→監査→納品
  - 各シナリオで迷う箇所がないか、3分以内に完了するかを確認
  -結果を本計画書末尾の検証ログに追記
- **完了条件**: 2シナリオとも迷いなく3分以内完了、検証ログ記入済

---

## 📝 検証ログ（Step36完了後に追記）

| シナリオ | 所要時間 | つまづき箇所 | 対応ステップ |
|---------|---------|-------------|-------------|
| 初心者かんたん起稿 | （計測） | （記入） | （該当Step） |
| 上級者詳細執筆→納品 | （計測） | （記入） | （該当Step） |

---

## 実装順序の指針

- 各ステップは独立して実装可能。ただしStep1→2→3は順序必須（CSS基盤→トークン→アイコン）
- フェーズA完了後にB-Fは並行実装可能
- 1ステップ完了ごとに `streamlit run streamlit_app/app.py` で表示確認を推奨
- 低性能LLMの場合、1ステップ1プロンプト完結を推奨（「Step Xを実行して」形式）

---

## 関連ファイル一覧（変更対象）

| フェーズ | 主変更ファイル |
|---------|--------------|
| A | `streamlit_app/styles.py`(新規), `ui/icons.py`(新規), `ui/components/widgets.py`, `app.py` |
| B | `streamlit_app/landing.py` |
| C | `streamlit_app/sidebar.py`, `ui/components/nsfw_disclaimer.py` |
| D | `streamlit_app/ui_tabs_planning.py` |
| E | `streamlit_app/ui_tabs_writing.py`, `ui_tabs_audit.py`, `ui_tabs_monitor.py`, `ui_tabs_marketing.py` |
| F | 全体確認 |

---

*本計画書は `plans/ui_ux_improvement_plan_36steps.md` に保存されています。Step実行時に本ファイルの該当箇所に✔を付けて進捗管理してください。*
