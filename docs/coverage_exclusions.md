# Coverage Exclusions Justification

## src/backend/observability/health.py:209-212
- **理由**: モニタリングメトリクスのリセット関数はテスト専用であり、本番コードからは呼び出されない
- **コード**:
  ```python
  @pytest.fixture(autouse=True)
  def reset_metrics():
      """各テスト後に health.py のプロセスメトリクスをゼロリセットする。

      pytest-xdist 並列実行時にメトリクスがリークするのを防止する。
      """
      from src.backend.observability.health import metrics

      yield
      metrics.reset_for_testing()
  ```
- **テスト戦略**: 本番コードではこのフィクスチャは使用されないため、カバレッジ対象外とする

## src/backend/auth.py:25-36
- **理由**: 開発・テスト用のモックユーザーを生成するヘルパー関数。本番では AUTH_DISABLED が False なので呼び出されない
- **コード**:
  ```python
  def _get_dev_mock_user() -> User:
      """開発・テスト用のモック管理者ユーザーを生成する。"""
      user = User(
          id=1,
          email="dev@autonovel.local",
          display_name="Dev Admin",
          role="admin",
          status="active",
          plan_tier="enterprise",
          credits=99999,
      )
      return user
  ```
- **テスト戦略**: AUTH_DISABLED が True の場合のみ使用されるため、本番相当のテストではカバレッジ対象外とする

## src/backend/auth.py:46-47
- **理由**: AUTH_DISABLED が True の場合のみモックユーザーを返す分岐。本番では AUTH_DISABLED が False なのでこのパスは通らない
- **コード**:
  ```python
  if settings.AUTH_DISABLED:
      return _get_dev_mock_user()
  ```
- **テスト戦略**: 本番相当の設定（AUTH_DISABLED=False）ではこのパスは通らないことを保証

## src/backend/auth.py:151-152
- **理由**: API キー検証において、AUTH_DISABLED が True の場合は開発キーを返す。本番では AUTH_DISABLED が False なのでこのパスは通らない
- **コード**:
  ```python
  if settings.AUTH_DISABLED:
      return "dev-key"
  ```
- **テスト戦略**: 本番相当の設定ではこのパスは通らないことを保証

## src/backend/auth.py:155-156
- **理由**: API キー検証において、許可されたキーリストが空または一致しない場合は False を返すが、本番では環境変数で適切なキーが設定されているためこのパスは通らない
- **コード**:
  ```python
  if not allowed_keys or api_key not in allowed_keys:
      return False
  ```
- **テスト戦략**: 本番環境では有効な API キーが設定されているためこのパスは通らないことを保証