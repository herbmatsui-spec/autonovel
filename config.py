"""
config.py - 覇権エンジン設定・定数モジュール
全ての定数・スタイル定義・アーキタイプ・設定クラスを集約。
ここを変えるだけで作品の方向性が変わる「作家の意志」ファイル。
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# ==========================================
# ロガー
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# モデル設定
# ==========================================
MODEL_PLANNING        = "gemini-3.1-flash-lite-preview"
MODEL_PLOT_EXPANSION  = "gemma-4-31b-it" 
MODEL_WRITING         = "gemini-3.1-flash-lite-preview" # Keep this as is, only change MODEL_PLOT_EXPANSION
MODEL_CLIMAX          = "gemini-3.1-flash-lite-preview"
MODEL_STABLE_FALLBACK = "gemma-4-31b-it" # 503エラー時の緊急回避用モデルエラー時の緊急回避用モデル

# ==========================================
# ファイルパス
# ==========================================
BASE_DIR = Path(__file__).parent.absolute()
DB_FILE  = "kaku_hegemony_v2.db"

# ==========================================
# API制御定数
# ==========================================
MAX_PROMPT_CHARS        = 1_000_000
CONTENT_SEPARATOR       = "### NOVEL CONTENT ###"
DEFAULT_GOLDEN_PEAKS    = [5, 10, 15, 25, 50]

# カクヨム1位獲得のための「極限ヘイト・爆速カタルシス」調整
STRESS_CATHARSIS_THRESHOLD = 85   # 爆発力を高めるため、極限までヘイトを溜める
STRESS_FILLER_THRESHOLD    = 35   # 読者が飽きる前にヘイト（溜め）を補充
STRESS_CLIMAX_BONUS        = 50   # カタルシス回でのストレス解放量
STRESS_HATE_GAIN_BASE      = 2    # Hate フェーズでの標準ストレス積算量

# 語彙ランダマイズ・強制置換設定
FORBIDDEN_WORD_REPLACEMENTS: Dict[str, str] = {
    "蹂躙": "「蹂躙」という言葉を直接使わず、代わりにそれを想起させる具体的な破壊現象（例：踏み潰される土、引き裂かれる旗、崩落する壁、悲鳴を上げる鉄、砕け散る瓦礫）を3話以上描写せよ。",
    "驚愕": "「驚愕」や「驚きを隠せない」といった抽象語を使わず、喉の鳴る音、震える指先、呼吸の停止、産毛の逆立ち等の生理現象で描写せよ。",
    "絶望": "「絶望」を使わず、色彩を失う視界、胃の腑に沈む鉛の重さ、肺を圧迫する空気、凍りつく思考等の物理的感覚で描写せよ。",
    "静寂": "「静寂」を使わず、風の音だけが響く感覚、自分の心臓の音だけが耳元でうるさいほどの無音、肌にまとわりつく空気の重さ等で描写せよ。",
    "圧倒": "「圧倒的」「圧倒された」を使わず、相手との体格差、魔圧による重圧、逃げ場のない包囲感、あるいは「蛇に睨まれた蛙」のような身体的硬直を描写せよ。",
    "歓喜": "「歓喜」「喜びに震える」を使わず、顔の筋肉が勝手に緩む感覚、心臓が跳ねるような鼓動、視界が急激に明るく開ける主観的変化で描写せよ。",
}

# --- Hegemony 3.1: 物語の「質感」を強制的にズラすためのアセット ---
NARRATIVE_PROPS: List[str] = [
    "ひび割れた古い手鏡（真実を歪める象徴）", "不機嫌そうな片目の黒猫", "見たことのない青い野生の果実",
    "錆びついたゼンマイ仕掛けの鳥", "誰かが忘れていった刺繍入りのハンカチ", "不自然に冷たい風が吹き抜ける隙間",
    "香草が焦げるような、妙に癖になる匂い", "遠くで聞こえる、リズムの狂った鐘の音", "琥珀の中に閉じ込められた得体の知れない虫"
]

DAILY_MICRO_HOOKS: List[str] = [
    "靴の紐が何度も解けることへの苛立ち", "料理の塩加減が完璧だったことへの小さな恐怖",
    "鏡に映った自分の顔が、一瞬だけ他人のものに見える錯覚", "お気に入りの道具が、自分の意志を持っているかのように手に馴染む瞬間",
    "通り過ぎた見知らぬ他人が、自分と同じ鼻歌を歌っていた不気味さ"
]

STYLE_REFINEMENT_DIRECTIONS: Dict[str, str] = {
    "light": (
        "【高解像度化指針：軽快・明瞭】読者がページを捲る手を止めないテンポの良いリズムを維持しつつ、キャラクターの『皮肉』や『本音』の独白を増やせ。"
        "比喩は短く、視覚的なキレを重視。読者がページを捲る手を止めないテンポの良いリズムを刻め。"
        "重苦しい生理現象を、軽妙な独白やコミカルな仕草に置換せよ。"
    ),
    "heavy": (
        "【高解像度化指針：重厚・執念】既存の文章を一切削るな。五感を飽和させ、"
        "読者の皮膚に熱や冷気が伝わるまで執拗に書き込め。特に『痛み』や『魔力の質感』に対する独自の比喩を1話に3つは必ず挿入せよ。"
        "感情は風景や道具の質感に徹底的に仮託せよ。"
    )
}

# 物語のマンネリを防ぐためのバリエーション定義
ROUTINE_VARIATIONS: List[str] = [
    "武器や道具の過剰な手入れ（フェティシズム）",
    "市場での買い出しと、現地住民との奇妙な交流",
    "限界を超えた自己修練と、肉体の軋み",
    "過去の断片的な記憶の整理（パズルを解くような感覚）",
    "食事の味に対する、異常なまでのこだわりと分析",
]

TRAGEDY_VARIATIONS: List[str] = [
    "物理的消去ではなく、信頼していた者からの『自発的な裏切り』",
    "守りたかった名誉や尊厳の『公衆の面前での剥奪』",
    "命ではなく、代々受け継がれた『唯一無二の遺産の破壊』",
    "肉体的な死ではなく、正気を失うほどの『精神的な汚染』",
]


# APIコスト設定 (Gemini 2.0 Flash 有料ティア基準: USD/token)
COST_INPUT_FLASH  = 0.00000025   # $0.25  / 1M tokens
COST_OUTPUT_FLASH = 0.0000015    # $1.50  / 1M tokens (思考トークン含む)
COST_INPUT_PRO    = 0.00000125   # $1.25  / 1M tokens (<128k)
COST_OUTPUT_PRO   = 0.00000375   # $3.75  / 1M tokens (<128k)

COOLDOWN_BASE_DEFAULT   = 0.0
COOLDOWN_MIN_DEFAULT    = 0.0
COOLDOWN_MAX_DEFAULT    = 90.0
SAFE_APPEND_MODE_OPTIONS = ["auto", "warn_only", "error_on_overflow"]
SAFE_APPEND_MODE_DEFAULT = "auto"

# ==========================================
# チートスケール・代償定義（物語の軸）
# ==========================================
CHEAT_DESCRIPTIONS: Dict[int, str] = {
    0: "【無チート】常人以下。努力しても報われない。無双は夢のまた夢。",
    1: "【微優位】常人より少し運が良い、または努力が報われやすい程度。圧倒的な力はなく、泥臭い工夫が必須。",
    2: "【秀才・天才】人間や魔族の限界内のトップクラス。多勢に無勢では負けるし、油断すれば死ぬ現実的な強さ。",
    3: "【英雄・公認チート】一対多でも圧倒できる、明確な強者。一般的な騎士や魔術師では太刀打ちできないレベル。",
    4: "【理外の力・法則破壊】世界の物理法則を一部無視する（魔力無限、絶対回避など）。",
    5: "【概念・神格】絶対的な勝利が約束された存在。存在自体が世界のバグ。",
}

COST_DESCRIPTIONS: Dict[int, str] = {
    -1: "【無限】代償は一切存在しない。",
    0:  "【無償】代償は一切存在しない。使い放題の万能感。",
    1:  "【日常的負担】空腹感、軽い疲れ。休憩すれば即座に回復。",
    2:  "【一時的損耗】一晩の寝込み、高価な魔石の消費。",
    3:  "【等価交換・苦痛】激痛、寿命の微減。使用に明確なリスク。",
    4:  "【永続的欠落・重傷】身体部位の欠損。不可逆なダメージ。",
    5:  "【破滅・呪い】自身の存在抹消、愛する者の死。使用＝物語の終焉。",
}

# ==========================================
# 悪役・敵の行動指針（ジャンル別）
# ==========================================
VILLAIN_STRATEGIES: Dict[str, str] = {
    "恋愛":    "【行動指針：婚約破棄と社会的抹殺】物理的暴力を控え、「権力を用いた理不尽な婚約破棄」「悪評の流布」「舞踏会での公開処刑」で主人公の社会的地位と愛を破壊せよ。",
    "ミステリー": "【行動指針：完全犯罪と知能犯】「証拠の隠滅」「偽の証言者の用意」「主人公を犯人に仕立て上げる罠」で知能的な妨害工作を行え。",
    "VR":     "【行動指針：炎上とBAN】「コメント欄へのbot攻撃」「捏造した切り抜き動画の拡散」「アカウント凍結警告」で配信者としての社会的死を狙え。",
    "ダンジョン": "【行動指針：ルールの悪用とMP枯渇】ダンジョンのギミックを書き換え、回復ポイントを消去し、システムそのものを敵に回す絶望を与えよ。",
    "default": "【行動指針：徹底的なプライドの破壊】単なる殺害を禁ずる。 1:『公衆の面前での冤罪と追放』 2:『婚約者や信頼する部下の目の前での無力化』 3:『積み上げてきた名誉の剥奪』。読者が「絶対に許せない」と思う理不尽さを最大化せよ。",
}

DEBUFF_PROFILES: Dict[str, str] = {
    "恋愛":    "『声の震え』『視線を合わせられない』『過去のトラウマのフラッシュバックによる過呼吸』など、精神的・関係性にヒビを入れる深刻な苦痛",
    "ミステリー": "『思考の混濁』『重要な手がかりの健忘』『幻覚による誤推理』など、論理的思考を阻害する深刻な苦痛",
    "VR":     "『通知音の幻聴』『ステータス画面のバグ』『現実の肉体の痙攣とのリンク』など、境界が曖昧になる苦痛",
    "ダンジョン": "『魔力回路の暴走による激痛』『平衡感覚の喪失』『ステータスの異常低下』など、生存に直結する苦痛",
    "default": "『思考にモヤがかかる』『視界がたまにブラックアウトする』『スキルが不発になる』などの深刻な苦痛",
}

# ==========================================
# キャラクター別・描写拡張テーマ（アンプリファイ用）
# ==========================================
CHARACTER_EXPANSION_THEMES: Dict[str, List[str]] = {
    "主人公": ["過去の挫折・不当な扱いのフラッシュバック", "独自の技術・武器・魔術へのフェティッシュな執着", "内なる矛盾や独白"],
    "ヒロイン": ["主人公への無自覚な独占欲や微細な嫉妬", "隠された出自や家柄に伴う重圧", "特定の香りや装飾品への愛着"],
    "ライバル": ["主人公への敗北感と屈辱の再燃", "武器や技の手入れに見る異常なまでのストイックさ", "高慢さの裏にある焦燥"],
    "悪役": ["歪んだ正義感や美学の独白", "他者の恐怖や苦痛を味わう生理的な反応", "過去に受けた傷跡の疼き"],
    "default": ["特定の癖（指を鳴らす、唇を噛む等）", "周囲の環境変化への過敏な反応", "道具や衣装の質感へのこだわり"],
}

# ==========================================
# アンチパターンDB（絶対に使ってはいけない展開）
# ==========================================
ANTI_PATTERNS: Dict[str, List[str]] = {
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

# ==========================================
# プロット構造テンプレート
# ==========================================
PLOT_STRUCTURES: Dict[str, Dict[str, Any]] = {
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

# ==========================================
# ゴールデンルールセット（文体DNA）
# ==========================================
RULE_SET_A_RULES = (
    "[CORE_MANIFESTO: ENT_MUZOU]\n"
    "- [STRICT_SHOW]: No meta-emotions. Translate to physical kinesics.\n"
    "- [NO_SIMILE]: Ban 'like/as'. Use direct metaphors only.\n"
    "- [ACTION_CHASE]: Keep (Dialogue -> Action -> Dialogue) ping-pong rhythm.\n"
    "- [NO_EXPLAIN]: Zero mechanics talk. Focus on sensory 'results'.\n"
    "- [STRESS_GEN]: Villain acts with 'hypocritical kindness'.\n"
    "- [STRONG_CALM]: MC is abnormally indifferent to pain/crisis.\n"
    "- [STACCATO]: Avg sentence <40 chars. Frequent nouns endings.\n"
    "- [GAP_EFFECT]: Contrast gore with mundane daily details.\n"
    "- [CLIFFHANGER]: Ending MUST trigger 'Crisis/Truth/Cost' (No peace)."
)
RULE_SET_A_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる, "
    "『冷や汗』『瞳孔が開く』『絶望』『顔が歪む』『嘔吐』などの大仰で劇的なシリアスワード"
)

RULE_SET_B_RULES = (
    "[CORE_MANIFESTO: DARK_HARD]\n"
    "- [SUBJECTIVE_ONLY]: No author meta-commentary. Focus on MC's limited view.\n"
    "- [BODILY_LANG]: Translate anger/fear to visceral pain/coldness.\n"
    "- [SURGICAL_VIOLENCE]: Describe combat as chronological anatomical events.\n"
    "- [FETISH_DETAIL]: Show emotion via interaction with environment/tools.\n"
    "- [IRREVERSIBLE]: Loss must be permanent (severed/broken).\n"
    "- [SILENCE_BUFFER]: Use 'dead silence' before explosive actions.\n"
    "- [SMOOTH_TRANS]: No time-skips. Use light/sound for transitions.\n"
    "- [CLIFFHANGER]: End with a betrayal of peace/sudden despair."
)
RULE_SET_B_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 目を見開く, 瞳孔が収縮する, 胃の腑が冷える, "
    "記憶喪失, 思い出の消失, 名前を忘れる, 『笑い』『コミカル』等の軽薄なワードやギャグ表現"
)

RULE_SET_C_RULES = (
    "[CORE_MANIFESTO: CHAR_PSYCHO]\n"
    "- [SHOW_EGO]: Show personality via erratic behavior, not adjectives.\n"
    "- [COG_GAP]: Drive plot via 'rational MC vs delusional observers'.\n"
    "- [HEAVY_LOVE]: Favor 'obsession/dependency' over simple kindness.\n"
    "- [REACTION_PORN]: Lavishly describe NPCs' shock/horror at MC.\n"
    "- [SENSORY_FETISH]: Mandatory scent/temp/touch in every interaction.\n"
    "- [HUMILIATION]: Villain must attack MC's dignity publicly.\n"
    "- [CLIFFHANGER]: End with 'betrayal of trust' or 'fatal secret'."
)
RULE_SET_C_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる"
)

RULE_SET_D_RULES = (
    "[CORE_MANIFESTO: SLOW_LIFE]\n"
    "- [POSITIVE_SENSORY]: Maximize 'gloss of food', 'cooking sounds', 'warmth'.\n"
    "- [NO_STRESS]: Neutralize malice. Use 'well, whatever' attitude.\n"
    "- [DETAIL_80]: 80% focus on daily chores/tools/cooking processes.\n"
    "- [NATURAL_OP]: MC is comically indifferent to their own OP results.\n"
    "- [LIGHT_INTERNAL]: Allow direct internal monologue for humor/pacing.\n"
    "- [SOFT_HOOK]: End with 'new discovery' or 'expected guest'."
)
RULE_SET_D_NEG = (
    "現代知識, 地球の技術, マヨネーズ, 上下水道, 記憶喪失, 思い出の消失, 名前を忘れる, "
    "『冷や汗』『絶望』などの大仰で劇的なシリアスワード"
)

# ==========================================
# スタイル定義（文体DNA辞書）
# ==========================================
STYLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
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
        "metaphor_dna":   "「秒で終わる」「まるでゲームのバグのような」といった現代的・デジタルな比喩。明るい色彩の比喩。",
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

# ==========================================
# 執筆アーキタイプ（プリセット設定）
# ==========================================
STORY_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "カスタム": {},
    "王道ざまぁ（爽快感最大）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   5,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 90,
        "reality_cost":  20,
        "cost_severity": 1,
        "style_key":     "style_web_standard",
        "default_target_eps": 50,
        "default_word_count": 2500,
    },
    "本格戦記（泥臭い逆転）": {
        "cheat_scale":   2,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 30,
        "reality_cost":  80,
        "cost_severity": 4,
        "style_key":     "style_military_rational",
        "default_target_eps": 80,
        "default_word_count": 3000,
    },
    "死に戻り（絶望と執念）": {
        "cheat_scale":   3,
        "growth_curve":  "条件付き最強(ピーキー)",
        "system_assist": 50,
        "reality_cost":  60,
        "cost_severity": 5,
        "style_key":     "style_psychological_loop",
        "default_target_eps": 60,
        "default_word_count": 2800,
    },
    "ほのぼの飯テロ（ストレス皆無）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 100,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 30,
        "default_word_count": 1500,
    },
    "悪役令嬢の逆転劇": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 60,
        "reality_cost":  40,
        "cost_severity": 2,
        "style_key":     "style_villainess_elegant", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 2000,
    },
    "勘違い爆走（ギャップ萌え）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 80,
        "reality_cost":  20,
        "cost_severity": 0,
        "style_key":     "style_overlord", # Changed to a more appropriate style
        "default_target_eps": 45,
        "default_word_count": 2200,
    },
    "最強テイマー（もふもふ無双）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 70,
        "reality_cost":  10,
        "cost_severity": 1,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 35,
        "default_word_count": 1800,
    },
    "万能錬金術師（商会成り上がり）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   3,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 60,
        "reality_cost":  30,
        "cost_severity": 1,
        "style_key":     "style_web_standard", # Changed to a more appropriate style
        "default_target_eps": 55,
        "default_word_count": 2600,
    },
    "現代知識チート（文明無双）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 50,
        "reality_cost":  40,
        "cost_severity": 0,
        "style_key":     "style_web_standard", # Changed to a more appropriate style
        "default_target_eps": 60,
        "default_word_count": 2700,
    },
    "絶品料理人（美食無双）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 80,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 30,
        "default_word_count": 1600,
    },
    "爆笑冒険譚（コメディ最大）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 40,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_comedy_speed", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 1800,
    },
    "異世界配信者（バズり無双）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 100,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_chat_log", # Changed to a more appropriate style
        "default_target_eps": 50,
        "default_word_count": 2000,
    },
    "癒やしの聖女（溺愛平和）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   5,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 50,
        "reality_cost":  20,
        "cost_severity": 0,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 35,
        "default_word_count": 1700,
    },
    "万能魔導具師（快適生活）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   3,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 60,
        "reality_cost":  30,
        "cost_severity": 1,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 1900,
    },
    "モブ生徒の学園青春記": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   1,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 20,
        "reality_cost":  10,
        "cost_severity": 1,
        "style_key":     "style_web_standard", # Changed to a more appropriate style
        "default_target_eps": 25,
        "default_word_count": 1200,
    },
    "お気楽宝探し（浪漫追求）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 40,
        "reality_cost":  40,
        "cost_severity": 2,
        "style_key":     "style_light_fun", # Changed to a more appropriate style
        "default_target_eps": 50,
        "default_word_count": 2300,
    },
    "聖獣カフェのまったり経営": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 80,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 30,
        "default_word_count": 1400,
    },
    "ダンジョン農家（魔力で豊作）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 90,
        "reality_cost":  5,
        "cost_severity": 0,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 1700,
    },
    "癒やしの衛生兵（後方支援無双）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   3,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 40,
        "reality_cost":  20,
        "cost_severity": 1,
        "style_key":     "style_light_fun", # Changed to a more appropriate style
        "default_target_eps": 50,
        "default_word_count": 2400,
    },
    "異世界コンビニ（現代品無双）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   5,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 100,
        "reality_cost":  0,
        "cost_severity": 0,
        "style_key":     "style_web_standard", # Changed to a more appropriate style
        "default_target_eps": 45,
        "default_word_count": 2000,
    },
    "モブ執事の矜持（有能側近）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 30,
        "reality_cost":  40,
        "cost_severity": 1,
        "style_key":     "style_villainess_elegant", # Changed to a more appropriate style
        "default_target_eps": 50,
        "default_word_count": 2300,
    },
    "不老不死の道楽（伝説の趣味人）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 10,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_serious_fantasy", # Changed to a more appropriate style
        "default_target_eps": 70,
        "default_word_count": 2800,
    },
    "ギャル転生（ハイテンション）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 60,
        "reality_cost":  10,
        "cost_severity": 0,
        "style_key":     "style_comedy_speed", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 1700,
    },
    "辺境開拓（ホワイト領地経営）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 70,
        "reality_cost":  20,
        "cost_severity": 1,
        "style_key":     "style_bookworm_daily", # Changed to a more appropriate style
        "default_target_eps": 60,
        "default_word_count": 2500,
    },
    "竜騎士無双（伝説の再起）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   5,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 30,
        "reality_cost":  40,
        "cost_severity": 2,
        "style_key":     "style_web_standard", # Changed to a more appropriate style
        "default_target_eps": 70,
        "default_word_count": 2900,
    },
    "鉄壁タンク（不動の守護）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 50,
        "reality_cost":  50,
        "cost_severity": 1,
        "style_key":     "style_iron_wall", # Changed to a more appropriate style
        "default_target_eps": 65,
        "default_word_count": 2700,
    },
    "鬼人進化（弱肉強食）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   5,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 30,
        "reality_cost":  70,
        "cost_severity": 3,
        "style_key":     "style_evolution", # Changed to a more appropriate style
        "default_target_eps": 75,
        "default_word_count": 3000,
    },
    "禁書司書（全知の隠者）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 10,
        "reality_cost":  80,
        "cost_severity": 2,
        "style_key":     "style_forbidden_library", # Changed to a more appropriate style
        "default_target_eps": 50,
        "default_word_count": 2400,
    },
    "豪運ギャンブラー（一攫千金）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   4,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 60,
        "reality_cost":  30,
        "cost_severity": 2,
        "style_key":     "style_high_luck_gambler", # Changed to a more appropriate style
        "default_target_eps": 55,
        "default_word_count": 2600,
    },
    "旋律の魔術師（伝説の演奏）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 40,
        "reality_cost":  20,
        "cost_severity": 1,
        "style_key":     "style_melody_mage", # Changed to a more appropriate style
        "default_target_eps": 40,
        "default_word_count": 1900,
    },
    "孤高の真祖（夜の支配者）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   5,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 20,
        "reality_cost":  40,
        "cost_severity": 1,
        "style_key":     "style_true_ancestor", # Changed to a more appropriate style
        "default_target_eps": 60,
        "default_word_count": 2700,
    },
    "遺物修理屋（職人の矜持）": {
        "plot_pattern":  "slow_life",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 30,
        "reality_cost":  10,
        "cost_severity": 1,
        "style_key":     "style_relic_repairer", # Changed to a more appropriate style
        "default_target_eps": 45,
        "default_word_count": 2100,
    },
    "呪いの剣聖（一刀両断）": {
        "plot_pattern":  "exile_rise",
        "cheat_scale":   4,
        "growth_curve":  "徐々に成長(王道)",
        "system_assist": 0,
        "reality_cost":  90,
        "cost_severity": 4,
        "style_key":     "style_cursed_sword", # Changed to a more appropriate style
        "default_target_eps": 70,
        "default_word_count": 2900,
    },
    "影の支配者（黒幕の愉悦）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   3,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 40,
        "reality_cost":  50,
        "cost_severity": 2,
        "style_key":     "style_shadow_ruler", # Changed to a more appropriate style
        "default_target_eps": 60,
        "default_word_count": 2600,
    },
    "最強陰陽師（和風無双）": {
        "plot_pattern":  "reincarnation_cheat",
        "cheat_scale":   5,
        "growth_curve":  "最初からカンスト(無双)",
        "system_assist": 50,
        "reality_cost":  30,
        "cost_severity": 2,
        "style_key":     "style_onmyoji_master", # Changed to a more appropriate style
        "default_target_eps": 65,
        "default_word_count": 2800,
    },
}

EASY_MODE_KEYWORDS_MAP: Dict[str, str] = {
    "⚔️ 追放ざまぁ":         "追放, チート, ざまぁ, 成り上がり, 認められなかった才能",
    "🌸 悪役令嬢":           "乙女ゲーム, 転生, 破滅フラグ, 攻略対象, 逆転",
    "🔄 死に戻り":           "ループ, 死に戻り, 絶望, 執念, 完璧なルート",
    "🍲 ほのぼのスローライフ": "スローライフ, 飯テロ, 田舎暮らし, 料理, 癒し",
    "⚡ 転生チート":         "転生, チートスキル, 無自覚無双, ステータス, 異世界",
    "🗡️ 本格戦記":           "戦記, 知略, 逆転, 兵法, 硬派ファンタジー",
    "🎭 勘違い魔王":         "勘違い, 魔王, ギャップ, 威厳, 小心者",
    "🐾 もふもふ":           "もふもふ, 聖獣, テイマー, 癒やし, 召喚",
    "💰 商会無双":           "錬金術, 商会, 経営, 成り上がり, 経済",
    "💡 現代知識":           "現代知識, 文明開化, 無双, チート, 異世界",
    "🍳 絶品グルメ":         "料理, 飯テロ, 美食, 胃袋, 異世界メシ",
    "🤣 爆笑コメディ":       "コメディ, ギャグ, 残念な仲間, 爆笑, 冒険",
    "📱 異世界配信":         "配信, コメント欄, バズる, 地球, ネットスラング",
    "👼 癒やし聖女":         "聖女, 溺愛, 浄化, ほのぼの, 逆ハーレム",
    "🧙 万能魔導具師":       "魔導具, 発明, 製作, 快適, 生活魔法",
    "🌸 モブ学園":           "学園, モブ, 青春, 恋愛, 乙女ゲーム",
    "🗺️ お気楽トレジャー":       "宝探し, 鑑定, ロマン, 冒険, 秘境",
    "🐈 聖獣カフェ":         "カフェ, 聖獣, もふもふ, 経営, 癒やし",
    "🌾 ダンジョン農家":     "農家, 野菜, 収穫, ダンジョン, ステータス",
    "💊 衛生兵":           "衛生兵, 治療, サポート, TS, 勘違い",
    "🏪 異世界コンビニ":     "コンビニ, 現代知識, 道具, 利便性, 依存",
    "🤵 モブ執事":           "執事, 悪役令嬢, 献身, 有能, モブ",
    "🎨 不老不死道楽":     "不老不死, 趣味, 道具, 伝説, 超然",
    "💅 ギャル転生":         "ギャル, 陽キャ, ポジティブ, 破壊, コメディ",
    "🏰 辺境開拓":           "辺境, 開拓, 領地経営, 現代知識, 快適生活",
    "🐉 竜騎士無双":         "竜騎士, 復讐, 再起, 伝説の竜, パートナー",
    "🛡️ 鉄壁タンク":         "タンク, 鉄壁, 防御特化, 追放, 物理無効",
    "👺 鬼人進化":           "鬼人, 復讐, 進化, 覚醒, 弱肉強食",
    "📚 禁書司書":           "図書館, 禁書, 司書, 全知, 魔導書",
    "🎲 豪運ギャンブラー":    "ギャンブル, 豪運, カジノ, 心理戦, 一攫千金",
    "🎻 旋律の魔術師":       "音楽, 吟遊詩人, 旋律, バフ, 伝説の演奏",
    "🧛 孤高の真祖":         "吸血鬼, 真祖, 君臨, 眷属, 夜の支配者",
    "🛠️ 遺物修理屋":         "アーティファクト, 修理, 鑑定, 職人, ロストテクノロジー",
    "🗡️ 呪いの剣聖":         "剣聖, 呪い, 孤独, 修練, 一刀両断",
    "👑 影の支配者":         "王, 傀儡, 策略, 裏工作, 国家運営",
    "⛩️ 最強陰陽師":         "陰陽師, 式神, 呪術, 和風, 転生",
}

# --- UI用定数 ---
WIZARD_GENRE_OPTIONS = ["ファンタジー", "恋愛", "ミステリー", "VR・ゲーム", "ダンジョン", "転生", "その他"]
WIZARD_ARCHETYPE_LABELS = {
    "王道ざまぁ（爽快感最大）":     "⚔️ 王道ざまぁ",
    "本格戦記（泥臭い逆転）":       "🗡️ 本格戦記",
    "死に戻り（絶望と執念）":       "🔄 死に戻り",
    "ほのぼの飯テロ（ストレス皆無）": "🍲 ほのぼの飯テロ",
    "悪役令嬢の逆転劇":             "🌸 悪役令嬢",
    "勘違い爆走（ギャップ萌え）":   "🎭 勘違い爆走",
    "最強テイマー（もふもふ無双）": "🐾 最強テイマー",
    "万能錬金術師（商会成り上がり）": "💰 万能錬金術師",
    "現代知識チート（文明無双）":   "💡 現代知識",
    "絶品料理人（美食無双）":       "🍳 絶品料理人",
    "爆笑冒険譚（コメディ最大）":   "🤣 爆笑冒険譚",
    "異世界配信者（バズり無双）":   "📱 異世界配信",
    "癒やしの聖女（溺愛平和）":     "👼 癒やし聖女",
    "万能魔導具師（快適生活）":     "🧙 万能魔導具師",
    "モブ生徒の学園青春記":         "🌸 モブ学園",
    "お気楽宝探し（浪漫追求）":     "🗺️ お気楽トレジャー",
    "聖獣カフェのまったり経営":     "🐈 聖獣カフェ",
    "ダンジョン農家（魔力で豊作）": "🌾 ダンジョン農家",
    "癒やしの衛生兵（後方支援無双）": "💊 衛生兵",
    "異世界コンビニ（現代品無双）": "🏪 異世界コンビニ",
    "モブ執事の矜持（有能側近）":   "🤵 モブ執事",
    "不老不死の道楽（伝説の趣味人）": "🎨 不老不死道楽",
    "ギャル転生（ハイテンション）": "💅 ギャル転生",
    "辺境開拓（ホワイト領地経営）": "🏰 辺境開拓",
    "竜騎士無双（伝説の再起）":     "🐉 竜騎士無双",
    "鉄壁タンク（不動の守護）":     "🛡️ 鉄壁タンク",
    "鬼人進化（弱肉強食）":         "👺 鬼人進化",
    "禁書司書（全知の隠者）":       "📚 禁書司書",
    "豪運ギャンブラー（一攫千金）": "🎲 豪運ギャンブラー",
    "旋律の魔術師（伝説の演奏）":   "🎻 旋律の魔術師",
    "孤高の真祖（夜の支配者）":     "🧛 孤高の真祖",
    "遺物修理屋（職人の矜持）":     "🛠️ 遺物修理屋",
    "呪いの剣聖（一刀両断）":       "🗡️ 呪いの剣聖",
    "影の支配者（黒幕の愉悦）":     "👑 影の支配者",
    "最強陰陽師（和風無双）":       "⛩️ 最強陰陽師",
    "カスタム":                     "🎨 カスタム（自由設定）",
}

EASY_GENRES = {
    "⚔️ 追放ざまぁ":    {"genre": "ファンタジー", "archetype": "王道ざまぁ（爽快感最大）",
                          "desc": "不当に追放された主人公が成り上がり、元の仲間を見返す爽快ストーリー"},
    "🌸 悪役令嬢":      {"genre": "恋愛",         "archetype": "悪役令嬢の逆転劇",
                          "desc": "乙女ゲームに転生した令嬢が破滅フラグを回避しながら逆転を狙う"},
    "🔄 死に戻り":      {"genre": "ファンタジー", "archetype": "死に戻り（絶望と執念）",
                          "desc": "何度も死に戻りながら完璧な結末を目指す絶望と執念のループ作品"},
    "🍲 ほのぼのスローライフ": {"genre": "ファンタジー", "archetype": "ほのぼの飯テロ（ストレス皆無）",
                          "desc": "異世界でのんびりと料理や農業を楽しむ癒し系スローライフ"},
    "⚡ 転生チート":    {"genre": "ファンタジー", "archetype": "転生チート（無双重視）",
                          "desc": "チートスキルを持って転生した主人公が無自覚に無双するストーリー"},
    "🗡️ 本格戦記":     {"genre": "ファンタジー", "archetype": "本格戦記（泥臭い逆転）",
                          "desc": "知略と泥臭い努力で戦局を覆す硬派なリアル戦記ファンタジー"},
    "🎭 勘違い魔王":   {"genre": "ファンタジー", "archetype": "勘違い爆走（ギャップ萌え）",
                          "desc": "内心ビクビクなのに、なぜか周囲には威厳たっぷりに誤解される喜劇"},
    "🐾 もふもふ":     {"genre": "ファンタジー", "archetype": "最強テイマー（もふもふ無双）",
                          "desc": "聖獣や魔獣をテイムして愛でる、癒やしと冒険のライトストーリー"},
    "💰 商会無双":     {"genre": "ファンタジー", "archetype": "万能錬金術師（商会成り上がり）",
                          "desc": "便利な錬金アイテムで商売繁盛。富と名声を築くサクセスストーリー"},
    "💡 現代知識":     {"genre": "ファンタジー", "archetype": "現代知識チート（文明無双）",
                          "desc": "砂糖、石鹸、マヨネーズ。現代の知識で異世界の常識を塗り替える"},
    "🍳 絶品グルメ":   {"genre": "ファンタジー", "archetype": "絶品料理人（美食無双）",
                          "desc": "異世界の食材を究極の料理へ。胃袋から世界を征服する飯テロ物語"},
    "🤣 爆笑コメディ": {"genre": "ファンタジー", "archetype": "爆笑冒険譚（コメディ最大）",
                          "desc": "残念な仲間たちと贈る、腹筋崩壊間違いなしのハイテンション冒険譚"},
    "📱 異世界配信":   {"genre": "ファンタジー", "archetype": "異世界配信者（バズり無双）",
                          "desc": "魔導具で異世界から地球へ配信。リスナーとの掛け合いで爆速成り上がり"},
    "👼 癒やし聖女":   {"genre": "ファンタジー", "archetype": "癒やしの聖女（溺愛平和）",
                          "desc": "ただそこにいるだけで周囲を浄化。最強の騎士たちに溺愛される平和な日常"},
    "🧙 万能魔導具師": {"genre": "ファンタジー", "archetype": "万能魔導具師（快適生活）",
                          "desc": "現代の便利家電を魔導具で再現。異世界の生活をQOL爆上げで快適に"},
    "🌸 モブ学園":     {"genre": "学園",         "archetype": "モブ生徒の学園青春記",
                          "desc": "乙女ゲームの舞台で、メインキャラを横目にモブ同士で青春を謳歌する"},
    "🌾 ダンジョン農家": {"genre": "ファンタジー", "archetype": "ダンジョン農家（魔力で豊作）",
                          "desc": "危険なダンジョンで家庭菜園？ 魔力の水で育つ野菜はステータス爆上げ"},
    "🗺️ お気楽トレジャー": {"genre": "ファンタジー", "archetype": "お気楽宝探し（浪漫追求）",
                          "desc": "鑑定スキル片手に世界中の秘境を巡り、お宝を掘り出すロマン溢れる冒険譚"},
    "🐈 聖獣カフェ":    {"genre": "ファンタジー", "archetype": "聖獣カフェのまったり経営",
                          "desc": "最強の聖獣たちに懐かれた主人公が、街の片隅で癒やしのカフェを営む物語"},
    "💊 衛生兵":        {"genre": "ファンタジー", "archetype": "癒やしの衛生兵（後方支援無双）",
                          "desc": "戦場で傷つく兵士たちを規格外の魔法で救い、知らぬ間に伝説となる物語"},
    "🏪 異世界コンビニ": {"genre": "ファンタジー", "archetype": "異世界コンビニ（現代品無双）",
                          "desc": "現代の商品で異世界の常識を塗り替え、便利な暮らしを広めるサクセスストーリー"},
    "🤵 モブ執事":      {"genre": "恋愛",         "archetype": "モブ執事の矜持（有能側近）",
                          "desc": "悪役令嬢の側近として、彼女を救うために影で無双する有能な執事の物語"},
    "🎨 不老不死道楽":  {"genre": "ファンタジー", "archetype": "不老不死の道楽（伝説の趣味人）",
                          "desc": "永遠の時を生きる主人公が、気が向くままに究極の逸品を作る悠久の物語"},
    "💅 ギャル転生":    {"genre": "ファンタジー", "archetype": "ギャル転生（ハイテンション）",
                          "desc": "陽キャなギャルが異世界を救う？ 圧倒的ポジティブさで全てをハッピーにする物語"},
    "🏰 辺境開拓":      {"genre": "ファンタジー", "archetype": "辺境開拓（ホワイト領地経営）",
                          "desc": "見捨てられた辺境の地を、魔法と現代の知恵で理想のホワイト領地に変える領地経営物語"},
    "🐉 竜騎士無双":    {"genre": "ファンタジー", "archetype": "竜騎士無双（伝説の再起）",
                          "desc": "かつて世界を救った伝説の竜騎士が、名前を隠して学園に入学し無双するサクセスストーリー"},
    "🛡️ 鉄壁タンク":    {"genre": "ファンタジー", "archetype": "鉄壁タンク（不動の守護）",
                          "desc": "攻撃力ゼロと蔑まれ追放されたタンクが、実は物理無効の最強防御で無双する"},
    "👺 鬼人進化":      {"genre": "ファンタジー", "archetype": "鬼人進化（弱肉強食）",
                          "desc": "最弱の鬼として転生した主人公が、喰らった敵の能力を奪い進化し続ける物語"},
    "📚 禁書司書":      {"genre": "ファンタジー", "archetype": "禁書司書（全知の隠者）",
                          "desc": "世界の全知識を収めた禁断の図書館の主となり、知略で歴史を動かす隠者の物語"},
    "🎲 豪運ギャンブラー": {"genre": "その他", "archetype": "豪運ギャンブラー（一攫千金）",
                          "desc": "異世界カジノを舞台に、スキル『豪運』で強敵たちを破産させる逆転サクセスストーリー"},
    "🎻 旋律の魔術師":  {"genre": "ファンタジー", "archetype": "旋律の魔術師（伝説の演奏）",
                          "desc": "失われた古代の音楽魔法を操り、歌声一つで軍勢を鎮め世界を癒やす旅路"},
    "🧛 孤高の真祖":    {"genre": "ファンタジー", "archetype": "孤高の真祖（夜の支配者）",
                          "desc": "長い眠りから覚めた伝説の吸血鬼が、ただ静かに暮らしたいのに神格化される物語"},
    "🛠️ 遺物修理屋":    {"genre": "ファンタジー", "archetype": "遺物修理屋（職人の矜持）",
                          "desc": "ガラクタにしか見えない古代遺物を直し、現代知識を組み合わせて新文明を築く物語"},
    "🗡️ 呪いの剣聖":    {"genre": "ファンタジー", "archetype": "呪いの剣聖（一刀両断）",
                          "desc": "抜けば命を削る呪いの剣を背負い、たった一人で帝国の軍勢を迎え撃つ剣聖の孤独な戦記"},
    "👑 影の支配者":    {"genre": "ミステリー", "archetype": "影の支配者（黒幕の愉悦）",
                          "desc": "無能な傀儡王として擁立された少年が、裏で糸を引き国家を救い上げる策略譚"},
    "⛩️ 最強陰陽師":    {"genre": "転生",         "archetype": "最強陰陽師（和風無双）",
                          "desc": "現代最強の陰陽師が魔法世界に転生。式神と呪術で魔法の常識を破壊する"},
}

# ==========================================
# Jinja2 プロンプトテンプレート定義
# ==========================================
PROMPT_TEMPLATES: Dict[str, str] = {
    "style_instruction.j2": """
【Target Style: {{ style_name }}】
【Dialogue Ratio】: {{ dialogue_ratio }}
{{ instruction }}
{{ dna_correction }}
""",
    "script_prompt.j2": """
[SYSTEM]
あなたは超高性能な脚本家AIです。
以下のプロット（ゴール）、キャラクター設定、過去のあらすじに基づき、キャラクター間の緊迫した会話劇を生成せよ。

【厳格な禁止・制約事項】
1. プロットに書かれた事象を、そのままキャラクターの口で説明させることを禁ずる。
2. キャラクターは常に情報の半分を隠し、物語上の状況を語らせるな。
3. Showで意図を伝えよ: 肉体動作、表情の記述でのみ表現せよ。
4. Blueprintはゴール: 会話を通じてその状況を「観客に感じさせろ」。

OUTPUT STRICTLY IN JSON FORMAT.
[/SYSTEM]

{{ plots_text }}

【Character Context】
{{ char_context }}

【Previous Context】
{{ prev_context }}

【Villain Strategy】
{{ villain_prompt }}
""",
    "novelize_prompt.j2": """
[SYSTEM]
あなたは極上の文体を持つWeb小説家です。
以下の【台本】を骨格とし、最高密度の小説を執筆してください。

【Target Style & Rules】
{{ style_instruction }}
{{ rule_set_content }}
[/SYSTEM]

{{ plots_text }}
{{ scripts_text }}

【Character Context】
{{ char_context }}

【Previous Context】
{{ prev_context }}
""",
    "ai_producer_audit": """
あなたは覇権プロデューサーです。以下の企画案を分析し、より読者に刺さるキーワード、コンセプト、主人公像を提案してください。

ジャンル: {{ genre }}
キーワード: {{ keywords }}
注入要素: {{ trend_memo }}

【指令】現状の案をブラッシュアップし、商用出版でランキング1位を狙える具体的な修正案を出力してください。
""",
}

# ==========================================
# グローバル設定モデル（Pydantic）
# ==========================================
class GlobalConfigModel(BaseModel):
    model_writing:     str   = MODEL_WRITING
    model_planning:    str   = MODEL_PLANNING
    db_path:           str   = str(BASE_DIR / DB_FILE)
    max_history_len:   int   = 30

    # Pydantic V2 の 'model_' 予約語制限を回避
    model_config = {"protected_namespaces": ()}

    auto_backup:       bool  = True
    safe_append_mode:  str   = SAFE_APPEND_MODE_DEFAULT
    cooldown_base:     float = COOLDOWN_BASE_DEFAULT
    cooldown_min:      float = COOLDOWN_MIN_DEFAULT
    cooldown_max:      float = COOLDOWN_MAX_DEFAULT
    max_concurrency:   int   = 0   # 0 = 自動
    optimized_prompt_patch: str = "" # AIによる自己最適化パッチ

    @classmethod
    def default(cls) -> "GlobalConfigModel":
        return cls()

    def get_auto_concurrency(self) -> int:
        return min(8, (os.cpu_count() or 1) * 2)


# ==========================================
# GlobalConfig（Streamlitセッション統合設定管理）
# ==========================================
class GlobalConfig:
    """アプリケーション全体の設定をStreamlitセッション経由で保持する"""

    def __init__(self):
        import streamlit as st
        if "config" not in st.session_state:
            st.session_state.config = GlobalConfigModel.default().model_dump()

    def get(self, key: str, default=None):
        import streamlit as st
        cfg = st.session_state.get("config")
        if cfg is None:
            return default
        return cfg.get(key, default)

    def set(self, key: str, value) -> None:
        import streamlit as st
        if key not in GlobalConfigModel.model_fields.keys():
            raise KeyError(f"Unknown config key: {key}")
        if "config" not in st.session_state:
            st.session_state.config = GlobalConfigModel.default().model_dump()
        st.session_state.config[key] = value

    def update(self, **kwargs) -> None:
        import streamlit as st
        validated = GlobalConfigModel(**{**st.session_state.config, **kwargs})
        st.session_state.config = validated.model_dump()

    def get_auto_concurrency(self) -> int:
        return min(8, (os.cpu_count() or 1) * 2)

    def display_sidebar(self) -> None:
        import streamlit as st
        st.sidebar.header("⚙️ 詳細設定（Config）")
        st.sidebar.text(f"model_writing: {self.get('model_writing')}")
        st.sidebar.text(f"model_planning: {self.get('model_planning')}")
        st.sidebar.number_input(
            "max_history_len", min_value=1, max_value=100,
            value=self.get("max_history_len", 30), key="max_history_len"
        )
        st.sidebar.number_input(
            "max_concurrency (0=Auto)", min_value=0, max_value=20,
            value=self.get("max_concurrency", 0), key="cfg_max_concurrency"
        )
        st.sidebar.checkbox(
            "auto_backup", value=self.get("auto_backup", True), key="auto_backup"
        )
        st.sidebar.selectbox(
            "safe_append_mode", SAFE_APPEND_MODE_OPTIONS,
            index=SAFE_APPEND_MODE_OPTIONS.index(self.get("safe_append_mode", SAFE_APPEND_MODE_DEFAULT)),
            key="safe_append_mode"
        )
