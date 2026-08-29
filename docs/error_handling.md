# エラー処理ガイド

バックエンドコードの例外処理は以下の方針に従うこと。

## 基本原則

1. **広範な `except Exception` を避ける**
   捕捉する例外はできるだけ具体的にする（`ValueError`, `KeyError`, `RedisError` 等）。
2. **例外をログに残す**
   ログには `log_exception` を使い、トレース ID を自動付与する。
3. **必要に応じてドメイン例外へ変換**
   低レベルの例外（Redis/DB）は `src/backend/exceptions.py` のドメイン例外に変換して再送出する。

## 推奨パターン

```python
from src.backend.error_utils import log_exception
from src.backend.exceptions import CacheError

try:
    result = await redis.eval(script, keys, args)
except RedisError as e:
    log_exception(logger, "Redis Lua 実行失敗", e)
    raise CacheError("cache operation failed") from e
```

## 禁止事項

- `except Exception:` で例外を握りつぶす（再送出もログもしない）。
- 本番コードでの `print` によるデバッグ出力。
- `except Exception` を `pass` で終わらせる。

## 補足: キャッシュ層の例外変換例

```python
try:
    result = await redis.eval(script, keys, args)
except RedisError as e:
    log_exception(logger, "Redis Lua 実行失敗", e)
    raise CacheError("cache operation failed") from e
```

## 関連

- `src/backend/error_utils.py` : `log_exception`
- `src/backend/exceptions.py` : `BackendError`, `CacheError`, `CacheMiss`, `RateLimitExceeded`, `DatabaseError`
