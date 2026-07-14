from typing import List, List, Dict, Optional
from dataclasses import dataclass
import random

@dataclass
class NonVerbalCue:
    """
    非言語的な描写（視線、仕草、距離感）を定義する。
    """
    cue: str
    dimension: str  # "affection", "trust", "dependence", "tension"
    level: str       # "low", "mid", "high"
    intensity: str  # "subtle" (微細), "obvious" (明白), "intense" (強烈)

class BodyLanguageGenerator:
    """
    感情状態から非言語的な描写（身体性）を自動生成するエンジン。
    """
    
    # 非言語描写ライブラリ
    CUE_LIBRARY = {
        "affection": {
            "low": [
                NonVerbalCue("視線をわずかに逸らす", "affection", "low", "subtle"),
                NonVerbalCue("相手が近づいた時に小さく身を引く", "affection", "low", "obvious"),
                NonVerbalCue("表情を消し、事務的な態度を取る", "affection", "low", "obvious"),
            ],
            "mid": [
                NonVerbalCue("ふとした瞬間に相手を視線で追う", "affection", "mid", "subtle"),
                NonVerbalCue("穏やかな笑みを浮かべる", "affection", "mid", "subtle"),
                NonVerbalCue("自然な距離感で隣に立つ", "affection", "mid", "subtle"),
            ],
            "high": [
                NonVerbalCue("熱を帯びた視線でじっと見つめる", "affection", "high", "intense"),
                NonVerbalCue("無意識に相手の服の袖を掴む", "affection", "high", "obvious"),
                NonVerbalCue("相手の呼吸に合わせるように深く頷く", "affection", "high", "subtle"),
            ]
        },
        "trust": {
            "low": [
                NonVerbalCue("相手の言葉に眉をひそめる", "trust", "low", "subtle"),
                NonVerbalCue("腕を組み、防御的な姿勢を取る", "trust", "low", "obvious"),
                NonVerbalCue("相手の手元を警戒深く観察する", "trust", "low", "obvious"),
            ],
            "mid": [
                NonVerbalCue("相手の意見に自然に頷く", "trust", "mid", "subtle"),
                NonVerbalCue("リラックスして背もたれに身を預ける", "trust", "mid", "subtle"),
                NonVerbalCue("相手のペースに合わせ、歩調を揃える", "trust", "mid", "subtle"),
            ],
            "high": [
                NonVerbalCue("完全に無防備な姿勢で相手に身を任せる", "trust", "high", "obvious"),
                NonVerbalCue("視線を合わせずとも、相手の意図を察して動く", "trust", "high", "subtle"),
                NonVerbalCue("深く長い溜息をつき、全ての緊張を解く", "trust", "high", "obvious"),
            ]
        },
        "dependence": {
            "low": [
                NonVerbalCue("あえて一人で完結させようと背を向ける", "dependence", "low", "obvious"),
                NonVerbalCue("相手の助けを遮るように手を出す", "dependence", "low", "obvious"),
                NonVerbalCue("自立心を誇示するように顎を上げる", "dependence", "low", "subtle"),
            ],
            "mid": [
                NonVerbalCue("ふと相手の顔色を伺う", "dependence", "mid", "subtle"),
                NonVerbalCue("心地よい距離で寄り添う", "dependence", "mid", "subtle"),
                NonVerbalCue("迷った時にさりげなく相手の反応を確認する", "dependence", "mid", "subtle"),
            ],
            "high": [
                NonVerbalCue("相手の視線が外れると不安げに眉を寄せる", "dependence", "high", "obvious"),
                NonVerbalCue("縋るように相手の視線を追い求める", "dependence", "high", "intense"),
                NonVerbalCue("物理的な接触がないと落ち着かない様子を見せる", "dependence", "high", "obvious"),
            ]
        },
        "tension": {
            "low": [
                NonVerbalCue("あくびを噛み殺す", "tension", "low", "subtle"),
                NonVerbalCue("重心を崩してだらしなく座る", "tension", "low", "obvious"),
                NonVerbalCue("視線が定まらず、周囲を漫然と眺める", "tension", "low", "subtle"),
            ],
            "mid": [
                NonVerbalCue("わずかに身体を強張らせる", "tension", "mid", "subtle"),
                NonVerbalCue("相手との距離を測るように、ゆっくりと近づく", "tension", "mid", "subtle"),
                NonVerbalCue("視線がぶつかり、僅かに火花が散る", "tension", "mid", "obvious"),
            ],
            "high": [
                NonVerbalCue("呼吸が浅くなり、肩が上下する", "tension", "high", "obvious"),
                NonVerbalCue("指先が微かに震える", "tension", "high", "subtle"),
                NonVerbalCue("逃げ場のない至近距離で、互いの熱量を感じる", "tension", "high", "intense"),
            ]
        }
    }

    def generate_cues(self, state: 'ConnectionState', num_cues: int = 2) -> List[str]:
        """
        現在の感情状態に基づき、シーンに挿入すべき非言語描写を生成する。
        """
        candidates = []
        
        dims = {
            "affection": state.affection,
            "trust": state.trust,
            "dependence": state.dependence,
            "tension": state.tension
        }
        
        for dim, val in dims.items():
            level = "low" if val <= 30 else ("high" if val >= 70 else "mid")
            cues = self.CUE_LIBRARY[dim][level]
            candidates.extend(cues)
            
        if not candidates:
            return []
            
        selected = random.sample(candidates, min(num_cues, len(candidates)))
        return [s.cue for s in selected]

    def generate_non_verbal_prompt(self, char_a: str, char_b: str, state: 'ConnectionState') -> str:
        """
        LLMへの指示として、挿入すべき非言語描写をフォーマットして出力する。
        """
        cues = self.generate_cues(state)
        cues_str = "、".join(cues)
        
        return (
            f"【{char_a}の非言語描写ガイドライン】\n"
            f"以下の身体的反応を、シーンの適切な箇所にト書きとして挿入してください：\n"
            f"→ {cues_str}\n"
            f"※セリフで説明せず、視線、呼吸、微細な動作として描写してください。"
        )


# ==========================================
# 商用役割：ギャップ萌え表現パターン（ステップ20）
# ==========================================

# ギャップ萌え属性ペア对应的身体言語
GAP_MOE_BODY_LANGUAGE = {
    ("cold_aristocrat", "secret_sweet_tooth"): {
        "surface_behavior": [
            "常に完璧な作法を保ち、笑みを浮かべない",
            "讨论要紧事のみ，声音は低く冷たく",
            "谁にも近づきせず、一人で歩く",
        ],
        "gap_revealing_behavior": [
            "甘いものを前にした时、瞳が自然と輝く",
            "无意識に手を伸ばし、食べ物の包装纸を丁寧に抚でる",
            "「别に好きで食べたわけじゃない」と言いながら梦中で味わう",
            "嘴角に付いたクリームを気づきもせず微笑む",
        ],
    },
    ("fearless_warrior", "animal_lover"): {
        "surface_behavior": [
            "战场で恐れを知らない最强の战士",
            "谁都寄せ付けない杀気立つ风압",
            "笑うことは稀で、怖い颜ばかりしている",
        ],
        "gap_revealing_behavior": [
            "路地用动物を見かけると足を止め、じっと見つめる",
            "子犬や子猫を見つけた时、目が异常に柔らかくなる",
            "「触るな」と制ぎながら自分の袖で世话烧ける",
            "动物の前でのみ低声で饶有兴趣に话しかける",
        ],
    },
    ("respected_leader", "clumsy_daily_life"): {
        "surface_behavior": [
            " Presence，稳定感があり全场を魅了する",
            "社交的で全场をまとめ導く",
            "缺点がない完美な人物という评価",
        ],
        "gap_revealing_behavior": [
            " Severabilityに置くと必ずつまずく",
            " documentsをいつも飲み込んでしまう",
            "人前で纸袋を破ってコラー损失を出す",
            "紧张すると必ず过他にぶつかる",
        ],
    },
    ("sharp_tongued", "secret_soft_heart"): {
        "surface_behavior": [
            "口が悪い、毒舌で谁都zon分析する",
            "赞扬することは绝不会",
            "批评は具体的で容赦がない",
        ],
        "gap_revealing_behavior": [
            "不器用な优しさを隐性ながら世話を烧ける",
            "「别に关心したんじゃない」と言いながら薬を持たせる",
            "困ってる人の前だけ声が低くなる",
            "泣いてる子供の前だけ黙って隣に立つ",
        ],
    },
}


def gap_expression_patterns(
    surface_attribute: str,
    hidden_attribute: str
) -> Dict[str, List[str]]:
    """ギャップ萌えの身体言語パターンを取得
    
    Returns:
        {"surface": [...], "gap": [...]} 身体言語リスト
    """
    #  정확한ペアを探す
    pair_key = (surface_attribute, hidden_attribute)
    if pair_key in GAP_MOE_BODY_LANGUAGE:
        return GAP_MOE_BODY_LANGUAGE[pair_key]
    
    # 逆順でも探す
    reverse_key = (hidden_attribute, surface_attribute)
    if reverse_key in GAP_MOE_BODY_LANGUAGE:
        return GAP_MOE_BODY_LANGUAGE[reverse_key]
    
    # 部分的マッチを試みる
    for key, value in GAP_MOE_BODY_LANGUAGE.items():
        if surface_attribute in key[0] or hidden_attribute in key[1]:
            return value
    
    # フォールバック：汎用ギャップ表現
    return {
        "surface_behavior": [
            f"{surface_attribute}としての态度を保っている",
            "筋道を立てた話し方で感情を悟らせない",
        ],
        "gap_revealing_behavior": [
            f"しかし{hidden_attribute}な瞬间、表情が柔らかくなる",
            "无意識にそんな素振りを見せてしまう",
        ],
    }


def generate_gap_moe_scene_prompt(
    character_name: str,
    surface_attribute: str,
    hidden_attribute: str,
    trigger_situation: str = ""
) -> str:
    """ギャップ萌え場面の生成プロンプトを作成"""
    patterns = gap_expression_patterns(surface_attribute, hidden_attribute)
    
    surface_list = "\n".join([f"  - {s}" for s in patterns["surface_behavior"]])
    gap_list = "\n".join([f"  - {g}" for g in patterns["gap_revealing_behavior"]])
    
    return f"""
【ギャップ萌え場面の生成 - {character_name}】

■ 表面的な属性: {surface_attribute}
■ 隐藏的な属性: {hidden_attribute}

■ {character_name}の普段の行动（表面）:
{surface_list}

■ しかし、実は┗┓な行动（ギャップ発覚）:
{gap_list}

■ 指示:
{character_name}の「{surface_attribute}」な态度が确立されている狀況から、
ふとした切っ掛けで「{hidden_attribute}」が露呈する場面を描写してください。

要点:
1. 最初は完全に「{surface_attribute}」な人物として描画
2. あるトリガー（甘いもの、弱いもの、感人的な場面等）で隙ができる
3. 本人は気づいていないが、読者には明確に分かるギャップ
4. 最終的には「やらせない」态度で表面を保ち、読者は萌えを享受

状況: {trigger_situation or "（指定なし）"}
"""

