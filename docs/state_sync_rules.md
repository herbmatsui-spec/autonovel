# Fragment間状態同期ガイドライン

Streamlitの `@st.fragment` 導入に伴い、フラグメント間およびメインエリアとの状態同期を最適化し、不要な `st.rerun()` を抑制しつつ、UIの整合性を保つための運用ルールを策定する。

## 1. 基本原則：状態更新の単一方向化
- **UIStateStore 経由の操作**: `st.session_state` への直接書き込みは禁止する。必ず `UIStateStore.update()` または `UIStateStore.get_runtime()` 経由で操作し、永続化（SessionManager.save_state）と通知の仕組みを共通化する。
- **読み取り**: 最新の状態は常に `UIStateStore.get()` または `UIStateStore.get_runtime()` から取得する。

## 2. 同期レベルと再実行戦略
状態変更の重要度に応じて、以下の3レベルに分類し、再実行（rerun）を制御する。

| レベル | 内容 | 同期方法 | 再実行戦略 |
| :--- | :--- | :--- | :--- |
| **L1: 局所的変更** | 入力フォームの途中値、スライダー操作、一時的なUI状態 | `UIStateStore` で更新のみ | **再実行なし**。Fragment内でのみ反映される。 |
| **L2: 部分的同期** | 他のFragmentに影響する設定（例：ジャンル変更によるプリセット切り替え） | `UIStateStore` 更新 + 特定の通知 | **Fragment内再実行** または **明示的な `st.rerun()`**。 |
| **L3: 全域的変更** | モード切替、生成開始、重大なエラー、ユーザー認証 | `UIStateStore` 更新 | **即時 `st.rerun()`**。ページ全体をリフレッシュし、整合性を確保。 |

## 3. Fragment間の通信フロー
- **送信側**: `UIStateStore.update(update_func, notify_keys=["key"])` を呼び出し、変更を通知する。
- **受信側**:
    - **リアルタイム同期**: `@st.fragment(run_every=N)` を設定し、定期的に `UIStateStore` から最新値を取得する（ポーリング）。
    - **イベント駆動**: `UIStateStore.subscribe` によるコールバックを利用するが、UIへの反映には最終的に rerun が必要であることを留意する。

## 4. 状態の「確定」タイミングの導入
- L1 の変更（入力中）は Fragment 内で保持し、最終的な「適用」または「生成開始」ボタンが押されたタイミングで L3 として全体に同期させることで、不要な全体再レンダリングを最小化する。

## 5. 実装チェックリスト
- [ ] Fragment 内で `st.session_state` を直接操作していないか？
- [ ] 不要な `st.rerun()` を呼び出していないか？（L1/L2で L3 の処理をしていないか）
- [ ] 重要な状態変更後に、それを参照する他の UI コンポーネントが更新されているか？
