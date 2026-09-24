# Phase 1 残りタスク 詳細実装計画書

## 作成日: 2026-09-24
## 目的: Flaky テストの検出・修復および最終検証を完了し、Phase 1 を達成する

## 残りタスク
1. Flaky テスト検出スクリプトの改善と実行
2. 特定された Flaky テストの修復またはマーク付与
3. 最終検証（テストスイート、リンター、型チェック、テスト時間、Flaky テスト数）
4. PR 作成

## 詳細手順

### Step 1: Flaky テスト検出スクリプトの改善
- 問題: 現在の `scripts/detect_flaky.py` は特定のテスト（例: test_marketing_agent.py）でタイムアウトする
- 改善案:
  a. テストごとのタイムアウトを延長（例: 60秒）
  b. 既知の問題のあるテストをスキップするリストを作成し、検出から除外
  c. テスト実行時に `--timeout` オプションを使用して pytest 自身のタイムアウトを設定
  d. テストがタイムアウトした場合は「フラキー」とは判定せず、別途調査対象とする

### Step 2: Flaky テスト検出の実行
- 改善後のスクリプトを実行し、`artifacts/flaky_tests.json` を生成
- フラキー テストが見つかった場合は、それぞれについて以下の対応を検討
  - 根本原因修復（推奨）: タイムアウト・レースコンディション・状態依存を解消
  - 一時的回避: `@pytest.mark.flaky(reruns=3, reruns_delay=2)` を付与
  - 隔離: 本当に修復困難なら `tests/flaky/` へ移動し、CI で別実行

### Step 3: 最終検証
1. テストスイート実行（カバレッジ付き）
   - `pytest --cov=src --cov-fail-under=55 --tb=short -q`
   - カバレッジ ≥ 55% かつ全テスト PASS を確認
2. リンター・型チェック
   - `ruff check .` （エラーがないこと）
   - `mypy src/` （エラーがないこと）
3. テストスピード確認
   - `python scripts/measure_test_duration.py` （`target_met: true` であること）
4. Flaky テスト状況確認
   - `python scripts/detect_flaky.py` （0 を返すことが理想）
   - 注意: フラキー テストを修復済みまたはマーク付与済みであるため、検出スクリプトはフラキーを検出しないはず

### Step 4: PR 作成
- ブランチ `phase1-stabilization` を `main` へプルリクエスト
- タイトル: `Phase 1: テスト救命 (Test Stabilization & ALL GREEN)`
- 本文: `plans/PHASE_1_IMPLEMENTATION_PLAN.md` を使用

## 完了判定基準
- [ ] Flaky テスト検出スクリプトが改善され、実行可能である
- [ ] 特定された Flaky テストが全て修復またはマーク付与されている
- [ ] `pytest --cov=src --cov-fail-under=55` が PASS
- [ ] `ruff check .` が PASS
- [ ] `mypy src/` が PASS
- [ ] テストスイート実行時間 ≤ 60 秒
- [ ] `scripts/detect_flaky.py` が 0 を返す
- [ ] PR が作成され、レビュー済みかつマージ済み

## 注意点
- 環境によっては一部のテストが外部リソースに依存してタイムアウトする可能性がある
  - その場合は、テストごとにモックまたはスタブを使用して外部依存を排除することを検討
- Flaky テストの修復は根本原因を優先するが、時間がかかる場合は一時的にマーク付与でも acceptable とする
- 最終検証は全ての条件を満たすまで繰り返し実行すること