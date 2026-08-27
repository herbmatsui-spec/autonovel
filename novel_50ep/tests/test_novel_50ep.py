"""Comprehensive unit and integration test suite for the 50-episode pipeline (Phases A through I)."""

import csv
import json
from pathlib import Path
import pytest
import yaml

from novel_50ep.batch_runner import (
    clean_novel_text,
    dedup_sentence_endings,
    normalize_names,
    BatchRunner,
)
from novel_50ep.config import (
    CLIFFS_FILE,
    EMOTIONS_FILE,
    FINAL_DIR,
    LOG_DIR,
    MANGA_PROMPTS_DIR,
    ILLUST_SAFETY,
    MAX_CHARS,
    METADATA_FILE,
    MIN_CHARS,
    OUTPUT_DIR,
    PART_TARGETS,
    PART_TOLERANCE,
    PROGRESS_FILE,
    SCORES_FILE,
    TARGET_CHARS,
    TEMPLATE_FILE,
    TOTAL_EPISODES,
    WORLD_FILE,
    enable_manga_prompts,
    is_manga_enabled,
)
from novel_50ep.count_chars import (
    check_cliff,
    check_range,
    count_chars,
    detect_dup,
    extract_parts,
    require_words,
    validate_episode,
)
from novel_50ep.foreshadow_manager import ForeshadowManager
from novel_50ep.generator import MangaBuilder, MockLLMGenerator, NovelGenerator
from novel_50ep.polish_tool import PolishTool, proofread_text
from novel_50ep.publish_prep import PublishPreparer
from novel_50ep.score_reviewer import ScoreReviewer


# ==============================================================================
# Phase A & B: 設定・世界観・プロンプト雛形 (ステップ1〜18)
# ==============================================================================
def test_phase_a_and_b():
    # ステップ1, 2
    assert TARGET_CHARS == 3000
    assert MIN_CHARS == 2900
    assert MAX_CHARS == 3100
    assert TOTAL_EPISODES == 50
    assert sum(PART_TARGETS.values()) == 3000

    # ステップ3〜7, 10
    assert WORLD_FILE.exists()
    world = yaml.safe_load(WORLD_FILE.read_text(encoding="utf-8"))
    assert world["genre"] == "光層ファンタジー"
    assert "凛" in world["protagonist"]["name"]
    assert "光の石" in world["symbol"]
    assert len(world["subcharacters"]) >= 2

    # ステップ8, 9
    assert EMOTIONS_FILE.exists()
    assert CLIFFS_FILE.exists()

    # ステップ11〜18
    assert TEMPLATE_FILE.exists()
    for p in range(1, 8):
        gen = NovelGenerator()
        prompt = gen._load_prompt_template(p)
        assert len(prompt) > 20


# ==============================================================================
# Phase C: 文字数・品質チェックツール (ステップ19〜27)
# ==============================================================================
def test_phase_c_validation_suite():
    text = "光の石が輝く。"
    assert count_chars(text) == 7
    assert check_range(3000) is True
    assert check_range(2800) is False

    em_cnt, matched = require_words("胸に恐怖と決意が交錯する。")
    assert em_cnt >= 2

    cliff_text = "その瞬間、胸元の光の石が突如として不吉な黒に染まり、脈打ち始めた。"
    has_cliff, _ = check_cliff(cliff_text)
    assert has_cliff is True

    dup_text = "同じ言葉。\n同じ言葉。\n同じ言葉。"
    has_dup, _ = detect_dup(dup_text)
    assert has_dup is True


# ==============================================================================
# Phase D: 第1話プロトタイプ生成・調整 (ステップ28〜36)
# ==============================================================================
def test_phase_d_prototype_generation():
    gen = NovelGenerator()

    # パート①生成
    p1 = gen.generate_part(1, 1, "テストコンテキスト")
    assert 250 <= count_chars(p1) <= 350

    # 1話まるごと生成
    novel_text, val_result, part_texts = gen.generate_episode(1)
    assert len(part_texts) == 7
    assert MIN_CHARS - 100 <= count_chars(novel_text) <= MAX_CHARS + 100
    assert val_result.is_valid is True
    assert (OUTPUT_DIR / "ep01.md").exists()
    assert (OUTPUT_DIR / "ep01_raw.md").exists()
    assert (OUTPUT_DIR / "ep01_p1.txt").exists()


# ==============================================================================
# Phase E: バッチ生成運用 (ステップ37〜50)
# ==============================================================================
def test_phase_e_batch_run_and_normalization():
    # 正規化テスト (ステップ48, 49)
    norm = normalize_names("リンとセリア巫女が虚無のつめに挑む")
    assert "凛" in norm
    assert "セリア" in norm
    assert "虚無の爪" in norm

    dedup = dedup_sentence_endings("真実だ。だ。だ。")
    assert dedup == "真実だ。"

    # バッチ実行 (話数 1〜3)
    runner = BatchRunner()
    success = runner.run_batch(start=1, end=3, resume=False)
    assert 1 in success
    assert 2 in success
    assert 3 in success

    # 進捗永続化確認 (ステップ44)
    completed = runner.load_progress()
    assert 1 in completed and 2 in completed and 3 in completed

    # 中間レビュー (ステップ46)
    rev = runner.intermediate_review(1, 3)
    assert rev["avg_chars"] >= 2800

    # ログ出力確認 (ステップ42)
    assert (LOG_DIR / "ep01.log").exists()


# ==============================================================================
# Phase F: 伏線・クリフ管理 (ステップ51〜58)
# ==============================================================================
def test_phase_f_foreshadow_management():
    fm = ForeshadowManager()
    fm.add_foreshadow(ep=1, f_type="伏線", text="謎の黒い結晶の欠片", status="未回収")

    unres = fm.get_latest_unresolved(current_ep=2)
    assert unres is not None
    assert "謎の黒い結晶" in unres.text

    # 回収
    fm.resolve_foreshadow("謎の黒い結晶", resolved_ep=2)
    unres_after = fm.get_latest_unresolved(current_ep=3)
    assert unres_after is None or "謎の黒い結晶" not in unres_after.text

    # クリフ使用集計 (ステップ56, 57)
    usage = fm.cliff_usage()
    assert isinstance(usage, dict)
    next_c = fm.next_cliff()
    assert isinstance(next_c, str) and len(next_c) > 0

    # 伏線マップ出力 (ステップ58)
    fm.export_foreshadow_map()
    assert (Path("novel_50ep/foreshadow_map.md")).exists()


# ==============================================================================
# Phase G: 自動レビュー・スコアリング (ステップ59〜64)
# ==============================================================================
def test_phase_g_score_reviewer():
    reviewer = ScoreReviewer()
    ep1_file = OUTPUT_DIR / "ep01.md"
    assert ep1_file.exists()

    text = ep1_file.read_text(encoding="utf-8")
    score_obj = reviewer.score_episode(1, text)

    assert 0.0 <= score_obj.pacing_score <= 1.0
    assert 0.0 <= score_obj.emotion_score <= 1.0
    assert 0.0 <= score_obj.world_score <= 1.0
    assert 0.0 <= score_obj.cliff_score <= 1.0
    assert score_obj.total_score >= 0.80

    scores, avg_score = reviewer.score_all(total=3)
    assert len(scores) == 3
    assert avg_score >= 0.85
    assert SCORES_FILE.exists()


# ==============================================================================
# Phase H: 人手微調整・校正 (ステップ65〜68)
# ==============================================================================
def test_phase_h_polish_and_final():
    tool = PolishTool()
    low_eps = tool.list_low_score_episodes(threshold=0.80)
    assert isinstance(low_eps, list)

    ok, fix_cnt = tool.polish_episode(1)
    assert ok is True

    exported_count, fails = tool.export_all_to_final(total=3)
    assert exported_count == 3
    assert (FINAL_DIR / "ep01.md").exists()


# ==============================================================================
# Phase I: カクヨム公開準備 (ステップ69〜72)
# ==============================================================================
def test_phase_i_publish_prep():
    prep = PublishPreparer()
    full_novel, zip_pkg = prep.export_publication_package(total=3)

    assert full_novel.exists()
    assert zip_pkg.exists()
    assert METADATA_FILE.exists()

    meta = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    assert "輝石の遺産" in meta["title"]
    assert "カクヨムオンリー" in meta["tags"]
    assert meta["synopsis_chars"] > 100

    ep1_final = (FINAL_DIR / "ep01.md").read_text(encoding="utf-8")
    assert ep1_final.startswith("第1話")


# ==============================================================================
# Phase M: 4コマ漫画プロンプト生成（オプトイン） (ステップ1〜72 最小セット)
# ==============================================================================
def test_phase_m_manga_prompt():
    import novel_50ep.config as cfg_mod

    # ステップ71: デフォルト（オプトインOFF）ではファイルが生成されない
    cfg_mod.MANGA_PROMPT_ENABLED = False
    gen = NovelGenerator()
    dummy_parts = {p: f"パート{p}の本文です。{ '。'.join(['テスト文'] * 5)}。" for p in range(1, 8)}
    # クリフを含ませる
    dummy_parts[7] = "その時、胸元の光の石が不吉な黒に染まり脈打ち始めた。"

    for f in ["ep01_manga_prompt.txt", "ep01_manga_panels.jsonl"]:
        p = MANGA_PROMPTS_DIR / f
        if p.exists():
            p.unlink()

    # ステップ69: マッピング結果は4コマ
    panels = gen.manga_builder.build_panels(dummy_parts, 1, cliff="クリフテスト")
    assert len(panels) == 4
    assert panels[0].role == "導入"
    assert panels[3].role == "オチ（驚き）"
    # ステップ15-18, 28: 構造化メタが揃っている
    for p in panels:
        assert p.scene
        assert p.dialogue
        assert p.camera_angle
        assert p.emotion
        assert p.character_ref
    errs = gen.manga_builder.validate_panels(panels)
    assert errs == []

    # ステップ70: generate_manga_prompt で両形式出力
    written = gen.generate_manga_prompt(1, dummy_parts)
    assert (MANGA_PROMPTS_DIR / "ep01_manga_prompt.txt").exists()
    assert (MANGA_PROMPTS_DIR / "ep01_manga_panels.jsonl").exists()
    assert len(written) == 2

    # JSONL の中身を1行ずつパース
    lines = (MANGA_PROMPTS_DIR / "ep01_manga_panels.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    import json as _json
    for ln in lines:
        rec = _json.loads(ln)
        assert "panel" in rec and "scene" in rec and "characters" in rec

    # ステップ71: オプトインOFF の generate_episode では漫画ファイルが作られない
    for f in ["ep99_manga_prompt.txt", "ep99_manga_panels.jsonl"]:
        p = MANGA_PROMPTS_DIR / f
        if p.exists():
            p.unlink()
    cfg_mod.MANGA_PROMPT_ENABLED = False
    gen.generate_episode(99)
    assert not (MANGA_PROMPTS_DIR / "ep99_manga_prompt.txt").exists()

    # ステップ64, 71: --manga 相当の有効化で generate_episode から生成される
    enable_manga_prompts()
    assert is_manga_enabled() is True
    gen.generate_episode(99)
    assert (MANGA_PROMPTS_DIR / "ep99_manga_prompt.txt").exists()
    assert (MANGA_PROMPTS_DIR / "ep99_manga_panels.jsonl").exists()

    # 後始末
    cfg_mod.MANGA_PROMPT_ENABLED = False
    for f in ["ep01_manga_prompt.txt", "ep01_manga_panels.jsonl",
              "ep99_manga_prompt.txt", "ep99_manga_panels.jsonl", "ep99.md", "ep99_raw.md"]:
        p = MANGA_PROMPTS_DIR / f if f.startswith("ep99_manga") else OUTPUT_DIR / f
        if p.exists():
            p.unlink()


# ==============================================================================
# Phase E: 検証・安全性・ドライラン (ステップ57〜72)
# ==============================================================================
def test_phase_e_security():
    import novel_50ep.config as cfg_mod
    from novel_50ep.generator import NovelGenerator

    gen = NovelGenerator()

    # ステップ69: 検証でコマ数/文字数超過が検出される
    bad_panels = gen.manga_builder.build_panels(
        {p: "短い文。" for p in range(1, 8)}, 1, cliff="ク"
    )
    # 文字数上限を超えるよう意図的に改変
    bad_panels[0].raw_text = "あ" * (cfg_mod.MANGA_MAX_CHARS_PER_PANEL + 10)
    errs = gen.manga_builder.validate_panels(bad_panels)
    assert any("文字数上限" in e for e in errs)

    # ステップ57, 70: NG表現が sanitize されて出力に残らない
    ng = ILLUST_SAFETY[0]
    parts = {p: f"パート{p}の本文。普通の描写。" for p in range(1, 8)}
    parts[5] = f"激しい{ng}の描写が続いた。"
    parts[7] = "その時、胸元の光の石が不吉な黒に染まり脈打ち始めた。"
    written = gen.generate_manga_prompt(1, parts)
    txt = written[0].read_text(encoding="utf-8")
    assert ng not in txt, f"NG表現が残っている: {ng}"
    assert "（自主規制）" in txt

    # ステップ71: ドライラン相当（manga有効＋1話生成）で1話分だけ出力
    cfg_mod.MANGA_PROMPT_ENABLED = False
    for f in ["ep98_manga_prompt.txt", "ep98_manga_panels.jsonl"]:
        p = MANGA_PROMPTS_DIR / f
        if p.exists():
            p.unlink()
    cfg_mod.enable_manga_prompts()
    gen.generate_episode(98)
    assert (MANGA_PROMPTS_DIR / "ep98_manga_prompt.txt").exists()
    assert (MANGA_PROMPTS_DIR / "ep98_manga_panels.jsonl").exists()

    # 後始末
    cfg_mod.MANGA_PROMPT_ENABLED = False
    for f in ["ep01_manga_prompt.txt", "ep01_manga_panels.jsonl",
              "ep98_manga_prompt.txt", "ep98_manga_panels.jsonl", "ep98.md", "ep98_raw.md"]:
        p = MANGA_PROMPTS_DIR / f if f.startswith("ep98_manga") or f.startswith("ep01_manga") else OUTPUT_DIR / f
        if p.exists():
            p.unlink()


# ==============================================================================
# Phase 9: Continuity 統合テスト (ステップ 71)
# ==============================================================================
def test_continuity_full():
    """全ルールファイルを読み、戦闘・会話・探索の複数シーンを通した一貫性検証"""
    import os
    from novel_50ep.continuity_tracker import ContinuityTracker
    from novel_50ep.scene_model import (
        DialogueScene,
        CombatScene,
        ExplorationScene,
    )

    rules_dir = str(Path(__file__).parent.parent / "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    # 1. 会話シーン 1
    d1 = DialogueScene(id="d1", start=0, end=100, speakers=["凛", "セリア"], topics=["遺跡調査"])
    v_d1 = tracker.feed(d1)
    assert len(v_d1) == 0

    # 2. 会話シーン 2 (話者・トピック継続: OK)
    d2 = DialogueScene(id="d2", start=100, end=200, speakers=["凛"], topics=["遺跡調査"])
    v_d2 = tracker.feed(d2)
    assert len(v_d2) == 0

    # 3. 戦闘シーン 1 (初期状態: HP 100, MP 50, 装備 [光刃, 光の盾])
    c1 = CombatScene(id="c1", start=200, end=300, hp=100, mp=50, equipment=["光刃", "光の盾"])
    v_c1 = tracker.feed(c1)
    assert len(v_c1) == 0

    # 4. 戦闘シーン 2 (HP減少・MP減少・装備維持: OK)
    c2 = CombatScene(id="c2", start=300, end=400, hp=80, mp=30, equipment=["光刃", "光の盾"])
    v_c2 = tracker.feed(c2)
    assert len(v_c2) == 0

    # 5. 戦闘シーン 3 (HPが不正に増加: 違反1件検出)
    c3 = CombatScene(id="c3", start=400, end=500, hp=95, mp=20, equipment=["光刃", "光の盾"])
    v_c3 = tracker.feed(c3)
    assert len(v_c3) == 1
    assert v_c3[0]["field"] == "hp"

    # 6. 探索シーン 1
    x1 = ExplorationScene(id="x1", start=500, end=600, location="蒼穹の回廊", items=["光導器"])
    v_x1 = tracker.feed(x1)
    assert len(v_x1) == 0

    # 7. 探索シーン 2 (場所が説明なく変化: 違反1件検出)
    x2 = ExplorationScene(id="x2", start=600, end=700, location="未知の最深部", items=["光導器"])
    v_x2 = tracker.feed(x2)
    assert len(v_x2) == 1
    assert v_x2[0]["field"] == "location"

    # 累積違反数が2件であることを確認
    assert len(tracker.violations) == 2
    report = tracker.report()
    assert "hp:" in report
    assert "location:" in report
