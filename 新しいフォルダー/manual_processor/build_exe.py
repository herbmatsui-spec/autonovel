import subprocess
import sys

def build():
    print("===================================================")
    print(" Manual & Business Document Processor - EXE Builder")
    print("===================================================")
    print("\n1. Installing requirements and PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("\n2. Building Single-File EXE...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "DocumentProcessor",
        "--collect-all", "google.genai",
        "--collect-all", "google.cloud.vision",
        "--hidden-import", "PIL",
        "--hidden-import", "fitz",
        "--hidden-import", "docx",
        "--hidden-import", "fpdf",
        "--hidden-import", "gtts",
        "--clean",
        "main.py"
    ]
    
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n===================================================")
        print(" ✅ ビルドが正常に完了しました！")
        print(" dist フォルダ内に 単一exeファイル 「DocumentProcessor.exe」 が作成されました。")
        print("===================================================")
    else:
        print("\n❌ ビルド中にエラーが発生しました。")

if __name__ == "__main__":
    build()
    input("\nEnterキーを押して終了します...")
