import subprocess
import sys
import time


def run_tests(run_idx, log_file):
    print(f"[{run_idx}/10] 統合テストを実行中...")
    log_file.write("\n=========================================\n")
    log_file.write(f"RUN {run_idx} - Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write("=========================================\n")
    log_file.flush()

    # Set PYTHONPATH
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.getcwd()}/src;{os.getcwd()}"

    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integration/test_app_integration.py", "-v"],
        capture_output=True,
        text=True,
        env=env
    )

    log_file.write("--- STDOUT ---\n")
    log_file.write(res.stdout)
    log_file.write("\n--- STDERR ---\n")
    log_file.write(res.stderr)
    log_file.write(f"\nExit Code: {res.returncode}\n")
    log_file.flush()

    success = (res.returncode == 0)
    print(f"[{run_idx}/10] 結果: {'成功' if success else '失敗'}")
    return success

def main():
    print("=========================================")
    print(" 統合テスト反復実行スクリブト (10回ループ)")
    print("=========================================")

    start_time = time.time()
    success_count = 0
    total_runs = 10

    with open("integration_test_results.log", "w", encoding="utf-8") as f:
        f.write(f"統合テスト反復実行ログ - 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("対象テスト: tests/integration/test_app_integration.py\n")

        for i in range(1, total_runs + 1):
            if run_tests(i, f):
                success_count += 1
            # Add a small delay between runs to avoid potential resource locks or timing issues
            time.sleep(0.5)

        duration = time.time() - start_time
        summary = (
            f"\n=========================================\n"
            f"実行サマリー\n"
            f"=========================================\n"
            f"総実行回数: {total_runs}\n"
            f"成功回数  : {success_count}\n"
            f"失敗回数  : {total_runs - success_count}\n"
            f"勝率      : {success_count / total_runs * 100:.1f}%\n"
            f"所要時間  : {duration:.2f} 秒\n"
            f"=========================================\n"
        )
        f.write(summary)
        print(summary)

    if success_count == total_runs:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

