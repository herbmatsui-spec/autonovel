import io
import json
import logging
import zipfile
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_FALLBACK: dict[str, Any] = {
    "title": "R15ファンタジー作品",
    "genre": "ファンタジー (R15)",
    "chapters": [
        {
            "ep_num": 1,
            "title": "運命の覚醒",
            "content": (
                "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。"
                "刃が鈍い蒼光を放ち、彼の秘められた魔力が解き放たれる。"
                "（※R15: 軽度の戦闘・流血描写あり）"
            ),
        }
    ],
    "characters": [
        {
            "name": "アルト",
            "role": "主人公",
            "personality": "熱血・正義感が強い",
            "ability": "古代魔導剣術",
        }
    ],
    "plots": [
        {
            "ep_num": 1,
            "title": "運命の覚醒",
            "one_line_summary": "ダンジョンでの危機を乗り越え、秘められた真の力を覚醒させる。",
        }
    ],
    "bible_settings": {},
}


class MarketingAgent:
    """作品データ一式（本文、設定、プロット、JSONダンプ）のパッケージング・エクスポートを管轄するエージェント"""

    def __init__(self, repo: Any = None) -> None:
        self.repo = repo

    async def create_export_package(
        self,
        book_id: int,
        book_data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        """作品データ一式をZIPパッケージ化して返却する。

        repoが指定されている場合はDBから取得し、無ければ引数のbook_dataまたは
        フォールバックデータを使用する。
        """
        title = DEFAULT_FALLBACK["title"]
        genre = DEFAULT_FALLBACK["genre"]
        chapters: list[dict[str, Any]] = []
        characters: list[dict[str, Any]] = []
        plots: list[dict[str, Any]] = []
        bible_settings: dict[str, Any] = {}

        if self.repo:
            try:
                book = self.repo.get_book(book_id)
                if book:
                    logger.info(
                        "Export: book found in DB book_id=%s title=%s",
                        book_id,
                        getattr(book, "title", ""),
                    )
                    title = getattr(book, "title", title)
                    genre = getattr(book, "genre", genre)
                    branch_id = getattr(book, "current_branch_id", 1) or 1

                    db_chapters = self.repo.get_all_non_anchor_chapters(
                        book_id, branch_id=branch_id, order_by="ep_num"
                    )
                    chapters = [
                        {
                            "ep_num": getattr(c, "ep_num", i + 1),
                            "title": getattr(c, "title", f"第{i + 1}話"),
                            "content": getattr(c, "content", ""),
                        }
                        for i, c in enumerate(db_chapters)
                    ]

                    db_chars = self.repo.get_all_characters(book_id)
                    characters = [
                        {
                            "name": getattr(c, "name", "不明"),
                            "role": getattr(c, "role", "登場人物"),
                            "personality": getattr(c, "personality", "設定なし"),
                            "ability": getattr(c, "ability", "設定なし"),
                        }
                        for c in db_chars
                    ]

                    bible = self.repo.get_latest_bible(book_id)
                    if bible and hasattr(bible, "settings"):
                        bible_settings = bible.settings or {}

                    db_plots = self.repo.get_all_plots(book_id, branch_id=branch_id)
                    plots = [
                        {
                            "ep_num": getattr(p, "ep_num", i + 1),
                            "title": getattr(p, "title", ""),
                            "one_line_summary": getattr(p, "one_line_summary", ""),
                        }
                        for i, p in enumerate(db_plots)
                    ]
                else:
                    logger.info(
                        "Export: book not found in DB, using fallback data book_id=%s",
                        book_id,
                    )
            except Exception:
                logger.warning("DB fetch failed, using fallback", exc_info=True)

        if not chapters and book_data:
            title = book_data.get("title", title)
            genre = book_data.get("genre", genre)
            chapters = book_data.get("chapters", [])
            characters = book_data.get("characters", [])
            plots = book_data.get("plots", [])
            bible_settings = book_data.get("bible_settings", {})

        # デフォルトフォールバックデータ（かんたんモード等の単体実行時）
        if not chapters:
            chapters = DEFAULT_FALLBACK["chapters"]
        if not characters:
            characters = DEFAULT_FALLBACK["characters"]
        if not plots:
            plots = DEFAULT_FALLBACK["plots"]

        buf = io.BytesIO()
        try:
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                # 01: 本文
                full_text = f"■ 作品タイトル: {title}\n■ ジャンル・区分: {genre}\n\n"
                full_text += "".join(
                    f"第{c.get('ep_num', 1)}話 {c.get('title', '')}\n\n{c.get('content', '')}\n\n"
                    for c in chapters
                )
                z.writestr("01_本文.txt", full_text.encode("utf-8"))

                # 02: キャラクター・世界観設定集
                settings_str = (
                    json.dumps(bible_settings, ensure_ascii=False, indent=2)
                    if isinstance(bible_settings, dict)
                    else str(bible_settings)
                )
                setting_text = f"【世界観設定】\n{settings_str}\n\n【キャラクター設定】\n"
                for c in characters:
                    setting_text += (
                        f"■ {c.get('name', '')} ({c.get('role', '')})\n"
                        f"性格: {c.get('personality', '設定なし')}\n"
                        f"能力: {c.get('ability', '設定なし')}\n\n"
                    )
                z.writestr("02_キャラクター・世界観設定集.txt", setting_text.encode("utf-8"))

                # 03: プロット概要
                plot_text = f"【作品プロット概要】 - {title}\n\n"
                for p in plots:
                    plot_text += (
                        f"第{p.get('ep_num', 1)}話: {p.get('title', '')}\n"
                        f"{p.get('one_line_summary', '')}\n\n"
                    )
                z.writestr("03_プロット概要.txt", plot_text.encode("utf-8"))

                # 04: データダンプ (JSON)
                dump = {
                    "book_id": book_id,
                    "title": title,
                    "genre": genre,
                    "chapters": chapters,
                    "characters": characters,
                    "plots": plots,
                    "bible_settings": bible_settings,
                }
                z.writestr(
                    "04_データダンプ.json",
                    json.dumps(dump, ensure_ascii=False, indent=2).encode("utf-8"),
                )

        except (zipfile.BadZipFile, OSError) as e:
            logger.exception("ZIP creation failed")
            raise RuntimeError("Export package creation failed") from e

        zip_filename = f"export_{book_id}.zip"
        return buf.getvalue(), zip_filename
