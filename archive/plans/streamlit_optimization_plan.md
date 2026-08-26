# Streamlit Optimization Plan

**概要**: 
- 現行のStreamlitアプリは `st.fragment` を一部しか使用していない。
- `st.session_state` に多くのキーをハードコーディングし、再画面描画のたびに不必要な API 呼び出しが行われる。
- 本計画は、 `st.fragment` の拡張と `st.session_state` の整理により、**DOM 更新**と**API 呼び出し**の削減を目標とする。

## 10 ステップ実装フロー

1. **st.fragment 使用箇所の洗い出し** 
   - `rg -l "st\.fragment" streamlit_app/` で全てのハンドラをリスト。
   - 各フラグメントごとに `run_every`, `key`, `max_runs` 等のデフォルトオプションを収集。
   - 位置情報を含めた表 (`fragment_summary.md`) を作成。

2. **st.session_state キーの抽出 & コメント化** 
   - `grep -R "session_state" -n streamlit_app/` で全使用箇所を取得。
   - 変数名と用途を `session_state_map.md` に記す。
   - 変数名にコンテキスト接頭辞（`plan_`, `audit_`, `ui_` 等）を追加。

3. **API呼び出しパターンのマッピング** 
   - `api_client.py` での `async def call_*` メソッドをリスト。
   - `st.session_state` キーと呼び出し関係を可視化（`api_frag_map.md`）。
   - 冗長呼び出しの候補を抽出。

4. **命名規約とユーティリティ関数の設計** 
   - `state.py` に全キーを統一した定数化。
   - `state_util.py` を作成し `get_state`, `set_state` アクセサを実装。
   - 既存コードで定数を参照に置換。

5. **fragment の `run_every` / `key` の最適化** 
   - 既存フラグメントに `run_every=1s` など適切に設定。
   - 再描画の粒度を細分化し、DOM 更新を減らす。
   - 必要に応じて `@st.fragment` の呼び出しを複数項目に分割。

6. **呼び出しごとのキャッシュ導入** 
   - `@st.cache_resource` / `@st.cache_data` で頻出 API をキャッシュ。
   - `cachest` を補助的に使用して `session_state` 上に保持。
   - 減算した呼び出し数を `cache_stats.json` に記録。

7. **選択的再描画ロジック実装** 
   - `st.fragment(key=…)` を使い、特定 UI 部分だけ再描画。
   - `sidebar.py` の `render_*` でキーを統一。
   - 変化しない部分は `st.empty()` で固定。

8. **ベンチマークスクリプト作成** 
   - `tests/benchmark_streamlit.py` を実装。
   - ① ページ読み込み＋フレームレート ② API 呼び出し回数を収集。
   - `pre_optim_result.json` / `post_optim_result.json` を保存。

9. **UI/UX 影響検証** 
   - `app.py` でのレイアウト変更を確認。
   - ユーザーが操作可能かテストケース `tests/ux_test.yml` を作成。
   - フェードイン・アウトなどの可視化を追加。

10. **ドキュメント化 & コミュニケーション** 
   - すべての変更点を `streamlit_optimization.md` にまとめ。
   - PR 作成前にレビュワーへ変更点を共有。
   - 変更理由とベンチマーク結果を図表化。

## 期待効果
- DOM 再描画の頻度を 30% 低減。
- API 呼び出し回数を 50% 削減。
- ページ読み込み時間を 200ms 前後 短縮。
- コード保守性を向上（キー統一・キャッシュ管理）。