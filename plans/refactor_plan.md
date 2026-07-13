# 実装計画書: ツール全体の構造最適化およびモダン化

## 1. 目的
本計画の目的は、`streamlit_app/app.py` を含むツール全体のコードベースを精査し、保守性、型安全性、および実行パフォーマンスを向上させることである。具体的には、ディレクトリ構造の整理、Python型ヒントの全面導入、およびI/O待ちの多い処理への非同期処理（asyncio）の導入を行う。

## 2. 主要改善項目

### 2.1 ディレクトリ構造の整理
現状、`streamlit_app/` フォルダに UI ロジックとビジネスロジックが混在している。これを `src/` フォルダ配下へ移行し、関心の分離（Separation of Concerns）を徹底する。

- **現状**: `streamlit_app/` (UI + Service)
- **目標**: 
    - `streamlit_app/`: Streamlit のプレゼンテーション層（UI定義、ページルーティング）のみを配置。
    - `src/`: ビジネスロジック、データアクセス、外部 API 連携、ドメインモデルを配置。

### 2.2 型ヒント（Type Hints）の導入
静的解析ツールによるバグの早期発見と、開発効率向上のため、関数シグネチャおよび変数に厳格な型ヒントを追加する。

- `typing` モジュールの活用 (`List`, `Dict`, `Optional`, `Union`, `Callable` 等)
- Pydantic モデルによるデータバリデーションの強化
- 複雑な型に対する `TypeAlias` の定義

### 2.3 非同期処理（asyncio）の導入
API 連携やデータベース操作などの I/O 待ち時間を削減するため、同期的な処理を `async/await` パターンに移行し、体感速度を向上させる。

- `httpx` などの非同期 HTTP クライアントの導入
- `sqlalchemy[asyncio]` による非同期 DB アクセスの実装
- Streamlit と非同期処理の統合（`asyncio.run` または専用のランナーの活用）

---

## 3. 詳細実装ステップ (Step 1-36)

### フェーズ 1: 現状分析と基盤整備 (Step 1-6)
- [ ] Step 1: 全ファイルの依存関係グラフを作成し、循環参照の有無を確認を確認する
- [ ] Step 2: `streamlit_app/` 内のロジックと UI の境界線を明確に定義する
- [ ] Step 3: `src/` フォルダのディレクトリ構造（`core`, `services`, `domain`, `infrastructure`）を再定義する
- [ ] Step 4: 型チェックツール `mypy` の導入と基本設定ファイルの作成
- [ ] Step 5: 非同期ライブラリ（`httpx`, `anyio` 等）の依存関係を追加
- [ ] Step 6: 回帰テストのための現状の動作確認スイートを整備する

### フェーズ 2: ディレクトリ構造の再編 (Step 7-15)
- [ ] Step 7: `src/domain/` にデータモデル（Entity/Value Object）を定義し、`streamlit_app/` から移行
- [ ] Step 8: `src/infrastructure/` に DB アクセス層（Repository パターン）を構築
- [ ] Step 9: `streamlit_app/engine_service.py` のビジネスロジックを `src/services/` へ抽出
- [ ] Step 10: `streamlit_app/api_client.py` を `src/infrastructure/api/` へ移行
- [ ] Step 11: `streamlit_app/state.py` を `src/core/state/` へ整理
- [ ] Step 12: `streamlit_app/utils/` の汎用関数を `src/shared/utils/` へ移行
- [ ] Step 13: `app.py` のエントリーポイントを `src/` のサービスを呼び出す形にリファクタリング
- [ ] Step 14: インポートパスの全面的な修正（`streamlit_app.xxx` → `src.xxx`）
- [ ] Step 15: ディレクトリ移行後の動作確認とパス解決の検証

### フェーズ 3: 型ヒントの全面導入 (Step 16-24)
- [ ] Step 16: `src/domain/` 内の全モデルに厳格な型定義を適用
- [ ] Step 17: Repository 層のインターフェースに型ヒントを導入
- [ ] Step 18: Service 層のメソッドシグネチャ（引数・戻り値）に型を追加
- [ ] Step 19: `streamlit_app/` 内の UI コンポーネントに型ヒントを導入
- [ ] Step 20: 複雑な辞書型を Pydantic モデルまたは `TypedDict` に置き換え
- [ ] Step 21: `Optional` や `Union` を活用して None 許容型の安全性を確保
- [ ] Step 22: `mypy` による静的解析を実行し、型エラーをすべて解消
- [ ] Step 23: ジェネリクス (`TypeVar`) を導入し、再利用可能なコンポーネントを型安全にする
- [ ] Step 24: 型定義ドキュメント（docstring）の整備

### フェーズ 4: 非同期処理への移行 (Step 25-33)
- [ ] Step 25: I/O 負荷の高い主要 API エンドポイントの特定
- [ ] Step 26: `src/infrastructure/api/` のクライアントを `httpx.AsyncClient` に変更
- [ ] Step 27: DB アクセス層を `AsyncSession` を利用した非同期クエリに書き換え
- [ ] Step 28: Service 層のメソッドを `async def` に変更し、`await` チェーンを構築
- [ ] Step 29: `asyncio.gather` を利用した並行 API リクエストの実装
- [ ] Step 30: Streamlit の同期的なイベントループ内で非同期関数を呼び出すためのラッパー実装
- [ ] Step 31: `streamlit_app/` の UI 更新処理と非同期処理の同期タイミングを最適化
- [ ] Step 32: 非同期処理におけるエラーハンドリングとリトライメカニズムの構築
- [ ] Step 33: 非同期化によるパフォーマンス計測（Before/After の比較）

### フェーズ 5: 最終調整と品質保証 (Step 34-36)
- [ ] Step 34: 全体的なコードレビューと Python コーディング規約 (PEP 8) への準拠確認
- [ ] Step 35: 統合テストの実施によるデグレ（機能退行）の確認
- [ ] Step 36: 最終的なデプロイ確認とメンテナンスドキュメントの更新