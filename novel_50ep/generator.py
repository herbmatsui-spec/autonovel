"""小説チャンク分割生成・プロトタイプエンジン (ステップ28〜40)"""

from __future__ import annotations
import os
import json
from pathlib import Path
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import yaml

try:
    from novel_50ep.config import (
        CLIFFS_FILE,
        EMOTIONS_FILE,
        LOG_DIR,
        MANGA_LAYOUT,
        MANGA_MAX_CHARS_PER_PANEL,
        MANGA_PANEL_COUNT,
        MANGA_PROMPTS_DIR,
        MANGA_PROMPT_ENABLED,
        MAX_CHARS,
        MAX_PART_RETRIES,
        MIN_CHARS,
        OUTPUT_DIR,
        PART_TARGETS,
        PART_TOLERANCE,
        PROMPTS_DIR,
        TARGET_CHARS,
        WORLD_FILE,
        load_illust_style,
        ILLUST_SAFETY,
        MANGA_DRY_RUN,
    )
    from novel_50ep.count_chars import count_chars, validate_episode, ValidationResult
    from novel_50ep.foreshadow_manager import ForeshadowManager
    from novel_50ep.scene_model import SceneBase, make_scene, DialogueScene, CombatScene, ExplorationScene
    from novel_50ep.continuity_tracker import ContinuityTracker
except ImportError:
    from config import (
        CLIFFS_FILE,
        EMOTIONS_FILE,
        LOG_DIR,
        MANGA_LAYOUT,
        MANGA_MAX_CHARS_PER_PANEL,
        MANGA_PANEL_COUNT,
        MANGA_PROMPTS_DIR,
        MANGA_PROMPT_ENABLED,
        MAX_CHARS,
        MAX_PART_RETRIES,
        MIN_CHARS,
        OUTPUT_DIR,
        PART_TARGETS,
        PART_TOLERANCE,
        PROMPTS_DIR,
        TARGET_CHARS,
        WORLD_FILE,
        load_illust_style,
        ILLUST_SAFETY,
        MANGA_DRY_RUN,
    )
    from count_chars import count_chars, validate_episode, ValidationResult
    from foreshadow_manager import ForeshadowManager
    from scene_model import SceneBase, make_scene, DialogueScene, CombatScene, ExplorationScene
    from continuity_tracker import ContinuityTracker

import novel_50ep.config as _cfg


class MockLLMGenerator:
    """オフライン検証・低性能LLMシミュレーション用の高品質テンプレート生成器"""

    def __init__(self, world_data: dict):
        self.world = world_data

    def generate(self, prompt: str, target_chars: int, part_id: int, ep: int, cliff: str = "") -> str:
        symbol = self.world.get("symbol", "光の石")
        protagonist = self.world.get("protagonist", {}).get("name", "凛")
        subchars = self.world.get("subcharacters", [])
        sub1 = subchars[0].get("name", "セリア") if len(subchars) > 0 else "セリア"
        sub2 = subchars[1].get("name", "ガルド") if len(subchars) > 1 else "ガルド"
        antagonist = self.world.get("antagonist", {}).get("name", "闇結社『虚無の爪』")

        sentences_pool = {
            1: [
                f"天空へと聳える多層都市ルクスの尖塔群は、淡い青白い光脈によって脈打っていた。",
                f"都市の中心に鎮座する巨石、{symbol}が放つ神秘的な輝きは、街全体を魔獣の脅威から守り続けている。",
                f"しかしその光は、かつての神聖な眩さを失い、かすかな揺らぎを見せ始めていた。",
                f"風が吹き抜けるたび、冷たい空気の中に微小な光の粒子が舞い上がり、静寂の街路を照らし出す。",
                f"{protagonist}は高台から広がる階層構造の街並みを見下ろし、静かに息を潜めていた。",
                f"街を包む燐光のカーテンがかすかに波打ち、夜の闇との境界線を曖昧に滲ませていく。",
                f"古より受け継がれし光の加護が、今まさに試練の時を迎えていることは明白だった。",
            ],
            2: [
                f"かつて幼き日、家族と共に見た{symbol}の光はどこまでも温かく、永遠に続くものだと信じていた。",
                f"だが突如として闇の襲撃を受け、すべてが炎と混沌に呑み込まれたあの夜の光景が、今も脳裏に焼き付いて離れない。",
                f"胸中を満たすのは、拭い去ることのできない深い【不安】と、失われた絆を取り戻すという硬い【決意】だった。",
                f"{antagonist}が再び蠢動を始めた今、自分自身の力がこの街を救うに足るものなのか、自問自答が続く。",
                f"握りしめた拳には微かな震えが走るが、立ち止まるわけにはいかない。",
                f"未来を拓く希望の糸を手繰り寄せるように、{protagonist}は冷たい夜気に視線を向けた。",
                f"誓いを交わしたあの日から、一歩たりとも退くつもりは毛頭なかった。",
                f"自らの内に秘められた光の波長を確かめながら、静かに呼吸を整えていく。",
            ],
            3: [
                f"第{ep}話における今回の任務は、光層外縁部に位置する古代遺跡『蒼穹の回廊』へと潜入し、減衰しつつある光脈の核を再起動することだ。",
                f"{antagonist}の工作員たちが既に先遣隊として侵入しており、遺跡の封印を内側から解こうとしているとの報が入っていた。",
                f"もし奴らに光脈の核を奪われれば、ルクス全域の防壁結界が崩壊し、下層の魔獣が一気に押し寄せることになる。",
                f"残された猶予は次の黎明まで、一刻の猶予も許されない極めて切迫した状況だ。",
                f"{protagonist}は手元の地図と光導器の針を確認し、最短ルートで回廊の最深部へと到達する経路を策定した。",
                f"敵の哨戒部隊を突破し、確実に防衛装置を掌握しなければならない。",
                f"この任務の成否が、都市に暮らす数万の人々の命運を直結して握っているのだ。",
                f"緊張感に満ちた空気が張り詰める中、迅速かつ確実な行動が求められていた。",
                f"一切の油断を排し、{protagonist}は闇に包まれた回廊の入口へと静かに歩を進めた。",
                f"光導器の針が指し示す方角には、未知の危険と罠が待ち構えているに違いなかった。",
            ],
            4: [
                f"遺跡の入り口で合流した{sub1}は、古びた魔導書を広げながら真剣な面持ちで言った。",
                f"「{protagonist}、この先は結界の干渉が強くなっているわ。私が光路を開くから、一瞬の隙を突いて」",
                f"「了解だ。合図を頼む」",
                f"{sub1}が詠唱を紡ぐと、重厚な石扉の隙間から眩い燐光が溢れ出した。",
                f"息の合った連携で二人は結界の亀裂を滑り抜け、迷宮のような内部通路へと足を踏み入れた。",
                f"背後を警戒する{sub2}の足音が重厚に響き、頼もしい援護の気配が背中を支えてくれる。",
                f"互いの役割を熟知したチームワークが、暗闇の中で確固たる前進を可能にしていた。",
            ],
            5: [
                f"回廊の大広間に踏み込んだ瞬間、空間を鋭く引き裂く風切り音が鼓膜を打った。",
                f"視界の端から黒炎を纏った漆黒の刃が閃光のように迫り、{protagonist}は反射的に身を翻す。",
                f"閃いた光刃と闇の刃が激突し、眩い火花が視界いっぱいに激しく飛び散った。",
                f"周囲の気温が急激に氷点下へと下がり、肌を突き刺すような凄まじい冷気と痛烈な衝撃が全身を襲う。",
                f"「小癪な光の徒が！」敵の尖兵が怒号と共に振り下ろす重撃を、{protagonist}は光の盾で受け止める。",
                f"金属が軋む凄まじい衝撃と痺れが両腕を貫き、足元の石畳に放射状の亀裂が走る。",
                f"敵の構えが一瞬崩れた隙を見逃さず、{protagonist}は光の刃に全魔力を込めて横一文字に薙ぎ払った。",
                f"轟音と共に闇の影が吹き飛び、床に倒れ伏して黒い霧となって消滅した。",
                f"激しい衝突の余波が広間の壁を激しく揺らし、天井から無数の砂塵が降り注ぐ。",
                f"呼吸を乱すことなく即座に残敵の気配を索敵し、次の襲撃に備えて武器を構え直した。",
                f"極限の集中状態の中で研ぎ澄まされた感覚が、僅かな空気の揺らぎすらも見逃さない。",
                f"光と闇の激突は一瞬の油断が生死を分ける、まさに紙一重の死線だった。",
            ],
            6: [
                f"荒い息を吐き出しながら、{protagonist}は武器の切っ先をゆっくりと下ろした。",
                f"激しい死闘を制した安堵感が全身を包み込み、張り詰めていた神経が僅かに緩む。",
                f"「やりましたね、{protagonist}！」駆け寄った{sub1}の声に、微かな笑みを返す。",
                f"戦場を支配していた極度の緊張から解放され、仲間たちと交わす視線に確かな絆の実感が宿った。",
                f"しかしその瞬間、広間の床下深くから不気味な地鳴りが響き渡り、再び全身の警戒が跳ね上がった。",
                f"倒した尖兵は単なる囮に過ぎず、真の脅威が目覚めようとしているのだ。",
                f"解放された直後の空気が一転して冷え込み、さらなる危機の予兆が重くのしかかる。",
                f"戦いはまだ終わっていないことを、その不穏な振動が雄弁に物語っていた。",
            ],
            7: [
                f"戦闘の余燼が漂う静寂の中、かすかな光の粉塵が暗闇へと吸い込まれていく。",
                f"勝利の余韻に浸る間もなく、冷たい風が遺跡の奥深くから吹き抜けた。",
                f"{protagonist}は息を整えながら、手にした光導器の異常な針の振れを見つめた。",
                f"事態は当初の予測を遥かに超えて、深刻な局面へと向かっている。",
                f"遠く光層都市の空を覆う雲間に、妖しく揺らめく影が確実に蠢いていた。",
                f"次なる戦いの幕が上がる予感に、一行は静かに覚悟を固める。",
                f"仲間たちの表情にも緊張の色が戻り、誰もが次の展開を見据えていた。",
                f"幾重にも重なる試練の先にある真実を求め、決して歩みを止めることはない。",
                f"冷徹な静寂が広間を満たし、次の嵐を告げるかのように大気が震える。",
                f"その時、突如として空間が歪み、信じがたい異変が眼前で発生した。",
                f"{cliff if cliff else '胸元の光の石が突如として不吉な黒に染まり、脈打ち始めた。'}",
            ],
        }

        pool = sentences_pool.get(part_id, sentences_pool[1])
        selected: List[str] = []
        cliff_sentence = pool[-1] if part_id == 7 else None

        for s in pool:
            if part_id == 7 and s == cliff_sentence:
                continue
            selected.append(s)
            current_c = count_chars("".join(selected) + (cliff_sentence or ""))
            if current_c >= target_chars:
                break

        if part_id == 7 and cliff_sentence:
            selected.append(cliff_sentence)

        result_text = "".join(selected)

        # 文字数が足りない場合は動的フィラーで補填（Step 1: 固定リスト廃止）
        extra_sentences = self._build_dynamic_fillers(ep, part_id, cliff_sentence)

        ext_idx = 0
        while count_chars(result_text) < target_chars - 10 and ext_idx < len(extra_sentences):
            ext = extra_sentences[ext_idx]
            if count_chars(result_text) + count_chars(ext) <= target_chars + 15:
                if part_id == 7 and cliff_sentence and cliff_sentence in result_text:
                    result_text = result_text.replace(cliff_sentence, ext + cliff_sentence)
                else:
                    result_text += ext
            ext_idx += 1

        # 許容上限を超えた場合は末尾文を調整
        while count_chars(result_text) > target_chars + PART_TOLERANCE:
            idx = result_text.rfind("。")
            if idx > 50:
                result_text = result_text[:idx]
            else:
                break

        # Step 8: パート②・⑥に感情語を挿入
        result_text = self._inject_emotion_words(result_text, part_id, ep)

        return result_text

    def _inject_emotion_words(self, text: str, part_id: int, ep: int) -> str:
        """パート②・⑥に感情語をランダム挿入（Step 8）"""
        if part_id not in (2, 6):
            return text
        
        # EMOTIONS_FILE から読み込み
        from novel_50ep.config import EMOTIONS_FILE
        if EMOTIONS_FILE.exists():
            word_list = [w.strip() for w in EMOTIONS_FILE.read_text(encoding="utf-8").splitlines() if w.strip()]
        else:
            word_list = ["喜悦", "恐怖", "決意", "不安", "希望", "驚愕", "歓喜", "焦燥", "絶望", "哀惜", "慈愛", "安堵", "戦慄", "高揚", "疑惑"]
        
        # 話数をシードにして決定論的に選択
        import random
        rnd = random.Random(ep * 1000 + part_id * 100)
        selected = rnd.sample(word_list, min(3, len(word_list)))
        
        # 既出感情語を避ける
        existing = [w for w in word_list if f"【{w}】" in text or f"[{w}]" in text]
        available = [w for w in selected if w not in existing]
        if not available:
            available = selected
        
        # 文末付近に挿入（最大2語）
        sentences = text.split("。")
        if len(sentences) >= 2:
            insert_idx = -2  # 最後から2番目の文の後
            emotion_text = "".join([f"胸には【{w}】が満ちていた。" for w in available[:2]])
            sentences[insert_idx] = sentences[insert_idx].rstrip() + emotion_text
            text = "。".join(sentences)
        
        return text

    def _build_dynamic_fillers(self, ep: int, part_id: int, cliff_sentence: Optional[str] = None) -> List[str]:
        """話数・パート・伏線に応じた動的フィラー文を生成（Step 2）"""
        protagonist = self.world.get("protagonist", {}).get("name", "凛")
        symbol = self.world.get("symbol", "光の石")
        antagonist = self.world.get("antagonist", {}).get("name", "闇結社『虚無の爪』")
        
        # パート別・話数シードでバリエーションを出す簡易テンプレート
        templates = {
            1: [
                f"{protagonist}は{ep}話目の夜、{symbol}の揺らぎを改めて感じ取っていた。",
                f"遠くの尖塔から届く微かな光の音が、{protagonist}の決意を静かに後押しする。",
                f"階層都市ルクスの夜風が、{protagonist}の頬を冷たく撫でていく。",
            ],
            2: [
                f"過去の記憶がフラッシュバックし、{protagonist}の胸に熱いものが込み上げる。",
                f"失われた日々への想いが、{protagonist}の足元を確かなものに変えていく。",
                f"{antagonist}の影が脳裏をよぎり、{protagonist}は静かに拳を握りしめる。",
            ],
            3: [
                f"今回の任務の重みを噛み締め、{protagonist}は光導器の針を見つめ直す。",
                f"仲間たちの無事を祈りつつ、{protagonist}は最短ルートを胸に刻む。",
                f"迫り来る黎明までのタイムリミットが、{protagonist}の集中を研ぎ澄ます。",
            ],
            4: [
                f"仲間との信頼が、{protagonist}の背中を押す力となる。",
                f"セリアの詠唱が響く中、{protagonist}は自らの役割を再確認する。",
                f"ガルドの堅実な足音が、チームの結束を静かに物語っている。",
            ],
            5: [
                f"刃が交わる瞬きの隙に、{protagonist}は勝機を見出す。",
                f"激闘の只中で、{protagonist}の光刃が一筋の閃きを放つ。",
                f"敵の隙を突くタイミングを、{protagonist}は五感で計り知る。",
            ],
            6: [
                f"戦いの余韻の中で、{protagonist}は仲間の温もりを噛み締める。",
                f"安堵の裏で新たな予兆を感じ取り、{protagonist}は警戒を解かない。",
                f"地鳴りが遠くに響くたび、{protagonist}の決意がさらに固まっていく。",
            ],
            7: [
                f"{protagonist}は次なる戦いへの覚悟を、静かな呼吸に込める。",
                f"光導器の異常な振れが、未知の脅威を告げている。",
                f"仲間たちの視線が交わる瞬間、新たな絆が生まれつつある。",
            ],
        }
        
        pool = templates.get(part_id, templates[1])
        # 話数をシードにして決定論的にシャッフル
        import random
        rnd = random.Random(ep * 100 + part_id * 10)
        shuffled = pool[:]
        rnd.shuffle(shuffled)
        
        # クリフ文と重複しないようフィルタ
        if cliff_sentence:
            shuffled = [s for s in shuffled if s != cliff_sentence]
        
        return shuffled[:3]  # 最大3文まで返す


# ==============================================================================
# ステップ(2) 7パート → 4コマ マッピング (MangaBuilder)
# 低性能LLMでも動くよう、LLM呼び出しに依存しない決定論的ルールで動作する。
# ==============================================================================
@dataclass
class MangaPanel:
    panel_no: int
    role: str
    source_parts: List[int]
    raw_text: str = ""          # 後方互換用（= scene と同一）
    lines: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    emotion: str = "neutral"
    camera_angle: str = "wide"
    # ステップ15: パネル構造化メタ
    scene: str = ""
    dialogue: str = ""
    caption: str = ""
    # ステップ8: キャラ参照辞書（外見統一用）
    character_ref: str = ""


# ステップ35: 五感描写語（音/光/冷/痛等）の簡易スコアリング用キーワード
_SENSORY_WORDS = ["音", "光", "冷", "痛", "震", "匂", "触", "視", "聴", "肌", "風", "響", "閃", "灼"]


class MangaBuilder:
    """各話の7パート本文を4コマ漫画用パネルに圧縮するビルダー"""

    # ステップ19: コマ別カメラアングル・感情の既定ルール
    CAMERA_RULES = {1: "wide", 2: "medium", 3: "close-up/action", 4: "zoom_on_cliff"}
    EMOTION_RULES = {1: "calm", 2: "curious", 3: "tense", 4: "shock"}

    def __init__(self, world_data: dict):
        self.world = world_data or {}
        # ステップ5-7: キャラ参照辞書を構築して保持
        self.char_refs: Dict[str, str] = self._build_char_refs()
        # ステップ38: 画風設定を保持
        self.style: dict = load_illust_style()

    # ステップ16: 文分割ヘルパ（低性能でも可）
    def _split_sentences(self, text: str) -> List[str]:
        text = re.sub(r"<!--\s*PART:\d+\s*-->", "", text)
        sentences = re.split(r"(?<=[。！？])", text)
        return [s.strip() for s in sentences if s.strip()]

    # ステップ6-7: world.yaml からキャラの「名前: 外見説明」辞書を構築
    def _build_char_refs(self) -> Dict[str, str]:
        refs: Dict[str, str] = {}
        prot = self.world.get("protagonist", {})
        if prot.get("name"):
            refs[prot["name"]] = f"{prot['name']}: {prot.get('appearance', '外見設定なし')}"
        for sc in self.world.get("subcharacters", []):
            if sc.get("name"):
                refs[sc["name"]] = f"{sc['name']}: {sc.get('appearance', '外見設定なし')}"
        ant = self.world.get("antagonist", {})
        if ant.get("name"):
            refs[ant["name"]] = f"{ant['name']}: {ant.get('appearance', '外見設定なし')}"
        return refs

    # ステップ17: 先頭/末尾n文抽出ヘルパ
    def _take_first_last(self, text: str, n_first: int, n_last: int) -> str:
        sents = self._split_sentences(text)
        if not sents:
            return ""
        first = sents[:n_first]
        last = sents[-n_last:] if n_last > 0 else []
        selected = first + [s for s in last if s not in first]
        return "".join(selected)

    def _longest_sentences(self, text: str, n: int, prefer_sensory: bool = False) -> str:
        sents = self._split_sentences(text)
        if not sents:
            return ""

        def score(s: str) -> int:
            base = len(s)
            if prefer_sensory:
                base += sum(s.count(w) for w in _SENSORY_WORDS) * 5
            return base

        ranked = sorted(sents, key=score, reverse=True)
        return "".join(ranked[:n])

    def _strip_markers(self, text: str) -> str:
        return re.sub(r"<!--\s*PART:\d+\s*-->", "", text).strip()

    def _collect_characters(self, text: str) -> List[str]:
        names: List[str] = []
        prot = self.world.get("protagonist", {}).get("name", "")
        if prot and prot in text and prot not in names:
            names.append(prot)
        for sc in self.world.get("subcharacters", []):
            n = sc.get("name", "")
            if n and n in text and n not in names:
                names.append(n)
        ant = self.world.get("antagonist", {}).get("name", "")
        if ant and ant in text and ant not in names:
            names.append(ant)
        return names

    # ステップ63: NG表現を「（自主規制）」に置換するサニタイズ
    def _sanitize_text(self, text: str) -> str:
        cleaned = text
        for ng in _cfg.ILLUST_SAFETY:
            if ng in cleaned:
                cleaned = cleaned.replace(ng, "（自主規制）")
        return cleaned

    # ステップ61-62: キャラ名が scene に実在するかの整合チェック（warning 扱い）
    def _check_char_consistency(self, panels: List[MangaPanel]) -> List[str]:
        warnings: List[str] = []
        for panel in panels:
            for name in panel.characters:
                if name and name not in (panel.scene or panel.raw_text):
                    warnings.append(f"コマ{panel.panel_no}: キャラ「{name}」がシーン文に出現しません")
        return warnings

    # ステップ30: クリフをコマ4に確定代入するための内部ヘルパ
    def _panel4_cliff(self, part7_text: str, cliff: str) -> str:
        if cliff and cliff in part7_text:
            return cliff
        # 末尾の文をクリフとみなす
        sents = self._split_sentences(part7_text)
        return sents[-1] if sents else (cliff or "")

    # ステップ44, 50: コマ4専用ビルド（余韻＋クリフの「驚き/つっこみ」）
    def _build_panel4(self, part6: str, part7: str, cliff: str) -> str:
        p6 = self._take_first_last(part6, 0, 1)  # 余韻（パート⑥末尾1文）
        cliff_text = self._panel4_cliff(part7, cliff)  # クリフ
        return p6 + cliff_text

    # ステップ30, 38, 44-54: マッピング本体
    def build_panels(self, part_texts: Dict[int, str], ep: int, cliff: str = "") -> List[MangaPanel]:
        prot = self.world.get("protagonist", {}).get("name", "主人公")

        # ステップ19-20: コマ1 導入 = パート①先頭2文
        p1_text = self._take_first_last(part_texts.get(1, ""), 2, 0)

        # ステップ21-22: コマ2 展開 = パート③先頭1文 + パート④先頭1文
        p3 = self._take_first_last(part_texts.get(3, ""), 1, 0)
        p4 = self._take_first_last(part_texts.get(4, ""), 1, 0)
        p2_text = p3 + p4

        # ステップ23-24, 35, 38: コマ3 ピーク = パート⑤最長1-2文（五感優先）
        p5 = self._longest_sentences(part_texts.get(5, ""), 2, prefer_sensory=True)
        if not p5:  # ステップ38: アクション必須の保証
            p5 = f"{prot}は眼前の危機に立ち向かう。"

        # ステップ44: コマ4 オチ = 余韻 + クリフ
        p4_text = self._build_panel4(part_texts.get(6, ""), part_texts.get(7, ""), cliff)

        panels = [
            MangaPanel(1, "導入", [1], p1_text),
            MangaPanel(2, "展開", [3, 4], p2_text),
            MangaPanel(3, "ピーク", [5], p5),
            MangaPanel(4, "オチ（驚き）", [6, 7], p4_text),
        ]

        # ステップ27-29, 31, 33-34, 36, 9-11, 15-22: 各コマの後処理
        for panel in panels:
            panel.raw_text = self._strip_markers(panel.raw_text)
            panel.raw_text = self._sanitize_text(panel.raw_text)  # ステップ64: NG表現除外
            if not panel.raw_text:  # ステップ29: フォールバック
                panel.raw_text = f"第{ep}話の{panel.role}シーン"
            panel.lines = self._split_sentences(panel.raw_text)
            panel.characters = self._collect_characters(panel.raw_text)
            # ステップ19-22: カメラ/感情ルール適用
            panel.camera_angle = self.CAMERA_RULES.get(panel.panel_no, "wide")
            panel.emotion = self.EMOTION_RULES.get(panel.panel_no, "neutral")
            # ステップ15-18: 構造化メタ
            panel.scene = panel.raw_text
            panel.dialogue = " / ".join(panel.lines) if panel.lines else panel.raw_text
            panel.caption = f"視点:{panel.camera_angle} 感情:{panel.emotion}"
            # ステップ50: コマ4は「驚きのオチ」をキャプションに付与
            if panel.panel_no == 4 and cliff:
                panel.caption = f"{panel.caption} / 驚きのオチ: {cliff}"
            # ステップ9-11: キャラ参照辞書注入（外見統一）
            refs = [self.char_refs[c] for c in panel.characters if c in self.char_refs]
            panel.character_ref = "。".join(refs) if refs else "（主要キャラの外見は作品全体で統一）"

        return panels

    # ステップ38: 文字数上限で切り詰め
    def _truncate(self, text: str, limit: int) -> str:
        if count_chars(text) <= limit:
            return text
        sents = self._split_sentences(text)
        out = ""
        for s in sents:
            if count_chars(out + s) > limit:
                break
            out += s
        return out or sents[0][:limit]

    # ステップ39, 55: パネル検証（コマ数==4, 非空, 文字数上限, コマ4はクリフ必須）
    def validate_panels(self, panels: List[MangaPanel]) -> List[str]:
        errors: List[str] = []
        if len(panels) != _cfg.MANGA_PANEL_COUNT:
            errors.append(f"コマ数が {_cfg.MANGA_PANEL_COUNT} ではなく {len(panels)} です")
        for panel in panels:
            if not panel.raw_text.strip():
                errors.append(f"コマ{panel.panel_no} が空です")
            if count_chars(panel.raw_text) > _cfg.MANGA_MAX_CHARS_PER_PANEL:
                errors.append(f"コマ{panel.panel_no} が文字数上限 {_cfg.MANGA_MAX_CHARS_PER_PANEL} を超過")
            # ステップ55: コマ4（オチ）にはクリフが含まれていること
            if panel.panel_no == 4 and not panel.raw_text.strip():
                errors.append("コマ4（オチ）にクリフが含まれていません")
        return errors


class NovelGenerator:
    """エピソード生成エンジン"""

    def __init__(
        self,
        world_path: Path = WORLD_FILE,
        llm_fn: Optional[Callable[[str, int], str]] = None,
    ):
        self.world_path = world_path
        self.world_data = self._load_world()
        self.foreshadow_mgr = ForeshadowManager()
        self.mock_generator = MockLLMGenerator(self.world_data)
        self.manga_builder = MangaBuilder(self.world_data)
        self.llm_fn = llm_fn

    def _load_world(self) -> dict:
        if self.world_path.exists():
            return yaml.safe_load(self.world_path.read_text(encoding="utf-8")) or {}
        return {}

    def _load_prompt_template(self, part: int) -> str:
        prompt_files = {
            1: PROMPTS_DIR / "part1_symbol.txt",
            2: PROMPTS_DIR / "part2_reminiscence_anxiety.txt",
            3: PROMPTS_DIR / "part3_mission.txt",
            4: PROMPTS_DIR / "part4_subchar.txt",
            5: PROMPTS_DIR / "part5_action.txt",
            6: PROMPTS_DIR / "part6_climax.txt",
            7: PROMPTS_DIR / "part7_cliff.txt",
        }
        p_path = prompt_files.get(part)
        if p_path and p_path.exists():
            return p_path.read_text(encoding="utf-8")
        return f"パート{part}を執筆してください。"

    # ステップ 39: 会話シーン生成フック
    def generate_dialogue_scene(
        self,
        id: str,
        start: int = 0,
        end: int = 0,
        speakers: Optional[List[str]] = None,
        utterances: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
    ) -> DialogueScene:
        if speakers is None:
            prot = self.world_data.get("protagonist", {}).get("name", "凛")
            subchars = self.world_data.get("subcharacters", [])
            sub1 = subchars[0].get("name", "セリア") if subchars else "セリア"
            speakers = [prot, sub1]
        if topics is None:
            topics = ["任務計画"]
        scene = make_scene(
            "dialogue",
            id=id,
            start=start,
            end=end,
            speakers=speakers,
            utterances=utterances or [],
            topics=topics,
        )
        return scene

    # ステップ 47: 戦闘シーン生成フック
    def generate_combat_scene(
        self,
        id: str,
        start: int = 0,
        end: int = 0,
        hp: int = 100,
        mp: int = 50,
        equipment: Optional[List[str]] = None,
        enemies: Optional[List[str]] = None,
    ) -> CombatScene:
        if equipment is None:
            equipment = ["光刃", "光の盾"]
        if enemies is None:
            ant = self.world_data.get("antagonist", {}).get("name", "闇結社尖兵")
            enemies = [ant]
        scene = make_scene(
            "combat",
            id=id,
            start=start,
            end=end,
            hp=hp,
            mp=mp,
            equipment=equipment,
            enemies=enemies,
        )
        return scene

    # ステップ 54: 探索シーン生成フック
    def generate_exploration_scene(
        self,
        id: str,
        start: int = 0,
        end: int = 0,
        location: Optional[str] = None,
        items: Optional[List[str]] = None,
        map_flags: Optional[Dict[str, Any]] = None,
    ) -> ExplorationScene:
        if location is None:
            location = self.world_data.get("world_setting", "多層都市ルクス")
        if items is None:
            items = ["光導器"]
        scene = make_scene(
            "exploration",
            id=id,
            start=start,
            end=end,
            location=location,
            items=items,
            map_flags=map_flags or {},
        )
        return scene

    # ステップ49: 4コマ専用プロンプトテンプレート読み込み
    def load_manga_template(self) -> str:
        tpl_path = PROMPTS_DIR / "manga_panel.txt"
        if tpl_path.exists():
            return tpl_path.read_text(encoding="utf-8")
        # ステップ53: フォールバック文字列
        return (
            "4コマ漫画を生成してください。タイトル:{title} 第{episode_num}話 レイアウト:{layout} 画風:{style_hint}\n"
            "PANEL1 scene={panel1_scene} chars={panel1_characters} dialogue={panel1_dialogue} caption={panel1_caption}\n"
            "PANEL2 scene={panel2_scene} chars={panel2_characters} dialogue={panel2_dialogue} caption={panel2_caption}\n"
            "PANEL3 scene={panel3_scene} chars={panel3_characters} dialogue={panel3_dialogue} caption={panel3_caption}\n"
            "PANEL4 scene={panel4_scene} chars={panel4_characters} dialogue={panel4_dialogue} caption={panel4_caption}\n"
        )

    # ステップ50-52: テンプレート用フォーマット辞書構築
    def _build_manga_format_dict(self, ep: int, panels: List[MangaPanel]) -> dict:
        world = self.world_data
        title = world.get("title", "タイトル不明")
        # ステップ38-39: 画風設定をロードして全フィールドを渡す
        style = load_illust_style()

        fmt = {
            "title": title,
            "episode_num": ep,
            "layout": _cfg.MANGA_LAYOUT,
            "style_hint": style.get("style_hint", "セルルックアニメ風"),
            "color_tone": style.get("color_tone", ""),
            "aspect_ratio": style.get("aspect_ratio", "vertical_strip"),
            "font": style.get("font", ""),
        }
        for panel in panels:
            key = f"panel{panel.panel_no}"
            # ステップ15-18, 23-25: 構造化メタを全て出力
            fmt[f"{key}_scene"] = panel.scene or panel.raw_text
            fmt[f"{key}_characters"] = "、".join(panel.characters) if panel.characters else "（主要キャラ）"
            fmt[f"{key}_camera_angle"] = panel.camera_angle
            fmt[f"{key}_emotion"] = panel.emotion
            fmt[f"{key}_dialogue"] = panel.dialogue
            fmt[f"{key}_caption"] = panel.caption
            # ステップ12-13: キャラ参照辞書を出力
            fmt[f"{key}_character_ref"] = panel.character_ref
        return fmt

    # ステップ55-62: 4コマ漫画プロンプトの生成と出力（Gemini互換 txt / jsonl）
    def generate_manga_prompt(self, ep: int, part_texts: Dict[int, str]) -> List[Path]:
        # ステップ30: クリフを伏線管理から取得しコマ4へ
        cliff = self.foreshadow_mgr.next_cliff()
        panels = self.manga_builder.build_panels(part_texts, ep, cliff=cliff)

        # ステップ38, 66: 検証＋文字数上限で切り詰め
        for panel in panels:
            panel.raw_text = self.manga_builder._truncate(
                panel.raw_text, _cfg.MANGA_MAX_CHARS_PER_PANEL
            )
            panel.lines = self.manga_builder._split_sentences(panel.raw_text)
        errors = self.manga_builder.validate_panels(panels)
        if errors:
            print(f"[MANGA-WARN] 第{ep:02d}話 パネル検証: {'; '.join(errors)}")

        # ステップ59: テンプレート整形
        template = self.load_manga_template()
        fmt = self._build_manga_format_dict(ep, panels)
        # ステップ54: 全プレースホルダが埋まることを保証
        try:
            prompt_str = template.format(**fmt)
        except KeyError as e:
            print(f"[MANGA-WARN] 第{ep:02d}話 テンプレート未対応キー: {e}")
            prompt_str = template
        # ステップ54: 残置き {xxx} があれば空文字でクリア
        prompt_str = re.sub(r"\{[^{}]*\}", "", prompt_str)

        out_dir = _cfg.MANGA_PROMPTS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []

        # ステップ60: 結合プロンプト (txt)
        if "txt" in _cfg.MANGA_OUTPUT_FORMATS:
            txt_path = out_dir / f"ep{ep:02d}_manga_prompt.txt"
            txt_path.write_text(prompt_str, encoding="utf-8")
            written.append(txt_path)

        # ステップ61-62: コマ別 JSONL
        if "jsonl" in _cfg.MANGA_OUTPUT_FORMATS:
            jsonl_path = out_dir / f"ep{ep:02d}_manga_panels.jsonl"
            with jsonl_path.open("w", encoding="utf-8") as f:
                for panel in panels:
                    rec = {
                        "ep": ep,
                        "panel": panel.panel_no,
                        "role": panel.role,
                        "scene": panel.raw_text,
                        "characters": panel.characters,
                        "dialogue": panel.lines,
                        "caption": f"視点:{panel.camera_angle} 感情:{panel.emotion}",
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written.append(jsonl_path)

        return written

    # ステップ38: build_ctx (前話あらすじ + 直近未回収伏線)
    def build_ctx(self, ep: int, prev_ep_summary: str = "") -> str:
        latest_unres = self.foreshadow_mgr.get_latest_unresolved(ep)
        foreshadow_text = f"【未回収伏線】第{latest_unres.ep}話: {latest_unres.text}" if latest_unres else "特になし"

        if not prev_ep_summary:
            if ep == 1:
                prev_ep_summary = "物語の始まり。光層都市ルクスと凛の旅立ちのプロローグ。"
            else:
                prev_ep_summary = f"第{ep - 1}話での激闘を乗り越え、さらなる深層の秘密へと迫る。"

        return f"前話あらすじ: {prev_ep_summary} / {foreshadow_text}"

    # ステップ34: 感情語補正補助関数
    def inject_emotion_words(self, text: str, emotions: Optional[List[str]] = None) -> str:
        if emotions is None:
            emotions = ["決意", "希望"]
        if not any(em in text for em in emotions):
            text += f"胸には強い【{emotions[0]}】と、未来を拓く【{emotions[1]}】が宿っていた。"
        return text

    # ステップ35: クリフハンガー補正補助関数
    def inject_cliff_pattern(self, part7_text: str, cliff: Optional[str] = None) -> str:
        if not cliff:
            cliff = self.foreshadow_mgr.next_cliff()
        has_c, _ = self.foreshadow_mgr.check_cliff_pattern(part7_text) if hasattr(self.foreshadow_mgr, "check_cliff_pattern") else (False, None)
        if not has_c and cliff not in part7_text:
            part7_text = part7_text.rstrip() + f"\nその時、{cliff}"
        return part7_text

    # ステップ37: generate_part(ep, part, ctx)
    def generate_part(
        self,
        ep: int,
        part: int,
        ctx: str,
        cliff_override: Optional[str] = None,
        target_override: Optional[int] = None,
    ) -> str:
        target_chars = target_override or PART_TARGETS.get(part, 300)
        p_min = target_chars - PART_TOLERANCE
        p_max = target_chars + PART_TOLERANCE

        # プロンプト変数のフォーマット
        prompt_tmpl = self._load_prompt_template(part)
        subchars = self.world_data.get("subcharacters", [{}, {}])
        selected_sub = subchars[0] if part == 4 else subchars[0]

        cliff_to_use = cliff_override or self.foreshadow_mgr.next_cliff()

        prompt_str = prompt_tmpl.format(
            genre=self.world_data.get("genre", "ファンタジー"),
            symbol=self.world_data.get("symbol", "光の石"),
            world_setting=self.world_data.get("world_setting", "多層都市ルクス"),
            protagonist_name=self.world_data.get("protagonist", {}).get("name", "凛"),
            protagonist_age=self.world_data.get("protagonist", {}).get("age", 18),
            protagonist_personality=self.world_data.get("protagonist", {}).get("personality", "冷静沈着"),
            protagonist_motivation=self.world_data.get("protagonist", {}).get("motivation", "真相究明"),
            antagonist_name=self.world_data.get("antagonist", {}).get("name", "闇結社"),
            antagonist_summary=self.world_data.get("antagonist", {}).get("summary", "闇を呼ぶ結社"),
            subchar_name=selected_sub.get("name", "セリア"),
            subchar_role=selected_sub.get("role", "巫女"),
            episode_num=ep,
            context=ctx,
            emotion_word_1="不安",
            emotion_word_2="決意",
            mission_summary=f"第{ep}話の重要拠点突破ミッション",
            cliff_pattern=cliff_to_use,
        )

        # ステップ29: 文字数300±50等に収まるまで再生成（最大3回）
        for attempt in range(1, MAX_PART_RETRIES + 1):
            if self.llm_fn:
                try:
                    generated = self.llm_fn(prompt_str, target_chars)
                except Exception:
                    generated = self.mock_generator.generate(prompt_str, target_chars, part, ep, cliff_to_use)
            else:
                generated = self.mock_generator.generate(prompt_str, target_chars, part, ep, cliff_to_use)

            # パート②感情語チェック & パート⑦クリフハンガー付与
            if part == 2 and attempt == MAX_PART_RETRIES:
                generated = self.inject_emotion_words(generated)
            if part == 7 and cliff_to_use not in generated:
                generated = self.inject_cliff_pattern(generated, cliff_to_use)

            c_count = count_chars(generated)
            if p_min <= c_count <= p_max:
                return generated

        # 最大リトライ後も収まらない場合は最後の生成結果を返す
        return generated

    # ステップ40: retry_parts
    def retry_parts(
        self,
        ep: int,
        part_texts: Dict[int, str],
        invalid_parts: List[int],
        ctx: str,
        cliff: str,
    ) -> Dict[int, str]:
        for p in invalid_parts:
            part_texts[p] = self.generate_part(ep, p, ctx, cliff_override=cliff)
        return part_texts

    # ステップ28〜36, 39: generate_episode
    def generate_episode(
        self,
        ep: int,
        prev_summary: str = "",
        save_intermediates: bool = True,
    ) -> Tuple[str, ValidationResult, Dict[int, str]]:
        # ステップ 60: 生成時に foreshadow_manager.get_expects() を tracker に渡す
        rules_dir = str(Path(__file__).parent / "continuity_rules")
        tracker = ContinuityTracker(rules_dir=rules_dir, expects=self.foreshadow_mgr.get_expects())

        ctx = self.build_ctx(ep, prev_summary)
        chosen_cliff = self.foreshadow_mgr.next_cliff()

        part_texts: Dict[int, str] = {}

        # ステップ28, 30: パート①〜⑦順次生成
        for p in range(1, 8):
            p_text = self.generate_part(ep, p, ctx, cliff_override=chosen_cliff)
            part_texts[p] = p_text

            if save_intermediates:
                p_file = OUTPUT_DIR / f"ep{ep:02d}_p{p}.txt"
                p_file.write_text(p_text, encoding="utf-8")

        # ステップ31: 7ファイルを結合し epNN_raw.md を作成
        raw_content = "\n\n".join([f"<!-- PART:{p} -->\n{part_texts[p]}" for p in range(1, 8)])
        raw_file = OUTPUT_DIR / f"ep{ep:02d}_raw.md"
        raw_file.write_text(raw_content, encoding="utf-8")

        # ステップ32: validate_episode による検証
        val_result = validate_episode(part_texts, part7_text_override=part_texts[7])

        # ステップ33, 40: 不合格時は不足/不適合パートだけ再生成
        if not val_result.is_valid:
            bad_parts = []
            for p, target in PART_TARGETS.items():
                p_cnt = count_chars(part_texts.get(p, ""))
                if p_cnt < target - PART_TOLERANCE or p_cnt > target + PART_TOLERANCE:
                    bad_parts.append(p)

            if bad_parts:
                part_texts = self.retry_parts(ep, part_texts, bad_parts, ctx, chosen_cliff)
                raw_content = "\n\n".join([f"<!-- PART:{p} -->\n{part_texts[p]}" for p in range(1, 8)])
                raw_file.write_text(raw_content, encoding="utf-8")
                val_result = validate_episode(part_texts, part7_text_override=part_texts[7])

        # 総文字数が3100を超過した場合は最大パートから微調整
        cur_total = count_chars("\n\n".join([part_texts[p] for p in range(1, 8)]))
        if cur_total > MAX_CHARS:
            longest_p = max([p for p in range(1, 7)], key=lambda p: count_chars(part_texts[p]))
            p_text = part_texts[longest_p]
            s_list = [s for s in p_text.split("。") if s]
            if len(s_list) > 3:
                part_texts[longest_p] = "。".join(s_list[:-1]) + "。"
                val_result = validate_episode(part_texts, part7_text_override=part_texts[7])

        # ステップ36: 完成版 epNN.md 保存 (ステップ 63: polish 呼び出し)
        clean_novel_text = "\n\n".join([part_texts[p] for p in range(1, 8)])
        try:
            from novel_50ep.polish_tool import polish
        except ImportError:
            from polish_tool import polish
        polished_novel_text = polish(clean_novel_text, tracker=tracker)
        final_ep_file = OUTPUT_DIR / f"ep{ep:02d}.md"
        final_ep_file.write_text(polished_novel_text, encoding="utf-8")

        # ステップ52: クリフを伏線台帳に登録
        self.foreshadow_mgr.add_foreshadow(
            ep=ep,
            f_type="伏線",
            text=f"第{ep}話クリフ: {chosen_cliff}",
            status="未回収",
        )

        # ステップ63-64, 67: オプトイン有効時のみ4コマ漫画プロンプト生成（小説生成は継続）
        if _cfg.is_manga_enabled():
            try:
                self.generate_manga_prompt(ep, part_texts)
            except Exception as e:
                print(f"[MANGA-ERROR] 第{ep:02d}話 4コマプロンプト生成失敗(継続): {e}")

        return clean_novel_text, val_result, part_texts
