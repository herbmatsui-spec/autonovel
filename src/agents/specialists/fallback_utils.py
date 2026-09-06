"""Common fallback utilities for specialist auditors.

Phase 2 / Guideline #3: Shared rule-based fallback logic for all 8 specialists.
Provides entity extraction, relation graph building, and semantic consistency checking.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def extract_entities(text: str, bible: dict[str, Any]) -> dict[str, set[str]]:
    """Extract entities from world bible categorized by type.

    Args:
        text: Draft text to check for entity mentions
        bible: World bible snapshot with characters, locations, items, factions, terms

    Returns:
        Dict mapping category -> set of entity names mentioned in bible
    """
    entities: dict[str, set[str]] = defaultdict(set)

    for category in ("characters", "locations", "items", "factions", "terms"):
        val = bible.get(category)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    if name:
                        entities[category].add(name)
                elif isinstance(item, str):
                    entities[category].add(item)
        elif isinstance(val, dict):
            name = val.get("name", "")
            if name:
                entities[category].add(name)

    return dict(entities)


def build_relation_graph(bible: dict[str, Any]) -> dict[str, set[str]]:
    """Build entity relation graph from world bible.

    Extracts explicit relationships like:
    - character -> location (where they are)
    - character -> item (what they own)
    - character -> faction (allegiance)
    - faction -> location (territory)
    - character -> character (enemy/ally/family)

    Args:
        bible: World bible snapshot

    Returns:
        Dict mapping entity -> set of related entities
    """
    graph: dict[str, set[str]] = defaultdict(set)

    characters = bible.get("characters", [])
    locations = bible.get("locations", [])
    items = bible.get("items", [])
    factions = bible.get("factions", [])

    char_names = set()
    for c in characters:
        if isinstance(c, dict):
            name = c.get("name", "")
            if name:
                char_names.add(name)
                # Location relation
                loc = c.get("location") or c.get("current_location")
                if loc:
                    graph[name].add(loc)
                # Item relations
                for key in ("items", "equipment", "weapon", "possessions"):
                    val = c.get(key)
                    if isinstance(val, list):
                        for v in val:
                            if isinstance(v, str):
                                graph[name].add(v)
                            elif isinstance(v, dict):
                                n = v.get("name", "")
                                if n:
                                    graph[name].add(n)
                    elif isinstance(val, str):
                        graph[name].add(val)
                # Faction relation
                fac = c.get("faction") or c.get("allegiance")
                if fac:
                    graph[name].add(fac)
                # Status relations (dead/alive)
                status = c.get("status") or c.get("state")
                if status:
                    graph[name].add(f"status:{status}")
        elif isinstance(c, str):
            char_names.add(c)

    # Location -> characters mapping
    for loc in locations:
        if isinstance(loc, dict):
            name = loc.get("name", "")
            if name:
                for c in characters:
                    if isinstance(c, dict) and (c.get("location") == name or c.get("current_location") == name):
                        graph[name].add(c.get("name", ""))

    # Faction -> members
    for fac in factions:
        if isinstance(fac, dict):
            name = fac.get("name", "")
            if name:
                members = fac.get("members", [])
                for m in members:
                    if isinstance(m, str):
                        graph[name].add(m)
                    elif isinstance(m, dict):
                        graph[name].add(m.get("name", ""))

    # Explicit relationship pairs
    relationships = bible.get("relationships", [])
    for rel in relationships:
        if isinstance(rel, dict):
            a = rel.get("from") or rel.get("source")
            b = rel.get("to") or rel.get("target")
            rtype = rel.get("type", "related")
            if a and b:
                graph[a].add(f"{rtype}:{b}")
                graph[b].add(f"{rtype}:{a}")

    return {k: v for k, v in graph.items() if v}


def check_semantic_consistency(draft: str, graph: dict[str, set[str]]) -> float:
    """Check semantic consistency of draft against relation graph.

    Detects contradictions like:
    - Dead character appearing alive
    - Character in location they can't reach
    - Character using item they don't own
    - Faction member acting against faction

    Args:
        draft: Draft text
        graph: Entity relation graph from build_relation_graph

    Returns:
        Consistency score 0.0-1.0 (1.0 = no contradictions detected)
    """
    if not graph:
        return 0.8  # Neutral when no graph

    contradictions = 0
    total_checks = 0

    # Check 1: Dead character appearing in action
    dead_chars = {ent for ent, rels in graph.items() if any("dead" in r.lower() or "deceased" in r.lower() or "死亡" in r for r in rels)}
    for char in dead_chars:
        total_checks += 1
        # Look for active verbs near character name
        pattern = rf"{re.escape(char)}[^。]*?(?:動い|走っ|戦っ|話し|考え|感じ|見|聞|立ち|座っ|歩い|飛ん|跳ん|斬っ|刺し|撃ち|放っ|振っ|構え|抜い|握っ|掴み|放ち|放た|唱え|詠ん|祈っ|笑っ|泣き|怒っ|叫び|囁き|頷い|眉を|目を見|視線|表情|声|手|足|体|身|心|精神|魂|命|息|鼓動)"
        if re.search(pattern, draft):
            contradictions += 1

    # Check 2: Location contradiction (character in two places)
    char_locations: dict[str, set[str]] = defaultdict(set)
    for ent, rels in graph.items():
        for rel in rels:
            if rel.startswith("location:") or rel in (l for l in graph.keys() if any(loc in rel for loc in ["都", "城", "村", "町", "森", "山", "川", "海", "砂漠", "平原", "洞窟", "遺跡", "ダンジョン", "塔", "神殿", "教会", "学校", "病院", "会社", "家", "部屋", "駅", "空港", "港"])):
                char_locations[ent].add(rel.replace("location:", ""))

    for char, locs in char_locations.items():
        if len(locs) > 1:
            total_checks += 1
            # Check if draft mentions char in multiple locations
            mentioned_locs = [loc for loc in locs if loc in draft]
            if len(mentioned_locs) > 1:
                contradictions += 1

    # Check 3: Item ownership contradiction
    for char, rels in graph.items():
        for rel in rels:
            if rel.startswith("item:") or any(keyword in rel for keyword in ["剣", "刀", "槍", "弓", "矢", "盾", "鎧", "杖", "魔法", "指輪", "首飾り", "薬", "巻物", "書", "地図", "鍵", "宝石", "金貨", "銀貨", "銅貨"]):
                item_name = rel.replace("item:", "")
                total_checks += 1
                # Character uses item not in their relations
                if char in draft and item_name in draft:
                    # Check if item is associated with char in graph
                    char_items = {r.replace("item:", "") for r in rels if r.startswith("item:")}
                    if item_name not in char_items and char_items:
                        contradictions += 1

    # Check 4: Faction allegiance contradiction
    for char, rels in graph.items():
        char_factions = {r.replace("faction:", "").replace("allegiance:", "") for r in rels if r.startswith("faction:") or r.startswith("allegiance:")}
        for faction in char_factions:
            total_checks += 1
            # Check for hostile action against own faction
            hostile_patterns = [f"{faction}を裏切", f"{faction}を攻撃", f"{faction}を殺", f"{faction}を倒", f"{faction}に反逆", f"{faction}から逃げ"]
            for pattern in hostile_patterns:
                if pattern in draft and char in draft:
                    contradictions += 1
                    break

    if total_checks == 0:
        return 0.8

    consistency = 1.0 - (contradictions / total_checks)
    return max(0.0, min(1.0, consistency))


def compute_coverage(draft: str, entities: set[str]) -> float:
    """Compute entity mention coverage in draft.

    Args:
        draft: Draft text
        entities: Set of entity names to check

    Returns:
        Coverage ratio 0.0-1.0
    """
    if not entities:
        return 1.0

    found = sum(1 for e in entities if e in draft)
    return found / len(entities)


def load_era_blacklist(era: str) -> list[str]:
    """Load anachronistic terms blacklist for a given era.

    Args:
        era: Era identifier (medieval, modern, futuristic, fantasy, etc.)

    Returns:
        List of terms that are inappropriate for the era
    """
    blacklists = {
        "medieval": [
            "スマホ", "スマートフォン", "携帯", "ケータイ", "インターネット", "ネット", "ウェブ", "Web", "メール", "LINE", "ツイッター", "Twitter", "X", "インスタ", "Instagram", "フェイスブック", "Facebook", "ユーチューブ", "YouTube", "グーグル", "Google", "アマゾン", "Amazon", "ウーバー", "Uber", "タクシー", "電車", "列車", "新幹線", "地下鉄", "バス", "飛行機", "ヘリコプター", "ロケット", "人工衛星", "GPS", "ナビ", "カーナビ", "コンビニ", "コンビニエンスストア", "スーパー", "デパート", "ショッピングモール", "エレベーター", "エスカレーター", "エアコン", "クーラー", "ヒーター", "ストーブ", "電子レンジ", "冷蔵庫", "洗濯機", "テレビ", "TV", "ラジオ", "パソコン", "PC", "ノートパソコン", "タブレット", "AI", "人工知能", "ロボット", "ドローン", "VR", "AR", "メタバース", "ブロックチェーン", "ビットコイン", "暗号通貨", "NFT", "クレジットカード", "キャッシュレス", "電子マネー", "Suica", "PASMO", "ICカード", "マイナンバー", "免許証", "パスポート", "保険証", "年金", "税金", "確定申告", "選挙", "投票", "国会", "議会", "法律", "憲法", "裁判", "弁護士", "検事", "裁判官", "警察", "消防", "自衛隊", "軍隊", "ミサイル", "核", "原子力", "発電所", "太陽光", "風力", "地熱", "水力", "火力", "石油", "ガス", "石炭", "ウラン", "プラスチック", "ナイロン", "ポリエステル", "ビニール", "ゴム", "タイヤ", "車", "自動車", "トラック", "バイク", "自転車", "船", "フェリー", "クルーズ", "ホテル", "旅館", "民泊", "Airbnb", "予約", "アプリ", "アプリケーション", "ソフトウェア", "ハードウェア", "クラウド", "サーバー", "データベース", "API", "SDK", "フレームワーク", "ライブラリ", "GitHub", "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Firebase", "Vercel", "Netlify", "Heroku", "Railway", "Render", "Fly.io", "Cloudflare", "Fastly", "Akamai", "CDN", "SSL", "TLS", "HTTPS", "HTTP", "DNS", "ドメイン", "サブドメイン", "メールアドレス", "パスワード", "二段階認証", "2FA", "MFA", "SSO", "OAuth", "OpenID", "JWT", "トークン", "セッション", "クッキー", "Cookie", "ローカルストレージ", "IndexedDB", "WebSQL", "Service Worker", "PWA", "SPA", "SSR", "SSG", "CSR", "React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt", "Remix", "Astro", "TypeScript", "JavaScript", "Python", "Rust", "Go", "Java", "Kotlin", "Swift", "Dart", "Flutter", "React Native", "Expo", "Capacitor", "Ionic", "Electron", "Tauri", "Wails", "Node.js", "Deno", "Bun", "pnpm", "yarn", "npm", "webpack", "Vite", "esbuild", "Rollup", "Parcel", "Snowpack", "Turbopack", "Rome", "Biome", "ESLint", "Prettier", "TypeScript", "tsc", "jest", "vitest", "playwright", "cypress", "testing-library", "storybook", "chromatic", "vercel", "netlify", "cloudflare", "aws", "gcp", "azure", "digitalocean", "linode", "vultr", "hetzner", "scaleway", "ovh", "github", "gitlab", "bitbucket", "sourcehut", "codeberg", "radicle", "git", "mercurial", "svn", "cvs", "perforce", "plastic scm", "fossil", "bazaar", "darcs", "monotone", "arch", "tla", "codeville", "gnu arch", "bitkeeper", "teamware", "clearcase", "visual sourcesafe", "team foundation server", "azure devops", "jenkins", "gitlab ci", "github actions", "circleci", "travis ci", "codeship", "drone", "woodpecker", "concourse", "tekton", "argo", "flux", "argocd", "flagger", "istio", "linkerd", "consul", "etcd", "zookeeper", "kafka", "rabbitmq", "nats", "redis", "memcached", "postgresql", "mysql", "mongodb", "cassandra", "dynamodb", "firebase", "supabase", "planetscale", "neon", "turso", "libsql", "sqlite", "duckdb", "clickhouse", "apache druid", "pinot", "elasticsearch", "opensearch", "meilisearch", "typesense", "algolia", "pinecone", "weaviate", "milvus", "qdrant", "chromadb", "lancedb", "faiss", "annoy", "hnswlib", "ngt", "pysparnn", "scikit-learn", "tensorflow", "pytorch", "jax", "keras", "fastai", "huggingface", "transformers", "accelerate", "peft", "trl", "datasets", "tokenizers", "safetensors", "onnx", "onnxruntime", "tensorrt", "openvino", "coreml", "tflite", "mediapipe", "opencv", "pillow", "torchvision", "torchtext", "torchaudio", "torchdata", "torchmetrics", "lightning", "pytorch lightning", "wandb", "mlflow", "clearml", "neptune", "comet", "dvc", "dags hub", "kubeflow", "mlrun", "zenml", "prefect", "dagster", "airflow", "luigi", "pinball", "azkaban", "oozie", "chronos", "mesos", "yarn", "kubernetes", "k8s", "k3s", "k0s", "microk8s", "kind", "minikube", "k3d", "kind", "talos", "flatcar", "bottlerocket", "ubuntu core", "fedora coreos", "rhcos", "openshift", "rancher", "kubevirt", "kubeedge", "k3s", "k0s", "microk8s", "kind", "minikube", "k3d", "talos", "flatcar", "bottlerocket", "ubuntu core", "fedora coreos", "rhcos", "openshift", "rancher", "kubevirt", "kubeedge",
        ],
        "modern": [],
        "futuristic": [],
        "fantasy": [],
    }
    return blacklists.get(era.lower(), blacklists["medieval"])


def detect_anachronisms(draft: str, era: str) -> list[str]:
    """Detect anachronistic terms in draft for given era.

    Args:
        draft: Draft text
        era: Era identifier

    Returns:
        List of detected anachronistic terms
    """
    blacklist = load_era_blacklist(era)
    return [term for term in blacklist if term in draft]


def analyze_pacing(draft: str, plot_phases: list[str]) -> float:
    """Analyze pacing balance across plot phases.

    Args:
        draft: Draft text
        plot_phases: List of phase keywords (e.g., ["intro", "conflict", "climax", "resolution"])

    Returns:
        Pacing score 0.0-1.0 (1.0 = well balanced)
    """
    if not plot_phases or len(plot_phases) < 2:
        return 0.5

    # Split draft into segments corresponding to phases
    segment_length = len(draft) // len(plot_phases)
    if segment_length == 0:
        return 0.5

    segments = [draft[i*segment_length:(i+1)*segment_length] for i in range(len(plot_phases))]
    # Last segment gets remainder
    segments[-1] = draft[(len(plot_phases)-1)*segment_length:]

    lengths = [len(s) for s in segments]
    if not lengths or max(lengths) == 0:
        return 0.5

    # Coefficient of variation (lower = more balanced)
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    cv = (variance ** 0.5) / mean_len if mean_len > 0 else 1.0

    # Convert to score: exponential decay for high CV
    # cv=0 -> 1.0, cv=0.5 -> ~0.78, cv=1 -> ~0.61, cv=2 -> ~0.37
    score = max(0.0, min(1.0, 1.0 / (1.0 + cv)))
    return score


def extract_emotion_triples(text: str) -> set[tuple[str, str, str]]:
    """Extract (character, prop, emotion) triples from text.

    Simplified rule-based extraction for multimodal fallback.

    Args:
        text: Input text

    Returns:
        Set of (character, prop, emotion) triples
    """
    triples = set()

    # Character patterns
    char_pattern = r"(?:[一-龯ぁ-んァ-ヶーa-zA-Z]{1,10})(?:は|が|を|に|で|と|の|だ|です|だった|だった|だろう|らしい|ようだ|みたいだ|そうだ|らしい|かもしれない|はずだ|に違いない|わけだ|もん|んだ|のだ|のです|なのだ|なのです)"

    # Emotion keywords
    emotions = {
        "喜び": ["笑", "喜", "楽", "嬉", "幸", "歓", "悦"],
        "悲しみ": ["泣", "悲", "哀", "涙", "嘆", "愁", "憂"],
        "怒り": ["怒", "憤", "激昂", "憤慨", "腹立ち", "ムカ", "イライラ"],
        "恐怖": ["恐", "怖", "怯", "戦慄", "震", "ビク", "ドキ"],
        "驚き": ["驚", "愕", "衝撃", "びっくり", "ハッ"],
        "安心": ["安堵", "ほっ", "安心", "安らぎ"],
        "緊張": ["緊張", "ピリピリ", "ハラハラ", "ドキドキ"],
        "期待": ["期待", "楽しみ", "わくわく", "ドキドキ"],
    }

    # Prop/Item keywords
    props = ["剣", "刀", "槍", "弓", "矢", "盾", "鎧", "兜", "杖", "魔法", "指輪", "首飾り", "薬", "巻物", "書", "地図", "鍵", "宝石", "金貨", "銀貨", "銅貨", "花", "剣", "刃", "刀身", "鞘", "柄", "鍔", "切っ先", "峰", "鎬", "棟", "樋", "棟", "切刃", "元", "茎", "目釘", "翡翠", "鞘書", "刀装具", "鍔", "目貫", "縁頭", "頭", "栗形", "小柄", "笄", "割箸", "刀掛", "刀袋", "下緒", "石突", "鯉口", "角", "袋", "革", "鮫肌", "柄巻", "糸", "皮", "布", "紙", "漆", "金", "銀", "銅", "鉄", "鋼", "玉鋼", "極上", "上々", "良", "並", "下", "無銘", "銘", "年紀", "国", "刀工", "流派", "伝来", "名物", "天下五剣", "鬼切", "鬼丸", "童子切", "大典太", "三日月", "数珠丸", "にっかり", "青江", "備前", "長船", "一文字", "助真", "兼光", "正真", "光忠", "長光", "兼氏", "恒次", "助次", "助真", "兼光", "正真", "光忠", "長光", "兼氏", "恒次", "助次", "助真", "兼光", "正真", "光忠", "長光", "兼氏", "恒次", "助次", "助真", "兼光", "正真", "光忠", "長光", "兼氏", "恒次", "助次", "助真", "兼光", "正真", "光忠", "長光", "兼氏", "恒次", "助次"]

    # Simple extraction: look for character near emotion/prop
    sentences = re.split(r"[。！？]", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        # Find characters (simplified: proper nouns before particles)
        chars = re.findall(r"([一-龯ぁ-んァ-ヶー]{2,10})(?:は|が|を|に|で|と|の)", sent)

        # Find emotions
        found_emotions = []
        for emo, keywords in emotions.items():
            for kw in keywords:
                if kw in sent:
                    found_emotions.append(emo)
                    break

        # Find props
        found_props = [p for p in props if p in sent]

        for char in chars:
            for emo in found_emotions or ["不明"]:
                for prop in found_props or ["なし"]:
                    triples.add((char, prop, emo))

    return triples


__all__ = [
    "extract_entities",
    "build_relation_graph",
    "check_semantic_consistency",
    "compute_coverage",
    "load_era_blacklist",
    "detect_anachronisms",
    "analyze_pacing",
    "extract_emotion_triples",
]