"""v5.0 プロット入力〜章生成〜監査〜EPUB出力の全結合ライフサイクルテスト (v5.0 Step 23).

Unified Domain Model, Two-Tier Hybrid Auditor, PlatformCopyFormatter,
PureCommercialEpubBuilder が一体となって動作するライフサイクルを検証する。
"""
from __future__ import annotations

import pytest
from src.domain.schemas.project import ProjectCreateRequest
from src.domain.schemas.chapter import ChapterCreateRequest, SceneBeat, CliffhangerDef
from src.domain.schemas.character import CharacterCreateRequest
from src.domain.schemas.foreshadowing import ForeshadowingCreateRequest
from src.services.auditors.hybrid_auditor import TwoTierAuditor
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder


@pytest.mark.asyncio
async def test_v5_full_novel_lifecycle():
    # 1. プロジェクト・章（五感ビート・引き）・キャラ（心理葛藤・語尾）・伏線定義
    proj = ProjectCreateRequest(name="v5テスト大作", genre="fantasy", cheat_scale=4)
    char = CharacterCreateRequest(
        book_id=1,
        name="アリス",
        surface_persona="高飛車な令嬢",
        inner_conflict="本当は誰かに甘えたい",
        save_the_cat_event="落ちていた小鳥を巣に戻す",
        suffix_patterns=["ですわ$"],
    )
    chap = ChapterCreateRequest(
        book_id=1,
        episode_number=1,
        title="プロローグ",
        scene_beats=[SceneBeat(beat_num=1, physical_action="剣を抜く", sensory_tags=["sound"])],
        cliffhanger=CliffhangerDef(type="Shocking Truth", description="黒幕の正体"),
    )
    fore = ForeshadowingCreateRequest(book_id=1, title="銀の鍵", description="鍵の由来", planted_episode=1)

    assert proj.name and char.surface_persona and chap.cliffhanger.type == "Shocking Truth"
    assert fore.planted_episode == 1

    # 2. 執筆本文の監査 (Two-Tier Auditor: 静的語尾・NG検査 + 定性判定)
    body = "「何かが始まりますわ」\nアリスは銀の鍵を握りしめた。"
    report = await TwoTierAuditor.audit_chapter(body, forbidden_words=["NGワード"])
    assert report.static_audit.passed is True
    assert report.final_decision in ("pass", "patch_required")

    # 3. 投稿サイト整形 (なろう向けルビ・字下げ整形)
    narou_copy = PlatformCopyFormatter.format_for_platform(chap.title, body, platform="narou")
    assert "「何かが始まりますわ」" in narou_copy.body

    # 4. 商用EPUB 3生成
    epub = PureCommercialEpubBuilder().build_epub(
        title=proj.name,
        author="テスト作家",
        chapters=[{"title": chap.title, "body": body}],
    )
    assert len(epub) > 300
