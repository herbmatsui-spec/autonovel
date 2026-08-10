#!/usr/bin/env python3
"""挿絵生成 CLI（表紙 / 挿絵 / キャラクター）。

使い方例:
  python -m src.cli.illustration_cli cover --book-id 1 --title "天空の城" --genre ファンタジー
  python -m src.cli.illustration_cli scene --book-id 1 --episode 3 --text "シーン本文..."
  python -m src.cli.illustration_cli character --book-id 1 --name アヤ --appearance "青い髪"
"""

import argparse
import asyncio
import json
import os
import sys

from src.models.illustration import (
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)
from src.services.image_service import ImageService


def _build_agent():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY 環境変数が設定されていません。", file=sys.stderr)
        sys.exit(1)
    image_service = ImageService(api_key=api_key)
    from src.agents.illustration_agent import IllustrationAgent

    return IllustrationAgent(image_service=image_service)


async def _run_cover(args):
    agent = _build_agent()
    book_context = {
        "title": args.title or f"Book {args.book_id}",
        "genre": args.genre or "",
        "concept": args.concept or "",
        "keywords": args.keywords or "",
    }
    request = IllustrationRequest(
        book_id=args.book_id,
        illustration_type=IllustrationType.COVER,
        book_context=book_context,
        model=_model(args.model),
        safety_level=_safety(args.safety),
        aspect_ratio=args.aspect or "3:4",
    )
    result = await agent.run(request=request)
    _print_result(result)


async def _run_scene(args):
    agent = _build_agent()
    text = args.text or _read_stdin()
    request = IllustrationRequest(
        book_id=args.book_id,
        illustration_type=IllustrationType.EPISODE,
        episode_number=args.episode,
        scene_text=text,
        book_context={"genre": args.genre or ""},
        model=_model(args.model),
        safety_level=_safety(args.safety),
        aspect_ratio=args.aspect or "16:9",
    )
    if args.extract:
        results = await agent.generate_episode_scenes(request)
        for r in results:
            _print_result({"status": "success", "result": r})
    else:
        result = await agent.run(request=request)
        _print_result(result)


async def _run_character(args):
    agent = _build_agent()
    book_context = {
        "name": args.name or "character",
        "role": args.role or "",
        "appearance": args.appearance or "",
        "traits": args.traits or "",
        "background": args.background or "",
    }
    request = IllustrationRequest(
        book_id=args.book_id,
        illustration_type=IllustrationType.CHARACTER,
        character_id=args.character_id,
        book_context=book_context,
        model=_model(args.model),
        safety_level=_safety(args.safety),
        aspect_ratio=args.aspect or "3:4",
    )
    result = await agent.run(request=request)
    _print_result(result)


def _model(value: str):
    from src.models.illustration import IllustrationModel

    return IllustrationModel[value.upper()]


def _safety(value: str) -> SafetyLevel:
    return SafetyLevel.R15_CONTENT if value == "r15" else SafetyLevel.BLOCK_SOME


def _read_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def _print_result(result):
    if result.get("status") != "success":
        print(f"FAILED: {result.get('message')}", file=sys.stderr)
        sys.exit(1)
    r = result["result"]
    print(json.dumps({"image_url": r.image_url, "prompt": r.prompt}, ensure_ascii=False))


def _add_common(p):
    p.add_argument("--book-id", type=int, required=True)
    p.add_argument("--model", choices=["auto", "fast", "quality", "ultra"], default="auto")
    p.add_argument("--safety", choices=["standard", "r15"], default="standard")
    p.add_argument("--aspect", type=str, default=None)


def main():
    parser = argparse.ArgumentParser(prog="illustration", description="Imagen 挿絵生成CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cover = sub.add_parser("cover", help="表紙生成")
    p_cover.add_argument("--title", type=str, default=None)
    p_cover.add_argument("--genre", type=str, default=None)
    p_cover.add_argument("--concept", type=str, default=None)
    p_cover.add_argument("--keywords", type=str, default=None)
    _add_common(p_cover)

    p_scene = sub.add_parser("scene", help="挿絵（シーン）生成")
    p_scene.add_argument("--episode", type=int, default=None)
    p_scene.add_argument("--genre", type=str, default=None)
    p_scene.add_argument("--text", type=str, default=None)
    p_scene.add_argument("--extract", action="store_true", help="本文から複数シーンを抽出")
    _add_common(p_scene)

    p_char = sub.add_parser("character", help="キャラクター立ち絵生成")
    p_char.add_argument("--name", type=str, default=None)
    p_char.add_argument("--role", type=str, default=None)
    p_char.add_argument("--appearance", type=str, default=None)
    p_char.add_argument("--traits", type=str, default=None)
    p_char.add_argument("--background", type=str, default=None)
    p_char.add_argument("--character-id", type=int, default=None)
    _add_common(p_char)

    args = parser.parse_args()
    if args.command == "cover":
        asyncio.run(_run_cover(args))
    elif args.command == "scene":
        asyncio.run(_run_scene(args))
    elif args.command == "character":
        asyncio.run(_run_character(args))


if __name__ == "__main__":
    main()
