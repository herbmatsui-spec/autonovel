#!/usr/bin/env python3
import tomli
import sys
from pathlib import Path

def main():
    with open("pyproject.toml", "rb") as f:
        data = tomli.load(f)
    # tool.coverage.run.omit または tool.coverage.report.omit を想定
    omit = data.get("tool", {}).get("coverage", {}).get("run", {}).get("omit", [])
    if not omit:
        omit = data.get("tool", {}).get("coverage", {}).get("report", {}).get("omit", [])
    
    output_path = Path("artifacts/omit_list.txt")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        for pattern in omit:
            f.write(pattern + "\n")
    
    print(f"Found {len(omit)} omit patterns")
    # 実際にファイルシステムでマッチするものを列挙（オプション）
    import glob
    matched = []
    for pattern in omit:
        matched.extend(glob.glob(pattern, recursive=True))
    matched = sorted(set(matched))
    print(f"Matched {len(matched)} files")
    with open("artifacts/omit_matched_files.txt", "w") as f:
        for file in matched:
            f.write(file + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
