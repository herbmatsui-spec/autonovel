# セキュリティ方針 (Security)

## 認証 (Authentication)

- API キーは ``ALLOWED_API_KEYS`` 環境変数（カンマ区切り）で設定する。
- リクエストヘッダ ``X-API-Key`` による認証を行う。
- ``AUTH_DISABLED=true`` は **非本番環境のみ** で許可される。
  - 本番環境（``ENVIRONMENT=production``）では無効化は拒否され、必ず認証が要求される。

## レート制限 (Rate Limiting)

- クライアント IP ごとに ``RATE_LIMIT_MAX_REQUESTS`` 件 / ``RATE_LIMIT_WINDOW_SECONDS`` 秒の制限を適用。
- 上限超過時は ``429 Too Many Requests`` を返す。
- メモリリーク防止のため、ストアエントリが ``RATE_LIMIT_STORE_MAX_ENTRIES`` を超えた場合は古いエントリから削除される。

## 入力検証 (Input Validation)

- 全リクエストボディは Pydantic スキーマで検証される。
- LLM の出力は ``OutputSanitizer`` によりサニタイズされ、スキーマ検証（``LLMValidationError``）を通る。
- 異常な入力は ``422 Unprocessable Entity`` で弾かれる。

## エラーレスポンス統一 (Unified Error Response)

- 全てのエラーは ``src/core/exceptions.py`` の ``HegemonyError`` 階層に基づき、
  ``{ "error_code": ..., "message": ... }`` 形式で返される。
- 詳細は [EXCEPTION_HIERARCHY.md](./EXCEPTION_HIERARCHY.md) を参照。

## セキュリティヘッダー

- 全レスポンスに ``X-Content-Type-Options: nosniff``、``X-Frame-Options: DENY``、
  ``X-XSS-Protection: 1; mode=block``、``Strict-Transport-Security`` を付与。

## 脆弱性報告

不具合や脆弱性を発見した場合は、公開リポジトリの Issue ではなく、
管理者へ直接連絡すること。
