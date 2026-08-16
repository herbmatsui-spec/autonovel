# 設定管理ファイル棚卸し

作成日: 2026-08-16
対象: `/home/herbmatsui/autonovel/config/` 配下の設定関連ファイル

---

## 1. 設定関連ファイル一覧

### 1.1 定数定義ファイル
| ファイル | 行数 | 役割 | 参照箇所 |
|---------|------|------|---------|
| `config/constants.py` | 74 | プロジェクト全体の定数値（Final型） | `src/backend/server.py`, `src/easy_mode/pipeline.py`, `config/project_context.py` 等多数 |

### 1.2 Pydantic設定モデル
| ファイル | 行数 | 役割 | 参照箇所 |
|---------|------|------|---------|
| `schemas/config.py` | 467 | **SSOT**: `GlobalConfigModel`（全設定の単一真実源） | `config/project_context.py`, `config/settings.py`, `config/validator.py`, `config/container.py` |
| `config/settings.py` | 45 | `ConfigManager`（シングルトン）、`Settings`（BaseSettings） | `config/project_context.py` |

### 1.3 設定アクセサ・ユーティリティ
| ファイル | 行数 | 役割 | 参照箇所 |
|---------|------|------|---------|
| `config/project_context.py` | 161 | `ProjectContext`（シングルトン風アクセサ）、`GlobalConfig`（永続化付き）、`GlobalConfigModel`ファサード | `src/backend/engine_narrative.py`, `src/backend/engine_critique.py`, `src/backend/planning_service.py` 等多数 |
| `config/validator.py` | ~500 | `ConfigValidator.validate_all()`（全設定ファイルのバリデーション・マージ） | `schemas/config.py` の `GlobalConfigModel.load()` から呼出 |
| `config/container.py` | ~50 | DI用設定プロバイダ | `src/core/container/infra.py` |

### 1.4 環境変数・TOML連携
| ファイル | 役割 |
|---------|------|
| `config/settings.toml` | 設定値の永続化ストレージ（SSOT） |
| `.env.example` | 環境変数テンプレート |

### 1.5 その他設定ファイル（ドメイン固有）
| ファイル/ディレクトリ | 役割 |
|---------------------|------|
| `config/archetypes_new.py` | キャラクターアーキタイプ定義 |
| `config/domain_profile_manager.py` | ドメインプロファイル管理 |
| `config/domain_profiles/` | ドメイン別プロファイルJSON |
| `config/styles.py` | スタイル定義 |
| `config/narrative.py` | ナラティブ設定 |
| `config/erotic_*.py` | 官能関連設定 |
| `config/models.yaml` | モデルレジストリ |
| `config/system_plugins.yaml` | システムプラグイン設定 |
| `config/tropes.json` | トロープ設定 |
| `config/interaction_matrix.yaml` | インタラクションマトリクス |

---

## 2. 設定値の重複・分散状況

### 2.1 重複定義されている設定値

| 設定キー | 定義箇所 | 備考 |
|---------|---------|------|
| `DATABASE_URL` | `constants.py:36`, `schemas/config.py:44`, `config/settings.py:25` | 3箇所で定義 |
| `MODEL_WRITING` | `constants.py:51`, `schemas/config.py:29` | 2箇所 |
| `MODEL_PLANNING` | `constants.py:47`, `schemas/config.py:30` | 2箇所 |
| `MODEL_PLOT_EXPANSION` | `constants.py:48`, `schemas/config.py:31` | 2箇所 |
| `MODEL_CLIMAX` | `constants.py:45`, `schemas/config.py:32` | 2箇所 |
| `MAX_CONCURRENT_API_CALLS` | `constants.py:71`, `schemas/config.py:75` | 2箇所 |
| `MAX_LLM_RETRIES` | `constants.py:14`, `src/easy_mode/pipeline.py:69` | 2箇所 |
| `LLM_RETRY_DELAY_SEC` | `constants.py:15`, `src/easy_mode/pipeline.py:70` | 2箇所 |
| `DEFAULT_TARGET_EPISODES` | `constants.py:9`, `src/easy_mode/pipeline.py:58` | 2箇所 |
| `DEFAULT_MAX_REWRITE_ITERATIONS` | `constants.py:10`, `src/easy_mode/pipeline.py:59` | 2箇所 |
| `DEFAULT_TARGET_AUDIT_SCORE` | `constants.py:11`, `src/easy_mode/pipeline.py:60` | 2箇所 |

### 2.2 参照パターンの分析

| 参照パターン | 使用箇所 | 問題点 |
|-------------|---------|--------|
| `from config.constants import X` | 20+ ファイル | 定数が分散、環境変数非対応 |
| `ProjectContext.get_setting("X")` | 15+ ファイル | 動的アクセス、型安全性なし |
| `GlobalConfigModel.load()` | 5+ ファイル | 重い処理、キャッシュ依存 |
| `get_settings().X` | 3 ファイル | 限定的（BaseSettingsのみ） |

---

## 3. 設定値のライフサイクル

```
settings.toml (SSOT)
    ↓ ConfigValidator.validate_all() でバリデーション・マージ
GlobalConfigModel (Pydantic検証済み)
    ↓ 環境変数オーバーライド (ENV_OVERRIDE_MAP)
有効な設定インスタンス
    ↓ ConfigManager.get_config() でシングルトン化
ProjectContext.get_setting() / GlobalConfig.get() でアクセス
```

---

## 4. 問題点サマリ

1. **定数と設定モデルの二重管理**: `constants.py` と `GlobalConfigModel` で同値が定義
2. **環境変数対応の不統一**: `constants.py` は非対応、`GlobalConfigModel` はホワイトリスト制
3. **アクセス方法の乱立**: 4種類以上のアクセス方法が混在
4. **型安全性の欠如**: `ProjectContext.get_setting()` は `Any` 返却
5. **永続化の複雑性**: `GlobalConfig.update()` が TOML 直接書き込み

---

## 5. 統合設計の方針

**目標**: `pydantic-settings.BaseSettings` 単一クラスへの統合

### 5.1 統合後の構造
```
config/
├── settings.py          # 統一 Settings クラス (BaseSettings)
├── constants.py         # 純粋な定数のみ（設定値は削除）
├── cors_config.py       # CORS専用（現状維持）
├── logging_config.py    # ログ設定（現状維持）
└── validator.py         # 拡張設定ファイルのバリデーション専用
```

### 5.2 移行マッピング例
| 旧 | 新 |
|----|----|
| `constants.DATABASE_URL` | `settings.database_url` |
| `GlobalConfigModel.model_writing` | `settings.model_writing` |
| `ProjectContext.get_setting("X")` | `settings.X` (型付き) |
| `config.constants.MAX_CONCURRENT_API_CALLS` | `settings.max_concurrent_api_calls` |