# AutoNovel 実装計画書: 重大バグ修正

## 概要

本書は AutoNovel プロジェクトにおける 2 つの重大リスク（P1）の修正実装計画を定義する。

---

## Issue 1: Alembic マイグレーションの二重配置

### 1.1 問題の詳細

**現状:**
- ルート `alembic/versions/` に 7 個のマイグレーションが存在
  - `00000000_initial_migration.py`
  - `0001_erotic_intensity.py`
  - `0002_add_catchcopy.py`
  - `0003_pgvector_chapter_chunks.py`
  - `0003_add_ai_assistant_config.py` （同名リビジョンID: 0003 の重複）
  - `0011_multimedia_artifacts.py`
- `src/backend/alembic/versions/` に 2 個のマイグレーションが存在
  - `0012_age_graph_init.py`
  - `0013_graph_pipeline_idempotency.py`
- `alembic.ini` の `script_location = src/backend/alembic` 設定により、ルート側のマイグレーション（0000-0011）が適用されない

**影響:**
- 本番環境でスキーマが部分的に古いままになる
- `0003` リビジョンID重複によりマイグレーション履歴が破損するリスク
- `graph_pipeline_idempotency` テーブル等の本番適用漏れ

### 1.2 修正方針

**戦略: ルート `alembic/` を削除し、`src/backend/alembic/` に全マイグレーションを統合**

理由:
- `alembic.ini` が `src/backend/alembic` を指している
- アプリケーションコード（`src/backend/` 配下）からの参照パスと一致
- Docker/CI での実行パスと整合

### 1.3 実装手順

#### Phase 1: 現状調査・バックアップ（Day 1）

```bash
# 1. 現在のマイグレーション履歴を確認
alembic -c alembic.ini history

# 2. 適用済みリビジョンを確認（本番DB接続時）
alembic -c alembic.ini current

# 3. ルート側マイグレーションファイルをバックアップ
cp -r alembic/versions alembic/versions.backup.$(date +%Y%m%d)
```

#### Phase 2: マイグレーション統合（Day 1-2）

**Step 2.1: 重複リビジョン ID の解決**

| ファイル | 現リビジョンID | 新リビジョンID | down_revision |
|---------|--------------|--------------|--------------|
| `0003_pgvector_chapter_chunks.py` | `0003_pgvector_chapter_chunks` | `0003_pgvector_chapter_chunks` | `0002_add_catchcopy` |
| `0003_add_ai_assistant_config.py` | `0003_add_ai_assistant_config` | **`0004_add_ai_assistant_config`** | **`0003_pgvector_chapter_chunks`** |

**Step 2.2: マイグレーションファイル移動・リネーム**

```bash
# 移動先: src/backend/alembic/versions/
# 連番を整理してリネーム
mv alembic/versions/00000000_initial_migration.py \
   src/backend/alembic/versions/0000_initial_migration.py

mv alembic/versions/0001_erotic_intensity.py \
   src/backend/alembic/versions/0001_erotic_intensity.py

mv alembic/versions/0002_add_catchcopy.py \
   src/backend/alembic/versions/0002_add_catchcopy.py

mv alembic/versions/0003_pgvector_chapter_chunks.py \
   src/backend/alembic/versions/0003_pgvector_chapter_chunks.py

# 0003 重複分を 0004 に変更
# down_revision を 0003_pgvector_chapter_chunks に修正
mv alembic/versions/0003_add_ai_assistant_config.py \
   src/backend/alembic/versions/0004_add_ai_assistant_config.py

mv alembic/versions/0011_multimedia_artifacts.py \
   src/backend/alembic/versions/0011_multimedia_artifacts.py
```

**Step 2.3: 既存ファイルのリビジョンチェーン修正**

`src/backend/alembic/versions/0012_age_graph_init.py`:
```python
# 修正前
down_revision = "0011_multimedia_artifacts"

# 修正後（ルート側の 0011 と同一のため変更不要だが、明示的に確認）
down_revision = "0011_multimedia_artifacts"
```

`src/backend/alembic/versions/0013_graph_pipeline_idempotency.py`:
```python
# 修正前
down_revision = "0012_age_graph_init"
# 変更不要
```

#### Phase 3: 検証・テスト（Day 2-3）

**Step 3.1: 空DBでのフルマイグレーションテスト**

```bash
# SQLite でテスト
alembic -c src/backend/alembic.ini upgrade head

# PostgreSQL でテスト（Docker 利用）
docker run -d --name test-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=autonovel postgres:16
alembic -c src/backend/alembic.ini -x db_url=postgresql://postgres:test@localhost:5432/autonovel upgrade head
```

**Step 3.2: 既存DBへの適用テスト（ステージング環境）**

```bash
# 現在のヘッドを確認
alembic -c src/backend/alembic.ini current

# マイグレーション履歴の整合性確認
alembic -c src/backend/alembic.ini history --verbose

# 差分確認
alembic -c src/backend/alembic.ini check
```

**Step 3.3: ダウングレードテスト**

```bash
# 1つ戻す
alembic -c src/backend/alembic.ini downgrade -1

# ベースまで戻す
alembic -c src/backend/alembic.ini downgrade base

# 再適用
alembic -c src/backend/alembic.ini upgrade head
```

#### Phase 4: クリーンアップ・ドキュメント更新（Day 3）

```bash
# ルート側 alembic/ を削除（バックアップ後に）
rm -rf alembic/versions.backup.*
rm -rf alembic/

# README §3.6 / §17.2 のパス記載を修正
# 修正前: "マイグレーションモジュールはルート alembic/versions/ に配置"
# 修正後: "マイグレーションモジュールは src/backend/alembic/versions/ に配置"
```

### 1.4 受け入れ基準

- [ ] `alembic -c src/backend/alembic.ini history` で 0000-0013 が連続して表示される
- [ ] `alembic -c src/backend/alembic.ini upgrade head` がエラーなく完了する
- [ ] PostgreSQL と SQLite 両方でマイグレーションが適用できる
- [ ] `0003` リビジョンID重複が解消されている
- [ ] ルート `alembic/` ディレクトリが削除されている
- [ ] README のパス記載が修正されている

---

## Issue 2: LLM プロバイダ claude / ollama の欠落

### 2.1 問題の詳細

**現状:**
- README §3.2 / §12.1 で **5プロバイダ対応**を謳っている
  - OpenAI, Gemini, **Claude, Ollama, vLLM**
- 実装されているアダプタ: **3種類のみ**
  - `GeminiAdapter` (`src/services/llm/gemini_adapter.py`)
  - `OpenAIAdapter` (`src/services/llm/openai_adapter.py`) - OpenAI互換API用
  - `MockLLMAdapter` (`src/services/llm/mock_adapter.py`)
- `factory.py` で `claude`/`ollama` 指定時、警告なしで `MockLLMAdapter` にフォールバック
- 本番環境で空小説が生成される事故リスク

**コード上の問題箇所:**

`src/services/llm/factory.py:22-39`:
```python
p = (provider or settings.LLM_PROVIDER).lower()

if p == "gemini":
    # ...
if p == "openai":
    # ...

return MockLLMAdapter()  # claude, ollama, vLLM 等は全てここに来る
```

`src/backend/config.py:63`:
```python
LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "openai"  # claude/ollama 不在
```

### 2.2 修正方針

**戦略A: 実装コスト最小（README修正＋警告ログ追加） - 推奨**

1. **README から claude/ollama/vLLM 記載を削除**（実装されていない機能を謳わない）
2. **factory.py に警告ログ追加**（未対応プロバイダ指定時に明示的に警告）
3. **設定の Literal 型を実装済みのみに制限**

**戦略B: アダプタ実装（中〜大コスト）**

- `ClaudeAdapter` 実装（Anthropic SDK または OpenRouter 経由）
- `OllamaAdapter` 実装（OpenAI互換エンドポイントとして OpenAIAdapter 流用可）
- `vLLMAdapter` 実装（同上）

**推奨: 戦略A で即時対応、戦略B は別チケットで計画的実装**

理由:
- 即座に本番事故を防げる
- 実装コストが最小（数時間）
- claude/ollama 実装は要件確認・テストを含め数日〜数週間必要

### 2.3 実装手順（戦略A: 即時対応）

#### Phase 1: factory.py 修正（Day 1）

```python
# src/services/llm/factory.py
def get_llm_adapter(...) -> BaseLLMAdapter:
    p = (provider or settings.LLM_PROVIDER).lower()

    # 実装済みプロバイダ
    IMPLEMENTED_PROVIDERS = {"gemini", "openai", "mock"}

    if p not in IMPLEMENTED_PROVIDERS:
        logger.error(
            f"LLMプロバイダ '{p}' は未実装です。利用可能: {IMPLEMENTED_PROVIDERS}。"
            f"MockLLMAdapter にフォールバックします。本番環境では空の応答になります。"
        )
        return MockLLMAdapter()

    if p == "gemini":
        # 既存コード
    if p == "openai":
        # 既存コード
    if p == "mock":
        return MockLLMAdapter()
```

#### Phase 2: 設定バリデーション強化（Day 1）

`src/backend/config.py`:
```python
# 修正前
LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "openai"

# 修正後：実装済みのみ許可、環境変数で上書き可能
LLM_PROVIDER: Literal["openai", "gemini", "mock"] = "mock"  # デフォルトを安全側に
```

#### Phase 3: README 修正（Day 1）

**README.md §3.2 採用技術スタック一覧:**
```markdown
| **LLM Gateway** | Provider Factory | 自作 | **OpenAI, Gemini, Mock** (Claude/Ollama/vLLM は未実装・将来対応) |
```

**README.md §12.1 サポートプロバイダと切り替え設定:**
```markdown
## 12.1 サポートプロバイダと切り替え設定

現在実装済みのプロバイダ:
- **openai**: OpenAI API および互換エンドポイント (OpenRouter, vLLM, LocalAI 等)
- **gemini**: Google Gemini API
- **mock**: テスト・開発用モックアダプタ

未実装（将来対応予定）:
- **claude**: Anthropic Claude API (OpenRouter 経由で openai として利用可能)
- **ollama**: ローカル LLM (OpenAI 互換モードで openai として利用可能)
- **vLLM**: 高スループット推論サーバ (OpenAI 互換モードで openai として利用可能)
```

#### Phase 4: 代替利用方法のドキュメント化（Day 1）

README §12.2 に追記:
```markdown
### OpenRouter / Ollama / vLLM を利用する場合

これらは OpenAI 互換 API として提供されるため、`LLM_PROVIDER=openai` として設定し、
`OPENAI_BASE_URL` と `OPENAI_API_KEY` でエンドポイントを指定してください。

```bash
# OpenRouter (Claude 等) 例
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-xxx
OPENAI_MODEL=anthropic/claude-3.5-sonnet

# Ollama 例
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.1

# vLLM 例
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_API_KEY=dummy
OPENAI_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```
```

### 2.4 受け入れ基準（戦略A）

- [ ] `LLM_PROVIDER=claude` 指定時に ERROR レベルログが出力される
- [ ] `LLM_PROVIDER=ollama` 指定時に ERROR レベルログが出力される
- [ ] `LLM_PROVIDER=mock` 指定時は警告なしで MockLLMAdapter が返される
- [ ] README から「5プロバイダ対応」等の誤認を招く記述が削除されている
- [ ] OpenRouter/Ollama/vLLM 利用時の設定例が README に記載されている
- [ ] 既存テスト（`test_llm_factory.py` 等）が全てパスする

---

## 統合スケジュール

| Day | Issue 1 (Alembic) | Issue 2 (LLM Provider) |
|-----|-------------------|------------------------|
| 1   | 調査・バックアップ・統合作業 | factory.py 修正・設定修正・README修正 |
| 2   | 検証テスト（SQLite/PostgreSQL） | 単体テスト・統合テスト実行 |
| 3   | ダウングレードテスト・クリーンアップ | ドキュメント最終確認・マージ |

**総工数目安: 3 日（1 人日相当）**

---

## リスクと対策

### Issue 1 リスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| 本番DBのマイグレーション履歴不整合 | 高 | ステージングで事前検証、バックアップ必須 |
| 0003 重複解消時の down_revision 間違い | 中 | 単体テストでチェーン整合性確認 |
| 既存環境での `alembic upgrade head` 失敗 | 高 | 事前に `alembic check` で差分確認 |

### Issue 2 リスク

| リスク | 影響度 | 対策 |
|--------|--------|------|
| 既存ユーザーが `claude` 指定で動いていたケース | 低 | 設定例を提示し移行案内 |
| OpenRouter 利用者が `openai` 挈定に気づかない | 中 | README に明記、起動時ログでヒント表示 |

---

## 今後の拡張（Issue 2 戦略B 実装時）

### ClaudeAdapter 実装要件

- `anthropic` SDK または OpenRouter 経由（OpenAI互換）
- `generate_text`, `stream_text`, `generate_json` 実装
- System prompt 対応（Anthropic は `system` パラメータ別途）
- Token usage 取得対応

### OllamaAdapter 実装要件

- OpenAI 互換エンドポイントとして `OpenAIAdapter` を継承・設定のみで対応可能
- `/api/generate` 非互換エンドポイント対応が必要な場合のみ専用実装

### 共通化リファクタリング案

```python
# src/services/llm/base.py に共通基底クラス追加
class OpenAICompatibleAdapter(BaseLLMAdapter):
    """OpenAI 互換 API 用基底クラス"""
    def __init__(self, api_key: str, base_url: str, model: str, **kwargs):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
```

---

## チェックリスト

### Issue 1 完了確認

- [ ] `src/backend/alembic/versions/` に 0000-0013 の 14 ファイルが存在
- [ ] リビジョンチェーンが `0000 -> 0001 -> 0002 -> 0003 -> 0004 -> 0011 -> 0012 -> 0013` で連続
- [ ] `alembic.ini` が `script_location = src/backend/alembic` のまま動作
- [ ] ルート `alembic/` ディレクトリ削除済み
- [ ] README パス修正済み

### Issue 2 完了確認

- [ ] `factory.py` に未実装プロバイダ検知・警告ロジック追加
- [ ] `config.py` の `LLM_PROVIDER` Literal 型が実装済みのみ
- [ ] README §3.2, §12.1, §12.2 修正済み
- [ ] 既存テスト全パス
- [ ] 手動テスト: `LLM_PROVIDER=claude python -m src.services.llm.factory` で警告確認