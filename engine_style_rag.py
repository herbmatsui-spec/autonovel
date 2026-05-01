import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)

class StyleRagManager:
    """
    文体RAGマネージャー:
    シーンの文脈に基づき、最適な「覇権文章サンプル」をベクトル検索で取得する。
    """
    def __init__(self, engine: "UltimateHegemonyEngine"):
        self.engine = engine
        self.embedding_model = "gemini-embedding-2" # 業界標準の高性能モデルに固定

    async def _get_embedding(self, text: str) -> List[float]:
        """Gemini APIを使用してテキストのベクトルを生成"""
        try:
            # Google GenAI SDKを使用してEmbeddingを取得
            # engine._generate_json の仕組みとは別に、SDKの embed_content を使用
            def _call():
                return self.engine.client.models.embed_content(
                    model=self.embedding_model,
                    contents=[text]
                )
            import asyncio
            res = await asyncio.to_thread(_call)
            return res.embeddings[0].values
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    async def add_master_fragment(self, tag: str, content: str, origin: str = "Masterpiece"):
        """理想的な文章をDBに登録（Embedding付き）"""
        vec = await self._get_embedding(content)
        if vec:
            await self.engine.repo.add_style_fragment(tag, content, vec, origin)
            return True
        return False

    async def find_best_sample(self, scene_description: str, phase: str = "Hate", tag_hint: Optional[str] = None, top_k: int = 2) -> List[str]:
        """
        WritingAgentとのインターフェース用。
        """
        return await self.find_best_samples(
            scene_description=scene_description,
            phase=phase,
            trope_hint=tag_hint,
            top_k=top_k
        )

    async def find_best_samples(self, scene_description: str, phase: str = "Hate", trope_hint: Optional[str] = None, top_k: int = 2) -> List[str]:
        """
        現在のシーンに最も近い文章サンプルを検索。
        1. クエリの強化（トロープとフェーズ情報を付与）
        2. トロープタグでの優先フィルタリング
        3. ベクトル類似度によるTop-K抽出
        """
        # 改善案①: トロープ情報をクエリに注入し、バズるリズムを優先
        trope_str = f"【Trope:{trope_hint}】" if trope_hint else ""
        enhanced_query = f"{trope_str} 【Phase:{phase}】 シーン描写: {scene_description}"

        # 検索クエリのベクトル化
        query_vec = await self._get_embedding(enhanced_query)
        if not query_vec:
            return []

        # トロープタグがあれば優先して候補を取得
        # 大量のデータを取得しないよう、必要に応じてDB側で制限をかけるべきだが
        # 現状はRepositoryの仕様に合わせて取得
        if trope_hint:
            candidates = await self.engine.repo.get_all_style_fragments(tag=trope_hint)
            if not candidates:
                candidates = await self.engine.repo.get_all_style_fragments()
        else:
            candidates = await self.engine.repo.get_all_style_fragments()

        if not candidates:
            # 改善案③: ジャンル等に合わせた高度なフォールバック
            return [self._get_fallback_sample(phase)]

        scored_samples = []
        v1 = np.array(query_vec)
        
        for cand in candidates:
            try:
                v2 = np.array(json.loads(cand["embedding_json"]))
                sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                scored_samples.append((sim, cand["content"]))
            except:
                continue
        
        # 類似度順にソート
        scored_samples.sort(key=lambda x: x[0], reverse=True)
        
        # 上位K件を抽出
        results = [content for sim, content in scored_samples[:top_k] if sim > 0.5]
        
        if not results:
            return [self._get_fallback_sample(phase)]

        logger.info(f"🎯 Style RAG: Found {len(results)} samples.")
        return results

    def _get_fallback_sample(self, phase: str) -> str:
        """検索ヒットなし、またはDB空時のための覇権テンプレート"""
        # 改善案③: 覇権作家特有のリズムをプリセット
        fallbacks = {
            "Hate": "嘲笑が、冷たく鼓膜を打つ。「無能が」「ゴミめ」。投げつけられる言葉の礫（つぶて）。少年はただ、俯き、泥を噛む。握りしめた拳だけが、爆発しそうな熱を帯びていた。",
            "Payoff": "静寂。先程まで勝ち誇っていた男の顔から、急速に色が失われる。「そ、そんな……」。理外の力。圧倒的な現実。観衆はただ、畏怖と共にその背中を見上げるしかなかった。",
            "Prep": "風が変わる。草原を歩く足取りは軽い。まだ誰も知らない、手に入れたばかりの力。それが体の奥底で、静かに、しかし確かに脈動を始めていた。",
            "Comedy": "「いや、おかしいだろ！」俺のツッコミが虚しく響く。目の前の美少女は、あろうことか伝説の聖剣でカボチャを切り刻んでいた。もったいねえ……。",
            "Love": "不意に、視線が重なる。心臓が跳ねた。微かに香る、甘い香草の匂い。彼女の頬が朱に染まるのを見て、俺は言葉を失う。時間が、止まったようだった。"
        }
        # キーがなければ Prep を返し、さらにランダム性を加味することも検討可能
        return fallbacks.get(phase) or random.choice(list(fallbacks.values()))

    def format_as_prompt(self, samples: List[str]) -> str:
        """プロンプトに注入する形式に整形"""
        if not samples:
            return ""
        
        formatted_samples = "\n\n".join([f"【サンプル{i+1}】\n{s}" for i, s in enumerate(samples)])
        
        return (
            "\n### 🏆 覇権作品・文体エミュレーション（最高位の質感） ###\n"
            "以下のサンプルは、ランキング1位を獲るための『商業的リズム』の極致である。\n"
            "これらのサンプルの内容ではなく、**【構造と質感】**を完璧にコピーせよ：\n"
            "1. 【視覚的白さ】: 漢字率を30%以下に抑え、スマホで読みやすい1-2行での改行リズムを模倣せよ。\n"
            "2. 【比喩のキレ】: 五感を刺激する鮮烈な比喩（例：心臓が跳ねる、胃が冷える）の密度を同等にせよ。\n"
            "3. 【心理と行動の黄金比】: 内面描写と物理的なアクションの配分をサンプルと完全に一致させよ。\n"
            "※固有名詞は無視し、読者がページを捲る手が止まらなくなる『文体の魔力』だけを抽出しろ。\n\n"
            "--- 理想の質感サンプル ---\n"
            f"{formatted_samples}\n"
            "--------------------------\n"
        )