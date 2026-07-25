# AutoNovel 残作業実装計画書（フェーズ3後続 + ステップ73-75）

## 概要

本計画書は、[`PLANCORRECTION_72STEPS.md`](autonovel/PLANCORRECTION_72STEPS.md:1) のフェーズ3（ステップ46-72）がすべて未完了の状態を踏まえ、**bare except修正・E722抑制解除・mypy設定矛盾解消・完了レポート** を対象とする実装計画書です。元の72ステッププランから75ステップに拡張し、既存の完了状況を考慮した新しい計画として機能します。

---

## 背景: 現在の状態

### 完了済み
- **フェーズ1（ステップ1-18）**: すべて完了
- **フェーズ2（ステップ19-45）**: すべて完了

### 未完了（フェーズ3: ステップ46-72）
以下の問題が残っています:

1. **bare except が8箇所残存**（ステップ47-51 未完了）
2. **pyproject.toml に E722 抑制 `"**" = ["E722"]` が残存**（ステップ52 未完了）
3. **mypy.ini と pyproject.toml の strict 設定が矛盾**（ステップ54-61 未完了）
4. **完了レポートが存在しない**（ステップ72 未完了）

---

## フェーズ3拡張: 残存bare except修正（ステップ46-51 後続）

### ステップ46（再定義）: bare except の正確な位置確認
**対象ファイル一覧**:

| # | ファイル | 行 | 現在のコード | 修正後 |
|---|----------|-----|-------------|--------|
| 1 | [`src/models/character.py`](autonovel/src/models/character.py:192) | 192 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 2 | [`src/backend/database/repo_bible.py`](autonovel/src/backend/database/repo_bible.py:67) | 67 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 3 | [`src/backend/database/repositories/bible.py`](autonovel/src/backend/database/repositories/bible.py:62) | 62 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 4 | [`src/agents/plot.py`](autonovel/src/agents/plot.py:323) | 323 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 5 | [`src/agents/marketing.py`](autonovel/src/agents/marketing.py:65) | 65 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 6 | [`src/services/writing_services.py`](autonovel/src/services/writing_services.py:389) | 389 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 7 | [`src/services/writing_services.py`](autonovel/src/services/writing_services.py:464) | 464 | `except:` | `except (json.JSONDecodeError, ValueError):` |
| 8 | [`src/backend/engine_style_rag.py`](autonovel/src/backend/engine_style_rag.py:107) | 107 | `except:` | `except Exception:` |

**理由**: いずれのパターンもJSONパース失敗時のフォールバックであり、具体性のある例外型（`json.JSONDecodeError`, `ValueError`）または `Exception` を指定することで、E722 bare-except違反を解消しつつデバッグ可能性を向上させます。

**確認コマンド**:
```bash
python -m ruff check autonovel/src --select=E722
```
期待結果: 出力なし（エラー0件）

---

### ステップ47: src/models/character.py の修正
**対象ファイル**: [`src/models/character.py`](autonovel/src/models/character.py:192)
**修正内容**: 192行目の `except:` を `except (json.JSONDecodeError, ValueError):` に変更

```python
<<<<<<< SEARCH
:start_line:190
-------
                data = json.loads(data)
            except:
                data = {}
=======
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                data = {}
>>>>>>> REPLACE
```

---

### ステップ48: src/backend/database/repo_bible.py の修正
**対象ファイル**: [`src/backend/database/repo_bible.py`](autonovel/src/backend/database/repo_bible.py:67)
**修正内容**: 67行目の `except:` を修正

---

### ステップ49: src/backend/database/repositories/bible.py の修正
**対象ファイル**: [`src/backend/database/repositories/bible.py`](autonovel/src/backend/database/repositories/bible.py:62)
**修正内容**: 62行目の `except:` を修正

---

### ステップ50: src/agents/plot.py の修正
**対象ファイル**: [`src/agents/plot.py`](autonovel/src/agents/plot.py:323)
**修正内容**: 323行目の `except:` を修正

---

### ステップ51: src/agents/marketing.py の修正
**対象ファイル**: [`src/agents/marketing.py`](autonovel/src/agents/marketing.py:65)
**修正内容**: 65行目の `except:` を修正

---

### ステップ52: src/services/writing_services.py の修正
**対象ファイル**: [`src/services/writing_services.py`](autonovel/src/services/writing_services.py:389)
**修正内容**: 389行目と464行目の `except:` を修正（2箇所）

---

### ステップ53: src/backend/engine_style_rag.py の修正
**対象ファイル**: [`src/backend/engine_style_rag.py`](autonovel/src/backend/engine_style_rag.py:107)
**修正内容**: 107行目の `except:` を `except Exception:` に変更

---

## ステップ54: E722抑制の解除

**対象ファイル**: [`autonovel/pyproject.toml`](autonovel/pyproject.toml:28)
**修正内容**: 28行目の `"**" = ["E722"]` を削除

```toml
<<<<<<< SEARCH
:start_line:27
-------
[tool.ruff.lint.per-file-ignores]
"**" = ["E722"]
=======
[tool.ruff.lint.per-file-ignores]
>>>>>>> REPLACE
```

**確認**: ステップ53完了後、ruff E722 エラーが0件であれば解除成功

---

## ステップ55: ruff 最終確認

**実行コマンド**: `python -m ruff check autonovel/src`
**期待結果**: E722 エラー0件

---

## ステップ56-63: mypy設定矛盾の解消

### 現状の問題
- [`mypy.ini`](autonovel/mypy.ini:1): `disallow_untyped_defs = False`, `warn_return_any = False`（緩い）
- [`pyproject.toml`](autonovel/pyproject.toml:3): `strict = true`（厳格）

**問題点**: `pyproject.toml` の `[tool.mypy]` が優先される環境では `mypy.ini` が無視され、`strict=true` が即座に全エラーを発動させる可能性があります。

### ステップ56: mypy設定の統合判断
**判断基準**:
- `pyproject.toml` の `strict = true` を維持し、`mypy.ini` を削除 or `ignore_missing_imports = True` のみに简化
- ただし CI/CD や既存ワークフローが `mypy.ini` に依存している場合は統合を避ける

**作業**:
1. `mypy.ini` を `[mypy]` セクションとして `pyproject.toml` に統合することを検討
2. または `mypy.ini` をそのまま残し、`pyproject.toml` の `[tool.mypy]` を削除して一貫性を確保

**推奨**: `pyproject.toml` 側の設定を一貫して使用し、`mypy.ini` をlegacyとして温存（新規追加ファイルは `pyproject.toml` 設定適用）

### ステップ57-63: mypy段階的strict化（元のステップ54-61 再継承）
**方針**: ステップ53（bare except修正）完了後、以下の順番で段階的にstrict機能を有効化:

| ステップ | 追加設定 | pyproject.toml での設定 |
|---------|----------|------------------------|
| 57 | `disallow_untyped_defs = true` | 既に `true` であること確認 |
| 58 | `strict_optional = true` | `strict_optional = true` |
| 59 | `warn_return_any = true` | 既に `true` であること確認 |
| 60 | `disallow_any_expr = true` | 追加設定 |
| 61 | 追加 strict 設定（必要に応じて） | 追加設定 |
| 62 | 型エラー修正フェーズ | 検出したエラー逐次修正 |

**注意**: 既存の型エラーが大量にある場合、一度に strict=true を有効化すると発破が多すぎて修正が困難になります。段階的有効化によりエラーメッセージを制御します。

---

## ステップ64-71: テストスイート・統合テスト

### ステップ64: テストスイート実行
**実行コマンド**: `python -m pytest autonovel/tests -v --tb=short`
**確認内容**: テスト成功率、失败テスト一覧

### ステップ65-68: 失敗テストの分析・修正（3サイクル）
**対応方針**: 失敗テストの原因を特定し修正。典型的な原因:
- モック不足（Streamlit依存）
- パス解決エラー
- 型エラーによる実行時例外
- 設定ファイルの不整合

### ステップ69: 統合テスト（e2e）の実行
**実行コマンド**: `python -m pytest autonovel/tests -k 'e2e' -v`
**確認内容**: end-to-endテスト成功率

---

## ステップ72: 最終 mypy 実行

**実行コマンド**: `python -m mypy autonovel/src --strict`
**期待結果**: エラー0件 または 許容可能な既知エラー一覧

---

## ステップ73: 最終 ruff 実行

**実行コマンド**: `python -m ruff check autonovel/src`
**期待結果**: 全エラー0件

---

## ステップ74: 設定ファイル最終確認

### mypy.ini vs pyproject.toml 統一確認
- `pyproject.toml` の `[tool.mypy]` を最終設定として使用
- `mypy.ini` は legacy として保持（削除しない、コメントで非推奨明記）

### pytest.ini 確認
- `pythonpath` に `autonovel/src` が含まれていることを確認

### pyproject.toml ruff 確認
- E722抑制が解除されていることを確認
- line-length, target-version が適切に設定されていることを確認

---

## ステップ75: 完了レポート作成（REPORT_CORRECTION_COMPLETE.md）

**対象ファイル**: [`autonovel/REPORT_CORRECTION_COMPLETE.md`](autonovel/REPORT_CORRECTION_COMPLETE.md:1)（新規作成）
**内容**:

```markdown
# AutoNovel 修正完了レポート

## 概要
本プロジェクトは、72ステップ修正計画 + 75ステップ拡張計画的执行により、
以下の問題をすべて解決しました。

## 修正前後の状態

### ruff (E722 bare-except)
- 修正前: 8件の bare except
- 修正後: 0件

### mypy
- 修正前: 未検証（設定矛盾あり）
- 修正後: --strict モードでエラー0件（または既知エラー一覧）

### テストスイート
- 修正前: コレクションエラー28件
- 修正後: 全テストが正常にコレクション・実行可能

## 実装された修正の内訳

### フェーズ1（テスト基盤・環境正規化）
- 設定ファイルパスの正規化（validator.py）
- pytest設定ファイル作成
- conftest.py のパス設定確認
- streamlit_app/stores.py の空ファイル作成

### フェーズ2（インターフェース・型定義の整合）
- IRepository インターフェースへの3メソッド追加
- InMemoryRepository, SQLRepository への実装追加
- 型ヒントの欠落修正

### フェーズ3拡張（堅牢性改善）
- bare except 8箇所の修正（character.py, repo_bible.py, repositories/bible.py, plot.py, marketing.py, writing_services.py, engine_style_rag.py）
- E722抑制の解除
- mypy 設定矛盾の解消（pyproject.toml / mypy.ini 統合）
- mypy 段階的 strict 化

## 残存する既知の問題

1. （問題と应对策を記載）

## 推奨される今後の改善点

1. 型ヒントの完全遵守（disallow_any_expr 等）
2. テストカバレッジの向上
3. CI/CD パイプラインでの自動検証
```

---

## 検証コマンド一覧

```bash
# ruff bare-except チェック
python -m ruff check autonovel/src --select=E722

# ruff 全チェック
python -m ruff check autonovel/src

# mypy strict チェック
python -m mypy autonovel/src --strict

# pytest 実行
python -m pytest autonovel/tests -v --tb=short

# テスト収集のみ
python -m pytest autonovel/tests --collect-only
```

---

## 優先度表

| 優先度 | ステップ範囲 | 理由 |
|--------|-------------|------|
| 高 | 46-53 | bare except修正はコードの安全性に直結 |
| 中 | 54-55 | E722抑制解除とruff最終確認 |
| 中 | 56-63 | mypy設定矛盾の解消と段階的strict化 |
| 低 | 64-74 | テスト・統合テスト・最終確認 |
| 低 | 75 | 完了レポート作成 |

---

*本計画書は PLANCORRECTION_72STEPS.md のフェーズ3未完了部分を対象として作成されました。*
*各ステップは独立して実行可能ですが、ステップ間の依存関係（特にmypy設定変更前後）に注意してくだし。*