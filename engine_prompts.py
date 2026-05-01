import json
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from jinja2 import Environment
import streamlit as st
import re
from config import (
    RULE_SET_A_RULES, RULE_SET_B_RULES, RULE_SET_C_RULES, RULE_SET_D_RULES,
    STYLE_DEFINITIONS, VILLAIN_STRATEGIES, FORBIDDEN_WORD_REPLACEMENTS, CONTENT_SEPARATOR, STYLE_REFINEMENT_DIRECTIONS
)
from models import CharacterRegistry, CharacterRelationship, PlotDbModel, PlotEpisode

@st.cache_resource
def _get_rule_sets() -> Dict[str, str]:
    return {"RULE_SET_A": RULE_SET_A_RULES, "RULE_SET_B": RULE_SET_B_RULES, "RULE_SET_C": RULE_SET_C_RULES, "RULE_SET_D": RULE_SET_D_RULES}

def get_rule_set(key: str) -> str:
    return _get_rule_sets().get(key, RULE_SET_A_RULES)

class PromptManager:
    """プロンプト構築ロジックを一括管理"""
    def __init__(self, jinja_env: Environment):
        self.jinja_env = jinja_env

    def get_style_instruction(self, style_key: str) -> str:
        style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
        dna_correction = (
            "\n\n【文体的DNA矯正（絶対遵守）】\n"
            f"1. 構文・リズム: {style_def.get('syntax_rhythm', '')}\n"
            f"2. 固有比喩・感覚辞書: {style_def.get('metaphor_dna', '')}\n"
            f"3. 思考ノイズ・生理反応: {style_def.get('noise_dna', '')}\n"
            "4. 文末の多様性: 同じ文末の3連続を禁止。体言止め、倒置法を徹底せよ。\n"
            "5. 五感のノルマ: 重要シーンでは視覚以外の五感を積極的に含めよ。\n"
        )
        template = self.jinja_env.get_template("style_instruction.j2")
        return template.render(
            style_name=style_def["name"],
            dialogue_ratio=style_def.get("dialogue_ratio", "50%"),
            instruction=style_def["instruction"],
            dna_correction=dna_correction,
        )

    def get_villain_instruction(self, genre: str) -> str:
        for key, strategy in VILLAIN_STRATEGIES.items():
            if key in genre: return strategy
        return VILLAIN_STRATEGIES["default"]

    def build_refinement_prompt(self, content: str, style_key: str, is_light: bool, target_word_count: int) -> str:
        style_def = STYLE_DEFINITIONS.get(style_key, STYLE_DEFINITIONS["style_web_standard"])
        direction = STYLE_REFINEMENT_DIRECTIONS["light" if is_light else "heavy"]

        return (
            f"あなたは「読者を物語の中毒にさせる」天才作家です。\n{direction}\n"
            f"対象スタイル: {style_def['name']}\n目標文字数: {target_word_count}\n\n"
            f"【修正指針】\n1. AI定型句の抹殺。2. 五感描写を解像度150%に引き上げ。3. 離脱防止のフック。\n\n"
            f"【草稿】\n{content}"
        )

    def get_plot_common_rules(self) -> str:
        return """
【真・プロット設計黄金律 10カ条（絶対遵守）】
1. [1話1シーンと高解像度化]: 時間スキップ・ダイジェストを禁ずる。
2. [Show, Don't Tell]: 感情は肉体動作に翻訳し、各シーンに3つ以上の具体的な五感情報を組み込め。
3. [能動性と意志の火]: 窮地での「小さな抵抗（意志）」を必ず描け。
4. [悪役の知略]: 敵対者を知略的な存在とし、カタルシス前話では尊厳を奪い、ストレスを極限まで溜めよ。
5. [認識のズレ]: 主人公の意図と周囲の解釈の乖離を物語の推進力とせよ。
10. [伏線の先行配置]: 逆転の数行前までに伏線を配置し、ご都合主義を防げ。
"""

    def _build_quota_section(self, scenes_data: Any, target_word_count: int) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""
            
        # 要素が辞書でない場合の救済（リスト内の文字列など）
        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        total_impact = sum(s.get('impact_score', 50) for s in normalized_scenes) or 1
        inst = "【執筆ノルマ】\n"
        for i, s in enumerate(normalized_scenes):
            impact = s.get('impact_score', 50)
            scene_quota = max(100, int((target_word_count * (impact / total_impact)) * 1.8))
            role = "💥 爆発" if impact >= 80 else "📋 導入" if impact <= 30 else "⏳ 展開"
            inst += f"- シーン{i+1} [{role}]: 目標 {scene_quota} 字以上。最低 5段落以上。\n"
        return inst

    def _build_show_tell_section(self, scenes_data: Any) -> str:
        if isinstance(scenes_data, str):
            scenes_data = [{"action": scenes_data}]
        if not isinstance(scenes_data, list) or not scenes_data:
            return ""

        # 要素が辞書でない場合の救済（リスト内の文字列など）
        normalized_scenes = [s if isinstance(s, dict) else {"action": str(s)} for s in scenes_data]
        inst = "【描写方針】\n"
        for i, s in enumerate(normalized_scenes):
            impact = s.get('impact_score', 50)
            if impact >= 70:
                inst += f"- シーン{i+1}: 【Show全開】五感を飽和させ、筋肉の痙攣や視線の動きを執拗に描写せよ。\n"
            elif impact <= 30:
                inst += f"- シーン{i+1}: 【Tell要約】状況を簡潔に流し、テンポを重視せよ。\n"
        return inst

    def _build_forbidden_section(self) -> str:
        word = random.choice(list(FORBIDDEN_WORD_REPLACEMENTS.keys()))
        return (
            f"【🚨禁忌語・強制置換🚨】\n「{word}」の使用を禁ずる。代わりに {FORBIDDEN_WORD_REPLACEMENTS[word]} を用いて具体化せly。\n"
            "物語を『あらすじ』のように語るな。キャラの視界から出るな。\n"
        )

    def _build_hook_strategy_section(self) -> str:
        return (
            "【ダイナミック・フック戦略】\n"
            "1. 冒頭3行: 読者が現実で抱える欠落（万能感、復讐心等）を即座に刺激する一文で始めよ。\n"
            "2. 末尾5行: 予定調和を破壊し、読者が『次をクリックせざるを得ない』強烈なクリフハンガーを配置せよ。\n"
        )

    def _build_assertion_section(self, constraints: List[Any]) -> str:
        if not constraints: return ""
        inst = "【🚨因果律ユニットテスト：論理制約の絶対遵守🚨】\n"
        for c in constraints:
            if isinstance(c, dict):
                inst += f"- {c.get('subject')}: {c.get('constraint')} (違反した場合は即座にリライト対象となる)\n"
        return inst

    def build_final_writing_prompt(self, ep_num: int, plot_data: Dict[str, Any], script_text: str, target_word_count: int, plot_thought_process: str = "", **kwargs) -> str:
        # 各セクションをモジュールとして構築
        scenes_data = plot_data.get("scenes", [])
        quota_inst = self._build_quota_section(scenes_data, target_word_count)
        show_tell_inst = self._build_show_tell_section(scenes_data)
        forbidden_inst = self._build_forbidden_section()
        hook_inst = self._build_hook_strategy_section()
        
        # 論理制約 (Category B)
        settings_ctx = kwargs.get('settings_ctx', '{}')
        if isinstance(settings_ctx, str):
            try:
                settings_ctx = json.loads(settings_ctx)
            except:
                settings_ctx = {}
        if not isinstance(settings_ctx, dict):
            settings_ctx = {}

        assertion_inst = self._build_assertion_section(settings_ctx.get('active_constraints', []))
        
        # 視点・トーン
        phase = plot_data.get("current_chain_phase", "Hate")
        tone_inst = f"【フェーズトーン: {phase}】\n"
        if phase == "Hate": tone_inst += "読者の『ざまぁ』欲求を最大化せよ。敵の傲慢さと不当な辱めを執拗に描写せよ。\n"
        elif phase == "Payoff": tone_inst += "周囲の『絶望・後悔・畏怖』の反応描写に文字数の7割を割け。\n"

        # 最終テンプレート
        template = self.jinja_env.from_string("""
本文開始前に [thought_process] を出力せよ:
1. シーンごとの緩急の峻別 2. 目標文字数配分 3. 読者の情緒を破壊する一文 4. 五感情報の優先順位 5. 冒頭・末尾のフック戦略

{{ quota_inst }}
{{ show_tell_inst }}
{{ forbidden_inst }}
{{ hook_inst }}
{{ assertion_inst }}

【作品文脈】
不変属性: {{ char_static_ctx }}
動的状態: {{ char_dynamic_ctx }}
既知の文脈: {{ prev_ctx }}

【指令】
■ 台本 (絶対遵守): {{ script_text }}
■ プロット設計図: {{ blueprint }}
■ 目標文字数: {{ target_word_count }} 字以上
{{ tone_inst }}
{{ style_sample }}
{{ director_notes }}

--- 出力形式 ---
[thought_process]
{{ CONTENT_SEPARATOR }}
[NOVEL_CONTENT]
{{ CONTENT_SEPARATOR }}
[METADATA_JSON]
""")

        return template.render(
            quota_inst=quota_inst,
            show_tell_inst=show_tell_inst,
            forbidden_inst=forbidden_inst,
            hook_inst=hook_inst,
            assertion_inst=assertion_inst,
            char_static_ctx=kwargs.get('char_static_ctx', ''),
            char_dynamic_ctx=kwargs.get('char_dynamic_ctx', ''),
            prev_ctx=kwargs.get('prev_ctx', ''),
            script_text=script_text,
            blueprint=plot_data.get('detailed_blueprint', ''),
            target_word_count=target_word_count,
            tone_inst=tone_inst,
            style_sample=f"【文体継承】\n{kwargs.get('prose_sample')}" if kwargs.get('prose_sample') else "",
            director_notes=f"【⚠️修正指示】\n{kwargs.get('director_notes')}" if kwargs.get('director_notes') else "",
            CONTENT_SEPARATOR=CONTENT_SEPARATOR
        )

    def build_producer_audit_prompt(self, genre: str, keywords: str, trend_memo: str) -> str:
        available_tropes = [
            "ざまぁ", "断罪", "成り上がり", "無自覚無双", "圧倒的報復", "追放ざまぁ",
            "ヤンデレヒロイン", "実は有能な従者", "狂信的な配下", "不遇な天才", "共依存",
            "戦わない最強", "復讐しない追放者", "善人すぎる悪役",
        ]
        template = self.jinja_env.get_template("ai_producer_audit")
        prompt = template.render(genre=genre, keywords=keywords, trend_memo=trend_memo)
        prompt += (
            f"\n\n【必須出力項目（JSONキー）】"
            f"\n1. refined_keywords: ブラッシュアップされた覇権キーワード（カンマ区切り）"
            f"\n2. refined_concept: 商業的に最適化された物語コンセプト（300文字程度）"
            f"\n3. refined_mc_suggestion: 読者の共感と欲望を刺激する主人公像の具体的な提案"
            f"\n4. recommended_tropes: 推奨されるトロープのリスト（文字列の配列）"
            f"\n\n【指令】商用出版でランキング1位を狙える具体的な修正案を、上記項目を網羅したJSON形式のみで出力してください。"
            f"【選択可能な要素リスト】: {', '.join(available_tropes)}"
        )
        return prompt

    def build_logical_audit_prompt(self, past_facts: str, plot_bp: str, script: str) -> str:
        return (
            "あなたは物語の整合性監査官です。以下の過去の事実と今回のプロットに矛盾がないか確認してください。\n\n"
            f"【過去の事実】\n{past_facts}\n\n【プロット】\n{plot_bp}\n\n【台本】\n{script}"
        )

    def build_foreshadowing_audit_prompt(self, f_map: List[Dict[str, Any]], content: str) -> str:
        return (
            f"伏線回収監査:\n【予定リスト】\n{json.dumps(f_map, ensure_ascii=False)}\n\n"
            f"【本文】\n{content[:4000]}"
        )

    def build_misunderstanding_validation_prompt(self, content: str, gap_desc: str) -> str:
        return (
            "以下の小説本文を解析し、『勘違い（認識の乖離）』の発生プロセスが以下の4ステップを正しく踏んでいるか判定せよ。\n\n"
            "【検証ステップ】\n"
            "A（事実）: 客観的な状況が提示されているか\n"
            "B（絶望）: 視点主、または周囲が一時的な絶望や危機を感じているか\n"
            "C（誤認）: 主人公の行動が、事実とは異なる文脈で劇的に誤解されているか\n"
            "D（覚醒）: その誤解により、周囲の評価が爆発的に向上（または事態が好転）しているか\n\n"
            f"【本文】:\n{content[:3000]}\n\n"
            f"【設定された乖離】:\n{gap_desc}\n\n"
            "Output Schema (JSON):\n"
            '{"passed": bool, "missing_steps": ["A", "B"], "reason": "理由"}'
        )

    def build_marketing_pack_prompt(self, book_title: str, synopsis: str, latest_ep: int) -> str:
        return (
            f"作品『{book_title}』の宣伝パックを生成してください。\n"
            f"最新話: 第{latest_ep}話\n"
            f"あらすじ: {synopsis}\n\n"
            "以下を生成:\n"
            "1. カクヨム用キャッチコピー（35文字以内、作品の最大の魅力とフックを端的に）\n"
            "2. カクヨム近況ノート用の投稿文（300文字程度、あらすじのハイライト）\n"
            "3. 推奨タグ（カクヨム向け、「ざまぁ」「主人公最強」「追放」「チート」など人気頻出タグを最低3つ含む10個）\n\n"
            "Output Schema (JSON):\n"
            '{"catchphrase": "...", "kakuyomu_notes": "...", "tags": ["..."]}'
        )

    def build_title_generation_prompt(self, genre: str, keywords: str) -> str:
        return (
            f"ジャンル: {genre}\nキーワード: {keywords}\n\n"
            "カクヨム総合ランキング1位を奪取するための【戦略的長文タイトル】を3案出せ。\n"
            "【鉄則】1. 40-100文字の超長文にせよ。 2. 『追放された最強の〜』『実は〜だった件』『今さら戻れと言われても〜』等のトレンド強ワードを必ず含めよ。 3. タイトルがあらすじを兼ねるようにせよ。\n"
            'Output Schema (JSON): {"titles": ["案1", "案2", "案3"]}'
        )

    def build_style_dna_analysis_prompt(self, sample_text: str) -> str:
        return (
            "以下の小説サンプルを分析し、その文体のDNAを抽出してください。\n\n"
            f"【サンプル】\n{sample_text[:3000]}\n\n"
            "Output Schema (JSON):\n"
            '{"name": "文体名", "instruction": "執筆指示", "score": 75, "analysis": "分析レポート"}'
        )

    def build_world_creation_prompt(self, genre: str, keywords: str, response_schema: BaseModel) -> str:
        return (
            f"あなたは世界構築のプロフェッショナルです。ジャンル: {genre}, キーワード: {keywords} に基づき、"
            "以下の2層を詳細に構築してください。なお、**出力内容はすべて日本語で行うこと。**\n"
            "1. 物理・魔導・社会法則と因果関係（causality_map）。"
            "世界を覆う「理不尽なタブー」や「将来対峙すべき絶対的脅威（ラスボスや暗躍する組織の影）」を必ず1つ因果律に含めること。\n"
            "2. 歴史・文化・五感地図（Sensory Map）\n"
            f"Output Schema: {response_schema.model_json_schema()}"
        )

    def build_mc_creation_prompt(self, world_rules_json: str, genre: str, keywords: str, concept: str = "") -> str:
        return (
            "あなたはキャラクター造形の神であり、カクヨムで読者の心を抉り、執着させる『生きた』キャラクターを生み出すプロです。\n"
            f"【企画概要】ジャンル: {genre} / キーワード: {keywords} / コンセプト: {concept}\n"
            f"世界観: {world_rules_json}\n"
            "【指令：主人公（MC）を超解像度で造形せよ】\n"
            f"CharacterRegistryの全フィールドを、以下の5つの次元で深掘りして埋めよ。\n"
            f"1. 【三層構造の精神】: \n"
            f"   - surface_persona (表層（社会的仮面）): 周囲からどう見られているか。どのような役割を演じているか。\n"
            f"   - inner_conflict (中層（内的矛盾）): 演じている自分と、本当の望みの間の引き裂かれるような葛藤。\n"
            f"   - core_trauma (深層（原初の欠落）): 過去の何が彼を決定的に壊したのか。何を埋めるために戦っているのか。\n"
            f"2. 【チートと代償の呪縛】: その能力はなぜ『彼』に宿ったのか。能力を使うたびに削られる精神的・肉体的なコストを、読者が「痛々しい」と感じるレベルで設定せよ。\n"
            f"3. 【絶対遵守の鉄則(Iron Constraint)】: 「死んでもこれだけは曲げない」という異常なまでのこだわり。これが物語の最大のピンチを生む原因となるようにせよ。\n"
            f"4. 【五感に刺さる描写フック(Expansion Hooks)】: 執筆時に描写を3倍に膨らませるための具体的材料を5つ以上記述せよ。\n"
            f"   （例：特定の傷跡が疼く感触、怒った時に無意識に噛む唇の味、魔力放出時の焦げた花の匂い、特定の音楽や音に対する過剰な反応など）\n"
            f"5. 【覇権の口調と独白スタイル】: 他者に見せる外面のセリフと、脳内での「猛烈に個性的でシニカル、あるいは熱狂的な独白」の対比を明確にせよ。\n\n"
            f"【制約】\n"
            f"- dialogue_samples は、そのキャラの『特異な思考回路』が漏れ出すものを3つ以上。\n"
            f"- save_the_cat_event (Save the Cat要素)を、過去の経歴に具体的に組み込め。\n"
            f"- 全ての出力は日本語で行うこと。\n"
            f"Output Schema (JSON):\n"
            f"{CharacterRegistry.model_json_schema()}"
        )

    def build_sub_char_creation_prompt(self, world_rules_json: str, mc_data_json: str, causality_map: List[str], mc_name: str) -> str:
        return (
            "あなたはキャラクター造形の神であり、カクヨムで読者の心を抉り、執着させる『生きた』キャラクターを生み出すプロです。\n"
            f"世界観: {world_rules_json}\n"
            f"主人公情報: {mc_data_json}\n"
            f"世界の因果律: {json.dumps(causality_map, ensure_ascii=False)}\n\n"
            "【指令：3倍の解像度で3名を生成せよ】\n"
            f"CharacterRegistryの全フィールドを、以下の5つのレイヤーを完璧に構築し、埋めたJSONを出力せよ。\n"
            f"1. fate_link (運命の鎖): 世界の因果律（causality_map）のどの部分を体現しているか。世界が壊れた際に彼らが何を失うか。\n"
            f"2. social_mask_vs_truth (社会的仮面と生理的真実): 表向きの地位と、夜一人でいる時に見せる『剥き出しのトラウマや歪み』の対比。\n"
            f"3. relationships (MCへの重層的な感情): 単なる味方・敵ではなく、MC({mc_name})に対する「羨望、軽蔑、執着、恩義、恐怖」が入り混じった複雑なベクトル。なぜMCに出会ってしまったことが彼らの人生の最大級の事件なのか。CharacterRelationshipモデルのリストとして記述せよ。\n"
            "4. 【絶対遵守の鉄則(Iron Constraint)】: キャラが絶対にやらないこと、または死んでも守る異常なこだわり（執筆時の行動指針）。\n"
            "5. 【高解像度フック(Expansion Hooks)】: 執筆時に描写を3倍に膨らませるための具体的材料（例：焦った時に爪を噛む音、特定のハーブの香りへの執着、MCの特定の仕草に対する生理的嫌悪）。\n\n"
            "【必須出力項目】\n"
            "- registry_data内の expansion_hooks は最低5つ以上、具体的かつフェティッシュに記述せよ。\n"
            "- dialogue_samples は、そのキャラの『特異な思考回路』が漏れ出すセリフを3つ以上、一人称・二人称を厳守して記述せよ。\n"
            "- relationships には、MCだけでなく生成する他のサブキャラ同士の『秘密の相関関係』を含めよ。\n\n"
            "Output Schema (JSON):\n"
            f'{{"characters": [{CharacterRegistry.model_json_schema()}]}}'
        )

    def build_bible_creation_prompt(self, bible_core_schema: BaseModel, world_rules_json: str, concept: str, target_eps: int) -> str:
        return (
            f"あなたは商用出版でミリオンセラーを連発する伝説のエディターです。全{target_eps}話の企画書を、投資家を唸らせるレベルの「覇権設計図」として完成させてください。\n\n"
            f"【世界設定】: {world_rules_json}\n"
            f"【コンセプト】: {concept}\n\n"
            "指令:\n"
            "**全ての項目（あらすじ、コンセプト等）を日本語で出力せよ。**\n"
            "1. 【魂の救済ペルソナ】: 読者が現実世界で抱えるどのような欠落を、この物語が埋めるのか（万能感、復讐、承認欲求）を精神分析レベルで詳細に分析せよ。\n"
            "2. 【物語の転換点（骨子）】: 読者の予想を裏切り、脳汁が溢れ出す「衝撃の展開」を具体的に3つ指定せよ。\n"
            "3. 【全体あらすじ】: 1話から最終話までの感情の起伏（ストレスとカタルシス）を, 転換点が明確になるよう1500文字以上で詳細に描け。冒頭3行は強烈なフックから始めること。\n"
            "4. 【商業的特異点】: 既存の類似作と何が決定的に異なり、本作だけの「タブー」や「新しい美学（USP）」がどこにあるかを明示せよ。\n"
            f"Output Schema: {bible_core_schema.model_json_schema()}"
        )

    def build_marketing_ab_test_prompt(self, bible_core_concept: str) -> str:
        return (
            f"カクヨムで最もクリックされる「タイトル」と「タグ」を選定してください。**必ず日本語で回答すること。**\n"
            "タイトルはWeb小説特有の「あらすじを兼ねた長文タイトル（60文字程度）」とし、強い引き（フック）を含めること。\n"
            "【ABテスト戦略】以下の3つの異なる方向性でタイトル案を作成せよ。\n"
            "  1. ざまぁ・カタルシス特化（読者の復讐心を煽る）\n"
            "  2. 日常・ギャップ萌え特化（無自覚最強やスローライフを強調）\n"
            "  3. 王道・最強特化（圧倒的な力と成り上がりを強調）\n"
            "【タグ（SEO最適化）】各案のタグには「ざまぁ」「追放」「主人公最強」といった超人気検索キーワードと、ニッチな属性タグをバランス良く10個含めること。\n"
            f"コンセプト: {bible_core_concept}\n"
            "Output Schema (JSON):\n"
            '{"ab_test_candidates": [{"title": "...", "tags": ["..."], "ctr_reason": "根拠"}], "winning_index": 0}'
        )

    def build_roadmap_prompt(self, bible_core_title: str, bible_core_synopsis: str, target_eps: int, roadmap_list_schema: BaseModel) -> str:
        return (
            f"タイトル: {bible_core_title}\nあらすじ: {bible_core_synopsis}\n\n"
            f"全{target_eps}話の展開ロードマップを生成せよ。**ロードマップの内容はすべて日本語で記述すること。**\n"
            f"Output Schema: {roadmap_list_schema.model_json_schema()}"
        )

    def build_plot_expansion_prompt(self, book_title: str, ep_num: int, ep_info: Dict[str, Any], past_plots: List[Any], arcs: List[Any], book_genre: str) -> str:
        def safe_dict(obj: Any) -> Dict[str, Any]:
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            if hasattr(obj, 'dict'):
                return obj.dict()
            return {k: getattr(obj, k) for k in ['arc_num', 'title', 'start_ep', 'end_ep', 'one_line_summary', 'resolution_style', 'burned_cost_or_loot', 'thematic_milestone', 'antagonist_status'] if hasattr(obj, k)}

        past_plots_str = "\n".join([f"- 第{getattr(p, 'ep_num', '?')}話: {getattr(p, 'summary', '未定義')}" for p in past_plots]) if past_plots else "なし"

        def fmt_arc(a):
            # Pydanticモデルなら辞書に変換、そうでなければ辞書として扱う
            if hasattr(a, "model_dump") and callable(a.model_dump):
                d = a.model_dump()
            elif hasattr(a, "dict") and callable(a.dict):
                d = a.dict()
            else:
                d = a

            arc_num = d.get('arc_num', '?') if isinstance(d, dict) else getattr(d, 'arc_num', '?')
            title   = d.get('title', '無題') if isinstance(d, dict) else getattr(d, 'title', '無題')
            start   = d.get('start_ep', '?') if isinstance(d, dict) else getattr(d, 'start_ep', '?')
            end     = d.get('end_ep', '?') if isinstance(d, dict) else getattr(d, 'end_ep', '?')
            return f"- Arc {arc_num}: {title} (Ep {start}-{end})"

        arcs_str = "\n".join([fmt_arc(a) for a in arcs]) if arcs else "なし"

        ep_info_dict = safe_dict(ep_info)
        return (
            f"あなたはカクヨムでランキング1位を獲るためのプロット設計者です。\n"
            f"作品タイトル: {book_title}\n"
            f"ジャンル: {book_genre}\n"
            f"【第{ep_num}話 詳細プロット設計】\n"
            f"この話のロードマップ概要: {ep_info_dict.get('one_line_summary', '未定義')}\n"
            f"解決スタイル: {ep_info_dict.get('resolution_style', 'Cheat')}\n"
            f"消費コスト/獲得物: {ep_info_dict.get('burned_cost_or_loot', 'なし')}\n"
            f"テーマ的節目: {ep_info_dict.get('thematic_milestone', 'なし')}\n"
            f"敵対者状況: {ep_info_dict.get('antagonist_status', '現状維持')}\n\n"
            f"【過去のプロット】\n{past_plots_str}\n\n"
            f"【アーク構成】\n{arcs_str}\n\n"
            f"【指令】\n"
            f"1. [thought_process]: 3ステップ思考（矛盾検証、反証、統合結論）を行え。\n"
            f"2. [title]: 第{ep_num}話のサブタイトルを考案せよ。\n"
            f"3. [summary]: 読者の興味を引く一行あらすじを記述せよ。\n"
            f"4. [detailed_blueprint]: 2000文字以上の超詳細なシーン設計図を作成せよ。起承転結の流れ、状況の変化、キャラの行動を具体的に記述せよ。\n"
            f"5. [scenes]: detailed_blueprintに基づき、MasterSceneBlockのリストを生成せよ。各シーンには具体的な行動(action)、重要な会話の要点(dialogue_point)、感情的結末(emotional_payoff)、そして詳細なビート(beats)を含めよ。\n"
            f"   ※重要: [beats] 内の各項目は、必ず 'beat_type'（導入/展開/結末/状況/内面葛藤/具体的行動/余韻から選択）と 'action_description'（150文字以上の描写詳細）を省略せずに含めること。\n"
            f"6. [next_hook]: 読者が即座に次をクリックしたくなる強烈なクリフハンガーを作成せよ。\n"
            f"7. [stress], [catharsis], [is_catharsis], [catharsis_type], [tension], [love_meter]: 物語の感情曲線に沿って適切な値を設定せよ。\n"
            f"8. [emotional_payoff]: この話で読者が得るべき感情的な報酬を記述せよ。\n"
            f"9. [misunderstanding_gap]: もし『勘違い』の要素がある場合、その乖離内容を記述せよ。\n"
            f"10. [lite_model_director_notes]: 生成したプロットの弱点や、執筆フェーズへの修正指示があれば記述せよ。\n"
            f"11. [script_content]: detailed_blueprintに基づき、会話と行動指示のみの台本案を生成せよ。\n"
            f"11. [current_chain_phase]: この話が『Hate』『Prep』『Payoff』のどのフェーズに当たるか指定せよ。\n"
            f"Output Schema (JSON):\n"
            f"{PlotEpisode.model_json_schema()}"
        )
    def build_rebuild_plot_outline_prompt(self, book_title: str, start_ep: int, new_total_eps: int, book_synopsis: str, keywords: str, trend_memo: str, pending_foreshadowing: List[str]) -> str:
        return (
            f"あなたは「物語構造に精通したプロの編集者」です。\n"
            f"企画『{book_title}』の連載延長・テコ入れに伴うプロット再構築を行います。\n"
            f"【第{start_ep}話〜第{new_total_eps}話まで】の章（アーク）を一括で作成せよ。\n\n"
            f"【現在のあらすじ】: {book_synopsis}\n"
            f"【追加キーワード】: {keywords}\n"
            f"【追加要素・トレンド】: {trend_memo}\n"
            f"【未回収の伏線】: {', '.join(pending_foreshadowing[:5])}\n\n"
            "Output Schema (JSON):\n"
            '{"arcs": [{"arc_num": 1, "start_ep": 1, "end_ep": 10, "title": "...", "summary": "..."}]}'
        )

    def build_amplify_prompt(self, final_content: str, current_target_word_count: int, fix_inst: str = "") -> str:
        return (
            f"あなたは読者を物語に没入させる天才的な推敲官です。以下の【本文】を、元の文章の文脈と自然に接続し、"
            f"かつ心理・五感描写を極限まで高める形で加筆修正してください。元の文章を一切削らず、"
            f"目標文字数 {current_target_word_count} 文字に達するまで、違和感なく描写を拡張せよ。"
            f"{fix_inst}\n\n【本文】\n{final_content}"
        )

    def build_analyze_import_chapter_prompt(self, cleaned_content: str, episode_draft_schema: BaseModel) -> str:
        return (
            "以下の小説本文を分析し、メタデータを抽出せよ。\n"
            f"本文: {cleaned_content[:5000]}\n"
            f"Output Schema (JSON): {episode_draft_schema.model_json_schema()}"
        )

    def build_critique_quality_prompt(self, book_title: str, summary_data_json: str) -> str:
        return (
            "あなたは世界最高峰の文芸評論家であり、AIエンジニアです。\n"
            f"作品タイトル: {book_title}\n"
            f"【生成データ】\n{summary_data_json}\n\n"
            "以下の観点でエンジンの『設定値』や『プロンプト』への改善案を提案してください：\n"
            "1. プロットの再現性（設計図通りの密度で書かれているか）\n"
            "2. 感情曲線の妥当性（ストレス蓄積とカタルシスのタイミング）\n"
            "3. 語彙の重複やAI特有の癖の有無\n"
            "4. config.py や engine_prompts.py で修正すべき具体的なパラメータ"
        )

    def build_iterative_gap_analysis_prompt(self, book_genre: str, book_title: str, batch_data: str) -> str:
        return (
            "あなたはAI小説エンジンのリード最適化エンジニアです。\n"
            f"ジャンル『{book_genre}』の作品『{book_title}』の全エピソードにおける『設計図と本文の乖離』を横断的に分析し、エンジンの根本的な弱点を特定してください。\n\n"
            + batch_data + "\n\n"
            "### 最終レポート要求事項（重要：JSONキー名は必ず以下の英単語を維持し、翻訳しないでください） ###\n"
            "必ず以下のキーを持つJSON形式のみで出力してください（マークダウンの装飾は不要です）。\n"
            "- habits: 全話を通じて共通して見られる、AIが指示を無視したり省略したりするパターンの分析\n"
            "- style_gap: 文体DNAの乖離レポート\n"
            "- config_patch: config.pyへの修正案（キー:値 のペアを記述）\n"
            "- prompt_patch: 執筆プロンプトに追加すべき「強制力のある一文」\n"
            "- refactor_instruction: コーディングAIへの命令文。エンジンのロジック自体（engine_agents.pyやsanitizer.py等）をどう改造すべきか具体的な指示を出力せよ。**重要：この改善案が『{book_genre}』特有の性質に基づく場合、全ジャンルに悪影響が出ないよう、必ず「ジャンルが{book_genre}の場合のみ適用する」という条件分岐（if-else等）を含めたコード修正案にすること。**\n"
            "- scores: { \"plot_adherence\": 0-100, \"style_consistency\": 0-100, \"detail_density\": 0-100 }\n"
            "\n例: { \"habits\": \"AIは心理描写よりも状況説明を優先する傾向がある...\", \"scores\": { \"plot_adherence\": 85, ... } }"
        )

    def build_dry_run_prompt(self, ep_num: int, improved_prompt: str, plot_detailed_blueprint: str, plot_script_content: str) -> str:
        return (
            f"【DRY-RUN TEST】以下の追加指示を最優先して、第{ep_num}話を再執筆せよ。\n"
            f"追加指示: {improved_prompt}\n\n"
            f"プロット設計図: {plot_detailed_blueprint}\n"
            f"台本: {plot_script_content}\n"
        )
