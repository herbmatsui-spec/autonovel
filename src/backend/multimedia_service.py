"""Multimedia 機能の統合サービス層。

`MultimediaService` は FastAPI ルータから呼ばれ、Phase3 の各生成器を束ねる。
- `require_multimedia()` で機能フラグを最初に確認
- DB セッションはテスト容易性のためコンストラクタ注入
- 成果物は `MULTIMEDIA_OUTPUT_DIR` 配下に保存し、メタデータを DB に永続化
"""

from __future__ import annotations

import json
import logging
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.database import SessionLocal
from src.backend.database.series_loader import SeriesDataLoader, SeriesDataLoaderConfig
from src.backend.feature_flags import require_multimedia
from src.backend.multimedia_storage import ensure_multimedia_dir
from src.easy_mode.phase3.ebook_export import (
    PDF_AVAILABLE,
    create_ebook_exporter,
)
from src.easy_mode.phase3.if_routes import (
    IFRouteGraph,
    create_if_route_system,
)
from src.easy_mode.phase3.media_mix import (
    MediaFormat,
    create_media_mix_exporter,
)
from src.easy_mode import SeriesResult

logger = logging.getLogger(__name__)


def _extract_preset(series: SeriesResult) -> dict[str, Any]:
    """series.bible から characters と style を安全に抽出しプリセット辞書を組み立てる (Step 19)。"""
    bible = series.bible or {}
    raw_characters = bible.get("characters") or {}
    if not isinstance(raw_characters, dict):
        raw_characters = {}
    archetypes = raw_characters.get("archetypes") or {}
    if not isinstance(archetypes, dict):
        archetypes = {}

    normalized_archetypes = {}
    for k, v in archetypes.items():
        if isinstance(v, dict):
            normalized_archetypes[k] = v
        elif isinstance(v, str):
            normalized_archetypes[k] = {"name_pattern": v, "display_name": v}
        else:
            normalized_archetypes[k] = {"name_pattern": str(v)}

    characters = dict(raw_characters)
    characters["archetypes"] = normalized_archetypes

    style = bible.get("style") or {}
    erotic = bible.get("erotic") or {}
    return {
        "genre": series.genre,
        "characters": characters,
        "style": style,
        "erotic": erotic,
    }


# 後方互換性のためテストフィクスチャからエイリアス提供 (Step 21)
try:
    from tests.helpers.multimedia_fixtures import (
        make_minimal_episode as _make_minimal_episode,
        make_minimal_preset as _make_minimal_preset,
        make_minimal_series,
    )
except ImportError:
    pass


@dataclass
class MultimediaResult:
    """サービス層の戻り値。"""

    asset_id: int | None
    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MultimediaService:
    """Multimedia 機能の統合サービス。"""

    def __init__(
        self,
        session_factory: Any = None,
        output_dir: Path | None = None,
        series_loader: SeriesDataLoader | None = None,
    ) -> None:
        self._session_factory = session_factory or SessionLocal
        self._output_dir = output_dir
        self._series_loader = series_loader or SeriesDataLoader(self._session_factory)

    def _resolve_series(self, book_id: int, series: SeriesResult | None = None) -> SeriesResult:
        """外部から渡された series を返すか、未指定なら DB から実データを読み出す。"""
        if series is not None:
            return series
        return self._series_loader.load_series(SeriesDataLoaderConfig(book_id=book_id))

    def _output_path(self) -> Path:
        if self._output_dir is not None:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            return self._output_dir
        return ensure_multimedia_dir()

    def _session(self) -> Session:
        return self._session_factory()

    def _record_artifact(
        self,
        session: Session,
        book_id: int,
        asset_type: str,
        fmt: str,
        file_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """MultimediaArtifact 行を挿入し、生成された id を返す。"""
        row = session.execute(
            text(
                """
                INSERT INTO multimedia_artifacts (book_id, asset_type, format, file_path, metadata_json, created_at)
                VALUES (:book_id, :asset_type, :fmt, :file_path, :meta, :created_at)
                """
            ),
            {
                "book_id": book_id,
                "asset_type": asset_type,
                "fmt": fmt,
                "file_path": str(file_path),
                "meta": json.dumps(metadata or {}, ensure_ascii=False),
                "created_at": datetime.now(),
            },
        )
        return int(getattr(row, "lastrowid", 0) or 0)

    def _record_task(
        self,
        session: Session,
        task_id: str,
        asset_id: int | None = None,
        status: str = "pending",
    ) -> int:
        row = session.execute(
            text(
                """
                INSERT INTO multimedia_tasks (task_id, asset_id, status, started_at)
                VALUES (:task_id, :asset_id, :status, :started_at)
                """
            ),
            {
                "task_id": task_id,
                "asset_id": asset_id,
                "status": status,
                "started_at": datetime.now(),
            },
        )
        return int(getattr(row, "lastrowid", 0) or 0)

    def update_task(
        self,
        session: Session,
        task_id: str,
        status: str,
        error: str | None = None,
        finished: bool = True,
    ) -> None:
        session.execute(
            text(
                """
                UPDATE multimedia_tasks
                SET status = :status, error = :error,
                    finished_at = CASE WHEN :finished THEN :finished_at ELSE finished_at END
                WHERE task_id = :task_id
                """
            ),
            {
                "status": status,
                "error": error,
                "finished": finished,
                "finished_at": datetime.now() if finished else None,
                "task_id": task_id,
            },
        )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._session() as s:
            row = s.execute(
                text(
                    """
                    SELECT task_id, asset_id, status, started_at, finished_at, error
                    FROM multimedia_tasks WHERE task_id = :task_id
                    """
                ),
                {"task_id": task_id},
            ).fetchone()
        if row is None:
            return None
        keys = ["task_id", "asset_id", "status", "started_at", "finished_at", "error"]
        return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in zip(keys, row)}

    def get_artifact(self, asset_id: int) -> dict[str, Any] | None:
        with self._session() as s:
            row = s.execute(
                text(
                    """
                    SELECT id, book_id, asset_type, format, file_path, metadata_json, created_at
                    FROM multimedia_artifacts WHERE id = :id
                    """
                ),
                {"id": asset_id},
            ).fetchone()
        if row is None:
            return None
        try:
            meta = json.loads(row[5]) if row[5] else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
        return {
            "asset_id": row[0],
            "book_id": row[1],
            "asset_type": row[2],
            "format": row[3],
            "file_path": row[4],
            "metadata": meta,
            "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else row[6],
        }

    # ===== Media Mix =====
    def generate_media_mix(
        self,
        book_id: int,
        format_name: str = "manga",
        series: SeriesResult | None = None,
        episode_num: int | None = None,
    ) -> MultimediaResult:
        require_multimedia()
        series = self._resolve_series(book_id, series)
        if not series.episodes:
            raise ValueError(f"No chapters found for book {book_id}")
        target_idx = (episode_num or 1) - 1
        if 0 <= target_idx < len(series.episodes):
            target_ep = series.episodes[target_idx]
        else:
            target_ep = series.episodes[0]

        try:
            fmt = MediaFormat(format_name)
        except ValueError:
            raise ValueError(f"Unsupported media mix format: {format_name}")

        exporter = create_media_mix_exporter(series.genre, _extract_preset(series))
        scripts = exporter.export_all(target_ep, series, [fmt])

        out_dir = self._output_path() / f"book_{book_id}" / "media_mix"
        out_dir.mkdir(parents=True, exist_ok=True)
        files: list[str] = []
        for f, script in scripts.items():
            p = out_dir / f"ep{target_ep.episode_num:03d}_{f.value}.json"
            p.write_text(script.to_json(), encoding="utf-8")
            files.append(str(p))

        with self._session() as s:
            asset_id = self._record_artifact(
                s,
                book_id,
                "media_mix",
                fmt.value,
                out_dir / "index.json",
                {"file_count": len(files), "files": files},
            )
            s.commit()

        return MultimediaResult(
            asset_id=asset_id,
            files=files,
            metadata={"format": fmt.value, "episode_num": target_ep.episode_num},
        )

    def _load_book_illustrations(self, session: Session, book_id: int) -> list[dict[str, Any]]:
        """DBから該当書籍の挿絵・イラストアセットを安全に取得・ロードする (Step 39, 40)。"""
        illustrations: list[dict[str, Any]] = []
        try:
            rows = session.execute(
                text(
                    """
                    SELECT id, file_path, metadata_json
                    FROM multimedia_artifacts
                    WHERE book_id = :book_id AND asset_type = 'illustration'
                    ORDER BY id ASC
                    """
                ),
                {"book_id": book_id},
            ).fetchall()
            for r in rows:
                row_id, fp_str, meta_str = r[0], r[1], r[2]
                try:
                    meta = json.loads(meta_str) if meta_str else {}
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                fp = Path(fp_str)
                if not fp.exists():
                    logger.warning("Illustration file not found: %s", fp_str)
                    continue
                try:
                    data = fp.read_bytes()
                except Exception as exc:
                    logger.warning("Failed to read illustration file %s: %s", fp_str, exc)
                    continue

                illustrations.append({
                    "image_id": f"art_{row_id}",
                    "image_bytes": data,
                    "file_name": fp.name,
                    "media_type": meta.get("media_type", "image/jpeg"),
                    "position": meta.get("position", "chapter_start"),
                    "chapter_index": meta.get("chapter_index", 1),
                    "caption": meta.get("caption", ""),
                })
        except Exception as e:
            logger.debug("Could not query illustrations from multimedia_artifacts: %s", e)

        # illustrations テーブルがある場合のフォールバック試行
        try:
            ill_rows = session.execute(
                text(
                    """
                    SELECT id, file_path, chapter_number, caption, position
                    FROM illustrations
                    WHERE book_id = :book_id
                    ORDER BY id ASC
                    """
                ),
                {"book_id": book_id},
            ).fetchall()
            for r in ill_rows:
                row_id, fp_str, chap_num, caption, pos = r[0], r[1], r[2], r[3], r[4]
                fp = Path(fp_str)
                if not fp.exists():
                    continue
                try:
                    data = fp.read_bytes()
                except Exception:
                    continue
                illustrations.append({
                    "image_id": f"ill_{row_id}",
                    "image_bytes": data,
                    "file_name": fp.name,
                    "media_type": "image/jpeg",
                    "position": pos or "chapter_start",
                    "chapter_index": chap_num or 1,
                    "caption": caption or "",
                })
        except Exception:
            pass

        return illustrations

    # ===== Ebook =====
    def export_ebook(
        self,
        book_id: int,
        formats: Sequence[str] = ("epub", "pdf"),
        series: SeriesResult | None = None,
        images: list[dict[str, Any]] | None = None,
    ) -> MultimediaResult:
        require_multimedia()
        series = self._resolve_series(book_id, series)
        exporter = create_ebook_exporter(series.genre, _extract_preset(series))

        out_dir = self._output_path() / f"book_{book_id}" / "ebook"
        out_dir.mkdir(parents=True, exist_ok=True)

        with self._session() as s:
            illustrations = images if images is not None else self._load_book_illustrations(s, book_id)

        results: dict[str, str] = {}
        for fmt in formats:
            base = f"{series.title}_ep{len(series.episodes)}"
            fname = f"{base}.{fmt}"
            path = out_dir / fname
            try:
                if fmt == "epub":
                    # Step 54 & Step 41: Pure Python 商用縦書きEPUB 3ビルダーへの挿絵受け渡し
                    from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder
                    builder = CommercialEpubBuilder()
                    chap_list = [
                        {"title": ep.title, "content": ep.content}
                        for ep in series.episodes
                    ]
                    epub_bytes = builder.build_commercial_epub(
                        novel_meta={"title": series.title},
                        chapters=chap_list,
                        images=illustrations,
                    )
                    path.write_bytes(epub_bytes)
                elif fmt == "pdf":
                    if not PDF_AVAILABLE:
                        path = out_dir / f"{base}.pdf.json"
                        path.write_text(
                            json.dumps(
                                {"format": "pdf", "title": series.title, "fallback": True},
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                    else:
                        exporter.export_pdf(series, path)
                elif fmt == "mobi":
                    exporter.export_mobi(series, path)
                else:
                    logger.warning("Unknown ebook format: %s", fmt)
                    continue
                results[fmt] = str(path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to export %s: %s", fmt, exc)
                fb = out_dir / f"{base}.{fmt}.error.json"
                fb.write_text(
                    json.dumps(
                        {"format": fmt, "error": str(exc), "fallback": True}, ensure_ascii=False
                    ),
                    encoding="utf-8",
                )
                results[fmt] = str(fb)

        with self._session() as s:
            asset_id = self._record_artifact(
                s,
                book_id,
                "ebook",
                "+".join(formats),
                out_dir / "index.json",
                {
                    "formats": list(results.keys()),
                    "files": list(results.values()),
                    "illustration_count": len(illustrations),
                },
            )
            s.commit()

        return MultimediaResult(
            asset_id=asset_id,
            files=list(results.values()),
            metadata={
                "formats": list(results.keys()),
                "illustration_count": len(illustrations),
            },
        )

    # ===== IF Routes =====
    def generate_if_routes(
        self,
        book_id: int,
        series: SeriesResult | None = None,
        persist: bool = True,
    ) -> tuple[MultimediaResult, IFRouteGraph | None]:
        require_multimedia()
        series = self._resolve_series(book_id, series)
        graph = create_if_route_system(series.genre, series, _extract_preset(series))

        out_dir = self._output_path() / f"book_{book_id}" / "if_routes"
        out_dir.mkdir(parents=True, exist_ok=True)
        graph_file = out_dir / "graph.json"
        graph_file.write_text(
            json.dumps(
                {
                    "entry_node_id": graph.entry_node_id,
                    "nodes": {nid: n.to_dict() for nid, n in graph.nodes.items()},
                    "metadata": graph.metadata,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        if not persist:
            return (
                MultimediaResult(
                    asset_id=None,
                    files=[str(graph_file)],
                    metadata={"node_count": len(graph.nodes)},
                ),
                graph,
            )

        with self._session() as s:
            asset_id = self._record_artifact(
                s,
                book_id,
                "if_routes",
                "json",
                graph_file,
                {"entry_node_id": graph.entry_node_id, "node_count": len(graph.nodes)},
            )
            s.commit()
        return (
            MultimediaResult(
                asset_id=asset_id,
                files=[str(graph_file)],
                metadata={"entry_node_id": graph.entry_node_id, "node_count": len(graph.nodes)},
            ),
            graph,
        )

    # ===== Asset Pack =====
    def generate_asset_pack(
        self,
        book_id: int,
        include_if_routes: bool = True,
        include_media_mix: bool = True,
        include_ebook: bool = True,
        include_audio: bool = True,
        ebook_formats: Sequence[str] = ("epub", "pdf"),
        media_mix_formats: Sequence[str] = ("manga",),
        series: SeriesResult | None = None,
    ) -> tuple[MultimediaResult, str]:
        require_multimedia()
        task_id = str(uuid.uuid4())
        series = self._resolve_series(book_id, series)

        out_dir = self._output_path() / f"book_{book_id}" / f"pack_{task_id[:8]}"
        out_dir.mkdir(parents=True, exist_ok=True)
        bundle: dict[str, Any] = {"book_id": book_id, "task_id": task_id, "items": []}

        if include_if_routes:
            mm, _ = self.generate_if_routes(book_id, series=series, persist=False)
            bundle["items"].append({"type": "if_routes", "files": mm.files})

        if include_media_mix:
            for f in media_mix_formats:
                mm = self.generate_media_mix(book_id, format_name=f, series=series)
                bundle["items"].append({"type": "media_mix", "format": f, "files": mm.files})

        if include_ebook:
            mm = self.export_ebook(book_id, formats=ebook_formats, series=series)
            bundle["items"].append({"type": "ebook", "files": mm.files, "asset_id": mm.asset_id})

        # Step 31: 音声ファイルの同梱
        audio_files = []
        if include_audio:
            with self._session() as s:
                try:
                    audio_rows = s.execute(
                        text("SELECT file_path FROM audio_assets WHERE book_id = :book_id"),
                        {"book_id": book_id},
                    ).fetchall()
                    for r in audio_rows:
                        if r[0] and Path(r[0]).exists():
                            audio_files.append(str(r[0]))
                except Exception:
                    pass
            if audio_files:
                bundle["items"].append({"type": "audio", "files": audio_files})

        bundle_path = out_dir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

        zip_path = out_dir / "asset_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bundle_path, arcname="bundle.json")
            for item in bundle["items"]:
                item_type = item.get("type", "other")
                for f in item.get("files", []):
                    p = Path(f)
                    if p.exists():
                        if item_type == "audio":
                            arcname = f"05_音声/{p.name}"
                        elif item_type == "ebook":
                            arcname = f"04_電子書籍/{p.name}"
                        else:
                            arcname = p.name
                        zf.write(p, arcname=arcname)

        with self._session() as s:
            asset_id = self._record_artifact(
                s,
                book_id,
                "asset_pack",
                "zip",
                zip_path,
                {"task_id": task_id, "item_count": len(bundle["items"])},
            )
            self._record_task(s, task_id, asset_id, status="completed")
            s.commit()

        result = MultimediaResult(
            asset_id=asset_id,
            files=[str(zip_path)],
            metadata={"task_id": task_id, "item_count": len(bundle["items"])},
        )
        return result, task_id

    def get_artifacts_by_book(self, book_id: int) -> list[dict[str, Any]]:
        """特定の book_id に紐づく全アセットメタデータ（二次創作および音声アセット）を取得 (Step 22)。"""
        results = []
        with self._session() as s:
            rows = s.execute(
                text(
                    """
                    SELECT id, book_id, asset_type, format, file_path, metadata_json, created_at
                    FROM multimedia_artifacts WHERE book_id = :book_id
                    ORDER BY created_at DESC
                    """
                ),
                {"book_id": book_id},
            ).fetchall()
            for row in rows:
                try:
                    meta = json.loads(row[5]) if row[5] else {}
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                results.append(
                    {
                        "asset_id": row[0],
                        "book_id": row[1],
                        "asset_type": row[2],
                        "format": row[3],
                        "file_path": row[4],
                        "metadata": meta,
                        "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else row[6],
                    }
                )

            # 音声アセットも含める
            try:
                audio_rows = s.execute(
                    text(
                        """
                        SELECT id, book_id, episode_num, file_path, duration_seconds, file_size_bytes, created_at
                        FROM audio_assets WHERE book_id = :book_id
                        ORDER BY created_at DESC
                        """
                    ),
                    {"book_id": book_id},
                ).fetchall()
                for a in audio_rows:
                    results.append(
                        {
                            "asset_id": a[0],
                            "book_id": a[1],
                            "asset_type": "audio",
                            "format": "wav",
                            "file_path": a[3],
                            "metadata": {
                                "episode_num": a[2],
                                "duration_seconds": a[4],
                                "file_size_bytes": a[5],
                            },
                            "created_at": a[6].isoformat() if hasattr(a[6], "isoformat") else a[6],
                        }
                    )
            except Exception:
                # audio_assetsテーブルが存在しない・マイグレーション未適用環境での耐障害性
                pass

        return results
