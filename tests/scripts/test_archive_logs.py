import os
import subprocess
import sys

def test_archive_logs_script_runs():
    """Run the archive logs script and verify it runs without error."""
    result = subprocess.run(
        [sys.executable, "scripts/archive_logs.py"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    # The script should exit with 0 (success)
    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    # Check that the script logged the expected messages (output goes to stderr due to logging)
    assert "Starting log archiving" in result.stderr
    assert "Log archiving completed." in result.stderr