#!/usr/bin/env python3
"""
scripts/generate_plot.py

ストーリープロット自動生成パイプライン
- novelize_prompt.j2 テンプレートを使用してプロットを生成
- genres.json のジャンル情報を活用して多様なシナリオを生成
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field, field_validator

from config import BASE_DIR

logger = logging.getLogger(__name__)

# =============================================================================
# データモデル定義 (Pydantic)
# =============================================================================


class GenreProfile(BaseModel):
    """ジャンルプロファイル（genres.json の各エントリに対応）"""
    name: str
    description: str
    evaluation_axes: List[str] = Field(default_factory=list)
    constraint_profile: str = ""
    keywords: List[str] = Field(default_factory=list)


class PlotGenerationInput(BaseModel):
    """プロット生成入力パラメータ"""
    genre: str = "standard"
    seed_keywords: List[str] = Field(default_factory=list)
    target_length: int = 3000
    style_key: str = "style_web_standard"
    write_rule_type: str = "RULE_SET_A"
    extra_context: str = ""
    target_episodes: int = 1
    temperature: float = 0.8
    max_tokens: int = 4000

    @field_validator("genre")
    def validate_genre(cls, v: str) -> str:
        valid_genres = {"light", "standard", "dark", "psychological_horror"}
        if v not in valid_genres:
            raise ValueError(f"Invalid genre: {v}. Must be one of {valid_genres}")
        return v


class PlotGenerationOutput(BaseModel):
    """プロット生成結果"""
    title: str
    logline: str
    synopsis: str
    beats: List[str] = Field(default_factory=list)
    characters: List[Dict[str, Any]] = Field(default_factory=list)
    genre_metadata: Dict[str, Any] = Field(default_factory=dict)
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# 設定・テンプレート読み込みユーティリティ
# =============================================================================


def load_genre_config() -> Dict[str, GenreProfile]:
    """
    config/data/genres.json を読み込み、ジャンルキー -> GenreProfile の辞書を返す
    """
    genres_path = BASE_DIR / "config" / "data" / "genres.json"
    logger.debug(f"Loading genre config from: {genres_path}")

    with open(genres_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    genres = {}
    for key, value in data.get("genres", {}).items():
        genres[key] = GenreProfile(
            name=value.get("name", key.upper()),
            description=value.get("description", ""),
            evaluation_axes=value.get("evaluation_axes", []),
            constraint_profile=value.get("constraint_profile", ""),
            keywords=value.get("keywords", []),
        )

    logger.info(f"Loaded {len(genres)} genre profiles: {list(genres.keys())}")
    return genres


# グローバルキャッシュ
_GENRE_CONFIG_CACHE: Optional[Dict[str, GenreProfile]] = None
_NOVELIZE_TEMPLATE_CACHE: Optional[Template] = None


def get_genre_config() -> Dict[str, GenreProfile]:
    """ジャンル設定をキャッシュ付きで取得"""
    global _GENRE_CONFIG_CACHE
    if _GENRE_CONFIG_CACHE is None:
        _GENRE_CONFIG_CACHE = load_genre_config()
    return _GENRE_CONFIG_CACHE


def load_novelize_template() -> Template:
    """
    prompts/templates/utility/novelize_prompt.j2 を読み込み、Jinja2 Template オブジェクトを返す
    """
    global _NOVELIZE_TEMPLATE_CACHE

    if _NOVELIZE_TEMPLATE_CACHE is not None:
        return _NOVELIZE_TEMPLATE_CACHE

    template_dir = BASE_DIR / "prompts" / "templates" / "utility"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("novelize_prompt.j2")
    _NOVELIZE_TEMPLATE_CACHE = template
    logger.debug("Loaded novelize_prompt.j2 template")
    return template


def get_genre_profile(genre_key: str) -> GenreProfile:
    """
    ジャンルキーから GenreProfile を取得
    存在しない場合は standard をフォールバックとして返す
    """
    config = get_genre_config()
    if genre_key not in config:
        logger.warning(f"Genre '{genre_key}' not found, falling back to 'standard'")
        genre_key = "standard"
    return config[genre_key]


# =============================================================================
# キーワード選択ロジック
# =============================================================================


def select_keywords_for_genre(
    genre_key: str,
    count: int = 5,
    user_keywords: Optional[List[str]] = None,
) -> List[str]:
    """
    ジャンルに基づいてキーワードを選択（ユーザー指定 + ランダム重み付け選択）
    """
    profile = get_genre_profile(genre_key)
    keywords = profile.keywords.copy()

    # ユーザー指定キーワードを優先
    selected = []
    if user_keywords:
        for kw in user_keywords:
            if kw in keywords:
                selected.append(kw)
                keywords.remove(kw)

    # 残りを重み付けランダム選択（evaluation_axes を重みのヒントとして使用）
    remaining = max(0, count - len(selected))
    if remaining > 0 and keywords:
        # evaluation_axes の長さを重みのベースとして使用（軸が多いジャンルほど多様性重視）
        weight_base = len(profile.evaluation_axes) or 1
        weights = [weight_base + random.random() for _ in keywords]
        selected.extend(random.choices(keywords, weights=weights, k=min(remaining, len(keywords))))

    logger.debug(f"Selected keywords for {genre_key}: {selected}")
    return selected


# =============================================================================
# プロンプト変数構築・レンダリング
# =============================================================================


def build_prompt_variables(
    input_params: PlotGenerationInput,
    genre_profile: GenreProfile,
    selected_keywords: List[str],
    style_instruction: str = "",
    rule_set_content: str = "",
    plots_text: str = "",
    scripts_text: str = "",
    char_context: str = "",
    prev_context: str = "",
) -> Dict[str, Any]:
    """
    novelize_prompt.j2 テンプレートに渡す変数 dict を構築
    
    Args:
        input_params: 生成パラメータ
        genre_profile: ジャンルプロファイル
        selected_keywords: 選択されたキーワードリスト
        style_instruction: スタイル指示（空の場合はデフォルト）
        rule_set_content: ルールセット内容（空の場合はデフォルト）
        plots_text: プロットテキスト
        scripts_text: スクリプトテキスト
        char_context: キャラクター文脈
        prev_context: 前回文脈
        
    Returns:
        テンプレート変数辞書
    """
    # デフォルトのスタイル指示・ルールセットを取得（PromptManager経由で後で解決）
    variables = {
        "style_instruction": style_instruction or f"【ジャンル: {genre_profile.name}】{genre_profile.description}",
        "rule_set_content": rule_set_content or genre_profile.constraint_profile or "【制約】特になし",
        "plots_text": plots_text or f"【キーワード】{', '.join(selected_keywords)}",
        "scripts_text": scripts_text or "",
        "char_context": char_context or "【キャラクター】未設定",
        "prev_context": prev_context or "【前回文脈】なし",
    }

    logger.debug(f"Built prompt variables for genre={input_params.genre}")
    return variables


def render_novelize_prompt(template: Template, variables: Dict[str, Any]) -> str:
    """
    Jinja2テンプレートをレンダリングしてプロンプト文字列を生成
    
    Args:
        template: Jinja2 Template オブジェクト
        variables: テンプレート変数
        
    Returns:
        レンダリングされたプロンプト文字列
    """
    rendered = template.render(**variables)
    logger.debug(f"Rendered prompt length: {len(rendered)} chars")
    return rendered


# =============================================================================
# LLM呼び出し・レスポンス処理
# =============================================================================


async def call_llm_for_plot(
    prompt: str,
    temperature: float = 0.8,
    max_tokens: int = 4000,
) -> str:
    """
    LLMを呼び出してプロット生成レスポンスを取得
    
    Args:
        prompt: 生成プロンプト
        temperature: 温度パラメータ
        max_tokens: 最大トークン数
        
    Returns:
        LLM生成テキスト
        
    Note:
        既存のLLMクライアント（services/llm_client.py等）がある場合はそれを使用。
        ここではシンプルなラッパーとして実装し、必要に応じて差し替え可能。
    """
    # TODO: 既存のLLMクライアントと統合
    # 現時点ではモック実装としてプロンプトをログ出力し、プレースホルダ返却
    logger.info(f"Calling LLM for plot generation (temp={temperature}, max_tokens={max_tokens})")
    logger.debug(f"Prompt preview: {prompt[:200]}...")

    # 実際の実装では以下のように既存クライアントを呼び出す想定
    # from services.llm_client import LLMClient
    # client = LLMClient()
    # response = await client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
    # return response.text

    # プレースホルダレスポンス（開発・テスト用）
    return """```json
{
  "title": "生成されたタイトル（プレースホルダ）",
  "logline": "ひとことで言うと...（プレースホルダ）",
  "synopsis": "あらすじのプレースホルダ。実際にはLLMが生成した内容が入ります。",
  "beats": ["ビート1: 導入", "ビート2: 発展", "ビート3: 転換", "ビート4: 結末"],
  "characters": [
    {"name": "主人公", "role": "main", "description": "主人公の説明"},
    {"name": "ヒロイン", "role": "support", "description": "ヒロインの説明"}
  ],
  "genre_metadata": {"genre": "standard", "keywords": []}
}
```"""


def parse_llm_plot_response(raw_response: str) -> PlotGenerationOutput:
    """
    LLMレスポンスから PlotGenerationOutput をパース
    
    Args:
        raw_response: LLM生成テキスト（JSONブロック含む想定）
        
    Returns:
        パース済み PlotGenerationOutput
        
    Raises:
        ValueError: パース失敗時
    """
    import re

    # JSONブロック抽出（```json ... ``` または ``` ... ```）
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL)

    if json_match:
        json_str = json_match.group(1)
    else:
        # JSONブロックがない場合、全体をJSONとしてパース試行
        json_str = raw_response.strip()

    try:
        data = json.loads(json_str)
        output = PlotGenerationOutput(**data)
        logger.debug("Successfully parsed LLM response as JSON")
        return output
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed, attempting heuristic fallback: {e}")
        # ヒューリスティックフォールバック: テキストから主要要素を抽出
        return _heuristic_parse_fallback(raw_response)


def _heuristic_parse_fallback(text: str) -> PlotGenerationOutput:
    """JSONパース失敗時のフォールバック解析"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    title = "無題のプロット"
    logline = ""
    synopsis = ""
    beats = []
    characters = []

    current_section = None
    for line in lines:
        if "タイトル" in line or "title" in line.lower():
            title = line.split(":", 1)[-1].strip() or title
        elif "ログライン" in line or "logline" in line.lower():
            logline = line.split(":", 1)[-1].strip()
        elif "あらすじ" in line or "synopsis" in line.lower():
            synopsis = line.split(":", 1)[-1].strip()
        elif line.startswith(("-", "・", "*", "1.", "2.", "3.")):
            beats.append(line.lstrip("-・*1234567890. "))

    if not synopsis:
        synopsis = text[:500]

    return PlotGenerationOutput(
        title=title,
        logline=logline or "ログライン未生成",
        synopsis=synopsis,
        beats=beats or ["ビート自動抽出失敗"],
        characters=characters,
        genre_metadata={"parse_method": "heuristic_fallback"},
    )


# =============================================================================
# バリデーション・制約適用・保存
# =============================================================================


def validate_generated_plot(output: PlotGenerationOutput) -> bool:
    """
    生成されたプロットの妥当性を検証
    
    Args:
        output: 生成結果
        
    Returns:
        妥当なら True
        
    Raises:
        ValueError: 重大な不備がある場合
    """
    errors = []

    # 必須フィールドチェック
    if not output.title or output.title.strip() == "":
        errors.append("title is empty")
    if not output.logline or output.logline.strip() == "":
        errors.append("logline is empty")
    if not output.synopsis or output.synopsis.strip() == "":
        errors.append("synopsis is empty")

    # 文字数チェック
    if len(output.synopsis) < 50:
        errors.append(f"synopsis too short ({len(output.synopsis)} chars)")
    if len(output.synopsis) > 10000:
        errors.append(f"synopsis too long ({len(output.synopsis)} chars)")

    # ビート数チェック
    if len(output.beats) < 3:
        errors.append(f"too few beats ({len(output.beats)})")
    if len(output.beats) > 20:
        errors.append(f"too many beats ({len(output.beats)})")

    if errors:
        error_msg = "; ".join(errors)
        logger.error(f"Plot validation failed: {error_msg}")
        raise ValueError(f"Plot validation failed: {error_msg}")

    logger.info("Plot validation passed")
    return True


def apply_genre_constraints(
    output: PlotGenerationOutput,
    genre_profile: GenreProfile,
) -> PlotGenerationOutput:
    """
    ジャンル制約プロファイルを生成結果に適用
    
    Args:
        output: 生成結果
        genre_profile: ジャンルプロファイル
        
    Returns:
        制約適用済みの生成結果（新しいインスタンス）
    """
    if not genre_profile.constraint_profile:
        return output

    # 制約プロファイルに基づく後処理
    # ここではシンプルにメタデータに記録し、実際のテキスト置換は
    # 専用のポリッシングパイプラインで行う想定
    metadata = output.genre_metadata.copy()
    metadata["applied_constraints"] = genre_profile.constraint_profile
    metadata["evaluation_axes"] = genre_profile.evaluation_axes

    # 禁止表現チェック（lightジャンル等）
    if "禁止" in genre_profile.constraint_profile or "封殺" in genre_profile.constraint_profile:
        metadata["has_strict_constraints"] = True

    # カタルシス必須チェック（dark, psychological_horror）
    if "カタルシス" in genre_profile.constraint_profile or "犠牲" in genre_profile.constraint_profile:
        metadata["requires_catharsis"] = True

    return PlotGenerationOutput(
        title=output.title,
        logline=output.logline,
        synopsis=output.synopsis,
        beats=output.beats,
        characters=output.characters,
        genre_metadata=metadata,
        generation_params=output.generation_params,
        created_at=output.created_at,
    )


def save_plot_output(
    output: PlotGenerationOutput,
    output_dir: Path,
    fmt: Literal["json", "md"] = "json",
) -> Path:
    """
    生成結果をファイル保存
    
    Args:
        output: 生成結果
        output_dir: 出力ディレクトリ
        fmt: 出力形式 ("json" or "md")
        
    Returns:
        保存されたファイルパス
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    genre = output.genre_metadata.get("genre", "unknown")

    if fmt == "json":
        file_path = output_dir / f"plot_{genre}_{timestamp}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output.model_dump(), f, ensure_ascii=False, indent=2)
    elif fmt == "md":
        file_path = output_dir / f"plot_{genre}_{timestamp}.md"
        md_content = _format_plot_as_markdown(output)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    logger.info(f"Saved plot output to: {file_path}")
    return file_path


def _format_plot_as_markdown(output: PlotGenerationOutput) -> str:
    """プロット結果をMarkdown形式で整形"""
    lines = [
        f"# {output.title}",
        "",
        f"**Logline**: {output.logline}",
        "",
        f"**Generated**: {output.created_at}",
        f"**Genre**: {output.genre_metadata.get('genre', 'unknown')}",
        "",
        "## あらすじ",
        "",
        output.synopsis,
        "",
        "## ビート（展開）",
        "",
    ]

    for i, beat in enumerate(output.beats, 1):
        lines.append(f"{i}. {beat}")

    if output.characters:
        lines.extend(["", "## 登場人物", ""])
        for char in output.characters:
            name = char.get("name", "名無し")
            role = char.get("role", "")
            desc = char.get("description", "")
            lines.append(f"- **{name}** ({role}): {desc}")

    if output.genre_metadata:
        lines.extend(["", "## ジャンルメタデータ", ""])
        for k, v in output.genre_metadata.items():
            lines.append(f"- **{k}**: {v}")

    return "\n".join(lines)


# =============================================================================
# メイン生成パイプライン（完全実装）
# =============================================================================


async def run_generate_plot(input_params: PlotGenerationInput) -> PlotGenerationOutput:
    """
    プロット生成メインパイプライン
    
    Args:
        input_params: 生成パラメータ
        
    Returns:
        生成されたプロット情報
        
    Raises:
        ValueError: 無効なジャンル等
        RuntimeError: LLM呼び出し失敗等
    """
    logger.info(f"Starting plot generation for genre={input_params.genre}")

    # 1. ジャンルプロファイル取得
    genre_profile = get_genre_profile(input_params.genre)

    # 2. キーワード選択
    selected_keywords = select_keywords_for_genre(
        input_params.genre,
        count=5,
        user_keywords=input_params.seed_keywords,
    )

    # 3. プロンプト変数構築
    # スタイル指示・ルールセットは PromptManager から取得する想定
    # ここでは簡易的に genre_profile から構築
    variables = build_prompt_variables(
        input_params=input_params,
        genre_profile=genre_profile,
        selected_keywords=selected_keywords,
    )

    # 4. テンプレートレンダリング
    template = load_novelize_template()
    prompt = render_novelize_prompt(template, variables)

    # 5. LLM呼び出し
    raw_response = await call_llm_for_plot(
        prompt,
        temperature=input_params.temperature,
        max_tokens=input_params.max_tokens,
    )

    # 6. レスポンスパース
    output = parse_llm_plot_response(raw_response)

    # 7. 生成パラメータ記録
    output.generation_params = {
        "genre": input_params.genre,
        "seed_keywords": input_params.seed_keywords,
        "selected_keywords": selected_keywords,
        "target_length": input_params.target_length,
        "style_key": input_params.style_key,
        "write_rule_type": input_params.write_rule_type,
        "temperature": input_params.temperature,
        "max_tokens": input_params.max_tokens,
    }
    output.genre_metadata["genre"] = input_params.genre

    # 8. バリデーション
    validate_generated_plot(output)

    # 9. ジャンル制約適用
    output = apply_genre_constraints(output, genre_profile)

    logger.info(f"Plot generation completed: {output.title}")
    return output


# =============================================================================
# CLI 引数パーサー・エントリーポイント
# =============================================================================


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI引数パーサーを構築"""
    import argparse
    parser = argparse.ArgumentParser(
        prog="generate_plot",
        description="ストーリープロット自動生成ツール - novelize_prompt.j2 と genres.json を使用してプロットを生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な生成（standardジャンル）
  python scripts/generate_plot.py

  # ジャンル指定・キーワード指定
  python scripts/generate_plot.py --genre light --keywords ほのぼの,スローライフ,カフェ

  # 複数生成・出力形式指定
  python scripts/generate_plot.py --genre dark --count 3 --format md --output-dir ./outputs/plots

  # カスタムパラメータ
  python scripts/generate_plot.py --genre psychological_horror --length
    --target-length 5000 --temperature 0.9 --max-tokens 6000
        """,
    )

    # 基本パラメータ
    parser.add_argument(
        "--genre",
        type=str,
        default="standard",
        choices=["light", "standard", "dark", "psychological_horror"],
        help="生成するジャンル (default: standard)",
    )

    parser.add_argument(
        "--keywords",
        type=str,
        default="",
        help="カンマ区切りで指定するシードキーワード (例: ほのぼの,スローライフ,カフェ)",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="生成するプロット数 (default: 1)",
    )

    # 出力設定
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/plots",
        help="出力ディレクトリ (default: outputs/plots)",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "md"],
        default="json",
        help="出力形式 (default: json)",
    )

    # 生成パラメータ
    parser.add_argument(
        "--target-length",
        type=int,
        default=3000,
        help="目標文字数 (default: 3000)",
    )

    parser.add_argument(
        "--style-key",
        type=str,
        default="style_web_standard",
        help="スタイルキー (default: style_web_standard)",
    )

    parser.add_argument(
        "--write-rule-type",
        type=str,
        default="RULE_SET_A",
        help="ライトルールタイプ (default: RULE_SET_A)",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
        help="LLM温度パラメータ (default: 0.8)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="最大トークン数 (default: 4000)",
    )

    parser.add_argument(
        "--target-episodes",
        type=int,
        default=1,
        help="対象エピソード数 (default: 1)",
    )

    # その他
    parser.add_argument(
        "--extra-context",
        type=str,
        default="",
        help="追加文脈情報",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のLLM呼び出しを行わず、プロンプトのみ表示",
    )

    return parser


def parse_keywords(keyword_str: str) -> List[str]:
    """カンマ区切りキーワード文字列をリストに変換"""
    if not keyword_str:
        return []
    return [kw.strip() for kw in keyword_str.split(",") if kw.strip()]


async def run_cli_generation(args: argparse.Namespace) -> List[PlotGenerationOutput]:
    """CLI引数に基づいてプロット生成を実行"""
    # キーワードパース
    seed_keywords = parse_keywords(args.keywords)

    # 入力パラメータ構築
    input_params = PlotGenerationInput(
        genre=args.genre,
        seed_keywords=seed_keywords,
        target_length=args.target_length,
        style_key=args.style_key,
        write_rule_type=args.write_rule_type,
        extra_context=args.extra_context,
        target_episodes=args.target_episodes,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    output_dir = Path(args.output_dir)
    results = []

    for i in range(args.count):
        logger.info(f"Generating plot {i+1}/{args.count} (genre={args.genre})")

        if args.dry_run:
            # ドライラン: プロンプトのみ生成して表示
            genre_profile = get_genre_profile(args.genre)
            selected_keywords = select_keywords_for_genre(args.genre, count=5, user_keywords=seed_keywords)
            variables = build_prompt_variables(input_params, genre_profile, selected_keywords)
            template = load_novelize_template()
            prompt = render_novelize_prompt(template, variables)
            print(f"\n=== DRY RUN: Plot {i+1} Prompt ===")
            print(prompt)
            print("=== END DRY RUN ===\n")
            continue

        # 実際の生成
        try:
            output = await run_generate_plot(input_params)
            output.genre_metadata["generation_index"] = i + 1
            output.genre_metadata["total_generations"] = args.count

            # 保存
            saved_path = save_plot_output(output, output_dir, fmt=args.format)
            logger.info(f"Saved: {saved_path}")

            results.append(output)

            # 簡易サマリ表示
            print(f"  ✓ Plot {i+1}: {output.title} ({len(output.synopsis)} chars, {len(output.beats)} beats)")

        except Exception as e:
            logger.error(f"Generation {i+1} failed: {e}")
            print(f"  ✗ Plot {i+1} failed: {e}")

    return results


def main():
    """CLI エントリーポイント"""
    parser = build_arg_parser()
    args = parser.parse_args()

    # ログレベル設定
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info(f"Starting plot generation CLI: genre={args.genre}, count={args.count}")

    # 非同期実行
    import asyncio
    try:
        results = asyncio.run(run_cli_generation(args))

        if results:
            print("\n=== Generation Complete ===")
            print(f"Generated {len(results)} plot(s)")
            print(f"Output directory: {Path(args.output_dir).absolute()}")
            print(f"Format: {args.format}")
        elif not args.dry_run:
            print("\n=== Generation Failed ===")
            print("No plots were successfully generated.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Generation interrupted by user")
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error in main")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    import sys
    main()

