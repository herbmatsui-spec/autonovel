# 例外階層 (Exception Hierarchy)

`src/core/exceptions.py` で定義される例外は、全て `HegemonyError` を基底クラスとする。
各例外は `status_code` / `error_code` / `message` / `original` を提供し、
API レイヤのエラーハンドラで統一的に HTTP レスポンスへ変換される。

## 階層ツリー

```
HegemonyError (基底, status=500, code=INTERNAL_ERROR)
├── EngineError                       (500, ENGINE_ERROR)
├── APIError                          (502, API_ERROR)
├── AppError                          (500, APP_ERROR)
├── ValidationError                   (422, VALIDATION_ERROR)
├── NotFoundError                     (404, NOT_FOUND)
├── PipelineError                     (502, COMMERCIAL_PIPELINE_ERROR)
└── LLMError                          (502, LLM_ERROR)
    ├── LLMTemporaryError             (429, LLM_TEMPORARY_ERROR)    # レート制限等リトライ可能
    ├── LLMTokenLimitError            (400, LLM_TOKEN_LIMIT_ERROR)
    ├── LLMValidationError            (422, LLM_VALIDATION_ERROR)  # スキーマ検証失敗
    └── LLMUnrecoverableError         (502, LLM_UNRECOVERABLE_ERROR)
```

## HTTP ステータス対応表

| 例外クラス                  | status_code | error_code                   | 想定シナリオ                  |
|----------------------------|-------------|------------------------------|------------------------------|
| `HegemonyError`            | 500         | `INTERNAL_ERROR`             | 基底（捕捉されなかった場合）|
| `EngineError`              | 500         | `ENGINE_ERROR`               | エンジン内部エラー          |
| `APIError`                 | 502         | `API_ERROR`                  | 外部 API 呼び出し失敗        |
| `AppError`                 | 500         | `APP_ERROR`                  | アプリケーションロジック    |
| `ValidationError`          | 422         | `VALIDATION_ERROR`           | 入力検証失敗                 |
| `NotFoundError`            | 404         | `NOT_FOUND`                  | リソース未検出               |
| `PipelineError`            | 502         | `COMMERCIAL_PIPELINE_ERROR`  | 商用パイプライン失敗         |
| `LLMError`                | 502         | `LLM_ERROR`                  | LLM 呼び出し汎用エラー      |
| `LLMTemporaryError`        | 429         | `LLM_TEMPORARY_ERROR`        | レート制限 / 一時障害       |
| `LLMTokenLimitError`       | 400         | `LLM_TOKEN_LIMIT_ERROR`      | トークン上限超過             |
| `LLMValidationError`       | 422         | `LLM_VALIDATION_ERROR`       | レスポンススキーマ検証失敗  |
| `LLMUnrecoverableError`    | 502         | `LLM_UNRECOVERABLE_ERROR`    | 認証キー不正 / 回復不可     |

## 利用指針

- **リトライ可能** なエラーは `LLMTemporaryError`（429）として報告し、
  呼び出し側のリトライ装飾子 (`with_llm_retry`) に処理を委ねる。
- **回復不可能** なエラー（認証失敗等）は即座に `LLMUnrecoverableError`（502）を送出する。
- Pydantic モデル検証時は `safe_model_validate` が `PydanticUserError` を
  `LLMValidationError` にWrapして送出する。
- キャンセル (`RuntimeError("Cancelled")`) は基底例外ではなく、
  パイプラインの `_cancelled` フラグ経由で上位へ伝播させる。
