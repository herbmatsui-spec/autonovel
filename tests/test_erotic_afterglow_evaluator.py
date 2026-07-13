"""
tests/test_erotic_afterglow_evaluator.py
afterglow評価のユニットテスト。
"""
from src.services.erotic_afterglow_evaluator import AfterglowEvaluator


def test_afterglow_passes():
    evaluator = AfterglowEvaluator()
    good_text = """
二人の体温がゆっくりと下がっていく。

静寂の中、彼女は彼の肩に頭を預けた。
このまま時間が止まればいいと、二人は同時に思った。
温もりが残る部屋の中で、彼はそっと彼女の髪を撫でた。

次話への伏線がここに張られる。帝国の陰謀が近づいている。

二人は互いの温もりを確かめ合いながら、静かに夜を過ごした。
余韻が広がる部屋の中、彼女はそっと彼の手を握りしめた。
この距離感を大切にしながら、次の物語を待ち望むのであった。
穏やかな時間が流れ、二人の心と身体は完全に落ち着きを取り戻した。

暗闇の中で、二人は何も語らずにただ互いの存在を感じていた。
言葉はいらない。この静かな時間こそが二人の証だった。
明日への不安も、過去の後悔も、今は全て遠く感じられる。

朝が来る前に、彼女はもう一度彼の胸に顔を埋めた。
この温もりを忘れないように、心に刻み込むように。
二人の夜は深く、静かに、そして確かに二人を繋いでいた。
    """.strip()
    ok, issues = evaluator.evaluate(good_text)
    assert ok is True, issues


def test_afterglow_fails_paragraph_count():
    evaluator = AfterglowEvaluator()
    short_text = "二人の夜が更けていった。" * 20
    ok, issues = evaluator.evaluate(short_text)
    assert ok is False
    assert any("段落数" in i for i in issues)


def test_afterglow_fails_char_count():
    evaluator = AfterglowEvaluator()
    tiny_text = "温もりが残る。" * 5
    ok, issues = evaluator.evaluate(tiny_text)
    assert ok is False
    assert any("文字数" in i for i in issues)


def test_afterglow_fails_no_emotional_settling():
    evaluator = AfterglowEvaluator()
    text = ("動き続ける。" * 50 + "\n\n" + "次話への伏線。") * 3
    ok, issues = evaluator.evaluate(text)
    assert ok is False
    assert any("沈降" in i or "余韻" in i for i in issues)


def test_count_paragraphs():
    evaluator = AfterglowEvaluator()
    assert evaluator.count_paragraphs("a\n\nb\n\nc") == 3
    assert evaluator.count_paragraphs("a\n\n\n\nb") == 2
