"""Docker イメージのセキュリティ構成をテスト"""
import subprocess

def test_image_contains_no_unnecessary_packages():
    # イメージをビルド（または既存のものを使用）
    result = subprocess.run(
        ["docker", "build", "-q", "-f", "Dockerfile.prod", "."],
        capture_output=True, text=True, check=True
    )
    image_id = result.stdout.strip()
    # パッケージリストを取得
    result = subprocess.run(
        ["docker", "run", "--rm", image_id, "dpkg", "-l"],
        capture_output=True, text=True, check=True
    )
    installed_packages = set(result.stdout.splitlines())
    # 必要最低限のパッケージ以外がインストールされていないことを確認
    # （例: python3, ca-certificates 等は許容、vim, nano, ssh サーバー等はNG）
    unnecessary = {"vim", "nano", "openssh-server", "net-tools"}
    found_unnecessary = unnecessary & {p.split()[1] for p in installed_packages if p.startswith("ii")}
    assert not found_unnecessary, f"Found unnecessary packages: {found_unnecessary}"

def test_image_runs_as_nonroot():
    result = subprocess.run(
        ["docker", "build", "-q", "-f", "Dockerfile.prod", "."],
        capture_output=True, text=True, check=True
    )
    image_id = result.stdout.strip()
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "", image_id, "ps", "-o", "pid,user"],
        capture_output=True, text=True, check=True
    )
    # プロセス一覧から、PID 1 (通常は uvicorn) が root でないことを確認
    lines = result.stdout.strip().splitlines()[1:]  # ヘッダー行を除く
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "1":  # PID 1
            assert parts[1] != "root", f"PID 1 runs as {parts[1]}"