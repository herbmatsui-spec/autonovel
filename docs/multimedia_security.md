# Multimedia セキュリティレビュー

## 入力検証

- `book_id` は Pydantic で `ge=1` 制約
- `format` は Literal による厳格な値のみ許可
- 不明な値は 422 を返す

## パストラバーサル防止

- `/multimedia/files/{filename:path}` は `_safe_path_under_base()` でベースディレクトリ外を拒否
- `..` を含むパスは 400

## SSRF

- Multimedia は出力のみを扱い、外部への HTTP 呼び出しは行わない
- したがって SSRF リスクなし

## 認証

- 全エンドポイントが `validate_api_key_or_raise` を要求
- 内部管理用エンドポイントは追加で `admin` ロールを要求する想定

## レート制限

- `generate_limiter` (10 req / 60s) を全エンドポイントに適用
- `stream_limiter` は使用しない (Multimedia は同期)

## データ保護

- `MULTIMEDIA_OUTPUT_DIR` は `storage/multimedia` 配下
- ファイル名は UUID ベース (`asset_pack_<uuid>.zip`) で推測攻撃を防止
- DB には `metadata_json` のみ保存し、本文は含めない
