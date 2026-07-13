from __future__ import annotations

"""
database.py - データベース管理モジュール
非同期SQLite (aiosqlite) によるデータ永続化レイヤー。
Repository パターンで全DB操作を集約。

[Cache-Bust: 2026-05-19 06:10 - Force Bytecode Recompilation]
"""
import asyncio
import functools
import json
import logging
import re
import shutil
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from config import BASE_DIR, DB_FILE
from models import (
    BibleDbModel,
    BookDbModel,
    BranchDbModel,
    ChapterDbModel,
    CharacterDbModel,
    PlotDbModel,
    WorldBible,
)

logger = logging.getLogger(__name__)


# ==========================================
# リトライデコレータ
# ==========================================
def retry_with_logging(retries: int = 15, base_delay: float = 0.1, max_delay: float = 60.0): # max_delayを延長
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (aiosqlite.Error, sqlite3.Error, OSError, asyncio.TimeoutError) as e:
                    if i == retries - 1:
                        logger.error(f"Final error in {func.__name__} after {retries} retries: {e}\n{traceback.format_exc()}")
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
        # Ensure aiosqlite connection is tied to the current thread's event loop
        # This is crucial for background tasks running in separate threads with their own loops
        conn = await aiosqlite.connect(self.db_path, timeout=10.0)
        await conn.execute("PRAGMA busy_timeout = 10000;")
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def start(self, retry_count: int = 0) -> None:
        """起動時の初期化を完全な同期処理に変更し、スレッドエラーを回避する"""
        if retry_count > 5:
            logger.error("Maximum database initialization retries exceeded. Database state is invalid.")
            raise RuntimeError("Database initialization failed after maximum retries.")

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # マイグレーション中は外部キー制約を一時的にオフにする（テーブル再構築のため）
            conn.execute("PRAGMA foreign_keys=OFF;")
            schemas = {
                "books": "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, genre TEXT, concept TEXT, synopsis TEXT, target_eps INTEGER, style_dna TEXT, marketing_data TEXT, cumulative_stress INTEGER DEFAULT 0, cumulative_qol INTEGER DEFAULT 0, cumulative_cost REAL DEFAULT 0.0, sanctuary_integrity INTEGER DEFAULT 100, current_branch_id INTEGER, created_at TEXT",
                "internal_state": "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT"
            }
            with conn:
                for table, definition in schemas.items():
                    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({definition});")

                # 他のテーブルも同様に作成
                conn.execute('CREATE TABLE IF NOT EXISTS bible (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER, settings TEXT, revealed TEXT, version INTEGER DEFAULT 0, last_updated TEXT, FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE);')
                conn.execute('CREATE TABLE IF NOT EXISTS branches (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER, name TEXT, parent_id INTEGER, fork_ep_num INTEGER DEFAULT 0, created_at TEXT, FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE);')

                # plot/chapters は branch_id を含む新しい定義で作成を試みる
                # (既に存在する場合は無視されるため、その後の _ensure_schema_version_sync でマイグレーションされる)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS plot (
                        book_id INTEGER, branch_id INTEGER DEFAULT 1, ep_num INTEGER, title TEXT, summary TEXT,
                        thought_process TEXT DEFAULT '', detailed_blueprint TEXT, tension INTEGER DEFAULT 50,
                        stress INTEGER DEFAULT 0, catharsis INTEGER DEFAULT 0, status TEXT DEFAULT 'planned',
                        scenes TEXT, is_catharsis BOOLEAN DEFAULT 0, catharsis_type TEXT DEFAULT 'なし',
                        love_meter INTEGER DEFAULT 0, next_hook TEXT, misunderstanding_gap TEXT DEFAULT '',
                        lite_model_director_notes TEXT DEFAULT '', current_chain_phase TEXT DEFAULT 'Hate',
                        script_content TEXT DEFAULT '', resolution_style TEXT DEFAULT 'Cheat',
                        burned_cost_or_loot TEXT DEFAULT 'なし', antagonist_status TEXT DEFAULT '現状維持',
                        thematic_milestone TEXT DEFAULT 'なし',
                        state_integrity_score INTEGER DEFAULT 100,
                        healed_fields TEXT,
                        is_micro_catharsis BOOLEAN DEFAULT 0,
                        information_asymmetry_level REAL DEFAULT 0.0,
                        cost_score REAL DEFAULT 0.0,
                        qol_delta INTEGER DEFAULT 0,
                        discovery_item TEXT,
                        sanctuary_event TEXT,
                        PRIMARY KEY(branch_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS chapters (
                        book_id INTEGER, branch_id INTEGER DEFAULT 1, ep_num INTEGER, title TEXT, content TEXT,
                        score_story INTEGER, killer_phrase TEXT, summary TEXT,
                        world_state TEXT, trinity_review_log TEXT, ai_insight TEXT,
                        created_at TEXT, stress_delta INTEGER DEFAULT 0,
                        qol_delta INTEGER DEFAULT 0,
                        PRIMARY KEY(branch_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                # その他テーブル...
                conn.execute('CREATE TABLE IF NOT EXISTS characters (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER, name TEXT, role TEXT, registry_data TEXT, FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE);')
                conn.execute('CREATE TABLE IF NOT EXISTS optimization_history (id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER, report_json TEXT, created_at TEXT, FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE);')
                conn.execute('CREATE TABLE IF NOT EXISTS style_fragments (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT, content TEXT, embedding_json TEXT, origin TEXT, created_at TEXT);')
                conn.execute('CREATE TABLE IF NOT EXISTS custom_styles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, instruction TEXT, score INTEGER, analysis TEXT, created_at TEXT);')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS pending_patches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        book_id INTEGER,
                        patch_type TEXT,
                        patch_content TEXT,
                        ab_test_result TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT,
                        reviewed_at TEXT,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')

                # マイグレーション実行 (カラムの追加やテーブル再構築を先に行う)
                self._ensure_schema_version_sync(conn)

                # インデックス作成 (カラムが存在することが保証された後で行う)
                conn.execute('CREATE INDEX IF NOT EXISTS idx_plot_branch_ep ON plot(branch_id, ep_num);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_chapters_branch_ep ON chapters(branch_id, ep_num);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_branches_book ON branches(book_id);')

            # 制約を戻す
            conn.execute("PRAGMA foreign_keys=ON;")
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            err_msg = str(e).lower()
            if "malformed" in err_msg or "corrupt" in err_msg or "i/o error" in err_msg:
                logger.error(f"Database corruption detected: {e}. Attempting recovery...")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass

                corrupted_path = f"{self.db_path}.corrupt_{int(time.time())}"
                try:
                    if Path(self.db_path).exists():
                        shutil.move(self.db_path, corrupted_path)
                        logger.info(f"Moved corrupted DB to {corrupted_path}")

                    for suffix in ["-wal", "-shm", "-journal"]:
                        sidecar = f"{self.db_path}{suffix}"
                        if Path(sidecar).exists():
                            try:
                                shutil.move(sidecar, f"{corrupted_path}{suffix}")
                                logger.info(f"Moved sidecar file: {sidecar}")
                            except OSError as side_e:
                                logger.warning(f"Could not move {sidecar}: {side_e}\n{traceback.format_exc()}")
                except OSError as move_e:
                    logger.error(f"Critical failure during DB recovery: {move_e}\n{traceback.format_exc()}")

                # Retry initialization
                self.start(retry_count=retry_count + 1)
            elif "lock" in err_msg or "busy" in err_msg or "timeout" in err_msg:
                logger.warning(f"Database locked or busy: {e}. Retrying initialization ({retry_count + 1}/5)...")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                time.sleep(1.0)
                self.start(retry_count=retry_count + 1)
            else:
                logger.exception("Database initialization failed due to an operational error")
                raise e
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def _ensure_schema_version_sync(self, conn: sqlite3.Connection) -> None:
        """同期的なカラム追加・テーブル再構築マイグレーション"""
        try:
            # 1. books table
            cursor = conn.execute("PRAGMA table_info(books);")
            current_books_cols = {row[1] for row in cursor.fetchall()}
            if "current_branch_id" not in current_books_cols:
                conn.execute("ALTER TABLE books ADD COLUMN current_branch_id INTEGER;")
            if "cumulative_qol" not in current_books_cols:
                conn.execute("ALTER TABLE books ADD COLUMN cumulative_qol INTEGER DEFAULT 0;")
            if "cumulative_cost" not in current_books_cols:
                conn.execute("ALTER TABLE books ADD COLUMN cumulative_cost REAL DEFAULT 0.0;")
            if "sanctuary_integrity" not in current_books_cols:
                conn.execute("ALTER TABLE books ADD COLUMN sanctuary_integrity INTEGER DEFAULT 100;")

            # 2. 初期ブランチの作成（データ移行の前に必要）
            cursor = conn.execute("SELECT id FROM books")
            books = cursor.fetchall()
            for (book_id,) in books:
                cursor = conn.execute("SELECT id FROM branches WHERE book_id=? AND name='Main'", (book_id,))
                if not cursor.fetchone():
                    conn.execute("INSERT INTO branches (book_id, name, created_at) VALUES (?, 'Main', ?)", (book_id, time.strftime('%Y-%m-%dT%H:%M:%S')))
                    new_branch_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute("UPDATE books SET current_branch_id=? WHERE id=?", (new_branch_id, book_id))
                else:
                    cursor = conn.execute("SELECT id FROM branches WHERE book_id=? AND name='Main'", (book_id,))
                    b_id = cursor.fetchone()[0]
                    conn.execute("UPDATE books SET current_branch_id=? WHERE id=? AND current_branch_id IS NULL", (b_id, book_id))

            # 3. plot table migration
            cursor = conn.execute("PRAGMA table_info(plot);")
            existing_cols_plot = {row[1] for row in cursor.fetchall()}
            if "branch_id" not in existing_cols_plot:
                logger.info("Migrating 'plot' table...")
                conn.execute("ALTER TABLE plot RENAME TO plot_old;")
                conn.execute('''
                    CREATE TABLE plot (
                        book_id INTEGER, branch_id INTEGER DEFAULT 1, ep_num INTEGER, title TEXT, summary TEXT,
                        thought_process TEXT DEFAULT '', detailed_blueprint TEXT, tension INTEGER DEFAULT 50,
                        stress INTEGER DEFAULT 0, catharsis INTEGER DEFAULT 0, status TEXT DEFAULT 'planned',
                        scenes TEXT, is_catharsis BOOLEAN DEFAULT 0, catharsis_type TEXT DEFAULT 'なし',
                        love_meter INTEGER DEFAULT 0, next_hook TEXT, misunderstanding_gap TEXT DEFAULT '',
                        lite_model_director_notes TEXT DEFAULT '', current_chain_phase TEXT DEFAULT 'Hate',
                        script_content TEXT DEFAULT '', resolution_style TEXT DEFAULT 'Cheat',
                        burned_cost_or_loot TEXT DEFAULT 'なし', antagonist_status TEXT DEFAULT '現状維持',
                        thematic_milestone TEXT DEFAULT 'なし',
                        state_integrity_score INTEGER DEFAULT 100,
                        healed_fields TEXT,
                        is_micro_catharsis BOOLEAN DEFAULT 0,
                        information_asymmetry_level REAL DEFAULT 0.0,
                            cost_score REAL DEFAULT 0.0,
                            qol_delta INTEGER DEFAULT 0,
                            discovery_item TEXT,
                            sanctuary_event TEXT,
                        PRIMARY KEY(branch_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                cursor = conn.execute("PRAGMA table_info(plot_old);")
                old_cols = [row[1] for row in cursor.fetchall()]
                new_cols = ["book_id", "ep_num", "title", "summary", "thought_process", "detailed_blueprint", "tension", "stress", "catharsis", "status", "scenes", "is_catharsis", "catharsis_type", "love_meter", "next_hook", "misunderstanding_gap", "lite_model_director_notes", "current_chain_phase", "script_content", "resolution_style", "burned_cost_or_loot", "antagonist_status", "thematic_milestone", "state_integrity_score", "healed_fields", "is_micro_catharsis", "information_asymmetry_level", "cost_score", "qol_delta", "discovery_item", "sanctuary_event"]
                valid_cols = [c for c in new_cols if c in old_cols]
                col_str = ", ".join(valid_cols)
                conn.execute(f"""
                    INSERT INTO plot ({col_str}, branch_id)
                    SELECT {", ".join(["p."+c for c in valid_cols])}, b.id
                    FROM plot_old p
                    JOIN branches b ON p.book_id = b.book_id
                    WHERE b.name = 'Main';
                """)
                conn.execute("DROP TABLE plot_old;")
            else:
                # branch_idはあるが、他の新設カラムが欠落している場合の個別のカラム追加
                cursor = conn.execute("PRAGMA table_info(plot);")
                current_cols = {row[1] for row in cursor.fetchall()}
                target_cols = {
                    "misunderstanding_gap": "TEXT DEFAULT ''",
                    "lite_model_director_notes": "TEXT DEFAULT ''",
                    "current_chain_phase": "TEXT DEFAULT 'Hate'",
                    "script_content": "TEXT DEFAULT ''",
                    "resolution_style": "TEXT DEFAULT 'Cheat'",
                    "burned_cost_or_loot": "TEXT DEFAULT 'なし'",
                    "antagonist_status": "TEXT DEFAULT '現状維持'",
                    "thematic_milestone": "TEXT DEFAULT 'なし'",
                    "state_integrity_score": "INTEGER DEFAULT 100",
                    "healed_fields": "TEXT",
                    "is_micro_catharsis": "BOOLEAN DEFAULT 0",
                    "information_asymmetry_level": "REAL DEFAULT 0.0",
                    "cost_score": "REAL DEFAULT 0.0",
                    "qol_delta": "INTEGER DEFAULT 0",
                    "discovery_item": "TEXT",
                    "sanctuary_event": "TEXT"
                }
                for col, col_def in target_cols.items():
                    if col not in current_cols:
                        logger.info(f"Adding missing column to plot: {col}")
                        conn.execute(f"ALTER TABLE plot ADD COLUMN {col} {col_def};")

            # 4. chapters table migration
            cursor = conn.execute("PRAGMA table_info(chapters);")
            existing_cols_chapters = {row[1] for row in cursor.fetchall()}
            if "branch_id" not in existing_cols_chapters:
                logger.info("Migrating 'chapters' table...")
                conn.execute("ALTER TABLE chapters RENAME TO chapters_old;")
                conn.execute('''
                    CREATE TABLE chapters (
                        book_id INTEGER, branch_id INTEGER DEFAULT 1, ep_num INTEGER, title TEXT, content TEXT,
                        score_story INTEGER, killer_phrase TEXT, summary TEXT,
                        world_state TEXT, trinity_review_log TEXT, ai_insight TEXT,
                        created_at TEXT, stress_delta INTEGER DEFAULT 0,
                            qol_delta INTEGER DEFAULT 0,
                        PRIMARY KEY(branch_id, ep_num),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    );
                ''')
                cursor = conn.execute("PRAGMA table_info(chapters_old);")
                old_cols = [row[1] for row in cursor.fetchall()]
                new_cols = ["book_id", "ep_num", "title", "content", "score_story", "killer_phrase", "summary", "world_state", "trinity_review_log", "ai_insight", "created_at", "stress_delta", "qol_delta"]
                valid_cols = [c for c in new_cols if c in old_cols]
                col_str = ", ".join(valid_cols)
                conn.execute(f"""
                    INSERT INTO chapters ({col_str}, branch_id)
                    SELECT {", ".join(["c."+col for col in valid_cols])}, b.id
                    FROM chapters_old c
                    JOIN branches b ON c.book_id = b.book_id
                    WHERE b.name = 'Main';
                """)
                conn.execute("DROP TABLE chapters_old;")
            else:
                cursor = conn.execute("PRAGMA table_info(chapters);")
                current_cols = {row[1] for row in cursor.fetchall()}
                if "stress_delta" not in current_cols:
                    conn.execute("ALTER TABLE chapters ADD COLUMN stress_delta INTEGER DEFAULT 0;")
                if "qol_delta" not in current_cols:
                    conn.execute("ALTER TABLE chapters ADD COLUMN qol_delta INTEGER DEFAULT 0;")

        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            err_msg = str(e).lower()
            if "malformed" in err_msg or "corrupt" in err_msg or "readonly" in err_msg:
                # 破損エラーは上位の start() で処理させるため、ここでは例外をそのまま投げる
                raise e
            logger.exception("Schema migration failed due to a structural error")
            raise e
        except Exception as e:
            logger.exception("Schema migration failed due to an unexpected error")
            raise e

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
def _get_cached_db_manager(db_path: str) -> DatabaseManager:
    """Streamlit用のモジュールレベルキャッシュ関数"""
    manager = DatabaseManager(db_path)
    manager.start()
    return manager


def get_db_manager() -> DatabaseManager:
    """
    DBマネージャーを取得。
    Streamlit実行時はキャッシュを利用し、テスト環境等では警告を抑制して直接生成する。
    """
    db_path = WorkspaceManager.get_path(DB_FILE)

    # Streamlitコンテキストがある場合のみキャッシュを適用
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        # get_script_run_ctx() を呼び出す前に、engine.py での抑制が効くよう配置
        ctx = get_script_run_ctx()
        if ctx:
            return _get_cached_db_manager(db_path)
    except (ImportError, RuntimeError):
        pass

    manager = DatabaseManager(db_path)
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

    # ---------- Branches ----------
    @retry_with_logging()
    async def create_branch(self, book_id: int, name: str, parent_id: Optional[int] = None, fork_ep_num: int = 0) -> int:
        """新しいブランチを作成し、必要に応じて親ブランチからデータをコピーする"""
        branch_id = await self.db.fetch_lastrowid(
            "INSERT INTO branches (book_id, name, parent_id, fork_ep_num, created_at) VALUES (?,?,?,?,?)",
            (book_id, name, parent_id, fork_ep_num, time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

        # 親ブランチがある場合、指定された話数までのプロットとチャプターをコピーする（スナップショット）
        if parent_id and fork_ep_num > 0:
            # プロットのコピー
            await self.db.execute(
                """INSERT INTO plot (book_id, branch_id, ep_num, title, summary, thought_process, detailed_blueprint, 
                                     tension, stress, catharsis, status, scenes, is_catharsis, catharsis_type, 
                                     love_meter, next_hook, misunderstanding_gap, lite_model_director_notes, 
                                     current_chain_phase, script_content, resolution_style, burned_cost_or_loot, 
                                     antagonist_status, thematic_milestone, state_integrity_score, healed_fields,
                                     is_micro_catharsis, information_asymmetry_level, cost_score)
                   SELECT book_id, ?, ep_num, title, summary, thought_process, detailed_blueprint, 
                          tension, stress, catharsis, status, scenes, is_catharsis, catharsis_type, 
                          love_meter, next_hook, misunderstanding_gap, lite_model_director_notes, 
                          current_chain_phase, script_content, resolution_style, burned_cost_or_loot, 
                          antagonist_status, thematic_milestone, state_integrity_score, healed_fields,
                          is_micro_catharsis, information_asymmetry_level, cost_score 
                   FROM plot WHERE branch_id=? AND ep_num<=?""",
                (branch_id, parent_id, fork_ep_num)
            )
            # チャプターのコピー
            await self.db.execute(
                """INSERT INTO chapters (book_id, branch_id, ep_num, title, content, score_story, killer_phrase, 
                                         summary, world_state, trinity_review_log, ai_insight, created_at, stress_delta)
                   SELECT book_id, ?, ep_num, title, content, score_story, killer_phrase, 
                          summary, world_state, trinity_review_log, ai_insight, created_at, stress_delta 
                   FROM chapters WHERE branch_id=? AND ep_num<=?""",
                (branch_id, parent_id, fork_ep_num)
            )
        return branch_id

    @retry_with_logging()
    async def get_branches(self, book_id: int) -> List[BranchDbModel]:
        rows = await self.db.fetch_all("SELECT * FROM branches WHERE book_id=? ORDER BY created_at", (book_id,))
        return [BranchDbModel(**dict(r)) for r in rows]

    @retry_with_logging()
    async def update_book_current_branch(self, book_id: int, branch_id: int) -> None:
        await self.db.execute("UPDATE books SET current_branch_id=? WHERE id=?", (branch_id, book_id))

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
    async def get_plot(self, book_id_or_branch_id: int, ep_num: int, branch_id: Optional[int] = None) -> Optional[PlotDbModel]:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        row = await self.db.fetch_one("SELECT * FROM plot WHERE branch_id=? AND ep_num=?", (target_branch_id, ep_num))
        if not row:
            return None
        return PlotDbModel(**self._parse_row(dict(row), ['scenes', 'next_hook', 'healed_fields']))

    @retry_with_logging()
    async def get_all_plots(self, book_id_or_branch_id: int, branch_id: Optional[int] = None) -> List[PlotDbModel]:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        rows = await self.db.fetch_all("SELECT * FROM plot WHERE branch_id=? ORDER BY ep_num", (target_branch_id,))
        return [PlotDbModel(**self._parse_row(dict(r), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for r in rows]

    @retry_with_logging()
    async def create_or_replace_plot(
        self, book_id: int, ep_num: int, thought_process: str, title: str, summary: str, detailed_blueprint: str,
        next_hook: str, tension: int, stress: int, catharsis: int, love_meter: int, is_catharsis: bool, catharsis_type: str,
        scenes: Any, status: str, misunderstanding_gap: str,
        lite_model_director_notes: str, script_content: str = "",
        current_chain_phase: str = "Hate",
        resolution_style: str = "Cheat", burned_cost_or_loot: str = "なし",
        antagonist_status: str = "現状維持", thematic_milestone: str = "なし",
        state_integrity_score: int = 100, healed_fields: Any = None, branch_id: int = 1,
        is_micro_catharsis: bool = False, information_asymmetry_level: float = 0.0,
        cost_score: float = 0.0,
        qol_delta: int = 0, discovery_item: str = "", sanctuary_event: str = ""
    ) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO plot
               (book_id, branch_id, ep_num, thought_process, title, summary, detailed_blueprint, next_hook, tension, stress, catharsis,
                love_meter, is_catharsis, catharsis_type, scenes, status,
                misunderstanding_gap, lite_model_director_notes, script_content, current_chain_phase,
                resolution_style, burned_cost_or_loot, antagonist_status, thematic_milestone,
                state_integrity_score, healed_fields, is_micro_catharsis, information_asymmetry_level,
                cost_score, qol_delta, discovery_item, sanctuary_event)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (book_id, branch_id, ep_num, thought_process, title, summary, detailed_blueprint,
             json.dumps(next_hook, ensure_ascii=False) if isinstance(next_hook, (dict, list)) else (next_hook or "{}"),
             tension, stress, catharsis,
             love_meter, is_catharsis, catharsis_type,
             json.dumps(scenes, ensure_ascii=False) if isinstance(scenes, (list, dict)) else (scenes or "[]"),
             status, misunderstanding_gap, lite_model_director_notes, script_content, current_chain_phase,
             resolution_style, burned_cost_or_loot, antagonist_status, thematic_milestone,
             state_integrity_score,
             json.dumps(healed_fields, ensure_ascii=False) if isinstance(healed_fields, list) else (healed_fields or "[]"),
             1 if is_micro_catharsis else 0,
             information_asymmetry_level,
             cost_score,
             qol_delta, discovery_item, sanctuary_event)
        )

    @retry_with_logging()
    async def save_plot(self, branch_id: int, ep_num: int, plot: Any) -> None:
        """
        Pydanticモデル（PlotEpisode）をデータベースのplotテーブルに一括登録/更新する。
        """
        row = await self.db.fetch_one("SELECT book_id FROM branches WHERE id=?", (branch_id,))
        if not row:
            latest_book = await self.db.fetch_one("SELECT id FROM books ORDER BY id DESC LIMIT 1")
            if latest_book:
                book_id = latest_book[0]
            else:
                raise ValueError(f"Branch with ID {branch_id} does not exist and no books found.")
        else:
            book_id = row[0]

        next_hook_data = {}
        if hasattr(plot, "next_hook") and plot.next_hook:
            if hasattr(plot.next_hook, "model_dump"):
                next_hook_data = plot.next_hook.model_dump()
            elif isinstance(plot.next_hook, dict):
                next_hook_data = plot.next_hook
            else:
                next_hook_data = {"type": getattr(plot.next_hook, "type", ""), "description": getattr(plot.next_hook, "description", "")}

        scenes_data = []
        if hasattr(plot, "scenes") and plot.scenes:
            for s in plot.scenes:
                if hasattr(s, "model_dump"):
                    scenes_data.append(s.model_dump())
                elif isinstance(s, dict):
                    scenes_data.append(s)

        healed_fields_data = []
        if hasattr(plot, "healed_fields") and plot.healed_fields:
            healed_fields_data = list(plot.healed_fields)

        await self.create_or_replace_plot(
            book_id=book_id,
            ep_num=ep_num,
            thought_process=getattr(plot, "thought_process", "") or "",
            title=getattr(plot, "title", "") or f"第{ep_num}話",
            summary=getattr(plot, "one_line_summary", "") or "",
            detailed_blueprint=getattr(plot, "detailed_blueprint", "") or "",
            next_hook=next_hook_data,
            tension=int(getattr(plot, "tension", 50) or 50),
            stress=int(getattr(plot, "stress", 0) or 0),
            catharsis=int(getattr(plot, "catharsis", 0) or 0),
            love_meter=int(getattr(plot, "love_meter", 0) or 0),
            is_catharsis=bool(getattr(plot, "is_catharsis", False)),
            catharsis_type=getattr(plot, "catharsis_type", "なし") or "なし",
            scenes=scenes_data,
            status=getattr(plot, "status", "expanded") or "expanded",
            misunderstanding_gap=getattr(plot, "misunderstanding_gap", "") or "",
            lite_model_director_notes=getattr(plot, "lite_model_director_notes", "") or "",
            script_content=getattr(plot, "script_content", "") or "",
            current_chain_phase=getattr(plot, "current_chain_phase", "Hate") or "Hate",
            resolution_style=getattr(plot, "resolution_style", "Cheat") or "Cheat",
            burned_cost_or_loot=str(getattr(plot, "burned_cost_or_loot", "なし") or "なし"),
            antagonist_status=getattr(plot, "antagonist_status", "現状維持") or "現状維持",
            thematic_milestone=getattr(plot, "thematic_milestone", "なし") or "なし",
            state_integrity_score=int(getattr(plot, "state_integrity_score", 100) or 100),
            healed_fields=healed_fields_data,
            branch_id=branch_id,
            is_micro_catharsis=bool(getattr(plot, "is_micro_catharsis", False)),
            information_asymmetry_level=float(getattr(plot, "information_asymmetry_level", 0.0) or 0.0),
            cost_score=float(getattr(plot, "cost_score", 0.0) or 0.0),
            qol_delta=int(getattr(plot, "qol_delta", 0) or 0),
            discovery_item=getattr(plot, "discovery_item", "") or "",
            sanctuary_event=getattr(plot, "sanctuary_event", "") or ""
        )

    @retry_with_logging()
    async def update_plot_status_stress_love(self, branch_id: int, ep_num: int, stress: int, love_meter: int) -> None:
        await self.db.execute(
            "UPDATE plot SET status='completed', stress=?, love_meter=? WHERE branch_id=? AND ep_num=?",
            (stress, love_meter, branch_id, ep_num)
        )

    @retry_with_logging()
    async def reset_plot_status(self, branch_id: int, ep_num: int) -> None:
        """プロットのステータスを計画済みに戻し、設計図や個別統計を完全にリセットする"""
        await self.db.execute(
            """UPDATE plot SET 
               status='planned', stress=0, love_meter=0, 
               detailed_blueprint='', thought_process='', 
               script_content='', scenes='[]'
               WHERE branch_id=? AND ep_num=?""",
            (branch_id, ep_num)
        )

    @retry_with_logging()
    async def update_plot_blueprint(self, branch_id: int, ep_num: int, detailed_blueprint: str) -> None:
        """プロットの設計図を直接更新する"""
        await self.db.execute(
            "UPDATE plot SET detailed_blueprint=? WHERE branch_id=? AND ep_num=?",
            (detailed_blueprint, branch_id, ep_num)
        )


    @retry_with_logging()
    async def delete_plots_from(self, branch_id: int, start_ep: int) -> None:
        await self.db.execute("DELETE FROM plot WHERE branch_id=? AND ep_num >= ?", (branch_id, start_ep))

    @retry_with_logging()
    async def update_book_marketing_data(self, book_id: int, title: str, marketing_data: Dict[str, Any]) -> None:
        """作品名とマーケティングデータを更新する。既存のデータがある場合はマージを試みる。"""
        # 最新のデータを取得
        row = await self.db.fetch_one("SELECT marketing_data FROM books WHERE id=?", (book_id,))
        current_data = {}
        if row and row[0]:
            try:
                current_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse marketing_data JSON: {e}\n{traceback.format_exc()}")

        # 既存のデータをベースに新しいデータを上書き
        merged = {**current_data, **marketing_data}

        await self.db.execute(
            "UPDATE books SET title=?, marketing_data=? WHERE id=?",
            (title, json.dumps(merged, ensure_ascii=False), book_id)
        )

    @retry_with_logging()
    async def save_full_world_bible(self, bible: WorldBible, **kwargs) -> int:
        """WorldBible オブジェクトとその構成要素を一括保存する。book_id が指定されている場合は更新を行う。"""
        conn = await self.db.get_conn()
        book_id = kwargs.get("book_id")
        branch_id = 1
        try:
            await conn.execute("BEGIN")
            try:
                style_dna = json.dumps({"mode": bible.style_key}, ensure_ascii=False)
                mkt_data = json.dumps(bible.marketing_assets.model_dump(), ensure_ascii=False)

                if book_id:
                    # 既存のブックを更新（マーケティングデータはマージして保護）
                    row = await conn.execute("SELECT marketing_data FROM books WHERE id=?", (book_id,))
                    old_row = await row.fetchone()
                    current_mkt = {}
                    if old_row and old_row[0]:
                        try:
                            current_mkt = json.loads(old_row[0])
                        except:
                            pass

                    # 新しいデータを生成
                    new_mkt = bible.marketing_assets.model_dump()

                    # ユーザーが編集した可能性のある項目（tags, catchcopies）は、
                    # 既存にデータがあればそれを優先、なければ新生成を使用する。
                    merged_mkt = {
                        "catchcopies": current_mkt.get("catchcopies") if current_mkt.get("catchcopies") else new_mkt.get("catchcopies"),
                        "tags": current_mkt.get("tags") if current_mkt.get("tags") else new_mkt.get("tags"),
                        "ab_test_candidates": new_mkt.get("ab_test_candidates") # テスト案は最新を維持
                    }
                    mkt_data = json.dumps(merged_mkt, ensure_ascii=False)

                    row_b = await conn.execute("SELECT current_branch_id FROM books WHERE id=?", (book_id,))
                    res_b = await row_b.fetchone()
                    branch_id = res_b[0] if res_b and res_b[0] else None

                    await conn.execute(
                        "UPDATE books SET title=?, genre=?, concept=?, synopsis=?, target_eps=?, style_dna=?, marketing_data=? WHERE id=?",
                        (bible.title, bible.genre, bible.concept, bible.synopsis, kwargs.get("target_eps", 50), style_dna, mkt_data, book_id)
                    )
                else:
                    # 新規作成
                    mkt_data = json.dumps(bible.marketing_assets.model_dump(), ensure_ascii=False)
                    cursor = await conn.execute(
                        "INSERT INTO books (title, genre, concept, synopsis, target_eps, style_dna, marketing_data, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (bible.title, bible.genre, bible.concept, bible.synopsis, kwargs.get("target_eps", 50), style_dna, mkt_data, time.strftime('%Y-%m-%dT%H:%M:%S'))
                    )
                    book_id = cursor.lastrowid
                    branch_id = None

                ws_data = bible.world_settings.model_dump()
                if not branch_id:
                    # 新規ブック、またはブランチが未設定のブックに Main ブランチを強制作成
                    cursor_br = await conn.execute(
                        "INSERT INTO branches (book_id, name, created_at) VALUES (?, 'Main', ?)",
                        (book_id, time.strftime('%Y-%m-%dT%H:%M:%S'))
                    )
                    branch_id = cursor_br.lastrowid
                    await conn.execute("UPDATE books SET current_branch_id=? WHERE id=?", (branch_id, book_id))

                ws_data.update({
                    "story_direction": bible.story_direction,
                    "dynamic_pacing_graph": [p.model_dump() for p in bible.dynamic_pacing_graph],
                    "villain_parallel_timeline": bible.villain_parallel_timeline,
                    "arcs": [a.model_dump() for a in bible.arcs],
                    "full_story_roadmap": [r.model_dump() for r in bible.full_story_roadmap],
                    "dna": bible.dna.model_dump() if bible.dna else None
                })

                await conn.execute(
                    "INSERT INTO bible (book_id, settings, version, last_updated) VALUES (?,?,?,?)",
                    (book_id, json.dumps(ws_data, ensure_ascii=False), 1, time.strftime('%Y-%m-%dT%H:%M:%S'))
                )

                chars = [(book_id, bible.mc_profile.name, "主人公", json.dumps(bible.mc_profile.model_dump(), ensure_ascii=False))]
                chars += [(book_id, s.name, s.role, json.dumps(s.model_dump(), ensure_ascii=False)) for s in bible.sub_characters]
                await conn.executemany("INSERT INTO characters (book_id, name, role, registry_data) VALUES (?,?,?,?)", chars)

                plot_data = [(book_id, branch_id, ep, f"第{ep}話 (TBD)", "計画中...", "planned", "Hate")
                             for ep in range(1, kwargs.get("target_eps", 50) + 1)]
                await conn.executemany(
                    "INSERT OR REPLACE INTO plot (book_id, branch_id, ep_num, title, summary, status, current_chain_phase) VALUES (?,?,?,?,?,?,?)",
                    plot_data
                )
                await conn.commit()
                return book_id
            except Exception as e:
                await conn.rollback()
                logger.error(f"Failed to save full world bible: {e}\n{traceback.format_exc()}")
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
        trinity_review_log: Any, created_at: str, stress_delta: int = 0, qol_delta: int = 0, branch_id: int = 1
    ) -> None:
        await self.db.execute(
            """INSERT OR REPLACE INTO chapters
               (book_id, branch_id, ep_num, title, content, summary, killer_phrase, ai_insight,
                world_state, trinity_review_log, created_at, stress_delta, qol_delta)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (book_id, branch_id, ep_num, title, content, summary if isinstance(summary, str) else json.dumps(summary, ensure_ascii=False), killer_phrase, ai_insight,
             json.dumps(world_state, ensure_ascii=False) if isinstance(world_state, (dict, list)) else (world_state or "{}"),
             json.dumps(trinity_review_log, ensure_ascii=False) if isinstance(trinity_review_log, (dict, list)) else (trinity_review_log or "{}"),
             created_at, stress_delta, qol_delta)
        )

    @retry_with_logging()
    async def get_chapter(self, branch_id: int, ep_num: int) -> Optional[ChapterDbModel]:
        row = await self.db.fetch_one("SELECT * FROM chapters WHERE branch_id=? AND ep_num=?", (branch_id, ep_num))
        if not row:
            return None
        return ChapterDbModel(**self._parse_row(dict(row), ['world_state', 'trinity_review_log', 'summary']))

    @retry_with_logging()
    async def get_chapters_before(self, branch_id: int, ep_num: int) -> List[ChapterDbModel]:
        rows = await self.db.fetch_all(
            "SELECT * FROM chapters WHERE branch_id=? AND ep_num<? ORDER BY ep_num DESC",
            (branch_id, ep_num)
        )
        return [ChapterDbModel(**self._parse_row(dict(r), ['world_state', 'trinity_review_log', 'summary'])) for r in rows]

    @retry_with_logging()
    async def get_all_non_anchor_chapters(self, book_id_or_branch_id: int, branch_id: Optional[int] = None, order_by: str = "ep_num", limit: Optional[int] = None) -> List[ChapterDbModel]:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        limit_clause = f" LIMIT {limit}" if limit else ""
        rows = await self.db.fetch_all(
            f"SELECT * FROM chapters WHERE branch_id=? ORDER BY {order_by}{limit_clause}", (target_branch_id,)
        )
        return [ChapterDbModel(**self._parse_row(dict(r), ['world_state', 'trinity_review_log', 'summary'])) for r in rows]

    @retry_with_logging()
    async def delete_chapter(self, book_id_or_branch_id: int, ep_num: int, branch_id: Optional[int] = None) -> None:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        await self.db.execute("DELETE FROM chapters WHERE branch_id=? AND ep_num=?", (target_branch_id, ep_num))

    @retry_with_logging()
    async def update_chapter_content(self, branch_id: int, ep_num: int, content: str) -> None:
        await self.db.execute("UPDATE chapters SET content=? WHERE branch_id=? AND ep_num=?", (content, branch_id, ep_num))

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
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse internal_state JSON for key {key}, returning raw string: {e}")
                return row['value']
        return None

    # ---------- 拡張クエリ ----------
    @retry_with_logging()
    async def get_plots_before_limit_1(self, branch_id: int, ep_num: int) -> Optional[PlotDbModel]:
        """ep_num より前の最新プロットを1件取得（直前プロットの状態参照用）"""
        rows = await self.db.fetch_all(
            "SELECT * FROM plot WHERE branch_id=? AND ep_num < ? ORDER BY ep_num DESC LIMIT 1",
            (branch_id, ep_num)
        )
        if not rows:
            return None
        return PlotDbModel(**self._parse_row(dict(rows[0]), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score']))

    @retry_with_logging()
    async def get_plots_between(self, branch_id: int, start_ep: int, end_ep: int) -> List[PlotDbModel]:
        """start_ep〜end_ep の範囲のプロットを取得"""
        rows = await self.db.fetch_all(
            "SELECT * FROM plot WHERE branch_id=? AND ep_num BETWEEN ? AND ? ORDER BY ep_num",
            (branch_id, start_ep, end_ep)
        )
        return [PlotDbModel(**self._parse_row(dict(r), ['scenes', 'next_hook', 'healed_fields', 'state_integrity_score'])) for r in rows]

    @retry_with_logging()
    async def update_book_target_eps(self, book_id: int, new_total_eps: int) -> None:
        """作品の目標話数を更新する"""
        await self.db.execute("UPDATE books SET target_eps=? WHERE id=?", (new_total_eps, book_id))

    @retry_with_logging()
    async def recalculate_book_stress(self, book_id: int, branch_id: int = 1) -> int:
        """指定ブランチの全チャプターの stress_delta を合計して累積ストレスを再計算し、DBを更新する"""
        rows = await self.db.fetch_all("SELECT stress_delta FROM chapters WHERE branch_id=?", (branch_id,))
        total_stress = sum(row['stress_delta'] or 0 for row in rows)
        await self.db.execute("UPDATE books SET cumulative_stress=? WHERE id=?", (total_stress, book_id))
        return total_stress

    @retry_with_logging()
    async def recalculate_book_comfort(self, book_id: int, branch_id: int = 1) -> Tuple[int, int]:
        """指定ブランチの全チャプターの qol_delta を合計して累積QOLを再計算し、DBを更新する"""
        rows = await self.db.fetch_all("SELECT qol_delta FROM chapters WHERE branch_id=?", (branch_id,))
        total_qol = sum(row['qol_delta'] or 0 for row in rows)
        # 聖域の堅牢性は最新のプロットから取得
        latest_plot = await self.db.fetch_one("SELECT state_integrity_score FROM plot WHERE branch_id=? ORDER BY ep_num DESC LIMIT 1", (branch_id,))
        integrity = latest_plot['state_integrity_score'] if latest_plot else 100

        await self.db.execute("UPDATE books SET cumulative_qol=?, sanctuary_integrity=? WHERE id=?", (total_qol, integrity, book_id))
        return total_qol, integrity

    @retry_with_logging()
    async def recalculate_book_cost(self, book_id: int, branch_id: int = 1) -> float:
        """最新のプロットから代償蓄積スコアを取得し、DBを更新する"""
        latest_plot = await self.db.fetch_one("SELECT cost_score FROM plot WHERE branch_id=? AND status='expanded' ORDER BY ep_num DESC LIMIT 1", (branch_id,))
        total_cost = latest_plot['cost_score'] if latest_plot else 0.0
        await self.db.execute("UPDATE books SET cumulative_cost=? WHERE id=?", (total_cost, book_id))
        return total_cost

    async def get_relevant_past_logs(
        self,
        branch_id: int,
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
        sql = f"SELECT ep_num, ai_insight, summary FROM chapters WHERE branch_id=? AND ep_num < ? AND ({' OR '.join(clauses)}) ORDER BY ep_num DESC LIMIT ?"
        rows = await self.db.fetch_all(sql, (branch_id, current_ep, *params, top_k))

        if not rows: return ""

        res = "【過去の関連文脈（RAG）】\n"
        for r in rows:
            res += f"- 第{r['ep_num']}話: {r['summary']} (重要事項: {r['ai_insight']})\n"
        return res

    # ---------- Pending Patches (Human-in-the-Loop) ----------
    @retry_with_logging()
    async def save_pending_patch(
        self, book_id: int, patch_type: str,
        patch_content: str, ab_test_result: Dict[str, Any]
    ) -> int:
        """承認待ちパッチを保存"""
        return await self.db.fetch_lastrowid(
            "INSERT INTO pending_patches (book_id, patch_type, patch_content, ab_test_result, status, created_at) VALUES (?,?,?,?,?,?)",
            (book_id, patch_type, json.dumps(patch_content, ensure_ascii=False) if isinstance(patch_content, dict) else patch_content,
             json.dumps(ab_test_result, ensure_ascii=False),
             "pending", time.strftime('%Y-%m-%dT%H:%M:%S'))
        )

    @retry_with_logging()
    async def get_pending_patches(self, book_id: int) -> List[Dict[str, Any]]:
        """承認待ちパッチ一覧を取得"""
        rows = await self.db.fetch_all(
            "SELECT * FROM pending_patches WHERE book_id=? AND status='pending' ORDER BY created_at DESC",
            (book_id,)
        )
        return [self._parse_row(dict(r), ['ab_test_result']) for r in rows]

    @retry_with_logging()
    async def update_patch_status(self, patch_id: int, status: str) -> None:
        """パッチのステータスを更新（approved / rejected）"""
        await self.db.execute(
            "UPDATE pending_patches SET status=?, reviewed_at=? WHERE id=?",
            (status, time.strftime('%Y-%m-%dT%H:%M:%S'), patch_id)
        )

    @retry_with_logging()
    async def get_rejected_patches(self, book_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """却下されたパッチの履歴を取得"""
        rows = await self.db.fetch_all(
            "SELECT * FROM pending_patches WHERE book_id=? AND status='rejected' ORDER BY reviewed_at DESC LIMIT ?",
            (book_id, limit)
        )
        return [self._parse_row(dict(r), ['ab_test_result']) for r in rows]

