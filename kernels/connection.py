from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ConnectionState(BaseModel):
    """
    キャラクター間の感情状態を保持するモデル。
    次元ごとに0-100の数値で管理する。
    """
    affection: float = Field(default=50.0, ge=0.0, le=100.0)    # 親愛
    trust: float = Field(default=50.0, ge=0.0, le=100.0)        # 信頼
    dependence: float = Field(default=50.0, ge=0.0, le=100.0)   # 依存
    tension: float = Field(default=50.0, ge=0.0, le=100.0)      # 緊張

    # 関係性の「質」を定義するメタデータ
    bond_type: str = Field(default="acquaintance") # acquaintance, partner, co_conspirator, destiny_bond etc.
    resonance_level: int = Field(default=0, ge=0, le=5) # 心理的同期レベル (0-5)

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()

class ConnectionTrigger(BaseModel):
    """
    関係性深化を促すための介入トリガー。
    """
    trigger_id: str
    reason: str
    suggested_intervention: str
    priority: int = 1 # 1: Low, 5: Critical

class TranslationEngine:
    """
    数値的な感情状態を具体的な描写タグに変換するエンジン。
    """

    # 感情次元別のマトリクス定義
    # 構造: { 次元名: { レベル: { カテゴリ: [タグ] } } }
    MATRIX = {
        "affection": {
            "low": {
                "action": ["相手を避ける", "視線を合わせない", "形式的な対応に終始する"],
                "tone": ["冷淡な口調", "突き放すような言い回し", "最小限の言葉数"],
                "distance": ["物理的に距離を置く", "パーソナルスペースを厳格に守る"]
            },
            "mid": {
                "action": ["礼儀正しい態度", "時折微笑む", "適度な関心を示す"],
                "tone": ["標準的な丁寧語", "友好的だが一定の距離がある口調"],
                "distance": ["社会的に適切な距離感", "自然な視線のやり取り"]
            },
            "high": {
                "action": ["相手の小さな変化に気づき言及する", "無意識に相手に寄り添う", "深い慈しみを込めた動作"],
                "tone": ["親密で柔らかい口調", "内輪だけの共通言語や愛称の使用", "深い共感を示す相槌"],
                "distance": ["視線を長く合わせる", "身体的な接触を厭わない距離感"]
            }
        },
        "trust": {
            "low": {
                "action": ["相手の行動を監視する", "言葉の裏を読みすぎる", "重要な情報を隠す"],
                "tone": ["疑念を孕んだ問いかけ", "慎重に言葉を選ぶ", "冷ややかな確認"],
                "distance": ["警戒心による距離感", "相手の動きに敏感に反応する"]
            },
            "mid": {
                "action": ["概ね相手に任せる", "根拠がある場合は信頼する", "適度な確認を行う"],
                "tone": ["率直な意見交換", "信頼を前提としたが慎重な話し方"],
                "distance": ["リラックスした距離感", "自然な信頼関係に基づく間合い"]
            },
            "high": {
                "action": ["背中を完全に任せる", "言葉にしなくても意図を汲み取る", "全幅の信頼を寄せる動作"],
                "tone": ["迷いのない断定的な口調", "深い信頼に基づく率直な告白", "安心感を与えるトーン"],
                "distance": ["精神的な一体感を感じさせる距離", "完全に心を開いた姿勢"]
            }
        },
        "dependence": {
            "low": {
                "action": ["独力で解決しようとする", "相手の助けを拒む", "自立した態度を強調する"],
                "tone": ["自立心に満ちた口調", "相手を必要としない突き放した言い方"],
                "distance": ["独立した個としての距離感", "感情的に切り離された状態"]
            },
            "mid": {
                "action": ["適度に相談する", "必要な時にだけ頼る", "心地よい依存関係を維持する"],
                "tone": ["相談ベースの口調", "適度な甘えや頼り方"],
                "distance": ["相互補完的な心地よい距離感"]
            },
            "high": {
                "action": ["相手の不在に強い不安を示す", "相手の承認を強く求める", "盲目的に従う動作"],
                "tone": ["縋るような口調", "相手への心酔が滲む話し方", "不安げな確認"],
                "distance": ["密着した距離感", "精神的に寄りかかった姿勢"]
            }
        },
        "tension": {
            "low": {
                "action": ["完全にリラックスしている", "緊張感のない動作", "退屈そうにする"],
                "tone": ["弛緩した口調", "気だらげな話し方", "緊張感のないやり取り"],
                "distance": ["安定しすぎた距離感", "刺激のない静かな間合い"]
            },
            "mid": {
                "action": ["相手を意識した挙動", "適度な緊張感のある動作", "心地よい摩擦"],
                "tone": ["適度な刺激を含む口調", "意識し合っていることが伝わるトーン"],
                "distance": ["意識的な距離感", "惹かれ合うような絶妙な間合い"]
            },
            "high": {
                "action": ["激しい衝突や対立", "強烈な色気や衝動", "震えるほどの緊張感"],
                "tone": ["感情的な激しさを孕んだ口調", "張り詰めた空気感", "衝動的な言い回し"],
                "distance": ["爆発寸前の至近距離", "張り詰めた緊張感のある距離"]
            }
        }
    }

    @classmethod
    def _get_level(cls, value: float) -> str:
        if value <= 30: return "low"
        if value >= 70: return "high"
        return "mid"

    def get_tags(self, state: ConnectionState, category: str = "action") -> List[str]:
        """
        状態から指定されたカテゴリ（action, tone, distance）の描写タグを抽出する。
        """
        return self.get_tags_fixed(state, category)

    def get_tags_fixed(self, state: ConnectionState, category: str = "action") -> List[str]:
        all_tags = []
        dims = {"affection": state.affection, "trust": state.trust, "dependence": state.dependence, "tension": state.tension}
        for dim, val in dims.items():
            level = self._get_level(val)
            tags = self.MATRIX[dim][level].get(category, [])
            all_tags.extend(tags)
        return all_tags

    def get_all_guidelines(self, state: ConnectionState) -> Dict[str, List[str]]:
        """
        状態から描写ガイドラインを抽出する。
        信頼レベル（Trust Level）に基づき、アクセス可能な情報の深度を制限し、
        関係性の「質」に応じた特有の描写タグを追加する。
        """
        trust_level = state.trust
        bond_type = state.bond_type

        all_guidelines = {
            "action": self.get_tags_fixed(state, "action"),
            "tone": self.get_tags_fixed(state, "tone"),
            "distance": self.get_tags_fixed(state, "distance"),
        }

        # 関係性の質（Bond Type）による特有の描写を追加 (Phase 7)
        bond_specific_tags = {
            "co_conspirator": {
                "action": ["密やかな合図を交わす", "互いの意図を瞬時に察して動く"],
                "tone": ["外部には見せない共犯的な口調", "皮肉を共有する親密なトーン"],
                "distance": ["境界線を共有する一体感のある距離"]
            },
            "destiny_bond": {
                "action": ["運命的な必然性を感じさせる動作", "魂が惹かれ合うような深い凝視"],
                "tone": ["静謐で絶対的な信頼を孕んだ口調", "言葉を超えた理解に基づく沈黙"],
                "distance": ["精神的な境界が消失した至近距離"]
            },
            "dependence": {
                "action": ["相手の反応に過敏に反応する", "無意識に相手の衣服を掴む"],
                "tone": ["縋るような、あるいは支配的な口調", "相手の承認を求める切実なトーン"],
                "distance": ["依存的な密着感のある距離"]
            }
        }

        if bond_type in bond_specific_tags:
            specifics = bond_specific_tags[bond_type]
            for category in all_guidelines:
                all_guidelines[category].extend(specifics.get(category, []))

        return all_guidelines

class ConnectionStagnationDetector:
    """
    関係性の停滞（親密度や信頼度の数値が変動せず、物語的な深化が止まっている状態）を検知する。
    """
    def __init__(self, window_size: int = 5):
        self.window_size = window_size

    def detect(self, history: List[ConnectionState]) -> Optional[ConnectionTrigger]:
        if len(history) < self.window_size:
            return None

        recent = history[-self.window_size:]

        # 各次元の変動幅を計算
        dims = ["affection", "trust", "dependence"]
        is_stagnant = True
        for dim in dims:
            values = [getattr(s, dim) for s in recent]
            delta = max(values) - min(values)
            if delta > 5.0: # 変動幅が5以上あれば停滞していないとみなす
                is_stagnant = False
                break

        if is_stagnant:
            return ConnectionTrigger(
                trigger_id="RELATIONSHIP_STAGNATION",
                reason="関係性の数値変動が停滞しており、心理的深化が不足している",
                suggested_intervention="共有体験の創出、または隠された脆弱性の露呈（Vulnerability Reveal）をトリガーして、関係性のブレイクスルーを誘発せよ。",
                priority=3
            )
        return None

