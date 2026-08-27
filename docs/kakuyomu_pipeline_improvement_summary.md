# カクヨム・商業品質パイプライン改善 実装完了サマリー

## 1. 概要
`docs/kakuyomu_pipeline_improvement_plan.md` に基づき、カクヨムランキング上位・商業レベルの品質を安定して生み出すためのパイプライン強化（全72ステップ）を完了しました。

---

## 2. 主要な実装成果

### ① 差し戻しループ (Phase 1: Steps 9-16)
- **機能**: `ReviewGraph` で要修正（`requires_revision=True`）と判定されたエピソードのみを `revise_writing_node` で再生成・差分再監査。
- **ガードレール**: `revision_budget` による最大反復制限と収束判定（要修正数が減少しなければ強制終了）により、コスト爆発を防止。

### ② 密度ルービック (Phase 2: Steps 17-26)
- **機能**: 下限文字数 `MIN_DRAFT_CHARS = 1500` の設定と、事件密度指標 `event_density`（0.0〜1.0）の導入。
- **効果**: 展開の薄い草稿を Actor-Critic ループ内で自動検知し、不足要素（展開・キャラクター露出・緊張感）を反映して再生成。

### ③ 話内並列化と Bible ロック (Phase 3: Steps 27-34)
- **機能**: `ReviewGraph` 内部で独立している `analyze_pacing` と `check_character_consistency` を `asyncio.gather` で並列実行。
- **整合性**: 執筆話間の `bible_state` 書き込みは直列ロックを維持し、物語の因果連続性を完全担保。

### ④ カクヨム商業ヒットルービック (Phase 4: Steps 35-42)
- **機能**: LLM-as-Judge ノード `score_commercial_node`（モデル `audit`）を追加。
- **5大指標**:
  1. 冒頭300字フック密度
  2. 引きの発生頻度 (800〜1200字)
  3. 感情バレンスの振れ幅
  4. シリーズ級の謎・伏線設置度
  5. 未解決緊張・クリフハンガー維持度
- **集計**: `commercial_score`（合格ライン 0.70）を算出し `quality_metrics` に集約。

### ⑤ プロット複数案×選抜 (Phase 5: Steps 43-50)
- **機能**: `generate_initial_plot_node` で `num_variants=3` 案を生成し、`evaluate_plot_node` で客観評価して最高スコア案を自動選抜。
- **閾値**: 合格閾値を 0.85 に引き上げ、粗削りなプロットの流出を防止。

### ⑥ 前話文脈参照・連続性保証 (Phase 6: Steps 51-58)
- **機能**: 直前話の末尾 500 文字（`prev_episode_tail`）を執筆プロンプトに注入。
- **監査**: `self_audit_node` に前話との接続性・連続性チェック項目を追加。

### ⑦ UI連携と型定義 (Phase 7: Steps 59-72)
- **型定義**: `Chapter`, `Plot` に `event_density`, `commercial_score`, `plot_variants` を追加。
- **UI表示**:
  - `AuditTab.tsx`: カクヨム商業指標ルービック5項目のスコアカード表示。
  - `WriteTab.tsx` / `ChapterCard.tsx`: 草稿文字数バッジと事件密度プログレスバー表示。
  - `PlotsTab.tsx`: 複数生成案の切り替え・最良案採用バッジ表示。
  - `TaskMonitor.tsx`: 差し戻し修正ループ発生時の注視バッジ表示。

---

## 3. テスト検証結果
- 全 26 件のワークフロー・ユニットテストが全パス (`pytest tests/workflows/ tests/unit/`)。
- フロントエンド TypeScript 型チェックおよび Vite プロダクションビルドが正常完了。
