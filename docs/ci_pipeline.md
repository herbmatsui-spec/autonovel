# 覇権小説エンジン CI パイプライン概要

本プロジェクトでは、コードの品質と堅牢性を維持するために以下のCIパイプラインを定義します。

## 1. テスト自動化 (pytest)
GitHub Actions にて、毎プッシュごとに `tests/` 以下のユニットテストを実行します。
```yaml
- name: Run Tests
  run: pytest
```

## 2. リンター・静的解析 (ruff/mypy)
コードスタイルの統一と型チェックを強制します。
```yaml
- name: Linting
  run: ruff check .
- name: Type Check
  run: mypy .
```

## 3. 生成プロセス監査
生成ログ（JSONL）の妥当性をチェックする簡易的な検証スクリプトをCIに統合します。
```yaml
- name: Validate Traces
  run: python scripts/validate_traces.py
```
