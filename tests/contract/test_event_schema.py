"""イベントスキーマ（WebSocket, Webhook 等）の後方互換性を検証"""

def test_webhook_event_schema_backward_compatible():
    """Stripe Webhook 等のイベントスキーマが後方互換であるか"""
    # イベントスキーマファイルを読み込み
    # jsonschema.Draft7Validator で後方互換性検証
    # （フィールド追加は OK、フィールド削除・型変更は NG）
    pass