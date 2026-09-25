# AutoNovel 実装計画書: Phase 3 & 4 統合および商用準備完了計画 (7 Steps)

**策定日**: 2026-09-24  
**マスターSSOT**: [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md)  
**対象ブランチ**: `phase3-easymode` ⇄ `phase4-production`  
**目的**: `phase3-easymode` で完了した「8オーディター集約・PDCAスリム化・Easy Mode」と、`phase4-production` で完了した「環境境界・本番Docker・Sentry/OTEL監視・ヘルスチェック」を単一の完成ブランチへ統合し、残存テストを解消して商用ローンチ可能な状態を確立する。

---

## 📋 全体工程概要

```
[Step 1: テスト救命・局所修正] ──► [Step 2: セーブポイント作成] ──► [Step 3: ブランチ統合]
 (test_local_polish.py 修正)     (phase3-easymode コミット)      (phase-master-integration)
             │
             ▼
[Step 4: ドキュメント/計画書同期] ──► [Step 5: 本番インフラ・監視設定疎通] ──► [Step 6: 総合テスト実行] ──► [Step 7: 最終検証・完了]
 (PHASE_ROADMAP_MASTER.md 等)       (Dockerfile.prod / Sentry / OTEL)        (E2E / Audit / Health)
```

---

## 🛠️ 各ステップの詳細定義

### Step 1: 局所パッチテスト（`test_local_polish.py`）の修正
- **目的**: `tests/generation/test_local_polish.py` におけるモック欠落と日本語文字列スライスのオフセット不整合を修正し、Phase 3 単体テスト全件 PASS を達成する。
- **対象ファイル**: [test_local_polish.py](file:///e:/hhh/tests/generation/test_local_polish.py)
- **修正内容**:
  1. `test_polish_preserves_context` に `@patch("src.generation.local_polish.call_llm_api")` を付与し、モック返り値を設定。
  2. `test_polish_calls_llm_with_correct_prompt` の `target_range` を `text.index("対象部分")` を用いた動的で正確なオフセット指定へ改修。
- **検証コマンド**: `pytest tests/generation/test_local_polish.py`
- **期待結果**: `4 passed, 0 failed`

### Step 2: Phase 3 作業ツリーのセーブポイントコミット作成
- **目的**: `phase3-easymode` の全完了作業（Step 1〜23）を確実に記録し、安全なマージ基準点を確定する。
- **対象ブランチ**: `phase3-easymode`
- **実行コマンド**:
  ```bash
  git add tests/generation/test_local_polish.py plans/PHASE_3_4_INTEGRATION_AND_PRODUCTION_PLAN.md
  git commit -m "fix(generation): fix mock and character slicing offset in test_local_polish"
  ```
- **期待結果**: 作業ツリーがクリーンな状態となること。

### Step 3: ブランチ統合（`phase-master-integration` の作成とマージ）
- **目的**: `phase3-easymode` と `phase4-production` の成果物を安全に統合する。
- **実行コマンド**:
  ```bash
  git checkout -b phase-master-integration phase4-production
  git merge phase3-easymode -m "Merge branch 'phase3-easymode' into phase-master-integration: integrate Phase 3 core lightweight & Easy Mode with Phase 4 production readiness"
  ```
- **競合発生時の対応方針**:
  - `src/audit/`, `src/generation/`, `web/easy_mode/`: `phase3-easymode` の最新実装を採用。
  - `src/monitoring/`, `src/api/health.py`, `Dockerfile.prod`, `config/`: `phase4-production` の本番設定を採用。
  - `pyproject.toml`: 依存関係（`cachetools`, `sudachipy` 等）をマージし、最新バージョン `5.1.0` に統一。

### Step 4: 計画書・ドキュメントおよびSSOTの同期
- **目的**: `plans/PHASE_ROADMAP_MASTER.md` および各フェーズ計画書（`PHASE_0`〜`PHASE_4`）が最新の統合ワーキングツリーに漏れなく配置されていることを保証する。
- **対象ファイル**:
  - `plans/PHASE_ROADMAP_MASTER.md`
  - `plans/PHASE_4_IMPLEMENTATION_PLAN.md`
  - `README.md`
- **検証コマンド**: `Get-ChildItem plans/ -Filter "PHASE_*.md"` で全計画書の存在を確認。

### Step 5: 本番インフラ・監視設定の疎通確認
- **目的**: Phase 4 で追加された本番コンポーネントが、Phase 3 の Easy Mode / オーディターと正しく連携することを確認。
- **対象ファイル**:
  - `src/config/env_loader.py`
  - `src/monitoring/sentry.py`
  - `src/monitoring/otel.py`
  - `src/api/health.py`
- **検証テスト**:
  - `pytest tests/api/test_health.py`
  - `pytest tests/monitoring/test_observability.py`
  - `pytest tests/config/test_env_isolation.py`
- **期待結果**: 全テスト PASS。

### Step 6: 統合テストスイートの実行（回帰防止・E2E）
- **目的**: Phase 3 の機能と Phase 4 の機能が同時に稼働する状態で、すべてのリグレッション防止テストが PASS することを確認。
- **対象テスト**:
  - `tests/audit/`（静的ルール・統合LLMオーディター・パイプライン等）
  - `tests/generation/`（PDCAコントローラー・局所パッチ・キャッシュ・フォールバック等）
  - `tests/e2e/test_easy_mode_flow.py`（Easy Mode E2E）
  - `tests/e2e/test_production_e2e.py`（本番構成 E2E）
- **実行コマンド**:
  ```bash
  pytest tests/audit/ tests/generation/ tests/e2e/test_easy_mode_flow.py tests/api/test_health.py tests/monitoring/
  ```
- **期待結果**: `0 failed, 0 errors`

### Step 7: 最終検証と成果サマリー作成
- **目的**: [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md) のゴール（低コスト・1話1分以内完走・本番安定性）の達成状況をエビデンス付きでレポートし、商用ローンチ準備を完了とする。

---

## ⚠️ リスクとロールバック手順
- **マージ競合リスク**: 万が一コンフリクトが複雑化した場合は `git merge --abort` で即時中止し、ファイル単位のパッチ適用（`git checkout phase3-easymode -- <files>`）へ切り替える。
- **既存テストへの影響**: 既存の別機能テストが壊れないよう、新ブランチ `phase-master-integration` 上で段階的に検証を進める。
