import os

config_path = "d:/claude2/config.py"

# Restore config.py to clean git state first
os.system(f"git checkout {config_path}")

with open(config_path, "rb") as f:
    raw_data = f.read()

# Normalize all line endings to LF
normalized_data = raw_data.replace(b"\r\n", b"\n")
content = normalized_data.decode("utf-8")

# 1. Replace TrendConfigManager properties
old_props = """    @property
    def tropes(self) -> List[str]:
        return self._config_data.get("tropes", [])

    @property
    def title_patterns(self) -> List[str]:
        return self._config_data.get("title_patterns", [])

    @property
    def forbidden_words_replacements(self) -> Dict[str, str]:
        return self._config_data.get("forbidden_words_replacements", {})

FORBIDDEN_WORD_REPLACEMENTS: Dict[str, str] = TrendConfigManager.get_instance().forbidden_words_replacements"""

old_props = old_props.replace("\r\n", "\n")

new_props = """    @property
    def tropes(self) -> List[str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.tropes is not None:
            return plugin.tropes
        return self._config_data.get("tropes", [])

    @property
    def title_patterns(self) -> List[str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.title_patterns is not None:
            return plugin.title_patterns
        return self._config_data.get("title_patterns", [])

    @property
    def forbidden_words_replacements(self) -> Dict[str, str]:
        from core.plugin_loader import PluginLoader
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.forbidden_words_replacements is not None:
            return plugin.forbidden_words_replacements
        return self._config_data.get("forbidden_words_replacements", {})"""

new_props = new_props.replace("\r\n", "\n")

if old_props in content:
    content = content.replace(old_props, new_props)
    print("TrendConfigManager properties replaced.")
else:
    print("TrendConfigManager properties NOT found.")

# 2. Locate VILLAIN_STRATEGIES block start and end
villain_start = content.find("VILLAIN_STRATEGIES: Dict[str, str] = {")
if villain_start == -1:
    print("VILLAIN_STRATEGIES block not found.")
else:
    onmyoji_idx = content.find('"style_onmyoji_master": {', villain_start)
    if onmyoji_idx == -1:
        print("style_onmyoji_master not found.")
    else:
        # Find closing brace of STYLE_DEFINITIONS
        # Let's search for "}\n}"
        end_brace = content.find("}\n}", onmyoji_idx)
        if end_brace == -1:
            print("Closing brace of STYLE_DEFINITIONS not found.")
        else:
            end_idx = end_brace + len("}\n}")
            block_to_replace = content[villain_start:end_idx]

            replacement = """# ==========================================
# 悪役・敵の行動指針（デフォルト・フォールバック）
# ==========================================
_DEFAULT_VILLAIN_STRATEGIES: Dict[str, str] = {
    "恋愛":    "【行動指針：婚約破棄と社会的抹殺】物理的暴力を控え、「権力を用いた理不尽な婚約破棄」「悪評の流布」「舞踏会での公開処刑」で主人公の社会的地位と愛を破壊せよ。",
    "ミステリー": "【行動指針：完全犯罪と知能犯】「証拠の隠滅」「偽の証言者の用意」「主人公を犯人に仕立て上げる罠」で知能的な妨害工作を行え。",
    "VR":     "【行動指針：炎上とBAN】「コメント欄へのbot攻撃」「捏造した切り抜き動画の拡散」「アカウント凍結警告」で配信者としての社会的死を狙え。",
    "ダンジョン": "【行動指針：ルールの悪用とMP枯渇】ダンジョンのギミックを書き換え、回復ポイントを消去し、システムそのものを敵に回す絶望を与えよ。",
    "default": "【行動指針：徹底的なプライドの破壊】単なる殺害を禁ずる。 1:『公衆の面前での冤罪と追放』 2:『婚約者や信頼する部下の目の前での無力化』 3:『積み上げてきた名誉の剥奪』。読者が「絶対に許せない」と思う理不尽さを最大化せよ。",
}

_DEFAULT_DEBUFF_PROFILES: Dict[str, str] = {
    "恋愛":    "『声の震え』『視線を合わせられない』『過去のトラウマのフラッシュバックによる過呼吸』など、精神的・関係性にヒビを入れる深刻な苦痛",
    "ミステリー": "『思考の混濁』『重要な手がかりの健忘』『幻覚による誤推理』など、論理的思考を阻害する深刻な苦痛",
    "VR":     "『通知音の幻聴』『ステータス画面のバグ』『現実の肉体の痙攣とのリンク』など、境界が曖昧になる苦痛",
    "ダンジョン": "『魔力回路の暴走による激痛』『平衡感覚の喪失』『ステータスの異常低下』など、生存に直結する苦痛",
    "default": "『思考にモヤがかかる』『視界がたまにブラックアウトする』『スキルが不発になる』などの深刻な苦痛",
}

_DEFAULT_CHARACTER_EXPANSION_THEMES: Dict[str, List[str]] = {
    "主人公": ["過去の挫折・不当な扱いのフラッシュバック", "独自の技術・武器・魔術へのフェティッシュな執着", "内なる矛盾や独白"],
    "ヒロイン": ["主人公への無自覚な独占欲や微細な嫉妬", "隠された出自や家柄に伴う重圧", "特定の香りや装飾品への愛着"],
    "ライバル": ["主人公への敗北感と屈辱の再燃", "武器や技の手入れに見る異常なまでのストイックさ", "高慢さの裏にある焦燥"],
    "悪役": ["歪んだ正義感や美学の独白", "他者の恐怖や苦痛を味わう生理的な反応", "過去に受けた傷跡の疼き"],
    "default": ["特定の癖（指を鳴らす、唇を噛む等）", "周囲の環境変化への過敏な反応", "道具や衣装の質感へのこだわり"],
}

_DEFAULT_ANTI_PATTERNS: Dict[str, List[str]] = {
    "common": [
        "主人公が都合よく助けられる（デウス・エクス・マキナ）",
        "敵が急に弱くなる、または理由なく改心する",
        "ヒロインが主人公のチート能力に驚くだけで物語に能動的に関わらない",
        "説明台詞が長く、状況を読者に語りかける（Show, Don't Tell違反）",
        "危機が簡単に解決され、緊張感が持続しない",
        "主人公が過去のトラウマを簡単に乗り越える",
        "物語の序盤で全ての謎が解明される",
        "読者の予想通りの展開が続く",
    ],
}

_DEFAULT_PLOT_STRUCTURES: Dict[str, Dict[str, Any]] = {
    "exile_rise": {
        "name":        "追放→成り上がり（王道ざまぁ）",
        "hook":        "不当な追放と屈辱",
        "mid_crisis":  "旧勢力の妨害と拮抗",
        "climax_type": "圧倒的逆転と断罪",
        "ending":      "社会的成功と完全な立場逆転",
        "key_tropes":  ["ざまぁ", "断罪", "成り上がり"],
    },
    "slow_life": {
        "name":        "スローライフ（ほのぼの飯テロ）",
        "hook":        "穏やかな日常の始まり",
        "mid_crisis":  "軽いトラブルとそれを料理で解決",
        "climax_type": "大きな発見と人間関係の深化",
        "ending":      "静かな充実感と日常への回帰",
        "key_tropes":  ["飯テロ", "のんびり最強", "田舎暮らし"],
    },
    "reincarnation_cheat": {
        "name":        "転生チート（ステータス無双）",
        "hook":        "転生と隠されたステータス覚醒",
        "mid_crisis":  "隠された真の力を発揮する場面",
        "climax_type": "真の力の完全解放と認知",
        "ending":      "世界に認められた新たな立場の確立",
        "key_tropes":  ["無自覚無双", "ステータス偽装", "スキル強奪"],
    },
    "death_loop": {
        "name":        "死に戻り（絶望と執念）",
        "hook":        "圧倒的な理不尽な死",
        "mid_crisis":  "繰り返しの中での情報収集と成長",
        "climax_type": "最後の正解ルートの発見",
        "ending":      "ループからの完全な脱出と救済",
        "key_tropes":  ["ループ", "絶望からの逆転", "知識の蓄積"],
    },
}

RULE_SET_A_RULES = (
    "[CORE_MANIFESTO: ENT_MUZOU]\\n"
    "- [STRICT_SHOW]: No meta-emotions. Translate to physical kinesics.\\n"
    "- [NO_SIMILE]: Ban 'like/as'. Use direct metaphors only.\\n"
    "- [ACTION_CHASE]: Keep (Dialogue -> Action -> Dialogue) ping-pong rhythm.\\n"
    "- [NO_EXPLAIN]: Zero mechanics talk. Focus on sensory 'results'.\\n"
    "- [STRESS_GEN]: Villain acts with 'hypocritical kindness'.\\n"
    "- [STRONG_CALM]: MC is abnormally indifferent to pain/crisis.\\n"
    "- [STACCATO]: Avg sentence <40 chars. Frequent nouns endings.\\n"
    "- [GAP_EFFECT]: Contrast gore with mundane daily details.\\n"
    "- [CLIFFHANGER]: Ending MUST trigger 'Crisis/Truth/Cost' (No peace)."
)
RULE_SET_A_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる, "
    "『冷や汗』『瞳孔が開く』『絶望』『顔が歪む』『嘔吐』などの大仰で劇的なシリアスワード"
)

RULE_SET_B_RULES = (
    "[CORE_MANIFESTO: DARK_HARD]\\n"
    "- [SUBJECTIVE_ONLY]: No author meta-commentary. Focus on MC's limited view.\\n"
    "- [BODILY_LANG]: Translate anger/fear to visceral pain/coldness.\\n"
    "- [SURGICAL_VIOLENCE]: Describe combat as chronological anatomical events.\\n"
    "- [FETISH_DETAIL]: Show emotion via interaction with environment/tools.\\n"
    "- [IRREVERSIBLE]: Loss must be permanent (severed/broken).\\n"
    "- [SILENCE_BUFFER]: Use 'dead silence' before explosive actions.\\n"
    "- [SMOOTH_TRANS]: No time-skips. Use light/sound for transitions.\\n"
    "- [CLIFFHANGER]: End with a betrayal of peace/sudden despair."
)
RULE_SET_B_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 目を見開く, 瞳孔が収縮する, 胃の腑が冷える, "
    "記憶喪失, 思い出の消失, 名前を忘れる, 『笑い』『コミカル』等の軽薄なワードやギャグ表現"
)

RULE_SET_C_RULES = (
    "[CORE_MANIFESTO: CHAR_PSYCHO]\\n"
    "- [SHOW_EGO]: Show personality via erratic behavior, not adjectives.\\n"
    "- [COG_GAP]: Drive plot via 'rational MC vs delusional observers'.\\n"
    "- [HEAVY_LOVE]: Favor 'obsession/dependency' over simple kindness.\\n"
    "- [REACTION_PORN]: Lavishly describe NPCs' shock/horror at MC.\\n"
    "- [SENSORY_FETISH]: Mandatory scent/temp/touch in every interaction.\\n"
    "- [HUMILIATION]: Villain must attack MC's dignity publicly.\\n"
    "- [CLIFFHANGER]: End with 'betrayal of trust' or 'fatal secret'."
)
RULE_SET_C_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる"
)

RULE_SET_D_RULES = (
    "[CORE_MANIFESTO: SLOW_LIFE]\\n"
    "- [POSITIVE_SENSORY]: Maximize 'gloss of food', 'cooking sounds', 'warmth'.\\n"
    "- [NO_STRESS]: Neutralize malice. Use 'well, whatever' attitude.\\n"
    "- [DETAIL_80]: 80% focus on daily chores/tools/cooking processes.\\n"
    "- [NATURAL_OP]: MC is comically indifferent to their own OP results.\\n"
    "- [LIGHT_INTERNAL]: Allow direct internal monologue for humor/pacing.\\n"
    "- [SOFT_HOOK]: End with 'new discovery' or 'expected guest'."
)
RULE_SET_D_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる, "
    "『冷や汗』『絶望』などの大仰で劇的なシリアスワード"
)

_DEFAULT_STYLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "style_web_standard": {
        "name":           "なろう・カクヨム標準（テンポ重視）",
        "instruction":    "【指針】短文と改行を多用し、スマホでの読みやすさを最優先せよ。主人公への称賛とチート能力の結果を淡々と、かつ爽快に描け。1段落は最大2文まで。",
        "dialogue_ratio": "60%",
        "syntax_rhythm":  "1文20文字以内、体言止め多用。感嘆符の後は必ず全角スペース。",
        "metaphor_dna":   "光、速度、ゲーム的UI効果音。「紙切れのように」等、敵の脆さを強調する比喩。",
        "noise_dna":      "「ま、いっか」という思考放棄。頬を掻く、ため息。周囲の驚嘆に対する無自覚なスルー。",
        "golden_rules":   RULE_SET_A_RULES,
        "negative_prompt": RULE_SET_A_NEG,
        "is_light":        True,
    },
    "style_serious_fantasy": {
        "name":           "ハイファンタジー（無職転生風）",
        "instruction":    "【指針】回想的かつ内省的なトーンで記述せよ。五感を通じた生活感を重視し、弱さを隠さない客観的な心理描写を行え。",
        "dialogue_ratio": "20%",
        "syntax_rhythm":  "1文40文字前後、重厚な接続詞。心情の直接描写禁止（風景に仮託）。",
        "metaphor_dna":   "泥、鉄の錆、血の匂い、冷たい雨。感情を「温度」や「重力」で表現。",
        "noise_dna":      "前世のトラウマによるフラッシュバック。古傷の疼き、泥を握りしめる感触。",
        "golden_rules":   RULE_SET_B_RULES,
        "negative_prompt": RULE_SET_B_NEG,
        "is_light":        False,
    },
    "style_psychological_loop": {
        "name":           "死に戻り・絶望（リゼロ風）",
        "instruction":    "【指針】呼吸音や絶叫を交え、切迫した心理を畳み掛けろ。自己嫌悪と他者への執着を、粘着質に繰り返せ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "短い単語の3連続反復（熱い熱い熱い）。倒置法による切迫感の演出。",
        "metaphor_dna":   "臓腑の冷たさ、吐瀉物の酸味。世界が「歪む」「ひび割れる」表現。",
        "noise_dna":      "過呼吸、歯の根が合わない震え。幻聴、眼球の痙攣。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_C_NEG,
    },
    "style_chat_log": {
        "name":           "ダンジョン配信（掲示板・コメント風）",
        "instruction":    "【指針】地の文に加え、配信コメントや掲示板のレスを挿入せよ。ネットスラングを多用し、ライブ感を演出せよ。",
        "dialogue_ratio": "70%",
        "syntax_rhythm":  "「草」「ｗ」などのネットスラング。レス番、タイムスタンプの羅列。",
        "metaphor_dna":   "画面の明滅、タイピングの打鍵音。「バグ」「チート」等のメタ語彙。",
        "noise_dna":      "誤字と訂正、文脈を無視した煽り合い。「これってマ？」等の現実逃避。",
        "golden_rules":   RULE_SET_A_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_villainess_elegant": {
        "name":           "悪役令嬢（優雅・皮肉）",
        "instruction":    "【指針】優雅な敬語（お嬢様言葉）で毒を吐け。ドレスや宝石の美しさを描写しつつ、高度な皮肉の応酬を行え。",
        "dialogue_ratio": "50%",
        "syntax_rhythm":  "「〜ですわ」「〜こと」等、優雅な長文。段落頭に優雅な動作のト書きを強制。",
        "metaphor_dna":   "紅茶の香り、絹の衣擦れ。相手を「路傍の石」と表現。",
        "noise_dna":      "扇で口元を隠す、ドレスの皺を伸ばす。内心の「イラッ」を笑顔で隠す筋肉の引き攣り。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_C_NEG,
    },
    "style_military_rational": {
        "name":           "戦記・合理的（幼女戦記風）",
        "instruction":    "【指針】感情を排した報告書的な文体を維持せよ。硬質な語彙を用い、徹底的な合理主義を貫け。",
        "dialogue_ratio": "15%",
        "syntax_rhythm":  "「故に」「したがって」等、論理的接続詞。主観的形容詞（悲しい等）の完全排除。",
        "metaphor_dna":   "硝煙、機械の駆動音、冷たい金属。損耗率、確率の数値化。",
        "noise_dna":      "眼鏡を押し上げる、軍服の襟を正す。無能な味方に対する冷たい舌打ち。",
        "golden_rules":   RULE_SET_B_RULES,
        "negative_prompt": RULE_SET_B_NEG,
    },
    "style_comedy_speed": {
        "name":           "高速コメディ（このすば風）",
        "instruction":    "【指針】ボケとツッコミの応酬で構成せよ。地の文は動作のみに留め、テンポを極限まで加速させよ。",
        "dialogue_ratio": "80%",
        "syntax_rhythm":  "地の文は最大2文。「ボケ→ツッコミ→被せ」の3拍子。擬音語の多用。",
        "metaphor_dna":   "滑稽な物理演算。「まるでダメな〇〇」というパロディ比喩。",
        "noise_dna":      "声の裏返り、白目を剥く、土下座の速度。クズな本音の即時漏洩。",
        "golden_rules":   RULE_SET_A_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_dark_hero": {
        "name":           "ダークヒーロー（ありふれ風）",
        "instruction":    "【指針】敵には容赦ない断定的な暴力性を、身内には甘いデレを見せろ。厨二病的なカッコよさを肯定的に描け。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "断定（〜だ、〜する）と命令形のみ。疑問符の排除（迷いのなさ）。",
        "metaphor_dna":   "真紅の光、圧倒的な質量による圧殺。敵を「肉塊」「塵」と認識する視点。",
        "noise_dna":      "冷たい嘲笑、首の骨を鳴らす。身内への過保護なスキンシップ。",
        "golden_rules":   RULE_SET_A_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_overlord": {
        "name":           "勘違い・魔王（オバロ風）",
        "instruction":    "【指針】絶対支配者としての外面と、小心者の内面のギャップを描け。配下の過剰な崇拝と残酷な蹂躙描写を重厚に記述せよ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "【外】威厳ある重厚な文体 ⇔ 【内】平易で焦った文体。句読点で「間」を意図的に作る。",
        "metaphor_dna":   "圧倒的な死のオーラ。配下からの視線を「刺さるような忠誠心」と表現。",
        "noise_dna":      "アドリブ発言の直後の「（やべっ）」という胃痛。威厳を保つための過剰な咳払い。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_C_NEG,
    },
    "style_bookworm_daily": {
        "name":           "ビブリオ・日常（本好き風）",
        "instruction":    "【指針】生活の細部や作業工程を丁寧に描写せよ。周囲との温かい交流と、目的への異常な執着を対比させよ。",
        "dialogue_ratio": "50%",
        "syntax_rhythm":  "作業工程の執拗な箇条書き的描写。フェティッシュなまでの素材描写。",
        "metaphor_dna":   "インクの匂い、羊皮紙のざらつき。本を「黄金」とする比喩。",
        "noise_dna":      "本を見ると周囲の音が聞こえなくなる。活字中毒による禁断症状の震え。",
        "golden_rules":   RULE_SET_D_RULES,
        "negative_prompt": RULE_SET_D_NEG,
    },
    "style_light_fun": {
        "name":           "ライト・エンタメ（爽快・軽快）",
        "instruction":    "【指針】コメディタッチで明るいトーンを維持せよ。深刻な状況でも主人公の楽観的な視点や周囲の滑稽な反応を挟み、読者が気楽に楽しめるようにせよ。比喩に現代的なパロディや軽妙な例えを混ぜよ。",
        "dialogue_ratio": "60%",
        "syntax_rhythm":  "1文30文字以内。三点リーダーや感嘆符を適度に使い、リズムを弾ませる。テンポの良い掛け合いを重視。",
        "metaphor_dna":   "「秒で終わる」「まるでゲーム of バグのような」といった現代的・デジタルな比喩。明るい色彩の比喩。",
        "noise_dna":      "「まあ、なんとかなるだろう」という極度のポジティブ思考。お腹が鳴る、あくび。コメディ的なズッコケ描写。",
        "golden_rules":   RULE_SET_D_RULES,
        "negative_prompt": RULE_SET_B_NEG,
    },
    "style_iron_wall": {
        "name":           "鉄壁・重厚（タンク無双）",
        "instruction":    "【指針】金属の重みと衝撃、そして『動かざる山』のような不動性を強調せよ。敵の攻撃が虚しく弾ける音や、盾の裏側で感じる振動を執拗に描け。",
        "dialogue_ratio": "30%",
        "syntax_rhythm":  "どっしりとした長文。倒置法を使い、攻撃を『受け止める』余韻を作れ。擬音語は重低音系（ゴォォ、ドンッ）に固定。",
        "metaphor_dna":   "鋼鉄、岩盤、城壁。敵を「羽虫」や「小波」とする比喩。",
        "noise_dna":      "盾を叩く指の感触。鎧の中の汗、重い呼吸。どれだけ叩かれても揺るがない精神的静寂。",
        "golden_rules":   RULE_SET_B_RULES,
        "negative_prompt": RULE_SET_D_NEG,
    },
    "style_evolution": {
        "name":           "野生・進化（弱肉強食）",
        "instruction":    "【指針】生理的な『飢え』と、肉体が作り変わる異質な感覚を強調せよ。捕食の生々しさと、能力を奪う瞬間の快楽を動物的な文体で記述せよ。",
        "dialogue_ratio": "20%",
        "syntax_rhythm":  "短文の連打。動詞を優先。進化の瞬間はカタカナを交えて異質さを演出。",
        "metaphor_dna":   "胃袋、牙、脈動する肉。敵を「餌」や「素材」として認識する視点。",
        "noise_dna":      "喉が鳴る音、骨の軋み、皮膚の下で何かが蠢く感覚。理性を飲み込む本能の咆哮。",
        "golden_rules":   RULE_SET_A_RULES,
        "negative_prompt": RULE_SET_B_NEG,
    },
    "style_forbidden_library": {
        "name":           "全知・神秘（禁書司書）",
        "instruction":    "【指針】静謐で知的なトーン。ページを捲る音やインクの匂いを五感の軸とし、世界の裏側を見透かすような超然とした視点を維持せよ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "理路整然とした長文。難読漢字を効果的に使い、古文書のような質感を出す。",
        "metaphor_dna":   "紙の海、文字の鎖、歴史の栞。世界を「一冊の本」として読み解く比喩。",
        "noise_dna":      "眼鏡を直す指、紙で指を切る微かな痛み。文字が目に吸い込まれる感覚。",
        "golden_rules":   RULE_SET_D_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_high_luck_gambler": {
        "name":           "心理・狂気（豪運ギャンブラー）",
        "instruction":    "【指針】極限の緊張状態における心拍、発汗、瞳孔の変化を執拗に描け。確率を支配する快感と、破滅の瀬戸際での狂気をスピード感ある文体で記述せよ。",
        "dialogue_ratio": "60%",
        "syntax_rhythm":  "テンポの速い短いやり取り。思考の加速を、句読点を極限まで削った独白で表現。",
        "metaphor_dna":   "コインの回転、ダイスの目、天秤。人生を「チップ」として賭ける比喩。",
        "noise_dna":      "指先の震え、乾いた喉、カードを捲る爪の音。脳裏で鳴り響く歓喜のファンファーレ。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_D_NEG,
    },
    "style_melody_mage": {
        "name":           "詩的・旋律（音楽魔法）",
        "instruction":    "【指針】聴覚情報を最優先し、文章自体がリズムを刻むように記述せよ。情景描写を歌詞のように詩的に表現し、音が世界を書き換える様子を描け。",
        "dialogue_ratio": "50%",
        "syntax_rhythm":  "七五調や反復を意識した流麗な文体。擬音語ではなく楽器や和音の名称を比喩に使う。",
        "metaphor_dna":   "共鳴、不協和音、残響。感情を「音色」や「旋律」で表現。",
        "noise_dna":      "ハミング、指で刻むリズム。静寂の中に響く一音の波紋。",
        "golden_rules":   RULE_SET_D_RULES,
        "negative_prompt": RULE_SET_B_NEG,
    },
    "style_true_ancestor": {
        "name":           "優雅・君臨（吸血鬼真祖）",
        "instruction":    "【指針】冷徹な美しさと圧倒的な威圧感。月の光や影の濃淡を強調し、他者を跪かせる真祖としての矜持を気高く記述せよ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "ゆったりとした優雅な文体。命令形を静かに使い、絶対的な権威を演出。",
        "metaphor_dna":   "深紅の瞳、闇の眷属、夜の支配。人間を「家畜」や「器」とする冷淡な比喩。",
        "noise_dna":      "赤い液体の揺らぎ、爪が触れる冷たいガラスの音。月を仰ぐ仕草の優雅さ。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_relic_repairer": {
        "name":           "職人・緻密（遺物修理屋）",
        "instruction":    "【指針】素材の質感、機構の噛み合わせ、磨耗の具合をミクロン単位の解像度で描写せよ。失われた技術を蘇らせる工程を、偏愛的に細かく記述せよ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "箇条書きに近い緻密な観察。動作の一つ一つを丁寧に分割して描写。",
        "metaphor_dna":   "歯車、ゼンマイ、油の匂い。世界を「壊れた精密機械」とする比喩。",
        "noise_dna":      "金属が擦れ合う音、火花。道具が指の延長になる一体感。",
        "golden_rules":   RULE_SET_D_RULES,
        "negative_prompt": RULE_SET_C_NEG,
    },
    "style_cursed_sword": {
        "name":           "鋭利・孤独（呪いの剣聖）",
        "instruction":    "【指針】削ぎ落とされた、刃のように鋭い文体。痛みと血の匂い、そして一撃にすべてを賭ける剣士の孤独と覚悟を冷たく記述せよ。",
        "dialogue_ratio": "15%",
        "syntax_rhythm":  "極限まで削られた短文。体言止めと断定の多用。呼吸さえも刃の一部とするような緊張感。",
        "metaphor_dna":   "研ぎ澄まされた刃、一閃、氷。自分を「鞘のない刀」とする比喩。",
        "noise_dna":      "血を払う音、鞘に収まる金属音。呪いが肉体を蝕む微かな疼き。",
        "golden_rules":   RULE_SET_B_RULES,
        "negative_prompt": RULE_SET_D_NEG,
    },
    "style_shadow_ruler": {
        "name":           "冷徹・策略（影の支配者）",
        "instruction":    "【指針】観察者としての冷徹な視点。表舞台の茶番を見下ろし、糸を引く黒幕としての愉悦を淡々と、しかし確実に記述せよ。",
        "dialogue_ratio": "40%",
        "syntax_rhythm":  "含みのある複文。相手の反応を予測し、誘導するような知的なリズム。",
        "metaphor_dna":   "蜘蛛の巣、盤上の駒、舞台袖。世界を「巨大なチェス盤」として読み解く比喩。",
        "noise_dna":      "チェスの駒を動かす音、影の中に溶け込む感覚。他人の愚かさに対する小さな溜息。",
        "golden_rules":   RULE_SET_C_RULES,
        "negative_prompt": RULE_SET_A_NEG,
    },
    "style_onmyoji_master": {
        "name":           "和風・律儀（最強陰陽師）",
        "instruction":    "【指針】呪歌や真言を交えた律儀で和風な文体。静かな所作の中に爆発的な呪力を秘め、陰陽の理で敵を滅ぼす様を端正に記述せよ。",
        "dialogue_ratio": "50%",
        "syntax_rhythm":  "格式高い言葉遣い。呪文の詠唱は改行を使い、空間を支配する演出を。",
        "metaphor_dna":   "五行（木火土金水）、式神、紙吹雪。穢れを「塵」として掃き清める比喩。",
        "noise_dna":      "印を結ぶ指の動き、狩衣の衣擦れ。呪符が燃える瞬間の微かな匂い。",
        "golden_rules":   RULE_SET_B_RULES,
        "negative_prompt": RULE_SET_D_NEG,
    },
}

# Dynamic Proxy getattr support
def __getattr__(name: str) -> Any:
    from core.plugin_loader import PluginLoader

    if name == "VILLAIN_STRATEGIES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.villain_strategies is not None:
            return plugin.villain_strategies
        return _DEFAULT_VILLAIN_STRATEGIES

    if name == "DEBUFF_PROFILES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.debuff_profiles is not None:
            return plugin.debuff_profiles
        return _DEFAULT_DEBUFF_PROFILES

    if name == "CHARACTER_EXPANSION_THEMES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.character_expansion_themes is not None:
            return plugin.character_expansion_themes
        return _DEFAULT_CHARACTER_EXPANSION_THEMES

    if name == "ANTI_PATTERNS":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.anti_patterns is not None:
            return plugin.anti_patterns
        return _DEFAULT_ANTI_PATTERNS

    if name == "PLOT_STRUCTURES":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.plot_structures is not None:
            return {k: v.model_dump() for k, v in plugin.plot_structures.items()}
        return _DEFAULT_PLOT_STRUCTURES

    if name == "STYLE_DEFINITIONS":
        plugin = PluginLoader.get_instance().get_active_plugin()
        if plugin.style_definitions is not None:
            return {k: v.model_dump() for k, v in plugin.style_definitions.items()}
        return _DEFAULT_STYLE_DEFINITIONS

    if name == "FORBIDDEN_WORD_REPLACEMENTS":
        return TrendConfigManager.get_instance().forbidden_words_replacements

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
"""

            replacement = replacement.replace("\r\n", "\n")

            if block_to_replace in content:
                content = content.replace(block_to_replace, replacement)
                print("VILLAIN_STRATEGIES block replaced successfully.")
            else:
                print("VILLAIN_STRATEGIES block NOT found.")

# Write back as UTF-8
with open(config_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Config.py refactored and written successfully.")

