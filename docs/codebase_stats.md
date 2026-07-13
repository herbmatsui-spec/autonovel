# コードベース統計（ベースライン）

## 概要

本プロジェクト `R15/cR15` のPythonコードベースの規模を測定した結果を記録します。

## 測定結果

| 指標 | 値 |
|------|-----|
| 総ファイル数 | 643 |
| 総行数 | 79,265 |

## 測定条件

- **測定日**: 2026-07-07
- **対象ディレクトリ**: `I:\R15\cR15`
- **除外パターン**:
  - `__pycache__`
  - `.venv`
  - `.test_venv`
  - `.pytest_cache`
  - `.mypy_cache`

## 測定コマンド

```python
import os
files = [f for f in os.popen('dir /s /b *.py').read().split('\n') if f and '__pycache__' not in f and '.venv' not in f and '.pytest_cache' not in f and '.mypy_cache' not in f]
print(f'Total files: {len(files)}')
total = sum(len(open(f, encoding='utf-8', errors='ignore').readlines()) for f in files if os.path.exists(f))
print(f'Total lines: {total}')
```

## 備考

- 79,265行という規模は中〜大規模プロジェクトに相当します
- リファクタリング・テスト強化により、コード品質と保守性を向上させることが重要です
- 72ステップの詳細実装計画に基づき、段階的に改善を実施します