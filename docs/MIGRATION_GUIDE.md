# マイグレーションガイド (Migration Guide)

本ガイドは v3.3 → v3.4 の変更点と移行手順をまとめる。

## 1. 認証設定の必須化

- 本番環境では ``AUTH_DISABLED=true`` を **設定してはならない**。
  v3.4 では ``ENVIRONMENT=production`` 下で ``AUTH_DISABLED=true`` の場合、認証バイパスが
  **拒否** され、全リクエストに API キーが要求される。
- ``.env.example`` を参考に ``.env`` を作成し、``ALLOWED_API_KEYS`` を必ず設定する。

```bash
cp .env.example .env
# ALLOWED_API_KEYS=prod-key-1,prod-key-2
# AUTH_DISABLED=false
```

## 2. LLM クライアントのインポートパス変更

- ``GeminiApiClient`` / ``OpenAIApiClient`` は ``src/core/llm_gateway.py`` から
  ``src/core/llm_clients/gemini.py`` / ``src/core/llm_clients/openai.py`` に分離された。
- 互換のため ``src.core.llm_clients`` からのインポートを推奨。

```python
# 旧
from src.core.llm_gateway import GeminiApiClient
# 新
from src.core.llm_clients.gemini import GeminiApiClient
```

- 両クライアントは ``src.core.llm_clients.BaseLLMClient`` を継承する抽象インターフェースを実装。

## 3. タイムアウト / レート制限定数の集約

- タイムアウト値・レート制限値は ``config/constants.py`` に集約された。
- ハードコードされた数値を変更する場合は ``config/constants.py`` を編集する。

## 4. 非同期 API への移行

- ``services/async_wrapper.run_async`` は非推奨（``DeprecationWarning``）。
  同期コンテキストから非同期を呼ぶ場合は ``asyncio.run()`` または
  ``src.backend.engine_utils.safe_run_async`` を使用する。
- ブロッキング I/O は ``asyncio.to_thread`` から ``src.core.executor_manager.run_io()`` へ統一された。

## 5. LLMGenerateResultProxy.generate() の廃止

- ``LLMGenerateResultProxy.generate()`` は ``NotImplementedError`` を送出する。
  代わりに ``generate_text()`` / ``generate_json()`` を使用する。
