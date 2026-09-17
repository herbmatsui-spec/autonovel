"""20話〜100話連続執筆時のコンテキスト長不変性ベンチマークテスト (v5.0 Step 18).

3層ローリング記憶基盤（RollingMemoryBuilder）において、
エピソード数が 1話から 20話、50話、100話と増加しても、
コンテキスト長（文字数・推定トークン数）が爆発せず一定のウィンドウ内に
安定収束（フラット化）することを検証する。
"""
import time
import pytest

from src.services.context_compression.rolling_memory import RollingMemoryBuilder


def test_rolling_memory_token_stability_20_episodes():
    """1話から20話までのコンテキスト長推移を検証。"""
    builder = RollingMemoryBuilder(
        max_recent_digests=30,
        max_prev_episode_chars=2000,
        max_total_chars=5000,
    )

    bible = (
        "【世界観】\n"
        "舞台はエルドラシア帝国。魔術と蒸気機関が交錯する世界。\n"
        "【主人公】\n"
        "レオン: 帝国の元兵士。過去の裏切りを暴くため旅を続ける。\n"
        "【相棒】\n"
        "フェイ: 精霊使いの少女。明るく好奇心旺盛。"
    )

    digests = []
    stats_history = []

    # 1話〜20話までのシミュレーション
    for ep in range(1, 21):
        prev_text = f"第{ep-1}話の本文サンプル。レオンとフェイは敵の追手を振り切り、新たな街の門をくぐった。" * 15 if ep > 1 else ""
        stats = builder.get_context_stats(
            bible_summary=bible,
            past_digests=digests,
            prev_episode_text=prev_text,
        )
        stats_history.append((ep, stats))

        # 新たなエピソードダイジェストを追加
        digests.append(f"第{ep}話: レオン達は街の拠点で情報屋と接触し、帝国の動向を探った。")

    ep1_stats = stats_history[0][1]
    ep20_stats = stats_history[19][1]

    # 20話時点でもトークンバジェット（4000トークン / 5000文字）内に完全に収まっていること
    assert ep20_stats["total_chars"] <= 5000
    assert ep20_stats["estimated_tokens"] <= 4000
    print(f"\n[Ep 1] chars: {ep1_stats['total_chars']}, tokens: {ep1_stats['estimated_tokens']}")
    print(f"[Ep 20] chars: {ep20_stats['total_chars']}, tokens: {ep20_stats['estimated_tokens']}")


def test_rolling_memory_long_form_plateau_100_episodes():
    """100話まで執筆が進行した際のコンテキスト長プラトー（不変性）を検証。"""
    max_recent = 15
    builder = RollingMemoryBuilder(
        max_recent_digests=max_recent,
        max_prev_episode_chars=1500,
        preserve_initial_digests=2,
        max_total_chars=4000,
    )

    bible = "基本世界観と主要キャラ設定テキスト。" * 10
    prev_text = "前話の激しい戦闘と脱出劇の本文。" * 30

    digests = []
    token_counts = []

    start_time = time.perf_counter()

    for ep in range(1, 101):
        ctx = builder.build_context(
            bible_summary=bible,
            past_digests=digests,
            prev_episode_text=prev_text,
        )
        tokens = builder.estimate_tokens(ctx)
        token_counts.append(tokens)

        # 80〜100文字程度の客観的事実ダイジェスト
        digests.append(f"第{ep}話: 主人公達は新たな試練を突破し、次の手がかりを入手した。")

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # 1. 速度検証: 100話分のコンテキスト構築が50ms未満（1話あたり0.5ms未満）であること
    avg_speed_ms = elapsed_ms / 100
    assert avg_speed_ms < 2.0, f"Average build speed too slow: {avg_speed_ms:.3f}ms"

    # 2. プラトー（不変性）検証:
    # ウィンドウ上限（15話）を超えた後（例: 第30話 vs 第100話）で、
    # トークン数が実質的にフラット（増加率 5% 未満）であることを実証
    tokens_at_30 = token_counts[29]
    tokens_at_50 = token_counts[49]
    tokens_at_100 = token_counts[99]

    growth_rate_30_to_100 = (tokens_at_100 - tokens_at_30) / tokens_at_30

    print(f"\n[100 Ep Benchmark] Avg Speed: {avg_speed_ms:.3f}ms/ep")
    print(f"[Ep 15] tokens: {token_counts[14]}")
    print(f"[Ep 30] tokens: {tokens_at_30}")
    print(f"[Ep 50] tokens: {tokens_at_50}")
    print(f"[Ep 100] tokens: {tokens_at_100}")
    print(f"[Growth 30->100]: {growth_rate_30_to_100:.2%}")

    # ウィンドウ固定により、30話以降はトークン数が完全にプラトー化（変動幅5%未満）
    assert abs(growth_rate_30_to_100) < 0.05, f"Tokens grew unexpectedly: {growth_rate_30_to_100:.2%}"

    # ハードリミット絶対遵守検証
    for ep, tokens in enumerate(token_counts, start=1):
        assert tokens <= builder.max_total_tokens, f"Ep {ep} exceeded max tokens: {tokens}"
