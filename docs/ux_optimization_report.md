# UX向上とリソース最適化 実装記録 (v3.0)

## 1. 概要
本プロジェクトでは、Streamlit アプリケーションの UI ラグ（不要な再実行）の削減と、LLM 生成処理の応答性向上を目的とした最適化を実施した。

## 核心となるアプローチは、**「UI の断片化 (Fragmentation)」** と **「非同期ストリーミング・パイプラインの構築」** である。

## 2. 主要な変更点

### 2.1 UI の最適化: `@st.fragment` の導入
Streamlit のデフォルト動作である「何か一つが変われば全体が再実行される」挙動を抑制するため、`@st.fragment` を導入した。

- **導入箇所**: 
    - サイドバーの API キー検証・設定領域
    - メインエリアの各入力フォーム (Planning Tab 等)
    - リアルタイム進捗表示コンポーネント (`progress_fragment`)
- **効果**: 特定のコンポーネント内での状態変更がページ全体に波及しなくなり、入力中のラグや不要なスピナー表示が劇的に減少した。

### 2.2 非同期 LLM ストリーミング・パイプライン
LLM の生成完了を待ってから表示するのではなく、トークン単位で UI に反映させる仕組みを構築した。

- **アーキテクチャ**:
    `GeminiApiClient` (Async Stream) $\rightarrow$ `BackgroundReporter` $\rightarrow$ `ProgressState` (Redis/DB) $\rightarrow$ `ProgressStateProxy` $\rightarrow$ UI Fragment (Polling)
- **実装のポイント**:
    - `httpx.AsyncClient` による非同期 I/O 化。
    - `ProgressState` を介した状態の永続化。ストリーミングテキストは即座に保存され、UI 側のポーリング fragment がこれを検知して更新する。

### 2.3 状態同期ルール (L1/L2/L3)
Fragment 導入に伴い、状態更新の範囲を制御する同期ルールを策定した。
- **L1 (Local)**: Fragment 内部でのみ完結する状態。
- **L2 (Session)**: `st.session_state` を介して他の Fragment と共有する状態。
- **L3 (Global/DB)**: DB/Redis に保存し、ページリロード後も維持される状態。

### 2.4 リソース最適化とオブザーバビリティ
- **キャッシュ**: `ConfigValidator.validate_all` に `@st.cache_data` (TTL 600s) を導入し、起動時の設定検証コストを削減。
- **計測**: `scripts/perf_report.py` を作成し、LLM の TTFT (Time to First Token) や UI の再実行回数 (`rerun_count`) を定量的に計測可能にした。
- **エラーハンドリング**: `BackgroundReporter.report_exception` を実装し、非同期処理中の例外を `ProgressState.error` 経由で UI に即時通知するフローを確立。

## 3. 保守上の注意点
- **Fragment への追加**: 新しい UI コンポーネントを作成する際は、それが全体再実行を必要とするか検討し、可能であれば `@st.fragment` を適用すること。
- **状態更新**: `UIStateStore` を介して状態を更新し、必要に応じて `st.rerun()` を明示的に呼ぶか、Fragment の自動更新 (`run_every`) を利用すること。
- **非同期処理**: バックグラウンドタスク内で `ProgressState` を更新する際は、必ず `BackgroundReporter` を介してログと状態を同期させること。

## 4. パフォーマンス指標 (改善後)
- **UI レスポンス**: 入力フォームでのタイピングラグが解消。
- **体感速度**: ストリーミング導入により、生成開始までの待機時間が「数秒」から「数百ミリ秒 (TTFT)」へ短縮。
- **安定性**: 非同期処理の整合性を担保するテストスイートを拡充し、回帰テストを可能にした。
