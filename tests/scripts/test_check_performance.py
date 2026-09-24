import os
import subprocess
import sys

def test_check_performance_script():
    """Run the performance check script and verify it passes."""
    result = subprocess.run(
        [sys.executable, "scripts/check_performance.py"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    # The script should exit with 0 (success)
    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    # Check that the success message is in the output
    assert "Performance check passed" in result.stdout