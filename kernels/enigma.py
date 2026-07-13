from typing import Dict, List, Optional, Tuple

from kernels.base import KernelBase
from prompts.enigma_persona import ENIGMA_PERSONA


class EnigmaKernel(KernelBase):
    """
    情報の非対称性を管理し、伏線の提示・維持・回収を通じて
    知的カタルシス（Cognitive Catharsis）を設計するエンジン。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.persona = ENIGMA_PERSONA

    async def execute(self, context):
        if await self.should_intervene(context):
            return await self.generate_enigma_event(context)
        return None

    async def should_intervene(self, context) -> bool:
        """
        情報の欠落や、物語の停滞、または伏線回収のタイミングを検知して介入する。
        """
        analytics = getattr(context, 'analytics', None)
        if not analytics:
            return False

        # 1. 情報の停滞: 読者が「次に何が起きるか」を完全に予想できてしまい、好奇心が低下している場合
        curiosity_level = getattr(analytics, 'curiosity', 50)
        if curiosity_level < 40:
            return True

        # 2. 伏線回収のタイミング: 蓄積された伏線（Foreshadowing count）がある程度溜まっている場合
        # (context.foreshadowing に蓄積されている想定)
        foreshadowing = getattr(context, 'foreshadowing', [])
        if len(foreshadowing) >= 3:
            # 回収のタイミングを判断するロジック（例: tensionが高まった瞬間など）
            tension = getattr(analytics, 'tension', 0)
            if tension > 70:
                return True

        # 3. 謎の不在: 物語に「問い」が存在せず、単なるイベントの羅列になっている場合
        if getattr(analytics, 'is_too_predictable', False):
            return True

        return False

    async def generate_enigma_event(self, context):
        """
        状況に応じて「伏線の提示」「誤導（Red Herring）」「伏線の回収」を使い分ける。
        """
        # 1. 介入タイプの判定 (Setup / Reminder / Payoff)
        event_type = self._determine_enigma_event_type(context)

        # 2. パターン選択
        pattern = self._select_enigma_pattern(event_type)

        if event_type == "setup":
            # 伏線設計 ( prompts/enigma_foreshadowing_prompt.j2 )
            # scene = await self.llm.generate(prompt="prompts/enigma_foreshadowing_prompt.j2", context=context, pattern=pattern)
            pass
        elif event_type == "payoff":
            # 伏線回収と衝撃最大化 ( prompts/enigma_payoff_polish_prompt.j2 )
            # scene = await self.llm.generate(prompt="prompts/enigma_payoff_polish_prompt.j2", context=context, pattern=pattern)
            pass
        else:
            # 誤導やリマインドの生成
            pass

        # 3. 知的整合性監査 ( prompts/enigma_audit_prompt.j2 )
        # final_scene = await self._run_logical_audit(scene, context)
        # return final_scene
        return None

    def _determine_enigma_event_type(self, context) -> str:
        """
        現在の伏線数と物語の緊張度から、提示(Setup)か回収(Payoff)かを判定する。
        """
        foreshadowing = getattr(context, 'foreshadowing', [])
        tension = getattr(context.analytics, 'tension', 0)

        if len(foreshadowing) >= 3 and tension > 70:
            return "payoff"
        if len(foreshadowing) < 2:
            return "setup"
        return "reminder"

    def _select_enigma_pattern(self, event_type: str) -> dict:
        import json
        try:
            with open("config/data/enigma_patterns.json", "r", encoding="utf-8") as f:
                patterns = json.load(f)
            # イベントタイプに適したパターンを返す
            return patterns[0] # 簡易的に最初を返す
        except Exception:
            return {"pattern_id": "default", "name": "General Mystery"}

    async def _run_logical_audit(self, scene: str, context, max_retries: int = 2):
        """
        フェアプレイの原則に基づき、論理的矛盾や後出し設定がないかを監査する。
        """
        for i in range(max_retries):
            # audit_result = await self.llm.generate(prompt="prompts/enigma_audit_prompt.j2", context=context, scene=scene)
            # if "PASS" in audit_result: return scene
            # scene = await self.llm.generate(prompt="修正指示に基づく再構成", context=context, audit=audit_result)
            pass
        return scene

    def _analyze_information_gap(self, context) -> Dict:
        """
        「登場人物が知っていること」「読者が知っていること」「真実」の乖離を分析する。
        """
        # 情報の非対称性マップを生成するロジック
        return {
            "reader_gap": "known",
            "protagonist_gap": "unknown",
            "asymmetry_type": "dramatic_irony"
        }


# ==========================================
# 商用役割：情報独占ビルダー（ステップ19）
# ==========================================
from config.archetypes import INFORMATION_HEGEMONY_PATTERNS


class InformationMonopoly:
    """情報独占を管理するクラス"""

    def __init__(self, character_name: str, secret_type: str = "future_knowledge"):
        self.character_name = character_name
        self.secret_type = secret_type
        self.secret_content: Optional[str] = None
        self.reveal_progress: float = 0.0  # 0.0 - 1.0
        self.revealed_to: List[str] = []
        self.monopoly_intensity: float = 80.0  # 独占による優越感の強さ

    def register_secret(self, content: str):
        """秘密を登録"""
        self.secret_content = content

    def partial_reveal(self, target: str, reveal_amount: float = 0.2):
        """部分的な情報開示"""
        self.reveal_progress = min(1.0, self.reveal_progress + reveal_amount)
        if target not in self.revealed_to:
            self.revealed_to.append(target)

    def full_reveal(self):
        """完全な情報開示（カタルシスポイント）"""
        self.reveal_progress = 1.0

    def get_intellectual_pleasure_score(self) -> float:
        """知的快感を計算"""
        remaining_secret = 1.0 - self.reveal_progress
        return self.monopoly_intensity * remaining_secret


def information_monopoly_builder(
    protagonist_name: str,
    secret_holder_name: str,
    secret_type: str = "future_knowledge",
    context: str = ""
) -> Tuple[InformationMonopoly, str]:
    """情報独占を構築し、対応する伏線場面を生成
    
    Returns:
        (InformationMonopolyオブジェクト, 場面生成プロンプト)
    """
    pattern_desc = INFORMATION_HEGEMONY_PATTERNS.get(secret_type, "一般的な秘密")

    monopoly = InformationMonopoly(secret_holder_name, secret_type)

    prompt = f"""
【情報独占場面の生成 - {secret_holder_name}】

■ 主人公: {protagonist_name}
■ 秘密保持者: {secret_holder_name}
■ 秘密の種類: {pattern_desc}

■ 指示:
{secret_holder_name}だけが知っている「特別な情報」を描写してください。

要点:
1. {protagonist_name}は{secret_holder_name}の发言や行動に\"なぜ？\"と疑問を持つ
2. {secret_holder_name}は{'知識显示うかにして満足げな态度を取る' if secret_type == 'future_knowledge' else '秘密を共有しない'}
3. 読者と{protagonist_name}の間に「情報格差」が生まれる
4. この優位性により、{secret_holder_name}得有lyな優越感を漂わせる

文脈: {context or "（指定なし）"}
"""

    return (monopoly, prompt)


def build_information_hegemony_scene(
    protagonist_name: str,
    information_holder_name: str,
    monopoly: InformationMonopoly,
    scene_type: str = "monopoly"  # "monopoly" | "partial_reveal" | "full_reveal"
) -> str:
    """情報 hegemony 場面を生成
    
    Args:
        protagonist_name: 主人公名
        information_holder_name: 情報保持者名
        monopoly: InformationMonopolyオブジェクト
        scene_type: 場面タイプ
            - "monopoly": 情報を独占したまま優位性を見せる
            - "partial_reveal": 部分的に情報を明かす
            - "full_reveal": 完全に情報を明かす（最大のカタルシス）
    """
    from config.archetypes import INFORMATION_HEGEMONY_PATTERNS

    pattern_desc = INFORMATION_HEGEMONY_PATTERNS.get(monopoly.secret_type, "")

    templates = {
        "monopoly": f"""
【{information_holder_name}の情報の優位性を示す場面】

{information_holder_name}は知っている。
{monopoly.secret_content or "まだ明かせない何か"}を。

{protagonist_name}が苦しんでいる局面で、{information_holder_name}は静かに微笑む。

「大丈夫だ。全ては計算通りだから」

その言葉の意味を、{protagonist_name}はまだ理解できない。
しかし読者には、信息の差がもたらす圧倒的な優位性が伝わってくる。
""",
        "partial_reveal": f"""
【{information_holder_name}の部分的な情報開示】

{introduction_holder_name}はそろそろ时机だと思った。

{introduction_holder_name}が{prologue_name}に告げる。

「一つだけ教えておこう。{'今後の展開についての秘密' if monopoly.secret_type == 'future_knowledge' else '真実はもっと複雑な'}」

{introduction_holder_name}は一部だけを明かし、残りは┗┓に置き去りにする。

{introduction_holder_name}の笑みには、情報を保有する者特有の余裕が漂っている。
""",
        "full_reveal": f"""
【{information_holder_name}の完全なる真実開示 - 知的カタルシス】

{introduction_holder_name}がついに全てを明かした。

{introduction_holder_name}：「もう分かるだろう？ 最初から私は{'全てを知っていた' if monopoly.secret_type == 'future_knowledge' else '真実を把握していた'}」

{introduction_holder_name}の发言每一个が{prologue_name}の世界観を覆していく。

{introduction_holder_name}が独占していた情報が、一気に共有された瞬間。
{prologue_name}と{introduction_holder_name}の間に、「情報の壁」が崩れ落ちる。

{introduction_holder_name}：「怖かったのは、{'未来を変えられるかもしれない' if monopoly.secret_type == 'future_knowledge' else '真実に触れたくない'}きみの姿だ」

読者の持つ「全程認知」と{introduction_holder_name}の「 Exclusiveな知識」が一致し、知的カタルシスが発生する。
"""
    }

    return templates.get(scene_type, templates["monopoly"])

