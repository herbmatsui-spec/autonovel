
import os
import subprocess


def generate_architecture():
    """
    pyreverseを使用してクラス図とパッケージ依存関係図を生成する
    """
    output_dir = "docs/architecture"
    os.makedirs(output_dir, exist_ok=True)

    # クラス図の生成
    cmd_class = [
        "pyreverse",
        "-o", "png",
        "-p", "Claude2_System",
        "--output-directory", output_dir,
        "core", "agents", "services"
    ]

    print("Generating class diagrams...")
    subprocess.run(cmd_class, check=True)
    print(f"Diagrams generated in {output_dir}")

if __name__ == "__main__":
    try:
        generate_architecture()
    except Exception as e:
        print(f"Error generating architecture: {e}")
        print("Ensure pyreverse (part of pylint) is installed: pip install pylint")

