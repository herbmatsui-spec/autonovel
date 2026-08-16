# AutoNovel 修正計画書（72ステップ版）

## 概要
本計画書は、低性能なLLMでも実装可能なように、修正作業を72個の小さなステップに分割したものである。
各ステップは独立して実行可能で、前後の依存関係を最小限に抑えている。

---

## フェーズ1: テスト基盤・環境正規化（ステップ1-18）

### ステップ1: 設定ファイルパスの修正
**対象ファイル**: `autonovel/config/validator.py`
**修正内容**: `load_settings_toml` メソッドのデフォルト引数を `config/settings.toml` から `autonovel/config/settings.toml` に変更
**理由**: テスト実行時に `FileNotFoundError: config/settings.toml` が発生する問題を解決

### ステップ2: models.yaml のパス修正
**対象ファイル**: `autonovel/config/validator.py`
**修正内容**: `load_models_yaml` のデフォルト引数を `config/models.yaml` から `autonovel/config/models.yaml` に変更

### ステップ3: system_plugins.yaml のパス修正
**対象ファイル**: `autonovel/config/validator.py`
**修正内容**: `load_system_plugins_yaml` のデフォルト引数を修正

### ステップ4: tropes.json のパス修正
**対象ファイル**: `autonovel/config/validator.py`
**修正内容**: `load_tropes_json` のデフォルト引数を修正

### ステップ5: interaction_matrix.yaml のパス修正
**対象ファイル**: `autonovel/config/validator.py`
**修正内容**: `load_interaction_matrix_yaml` のデフォルト引数を修正

### ステップ6: テスト用pytest設定ファイル作成
**対象ファイル**: `autonovel/pytest.ini` (新規作成)
**修正内容**: 
```ini
[pytest]
testpaths = tests
pythonpath = . autonovel autonovel/src
addopts = -v --tb=short
```

### ステップ7: conftest.py のパス設定確認
**対象ファイル**: `autonovel/tests/conftest.py`
**修正内容**: `sys.path.insert(0, str(AUTONOVEL_ROOT))` が正しく設定されているか確認

### ステップ8: streamlit_app.stores の存在確認
**対象ファイル**: `autonovel/streamlit_app/stores.py`
**修正内容**: ファイルが存在しない場合、空のファイルを作成してインポートエラーを解決

### ステップ9: テスト収集確認
**実行コマンド**: `python -m pytest autonovel/tests --collect-only`
**確認内容**: 28件のコレクションエラーが解消されたか確認

### ステップ10: ruff設定ファイルの確認
**対象ファイル**: `autonovel/pyproject.toml` または `autonovel/ruff.toml`
**修正内容**: ruff の設定が正しいか確認、なければ作成

### ステップ11: ruff E501（行長）ルールの除外設定
**対象ファイル**: `autonovel/pyproject.toml`
**修正内容**: `line-length` を設定し、長い行を許容

### ステップ12: ruff E722（bare except）警告の抑制設定
**対象ファイル**: `autonovel/pyproject.toml`
**修正内容**: `per-file-ignores` に `**: E722` を追加（後続ステップで修正するため一時的）

### ステップ13: ruff 実行確認（修正前）
**実行コマンド**: `python -m ruff check autonovel/src --output-format=text`
**確認内容**: 786件のエラーの内訳を記録

### ステップ14: mypy 設定ファイル確認
**対象ファイル**: `autonovel/mypy.ini` または `autonovel/pyproject.toml` 内
**修正内容**: mypy の設定を確認、なければ作成

### ステップ15: mypy ターゲットディレクトリ設定
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `autonovel/src` をターゲットディレクトリとして設定

### ステップ16: mypy strictモードの無効化（初期段階）
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `strict = false` を設定し、段階的に有効化

### ステップ17: mypy 実行確認
**実行コマンド**: `python -m mypy autonovel/src --no-error-summary`
**確認内容**: 型エラーの概数を記録

### ステップ18: テスト実行基盤の最終確認
**実行コマンド**: `python -m pytest autonovel/tests/test_minimal.py -v`
**確認内容**: 最もシンプルなテストがパスすることを確認

---

## フェーズ2: インターフェース・型定義の整合（ステップ19-45）

### ステップ19: IRepository インターフェースの確認
**対象ファイル**: `autonovel/src/backend/database/repo_protocols.py`
**修正内容**: `IRepository` インターフェースに以下のメソッドが定義されているか確認:
- `update_plot_blueprint`
- `create_book`
- `save_plot`

### ステップ20: IRepository.update_plot_blueprint 追加
**対象ファイル**: `autonovel/src/backend/database/repo_protocols.py`
**修正内容**: `IRepository` インターフェースに `update_plot_blueprint` メソッドを追加

### ステップ21: IRepository.create_book 追加
**対象ファイル**: `autonovel/src/backend/database/repo_protocols.py`
**修正内容**: `IRepository` インターフェースに `create_book` メソッドを追加

### ステップ22: IRepository.save_plot 追加
**対象ファイル**: `autonovel/src/backend/database/repo_protocols.py`
**修正内容**: `IRepository` インターフェースに `save_plot` メソッドを追加

### ステップ23: InMemoryRepository の実装確認
**対象ファイル**: `autonovel/src/backend/database/repo_inmemory.py`
**修正内容**: ステップ20-22で追加したメソッドの実装是否存在か確認

### ステップ24: InMemoryRepository.update_plot_blueprint 実装
**対象ファイル**: `autonovel/src/backend/database/repo_inmemory.py`
**修正内容**: 不足しているメソッドを実装

### ステップ25: InMemoryRepository.create_book 実装
**対象ファイル**: `autonovel/src/backend/database/repo_inmemory.py`
**修正内容**: 不足しているメソッドを実装

### ステップ26: InMemoryRepository.save_plot 実装
**対象ファイル**: `autonovel/src/backend/database/repo_inmemory.py`
**修正内容**: 不足しているメソッドを実装

### ステップ27: SQLRepository の実装確認
**対象ファイル**: `autonovel/src/backend/database/repo_misc.py`
**修正内容**: ステップ20-22で追加したメソッドの実装是否存在か確認

### ステップ28: SQLRepository.update_plot_blueprint 実装
**対象ファイル**: `autonovel/src/backend/database/repo_misc.py`
**修正内容**: 不足しているメソッドを実装

### ステップ29: SQLRepository.create_book 実装
**対象ファイル**: `autonovel/src/backend/database/repo_misc.py`
**修正内容**: 不足しているメソッドを実装

### ステップ30: SQLRepository.save_plot 実装
**対象ファイル**: `autonovel/src/backend/database/repo_misc.py`
**修正内容**: 不足しているメソッドを実装

### ステップ31: engine.py の Optional インポート修正
**対象ファイル**: `autonovel/src/backend/engine.py`
**修正内容**: `from typing import Optional` を追加

### ステップ32: async_utils.py の logger 変数修正
**対象ファイル**: `autonovel/src/core/async_utils.py`
**修正内容**: `logger = logging.getLogger(__name__)` を追加

### ステップ33: EntertainmentCheckResult のインポート確認
**対象ファイル**: `autonovel/src/models/entertainment_check.py`
**修正内容**: `EntertainmentCheckResult` が定義されているか確認

### ステップ34: EntertainmentCheckResult の型定義確認
**対象ファイル**: `autonovel/src/models/entertainment_check.py`
**修正内容**: クラスまたは TypedDict が正しく定義されているか確認

### ステップ35: plot_service.py のメソッド呼び出し確認
**対象ファイル**: `autonovel/src/services/plot_service.py`
**修正内容**: `IRepository` の未定義メソッドを呼び出していないか確認

### ステップ36: novel_service.py のメソッド呼び出し確認
**対象ファイル**: `autonovel/src/services/novel_service.py`
**修正内容**: `IRepository` の未定義メソッドを呼び出していないか確認

### ステップ37: default_plot_expander.py のメソッド呼び出し確認
**対象ファイル**: `autonovel/src/services/default_plot_expander.py`
**修正内容**: `IRepository` の未定義メソッドを呼び出していないか確認

### ステップ38: 型ヒントの欠落を修正（episode_context.py）
**対象ファイル**: `autonovel/src/services/episode_context.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ39: episode_context.py の EpisodeContextBuilder 型修正
**対象ファイル**: `autonovel/src/services/episode_context.py`
**修正内容**: `Dict[str, Any]` や `List[Dict[str, Any]]` 等の型ヒントを追加

### ステップ40: 型ヒントの欠落を修正（server.py）
**対象ファイル**: `autonovel/src/backend/server.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ41: 型ヒントの欠落を修正（engine_context.py）
**対象ファイル**: `autonovel/src/backend/engine_context.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ42: 型ヒントの欠落を修正（image_service.py）
**対象ファイル**: `autonovel/src/services/image_service.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ43: 型ヒントの欠落を修正（promotion_service.py）
**対象ファイル**: `autonovel/src/services/promotion_service.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ44: 型ヒントの欠落を修正（digest_service.py）
**対象ファイル**: `autonovel/src/services/digest_service.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

### ステップ45: 型ヒントの欠落を修正（gacha_service.py）
**対象ファイル**: `autonovel/src/services/gacha_service.py`
**修正内容**: mypy が警告する型ヒントの欠落を修正

---

## フェーズ3: 堅牢性改善・リファクタリング（ステップ46-72）

### ステップ46: bare except の特定（全体）
**実行コマンド**: `python -m ruff check autonovel/src --select=E722 --output-format=json`
**修正内容**: bare except が使用されている箇所をリスト化

### ステップ47: bare except 修正（core ディレクトリ）
**対象ファイル**: `autonovel/src/core/` 内のファイル
**修正内容**: `except Exception:` または `except BaseException:` に変更

### ステップ48: bare except 修正（backend ディレクトリ）
**対象ファイル**: `autonovel/src/backend/` 内のファイル
**修正内容**: `except Exception:` または `except BaseException:` に変更

### ステップ49: bare except 修正（services ディレクトリ）
**対象ファイル**: `autonovel/src/services/` 内のファイル
**修正内容**: `except Exception:` または `except BaseException:` に変更

### ステップ50: bare except 修正（agents ディレクトリ）
**対象ファイル**: `autonovel/src/agents/` 内のファイル
**修正内容**: `except Exception:` または `except BaseException:` に変更

### ステップ51: bare except 修正（models ディレクトリ）
**対象ファイル**: `autonovel/src/models/` 内のファイル
**修正内容**: `except Exception:` または `except BaseException:` に変更

### ステップ52: E722抑制の解除
**対象ファイル**: `autonovel/pyproject.toml`
**修正内容**: `per-file-ignores` から `**: E722` を削除

### ステップ53: ruff 最終確認
**実行コマンド**: `python -m ruff check autonovel/src`
**確認内容**: E722 エラーが解消されたか確認

### ステップ54: mypy の段階的 strict 化（その1）
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `disallow_untyped_defs = true` を追加

### ステップ55: mypy 実行と修正
**実行コマンド**: `python -m mypy autonovel/src --no-error-summary`
**修正内容**: 新たに発生した型エラーを修正

### ステップ56: mypy の段階的 strict 化（その2）
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `disallow_any_expr = true` を追加

### ステップ57: mypy 実行と修正
**実行コマンド**: `python -m mypy autonovel/src --no-error-summary`
**修正内容**: 新たに発生した型エラーを修正

### ステップ58: mypy の段階的 strict 化（その3）
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `warn_return_any = true` を追加

### ステップ59: mypy 実行と修正
**実行コマンド**: `python -m mypy autonovel/src --no-error-summary`
**修正内容**: 新たに発生した型エラーを修正

### ステップ60: mypy の段階的 strict 化（その4）
**対象ファイル**: `autonovel/mypy.ini`
**修正内容**: `strict_optional = true` を追加

### ステップ61: mypy 実行と修正
**実行コマンド**: `python -m mypy autonovel/src --no-error-summary`
**修正内容**: 新たに発生した型エラーを修正

### ステップ62: テストスイート実行（全体）
**実行コマンド**: `python -m pytest autonovel/tests -v --tb=short`
**確認内容**: テストの成功率を記録

### ステップ63: 失敗テストの分析（その1）
**対象ファイル**: 失敗したテストファイル
**修正内容**: 失敗原因を特定し、修正対象を決定

### ステップ64: 失敗テストの修正
**対象ファイル**: 失敗したテストファイル
**修正内容**: 特定した原因に基づいて修正

### ステップ65: 失敗テストの分析（その2）
**対象ファイル**: まだ失敗しているテスト
**修正内容**: 失敗原因を特定し、修正対象を決定

### ステップ66: 失敗テストの修正
**対象ファイル**: 失敗したテストファイル
**修正内容**: 特定した原因に基づいて修正

### ステップ67: 失敗テストの分析（その3）
**対象ファイル**: まだ失敗しているテスト
**修正内容**: 失敗原因を特定し、修正対象を決定

### ステップ68: 失敗テストの修正
**対象ファイル**: 失敗したテストファイル
**修正内容**: 特定した原因に基づいて修正

### ステップ69: 統合テスト実行
**実行コマンド**: `python -m pytest autonovel/tests -k 'e2e' -v`
**確認内容**: end-to-end テストの成功率を確認

### ステップ70: 最終 mypy 実行
**実行コマンド**: `python -m mypy autonovel/src --strict`
**確認内容**: 最終的な型エラーの有無を確認

### ステップ71: 最終 ruff 実行
**実行コマンド**: `python -m ruff check autonovel/src`
**確認内容**: 最終的な lint エラーの有無を確認

### ステップ72: 修正完了レポート作成
**対象ファイル**: `autonovel/REPORT_CORRECTION_COMPLETE.md` (新規作成)
**修正内容**: 
- 修正前後のエラー数の比較
- テスト成功率
- 残存する既知の問題点
- 推奨される今後の改善点

---

## 残存問題（修正対象外の事項）

以下の問題は、本修正計画の範疇外に屬するため、別途対応すること:

1. **streamlit_app.stores の実装**: テスト環境でのみ使用されるモックファイル
2. **設定ファイルの動的パス解決**: 実行環境に応じたパス解決の改良
3. **テストデータの整備**: テスト用データの整備と管理
4. **CI/CD パスの設定**: GitHub Actions 等でのパス設定

---

## 修正優先度

| 優先度 | ステップ範囲 | 理由 |
|--------|-------------|------|
| 高 | 1-18 | テスト基盤の確立 |
| 中 | 19-45 | インターフェース・型の整合 |
| 低 | 46-72 | 堅牢性改善・リファクタリング |

---

## 検証コマンド一覧

```bash
# テスト実行
python -m pytest autonovel/tests -v --tb=short

# ruff lint
python -m ruff check autonovel/src

# mypy 型チェック
python -m mypy autonovel/src

# テスト収集のみ
python -m pytest autonovel/tests --collect-only
```

---

*本計画書は AutoNovel プロジェクトの修正支援のために作成されました。*
*各ステップは独立して実行可能ですが、ステップ間の依存関係に注意してください。*