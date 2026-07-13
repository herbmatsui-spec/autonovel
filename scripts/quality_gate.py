import os
import subprocess
import sys


def run_command(command, description):
    print(f"--- Running {description} ---")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        # Use capture_output=True and handle decoding manually to avoid cp932 errors
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            env=env
        )

        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace')

        if result.returncode == 0:
            print(f"[OK] {description} passed.")
            if stdout:
                print(stdout)
            return True
        else:
            print(f"[FAIL] {description} failed (Exit code: {result.returncode})")
            if stdout:
                print("STDOUT:", stdout)
            if stderr:
                print("STDERR:", stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Error executing {description}: {e}")
        return False

def main():
    # 1. Ruff Linting
    ruff_success = run_command("py -m ruff check src", "Ruff Linting")

    # 2. Mypy Type Checking
    mypy_success = run_command("py -m mypy src", "Mypy Type Checking")

    # 3. Radon Complexity Check
    print("--- Running Radon Complexity Check ---")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        complexity_result = subprocess.run(
            "py -m radon cc src -n B",
            shell=True,
            capture_output=True,
            env=env
        )
        stdout = complexity_result.stdout.decode('utf-8', errors='replace')
        if not stdout.strip():
            print("[OK] No high-complexity functions found (all Grade A).")
            radon_success = True
        else:
            print("[WARN] High complexity functions detected:")
            print(stdout)
            radon_success = False
    except Exception as e:
        print(f"[ERROR] Error executing Radon: {e}")
        radon_success = False

    print("\n--- Final Quality Gate Result ---")
    if ruff_success and mypy_success and radon_success:
        print("SUCCESS: ALL QUALITY GATES PASSED")
        sys.exit(0)
    else:
        print("FAILURE: QUALITY GATE FAILED")
        if not ruff_success: print("- Ruff Linting failed")
        if not mypy_success: print("- Mypy Type Checking failed")
        if not radon_success: print("- High complexity code detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
