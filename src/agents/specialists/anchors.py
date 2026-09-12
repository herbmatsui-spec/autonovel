"""Audit Anchor Examples and Presets for Specialist Auditors (Pillar 4 / Step 1).

Provides calibrated few-shot anchor examples for 8 specialist auditors to prevent
score drift and ensure consistent grading criteria (e.g. High: 85+, Mid: 65, Low: 40).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AuditAnchorExample:
    """A single calibrated anchor example representing a specific score tier."""
    specialist_name: str
    tier: Literal["high", "mid", "low"]
    score: float
    sample_text: str
    critique: str
    key_features: list[str] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Format anchor into a clear few-shot demonstration for the LLM judge."""
        features_str = "、".join(self.key_features) if self.key_features else "特になし"
        return (
            f"【基準アンカー事例 ({self.tier.upper()}水準: {self.score}点)】\n"
            f"▼サンプルテキスト:\n{self.sample_text.strip()}\n"
            f"▼評価理由・講評:\n{self.critique.strip()}\n"
            f"▼着眼点: {features_str}\n"
        )


@dataclass
class AnchorPreset:
    """Set of calibrated anchor examples for a specialist."""
    specialist_name: str
    anchors: list[AuditAnchorExample] = field(default_factory=list)

    def add_anchor(self, anchor: AuditAnchorExample) -> None:
        self.anchors.append(anchor)

    def get_by_tier(self, tier: Literal["high", "mid", "low"]) -> AuditAnchorExample | None:
        for a in self.anchors:
            if a.tier == tier:
                return a
        return None

    def format_for_prompt(self) -> str:
        """Format all anchors into a combined few-shot reference section."""
        if not self.anchors:
            return ""
        lines = [
            f"### 【採点基準アンカー例（{self.specialist_name}）】",
            "以下の基準事例を物差しとし、採点の甘さ・辛さのブレをなくして厳格に評価してください:\n",
        ]
        # Sort by score descending (high -> mid -> low)
        sorted_anchors = sorted(self.anchors, key=lambda a: a.score, reverse=True)
        for a in sorted_anchors:
            lines.append(a.to_prompt_text())
        return "\n".join(lines)


# Global registry of anchor presets for each of the 8 specialists
SPECIALIST_ANCHOR_PRESETS: dict[str, AnchorPreset] = {}
ANCHOR_PRESETS = SPECIALIST_ANCHOR_PRESETS


def register_anchor_preset(preset: AnchorPreset) -> None:
    """Register an anchor preset for a specialist."""
    SPECIALIST_ANCHOR_PRESETS[preset.specialist_name] = preset


def get_anchor_preset(specialist_name: str) -> AnchorPreset | None:
    """Get the registered anchor preset for a specialist."""
    return SPECIALIST_ANCHOR_PRESETS.get(specialist_name)


# ----------------------------------------------------------------------
# Step 2: Reader Hook Anchor Preset
# ----------------------------------------------------------------------
_READER_HOOK_PRESET = AnchorPreset(specialist_name="reader_hook")

_READER_HOOK_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="reader_hook",
    tier="high",
    score=88.0,
    sample_text=(
        "【冒頭】「逃げろ、アレン！ そいつはお前の父親じゃない！」\n"
        "血に塗れた母の絶叫とともに、穏やかだった父の貌が縦に裂け、無数の黒い触手が噴き出した。\n"
        "【末尾】冷たい石畳に倒れ伏すアレンの前に、純白のローブを纏った人物が歩み寄る。\n"
        "掲げられたフードの奥――そこに浮かんでいたのは、十年前に行方不明となったはずの、彼自身の冷酷な微笑みだった。"
    ),
    critique="冒頭1文目から生命の危機と肉親の異形化という強烈な謎・サスペンスを提示し、読者を鷲掴みにしている。末尾も主人公自身のドッペルゲンガーという衝撃的クリフハンガーで次回への渇望感を極限まで高めている。",
    key_features=["危機的状況の直後開始", "常識の破壊と謎", "衝撃のクリフハンガー", "次回牽引力抜群"],
))

_READER_HOOK_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="reader_hook",
    tier="mid",
    score=65.0,
    sample_text=(
        "【冒頭】アラームの音で目が覚めた。今日は冒険者ギルドの登録試験の日だ。\n"
        "「よし、遅刻しないように急がないとな」\n"
        "パンをかじりながら靴を履き、僕は家を飛び出した。\n"
        "【末尾】ギルドの扉を開けると、そこには屈強な男たちが酒を飲んでいた。\n"
        "受付嬢がこちらに気づき、笑顔で手招きをする。\n"
        "こうして僕の新しい冒険が始まろうとしていた。"
    ),
    critique="典型的な導入であり文章は読みやすいが、フックとなるべき謎や強い危機感、独自性に乏しい。末尾も予定調和の開始であり、今すぐ次を読まなければならないという衝動は生じにくい。",
    key_features=["平坦な日常スタート", "王道の導入", "予定調和な末尾", "切迫感の不足"],
))

_READER_HOOK_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="reader_hook",
    tier="low",
    score=38.0,
    sample_text=(
        "【冒頭】エルレイン歴七百四十二年、世界は神々の大戦によって四つの大陸に分断された。\n"
        "魔力の源であるエーテルは地脈を通じて循環しており、帝国はこのエーテルを独占することで繁栄を築いた。\n"
        "【末尾】以上がこの国の歴史と魔法の概要である。\n"
        "アレンは図書館の椅子から立ち上がり、家に帰ることにした。夜風が少し冷たかった。"
    ),
    critique="冒頭が退屈な世界観・年表の説明から始まっており、物語としてのつかみが完全に欠落している。末尾も単なる帰宅の描写で、葛藤・謎・フックが皆無であり、読者離脱の典型例。",
    key_features=["説明過多（インフォダンプ）", "感情移入の余地なし", "フック皆無の末尾", "強い読者離脱リスク"],
))

register_anchor_preset(_READER_HOOK_PRESET)


# ----------------------------------------------------------------------
# Step 3: Consistency Anchor Preset
# ----------------------------------------------------------------------
_CONSISTENCY_PRESET = AnchorPreset(specialist_name="consistency")

_CONSISTENCY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="consistency",
    tier="high",
    score=90.0,
    sample_text=(
        "レイは右腕の重傷を庇いながら、左手だけで短剣を構えた。\n"
        "先刻の毒刃によって魔力回路が麻痺しており、得意の転移魔術は使えない。\n"
        "「くそっ、あと三分で効果が切れるはずだ……耐え凌ぐしかない」\n"
        "彼は壁を背にして死角を塞ぎ、防御に徹した。"
    ),
    critique="直前に負った負傷、毒による魔力封絶という世界観ルール・身体的制限が完璧に持続し、その制約下で論理的かつキャラクターの知性に見合った現実的行動をとっている。",
    key_features=["負傷・制限の厳格な維持", "ルール内での論理的打開行動", "時間・空間の整合性完全維持"],
))

_CONSISTENCY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="consistency",
    tier="mid",
    score=65.0,
    sample_text=(
        "激戦の末に城を脱出したレイたちは、隣町の宿屋に到着していた。\n"
        "「ふう、なんとか逃げ切れたな」\n"
        "レイは平然とビールジョッキを右手で掲げた。\n"
        "宿屋の女将が笑顔でスープを運んでくる。"
    ),
    critique="重傷を負っていたはずの右手の状態に言及がなく、城から隣町への移動時間（徒歩で半日以上かかるはずの距離）の描写がスキップされており、時間・身体状態の整合性に軽微な甘さが見られる。",
    key_features=["傷・疲労の描写の軽視", "移動・時間経過の描写不足", "致命的ではないが違和感のある省略"],
))

_CONSISTENCY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="consistency",
    tier="low",
    score=35.0,
    sample_text=(
        "宿屋の扉が開き、戦士バルガスが入ってきた。\n"
        "「よおレイ、遅かったじゃないか！」\n"
        "バルガスは豪快に笑いながら椅子に座った。\n"
        "（※注: バルガスは前話の防衛戦で確実に死亡し、遺体も埋葬されていた設定）"
    ),
    critique="前話で戦死・埋葬されたはずの重要キャラクターが、蘇生や伏線・理由の提示なく生存し談笑している。小説の世界観と読者の信頼を完全に破壊する致命的な論理破綻。",
    key_features=["死亡キャラクターの理由なき再登場", "プロットフラグの完全崩壊", "読者の信頼喪失"],
))

register_anchor_preset(_CONSISTENCY_PRESET)


# ----------------------------------------------------------------------
# Step 4: Structure Anchor Preset
# ----------------------------------------------------------------------
_STRUCTURE_PRESET = AnchorPreset(specialist_name="structure")

_STRUCTURE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="structure",
    tier="high",
    score=88.0,
    sample_text=(
        "【起】城下町の祭りの喧騒と、潜入任務前の緊張感あるブリーフィング（全体の20%）\n"
        "【承】変装して貴族邸に潜入、警備を突破しながら目的の金庫室へ到達（全体の40%）\n"
        "【転】金庫は空であり、待ち受けていた宿敵の罠が発動し包囲される（全体の25%）\n"
        "【結】窮地を脱出するため煙幕を放ち、屋根伝いに跳躍して脱出を試みる引き（全体の15%）"
    ),
    critique="起承転結のボリューム配分が理想的であり、事件の導入から障害の突破、想定外のどんでん返し、脱出劇へのクリフハンガーへとテンポ良く展開が加速している。",
    key_features=["理想的な構成比率", "明確なターニングポイント", "緊張感の段階的上昇", "メリハリのある結末"],
))

_STRUCTURE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="structure",
    tier="mid",
    score=65.0,
    sample_text=(
        "【起】屋敷に潜入するための買い出しと準備（全体の30%）\n"
        "【承】屋敷の廊下を歩き、使用人と会話しながら進む（全体の50%）\n"
        "【転・結】部屋に入ると敵がいたので短剣を投げて倒し、書類を回収して帰還した（全体の20%）"
    ),
    critique="準備や廊下の移動など中盤の展開部（承）が間延びしており、クライマックスと結末が一瞬で片付けられてしまっている。山場への盛り上がりが弱く、消化不良感が残る。",
    key_features=["中だるみする中盤", "クライマックスのあっさりした解決", "メリハリ不足"],
))

_STRUCTURE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="structure",
    tier="low",
    score=40.0,
    sample_text=(
        "【全体の75%】宿屋のテーブルで仲間たちと料理の味や昨日の天気について延々と雑談を続ける。\n"
        "【全体の20%】外に出るとモンスターがいたので魔法で一撃で倒した。\n"
        "【全体の5%】肉を焼いて食べた。"
    ),
    critique="物語の本筋と無関係な日常雑談が章の大半を占め、プロット上の課題や葛藤、劇的な転換が完全に欠如している。ストーリーとしての起承転結が成立していない。",
    key_features=["プロット停止", "目的のない雑談の肥大化", "起承転結の崩壊"],
))

register_anchor_preset(_STRUCTURE_PRESET)


# ----------------------------------------------------------------------
# Step 5: Emotion Curve & Style Anchor Presets
# ----------------------------------------------------------------------
_EMOTION_CURVE_PRESET = AnchorPreset(specialist_name="emotion_curve")

_EMOTION_CURVE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="emotion_curve",
    tier="high",
    score=87.0,
    sample_text=(
        "仲間たちと勝利を確信した刹那、背後から突き立てられた白銀の刃。\n"
        "信じていた副団長の冷たい瞳を見た瞬間、歓喜は氷のような絶望へと急転直下した。\n"
        "胸を刺す激痛と裏切りの寒気に震えながらも、床に這いつくばる少年の瞳の奥底に、黒々とした復讐の劫火が点火する。"
    ),
    critique="歓喜（プラス極）から裏切りの絶望（マイナス極）への急降下、そしてそこからの不屈の復讐心への反転という感情のダイナミックレンジが極めて広く、読者の情動を激しく揺さぶる。",
    key_features=["感情のダイナミックレンジ", "落差とカタルシス", "情動を揺さぶる心理描写"],
))

_EMOTION_CURVE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="emotion_curve",
    tier="mid",
    score=64.0,
    sample_text=(
        "敵が現れたので少し驚いた。\n"
        "戦うのは少し怖かったが、剣を抜いて立ち向かった。\n"
        "倒すことができて安心した。"
    ),
    critique="驚き→恐れ→安心という感情の流れはあるものの、感情の振れ幅が小さく淡白。キャラクターの内面の葛藤や胸に迫る感情の熱量が伝わりにくい。",
    key_features=["平坦な感情変化", "表現の浅さ", "共感強度の不足"],
))

_EMOTION_CURVE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="emotion_curve",
    tier="low",
    score=42.0,
    sample_text=(
        "レイは敵を発見した。剣を振るった。敵は倒れた。\n"
        "レイは歩き出した。門を通過した。次の階層に到達した。"
    ),
    critique="感情や心理描写が完全に抜け落ちており、まるで作業ログや報告書のような無機質なテキスト。読者がキャラクターに一切感情移入できない。",
    key_features=["無感情な事実報告", "心理描写ゼロ", "感情移入不能"],
))

register_anchor_preset(_EMOTION_CURVE_PRESET)


_STYLE_PRESET = AnchorPreset(specialist_name="style")

_STYLE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="style",
    tier="high",
    score=89.0,
    sample_text=(
        "濡れた石畳に、蹄の音が鋭く響いた。\n"
        "夜霧の向こうから漂うのは、噎せ返るような鉄と硝煙の匂い。\n"
        "抜剣の冷たい金属音が闇を切り裂く。\n"
        "「誰だ」\n"
        "短く問うた声に、応えるのは吹きすさぶ夜風だけだった。"
    ),
    critique="視覚・聴覚・嗅覚に訴える五感描写が卓越しており、文末のリズム（体言止め、短文、会話の配置）が極めて洗練されている。不要な説明を排した高密度の文体。",
    key_features=["優れた五感描写", "洗練されたリズムと文末多様性", "Show, Don't Tellの実践"],
))

_STYLE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="style",
    tier="mid",
    score=66.0,
    sample_text=(
        "夜の街を歩いていた。雨が降っていた。\n"
        "向こうから誰かが歩いてきた。怪しい男だった。\n"
        "男は剣を抜いた。とても強そうだった。\n"
        "私は警戒した。"
    ),
    critique="意味は明確で誤字もないが、「〜だった」「〜した」の文末が単調に連続し、文章のリズムが平坦。描写が平板で小説としての味わいや没入感に欠ける。",
    key_features=["文末の単調な連続", "平板な描写", "リズム感の不足"],
))

_STYLE_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="style",
    tier="low",
    score=36.0,
    sample_text=(
        "この状況においては、敵を撃破することが極めて肝要であるといえるだろう。\n"
        "主人公の心中には、一抹の不安が生じたのではないだろうか。\n"
        "なぜなら、相手は強力だからである。そして彼は剣を握ったのである。"
    ),
    critique="「〜といえるだろう」「〜ではないだろうか」等の解説・評論調のAI構文が地の文に侵入し、小説としての文体が完全に破綻している。主客の混同と不自然な語尾が頻出。",
    key_features=["解説調・論文調のAI構文", "小説文体の破綻", "読書没入感の完全阻害"],
))

register_anchor_preset(_STYLE_PRESET)


# ----------------------------------------------------------------------
# Step 6: Factual, Creativity & Multimodal Anchor Presets
# ----------------------------------------------------------------------
_FACTUAL_PRESET = AnchorPreset(specialist_name="factual")

_FACTUAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="factual",
    tier="high",
    score=90.0,
    sample_text=(
        "帆走フリゲート艦の甲板で、航海士は六分儀を構えて北極星の高度を測定した。\n"
        "「北緯三十四度、微風東南東。メインスルを展開し、針路をヘリオス島へ」\n"
        "潮の干満差と星の運行に基づく正確な操艦手順が指示される。"
    ),
    critique="18世紀帆船時代の航海術、観測機器（六分儀）、帆の名称、海洋物理の考証が極めて正確であり、描写の真実味が作品の説得力を力強く担保している。",
    key_features=["徹底した専門考証", "リアリティの担保", "世界観との完全な調和"],
))

_FACTUAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="factual",
    tier="mid",
    score=65.0,
    sample_text=(
        "船長はコンパスを見て船を進めた。\n"
        "「全速前進だ！」\n"
        "船は波をかき分けてぐんぐん進んでいった。"
    ),
    critique="帆船であるにもかかわらず「全速前進」などの蒸気船・近代船用語が使われており、風向や帆の扱いに関する具体的考証が曖昧。致命的ではないが粗さが残る。",
    key_features=["専門用語の軽微な混同", "考証の浅さ", "一般論にとどまる描写"],
))

_FACTUAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="factual",
    tier="low",
    score=35.0,
    sample_text=(
        "中世の騎士たちは、戦いの合間にペットボトルの水を飲みながらスマホで戦況を確認した。\n"
        "（※注: 現代転移やSFハイブリッドではなく、正統派歴史ファンタジー作品での描写）"
    ),
    critique="正統派中世世界観の中に、理由や設定の説明なく現代の工業製品（ペットボトル、スマホ）が混入している。時代考証・事実基盤の完全な破綻。",
    key_features=["時代錯誤（アクロニズム）", "世界観の破壊", "考証の完全放棄"],
))

register_anchor_preset(_FACTUAL_PRESET)


_CREATIVITY_PRESET = AnchorPreset(specialist_name="creativity")

_CREATIVITY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="creativity",
    tier="high",
    score=92.0,
    sample_text=(
        "通常は傷を癒やす回復魔法『ヒール』。\n"
        "アレンはそれを敵の体内に存在する無害な常在菌に向けて限界突破で注ぎ込んだ。\n"
        "急速に異常増殖した菌糸が内臓を圧迫し、巨獣は内側から身悶えして崩れ落ちる。\n"
        "「回復も、過剰になれば劇薬だ」"
    ),
    critique="治癒魔法を過剰投与して細胞や常在菌を暴走させるという、既存のテンプレートを逆手にとった独創的な魔術応用。読者の意表を突き知的好奇心を刺激する。",
    key_features=["テンプレートの鮮やかな反転", "新奇なアイデアと説得力", "独自の切り口"],
))

_CREATIVITY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="creativity",
    tier="mid",
    score=65.0,
    sample_text=(
        "アレンは右手から火球（ファイアボール）を放った。\n"
        "さらに魔力を込めて巨大な火炎嵐を作り出し、敵を焼き尽くした。"
    ),
    critique="ファンタジーの定石通りの攻撃魔法であり、無難にまとまっているが、他作品と差別化できるような新規性や意外性は見られない。",
    key_features=["王道の描写", "平均的な展開", "独自性の希薄さ"],
))

_CREATIVITY_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="creativity",
    tier="low",
    score=38.0,
    sample_text=(
        "主人公は神様からチート能力をもらい、右手をかざすだけで全知全能のスキルが発動した。\n"
        "敵は全員土下座し、ヒロインは全員一瞬で惚れた。"
    ),
    critique="手垢のついた陳腐なステレオタイプの極端な詰め合わせであり、オリジナリティや作者独自の工夫が皆無。読者に既視感と退屈を与える。",
    key_features=["陳腐なクリシェ（常套句）の乱用", "オリジナリティ皆無", "極端なご都合主義"],
))

register_anchor_preset(_CREATIVITY_PRESET)


_MULTIMODAL_PRESET = AnchorPreset(specialist_name="multimodal")

_MULTIMODAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="multimodal",
    tier="high",
    score=88.0,
    sample_text=(
        "【本文】紅蓮の夕日を背に受け、黒曜石の甲冑を纏った騎士が断崖に立つ。\n"
        "風にたなびく真紅のマントと、右手に握られた銀の長剣が黄金色の残光を反射していた。\n"
        "【挿絵プロンプト】A dark knight standing on a cliff edge at vivid sunset, crimson cloak billowing in wind, silver longsword reflecting golden sunlight, dramatic wide angle."
    ),
    critique="本文の色彩設計（紅蓮の夕日、黒曜石の甲冑、真紅のマント、銀の長剣）と挿絵プロンプトのビジュアル構成・カメラアングルが完璧に1対1で整合し、読者の脳内イメージを強く補強する。",
    key_features=["色彩・光源の完全一致", "ダイナミックな構図調和", "読者の視覚体験強化"],
))

_MULTIMODAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="multimodal",
    tier="mid",
    score=65.0,
    sample_text=(
        "【本文】騎士は崖の上に立ち、剣を抜いた。\n"
        "【挿絵プロンプト】A knight with sword on mountain, daytime."
    ),
    critique="シーンの状況は合致しているが、本文の描写が淡白で、挿絵プロンプトとのビジュアルシナジー（色彩や感情の共鳴）が弱い。",
    key_features=["大枠の整合のみ", "視覚的ディテールの不足", "シナジー効果の限定性"],
))

_MULTIMODAL_PRESET.add_anchor(AuditAnchorExample(
    specialist_name="multimodal",
    tier="low",
    score=30.0,
    sample_text=(
        "【本文】深夜の暗黒の地下迷宮、松明の明かりだけが揺れる。\n"
        "【挿絵プロンプト】A cheerful girl playing with a dog in a sunny flower garden, blue sky, peaceful."
    ),
    critique="本文（深夜の地下迷宮）と挿絵（晴天の花畑で遊ぶ少女）で舞台、時間帯、キャラクター、雰囲気が完全に乖離している。重大なマルチモーダル不整合。",
    key_features=["時間・空間の完全な矛盾", "ビジュアルクラッシュ", "重大なマルチモーダル破綻"],
))

register_anchor_preset(_MULTIMODAL_PRESET)





