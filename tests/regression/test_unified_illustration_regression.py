"""統合イラスト生成エンジン リグレッション防止テスト（R-01 〜 R-18）。

本ファイルは「守りたい仕様」を1行ずつコードに固定する。違反したら即FAILする。

 Companion: tests/regression/test_manga_regression.py
 本计划書: plans/PLAN_I1_UNIFIED_ILLUSTRATION_ENGINE_24STEPS.md

|ID  |守りたい仕様
|:---|:---
|R-01|全 IllustrationType が既定モデルを使う / Legacy は image_service 注入時のみ
|R-02|既定モデルキーは nanobanana2lite（Imagen3件も登録のまま）
|R-03|全戦略プロンプトが文字描画を禁止（漫画系はフキダシも）
|R-04|全クライアントが Protocol に適合し、モデル差替えで挙動不変
|R-05|品質ゲートは「記録」であって「生成失敗」ではない
|R-06|Pillow なし環境でも生成は成功する
|R-07|出力は {root}/{book_id}/ 配下。ルート非漏洩
|R-08|R15_CONTENT 时は全戦略に "R15"、非R15時は無し
|R-09|設定スイッチ（enableIllustration / 各 generate*）が機能する
|R-10|panels クランプ（yonkoma 3-6 / manga24 1-24）
|R-11|ロジックの二重定義をしない（カメラワーク/スタイル/安全修飾の単一ソース）
|R-12|CI で外部ネットワークに一切出ない
|R-13|create_illustration へ book_id/type/model/safety_level が渡る
|R-14|enableErotic→R15 / visual_textual_synergy 再生成の入口が残る
|R-15|points→リクエスト変換が例外を投げない
|R-16|Imagen モデルIDが config/image_models.py 以外に現れない
|R-17|環境変数1つでモデル差し替えできる
|R-18|冪等性（同一入力2回でファイル衝突しない）
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from config.image_models import (
    DEFAULT_IMAGE_MODEL,
    ENV_MODEL_KEY,
    IMAGE_MODEL_CATALOG,
    get_image_model_id,
    get_image_model_spec,
    resolve_model_key_from_env,
)
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
    SafetyLevel,
)
from src.services.illustration.clients import ImageClientProtocol, build_client
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.strategies import get_strategy
from src.services.illustration.wiring import (
    build_unified_illustration_generator,
    self_check,
)
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator

ALL_TYPES = list(IllustrationType)
MULTI_PANEL = [IllustrationType.YONKOMA, IllustrationType.MANGA_24PANEL]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _config(tmp_path: Path, **kwargs) -> UnifiedIllustrationConfig:
    params = {"output_root": tmp_path / "out", "mock_mode": True, "max_retries": 0}
    params.update(kwargs)
    return UnifiedIllustrationConfig(**params)


def _generator(tmp_path: Path, **kwargs) -> UnifiedIllustrationGenerator:
    return build_unified_illustration_generator(
        output_root=tmp_path / "out", mock_mode=True, max_retries=0, **kwargs
    )


def _request(
    illo_type: IllustrationType,
    book_id: int = 1,
    safety_level: SafetyLevel = SafetyLevel.BLOCK_SOME,
    **kwargs,
) -> IllustrationRequest:
    params = {
        "book_id": book_id,
        "illustration_type": illo_type,
        "episode_number": 1,
        "scene_text": "夜空の下、主人公が剣を抜いた。",
        "book_context": {
            "title": "天空の城",
            "genre": "ファンタジー",
            "characters": ["タロウ"],
        },
        "safety_level": safety_level,
        "panels": 24 if illo_type == IllustrationType.MANGA_24PANEL else 6,
    }
    params.update(kwargs)
    return IllustrationRequest(**params)


# =====================================================================
# R-01 / R-02 / R-17: 単一モデル統一と差し替え
# =====================================================================


def test_regression_default_model_used_for_all_types(tmp_path):
    """【リグレッション防止】R-01: 全 IllustrationType が既定モデルを使う。

    壊 Illness: 種別ごとにモデルが散ると、コスト試算・品質基準・
    「NanoBanana2Lite 統一」という決定が全て破綻する。
    """
    generator = _generator(tmp_path)
    for illo_type in ALL_TYPES:
        result = asyncio.run(generator.generate(_request(illo_type)))
        assert result.model_used == get_image_model_id(DEFAULT_IMAGE_MODEL), (
            f"{illo_type.value} が既定モデル以外（{result.model_used}）を使っている"
        )


def test_regression_legacy_client_only_when_image_service_injected(tmp_path):
    """【リグレッション防止】R-01: Legacy 経路は旧 ImageService 注入時のみ。

    壊れると「統一モデル」_policy が形骸化し、Imagen が混在する。
    """
    default_gen = _generator(tmp_path / "a")
    assert default_gen.client.name == "gemini_image"

    legacy_gen = UnifiedIllustrationGenerator(
        config=_config(tmp_path / "b"), image_service=object()
    )
    assert legacy_gen.client.name == "legacy_imagen"


def test_regression_agent_uses_unified_model_without_image_service(tmp_path):
    """【リグレッション防止】R-01: Agent も既定モデルを使う。

    `image_service` を渡さない（旧経路を使わない）構成では NanoBanana2Lite。
    """
    from src.agents.illustration_agent import IllustrationAgent

    agent = IllustrationAgent(
        config=_config(tmp_path), repo=None, llm=None, image_service=None
    )
    result = asyncio.run(agent.run(request=_request(IllustrationType.COVER)))
    assert result["status"] == "success"
    assert result["result"].model_used == get_image_model_id(DEFAULT_IMAGE_MODEL)


def test_regression_default_model_key_is_nanobanana2lite(monkeypatch):
    """【リグレッション防止】R-02: 環境変数未設定なら nanobanana2lite。"""
    monkeypatch.delenv(ENV_MODEL_KEY, raising=False)
    assert resolve_model_key_from_env() == "nanobanana2lite"
    assert DEFAULT_IMAGE_MODEL == "nanobanana2lite"


def test_regression_imagen_models_still_registered():
    """【リグレッション防止】R-02: Imagen 3 tier は切替手段として残る。"""
    for key in ("imagen_fast", "imagen_quality", "imagen_ultra"):
        assert key in IMAGE_MODEL_CATALOG
        assert get_image_model_spec(key).client == "legacy_imagen"


def test_regression_env_var_switch_changes_model_used(tmp_path, monkeypatch):
    """【リグレッション防止】R-17: 環境変数1つでモデルが差し替えられる。

    壊れると「後でモデルを easily 交換できる」前提が崩壊する。
    """
    monkeypatch.setenv(ENV_MODEL_KEY, "imagen_ultra")
    config = UnifiedIllustrationConfig(output_root=tmp_path)
    assert config.model_key == "imagen_ultra"
    generator = UnifiedIllustrationGenerator(
        config=config, client=build_client("imagen_ultra", mock_mode=True)
    )
    result = asyncio.run(generator.generate(_request(IllustrationType.COVER)))
    assert result.model_used == "imagen-4.0-ultra-generate-001"


def test_regression_self_check_never_raises(monkeypatch):
    """【リグレッション防止】起動 self-check は不正値でも例外を出さない。"""
    monkeypatch.setenv(ENV_MODEL_KEY, "totally-unknown-model")
    report = self_check()
    assert report["ok"] is True
    assert report["model_key"] == DEFAULT_IMAGE_MODEL


# =====================================================================
# R-03 / R-08 / R-10: プロンプト規約
# =====================================================================


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_regression_all_strategies_forbid_text(illo_type):
    """【リグレッション防止】R-03: 全戦略が文字描画を禁止する。

    壊れると文字化け（豆腐）Translator画像の再生成コストが発生する。
    """
    strategy = get_strategy(illo_type, _config(Path(".")))
    prompt = strategy.build_prompt(_request(illo_type))
    lowered = prompt.lower()
    assert "no text" in lowered
    assert "letters" in lowered


@pytest.mark.parametrize("illo_type", MULTI_PANEL)
def test_regression_manga_strategies_forbid_speech_bubbles(illo_type):
    """【リグレッション防止】R-03: 漫画シートはフキダシも禁止する。"""
    strategy = get_strategy(illo_type, _config(Path(".")))
    prompt = strategy.build_prompt(_request(illo_type)).lower()
    assert "no speech bubbles" in prompt


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_regression_r15_modifier_present_for_all_types(illo_type):
    """【リグレッション防止】R-08: R15 时は全戦略プロンプトに R15 が乗る。"""
    strategy = get_strategy(illo_type, _config(Path(".")))
    prompt = strategy.build_prompt(_request(illo_type, safety_level=SafetyLevel.R15_CONTENT))
    assert "r15" in prompt.lower()


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_regression_non_r15_has_no_r15_modifier(illo_type):
    """【リグレッション防止】R-08: 非R15 に R15 表現を混ぜない。"""
    strategy = get_strategy(illo_type, _config(Path(".")))
    prompt = strategy.build_prompt(_request(illo_type, safety_level=SafetyLevel.BLOCK_SOME))
    assert "r15" not in prompt.lower()


def test_regression_yonkoma_panels_clamped_3_to_6():
    """【リグレッション防止】R-10: 6コマ要約は 3..6 コマ。"""
    from src.services.illustration.strategies import Yonkoma6Strategy

    assert Yonkoma6Strategy.clamp_panels(0) == 3
    assert Yonkoma6Strategy.clamp_panels(2) == 3
    assert Yonkoma6Strategy.clamp_panels(4) == 4
    assert Yonkoma6Strategy.clamp_panels(99) == 6
    assert Yonkoma6Strategy.clamp_panels(None) == 6


def test_regression_manga24_panels_clamped_to_24():
    """【リグレッション防止】R-10: 24コマシートは 1..24 コマ。"""
    from src.services.illustration.strategies import Manga24Strategy

    assert Manga24Strategy.clamp_panels(0) == 1
    assert Manga24Strategy.clamp_panels(1) == 1
    assert Manga24Strategy.clamp_panels(24) == 24
    assert Manga24Strategy.clamp_panels(99) == 24
    assert Manga24Strategy.clamp_panels(None) == 24


def test_regression_manga24_grid_is_4x6_with_24_panels():
    """【リグレッション防止】24コマは 4x6=24 コマの1枚であること。"""
    from src.services.illustration.strategies import Manga24Strategy

    strategy = Manga24Strategy(_config(Path(".")))
    prompt = strategy.build_prompt(_request(IllustrationType.MANGA_24PANEL, panels=24))
    assert "24 panels" in prompt
    assert "4x6 grid layout" in prompt
    for index in range(1, 25):
        assert f"Panel {index} " in prompt


# =====================================================================
# R-04: クライアント境界
# =====================================================================


@pytest.mark.parametrize("model_key", sorted(IMAGE_MODEL_CATALOG.keys()))
def test_regression_all_clients_satisfy_protocol(model_key):
    """【リグレッション防止】R-04: 全カタログモデルでクライアントを組み立てられる。"""
    client = build_client(model_key, mock_mode=True)
    assert isinstance(client, ImageClientProtocol)
    assert client.model_id == IMAGE_MODEL_CATALOG[model_key].model_id


# =====================================================================
# R-05 / R-06: 後処理の縮退
# =====================================================================


def test_regression_quality_failure_does_not_fail_generation(tmp_path):
    """【リグレッション防止】R-05: 品質ゲートNGでも生成は成功扱い。

    壊れると「1枚生成するたびに再試行」になり API コストが爆する。
    """
    generator = _generator(tmp_path)
    result = asyncio.run(generator.generate(_request(IllustrationType.EPISODE)))
    assert result.image_path.exists()
    assert result.quality is not None
    assert result.quality["is_valid"] is False  # mock は 1x1 なので不合格
    assert result.quality["reasons"]


def test_regression_quality_gate_can_be_disabled(tmp_path):
    """【リグレッション防止】R-05: 品質ゲートは任意で無効化できる。"""
    generator = _generator(tmp_path, enable_quality_gate=False)
    result = asyncio.run(generator.generate(_request(IllustrationType.EPISODE)))
    assert result.quality is None


def test_regression_generation_succeeds_without_pillow(tmp_path, monkeypatch):
    """【リグレッション防止】R-06: Pillow なし環境でも生成は成功する。

    壊れると Pillow 未導入 suddenlyの環境でイラスト機能が全滅する。
    """
    import builtins

    real_import = builtins.__import__

    def _blocked(name, *args, **kwargs):
        if name.startswith("PIL"):
            raise ImportError("No module named 'PIL'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    generator = _generator(tmp_path, enable_quality_gate=True, enable_upscale=True)
    result = asyncio.run(generator.generate(_request(IllustrationType.EPISODE)))
    assert result.image_path.exists()
    assert result.quality["skipped"] is True


# =====================================================================
# R-07 / R-18: 出力先と冪等性
# =====================================================================


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_regression_output_is_scoped_by_book_id(illo_type, tmp_path):
    """【リグレッション防止】R-07: 出力は book_id 配下へ整理される。

    壊れると static/illustrations/ 直下にAggregated、书籍ごとの弛緩が管理不能になる。
    """
    generator = _generator(tmp_path)
    result = asyncio.run(generator.generate(_request(illo_type, book_id=77)))
    assert result.image_path.parent == tmp_path / "out" / "77"


def test_regression_no_file_leak_in_root(tmp_path, monkeypatch):
    """【リグレッション防止】R-07: リポジトリルートへファイルを漏らさない。"""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    before = {p.name for p in workdir.iterdir()}

    generator = build_unified_illustration_generator(
        output_root=Path("static/illustrations"), mock_mode=True, max_retries=0
    )
    asyncio.run(generator.generate(_request(IllustrationType.MANGA_24PANEL)))

    assert {p.name for p in workdir.iterdir()} - before == {"static"}


def test_regression_repeated_generation_has_no_collision(tmp_path):
    """【リグレッション防止】R-18: 同一入力2回でもファイル名が衝突しない。"""
    generator = _generator(tmp_path)
    request = _request(IllustrationType.EPISODE)
    first = asyncio.run(generator.generate(request))
    second = asyncio.run(generator.generate(request))
    assert first.image_path != second.image_path
    assert first.image_path.exists() and second.image_path.exists()


# =====================================================================
# R-09: 設定スイッチ
# =====================================================================


class _StubReporter:
    def __init__(self):
        self.messages: list[str] = []

    def update_progress(self, current, total, message=""):
        self.messages.append(message)

    def report(self, message, level="info"):
        self.messages.append(message)


def _make_workflow(settings_enabled: bool = True, chapters: int = 6):
    from src.backend.workflows.illustration_workflow import IllustrationWorkflow

    generated: list[IllustrationRequest] = []

    class _Agent:
        repo = None

        async def run(self, request):
            generated.append(request)
            return {
                "status": "success",
                "result": IllustrationResult(
                    request=request,
                    image_url=f"/static/illustrations/{request.illustration_type.value}.png",
                    prompt="p",
                    model_used="gemini-3.1-flash-lite-image",
                    generation_time_ms=1,
                ),
                "prompt": "p",
            }

        async def generate_episode_yonkoma(self, episode_text, request, panels=6):
            generated.append(request)
            return IllustrationResult(
                request=request,
                image_url="/static/illustrations/y.png",
                prompt="p",
                model_used="gemini-3.1-flash-lite-image",
                generation_time_ms=1,
            )

    class _Repo:
        async def get_chapters(self, book_id):
            return [
                type("Ch", (), {"number": i, "content": f"第{i}話。本文。" * 20})()
                for i in range(1, chapters + 1)
            ]

        async def get_chapter(self, book_id, ep_num):
            return type("Ch", (), {"content": f"第{ep_num}話。本文。" * 20})()

        async def get_book(self, book_id):
            return type("Book", (), {"title": "T", "genre": "ファンタジー"})()

    workflow = IllustrationWorkflow(illustration_agent=_Agent(), repo=_Repo())
    return workflow, generated


def test_regression_illustration_disabled_generates_nothing():
    """【リグレッション防止】R-09: `enableIllustration=False` では何も作らない。

    壊れるとユーザー設定が無視され、課金が調停される。
    """
    workflow, generated = _make_workflow()
    result = asyncio.run(
        workflow.execute(_StubReporter(), book_id=1, settings={"enableIllustration": False})
    )
    assert result["status"] == "skipped"
    assert generated == []


def test_regression_each_generation_switch_is_honored():
    """【リグレッション防止】R-09: 各 generate* スイッチが機能する。"""
    from src.models.illustration import IllustrationType as T

    # 什么都不开 → 表紙のみ
    workflow, generated = _make_workflow()
    asyncio.run(workflow.execute(_StubReporter(), book_id=1, settings={"enableIllustration": True}))
    assert [r.illustration_type for r in generated] == [T.COVER]

    # 封面を切って挿絵を開く → interval=3 なので 1,4 話
    workflow, generated = _make_workflow(chapters=6)
    asyncio.run(
        workflow.execute(
            _StubReporter(),
            book_id=1,
            settings={
                "enableIllustration": True,
                "generateCover": False,
                "generateEpisodeIllustrations": True,
                "episodeInterval": 3,
            },
        )
    )
    assert [r.illustration_type for r in generated] == [T.EPISODE, T.EPISODE]
    assert [r.episode_number for r in generated] == [1, 4]


def test_regression_manga24_switch_generates_sheets():
    """【リグレッション防止】R-09: `generateManga24` で24コマシートが生成される。"""
    from src.models.illustration import IllustrationType as T

    workflow, generated = _make_workflow(chapters=3)
    asyncio.run(
        workflow.execute(
            _StubReporter(),
            book_id=1,
            settings={
                "enableIllustration": True,
                "generateCover": False,
                "generateEpisodeIllustrations": True,
                "episodeInterval": 3,
                "generateManga24": True,
            },
        )
    )
    assert T.MANGA_24PANEL in [r.illustration_type for r in generated]
    manga = [r for r in generated if r.illustration_type == T.MANGA_24PANEL]
    assert manga[0].panels == 24
    assert manga[0].aspect_ratio == "2:3"


# =====================================================================
# R-11 / R-16: 単一ソース・ハードコード禁止
# =====================================================================


def test_regression_no_duplicate_cover_variations():
    """【リグレッション防止】R-11: 表紙のカメラワークは既存定数を共有する。

    二重定義すると片方だけが更新され、仕様が乖離する。
    """
    from src.services.illustration.prompts import _COVER_VARIATIONS
    from src.services.illustration.strategies.cover import CoverStrategy

    strategy = CoverStrategy(_config(Path(".")))
    for index, expected in enumerate(_COVER_VARIATIONS):
        prompt = strategy.build_prompt(
            _request(IllustrationType.COVER, episode_number=index)
        )
        assert expected in prompt


def test_regression_genre_style_has_single_source():
    """【リグレッション防止】R-11: ジャンルスタイルは `prompts._genre_hint` のみ。"""
    from src.services.illustration.prompts import _genre_hint
    from src.services.illustration.strategies.cover import CoverStrategy

    strategy = CoverStrategy(_config(Path(".")))
    for genre in ("ファンタジー", "ラブコメ", "SF", "ホラー", "ミステリー"):
        assert strategy._genre_style(genre) == _genre_hint(genre)


_IMAGEN_ID_PATTERN = re.compile(r"imagen-\d+\.\d+[\w\-]*")

#: 統合エンジンのコード面（ここにモデルID直書きを禁じる）
#: 旧 Imagen 专用モジュール（`config/imagen_models.py` / `src/services/image_service.py` /
#: `src/core/spi/image/` / `src/infrastructure/repositories/illustration.py` /
#: `src/backend/database/models.py`）は移行対象外のレガシーとして除外する。
_UNIFIED_SUBSYSTEM_PATHS = (
    REPO_ROOT / "src" / "services" / "illustration",
    REPO_ROOT / "src" / "agents" / "illustration_agent.py",
    REPO_ROOT / "src" / "backend" / "workflows" / "illustration_workflow.py",
)


def test_regression_no_imagen_model_id_outside_catalog():
    """【リグレッション防止】R-16: Imagen モデルIDはカタログ以外に出さない。

    壊れるとモデル差し替え（1行運用）が不可能になる。
    """
    offenders: list[str] = []
    for target in _UNIFIED_SUBSYSTEM_PATHS:
        files = [target] if target.is_file() else list(target.rglob("*.py"))
        for path in files:
            if path.name == "imagen_models.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in _IMAGEN_ID_PATTERN.finditer(text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {match.group()}")
    assert not offenders, (
        "Imagen モデルIDが config/image_models.py 以外にあります: " + ", ".join(offenders)
    )


def test_regression_no_hardcoded_cost_in_engine():
    """【リグレッション防止】R-11: コストはカタログ参照（エンジンに直書きしない）。"""
    text = (REPO_ROOT / "src" / "services" / "illustration" / "unified_generator.py").read_text(
        encoding="utf-8"
    )
    assert "0.034" not in text, "コスト单价はカタログ（config/image_models.py） 管理すること"


# =====================================================================
# R-12: ネットワーク遮断
# =====================================================================


def _is_external(address) -> bool:
    """ループバック（127.0.0.1 / ::1 / localhost）以外の接続か判定する。"""
    if isinstance(address, tuple) and address:
        host = str(address[0])
    else:
        host = str(address)
    return host not in ("127.0.0.1", "::1", "localhost", "0.0.0.0")


def test_regression_no_network_access_in_generation(tmp_path, monkeypatch):
    """【リグレッション防止】R-12: 生成処理は外部ネットワークへ触らない。

    CI が意図せず課金される・Flaky になるのを防ぐ。ループバック
    （テスト基盤の内部通信）は許容し、外部接続のみを禁止する。
    """
    import socket

    attempts: list[object] = []
    real_connect = socket.socket.connect
    real_create = socket.create_connection

    def _spy_connect(self, address, *args, **kwargs):
        attempts.append(address)
        return real_connect(self, address, *args, **kwargs)

    def _spy_create(address, *args, **kwargs):
        attempts.append(address)
        return real_create(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", _spy_connect)
    monkeypatch.setattr(socket, "create_connection", _spy_create)

    generator = _generator(tmp_path)
    for illo_type in ALL_TYPES:
        result = asyncio.run(generator.generate(_request(illo_type)))
        assert result.image_path.exists()

    external = [a for a in attempts if _is_external(a)]
    assert not external, f"イラスト生成が外部ネットワークへ接続した: {external}"


# =====================================================================
# R-13 / R-14: 永続化・再生成入口
# =====================================================================


def test_regression_persist_call_shape(tmp_path):
    """【リグレッション防止】R-13: create_illustration へ必要な値が渡る。

    壊れると成果物とDBの紐付けが切れ、UI から画像が找不到。
    """
    from src.agents.illustration_agent import IllustrationAgent

    calls: list[dict] = []

    class _Repo:
        async def create_illustration(self, **kwargs):
            calls.append(kwargs)
            return 123

    agent = IllustrationAgent(config=_config(tmp_path), repo=_Repo(), llm=None)
    result = asyncio.run(agent.run(request=_request(IllustrationType.EPISODE, book_id=9)))
    assert result["status"] == "success"
    assert result["result"].illustration_id == 123
    assert calls, "create_illustration が呼ばれていない"
    payload = calls[0]
    for key in ("book_id", "illustration_type", "model", "safety_level", "generation_time_ms"):
        assert key in payload, f"create_illustration に {key} が渡っていない"
    assert payload["book_id"] == 9
    assert payload["illustration_type"] == "episode"
    assert payload["model"] == get_image_model_id(DEFAULT_IMAGE_MODEL)


def test_regression_persist_failure_does_not_raise(tmp_path):
    """【リグレッション防止】R-13: 永続化失敗でも生成結果は返す。"""
    from src.agents.illustration_agent import IllustrationAgent

    class _Repo:
        async def create_illustration(self, **kwargs):
            raise RuntimeError("db down")

    agent = IllustrationAgent(config=_config(tmp_path), repo=_Repo(), llm=None)
    result = asyncio.run(agent.run(request=_request(IllustrationType.COVER)))
    assert result["status"] == "success"
    assert result["result"].illustration_id is None


def test_regression_erotic_setting_maps_to_r15():
    """【リグレッション防止】R-14: `enableErotic` は R15_CONTENT に写像される。"""

    workflow, _ = _make_workflow()
    assert workflow._determine_safety_level({"enableErotic": True}) == SafetyLevel.R15_CONTENT
    assert workflow._determine_safety_level({}) == SafetyLevel.BLOCK_SOME


def test_regression_regeneration_focus_entrypoint_exists(tmp_path):
    """【リグレッション防止】R-14: visual_textual_synergy の再生成入口が残る。

    壊れると BookScore の visual_textual_synergy 次元が自動修復されなくなる。
    """
    from src.agents.illustration_agent import IllustrationAgent

    agent = IllustrationAgent(config=_config(tmp_path), repo=None, llm=None)
    request = _request(IllustrationType.EPISODE)
    out = asyncio.run(
        agent.regenerate_prompts(
            request,
            params={"refocus_on_text_entities": True, "match_emotional_tone": True},
        )
    )
    assert out["status"] == "success"
    assert out["focus"] == "visual_textual_synergy"
    assert out["enhancements_applied"]
    assert out["enhanced_prompt"].startswith(out["original_prompt"])


# =====================================================================
# R-15: points → リクエスト変換の例外安全性
# =====================================================================


def _workflow_context(**kwargs):
    """`WorkflowContext` の必須フィールドを満たすインスタンスを作る。"""
    from src.services.pipeline_base import WorkflowContext

    params = {
        "genre": "ファンタジー",
        "keywords": "魔法,剣",
        "archetype_key": "チート主人公",
        "target_eps": 3,
        "initial_limit": 3,
        "word_count": 2000,
    }
    params.update(kwargs)
    return WorkflowContext(**params)


def test_regression_point_conversion_never_raises(tmp_path):
    """【リグレッション防止】R-15: 不正な挿絵ポイントでも変換は例外を投げない。

    壊れると挿絵1点の不備で小説パイプライン全体が停止する。
    """
    from src.models.illustration_point import IllustrationPoint
    from src.services.pipeline_steps import IllustrationPointGenerationStep

    step = IllustrationPointGenerationStep(illustration_generator=_generator(tmp_path))
    ctx = _workflow_context(book_id=1, enable_illustration=True)
    ctx.illustration_points = [
        IllustrationPoint(
            id="IP-001",
            page="口絵1",
            scene_description="主人公が足を踏み入れる",
            composition="中央",
            props="剣",
            expressions={"主人公": "決意"},
            background="城",
        ),
        IllustrationPoint(
            id="IP-002",
            page="",  # 空ページでも変換できる
            scene_description="",
            composition="",
            props="",
            expressions={},
            background="",
        ),
        object(),  # 型違いの要素
    ]
    requests = step._build_requests_from_points(ctx)
    assert len(requests) == 2
    assert all(r.book_id == 1 for r in requests)
    assert requests[0].scene_text


def test_regression_zero_points_proceeds(tmp_path):
    """【リグレッション防止】R-15: 挿絵ポイントが0件でもStepは True を返す。"""
    from src.services.pipeline_steps import IllustrationPointGenerationStep

    step = IllustrationPointGenerationStep(illustration_generator=_generator(tmp_path))

    class _Engine:
        class repo:  # noqa: N801
            class bible:  # noqa: N801
                @staticmethod
                async def get_by_book_id(book_id):
                    return type("Bible", (), {"characters": []})()

            class plot:  # noqa: N801
                @staticmethod
                async def get_all_plots(book_id):
                    return []

            class episode:  # noqa: N801
                @staticmethod
                async def get_all_by_book_id(book_id):
                    return []

    ctx = _workflow_context(book_id=1, enable_illustration=True)
    assert asyncio.run(step.execute(ctx, _Engine(), _StubReporter())) is True
    assert ctx.illustration_points == []


def test_regression_image_generation_is_opt_in():
    """【リグレッション防止】R-15: 既定では挿絵画像生成しない（挙動不変）。"""
    assert _workflow_context().enable_illustration_generation is False
    assert (
        _workflow_context(enable_illustration_generation=True).enable_illustration_generation
        is True
    )
