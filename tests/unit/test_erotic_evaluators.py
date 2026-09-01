from src.services.erotic_density_controller import EroticDensityController
from src.services.erotic_diversity_score import classify_diversity, compute_diversity_score


def test_erotic_density_controller():
    """EroticDensityController のピーク許可判定と強度推薦の検証。"""
    controller = EroticDensityController()

    # 連続ピークが少ない場合はピークを許可
    assert controller.should_allow_peak([2, 3, 4]) is True

    # 進行度に応じた強度推薦
    rec_early = controller.recommend_intensity(current_ep=1, total_eps=10, base_intensity=4)
    assert rec_early <= 2

    rec_late = controller.recommend_intensity(current_ep=9, total_eps=10, base_intensity=3)
    assert rec_late >= 4

    # 平均強度計算
    avg = controller.compute_avg_intensity([2, 3, 4, 3])
    assert avg == 3.0


def test_erotic_diversity_score_and_classification():
    """多様性スコア計算と分類の検証。"""
    vocab = ["熱い", "吐息", "指先", "潤み", "震え"]

    # 空テキスト
    assert compute_diversity_score("", vocab) == 0.0

    # 均等に出現するリッチなテキスト
    rich_text = "熱い吐息が漏れ、指先が潤み、微かに震えが走った。"
    score = compute_diversity_score(rich_text, vocab)
    assert score >= 0.5
    assert classify_diversity(score) == "pass"
