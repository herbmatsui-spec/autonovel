# アーキテクチャ分析レポート

## 1. 現状の課題

### 1.1 モデル定義の二重管理
`models/db_models.py` (Pydantic) と `database/models.py` (SQLAlchemy) が存在し、スキーマ定義が重複している。これにより、DB定義変更時に2箇所の修正が必要となり、不整合のリスクが高い。

### 1.2 責務の曖昧さ
- `agents/` に本来 `services/` 等に配置すべき共通機能が混在している。
- `services/` が空であり、ロジック層の設計がなされていない。
- `UltimateHegemonyEngine` が全機能を統合しており、単一責任原則に反している。

## 2. 改善方針

### 2.1 モデル統合の戦略
- `SQLAlchemy` モデルを「真実のソース（Source of Truth）」とする。
- `Pydantic` モデルは `SQLAlchemy` モデルから自動生成、あるいは変換ロジックを共通化することで、手動メンテナンスを不要にする。
- 新しい共通基盤 `database/schemas.py` 等への移行を検討する。

### 2.2 レイヤーの再定義
- `services/` レイヤーを有効化し、ビジネスロジックを分離する。
- `agents/` は Orchestrator（制御層）として、サービス層を呼び出す役割に専念させる。
- `UltimateHegemonyEngine` を分割し、各サービスへ責務を委譲する。

### 2.3 整理対象
- `writer.py` と `writing.py` の統合（機能重複の解消）。
- `scratch/` ディレクトリ配下の実験的ファイルの削除・アーカイブ。
- `src/backend/engine.py` の肥大化解消。
