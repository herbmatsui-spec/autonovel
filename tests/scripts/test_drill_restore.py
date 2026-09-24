import os
import subprocess
import sys

def test_drill_restore_script_runs():
    """Run the drill restore script and verify it runs without error."""
    result = subprocess.run(
        [sys.executable, "scripts/drill_restore.py"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    # The script should exit with 0 (success)
    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    # Check that the script logged the expected messages (output goes to stderr due to logging)
    assert "Starting disaster recovery drill" in result.stderr
    assert "Step 1: Would download latest backup" in result.stderr
    assert "Disaster recovery drill completed." in result.stderr