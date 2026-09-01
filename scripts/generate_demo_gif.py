"""AutoNovel 次世代UI/UXワークフロー デモGIF自動生成スクリプト
Pillowを使用して、ダークテーマ・ガラスモーフィズム調の高品質アニメーションGIFを生成する。
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "demo.gif")
WIDTH = 960
HEIGHT = 540

# カラーパレット
BG_DARK = (15, 15, 20)
CARD_BG = (28, 28, 35)
PANEL_BG = (22, 22, 28)
BORDER_COLOR = (50, 50, 65)
TEXT_WHITE = (245, 245, 250)
TEXT_MUTED = (160, 160, 175)
ACCENT_PRIMARY = (167, 139, 250) # Purple
ACCENT_CYAN = (56, 189, 248)    # Sky Blue
ACCENT_AMBER = (251, 191, 36)   # Amber
ACCENT_ROSE = (244, 63, 94)     # Rose
ACCENT_GREEN = (52, 211, 153)   # Green

def get_font(size: int, bold: bool = False):
    try:
        font_name = "msgothic.ttc" if os.name == "nt" else "DejaVuSans.ttf"
        font_path = f"C:\\Windows\\Fonts\\{font_name}" if os.name == "nt" else font_name
        return ImageFont.truetype(font_path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

font_title = get_font(20, bold=True)
font_subtitle = get_font(14)
font_body = get_font(13)
font_small = get_font(11)
font_code = get_font(12)

def draw_header(draw: ImageDraw.ImageDraw, active_tab: str):
    # トップバー
    draw.rectangle([0, 0, WIDTH, 48], fill=(20, 20, 26))
    draw.line([0, 48, WIDTH, 48], fill=BORDER_COLOR, width=1)
    
    # ブランド
    draw.text((20, 14), "AutoNovel Studio", font=font_title, fill=ACCENT_PRIMARY)
    draw.text((220, 18), "v4.0 Next-Gen Orchestration", font=font_small, fill=TEXT_MUTED)
    
    # モード切り替えタブ
    tabs = [("⚡ かんたんモード", "easy"), ("🔮 逆算プロット", "reverse"), ("🚀 上級者 Studio", "studio"), ("🕸️ 相関図", "graph")]
    x = 480
    for label, mode in tabs:
        is_active = (active_tab == mode)
        bg = (55, 45, 90) if is_active else (30, 30, 38)
        border = ACCENT_PRIMARY if is_active else BORDER_COLOR
        draw.rounded_rectangle([x, 10, x + 110, 38], radius=6, fill=bg, outline=border, width=1)
        draw.text((x + 10, 17), label, font=font_small, fill=TEXT_WHITE if is_active else TEXT_MUTED)
        x += 118

def create_frame_1(): # かんたんモード & 企画ガチャ
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "easy")
    
    # 左パネル: 制作設定
    draw.rounded_rectangle([20, 64, 460, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((36, 80), "⚙️ 制作設定 & キャラクター", font=font_title, fill=ACCENT_PRIMARY)
    
    draw.text((36, 120), "ジャンル: ハイファンタジー (R15)", font=font_body, fill=TEXT_WHITE)
    draw.rounded_rectangle([36, 142, 440, 172], radius=4, fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.text((46, 148), "主人公名: アルト", font=font_body, fill=TEXT_WHITE)
    
    draw.rounded_rectangle([36, 184, 440, 214], radius=4, fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.text((46, 190), "能力: 古代魔導剣術 / 性格: 熱血・正義感", font=font_body, fill=TEXT_WHITE)
    
    # 3案ガチャモーダル（オーバーレイ）
    draw.rounded_rectangle([60, 240, 420, 490], radius=8, fill=(24, 24, 32), outline=ACCENT_CYAN, width=2)
    draw.text((75, 252), "🎲 3案 企画ガチャ (Gacha Pitch)", font=font_subtitle, fill=ACCENT_CYAN)
    
    plans = [
        ("⚔️ 王道", "古の覇剣を継ぐ者", "伝説の魔剣に選ばれた青年が滅びの運命に抗う", ACCENT_CYAN),
        ("🌀 変化球", "魔導剣の鑑定士", "戦えない青年が敵の魔導具を看破して無双", ACCENT_AMBER),
        ("🌑 ダーク", "呪われた復讐剣", "仲間を奪われた剣士が禁断の力で帝国を討つ", ACCENT_ROSE)
    ]
    
    py = 282
    for p_type, p_title, p_desc, col in plans:
        draw.rounded_rectangle([75, py, 405, py + 60], radius=6, fill=CARD_BG, outline=BORDER_COLOR, width=1)
        draw.text((85, py + 6), p_type, font=font_small, fill=col)
        draw.text((145, py + 6), p_title, font=font_subtitle, fill=TEXT_WHITE)
        draw.text((85, py + 28), p_desc[:32] + "...", font=font_small, fill=TEXT_MUTED)
        draw.rounded_rectangle([335, py + 30, 395, py + 52], radius=4, fill=ACCENT_PRIMARY)
        draw.text((345, py + 35), "採用", font=font_small, fill=(255, 255, 255))
        py += 68
        
    # 右パネル: 本文エディタプレビュー
    draw.rounded_rectangle([480, 64, 940, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((496, 80), "📖 執筆プレビュー & エクスポート", font=font_title, fill=ACCENT_CYAN)
    
    draw.rounded_rectangle([496, 120, 924, 156], radius=6, fill=ACCENT_GREEN)
    draw.text((610, 130), "📦 納品パッケージ (ZIP) ダウンロード", font=font_subtitle, fill=(10, 40, 20))
    
    draw.rounded_rectangle([496, 170, 924, 490], radius=6, fill=(12, 12, 16), outline=BORDER_COLOR, width=1)
    sample_text = [
        "【第1話: 運命の覚醒】",
        "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。",
        "刀身から青い燐光が立ち昇り、少年の身体を包み込む。",
        "『汝、永劫の誓約を果たす器たるや――』",
        "頭蓋に直接響く荘厳な声とともに、失われた魔導の記憶が怒涛のように流れ込んできた。"
    ]
    ty = 190
    for line in sample_text:
        draw.text((512, ty), line, font=font_body, fill=TEXT_WHITE)
        ty += 26
        
    return img

def create_frame_2(): # 逆算プロットビルダー
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "reverse")
    
    draw.rounded_rectangle([40, 64, 920, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((60, 80), "🔮 逆算プロットビルダー (4-Step Plot Generator)", font=font_title, fill=ACCENT_PRIMARY)
    
    # 4ステップ進捗バー
    steps = [("1. 感情ゴール", "爽快感・達成感"), ("2. 支払う代償", "平穏な日常"), ("3. 核心対立", "理想 vs 現実"), ("4. 開幕フック", "異世界・覚醒")]
    sx = 60
    for i, (st, sv) in enumerate(steps):
        draw.rounded_rectangle([sx, 120, sx + 195, 175], radius=6, fill=(40, 35, 60), outline=ACCENT_PRIMARY, width=1)
        draw.text((sx + 12, 130), f"Step {i+1}: {st}", font=font_small, fill=ACCENT_PRIMARY)
        draw.text((sx + 12, 150), f"✅ {sv}", font=font_subtitle, fill=TEXT_WHITE)
        sx += 205
        
    # 生成結果プレビュー
    draw.rounded_rectangle([60, 195, 900, 490], radius=6, fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.text((80, 210), "✨ 自動生成されたプロット構造 (全10話・3アーク & カタルシス波形)", font=font_subtitle, fill=ACCENT_CYAN)
    
    # アーク
    arcs = [
        ("第1部: 序章と覚醒 (第1〜3話)", "平穏を失い、秘剣の真実を追う旅へ出る"),
        ("第2部: 葛藤と試練 (第4〜7話)", "王国の暗部と対峙し、己の理想を試される"),
        ("第3部: 決戦と大団円 (第8〜10話)", "最大の敵を討ち、世界の理を再構築する")
    ]
    ax = 80
    for atitle, asumm in arcs:
        draw.rounded_rectangle([ax, 240, ax + 260, 310], radius=6, fill=(32, 32, 42), outline=BORDER_COLOR, width=1)
        draw.text((ax + 10, 250), atitle, font=font_small, fill=ACCENT_AMBER)
        draw.text((ax + 10, 275), asumm[:18] + "...", font=font_small, fill=TEXT_MUTED)
        ax += 272
        
    # エピソード一覧
    eps = [
        ("第1話: 運命の覚醒", "ダンジョンで魔導剣を入手", "緊張度: 40"),
        ("第2話: 追跡者たち", "帝国の密偵による襲撃", "緊張度: 60"),
        ("第3話: 決断の夜", "故郷を捨て旅立つ決意", "緊張度: 75 ⭐ カタルシス"),
        ("第4話: 迷宮都市", "新たな仲間との出会い", "緊張度: 50"),
    ]
    ey = 330
    for etitle, esum, etens in eps:
        draw.rounded_rectangle([80, ey, 900, ey + 32], radius=4, fill=(26, 26, 34), outline=BORDER_COLOR, width=1)
        draw.text((95, ey + 8), etitle, font=font_body, fill=TEXT_WHITE)
        draw.text((300, ey + 8), esum, font=font_body, fill=TEXT_MUTED)
        draw.text((700, ey + 8), etens, font=font_small, fill=ACCENT_CYAN if "カタルシス" not in etens else ACCENT_AMBER)
        ey += 38
        
    return img

def create_frame_3(): # 上級者Studio
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "studio")
    
    # 3カラム
    # 左: 設定 & キャラ
    draw.rounded_rectangle([20, 64, 250, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((36, 80), "📖 設定 & キャラ", font=font_subtitle, fill=ACCENT_CYAN)
    draw.text((36, 115), "主人公: アルト", font=font_small, fill=TEXT_WHITE)
    draw.text((36, 140), "性格: 熱血 / 誇り高い", font=font_small, fill=TEXT_MUTED)
    draw.text((36, 165), "能力: 古代魔導剣術", font=font_small, fill=TEXT_MUTED)
    draw.text((36, 190), "ジャンル: ハイファンタジー", font=font_small, fill=TEXT_MUTED)
    
    # 中央: 原稿エディタ + Next Beats
    draw.rounded_rectangle([265, 64, 695, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((280, 80), "✏️ 原稿エディタ (文字数: 1,842字)", font=font_subtitle, fill=TEXT_WHITE)
    
    # 本文テキスト
    draw.rounded_rectangle([280, 110, 680, 360], radius=6, fill=(12, 12, 16), outline=BORDER_COLOR, width=1)
    editor_lines = [
        "アルトは青く輝く刀身を構え、黒き騎士を見据えた。",
        "「ここから先は通さない。俺の剣がそう言っている」",
        "空気が凍りつき、魔力の火花が二人の間で激しく散る。",
        "黒き騎士の大剣が唸りを上げて振り下ろされた――！"
    ]
    ey = 125
    for eline in editor_lines:
        draw.text((295, ey), eline, font=font_body, fill=TEXT_WHITE)
        ey += 28
        
    # Next Beats 展開提案
    draw.rounded_rectangle([280, 375, 680, 495], radius=6, fill=PANEL_BG, outline=ACCENT_PRIMARY, width=1)
    draw.text((295, 385), "🔮 Next Beats (次の展開 3案)", font=font_small, fill=ACCENT_PRIMARY)
    beats = [
        ("⚔️ 必殺の一撃", "秘剣の覚醒奥義で大剣を打ち砕く", "緊張度: 90"),
        ("🛡️ 仲間の救援", "魔導士の詠唱が間に合い防壁を展開", "緊張度: 70"),
        ("🌀 衝撃の真実", "騎士の仮面が割れ、生き別れの兄の顔が", "緊張度: 95 ⭐")
    ]
    by = 405
    for b_title, b_desc, b_t in beats:
        draw.text((295, by), f"{b_title}: {b_desc}", font=font_small, fill=TEXT_WHITE)
        draw.text((600, by), b_t, font=font_small, fill=ACCENT_AMBER)
        by += 26
        
    # 右: GraphRAG 専属AI編集者
    draw.rounded_rectangle([710, 64, 940, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((725, 80), "🧠 専属 AI 編集者 (GraphRAG)", font=font_subtitle, fill=ACCENT_PRIMARY)
    
    # チャット吹き出し
    draw.rounded_rectangle([725, 120, 925, 165], radius=6, fill=(35, 30, 50))
    draw.text((735, 128), "ユーザー:", font=font_small, fill=ACCENT_PRIMARY)
    draw.text((735, 144), "魔導剣の弱点と設定は？", font=font_small, fill=TEXT_WHITE)
    
    draw.rounded_rectangle([725, 180, 925, 270], radius=6, fill=(26, 35, 45))
    draw.text((735, 188), "AI 編集者:", font=font_small, fill=ACCENT_CYAN)
    draw.text((735, 206), "古代魔導剣は連続使用で", font=font_small, fill=TEXT_WHITE)
    draw.text((735, 224), "所有者の魔力を急速消費します。", font=font_small, fill=TEXT_WHITE)
    draw.text((735, 246), "📊 出典: [設定Bible] p.12", font=font_small, fill=ACCENT_AMBER)
    
    # 矛盾診断結果
    draw.rounded_rectangle([725, 285, 925, 495], radius=6, fill=(20, 35, 28), outline=ACCENT_GREEN, width=1)
    draw.text((735, 295), "🔍 リアルタイム矛盾診断", font=font_small, fill=ACCENT_GREEN)
    draw.text((735, 320), "✅ キャラクター整合性: 良好", font=font_small, fill=TEXT_WHITE)
    draw.text((735, 345), "✅ タイムライン順序: 正常", font=font_small, fill=TEXT_WHITE)
    draw.text((735, 370), "✅ 伏線回収率: 85%", font=font_small, fill=TEXT_WHITE)
    
    return img

def create_frame_4(): # インライン推敲 & 五感描写
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "studio")
    
    draw.rounded_rectangle([100, 64, 860, 510], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((120, 80), "🪄 インライン AI 五感推敲 & Show, Don't Tell (Sudowrite 式)", font=font_title, fill=ACCENT_PRIMARY)
    
    # エディタ領域
    draw.rounded_rectangle([120, 120, 840, 240], radius=6, fill=(12, 12, 16), outline=BORDER_COLOR, width=1)
    draw.text((140, 140), "ダンジョンの奥深くで、アルトは冷たい石壁に手をついた。", font=font_body, fill=TEXT_WHITE)
    
    # 選択ハイライト
    draw.rectangle([140, 172, 450, 196], fill=(70, 45, 120))
    draw.text((140, 175), "アルトは強い恐怖を感じていた。", font=font_body, fill=(255, 255, 150))
    draw.text((460, 175), "暗闇の奥から唸り声が響く。", font=font_body, fill=TEXT_WHITE)
    
    # フローティング推敲ツールバー
    draw.rounded_rectangle([140, 215, 820, 275], radius=8, fill=(35, 35, 48), outline=ACCENT_CYAN, width=2)
    draw.text((155, 235), "🪄 AI推敲:", font=font_small, fill=ACCENT_PRIMARY)
    
    tools = ["👁️ 視覚", "👂 聴覚", "👃 嗅覚", "✋ 触覚", "✨ 比喩", "🎭 Show, Don't Tell", "⚡ 緊迫感UP"]
    tx = 230
    for t in tools:
        is_sel = (t == "🎭 Show, Don't Tell")
        bg = ACCENT_PRIMARY if is_sel else (50, 50, 65)
        draw.rounded_rectangle([tx, 227, tx + 82, 263], radius=4, fill=bg)
        draw.text((tx + 6, 236), t, font=font_small, fill=(255, 255, 255) if is_sel else TEXT_WHITE)
        tx += 86
        
    # AI 提案プレビューカード
    draw.rounded_rectangle([140, 290, 820, 485], radius=8, fill=PANEL_BG, outline=ACCENT_AMBER, width=2)
    draw.text((160, 305), "📝 提案プレビュー (Show, Don't Tell 変換 / 感情を行動と情景描写に昇華):", font=font_subtitle, fill=ACCENT_AMBER)
    
    preview_box = [
        "「心臓が早鐘のように肋骨を叩き、喉の奥が砂を噛んだように渇いていた。",
        " 握りしめた柄から伝わる冷たさすら、滲み出た脂汗で滑り落ちそうになる――」"
    ]
    py = 345
    for pline in preview_box:
        draw.text((160, py), pline, font=font_body, fill=(250, 250, 200))
        py += 28
        
    # 適用ボタン
    draw.rounded_rectangle([520, 430, 660, 470], radius=6, fill=ACCENT_PRIMARY)
    draw.text((540, 442), "✅ 選択箇所を置換", font=font_small, fill=(255, 255, 255))
    
    draw.rounded_rectangle([680, 430, 800, 470], radius=6, fill=(45, 45, 60))
    draw.text((705, 442), "➕ 直後に追記", font=font_small, fill=TEXT_WHITE)
    
    return img

def create_frame_5(): # GraphRAG 物理演算ナレッジグラフ & 納品パッケージ
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)
    draw_header(draw, "graph")
    
    draw.rounded_rectangle([40, 64, 920, 510], radius=8, fill=(18, 18, 24), outline=BORDER_COLOR, width=1)
    draw.text((60, 80), "🕸️ AutoNovel 物理演算ナレッジグラフ (Apache AGE / Force-Directed)", font=font_title, fill=ACCENT_PRIMARY)
    
    # グラフノード描画
    nodes = [
        ("アルト", "Character", 280, 250, ACCENT_CYAN, 24),
        ("古代魔導剣", "Item", 450, 180, ACCENT_AMBER, 18),
        ("王都ルミナス", "Location", 520, 320, ACCENT_GREEN, 20),
        ("黒き騎士", "Character", 200, 380, ACCENT_ROSE, 20),
        ("帝国騎士団", "Faction", 380, 420, ACCENT_PRIMARY, 22),
        ("300年前の大厄災", "Event", 650, 220, (230, 120, 200), 22)
    ]
    
    edges = [
        (280, 250, 450, 180, "EQUIPPED_WITH"),
        (280, 250, 200, 380, "RIVAL_OF"),
        (200, 380, 380, 420, "BELONGS_TO"),
        (280, 250, 520, 320, "HEADS_TO"),
        (450, 180, 650, 220, "CREATED_IN"),
    ]
    
    for x1, y1, x2, y2, label in edges:
        draw.line([x1, y1, x2, y2], fill=(70, 70, 90), width=2)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        draw.text((mx - 20, my - 8), label, font=font_small, fill=(130, 130, 150))
        
    for name, ntype, nx, ny, ncol, r in nodes:
        draw.ellipse([nx - r - 4, ny - r - 4, nx + r + 4, ny + r + 4], fill=(ncol[0]//3, ncol[1]//3, ncol[2]//3))
        draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=ncol, outline=(255, 255, 255), width=2)
        draw.text((nx - 20, ny + r + 6), name, font=font_small, fill=TEXT_WHITE)
        
    # サイドバー詳細
    draw.rounded_rectangle([720, 120, 900, 480], radius=8, fill=CARD_BG, outline=BORDER_COLOR, width=1)
    draw.text((735, 135), "📋 選択エンティティ", font=font_subtitle, fill=ACCENT_CYAN)
    draw.text((735, 170), "アルト (Character)", font=font_title, fill=TEXT_WHITE)
    draw.text((735, 205), "・役割: 主人公", font=font_body, fill=TEXT_MUTED)
    draw.text((735, 230), "・所持品: 古代魔導剣", font=font_body, fill=TEXT_MUTED)
    draw.text((735, 255), "・関係: 黒き騎士 (宿敵)", font=font_body, fill=TEXT_MUTED)
    draw.text((735, 280), "・所属: 自由冒険者", font=font_body, fill=TEXT_MUTED)
    
    draw.rounded_rectangle([735, 340, 885, 460], radius=6, fill=(20, 40, 30), outline=ACCENT_GREEN, width=1)
    draw.text((745, 355), "📦 納品パッケージ", font=font_small, fill=ACCENT_GREEN)
    draw.text((745, 380), "・01_本文.txt (10話)", font=font_small, fill=TEXT_WHITE)
    draw.text((745, 405), "・02_設定資料.txt", font=font_small, fill=TEXT_WHITE)
    draw.text((745, 430), "・04_データダンプ.json", font=font_small, fill=TEXT_WHITE)
    
    return img

def main():
    print("Generating demo frames...")
    frames = [
        create_frame_1(),
        create_frame_2(),
        create_frame_3(),
        create_frame_4(),
        create_frame_5(),
    ]
    
    # スムーズな遷移のため各フレームを複数枚保持（表示時間調整）
    gif_frames = []
    durations = []
    
    for f in frames:
        # 1フレームあたり約2秒（2000ms）
        gif_frames.append(f)
        durations.append(2200)
        
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    gif_frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    print(f"Demo GIF successfully generated at: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
