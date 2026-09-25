def test_flaky_detection_script_exists():
    """Flaky テスト検出スクリプトが存在し実行可能である"""
    assert Path("scripts/detect_flaky.py").exists()
    # 実行可能性チェック（簡易版）
    with open("scripts/detect_flaky.py") as f:
        content = f.read()
        assert "def main()" in content