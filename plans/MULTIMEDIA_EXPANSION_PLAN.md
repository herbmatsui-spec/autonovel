# マルチメディア展開 実装計画書

対象: Asset Pack / Media Mix / IF Routes / eBook Export
関連: `src/easy_mode/phase3/{asset_pack,media_mix,if_routes,ebook_export}.py`
目標: 孤児コード 3700 行を FastAPI ルータ + React フロントから呼び出し可能にし、機能フラグ `ENABLE_MULTIMEDIA` で段階ロールアウトする。
想定工数: 4〜6 週 (低性能 LLM でも実装可能な粒度)

---

## 全体方針

- 各ステップは「1 コミット = 1 テスト緑 = 1 ロールバック単位」で完結させる。
- 既存のレイヤ命名規約 (`src/backend/routers/*.py`、`frontend/src/components/*`、`frontend/src/api/*`) に厳密準拠する。
- 既存コードを変更せず「新ファイル追加 + 薄いアダプタ」で統合する。`phase3` モジュールは破壊的変更禁止。
- 1〜9: 基盤・観測性 / 10〜24: バックエンド実装 / 25〜48: バックエンド検証・統合 / 49〜60: フロント実装 / 61〜72: ロールアウト・運用

---

## Phase A: 基盤・機能フラグ整備 (Step 1〜9)

### Step 1. 機能フラグ定数を `config.py` に追加
- ファイル: `src/backend/config.py`
- 内容: `Settings` クラスに `ENABLE_MULTIMEDIA: bool = False`, `MULTIMEDIA_OUTPUT_DIR: str = Field(default_factory=lambda: str(STORAGE_DIR / "multimedia"))`, `ENABLE_AUDIO_SYNTH: bool = False` を追加。
- 検証: `python -c "from src.backend.config import settings; print(settings.ENABLE_MULTIMEDIA)"` で `False` を確認。

### Step 2. `.env.example` にフラグ雛形を追記
- ファイル: `.env.example`
- 内容: 末尾に `# --- Multimedia (Phase 7) ---` セクションを追加し `ENABLE_MULTIMEDIA=false`, `ENABLE_AUDIO_SYNTH=false`, `MULTIMEDIA_OUTPUT_DIR=storage/multimedia` を記載。
- 検証: `grep -n "ENABLE_MULTIMEDIA" .env.example` で 1 件ヒット。

### Step 3. `feature_flags.py` ユーティリティ新設
- ファイル: `src/backend/feature_flags.py` (新規)
- 内容: `is_multimedia_enabled() -> bool`, `is_audio_synth_enabled() -> bool`, `require_multimedia() -> None` (無効時に 503 を投げる) を実装。
- 検証: `python -c "from src.backend.feature_flags import is_multimedia_enabled; print(is_multimedia_enabled())"` で `False`。

### Step 4. 出力ディレクトリ初期化ユーティリティ
- ファイル: `src/backend/multimedia_storage.py` (新規)
- 内容: `ensure_multimedia_dir() -> Path` を実装 (settings の `MULTIMEDIA_OUTPUT_DIR` を `mkdir(parents=True, exist_ok=True)` して返す)。
- 検証: 関数呼び出しでディレクトリが生成されることを確認。

### Step 5. 共通エラークラス追加
- ファイル: `src/backend/exceptions.py`
- 内容: `MultimediaDisabledError(AutoNovelException)` を追加 (`status_code=503`, `detail="Multimedia features are disabled"`)。
- 検証: `from src.backend.exceptions import MultimediaDisabledError; raise MultimediaDisabledError()` で `status_code=503`。

### Step 6. 既存 `series_to_dict()` ヘルパの抽出
- ファイル: `src/services/series_serializer.py` (新規)
- 内容: `SeriesResult` を dict に変換する `series_to_dict(series: SeriesResult) -> dict[str, Any]` を実装。エピソード本文を `len(content)` 等の要約フィールドに変換。
- 検証: 既存 `pipeline.py` の呼び出し箇所を `grep -n "SeriesResult" src/services/ | head -3` で確認し、壊れていないか目視。

### Step 7. Alembic マイグレーション雛形生成
- ファイル: `alembic/versions/0011_multimedia_artifacts.py` (新規)
- 内容: 下記 3 テーブルを作成する `upgrade()`/`downgrade()` を実装 (詳細は Step 33〜35 で実装)。
- 検証: `alembic upgrade head` が通ること (Step 34 完了後に再確認)。

### Step 8. 開発サーバ起動スクリプト更新
- ファイル: `scripts/dev_multimedia.sh` (新規)
- 内容: `ENABLE_MULTIMEDIA=true ENABLE_AUDIO_SYNTH=true uvicorn src.backend.server:app --reload` を起動する 1 行スクリプト。
- 検証: `bash -n scripts/dev_multimedia.sh` で構文チェック。

### Step 9. ドキュメント雛形追加
- ファイル: `docs/multimedia.md` (新規)
- 内容: 「Multimedia 機能の有効化手順」「API エンドポイント一覧」「フロント UI スクリーンショット画像パス (TODO)」を Markdown で記述。
- 検証: ファイルが作成されたことを `ls docs/multimedia.md` で確認。

---

## Phase B: バックエンド実装 (Step 10〜24)

### Step 10. `multimedia_schemas.py` (Pydantic モデル)
- ファイル: `src/backend/schemas/multimedia.py` (新規)
- 内容: `MediaMixRequest`/`MediaMixResponse`, `EbookExportRequest`/`EbookExportResponse`, `IFRouteGenerateRequest`/`IFRouteResponse`, `AssetPackRequest`/`AssetPackResponse` を定義。`asset_id`, `book_id`, `format`(str), `include_if_routes`(bool), `include_media_mix`(bool) 等を含む。
- 検証: `python -c "from src.backend.schemas.multimedia import MediaMixRequest; MediaMixRequest(book_id=1, format='audio_drama')"` でインスタンス化可。

### Step 11. `multimedia_service.py` (統合サービス層)
- ファイル: `src/backend/multimedia_service.py` (新規)
- 内容: `MultimediaService` クラスを実装。`__init__(self, settings)` で `feature_flags` を参照。各メソッドは `require_multimedia()` を入口で呼び、無効時に `MultimediaDisabledError` を投げる。
- 検証: `from src.backend.multimedia_service import MultimediaService` でインポート可能。

### Step 12. `MultimediaService.generate_media_mix` 実装
- ファイル: `src/backend/multimedia_service.py` (継続)
- 内容: `book_id` を BookRepository で取得 → 直近 SeriesResult をインメモリ再現 → `create_media_mix_exporter(genre, preset).export_all(...)` を呼び、各フォーマット JSON を `multimedia_storage` に書き出す。戻り値は `{asset_id, files: [...]}`
- 検証: Step 30 のテストで網羅。

### Step 13. `MultimediaService.export_ebook` 実装
- ファイル: `src/backend/multimedia_service.py` (継続)
- 内容: `book_id` → SeriesResult → `create_ebook_exporter(genre, preset).export_all(...)`。EPUB/PDF/MOBI のパスを返す。`EPUB_AVAILABLE=False` 等の場合は警告ログ + JSON ダンプ出力にフォールバック。
- 検証: Step 31 のテストで網羅。

### Step 14. `MultimediaService.generate_if_routes` 実装
- ファイル: `src/backend/multimedia_service.py` (継続)
- 内容: `create_if_route_system(genre, series, preset)` を呼び、`IFRouteGraph` を dict 化 → `MultimediaArtifact` テーブル (Step 34 で作る) に保存 → `asset_id` 返却。
- 検証: Step 32 のテストで網羅。

### Step 15. `MultimediaService.generate_asset_pack` 実装
- ファイル: `src/backend/multimedia_service.py` (継続)
- 内容: `AssetPackGenerator(genre, preset).generate_pack(series, output_dir=...)` を呼び、ZIP 化 → 保存 → マニフェスト JSON を DB に格納。
- 検証: Step 33 のテストで網羅。

### Step 16. `routers/multimedia.py` 新設 (REST API)
- ファイル: `src/backend/routers/multimedia.py` (新規)
- 内容: `router = APIRouter()` を作成し、以下のエンドポイントを定義:
  - `POST /multimedia/media-mix` → `service.generate_media_mix`
  - `POST /multimedia/ebook` → `service.export_ebook`
  - `POST /multimedia/if-routes` → `service.generate_if_routes`
  - `POST /multimedia/asset-pack` → `service.generate_asset_pack`
  - `GET /multimedia/artifacts/{asset_id}` → メタデータ取得
  - `GET /multimedia/artifacts/{asset_id}/download` → ZIP / ファイルを StreamingResponse で返却
- 検証: Step 36〜40 のテストで網羅。

### Step 17. ルータ依存性注入 (`Depends`)
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: `def get_multimedia_service() -> MultimediaService: ...` を追加し、各エンドポイントを `Depends(get_multimedia_service)` で受ける。
- 検証: Step 36 のテストで `app.dependency_overrides` を使ってスタブ注入。

### Step 18. 認証・レート制限ミドルウェア適用
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: 既存 `easy_mode.py` の流儀に合わせ `Depends(validate_api_key_or_raise)` と `generate_limiter(...)` を各エンドポイントに付与。
- 検証: `grep -n "validate_api_key\|rate_limit" src/backend/routers/multimedia.py` でヒット確認。

### Step 19. `server.py` へのルータ登録
- ファイル: `src/backend/server.py`
- 内容: `restored_routers` リストに `"src.backend.routers.multimedia"` を追加。
- 検証: `python -c "from src.backend.server import app; print([r.path for r in app.routes if 'multimedia' in r.path])"` でパス列挙。

### Step 20. `multimedia_tasks.py` (非同期タスク) 新設
- ファイル: `src/backend/tasks/multimedia_tasks.py` (新規)
- 内容: Huey タスクとして `generate_asset_pack_task(asset_id, book_id)` を実装。`@huey.task()` デコレータを既存 `tasks/` に倣って使用。`MultimediaService` を呼び出して DB を更新する。
- 検証: Step 48 のテストで網羅。

### Step 21. タスク ID とレスポンスの橋渡し
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: `POST /multimedia/asset-pack` のレスポンスを `{"task_id": "...", "asset_id": "..."}` 形式にし、`GET /multimedia/tasks/{task_id}` を追加。
- 検証: Step 39 のテストで網羅。

### Step 22. 静的アセット配信エンドポイント
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: `/multimedia/files/{filename}` を追加し、`FileResponse` で `MULTIMEDIA_OUTPUT_DIR` 配下を配信。`pathlib` でトラバーサル防止。
- 検証: Step 40 のテストで `..` パスが 400/403 になることを確認。

### Step 23. OpenAPI 用 `responses` メタデータ
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: 各エンドポイントに `responses={503: {"description": "Multimedia disabled"}, 404: {...}}` を付与。
- 検証: `app.openapi()` の JSON に `"MultimediaDisabledError"` が含まれることを `python -c` で確認。

### Step 24. 構造化ロギング
- ファイル: `src/backend/routers/multimedia.py` (継続)
- 内容: 各エンドポイント入口で `logger.info("multimedia.%s book_id=%s", endpoint, book_id)` を 1 行追加。
- 検証: `grep -c "logger.info" src/backend/routers/multimedia.py` で 4 以上。

---

## Phase C: バックエンド検証・統合 (Step 25〜48)

### Step 25. `tests/conftest.py` 拡張: 一時 `MULTIMEDIA_OUTPUT_DIR`
- ファイル: `tests/conftest.py`
- 内容: `monkeypatch` フィクスチャで `settings.MULTIMEDIA_OUTPUT_DIR = tmp_path / "multimedia"` を上書きする `multimedia_settings` フィクスチャを追加。
- 検証: 既存テスト `pytest tests/unit/test_exporters_full.py` が緑のまま。

### Step 26. `tests/unit/test_media_mix.py` 新設
- ファイル: `tests/unit/test_media_mix.py` (新規)
- 内容: `AudioDramaScriptGenerator.generate(episode, series)` が `MediaScript` を返し、`voice_lines`/`bgm_plan`/`sfx_plan` を含むことを確認。`Panel.to_dict()` が camelCase 互換 dict を返すことを確認。
- 検証: `pytest tests/unit/test_media_mix.py -v` で全件緑。

### Step 27. `tests/unit/test_ebook_export.py` 新設
- ファイル: `tests/unit/test_ebook_export.py` (新規)
- 内容: `EbookExporter.export_all` が `dict[str, Path]` を返し、未知フォーマットがスキップされることを確認。`ebooklib` 不在環境でも JSON フォールバック出力が生成されることを確認。
- 検証: `pytest tests/unit/test_ebook_export.py -v` で全件緑。

### Step 28. `tests/unit/test_asset_pack.py` 新設
- ファイル: `tests/unit/test_asset_pack.py` (新規)
- 内容: `AssetPackGenerator.generate_pack(series, output_dir)` が ZIP ファイルを作成し、`AssetPackMetadata.to_dict()` に必須フィールドが含まれることを確認。
- 検証: `pytest tests/unit/test_asset_pack.py -v` で全件緑。

### Step 29. `tests/unit/test_if_routes.py` 拡充
- ファイル: `tests/unit/test_if_routes.py`
- 内容: `RouteChoice.apply_effects()` のネスト更新、`IFRouteGenerator.generate_from_series` が最低 1 つのノードを生成すること、`IFRouteGraph.validate()` が空リストを返すこと、を追加テスト。
- 検証: `pytest tests/unit/test_if_routes.py -v` で全件緑。

### Step 30. `tests/unit/test_multimedia_service.py` 新設 (Step 12 を網羅)
- ファイル: `tests/unit/test_multimedia_service.py` (新規)
- 内容: `MultimediaService.generate_media_mix` が `MagicMock` の SeriesResult を受け、`asset_id` を返すことを確認。`MultimediaDisabledError` が `require_multimedia()` 失敗時に発生することを確認。
- 検証: `pytest tests/unit/test_multimedia_service.py -v` で全件緑。

### Step 31. `tests/unit/test_multimedia_service.py` 続き (Step 13)
- 内容: `export_ebook` が `EPUB_AVAILABLE=False` 環境でも JSON ファイルを作成し、`files` リストに `.json` が含まれることを確認。
- 検証: 上記と同じ pytest コマンド。

### Step 32. `tests/unit/test_multimedia_service.py` 続き (Step 14)
- 内容: `generate_if_routes` が `MultimediaArtifact` 行を作成し、`asset_id` を返すことを確認。`InMemoryDB` をテスト用セットアップで注入。
- 検証: 上記と同じ pytest コマンド。

### Step 33. `tests/unit/test_multimedia_service.py` 続き (Step 15)
- 内容: `generate_asset_pack` が ZIP を `MULTIMEDIA_OUTPUT_DIR` に書き込み、`content_type="application/zip"` のレスポンス dict を返すことを確認。
- 検証: 上記と同じ pytest コマンド。

### Step 34. `tests/unit/test_multimedia_models.py` 新設 (Step 7)
- ファイル: `tests/unit/test_multimedia_models.py` (新規)
- 内容: `MultimediaArtifact` (book_id, asset_type, format, file_path, metadata_json, created_at) と `MultimediaTask` (asset_id, status, started_at, finished_at) の Pydantic モデルが round-trip 可能であることを確認。
- 検証: `pytest tests/unit/test_multimedia_models.py -v` で全件緑。

### Step 35. Alembic マイグレーション本体実装 (Step 7 続き)
- ファイル: `alembic/versions/0011_multimedia_artifacts.py` (継続)
- 内容: `op.create_table("multimedia_artifacts", ...)`, `op.create_table("multimedia_tasks", ...)` を `upgrade()` に実装し、`downgrade()` で `drop_table` する。
- 検証: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` の 3 コマンドが通る。

### Step 36. `tests/integration/test_multimedia_router.py` 新設 (Step 16-17)
- ファイル: `tests/integration/test_multimedia_router.py` (新規)
- 内容: `TestClient(app)` で `POST /multimedia/media-mix` を叩き、503 / 200 の両分岐を確認。`dependency_overrides` で `MultimediaService` をスタブ化。
- 検証: `pytest tests/integration/test_multimedia_router.py -v` で全件緑。

### Step 37. 同テストに ebook エンドポイント追加 (Step 16)
- 内容: `POST /multimedia/ebook` が 200 を返し、`files` キーが list[str] であることを確認。
- 検証: 上記と同じ。

### Step 38. 同テストに if-routes エンドポイント追加 (Step 16)
- 内容: `POST /multimedia/if-routes` が DB に 1 行 insert することを確認。
- 検証: 上記と同じ。

### Step 39. 同テストに asset-pack エンドポイント + task polling 追加 (Step 15, 21)
- 内容: `POST /multimedia/asset-pack` → 200 + `task_id` → `GET /multimedia/tasks/{task_id}` → 200 + `status="completed"` のフローを確認。
- 検証: 上記と同じ。

### Step 40. 同テストに download / files セキュリティ確認 (Step 22)
- 内容: `GET /multimedia/files/../../etc/passwd` が 400/403 を返すこと、正規パスが 200 を返すことを確認。
- 検証: 上記と同じ。

### Step 41. `tests/unit/test_feature_flags.py` 新設 (Step 3)
- ファイル: `tests/unit/test_feature_flags.py` (新規)
- 内容: `monkeypatch.setattr(settings, "ENABLE_MULTIMEDIA", True)` で `is_multimedia_enabled()` が `True` を返すこと、`require_multimedia()` が無効時に `MultimediaDisabledError` を投げることを確認。
- 検証: `pytest tests/unit/test_feature_flags.py -v` で全件緑。

### Step 42. `tests/unit/test_multimedia_storage.py` 新設 (Step 4)
- ファイル: `tests/unit/test_multimedia_storage.py` (新規)
- 内容: `ensure_multimedia_dir()` が冪等 (`mkdir(exist_ok=True)`) に動作し、`Path` を返すことを確認。
- 検証: `pytest tests/unit/test_multimedia_storage.py -v` で全件緑。

### Step 43. `tests/unit/test_multimedia_schemas.py` 新設 (Step 10)
- ファイル: `tests/unit/test_multimedia_schemas.py` (新規)
- 内容: 必須フィールド欠損時に `ValidationError` が出ること、`include_if_routes=True` 等がデフォルトで `False` であることを確認。
- 検証: `pytest tests/unit/test_multimedia_schemas.py -v` で全件緑。

### Step 44. `tests/unit/test_series_serializer.py` 新設 (Step 6)
- ファイル: `tests/unit/test_series_serializer.py` (新規)
- 内容: `series_to_dict()` が `SeriesResult` のエピソード本文を要約 (先頭 200 字等) に変換し、`total_episodes` を含む dict を返すことを確認。
- 検証: `pytest tests/unit/test_series_serializer.py -v` で全件緑。

### Step 45. `tests/integration/test_multimedia_e2e.py` 新設
- ファイル: `tests/integration/test_multimedia_e2e.py` (新規)
- 内容: `ENABLE_MULTIMEDIA=true` を monkeypatch → テスト用 SQLite DB を生成 → `POST /multimedia/asset-pack` → `GET /multimedia/artifacts/{id}/download` → ZIP が `application/zip` で返ることを end-to-end で確認。
- 検証: `pytest tests/integration/test_multimedia_e2e.py -v` で全件緑。

### Step 46. `tests/unit/test_observability.py` 拡張 (Step 24)
- ファイル: `tests/unit/test_observability.py`
- 内容: `caplog` で `multimedia.media_mix book_id=1` ログが記録されることを確認。
- 検証: `pytest tests/unit/test_observability.py -v` で全件緑。

### Step 47. `mypy` 型チェック
- コマンド: `mypy src/backend/multimedia_service.py src/backend/routers/multimedia.py src/backend/schemas/multimedia.py`
- 内容: すべての `->` 型注釈が満たされていることを確認。`Any` の濫用を最小化。
- 検証: `mypy ... --strict` の終了コード 0。

### Step 48. `tests/unit/test_multimedia_tasks.py` 新設 (Step 20)
- ファイル: `tests/unit/test_multimedia_tasks.py` (新規)
- 内容: `generate_asset_pack_task` を直接呼び、`MultimediaArtifact` 行の `status` が `completed` に更新されることを確認 (Huey の即時実行モード `immediate=True` で)。
- 検証: `pytest tests/unit/test_multimedia_tasks.py -v` で全件緑。

---

## Phase D: フロント実装 (Step 49〜60)

### Step 49. `frontend/src/types/multimedia.ts` 新設
- ファイル: `frontend/src/types/multimedia.ts` (新規)
- 内容: `MediaMixRequest`, `MediaMixResponse`, `EbookExportRequest`, `IFRouteRequest`, `AssetPackRequest`, `AssetPackResponse`, `ArtifactMeta` を `interface` で定義。
- 検証: `npx tsc --noEmit` で型エラーなし。

### Step 50. `frontend/src/api/multimedia.ts` 新設
- ファイル: `frontend/src/api/multimedia.ts` (新規)
- 内容: `generateMediaMix`, `exportEbook`, `generateIFRoutes`, `generateAssetPack`, `downloadArtifact` を `fetch` ベースで実装。`BASE = "/multimedia"`。
- 検証: `npx tsc --noEmit` で型エラーなし。

### Step 51. `frontend/src/hooks/useMultimedia.ts` 新設
- ファイル: `frontend/src/hooks/useMultimedia.ts` (新規)
- 内容: `useMultimedia()` フックで `loading`, `error`, `progress`, `assetId` を `useState` で管理し、`generateAssetPack`, `downloadAssetPack` を返却。
- 検証: `npx tsc --noEmit` で型エラーなし。

### Step 52. `frontend/src/components/AssetPackPanel.tsx` 新設
- ファイル: `frontend/src/components/AssetPackPanel.tsx` (新規)
- 内容: React FC。Props: `bookId: number`。UI: チェックボックス 4 種 (`IF Routes`/`Media Mix`/`Ebook EPUB`/`Ebook PDF`) + 「Generate Asset Pack」ボタン + プログレスバー + ダウンロードリンク。
- 検証: `npm run lint` で 0 エラー。

### Step 53. `AssetPackPanel` を `StudioWorkspace` に組み込み
- ファイル: `frontend/src/components/studio/StudioWorkspace.tsx`
- 内容: 既存タブ群に「Multimedia」タブを追加し、`<AssetPackPanel bookId={selectedBookId} />` を配置。
- 検証: `grep -n "AssetPackPanel" frontend/src/components/studio/StudioWorkspace.tsx` でヒット確認。

### Step 54. CSS / Tailwind スタイル追加
- ファイル: `frontend/src/components/AssetPackPanel.module.css` (新規) または Tailwind クラス
- 内容: チェックボックス横並び、ボタン無効化状態のスタイルを定義。
- 検証: `npm run lint` で 0 エラー。

### Step 55. Toast 通知の組み込み
- ファイル: `frontend/src/components/AssetPackPanel.tsx` (継続)
- 内容: 既存 `common/ToastContainer.tsx` の `useToast()` を使い、成功 / 失敗時にトースト表示。
- 検証: `grep -n "useToast" frontend/src/components/AssetPackPanel.tsx` でヒット確認。

### Step 56. 多言語 i18n キー追加
- ファイル: `frontend/src/i18n/ja.json`, `frontend/src/i18n/en.json`
- 内容: `multimedia.title`, `multimedia.if_routes`, `multimedia.media_mix`, `multimedia.ebook_epub`, `multimedia.ebook_pdf`, `multimedia.generate`, `multimedia.download`, `multimedia.success`, `multimedia.error` を追加。
- 検証: `jq . frontend/src/i18n/ja.json | grep multimedia` でヒット確認。

### Step 57. フロントエンドユニットテスト (`vitest`)
- ファイル: `frontend/tests/components/AssetPackPanel.test.tsx` (新規)
- 内容: `vi.mock("../api/multimedia")` で API をモック化し、ボタン押下 → 成功 / 失敗 UI を確認。
- 検証: `npm run test -- AssetPackPanel.test.tsx` で全件緑。

### Step 58. Storybook ストーリー追加 (任意)
- ファイル: `frontend/src/components/AssetPackPanel.stories.tsx` (新規)
- 内容: デフォルト / ロード中 / エラーの 3 バリアントを定義。
- 検証: `npm run lint` で 0 エラー。

### Step 59. E2E (Playwright) テスト
- ファイル: `frontend/tests/e2e/multimedia.spec.ts` (新規)
- 内容: `page.goto("/")` → スタジオタブを開く → Multimedia タブ → Generate → download イベント発火を確認。
- 検証: `npx playwright test frontend/tests/e2e/multimedia.spec.ts` で全件緑。

### Step 60. フロントエンド Lint / Typecheck
- コマンド: `npm run lint && npm run typecheck`
- 検証: 終了コード 0。

---

## Phase E: ロールアウト・運用 (Step 61〜72)

### Step 61. ステージング環境デプロイ手順
- ファイル: `docs/multimedia.md` (継続)
- 内容: `.env` で `ENABLE_MULTIMEDIA=true` を設定 → `docker compose up -d backend frontend` → `/health` で新ルートが登録されたか確認する手順を記述。
- 検証: 手順が Markdown として読めること。

### Step 62. フィーチャートグル UI 化 (管理画面)
- ファイル: `frontend/src/components/admin/FeatureFlagsPanel.tsx` (新規)
- 内容: 管理者向けに `ENABLE_MULTIMEDIA` を ON/OFF できるトグル UI (内部 API は別 Issue)。
- 検証: `npm run lint` で 0 エラー。

### Step 63. カナリアリリース (10% トラフィック)
- ファイル: `docs/multimedia.md` (継続)
- 内容: フロントの `useMultimedia` 内で `Math.random() < 0.1` カナリア分岐を有効化する手順 (FeatureFlagService 経由)。
- 検証: ドキュメント反映のみ。

### Step 64. メトリクス追加 (`/metrics` 拡張)
- ファイル: `src/backend/observability/health.py`
- 内容: `multimedia_requests_total{multimedia.media_mix, ...}`, `multimedia_errors_total` カウンタを追加。
- 検証: `curl /metrics | jq '.multimedia_requests_total'` で値取得。

### Step 65. アラート設定 (Grafana)
- ファイル: `docker/grafana/alerts/multimedia.yaml` (新規)
- 内容: 5xx エラー率 > 5% でアラート。
- 検証: YAML バリデーション `python -c "import yaml; yaml.safe_load(open('docker/grafana/alerts/multimedia.yaml'))"` で例外なし。

### Step 66. 負荷テスト (Locust)
- ファイル: `tests/load/multimedia_locust.py` (新規)
- 内容: `MediaMixUser` が `/multimedia/media-mix` を 100 RPS で叩くシナリオ。
- 検証: `locust -f tests/load/multimedia_locust.py --headless -u 10 -r 2 -t 30s` が完走。

### Step 67. SLO ドキュメント
- ファイル: `docs/multimedia_slo.md` (新規)
- 内容: 可用性 99.5%、レイテンシ p95 < 3s、を定義。
- 検証: ファイルが作成されたこと。

### Step 68. セキュリティレビュー (パストラバーサル / SSRF)
- ファイル: `docs/multimedia_security.md` (新規)
- 内容: Step 22 の `..` チェック、`MUL TIMEDIA_OUTPUT_DIR` をルート直下に置かない理由、SSRF リスクなし (出力のみ) を記述。
- 検証: ファイルが作成されたこと。

### Step 69. ユーザーマニュアル
- ファイル: `docs/user/multimedia.md` (新規)
- 内容: 「Multimedia タブから ZIP を生成 → ダウンロード → 解凍」の手順をスクショ付きで記載。
- 検証: ファイルが作成されたこと。

### Step 70. CHANGELOG 更新
- ファイル: `CHANGELOG.md`
- 内容: `## [Unreleased] - Multimedia (Phase 7)` セクションを追加し、Step 1〜69 の完了内容を箇条書きで記載。
- 検証: `grep -n "Multimedia (Phase 7)" CHANGELOG.md` でヒット確認。

### Step 71. 全テスト一括実行
- コマンド: `pytest tests/ -q --maxfail=3`
- 検証: 終了コード 0、failure 0 件。

### Step 72. 本番ロールアウト (100%)
- ファイル: `.env` (本番環境)
- 内容: `ENABLE_MULTIMEDIA=true` を設定 → ローリングデプロイ → `/metrics` でカウンタ増加を監視。
- 検証: デプロイ完了後 24 時間のインシデントなし。

---

## 凡例

- 各ステップは 30 分〜2 時間以内を想定。
- 1 ステップ完了ごとに `git add -p` → `pytest <新規/更新ファイル> -v` → 緑なら `git commit -m "step(N): <要約>"` を実施する。
- ロールバック判断は「テストが 30 分以内に緑にならない」または「既存テストを 3 件以上破壊」のいずれかで発動。
- ステップ番号はコミットメッセージのプレフィックスとして再利用することで、進捗を `git log --oneline | grep "^step"` で一覧化できる。
