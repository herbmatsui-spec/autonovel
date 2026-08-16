# コードレビュー追跡: 実装計画書

**作成日**: 2026-08-16
**ベース**: 2026-08-16 実施のコードレビュー結果
**対象**: 覇権小説エンジン v3.3

---

## 概要

コードレビューで検出された課題を優先度順に整理し、実装タスクとして分解した計画書です。全 **23タスク**、**推定工数: 約 12-16 時間**。

---

## タスク一覧

### 🔴 Critical (即時対応: 計 45 分)

| ID | タスク | ファイル | 工数 | 詳細 |
|----|--------|----------|------|------|
| C-01 | `_normalize_response` / `_usage_metric` 重複削除 | `src/core/llm_gateway.py` | 5分 | 262-287行目を削除、92-110行目を残す |
| C-02 | `"DUMMY"` APIキーを Settings 注入に変更 | `src/core/container/app.py` | 10分 | `providers.Object("DUMMY")` → `providers.Callable(get_settings().gemini_api_key)` 等 |
| C-03 | `connection_pipeline` 実装 or 削除判断 | `src/core/container/app.py` | 10分 | 使用箇所を grep し、未使用なら削除、使用なら実装 |
| C-04 | `polishing_min_content_ratio` 重複削除 | `config/settings.py` | 2分 | 209行目を削除（159行目を残す） |
| C-05 | `_normalize_response` 2つ目に `@staticmethod` 追加 or 統合 | `src/core/llm_gateway.py` | 2分 | C-01 で解決するが、念のため確認 |
| C-06 | 重複削除後の動作確認テスト実行 | - | 15分 | `pytest tests/ -k "llm" -xvs` 等で回帰確認 |

---

### 🟡 High (今スプリント内: 計 4-6 時間)

| ID | タスク | ファイル | 工数 | 詳細 |
|----|--------|----------|------|------|
| H-01 | `UltimateHegemonyEngine` コンストラクタ リファクタ | `src/backend/engine.py` | 2-4時間 | 13+引数を `EngineDeps` / `AgentDeps` データクラスにグループ化。ビルダーパターン導入検討 |
| H-02 | レガシーフォールバックを起動時検証に変更 | `src/backend/engine.py` | 1時間 | `__init__` 終了時に全必須デップが揃っているか `assert`、または `validate_dependencies()` メソッド追加して起動時呼出 |
| H-03 | `ENV_OVERRIDE_MAP` とフィールド整合性検証 | `config/settings.py` | 30分 | マップ全エントリが実フィールド名と一致するかスクリプトで確認、不一致修正 |
| H-04 | `InfraContainer` が Settings 参照するか確認・修正 | `src/core/container/infra.py` | 30分 | `redis_url`, `chroma_db_path` 等を `Settings()` 経由で取得するよう変更 |
| H-05 | フロントエント `eslint.config.js` 存在確認・修正 | `frontend/eslint.config.js` | 15分 | 存在しないなら作成、存在するなら `npm run lint` 通るか確認 |
| H-06 | pre-commit `no-print-statements` フックスクリプト化 | `.pre-commit-config.yaml`, `scripts/no_print_check.py` | 30分 | インライン Python を `scripts/no_print_check.py` に移動、フックから呼出 |

---

### 🟠 Medium (次スプリント: 計 3-4 時間)

| ID | タスク | ファイル | 工数 | 詳細 |
|----|--------|----------|------|------|
| M-01 | `_build_prev_context` トークンベース切り捨て化 | `src/easy_mode/pipeline.py` | 1時間 | `tiktoken` 等でトークン数計算、設定値 `context_window_min_reserve` 考慮 |
| M-02 | `limit_concurrency` 実装確認・テスト追加 | `src/core/async_utils.py` | 30分 | 存在確認、未実装なら実装、既存なら単体テスト追加 |
| M-03 | CI で LLM ヘルスチェック有効化判断 | `.github/workflows/ci.yml` | 15分 | `KAKU_HEALTH_CHECK_LLM=true` で実行するか、モックで代替するか決定・実装 |
| M-04 | テストディレクトリ構造再編成 | `tests/` | 1時間 | `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/phase1-3/` 等に移動、import パス修正 |
| M-05 | `requirements.txt` ランタイム/開発分離 | `pyproject.toml`, `requirements.txt` | 30分 | `pyproject.toml` に `[project.dependencies]` と `[project.optional-dependencies.dev]` 追加 |
| M-06 | `pyproject.toml` に `project.dependencies` 追加 | `pyproject.toml` | 15分 | `requirements.txt` ランタイム分を `dependencies` に移植 |
| M-07 | Dockerfile レビュー・改善 | `Dockerfile`, `frontend/Dockerfile` | 1時間 | マルチステージ、非 root、distroless/base image 見直し、レイヤーキャッシュ最適化 |

---

### 🟢 Low (余裕あれば / 技術的負債: 計 2-3 時間)

| ID | タスク | ファイル | 工数 | 詳細 |
|----|--------|----------|------|------|
| L-01 | `py.typed` マーカー追加 | `src/py.typed` | 5分 | 空ファイル作成で PEP 561 対応 |
| L-02 | SpiceGuard アルゴリズム ドキュメント化 | `docs/architecture/spice_guard.md` | 1時間 | 抽出・マーカー注入・除去の詳細フロー、類似度閾値根拠等記載 |
| L-03 | フロントエンド Storybook 導入 | `frontend/` | 2時間 | `npx storybook@latest init`、主要コンポーネント stories 作成 |
| L-04 | ADR: LangGraph 採用理由 追加 | `docs/adr/0004-langgraph-adoption.md` | 30分 | カスタムパイプラインとの比較、決定理由記録 |
| L-05 | 廃止予定ベンチマークスクリプト削除/移行 | `tests/benchmark_streamlit.py` | 15分 | Streamlit 参照部分削除、または現行フロントエンド用に書き換え |
| L-06 | `xenon` 複雑度しきい値見直し | `.pre-commit-config.yaml` | 10分 | `--max-absolute B` 等が現状コードで通るか確認、必要なら緩和 |

---

## 実装順序推奨

### Phase 1: Critical 即時修正 (Day 1, 1時間)
```
C-01 → C-02 → C-03 → C-04 → C-05 → C-06
```
- 全て小さな変更、競合リスク低
- 完了後 `ruff check src/ && mypy src/` で回帰なし確認

### Phase 2: High 優先リファクタ (Day 1-2, 4-6時間)
```
H-01 → H-02 → H-03 → H-04 → H-05 → H-06
```
- H-01 (エンジンコンストラクタ) が最大の山場。先に設計ドキュメント化推奨
- H-02 は H-01 と同時並行可
- H-03, H-04 は独立して実施可

### Phase 3: Medium 改善 (Day 3-4, 3-4時間)
```
M-01 → M-02 → M-03 → M-04 → M-05 → M-06 → M-07
```
- M-04 (テスト再編成) は import 大量変更伴うため、他タスク完了後推奨
- M-07 (Dockerfile) は独立して実施可

### Phase 4: Low 余裕枠 (随時)
- 優先度低、技術的負債解消枠としてスケジュール

---

## 完了定義 (Definition of Done)

各タスク共通:
- [ ] 実装完了
- [ ] 既存テスト全パス (`pytest tests/ -x`)
- [ ] `ruff check src/` エラー 0
- [ ] `mypy --config-file pyproject.toml src/` エラー減少傾向 (strict 維持)
- [ ] 該当する場合、新規テスト追加 (単体/統合)

Critical/High 追加:
- [ ] 破壊的変更の場合、移行ガイド or CHANGELOG 更新
- [ ] CI パイプライン グリーン確認

---

## リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| H-01 リファクタで既存コード大量破壊 | 高 | 段階的移行: 新旧両対応期間設け、deprecation warning で誘導 |
| M-04 テスト移動で import エラー多発 | 中 | `sed` / `ruff` 一括置換スクリプト作成、小単位でコミット |
| C-02 APIキー注入で DI 循環参照発生 | 低 | `InfraContainer` → `AppContainer2` 依存方向確認、必要なら `providers.Resource` 使用 |
| H-02 起動時検証でテスト環境が壊れる | 中 | テスト用 `Settings` オーバーライド機構 (`reset_settings()`) 確認済み活用 |

---

## 検証コマンド集

```bash
# Lint / Typecheck
ruff check src/ tests/
mypy --config-file pyproject.toml src/

# テスト
pytest tests/ -x -q
pytest tests/unit -x -q
pytest tests/integration -x -q

# 文字化けチェック
git grep -P "\xEF\xBF\xBD" -- '*.py' '*.md' '*.yaml' '*.yml' '*.toml' '*.json' '*.txt'

# Pre-commit 全実行
pre-commit run --all-files

# フロントエンド
cd frontend && npm run lint && npm run test:run
```

---

## 進捗トラッキング

| タスク | ステータス | 担当 | 着手日 | 完了日 | 備考 |
|--------|------------|------|--------|--------|------|
| C-01 | 待機 | - | - | - | |
| C-02 | 待機 | - | - | - | |
| C-03 | 待機 | - | - | - | |
| C-04 | 待機 | - | - | - | |
| C-05 | 待機 | - | - | - | |
| C-06 | 待機 | - | - | - | |
| H-01 | 待機 | - | - | - | 設計ドキュメント先行推奨 |
| H-02 | 待機 | - | - | - | |
| H-03 | 待機 | - | - | - | |
| H-04 | 待機 | - | - | - | |
| H-05 | 待機 | - | - | - | |
| H-06 | 待機 | - | - | - | |
| M-01 | 待機 | - | - | - | |
| M-02 | 待機 | - | - | - | |
| M-03 | 待機 | - | - | - | |
| M-04 | 待機 | - | - | - | |
| M-05 | 待機 | - | - | - | |
| M-06 | 待機 | - | - | - | |
| M-07 | 待機 | - | - | - | |
| L-01 | 待機 | - | - | - | |
| L-02 | 待機 | - | - | - | |
| L-03 | 待機 | - | - | - | |
| L-04 | 待機 | - | - | - | |
| L-05 | 待機 | - | - | - | |
| L-06 | 待機 | - | - | - | |

---

## 関連ドキュメント

- [コードレビュー結果](コードレビュー結果の会話履歴参照)
- [IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md](IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md) — 過去の 48ステップ計画 (完了済み)
- [CHANGELOG.md](CHANGELOG.md)
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)

---

**次回レビュー予定**: Phase 1 完了時点 (Critical 全完了後)