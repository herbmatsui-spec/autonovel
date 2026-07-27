# バックエンド起動高速化実装計画書

## 1. 目的
バックエンドサーバーの起動時間を短縮し、開発サイクルおよびデプロイ時間を最適化する。特に、Pythonの同期的なインポートオーバーヘッドを削減することに焦点を当てる。

## 2. 対象とする改善策
- **ルーターの遅延ロード (Lazy Loading)**
- **重いインポートのローカル化 (Local Import)**

## 3. 詳細設計

### 3.1 ルーターの遅延ロード
現状、`server.py` のトップレベルで全てのルーターモジュールをインポートしており、これにより `create_app()` が呼ばれる前に大量の依存関係がロードされている。

#### 変更内容
- `server.py` のトップレベルにある `from src.backend.routers import (...)` を削除する。
- `create_app()` 関数内で、ルーターを動的にインポートし、`application.include_router()` に渡す。

#### 実装イメージ
```python
def create_app() -> FastAPI:
    # ... (中略)
    
    # ルーターの定義を文字列リストで管理
    router_modules = [
        "src.backend.routers.health",
        "src.backend.routers.books",
        # ... 他のルーター
    ]
    
    for module_path in router_modules:
        module = importlib.import_module(module_path)
        application.include_router(module.router)
```

### 3.2 重いインポートのローカル化
`server.py` で定義されている API エンドポイント（`/api/refine_erotic`, `/api/easy_mode/generate`, `/api/critique/optimize`）は、特定のワークフロー実行関数（`execute_service_workflow`）に依存している。

#### 変更内容
- `from src.backend.tasks import execute_service_workflow` および `from src.backend.task_helpers import create_task as _create_task` をトップレベルから削除する。
- これらを、それらを使用する各エンドポイント関数（`refine_erotic`, `generate_easy`, `critique_optimize`）の内部でインポートするように変更する。

#### 実装イメージ
```python
@app.post("/api/refine_erotic")
async def refine_erotic(req: RefineEroticRequest):
    from src.backend.task_helpers import create_task as _create_task
    from src.backend.tasks import execute_service_workflow
    # ... 処理
```

## 4. 期待される効果
- **起動時間の短縮**: Pythonインタプリタが起動時に読み込むモジュール数が大幅に削減されるため、`uvicorn` 起動からサーバー待機状態までの時間が短縮される。
- **メモリ使用量の最適化**: 起動直後に全てのルーターとタスク処理モジュールをメモリに展開しなくて済む。

## 5. 影響範囲とリスク
- **ルーターの不整合**: 文字列によるインポートに変更するため、リファクタリング時にモジュール名が変更された場合、静的解析（IDEの追跡など）で検知しにくくなる。
- **初回リクエストの遅延**: 遅延ロードにより、各ルーターへの初回アクセス時にインポートコストが発生する（が、サーバー全体の起動速度優先のため許容範囲とする）。

## 6. 実装ステップ
1. `server.py` のトップレベルインポートを整理し、`importlib` を導入する。
2. `create_app` 内のルーター登録処理を動的インポートに変更する。
3. 特定エンドポイント内の重い関数をローカルインポートに変更する。
4. サーバーを起動し、正常に API エンドポイントが動作することを確認する。
