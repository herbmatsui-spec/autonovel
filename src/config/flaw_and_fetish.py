"""
Presets for Character Flaw, Secret Motives, and Petty Ego.
PLAN 03: AI優等生病の外科的切除（生々しいエゴ・下品な打算・偏執的な毒気）
"""
from __future__ import annotations

from typing import Any

FLAW_PRESETS: dict[str, dict[str, Any]] = {
    "calculating_merchant": {
        "motive_type": "絶対的損得勘定",
        "inner_monologue_sample": "人助けなんて一文の得にもならねえ。だが、恩を売っておけば後で10倍搾り取れる。",
        "physical_trigger": "懐の金貨の重みを指先で確かめる",
    },
    "twisted_inferiority": {
        "motive_type": "見下し快感",
        "inner_monologue_sample": "かつて俺を虫ケラ扱いした連中が、今や俺の靴を舐めたがっている。傑作だな。",
        "physical_trigger": "口の端を吊り上げて静かに息を吐く",
    },
    "paranoia_monopoly": {
        "motive_type": "偏執的独占欲",
        "inner_monologue_sample": "こいつの笑顔も、頼り切った眼差しも全部俺だけのものだ。他の誰にも一ミリも渡さない。",
        "physical_trigger": "相手の細い手首を無意識に強く握りしめる",
    },
    "vengeful_grudge": {
        "motive_type": "執念深い復讐心",
        "inner_monologue_sample": "一発殴られたら、そいつの人生ごと根こそぎ破滅させてやらなきゃ気が済まねえ。",
        "physical_trigger": "奥歯をギリリと噛み締め、冷や汗を拭う",
    },
    "thirst_for_adulation": {
        "motive_type": "病的な承認欲求",
        "inner_monologue_sample": "もっと俺を崇めろ、天才だと騒げ。お前ら凡人の賞賛の声だけが俺の生きる糧なんだよ。",
        "physical_trigger": "わざとらしく無表情を装いながら喉仏を上下させる",
    },
    "snobbish_hedonism": {
        "motive_type": "俗物的快楽主義",
        "inner_monologue_sample": "英雄気取りなんてバカのすることだ。俺は美味い飯を食い、フカフカのベッドで美少女を侍らせて惰眠を貪りたいだけだ。",
        "physical_trigger": "値の張りそうな上着の襟元を撫で回す",
    },
}
