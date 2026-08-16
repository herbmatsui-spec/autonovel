# ミューテーションテスト導入

## 概要
コードの変更がテストで検出されるかを検証する「ミューテーションテスト」を導入し、テストの質を定量評価する。

## なぜミューテーションテストか

| 観点 | 従来のカバレッジ | ミューテーションテスト |
|------|-----------------|----------------------|
| **何を測るか** | コード実行率 | テストの「検出力」 |
| **偽陽性** | コード実行されればOK | ミューテーションが生存=テスト不足 |
| **リファクタリング検知** | できない | できる (ロジック変更を検知) |
| **テスト品質の指標** | 行数/分岐数 | ミューテーションスコア |

## ツール選定: `mutmut`

| ツール | 言語 | 速度 | 統合 | メンテナンス |
|--------|------|------|------|--------------|
| **mutmut** | Python | 高速 (並列) | pytest 直接対応 | 活発 |
| cosmic-ray | Python | 低速 | 別途設定 | 低頻度 |
| mutpy | Python | 中速 | 独自ランナー | 低頻度 |

**選定: `mutmut`** - 高速、pytest 統合が簡単、活発にメンテナンスされている。

## 導入手順

### 1. インストール
```bash
pip install mutmut
```

### 2. 設定ファイル作成
```toml
# pyproject.toml に追加
[tool.mutmut]
paths_to_mutate = ["src/"]
backup = false
runner = "python -m pytest"
tests_dir = "tests/"
dict_synonyms = {
    "==": "!=",
    "!=": "==",
    ">": "<=",
    "<": ">=",
    ">=": "<",
    "<=": ">",
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*",
    "in": "not in",
    "not in": "in",
    "True": "False",
    "False": "True",
    "and": "or",
    "or": "and",
    "is": "is not",
    "is not": "is",
}
```

### 3. 実行コマンド
```bash
# 初回実行 (ベースライン作成)
mutmut run --use-coverage

# 結果確認
mutmut results

# HTML レポート生成
mutmut html

# 特定ファイルのみ
mutmut run --paths-to-mutate=src/easy_mode/pipeline.py

# 並列実行 (CPU コア数指定)
mutmut run --runner="python -m pytest -x -q" --max-runners=4
```

## CI/CD 統合

```yaml
# .github/workflows/mutation.yml
name: Mutation Testing

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 3 * * 0'  # 毎週日曜 午前3時

jobs:
  mutation:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mutmut
      
      - name: Run mutation testing
        run: |
          mutmut run --use-coverage --max-runners=4
      
      - name: Check mutation score
        run: |
          SCORE=$(mutmut results | grep "Mutation score" | awk '{print $3}' | sed 's/%//')
          echo "Mutation score: $SCORE%"
          if (( $(echo "$SCORE < 60" | bc -l) )); then
            echo "❌ Mutation score below 60%: $SCORE%"
            exit 1
          fi
          echo "✅ Mutation score OK: $SCORE%"
      
      - name: Upload mutation report
        uses: actions/upload-artifact@v4
        with:
          name: mutation-report
          path: html/
          retention-days: 7
```

## 目標スコア

| フェーズ | 目標スコア | 期間 |
|---------|-----------|------|
| **Phase 1** | 40% | 導入直後 (現状把握) |
| **Phase 2** | 50% | 1ヶ月後 |
| **Phase 3** | **60%** | 3ヶ月後 (目標) |
| **Phase 4** | 70% | 継続的改善 |

## 対象外パス

```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = [
    "src/easy_mode/",
    "src/backend/",
    "src/core/",
    "src/services/",
    "src/agents/",
    "src/services/",
]
# 除外
exclude = [
    "tests/",
    "docs/",
    "config/",
    "scripts/",
    "*/migrations/*",
    "*_test.py",
    "*_test.pyi",
    "conftest.py",
]
```

## ミューテーション生存例と対策

### 典型的な生存パターン

| パターン | 原因 | 対策 |
|---------|------|------|
| `if x > 0` → `if x >= 0` | 境界値テスト不足 | `x = 0` のテスト追加 |
| `x + 1` → `x - 1` | 戻り値未検証 | 戻り値アサーション追加 |
| `True` → `False` | 条件分岐の片側のみテスト | 両分岐テスト追加 |
| `raise Exception` → 削除 | 例外発生パス未テスト | `pytest.raises` でテスト |
| `return x` → `return None` | 戻り値未使用 | 戻り値検証追加 |

### 実例: pipeline.py の境界値

```python
# 元コード
if audit_result.score >= self.config.target_audit_score:
    break

# ミューテーション: >= → >
if audit_result.score > self.config.target_audit_score:
    break

# 対策テスト
async def test_audit_score_boundary():
    # 境界値 95.0 で break することを確認
    result = await pipeline._generate_episode(...)
    assert result.audit_score >= 95.0  # 境界値テスト
```

## HTML レポート活用

```bash
# HTML レポート生成
mutmut html

# ブラウザで開く
open html/index.html
```

レポートで確認できること:
- **ファイル別生存率**: どのファイルが弱いか
- **行別生存**: 具体的にどの行が生存
- **ミューテーションタイプ**: どの種類の変更が検出されないか
- **履歴比較**: 前回実行からの改善/悪化

## 除外ルール

どうしても生存してしまうが仕様上問題ない場合:

```python
# pragma: no mutate
# 理由: 意図的な早期リターン、防御的プログラミング
if not items:
    return []  # pragma: no mutate
```

```toml
# pyproject.toml
[tool.mutmut]
# 特定行除外
exclude_lines = [
    "pragma: no mutate",
    "raise NotImplementedError",
    "pass  # pragma: no cover",
]
```

## 運用ルール

1. **PR ごと**: 変更ファイルのみミューテーション実行 (高速)
2. **夜間バッチ**: 全ファイル実行 (スケジュール)
3. **スコア低下時**: PR ブロック (CI で失敗)
4. **新規コード**: PR 作成時に最低 60% 維持必須
4. **レガシー改善**: 既存ファイルは段階的改善 (技術的負債チケット化)

## メトリクスダッシュボード

Grafana + Prometheus で可視化:

```yaml
# ダッシュボードクエリ例
mutation_score: (mutants_killed / mutants_total) * 100
survived_by_file: count by (file) (mutant_survived == 1)
mutation_types: count by (type) (mutant_status)
trend_7d: rate(mutation_score[7d])
```

## 導入スケジュール

| 週 | アクション |
|------|-----------|
| 1週目 | `mutmut` インストール・設定・ベースライン測定 |
| 2週目 | CI 統合・閾値 40% 設定・HTML レポート自動アップロード |
| 3-4週目 | 生存ミュータント上位 10 ファイルのテスト強化 |
| 5-8週目 | スコア 50% 達成 → CI 閾値 50% に引き上げ |
| 9-12週目 | スコア 60% 達成 → CI 閾値 60% に引き上げ (目標達成) |
| 継続 | 四半期ごとに閾値 5% 上昇、新規コードは 60% 必須 |

## 除外すべきコードパターン

```python
# これらはミューテーション対象外推奨
1. デバッグ用 print/log
2. 型ヒントのみのコード
3. @property で単純アクセスのみ
4. Enum 定義
5. 定数定義
6. 抽象メソッド (NotImplementedError)
7. 単純なデータクラス (フィールドのみ)
```

```toml
# pyproject.toml 除外設定例
[tool.mutmut]
exclude = [
    "tests/",
    "docs/",
    "config/",
    "*/conftest.py",
    "*/__init__.py",
    "*/migrations/*",
    "*_test.py",
    "*/mypy_cache/*",
    "*/.venv/*",
]
```