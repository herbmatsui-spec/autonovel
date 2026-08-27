# プロット生成 最高峰化 実装計画（72ステップ・補完版）

## 前提
`docs/kakuyomu_pipeline_improvement_plan.md`（以下「既存計画」）は**実装済み**とする。
既存計画がカバーするため本計画では**行わない**項目：
- ⑤ プロット複数案×商業スコア選抜（既存 Phase 5）
- ⑥ Bible 連続性台帳（未回収伏線含む）（既存 Phase 6）
- ⑦ フック最適化 cadence（既存 Phase 7）
- ⑧ タイトル/タグ CTR（既存 Phase 8）
- ⑨ HITL プロット承認ゲート（既存 Phase 9）
- ① 差し戻しループ / ② 密度ルービック / ③ 並列＋Bibleロック / ④ 商業ルービック（既存 Phase 1〜4）

本計画は**これらに依存しつつ、プロット生成サブシステムにのみ固有の穴**を埋める。
低性能 LLM（gemini-3.5-flash-lite）でも進むため、各ステップは「1ファイル・数行・単一責務・テスト可能」。

## フェーズA：プロットの正しさ（P0）ステップ 1〜18

**1. `PlotGraphState` フィールド確認（対象: `state.py`）**
`bible_context` / `user_instructions` が `total=False` で定義済みか確認。受け入れ: 両フィールド存在。

**2. `call_plot_graph_node` で bible 取得フック（対象: `master_nodes.py:51`）**
`plot_input` 構築前に `engine.repo.get_bible(book_id)` を呼ぶ空枠を追加。受け入れ: `plot_input["bible_context"]` が設定される。

**3. bible 取得のエラー安全化（対象: `master_nodes.py`）**
存在しない場合 `{}` を代入し `try/except` でラップ。受け入れ: bible 不在でも停止しない。

**4. `user_instructions` 伝播（対象: `master_nodes.py`）**
`state["metadata"].get("user_instructions","")` を `plot_input` へ渡す。受け入れ: 指示が含まれる。

**5. 初期プロンプトの bible 利用確認（対象: `plot_nodes.py:46-48`）**
`json.dumps(bible_context)` が実体を出すことをログ確認。受け入れ: ログに世界観 JSON。

**6. `summarize_bible` ヘルパ追加（対象: `utils.py`）**
`summarize_bible(bible, max_chars=1500)` で切り詰め。受け入れ: 1500超を切る単体テスト通る。

**7. 要約 bible の適用（対象: `plot_nodes.py:48`）**
bible 埋め込みを `summarize_bible` 経由に変更。受け入れ: プロンプト長が上限内。

**8. P0-A 統合テスト（対象: `tests/workflows/test_plot_graph.py`）**
bible 付きで呼び反映を断言。受け入れ: テスト緑。

**9. `strip_code_fence` ヘルパ（対象: `utils.py`）**
```json/``` と散文を除去し純 JSON を返す。受け入れ: フェンス付きを parse できる単体テスト。

**10. 初期生成パース置換（対象: `plot_nodes.py:80-85`）**
`json.loads` を `strip_code_fence` 経由に。受け入れ: フェンス付きでも list。

**11. リファイン・パース置換（対象: `plot_nodes.py:261-266`）**
同上を refine 側へ。受け入れ: リファインでも失敗しない。

**12. `PlotEpisode`/`PlotBatch` スキーマ追加（対象: `schemas.py`）**
ep_num/title/summary/next_hook/3tension を Pydantic 定義。受け入れ: import 可。

**13. 初期生成へ schema 適用（対象: `plot_nodes.py:69-75`）**
`generate_json(..., response_schema=PlotBatch)` を渡す。受け入れ: 構造化応答。

**14. パース失敗の error 化（対象: `plot_nodes.py:80-85`）**
除去後も失敗なら `status="error"` で `[]` 回避。受け入れ: 失敗時は空でなく error。

**15. 評価例外の `is_approved=False`（対象: `plot_nodes.py:204-209`）**
フォールバックを `is_approved=False, score=0.0` に。受け入れ: 例外時に refine へ回る。

**16. 評価失敗ログ強化（対象: `plot_nodes.py:203`）**
`logger.error` にプロンプト冒頭を含める。受け入れ: ログに手がかり。

**17. 評価例外の回帰テスト（対象: `tests/`）**
例外時に `is_approved=False` になるモック追加。受け入れ: テスト緑。

**18. P0 全体動作確認（手動）**
短編生成で世界観反映・JSON 崩れゼロ・評価機能を目視。受け入れ: 異常なし。

## フェーズB：プロット基盤・可観測（P1）ステップ 19〜30

**19. `plot_langgraph.py` 参照洗い出し（grep）**
本番参照が `tests/` のみか確認。受け入れ: リスト化。

**20. テストの import 付け替え（対象: `tests/integration/test_plot_workflow.py`）**
`PlotGraphManager` 参照を `graphs/plot_graph` に変更。受け入れ: 新モジュールを指す。

**21. レガシー削除（対象: `plot_langgraph.py`）**
ファイル削除。受け入れ: grep で参照ゼロ。

**22. 削除回帰（対象: 全体 pytest）**
`pytest` 緑。受け入れ: エラーなし。

**23. audit モデル分離（対象: `router.py:9`）**
`"audit": "gemini-3.5-flash"` へ（config `models.yaml` も同期）。受け入れ: `resolve_model("audit")` が flash。

**24. プロファイル同期（対象: `llm_profiles/*`）**
planning=lite, audit=flash を全プロファイル反映。受け入れ: 設定整合。

**25. モデル分離単体テスト（対象: `tests/unit/`）**
`resolve_model("planning")!=resolve_model("audit")` を断言。受け入れ: テスト緑。

**26. `PlotRunMetrics` 追加（対象: `utils.py`）**
model/input_chars/score/iter を持つ dataclass。受け入れ: import 可。

**27. 初期生成計測（対象: `plot_nodes.py`）**
入力文字数・使用モデルを `PlotRunMetrics` で `logger.info`。受け入れ: ログに文字数。

**28. 評価計測（対象: `plot_nodes.py`）**
score/is_approved/issues_count をログ出力。受け入れ: スコア可視。

**29. リファイン計測（対象: `plot_nodes.py`）**
iteration・使用モデルをログ出力。受け入れ: ループ回数可視。

**30. P1 計測テスト（対象: `tests/`）**
ログをキャプチャし主要項目が出ることを確認。受け入れ: テスト緑。

## フェーズC：プロット品質ゲート（既存にない独自分）ステップ 31〜50

**31. `logic_validator` シグネチャ確認（対象: `engine`）**
PlotGraph から呼べる `validate(blueprint)` の引数を確認。受け入れ: 呼び方ドキュメント化。

**32. Plan-time audit ノード追加（対象: `plot_nodes.py`）**
`audit_blueprint_node(state)` を新設し `logic_validator.audit(parsed_plots)` 実行。受け入れ: ノード定義。

**33. グラフ組込（対象: `graphs/plot_graph.py`）**
init → audit_blueprint → evaluate の順にエッジ追加。受け入れ: コンパイル可。

**34. audit 結果の状態反映（対象: `plot_nodes.py`）**
矛盾件数を `state["logic_issues"]` に格納。受け入れ: 状態保持。

**35. 矛盾時 refine 誘導（対象: `plot_edges.py`）**
`logic_issues>0` なら refine へ回す条件追加。受け入れ: 矛盾時にループ。

**36. Plan-time audit テスト（対象: `tests/`）**
矛盾含みプロットで refine 発火を断言。受け入れ: テスト緑。

**37. プロット厳密型バリデーション追加（対象: `schemas.py`）**
`PlotEpisode` に `ep_num>=1`・`summary` 非空・tension 範囲の制約を付与。受け入れ: 単体テスト通る。

**38. バリデーション適用（対象: `plot_nodes.py`）**
生成後に pydantic で各話検証し不合格話をリスト化。受け入れ: 不正話が検出される。

**39. バリデーション単体テスト（対象: `tests/`）**
欠損フィールドで検証失敗を断言。受け入れ: テスト緑。

**40. evaluate 差分入力化（対象: `plot_nodes.py:144`）**
未承認話のみ `json.dumps` する `diff_plots(parsed, approved)` 使用。受け入れ: 入力短縮。

**41. refine 差分入力化（対象: `plot_nodes.py:238`）**
同上を refine 側へ。受け入れ: 入力短縮。

**42. 差分入力単体テスト（対象: `tests/`）**
`diff_plots` が未承認話のみ返すことを断言。受け入れ: テスト緑。

**43. プロット予算 `plot_budget` 追加（対象: `state.py`）**
`PlotGraphState` に `plot_budget: int = 200000`（token）を追加。受け入れ: 定義あり。

**44. 予算計測（対象: `plot_nodes.py`）**
各呼び出しの推定 token を `PlotRunMetrics` に加算。受け入れ: 累積 token が出る。

**45. 予算超過フォールバック（対象: `plot_edges.py`）**
`plot_budget` 超過で強制 END。受け入れ: 超過時にループ停止。

**46. 話間連続性事前検証ノード（対象: `plot_nodes.py`）**
`check_cross_episode_node` で「同一キャラの所在/関係が話跨ぎで矛盾しないか」をプロット段で検証。受け入れ: ノード定義。

**47. 連続性検証プロンプト（対象: `prompts/plotting.py`）**
`CROSS_EPISODE_CHECK_TEMPLATE` 追加（既存⑥台帳の「事前」版）。受け入れ: 定数追加。

**48. 連続性不合格の refine 誘導（対象: `plot_edges.py`）**
矛盾ありなら refine へ。受け入れ: ループする。

**49. 連続性テスト（対象: `tests/`）**
矛盾プロットで refine 発火を断言。受け入れ: テスト緑。

**50. プロット回帰テスト雛形（対象: `tests/workflows/`）**
bible 付き・論理監査・連続性が通る e2e 雛形を追加。受け入れ: テスト緑。

## フェーズD：プロット差別化（既存にない独自分）ステップ 51〜72

**51. テンション目標テンプレート（対象: `prompts/plotting.py`）**
ジャンル別理想曲線 `TENSION_CURVE_TEMPLATES` 定義。受け入れ: 定数追加。

**52. テンション検証ノード（対象: `plot_nodes.py`）**
`check_tension_curve_node` で実測 deltas を理想曲線と比較。受け入れ: ノード定義。

**53. 中だるみ検出（対象: `plot_nodes.py`）**
山場間隔が広い話をフラグ。受け入れ: フラグが出る。

**54. テンション再設計 refine 誘導（対象: `plot_edges.py`）**
フラグありなら refine へ。受け入れ: ループする。

**55. 離脱予測ノード（対象: `plot_nodes.py`）**
各話冒頭に `EARLY_ENTERTAINMENT_CHECK_TEMPLATE` 適用（既存④の「プロット段事前版」）。受け入れ: ノード定義。

**56. 低 interest 自動補強（対象: `plot_nodes.py`）**
`interest_score` 閾値未満を refine へ。受け入れ: 弱話が回る。

**57. 離脱予測テスト（対象: `tests/`）**
低スコア話で refine 発火を断言。受け入れ: テスト緑。

**58. キャラアーク整合（plot 段）（対象: `plot_nodes.py`）**
`character_arc_extraction` とプロットを照合し、事件が成長軌跡と矛盾しないか検証。受け入れ: ノード定義。

**59. アーク矛盾 refine 誘導（対象: `plot_edges.py`）**
矛盾ありなら refine へ。受け入れ: ループする。

**60. キャラアーク整合テスト（対象: `tests/`）**
矛盾で refine 発火を断言。受け入れ: テスト緑。

**61. Emotional Hook 採点（対象: `plot_nodes.py`）**
`EMOTIONAL_HOOK_TEMPLATE` を全話へ適用し `hook_score` 記録（既存⑦の「計画段」版）。受け入れ: スコア記録。

**62. climax `is_catharsis` 確定（対象: `plot_nodes.py`）**
最高話に `is_catharsis=True` をセット。受け入れ: フラグあり。

**63. Hook 採点テスト（対象: `tests/`）**
各話に `hook_score` が入ることを断言。受け入れ: テスト緑。

**64. 市場適応プロンプト（対象: `prompts/plotting.py`）**
`trend_memo` を初期生成へ逆送する `MARKET_AWARE_PLOT_TEMPLATE`（既存⑧の「計画段」版）。受け入れ: 定数追加。

**65. トレンドABテスト（plot 段）（対象: `plot_nodes.py`）**
複数コンセプトを `build_marketing_ab_test_prompt` で採点し勝ちを採用。受け入れ: ノード定義。

**66. 市場適応テスト（対象: `tests/`）**
AB で勝ち案が `parsed_plots` に入ることを断言。受け入れ: テスト緑。

**67. プロット差分プレビュー生成（対象: `plot_nodes.py`）**
変更前後プロットの差分テキスト生成（既存⑨ HITL の「提示素材」）。受け入れ: 差分文字列出る。

**68. 差分プレビュー SSE 送信（対象: `master_nodes.py`）**
既存⑨の承認待ちに差分を添えて送信。受け入れ: ペイロードに diff 含む。

**69. プロンプト一元化（対象: `prompts/plotting.py`）**
プロット関連定数を1ファイルに集約し、ノードからの参照を統一。受け入れ: 重複定数なし。

**70. ループセマンティクス明文化（対象: `plot_edges.py`）**
`max_iterations` = refine 回数とコメント固定し `should_refine_plot` 調整。受け入れ: 仕様通り回数。

**71. `tension_delta` 検証・活用（対象: `plot_nodes.py`）**
初期プロンプトの3 tension を evaluate で「起承転結として妥当か」チェックし refine で整合。受け入れ: 検証される。

**72. 全体統合テスト＋ドキュメント（対象: `tests/`, `docs/`）**
全フェーズ e2e と本計画完了サマリを docs へ追記。受け入れ: pytest 緑・ドキュメント整合。

## 完了の定義
- `pytest` 全緑（新規＋既存）。
- 短編生成で「世界観反映・論理監査・話間連続性・テンション曲線・離脱予測・人間編集差分」が動作。
- lite モデルのみ（audit は flash 可）で再現し、JSON 破損ゼロ。
- 既存計画（⑤⑥⑦⑧⑨④等）との重複実装なし。
