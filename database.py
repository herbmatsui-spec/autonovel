from __future__ import annotations
"""
database.py - データベース管理モジュール
非同期SQLite (aiosqlite) によるデータ永続化レイヤー。
Repository パターンで全DB操作を集約。
"""
import re
import json
import logging
import time
import functools
import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import sqlite3
import streamlit as st

from config import BASE_DIR, DB_FILE
from models import (
    BookDbModel, BibleDbModel, PlotDbModel, ChapterDbModel, CharacterDbModel, WorldBible
)

logger = logging.getLogger(__name__)


# ==========================================
# リトライデコレータ
# ==========================================
def retry_with_logging(retries: int = 15, base_delay: float = 0.0, max_delay: float = 60.0): # max_delayを延長
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        logger.error(f"Final error in {func.__name__} after {retries} retries: {e}")
                        raise
                    delay = min(base_delay * (1.5 ** i), max_delay)
                    logger.warning(f"Retry {i+1}/{retries} in {func.__name__} after {delay:.1f}s due to: {e}")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator


# ==========================================
# WorkspaceManager（ファイルパス管理）
# ==========================================
class WorkspaceManager:
    """ディレクトリ構造とファイルパスを安全に管理する"""

    @staticmethod
    def get_path(filename: str) -> str:
        return str(BASE_DIR / filename)

    @staticmethod
    def list_backups() -> List[Path]:
        return sorted(BASE_DIR.glob("*.bak_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)

    @staticmethod
    def create_snapshot(db_path: str) -> str:
        """DBのスナップショット（バックアップ）を作成"""
        import shutil
        src = Path(db_path)
        if src.exists():
            dst = src.with_suffix(f".bak_{int(time.time())}.db")
            shutil.copy2(src, dst)
            logger.info(f"Snapshot created: {dst.name}")
            return str(dst)
        return ""


# ==========================================
# DatabaseManager（低レベルSQLite操作）
# ==========================================
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get_conn(self) -> aiosqlite.Connection:
        """スレッドセーフな運用のための接続生成"""
        conn = await aiosqlite.connect(self.db_path, timeout=90.0)
        await conn.execute(f"PRAGMA busy_timeout = 90000;")
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def start(self) -> None:
        """起動時の初期化を完全な同期処理に変更し、スレッドエラーを回避する"""
        conn = sqlite3.connect(self.db_path)
        try:
            schemas = {
                "books": "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, genre TEXT, concept TEXT, synopsis TEXT, target_eps INTEGER, style_dna TEXT, marketing_data TEXT, cumulative_stress INTEGER DEFAULT 0, created_at TEXT",
                "internal_state": "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT"
            }
            with conn:
                for table, definition in schemas.items():
                    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({definition});")
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS bible (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        book_id INTEGER, settings TEXT, revealed TEXT,
                        version INTEGER DEFAULT 0, last_updated TEXT,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS plot (
                        book_id INTEGER, ep_num INTEGER, title TEXT, summary TEXT,
                        thought_process TEXT DEFAULT '',
                        detailed_blueprint TEXT, tension INTEGER DEFAULT 50,
                        stress INTEGER DEFAULT 0, catharsis INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'planned', scenes TEXT,
                        is_catharsis BOOLEAN DEFAULT 0, catharsis_type TEXT DEFAULT 'なし',
                        love_meter INTEGER DEFAULT 0, next_hook TEXT,
                        misunderstanding_gap TEXT DEFAULT '',
                        lite_model_director_notes TEXT DEFAULT '',
                        current_chain_phase TEXT DEFAULT 'Hate',
                        script_content TEXT DEFAULT '',
                        resolution_style TEXT DEFAULT 'Cheat',
                        burned_cost_or_loot TEXT DEFAULT 'なし',
                        antagonist_status TEXT DEFAULT '現状維持',
                        thematic_milestone TEXT DEFAULT 'なし',
                        PRIMARY KEY(book_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS chapters (
                        book_id INTEGER, ep_num INTEGER, title TEXT, content TEXT,
                        score_story INTEGER, killer_phrase TEXT, summary TEXT,
                        world_state TEXT, trinity_review_log TEXT, ai_insight TEXT,
                        created_at TEXT,
                        PRIMARY KEY(book_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS characters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        book_id INTEGER, name TEXT, role TEXT, registry_data TEXT,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS optimization_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        book_id INTEGER,
                        report_json TEXT,
                        created_at TEXT,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS style_fragments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tag TEXT,
                        content TEXT,
                        embedding_json TEXT,
                        origin TEXT,
                        created_at TEXT
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS custom_styles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE,
                        instruction TEXT,
                        score INTEGER,
                        analysis TEXT,
                        created_at TEXT
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS internal_state (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT
                    );
                ''')
                # インデックス作成
                conn.execute('CREATE INDEX IF NOT EXISTS idx_plot_book_ep ON plot(book_id, ep_num);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_chapters_book_ep ON chapters(book_id, ep_num);')

                # マイグレーション
                self._ensure_schema_version_sync(conn)
        finally:
            conn.close()

    def _ensure_schema_version_sync(self, conn: sqlite3.Connection) -> None:
        """同期的なカラム追加マイグレーション"""
        target_cols = {
            "thought_process": "TEXT DEFAULT ''", "misunderstanding_gap": "TEXT DEFAULT ''",
            "lite_model_director_notes": "TEXT DEFAULT ''", "script_content": "TEXT DEFAULT ''",
            "current_chain_phase": "TEXT DEFAULT 'Hate'",
            "resolution_style": "TEXT DEFAULT 'Cheat'", "burned_cost_or_loot": "TEXT DEFAULT 'なし'",
            "antagonist_status": "TEXT DEFAULT '現状維持'", "thematic_milestone": "TEXT DEFAULT 'なし'"
        }
        cursor = conn.execute("PRAGMA table_info(plot);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        for col, col_def in target_cols.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE plot ADD COLUMN {col} {col_def};")

    async def execute(self, sql: str, params: tuple = ()) -> None:
        conn = await self.get_conn()
        try:
            await conn.execute(sql, params)
            await conn.commit()
        finally:
            await conn.close()

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Any]:
        conn = await self.get_conn()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(sql, params) as cursor:
                return await cursor.fetchone()
        finally:
            await conn.close()

    async def fetch_all(self, sql: str, params: tuple = ()) -> List[Any]:
        conn = await self.get_conn()
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(sql, params) as cursor:
                return await cursor.fetchall()
        finally:
            await conn.close()

    async def fetch_lastrowid(self, sql: str, params: tuple = ()) -> int:
        conn = await self.get_conn()
        try:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.lastrowid or 0
        finally:
            await conn.close()


# ==========================================
# グローバルDB取得（Streamlitキャッシュ）
# ==========================================
@st.cache_resource
def get_db_manager() -> DatabaseManager:
    db_path = WorkspaceManager.get_path(DB_FILE)
    manager = DatabaseManager(db_path)
    # 完全に同期的なメソッドとして初期化を実行。イベントループを汚染しない。
    manager.start()
    return manager


# ==========================================
# DataRepository（高レベルDB操作）
# ==========================================
class DataRepository:
    """DBモデルの CRUD を担当するリポジトリクラス"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    @staticmethod
    def _parse_row(row: Dict[str, Any], json_fields: List[str]) -> Dict[str, Any]:
        """Convert stored JSON strings to Python objects for fields that are
        expected to be complex types.  ``PlotDbModel`` stores ``next_hook`` and
        ``scenes`` as JSON strings, and the model's validator will ensure they are strings.
        Here, we deserialize them from the DB into Python objects.
        """
        for f in json_fields:
            if f in row and isinstance(row[f], str):
                try:
                    row[f] = json.loads(row[f])
                except (json.JSONDecodeError, TypeError):
                    pass
        return row

    # ---------- Books ----------
    @retry_with_logging()
    async def create_book(self, title: str, genre: str, concept: str, synopsis: str,
                          target_eps: int, style_dna: dict, marketing_data: dict) -> int:
        return await self.db.fetch_lastrowid(
            "INSERT INTO books (title, genre, concept, synopsis, target_eps, style_dna, marketing_data, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (title, genre, concept, synopsis, target_eps,
             json.dumps(style_dna, ensure_ascii=False),
             json.dumps(marketing_data, ensure_ascii=False),
             time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_book(self, book_id: int) -> Optional[BookDbModel]:
        row = await self.db.fetch_one("SELECT * FROM books WHERE id=?", (book_id,))
        if not row:
            return None
        d = self._parse_row(dict(row), ['style_dna', 'marketing_data'])
        return BookDbModel(**d)

    @retry_with_logging()
    async def get_all_books(self) -> List[BookDbModel]:
        rows = await self.db.fetch_all("SELECT * FROM books ORDER BY id DESC")
        return [BookDbModel(**self._parse_row(dict(r), ['style_dna', 'marketing_data'])) for r in rows]

    @retry_with_logging()
    async def update_book_cumulative_stress(self, book_id: int, stress: int) -> None:
        await self.db.execute("UPDATE books SET cumulative_stress=? WHERE id=?", (stress, book_id))

    @retry_with_logging()
    async def delete_book(self, book_id: int) -> None:
        await self.db.execute("DELETE FROM books WHERE id=?", (book_id,))

    # ---------- Bible ----------
    @retry_with_logging()
    async def create_bible(self, book_id: int, settings: Any, version: int, last_updated: str) -> None:
        await self.db.execute(
            "INSERT INTO bible (book_id, settings, version, last_updated) VALUES (?,?,?,?)",
            (book_id, json.dumps(settings, ensure_ascii=False) if not isinstance(settings, str) else settings,
             version, last_updated)
        )

    @retry_with_logging()
    async def get_latest_bible(self, book_id: int) -> Optional[BibleDbModel]:
        row = await self.db.fetch_one(
            "SELECT * FROM bible WHERE book_id=? ORDER BY id DESC LIMIT 1", (book_id,)
        )
        if not row:
            return None
        return BibleDbModel(**self._parse_row(dict(row), ['settings']))

    # ---------- Plots ----------
    @retry_with_logging()
    async def get_plot(self, book_id: int, ep_num: int) -> Optional[PlotDbModel]:
        row = await self.db.fetch_one("SELECT * FROM plot WHERE book_id=? AND ep_num=?", (book_id, ep_num))
        if not row:
            return None
        return PlotDbModel(**self._parse_row(dict(row), ['scenes', 'next_hook']))

    @retry_with_logging()
    async def get_all_plots(self, book_id: int) -> List[PlotDbModel]:
        rows = await self.db.fetch_all("SELECT * FROM plot WHERE book_id=? ORDER BY ep_num", (book_id,))
        return [PlotDbModel(**self._parse_row(dict(r), ['scenes', 'next_hook'])) for r in rows]

    @retry_with_logging()
    async def create_or_replace_plot(
        self, book_id: int, ep_num: int, thought_process: str, title: str, summary: str, detailed_blueprint: str,
        next_hook: str, tension: int, stress: int, catharsis: int, love_meter: int, is_catharsis: bool, catharsis_type: str,
        scenes: Any, status: str, misunderstanding_gap: str,
        lite_model_director_notes: str, script_content: str = "",
        current_chain_phase: str = "Hate",
        resolution_style: str = "Cheat", burned_cost_or_loot: str = "なし",
        antagonist_status: str = "現状維持", thematic_milestone: str = "なし"
    ) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO plot
               (book_id, ep_num, thought_process, title, summary, detailed_blueprint, next_hook, tension, stress, catharsis,
                love_meter, is_catharsis, catharsis_type, scenes, status,
                misunderstanding_gap, lite_model_director_notes, script_content, current_chain_phase,
                resolution_style, burned_cost_or_loot, antagonist_status, thematic_milestone)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (book_id, ep_num, thought_process, title, summary, detailed_blueprint,
             json.dumps(next_hook, ensure_ascii=False) if isinstance(next_hook, (dict, list)) else (next_hook or "{}"),
             tension, stress, catharsis,
             love_meter, is_catharsis, catharsis_type,
             json.dumps(scenes, ensure_ascii=False) if isinstance(scenes, (list, dict)) else (scenes or "[]"),
             status, misunderstanding_gap, lite_model_director_notes, script_content, current_chain_phase,
             resolution_style, burned_cost_or_loot, antagonist_status, thematic_milestone)
        )

    @retry_with_logging()
    async def update_plot_status_stress_love(self, book_id: int, ep_num: int, stress: int, love_meter: int) -> None:
        await self.db.execute(
            "UPDATE plot SET status='completed', stress=?, love_meter=? WHERE book_id=? AND ep_num=?",
            (stress, love_meter, book_id, ep_num)
        )

    @retry_with_logging()
    async def delete_plots_from(self, book_id: int, start_ep: int) -> None:
        await self.db.execute("DELETE FROM plot WHERE book_id=? AND ep_num >= ?", (book_id, start_ep))

    @retry_with_logging()
    async def save_full_world_bible(self, bible: WorldBible, **kwargs) -> int:
        """WorldBible オブジェクトとその構成要素を一括保存する（engine.pyより移譲）"""
        conn = await self.db.get_conn()
        try:
            await conn.execute("BEGIN")
            try:
                # style_dna にはスタイル設定のみを保存
                style_dna = json.dumps({"mode": bible.style_key}, ensure_ascii=False)
                mkt_data = json.dumps(bible.marketing_assets.model_dump(), ensure_ascii=False)
                
                cursor = await conn.execute(
                    "INSERT INTO books (title, genre, concept, synopsis, target_eps, style_dna, marketing_data, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (bible.title, bible.genre, bible.concept, bible.synopsis, kwargs.get("target_eps", 50), style_dna, mkt_data, time.strftime('%Y-%m-%dT%H:%M:%S'))
                )
                book_id = cursor.lastrowid

                ws_data = bible.world_settings.model_dump()
                ws_data.update({
                    "story_direction": bible.story_direction,
                    "dynamic_pacing_graph": [p.model_dump() for p in bible.dynamic_pacing_graph],
                    "villain_parallel_timeline": bible.villain_parallel_timeline,
                    "arcs": [a.model_dump() for a in bible.arcs],
                    "full_story_roadmap": [r.model_dump() for r in bible.full_story_roadmap]
                })

                await conn.execute(
                    "INSERT INTO bible (book_id, settings, version, last_updated) VALUES (?,?,?,?)",
                    (book_id, json.dumps(ws_data, ensure_ascii=False), 1, time.strftime('%Y-%m-%dT%H:%M:%S'))
                )
                
                chars = [(book_id, bible.mc_profile.name, "主人公", json.dumps(bible.mc_profile.model_dump(), ensure_ascii=False))]
                chars += [(book_id, s.name, s.role, json.dumps(s.model_dump(), ensure_ascii=False)) for s in bible.sub_characters]
                await conn.executemany("INSERT INTO characters (book_id, name, role, registry_data) VALUES (?,?,?,?)", chars)

                plot_data = [(book_id, ep, f"第{ep}話 (TBD)", "計画中...", "planned", "Hate") 
                             for ep in range(1, kwargs.get("target_eps", 50) + 1)]
                await conn.executemany(
                    "INSERT OR REPLACE INTO plot (book_id, ep_num, title, summary, status, current_chain_phase) VALUES (?,?,?,?,?,?)",
                    plot_data
                )
                await conn.commit()
                return book_id
            except Exception as e:
                await conn.rollback()
                logger.error(f"Failed to save full world bible: {e}")
                raise
        finally:
            await conn.close()

    @retry_with_logging()
    async def save_optimization_report(self, book_id: int, report: Dict[str, Any]) -> None:
        await self.db.execute(
            "INSERT INTO optimization_history (book_id, report_json, created_at) VALUES (?,?,?)",
            (book_id, json.dumps(report, ensure_ascii=False), time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_optimization_history(self, book_id: int) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all("SELECT * FROM optimization_history WHERE book_id=? ORDER BY created_at DESC", (book_id,))
        return [self._parse_row(dict(r), ['report_json']) for r in rows]

    # ---------- Style Fragments (RAG) ----------
    @retry_with_logging()
    async def add_style_fragment(self, tag: str, content: str, embedding: List[float], origin: str = "Master") -> None:
        await self.db.execute(
            "INSERT INTO style_fragments (tag, content, embedding_json, origin, created_at) VALUES (?,?,?,?,?)",
            (tag, content, json.dumps(embedding), origin, time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_all_style_fragments(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        if tag:
            rows = await self.db.fetch_all("SELECT * FROM style_fragments WHERE tag=?", (tag,))
        else:
            rows = await self.db.fetch_all("SELECT * FROM style_fragments")
        return [dict(r) for r in rows]

    @retry_with_logging()
    async def search_style_fragments_by_tag(self, tag: str, limit: int = 5) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            "SELECT * FROM style_fragments WHERE tag=? ORDER BY RANDOM() LIMIT ?", (tag, limit)
        )
        return [dict(r) for r in rows]

    # ---------- Chapters ----------
    @retry_with_logging()
    async def create_chapter(
        self, book_id: int, ep_num: int, title: str, content: str, summary: str,
        killer_phrase: Optional[str], ai_insight: str, world_state: Any,
        trinity_review_log: Any, created_at: str
    ) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO chapters
               (book_id, ep_num, title, content, summary, killer_phrase, ai_insight,
                world_state, trinity_review_log, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (book_id, ep_num, title, content, summary if isinstance(summary, str) else json.dumps(summary, ensure_ascii=False), killer_phrase, ai_insight,
             json.dumps(world_state, ensure_ascii=False) if isinstance(world_state, (dict, list)) else (world_state or "{}"),
             json.dumps(trinity_review_log, ensure_ascii=False) if isinstance(trinity_review_log, (dict, list)) else (trinity_review_log or "{}"),
             created_at)
        )

    @retry_with_logging()
    async def get_chapter(self, book_id: int, ep_num: int) -> Optional[ChapterDbModel]:
        row = await self.db.fetch_one("SELECT * FROM chapters WHERE book_id=? AND ep_num=?", (book_id, ep_num))
        if not row:
            return None
        return ChapterDbModel(**self._parse_row(dict(row), ['world_state', 'trinity_review_log', 'summary']))

    @retry_with_logging()
    async def get_chapters_before(self, book_id: int, ep_num: int) -> List[ChapterDbModel]:
        rows = await self.db.fetch_all(
            "SELECT * FROM chapters WHERE book_id=? AND ep_num<? ORDER BY ep_num DESC",
            (book_id, ep_num)
        )
        return [ChapterDbModel(**self._parse_row(dict(r), ['world_state', 'trinity_review_log', 'summary'])) for r in rows]

    @retry_with_logging()
    async def get_all_non_anchor_chapters(self, book_id: int, order_by: str = "ep_num") -> List[ChapterDbModel]:
        rows = await self.db.fetch_all(
            f"SELECT * FROM chapters WHERE book_id=? ORDER BY {order_by}", (book_id,)
        )
        return [ChapterDbModel(**self._parse_row(dict(r), ['world_state', 'trinity_review_log', 'summary'])) for r in rows]

    @retry_with_logging()
    async def delete_chapter(self, book_id: int, ep_num: int) -> None:
        await self.db.execute("DELETE FROM chapters WHERE book_id=? AND ep_num=?", (book_id, ep_num))

    # ---------- Characters ----------
    @retry_with_logging()
    async def get_all_characters(self, book_id: int) -> List[CharacterDbModel]:
        rows = await self.db.fetch_all("SELECT * FROM characters WHERE book_id=?", (book_id,))
        return [CharacterDbModel(**self._parse_row(dict(r), ['registry_data'])) for r in rows]

    @retry_with_logging()
    async def create_character(self, book_id: int, name: str, role: str, registry_data: Any) -> None:
        await self.db.execute(
            "INSERT INTO characters (book_id, name, role, registry_data) VALUES (?,?,?,?)",
            (book_id, name, role,
             json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data)
        )

    @retry_with_logging()
    async def update_character_registry(self, char_id: int, registry_data: Any) -> None:
        await self.db.execute(
            "UPDATE characters SET registry_data=? WHERE id=?",
            (json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data,
             char_id)
        )

    # ---------- Custom Styles ----------
    @retry_with_logging()
    async def save_custom_style(self, name: str, instruction: str, score: int, analysis: str) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO custom_styles (name, instruction, score, analysis, created_at) VALUES (?,?,?,?,?)",
            (name, instruction, score, analysis, time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_all_custom_styles(self) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all("SELECT * FROM custom_styles ORDER BY score DESC")
        return [dict(r) for r in rows]

    @retry_with_logging()
    async def delete_custom_style(self, style_id: int) -> None:
        await self.db.execute("DELETE FROM custom_styles WHERE id=?", (style_id,))

    # ---------- Internal State ----------
    @retry_with_logging()
    async def save_internal_state(self, key: str, value: Any) -> None:
        """ウィザードの下書きなどの内部状態を保存する"""
        await self.db.execute(
            "INSERT OR REPLACE INTO internal_state (key, value, updated_at) VALUES (?,?,?)",
            (key, json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value,
             time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_internal_state(self, key: str) -> Optional[Any]:
        """保存された内部状態を取得する"""
        row = await self.db.fetch_one("SELECT value FROM internal_state WHERE key=?", (key,))
        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        return None

    # ---------- 拡張クエリ ----------
    @retry_with_logging()
    async def get_plots_before_limit_1(self, book_id: int, ep_num: int) -> Optional[PlotDbModel]:
        """ep_num より前の最新プロットを1件取得（直前プロットの状態参照用）"""
        rows = await self.db.fetch_all(
            "SELECT * FROM plot WHERE book_id=? AND ep_num < ? ORDER BY ep_num DESC LIMIT 1",
            (book_id, ep_num)
        )
        return PlotDbModel(**self._parse_row(dict(rows[0]), ['scenes', 'next_hook'])) if rows else None

    @retry_with_logging()
    async def get_plots_between(self, book_id: int, start_ep: int, end_ep: int) -> List[PlotDbModel]:
        """start_ep〜end_ep の範囲のプロットを取得"""
        rows = await self.db.fetch_all(
            "SELECT * FROM plot WHERE book_id=? AND ep_num BETWEEN ? AND ? ORDER BY ep_num",
            (book_id, start_ep, end_ep)
        )
        return [PlotDbModel(**self._parse_row(dict(r), ['scenes', 'next_hook'])) for r in rows]

    @retry_with_logging()
    async def update_book_target_eps(self, book_id: int, new_total_eps: int) -> None:
        """作品の目標話数を更新する"""
        await self.db.execute("UPDATE books SET target_eps=? WHERE id=?", (new_total_eps, book_id))

    async def get_relevant_past_logs(
        self,
        book_id: int,
        current_ep: int,
        query_text: str = "",
        top_k: int = 5,
    ) -> str:
        """
        【強化版RAG機能】現在のプロットに含まれるキーワードに基づき、過去の重要ログを抽出する。
        """
        if not query_text: return ""
        # 簡易キーワード抽出
        keywords = re.findall(r'[一-龠々]{2,}|[ァ-ヶー]{2,}', query_text)
        if not keywords: return ""
        
        # キーワードを含む過去のチャプターを検索
        clauses = ["content LIKE ?" for _ in keywords[:5]]
        params = [f"%{k}%" for k in keywords[:5]]
        sql = f"SELECT ep_num, ai_insight, summary FROM chapters WHERE book_id=? AND ep_num < ? AND ({' OR '.join(clauses)}) ORDER BY ep_num DESC LIMIT ?"
        rows = await self.db.fetch_all(sql, (book_id, current_ep, *params, top_k))
        
        if not rows: return ""
        
        res = "【過去の関連文脈（RAG）】\n"
        for r in rows:
            res += f"- 第{r['ep_num']}話: {r['summary']} (重要事項: {r['ai_insight']})\n"
        return res
