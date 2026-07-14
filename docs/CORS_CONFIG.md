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