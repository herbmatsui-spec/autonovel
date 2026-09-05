# src/agents/enrichment_agent.py
"""EnrichmentAgent - 執筆済みテキストを多角的にエンリッチメントするスキルエージェント"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.agents.event_bus import (
    ENRICHMENT_STARTED,
    ENRICHMENT_STEP_COMPLETED,
    ENRICHMENT_COMPLETED,
    ENRICHMENT_ERROR,
)
from src.agents.enrichment.sensory import expand_sensory_details_pipeline
from src.agents.enrichment.multimedia import generate_scenarios

logger = logging.getLogger(__name__)


class EnrichmentAgent(SkillAgent):
    """エンリッチメントスキルエージェント
    
    4つの機能で生成テキストを強化:
    1. トリビア挿入 - 世界観雑学の自然な組み込み
    2. 引用付与 - World Bible 典拠の脚注化
    3. 感覚拡充 - 抽象感情の五感具体化 (Show, Don't Tell)
    4. マルチメディアシナリオ - 派生フォーマット生成
    """

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        rag_service: Any = None,
        prompt_manager: Any = None,
        event_bus: Any = None,
    ):
        super().__init__(
            repo=repo,
            llm=llm,
            style_rag=style_rag,
            rag_prefetch=rag_prefetch,
            event_bus=event_bus,
        )
        self.rag_service = rag_service
        self.prompt_manager = prompt_manager
        self._config = self._load_config()
        self._bible_index: dict[str, list[dict]] = {}

    def _load_config(self) -> dict:
        """設定ファイル読み込み"""
        import yaml
        try:
            with open("config/enrichment.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f).get("enrichment", {})
        except Exception as e:
            logger.warning(f"Failed to load enrichment config: {e}")
            return {}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント"""
        self.emit_event(ENRICHMENT_STARTED, {
            "book_id": ctx.book_id,
            "ep_num": ctx.ep_num,
        })

        drafted_text = ctx.artifacts.get("drafted_text")
        writing_context = ctx.artifacts.get("writing_context", {})

        if not drafted_text:
            self.emit_event(ENRICHMENT_ERROR, {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "error": "drafted_text is required in artifacts",
            })
            return AgentResult(
                next_agent=AgentName.AUDIT,
                artifacts={},
                error="drafted_text is required in artifacts",
            )

        enrichment_metadata = {
            "trivia": [],
            "citations": [],
            "sensory": [],
            "multimedia": {},
        }

        try:
            # 機能フラグチェック
            if not self._config.get("enabled", False):
                logger.info("Enrichment disabled via config, passing through original text")
                self.emit_event(ENRICHMENT_COMPLETED, {
                    "book_id": ctx.book_id,
                    "ep_num": ctx.ep_num,
                    "skipped": True,
                })
                return AgentResult(
                    next_agent=AgentName.AUDIT,
                    artifacts={
                        "enriched_text": drafted_text,
                        "enrichment_metadata": enrichment_metadata,
                    },
                )

            # ブラインドレビューモードチェック（Step 59）
            blind_review_mode = ctx.artifacts.get("blind_review_mode", False)
            if blind_review_mode:
                logger.info("Blind review mode: skipping trivia/citation that may leak other agents' outputs")

            # 1. トリビア挿入
            if not blind_review_mode:
                enriched_text, trivia_meta = await self._enrich_with_trivia(drafted_text, writing_context)
                enrichment_metadata["trivia"] = trivia_meta
                self.emit_event(ENRICHMENT_STEP_COMPLETED, {
                    "book_id": ctx.book_id,
                    "ep_num": ctx.ep_num,
                    "step": "trivia_insertion",
                    "insertions_count": len(trivia_meta),
                })
            else:
                enriched_text = drafted_text
                enrichment_metadata["trivia"] = [{"skipped": True, "reason": "blind_review_mode"}]

            # 2. 引用付与
            if not blind_review_mode:
                enriched_text, citation_meta = await self._attach_citations(enriched_text, writing_context, ctx.book_id)
                enrichment_metadata["citations"] = citation_meta
                self.emit_event(ENRICHMENT_STEP_COMPLETED, {
                    "book_id": ctx.book_id,
                    "ep_num": ctx.ep_num,
                    "step": "citation_attachment",
                    "citations_count": len(citation_meta),
                })
            else:
                enrichment_metadata["citations"] = [{"skipped": True, "reason": "blind_review_mode"}]

            # 3. 感覚拡充
            enriched_text, sensory_meta = await self._expand_sensory_details(enriched_text, writing_context)
            enrichment_metadata["sensory"] = sensory_meta
            self.emit_event(ENRICHMENT_STEP_COMPLETED, {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "step": "sensory_expansion",
                "expansions_count": len(sensory_meta),
            })

            # 4. マルチメディアシナリオ生成
            multimedia_meta = await self._generate_multimedia_scenarios(enriched_text, writing_context)
            enrichment_metadata["multimedia"] = multimedia_meta
            self.emit_event(ENRICHMENT_STEP_COMPLETED, {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "step": "multimedia_scenarios",
                "formats_generated": list(multimedia_meta.keys()),
            })

            # トークン予算チェック
            enriched_text = self._enforce_token_budget(drafted_text, enriched_text)

            self.emit_event(ENRICHMENT_COMPLETED, {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "metadata_summary": {
                    "trivia_count": len(enrichment_metadata["trivia"]),
                    "citation_count": len(enrichment_metadata["citations"]),
                    "sensory_count": len(enrichment_metadata["sensory"]),
                    "multimedia_formats": list(enrichment_metadata["multimedia"].keys()),
                },
            })

            return AgentResult(
                next_agent=AgentName.AUDIT,
                artifacts={
                    "enriched_text": enriched_text,
                    "enrichment_metadata": enrichment_metadata,
                },
            )

        except Exception as e:
            logger.exception(f"EnrichmentAgent error: {e}")
            self.emit_event("enrichment.error", {
                "book_id": ctx.book_id,
                "ep_num": ctx.ep_num,
                "error": str(e),
            })
            # フォールバック: 元のテキストを無傷で渡す
            return AgentResult(
                next_agent=AgentName.AUDIT,
                artifacts={
                    "drafted_text": drafted_text,
                    "enriched_text": drafted_text,
                    "enrichment_metadata": enrichment_metadata,
                },
                error=f"Enrichment failed, using original: {e}",
            )


    # --- トリビア挿入関連 ---

    async def _enrich_with_trivia(self, text: str, writing_context: dict) -> tuple[str, list]:
        """トリビア挿入: 関連トリビアを検索し、自然な位置に挿入"""
        if not self._config.get("trivia_insertion", {}).get("enabled", True):
            return text, []

        # 1. シーン文脈とエンティティ抽出
        scene_context = self._extract_scene_context(text, writing_context)
        entities = self._extract_entities(writing_context)

        # 2. トリビア候補取得
        trivia_candidates = []
        if self.rag_service and self.repo:
            try:
                session = getattr(self.repo, "session", None)
                if not session and hasattr(self.repo, "db") and hasattr(self.repo.db, "get_session"):
                    session = self.repo.db.get_session()
                trivia_candidates = await self.rag_service.query_trivia_candidates(
                    session, scene_context, entities, limit=20
                )
            except Exception as e:
                logger.warning(f"Trivia candidate query failed: {e}")


        if not trivia_candidates:
            return text, []

        # 3. 関連度スコアリング（Step 14）
        scored_trivia = []
        for trivia in trivia_candidates:
            score = self._score_trivia_relevance(trivia, scene_context)
            if score >= self._config.get("trivia_insertion", {}).get("relevance_threshold", 0.7):
                trivia["relevance_score"] = score
                scored_trivia.append(trivia)

        scored_trivia.sort(key=lambda x: x["relevance_score"], reverse=True)
        max_insertions = self._config.get("trivia_insertion", {}).get("max_insertions_per_chapter", 5)
        scored_trivia = scored_trivia[:max_insertions]

        if not scored_trivia:
            return text, []

        # 4. 挿入ポイント検出（Step 15）
        insertion_points = self._find_insertion_points(text, len(scored_trivia))

        # 5. トリビア書き換えと挿入（Step 16）
        enriched_text = text
        insertions_metadata = []
        offset = 0  # 文字位置オフセット調整用

        # トークン予算上限（1トークン ≒ 2文字換算）
        max_tokens = self._config.get("token_budget", {}).get("max_enrichment_tokens", 1500)
        trivia_budget_chars = max(300, int(max_tokens * 0.8))  # トリビア用予算
        accumulated_trivia_chars = 0

        for i, (trivia, insert_pos) in enumerate(zip(scored_trivia, insertion_points)):
            adjusted_pos = insert_pos + offset
            surrounding = enriched_text[max(0, adjusted_pos-200):adjusted_pos+200]
            pov = writing_context.get("pov", "third_person")

            rewritten = await self._rewrite_trivia_for_context(
                trivia["fact"], surrounding, pov, trivia.get("entity")
            )

            if rewritten and rewritten != trivia["fact"]:
                # トークン予算チェック（超過時は優先度の低いトリビアを自動切り捨て）
                if accumulated_trivia_chars + len(rewritten) > trivia_budget_chars:
                    logger.info(
                        "Trivia token budget reached (%d / %d chars). Pruning remaining %d trivia candidates.",
                        accumulated_trivia_chars, trivia_budget_chars, len(scored_trivia) - i
                    )
                    break

                # 挿入実行
                before = enriched_text[:adjusted_pos]
                after = enriched_text[adjusted_pos:]
                enriched_text = before + rewritten + after

                inserted_len = len(rewritten)
                offset += inserted_len
                accumulated_trivia_chars += inserted_len

                insertions_metadata.append({
                    "position": adjusted_pos,
                    "original": "",
                    "enriched": rewritten,
                    "trivia_source": trivia.get("source_type", "unknown"),
                    "entity": trivia.get("entity"),
                    "relevance": trivia.get("relevance_score", 0),
                })

        return enriched_text, insertions_metadata

    def _extract_scene_context(self, text: str, writing_context: dict) -> str:
        """シーン文脈抽出（冒頭500文字＋文脈キーワード）"""
        context_parts = []
        context_parts.append(text[:500])
        if writing_context.get("location"):
            context_parts.append(f"場所: {writing_context['location']}")
        if writing_context.get("characters"):
            chars = writing_context["characters"]
            if isinstance(chars, list):
                context_parts.append(f"登場人物: {', '.join(chars[:5])}")
            elif isinstance(chars, str):
                context_parts.append(f"登場人物: {chars}")
        return " ".join(context_parts)

    def _extract_entities(self, writing_context: dict) -> list[str]:
        """エンティティ抽出"""
        entities = []
        if writing_context.get("characters"):
            chars = writing_context["characters"]
            if isinstance(chars, list):
                entities.extend(chars)
            elif isinstance(chars, str):
                entities.append(chars)
        if writing_context.get("location"):
            entities.append(writing_context["location"])
        if writing_context.get("key_items"):
            items = writing_context["key_items"]
            if isinstance(items, list):
                entities.extend(items)
        return list(set(entities))

    def _score_trivia_relevance(self, trivia: dict, scene_context: str) -> float:
        """トリビア関連度スコアリング（Step 14）"""
        fact_text = trivia.get("fact", "")
        context_lower = scene_context.lower()
        
        # 日本語対応: キーワード抽出で類似度計算
        def extract_keywords(text: str) -> set:
            import re
            keywords = set()
            # 2文字以上の漢字・カタカナ・ひらがな連続
            keywords.update(re.findall(r'[一-龯ァ-ヴーぁ-ん]{2,}', text))
            # 1文字以上の漢字・カタカナも追加（部分一致用）
            keywords.update(re.findall(r'[一-龯ァ-ヴーぁ-ん]', text))
            # 英単語
            keywords.update(re.findall(r'[a-zA-Z]{2,}', text.lower()))
            return keywords
        
        fact_keywords = extract_keywords(fact_text)
        context_keywords = extract_keywords(scene_context)
        
        if not fact_keywords or not context_keywords:
            return 0.0
        
        overlap = len(fact_keywords & context_keywords)
        union = len(fact_keywords | context_keywords)
        jaccard = overlap / union if union > 0 else 0.0
        
        # エンティティマッチボーナス（大幅増加）
        entity_bonus = 0.0
        if trivia.get("entity"):
            entity = trivia["entity"].lower()
            if entity in context_lower:
                entity_bonus = 0.5
        
        # ソースタイプ重み
        source_weight = {
            "world_bible": 1.0,
            "historical_facts": 0.8,
            "cultural_trivia": 0.7,
        }.get(trivia.get("source_type", "unknown"), 0.5)
        
        # ベーススコア + ボーナス
        base_score = jaccard * 1.5
        return min(1.0, (base_score + entity_bonus) * source_weight)

    def _find_insertion_points(self, text: str, max_points: int) -> list[int]:
        """自然な挿入ポイント検出（Step 15）"""
        points = []
        
        # 先頭も候補に追加
        if len(text) > 0:
            points.append(0)
        
        # 段落区切り（\n\n）を優先
        for match in re.finditer(r'\n\n', text):
            pos = match.end()
            if pos not in points:
                points.append(pos)
            if len(points) >= max_points:
                break
        
        # 足りない場合は文末（。！？）
        if len(points) < max_points:
            for match in re.finditer(r'[。！？]["」』]*\s*', text):
                pos = match.end()
                if not any(abs(pos - p) < 50 for p in points):
                    points.append(pos)
                    if len(points) >= max_points:
                        break
        
        # それでも足りない場合は等間隔
        if len(points) < max_points and len(text) > 100:
            segment_len = len(text) // (max_points + 1)
            for i in range(1, max_points + 1):
                pos = i * segment_len
                snap = text.rfind('。', max(0, pos-100), pos)
                if snap != -1:
                    pos = snap + 1
                if not any(abs(pos - p) < 30 for p in points):
                    points.append(pos)
        
        return sorted(points)[:max_points]

    async def _rewrite_trivia_for_context(
        self, trivia_fact: str, surrounding_text: str, pov: str, entity: str | None
    ) -> str:
        """トリビア文脈書き換え（Step 16）"""
        if not self.llm or not self.prompt_manager:
            return trivia_fact
        
        try:
            from prompts.enrichment.trivia_insertion import TRIVIA_INSERTION_PROMPT
            prompt = TRIVIA_INSERTION_PROMPT.format(
                original_text=surrounding_text[:400],
                trivia_candidates=trivia_fact,
                max_insertions=1,
                relevance_threshold=0.7,
            )
            return trivia_fact
        except Exception as e:
            logger.warning(f"Trivia rewrite failed: {e}")
            return trivia_fact

    # --- 引用付与関連 ---

    async def _attach_citations(self, text: str, writing_context: dict, book_id: int) -> tuple[str, list]:
        """引用付与: 事実記述に脚注マーカーを挿入"""
        if not self._config.get("citation_attachment", {}).get("enabled", True):
            return text, []

        # 1. Bible 索引取得・キャッシュ
        if not self._bible_index and self.rag_service and self.repo:
            try:
                session = getattr(self.repo, "session", None)
                if not session and hasattr(self.repo, "db") and hasattr(self.repo.db, "get_session"):
                    session = self.repo.db.get_session()
                self._bible_index = await self.rag_service.index_bible_sources(session, book_id)
            except Exception as e:
                logger.warning(f"Bible index build failed: {e}")


        if not self._bible_index:
            return text, []

        # 2. 事実記述抽出（Step 20）
        claims = self._extract_factual_claims(text)

        # 3. ソースマッチング（Step 21）
        claim_source_pairs = self._match_claims_to_sources(claims)

        if not claim_source_pairs:
            return text, []

        # 4. 脚注マーカー挿入（Step 22）
        enriched_text, citations_meta = self._insert_footnote_markers(text, claim_source_pairs)

        # 5. 引用スタイルフォーマット（Step 23）
        style = self._config.get("citation_attachment", {}).get("style", "footnote")
        final_text = self._format_citations(enriched_text, citations_meta, style)

        return final_text, citations_meta

    def _extract_factual_claims(self, text: str) -> list[dict]:
        """事実記述抽出（Step 20）"""
        claims = []
        
        # 文単位で分割してから各文をチェック（より確実）
        sentences = re.split(r'(?<=[。！？])', text)
        pos = 0
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                pos += len(sent) + 1
                continue
            
            # 事実記述らしい文の条件:
            # 1. 設定用語を含む
            # 2. 断定形（です/だ/である/という/過去形/丁寧語）で終わる
            # 3. 十分な長さ
            setting_keywords = ['魔法', 'スキル', '能力', 'システム', 'ルール', '設定', '世界', '歴史', 
                               'MP', 'HP', 'レベル', 'ステータス', 'アイテム', '武器', '剣', '呪文', 
                               '術式', '防具', '聖剣', 'ダンジョン', '遺跡', '国家', '都市', '組織', '勢力']
            
            has_setting_kw = any(kw in sent for kw in setting_keywords)
            # 断定形: です/だ/である/という/ます + 過去形(た/だ/た。/だ。) + 丁寧語
            # 辞書形動詞(う動詞/る動詞)も断定として扱う
            declarative_endings = (
                'です', 'だ', 'である', 'という', 
                'ます', 'ます。', 'です。', 'だ。', 'である。', 'という。',
                'た', 'た。', 'だ。', 'た。',  # 過去形
                'ました', 'ました。', 'ました',  # 丁寧過去
                'る', 'る。', 'う', 'う。', 'す', 'す。', 'く', 'く。', 'ぐ', 'ぐ。', 'つ', 'つ。', 'ぬ', 'ぬ。', 'ぶ', 'ぶ。', 'む', 'む。', 'す', 'す。',  # 五段動詞基本形
                'る', 'る。', 'える', 'える。', 'いる', 'いる。',  # 一段動詞基本形
            )
            is_declarative = any(sent.endswith(e) for e in declarative_endings)
            is_long_enough = len(sent) >= 8
            
            if has_setting_kw and is_declarative and is_long_enough:
                claims.append({
                    "text": sent,
                    "position": pos,
                    "end_position": pos + len(sent),
                })
            
            pos += len(sent) + 1
        
        # 重複除去（位置ベース）
        unique_claims = []
        for claim in claims:
            if not any(abs(claim["position"] - c["position"]) < 20 for c in unique_claims):
                unique_claims.append(claim)
        
        return unique_claims[:self._config.get("citation_attachment", {}).get("max_citations_per_chapter", 10)]

    def _match_claims_to_sources(self, claims: list[dict]) -> list[dict]:
        """ソースマッチング（Step 21）"""
        pairs = []
        
        for claim in claims:
            claim_text = claim["text"].lower()
            best_match = None
            best_score = 0.0
            
            # キーワードベースマッチング
            import re
            keywords = re.findall(r'[一-龯ァ-ヴー]{2,}|[a-zA-Z]{3,}', claim_text)
            
            for kw in keywords:
                if kw in self._bible_index:
                    for source in self._bible_index[kw]:
                        score = 0.5  # ベーススコア
                        # キーワード長ボーナス
                        score += min(0.3, len(kw) * 0.02)
                        if score > best_score:
                            best_score = score
                            best_match = source
            
            if best_match and best_score >= 0.5:
                pairs.append({
                    "claim": claim["text"],
                    "position": claim["position"],
                    "end_position": claim["end_position"],
                    "source": best_match,
                    "score": best_score,
                })
        
        return pairs

    def _insert_footnote_markers(self, text: str, claim_source_pairs: list[dict]) -> tuple[str, list]:
        """脚注マーカー挿入（Step 22）"""
        # 位置でソート（後ろから挿入してオフセット調整不要にする）
        sorted_pairs = sorted(claim_source_pairs, key=lambda x: x["position"], reverse=True)
        
        enriched_text = text
        citations_meta = []
        marker_counter = 0
        source_to_marker = {}  # 同一ソースは同一番号
        
        for pair in sorted_pairs:
            source_key = (pair["source"]["source"], pair["source"].get("page", ""))
            
            if source_key in source_to_marker:
                marker_num = source_to_marker[source_key]
            else:
                marker_counter += 1
                marker_num = marker_counter
                source_to_marker[source_key] = marker_num
            
            marker = f"[^{marker_num}]"
            insert_pos = pair["end_position"]
            
            # マーカー挿入
            enriched_text = enriched_text[:insert_pos] + marker + enriched_text[insert_pos:]
            
            citations_meta.append({
                "marker": marker_num,
                "claim": pair["claim"],
                "source": pair["source"],
                "score": pair["score"],
            })
        
        return enriched_text, citations_meta

    def _format_citations(self, text: str, citations_meta: list[dict], style: str) -> str:
        """引用スタイルフォーマット（Step 23）"""
        if style == "footnote":
            # 脚注スタイル: 文末に文献リスト追加
            if citations_meta:
                bibliography = "\n\n【参考文献】\n"
                for cite in citations_meta:
                    src = cite["source"]
                    bibliography += f"[^{cite['marker']}] {src['source']}"
                    if src.get("page"):
                        bibliography += f" {src['page']}"
                    bibliography += f" - {cite['claim'][:50]}...\n"
                return text + bibliography
        elif style == "bracket":
            # 括弧スタイル: インラインで展開（既にマーカー挿入済み）
            pass
        elif style == "endnote":
            # 後注スタイル: 章末にまとめる（footnote と同様）
            return self._format_citations(text, citations_meta, "footnote")
        
        return text

    # --- 感覚拡充関連 ---

    async def _expand_sensory_details(self, text: str, writing_context: dict) -> tuple[str, list]:
        """感覚拡充: 抽象的感情描写を五感ベースの具体描写に変換"""
        if not self._config.get("sensory_expansion", {}).get("enabled", True):
            return text, []

        scene_context = self._extract_scene_context(text, writing_context)
        pov = writing_context.get("pov", "third_person")

        try:
            enriched_text, expansions_meta = expand_sensory_details_pipeline(
                text=text,
                scene_context=scene_context,
                pov=pov,
                llm=self.llm,
                prompt_manager=self.prompt_manager,
            )
            return enriched_text, expansions_meta
        except Exception as e:
            logger.warning(f"Sensory expansion failed: {e}")
            return text, []

    # --- マルチメディアシナリオ関連 ---

    async def _generate_multimedia_scenarios(self, text: str, writing_context: dict) -> dict:
        """マルチメディアシナリオ生成: トリガーシーンから派生フォーマット生成"""
        if not self._config.get("multimedia_scenarios", {}).get("enabled", True):
            return {}

        try:
            scenarios = generate_scenarios(
                text=text,
                writing_context=writing_context,
                llm=self.llm,
            )
            return scenarios
        except Exception as e:
            logger.warning(f"Multimedia scenario generation failed: {e}")
            return {}

    def _enforce_token_budget(self, original: str, enriched: str) -> str:
        """Step 58: トークン予算制限。エンリッチメントによる肥大化を上限内に抑える。"""
        max_enrichment_tokens = self._config.get("token_budget", {}).get("max_enrichment_tokens", 1500)
        # 1トークン ≒ 約2文字換算
        max_allowed_growth_chars = max_enrichment_tokens * 2
        actual_growth = len(enriched) - len(original)

        if actual_growth <= max_allowed_growth_chars:
            return enriched

        logger.warning(
            "Enriched text growth (%d chars) exceeded token budget (%d chars). Enforcing fallback trimming.",
            actual_growth, max_allowed_growth_chars
        )
        # 超過時は、安全に元のテキストに許容範囲内の増分を結合するか、文境界で切り詰める
        allowed_len = len(original) + max_allowed_growth_chars
        trimmed = enriched[:allowed_len]
        last_period = trimmed.rfind("。")
        if last_period > len(original):
            return trimmed[:last_period + 1]
        return original