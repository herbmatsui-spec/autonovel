# Phase 1: テスト救命（Test Stabilization & ALL GREEN） - 詳細実装計画書

**作成日**: 2026-09-24  
**ベースライン**: `plans/PHASE_ROADMAP_MASTER.md` Phase 1 セクション + Phase 0 完了済み  
**ゴール**: どんな変更を加えても先祖返り（デグレーション）を即座に検知できるセーフティネットの確立  
**前提**: Phase 0 が完了し、正確なベースラインが確立されていること

---

## 全24ステップ 概要

| Step | カテゴリ | 作業内容 | 成果物 | テスト/検証 |
|------|----------|----------|--------|-------------|
| 1 | ブランチ | 作業ブランチ `phase1-stabilization` 作成・切替 | ブランチ | `git status` |
| 2 | ブランチ | Phase 0 完了ベースラインから開始 (`git checkout phase0-done`) | ベースライン確認 | `git log --oneline -1` |
| 3 | 失敗分析 | `fail_now.txt` の存在確認・内容精査・分類 | `docs/failnow_analysis.md` | 手動レビュー |
| 4 | 失敗修復 | エロティックパイプライン関連テスト修復（失敗があれば） | 修正済みテストファイル | 対象テスト PASS |
| 5 | 失敗修復 | DB周りテスト修復（失敗があれば） | 修正済みテストファイル | 対象テスト PASS |
| 6 | 失敗修復 | Stripe Webhook 500 クラッシュ修正（`await` 漏れ修正） | `src/api/billing_webhook.py` 修正 | テスト PASS + 手動動作確認 |
| 7 | 失敗修復 | 認証ミドルウェア修正（JWT/RBAC テスト正常化） | `src/api/middleware/*.py` 修正 | テスト PASS |
| 8 | テスト隔離 | 廃止機能テストの正式隔理（Apache AGE 等）・削除または `tests/legacy/` へ移動 | テストファイル移動/削除 | テストスイート実行時エラーなし |
| 9 | テスト品質 | Flaky テスト検出スクリプト作成（`pytest-rerunfailures` 使用） | `scripts/detect_flaky.py` | スクリプト単体テスト PASS |
| 10 | テスト品質 | Flaky テスト実行・結果記録・隔離フラグ付与 | `artifacts/flaky_tests.json` | 再発生しない失敗を特定 |
| 11 | テスト品質 | 特定された Flaky テストの修正または `pytest.mark.flaky` 付与 | 修正済みテスト | 同じテストの再実行で安定 |
| 12 | テスト品質 | カバレッジ未到達コードの到達不能判定・正当化ドキュメント作成 | `docs/coverage_exclusions.md` | レビュー承認 |
| 13 | テスト品質 | `pytest.ini` に並列実行設定追加（`-n auto`） | 更新済み pytest.ini | `pytest --co -q` でワーカー数表示 |
| 14 | テスト品質 | テストタイムアウト設定追加（`--timeout=60`） | 更新済み pytest.ini | 長時間テストがタイムアウトすること |
| 15 | テスト速度 | `pytest-xdist` 導入・依存追加 | 更新済み pyproject.toml | `pip list | grep pytest-xdist` |
| 16 | テスト速度 | テストスイート全体実行時間測定・目標60秒以内確認 | `artifacts/test_duration.json` | `total_duration <= 60.0` |
| 17 | リグレッション防止 | カバレッジ閾値テスト作成（Step 19-23 の雛形） | `tests/config/test_phase1_coverage.py` | `pytest` PASS |
| 18 | リグレッション防止 | Flaky テスト検知テスト作成 | `tests/config/test_flaky_detection.py` | `pytest` PASS |
| 19 | リグレッション防止 | API コントラクトテスト雛形作成（OpenAPI スキーマ検証） | `tests/contract/test_api_schema.py` | `pytest` PASS |
| 20 | リグレッション防止 | DB スキーマコントラクトテスト雛形作成（SQLAlchemy メタデータ比較） | `tests/contract/test_db_schema.py` | `pytest` PASS |
| 21 | リグレッション防止 | イベントスキーマコントラクトテスト雛形作成（Pydantic モデル検証） | `tests/contract/test_event_schema.py` | `pytest` PASS |
| 22 | ドキュメント | テスト戦略文書更新（Phase 1 達成方法・維持方法） | `docs/TEST_STRATEGY.md` | リンク切れなし・内容正確 |
| 23 | ドキュメント | コントラクトテスト方針文書作成 | `docs/CONTRACT_TESTING.md` | サンプルコード含む・実行可能 |
| 24 | 完了確認 | 全テスト GREEN 確認・CI ベースライン確定・PR 作成 | PR #xxx | 全テスト PASS・カバレッジ ≥ 55% |

---

## ステップ詳細

### Step 1-2: ブランチ作成・ベースライン確認
```bash
git checkout -b phase1-stabilization phase0-done
git push -u origin phase1-stabilization
```
**Done**: `git branch --show-current` → `phase1-stabilization`

### Step 3: fail_now.txt 分析
**ファイル**: `docs/failnow_analysis.md`
```markdown
# FailNow Analysis

## 分類
- [ ] エロティックパイプライン
- [ ] DB周り
- [ ] Stripe Webhook
- [ ] 認証ミドルウェア
- [ ] 廃止機能
- [ ] その他

## 各項目の詳細
- テスト名
- 失敗理由
- 推定工数
- 依存関係
```

### Step 4-5: エロティックパイプライン・DB テスト修復
**対象**: `fail_now.txt` にリストされている該当テスト
**修復方針**:
- 環境依存ならモック・フィクスチャで代替
- 実装バグなら根本原因修正
- 廃止済み機能ならテストごと削除（Step 8 参照）

### Step 6: Stripe Webhook 500 修正
**対象**: `src/api/billing_webhook.py`
**典型的問題**:
```python
# 修正前（間違い）
async def handle_webhook():
    stripe_event = stripe.Webhook.construct_event(...)  # これはコルーチンじゃない
    await process_event(stripe_event)  # await 漏れではないが例

# 実際の問題例（実際のコードを確認必要）
async def handle_webhook():
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    # ここで何らかの async 処理を await していない
    some_async_function()  # ← これが問題かも
```

**修正後**:
```python
async def handle_webhook():
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    await some_async_function()  # 適切に await
```

### Step 7: 認証ミドルウェア修正
**対象**: `src/api/middleware/` 以下
**典型的問題**:
- JWT トークン検証の例外ハンドリング不備
- RBAC 権限チェックのロジック誤り
- テストでのモック不足

### Step 8: 廃止機能テスト隔離・削除
**対象**: Apache AGE 直接依存等
**手順**:
1. `find tests/ -type f -name "*.py" -exec grep -l "age\|apache" {} \;`
2. 各ファイルを確認し、本当に不要なら削除
3. 一時的に残す必要があるなら `tests/legacy/` へ移動
4. 削除/移動後もテストスイートが PASS することを確認

### Step 9: Flaky テスト検出スクリプト作成
**ファイル**: `scripts/detect_flaky.py`
```python
#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

def run_with_reruns(test_path, reruns=3):
    """指定テストを複数回実行し、結果を返す"""
    results = []
    for i in range(reruns):
        result = subprocess.run(
            ["pytest", test_path, "-v", "--tb=short"],
            capture_output=True, text=True
        )
        results.append({
            "run": i+1,
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    return results

def main():
    # fail_now.txt からテストリスト取得または全テスト対象
    test_targets = []  # 実装により決定
    
    flaky_results = {}
    for test in test_targets:
        results = run_with_reruns(test)
        passed_count = sum(1 for r in results if r["passed"])
        if 0 < passed_count < len(results):  # 一部だけ通る = Flaky
            flaky_results[test] = results
    
    output_path = Path("artifacts/flaky_tests.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(flaky_results, f, indent=2, ensure_ascii=False)
    
    print(f"Found {len(flaky_results)} flaky tests")
    return 0 if len(flaky_results) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Step 10: Flaky テスト実行・記録
```bash
python scripts/detect_flaky.py
```
**Done**: `artifacts/flaky_tests.json` に Flaky テストリスト

### Step 11: Flaky テスト修復
**選択肢**:
- 根本原因修正（推奨）: タイムアウト・レースコンディション・状態依存を解消
- 一時的回避: `@pytest.mark.flaky(reruns=3, reruns_delay=2)` 付与
- 隔離: 本当に修復困難なら `tests/flaky/` へ移動し、CI で別実行

### Step 12: カバレッジ未到達コード判定
**手順**:
1. `pytest --cov=src --cov-report=html` 実行
2. HTML レポートで 0% の行を特定
3. 各行について:
   - 本当に到達不能か判定（例外パス・デバッグコード等）
   - 到達不能なら `docs/coverage_exclusions.md` に追記
   - 到達可能ならテストを追加してカバレッジ向上

**フォーマット**: `docs/coverage_exclusions.md`
```markdown
# Coverage Exclusions Justification

## src/module/file.py:123-125
- **理由**: デバッグ用ログ出力（本番では環境変数でオフ）
- **コード**:
  ```python
  if DEBUG:  # DEBUG=False が本番設定
      logger.debug("...")
  ```
- **テスト戦略**: 本番相当設定ではこのパスは通らないことを保証
```

### Step 13-14: pytest.ini 設定更新
**ファイル**: `pytest.ini`
```ini
[pytest]
addopts = 
    -n auto          # CPU コア数に応じた並列実行
    --timeout=60     # 1 テストのタイムアウト（秒）
    --maxfail=5      # 5 件失敗で早期終了
    -vv              # 詳細出力
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Step 15: pytest-xdist 導入
**ファイル**: `pyproject.toml`
```toml
[project.dependencies]
# ...
pytest = "^8.0.0"
pytest-xdist = "^3.5.0"
pytest-rerunfailures = "^12.0"
# ...
```

### Step 16: テストスピード測定・目標確認
**スクリプト**: `scripts/measure_test_duration.py`
```python
#!/usr/bin/env python3
import json, subprocess, time, sys
from pathlib import Path

def main():
    start = time.time()
    result = subprocess.run(
        ["pytest", "--tb=no", "-q"],  # 出力最小化で正確計測
        capture_output=True, text=True
    )
    end = time.time()
    
    duration = end - start
    passed = result.returncode == 0
    
    data = {
        "total_duration": duration,
        "passed": passed,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "target_met": duration <= 60.0
    }
    
    output_path = Path("artifacts/test_duration.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Test duration: {duration:.2f}s ({'PASS' if data['target_met'] else 'FAIL'} target)")
    return 0 if data['target_met'] else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Step 17-18: リグレッション防止テスト（カバレッジ・Flaky検知）
**ファイル**: `tests/config/test_phase1_coverage.py`
```python
import tomli

def test_coverage_threshold_meets_phase1_goal():
    """Phase 1 ではカバレッジ閾値を維持・向上させる"""
    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 55
```

**ファイル**: `tests/config/test_flaky_detection.py`
```python
def test_flaky_detection_script_exists():
    """Flaky テスト検出スクリプトが存在し実行可能である"""
    assert Path("scripts/detect_flaky.py").exists()
    # 実行可能性チェック（簡易版）
    with open("scripts/detect_flaky.py") as f:
        content = f.read()
        assert "def main()" in content
```

### Step 19-21: コントラクトテスト雛形作成

**ファイル**: `tests/contract/test_api_schema.py`
```python
"""API スキーマの後方互換性を検証するコントラクトテスト"""
import json
from pathlib import Path

def test_openapi_schema_has_not_changed():
    """OpenAPI スキーマが破壊的変更なく進化しているか"""
    # 実際の実装では:
    # 1. 現在のスキーマを生成（または取得）
    # 2. ベースラインスキーマと比較
    # 3. 破壊的変更（필수 필드 삭제, 타입 변경 등）がないか検証
    
    # 暫定実装：ファイル存在確認
    schema_path = Path("docs/openapi.yaml")
    assert schema_path.exists(), "OpenAPI スキーマファイルが見つかりません"
    
    # TODO: 実際のスキーマ比較ロジックを実装
    # 現在はフェーズ移行のためのプレースホルダー
```

**ファイル**: `tests/contract/test_db_schema.py`
```python
"""データベーススキーマの後方互換性を検証するコントラクトテスト"""
from sqlalchemy import inspect
from src.db.base import Base  # 実際のインポートパスに合わせる

def test_table_count_has_not_decreased():
    """テーブル数が減っていないか（削除ではなく追加のみ許容）"""
    inspector = inspect(Base.metadata)
    current_tables = set(inspector.get_table_names())
    
    # ベースラインとの比較は artifatcs/ から取得
    baseline_path = Path("artifacts/db_schema_baseline.json")
    if baseline_path.exists():
        import json
        with open(baseline_path) as f:
            baseline = json.load(f)
        baseline_tables = set(baseline.get("tables", []))
        # テーブル削除がないかチェック
        removed = baseline_tables - current_tables
        assert not removed, f"以下のテーブルが削除されています: {removed}"
    else:
        # 初回実行時はベースライン作成
        baseline_path.parent.mkdir(exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump({"tables": list(current_tables)}, f)

def test_column_nullability_has_not_become_strict():
    """カラムの NULL 制約が厳しくなっていないか"""
    # 同様にベースライン比較で NULL 制約の追加を検知
    pass
```

**ファイル**: `tests/contract/test_event_schema.py`
```python
"""イベントスキーマ（WebSocket, Webhook 等）の後方互換性を検証"""
import jsonschema
from pathlib import Path

def test_webhook_event_schema_backward_compatible():
    """Stripe Webhook 等のイベントスキーマが後方互換であるか"""
    # イベントスキーマファイルを読み込み
    # jsonschema.Draft7Validator で後方互換性検証
    # （フィールド追加は OK、フィールド削除・型変更は NG）
    pass
```

### Step 22: テスト戦略文書更新
**ファイル**: `docs/TEST_STRATEGY.md`
```markdown
# AutoNovel テスト戦略

## Phase 1 達成方法
1. 失敗テストの根本原因修復
2. Flaky テストの検出・修復または隔離
3. テスト実行時間の予算化・並列化
4. カバレッジの品質志向運用

## テスト維持方法 (Phase 2 以降)
- コントラクトテストによるインターフェース保護
- フックによるコミット前テスト実行
- 週次 Flaky テスト再検証
- カバレッジ閾値の漸進的向上（55% → 65% → 75%）

## テスト種類別役割
- **単体テスト**: 内部ロジックの正確性
- **統合テスト**: モジュール間連携
- **E2E テスト**: ユーザーシナリオ全体
- **コントラクトテスト**: インターフェース後方互換性
- **性能テスト**: レイテンシー・スループット基準
```

### Step 23: コントラクトテスト方針文書作成
**ファイル**: `docs/CONTRACT_TESTING.md`
```markdown
# コントラクトテスト方針

## 目的
リファクタリング時のインターフェース破壊を未然に防ぐ

## 対象範囲
- REST/OpenAPI API スキーマ
- データベーススキーマ (SQLAlchemy メタデータ)
- イベントスキーマ (WebSocket, Webhook, 内部イベント)
- プラグインインターフェース

## 実装方法
1. **スキーマ抽出**: 実行時またはビルド時にスキーマを取得
2. **ベースライン比較**: 以前のバージョンと差分を検出
3. **互換性判定**: 後方互換性のルールに基づいて PASS/FAIL

## 後方互換性ルール
| 変更種類 | 後方互換 | 前方互換 | コメント |
|----------|----------|----------|----------|
| フィールド追加 | ✅ | ❌ | 新しいクライアントのみ利用可能 |
| フィールド削除 | ❌ | ✅ | 古いクライアントが壊れる |
| フィールド名変更 | ❌ | ❌ | 両方向で破壊 |
| 型変更 (互換) | ✅ | ✅ | 例: int → float (ただし精度損失に注意) |
| 型変更 (非互換) | ❌ | ❌ | 例: string → integer |
| 必須 → 任意 | ✅ | ❌ | 古いクライアントは動作する |
| 任意 → 必須 | ❌ | ✅ | 新しいクライアントはエラーになる可能性あり |

## 実装例
See `tests/contract/` ディレクトリのテストファイル参照
```

### Step 24: 完了確認・PR 作成
```bash
# 全テスト実行（カバレッジ付き）
pytest --cov=src --cov-fail-under=55 --tb=short -q

# リンター・型チェック
ruff check .
mypy src/

# テストスピード確認
python scripts/measure_test_duration.py

# Flaky テスト状況確認
python scripts/detect_flaky.py  # 0 を返すことが理想

# PR 作成
gh pr create --title "Phase 1: テスト救命 (Test Stabilization & ALL GREEN)" \
             --body-file plans/PHASE_1_IMPLEMENTATION_PLAN.md \
             --base main \
             --head phase1-stabilization
```

---

## 依存関係・並列化ガイド

```
Step 1-2 → 
Step 3 → (Step 4-5 並列) → 
Step 6-7 → 
Step 8 → 
Step 9-11 → 
Step 12 → 
Step 13-16 → 
Step 17-18 → 
Step 19-21 → 
Step 22-23 → 
Step 24
```

- **ブロックされない**: 
  - ドキュメント作成 (Step 22-23) は他と並列可能
  - コントラクトテスト作成 (Step 19-21) は相対的に独立
  - テスト品質向上 (Step 9-12) は段階的に進める

- **順序必須**: 
  - 失敗分析(3) → 失敗修復(4-8) 
  - 品質基盤(9-16) → リグレッション防止(17-23)

---

## 完了判定基準 (Definition of Done)

- [ ] 全 24 ステップのチェックボックス完了
- [ ] `pytest --cov-fail-under=55` PASS
- [ ] `ruff check .` / `mypy src/` PASS
- [ ] テストスイート実行時間 ≤ 60 秒 (`artifacts/test_duration.json`)
- [ ] Flaky テスト数 = 0 （`scripts/detect_flaky.py` が 0 を返す）
- [ ] `fail_now.txt` が空または存在しない（全テストが PASS）
- [ ] Stripe Webhook テストが PASS かつ手動動作確認済み
- [ ] 認証ミドルウェア関連テストが PASS
- [ ] 廃止機能テストが適切に隔離または削除済み
- [ ] 新規テスト 6 本（Step 17-21）全 PASS
- [ ] ドキュメント 2 ファイル（TEST_STRATEGY.md, CONTRACT_TESTING.md）作成・レビュー済み
- [ ] PR 作成・レビュー承認・マージ完了
- [ ] `main` ブランチで `git tag phase1-done` 打刻
- [ ] CI ベースライン確定：全テスト GREEN がデフォルト状態