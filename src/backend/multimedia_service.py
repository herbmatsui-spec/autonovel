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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.database import SessionLocal
from src.backend.feature_flags import require_multimedia
from src.backend.multimedia_storage import ensure_multimedia_dir
from src.easy_mode.phase3.ebook_export import (
    EPUB_AVAILABLE,
    PDF_AVAILABLE,
    create_ebook_exporter,
)
from src.easy_mode.phase3.if_routes import (
    IFRouteGraph,
    create_if_route_system,
)
from src.easy_mode.phase3.media_mix import (
    MediaFormat,
    MediaScript,
    create_media_mix_exporter,
)
from src.easy_mode.pipeline import EpisodeResult, SeriesResult

logger = logging.getLogger(__name__)


PRESET_FALLBACK: dict[str, Any] = {
    "characters": {"archetypes": {}},
    "erotic": {},
}


def _make_minimal_preset(genre: str) -> dict[str, Any]:
    """genre のみから preset を組み立てる (DB 不在のテスト用)。"""
    return {
        "genre": genre,
        "characters": {"archetypes": {}},
        "erotic": {},
    }


def _make_minimal_episode(num: int = 1, title: str = "テスト話") -> EpisodeResult:
    """単体エピソードを組み立てるヘルパ。"""
    content = f"第{num}話のテスト本文です。\n\n主人公は困難に立ち向かった。\n「行くぞ」と彼は言った。\n"
    return EpisodeResult(
        episode_num=num,
        title=title,
        content=content,
        word_count=len(content),
        audit_score=80.0,
        audit_passed=True,
        rewrite_count=0,
        spice_elements=[],
        metadata={},
        needs_human_review=False,
    )


def make_minimal_series(
    genre: str = "ハイファンタジー (R15)",
    title: str = "テストシリーズ",
    episode_count: int = 1,
) -> SeriesResult:
    """テスト・サービス層から利用する最小 SeriesResult を生成する。"""
    eps = [_make_minimal_episode(i + 1, f"第{i + 1}話") for i in range(episode_count)]
    return SeriesResult(
        genre=genre,
        title=title,
        concept="テストコンセプト",
        total_episodes=episode_count,
        episodes=eps,
        bible={},
        plot_outline=[],
        metadata={"prologue": f"{title} - 始まりの物語"},
    )


@dataclass
class MultimediaResult:
    """サービス層の戻り値。"""

    asset_id: int | None
    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MultimediaService:
    """Multimedia 機能の統合サービス。"""

    def __init__(self, session_factory: Any = None, output_dir: Path | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._output_dir = output_dir

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
        series = series or make_minimal_series(episode_count=max(1, episode_num or 1))
        target_ep = series.episodes[(episode_num or 1) - 1] if series.episodes else None
        if target_ep is None:
            target_ep = _make_minimal_episode(1)

        try:
            fmt = MediaFormat(format_name)
        except ValueError:
            raise ValueError(f"Unsupported media mix format: {format_name}")

        exporter = create_media_mix_exporter(series.genre, _make_minimal_preset(series.genre))
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
                s, book_id, "media_mix", fmt.value, out_dir / "index.json",
                {"file_count": len(files), "files": files},
            )
            s.commit()

        return MultimediaResult(
            asset_id=asset_id,
            files=files,
            metadata={"format": fmt.value, "episode_num": target_ep.episode_num},
        )

    # ===== Ebook =====
    def export_ebook(
        self,
        book_id: int,
        formats: Sequence[str] = ("epub", "pdf"),
        series: SeriesResult | None = None,
    ) -> MultimediaResult:
        require_multimedia()
        series = series or make_minimal_series()
        exporter = create_ebook_exporter(series.genre, _make_minimal_preset(series.genre))

        out_dir = self._output_path() / f"book_{book_id}" / "ebook"
        out_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, str] = {}
        for fmt in formats:
            base = f"{series.title}_ep{len(series.episodes)}"
            fname = f"{base}.{fmt}"
            path = out_dir / fname
            try:
                if fmt == "epub":
                    if not EPUB_AVAILABLE:
                        path = out_dir / f"{base}.epub.json"
                        path.write_text(
                            json.dumps({"format": "epub", "title": series.title, "fallback": True}, ensure_ascii=False),
                            encoding="utf-8",
                        )
                    else:
                        exporter.export_epub(series, path)
                elif fmt == "pdf":
                    if not PDF_AVAILABLE:
                        path = out_dir / f"{base}.pdf.json"
                        path.write_text(
                            json.dumps({"format": "pdf", "title": series.title, "fallback": True}, ensure_ascii=False),
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
                    json.dumps({"format": fmt, "error": str(exc), "fallback": True}, ensure_ascii=False),
                    encoding="utf-8",
                )
                results[fmt] = str(fb)

        with self._session() as s:
            asset_id = self._record_artifact(
                s, book_id, "ebook", "+".join(formats), out_dir / "index.json",
                {"formats": list(results.keys()), "files": list(results.values())},
            )
            s.commit()

        return MultimediaResult(
            asset_id=asset_id,
            files=list(results.values()),
            metadata={"formats": list(results.keys())},
        )

    # ===== IF Routes =====
    def generate_if_routes(
        self,
        book_id: int,
        series: SeriesResult | None = None,
        persist: bool = True,
    ) -> tuple[MultimediaResult, IFRouteGraph | None]:
        require_multimedia()
        series = series or make_minimal_series(episode_count=2)
        graph = create_if_route_system(series.genre, series, _make_minimal_preset(series.genre))

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
                s, book_id, "if_routes", "json", graph_file,
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
        ebook_formats: Sequence[str] = ("epub", "pdf"),
        media_mix_formats: Sequence[str] = ("manga",),
        series: SeriesResult | None = None,
    ) -> tuple[MultimediaResult, str]:
        require_multimedia()
        task_id = str(uuid.uuid4())
        series = series or make_minimal_series(episode_count=1)

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

        bundle_path = out_dir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

        zip_path = out_dir / "asset_pack.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bundle_path, arcname="bundle.json")
            for item in bundle["items"]:
                for f in item.get("files", []):
                    p = Path(f)
                    if p.exists():
                        zf.write(p, arcname=p.name)

        with self._session() as s:
            asset_id = self._record_artifact(
                s, book_id, "asset_pack", "zip", zip_path,
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
