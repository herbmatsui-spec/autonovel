# CORS 設定

## 目的
API サーバーは外部からのリクエストを制限するため、CORS（Cross-Origin Resource Sharing）設定が必要です。このドキュメントでは、サーバー側とフロントエンドでの設定手順を説明します。

## 1. サーバー側設定

```python
# config/cors_config.py
from starlette.middleware.cors import CORSMiddleware

def get_cors_origins() -> list[str]:
    """設定ファイルまたは環境変数から許可するオリジンを取得します。"""
    env_var = os.getenv("CORS_ORIGINS", "*")
    return [origin.strip() for origin in env_var.split(",")]
```

以下のように `FastAPI` アプリにミドルウェアを追加します。

```python
# server.py
from cors_config import get_cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 設定環境変数
- `CORS_ORIGINS`：許可オリジンをカンマ区切りで指定。
  - デフォルトは `*`（全域許可）です。

## 2. 環境変数の設定

```bash
export CORS_ORIGINS="http://localhost:3000,http://my-frontend.com"
```

## 3. テスト確認

- CORS が正しく設定されているか確認するには。`curl` で `Origin` ヘッダーを付与してリクエストします。

```bash
curl -H "Origin: http://localhost:3000" -I http://localhost:8000/api/ping
```

レスポンスに `Access-Control-Allow-Origin` が含まれていれば設定は成功です。

---

## 参考
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS](https://developer.mozilla.org/ja/docs/Web/HTTP/CORS)
---

## 4. API キー認証設定

### 目的
API エンドポイントへのアクセスを制御するため、API キー認証を実装しています。

### 1. サーバー側設定

認証は `src/backend/auth.py` の `APIKeyService` クラスで実装されています。

```python
# src/backend/auth.py
class APIKeyService:
    def __init__(self, allowed_keys: Optional[List[str]] = None, disabled: bool = False):
        self.allowed_keys = allowed_keys or []
        self.disabled = disabled

    def validate(self, api_key: str) -> bool:
        if self.disabled:
            logger.warning("AUTH_DISABLED is set - authentication is bypassed")
            return True
        if not self.allowed_keys:
            return False
        return api_key in self.allowed_keys
```

### 2. 環境変数設定

以下の環境変数で認証を設定します。

```bash
# API キー認証
export ALLOWED_API_KEYS="your-api-key-1,your-api-key-2"
export AUTH_DISABLED=false  # true にすると認証を無効化（開発用のみ推奨）

# 本番環境では必ず AUTH_DISABLED=false に設定してください
```

### 3. リクエスト方法

API リクエストには `X-API-Key` ヘッダーで API キーを指定します。

```bash
curl -H "X-API-Key: your-api-key-1" http://localhost:8000/api/health
```

### 4. エラーレスポンス

| ステータス | エラーコード | 説明 |
|------------|--------------|------|
| 401 | UNAUTHORIZED | API キーが指定されていません |
| 403 | FORBIDDEN | API キーが無効です |

エラーレスポンスは統一された JSON 形式で返されます：

```json
{
  "error_code": "FORBIDDEN",
  "error_message": "API キーが無効です。"
}
```

### 5. レート制限

各 API キーごとにレート制限が適用されます（デフォルト: 60秒間に100リクエスト）。制限を超えると 429 (Too Many Requests) が返されます。

```bash
# レート制限テスト
for i in {1..105}; do curl -H "X-API-Key: your-key" http://localhost:8000/api/health; done
```

---

## 5. セキュリティヘッダー

サーバーは以下のセキュリティヘッダーを自動的に付与します：

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

---

## 参考
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
