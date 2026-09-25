"""40話商業ビートシート構成定義 (PLAN P3 / Stage A).

Web小説・ライトノベル単行本1巻分（約10万字・40話）を読ませ切るための黄金構成比率。
各フェーズにおけるストーリー方針と、伏線回収スロットの契約方針を定義。
"""
from typing import Any, Dict, List, Optional

COMMERCIAL_40EP_BEATS: List[Dict[str, Any]] = [
    {
        "range": (1, 3),
        "phase": "開幕フック",
        "directive": "理不尽な侮蔑・追放からの規格外覚醒と圧倒的引き",
        "foreshadowing_directive": "短期伏線の設置と黒幕・大いなる謎（長期伏線）の布石",
        "target_scopes": ["short_term"],
    },
    {
        "range": (4, 10),
        "phase": "初期成功・拠点確立",
        "directive": "新天地での能力証明、ヒロイン/相棒との出会い、小ざまぁ",
        "foreshadowing_directive": "開幕で撒いた短期伏線の回収（小カタルシス）と新天地の謎設置",
        "target_scopes": ["short_term"],
    },
    {
        "range": (11, 18),
        "phase": "第1の試練・勢力拡大",
        "directive": "街やギルドでの名声拡大、旧勢力の焦燥、中規模ボスの撃破",
        "foreshadowing_directive": "中規模ボス関連の伏線回収、勢力争いの布石強化",
        "target_scopes": ["short_term"],
    },
    {
        "range": (19, 25),
        "phase": "Midpoint・大転換",
        "directive": "世界観の秘密・黒幕の示唆、主人公の新たな目標の確立",
        "foreshadowing_directive": "世界観の謎の一部開示（中期伏線回収）と真の敵の示唆",
        "target_scopes": ["short_term", "long_term"],
    },
    {
        "range": (26, 32),
        "phase": "最大の危機・包囲網",
        "directive": "旧勢力や強大敵の本格侵攻、一時的な孤立（中だるみ防止の谷間）",
        "foreshadowing_directive": "過去の布石が裏目に出る等の危機進展、クライマックス伏線への収束",
        "target_scopes": ["short_term"],
    },
    {
        "range": (33, 38),
        "phase": "クライマックス決戦",
        "directive": "伏線全回収、圧倒的カタルシス（特大ざまぁ・完全勝利）",
        "foreshadowing_directive": "1巻を通じた長期伏線・大ネタの完全回収（特大カタルシス）",
        "target_scopes": ["long_term", "short_term"],
    },
    {
        "range": (39, 40),
        "phase": "凱旋・第1巻結び",
        "directive": "圧倒的称賛・地位の確立、第2巻への壮大な予告引き",
        "foreshadowing_directive": "残存の軽微な伏線回収と第2巻へ向けた新伏線の提示",
        "target_scopes": ["short_term"],
    },
]


def get_beat_for_episode(ep_num: int) -> Dict[str, Any]:
    """指定された話数に対応するビート定義を取得する"""
    for beat in COMMERCIAL_40EP_BEATS:
        start_ep, end_ep = beat["range"]
        if start_ep <= ep_num <= end_ep:
            return beat
    # 40話超過などのフォールバック
    return COMMERCIAL_40EP_BEATS[-1]