"""誤って detailed_blueprint から作られてしまった伏線を削除する。

使い方:
    python scripts/cleanup_false_foreshadowings.py            # dry-run（一覧のみ）
    python scripts/cleanup_false_foreshadowings.py --apply    # 実際に削除
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from src.backend.config import settings

# 削除対象: 「同じ book_id の Plot.detailed_blueprint と完全一致し、
# 専用カラム foreshadowing_notes に対応行が無い」planted の伏線のみ。
SQL_SELECT = """
SELECT f.id, f.book_id, f.planted_episode, f.description
FROM foreshadowings f
WHERE EXISTS (
    SELECT 1 FROM plots p
    WHERE p.book_id = f.book_id
      AND TRIM(p.detailed_blueprint) = TRIM(f.description)
)
AND NOT EXISTS (
    SELECT 1 FROM plots p2
    WHERE p2.book_id = f.book_id
      AND p2.ep_num = f.planted_episode
      AND TRIM(p2.foreshadowing_notes) = TRIM(f.description)
)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実際に削除する（既定は dry-run）")
    args = parser.parse_args()

    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        rows = conn.execute(text(SQL_SELECT)).fetchall()
        print(f"対象: {len(rows)} 件")
        for row in rows:
            print(f"  id={row[0]} book_id={row[1]} ep={row[2]} desc={row[3]!r}")
        if args.apply and rows:
            for row in rows:
                conn.execute(text("DELETE FROM foreshadowings WHERE id = :id"), {"id": row[0]})
            print(f"{len(rows)} 件を削除しました")
        elif rows:
            print("dry-run のため削除していません（--apply で実行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
