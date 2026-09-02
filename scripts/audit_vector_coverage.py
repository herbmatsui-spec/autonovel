"""CLI: 監査ベクトルコレクションが正常に初期化されるかを確認する.

Usage:
    python scripts/audit_vector_coverage.py [--exit-on-fail]

終了コード:
    0  全コレクション成功
    1  失敗あり
"""
from __future__ import annotations

import argparse
import sys

from src.services.vector_store import HAS_CHROMA, audit_collection_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exit-on-fail",
        action="store_true",
        help="1 つでも失敗があれば exit code 1 で終了",
    )
    args = parser.parse_args()

    if not HAS_CHROMA:
        print(
            "chromadb がインストールされていないため、ChromaDB 経由の監査はスキップします。",
            file=sys.stderr,
        )
        print("pip install -e '.[rag]' を実行するとフル監査できます。", file=sys.stderr)
        return 0

    from src.services.vector_store import ChromaClientProvider, ChromaVectorStore

    provider = ChromaClientProvider()
    store = ChromaVectorStore(provider)
    results = store.audit_collection_coverage()

    failed = [name for name, ok in results.items() if not ok]
    for name, ok in results.items():
        status = "OK " if ok else "FAIL"
        print(f"[{status}] {name}")

    if failed and args.exit_on_fail:
        print(f"\n{len(failed)} collection(s) failed: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
