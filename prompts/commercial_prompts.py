"""
Commercial Prompts Registry
商用化作品自動生成のためのプロンプトレジストリ

フェーズ3（ステップ25-36）：プロンプト・レジストリ拡張
"""

from typing import Any, Dict, List, Optional

from config.archetypes import (
    COMMERCIAL_ROLE_DESCRIPTIONS,
)

# =============================================================================
# ステップ25: Commercial Role Prompt Registry
# 商業的役割に応じたプロンプト生成
# =============================================================================

COMMERCIAL_ROLE_PROMPT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "avatar_of_desire": {
        "name": "自己投影・願望充足役",
        "scene_generation": (
            "読者 が{character}に感情移入し、自己投影できる場面を生成してください。\n"
            "■ 鍵となる要素:\n"
            "  1. {character}の行動を「俺だったらこうするのに」という視点で描写\n"
            "  2. 読者の願望（最強・最美・最受容）を直接満たす場面\n"
            "  3. 普遍的な欲望に訴える価値基準（正義・絆・成長）\n"
            "  4. 短絡的满足ではなく、目標への「過程」を重視し、投資심을育成\n"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 読者が渇望する「理想自己」を体現\n"
            "  - 弱点・苦悩を持たせ、共感と自己投影を両立\n"
            "  - 努力的描写で「応援したい」感を創出"
        ),
    },
    "hate_magnet": {
        "name": "憎悪集積型悪役",
        "scene_generation": (
            "読者 が{character}を憎む感情が积蓄される場面を生成してください。\n"
            "■ 憎悪蓄積パターン:\n"
            "  1. 不条理な傲慢さ（自分より立場の低い者を足で踏む）\n"
            "  2. 無神経なまでに残酷な発言（現在の努力を嘲笑）\n"
            "  3. 無敵な存在としての描画（現在の読者 heroesに報いない）\n"
            "  4. 特権階級的な横柄（証拠があっても処罰されない）\n"
            "■ 最終的なカタルシスに向け、憎悪を戦略的に蓄積"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 明確な「悪役」としての存在意義\n"
            "  - 倒了時のReaders'快感最大化为目标\n"
            "  - Comparable roleとの差别化を確保"
        ),
    },
    "unconditional_supporter": {
        "name": "絶対的肯定シェルター",
        "scene_generation": (
            "読者 と{character}が共にいる安心感·無条件の受容を感じる場面を生成してください。\n"
            "■ シェルター効果パターン:\n"
            "  1. 何しても受け入れてくれる温かさ\n"
            "  2. 失敗しても否定しない信頼感\n"
            "  3. ただそこに存在してくれる安心感\n"
            "  4. 言葉で雰囲わない「理解されている」感覚\n"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 現実には得られない「完全な受容」を投影可能に\n"
            "  - 他の役柄との組み合わせで相乗効果\n"
            "  - あたたかみ·包容力を体現する存在"
        ),
    },
    "contrast_engine": {
        "name": "ギャップ萌え駆動",
        "scene_generation": (
            "{character}の「表面的資質」と「内面的資質」のギャップを楽しめる場面を生成してください。\n"
            "■ ギャップパターン:\n"
            "  1. 強面の外見 × 涙脆い内面\n"
            "  2. 冷淡な態度 × 情熱的な本心\n"
            "  3. 学业最高 × 運動音痴\n"
            "  4. 冷酷な一面 × 子供のような素直さ\n"
            "■ 読者が「新事実発见!」と驚き、亲了近感を覚える展開"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 单一なイメージではなく「多层的な魅力」を付与\n"
            "  - 予想外の侧面発见で constantly新しい感動を提供\n"
            "  - 話が広がる· оценкаが広がる要素"
        ),
    },
    "unique_value": {
        "name": "希少能力・承認欲求充足",
        "scene_generation": (
            "{character}が唯一無二の価値を認められ、承認欲求が充足される場面を生成してください。\n"
            "■ 承認成就パターン:\n"
            "  1. 誰も気づかなかった事に光が当てられる\n"
            "  2. その人がからこそ成せる事の証明\n"
            "  3. 長年の努力が報われる瞬間\n"
            "  4. 「お前にはやはり特別なんだ」と認知される"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 読者も同样的承認欲求を持つ場合への共振\n"
            "  - 「特別な存在になりたい」という愿望の投影先\n"
            "  - 努力が報われるプロセスへの共感"
        ),
    },
    "growth_investment": {
        "name": "成長可視化・投資心理喚起",
        "scene_generation": (
            "{character}の成長過程を追い、その成長がユーザーに「投資した甲斐があった」と感じさせる場面を生成してください。\n"
            "■ 成長可視化パターン:\n"
            "  1. 過去の自分_vs_現在の自分の明确な差分\n"
            "  2. 当時は無理だった事が「今」は簡単\n"
            "  3. かつてのバカにしていた存在を「今」は一笑に付す\n"
            "  4. 成長速度が加速している事の可视化管理\n"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 「あの頃から見るとこんなにも育った」感を最大化\n"
            "  - ユーザーが早期に始めた投资が高原になる快感\n"
            "  - 成長ストーリーへの持续的関心"
        ),
    },
    "destined_resonance": {
        "name": "運命的結びつき",
        "scene_generation": (
            "{character}と他の運命的な結びつきが感じられる場面を生成してください。\n"
            "■ 運命パターン:\n"
            "  1. 出会いが偶然ではない暗示\n"
            "  2. 似た傷を持つ者同士の本能的惹近\n"
            "  3.  Portrait配合の暗示\n"
            "  4. 紞が解けて自然と结びつく再生\n"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 「この二人は결국，结ばれるべき」という期待感\n"
            "  - 读者の愛実现願望の投影先\n"
            "  - 关系性の深まりへの持続的期待"
        ),
    },
    "information_hegemony": {
        "name": "情報支配・知的快感",
        "scene_generation": (
            "{character}が情報を支配し、读者に「私だけが知っている」快感を与える場面を生成してください。\n"
            "■ 情報支配パターン:\n"
            "  1. 読者だけが知る秘密（他のキャラクターは知らない）\n"
            "  2. 他のキャラクターの误解を讀者是正できる瞬間\n"
            "  3. 伏線が回収され、「だから!」と繋がる快感\n"
            "  4. 複雑骨折な関係が整理され、見通しが良くなる"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 信息的優越感の提供\n"
            "  - 推理・理解の樂趣の付与\n"
            "  - 読み返すことで新たな発見がある構造の提供"
        ),
    },
    "status_flip_trigger": {
        "name": "地位反転トリガー",
        "scene_generation": (
            "{character}を通じて社会的地位の反転を描き、「待ってた！」というカタルシスを与える場面を生成してください。\n"
            "■ ステータス反転パターン:\n"
            "  1. 低位からの出発→高位への到達\n"
            "  2. 以前は勝てなかった相手への復讐·雪辱\n"
            "  3. 見下していた人間からの評価改变\n"
            "  4. 絶対的権力者の弱体化·降格\n"
        ),
        "character_building": (
            "■ {character}の商業的価値を構築:\n"
            "  - 社会流动の愿望着色の投影先\n"
            "  - 「下克上」「成り上がり」愿望の充足\n"
            "  - 社会的サ suspect 成功の代理体験"
        ),
    },
}


def commercial_role_prompt_registry(
    role: str,
    character_name: str,
    prompt_type: str = "scene_generation",
) -> str:
    """
    商業的役割に応じたプロンプトを取得する。
    
    Args:
        role: 商業的役割名
        character_name: キャラクター名
        prompt_type: プロンプトタイプ (scene_generation/character_building)
    
    Returns:
        生成されたプロンプト文字列
    """
    role_data = COMMERCIAL_ROLE_PROMPT_TEMPLATES.get(role, COMMERCIAL_ROLE_PROMPT_TEMPLATES["avatar_of_desire"])
    template = role_data.get(prompt_type, role_data["scene_generation"])

    return template.format(character=character_name)


def generate_commercial_role_summary(character_name: str, roles: List[str]) -> str:
    """
    キャラクターの商業的役割全てのサマリーを生成。
    
    Args:
        character_name: キャラクター名
        roles: 役割リスト
    
    Returns:
        役割サマリーのプロンプト
    """
    role_infos = []
    for role in roles:
        desc = COMMERCIAL_ROLE_DESCRIPTIONS.get(role, "")
        template_data = COMMERCIAL_ROLE_PROMPT_TEMPLATES.get(role, {})
        name = template_data.get("name", role)
        role_infos.append(f"■ {name}: {desc}")

    return (
        f"【{character_name}の商業的役割サマリー】\n"
        + "\n".join(role_infos) + "\n"
        "※ これらの役割を意識した物語構築を行ってください。"
    )


# =============================================================================
# ステップ26-27: Pleasure Prompt Registry (快感設計・カタルシス管理)
# =============================================================================

PLEASURE_GRAPH_PROMPT_TEMPLATES: Dict[str, str] = {
    "catharsis_building": (
        "【カタルシス構築プロンプト】\n"
        "■ 目的: 最終的な感情的な開放・満足感の最大化\n"
        "■ 構成要素:\n"
        "  1. TENSION_ELEVATION: 緊張・期待の段階的構築\n"
        "  2. OBSTACLE_ACCUMULATION: 障壁・苦难の重ね刷け\n"
        "  3. DESPERATE_STRUGGLE: 追い込み・決断の場面\n"
        "  4. CATHARTIC_RELEASE: 解放・成就・逆襲の瞬間\n"
        "■ 報酬設計: 苦难が深いほど、カタルシスは大きくなる"
    ),
    "schadenfreude_building": (
        "【審判・滅びのプロンプト】\n"
        "■ 目的: 憎い奴が落ちる快感の最大化\n"
        "■ 構成要素:\n"
        "  1. HATE_ACCUMULATION: 犯行の蓄積による憎悪増幅\n"
        "  2. ARROGANCE_PEAK: 犯行が頂点に達する傲慢さ\n"
        "  3. EVIDENCE_REVELATION: 証拠·真実の暴露\n"
        "  4. PUBLIC_FALL: 皆の前での権威失墜·制裁\n"
        "■ 感情的設計: 憎い奴が「掉ちる瞬間」に最大のカタルシス"
    ),
    "tension_release_building": (
        "【緊張→緩和リズムのプロンプト】\n"
        "■ 目的: リズム良好的な感情の波の創出\n"
        "■ パターン:\n"
        "  1. 緊張局面（対立·危机·障壁）\n"
        "  2. 窒息感的anen（微かな希望·小さな前進）\n"
        "  3. 緩和局面（危機突破·関係修復·成長の證）\n"
        "  4. 新しい緊張の予告\n"
        "■ 報酬設計: 「一山越えるたびに小さなカタルシス」を積み重ねる"
    ),
    "superiority_building": (
        "【優越感・全能感のプロンプト】\n"
        "■ 目的: 讀者が「俺は正しい·強い·美しい」を体験\n"
        "■ 構成要素:\n"
        "  1. IDOLIZATION_TARGET: 理想像の描写\n"
        "  2. COMPARISON_CONTEXT: 周囲との比較での優越性\n"
        "  3. RIVAL_DEFEAT: 競合他者の論破·完封\n"
        "  4. RECOGNITION_ACQUISITION: 他者からの認知·赞赏\n"
        "■ 報酬設計: 理想自己の投影と、他人より優れた优越感"
    ),
    "intimacy_building": (
        "【親密感・連帯感のプロンプト】\n"
        "■ 目的: キャラクター同士の絆·読者の参加意識\n"
        "■ 構成要素:\n"
        "  1. SHARED_STRUGGLE: 共に困难を乗り越える経験\n"
        "  2. VULNERABLE_MOMENT: 互いに無防備になる親密場面\n"
        "  3. MUTUAL_RECOGNITION: 相互理解·感謝的表达\n"
        "  4. BOND_RENEWAL: 絆の更新·深化\n"
        "■ 報酬設計: 「この二人の関係を見ていたい」という願望充足"
    ),
}


def pleasure_prompt_registry(
    pleasure_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    快感設計（カタルシス）プロンプトを取得する。
    
    Args:
        pleasure_type: 快感タイプ (catharsis_building/schadenfreude_building/tension_release_building/superiority_building/intimacy_building)
        context: オプションの文脈情報
    
    Returns:
        快感設計プロンプト文字列
    """
    template = PLEASURE_GRAPH_PROMPT_TEMPLATES.get(
        pleasure_type,
        PLEASURE_GRAPH_PROMPT_TEMPLATES["catharsis_building"]
    )

    if context:
        formatted = template
        for key, value in context.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))
        return formatted

    return template


def generate_pleasure_graph_prompt(
    story_progress: float,
    target_catharsis: float = 0.8,
) -> str:
    """
    物語の進行度に応じた快感グラフ最適化プロンプトを生成。
    
    Args:
        story_progress: 物語の進行度 (0.0-1.0)
        target_catharsis: 目標カタルシス値
    
    Returns:
        快感バランス調整プロンプト
    """
    if story_progress < 0.3:
        phase = "導入期"
        directive = "期待の構築・投資の開始"
    elif story_progress < 0.6:
        phase = "展開期"
        directive = "緊張の維持・障壁の蓄積"
    elif story_progress < 0.85:
        phase = "逼近期"
        directive = "追い込み・决策の準備"
    else:
        phase = "決戦期"
        directive = f"最大カタルシス（目標: {target_catharsis:.0%}）"

    return (
        f"【快感グラフ最適化: {phase}】\n"
        f"■ 物語進捗: {story_progress:.0%}\n"
        f"■ 現在のフェーズ指示: {directive}\n"
        f"■ 快感設計原則:\n"
        f"  - 現在のカタルシス投資: {story_progress:.0%}的程度完了\n"
        f"  - 残りの投資で {(1-story_progress):.0%} のカタルシスを構築\n"
        f"  - 山場に向けた伏線回収を意識してください"
    )


# =============================================================================
# ステップ28: Marketing & Style Prompt Registry
# =============================================================================

MARKETING_PROMPT_TEMPLATES: Dict[str, str] = {
    "hook_generation": (
        "【フック・キャッチコピー生成】\n"
        "■ 目的: 讀者を惹きつける「読みたくなる」最初の1行\n"
        "■ 原則:\n"
        "  1. 好奇心扇動: 物語の始まりで疑問を提示\n"
        "  2. 感情惹起: 「かわいい」「感人」「怖い」等の即時的感情\n"
        "  3. 謎かけ: 讀者が答えを探したくなる構図\n"
        "  4. 衝突提示: 魅力的な対立の暗示\n"
    ),
    "tagline_generation": (
        "【 tagline·本作を表現する一言】\n"
        "■ 目的: 作品の本質を端的網羅\n"
        "■ パターン:\n"
        "  1. 設定押し: 「世界上唯一の『─』を持つ少年」\n"
        "  2. 感情押し: 「かつての初恋の、答え合わせ」\n"
        "  3. アクション押し: 「俺は今日、親を殺した」\n"
        "  4. 期待違反: 「勇者，却在，留年勇士vs.魔王」\n"
    ),
    "synopsis_generation": (
        "【 あらすじ・概要生成】\n"
        "■ 目的: 作品の魅力を短時間で伝達\n"
        "■ 構成:\n"
        "  1. 主人公と世界観の提示（簡潔に）\n"
        "  2. 主な冲突・障壁の示唆\n"
        "  3. 魅力的な独自要素の強調\n"
        "  4. 讀者が期待する展開の暗示\n"
    ),
}


STYLE_DNA_PROMPT_TEMPLATES: Dict[str, str] = {
    "voice_extraction": (
        "【文体DNA抽出】\n"
        "■ 目的: 作品の固有の語り口·スタイルを定義\n"
        "■ 抽出要素:\n"
        "  1. 語り手の视角（一人称/三人称有限/三人称全能）\n"
        "  2. 文章のテンポ（短文主体/長文あり/リズム感）\n"
        "  3. 感情表出の密度（多い/節制/必要なところに集中）\n"
        "  4. 特有表現·高频語句の特定\n"
    ),
    "character_voice_extraction": (
        "【キャラクターバイス抽出】\n"
        "■ 目的: 各キャラクターの对话パターンを定義\n"
        "■ 抽出要素:\n"
        "  1. 話し方の特徴（敬語/タメ口/独特的語尾）\n"
        "  2. 心理活動の頻度·形態\n"
        "  3. 价值观·口癖の特定\n"
        "  4. 他のキャラクターとの对话時の変化\n"
    ),
    "rhythm_pattern_extraction": (
        "【リズムパターン抽出】\n"
        "■ 目的: 物語の時間経過のテンポ感を定義\n"
        "■ 抽出要素:\n"
        "  1. 1章あたりの分量·話数の進行速度\n"
        "  2. 情景描写と会話の比率\n"
        "  3. 山場·尻すぼらしの周期的パターン\n"
        "  4.  читательの期待との一致度\n"
    ),
}


def marketing_prompt_registry(
    marketing_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    マーケティング素材生成プロンプトを取得する。
    
    Args:
        marketing_type: マーケティングタイプ (hook_generation/tagline_generation/synopsis_generation)
        context: オプションの文脈情報
    
    Returns:
        マーケティングプロンプト文字列
    """
    template = MARKETING_PROMPT_TEMPLATES.get(
        marketing_type,
        MARKETING_PROMPT_TEMPLATES["hook_generation"]
    )

    if context:
        formatted = template
        for key, value in context.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))
        return formatted

    return template


def style_prompt_registry(
    style_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    スタイルDNA抽出プロンプトを取得する。
    
    Args:
        style_type: スタイルタイプ (voice_extraction/character_voice_extraction/rhythm_pattern_extraction)
        context: オプションの文脈情報
    
    Returns:
        スタイルDNAプロンプト文字列
    """
    template = STYLE_DNA_PROMPT_TEMPLATES.get(
        style_type,
        STYLE_DNA_PROMPT_TEMPLATES["voice_extraction"]
    )

    if context:
        formatted = template
        for key, value in context.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))
        return formatted

    return template


# =============================================================================
# ステップ29-32: Series & A/B Test Prompt Registry
# =============================================================================

SERIES_EXPENSION_PROMPTS: Dict[str, str] = {
    "arc_planning": (
        "【シリーズ展開·阿部計画】\n"
        "■ 目的: 最初の物語で成功后、続けるべき物語の計画\n"
        "■ 構成要素:\n"
        "  1. MAIN_CHARACTER_GROWTH: 主人公の成長道のりの設計\n"
        "  2. VILLAIN_ESCALATION: 敵·障壁の階層的強化\n"
        "  3. ROMANCE_PROGRESSION: 関係性の段階的深化\n"
        "  4. WORLD_EXPANSION: 世界観の段階的開示\n"
    ),
    "sequel_hooks": (
        "【後続作への口火·伏線管理】\n"
        "■ 目的: 読者を次作に引き寄せる要素の確保\n"
        "■ パターン:\n"
        "  1. UNRESOLVED_TENSION: 未解決の緊張関係の放置\n"
        "  2. NEW_THREAT_INTRO: 新たな威胁の示唆\n"
        "  3. CHARACTER_POTENTIAL: 未発動のキャラクター潜力\n"
        "  4. WORLD_MYSTERY: 世界に関する新たな疑問提示\n"
    ),
    "filler_strategy": (
        "【 стороны・エピソード設計】\n"
        "■ 目的: メイン筋と並行する魅力的な短編\n"
        "■ 構成:\n"
        "  1. CHARACTER_EPISODE: 配役キャラクターの掘り下げ話\n"
        "  2. WORLD_BUILDING: 世界観の細部の見える化\n"
        "  3. RELATIONSHIP_BUILDING: 関係性を試す小波乱\n"
        "  4. COMEDY_RELIEF: 息的抜き·ユーモア挿入\n"
    ),
}


AB_TEST_PROMPTS: Dict[str, str] = {
    "opening_variation": (
        "【A/Bテスト: 開始場面バライエーション】\n"
        "■ テスト対象: 物語の入り口\n"
        "■ パターンA: 謎かけ始め（ читатель的好奇心立即刺激）\n"
        "■ パターンB: 衝突始め（ читательの感情即時投入）\n"
        "■ パターンC: 日常始め（ читательの親近感確保）\n"
    ),
    "conflictr_resolution_variation": (
        "【A/Bテスト: 冲突解決バライエーション】\n"
        "■ テスト対象: 障壁への対処\n"
        "■ パターンA: 力地解决（物理的な解決·成長の證）\n"
        "■ パターンB: 智恵力解决（戦略·話術·機知）\n"
        "■ パターンC: 偶然解决（運命的な出会い·幸運）\n"
    ),
    "romance_development_variation": (
        "【A/Bテスト: ロマンス展開バライエーション】\n"
        "■ テスト対象: 恋愛要素の進め方\n"
        "■ パターンA: 一騎打ち型（互いに的意识の对方）\n"
        "■ パターンB: 信頼構築型（共に困难乗り越え自然発生）\n"
        "■ パターンC: 三角関係型（恋のライバル導入）\n"
    ),
}


def series_prompt_registry(
    series_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    シリーズ展開プロンプトを取得する。
    
    Args:
        series_type: シリーズタイプ (arc_planning/sequel_hooks/filler_strategy)
        context: オプションの文脈情報
    
    Returns:
        シリーズ展開プロンプト文字列
    """
    template = SERIES_EXPENSION_PROMPTS.get(
        series_type,
        SERIES_EXPENSION_PROMPTS["arc_planning"]
    )

    if context:
        formatted = template
        for key, value in context.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))
        return formatted

    return template


def ab_test_prompt_registry(
    test_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    A/Bテスト用プロンプトを取得する。
    
    Args:
        test_type: テストタイプ (opening_variation/conflictr_resolution_variation/romance_development_variation)
        context: オプションの文脈情報
    
    Returns:
        A/Bテストプロンプト文字列
    """
    template = AB_TEST_PROMPTS.get(
        test_type,
        AB_TEST_PROMPTS["opening_variation"]
    )

    if context:
        formatted = template
        for key, value in context.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))
        return formatted

    return template


def generate_full_commercial_prompt_pack(
    character_name: str,
    commercial_roles: List[str],
    target_market: str = "web novel",
) -> Dict[str, str]:
    """
    完全な商用プロンプトパックを生成。
    
    Args:
        character_name: キャラクター名
        commercial_roles: 商業的役割リスト
        target_market: 目標市場 (web novel/kindle/comics)
    
    Returns:
        プロンプトパック辞書
    """
    pack = {}

    # 商業的役割プロンプト
    for role in commercial_roles:
        pack[f"commercial_role_{role}"] = commercial_role_prompt_registry(
            role=role,
            character_name=character_name,
            prompt_type="scene_generation"
        )

    # 快感設計プロンプト
    pack["pleasure_catharsis"] = pleasure_prompt_registry("catharsis_building")
    pack["pleasure_schadenfreude"] = pleasure_prompt_registry("schadenfreude_building")
    pack["pleasure_tension_release"] = pleasure_prompt_registry("tension_release_building")
    pack["pleasure_superiority"] = pleasure_prompt_registry("superiority_building")
    pack["pleasure_intimacy"] = pleasure_prompt_registry("intimacy_building")

    # マーケティングプロンプト
    pack["marketing_hook"] = marketing_prompt_registry("hook_generation")
    pack["marketing_tagline"] = marketing_prompt_registry("tagline_generation")
    pack["marketing_synopsis"] = marketing_prompt_registry("synopsis_generation")

    # スタイルDNAプロンプト
    pack["style_voice"] = style_prompt_registry("voice_extraction")
    pack["style_character"] = style_prompt_registry("character_voice_extraction")
    pack["style_rhythm"] = style_prompt_registry("rhythm_pattern_extraction")

    # シリーズ展開プロンプト
    pack["series_arc"] = series_prompt_registry("arc_planning")
    pack["series_hooks"] = series_prompt_registry("sequel_hooks")
    pack["series_filler"] = series_prompt_registry("filler_strategy")

    # A/Bテストプロンプト
    pack["ab_opening"] = ab_test_prompt_registry("opening_variation")
    pack["ab_conflict"] = ab_test_prompt_registry("conflictr_resolution_variation")
    pack["ab_romance"] = ab_test_prompt_registry("romance_development_variation")

    # 市場別調整
    if target_market == "web novel":
        pack["platform_optimization"] = (
            "【プラットフォーム最適化: ウェブ小説】\n"
            "■ 特徴: 長期連載向け·読み続けさせる構造\n"
            "■ 最適化ポイント:\n"
            "  - 各話の終わりに「次に続く」構造\n"
            "  - 1話あたりの分量: 2000-3000文字\n"
            "  - 段落を短く·読みやすさを優先"
        )
    elif target_market == "kindle":
        pack["platform_optimization"] = (
            "【プラットフォーム最適化: Kindle】\n"
            "■ 特徴: 一冊完結型·密度の高い物語\n"
            "■ 最適化ポイント:\n"
            "  - 最初から最後まで一貫した的主題\n"
            "  - 山場の十分な盛り上がり\n"
            "  - 読み终わり感のある決着"
        )

    return pack

