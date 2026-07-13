from unittest.mock import MagicMock, patch

from config.file_watcher import ConfigFileHandler


def test_config_file_handler_initialization():
    """ConfigFileHandler が notifier を正しく受け取るかテスト"""
    mock_notifier = MagicMock()
    mock_callback = MagicMock()

    handler = ConfigFileHandler(callback=mock_callback, notifier=mock_notifier)

    assert handler.notifier == mock_notifier
    assert handler.callback == mock_callback

def test_config_file_handler_on_modified_triggers_callback():
    """設定ファイル変更時に正しく反応するかテスト"""
    mock_notifier = MagicMock()
    mock_callback = MagicMock()

    handler = ConfigFileHandler(callback=mock_callback, notifier=mock_notifier)

    # 監視対象ファイルのパスを模倣
    event = MagicMock()
    event.src_path = "config/settings.toml"
    event.is_directory = False

    # デバウンスを回避するために内部メソッドを直接呼ぶテストは難しいが、
    # 少なくとも on_modified が呼ばれたときに適切に処理されるか確認
    # (ここではタイマー起動の確認のみを行う)
    with patch("threading.Timer") as mock_timer:
        handler.on_modified(event)
        mock_timer.assert_called()
