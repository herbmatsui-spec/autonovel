"""Style Distiller Service
ユーザーから提供されたテキストサンプル（500〜1,000文字）から、
作家性DNA（StyleProfile）を自動分析・抽出（蒸留）するサービス。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.models.style_profile import (
    MetaphorFrequency,
    SentenceEndDistribution,
    SentenceLengthModel,
    StyleProfile,
)
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.factory import get_llm_adapter

logger = logging.getLogger(__name__)

STYLE_DISTILLER_SYSTEM_PROMPT = """あなたはプロの小説文体アナリストおよび文芸編集者です。
与えられた小説テキスト（サンプル）の「文体・リズム・語彙・比喩・ケレン味」を精密に逆算分析し、
その作家特有のDNA（StyleProfile）をJSON形式で抽出してください。

【分析観点】
1. tone_description: 語り口（クール、熱血、皮肉、重厚、軽妙など）
2. sentence_length: 平均文長、短文・長文の分布
3. sentence_end_distribution: 文末（だ・である、体言止め、です・ます、！等）の割合
4. metaphor_frequency: 比喩の頻度と五感（視覚・触覚・聴覚など）の偏り
5. kerenmi_intensity: ハッタリ・過剰演出・感情の誇張の度合い（0.0〜1.0）
6. required_patterns: この文体を再現するために必須の言い回しやリズム特徴
7. forbidden_patterns: この文体の味を殺してしまうAI特有の手癖（無感情な報告、〜だったの連続など）
8. few_shot_sample: この文章の中で最も「味」が出ている100〜250文字の抜粋

【出力JSONフォーマット】
必ず以下のキーを持つJSONオブジェクトのみを出力してください（Markdownコードブロックは含めないか、```json```で囲んでください）：
{
  "name": "抽出された文体名（例: 疾走ダークヒーロー調）",
  "tone_description": "...",
  "sentence_length": {
    "avg": 35,
    "std_dev": 10,
    "min": 10,
    "max": 75,
    "description": "..."
  },
  "sentence_end_distribution": {
    "desu_masu": 0.05,
    "da_dearu": 0.65,
    "nominal": 0.20,
    "exclamatory": 0.08,
    "interrogative": 0.02,
    "description": "..."
  },
  "metaphor_frequency": {
    "per_1000_chars": 4.0,
    "types": {
      "visual": 0.45,
      "tactile": 0.25,
      "auditory": 0.15,
      "kinesthetic": 0.10,
      "abstract": 0.05
    },
    "description": "..."
  },
  "kerenmi_intensity": 0.85,
  "required_patterns": ["...", "..."],
  "forbidden_patterns": ["...", "..."],
  "few_shot_sample": "..."
}
"""

STYLE_DISTILLER_USER_PROMPT = """以下の小説サンプルテキストを分析し、StyleProfile JSONを出力してください。

【サンプルテキスト】
{sample_text}
"""

NOTABLE_STYLE_SAMPLES: dict[str, dict] = {
    "style_web_standard": {
        "name": "なろう・カクヨム標準（テンポ重視）",
        "sample": "光かがやく。チート能力炸裂の瞬間。敵は紙切れのように崩れ落ちた。主人公は淡々と振り返らない。その姿に周囲は惊叹するも、本人はborg。ま、いっか。",
    },
    "style_serious_fantasy": {
        "name": "ハイファンタジー（無職転生風）",
        "sample": "泥水を啣みしめる感触。前世の記憶がフラッシュバックする。古傷の疼きが、足取りを重くした。窓から差し込む弱い光が、冷たい雨の音と共に回忆を呼び起こす。",
    },
    "style_psychological_loop": {
        "name": "死に戻り・絶望（リゼロ風）",
        "sample": "熱い熱い熱い。臓腑が冷えていく。吐瀉物の酸味が鼻を突く。世界の音が歪んでいく。あの、政、嘘だと言い張る自分の声が、懐かしく響く。",
    },
    "style_chat_log": {
        "name": "ダンジョン配信（掲示板・コメント風）",
        "sample": "草草草w 結局このダンジョン突破した的风 Bootstrap??? 楼主超人！ 実況開始→敗北 →リベンジ →草",
    },
    "style_villainess_elegant": {
        "name": "悪役令嬢（優雅・皮肉）",
        "sample": "扇で口元を隠し、微笑を浮かべるですわ。あの平民が司徒の目を楽しませようとは、愚かなことですねことですわ。 Dress details.",
    },
    "style_military_rational": {
        "name": "戦記・合理的（幼女戦記風）",
        "sample": "故に、本作戦は合理的に妥当である。敵の損耗率は推定十二パーセント。、眼鏡を押し上げ、軍服の襟を正す。无能な味方は批判した。",
    },
    "style_comedy_speed": {
        "name": "高速コメディ（このすば風）",
        "sample": "正义 Execute! 声の裏返り、白目、 土下座的速度!ボケ→ope!!!ツッコミ被せの三拍子。拟音拟音拟音。",
    },
    "style_dark_hero": {
        "name": "ダークヒーロー（ありふれ風）",
        "sample": "真紅の光が部屋に満ちる。敵は肉塊と化した。身内だけは甘えられる。冷たく嘲う:「愚か者」",
    },
    "style_overlord": {
        "name": "勘違い・魔王（オバロ風）",
        "sample": "私はAbsolute Dark Overseer。配下は畏怖の視線を向ける。（この发言装得太大了......) 威厳を保ちながら咳払い。",
    },
    "style_bookworm_daily": {
        "name": "ビブリオ・日常（本好き風）",
        "sample": "本の背表紙をなぞる指。羊皮紙のざらついた感触に、胸が跃る。黄金と呼べる瑰水を部屋に並べた。活字中毒の徒が、快楽を貪る。",
    },
    "style_light_fun": {
        "name": "ライト・エンタメ（爽快・軽快）",
        "sample": "秒で終わらせたる！ 餐間の一瞬も無駄にしない快乐操作性! 彼の顔が三点リーダーで笑う。",
    },
    "style_iron_wall": {
        "name": "鉄壁・重厚（タンク無双）",
        "sample": "盾は動かない。どの程度の衝撃が来ようとも。敵の矢は羽虫のように弾かれ、盾の裏側に伝わる微かな振動だけが存在を知らせる。",
    },
    "style_evolution": {
        "name": "野生・進化（弱肉強食）",
        "sample": "胃袋が鳴る。喉から込み上げる本能の咆哮。皮膚の下で何かが蠢く。カタカタ、牙が萌えたとき、意識は飲まれた。",
    },
    "style_forbidden_library": {
        "name": "全知・神秘（禁書司書）",
        "sample": "古びた書物の感触。文字が網膜に吸い込まれる。眼鏡を直す指が、紙の海をNavigieren。世界の真理は、一冊の本に収まっている。",
    },
    "style_high_luck_gambler": {
        "name": "心理・狂気（豪運ギャンブラー）",
        "sample": "コインが旋转する。指先が震え、カードを捲る。確率は操る者のもの。脑裏に鳴り响く歓喜のファンファーレ。リスクが快感に化する瞬間。",
    },
    "style_melody_mage": {
        "name": "詩的・旋律（音楽魔法）",
        "sample": "共鳴が空気を震わせる。旋律が世界の形を変える。静寂の中に響く一音の波紋。感情は音色となり、音波となって世界を包む。",
    },
    "style_true_ancestor": {
        "name": "優雅・君臨（吸血鬼真祖）",
        "sample": "深紅の瞳が月光を映す。闇の眷属として、夜を支配する。人間を『家畜』とも『器』とも呼ばず、ただ冷たく見下ろす。優雅なる哉。",
    },
    "style_relic_repairer": {
        "name": "職人・緻密（遺物修理屋）",
        "sample": "磨损した歯車に耳を当てる。微かな擦れ音が、指の延長として伝わる。油の匂い。失われた技が、ようやく눈을 떴다。",
    },
    "style_cursed_sword": {
        "name": "鋭利・孤独（呪いの剣聖）",
        "sample": "刃が走る。血を甩く音。静寂の中、呪いが肉体を蝕む疼き。すべてを削ぎ落とした先にあるのは、孤独のみ。",
    },
    "style_shadow_ruler": {
        "name": "冷徹・策略（影の支配者）",
        "sample": "チェスの駒が動く。影の中で糸を引く者の笑み。愚かな者共が舞台の上で起舞く。その操り人を、私は知っている。",
    },
    "style_onmyoji_master": {
        "name": "和風・律儀（最強陰陽師）",
        "sample": "印を結ぶ。狩衣の袖が風に揺れる。五行の理に従い、式神が姿を現す。紙吹雪の舞い散る中、邪霊を焼き清める。",
    },
    "style_flash_blade": {
        "name": "閃光一刀・疾走感",
        "sample": "刃が走る。……一本。血飛沫が宙を舞う。敵の身体が崩れ落ちるまでの一秒。振り返らない。振り返る暇など、ない。",
    },
    "style_burst_comedy": {
        "name": "弾けコメディ・擬音洪水",
        "sample": "ばあかーん！ 声裏返り、白目、 土下座一波い！拟音拟音拟音☆ ボケ→ope!!! 弾ける笑顔が世界を覆う。",
    },
    "style_dungeon_party": {
        "name": "冒険パーティ・連携",
        "sample": "ダンジョンの壁に松明の明かりが揺れる。MTP——。『次どうする？』『任せて！』 仲間との呼吸が一致する瞬間。",
    },
    "style_slime_chill": {
        "name": "スライム無双・淡定",
        "sample": "するりと笑いを得る。攻击は水たまりに溶ける。淡定として状況を飲み込み、画面が酿し出す储け。",
    },
    "style_cinematic_action": {
        "name": "映画カット・戦闘美学",
        "sample": "血飛沫が宙を舞う。カメラがパン。スローで捕らえる刃の軌跡。フィルムの粒子が战斗の美しさを际立たせる。",
    },
    "style_epic_fantasy": {
        "name": "叙事詩ファンタジー・古書",
        "sample": "古びた書物を開けば、埃が舞い上がる。森の気配が肌を撫でる。歴史の重みが、静かに積み上げられていく。",
    },
    "style_historical_saga": {
        "name": "歴史大河・土の匂い",
        "sample": "馬の蹄が土を蹴る。市場の喧騒が遠く響く。世代を超えて伝わる物語を、今日は私も紡ぐ。",
    },
    "style_minimal_quiet": {
        "name": "寡黙・最小限の美",
        "sample": "沈黙。呼吸さえも削がれる。言葉の前に立ち尽くす。金属の刃だけが、冷たく光っている。",
    },
    "style_philosophy_maze": {
        "name": "迷宮思索・自己対話",
        "sample": "自らの影が壁を侵蚀する。思考が迷宮を形成する。立ち止まり、 lamps を片手に、Mixinな自問を 반복する。",
    },
    "style_kyoto_seasons": {
        "name": "古都四季・湯気と光",
        "sample": "湯気の白さが朝の光に溶ける。五重の塔がシルエットで見える。風鈴の音が遠くで響く。京都の季節が移ろい行く。",
    },
    "style_isekai_romance": {
        "name": "異世界恋愛・魔法陣",
        "sample": "魔法陣が淡く光る。召喚の光が走る。贵族の令嬢は、私の前に立ちはだかり、「もう放手しない」と喘く。",
    },
    "style_mystery_observe": {
        "name": "観察ミステリ・鍵穴",
        "sample": "鍵穴から覗く影。わずかな震動。証拠は静かに积累する。推理が弧を描き、やがて真相に到达する。",
    },
    "style_youth_bittersweet": {
        "name": "青春微熱・夕陽部活",
        "sample": "夕陽が部を照らす。汗の跡が光る。練習结束后、切なさが胸を过る。もう帰れないあの瞬間が、思い出になる。",
    },
    "style_intellectual_talk": {
        "name": "知的会話劇・破綻",
        "sample": "知的会話が弾む。空気が少し静まる。观察 точки。对方の答えに、少しだけ椅子の緑が揺らぐ。",
    },
    "style_dark_hierarchy": {
        "name": "暗黒階層・崩壊秩序",
        "sample": "金字塔の影が落ちる。鎖が軋む。階層が崩壊する音が、微かに近づく。支配者の笑みが、崩れ落ちる秩序の中で歪む。",
    },
    "style_poetic_wind": {
        "name": "詩的風景・余韻",
        "sample": "風の匂いが鼻をくすぐる。葉の震えが语る。夕暮れの沈黙の中、足音が遠ざかる。残余の余韻だけが、空気に漂う。",
    },
    "style_aesthetic_flesh": {
        "name": "美学肉体・官能緊張",
        "sample": "深紅の唇が光を映す。肉の感覚が意識を占领する。美と死の境界線で、精神が震える。",
    },
    "style_private_confession": {
        "name": "私小説・弱さ直視",
        "sample": "雨が窓を伝う。泣き笑いの后在宅の声。是自己的弱的直視。嘆きが染み入った墨的味道。",
    },
    "style_daily_warmth": {
        "name": "日常温もり・紅茶窓辺",
        "sample": "湯気が窓辺の光に溶ける。紅茶の温もりが指先に伝わる。窓の外で鳥が鳴く。小さな幸せを累积していく。",
    },
    "style_wa_japanese": {
        "name": "和風律儀・印と袖",
        "sample": "印を結ぶ。狩衣の袖が風に揺れる。五行の理に従い、式神が姿を現す。紙吹雪の舞い散る中、邪霊を焼き清める。",
    },
}


class StyleDistillerService:
    """作家性DNA抽出サービス"""

    def __init__(self, llm_adapter: BaseLLMAdapter | None = None):
        self._llm = llm_adapter

    @property
    def llm(self) -> BaseLLMAdapter:
        if self._llm is None:
            self._llm = get_llm_adapter()
        return self._llm

    async def distill_from_text(
        self, sample_text: str, name_hint: str | None = None
    ) -> StyleProfile:
        """サンプルテキストからStyleProfileを抽出"""
        cleaned_text = sample_text.strip()
        if not cleaned_text:
            return StyleProfile(name="デフォルト標準文体")

        stats_profile = self._calculate_rule_based_stats(cleaned_text, name_hint)

        prompt = STYLE_DISTILLER_USER_PROMPT.format(sample_text=cleaned_text[:2500])
        try:
            response_text = await self.llm.generate_text(
                prompt=prompt,
                system_prompt=STYLE_DISTILLER_SYSTEM_PROMPT,
                max_tokens=1500,
            )
            parsed = self._extract_json_from_response(response_text)
            if parsed and isinstance(parsed, dict):
                profile_data = {**stats_profile.model_dump(), **parsed}
                if name_hint:
                    profile_data["name"] = name_hint
                profile_data["raw_sample"] = cleaned_text[:500]
                if not profile_data.get("few_shot_sample"):
                    profile_data["few_shot_sample"] = cleaned_text[:250]
                return StyleProfile(**profile_data)
        except Exception as e:
            logger.warning(f"LLM style distillation failed, using rule-based stats: {e}")

        return stats_profile

    def _calculate_rule_based_stats(self, text: str, name_hint: str | None = None) -> StyleProfile:
        """正規表現・統計によるルールベースの簡易文体解析"""
        sentences = [s.strip() for s in re.split(r"[。！？!?\n]+", text) if s.strip()]
        if not sentences:
            return StyleProfile(name=name_hint or "カスタム文体", raw_sample=text[:500])

        lengths = [len(s) for s in sentences]
        avg_len = int(sum(lengths) / len(lengths))
        min_len = min(lengths)
        max_len = max(lengths)

        da_dearu_count = sum(
            1 for s in sentences if s.endswith(("だ", "である", "た", "いた", "った"))
        )
        desu_masu_count = sum(
            1 for s in sentences if s.endswith(("です", "ます", "でした", "ました"))
        )
        nominal_count = sum(
            1
            for s in sentences
            if not s.endswith(
                ("だ", "である", "た", "いた", "った", "です", "ます", "でした", "ました")
            )
        )
        total_s = max(len(sentences), 1)

        sample_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        few_shot = sample_paragraphs[0] if sample_paragraphs else text[:250]

        profile = StyleProfile(
            name=name_hint or "分析されたカスタム文体",
            tone_description="メリハリのあるリズムと特徴的な語彙を持つ文体",
            sentence_length=SentenceLengthModel(
                avg=avg_len,
                std_dev=10,
                min=min_len,
                max=max_len,
                description=f"平均{avg_len}文字のリズム",
            ),
            sentence_end_distribution=SentenceEndDistribution(
                desu_masu=round(desu_masu_count / total_s, 2),
                da_dearu=round(da_dearu_count / total_s, 2),
                nominal=round(nominal_count / total_s, 2),
                exclamatory=0.08,
                interrogative=0.02,
                description="だ・である調と体言止めのバランス",
            ),
            metaphor_frequency=MetaphorFrequency(
                per_1000_chars=3.5,
                description="五感を刺激する比喩表現",
            ),
            kerenmi_intensity=0.8,
            few_shot_sample=few_shot[:300],
            raw_sample=text[:500],
        )

        if name_hint and name_hint in NOTABLE_STYLE_SAMPLES:
            sample_data = NOTABLE_STYLE_SAMPLES[name_hint]
            profile.name = sample_data["name"]
            profile.few_shot_sample = sample_data["sample"]

        return profile

    def _extract_json_from_response(self, text: str) -> dict[str, Any] | None:
        """LLMの応答テキストからJSON部分を抽出"""
        try:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                return json.loads(match.group(1))
            return json.loads(text.strip())
        except Exception:
            return None


style_distiller_service = StyleDistillerService()
